import subprocess
from pathlib import Path

from adas_cc.nodes.scanner import scan_repo


def _init_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.email=a@a.com", "-c", "user.name=a", "commit", "-q", "-m", "init"],
        cwd=root,
        check=True,
    )


def test_scan_detects_fastapi_project(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "sample"\ndependencies = ["fastapi", "pytest"]\n')
    (tmp_path / "src" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    (tmp_path / "tests" / "test_main.py").write_text("def test_ok():\n    assert True\n")
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")
    (tmp_path / "README.md").write_text("# Sample\n")
    _init_git(tmp_path)

    report = scan_repo(tmp_path)

    assert report["primary_language"] == "python"
    assert "FastAPI" in report["frameworks"]
    assert "pytest" in report["test_frameworks"]
    assert report["has_ci"] is True
    assert "GitHub Actions" in report["ci_systems"]
    assert report["is_update_mode"] is False
    assert report["file_count"] >= 5
    assert len(report["recent_commits"]) == 1


def test_scan_detects_existing_claude_config(tmp_path: Path):
    claude_dir = tmp_path / ".claude" / "agents"
    claude_dir.mkdir(parents=True)
    (claude_dir / "planner.md").write_text("---\nname: planner\ndescription: x\n---\nbody\n")
    (tmp_path / "CLAUDE.md").write_text("# hi\n")

    report = scan_repo(tmp_path)

    assert report["is_update_mode"] is True
    assert "agents/planner.md" in report["existing_claude_config"]["agents"]
    assert "CLAUDE.md" in report["existing_claude_config"]


def test_scan_empty_repo_warns(tmp_path: Path):
    report = scan_repo(tmp_path)
    assert report["file_count"] == 0
    assert any("empty" in w for w in report["warnings"])
