from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

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


def get_inventory_values(
    db: DatabaseManager,
    item_id: Optional[int] = None,
    customer_id: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], float]:
    """Return inventory valuations filtered by item or customer, using last purchase price."""
    cur = db.conn.cursor()
    cur.execute(
        """
        SELECT Inventory.stock_qty, Inventory.price_excl_tax,
               Items.item_id, Items.name AS item_name,
               Customers.customer_id, Customers.name AS customer_name
        FROM Inventory
        JOIN Items ON Inventory.item_id = Items.item_id
        JOIN Customers ON Inventory.customer_id = Customers.customer_id
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    if item_id is not None:
        rows = [r for r in rows if r["item_id"] == item_id]
    if customer_id is not None:
        rows = [r for r in rows if r["customer_id"] == customer_id]

    data: List[Dict[str, Any]] = []
    total_value = 0.0

    for r in rows:
        # Use last purchase price from InvoiceItems if available
        cur.execute(
            """
            SELECT unit_price FROM InvoiceItems
            JOIN Invoices ON Invoices.inv_id = InvoiceItems.inv_id
            WHERE InvoiceItems.item_id=? AND InvoiceItems.customer_id=? AND Invoices.type='Purchase'
            ORDER BY Invoices.date DESC, InvoiceItems.id DESC LIMIT 1
            """,
            (r["item_id"], r["customer_id"]),
        )
        price_row = cur.fetchone()
        price = price_row[0] if price_row else r["price_excl_tax"]
        value = r["stock_qty"] * price
        data.append({
            "item_id": r["item_id"],
            "name": r["item_name"],
            "customer_id": r["customer_id"],
            "customer_name": r["customer_name"],
            "stock": r["stock_qty"],  # Use 'stock' key for UI compatibility
            "price": price,
            "value": value,
        })
        total_value += value
    return data, total_value
