# CLAUDE.md

> Entry point for Claude Code. Skills-based progressive disclosure architecture.


## Execution Mode

**CHECK FIRST**: Is there an active workflow?

| Workflow State | Detection | Behavior |
|----------------|-----------|----------|
| **Active** (`workflow.active: true`) | Session Context shows workflow | MUST delegate via Task tool |
| **Inactive** | No workflow in context | May execute directly |

**When in an active workflow (/task, /sprint, /consolidate):**
1. The main thread is the COACH - coordinates, does not play
2. CONSULT the orchestrator for direction (do not ask it to execute)
3. PARSE the directive and invoke specialists via Task tool
4. NEVER use Edit/Write directly - that is specialist work

**Correct Pattern**:
```
Main Thread -> [Task tool] -> Orchestrator (returns directive)
Main Thread -> [Task tool] -> Specialist (per directive)
```

**Incorrect Pattern**:
```
Main Thread -> [Edit/Write] -> Direct implementation
Main Thread -> "Execute the sprint" -> Orchestrator (cannot execute)
```

See: `.claude/skills/orchestration/main-thread-guide.md` for the consultation loop template.

## Quick Start

This project uses a 5-agent workflow (10x-dev-pack):

| Agent | Role | Produces |
| ----- | ---- | -------- |
| **architect** | Designs solutions, makes decisions | TDD, ADRs |
| **orchestrator** | Coordinates multi-phase workflows | Work breakdown |
| **principal-engineer** | Implements with craft | Code |
| **qa-adversary** | Validates, finds problems | Test reports |
| **requirements-analyst** | Clarifies intent, defines success | PRD |

**New here?** Use the `prompting` skill for copy-paste patterns, or `initiative-scoping` to start a new project.

<!-- SYNC: skeleton-owned -->
## Agent Routing

Before implementing work, check:
1. **Is there an active workflow?** (see Execution Mode above)
   - If YES: You MUST delegate. Do not implement directly.
2. Is there an active team? (see Team Context below)
3. Does this task match a phase in the workflow?
4. If yes -> invoke that phase's agent via Task tool

**During active workflow**: Always delegate via Task tool. No exceptions.
**Outside workflow** (ad-hoc request, no /task or /sprint active):
  - **Single-phase work** (bug fix, docs update): May execute directly.
  - **Multi-phase work**: Route to `/task` or team agent.
**Unsure?** Route to `/consult` for guidance.

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

## Agent Configurations

Full agent prompts live in `.claude/agents/`:

- `architect.md` - The system design authority who evaluates tradeoff
- `orchestrator.md` - The coordination hub for complex feature developme
- `principal-engineer.md` - The master builder who transforms designs into pro
- `qa-adversary.md` - The adversarial tester who breaks things on purpos
- `requirements-analyst.md` - The specification specialist who transforms ambigu

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

<!-- SYNC: skeleton-owned -->
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
