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
        price_excl_tax: float,
        stock_qty: float,
        grower_id: Optional[int] = None,
    ) -> None:
        name = camel_case(name)
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Items (name, grower_id, price_excl_tax, stock_qty) VALUES (?, ?, ?, ?)",
                (name, grower_id, price_excl_tax, stock_qty),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to add item: {exc}") from exc

    def update_item(self, name: str, grower_id: int, **kwargs) -> None:
        allowed = {"name", "grower_id", "price_excl_tax", "stock_qty"}
        if "name" in kwargs:
            kwargs["name"] = camel_case(str(kwargs["name"]))
        fields = [f"{k}=?" for k in kwargs if k in allowed]
        values = [kwargs[k] for k in kwargs if k in allowed]
        if not fields:
            return
        values.extend([name, grower_id])
        cur = self.conn.cursor()
        try:
            cur.execute(
                f"UPDATE Items SET {', '.join(fields)} WHERE name=? AND grower_id=?",
                values,
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to update item: {exc}") from exc

    def delete_item(self, name: str, grower_id: int) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM Items WHERE name=? AND grower_id=?", (name, grower_id))
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to delete item: {exc}") from exc

    def update_item_stock(self, name: str, grower_id: int, change: float) -> None:
        """Increment item stock by ``change`` which may be negative."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "UPDATE Items SET stock_qty = stock_qty + ? WHERE name=? AND grower_id=?",
                (change, name, grower_id),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to update item stock: {exc}") from exc

    def get_all_items(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM Items")
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
                cur.execute(
                    "INSERT INTO InvoiceItems (inv_id, item_name, grower_id, quantity, unit_price, line_total) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        inv_id,
                        item["name"],
                        item["grower_id"],
                        item["quantity"],
                        item["price"],
                        item["price"] * item["quantity"],
                    ),
                )
            if is_credit and customer_id:
                cur.execute(
                    "UPDATE Customers SET balance = balance + ? WHERE customer_id=?",
                    (subtotal, customer_id),
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
            cur.execute("SELECT * FROM InvoiceItems WHERE inv_id=?", (inv_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch invoice items: {exc}") from exc

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
        name TEXT NOT NULL,
        grower_id INTEGER NOT NULL,
        price_excl_tax REAL NOT NULL,
        stock_qty REAL NOT NULL DEFAULT 0,
        PRIMARY KEY(name, grower_id),
        FOREIGN KEY(grower_id) REFERENCES Customers(customer_id)
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
        item_name TEXT NOT NULL,
        grower_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY(inv_id) REFERENCES Invoices(inv_id),
        FOREIGN KEY(item_name, grower_id) REFERENCES Items(name, grower_id)
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
]

