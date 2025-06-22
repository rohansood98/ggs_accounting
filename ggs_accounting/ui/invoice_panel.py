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
        self._customers: List[Dict[str, Any]] = []
        self._buyers: List[Dict[str, Any]] = []
        self._growers: List[Dict[str, Any]] = []
        self._init_ui()
        self._load_customers()
        self._load_items()

    # ---- UI setup ----
    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        # Add Customer button at the top
        add_party_btn = QtWidgets.QPushButton("Add Customer")
        add_party_btn.clicked.connect(self._add_customer)
        layout.addWidget(add_party_btn)

        form = QtWidgets.QFormLayout()
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(["Sale", "Purchase"])
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.buyer_combo = QtWidgets.QComboBox()
        self.buyer_combo.setEditable(True)
        form.addRow("Type", self.type_combo)
        form.addRow("Date", self.date_edit)
        form.addRow("Buyer", self.buyer_combo)
        layout.addLayout(form)

        add_line_btn = QtWidgets.QPushButton("Add Line")
        add_line_btn.clicked.connect(self._add_line)
        layout.addWidget(add_line_btn)

        # Table: Item, Customer, Qty, Price, Total, Delete
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Item", "Customer", "Qty", "Price (₹)", "Total (₹)", "Delete"])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.table)

        buttons = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(self._save_invoice)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        totals_layout = QtWidgets.QFormLayout()
        self.amount_paid = QtWidgets.QDoubleSpinBox()
        self.amount_paid.setMaximum(1e9)
        self.amount_paid.setPrefix("₹")
        self.subtotal_label = QtWidgets.QLabel("Subtotal: 0.00")
        self.due_label = QtWidgets.QLabel("Due: 0.00")
        totals_layout.addRow("Paid", self.amount_paid)
        totals_layout.addRow(self.subtotal_label, self.due_label)
        layout.addLayout(totals_layout)

    # ---- Data loading ----
    def _load_customers(self) -> None:
        try:
            all_cust = self._db.get_all_customers()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            all_cust = []
        self._customers = all_cust
        self._growers = [c for c in all_cust if c.get("customer_type") == "Grower"]
        self._buyers = [c for c in all_cust if c.get("customer_type") != "Grower"]
        self.buyer_combo.clear()
        self.buyer_combo.addItems([b["name"] for b in self._buyers])

    def _load_items(self) -> None:
        try:
            self._items = self._db.get_all_items()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._items = []

    def _add_customer(self) -> None:
        from ggs_accounting.ui.party_dialog import CustomerDialog

        dlg = CustomerDialog(self._db)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._load_customers()

    # ---- Table helpers ----
    def _add_line(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Item dropdown (independent of customer)
        item_combo = QtWidgets.QComboBox()
        item_combo.setEditable(True)
        item_combo.addItems([it["name"] for it in self._items])
        item_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        # Customer dropdown (per row, but not tied to item)
        customer_combo = QtWidgets.QComboBox()
        customer_combo.setEditable(True)
        customer_combo.addItems([c["name"] for c in self._growers])
        customer_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
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
        item_combo.currentTextChanged.connect(self._recalc_totals)
        customer_combo.currentTextChanged.connect(self._recalc_totals)
        self.table.setCellWidget(row, 0, item_combo)
        self.table.setCellWidget(row, 1, customer_combo)
        self.table.setCellWidget(row, 2, qty_spin)
        self.table.setCellWidget(row, 3, price_spin)
        self.table.setItem(row, 4, total_item)
        self.table.setCellWidget(row, 5, del_btn)
        self._recalc_totals()

    def _delete_row(self, row: int) -> None:
        self.table.removeRow(row)
        self._recalc_totals()

    def _gather_items(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for row in range(self.table.rowCount()):
            item_widget = self.table.cellWidget(row, 0)
            customer_widget = self.table.cellWidget(row, 1)
            qty_widget = self.table.cellWidget(row, 2)
            price_widget = self.table.cellWidget(row, 3)
            if not isinstance(item_widget, QtWidgets.QComboBox) or not isinstance(customer_widget, QtWidgets.QComboBox):
                continue
            item_name = item_widget.currentText().strip()
            customer_name = customer_widget.currentText().strip()
            if not item_name:
                QtWidgets.QMessageBox.warning(self, "Validation", f"Item name required in row {row+1}")
                return []
            if not customer_name:
                QtWidgets.QMessageBox.warning(self, "Validation", f"Customer required in row {row+1}")
                return []
            # Find or add customer
            customer = next((c for c in self._growers if c["name"] == customer_name), None)
            if customer is None:
                ans = QtWidgets.QMessageBox.question(self, "Add Customer?", f"Customer '{customer_name}' not found. Add new?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
                if ans == QtWidgets.QMessageBox.StandardButton.Yes:
                    from ggs_accounting.ui.party_dialog import CustomerDialog
                    dlg = CustomerDialog(self._db)
                    dlg.name_edit.setText(customer_name)
                    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                        self._load_customers()
                        customer = next((c for c in self._growers if c["name"] == customer_name), None)
                if customer is None:
                    QtWidgets.QMessageBox.warning(self, "Validation", f"Customer '{customer_name}' not found.")
                    return []
            # Find or add item (independent of customer)
            item = next((it for it in self._items if it["name"] == item_name), None)
            if item is None:
                ans = QtWidgets.QMessageBox.question(self, "Add Item?", f"Item '{item_name}' not found. Add new?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
                if ans == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        self._db.add_item(
                            item_name,
                            "AUTO",
                            price_excl_tax=cast(QtWidgets.QDoubleSpinBox, price_widget).value(),
                            stock_qty=0.0,
                            customer_id=customer["customer_id"],
                        )
                        self._load_items()
                        item = next((it for it in self._items if it["name"] == item_name), None)
                    except Exception as exc:
                        QtWidgets.QMessageBox.critical(self, "Error", f"Failed to add new item '{item_name}': {exc}")
                        return []
                if item is None:
                    QtWidgets.QMessageBox.warning(self, "Validation", f"Item '{item_name}' not found.")
                    return []
            quantity = float(cast(QtWidgets.QDoubleSpinBox, qty_widget).value())
            price = float(cast(QtWidgets.QDoubleSpinBox, price_widget).value())
            items.append({"item_id": item["item_id"], "name": item_name, "customer_id": customer["customer_id"], "quantity": quantity, "price": price})
        return items

    def _recalc_totals(self) -> None:
        subtotal = 0.0
        for row in range(self.table.rowCount()):
            qty_widget = self.table.cellWidget(row, 2)
            price_widget = self.table.cellWidget(row, 3)
            qty = cast(QtWidgets.QDoubleSpinBox, qty_widget).value()
            price = cast(QtWidgets.QDoubleSpinBox, price_widget).value()
            total = qty * price
            subtotal += total
            item = QtWidgets.QTableWidgetItem(f"₹{total:.2f}")
            self.table.setItem(row, 4, item)
        paid = self.amount_paid.value() if hasattr(self, "amount_paid") else 0.0
        due = subtotal - paid
        self.subtotal_label.setText(f"Subtotal: ₹{subtotal:.2f}")
        self.due_label.setText(f"Due: ₹{due:.2f}")

    # ---- Save ----
    def _save_invoice(self) -> None:
        items = self._gather_items()
        if not items:
            QtWidgets.QMessageBox.warning(self, "Validation", "Add at least one item")
            return
        inv_type = self.type_combo.currentText()
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        buyer_name = self.buyer_combo.currentText().strip()
        buyer = next((b for b in self._buyers if b["name"] == buyer_name), None)
        if buyer is None:
            QtWidgets.QMessageBox.warning(self, "Validation", "Select buyer")
            return
        customer_id = buyer["customer_id"]
        try:
            self._logic.create_invoice(
                inv_type,
                customer_id,
                items,
                date=date_str,
                is_credit=True,
                amount_paid=self.amount_paid.value(),
            )
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self.table.setRowCount(0)
        self._recalc_totals()
        self.amount_paid.setValue(0.0)
        QtWidgets.QMessageBox.information(self, "Saved", "Invoice saved")

