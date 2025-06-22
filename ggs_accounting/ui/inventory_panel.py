from __future__ import annotations

from PyQt6 import QtWidgets
from typing import Optional, Dict, Any, List

from ggs_accounting.db.db_manager import DatabaseManager


class ItemDialog(QtWidgets.QDialog):
    """Dialog for adding or editing an inventory item."""

    def __init__(self, db: DatabaseManager, item: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self._db = db
        self._item = item
        self.setWindowTitle("Edit Item" if item else "Add Item")

        self.name_edit = QtWidgets.QLineEdit()
        self.price_edit = QtWidgets.QDoubleSpinBox()
        self.price_edit.setMaximum(1e9)
        self.price_edit.setPrefix("₹")
        self.stock_edit = QtWidgets.QDoubleSpinBox()
        self.stock_edit.setMaximum(1e9)
        self.customer_combo = QtWidgets.QComboBox()

        form = QtWidgets.QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Price", self.price_edit)
        form.addRow("Stock", self.stock_edit)
        form.addRow("Customer", self.customer_combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._populate_customer_combo()

        # If no growers exist, warn and disable dialog
        if not self._customers:
            QtWidgets.QMessageBox.warning(self, "No Growers", "No growers found. Please add a grower before adding items.")
            self.setEnabled(False)

        if item:
            self.name_edit.setText(item.get("name", ""))
            self.price_edit.setValue(float(item.get("price_excl_tax", 0)))
            self.stock_edit.setValue(float(item.get("stock_qty", 0)))
            idx = self.customer_combo.findData(item.get("customer_id"))
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)

    def _populate_customer_combo(self) -> None:
        """Populate the customer (party) combo box."""
        self._customers = self._db.get_customers_by_type("Grower")
        self.customer_combo.addItem("", None)
        for p in self._customers:
            self.customer_combo.addItem(p["name"], p["customer_id"])

    def get_data(self) -> Optional[Dict[str, Any]]:
        name = self.name_edit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Validation", "Name is required")
            return None
        price = self.price_edit.value()
        if price < 0:
            QtWidgets.QMessageBox.warning(self, "Validation", "Price must be positive")
            return None
        data = {
            "name": name,
            "price_excl_tax": price,
            "stock_qty": self.stock_edit.value(),
            "customer_id": self.customer_combo.currentData(),
        }
        if data["customer_id"] is None:
            QtWidgets.QMessageBox.warning(self, "Validation", "Customer is required")
            return None
        return data

    def accept(self) -> None:  # type: ignore[override]
        data = self.get_data()
        if data is None:
            return
        try:
            if self._item:
                self._db.update_item(self._item["name"], self._item["customer_id"], **data)
            else:
                self._db.add_item(**data)
        except Exception as exc:  # pragma: no cover - unexpected errors
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        super().accept()


class InventoryPanel(QtWidgets.QWidget):
    """Widget for managing inventory items."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._items: List[Dict[str, Any]] = []
        self._init_ui()
        self._load_items()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        controls = QtWidgets.QHBoxLayout()
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Search...")
        self.search_edit.textChanged.connect(self._apply_filter)
        add_btn = QtWidgets.QPushButton("Add")
        edit_btn = QtWidgets.QPushButton("Edit")
        del_btn = QtWidgets.QPushButton("Delete")
        refresh_btn = QtWidgets.QPushButton("Refresh")
        add_btn.clicked.connect(self._add_item)
        edit_btn.clicked.connect(self._edit_item)
        del_btn.clicked.connect(self._delete_item)
        refresh_btn.clicked.connect(self._load_items)
        controls.addWidget(self.search_edit)
        for btn in [add_btn, edit_btn, del_btn, refresh_btn]:
            controls.addWidget(btn)
        layout.addLayout(controls)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Customer", "Price", "Stock"])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        gst = self._db.get_setting("GST")
        if gst:
            note = QtWidgets.QLabel("Prices exclude GST; tax added on invoices.")
            layout.addWidget(note)

    # ---- UI helpers ----
    def _load_items(self) -> None:
        try:
            self._items = self._db.get_all_items()
        except Exception as exc:  # pragma: no cover - unexpected errors
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._items = []
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.search_edit.text().strip().lower()
        filtered = [item for item in self._items if query in item["name"].lower()]
        self._populate_table(filtered)

    def _populate_table(self, items: List[Dict[str, Any]]) -> None:
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(item.get("name", ""))))
            customer_name = ""
            if item.get("customer_id"):
                customer = next((g for g in self._customers if g["customer_id"] == item["customer_id"]), None)
                if customer:
                    customer_name = customer["name"]
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(customer_name))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"₹{item.get('price_excl_tax', 0):.2f}"))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem(str(item.get("stock_qty", 0))))
            self.table.setRowHeight(row, 20)
        self.table.resizeColumnsToContents()

    def _get_selected_item(self) -> Optional[Dict[str, Any]]:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._items):
            return None
        # map table row to item via filter
        query = self.search_edit.text().strip().lower()
        filtered = [item for item in self._items if query in item["name"].lower()]
        if row >= len(filtered):
            return None
        return filtered[row]

    # ---- Button handlers ----
    def _add_item(self) -> None:
        dlg = ItemDialog(self._db)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._load_items()

    def _edit_item(self) -> None:
        item = self._get_selected_item()
        if not item:
            return
        dlg = ItemDialog(self._db, item)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._load_items()

    def _delete_item(self) -> None:
        item = self._get_selected_item()
        if not item:
            return
        ans = QtWidgets.QMessageBox.question(
            self,
            "Confirm",
            f"Delete {item['name']}?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
        )
        if ans == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                self._db.delete_item(item["name"], item["customer_id"])
            except Exception as exc:  # pragma: no cover - unexpected errors
                QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._load_items()

