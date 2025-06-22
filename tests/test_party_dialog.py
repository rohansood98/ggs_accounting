import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.ui.party_dialog import PartyDialog


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def ensure_app():
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def test_party_dialog_adds_party(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    dlg = PartyDialog(mgr)
    dlg.name_edit.setText("Vendor")
    dlg.contact_edit.setText("info")
    dlg.accept()
    parties = mgr.get_all_parties()
    assert any(p["name"] == "Vendor" for p in parties)
