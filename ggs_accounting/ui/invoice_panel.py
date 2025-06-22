from __future__ import annotations

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from datetime import date
from typing import List, Dict, Any, cast, Tuple, Optional

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
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        form.addRow("Type", self.type_combo)
        form.addRow("Date", self.date_edit)
        layout.addLayout(form)

        add_line_btn = QtWidgets.QPushButton("Add Line")
        add_line_btn.clicked.connect(self._add_line)
        layout.addWidget(add_line_btn)

        # Table: Customer, Item, Item Source, Qty, Price, Total, Delete
        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Customer",
            "Item",
            "Item Source",
            "Qty",
            "Price (₹)",
            "Total (₹)",
            "Delete",
        ])
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
        for row in range(self.table.rowCount()):
            cust_combo = self.table.cellWidget(row, 0)
            src_combo = self.table.cellWidget(row, 2)
            if isinstance(cust_combo, QtWidgets.QComboBox):
                current = cust_combo.currentText()
                cust_combo.clear()
                cust_combo.addItem("")
                cust_combo.addItems([c["name"] for c in self._customers])
                idx = cust_combo.findText(current)
                cust_combo.setCurrentIndex(idx if idx >= 0 else 0)
            if isinstance(src_combo, QtWidgets.QComboBox):
                current = src_combo.currentText()
                src_combo.clear()
                src_combo.addItem("")
                src_combo.addItems([c["name"] for c in self._growers])
                idx = src_combo.findText(current)
                src_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _load_items(self) -> None:
        try:
            self._items = self._db.get_all_items()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._items = []
        for row in range(self.table.rowCount()):
            item_combo = self.table.cellWidget(row, 1)
            if isinstance(item_combo, QtWidgets.QComboBox):
                current = item_combo.currentText()
                item_combo.clear()
                item_combo.addItem("")
                item_combo.addItems([it["name"] for it in self._items])
                idx = item_combo.findText(current)
                item_combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _add_customer(self) -> None:
        from ggs_accounting.ui.party_dialog import CustomerDialog

        dlg = CustomerDialog(self._db)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._load_customers()

    def _on_type_changed(self, _text: str = "") -> None:
        is_purchase = self.type_combo.currentText() == "Purchase"
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 2)
            if isinstance(widget, QtWidgets.QComboBox):
                widget.setEnabled(not is_purchase)

    # ---- Table helpers ----
    def _add_line(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Customer dropdown per row
        customer_combo = QtWidgets.QComboBox()
        customer_combo.setEditable(True)
        customer_combo.addItem("")
        customer_combo.addItems([c["name"] for c in self._customers])
        customer_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        customer_combo.setCurrentIndex(0)
        customer_combo.lineEdit().textEdited.connect(customer_combo.showPopup)
        # Item dropdown (independent of customer)
        item_combo = QtWidgets.QComboBox()
        item_combo.setEditable(True)
        item_combo.addItem("")
        item_combo.addItems([it["name"] for it in self._items])
        item_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        item_combo.setCurrentIndex(0)
        item_combo.lineEdit().textEdited.connect(item_combo.showPopup)
        # Item source dropdown per row
        source_combo = QtWidgets.QComboBox()
        source_combo.setEditable(True)
        if self.type_combo.currentText() == "Sale":
            source_combo.addItem("")
            source_combo.addItems([c["name"] for c in self._growers])
            source_combo.setEnabled(True)
        else:
            # For purchase, do not preload any names and keep disabled
            source_combo.clear()
            source_combo.setEnabled(False)
        source_combo.lineEdit().textEdited.connect(source_combo.showPopup)
        qty_spin = QtWidgets.QDoubleSpinBox()
        qty_spin.setMaximum(1e6)
        qty_spin.setValue(1)
        price_spin = QtWidgets.QDoubleSpinBox()
        price_spin.setMaximum(1e9)
        price_spin.setPrefix("₹")
        price_spin.setValue(0.0)
        total_item = QtWidgets.QTableWidgetItem("₹0.00")
        del_btn = QtWidgets.QPushButton("Delete")
        del_btn.clicked.connect(lambda _, r=row: self._delete_row(r))
        qty_spin.valueChanged.connect(self._recalc_totals)
        price_spin.valueChanged.connect(self._recalc_totals)
        item_combo.currentTextChanged.connect(self._recalc_totals)
        source_combo.currentTextChanged.connect(self._recalc_totals)
        customer_combo.currentTextChanged.connect(self._recalc_totals)
        self.table.setCellWidget(row, 0, customer_combo)
        self.table.setCellWidget(row, 1, item_combo)
        self.table.setCellWidget(row, 2, source_combo)
        self.table.setCellWidget(row, 3, qty_spin)
        self.table.setCellWidget(row, 4, price_spin)
        self.table.setItem(row, 5, total_item)
        self.table.setCellWidget(row, 6, del_btn)
        self._recalc_totals()

    def _delete_row(self, row: int) -> None:
        self.table.removeRow(row)
        self._recalc_totals()

    def _gather_items(self) -> Tuple[Optional[int], List[Dict[str, Any]]]:
        items: List[Dict[str, Any]] = []
        inv_customer_id: Optional[int] = None
        is_purchase = self.type_combo.currentText() == "Purchase"
        for row in range(self.table.rowCount()):
            customer_widget = self.table.cellWidget(row, 0)
            item_widget = self.table.cellWidget(row, 1)
            source_widget = self.table.cellWidget(row, 2)
            qty_widget = self.table.cellWidget(row, 3)
            price_widget = self.table.cellWidget(row, 4)
            if not isinstance(customer_widget, QtWidgets.QComboBox) or not isinstance(item_widget, QtWidgets.QComboBox) or not isinstance(source_widget, QtWidgets.QComboBox):
                continue
            customer_name = customer_widget.currentText().strip()
            item_name = item_widget.currentText().strip()
            source_name = source_widget.currentText().strip()
            if not customer_name:
                QtWidgets.QMessageBox.warning(self, "Validation", f"Customer required in row {row+1}")
                return []
            if not item_name:
                QtWidgets.QMessageBox.warning(self, "Validation", f"Item name required in row {row+1}")
                return []
            # Only require item source for Sale
            if not is_purchase:
                if not source_name:
                    QtWidgets.QMessageBox.warning(self, "Validation", f"Item source required in row {row+1}")
                    return []
            # Find or add customer
            customer = next((c for c in self._customers if c["name"] == customer_name), None)
            if customer is None:
                ans = QtWidgets.QMessageBox.question(self, "Add Customer?", f"Customer '{customer_name}' not found. Add new?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
                if ans == QtWidgets.QMessageBox.StandardButton.Yes:
                    from ggs_accounting.ui.party_dialog import CustomerDialog
                    dlg = CustomerDialog(self._db)
                    dlg.name_edit.setText(customer_name)
                    if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                        self._load_customers()
                        customer = next((c for c in self._customers if c["name"] == customer_name), None)
                if customer is None:
                    QtWidgets.QMessageBox.warning(self, "Validation", f"Customer '{customer_name}' not found.")
                    return []
            # Find or add item source (only for Sale)
            source = None
            if not is_purchase:
                source = next((c for c in self._growers if c["name"] == source_name), None)
                if source is None:
                    ans = QtWidgets.QMessageBox.question(self, "Add Customer?", f"Item source '{source_name}' not found. Add new?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
                    if ans == QtWidgets.QMessageBox.StandardButton.Yes:
                        from ggs_accounting.ui.party_dialog import CustomerDialog
                        dlg = CustomerDialog(self._db)
                        dlg.name_edit.setText(source_name)
                        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                            self._load_customers()
                            source = next((c for c in self._growers if c["name"] == source_name), None)
                    if source is None:
                        QtWidgets.QMessageBox.warning(self, "Validation", f"Item source '{source_name}' not found.")
                        return []
            # Find or add item (independent of customer)
            item = next((it for it in self._items if it["name"] == item_name), None)
            if item is None:
                ans = QtWidgets.QMessageBox.question(self, "Add Item?", f"Item '{item_name}' not found. Add new?", QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
                if ans == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        # For purchase, use customer as the supplier; for sale, use source as the supplier
                        if is_purchase:
                            supplier_id = customer["customer_id"]
                        else:
                            if source is None:
                                QtWidgets.QMessageBox.warning(self, "Validation", f"Item source required to add item '{item_name}' in row {row+1}")
                                return []
                            supplier_id = source["customer_id"]
                        self._db.add_item(
                            item_name,
                            "AUTO",
                            price_excl_tax=cast(QtWidgets.QDoubleSpinBox, price_widget).value(),
                            stock_qty=0.0,
                            customer_id=supplier_id,
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
            # For purchase, set customer_id as supplier and source_id as None
            # For sale, set customer_id as buyer and source_id as supplier
            if inv_customer_id is None:
                inv_customer_id = customer["customer_id"]
            item_dict = {
                "item_id": item["item_id"],
                "name": item_name,
                "customer_id": customer["customer_id"] if is_purchase else customer["customer_id"],
                "source_id": None if is_purchase else (source["customer_id"] if source else None),
                "quantity": quantity,
                "price": price,
                "price_excl_tax": price,
            }
            items.append(item_dict)
        return inv_customer_id, items

    def _recalc_totals(self) -> None:
        subtotal = 0.0
        for row in range(self.table.rowCount()):
            qty_widget = self.table.cellWidget(row, 3)
            price_widget = self.table.cellWidget(row, 4)
            qty = cast(QtWidgets.QDoubleSpinBox, qty_widget).value()
            price = cast(QtWidgets.QDoubleSpinBox, price_widget).value()
            total = qty * price
            subtotal += total
            item = QtWidgets.QTableWidgetItem(f"₹{total:.2f}")
            self.table.setItem(row, 5, item)
        paid = self.amount_paid.value() if hasattr(self, "amount_paid") else 0.0
        due = subtotal - paid
        self.subtotal_label.setText(f"Subtotal: ₹{subtotal:.2f}")
        self.due_label.setText(f"Due: ₹{due:.2f}")

    # ---- Save ----
    def _save_invoice(self) -> None:
        customer_id, items = self._gather_items()
        if not items:
            QtWidgets.QMessageBox.warning(self, "Validation", "Add at least one item")
            return
        inv_type = self.type_combo.currentText()
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        # customer_id already determined in _gather_items
        try:
            self._logic.create_invoice(
                inv_type,
                customer_id,  # Pass correct customer_id
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

    def showEvent(self, a0):
        """Refresh data when the panel becomes visible."""
        self._load_customers()
        self._load_items()
        super().showEvent(a0)

