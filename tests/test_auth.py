from pathlib import Path
import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.ui.login_dialog import LoginDialog
from ggs_accounting.models.auth import UserRole


def create_manager(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(tmp_path / "test.sqlite")
    manager.init_db()
    return manager


def ensure_app():
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def test_get_user(tmp_path):
    mgr = create_manager(tmp_path)
    mgr.create_user("bob", "secret", UserRole.ACCOUNTANT.value)
    user = mgr.get_user("bob")
    assert user is not None
    assert user.username == "bob"
    assert user.role == UserRole.ACCOUNTANT
    assert user.verify_password("secret")


def test_login_dialog_success(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    dlg = LoginDialog(mgr)
    dlg.username_edit.setText("admin")
    dlg.password_edit.setText("admin")
    dlg.handle_login()
    assert dlg.user_role == UserRole.ADMIN


def test_login_dialog_invalid(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    dlg = LoginDialog(mgr)
    dlg.username_edit.setText("nosuch")
    dlg.password_edit.setText("bad")
    dlg.handle_login()
    assert dlg.user_role is None
    assert dlg.message_label.text() == "Invalid credentials"


