from __future__ import annotations

from PyQt6 import QtWidgets

from ggs_accounting.db.db_manager import DatabaseManager


class SettingsPanel(QtWidgets.QWidget):
    """Panel for editing simple application settings."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        self.company_edit = QtWidgets.QLineEdit()
        self.address_edit = QtWidgets.QLineEdit()
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        layout.addRow("Company Name", self.company_edit)
        layout.addRow("Address", self.address_edit)
        layout.addRow(save_btn)

    def _load_settings(self) -> None:
        self.company_edit.setText(self._db.get_setting("company_name") or "")
        self.address_edit.setText(self._db.get_setting("company_address") or "")

    def _save_settings(self) -> None:
        try:
            self._db.set_setting("company_name", self.company_edit.text().strip())
            self._db.set_setting(
                "company_address", self.address_edit.text().strip()
            )
        except Exception as exc:  # pragma: no cover - unexpected errors
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        QtWidgets.QMessageBox.information(self, "Saved", "Settings updated")
