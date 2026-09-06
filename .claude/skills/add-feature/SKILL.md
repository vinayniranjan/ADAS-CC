---
name: add-feature
description: Applies when the user wants to add a new feature end-to-end: plan, implement, test, and review in sequence.
---

# Skill: Add a New Feature (End-to-End)

Use this skill whenever a new feature needs to be planned, implemented, tested, and reviewed.

## Procedure

### 1. Plan (planner agent)
- Glob `src/` and `tests/` to understand the current structure.
- Read relevant existing modules.
- Produce a plan: files to create/modify, implementation steps, test plan.
- Get user confirmation before proceeding.

### 2. Implement (implementer agent)
- Follow the approved plan exactly.
- Place all new modules under `src/`.
- Add type hints and Google-style docstrings to every public symbol.
- Run `ruff check src/ && mypy src/` and fix all issues.

### 3. Test (tester agent)
- Create test files in `tests/` mirroring the `src/` structure.
- Cover happy paths, edge cases, and error conditions.
- Run `pytest tests/ -v --cov=src --cov-report=term-missing`.
- Confirm all tests pass and coverage is acceptable.

### 4. Review (reviewer agent)
- Read all changed files.
- Check the review checklist (correctness, security, style, tests).
- Issue APPROVE or REQUEST CHANGES.

## Checklist
- [ ] Plan approved by user
- [ ] All new code in `src/`
- [ ] Type hints and docstrings present
- [ ] `ruff`/`mypy` clean
- [ ] Tests written and passing
- [ ] Reviewer approved

## Example
User: "Add a CSV export function to the data module."
1. Planner reads `src/data/` and proposes adding `src/data/export.py`.
2. Implementer writes `export.py` with `export_csv(df, path: Path) -> None`.
3. Tester writes `tests/test_data/test_export.py` with parametrized cases.
4. Reviewer confirms no security issues (e.g. path traversal) and approves.
