# Session State Machine

> Lifecycle states and valid transitions for sessions.

## Overview

Sessions move through a simple state machine with three primary states: **Active**, **Parked**, and **Archived**. State transitions are triggered by session-lifecycle commands and enforced by the moirai agent.

## State Diagram

```
    /start
       │
       ▼
┌──────────────┐
│    ACTIVE    │◄─────┐
│              │      │
│ parked_at:   │      │
│   not set    │      │ /resume
└───┬──────┬───┘      │
    │      │          │
    │      │      ┌───┴──────┐
    │      └─────►│  PARKED  │
    │  /park      │          │
    │             │parked_at:│
    │             │   set    │
    │             └──────────┘
    │ /wrap
    │
    ▼
┌──────────────┐
│   ARCHIVED   │
│              │
│completed_at: │
│   set        │
└──────────────┘
    (terminal)
```

## State Definitions

### ACTIVE

**Description**: Work in progress, session available for agent work

**Indicators**:
- `parked_at` field NOT set
- `completed_at` field NOT set
- SESSION_CONTEXT file exists in `.sos/sessions/{session_id}/`

**Valid Commands**:
- /park - Pause work
- /wrap - Complete session
- /handoff - Switch agents

**Invalid Commands**:
- /start - Session already active
- /resume - Session not parked

---

### PARKED

**Description**: Work paused, session preserved for later resumption

**Indicators**:
- `parked_at` field SET
- `parked_reason` field SET
- `completed_at` field NOT set
- SESSION_CONTEXT file exists in `.sos/sessions/{session_id}/`

**Valid Commands**:
- /resume - Continue work

**Invalid Commands**:
- /start - Session already exists
- /park - Already parked
- /wrap - Must resume first (or wrap auto-resumes)
- /handoff - Must resume first

---

### ARCHIVED

**Description**: Session complete, moved to archive

**Indicators**:
- `completed_at` field SET
- SESSION_CONTEXT moved to archive location
- Session summary created in `/docs/sessions/`

**Valid Commands**:
- None (terminal state)

**Invalid Commands**:
- All session-lifecycle commands (session no longer active)

**Note**: Can view archived session via `ari session audit`

---

## State Transitions

### ACTIVE → PARKED

**Command**: `/park [reason]`

**Trigger**: User needs to pause work

**Pre-conditions**:
- Session in ACTIVE state
- No other session-lifecycle command in progress

**Actions**:
1. Capture current work state (git status, phase, artifacts)
2. Generate parking summary
3. Invoke moirai: `park_session reason='{reason}'`
4. moirai sets `parked_at`, `parked_reason`, `parked_phase`, etc.

**Post-conditions**:
- State → PARKED
- `parked_at` timestamp set
- Parking summary appended to SESSION_CONTEXT body

**Rollback**: If moirai fails, state remains ACTIVE (no mutation)

---

### PARKED → ACTIVE

**Command**: `/resume [--agent=NAME]`

**Trigger**: User ready to continue work

**Pre-conditions**:
- Session in PARKED state
- Target agent exists (if specified)

**Actions**:
1. Display session summary (how long parked, reason, state)
2. Validate rite/git consistency (warnings only)
3. Invoke moirai: `resume_session`
4. moirai removes `parked_*` fields, sets `resumed_at`
5. Invoke selected agent with full context

**Post-conditions**:
- State → ACTIVE
- `parked_at` and related fields REMOVED
- `resumed_at` timestamp set
- `resume_count` incremented

**Rollback**: If moirai fails, state remains PARKED

---

### ACTIVE → ARCHIVED

**Command**: `/wrap [--skip-checks] [--archive]`

**Trigger**: Session work complete

**Pre-conditions**:
- Session in ACTIVE state (or auto-resume from PARKED)
- Quality gates passing (unless --skip-checks)

**Actions**:
1. Run quality gate validation
2. Optionally offer QA review
3. Invoke moirai: `wrap_session`
4. moirai sets `completed_at`, generates summary
5. Move SESSION_CONTEXT to archive
6. Create session summary in `/docs/sessions/`
7. Update session index

**Post-conditions**:
- State → ARCHIVED
- `completed_at` timestamp set
- SESSION_CONTEXT moved from `.sos/sessions/` to archive
- Session summary created

**Rollback**: If moirai or archival fails, state remains ACTIVE

---

### Special Case: PARKED → ARCHIVED

**Command**: `/wrap` (auto-resume)

**Trigger**: User wraps a parked session

**Implementation**: Two-phase transition
1. Implicit `/resume` (PARKED → ACTIVE)
2. Immediate `/wrap` (ACTIVE → ARCHIVED)

**Note**: This is a convenience to avoid requiring explicit `/resume` before `/wrap`.

---

## State Enforcement

### Moirai Authority

All state transitions MUST go through `moirai` agent. Direct file writes are blocked by PreToolUse hook.

See: [Moirai Invocation Pattern](../shared/moirai-invocation.md)

### Validation Hooks

| Hook | Check | Action |
|------|-------|--------|
| PreToolUse | Edit/Write to SESSION_CONTEXT | Block, suggest moirai |
| SessionStart | Load session state | Display to user |
| PostToolUse | moirai response | Validate state transition |

### State Query

Get current session state:

```bash
ari session status | jq -r '.session_state'
# Returns: "active" | "parked" | "none"
```

## Invalid Transitions

These transitions are **not allowed**:

| From | To | Why |
|------|----|----|
| ACTIVE | ARCHIVED | Must run quality gates (/wrap) |
| PARKED | PARKED | Already parked (idempotency issue) |
| ARCHIVED | Any | Terminal state, immutable |
| None | PARKED | Can't park non-existent session |
| None | ARCHIVED | Can't archive non-existent session |

**Enforcement**: moirai returns error, PreToolUse blocks direct writes

## State Metadata

### ACTIVE State Fields

```yaml
created_at: "ISO 8601"
current_phase: "requirements | design | implementation | validation"
last_agent: "agent-name"
handoff_count: integer
# NO parked_* fields
# NO completed_at
```

### PARKED State Fields

```yaml
created_at: "ISO 8601"
current_phase: "..."
last_agent: "..."
# ACTIVE fields plus:
parked_at: "ISO 8601"
parked_reason: "string"
parked_phase: "phase at park time"
parked_git_status: "clean | dirty"
parked_uncommitted_files: integer (optional)
# NO completed_at
```

### ARCHIVED State Fields

```yaml
created_at: "ISO 8601"
current_phase: "final phase"
last_agent: "final agent"
# NO parked_* fields
completed_at: "ISO 8601"
quality_gates_passed: boolean
quality_gates_skipped: boolean (if --skip-checks)
```

## State Duration Tracking

### Park Duration

```bash
parked_at=$(yq e '.parked_at' SESSION_CONTEXT.md)
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
duration=$(calculate_duration "$parked_at" "$now")
```

### Session Duration

```bash
created_at=$(yq e '.created_at' SESSION_CONTEXT.md)
completed_at=$(yq e '.completed_at' SESSION_CONTEXT.md)
total_duration=$(calculate_duration "$created_at" "$completed_at")
```

**Note**: Session duration includes park time. For "active work time", subtract park durations.

## Error Handling

### State Transition Failures

If moirai returns error:

1. **Parse error message** and `error_type`
2. **Surface to user** with hint
3. **Preserve current state** (no partial mutations)
4. **Log failure** to session audit trail

Example error:
```json
{
  "success": false,
  "error_type": "LIFECYCLE_VIOLATION",
  "message": "Cannot park: session already parked",
  "hint": "Use /resume to continue or check /status"
}
```

### Concurrent Mutation Prevention

moirai uses atomic file writes to prevent race conditions. If multiple commands run concurrently, last-write-wins with warning.

**Best Practice**: One command at a time per session.

## Audit Trail

All state transitions logged in SESSION_CONTEXT body:

```markdown
---
**State Transition**: ACTIVE → PARKED
**Timestamp**: 2026-01-01T16:12:00Z
**Reason**: Waiting for design system update
---
```

This creates a full history of session lifecycle.

## Cross-References

- [Session Context Schema](session-context-schema.md) - Field definitions
- [Session Validation](session-validation.md) - Pre-flight checks
- [Moirai Invocation](../shared/moirai-invocation.md) - Mutation pattern
- ADR-0005-state-mate-centralized-state-authority.md - Design rationale
