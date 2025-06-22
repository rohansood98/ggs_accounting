from PyQt6 import QtWidgets

class PartyDialog(QtWidgets.QDialog):
    """Dialog for adding a new party."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Party")
        self.name_edit = QtWidgets.QLineEdit()
        self.contact_edit = QtWidgets.QLineEdit()
        form = QtWidgets.QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Contact Info", self.contact_edit)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def get_data(self):
        return self.name_edit.text().strip(), self.contact_edit.text().strip()
