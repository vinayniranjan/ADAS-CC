---
name: setup-ci
description: Applies when the user wants to add CI configuration (GitHub Actions or similar) to the project, which currently has none.
---

# Skill: Set Up CI for a Python Project

This project has no CI configuration. Use this skill to add one.

## Procedure

### 1. Assess (planner agent)
- Read `pyproject.toml` / `setup.cfg` / `requirements.txt` to determine the package manager (uv, poetry, or pip).
- Check Python version constraints.
- Confirm test command: `pytest tests/ -v --cov=src`.

### 2. Create CI Workflow (implementer agent)
Create `.github/workflows/ci.yml` with these jobs:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install uv
          uv sync  # or: poetry install / pip install -e .[dev]
      - name: Lint
        run: ruff check src/ tests/
      - name: Type check
        run: mypy src/
      - name: Test
        run: pytest tests/ -v --cov=src --cov-report=term-missing
```

### 3. Verify Locally (tester agent)
- Run `pytest tests/ -v` locally to confirm the suite passes before pushing.

### 4. Review (reviewer agent)
- Confirm the workflow file is correct and secure (no secret leakage, pinned action versions).

## Checklist
- [ ] Package manager install step matches project (uv/poetry/pip)
- [ ] Python version matrix matches `pyproject.toml` constraints
- [ ] Lint, type-check, and test steps all present
- [ ] Action versions pinned (e.g. `@v4`)
- [ ] Local tests pass before committing workflow
