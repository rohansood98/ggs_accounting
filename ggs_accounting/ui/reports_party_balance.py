from __future__ import annotations

from PyQt6 import QtWidgets
import pandas as pd

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models.reporting import get_party_balances


class PartyBalancePanel(QtWidgets.QWidget):
    """Display party-wise outstanding balances."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        btns = QtWidgets.QHBoxLayout()
        refresh_btn = QtWidgets.QPushButton("Refresh")
        export_btn = QtWidgets.QPushButton("Export")
        refresh_btn.clicked.connect(self._load_data)
        export_btn.clicked.connect(self._export)
        btns.addWidget(refresh_btn)
        btns.addWidget(export_btn)
        layout.addLayout(btns)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Party", "Balance", "Status"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def _load_data(self) -> None:
        try:
            data = get_party_balances(self._db)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(item["name"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{item['balance']:.2f}"))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(item["status"]))
        self.table.resizeColumnsToContents()
        self._data = data

    def _export(self) -> None:
        if not getattr(self, "_data", None):
            return
        df = pd.DataFrame(self._data)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export", filter="Excel Files (*.xlsx)")
        if path:
            try:
                df.to_excel(path, index=False)
            except Exception as exc:  # pragma: no cover
                QtWidgets.QMessageBox.critical(self, "Error", str(exc))
