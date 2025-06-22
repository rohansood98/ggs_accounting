from __future__ import annotations

from datetime import date as _date
from typing import Dict, List, Optional, Any

from ggs_accounting.db.db_manager import DatabaseManager


class InvoiceLogic:
    """Backend logic helper for billing operations."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    def create_invoice(
        self,
        inv_type: str,
        party_id: Optional[int],
        items: List[Dict[str, Any]],
        *,
        date: Optional[str] = None,
        is_credit: bool = False,
    ) -> int:
        if not items:
            raise ValueError("Invoice requires at least one item")
        date_str = date or _date.today().isoformat()
        inv_id = self._db.create_invoice(
            date_str,
            inv_type,
            party_id,
            items,
            is_credit=is_credit,
        )
        for item in items:
            change = item["quantity"] if inv_type == "Purchase" else -item["quantity"]
            self._db.update_item_stock(item["item_id"], change)
        return inv_id

