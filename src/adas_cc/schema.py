"""Pydantic models used to constrain the designer LLM's structured output.

These mirror the TypedDicts in `state.py` but as Pydantic models, which
`ChatAnthropic.with_structured_output()` needs to build a tool-call schema.
Keep the two in sync manually; they're intentionally simple.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SubagentModel(BaseModel):
    name: str = Field(description="lowercase-hyphenated unique id, e.g. 'test-runner'")
    description: str = Field(
        description="When Claude should delegate to this subagent. Written so it "
        "clearly distinguishes this agent from the others in the system."
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Claude Code tool names this agent is restricted to, e.g. "
        "['Read', 'Grep', 'Glob', 'Bash']. Empty list means inherit all tools.",
    )
    model: str = Field(
        default="inherit",
        description="One of: sonnet, opus, haiku, inherit",
    )
    system_prompt: str = Field(
        description="The full system prompt / persona for this subagent, written "
        "in second person ('You are a...'). Include a numbered workflow and an "
        "explicit output format."
    )
    handoff_to: list[str] = Field(
        default_factory=list,
        description="Names of other subagents this one should suggest handing off "
        "to when it finishes (referenced in its own prompt as next steps).",
    )
    color: Optional[str] = Field(
        default=None,
        description="Optional display color: red, blue, green, yellow, purple, "
        "orange, pink, or cyan.",
    )


class CommandModel(BaseModel):
    name: str = Field(description="lowercase-hyphenated slash command name, no leading slash")
    description: str = Field(description="One-line description shown in /help")
    argument_hint: str = Field(default="", description="e.g. '[issue-number]'")
    allowed_tools: list[str] = Field(default_factory=list)
    routes_to_agent: Optional[str] = Field(
        default=None, description="Name of the subagent this command should delegate to, if any"
    )
    body: str = Field(description="The prompt template body, may use $ARGUMENTS or $1, $2")


class SkillModel(BaseModel):
    name: str = Field(description="lowercase-hyphenated skill id")
    description: str = Field(
        description="Third-person trigger description: when this skill applies, "
        "written so Claude can decide when to invoke it."
    )
    body: str = Field(description="Full SKILL.md body: procedure, checklist, examples")


class HookModel(BaseModel):
    event: str = Field(description="PreToolUse, PostToolUse, SubagentStart, or SubagentStop")
    matcher: str = Field(description="Tool name or agent name regex to match, e.g. 'Edit|Write'")
    command: str = Field(description="Shell command to run")
    description: str = Field(description="Why this hook exists")


class DesignModel(BaseModel):
    project_summary: str = Field(
        description="2-4 sentence summary of the project's stack and conventions, "
        "for use as the opening of CLAUDE.md"
    )
    claude_md_body: str = Field(
        description="Full markdown body for the project's CLAUDE.md: stack, key "
        "commands (build/test/lint), directory layout, and conventions the whole "
        "agent system should follow."
    )
    subagents: list[SubagentModel] = Field(min_length=1)
    commands: list[CommandModel] = Field(default_factory=list)
    skills: list[SkillModel] = Field(default_factory=list)
    hooks: list[HookModel] = Field(default_factory=list)
