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
    item_id = mgr.add_item("Banana", "Fruit", 5.0, 10)
    party_id = mgr.add_party("Customer")
    logic = InvoiceLogic(mgr)
    logic.create_invoice(
        "Sale",
        party_id,
        [{"item_id": item_id, "quantity": 4, "price": 5.0}],
        date="2024-01-02",
        is_credit=True,
    )
    qty = mgr.conn.execute("SELECT stock_qty FROM Items WHERE item_id=?", (item_id,)).fetchone()[0]
    assert qty == 6
    bal = mgr.conn.execute("SELECT balance FROM Parties WHERE party_id=?", (party_id,)).fetchone()[0]
    assert bal == 20.0

