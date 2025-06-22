from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from ggs_accounting.models.auth import UserRole
from ggs_accounting.ui.inventory_panel import InventoryPanel
from ggs_accounting.ui.invoice_panel import InvoicePanel
from ggs_accounting.db.db_manager import DatabaseManager

class MainWindow(QtWidgets.QMainWindow):
    """Main application shell."""

    logout_requested = pyqtSignal()
    exit_requested = pyqtSignal()  # Add a new signal for exit


    def __init__(self, user_role: str, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._role = UserRole(user_role)
        self.setWindowTitle("Wholesale Billing System")
        self.resize(800, 600)

        self._stack = QtWidgets.QTabWidget()
        self.setCentralWidget(self._stack)
        self.statusBar().showMessage("Ready")

        self._settings_index: int | None = None
        self._db = db  # Store db for use in panels
        self._init_tabs()
        self._init_menu()
        self._stack.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, idx: int) -> None:
        widget = self._stack.widget(idx)
        from ggs_accounting.ui.reports_inventory import InventoryValuationPanel
        if isinstance(widget, InventoryValuationPanel):
            widget._load_data()

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
        from .inventory_panel import InventoryPanel
        from .invoice_panel import InvoicePanel
        from .receipt_console import ReceiptConsole
        from .reports_panel import ReportsPanel
        from .reports_party_balance import CustomerBalancePanel
        from .payment_panel import PaymentPanel
        from .reports_inventory import InventoryValuationPanel
        from .settings_panel import SettingsPanel

        self._stack.addTab(InventoryPanel(self._db), "Inventory")
        self._stack.addTab(InvoicePanel(self._db), "Billing")
        self._stack.addTab(PaymentPanel(self._db), "Payments")
        self._stack.addTab(ReceiptConsole(self._db), "Receipts")
        self._stack.addTab(ReportsPanel(self._db), "SQL")
        self._stack.addTab(CustomerBalancePanel(self._db), "Customer Balances")
        self._stack.addTab(InventoryValuationPanel(self._db), "Inventory Value")
        self._stack.addTab(self._create_placeholder("Backup"), "Backup")

        if self._role is UserRole.ADMIN:
            settings_widget = SettingsPanel(self._db)
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
