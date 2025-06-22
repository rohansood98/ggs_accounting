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
    mgr.add_item("Apple", "Fruit", 10.0, 5)
    mgr.add_item("Carrot", "Vegetable", 5.0, 10)
    panel = InventoryPanel(mgr)
    assert panel.table.rowCount() == 2


def test_inventory_filter(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    mgr.add_item("Apple", "Fruit", 10.0, 5)
    mgr.add_item("Carrot", "Vegetable", 5.0, 10)
    panel = InventoryPanel(mgr)
    panel.search_edit.setText("apple")
    QtWidgets.QApplication.processEvents()
    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 0).text() == "Apple"

