from __future__ import annotations

from typing import List

from PyQt6 import QtWidgets

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.models import reporting


class ReportsPanel(QtWidgets.QWidget):
    """SQL console with saved queries and templates."""

    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self._db = db
        self._init_ui()
        self._load_saved()

    def _init_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        top = QtWidgets.QHBoxLayout()
        self.template_combo = QtWidgets.QComboBox()
        self.template_combo.addItem("Select Template", "")
        for name in reporting.BUILT_IN_QUERIES:
            self.template_combo.addItem(name)
        self.template_combo.currentTextChanged.connect(self._apply_template)

        self.saved_combo = QtWidgets.QComboBox()
        self.saved_combo.currentIndexChanged.connect(self._load_saved_query)

        self.name_edit = QtWidgets.QLineEdit()
        run_btn = QtWidgets.QPushButton("Run")
        save_btn = QtWidgets.QPushButton("Save")
        run_btn.clicked.connect(self._run_query)
        save_btn.clicked.connect(self._save_query)

        top.addWidget(self.template_combo)
        top.addWidget(self.saved_combo)
        top.addWidget(self.name_edit)
        top.addWidget(save_btn)
        top.addWidget(run_btn)
        layout.addLayout(top)

        self.sql_edit = QtWidgets.QPlainTextEdit()
        self.sql_edit.setPlaceholderText("SELECT ...")
        layout.addWidget(self.sql_edit)

        self.table = QtWidgets.QTableWidget(0, 0)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def _apply_template(self, name: str) -> None:
        sql = reporting.BUILT_IN_QUERIES.get(name)
        if sql:
            self.sql_edit.setPlainText(sql)

    def _load_saved(self) -> None:
        self.saved_combo.clear()
        self.saved_combo.addItem("Saved Queries", None)
        try:
            queries = self._db.get_saved_queries()
        except Exception as exc:  # pragma: no cover - unexpected errors
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        for q in queries:
            self.saved_combo.addItem(q["name"], q["sql"])

    def _load_saved_query(self) -> None:
        sql = self.saved_combo.currentData()
        if sql:
            self.sql_edit.setPlainText(str(sql))

    def _run_query(self) -> None:
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            return
        try:
            cols, rows = reporting.run_query(self._db, sql)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([str(c) for c in cols])
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(str(val)))
        self.table.resizeColumnsToContents()

    def _save_query(self) -> None:
        name = self.name_edit.text().strip()
        sql = self.sql_edit.toPlainText().strip()
        if not name or not sql:
            return
        try:
            self._db.save_query(name, sql)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            return
        self._load_saved()
