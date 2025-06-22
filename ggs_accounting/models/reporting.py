from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ggs_accounting.db.db_manager import DatabaseManager


BUILT_IN_QUERIES: dict[str, str] = {
    "Outstanding Balances": "SELECT name, balance FROM Customers WHERE balance <> 0",
    "Top Selling Items": (
        "SELECT item_name, customer_id, SUM(quantity) AS total_sold\n"
        "FROM InvoiceItems\n"
        "JOIN Invoices ON Invoices.inv_id = InvoiceItems.inv_id\n"
        "WHERE Invoices.date >= date('now', '-30 days') AND Invoices.type = 'Sale'\n"
        "GROUP BY item_name, customer_id\n"
        "ORDER BY total_sold DESC"
    ),
    "Low Stock Items": "SELECT name, customer_id, stock_qty FROM Items WHERE stock_qty < 10",
    "Recent Sales": (
        "SELECT date, total_amount FROM Invoices\n"
        "WHERE type = 'Sale'\n"
        "ORDER BY date DESC LIMIT 10"
    ),
    "High Value Customers": (
        "SELECT Customers.name, SUM(Invoices.total_amount) as total_spent\n"
        "FROM Invoices JOIN Customers ON Invoices.customer_id = Customers.customer_id\n"
        "WHERE Invoices.type = 'Sale'\n"
        "GROUP BY Customers.name\n"
        "ORDER BY total_spent DESC"
    ),
}


def run_query(db: DatabaseManager, sql: str) -> Tuple[List[str], List[tuple]]:
    """Execute SQL via DatabaseManager ensuring it's a SELECT."""
    return db.run_raw_query(sql)


def get_customer_balances(db: DatabaseManager) -> List[Dict[str, Any]]:
    cur = db.conn.cursor()
    cur.execute("SELECT name, balance FROM Customers")
    rows = cur.fetchall()
    result: List[Dict[str, Any]] = []
    for row in rows:
        bal = float(row["balance"])
        status = "Receivable" if bal > 0 else "Payable" if bal < 0 else "Settled"
        result.append({"name": row["name"], "balance": bal, "status": status})
    return result


def get_inventory_values(db: DatabaseManager) -> Tuple[List[Dict[str, Any]], float]:
    cur = db.conn.cursor()
    cur.execute(
        """
        SELECT Items.name, Inventory.stock_qty, Inventory.price_excl_tax
        FROM Inventory JOIN Items ON Inventory.item_id = Items.item_id
        """
    )
    rows = cur.fetchall()
    total_value = 0.0
    result: List[Dict[str, Any]] = []
    for row in rows:
        value = float(row["stock_qty"] * row["price_excl_tax"])
        total_value += value
        result.append(
            {
                "name": row["name"],
                "stock": row["stock_qty"],
                "price": row["price_excl_tax"],
                "value": value,
            }
        )
    return result, total_value
