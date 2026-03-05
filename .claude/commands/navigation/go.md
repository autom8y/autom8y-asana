---
name: go
description: "Session status dashboard — shows where you are and suggests next action"
argument-hint: "[task description] [--full]"
allowed-tools: Bash, Read
model: opus
---

## Purpose

`/go` is a lightweight status dashboard. It reads system state, presents it, and suggests what to do next. It does NOT dispatch to other commands — the user decides what to invoke.

## Context

Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Show session status and suggest next action. $ARGUMENTS

## Phase 1: Collect State (parallel)

Run these in parallel to gather all state in under 3 seconds:

```bash
# 1. Session status
ari session status --output json 2>/dev/null

# 2. Session list (recent, any status)
ari session list --output json 2>/dev/null

# 3. Active rite
cat .knossos/ACTIVE_RITE 2>/dev/null || echo "none"

# 4. WIP artifacts
ls .sos/wip/ 2>/dev/null
```

Also read the session context table injected by the SessionStart hook (already in your context above).

## Phase 2: Classify and Present

Evaluate the collected state and classify into one of four states: ALREADY_ACTIVE, RESUME_PARKED, NEW_WORK, or ORIENTATION.

### Mode Selection

If `$ARGUMENTS` contains `--full`:
- Strip `--full` from arguments (it is a flag, not a task description)
- Use **Full Mode** below

Otherwise: use **Brief Mode** (default).

---

### Brief Mode (default)

For each classified state, output a compact card. No preamble, no extra commentary.

**ALREADY_ACTIVE** (session with status=ACTIVE):
```
Rite:    {active_rite}
Phase:   {current_phase}
Session: {session_id}

next: {hint}
```

Resolve the `next:` hint: read `.knossos/ACTIVE_WORKFLOW.yaml`, find the phase matching `current_phase`, check its `next` field. If `next` names a phase → `/handoff {that_phase_agent}`. If `next: null` (terminal) → `/wrap` or `/commit && /pr`. If the user provided `$ARGUMENTS`, use their intent as the hint instead.

**RESUME_PARKED** (single parked session):
```
Parked:  {session_id} ({relative_time} ago)
Rite:    {active_rite}

next: /continue
```

**RESUME_PARKED** (multiple parked sessions):
```
Parked sessions:
1. {id_1} — {initiative_1} ({time})
2. {id_2} — {initiative_2} ({time})

next: /continue
```

**NEW_WORK** ($ARGUMENTS provided, no active/parked sessions):
```
No active session.
Intent: {$ARGUMENTS}

next: /consult "{$ARGUMENTS}"
```

**ORIENTATION** (nothing active, no arguments):
```
Rite:    {active_rite or "none"}
Sessions: {active_count} active, {parked_count} parked

next: /consult
```

If `.sos/wip/` artifacts exist without a session, append: `Note: {n} artifacts in .wip/ with no active session.`

---

### Full Mode (`--full`)

Display expanded dashboard with sprint progress and multiple options.

**ALREADY_ACTIVE** (session with status=ACTIVE):

Display a compact status block. No preamble.

```
Session: {session_id}
Rite: {active_rite} | Phase: {current_phase}
Initiative: {initiative}

Sprint Progress:
- [x] Completed task
- [ ] Current task  <-- you are here
- [ ] Next task

Suggested next action: {inferred from phase and sprint state}
```

Read the session's `SESSION_CONTEXT.md` and any `SPRINT_CONTEXT.md` to populate sprint progress. If sprint data is not available, show the phase and initiative without a task list.

If the user provided `$ARGUMENTS`, acknowledge the active session AND relay their intent as the suggested next action.

**RESUME_PARKED** (one or more sessions with status=PARKED, none ACTIVE):

*Single parked session*:
```
Parked session found: {session_id}
Initiative: {initiative} (parked {relative_time})

Resume with: /continue
```

*Multiple parked sessions*:
```
Found {n} parked sessions:

1. {session_id_1} — {initiative_1} (parked {relative_time})
2. {session_id_2} — {initiative_2} (parked {relative_time})

Resume one with: /continue
Start fresh with: /start "<initiative>"
```

**NEW_WORK** ($ARGUMENTS provided, no active/parked sessions):

```
No active sessions.

Your intent: {$ARGUMENTS}

Get started:
  /consult "{$ARGUMENTS}"  — Get rite recommendation and workflow routing
  /start "{$ARGUMENTS}"    — Start directly with current rite ({active_rite})
```

**ORIENTATION** (nothing active, no arguments):

```
Rite: {active_rite or "none"}
Sessions: {count active} active, {count parked} parked

Options:
  /go <task>     — Show dashboard with intent
  /consult       — Get guidance on what to do
  /start <task>  — Start a new session
  /sessions      — Browse all sessions
  /rite --list   — See available rites
```

If `.sos/wip/` artifacts exist without a session, mention them:

```
Note: Found {n} artifacts in .wip/ with no active session.
Review with: ls .sos/wip/
```

## Behavioral Rules

1. **Present, don't dispatch.** `/go` shows status and suggests commands. It does NOT invoke `/start`, `/continue`, `/consult`, or any other command. The user decides what to do next.

2. **Read everything, ask almost nothing.** Collect all state in parallel, then present. Never ask "do you have an active session?" — check it yourself.

3. **One question maximum.** If state is unambiguous, present it. Only ask when multiple parked sessions exist and the user needs to choose.

4. **No mythology.** Use plain operational vocabulary. Session, rite, phase, sprint.

5. **No preamble.** Do not say "Let me check your session state..." Just collect, decide, and present.

6. **Terse output.** Tables and short lines, not paragraphs. Every extra line costs time-to-productive.

## Examples

```bash
# Brief status card (default)
/go

# Full dashboard
/go --full

# Brief with intent
/go "add user authentication to the API"

# Full with intent
/go --full "add user authentication to the API"
```
