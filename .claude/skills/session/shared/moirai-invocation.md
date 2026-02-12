# Moirai Invocation Pattern

> Centralized session state mutation through the unified Moirai agent.

## Overview

**Moirai** is the unified session lifecycle agent and sole authority for `SESSION_CONTEXT.md` and `SPRINT_CONTEXT.md` mutations. All state transitions and context updates MUST go through this agent via the Task tool.

**Architecture**: Moirai embodies the three Fates as internal skills (not separate agents):
- **Clotho** (creation): `create_session`, `create_sprint`, `start_sprint`
- **Lachesis** (measurement): `mark_complete`, `transition_phase`, `park_session`, etc.
- **Atropos** (termination): `wrap_session`, `generate_sails`, `delete_sprint`

## Invocation Format

Short form is canonical. Pass the session ID from the hook-injected Session Context table when available.

```
Task(moirai, "{operation} {parameters}")
```

### Examples

```
Task(moirai, "create_session initiative='Add dark mode' complexity=MODULE")
Task(moirai, "park_session reason='Waiting for feedback' session_id=\"<session-id>\"")
Task(moirai, "resume_session session_id=\"<session-id>\"")
Task(moirai, "wrap_session session_id=\"<session-id>\"")
Task(moirai, "transition_phase to='implementation'")
Task(moirai, "update_field current_phase='implementation'")
Task(moirai, "create_sprint name='Sprint 1' goal='Core features' tasks='task1,task2'")
Task(moirai, "mark_complete task_id='task-1'")
Task(moirai, "handoff from=architect to=principal-engineer with notes: 'Design approved'")
```

**Note**: For `park_session`, `resume_session`, and `wrap_session`, extract the session ID from the hook-injected `| Session | session-xxx |` context table and pass it as `session_id=`. The CLI cannot discover sessions from Bash subprocesses without this.

## Expected Response

Moirai returns structured JSON:

```json
{
  "success": true,
  "operation": "park_session",
  "session_id": "session-20260106-123456-abc123",
  "state_before": "ACTIVE",
  "state_after": "PARKED",
  "timestamp": "2026-01-06T12:34:56Z"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| SESSION_NOT_FOUND | Invalid session ID |
| INVALID_STATE_TRANSITION | Illegal FSM transition |
| SCHEMA_VALIDATION_FAILED | Context update violates schema |
| FILE_WRITE_ERROR | Filesystem operation failed |

## Response Handling

1. Check `success` flag
2. On success: confirm to user with state transition details
3. On error: handle based on `error_code`

## Cross-References

- `agents/moirai.md` — Full Moirai agent specification
- `.claude/skills/session/moirai/` — Fate skills (INDEX.md, clotho.md, lachesis.md, atropos.md)
- `ari hook writeguard` — Direct write prevention
