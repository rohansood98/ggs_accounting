from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, user_role: str):
        super().__init__()
        self.setWindowTitle("GGS Accounting")
        self.resize(800, 600)
        label = QtWidgets.QLabel(f"Logged in as {user_role}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)
