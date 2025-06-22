from pathlib import Path
import sqlite3

from ggs_accounting.utils import hash_password

DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'database.sqlite'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

CREATE_TABLE_QUERIES = [
    """CREATE TABLE IF NOT EXISTS Users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )""",
    # Global Items table: item_id, name, item_code
    """CREATE TABLE IF NOT EXISTS Items(
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        item_code TEXT NOT NULL UNIQUE
    )""",
    # Customer details
    """CREATE TABLE IF NOT EXISTS Customers(
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_info TEXT,
        customer_type TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0
    )""",
    # Inventory: customer_id, item_id, price, stock
    """CREATE TABLE IF NOT EXISTS Inventory(
        inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        price_excl_tax REAL NOT NULL,
        stock_qty REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id),
        FOREIGN KEY(item_id) REFERENCES Items(item_id),
        UNIQUE(customer_id, item_id)
    )""",
    # Invoices
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
    # InvoiceItems: inv_id, item_id, customer_id, quantity, unit_price, line_total
    """CREATE TABLE IF NOT EXISTS InvoiceItems(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inv_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY(inv_id) REFERENCES Invoices(inv_id),
        FOREIGN KEY(item_id) REFERENCES Items(item_id),
        FOREIGN KEY(customer_id) REFERENCES Customers(customer_id)
    )""",
    """CREATE TABLE IF NOT EXISTS Settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS SavedQueries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sql TEXT NOT NULL
    )"""
]


def get_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as exc:
        raise RuntimeError(f"Failed to connect to database: {exc}") from exc


def create_default_admin(conn: sqlite3.Connection):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM Users")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", hash_password("admin"), "Admin"),
            )
            conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise RuntimeError(f"Failed to create default admin: {exc}") from exc


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        for query in CREATE_TABLE_QUERIES:
            cursor.execute(query)
        conn.commit()
        create_default_admin(conn)
    finally:
        conn.close()

