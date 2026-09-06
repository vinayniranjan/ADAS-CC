---
name: run-tests
description: Use this skill whenever the user asks to run the test suite for this python project, or after implementing a change that needs verification.
---

# Run Tests

1. Detect the test command from the project manifest (package.json scripts, pyproject.toml, Makefile, etc).
2. Run the full suite first; if it's slow, scope to changed files.
3. On failure, report only the failing test names and error output.
4. On success, report a one-line summary (N passed, M skipped).
