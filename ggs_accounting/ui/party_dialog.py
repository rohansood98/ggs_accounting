from __future__ import annotations

from PyQt6 import QtWidgets

from ggs_accounting.db.db_manager import DatabaseManager


class PartyDialog(QtWidgets.QDialog):
    """Dialog for adding a new party."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self.setWindowTitle("Add Party")

        self.name_edit = QtWidgets.QLineEdit()
        self.contact_edit = QtWidgets.QLineEdit()

        form = QtWidgets.QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Contact", self.contact_edit)

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
        try:
            self._db.add_party(name, self.contact_edit.text().strip())
        except Exception as exc:  # pragma: no cover - unexpected errors
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        super().accept()
