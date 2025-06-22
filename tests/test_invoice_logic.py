import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models.invoice_logic import InvoiceLogic


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def test_invoice_logic_updates_stock(tmp_path):
    mgr = create_manager(tmp_path)
    customer_id = mgr.add_customer("Grower", customer_type="Grower")
    item_id = mgr.add_item("Banana", "BAN", 5.0, 10, customer_id=customer_id)
    buyer_id = mgr.add_customer("Customer")
    logic = InvoiceLogic(mgr)
    logic.create_invoice(
        "Sale",
        buyer_id,
        [{"item_id": item_id, "customer_id": buyer_id, "source_id": customer_id, "quantity": 4, "price": 5.0}],
        date="2024-01-02",
        is_credit=True,
        amount_paid=0.0,
    )
    qty = mgr.conn.execute("SELECT stock_qty FROM Inventory WHERE item_id=? AND customer_id=?", (item_id, customer_id)).fetchone()[0]
    assert qty == 6
    bal = mgr.conn.execute("SELECT balance FROM Customers WHERE customer_id=?", (buyer_id,)).fetchone()[0]
    assert bal == 20.0


def test_sale_uses_purchase_price(tmp_path):
    mgr = create_manager(tmp_path)
    grower = mgr.add_customer("Grower", customer_type="Grower")
    item = mgr.add_item("Apple", "APL", 10.0, 20, customer_id=grower)
    buyer = mgr.add_customer("Buyer")
    logic = InvoiceLogic(mgr)
    # Sell at a different price; inventory should reduce using the purchase price
    logic.create_invoice(
        "Sale",
        buyer,
        [
            {
                "item_id": item,
                "customer_id": buyer,
                "source_id": grower,
                "quantity": 5,
                "price": 15.0,
                "price_excl_tax": 15.0,
            }
        ],
        date="2024-01-03",
        is_credit=True,
        amount_paid=0.0,
    )
    rows = list(
        mgr.conn.execute(
            "SELECT price_excl_tax, stock_qty FROM Inventory WHERE item_id=? AND customer_id=?",
            (item, grower),
        )
    )
    assert len(rows) == 1
    assert rows[0]["stock_qty"] == 15.0


def test_purchase_invoice_new_price_creates_row(tmp_path):
    mgr = create_manager(tmp_path)
    grower = mgr.add_customer("Grower", customer_type="Grower")
    item = mgr.add_item("Apple", "APL", 10.0, 5, customer_id=grower)
    logic = InvoiceLogic(mgr)
    logic.create_invoice(
        "Purchase",
        grower,
        [
            {
                "item_id": item,
                "customer_id": grower,
                "quantity": 5,
                "price": 12.0,
                "price_excl_tax": 12.0,
            }
        ],
        date="2024-01-04",
        amount_paid=60.0,
    )
    rows = list(
        mgr.conn.execute(
            "SELECT price_excl_tax, stock_qty FROM Inventory WHERE item_id=? AND customer_id=? ORDER BY price_excl_tax",
            (item, grower),
        )
    )
    assert len(rows) == 2
    assert rows[0][0] == 10.0 and rows[0][1] == 5
    assert rows[1][0] == 12.0 and rows[1][1] == 5

