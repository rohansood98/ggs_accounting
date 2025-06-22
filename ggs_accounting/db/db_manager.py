from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ggs_accounting.utils import hash_password, verify_password


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
    def add_item(self, name: str, category: str, price_excl_tax: float, stock_qty: float) -> int:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Items (name, category, price_excl_tax, stock_qty) VALUES (?, ?, ?, ?)",
                (name, category, price_excl_tax, stock_qty),
            )
            self.conn.commit()
            lastrowid = cur.lastrowid
            if lastrowid is None:
                raise RuntimeError("Failed to retrieve lastrowid after adding item.")
            return lastrowid
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to add item: {exc}") from exc

    def update_item(self, item_id: int, **fields: Any) -> None:
        if not fields:
            return
        columns = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [item_id]
        sql = f"UPDATE Items SET {columns} WHERE item_id=?"
        cur = self.conn.cursor()
        try:
            cur.execute(sql, values)
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to update item: {exc}") from exc

    def delete_item(self, item_id: int) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM Items WHERE item_id=?", (item_id,))
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to delete item: {exc}") from exc

    def update_item_stock(self, item_id: int, change: float) -> None:
        """Increment item stock by ``change`` which may be negative."""
        cur = self.conn.cursor()
        try:
            cur.execute(
                "UPDATE Items SET stock_qty = stock_qty + ? WHERE item_id=?",
                (change, item_id),
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

    # ---- Parties ----
    def add_party(self, name: str, contact_info: str = "") -> int:
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO Parties (name, contact_info) VALUES (?, ?)",
                (name, contact_info),
            )
            self.conn.commit()
            lastrowid = cur.lastrowid
            if lastrowid is None:
                raise RuntimeError("Failed to retrieve lastrowid after adding party.")
            return lastrowid
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to add party: {exc}") from exc

    def update_party_balance(self, party_id: int, amount: float) -> None:
        cur = self.conn.cursor()
        try:
            cur.execute("UPDATE Parties SET balance = balance + ? WHERE party_id=?", (amount, party_id))
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise RuntimeError(f"Failed to update party balance: {exc}") from exc

    def get_all_parties(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT * FROM Parties")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"Failed to fetch parties: {exc}") from exc

    # ---- Invoices ----
    def create_invoice(
        self,
        date: str,
        inv_type: str,
        party_id: Optional[int],
        items: Iterable[Dict[str, Any]],
        is_credit: bool = False,
    ) -> int:
        cur = self.conn.cursor()
        try:
            subtotal = sum(item["price"] * item["quantity"] for item in items)
            cur.execute(
                """INSERT INTO Invoices
                   (date, type, party_id, subtotal, total_amount, is_credit)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (date, inv_type, party_id, subtotal, subtotal, int(is_credit)),
            )
            inv_id = cur.lastrowid
            if inv_id is None:
                raise RuntimeError("Failed to retrieve lastrowid after creating invoice.")
            for item in items:
                cur.execute(
                    "INSERT INTO InvoiceItems (inv_id, item_id, quantity, unit_price, line_total) VALUES (?, ?, ?, ?, ?)",
                    (
                        inv_id,
                        item["item_id"],
                        item["quantity"],
                        item["price"],
                        item["price"] * item["quantity"],
                    ),
                )
            if is_credit and party_id:
                cur.execute("UPDATE Parties SET balance = balance + ? WHERE party_id=?", (subtotal, party_id))
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
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        price_excl_tax REAL NOT NULL,
        stock_qty REAL NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS Parties(
        party_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_info TEXT,
        balance REAL NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS Invoices(
        inv_id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        party_id INTEGER,
        subtotal REAL NOT NULL,
        total_amount REAL NOT NULL,
        is_credit INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(party_id) REFERENCES Parties(party_id)
    )""",
    """CREATE TABLE IF NOT EXISTS InvoiceItems(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inv_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY(inv_id) REFERENCES Invoices(inv_id),
        FOREIGN KEY(item_id) REFERENCES Items(item_id)
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

