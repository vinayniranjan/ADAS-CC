---
description: Run the complete plan → implement → test → review workflow for a feature
argument-hint: [feature or issue description]
---

Orchestrate the full development cycle for the following feature or fix:

$ARGUMENTS

Step 1: Delegate to the `planner` agent to research and produce an implementation plan.
Step 2: Once the plan is approved, delegate to the `implementer` agent to write the code.
Step 3: Delegate to the `tester` agent to write tests and verify they pass.
Step 4: Delegate to the `reviewer` agent for a final quality and security review.
Step 5: Report a summary of all changes made and test results.
