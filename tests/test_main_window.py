import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.ui.main_window import MainWindow
from ggs_accounting.models.auth import UserRole


def ensure_app():
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def test_admin_sees_settings_tab(tmp_path):
    ensure_app()
    win = MainWindow(UserRole.ADMIN.value)
    tabs = [win._stack.tabText(i) for i in range(win._stack.count())]
    assert "Settings" in tabs


def test_accountant_hides_settings(tmp_path):
    ensure_app()
    win = MainWindow(UserRole.ACCOUNTANT.value)
    tabs = [win._stack.tabText(i) for i in range(win._stack.count())]
    assert "Settings" not in tabs


def test_logout_signal_emitted(tmp_path):
    ensure_app()
    win = MainWindow(UserRole.ADMIN.value)
    triggered = []
    win.logout_requested.connect(lambda: triggered.append(True))
    win._handle_logout()
    assert triggered

