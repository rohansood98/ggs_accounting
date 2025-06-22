import pytest

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models import reporting


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def test_run_raw_query(tmp_path):
    mgr = create_manager(tmp_path)
    mgr.add_customer("Cust")
    cols, rows = mgr.run_raw_query("SELECT name FROM Customers")
    assert cols == ["name"]
    assert rows[0][0] == "Cust"


def test_run_raw_query_rejects_dml(tmp_path):
    mgr = create_manager(tmp_path)
    with pytest.raises(ValueError):
        mgr.run_raw_query("DELETE FROM Customers")


def test_party_balance_logic(tmp_path):
    mgr = create_manager(tmp_path)
    pid = mgr.add_customer("A")
    mgr.update_customer_balance(pid, 50)
    data = reporting.get_customer_balances(mgr)
    assert data[0]["status"] == "Receivable"


def test_inventory_value(tmp_path):
    mgr = create_manager(tmp_path)
    customer_id = mgr.add_customer("Grower", customer_type="Grower")
    mgr.add_item("Item", "ITM", 2.0, 5, customer_id=customer_id)
    data, total = reporting.get_inventory_values(mgr)
    assert total == 10.0


def test_inventory_value_by_customer(tmp_path):
    mgr = create_manager(tmp_path)
    c1 = mgr.add_customer("G1", customer_type="Grower")
    c2 = mgr.add_customer("G2", customer_type="Grower")
    mgr.add_item("Apple", "APL", 2.0, 5, customer_id=c1)
    mgr.add_item("Banana", "BAN", 3.0, 4, customer_id=c2)
    data, total = reporting.get_inventory_values(mgr, item_id=None)
    names = {d["name"] for d in data}
    assert names == {"Apple", "Banana"}
    assert total == pytest.approx(5 * 2.0 + 4 * 3.0)


def test_inventory_value_multiple_prices(tmp_path):
    mgr = create_manager(tmp_path)
    g = mgr.add_customer("Grower", customer_type="Grower")
    item = mgr.add_item("Tomato", "TOM", 2.0, 5, customer_id=g)
    mgr.update_item_stock(item, g, 3.0, 10)
    data, total = reporting.get_inventory_values(mgr, customer_id=g)
    values = sorted((d["price"], d["stock"]) for d in data if d["item_id"] == item)
    assert values == [(2.0, 5), (3.0, 10)]
    assert total == pytest.approx(5 * 2.0 + 10 * 3.0)
