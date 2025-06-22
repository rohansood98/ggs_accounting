from __future__ import annotations

from PyQt6 import QtWidgets
import pandas as pd

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models.reporting import get_inventory_values


class InventoryValuationPanel(QtWidgets.QWidget):
    """Report showing inventory valuation."""

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

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Item", "Stock", "Price", "Value"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.total_label = QtWidgets.QLabel()
        layout.addWidget(self.total_label)

    def _load_data(self) -> None:
        try:
            data, total = get_inventory_values(self._db)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(item["name"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(item["stock"])))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{item['price']:.2f}"))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{item['value']:.2f}"))
        self.table.resizeColumnsToContents()
        self.total_label.setText(f"Total Stock Value: {total:.2f}")
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
