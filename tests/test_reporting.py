import pytest

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models import reporting


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def test_run_raw_query(tmp_path):
    mgr = create_manager(tmp_path)
    mgr.add_party("Cust")
    cols, rows = mgr.run_raw_query("SELECT name FROM Parties")
    assert cols == ["name"]
    assert rows[0][0] == "Cust"


def test_run_raw_query_rejects_dml(tmp_path):
    mgr = create_manager(tmp_path)
    with pytest.raises(ValueError):
        mgr.run_raw_query("DELETE FROM Parties")


def test_party_balance_logic(tmp_path):
    mgr = create_manager(tmp_path)
    pid = mgr.add_party("A")
    mgr.update_party_balance(pid, 50)
    data = reporting.get_party_balances(mgr)
    assert data[0]["status"] == "Receivable"


def test_inventory_value(tmp_path):
    mgr = create_manager(tmp_path)
    mgr.add_item("Item", "cat", 2.0, 5)
    data, total = reporting.get_inventory_values(mgr)
    assert total == 10.0
