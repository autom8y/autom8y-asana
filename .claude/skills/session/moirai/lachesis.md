# Lachesis - The Measurer

> What Clotho spins, Lachesis measures. Every transition is witnessed.

## mark_complete

Marks a sprint task as completed.

**Syntax**: `mark_complete task_id="{id}" [notes="{notes}"]`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| task_id | Yes | Task identifier |
| notes | No | Completion notes |

**Validation**:
1. Task must exist in active sprint
2. Task must not already be completed

**Execution**:
1. Update task status to "complete"
2. Record completion timestamp
3. Check if all tasks complete — if so, suggest sprint completion

**MOIRAI_BYPASS**: Required for SPRINT_CONTEXT.md write.

**Lock**: Required (context.lock).

---

## transition_phase

Transitions the session to a new workflow phase.

**Syntax**: `transition_phase to="{phase}"`

**CLI**: `ari session transition {phase}`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| to | Yes | Target phase name |

**Validation**:
1. Target phase must be valid for current workflow
2. Current phase must allow transition to target

**Execution**:
1. Call `ari session transition -s "{session_id}" {phase}` (omit `-s` if no session_id provided)
2. CLI handles lock acquisition and SESSION_CONTEXT.md mutation
3. Return CLI output

**MOIRAI_BYPASS**: Not needed (CLI handles).

**Lock**: CLI handles locking.

---

## update_field

Updates a field in SESSION_CONTEXT.md or SPRINT_CONTEXT.md.

**Syntax**: `update_field target="{session|sprint}" field="{name}" value="{value}"`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| target | Yes | Context file: session or sprint |
| field | Yes | Field name to update |
| value | Yes | New value |

**Read-only fields** (cannot be updated):
- schema_version
- session_id
- sprint_id
- created_at

**Validation**:
1. Field must not be read-only
2. Target context file must exist

**Execution**:
1. Read current context file
2. Validate field is writable
3. Update field value
4. Write context file

**MOIRAI_BYPASS**: Required for *_CONTEXT.md write.

**Lock**: Required (context.lock).

---

## park_session

Pauses the active session.

**Syntax**: `park_session reason="{reason}" [session_id="{id}"]`

**CLI**: `ari session park -s "{session_id}" --reason="{reason}"`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| reason | Yes | Reason for parking |
| session_id | No | Session ID (pass via `-s` flag to CLI) |

**Validation**:
1. Session must be ACTIVE
2. Reason must be non-empty

**Execution**:
1. Call `ari session park -s "{session_id}" --reason="{reason}"` (omit `-s` if no session_id provided)
2. CLI handles lock acquisition and SESSION_CONTEXT.md mutation
3. CLI updates session status to PARKED
4. CLI records park reason and timestamp
5. Return CLI output

**MOIRAI_BYPASS**: Not needed (CLI handles).

**Lock**: CLI handles locking.

---

## resume_session

Resumes a parked session.

**Syntax**: `resume_session [session_id="{id}"]`

**CLI**: `ari session resume -s "{session_id}"`

**Validation**:
1. Session must be PARKED

**Execution**:
1. Call `ari session resume -s "{session_id}"` (omit `-s` if no session_id provided)
2. CLI handles lock acquisition and SESSION_CONTEXT.md mutation
3. CLI updates session status to ACTIVE
4. CLI records resume timestamp
5. Return CLI output

**MOIRAI_BYPASS**: Not needed (CLI handles).

**Lock**: CLI handles locking.

---

## handoff

Records a handoff between agents.

**Syntax**: `handoff from="{agent}" to="{agent}" [context="{notes}"]`

**CLI**: `ari handoff execute --artifact={artifact} --to={agent}`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| from | Yes | Source agent name |
| to | Yes | Target agent name |
| context | No | Handoff notes |

**Validation**:
1. Session must be ACTIVE
2. Source and target agents must be valid

**Execution**:
1. Call `ari handoff execute --artifact={artifact} --to={agent}`
2. CLI handles lock acquisition and SESSION_CONTEXT.md mutation
3. CLI appends handoff record to session context
4. Return CLI output

**MOIRAI_BYPASS**: Not needed (CLI handles).

**Lock**: CLI handles locking.

---

## record_decision

Records an architectural or design decision.

**Syntax**: `record_decision title="{title}" rationale="{rationale}" [alternatives="{alt1,alt2}"]`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| title | Yes | Decision title |
| rationale | Yes | Reason for decision |
| alternatives | No | Comma-separated alternatives considered |

**Execution**:
1. Append decision to session decisions list
2. Record timestamp and current phase

**MOIRAI_BYPASS**: Required for SESSION_CONTEXT.md write.

**Lock**: Required (context.lock).

---

## append_content

Appends content to a named section of the session context.

**Syntax**: `append_content section="{name}" content="{text}"`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| section | Yes | Section name in context file |
| content | Yes | Content to append |

**Validation**:
1. Section must exist in context file
2. Content must be non-empty

**Execution**:
1. Read current context file
2. Locate section
3. Append content
4. Write context file

**MOIRAI_BYPASS**: Required for SESSION_CONTEXT.md write.

**Lock**: Required (context.lock).
