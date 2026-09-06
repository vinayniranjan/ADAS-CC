# Claude Code primitives ADAS-CC generates

ADAS-CC targets Claude Code's file-based configuration system, which lives
under `.claude/` in a repo (project scope) or `~/.claude/` (user scope).
This is the ADAS "VS Code Copilot" surface, ported to Claude Code.

| Primitive           | Location                          | What ADAS-CC generates |
| ------------------- | ---------------------------------- | ----------------------- |
| Project memory      | `CLAUDE.md` (repo root)            | Stack summary, key commands, conventions — loaded into every session and subagent. |
| Subagents           | `.claude/agents/<name>.md`         | Role-based personas (planner, implementer, reviewer, tester, ...) with `name`, `description`, `tools`, `model` frontmatter and a system-prompt body. |
| Slash commands      | `.claude/commands/<name>.md`       | One-shot task prompts (`/plan`, `/review`, ...), with `description`/`argument-hint`/`allowed-tools` frontmatter, routed to the right subagent. |
| Skills              | `.claude/skills/<name>/SKILL.md`   | Reusable multi-step procedures (e.g. "run the test suite") that Claude can discover and invoke. |
| Hooks               | `.claude/settings.json` `hooks{}`  | Deterministic `PreToolUse`/`PostToolUse` enforcement, e.g. auto-format after `Edit`/`Write`. |

## Subagent frontmatter fields ADAS-CC uses

Only `name` and `description` are required by Claude Code; ADAS-CC also sets
`tools` (an allowlist) and `model` (`sonnet` / `opus` / `haiku` / `inherit`)
so each agent runs with the minimum privilege and the right cost/quality
tradeoff for its role. See the [subagents guide](https://code.claude.com/docs/en/sub-agents)
for the full field list, including `hooks`, `skills`, `mcpServers`, and
`permissionMode`, which ADAS-CC leaves for you to add by hand if a
generated agent needs them.

## Why files instead of the Agent SDK's `agents` parameter

Claude Code also supports defining subagents programmatically via the Agent
SDK's `agents` parameter. ADAS-CC writes markdown files instead because:

- They're checked into version control and reviewable in a normal PR.
- They work the same way whether you invoke Claude Code interactively or
  headlessly.
- Programmatically-defined agents take precedence over filesystem ones with
  the same name, so nothing here conflicts with an SDK-based setup you add
  later.

## Update mode

If `.claude/` already exists in the target repo, ADAS-CC scans it, avoids
proposing duplicates, and shows a unified diff for any file it would
change instead of silently overwriting it. Nothing is deleted automatically.
