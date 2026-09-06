"""Designer node.

Turns a `ScanReport` (+ optional human revision feedback) into a
`DesignSpec` describing the interconnected agent system: subagents,
skills, commands, and hooks.

If `ANTHROPIC_API_KEY` is set, this calls Claude (via langchain-anthropic)
with structured output constrained to `schema.DesignModel`. Otherwise it
falls back to a solid rule-based default (planner/implementer/reviewer/
tester) so the whole pipeline still runs end-to-end without an API key,
e.g. in CI or for a quick offline demo.
"""
from __future__ import annotations

import os

from adas_cc.schema import CommandModel, DesignModel, HookModel, SkillModel, SubagentModel
from adas_cc.state import AdasState, DesignSpec, ScanReport

SYSTEM_PROMPT = """You are ADAS-CC, a meta-agent that designs multi-agent Claude Code \
configurations for software repositories.

Given a structured scan report of a repository, design an INTERCONNECTED system of \
Claude Code subagents, slash commands, skills, and hooks tailored to this specific \
repo's stack and conventions. Favor a small number of focused agents over many \
overlapping ones. Typical roles worth considering: planner (read-only research and \
planning), implementer (writes code following conventions), reviewer (read-only \
quality/security review), tester (writes and runs tests). Adapt roles to what the \
scan actually shows - e.g. add a migration-runner for repos with a database layer, \
or a docs-writer for documentation-heavy repos. Every agent's description must be \
specific enough that Claude can pick the right one; every agent's system prompt \
must reference the real commands/frameworks found in the scan, not generic advice.

Design commands that route one-shot tasks to the right agent, and skills that \
capture any multi-step workflow the scan reveals (e.g. a test command, a release \
process). Include at least one hook if the scan shows an obvious deterministic \
enforcement opportunity (e.g. auto-format after edits when a formatter is \
detected in the manifest)."""


def _format_scan_report(report: ScanReport) -> str:
    lines = [
        f"root: {report.get('root')}",
        f"primary_language: {report.get('primary_language')}",
        f"frameworks: {', '.join(report.get('frameworks', [])) or 'none detected'}",
        f"package_managers: {', '.join(report.get('package_managers', [])) or 'none detected'}",
        f"test_frameworks: {', '.join(report.get('test_frameworks', [])) or 'none detected'}",
        f"has_ci: {report.get('has_ci')} ({', '.join(report.get('ci_systems', []))})",
        f"entry_points: {report.get('entry_points')}",
        f"top_level_dirs_by_file_count: {report.get('directory_summary')}",
        f"notable_docs: {report.get('notable_docs')}",
        f"file_count: {report.get('file_count')}",
        f"recent_commits: {report.get('recent_commits', [])[:8]}",
        f"is_update_mode: {report.get('is_update_mode')}",
        f"existing_claude_config: {report.get('existing_claude_config')}",
    ]
    return "\n".join(lines)


def _call_llm(report: ScanReport, model_name: str, feedback: str | None) -> DesignModel:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatAnthropic(model=model_name, temperature=0.2, max_tokens=8000)
    structured_llm = llm.with_structured_output(DesignModel)

    user_content = "Scan report:\n\n" + _format_scan_report(report)
    if report.get("is_update_mode"):
        user_content += (
            "\n\nThis repo already has a .claude/ configuration (listed above as "
            "existing_claude_config). Propose only new or improved subagents/"
            "commands/skills that fill real gaps - don't duplicate what already "
            "exists unless it's clearly outdated for this stack."
        )
    if feedback:
        user_content += (
            f"\n\nA human reviewed a previous draft of this design and requested "
            f"changes:\n\"\"\"\n{feedback}\n\"\"\"\nIncorporate this feedback."
        )

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_content)]
    result = structured_llm.invoke(messages)
    assert isinstance(result, DesignModel)
    return result


def _heuristic_design(report: ScanReport) -> DesignModel:
    """A dependable default design used when no LLM is configured."""
    lang = report.get("primary_language") or "the project's language"
    frameworks = ", ".join(report.get("frameworks", [])) or "no specific framework detected"
    test_fw = ", ".join(report.get("test_frameworks", [])) or "no test framework detected"

    claude_md = f"""# Project Overview

This is a **{lang}** project. Frameworks: {frameworks}. Test tooling: {test_fw}.

## Key facts (from automated scan)
- Package managers: {', '.join(report.get('package_managers', [])) or 'n/a'}
- CI: {'yes (' + ', '.join(report.get('ci_systems', [])) + ')' if report.get('has_ci') else 'not detected'}
- Entry points: {', '.join(report.get('entry_points', [])) or 'n/a'}

## Conventions
Follow the existing code style in the repository. Prefer small, reviewable diffs.
Run the project's test suite before considering a task complete.

## Agent system
This repo's `.claude/` directory was generated by ADAS-CC. Four subagents cover
the standard flow: `planner` -> `implementer` -> `reviewer` -> `tester`.
"""

    subagents = [
        SubagentModel(
            name="planner",
            description=(
                "Research and plan before coding. Use proactively for any task "
                "that touches more than one file or is ambiguous."
            ),
            tools=["Read", "Grep", "Glob", "Bash"],
            model="inherit",
            system_prompt=(
                f"You are a senior {lang} engineer acting as a read-only planner.\n\n"
                "When invoked:\n"
                "1. Read the relevant files and understand existing conventions.\n"
                "2. Produce a numbered implementation plan with concrete file paths.\n"
                "3. Call out risks, edge cases, and open questions.\n"
                "4. Hand off to the implementer agent with the plan.\n\n"
                "You never edit files. Output only the plan."
            ),
            handoff_to=["implementer"],
            color="blue",
        ),
        SubagentModel(
            name="implementer",
            description=(
                f"Write {lang} code following this project's conventions. Use after "
                "a plan exists, or for small well-scoped changes."
            ),
            tools=["Read", "Write", "Edit", "Grep", "Glob", "Bash"],
            model="inherit",
            system_prompt=(
                f"You are a {lang} implementer. Follow the plan you're given (or the "
                "user's request directly for small changes). Match existing code "
                "style. Keep diffs minimal and focused. When done, summarize what "
                "changed and hand off to the reviewer agent."
            ),
            handoff_to=["reviewer"],
            color="green",
        ),
        SubagentModel(
            name="reviewer",
            description=(
                "Read-only code review for quality, security, and correctness. "
                "Use immediately after implementer finishes a change."
            ),
            tools=["Read", "Grep", "Glob", "Bash"],
            model="inherit",
            system_prompt=(
                "You are a senior reviewer. Run `git diff` to see recent changes and "
                "focus your review there.\n\n"
                "Checklist:\n- Correctness and edge cases\n- Security (no exposed "
                "secrets, input validation)\n- Readability and naming\n- Test "
                "coverage of the change\n\n"
                "Organize feedback as Critical / Warnings / Suggestions. Hand off to "
                "the tester agent once the diff looks structurally sound."
            ),
            handoff_to=["tester"],
            color="yellow",
        ),
        SubagentModel(
            name="tester",
            description=(
                f"Write and run tests using {test_fw if test_fw != 'no test framework detected' else 'the project test tooling'}. "
                "Use after implementer or reviewer to validate a change."
            ),
            tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            model="inherit",
            system_prompt=(
                "You are a test engineer. Write tests that cover the new behavior "
                "and edge cases, run the test suite, and report failing tests with "
                "their error messages only (don't dump full passing output)."
            ),
            handoff_to=[],
            color="purple",
        ),
    ]

    commands = [
        CommandModel(
            name="plan",
            description="Plan an implementation for a task before writing any code",
            argument_hint="[task description]",
            allowed_tools=["Read", "Grep", "Glob"],
            routes_to_agent="planner",
            body="Use the planner subagent to produce an implementation plan for: $ARGUMENTS",
        ),
        CommandModel(
            name="review",
            description="Run a read-only review of the current diff",
            argument_hint="",
            allowed_tools=["Read", "Grep", "Glob", "Bash(git diff *)"],
            routes_to_agent="reviewer",
            body="Use the reviewer subagent to review the current uncommitted changes (`git diff`).",
        ),
    ]

    skills = [
        SkillModel(
            name="run-tests",
            description=(
                f"Use this skill whenever the user asks to run the test suite for this "
                f"{lang} project, or after implementing a change that needs verification."
            ),
            body=(
                "# Run Tests\n\n"
                f"1. Detect the test command from the project manifest (package.json "
                f"scripts, pyproject.toml, Makefile, etc).\n"
                "2. Run the full suite first; if it's slow, scope to changed files.\n"
                "3. On failure, report only the failing test names and error output.\n"
                "4. On success, report a one-line summary (N passed, M skipped)."
            ),
        )
    ]

    hooks: list[HookModel] = []
    if "npm" in report.get("package_managers", []) or "python" in (report.get("primary_language") or ""):
        hooks.append(
            HookModel(
                event="PostToolUse",
                matcher="Edit|Write",
                command=".claude/hooks/format-changed-file.sh",
                description="Auto-format a file after it is edited or written.",
            )
        )

    return DesignModel(
        project_summary=(
            f"A {lang} project ({frameworks}) using {test_fw} for testing."
        ),
        claude_md_body=claude_md,
        subagents=subagents,
        commands=commands,
        skills=skills,
        hooks=hooks,
    )


def _to_design_spec(model: DesignModel) -> DesignSpec:
    return DesignSpec(
        project_summary=model.project_summary,
        claude_md_body=model.claude_md_body,
        subagents=[a.model_dump() for a in model.subagents],
        commands=[c.model_dump() for c in model.commands],
        skills=[s.model_dump() for s in model.skills],
        hooks=[h.model_dump() for h in model.hooks],
    )


def designer_node(state: AdasState) -> dict:
    report = state["scan_report"]
    model_name = state.get("model_name") or "claude-sonnet-4-6"
    feedback = state.get("feedback")

    if os.environ.get("ANTHROPIC_API_KEY"):
        design_model = _call_llm(report, model_name, feedback)
    else:
        design_model = _heuristic_design(report)

    return {
        "design_spec": _to_design_spec(design_model),
        "feedback": None,  # consumed
    }
