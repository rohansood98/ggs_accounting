from PyQt6 import QtWidgets
from ggs_accounting.db.db_manager import DatabaseManager

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self._db = db
        self.setWindowTitle("Login")
        self.username_edit = QtWidgets.QLineEdit()
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.login_button = QtWidgets.QPushButton("Login")
        self.message_label = QtWidgets.QLabel()
        layout = QtWidgets.QFormLayout()
        layout.addRow("Username", self.username_edit)
        layout.addRow("Password", self.password_edit)
        layout.addRow(self.login_button)
        layout.addRow(self.message_label)
        self.setLayout(layout)
        self.login_button.clicked.connect(self.handle_login)
        self.user_role = None

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        try:
            role = self._db.verify_user(username, password)
        except Exception as exc:  # pragma: no cover - unexpected errors
            self.message_label.setText(str(exc))
            return
        if role:
            self.user_role = role
            self.accept()
        else:
            self.message_label.setText("Invalid credentials")
