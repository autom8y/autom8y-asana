# CLAUDE.md

> Entry point for Claude Code. Skills-based progressive disclosure architecture.

## Quick Start

This project uses a 4-agent development workflow:

| Agent                    | Role                                          | Produces                  |
| ------------------------ | --------------------------------------------- | ------------------------- |
| **Requirements Analyst** | Clarifies intent, defines success             | PRD                       |
| **Architect**            | Designs solutions, makes structural decisions | TDD, ADRs                 |
| **Principal Engineer**   | Implements with craft and discipline          | Code, impl ADRs           |
| **QA/Adversary**         | Validates, finds problems before production   | Test Plan, defect reports |

**New here?** Use the `prompting` skill for copy-paste patterns, or `initiative-scoping` to start a new project.

## Skills Architecture

Skills provide domain knowledge on-demand. They activate based on your task:

| Skill                | When to Activate                                           |
| -------------------- | ---------------------------------------------------------- |
| **10x-workflow**     | Agent coordination, handoffs, pipeline flow                |
| **atuin-desktop**    | Creating/editing .atrb runbooks, validating runbook YAML   |
| **documentation**    | PRD/TDD/ADR/Test Plan templates and formats                |
| **initiative-scoping** | Starting new projects, Prompt -1/0 templates             |
| **justfile**         | Task automation, just recipes, project commands            |
| **prompting**        | Copy-paste prompt patterns, agent invocation examples      |
| **standards**        | Code conventions, tech stack, repository structure, commands |

## Agent Configurations

Full agent prompts live in `.claude/agents/`:

- `orchestrator.md` - Coordinates multi-phase workflows
- `requirements-analyst.md` - Produces PRDs
- `architect.md` - Produces TDDs and ADRs
- `principal-engineer.md` - Implements code
- `qa-adversary.md` - Validates and tests

## Hooks (Automatic Context)

Hooks auto-inject context on session start and automate common operations:

| Hook | Event | What It Does |
|------|-------|--------------|
| session-context | SessionStart | Loads project, team, session, git info |
| auto-park | Stop | Saves session state when Claude exits |
| artifact-tracker | PostToolUse | Tracks PRD/TDD/ADR creation |
| team-validator | PreToolUse | Validates team switch commands |

**No manual context needed** - hooks inject it automatically.

See `.claude/hooks/` for scripts, `.claude/settings.local.json` for config.

## Dynamic Context Syntax

Commands can include dynamic context using the `!` prefix syntax:

```markdown
**Active team**: !`cat .claude/ACTIVE_TEAM`
**Git branch**: !`git branch --show-current`
```

When Claude reads a command file:
1. Lines starting with `!` followed by backtick-wrapped commands are executed
2. The output replaces the command inline
3. This provides live context without hook complexity

**Best practices:**
- Use for simple, fast queries (avoid slow operations)
- Always include fallbacks: `!`cat file 2>/dev/null || echo "default"`
- Prefer hooks for complex context that all commands need

## Getting Help

| Question                        | Go To                        |
| ------------------------------- | ---------------------------- |
| How do I invoke an agent?       | `prompting` skill            |
| What template do I use?         | `documentation` skill        |
| Where does this code go?        | `standards` skill            |
| Which agent handles this?       | `10x-workflow` skill         |
| How do I start a new project?   | `initiative-scoping` skill   |
| How do I create a runbook?      | `atuin-desktop` skill        |
| How do I automate tasks?        | `justfile` skill             |
| What hooks are configured?      | `.claude/hooks/` directory   |
