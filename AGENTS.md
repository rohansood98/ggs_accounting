# Agent Instructions

- Ensure all Python code includes basic error handling. Catch and handle database or IO errors where appropriate.
- Every new feature must include unit tests placed under the `tests/` directory. Run them with `python -m pytest -q`.
- After modifying the code, always execute:
  1. `pip install -e .`
  2. `python -m pytest -q`
- Keep this file updated with any new guidelines.
- Database schema uses global Items table with Inventory linking customers to items.
- Payments table now includes a `received` column to mark incoming or outgoing payments.
- Legacy `Sales` and `Purchases` tables were removed from the schema.
- Common helper functions live in `ggs_accounting/utils`.
  - `helpers.py` provides `export_to_csv`, `export_to_excel`,
    `print_pdf_via_windows`, `open_pdf`, `format_currency`, and
    `format_date`.
- Use Unix (LF) line endings for all text files like requirements.txt.

