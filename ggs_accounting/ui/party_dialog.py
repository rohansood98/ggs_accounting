from __future__ import annotations
from PyQt6 import QtWidgets
from ggs_accounting.db.db_manager import DatabaseManager


class CustomerDialog(QtWidgets.QDialog):
    """Dialog for adding a new customer."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self.setWindowTitle("Add Customer")

        self.name_edit = QtWidgets.QLineEdit()
        self.contact_edit = QtWidgets.QLineEdit()
        self.customer_type_combo = QtWidgets.QComboBox()
        self.customer_type_combo.addItems(["Grower", "Buyer", "Other"])

        form = QtWidgets.QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Contact Info", self.contact_edit)
        form.addRow("Type", self.customer_type_combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:  # type: ignore[override]
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Validation", "Name required")
            return
        customer_type = self.customer_type_combo.currentText()
        try:
            self._db.add_customer(name, self.contact_edit.text().strip(), customer_type)
        except Exception as exc:  # pragma: no cover - unexpected errors
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        super().accept()

    def get_data(self):
        return self.name_edit.text().strip(), self.contact_edit.text().strip(), self.customer_type_combo.currentText()

