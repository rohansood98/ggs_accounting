import os
# os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_QPA_FONTDIR"] = os.path.abspath("ggs_accounting/fonts/ttf")
from PyQt6 import QtWidgets
from PyQt6.QtGui import QPalette, QColor
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
    QtWidgets.QApplication.setStyle("Fusion")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    while True:
        login = LoginDialog(db)
        if login.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            if login.user_role is None:
                print("Login failed: user role is None.")
                continue
            window = MainWindow(login.user_role, db)
            window.showMaximized()

            # Track if exit was requested
            exit_flag = {'exit': False}
            def set_exit():
                exit_flag['exit'] = True
            window.logout_requested.connect(window.close)
            window.exit_requested.connect(set_exit)
            window.exit_requested.connect(window.close)
            window.show()
            app.exec()
            if exit_flag['exit']:
                break
        else:
            break


if __name__ == "__main__":
    main()
