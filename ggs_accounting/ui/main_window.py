from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from ggs_accounting.models.auth import UserRole

class MainWindow(QtWidgets.QMainWindow):
    """Main application shell."""

    logout_requested = pyqtSignal()
    exit_requested = pyqtSignal()  # Add a new signal for exit

    def __init__(self, user_role: str) -> None:
        super().__init__()
        self._role = UserRole(user_role)
        self.setWindowTitle("Wholesale Billing System")
        self.resize(800, 600)

        self._stack = QtWidgets.QTabWidget()
        self.setCentralWidget(self._stack)
        self.statusBar().showMessage("Ready")

        self._settings_index: int | None = None
        self._init_tabs()
        self._init_menu()

    def _init_menu(self) -> None:
        menubar = self.menuBar()
        # Explicitly create a QMenu and add it to the menubar
        file_menu = QtWidgets.QMenu("File", self)
        menubar.addMenu(file_menu)
        logout_action = file_menu.addAction("Logout")
        logout_action.triggered.connect(self._handle_logout)
        # Insert Settings above Exit if admin
        if self._role is UserRole.ADMIN:
            settings_action = file_menu.addAction("Settings")
            settings_action.triggered.connect(self._open_settings_tab)
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self._handle_exit)

    def _init_tabs(self) -> None:
        for name in ["Inventory", "Billing", "Reports", "Backup"]:
            self._stack.addTab(self._create_placeholder(name), name)
        if self._role is UserRole.ADMIN:
            settings_widget = self._create_placeholder("Settings")
            self._settings_index = self._stack.addTab(settings_widget, "Settings")

    def _create_placeholder(self, title: str) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        label = QtWidgets.QLabel(f"{title} module")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(label)
        return widget

    def _open_settings_tab(self) -> None:
        if self._settings_index is not None:
            self._stack.setCurrentIndex(self._settings_index)

    def _handle_logout(self) -> None:
        self.close()
        self.logout_requested.emit()

    def _handle_exit(self) -> None:
        self.close()
        self.exit_requested.emit()
