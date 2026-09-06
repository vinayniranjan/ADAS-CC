---
name: run-tests
description: Use this skill whenever the user asks to run the test suite for this FastAPI project, or after implementing a change that needs verification.
---

# Run Tests

1. Run `pytest -q` from the repo root.
2. If the suite is slow, scope to the changed module: `pytest -q tests/test_<module>.py`.
3. On failure, report only the failing test names and their error output —
   don't paste the full passing output.
4. On success, report a one-line summary (N passed, M skipped).
5. If a dependency is missing, check `pyproject.toml`'s `[project.optional-dependencies]`
   for a `test` extra before asking the user to install anything manually.
