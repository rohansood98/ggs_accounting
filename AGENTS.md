# Agent Instructions

- Ensure all Python code includes basic error handling. Catch and handle database or IO errors where appropriate.
- Every new feature must include unit tests placed under the `tests/` directory. Run them with `python -m pytest -q`.
- After modifying the code, always execute:
  1. `pip install -e .`
  2. `python -m pytest -q`
- Keep this file updated with any new guidelines.
- Database schema uses global Items table with Inventory linking customers to items.

