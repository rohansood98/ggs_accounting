from pathlib import Path
from ggs_accounting.db.db_manager import DatabaseManager


def create_manager(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(tmp_path / "test.sqlite")
    manager.init_db()
    return manager


def test_init_creates_tables_and_admin(tmp_path):
    mgr = create_manager(tmp_path)
    tables = {row[0] for row in mgr.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "Users" in tables
    assert mgr.verify_user("admin", "admin") == "Admin"


def test_item_crud(tmp_path):
    mgr = create_manager(tmp_path)
    grower_id = mgr.add_customer("Grower", customer_type="Grower")
    mgr.add_item("Apple", 10.0, 5, grower_id=grower_id)
    items = mgr.get_all_items()
    assert any(i["name"] == "Apple" for i in items)
    mgr.update_item("Apple", 1, stock_qty=10)
    assert mgr.get_all_items()[0]["stock_qty"] == 10
    mgr.delete_item("Apple", 1)
    assert mgr.get_all_items() == []


def test_create_invoice(tmp_path):
    mgr = create_manager(tmp_path)
    grower_id = mgr.add_customer("Grower", customer_type="Grower")
    mgr.add_item("Apple", 10.0, 5, grower_id=grower_id)
    customer_id = mgr.add_customer("Customer")
    inv_id = mgr.create_invoice(
        "2024-01-01",
        "Sale",
        customer_id,
        [{"name": "Apple", "grower_id": grower_id, "quantity": 2, "price": 10.0}],
        is_credit=True,
    )
    assert any(inv["inv_id"] == inv_id for inv in mgr.get_invoices())
    items = mgr.get_invoice_items(inv_id)
    assert items[0]["quantity"] == 2
    bal = mgr.conn.execute("SELECT balance FROM Customers WHERE customer_id=?", (customer_id,)).fetchone()[0]
    assert bal > 0


def test_settings(tmp_path):
    mgr = create_manager(tmp_path)
    mgr.set_setting("GST", "5")
    assert mgr.get_setting("GST") == "5"

