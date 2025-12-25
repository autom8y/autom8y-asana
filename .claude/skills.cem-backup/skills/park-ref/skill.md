---
name: park-ref
description: "Pause current work session and preserve state. Captures current progress, decisions, blockers. Saves to SESSION_CONTEXT for later resumption. Triggers: /park, pause session, save session, park work, suspend session, pause work."
---

# /park - Pause Current Work Session

> **Category**: Session Lifecycle | **Phase**: Session Suspension

## Purpose

Pause the current work session and preserve all state for later resumption. Captures current progress, decisions made, open questions, and blockers. Writes complete state to `.claude/SESSION_CONTEXT` with park metadata, enabling seamless continuation via `/resume`.

Use `/park` when:
- Taking a break between work periods
- Waiting for external input (design review, stakeholder feedback)
- Encountering blockers that require outside resolution
- Switching context to different work temporarily

---

## Usage

```bash
/park [reason]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `reason` | No | None | Optional explanation for why work is being paused |

---

## Behavior

When `/park` is invoked, the following sequence occurs:

### 1. Pre-flight Validation

- **Check for active session**: Verify `.claude/SESSION_CONTEXT` file exists
  - If missing → Error: "No active session to park. Use `/start` to begin a session"
- **Check if already parked**: Verify `parked_at` field not already set
  - If set → Error: "Session already parked at {timestamp}. Use `/resume` to continue"

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

Create a human-readable summary of session state at park time:

```markdown
## Parking Summary

**Parked**: 2025-12-24 15:30:00
**Reason**: {user-provided reason or "Manual park"}
**Duration so far**: {created_at → now}
**Current phase**: {requirements|design|implementation|validation}
**Last agent**: {agent-name}

### Progress

Artifacts completed:
- ✓ PRD: /docs/requirements/PRD-{slug}.md
- ✓ TDD: /docs/design/TDD-{slug}.md
- ⧗ Implementation: In progress

### State

Git status: {clean | N uncommitted files}
Blockers: {count} active
Open questions: {count} unresolved

### Next Steps on Resume

1. {first next step}
2. {second next step}
```

### 4. Update SESSION_CONTEXT

Add park metadata to SESSION_CONTEXT YAML frontmatter:

```yaml
---
# ... existing fields ...
parked_at: "2025-12-24T15:30:00Z"
parked_reason: "{user-provided or 'Manual park'}"
parked_phase: "{current_phase}"
parked_git_status: "{clean|dirty}"
parked_uncommitted_files: 3  # if applicable
---
```

Append parking summary to SESSION_CONTEXT body:

```markdown
---
{existing frontmatter with park fields added}
---

{existing context section}

---

## Parking Summary - 2025-12-24 15:30:00

{generated parking summary from step 3}

---

{rest of existing content}
```

### 5. Save SESSION_CONTEXT

Write updated SESSION_CONTEXT to `.claude/SESSION_CONTEXT` file.

### 6. Confirmation

Display confirmation message:

```
Session parked: {initiative-name}
Parked at: 2025-12-24 15:30:00
Reason: {reason}

Current state preserved:
✓ Phase: {current_phase}
✓ Last agent: {last_agent}
✓ Artifacts: {count} files
⚠ Uncommitted changes: {count} files [if applicable]

To resume: /resume
To view status: /status
```

---

## State Changes

### Fields Modified in SESSION_CONTEXT

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

## Examples

### Example 1: Simple Park

```bash
/park
```

Output:
```
Session parked: Add dark mode toggle
Parked at: 2025-12-24 15:30:00
Reason: Manual park

Current state preserved:
✓ Phase: design
✓ Last agent: architect
✓ Artifacts: 2 files (PRD, TDD)
✓ Git status: Clean

To resume: /resume
```

### Example 2: Park with Reason

```bash
/park "Waiting for design review from stakeholders"
```

Output:
```
Session parked: Multi-tenant authentication
Parked at: 2025-12-24 10:15:00
Reason: Waiting for design review from stakeholders

Current state preserved:
✓ Phase: design
✓ Last agent: architect
✓ Artifacts: 4 files (PRD, TDD, 2 ADRs)
✓ Git status: Clean
✓ Blockers: 1 (design review pending)

To resume: /resume
```

### Example 3: Park with Uncommitted Work

```bash
/park "End of day - implementation in progress"
```

Output:
```
Session parked: API retry logic
Parked at: 2025-12-24 17:45:00
Reason: End of day - implementation in progress

Current state preserved:
✓ Phase: implementation
✓ Last agent: engineer
✓ Artifacts: 3 files (PRD, code files)
⚠ Git status: Dirty (5 uncommitted files)
  - src/api/client.py (modified)
  - src/api/retry.py (new)
  - tests/test_retry.py (new)
  - src/config.py (modified)
  - README.md (modified)

⚠ Reminder: Commit or stash changes before resuming to avoid conflicts.

To resume: /resume
```

---

## Prerequisites

- Active session exists (`.claude/SESSION_CONTEXT` file present)
- Session not already parked (`parked_at` field not set)

---

## Success Criteria

- SESSION_CONTEXT updated with park metadata
- Parking summary appended to SESSION_CONTEXT
- User receives clear confirmation with resume instructions
- All current state preserved accurately

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No active session | `.claude/SESSION_CONTEXT` missing | Use `/start` to begin a new session |
| Already parked | `parked_at` field already set | Use `/resume` to continue, or check session status |
| File write error | Permission denied on SESSION_CONTEXT | Check file permissions, ensure not read-only |

---

## Related Commands

- `/start` - Begin new session
- `/resume` - Continue parked session
- `/status` - View current session state
- `/wrap` - Complete and finalize session

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Session lifecycle and phase transitions
- [documentation](../documentation/SKILL.md) - Understanding artifact states

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

This prevents accidental state corruption and encourages deliberate session management.
