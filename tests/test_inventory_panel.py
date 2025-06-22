import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.ui.inventory_panel import InventoryPanel


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def ensure_app():
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def test_inventory_loads_items(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    cust = mgr.add_customer("Grower", customer_type="Grower")
    mgr.add_item("Apple", "APL", 10.0, 5, customer_id=cust)
    mgr.add_item("Carrot", "CRT", 5.0, 10, customer_id=cust)
    panel = InventoryPanel(mgr)
    assert panel.table.rowCount() == 2


def test_inventory_filter(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    cust = mgr.add_customer("Grower", customer_type="Grower")
    mgr.add_item("Apple", "APL", 10.0, 5, customer_id=cust)
    mgr.add_item("Carrot", "CRT", 5.0, 10, customer_id=cust)
    panel = InventoryPanel(mgr)
    panel.search_edit.setText("apple")
    QtWidgets.QApplication.processEvents()
    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 0).text() == "Apple"


def test_inventory_panel_multiple_purchase_rows(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    g = mgr.add_customer("Grower", customer_type="Grower")
    item = mgr.add_item("Tomato", "TM", 2.0, 5, customer_id=g)
    # new purchase at different price creates separate row
    mgr.update_item_stock(item, g, 3.0, 10)
    panel = InventoryPanel(mgr)
    names = [panel.table.item(r, 0).text() for r in range(panel.table.rowCount())]
    tomato_rows = [i for i, n in enumerate(names) if n == "Tomato"]
    assert len(tomato_rows) == 2

