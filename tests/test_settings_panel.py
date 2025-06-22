import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.ui.settings_panel import SettingsPanel


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def ensure_app():
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def test_save_settings(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    panel = SettingsPanel(mgr)
    panel.company_edit.setText("MyCo")
    panel.address_edit.setText("123 Road")
    panel._save_settings()
    assert mgr.get_setting("company_name") == "MyCo"
    assert mgr.get_setting("company_address") == "123 Road"
