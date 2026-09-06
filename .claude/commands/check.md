---
description: Run lint, type-check, and tests in one shot and report results
allowed-tools: Bash, Read
---

Run the following quality checks and report the results:

1. `ruff check src/ tests/` (fall back to `flake8 src/ tests/` if ruff is not installed)
2. `mypy src/` (fall back to `pyright src/` if mypy is not installed)
3. `pytest tests/ -v --cov=src --cov-report=term-missing`

Summarise: number of lint issues, type errors, tests passed/failed, and coverage percentage. If anything fails, list the specific errors.
