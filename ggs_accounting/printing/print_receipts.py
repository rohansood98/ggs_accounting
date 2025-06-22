from __future__ import annotations

import os
import tempfile
import webbrowser
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from ggs_accounting.db.db_manager import DatabaseManager


class ReceiptPrinter:
    """Generate simple PDF invoices or summaries."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    # ---- query helpers ----
    def fetch_invoices(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        party_id: Optional[int] = None,
        inv_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        invoices = self._db.get_invoices(start_date, end_date)
        result: List[Dict[str, Any]] = []
        for inv in invoices:
            if party_id and inv["party_id"] != party_id:
                continue
            if inv_type and inv["type"] != inv_type:
                continue
            result.append(inv)
        return result

    # ---- pdf helpers ----
    def _summary_table(self, invoices: Iterable[Dict[str, Any]]) -> Table:
        data = [["Date", "Invoice", "Party", "Total"]]
        parties = {p["party_id"]: p["name"] for p in self._db.get_all_parties()}
        for inv in invoices:
            data.append([
                inv["date"],
                str(inv["inv_id"]),
                parties.get(inv["party_id"], ""),
                f"{inv['total_amount']:.2f}",
            ])
        table = Table(data, colWidths=[80, 60, 200, 80])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        return table

    def print_summary(self, invoices: Iterable[Dict[str, Any]]) -> str:
        """Generate a summary PDF and open it."""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("Invoice Summary", styles["Title"]), self._summary_table(invoices)]
        doc.build(story)
        webbrowser.open(tmp.name)
        return tmp.name

    def print_detailed(self, invoices: Iterable[Dict[str, Any]]) -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=A4)
        styles = getSampleStyleSheet()
        parties = {p["party_id"]: p for p in self._db.get_all_parties()}
        story = []
        for inv in invoices:
            party = parties.get(inv["party_id"], {})
            story.append(Paragraph(f"Invoice {inv['inv_id']}", styles["Heading2"]))
            story.append(Paragraph(f"Date: {inv['date']}", styles["Normal"]))
            if party:
                story.append(Paragraph(f"Party: {party.get('name')}", styles["Normal"]))
            items = self._db.get_invoice_items(inv["inv_id"])
            data = [["Item", "Qty", "Price", "Total"]]
            for it in items:
                data.append(
                    [
                        str(it["item_id"]),
                        str(it["quantity"]),
                        f"{it['unit_price']:.2f}",
                        f"{it['line_total']:.2f}",
                    ]
                )
            tbl = Table(data, colWidths=[100, 60, 80, 80])
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )
            story.append(tbl)
            story.append(Paragraph(" ", styles["Normal"]))
        doc.build(story)
        webbrowser.open(tmp.name)
        return tmp.name
