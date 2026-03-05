---
user-invocable: false
---

# /start Behavior Specification

> Full step-by-step sequence for initializing a work session.

## Behavior Sequence

### 1. Pre-flight Validation

Apply [Session Resolution Pattern](../shared/session-resolution.md) (inverse):
- Requires: NO existing session
- Error if session exists: "Session already active. Use `/resume` or `/wrap` first"

Apply [Workflow Resolution Pattern](../shared/workflow-resolution.md):
- Target rite: User-specified or current ACTIVE_RITE
- Validate rite exists in knossos

See [session-validation](../common/session-validation.md) for validation patterns.

### 2. Gather Session Parameters

Prompt user for any missing parameters:

- **Initiative name**: Clear, concise description (e.g., "Add dark mode toggle")
- **Complexity level**:
  - `PATCH` - Single file, < 200 LOC, no external dependencies
  - `MODULE` - Multiple files, < 2000 LOC, clear interfaces
  - `SYSTEM` - Multiple modules, APIs, data persistence
  - `INITIATIVE` - Multiple services, infrastructure, complex integration
  - `MIGRATION` - Cross-cutting migrations, large-scale refactors
- **Target rite**: Defaults to current ACTIVE_RITE (read from `.knossos/ACTIVE_RITE`)

### 3. Rite Context Setup

- If `--rite` specified and differs from ACTIVE_RITE:
  - Run `ari sync --rite <rite-name>`
  - Verify ACTIVE_RITE file updated
  - Confirm: "Switched to {rite} for this session"

### 4. Create SESSION_CONTEXT via Moirai

Delegate session creation to the Moirai (Clotho - the Spinner) via Task tool:

```
Task(moirai, "create_session initiative='{user-initiative}' complexity={COMPLEXITY} rite={rite-name}

Session Context:
- New session requested
- Initiative: {user-provided-initiative}
- Complexity: {PATCH|MODULE|SYSTEM|INITIATIVE|MIGRATION}
- Rite: {rite-name}
- Phase: requirements")
```

Clotho will:
- Generate session ID with timestamp
- Create `.sos/sessions/{session_id}/SESSION_CONTEXT.md`
- Initialize session state with proper schema
- Set initial phase to "requirements"
- Return confirmation with session details

**Why Moirai?**
- Enforces schema validation
- Manages lifecycle transitions
- Maintains audit trail
- Ensures atomic state changes
- Prevents malformed session files

See [session-context-schema](../common/session-context-schema.md) for field definitions.

### 5. Invoke Requirements Analyst

Use Task tool to delegate to Requirements Analyst. See [integration.md](integration.md) for delegation template.

Wait for analyst to produce PRD artifact.

### 6. Conditional Architect Invocation

If complexity is MODULE, SYSTEM, INITIATIVE, or MIGRATION:
- Invoke **Architect** via Task tool
- Architect produces TDD and ADRs

See [integration.md](integration.md) for delegation template.

### 7. Update SESSION_CONTEXT via Moirai

After artifacts are produced, delegate to Moirai (Lachesis - the Measurer) to update session state:

```
Task(moirai, "update_session session_id={session-id}
  artifacts=[
    {type: PRD, path: .ledge/specs/PRD-{slug}.md, status: approved},
    {type: TDD, path: .ledge/specs/TDD-{slug}.md, status: draft}
  ]
  last_agent={architect|analyst}
  current_phase={design|requirements}

Session Context:
- Session ID: {session-id}
- Artifacts produced: PRD{, TDD}
- Phase transition: requirements → design
- Last agent: {architect|analyst}")
```

Lachesis will:
- Validate artifact paths exist
- Update artifacts list in SESSION_CONTEXT
- Transition phase if appropriate
- Record last active agent
- Maintain audit trail

**Never use Write/Edit directly** on SESSION_CONTEXT.md. All mutations go through Moirai.

### 8. Confirmation

Display confirmation message with:
- Session name, complexity, rite
- Artifacts produced (PRD, TDD, ADRs)
- Next steps
- Available commands (/park, /handoff, etc.)

---

## State Changes

### Files Created

**Via Moirai delegation**:
- `.sos/sessions/{session_id}/SESSION_CONTEXT.md` - Session metadata and state (created by Clotho)

**Via agent delegation**:
- `.ledge/specs/PRD-{slug}.md` - Product requirements document (Requirements Analyst)
- `.ledge/specs/TDD-{slug}.md` - Technical design (Architect, if complexity > PATCH)
- `.ledge/decisions/ADR-{NNNN}-{slug}.md` - Architecture decisions (Architect, if applicable)

### Fields Set in SESSION_CONTEXT (by Moirai)

| Field | Initial Value | Description |
|-------|---------------|-------------|
| `session_id` | Generated timestamp-based ID | Unique session identifier |
| `created_at` | Current ISO timestamp | Session start time |
| `initiative` | User-provided | Initiative name |
| `complexity` | User-provided | Complexity level |
| `active_rite` | Current or specified rite | Rite for this session |
| `current_phase` | "requirements" or "design" | Current workflow phase |
| `last_agent` | "analyst" or "architect" | Last agent to work on session |
| `artifacts` | List of produced artifacts | Tracks deliverables |

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Session already active | Active session for current project | Use `/wrap` to complete current session or `/resume` to continue it |
| Invalid rite name | Rite not found in knossos | Use `/rite` to list available rites |
| Knossos system unavailable | `$KNOSSOS_HOME/` not found | Set KNOSSOS_HOME environment variable or check installation |
| PRD creation failed | Analyst unable to produce PRD | Review error, provide more context, retry |
| Missing parameters | User cancels prompts | Command aborted, no state changed |
