"""Writer node.

Writes every proposed file to disk under the target repo. Runs only after
the approval node returns "approve". Creates parent directories as needed
and never deletes existing files that weren't part of this design.
"""
from __future__ import annotations

import stat
from pathlib import Path

from adas_cc.state import AdasState


def writer_node(state: AdasState) -> dict:
    root = Path(state["repo_path"]).expanduser().resolve()
    written: list[str] = []

    for f in state["proposed_files"]:
        full_path = root / f["path"]
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f["content"])
        if full_path.suffix == ".sh":
            full_path.chmod(full_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        written.append(f["path"])

    return {"written_files": written, "done": True}
