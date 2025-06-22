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
        self._items = []
        self._customers = []
        self._init_ui()
        self._load_filters()
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

        filters = QtWidgets.QHBoxLayout()
        self.item_combo = QtWidgets.QComboBox()
        self.customer_combo = QtWidgets.QComboBox()
        self.item_combo.currentIndexChanged.connect(self._load_data)
        self.customer_combo.currentIndexChanged.connect(self._load_data)
        filters.addWidget(self.item_combo)
        filters.addWidget(self.customer_combo)
        layout.addLayout(filters)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Item", "Stock", "Price (₹)", "Value (₹)"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)

        self.total_label = QtWidgets.QLabel()
        layout.addWidget(self.total_label)

    def _load_filters(self) -> None:
        try:
            self._items = self._db.get_all_items()
            self._customers = self._db.get_customers_by_type("Grower")
        except Exception as exc:  # pragma: no cover - unexpected errors
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._items = []
            self._customers = []
        self.item_combo.clear()
        self.item_combo.addItem("All Items", None)
        added = set()
        for it in self._items:
            if it["item_id"] in added:
                continue
            added.add(it["item_id"])
            self.item_combo.addItem(it["name"], it["item_id"])
        self.customer_combo.clear()
        self.customer_combo.addItem("All Customers", None)
        for c in self._customers:
            self.customer_combo.addItem(c["name"], c["customer_id"])

    def _load_data(self) -> None:
        item_id = self.item_combo.currentData()
        customer_id = self.customer_combo.currentData()
        try:
            data, total = get_inventory_values(self._db, item_id=item_id, customer_id=customer_id)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(item["name"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(item["stock"])))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"₹{item['price']:.2f}"))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"₹{item['value']:.2f}"))
        self.table.resizeColumnsToContents()
        total_stock = sum(d.get("stock", 0) for d in data)
        total_price = sum(d.get("price", 0) for d in data)
        self.total_label.setText(
            f"Totals - Stock: {total_stock:.2f} Price: ₹{total_price:.2f} Value: ₹{total:.2f}"
        )
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
