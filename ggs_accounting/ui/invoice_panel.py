from __future__ import annotations

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from datetime import date
from typing import List, Dict, Any, cast

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models.invoice_logic import InvoiceLogic


class InvoicePanel(QtWidgets.QWidget):
    """Simple panel for creating sales or purchase invoices."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._logic = InvoiceLogic(db)
        self._items: List[Dict[str, Any]] = []
        self._init_ui()
        self._load_parties()
        self._load_items()

    # ---- UI setup ----
    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(["Sale", "Purchase"])

        party_row = QtWidgets.QHBoxLayout()
        self.party_combo = QtWidgets.QComboBox()
        add_party_btn = QtWidgets.QPushButton("Add Party")
        add_party_btn.clicked.connect(self._add_party)
        party_row.addWidget(self.party_combo)
        party_row.addWidget(add_party_btn)

        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())

        form.addRow("Type", self.type_combo)
        form.addRow("Party", party_row)
        form.addRow("Date", self.date_edit)
        layout.addLayout(form)

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Item", "Qty", "Price (₹)", "Total (₹)", "Delete"])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)

        buttons = QtWidgets.QHBoxLayout()
        add_line_btn = QtWidgets.QPushButton("Add Line")
        save_btn = QtWidgets.QPushButton("Save")
        add_line_btn.clicked.connect(self._add_line)
        save_btn.clicked.connect(self._save_invoice)
        buttons.addWidget(add_line_btn)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        totals_layout = QtWidgets.QHBoxLayout()
        self.subtotal_label = QtWidgets.QLabel("Subtotal: 0.00")
        totals_layout.addStretch()
        totals_layout.addWidget(self.subtotal_label)
        layout.addLayout(totals_layout)

    # ---- Data loading ----
    def _load_parties(self) -> None:
        try:
            parties = self._db.get_all_parties()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            parties = []
        self.party_combo.clear()
        self.party_combo.addItem("", None)
        for p in parties:
            self.party_combo.addItem(p["name"], p["party_id"])

    def _load_items(self) -> None:
        try:
            self._items = self._db.get_all_items()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._items = []

    def _add_party(self) -> None:
        from ggs_accounting.ui.party_dialog import PartyDialog

        dlg = PartyDialog(self._db)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._load_parties()
            # select last added party
            parties = self._db.get_all_parties()
            if parties:
                self.party_combo.setCurrentIndex(len(parties))

    # ---- Table helpers ----
    def _add_line(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        item_edit = QtWidgets.QLineEdit()
        completer = QtWidgets.QCompleter([it["name"] for it in self._items])
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        item_edit.setCompleter(completer)
        qty_spin = QtWidgets.QDoubleSpinBox()
        qty_spin.setMaximum(1e6)
        qty_spin.setValue(1)
        price_spin = QtWidgets.QDoubleSpinBox()
        price_spin.setMaximum(1e9)
        price_spin.setPrefix("₹")
        if self._items:
            price_spin.setValue(float(self._items[0].get("price_excl_tax", 0)))
        total_item = QtWidgets.QTableWidgetItem("₹0.00")
        del_btn = QtWidgets.QPushButton("Delete")
        del_btn.clicked.connect(lambda _, r=row: self._delete_row(r))
        qty_spin.valueChanged.connect(self._recalc_totals)
        price_spin.valueChanged.connect(self._recalc_totals)
        item_edit.textChanged.connect(self._recalc_totals)
        self.table.setCellWidget(row, 0, item_edit)
        self.table.setCellWidget(row, 1, qty_spin)
        self.table.setCellWidget(row, 2, price_spin)
        self.table.setItem(row, 3, total_item)
        self.table.setCellWidget(row, 4, del_btn)
        self._recalc_totals()

    def _delete_row(self, row: int) -> None:
        self.table.removeRow(row)
        self._recalc_totals()

    def _gather_items(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            item_widget = self.table.cellWidget(row, 0)
            qty_widget = self.table.cellWidget(row, 1)
            price_widget = self.table.cellWidget(row, 2)
            if not isinstance(item_widget, QtWidgets.QLineEdit):
                continue
            item_name = cast(QtWidgets.QLineEdit, item_widget).text().strip()
            if not item_name:
                QtWidgets.QMessageBox.warning(self, "Validation", f"Item name required in row {row+1}")
                return []
            # Try to find item_id
            item = next((it for it in self._items if it["name"] == item_name), None)
            if item is None:
                # Add new item to DB with default values
                try:
                    item_id = self._db.add_item(item_name, category="", price_excl_tax=cast(QtWidgets.QDoubleSpinBox, price_widget).value(), stock_qty=0.0, grower_id=None)
                    # Reload items for future lookups
                    self._load_items()
                except Exception as exc:
                    QtWidgets.QMessageBox.critical(self, "Error", f"Failed to add new item '{item_name}': {exc}")
                    return []
            else:
                item_id = item["item_id"]
            quantity = float(cast(QtWidgets.QDoubleSpinBox, qty_widget).value())
            price = float(cast(QtWidgets.QDoubleSpinBox, price_widget).value())
            items.append({"item_id": item_id, "quantity": quantity, "price": price})
        return items

    def _recalc_totals(self) -> None:
        subtotal = 0.0
        for row in range(self.table.rowCount()):
            qty_widget = self.table.cellWidget(row, 1)
            price_widget = self.table.cellWidget(row, 2)
            qty = cast(QtWidgets.QDoubleSpinBox, qty_widget).value()
            price = cast(QtWidgets.QDoubleSpinBox, price_widget).value()
            total = qty * price
            subtotal += total
            item = QtWidgets.QTableWidgetItem(f"₹{total:.2f}")
            self.table.setItem(row, 3, item)
        self.subtotal_label.setText(f"Subtotal: ₹{subtotal:.2f}")

    # ---- Save ----
    def _save_invoice(self) -> None:
        items = self._gather_items()
        if not items:
            QtWidgets.QMessageBox.warning(self, "Validation", "Add at least one item")
            return
        party_id = self.party_combo.currentData()
        inv_type = self.type_combo.currentText()
        try:
            self._logic.create_invoice(inv_type, party_id, items, date=self.date_edit.date().toString("yyyy-MM-dd"))
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self.table.setRowCount(0)
        self._recalc_totals()
        QtWidgets.QMessageBox.information(self, "Saved", "Invoice saved")

