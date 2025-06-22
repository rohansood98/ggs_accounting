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
    mgr.add_item("Item", 2.0, 5, customer_id=customer_id)
    data, total = reporting.get_inventory_values(mgr)
    assert total == 10.0
