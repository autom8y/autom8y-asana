---
name: start-ref
description: "Begin a new work session. Captures initiative, complexity, and team context. Creates SESSION_CONTEXT, invokes Requirements Analyst for PRD, optionally Architect for TDD. Triggers: /start, new session, begin work, kickoff, start session, initialize session."
---

# /start - Initialize New Work Session

> **Category**: Session Lifecycle | **Phase**: Session Initiation

## Purpose

Initialize a new work session by capturing the initiative, complexity level, and team context. Automatically creates a SESSION_CONTEXT file, invokes the Requirements Analyst to produce a PRD, and for complex work (MODULE+), engages the Architect for TDD planning.

This command establishes the foundation for a tracked, multi-phase workflow where context and decisions are preserved throughout the session lifecycle.

---

## Usage

```bash
/start [initiative-name] [--complexity=LEVEL] [--team=PACK]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `initiative-name` | No* | Prompted | Name of the feature, task, or initiative |
| `--complexity` | No* | Prompted | SCRIPT \| MODULE \| SERVICE \| PLATFORM |
| `--team` | No | ACTIVE_TEAM | Team pack to use for this session |

*If not provided, user will be prompted interactively.

---

## Behavior

When `/start` is invoked, the following sequence occurs:

### 1. Pre-flight Validation

- **Check for existing session**: Verify no active session for current project (uses `get_session_id()` from session-utils.sh)
  - If exists → Error: "Session already active. Use `/resume` or `/wrap` first"
- **Validate team pack** (if specified): Check team exists in roster
  - If invalid → Error: "Team '{name}' not found. Use `/roster` to list available teams"

### 2. Gather Session Parameters

Prompt user for any missing parameters:

- **Initiative name**: Clear, concise description (e.g., "Add dark mode toggle")
- **Complexity level**:
  - `SCRIPT` - Single file, < 200 LOC, no external dependencies
  - `MODULE` - Multiple files, < 2000 LOC, clear interfaces
  - `SERVICE` - Multiple modules, APIs, data persistence
  - `PLATFORM` - Multiple services, infrastructure, complex integration
- **Target team**: Defaults to current ACTIVE_TEAM (read from `.claude/ACTIVE_TEAM`)

### 3. Team Context Setup

- If `--team` specified and differs from ACTIVE_TEAM:
  - Invoke `~/Code/roster/swap-team.sh <team-name>` via Bash tool
  - Verify ACTIVE_TEAM file updated
  - Confirm: "Switched to {team} for this session"

### 4. Create SESSION_CONTEXT

Generate `.claude/sessions/{session_id}/SESSION_CONTEXT.md` file with metadata:

```yaml
---
session_id: "session-20251224-HHMMSS"
created_at: "2025-12-24THH:MM:SSZ"
initiative: "{user-provided-initiative}"
complexity: "{SCRIPT|MODULE|SERVICE|PLATFORM}"
active_team: "{team-pack-name}"
current_phase: "requirements"
last_agent: null
artifacts: []
blockers: []
next_steps:
  - "Review PRD when complete"
---

## Context

{One-line summary of initiative}

## Open Questions

(To be filled during workflow)

## Handoff Notes

(Added by /handoff command)
```

### 5. Invoke Requirements Analyst

Use Task tool to delegate to Requirements Analyst:

```markdown
Act as **Requirements Analyst**.

Initiative: {initiative-name}
Complexity: {complexity}

Create a PRD following the template at `.claude/skills/documentation/templates/prd.md`.

Clarify any ambiguities with the user before drafting. When complete, save to:
`/docs/requirements/PRD-{initiative-slug}.md`
```

Wait for analyst to produce PRD artifact.

### 6. Conditional Architect Invocation

If complexity is MODULE, SERVICE, or PLATFORM:

- Invoke **Architect** via Task tool:

```markdown
Act as **Architect**.

Initiative: {initiative-name}
PRD Location: /docs/requirements/PRD-{slug}.md

Create TDD following template at `.claude/skills/documentation/templates/tdd.md`.

Identify architecture decisions and create ADRs using template at `.claude/skills/documentation/templates/adr.md`.

When complete, save:
- TDD to: /docs/design/TDD-{slug}.md
- ADRs to: /docs/decisions/ADR-{NNNN}-{decision-slug}.md
```

### 7. Update SESSION_CONTEXT

After artifacts are produced, update `.claude/sessions/{session_id}/SESSION_CONTEXT.md`:

```yaml
artifacts:
  - type: "PRD"
    path: "/docs/requirements/PRD-{slug}.md"
    status: "approved"
  - type: "TDD"  # if complexity > SCRIPT
    path: "/docs/design/TDD-{slug}.md"
    status: "draft"
last_agent: "architect"  # or "analyst" if SCRIPT
current_phase: "design"  # or "requirements" if SCRIPT
next_steps:
  - "Review TDD-{slug}.md"
  - "Approve design decisions"
```

### 8. Confirmation

Display confirmation message:

```
Session started: {initiative-name}
Complexity: {complexity}
Team: {active_team}

Artifacts produced:
✓ PRD: /docs/requirements/PRD-{slug}.md
✓ TDD: /docs/design/TDD-{slug}.md  [if applicable]

Next steps:
- Review PRD and provide feedback
- Approve design before implementation

Use `/park` to pause, `/handoff` to switch agents, or continue working.
```

---

## State Changes

### Files Created

- `.claude/sessions/{session_id}/SESSION_CONTEXT.md` - Session metadata and state
- `/docs/requirements/PRD-{slug}.md` - Product requirements document
- `/docs/design/TDD-{slug}.md` - Technical design (if complexity > SCRIPT)
- `/docs/decisions/ADR-{NNNN}-{slug}.md` - Architecture decisions (if applicable)

### Fields Modified in SESSION_CONTEXT

| Field | Initial Value | Description |
|-------|---------------|-------------|
| `session_id` | Generated timestamp-based ID | Unique session identifier |
| `created_at` | Current ISO timestamp | Session start time |
| `initiative` | User-provided | Initiative name |
| `complexity` | User-provided | Complexity level |
| `active_team` | Current or specified team | Team pack for this session |
| `current_phase` | "requirements" or "design" | Current workflow phase |
| `last_agent` | "analyst" or "architect" | Last agent to work on session |
| `artifacts` | List of produced artifacts | Tracks deliverables |
| `next_steps` | Generated based on phase | What to do next |

---

## Examples

### Example 1: Simple Script

```bash
/start "Add retry logic to API client"
```

Interactive prompts:
```
Initiative: Add retry logic to API client
Complexity? [SCRIPT/MODULE/SERVICE/PLATFORM]: SCRIPT
Team? [current: 10x-dev-pack]: <Enter>

✓ Session started
✓ Requirements Analyst creating PRD...
✓ PRD saved: /docs/requirements/PRD-api-retry.md

Review PRD and use /handoff engineer when ready to implement.
```

### Example 2: Module with Team Switch

```bash
/start "Multi-tenant authentication" --complexity=MODULE --team=10x-dev-pack
```

Output:
```
Switching to team: 10x-dev-pack (5 agents loaded)

✓ Session started: Multi-tenant authentication
✓ Complexity: MODULE
✓ Requirements Analyst creating PRD...
✓ PRD approved: /docs/requirements/PRD-multi-tenant-auth.md
✓ Architect creating TDD...
✓ TDD draft: /docs/design/TDD-multi-tenant-auth.md
✓ ADR created: /docs/decisions/ADR-0042-jwt-token-strategy.md

Next: Review design documents and approve before implementation.
```

### Example 3: Platform Initiative

```bash
/start "Migrate to microservices architecture" --complexity=PLATFORM
```

Output:
```
⚠ PLATFORM complexity detected - this is a multi-session initiative.

✓ Session started: Migrate to microservices architecture
✓ Requirements Analyst scoping initiative...
✓ PRD saved: /docs/requirements/PRD-microservices-migration.md
✓ Architect creating TDD and ADRs...
✓ TDD saved: /docs/design/TDD-microservices-migration.md
✓ ADRs created:
  - ADR-0043-service-decomposition-strategy.md
  - ADR-0044-api-gateway-selection.md
  - ADR-0045-data-consistency-approach.md

Next: This initiative will require multiple sessions. Consider breaking into phases.
Use /park to save state between work periods.
```

---

## Prerequisites

- No existing active session for current project (uses file-based session persistence via `.claude/sessions/.current-session`)
- Target team pack exists (if specified)
- Roster system available at `~/Code/roster/`

---

## Success Criteria

- `.claude/sessions/{session_id}/SESSION_CONTEXT.md` file created with valid YAML
- Requirements Analyst produces PRD meeting quality gates
- Architect produces TDD and ADRs (if complexity > SCRIPT)
- All artifacts saved to correct locations
- User receives clear confirmation with next steps

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Session already active | Active session for current project | Use `/wrap` to complete current session or `/resume` to continue it |
| Invalid team name | Team not found in roster | Use `/roster` to list available teams |
| Roster system unavailable | `~/Code/roster/` not found | Set ROSTER_HOME environment variable or check installation |
| PRD creation failed | Analyst unable to produce PRD | Review error, provide more context, retry |
| Missing parameters | User cancels prompts | Command aborted, no state changed |

---

## Related Commands

- `/park` - Pause current session
- `/resume` - Continue parked session
- `/handoff` - Transfer to different agent
- `/wrap` - Complete and finalize session
- `/switch` - Change active team pack

---

## Related Skills

- [documentation](../documentation/SKILL.md) - PRD/TDD/ADR templates
- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination and handoffs
- [initiative-scoping](../initiative-scoping/SKILL.md) - Prompt -1/0 for complex initiatives

---

## Agent Delegation

This command uses the Task tool to invoke:

1. **Requirements Analyst** - Always (produces PRD)
2. **Architect** - Conditionally (if complexity > SCRIPT, produces TDD + ADRs)

No direct shell execution of agent files. All agent invocation happens via Claude Code's native Task tool.
