"""Approval node.

Pauses the graph with LangGraph's `interrupt()` so the CLI (or any other
caller, e.g. a web UI) can show the proposed file tree/diffs and collect a
decision. The graph resumes with `Command(resume=<payload>)`.

Expected resume payload (dict):
    {"decision": "approve"} -> proceed to write
    {"decision": "revise", "notes": "..."} -> loop back to design
    {"decision": "reject"} -> stop without writing
"""
from __future__ import annotations

from langgraph.types import interrupt

from adas_cc.state import AdasState


def approval_node(state: AdasState) -> dict:
    if state.get("auto_approve"):
        return {"approval_decision": "approve"}

    payload = interrupt(
        {
            "type": "review_proposed_files",
            "proposed_files": [
                {
                    "path": f["path"],
                    "kind": f["kind"],
                    "is_new": f["is_new"],
                    "diff": f.get("diff"),
                    "preview": f["content"][:2000],
                }
                for f in state["proposed_files"]
            ],
        }
    )

    decision = payload.get("decision", "reject")
    result: dict = {"approval_decision": decision}
    if decision == "revise":
        result["feedback"] = payload.get("notes", "")
        result["revision_count"] = state.get("revision_count", 0) + 1
    return result


def route_after_approval(state: AdasState) -> str:
    decision = state.get("approval_decision")
    if decision == "approve":
        return "write"
    if decision == "revise" and state.get("revision_count", 0) < 3:
        return "design"
    return "end"
