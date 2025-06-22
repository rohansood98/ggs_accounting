from PyQt6 import QtWidgets
from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models.auth import UserRole

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self._db = db
        self.setWindowTitle("Login")
        self.username_edit = QtWidgets.QLineEdit()
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.login_button = QtWidgets.QPushButton("Login")
        self.cancel_button = QtWidgets.QPushButton("Exit")
        self.message_label = QtWidgets.QLabel()
        layout = QtWidgets.QFormLayout()
        layout.addRow("Username", self.username_edit)
        layout.addRow("Password", self.password_edit)
        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.login_button)
        btns.addWidget(self.cancel_button)
        layout.addRow(btns)
        layout.addRow(self.message_label)
        self.setLayout(layout)
        self.login_button.clicked.connect(self.handle_login)
        self.cancel_button.clicked.connect(self.reject)
        self.user_role: UserRole | None = None

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        try:
            role = self._db.verify_user(username, password)
        except Exception as exc:  # pragma: no cover - unexpected errors
            self.message_label.setText(str(exc))
            return
        if role:
            self.user_role = UserRole(role)
            self.accept()
        else:
            self.message_label.setText("Invalid credentials")
