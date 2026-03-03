---
user-invocable: false
---

# /continue Behavior Specification

> Full step-by-step sequence for resuming a parked work session.

## Behavior Sequence

### 1. Pre-flight Validation

Apply [Session Resolution Pattern](../shared/session-resolution.md):
- Requires: Parked session
- Verb: "resume"

See [session-validation](../../session-common/session-validation.md) for validation patterns.

### 2. Load and Display Session Summary

Read SESSION_CONTEXT and display:
- Session details (started, parked, reason, complexity, rite, phase, agent)
- Artifacts produced
- Blockers and open questions
- Next steps from park time

### 3. Validate Context

Apply [Workflow Resolution Pattern](../shared/workflow-resolution.md):
- Rite consistency: Compare ACTIVE_RITE to session.active_rite
- Allow override: Yes (user can continue with different rite)

See [validation-checks.md](validation-checks.md) for details.

**Git Status Check**: Compare current status to `parked_git_status`
- If new changes: Surface and offer to review diff

### 4. Agent Selection

Apply [Workflow Resolution Pattern](../shared/workflow-resolution.md):
- Target agent: Default to `last_agent` or override with `--agent=NAME`
- Validate agent exists in current rite

### 5. Invoke Moirai for Resume Mutation

Apply [Moirai Invocation Pattern](../shared/moirai-invocation.md):
- Operation: `resume_session`
- Post-action: Invoke selected agent with full session context

See pattern documentation for response handling and error types.

### 6. Update Agent Selection (Post-Resume)

After successful resume, if agent override was specified, invoke:

```
Task(moirai, "update_field last_agent='{selected_agent}'

Session Context:
- Session ID: {session_id}
- Session Path: .sos/sessions/{session_id}/SESSION_CONTEXT.md")
```

### 7. Invoke Selected Agent

Use Task tool to invoke agent with full session context:
- Initiative, complexity, phase
- Park duration and reason
- Artifacts, blockers, questions
- Next steps

### 8. Confirmation

Display:
- Session name and park duration
- Selected agent and phase
- First item from next steps
- Available commands

---

## State Changes

### Fields Modified

| Field | Action | Description |
|-------|--------|-------------|
| `parked_at` | REMOVED | Park timestamp deleted |
| `parked_reason` | REMOVED | Park reason deleted |
| `parked_phase` | REMOVED | Phase at park time deleted |
| `parked_git_status` | REMOVED | Git status deleted |
| `parked_uncommitted_files` | REMOVED | File count deleted |
| `resumed_at` | ADDED | Resume timestamp |
| `resume_count` | ADDED | Park/resume cycle count |
| `last_agent` | UPDATED | Agent selected for resume |

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No parked session | No session for project | Use `/start` to begin new session |
| Session not parked | `parked_at` not set | Session is active, continue working |
| Invalid agent | Agent not in rite | Specify valid agent or switch rites |
| Rite unavailable | Session rite not in knossos | Install rite or choose different |
| Merge conflicts | Git detects conflicts | Resolve conflicts before resuming |

---

## Design Notes

### Why Allow Agent Override?

Session phases evolve. A session parked during design (last_agent: architect) may be ready for implementation when resumed. `--agent` override supports natural phase transitions without separate `/handoff`.

### Resume Count Tracking

`resume_count` helps identify:
1. Frequently interrupted sessions (potential issues)
2. Sessions needing smaller scope
3. External dependencies causing delays
