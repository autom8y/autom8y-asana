# CLAUDE.md

> Entry point for Claude Code. Skills-based progressive disclosure architecture.


## Execution Mode

**Active workflow?** MUST delegate via Task tool. See `orchestration/execution-mode.md`.
**No workflow?** May execute directly for single-phase work.

## Quick Start

This project uses a 5-agent workflow (doc-team-pack):

| Agent | Role | Produces |
| ----- | ---- | -------- |
| **doc-auditor** | Inventories all existing documentation a | Artifacts |
| **doc-reviewer** | QA for documentation. Verifies technical | Artifacts |
| **information-architect** | Designs the organizational structure, ta | Artifacts |
| **orchestrator** | Coordinates multi-phase workflows | Work breakdown |
| **tech-writer** | Writes clear, consistent, scannable docu | Artifacts |

**New here?** Use the `prompting` skill for copy-paste patterns, or `initiative-scoping` to start a new project.

<!-- SYNC: skeleton-owned -->
## Agent Routing

**Active workflow?** Delegate via Task tool. **No workflow?** Execute directly or use `/task`.
**Unsure?** Route to `/consult` for guidance.

<!-- SYNC: skeleton-owned -->
## Skills

Skills are invoked via the **Skill tool**. Key skills: `10x-workflow` (coordination), `documentation` (templates), `prompting` (agent invocation), `standards` (conventions). See `.claude/skills/` for full list.

## Agent Configurations

Full agent prompts live in `.claude/agents/`:

- `doc-auditor.md` - Inventories all existing documentation across a co
- `doc-reviewer.md` - QA for documentation. Verifies technical accuracy 
- `information-architect.md` - Designs the organizational structure, taxonomy, an
- `orchestrator.md` - The coordination hub for documentation initiatives
- `tech-writer.md` - Writes clear, consistent, scannable documentation 

## Hooks

Hooks auto-inject context (SessionStart, Stop, PostToolUse). No manual context needed. See `.claude/hooks/`.

<!-- SYNC: skeleton-owned -->
## Dynamic Context

Commands use `!` prefix for live context: `!`cat .claude/ACTIVE_TEAM``. Prefer hooks for complex context.

<!-- SYNC: skeleton-owned -->
## Getting Help

| Question | Skill |
|----------|-------|
| Invoke agents | `prompting` |
| Templates | `documentation` |
| Conventions | `standards` |
| Coordination | `10x-workflow` |

<!-- SYNC: skeleton-owned -->
## State Management

**Mutating session/sprint state?** Use state-mate for all `SESSION_CONTEXT.md` and `SPRINT_CONTEXT.md` changes.

### state-mate Usage

state-mate is the centralized authority for session and sprint mutations. It enforces schema validation, lifecycle transitions, and maintains audit trails.

**When to Use**:
- Updating session state (park, resume, wrap)
- Marking tasks complete
- Transitioning workflow phases
- Creating or managing sprints
- Any modification to `*_CONTEXT.md` files

**Invocation Pattern** (MUST include session context):
```
Task(state-mate, "mark_complete task-001 artifact=docs/requirements/PRD-foo.md

Session Context:
- Session ID: {from session-manager.sh status}
- Session Path: .claude/sessions/{session-id}/SESSION_CONTEXT.md")
```

Get session context: `.claude/hooks/lib/session-manager.sh status | jq -r '.session_id'`

**Natural Language Supported**:
```
Task(state-mate, "Mark the PRD task complete with artifact at docs/requirements/PRD-foo.md")
```

**Control Flags**:
- `--dry-run`: Preview changes without applying
- `--emergency`: Bypass non-critical validations (logged)
- `--override=reason`: Bypass lifecycle rules with explicit reason

**Direct writes blocked**: PreToolUse hook intercepts `Write`/`Edit` to `*_CONTEXT.md` and instructs use of state-mate.

**Full documentation**: See `.claude/agents/state-mate.md` and `docs/decisions/ADR-0005-state-mate-centralized-state-authority.md`

<!-- SYNC: skeleton-owned -->
## Slash Commands

Always respond with outcome. "No response" is never correct for explicit user requests.

<!-- SYNC: skeleton-owned -->
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

<!-- SYNC: skeleton-owned -->
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
| **claude-md-architecture** | CLAUDE.md content placement, ownership model, boundary test |

<!-- SYNC: skeleton-owned -->
## Slash Command Response Contract

Slash commands (`/team`, `/sync`, `/start`, etc.) are **explicit user requests** invoked from the terminal. The user typed a command and is waiting for feedback.

**Requirements:**
- ALWAYS respond with the outcome, even for idempotent operations ("already on this team")
- "No response requested" is NEVER correct for slash commands
- Error states must be explained with next steps
