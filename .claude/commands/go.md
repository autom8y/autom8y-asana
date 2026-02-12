---
name: go
description: "Session status dashboard — shows where you are and suggests next action"
argument-hint: "[task description]"
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
cat .claude/ACTIVE_RITE 2>/dev/null || echo "none"

# 4. WIP artifacts
ls .wip/ 2>/dev/null
```

Also read the session context table injected by the SessionStart hook (already in your context above).

## Phase 2: Classify and Present

Evaluate the collected state and present the appropriate dashboard:

### ALREADY_ACTIVE (session with status=ACTIVE)

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

### RESUME_PARKED (one or more sessions with status=PARKED, none ACTIVE)

**Single parked session**:
```
Parked session found: {session_id}
Initiative: {initiative} (parked {relative_time})

Resume with: /continue
```

**Multiple parked sessions**:
```
Found {n} parked sessions:

1. {session_id_1} — {initiative_1} (parked {relative_time})
2. {session_id_2} — {initiative_2} (parked {relative_time})

Resume one with: /continue
Start fresh with: /start "<initiative>"
```

### NEW_WORK ($ARGUMENTS provided, no active/parked sessions)

```
No active sessions.

Your intent: {$ARGUMENTS}

Get started:
  /consult "{$ARGUMENTS}"  — Get rite recommendation and workflow routing
  /start "{$ARGUMENTS}"    — Start directly with current rite ({active_rite})
```

### ORIENTATION (nothing active, no arguments)

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

If `.wip/` artifacts exist without a session, mention them:

```
Note: Found {n} artifacts in .wip/ with no active session.
Review with: ls .wip/
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
# Active session exists — shows status immediately
/go

# Parked session — shows resume suggestion
/go

# New work with intent — shows start options
/go "add user authentication to the API"

# Nothing happening — shows dashboard
/go
```
