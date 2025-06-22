import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.ui.invoice_panel import InvoicePanel


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def ensure_app():
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def test_item_source_disabled_on_purchase(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    panel = InvoicePanel(mgr)
    panel._add_line()
    panel.type_combo.setCurrentText("Purchase")
    QtWidgets.QApplication.processEvents()
    widget = panel.table.cellWidget(0, 1)
    assert isinstance(widget, QtWidgets.QComboBox)
    assert not widget.isEnabled()
