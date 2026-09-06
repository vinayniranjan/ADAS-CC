---
name: fix-bug
description: Applies when a bug or failing test has been reported and needs to be diagnosed, fixed, and verified.
---

# Skill: Fix a Bug

Use this skill when a bug report or failing test needs to be diagnosed and resolved.

## Procedure

### 1. Reproduce (tester agent)
- Run `pytest tests/ -v` to confirm the failure.
- Identify the exact failing test(s) and error message.
- If no test exists for the bug, write a minimal reproducing test first.

### 2. Diagnose (planner agent)
- Read the failing code path in `src/`.
- Use `Grep` to trace the call chain.
- Identify the root cause and propose a minimal fix.

### 3. Fix (implementer agent)
- Apply the minimal fix in `src/`.
- Do not change unrelated code.
- Run `ruff check src/ && mypy src/`.

### 4. Verify (tester agent)
- Run `pytest tests/ -v` — all tests must pass.
- Confirm the reproducing test now passes.

### 5. Review (reviewer agent)
- Confirm the fix is correct and introduces no regressions or security issues.

## Checklist
- [ ] Bug reproduced with a failing test
- [ ] Root cause identified
- [ ] Minimal fix applied
- [ ] All tests pass
- [ ] Reviewer approved

## Example
User: "`parse_config()` crashes with a KeyError on missing optional keys."
1. Tester runs pytest, confirms failure, writes `test_parse_config_missing_key`.
2. Planner reads `src/config.py`, finds missing `.get()` call.
3. Implementer changes `config['key']` → `config.get('key', default)`.
4. Tester reruns pytest — all pass.
5. Reviewer approves.
