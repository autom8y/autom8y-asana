<!-- KNOSSOS:START execution-mode -->
## Execution Mode

This project supports three operating modes (see PRD-hybrid-session-model for details):

| Mode | Session | Rite | Main Agent Behavior |
|------|---------|------|---------------------|
| **Native** | No | - | Direct execution, no tracking |
| **Cross-Cutting** | Yes | No | Direct execution + session tracking |
| **Orchestrated** | Yes | Yes (ACTIVE) | Coach pattern, delegate via Task tool |

**Unsure?** Use `/consult` for workflow routing.

For enforcement rules: `orchestration/execution-mode.md`
<!-- KNOSSOS:END execution-mode -->

<!-- KNOSSOS:START knossos-identity -->
## Knossos Identity

> **roster/.claude/ IS Knossos.** This repository is the Knossos platform.

The naming reflects Greek mythology (see `docs/philosophy/knossos-doctrine.md` for the full doctrine):

| Myth | Component | Function |
|------|-----------|----------|
| **Knossos** | The platform | The labyrinth itself |
| **Ariadne** | CLI binary (`ari`) | The thread ensuring return |
| **Theseus** | Claude Code agent | The navigator with amnesia |
| **Moirai** | Session lifecycle agent | The Fates who spin, measure, and cut |
| **White Sails** | Confidence signal | Honest return indicator |
| **Rites** | Practice bundles | Invokable ceremonies |
| **Pantheon** | Agent collection | The specialist agents within a rite |

For full details: `docs/guides/knossos-integration.md` and `docs/decisions/ADR-0009-knossos-roster-identity.md`
<!-- KNOSSOS:END knossos-identity -->

<!-- KNOSSOS:START quick-start regenerate=true source=ACTIVE_RITE+agents -->
## Quick Start

This project uses a 5-agent workflow (10x-dev):

| Agent | Role | Produces |
| ----- | ---- | -------- |
| **orchestrator** | Coordinates development lifecycle phases and routes work to specialists |  |
| **requirements-analyst** | Gathers requirements and produces PRD artifacts |  |
| **architect** | Creates technical design documents and architecture decisions |  |
| **principal-engineer** | Implements code according to design specifications |  |
| **qa-adversary** | Validates implementation through adversarial testing |  |

**New here?** Use the `prompting` skill for copy-paste patterns, or `initiative-scoping` to start a new project.
<!-- KNOSSOS:END quick-start -->

<!-- KNOSSOS:START agent-routing -->
## Agent Routing

When working within an orchestrated session, the main thread coordinates via Task tool delegation to specialist agents. Without an active session, direct execution or `/task` initialization are both valid approaches.

For routing guidance: `/consult`
<!-- KNOSSOS:END agent-routing -->

<!-- KNOSSOS:START skills -->
## Skills

Skills are invoked via the **Skill tool**. Key skills: `orchestration` (workflow coordination), `documentation` (templates), `prompting` (agent invocation), `standards` (conventions), `ecosystem-ref` (roster ecosystem patterns). See `.claude/skills/` and `~/.claude/skills/` for full list.
<!-- KNOSSOS:END skills -->

<!-- KNOSSOS:START agent-configurations regenerate=true source=agents/*.md -->
## Agent Configurations

Full agent prompts live in `.claude/agents/`:

- `orchestrator.md` - Coordinates development lifecycle phases and routes work to specialists
- `requirements-analyst.md` - Gathers requirements and produces PRD artifacts
- `architect.md` - Creates technical design documents and architecture decisions
- `principal-engineer.md` - Implements code according to design specifications
- `qa-adversary.md` - Validates implementation through adversarial testing
<!-- KNOSSOS:END agent-configurations -->

<!-- KNOSSOS:START hooks -->
## Hooks

Hooks auto-inject context (SessionStart, Stop, PostToolUse). No manual context needed. See `.claude/hooks/`.
<!-- KNOSSOS:END hooks -->

<!-- KNOSSOS:START dynamic-context -->
## Dynamic Context

Commands use `!` prefix for live context: `!`cat .claude/ACTIVE_RITE``. Prefer hooks for complex context.
<!-- KNOSSOS:END dynamic-context -->

<!-- KNOSSOS:START ariadne-cli -->
## Ariadne CLI

The `ari` binary provides session lifecycle, rite management, and workflow operations.

### Session Management

```bash
ari session create "initiative" COMPLEXITY    # Create new session (PATCH|MODULE|SYSTEM|INITIATIVE|MIGRATION)
ari session status                            # Show current session state
ari session list                              # List all sessions
ari session park --reason "taking break"      # Park session with reason
ari session resume                            # Resume parked session
ari session wrap                              # Complete session with sails
ari session transition <phase>                # Transition to workflow phase
ari session audit                             # Show session audit log
```

### Rite Management

```bash
ari rite list                                 # List available rites
ari rite info <name>                          # Show rite details
ari rite status                               # Show active rite status
ari rite current                              # Show current active rite
ari rite swap <name>                          # Switch to different rite
ari rite invoke <name>                        # Invoke rite entry point
ari rite validate <name>                      # Validate rite manifest
```

### Sync Operations

```bash
ari sync materialize --rite <name>            # Materialize rite to .claude/
ari sync materialize --force                  # Force overwrite existing
ari sync status                               # Show sync status
ari sync diff                                 # Show pending changes
ari sync pull                                 # Pull from source
ari sync push                                 # Push to destination
ari sync history                              # Show sync history
```

### Hook Operations

```bash
ari hook clew                                 # Emit session clew (breadcrumb)
ari hook context                              # Emit full context injection
ari hook validate                             # Validate hook configuration
ari hook route                                # Route to appropriate handler
ari hook writeguard                           # Check write permissions
ari hook autopark                             # Check autopark conditions
```

### Quality Gates

```bash
ari sails check                               # Check White Sails confidence
ari validate artifact <file>                  # Validate PRD/TDD/ADR artifact
ari validate handoff --phase=<phase>          # Validate handoff criteria
ari validate schema <name> <file>             # Validate against schema
```

### Agent Handoffs

```bash
ari handoff prepare --from <agent> --to <agent>   # Prepare handoff package
ari handoff execute --from <agent> --to <agent>   # Execute handoff
ari handoff status                                # Show handoff status
ari handoff history                               # Show handoff history
```

### Manifest Operations

```bash
ari manifest show                             # Show current manifest
ari manifest diff                             # Show manifest differences
ari manifest merge                            # Merge manifest sources
ari manifest validate                         # Validate manifest structure
```

### Inscription (CLAUDE.md)

```bash
ari inscription sync                          # Sync CLAUDE.md with templates
ari inscription sync --dry-run                # Preview changes
ari inscription validate                      # Check manifest and CLAUDE.md
ari inscription diff                          # Show pending changes
ari inscription backups                       # List available backups
ari inscription rollback                      # Restore from backup
```

### Artifact Registry

```bash
ari artifact list                             # List registered artifacts
ari artifact register <path>                  # Register new artifact
ari artifact query <type>                     # Query artifacts by type
ari artifact rebuild                          # Rebuild artifact index
```

### Session Cleanup (Naxos)

```bash
ari naxos scan                                # Scan for orphaned sessions
ari naxos scan --inactive-threshold=12h       # Custom inactivity threshold
ari naxos scan --include-archived             # Include archived sessions
```

### Worktree Management

```bash
ari worktree create <name>                    # Create isolated worktree
ari worktree list                             # List worktrees
ari worktree status                           # Show worktree status
ari worktree switch <name>                    # Switch to worktree
ari worktree sync                             # Sync worktree state
ari worktree remove <name>                    # Remove worktree
ari worktree cleanup                          # Clean up stale worktrees
```

### Tribute Generation

```bash
ari tribute generate                          # Generate session tribute/summary
```

### Cognitive Budget

Tool usage tracking with configurable thresholds:
- `ARIADNE_MSG_WARN=250` - Warning threshold (default)
- `ARIADNE_MSG_PARK` - Park suggestion threshold
- `ARIADNE_BUDGET_DISABLE=1` - Disable tracking

Build: `just build` (from repo root)

Full reference: `docs/guides/ariadne-cli.md`
<!-- KNOSSOS:END ariadne-cli -->

<!-- KNOSSOS:START getting-help -->
## Getting Help

| Question | Skill |
|----------|-------|
| Invoke agents | `prompting` |
| Templates | `documentation` or `doc-ecosystem` |
| Conventions | `standards` |
| Workflow coordination | `orchestration` |
| Roster ecosystem | `ecosystem-ref` |
| User preferences | See `docs/guides/user-preferences.md` |
| Knossos integration | `docs/guides/knossos-integration.md` |
| Migration path | `docs/guides/knossos-migration.md` |
| Unsure where to start | `/consult` |
<!-- KNOSSOS:END getting-help -->

<!-- KNOSSOS:START state-management -->
## State Management

**Mutating session/sprint state?** Use the **Moirai** (the Fates) for all `SESSION_CONTEXT.md` and `SPRINT_CONTEXT.md` changes.

### Moirai Usage

Moirai is the unified session lifecycle agent embodying the three Fates: Clotho (creation), Lachesis (measurement), and Atropos (termination). It enforces schema validation, lifecycle transitions, and maintains audit trails. The Fates exist as internal skills loaded on-demand, not as separate agents.

**When to Use**:
- Updating session state (park, resume, wrap)
- Marking tasks complete
- Transitioning workflow phases
- Creating or managing sprints
- Any modification to `*_CONTEXT.md` files
- Generating White Sails confidence signals

**Invocation Pattern** (requires session context):
```
Task(moirai, "mark_complete task-001 artifact=docs/requirements/PRD-foo.md

Session Context:
- Session ID: {from session-manager.sh status}
- Session Path: .claude/sessions/{session-id}/SESSION_CONTEXT.md")
```

Get session context: `.claude/hooks/lib/session-manager.sh status | jq -r '.session_id'`

**Natural Language Supported**:
```
Task(moirai, "Mark the PRD task complete with artifact at docs/requirements/PRD-foo.md")
```

**Control Flags**:
- `--dry-run`: Preview changes without applying
- `--emergency`: Bypass non-critical validations (logged)
- `--override=reason`: Bypass lifecycle rules with explicit reason

**Direct writes blocked**: PreToolUse hook intercepts `Write`/`Edit` to `*_CONTEXT.md` and instructs use of Moirai.

**Full documentation**: See `.claude/agents/moirai.md` and `docs/philosophy/knossos-doctrine.md`
<!-- KNOSSOS:END state-management -->

<!-- KNOSSOS:START slash-commands -->
## Slash Commands

Always respond with outcome. "No response" is never correct for explicit user requests.
<!-- KNOSSOS:END slash-commands -->

<!-- KNOSSOS:START user-content -->
## Project-Specific Instructions

<!--
Add your project-specific Claude instructions here.
This section is preserved during re-materialization.

Examples:
- Project conventions and coding standards
- Important architectural decisions
- Team-specific workflows
- Links to key documentation

To add more custom sections:
  ari inscription add-region --name=my-section --owner=satellite
-->
<!-- KNOSSOS:END user-content -->