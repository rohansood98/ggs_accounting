import csv
import datetime as _dt
import locale
import os
import subprocess
from typing import Iterable, Mapping, Sequence, Optional

__all__ = [
    "export_to_csv",
    "export_to_excel",
    "print_pdf_via_windows",
    "open_pdf",
    "format_currency",
    "format_date",
]

try:
    import openpyxl  # type: ignore
    from openpyxl.workbook import Workbook
except Exception:  # pragma: no cover - openpyxl optional
    openpyxl = None
    Workbook = None


def export_to_csv(filename: str, data: Iterable[Mapping[str, object] | Sequence[object]], headers: Optional[Sequence[str]] = None) -> None:
    """Export rows of data to a CSV file."""
    try:
        with open(filename, "w", newline="", encoding="utf-8") as fh:
            if headers:
                writer = csv.DictWriter(fh, fieldnames=headers) if isinstance(next(iter(data), {}), Mapping) else csv.writer(fh)
                if isinstance(writer, csv.DictWriter):
                    writer.writeheader()
                    writer.writerows(data)  # type: ignore[arg-type]
                else:
                    writer.writerow(headers)
                    writer.writerows(data)  # type: ignore[arg-type]
            else:
                if isinstance(next(iter(data), {}), Mapping):
                    headers = list(next(iter(data)).keys()) if data else []
                    writer = csv.DictWriter(fh, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(data)  # type: ignore[arg-type]
                else:
                    writer = csv.writer(fh)
                    writer.writerows(data)
    except OSError as exc:
        raise RuntimeError(f"Failed to export CSV: {exc}") from exc


def export_to_excel(filename: str, data: Iterable[Mapping[str, object] | Sequence[object]], headers: Optional[Sequence[str]] = None) -> None:
    """Export rows of data to an Excel (.xlsx) file using openpyxl."""
    if openpyxl is None:
        raise RuntimeError("openpyxl not installed")
    try:
        wb = Workbook()
        ws = wb.active
        if headers:
            ws.append(list(headers))
        for row in data:
            if isinstance(row, Mapping):
                ws.append([row.get(h) for h in headers or row.keys()])
            else:
                ws.append(list(row))
        wb.save(filename)
    except Exception as exc:  # pragma: no cover - openpyxl errors
        raise RuntimeError(f"Failed to export Excel: {exc}") from exc


def print_pdf_via_windows(pdf_path: str) -> None:
    """Print a PDF file via Windows ShellExecute."""
    try:
        subprocess.run(["powershell", "-Command", f'Start-Process -FilePath \"{pdf_path}\" -Verb Print"'], check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Failed to print PDF: {exc}") from exc


def open_pdf(pdf_path: str) -> None:
    """Open a PDF file using the default viewer."""
    try:
        if os.name == "nt":
            os.startfile(pdf_path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", pdf_path], check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Failed to open PDF: {exc}") from exc


def format_currency(amount: float) -> str:
    """Return the number formatted as currency with two decimals."""
    locale.setlocale(locale.LC_ALL, "")  # use system locale
    try:
        return locale.currency(amount, grouping=True)
    except Exception:
        return f"{amount:,.2f}"


def format_date(date_obj: _dt.date) -> str:
    """Format a date object as DD-MM-YYYY."""
    return date_obj.strftime("%d-%m-%Y")
