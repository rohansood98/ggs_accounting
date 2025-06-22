from __future__ import annotations

from datetime import date
from typing import List, Dict, Any

from PyQt6 import QtWidgets

from ggs_accounting.db.db_manager import DatabaseManager


class PaymentPanel(QtWidgets.QWidget):
    """Record and display payments."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._payments: List[Dict[str, Any]] = []
        self._customers: List[Dict[str, Any]] = []
        self._init_ui()
        self._load_customers()
        self._load_payments()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        self.customer_combo = QtWidgets.QComboBox()
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(["Received", "Paid"])
        self.amount_spin = QtWidgets.QDoubleSpinBox()
        self.amount_spin.setMaximum(1e9)
        self.amount_spin.setPrefix("₹")
        form.addRow("Date", self.date_edit)
        form.addRow("Customer", self.customer_combo)
        form.addRow("Amount", self.amount_spin)
        form.addRow("Type", self.type_combo)
        layout.addLayout(form)
        add_btn = QtWidgets.QPushButton("Record Payment")
        add_btn.clicked.connect(self._record)
        layout.addWidget(add_btn)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Customer", "Amount", "Type"])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def _load_customers(self) -> None:
        try:
            self._customers = self._db.get_all_customers()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._customers = []
        self.customer_combo.clear()
        for c in self._customers:
            self.customer_combo.addItem(c["name"], c["customer_id"])

    def _load_payments(self) -> None:
        try:
            self._payments = self._db.get_payments()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._payments = []
        self.table.setRowCount(len(self._payments) + 1)
        parties = {c["customer_id"]: c["name"] for c in self._customers}
        total = 0.0
        for row, p in enumerate(self._payments):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(p["date"]))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(parties.get(p["customer_id"], "")))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"₹{p['amount']:.2f}"))
            self.table.setItem(row, 3, QtWidgets.QTableWidgetItem("Received" if p.get("received", 1) else "Paid"))
            total += float(p["amount"])
        # total row
        total_row = self.table.rowCount() - 1
        self.table.setSpan(total_row, 0, 1, 2)
        self.table.setItem(total_row, 0, QtWidgets.QTableWidgetItem("Total"))
        self.table.setItem(total_row, 2, QtWidgets.QTableWidgetItem(f"₹{total:.2f}"))
        self.table.resizeColumnsToContents()

    def _record(self) -> None:
        customer_id = self.customer_combo.currentData()
        amount = self.amount_spin.value()
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        if customer_id is None or amount <= 0:
            QtWidgets.QMessageBox.warning(self, "Validation", "Customer and amount required")
            return
        received = self.type_combo.currentText() == "Received"
        try:
            self._db.record_payment(customer_id, amount, date_str, received=received)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self.amount_spin.setValue(0.0)
        self._load_payments()

    def showEvent(self, a0):
        """Refresh data when the panel becomes visible."""
        self._load_customers()
        self._load_payments()
        super().showEvent(a0)
