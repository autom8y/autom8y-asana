---
user-invocable: false
---

# /park Behavior Specification

> Full step-by-step sequence for pausing a work session.

## Behavior Sequence

### 1. Pre-flight Validation

Apply [Session Resolution Pattern](../shared/session-resolution.md):
- Requires: Active session (not parked)
- Verb: "park"

See [session-validation](../common/session-validation.md) for validation patterns.

### 2. Capture Current Work State

Gather current session state:

- **Git status**: Run `git status` to detect uncommitted changes
  - If uncommitted work → Add warning to park notes
- **Current phase**: Record from SESSION_CONTEXT `current_phase` field
- **Last agent**: Record from SESSION_CONTEXT `last_agent` field
- **Artifacts produced**: List from SESSION_CONTEXT `artifacts` array
- **Open questions**: Extract from SESSION_CONTEXT content
- **Blockers**: Extract from SESSION_CONTEXT `blockers` array

### 3. Generate Parking Summary

Create a human-readable summary of session state at park time.
See [parking-summary.md](parking-summary.md) for template.

### 4. Invoke Moirai for Park Mutation

Session parking is managed via the Moirai (Lachesis - the Measurer):

```
Task(moirai, "park_session reason=\"{user_reason}\" session_id=\"{session_id}\"")
```

The Moirai will route to **Lachesis** (the Measurer), who will:
- Set session state metadata (parked_at, parked_reason, parked_phase, parked_git_status)
- Preserve session for later resume
- Validate lifecycle transition is legal

**Note**: `moirai` is the current agent name (formerly state-mate).

See [Moirai Invocation Pattern](../shared/moirai-invocation.md) for response handling and error types.

### 5. Confirm Result

Parse Moirai JSON response and display confirmation to user.
Do NOT attempt direct file writes--Moirai (via Lachesis) handles all mutations.

### 6. Confirmation

Display confirmation message with:
- Session name and park timestamp
- Reason for parking
- State summary (phase, agent, artifacts)
- Git status warning if dirty
- Resume instructions

---

## State Changes

### Fields Modified

| Field | Value | Description |
|-------|-------|-------------|
| `parked_at` | ISO 8601 timestamp | When session was parked |
| `parked_reason` | User-provided string or "Manual park" | Why work was paused |
| `parked_phase` | Current phase value | Phase at park time |
| `parked_git_status` | "clean" or "dirty" | Git working directory state |
| `parked_uncommitted_files` | Integer (if dirty) | Count of uncommitted files |

### Content Additions

- Parking summary appended to SESSION_CONTEXT body
- Preserves all existing content and metadata

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No active session | No session for current project | Use `/start` to begin a new session |
| Already parked | `parked_at` field already set | Use `/resume` to continue, or check session status |
| File write error | Permission denied on SESSION_CONTEXT | Check file permissions, ensure not read-only |

---

## Design Notes

### Why Preserve Git Status?

Git status at park time helps detect:
1. **Stale work**: If files changed outside the session
2. **Incomplete work**: If work was paused mid-implementation
3. **Merge conflicts**: If branch diverged during park period

This enables `/resume` to warn about potential issues before continuing.

### Why Append vs Overwrite?

Parking summaries are appended (not overwriting) to create an audit trail. Multiple park/resume cycles preserve the full session history, making it easier to understand context when resuming days or weeks later.

### Idempotency

Parking an already-parked session is an error (not idempotent) because:
1. It indicates user confusion about session state
2. Multiple park timestamps would create ambiguity
3. `/status` should be used to check state first
