import os
import pytest

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ggs_accounting.db.db_manager import DatabaseManager
from ggs_accounting.printing.print_receipts import ReceiptPrinter


def create_manager(tmp_path):
    mgr = DatabaseManager(tmp_path / "test.sqlite")
    mgr.init_db()
    return mgr


def ensure_app():
    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])


def test_summary_pdf(tmp_path):
    ensure_app()
    mgr = create_manager(tmp_path)
    customer_id = mgr.add_customer("Grower", customer_type="Grower")
    mgr.add_item("Apple", 10.0, 5, customer_id=customer_id)
    buyer_id = mgr.add_customer("Cust")
    mgr.create_invoice(
        "2024-01-01",
        "Sale",
        buyer_id,
        [{"name": "Apple", "customer_id": customer_id, "quantity": 2, "price": 10.0}],
    )
    printer = ReceiptPrinter(mgr)
    invoices = printer.fetch_invoices("2024-01-01", "2024-01-02", None, None)
    pdf = printer.print_summary(invoices)
    assert os.path.exists(pdf)
