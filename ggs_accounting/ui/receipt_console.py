from __future__ import annotations

from datetime import date
from typing import Optional

from PyQt6 import QtWidgets

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.printing.print_receipts import ReceiptPrinter


class ReceiptConsole(QtWidgets.QWidget):
    """Simple UI to filter and print invoices."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._printer = ReceiptPrinter(db)
        self._init_ui()
        self._load_parties()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form = QtWidgets.QFormLayout()
        self.from_date = QtWidgets.QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.to_date = QtWidgets.QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.from_date.setDate(date.today())
        self.to_date.setDate(date.today())
        self.party_combo = QtWidgets.QComboBox()
        self.party_combo.addItem("All", None)
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(["All", "Sale", "Purchase"])
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItems(["Detailed", "Summary"])

        form.addRow("From", self.from_date)
        form.addRow("To", self.to_date)
        form.addRow("Party", self.party_combo)
        form.addRow("Type", self.type_combo)
        form.addRow("Format", self.format_combo)
        layout.addLayout(form)

        btns = QtWidgets.QHBoxLayout()
        show_btn = QtWidgets.QPushButton("Show")
        print_btn = QtWidgets.QPushButton("Print")
        show_btn.clicked.connect(self._show)
        print_btn.clicked.connect(self._print)
        btns.addWidget(show_btn)
        btns.addWidget(print_btn)
        layout.addLayout(btns)

        self.summary_table = QtWidgets.QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(["Date", "Invoice", "Party", "Total"])
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.summary_table)

    def _load_parties(self) -> None:
        self.party_combo.clear()
        self.party_combo.addItem("All", None)
        try:
            parties = self._db.get_all_parties()
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        for p in parties:
            self.party_combo.addItem(p["name"], p["party_id"])

    def _fetch(self) -> list:
        start = self.from_date.date().toString("yyyy-MM-dd")
        end = self.to_date.date().toString("yyyy-MM-dd")
        party = self.party_combo.currentData()
        inv_type = self.type_combo.currentText()
        if inv_type == "All":
            inv_type = None
        return self._printer.fetch_invoices(start, end, party, inv_type)

    def _show(self) -> None:
        invoices = self._fetch()
        self.summary_table.setRowCount(len(invoices))
        parties = {p["party_id"]: p["name"] for p in self._db.get_all_parties()}
        for row, inv in enumerate(invoices):
            self.summary_table.setItem(row, 0, QtWidgets.QTableWidgetItem(inv["date"]))
            self.summary_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(inv["inv_id"])))
            self.summary_table.setItem(row, 2, QtWidgets.QTableWidgetItem(parties.get(inv["party_id"], "")))
            self.summary_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{inv['total_amount']:.2f}"))
        self.summary_table.resizeColumnsToContents()

    def _print(self) -> None:
        invoices = self._fetch()
        if not invoices:
            QtWidgets.QMessageBox.information(self, "No Data", "No invoices found")
            return
        fmt = self.format_combo.currentText()
        if fmt == "Summary":
            self._printer.print_summary(invoices)
        else:
            self._printer.print_detailed(invoices)
