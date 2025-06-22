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
        [{"item_id": item_id, "customer_id": customer_id, "quantity": 4, "price": 5.0}],
        date="2024-01-02",
        is_credit=True,
        amount_paid=0.0,
    )
    qty = mgr.conn.execute("SELECT stock_qty FROM Inventory WHERE item_id=? AND customer_id=?", (item_id, customer_id)).fetchone()[0]
    assert qty == 6
    bal = mgr.conn.execute("SELECT balance FROM Customers WHERE customer_id=?", (buyer_id,)).fetchone()[0]
    assert bal == 20.0

