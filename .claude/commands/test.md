---
description: Write pytest tests and run the full test suite for a module or feature
argument-hint: [module or feature to test]
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

Use the tester agent to write pytest tests and run the suite for the following:

$ARGUMENTS

Run: pytest tests/ -v --cov=src --cov-report=term-missing
