---
name: sos
description: Unified session state interface — Save Our Session
argument-hint: "[subcommand] [args...] or natural language"
allowed-tools: Bash, Read, Task
disallowed-tools: Write, Edit, NotebookEdit
model: opus
---

## Pre-computed Context

The SessionStart hook has already injected session state as YAML frontmatter above. Key fields:
- `has_session:` — whether a session exists
- `session_id:` — current session ID
- `status:` — ACTIVE, PARKED, or ARCHIVED
- `complexity:` — PATCH, MODULE, SYSTEM, INITIATIVE, MIGRATION
- `active_rite:` — current rite name

## Your Task

$ARGUMENTS

## Routing

Parse $ARGUMENTS to determine the operation. If empty, default to **status** mode.

### Subcommand Table

| Input Pattern | Operation | Requires Session |
|---------------|-----------|-----------------|
| (empty) | Status + triage | No |
| `park "reason"` | Park session | Yes (ACTIVE) |
| `resume` | Resume parked session | Yes (PARKED) |
| `start "initiative" [--complexity=X]` | Lightweight start | No |
| `wrap [--force]` | Archive session | Yes |
| Any other text | Natural language routing | Varies |

### Decision Flow

1. **Extract first word** from $ARGUMENTS
2. **If it matches a subcommand** (park, resume, start, wrap): route directly
3. **If no match**: treat entire input as natural language. Load routing spec:
   `Read("mena/session/sos/behavior.md")`
4. **If empty**: run status + triage mode (see below)

### Session ID Protocol

**CRITICAL**: Extract `session_id` from the hook-injected YAML frontmatter above.
You MUST pass this to Moirai — the CLI cannot discover the session from a Bash subprocess.

For operations that do NOT require an existing session:
- start: creates a new session
- status: reads from context, gracefully handles `has_session: false`

### Status + Triage (no arguments)

When /sos is invoked with no arguments:

1. If `has_session: false`: display "No active session" and run `ari session query` for recent sessions
2. If `status: ACTIVE`: show initiative, phase, complexity. Suggest: `/sos park`, `/handoff`, or `/fray`
3. If `status: PARKED`: show initiative, park reason. Suggest: `/sos resume` or `/sos wrap`

### Operation Dispatch

For each matched subcommand, load the detailed specification:
`Read("mena/session/sos/subcommands.md")`

Then execute using the operation's dispatch pattern.

### Dispatch Modes

**Via Task(moirai)** — state-mutating operations:
- park: `Task(moirai, "park_session reason=\"{reason}\" session_id=\"{id}\"")`
- resume: `Task(moirai, "resume_session session_id=\"{id}\"")`
- start: `Task(moirai, "create_session initiative='{initiative}' complexity={complexity}")`
- wrap: `Task(moirai, "wrap_session session_id=\"{id}\"")`

**Via Bash** — direct CLI operations:
- status: `ari session query`

## Sigils

### On Success

| Operation | Sigil |
|-----------|-------|
| status | (no sigil — informational) |
| park | `(parked) next: /sos resume (when ready)` |
| resume | `(resumed) next: /go` |
| start | `(started) next: start working` |
| wrap | `(wrapped) next: /land (for synthesis) or /sos start (new work)` |

### On Failure

`sos failed: {brief reason} — fix: {recovery}`
