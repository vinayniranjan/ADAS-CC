"""Scanner node.

Walks the target repository and builds a `ScanReport` using cheap,
deterministic heuristics (file extensions, manifest files, directory
layout, git log). This deliberately does NOT call an LLM: the scan
step should be fast, free, and reproducible. The design step is where
the LLM reasons over this report.
"""
from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

from adas_cc.state import AdasState, ScanReport

IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".turbo", ".mypy_cache", ".pytest_cache", "target", ".idea",
    ".vscode", "coverage", ".tox",
}

MANIFEST_HINTS = {
    "package.json": ("node", "npm"),
    "pnpm-lock.yaml": ("node", "pnpm"),
    "yarn.lock": ("node", "yarn"),
    "requirements.txt": ("python", "pip"),
    "pyproject.toml": ("python", "pip/poetry/uv"),
    "Pipfile": ("python", "pipenv"),
    "go.mod": ("go", "go modules"),
    "Cargo.toml": ("rust", "cargo"),
    "pom.xml": ("java", "maven"),
    "build.gradle": ("java/kotlin", "gradle"),
    "Gemfile": ("ruby", "bundler"),
    "composer.json": ("php", "composer"),
}

FRAMEWORK_HINTS = {
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "react": "React", "next": "Next.js", "vue": "Vue", "svelte": "Svelte",
    "express": "Express", "nestjs": "NestJS", "@nestjs/core": "NestJS",
    "spring-boot": "Spring Boot", "rails": "Ruby on Rails",
}

TEST_HINTS = {
    "pytest": "pytest", "vitest": "Vitest", "jest": "Jest",
    "unittest": "unittest", "rspec": "RSpec", "junit": "JUnit",
    "go test": "go test",
}

CI_FILES = {
    ".github/workflows": "GitHub Actions",
    ".gitlab-ci.yml": "GitLab CI",
    ".circleci/config.yml": "CircleCI",
    "Jenkinsfile": "Jenkins",
    "azure-pipelines.yml": "Azure Pipelines",
}


def _run_git(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _read_text(path: Path, limit: int = 20_000) -> str:
    try:
        return path.read_text(errors="ignore")[:limit]
    except Exception:
        return ""


def scan_repo(root: Path) -> ScanReport:
    languages: Counter[str] = Counter()
    dir_summary: Counter[str] = Counter()
    package_managers: set[str] = set()
    candidate_langs: set[str] = set()
    frameworks: set[str] = set()
    test_frameworks: set[str] = set()
    notable_docs: list[str] = []
    entry_points: list[str] = []
    file_count = 0
    manifest_texts: list[str] = []

    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in IGNORE_DIRS or part.startswith(".") and part not in {".github"} for part in rel.parts[:-1]):
            # allow .github, skip other dot-dirs like .git, .venv
            if any(part in IGNORE_DIRS for part in rel.parts):
                continue
        if path.is_dir():
            continue
        file_count += 1
        top = rel.parts[0] if len(rel.parts) > 1 else "."
        dir_summary[top] += 1
        if path.suffix:
            languages[path.suffix] += 1

        name = path.name
        if name in MANIFEST_HINTS:
            lang, pm = MANIFEST_HINTS[name]
            candidate_langs.add(lang)
            package_managers.add(pm)
            manifest_texts.append(_read_text(path).lower())

        if name.upper() in {"README.MD", "README", "ARCHITECTURE.MD", "CONTRIBUTING.MD"}:
            notable_docs.append(str(rel))

        if name in {"main.py", "app.py", "manage.py", "index.js", "index.ts",
                    "main.go", "main.rs", "server.js", "server.ts"}:
            entry_points.append(str(rel))

    blob = "\n".join(manifest_texts)
    for key, label in FRAMEWORK_HINTS.items():
        if key in blob:
            frameworks.add(label)
    for key, label in TEST_HINTS.items():
        if key in blob:
            test_frameworks.add(label)

    has_ci = False
    ci_systems: list[str] = []
    for rel_path, label in CI_FILES.items():
        p = root / rel_path
        if p.exists():
            has_ci = True
            ci_systems.append(label)

    primary_language = ""
    if candidate_langs:
        primary_language = sorted(candidate_langs)[0]
    elif languages:
        ext_to_lang = {
            ".py": "python", ".ts": "typescript", ".tsx": "typescript",
            ".js": "javascript", ".jsx": "javascript", ".go": "go",
            ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php",
        }
        top_ext, _ = languages.most_common(1)[0]
        primary_language = ext_to_lang.get(top_ext, top_ext.lstrip("."))

    existing_claude_config: dict[str, list[str]] = {}
    claude_dir = root / ".claude"
    is_update_mode = claude_dir.exists()
    if is_update_mode:
        for kind in ("agents", "commands", "skills"):
            sub = claude_dir / kind
            if sub.exists():
                existing_claude_config[kind] = sorted(
                    str(p.relative_to(claude_dir)) for p in sub.rglob("*.md")
                )
        if (root / "CLAUDE.md").exists():
            existing_claude_config["CLAUDE.md"] = ["CLAUDE.md"]

    recent = _run_git(root, ["log", "--oneline", "-15"])
    recent_commits = [line for line in recent.splitlines() if line.strip()]

    warnings: list[str] = []
    if file_count == 0:
        warnings.append("Repository appears empty or path is incorrect.")
    if not primary_language:
        warnings.append("Could not confidently detect a primary language.")

    return ScanReport(
        root=str(root),
        languages={ext: count for ext, count in languages.most_common(20)},
        primary_language=primary_language,
        frameworks=sorted(frameworks),
        package_managers=sorted(package_managers),
        test_frameworks=sorted(test_frameworks),
        has_ci=has_ci,
        ci_systems=ci_systems,
        entry_points=entry_points,
        directory_summary=dict(dir_summary.most_common(15)),
        recent_commits=recent_commits,
        existing_claude_config=existing_claude_config,
        is_update_mode=is_update_mode,
        notable_docs=notable_docs,
        file_count=file_count,
        warnings=warnings,
    )


def scanner_node(state: AdasState) -> dict:
    root = Path(state["repo_path"]).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"repo_path does not exist: {root}")
    report = scan_repo(root)
    return {"scan_report": report}
