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
        customer_id: Optional[int],
        items: List[Dict[str, Any]],
        *,
        date: Optional[str] = None,
        is_credit: bool = False,
        amount_paid: float = 0.0,
    ) -> int:
        if not items:
            raise ValueError("Invoice requires at least one item")
        date_str = date or _date.today().isoformat()
        inv_id = self._db.create_invoice(
            date_str,
            inv_type,
            customer_id,
            items,
            is_credit=is_credit,
            amount_paid=amount_paid,
        )
        for item in items:
            item_id = item.get("item_id")
            if item_id is None:
                # Fallback to lookup by name
                row = self._db.conn.execute("SELECT item_id FROM Items WHERE name=?", (item["name"],)).fetchone()
                if row:
                    item_id = int(row["item_id"])
            if item_id is None:
                continue
            price_excl_tax = item.get("price_excl_tax")
            if price_excl_tax is None:
                # Fallback: fetch from Inventory
                lookup_id = item.get("source_id") if inv_type == "Sale" else item.get("customer_id")
                row = self._db.conn.execute(
                    "SELECT price_excl_tax FROM Inventory WHERE item_id=? AND customer_id=? ORDER BY inventory_id DESC LIMIT 1",
                    (item_id, lookup_id),
                ).fetchone()
                if row:
                    price_excl_tax = row["price_excl_tax"]
                else:
                    raise KeyError("price_excl_tax")
            if inv_type == "Purchase":
                party_id = item.get("customer_id")
                change = item["quantity"]
            else:
                party_id = item.get("source_id")
                change = -item["quantity"]
            if party_id is None:
                raise RuntimeError("Missing inventory party reference")
            self._db.update_item_stock(item_id, party_id, price_excl_tax, change)
        return inv_id

