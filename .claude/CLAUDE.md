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
| **Ariadne** | CLI binary (`ari`) | The clew ensuring return |
| **Theseus** | Claude Code agent | The navigator with amnesia |
| **Moirai** | Session lifecycle agent | The Fates who spin, measure, and cut |
| **White Sails** | Confidence signal | Honest return indicator |
| **Rites** | Practice bundles | Invokable ceremonies |

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

The `ari` binary provides session and hook operations:

```bash
# Session management
ari session create "initiative" COMPLEXITY
ari session status
ari session park "reason"

# Hook operations
ari hook clew
ari hook context

# Quality gates
ari sails check

# Agent handoffs
ari handoff prepare --from <agent> --to <agent>
ari handoff execute --from <agent> --to <agent>
ari handoff status
ari handoff history
```

### Cognitive Budget

Tool usage tracking with configurable thresholds:
- `ARIADNE_MSG_WARN=250` - Warning threshold (default)
- `ARIADNE_MSG_PARK` - Park suggestion threshold
- `ARIADNE_BUDGET_DISABLE=1` - Disable tracking

Build: `cd ariadne && just build`

Full reference: `docs/guides/knossos-integration.md`
<!-- KNOSSOS:END ariadne-cli -->

<!-- KNOSSOS:START getting-help -->
## Getting Help

| Question | Command |
|----------|---------|
| Invoke agents | `prompting` |
| Conventions | `standards` |
| Workflow coordination | `orchestration` |
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