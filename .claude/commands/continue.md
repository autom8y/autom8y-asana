---
name: continue
description: Resume a parked work session with full context
argument-hint:
allowed-tools: Bash, Read, Task
disallowed-tools: Write, Edit, NotebookEdit
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Resume a parked work session with full context restoration. $ARGUMENTS

## Session Resolution

**CRITICAL**: Extract the session ID from the hook-injected Session Context table above.
Look for: `| Session | <session-id> |`. The CLI cannot discover the session automatically
from a Bash subprocess — you MUST pass the session ID explicitly to Moirai.

If no Session Context table is present (no hook output), fall back to scan:
`ari session status` to find PARKED sessions.

## Pre-flight

1. Verify a parked session exists (check Session Context table or `ari session status`)
2. Load session context from `SESSION_CONTEXT.md`

## Behavior

1. **Delegate to Moirai** for session state mutation:
   ```
   Task(moirai, "resume_session session_id=\"<session-id>\"")
   ```
   Moirai will:
   - Acquire lock to prevent race conditions
   - Validate FSM allows PARKED -> ACTIVE transition
   - Execute `ari session resume`
   - Update session state (status, resumed_at, clear parked_at/reason)
   - Validate the result and log to audit trail
   - Return structured response

2. **Display resumption summary** based on Moirai's response:
   ```json
   {
     "session_id": "session-20251224-143052-a1b2c3d4",
     "status": "ACTIVE",
     "previous_status": "PARKED",
     "resumed_at": "2025-01-07T10:30:00Z"
   }
   ```

## Error Conditions

- **No parked session**: Fails if no session in PARKED status found
- **Session not found**: Fails if session directory doesn't exist
- **Invalid transition**: Fails if session is not in PARKED status (e.g., already ACTIVE or WRAPPED)
- **Lock contention**: Fails if another process holds the session lock

## Example

```
/continue
```

