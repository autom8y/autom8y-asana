# SESSION_CONTEXT Schema

> Field definitions for `.claude/sessions/{session_id}/SESSION_CONTEXT.md`

## Overview

SESSION_CONTEXT is a YAML-frontmatter Markdown file that stores session metadata and state. The frontmatter contains structured fields, while the body contains human-readable notes, parking summaries, and handoff notes.

## File Structure

```markdown
---
{YAML frontmatter fields}
---

# Session: {initiative}

{Markdown body content}
```

## Frontmatter Schema

### Core Identity

| Field | Type | Required | Set By | Description |
|-------|------|----------|--------|-------------|
| `session_id` | string | Yes | /start | Unique identifier: `session-YYYYMMDD-HHMMSS` |
| `created_at` | ISO 8601 | Yes | /start | Session creation timestamp |
| `initiative` | string | Yes | /start | User-provided initiative name |
| `complexity` | enum | Yes | /start | SCRIPT \| MODULE \| SERVICE \| PLATFORM |
| `context_version` | string | Yes | /start | Schema version (currently "1.0") |

### Workflow State

| Field | Type | Required | Set By | Description |
|-------|------|----------|--------|-------------|
| `active_rite` | string | Yes | /start | Rite name (e.g., "10x-dev") |
| `current_phase` | enum | Yes | /start | requirements \| design \| implementation \| validation |
| `last_agent` | string | No | Agent invocations | Last agent to work on session |
| `handoff_count` | integer | No | /handoff | Number of agent handoffs |
| `last_handoff_at` | ISO 8601 | No | /handoff | Timestamp of last handoff |

### Artifacts & Deliverables

| Field | Type | Required | Set By | Description |
|-------|------|----------|--------|-------------|
| `artifacts` | array | Yes | Agents | List of produced artifacts (see Artifact Schema below) |
| `blockers` | array | Yes | Any | Current blockers (see Blocker Schema below) |
| `next_steps` | array | Yes | Any | Action items for next work session |

### Park/Resume State

| Field | Type | Required | Set By | Description |
|-------|------|----------|--------|-------------|
| `parked_at` | ISO 8601 | No | /park | When session was parked |
| `parked_reason` | string | No | /park | Why work was paused |
| `parked_phase` | enum | No | /park | Phase at park time |
| `parked_git_status` | enum | No | /park | clean \| dirty |
| `parked_uncommitted_files` | integer | No | /park | Count of uncommitted files |
| `resumed_at` | ISO 8601 | No | /resume | When session was last resumed |
| `resume_count` | integer | No | /resume | Number of park/resume cycles |

### Completion State

| Field | Type | Required | Set By | Description |
|-------|------|----------|--------|-------------|
| `completed_at` | ISO 8601 | No | /wrap | When session was wrapped |
| `quality_gates_passed` | boolean | No | /wrap | Whether quality gates passed |
| `quality_gates_skipped` | boolean | No | /wrap | Whether --skip-checks was used |

## Artifact Schema

Each entry in `artifacts` array:

```yaml
- type: "PRD" | "TDD" | "ADR" | "Test-Plan" | "Code"
  path: "/docs/requirements/PRD-{slug}.md"
  status: "draft" | "approved" | "implemented" | "validated"
  created_at: "ISO 8601 timestamp"
```

## Blocker Schema

Each entry in `blockers` array:

```yaml
- description: "Brief blocker description"
  type: "technical" | "external" | "decision" | "clarification"
  created_at: "ISO 8601 timestamp"
  resolved_at: "ISO 8601 timestamp" (optional)
```

## Complexity Levels

| Level | Scope | Artifacts | Typical Duration |
|-------|-------|-----------|------------------|
| SCRIPT | < 200 LOC, single file | PRD only | Hours |
| MODULE | < 2000 LOC, multiple files | PRD, TDD, ADRs | Days |
| SERVICE | APIs, persistence, multiple modules | PRD, TDD, ADRs, Test Plan | Weeks |
| PLATFORM | Multiple services, infrastructure | PRD, TDD, ADRs, Migration Plan | Months (multi-session) |

## Phase Transitions

| Phase | Valid Next Phases | Trigger |
|-------|-------------------|---------|
| requirements | design, implementation | Analyst → Architect or Engineer |
| design | implementation | Architect → Engineer |
| implementation | validation, requirements | Engineer → QA or Analyst (iteration) |
| validation | requirements (iteration), complete | QA → Wrap or Analyst |

See [session-phases](session-phases.md) for detailed transition rules.

## State Machine

Session can be in one of these states:

- **Active** - `parked_at` not set, work in progress
- **Parked** - `parked_at` set, work paused
- **Archived** - `completed_at` set, session complete

See [session-state-machine](session-state-machine.md) for transition diagram.

## Validation Rules

1. **Required fields**: All fields marked "Required: Yes" must be present
2. **Enum values**: Must match exactly (case-sensitive)
3. **ISO 8601**: All timestamps in UTC: `YYYY-MM-DDTHH:MM:SSZ`
4. **Arrays**: Can be empty `[]` but must exist
5. **Park fields**: All `parked_*` fields set together or none
6. **Phases**: Must follow valid transition paths

## Example: Minimal SESSION_CONTEXT

```yaml
---
session_id: "session-20260101-143022"
created_at: "2026-01-01T14:30:22Z"
initiative: "Add dark mode toggle"
complexity: "MODULE"
active_rite: "10x-dev"
current_phase: "requirements"
last_agent: "requirements-analyst"
artifacts:
  - type: "PRD"
    path: "/docs/requirements/PRD-dark-mode.md"
    status: "approved"
    created_at: "2026-01-01T14:35:12Z"
blockers: []
next_steps:
  - "Review PRD with stakeholders"
  - "Begin technical design"
context_version: "1.0"
---

# Session: Add dark mode toggle

## Artifacts
- PRD: /docs/requirements/PRD-dark-mode.md (approved)

## Blockers
None yet.

## Next Steps
1. Review PRD with stakeholders
2. Begin technical design
```

## Example: Parked SESSION_CONTEXT

```yaml
---
session_id: "session-20260101-143022"
created_at: "2026-01-01T14:30:22Z"
initiative: "Add dark mode toggle"
complexity: "MODULE"
active_rite: "10x-dev"
current_phase: "implementation"
last_agent: "principal-engineer"
artifacts:
  - type: "PRD"
    path: "/docs/requirements/PRD-dark-mode.md"
    status: "approved"
    created_at: "2026-01-01T14:35:12Z"
  - type: "TDD"
    path: "/docs/design/TDD-dark-mode.md"
    status: "approved"
    created_at: "2026-01-01T15:22:45Z"
blockers:
  - description: "Waiting for design system color tokens"
    type: "external"
    created_at: "2026-01-01T16:10:33Z"
next_steps:
  - "Resume implementation when tokens available"
parked_at: "2026-01-01T16:12:00Z"
parked_reason: "Waiting for design system update"
parked_phase: "implementation"
parked_git_status: "dirty"
parked_uncommitted_files: 3
context_version: "1.0"
---

# Session: Add dark mode toggle

## Artifacts
- PRD: /docs/requirements/PRD-dark-mode.md (approved)
- TDD: /docs/design/TDD-dark-mode.md (approved)

## Blockers
- **[External]** Waiting for design system color tokens (created 2026-01-01T16:10:33Z)

## Next Steps
1. Resume implementation when tokens available

---

**Parked**: 2026-01-01T16:12:00Z
**Reason**: Waiting for design system update
**Git Status**: Dirty (3 uncommitted files)
```

## Mutation Authority

**CRITICAL**: All SESSION_CONTEXT modifications MUST go through `moirai` agent.

Direct writes via Edit/Write tools are **blocked** by the PreToolUse hook. See:
- [Moirai invocation pattern](../shared/moirai-invocation.md)
- ADR-0005-state-mate-centralized-state-authority.md

## Cross-References

- [Session Phases](session-phases.md) - Phase transition rules
- [Session State Machine](session-state-machine.md) - Lifecycle states
- [Complexity Levels](complexity-levels.md) - Detailed complexity guide
- [Validation Patterns](session-validation.md) - Pre-flight checks
