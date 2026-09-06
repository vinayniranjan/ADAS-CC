"""Shared state for the ADAS-CC LangGraph graph.

The graph is a linear pipeline with one feedback loop:

    scan -> design -> generate -> approve -> write -> END
                ^                    |
                |____ revise ________|   (human requested changes)

`AdasState` is a plain TypedDict so it works with LangGraph's
`StateGraph` reducer model out of the box (each node returns a partial
dict that gets merged into the running state).
"""
from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


class ScanReport(TypedDict, total=False):
    root: str
    languages: dict[str, int]  # extension -> file count
    primary_language: str
    frameworks: list[str]
    package_managers: list[str]
    test_frameworks: list[str]
    has_ci: bool
    ci_systems: list[str]
    entry_points: list[str]
    directory_summary: dict[str, int]  # top-level dir -> file count
    recent_commits: list[str]
    existing_claude_config: dict[str, list[str]]  # e.g. {"agents": [...]}
    is_update_mode: bool
    notable_docs: list[str]
    file_count: int
    warnings: list[str]


class SubagentSpec(TypedDict, total=False):
    name: str
    description: str
    tools: list[str]
    model: str  # sonnet | opus | haiku | inherit
    system_prompt: str
    handoff_to: list[str]  # names of agents this one hands off to
    color: Optional[str]


class CommandSpec(TypedDict, total=False):
    name: str
    description: str
    argument_hint: str
    allowed_tools: list[str]
    routes_to_agent: Optional[str]
    body: str


class SkillSpec(TypedDict, total=False):
    name: str
    description: str
    body: str
    scripts: list[str]  # relative filenames of helper scripts referenced


class HookSpec(TypedDict, total=False):
    event: str  # PreToolUse | PostToolUse | SubagentStop | ...
    matcher: str
    command: str
    description: str


class DesignSpec(TypedDict, total=False):
    project_summary: str
    claude_md_body: str
    subagents: list[SubagentSpec]
    commands: list[CommandSpec]
    skills: list[SkillSpec]
    hooks: list[HookSpec]


class ProposedFile(TypedDict):
    path: str  # relative to target repo root
    content: str
    kind: Literal["claude_md", "agent", "command", "skill", "hook_settings", "other"]
    is_new: bool
    diff: Optional[str]


class AdasState(TypedDict, total=False):
    # --- inputs ---
    repo_path: str
    model_name: str
    auto_approve: bool
    feedback: Optional[str]

    # --- pipeline data ---
    scan_report: ScanReport
    design_spec: DesignSpec
    proposed_files: list[ProposedFile]

    # --- human-in-the-loop ---
    approval_decision: Optional[Literal["approve", "revise", "reject"]]
    revision_notes: Optional[str]
    revision_count: int

    # --- output ---
    written_files: list[str]
    done: bool
