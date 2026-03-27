---
name: naxos
description: "Session hygiene triage. Scans for orphaned sessions, triages by severity, recommends actions."
argument-hint: "[--severity=LEVEL] [session-id]"
allowed-tools: Bash, Read, Task
disallowed-tools: Write, Edit, NotebookEdit
model: opus
---

## Pre-computed Context

The SessionStart hook has already injected session state as YAML frontmatter above. Key fields:
- `has_session:` -- whether a session exists
- `session_id:` -- current session ID
- `naxos_summary:` -- pre-computed orphan summary (if present)

If `naxos_summary` is present in the frontmatter, reference it when presenting context to the user or the Naxos agent.

## Pre-flight: Naxos Availability

Check if naxos is currently available:
1. Run `ls ~/.claude/agents/naxos.md 2>/dev/null` via Bash
2. If file exists: proceed to Routing
3. If file missing:
   a. Run `ari agent summon naxos` via Bash
   b. Tell user: "Naxos summoned. Restart CC to activate, then re-run /naxos."
   c. STOP — do not attempt Agent("naxos") until restart

## Your Task

$ARGUMENTS

## Routing

Parse $ARGUMENTS to determine the operation scope. If empty, default to **full triage** mode.

### Input Patterns

| Input Pattern | Operation | Description |
|---------------|-----------|-------------|
| (empty) | Full triage via Naxos agent | Scan all sessions, triage all orphans |
| `--severity=CRITICAL` | Filtered triage | Triage only entries at specified severity level |
| `--severity=HIGH` | Filtered triage | Triage only entries at HIGH or above |
| `session-xxx` | Focused triage | Assess a specific session by ID |

### Decision Flow

1. **Extract** `session_id` from the hook-injected YAML frontmatter above
2. **Parse** $ARGUMENTS for severity filters or specific session IDs
3. **Dispatch** to Naxos agent with extracted parameters

### Session ID Protocol

**CRITICAL**: Extract `session_id` from the hook-injected YAML frontmatter above.
You MUST pass this to the Naxos agent so it can exclude the current session from orphan scanning.

## Dispatch

All operations dispatch to the Naxos agent via Task.

**Full triage** (no arguments):

```
Agent("naxos", "Full triage of all orphaned sessions. Current session: {session_id}.")
```

**Severity-filtered triage**:

```
Agent("naxos", "Triage orphaned sessions. Current session: {session_id}. Filter: severity >= {LEVEL}.")
```

**Specific session assessment**:

```
Agent("naxos", "Assess session {target_session_id} for orphan status. Current session: {session_id}.")
```

### Pre-flight Validation

Before dispatching:

1. If `has_session: false` and no specific session ID in $ARGUMENTS:
   - Run `Bash("ari naxos triage -o json")` directly (no agent needed for stateless scan)
   - Present results inline
2. If a specific session ID is provided, verify it exists:
   - `Read(".sos/sessions/{target_id}/SESSION_CONTEXT.md")`
   - If not found: report "Session {target_id} not found" and exit

## Post-Dispatch

After the Naxos agent returns its summary:

1. **Present** the triage results to the user
2. **Surface** the top recommendation with its rationale
3. **Offer** next actions based on recommendations:
   - For WRAP recommendations: `/sos wrap --session {id}`
   - For RESUME recommendations: `/sos resume --session {id}`
   - For DELETE recommendations: confirm with user before executing

## Closure: Naxos Dismissal

After triage completes:

1. Run `ari agent dismiss naxos` via Bash
2. Note: dismissal takes effect on next CC restart (or session end via autopark safety net)

## Sigils

### On Success

`(triaged) next: act on recommendations or /sos wrap <id>`

### On Failure

`naxos failed: {reason} -- fix: ari naxos triage`
