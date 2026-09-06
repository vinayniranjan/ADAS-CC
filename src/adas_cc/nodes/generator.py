"""Generator node.

Converts the `DesignSpec` into a list of `ProposedFile` entries pointing
at real paths under the target repo's `.claude/` directory (plus a root
`CLAUDE.md`). When a file already exists on disk (update mode), a unified
diff is attached so the approval step can show what would change.
"""
from __future__ import annotations

import difflib
import json
from pathlib import Path

from adas_cc.generators.render import (
    render_claude_md,
    render_command,
    render_format_hook_script,
    render_settings_json,
    render_skill,
    render_subagent,
)
from adas_cc.state import AdasState, ProposedFile


def _diff_if_exists(root: Path, rel_path: str, new_content: str) -> tuple[bool, str | None]:
    full = root / rel_path
    if not full.exists():
        return True, None
    old_content = full.read_text(errors="ignore")
    if old_content == new_content:
        return False, None
    diff = "\n".join(
        difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
            lineterm="",
        )
    )
    return True, diff


def generator_node(state: AdasState) -> dict:
    root = Path(state["repo_path"]).expanduser().resolve()
    design = state["design_spec"]
    proposed: list[ProposedFile] = []

    # CLAUDE.md
    claude_md = render_claude_md(design["project_summary"], design["claude_md_body"])
    is_new, diff = _diff_if_exists(root, "CLAUDE.md", claude_md)
    proposed.append(
        ProposedFile(path="CLAUDE.md", content=claude_md, kind="claude_md", is_new=is_new, diff=diff)
    )

    # Subagents
    for agent in design.get("subagents", []):
        rel = f".claude/agents/{agent['name']}.md"
        content = render_subagent(agent)
        is_new, diff = _diff_if_exists(root, rel, content)
        proposed.append(ProposedFile(path=rel, content=content, kind="agent", is_new=is_new, diff=diff))

    # Commands
    for cmd in design.get("commands", []):
        rel = f".claude/commands/{cmd['name']}.md"
        content = render_command(cmd)
        is_new, diff = _diff_if_exists(root, rel, content)
        proposed.append(ProposedFile(path=rel, content=content, kind="command", is_new=is_new, diff=diff))

    # Skills (each in its own directory, per the Agent Skills spec)
    for skill in design.get("skills", []):
        rel = f".claude/skills/{skill['name']}/SKILL.md"
        content = render_skill(skill)
        is_new, diff = _diff_if_exists(root, rel, content)
        proposed.append(ProposedFile(path=rel, content=content, kind="skill", is_new=is_new, diff=diff))

    # Hooks -> merged into .claude/settings.json
    hooks = design.get("hooks", [])
    if hooks:
        settings_path = root / ".claude" / "settings.json"
        existing = None
        if settings_path.exists():
            try:
                existing = json.loads(settings_path.read_text())
            except Exception:
                existing = None
        content = render_settings_json(existing, hooks)
        is_new, diff = _diff_if_exists(root, ".claude/settings.json", content)
        proposed.append(
            ProposedFile(
                path=".claude/settings.json", content=content, kind="hook_settings",
                is_new=is_new, diff=diff,
            )
        )

        # Emit the formatter script if any hook references it.
        script_rel = ".claude/hooks/format-changed-file.sh"
        if any(h["command"] == script_rel for h in hooks):
            lang = state["scan_report"].get("primary_language", "")
            script_content = render_format_hook_script(lang)
            is_new, diff = _diff_if_exists(root, script_rel, script_content)
            proposed.append(
                ProposedFile(path=script_rel, content=script_content, kind="other", is_new=is_new, diff=diff)
            )

    return {"proposed_files": proposed}
