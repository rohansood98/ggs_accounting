import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_QPA_FONTDIR"] = os.path.abspath("ggs_accounting/fonts/ttf")
from PyQt6 import QtWidgets
from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.ui.login_dialog import LoginDialog
from ggs_accounting.ui.main_window import MainWindow


def ensure_directories():
    from pathlib import Path
    base_dirs = [
        'ggs_accounting/ui',
        'ggs_accounting/db',
        'ggs_accounting/models',
        'ggs_accounting/reports',
        'ggs_accounting/printing',
        'ggs_accounting/backup',
        'data'
    ]
    for d in base_dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def main():
    ensure_directories()
    try:
        db = DatabaseManager()
        db.init_db()
    except Exception as exc:
        print(f"Database error: {exc}")
        return

    app = QtWidgets.QApplication([])
    login = LoginDialog(db)
    if login.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        if login.user_role is None:
            print("Login failed: user role is None.")
            return
        window = MainWindow(login.user_role)
        window.show()
        app.exec()


if __name__ == "__main__":
    main()
