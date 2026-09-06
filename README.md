# ADAS-CC — The Agent Compiler for Claude Code

A meta-agent, orchestrated with **LangGraph + Python**, that scans any
repository and generates a complete, interconnected **Claude Code**
multi-agent system: subagents, slash commands, skills, and hooks.

## What ADAS-CC does

You point it at a repo and it generates:

| What                  | Files                              | Purpose                                                             |
| --------------------- | ----------------------------------- | -------------------------------------------------------------------- |
| **Project memory**    | `CLAUDE.md`                         | Stack, key commands, conventions — loaded by every session/subagent. |
| **Subagents**         | `.claude/agents/*.md`               | Role-based personas (planner, implementer, reviewer, tester, ...) with tool/model restrictions and handoffs. |
| **Slash commands**    | `.claude/commands/*.md`             | One-shot tasks (`/plan`, `/review`) routed to the right subagent.    |
| **Skills**            | `.claude/skills/*/SKILL.md`         | Reusable multi-step workflows (e.g. running the test suite).         |
| **Hooks**             | `.claude/settings.json`             | Deterministic enforcement (e.g. auto-format after an edit).          |

See [`docs/claude-code-primitives.md`](docs/claude-code-primitives.md) for
how each of these maps to Claude Code's actual configuration format, or
[`docs/the-agent-compiler.html`](docs/the-agent-compiler.html) for a visual,
diagram-driven field guide to the whole pipeline and the multi-agent system
it generates.

## Architecture: a LangGraph pipeline, not one big prompt

```
START
  │
  ▼
┌────────┐   heuristic, no LLM      ┌─────────┐   LLM (or offline fallback) ┌───────────┐
│  scan  │ ───────────────────────▶ │ design  │ ───────────────────────────▶│ generate  │
└────────┘   ScanReport             └─────────┘   DesignSpec                └───────────┘
                                          ▲                                        │
                                          │ revise (human feedback)                ▼
                                          │                                  ┌───────────┐
                                          └───────────────────────────────── │  approve  │
                                                                              └───────────┘
                                                                          approve │   │ reject
                                                                                  ▼   ▼
                                                                            ┌───────┐ END
                                                                            │ write │
                                                                            └───────┘
                                                                                │
                                                                                ▼
                                                                               END
```

- **`scan`** — deterministic, dependency-free repo analysis (languages,
  frameworks, test tooling, CI, existing `.claude/` config for update mode).
  No LLM calls, so it's fast, free, and reproducible.
- **`design`** — an LLM call (Claude, via `langchain-anthropic`) with
  structured output constrained to a Pydantic schema, reasoning over the
  scan report to propose subagents/commands/skills/hooks tailored to the
  repo. Falls back to a solid rule-based default (planner → implementer →
  reviewer → tester) when `ANTHROPIC_API_KEY` isn't set, so the whole
  pipeline runs end-to-end offline too.
- **`generate`** — pure rendering: turns the design into real file paths
  and contents, computing a unified diff against anything that already
  exists on disk (update mode).
- **`approve`** — a human-in-the-loop checkpoint using LangGraph's
  `interrupt()`. The graph pauses, the CLI shows the proposed file tree
  and diffs, and you can **approve**, **revise** (send feedback back to
  `design` for another pass, up to 3 rounds), or **reject**.
- **`write`** — writes the approved files to disk. Never deletes anything
  it didn't propose.

Because this is a real `StateGraph` with a checkpointer, the same graph
can be driven by the CLI, a web backend, or a test harness — the
interrupt/resume contract is the same either way.

## Quick start

```bash
uv sync
export ANTHROPIC_API_KEY=sk-ant-...   # optional — omit to use the offline fallback design
uv run adas-cc scan /path/to/your-repo
```

You'll see the scan summary, then a table of proposed files. Choose:

- `a` — approve and write everything
- `v` — view a specific file's content or diff before deciding
- `r` — send written feedback back to the designer for another pass
- `x` — reject and exit without writing anything

Skip the interactive review entirely:

```bash
uv run adas-cc scan /path/to/your-repo --auto-approve
```

## Updating an existing `.claude/` setup

If the target repo already has a `.claude/` directory, ADAS-CC detects it,
tells the designer what already exists (so it proposes gaps rather than
duplicates), and shows a unified diff for any file it would change instead
of silently overwriting it.

## Project layout

```
src/adas_cc/
├── cli.py                 # Typer CLI: drives the graph, handles interrupt/resume
├── graph.py                # LangGraph StateGraph wiring
├── state.py                 # TypedDicts shared across all nodes
├── schema.py                 # Pydantic models for the designer's structured LLM output
├── nodes/
│   ├── scanner.py             # scan: heuristic repo analysis
│   ├── designer.py             # design: LLM call + offline fallback
│   ├── generator.py             # generate: DesignSpec -> ProposedFile[] with diffs
│   ├── approval.py                # approve: interrupt()-based human review
│   └── writer.py                    # write: writes approved files to disk
├── generators/
│   └── render.py                     # pure DesignSpec-piece -> file-content renderers
└── templates/                          # example generated outputs for reference
    ├── python-fastapi/
    └── typescript-react/

docs/claude-code-primitives.md      # what each generated file maps to in Claude Code
tests/                               # unit tests for scanner/render/generator
```

## Templates

`src/adas_cc/templates/` contains example outputs for common stacks —
`python-fastapi/` and `typescript-react/` — so you can see what a
generated `.claude/` tree looks like without running the tool.

## Requirements

- Python 3.10+ (developed and tested against the latest stable release, 3.14)
- [`uv`](https://docs.astral.sh/uv/) for dependency management and running the CLI
- `ANTHROPIC_API_KEY` for the LLM-driven designer (optional — see fallback above)
- A target repo to point it at (a git repo isn't required, but recent-commit
  context in the scan report is richer if it is one)

## License

Apache-2.0
