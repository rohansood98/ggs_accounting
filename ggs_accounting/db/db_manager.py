from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ggs_accounting.utils import hash_password, verify_password, camel_case


class DatabaseManager:
    """Simple SQLite database manager."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        base = Path(__file__).resolve().parents[2]
        self.db_path = db_path or base / "data" / "database.sqlite"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(self.db_path)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Unable to open database: {exc}") from exc
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def init_db(self) -> None:
        """Create tables if they don't exist and ensure default admin."""
        cursor = self.conn.cursor()
        try:
            for query in CREATE_TABLE_QUERIES:
                cursor.execute(query)
            self.conn.commit()
            self._create_default_admin()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Database initialization failed: {exc}") from exc

    def _create_default_admin(self) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM Users")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)",
                    ("admin", hash_password("admin"), "Admin"),
                )
                self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to create default admin: {exc}") from exc

    # ---- Users ----
    def create_user(self, username: str, password: str, role: str) -> int:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, hash_password(password), role),
            )
            self.conn.commit()
            lastrowid = cur.lastrowid
            if lastrowid is None:
                raise RuntimeError("Failed to retrieve lastrowid after creating user.")
            return lastrowid
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to create user: {exc}") from exc

    def get_user(self, username: str) -> Optional["User"]:
        from ggs_accounting.models.auth import User

        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT username, password_hash, role FROM Users WHERE username=?",
                (username,),
            )
            row = cur.fetchone()
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch user: {exc}") from exc
        if row:
            return User(
                username=row["username"],
                password_hash=row["password_hash"],
                role=row["role"],
            )
        return None

    def verify_user(self, username: str, password: str) -> Optional[str]:
        try:
            user = self.get_user(username)
        except RuntimeError as exc:
            raise RuntimeError(f"Failed to verify user: {exc}") from exc
        if user and user.verify_password(password):
            return user.role
        return None

    # ---- Items ----
    def add_item(
        self,
        name: str,
        item_code: str,
        price_excl_tax: float,
        stock_qty: float,
        customer_id: int,
    ) -> int:
        """Add a global item if needed and create an inventory record."""
        name = camel_case(name)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT OR IGNORE INTO Items (name, item_code) VALUES (?, ?)",
                (name, item_code),
            )
            cur.execute("SELECT item_id FROM Items WHERE name=?", (name,))
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to retrieve item_id after insert")
            item_id = int(row["item_id"])
            cur.execute(
                "INSERT INTO Inventory (customer_id, item_id, price_excl_tax, stock_qty) VALUES (?, ?, ?, ?)",
                (customer_id, item_id, price_excl_tax, stock_qty),
            )
            self.conn.commit()
            return item_id
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to add item: {exc}") from exc

    def update_item(self, item_id: int, customer_id: int, price_excl_tax: float, **kwargs) -> None:
        """Update item or inventory fields."""
        item_fields = {}
        inv_fields = {}
        if "name" in kwargs:
            item_fields["name"] = camel_case(str(kwargs["name"]))
        if "item_code" in kwargs:
            item_fields["item_code"] = kwargs["item_code"]
        for key in ("price_excl_tax", "stock_qty"):
            if key in kwargs:
                inv_fields[key] = kwargs[key]
        cur = self.conn.cursor()
        try:
            if item_fields:
                sets = ", ".join(f"{k}=?" for k in item_fields)
                cur.execute(
                    f"UPDATE Items SET {sets} WHERE item_id=?",
                    [*item_fields.values(), item_id],
                )
            if inv_fields:
                sets = ", ".join(f"{k}=?" for k in inv_fields)
                cur.execute(
                    f"UPDATE Inventory SET {sets} WHERE item_id=? AND customer_id=? AND price_excl_tax=?",
                    [*inv_fields.values(), item_id, customer_id, price_excl_tax],
                )
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to update item: {exc}") from exc

    def delete_item(self, item_id: int, customer_id: int) -> None:
        """Delete an inventory item if not referenced in InvoiceItems."""
        cur = self.conn.cursor()
        # Check for references in InvoiceItems
        ref_count = cur.execute(
            "SELECT COUNT(*) FROM InvoiceItems WHERE item_id=? AND customer_id=?",
            (item_id, customer_id),
        ).fetchone()[0]
        if ref_count > 0:
            raise RuntimeError(
                "Cannot delete item: It is referenced in one or more invoices."
            )
        try:
            cur.execute(
                "DELETE FROM Inventory WHERE item_id=? AND customer_id=?",
                (item_id, customer_id),
            )
            cur.execute(
                "DELETE FROM Items WHERE item_id=?",
                (item_id,),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to delete item: {exc}") from exc

    def update_item_stock(self, item_id: int, customer_id: int, price_excl_tax: float, change: float) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "UPDATE Inventory SET stock_qty = stock_qty + ? WHERE item_id=? AND customer_id=? AND price_excl_tax=?",
                (change, item_id, customer_id, price_excl_tax),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to update item stock: {exc}") from exc

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Return joined inventory records with item details."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT Inventory.customer_id, Inventory.price_excl_tax, Inventory.stock_qty,
                       Items.item_id, Items.name, Items.item_code
                FROM Inventory JOIN Items ON Inventory.item_id = Items.item_id
                """
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch items: {exc}") from exc

    # ---- Customers ----
    def add_customer(
        self, name: str, contact_info: str = "", customer_type: str = "Buyer"
    ) -> int:
        """Add a new customer and return its ID."""
        name = camel_case(name)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Customers (name, contact_info, customer_type) VALUES (?, ?, ?)",
                (name, contact_info, customer_type),
            )
            self.conn.commit()
            lastrowid = cur.lastrowid
            if lastrowid is None:
                raise RuntimeError("Failed to retrieve lastrowid after adding customer.")
            return lastrowid
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to add customer: {exc}") from exc

    def update_customer_balance(self, customer_id: int, amount: float) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "UPDATE Customers SET balance = balance + ? WHERE customer_id=?",
                (amount, customer_id),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to update customer balance: {exc}") from exc

    def get_all_customers(self) -> List[Dict[str, Any]]:
        """Return all customers."""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM Customers")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch customers: {exc}") from exc

    def get_customers_by_type(self, customer_type: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT * FROM Customers WHERE customer_type=?",
                (customer_type,),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch customers: {exc}") from exc

    # ---- Invoices ----
    def create_invoice(
        self,
        date: str,
        inv_type: str,
        customer_id: Optional[int],
        items: Iterable[Dict[str, Any]],
        is_credit: bool = False,
        amount_paid: float = 0.0,
    ) -> int:
        cur = self.conn.cursor()
        try:
            subtotal = sum(item["price"] * item["quantity"] for item in items)
            cur.execute(
                """INSERT INTO Invoices
                   (date, type, customer_id, subtotal, total_amount, is_credit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (date, inv_type, customer_id, subtotal, subtotal, int(is_credit)),
            )
            inv_id = cur.lastrowid
            if inv_id is None:
                raise RuntimeError("Failed to retrieve lastrowid after creating invoice.")
            for item in items:
                item_id = item.get("item_id")
                if item_id is None:
                    cur.execute("SELECT item_id FROM Items WHERE name=?", (item["name"],))
                    row = cur.fetchone()
                    if row is None:
                        raise RuntimeError("Unknown item")
                    item_id = int(row["item_id"])
                cur.execute(
                    "INSERT INTO InvoiceItems (inv_id, item_id, customer_id, source_id, quantity, unit_price, line_total) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        inv_id,
                        item_id,
                        item.get("customer_id"),
                        item.get("source_id"),
                        item["quantity"],
                        item["price"],
                        item["price"] * item["quantity"],
                    ),
                )
            if inv_type == "Sale":
                cur.execute("INSERT INTO Sales (inv_id) VALUES (?)", (inv_id,))
            elif inv_type == "Purchase":
                cur.execute("INSERT INTO Purchases (inv_id) VALUES (?)", (inv_id,))
            # Update customer balance for credit transactions
            if is_credit and customer_id:
                if inv_type == "Sale":
                    # Buyer owes you: increase their balance
                    cur.execute(
                        "UPDATE Customers SET balance = balance + ? WHERE customer_id=?",
                        (subtotal - amount_paid, customer_id),
                    )
                elif inv_type == "Purchase":
                    # You owe grower: decrease their balance
                    cur.execute(
                        "UPDATE Customers SET balance = balance - ? WHERE customer_id=?",
                        (subtotal - amount_paid, customer_id),
                    )
            self.conn.commit()
            return inv_id
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to create invoice: {exc}") from exc

    def get_invoices(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        sql = "SELECT * FROM Invoices"
        params: List[Any] = []
        if start_date and end_date:
            sql += " WHERE date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        try:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch invoices: {exc}") from exc

    def get_invoice_items(self, inv_id: int) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT InvoiceItems.*, Items.name
                FROM InvoiceItems
                JOIN Items ON InvoiceItems.item_id = Items.item_id
                WHERE inv_id=?
                """,
                (inv_id,),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch invoice items: {exc}") from exc

    # ---- Payments ----
    def record_payment(self, customer_id: int, amount: float, date: str) -> int:
        """Record a payment and update balance."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Payments (customer_id, date, amount) VALUES (?, ?, ?)",
                (customer_id, date, amount),
            )
            cur.execute(
                "UPDATE Customers SET balance = balance - ? WHERE customer_id=?",
                (amount, customer_id),
            )
            self.conn.commit()
            if cur.lastrowid is None:
                raise RuntimeError("Failed to retrieve lastrowid after payment")
            return cur.lastrowid
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to record payment: {exc}") from exc

    def get_payments(self, customer_id: Optional[int] = None) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        sql = "SELECT * FROM Payments"
        params: List[Any] = []
        if customer_id is not None:
            sql += " WHERE customer_id=?"
            params.append(customer_id)
        try:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch payments: {exc}") from exc

    # ---- Settings ----
    def set_setting(self, key: str, value: str) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("REPLACE INTO Settings (key, value) VALUES (?, ?)", (key, value))
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to set setting: {exc}") from exc

    def get_setting(self, key: str) -> Optional[str]:
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT value FROM Settings WHERE key=?", (key,))
            row = cur.fetchone()
            return row[0] if row else None
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to get setting: {exc}") from exc

    # ---- Saved Queries ----
    def save_query(self, name: str, sql: str) -> int:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO SavedQueries (name, sql) VALUES (?, ?)",
                (name, sql),
            )
            self.conn.commit()
            lastrowid = cur.lastrowid
            if lastrowid is None:
                raise RuntimeError("Failed to retrieve lastrowid after saving query.")
            return lastrowid
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to save query: {exc}") from exc

    def get_saved_queries(self) -> List[Dict[str, Any]]:
        """Return list of saved queries."""
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT id, name, sql FROM SavedQueries")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:  # pragma: no cover - unexpected errors
            raise RuntimeError(f"Failed to fetch saved queries: {exc}") from exc

    def run_raw_query(self, sql: str) -> tuple[list[str], list[tuple]]:
        """Execute a SELECT SQL statement and return (columns, rows)."""
        if not sql.strip().lower().startswith("select"):
            raise ValueError("Only SELECT queries are allowed")
        cur = self.conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description or []]
            return cols, rows
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to execute query: {exc}") from exc


CREATE_TABLE_QUERIES = [
    """CREATE TABLE IF NOT EXISTS Users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS Items(
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        item_code TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS Inventory(
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        price_excl_tax REAL NOT NULL,
        stock_qty REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id),
        FOREIGN KEY(item_id) REFERENCES Items(item_id),
        UNIQUE(customer_id, item_id, price_excl_tax)
    )""",
    """CREATE TABLE IF NOT EXISTS Customers(
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_info TEXT,
        customer_type TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS Invoices(
        inv_id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        customer_id INTEGER,
        subtotal REAL NOT NULL,
        total_amount REAL NOT NULL,
        is_credit INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id)
    )""",
    """CREATE TABLE IF NOT EXISTS InvoiceItems(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inv_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        source_id INTEGER,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY(inv_id) REFERENCES Invoices(inv_id),
        FOREIGN KEY(item_id) REFERENCES Items(item_id),
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id),
        FOREIGN KEY(source_id) REFERENCES Customers(customer_id)
    )""",
    """CREATE TABLE IF NOT EXISTS Sales(
        inv_id INTEGER PRIMARY KEY,
        FOREIGN KEY(inv_id) REFERENCES Invoices(inv_id)
    )""",
    """CREATE TABLE IF NOT EXISTS Purchases(
        inv_id INTEGER PRIMARY KEY,
        FOREIGN KEY(inv_id) REFERENCES Invoices(inv_id)
    )""",
    """CREATE TABLE IF NOT EXISTS Settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS SavedQueries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sql TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS Payments(
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id)
    )""",
]

