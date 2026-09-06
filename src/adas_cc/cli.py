"""CLI for ADAS-CC.

    adas-cc scan /path/to/repo
    adas-cc scan /path/to/repo --auto-approve
    adas-cc scan /path/to/repo --model claude-opus-5

Requires ANTHROPIC_API_KEY in the environment to use the LLM-driven
designer; without it, falls back to a rule-based default design (see
nodes/designer.py) so the tool still works end-to-end for a quick look.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import typer
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from adas_cc.graph import build_graph

app = typer.Typer(add_completion=False, help="Generate a Claude Code multi-agent system for a repo.")
console = Console()


def _print_scan_summary(scan: dict) -> None:
    table = Table(title="Repo Scan", show_header=False, box=None)
    table.add_row("Primary language", str(scan.get("primary_language") or "unknown"))
    table.add_row("Frameworks", ", ".join(scan.get("frameworks", [])) or "-")
    table.add_row("Test frameworks", ", ".join(scan.get("test_frameworks", [])) or "-")
    table.add_row("Package managers", ", ".join(scan.get("package_managers", [])) or "-")
    table.add_row("CI", ", ".join(scan.get("ci_systems", [])) or ("no" if not scan.get("has_ci") else "yes"))
    table.add_row("Files scanned", str(scan.get("file_count", 0)))
    table.add_row("Update mode", "yes (.claude/ already exists)" if scan.get("is_update_mode") else "no")
    console.print(table)
    for w in scan.get("warnings", []):
        console.print(f"[yellow]warning:[/yellow] {w}")


def _print_proposed_files(payload: dict) -> None:
    table = Table(title="Proposed Files")
    table.add_column("Path")
    table.add_column("Kind")
    table.add_column("Status")
    for f in payload["proposed_files"]:
        status = "[green]new[/green]" if f["is_new"] else ("[yellow]changed[/yellow]" if f["diff"] else "[dim]unchanged[/dim]")
        table.add_row(f["path"], f["kind"], status)
    console.print(table)


def _prompt_decision(payload: dict) -> dict:
    _print_proposed_files(payload)
    choice = typer.prompt(
        "\n[a]pprove / [v]iew a file / [r]evise with feedback / [x] reject",
        default="a",
    ).strip().lower()

    if choice.startswith("v"):
        path = typer.prompt("Which path to view?")
        match = next((f for f in payload["proposed_files"] if f["path"] == path), None)
        if match:
            lexer = "markdown" if path.endswith(".md") else "json"
            console.print(Panel(Syntax(match["preview"], lexer, word_wrap=True), title=path))
            if match["diff"]:
                console.print(Panel(match["diff"], title=f"diff: {path}"))
        return _prompt_decision(payload)

    if choice.startswith("r"):
        notes = typer.prompt("What should change?")
        return {"decision": "revise", "notes": notes}

    if choice.startswith("x"):
        return {"decision": "reject"}

    return {"decision": "approve"}


@app.command()
def scan(
    repo_path: str = typer.Argument(..., help="Path to the target repository"),
    model: str = typer.Option("claude-sonnet-4-6", help="Anthropic model for the designer step"),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Skip the interactive review and write files immediately"
    ),
):
    """Scan REPO_PATH and generate a Claude Code multi-agent system for it."""
    root = Path(repo_path).expanduser().resolve()
    if not root.exists():
        console.print(f"[red]error:[/red] path does not exist: {root}")
        raise typer.Exit(1)

    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    console.print(Panel(f"Scanning [bold]{root}[/bold]", title="ADAS-CC"))

    state = graph.invoke(
        {"repo_path": str(root), "model_name": model, "auto_approve": auto_approve},
        config=config,
    )

    while "__interrupt__" in state:
        interrupt_obj = state["__interrupt__"][0]
        payload = interrupt_obj.value
        decision = _prompt_decision(payload)
        state = graph.invoke(Command(resume=decision), config=config)

    if state.get("done"):
        console.print(Panel(
            "\n".join(f"[green]wrote[/green] {p}" for p in state["written_files"]),
            title="Done",
        ))
    else:
        console.print("[yellow]No files were written (rejected or interrupted).[/yellow]")

    if "scan_report" in state:
        _print_scan_summary(state["scan_report"])


if __name__ == "__main__":
    app()
