# Clotho - The Spinner

> What is spun cannot be unspun. Every session begins with Clotho's thread.

## create_session

Creates a new session.

**Syntax**: `create_session initiative="{initiative}" [complexity="{level}"] [rite="{rite}"]`

**CLI**: `ari session create "{initiative}" -c "{complexity}" [-r "{rite}"]`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| initiative | Yes | What is being built |
| complexity | No | PATCH|MODULE|SYSTEM|INITIATIVE|MIGRATION (default: MODULE) |
| rite | No | Rite to use (default: current) |

**Validation**:
1. No other session currently ACTIVE
2. Initiative must be non-empty

**Execution**:
1. Call `ari session create "{initiative}" -c "{complexity}" [-r "{rite}"]`
2. CLI creates session directory, SESSION_CONTEXT.md, sets state to ACTIVE
3. Return CLI output (JSON with session_id, entry_agent)

**MOIRAI_BYPASS**: Not needed (CLI handles).

**Lock**: CLI handles locking.

---

## create_sprint

Creates a new sprint within the active session.

**Syntax**: `create_sprint name="{name}" goal="{goal}" [tasks="task1,task2,..."]`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| name | Yes | Sprint name |
| goal | Yes | Sprint objective |
| tasks | No | Comma-separated initial task list |

**Validation**:
1. Active session must exist
2. No other sprint currently ACTIVE in this session
3. Sprint name must be non-empty
4. Session must be in ACTIVE state

**Execution**:
1. Generate sprint ID: `sprint-{date}-{slug}`
2. Create SPRINT_CONTEXT.md in session directory
3. Write initial sprint YAML with status: "ACTIVE"
4. Return success response with sprint ID

**MOIRAI_BYPASS**: Required for SPRINT_CONTEXT.md write.

**Lock**: Required (context.lock).

---

## start_sprint

Transitions a pending sprint to active.

**Syntax**: `start_sprint sprint_id="{id}"`

**Parameters**:
| Parameter | Required | Description |
|-----------|----------|-------------|
| sprint_id | Yes | Sprint identifier |

**Validation**:
1. Sprint must exist
2. Sprint must be in pending status
3. Session must be ACTIVE

**Execution**:
1. Update sprint status to ACTIVE
2. Record start timestamp
3. Return success response

**MOIRAI_BYPASS**: Required for SPRINT_CONTEXT.md write.

**Lock**: Required (context.lock).
