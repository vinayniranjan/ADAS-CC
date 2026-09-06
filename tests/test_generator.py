import json
from pathlib import Path

from adas_cc.nodes.generator import generator_node
from adas_cc.nodes.scanner import scanner_node
from adas_cc.nodes.writer import writer_node


def _base_design_spec():
    return {
        "project_summary": "A python (FastAPI) project using pytest.",
        "claude_md_body": "## Stack\npython + fastapi",
        "subagents": [
            {
                "name": "planner",
                "description": "Plan tasks",
                "tools": ["Read", "Grep", "Glob"],
                "model": "inherit",
                "system_prompt": "You are a planner.",
                "handoff_to": ["implementer"],
            },
            {
                "name": "implementer",
                "description": "Write code",
                "tools": ["Read", "Write", "Edit"],
                "model": "inherit",
                "system_prompt": "You implement.",
                "handoff_to": [],
            },
        ],
        "commands": [
            {
                "name": "plan",
                "description": "Plan a task",
                "argument_hint": "[task]",
                "allowed_tools": ["Read"],
                "body": "Plan: $ARGUMENTS",
            }
        ],
        "skills": [{"name": "run-tests", "description": "Run tests", "body": "Run pytest."}],
        "hooks": [
            {
                "event": "PostToolUse",
                "matcher": "Edit|Write",
                "command": ".claude/hooks/format-changed-file.sh",
                "description": "fmt",
            }
        ],
    }


def _scanned_state(tmp_path: Path) -> dict:
    state = {"repo_path": str(tmp_path)}
    state.update(scanner_node(state))
    return state


def test_generator_produces_expected_paths_and_marks_everything_new(tmp_path: Path):
    state = _scanned_state(tmp_path)
    state["design_spec"] = _base_design_spec()

    result = generator_node(state)
    paths = {f["path"]: f for f in result["proposed_files"]}

    assert set(paths) == {
        "CLAUDE.md",
        ".claude/agents/planner.md",
        ".claude/agents/implementer.md",
        ".claude/commands/plan.md",
        ".claude/skills/run-tests/SKILL.md",
        ".claude/settings.json",
        ".claude/hooks/format-changed-file.sh",
    }
    assert all(f["is_new"] for f in paths.values())
    assert all(f["diff"] is None for f in paths.values())
    assert paths["CLAUDE.md"]["kind"] == "claude_md"
    assert paths[".claude/agents/planner.md"]["kind"] == "agent"
    assert paths[".claude/commands/plan.md"]["kind"] == "command"
    assert paths[".claude/skills/run-tests/SKILL.md"]["kind"] == "skill"
    assert paths[".claude/settings.json"]["kind"] == "hook_settings"
    assert paths[".claude/hooks/format-changed-file.sh"]["kind"] == "other"


def test_generator_detects_diff_after_write_and_content_change(tmp_path: Path):
    state = _scanned_state(tmp_path)
    state["design_spec"] = _base_design_spec()
    state.update(generator_node(state))
    writer_node(state)

    # Re-scan: repo now has .claude/, so update mode should be detected.
    state2 = _scanned_state(tmp_path)
    assert state2["scan_report"]["is_update_mode"] is True

    changed_spec = _base_design_spec()
    changed_spec["project_summary"] += " UPDATED"
    changed_spec["subagents"][0]["description"] = "Plan tasks v2"
    state2["design_spec"] = changed_spec

    result2 = generator_node(state2)
    paths2 = {f["path"]: f for f in result2["proposed_files"]}

    assert paths2["CLAUDE.md"]["is_new"] is True  # exists=True reused as "changed" flag
    assert paths2["CLAUDE.md"]["diff"] is not None
    assert "UPDATED" in paths2["CLAUDE.md"]["diff"]
    assert paths2[".claude/agents/planner.md"]["diff"] is not None

    # An unchanged file (implementer.md) should report no diff.
    assert paths2[".claude/agents/implementer.md"]["diff"] is None


def test_writer_writes_files_and_sets_exec_bit_on_shell_scripts(tmp_path: Path):
    state = _scanned_state(tmp_path)
    state["design_spec"] = _base_design_spec()
    state.update(generator_node(state))

    result = writer_node(state)

    assert set(result["written_files"]) == {
        f["path"] for f in state["proposed_files"]
    }
    hook_path = tmp_path / ".claude" / "hooks" / "format-changed-file.sh"
    assert hook_path.exists()
    assert hook_path.stat().st_mode & 0o111  # executable bit set

    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert "PostToolUse" in settings["hooks"]


def test_generator_skips_hook_files_when_no_hooks_designed(tmp_path: Path):
    state = _scanned_state(tmp_path)
    spec = _base_design_spec()
    spec["hooks"] = []
    state["design_spec"] = spec

    result = generator_node(state)
    paths = {f["path"] for f in result["proposed_files"]}

    assert ".claude/settings.json" not in paths
    assert ".claude/hooks/format-changed-file.sh" not in paths
