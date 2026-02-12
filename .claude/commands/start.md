---
name: start
description: Initialize a new work session
argument-hint: "<initiative> [--complexity=LEVEL] [--rite=NAME]"
allowed-tools: Bash, Read, Task
disallowed-tools: Write, Edit, NotebookEdit
model: opus
disable-model-invocation: true
---

## Pre-computed Context

The SessionStart hook has already injected all session state above. Check:
- **Session Context** table → whether a session exists
- **Status** field → ACTIVE, PARKED, or ARCHIVED (empty if no session)
- **Available Rites** → list of rites in this project
- **Available Agents** → list of agents in the active rite

## Your Task

$ARGUMENTS

## Behavior

### 1. Check Pre-conditions (Read from context above)

| If Hook Output Shows | Action |
|------------------------|--------|
| "No active session" | Proceed with session creation |
| Session Context table with Status=PARKED | Offer options (see below) |
| Session Context table with Status=ACTIVE | Offer options (see below) |

**When session already exists, offer these options:**

```
A session already exists in this terminal.

Options:
1. /continue - Resume the parked session
2. /park + /start - Park current, then start new
3. /wrap - Complete current session first

See also: /worktree for parallel work in isolated worktrees
```

### 2. Gather Parameters

If not provided in arguments, ask the user:

| Parameter | Description | Default |
|-----------|-------------|---------|
| **Initiative** | What are we building? | Required |
| **Complexity** | PATCH \| MODULE \| SYSTEM \| INITIATIVE \| MIGRATION | MODULE |
| **Rite** | Rite to use | Current rite from context |

### 3. Create Session via Moirai

Delegate session creation to Moirai (Clotho) via Task tool:
```
Task(moirai, "create_session initiative='<initiative>' complexity=<COMPLEXITY> rite=<rite-name>")
```

Moirai will:
- Generate session ID with timestamp
- Create `.claude/sessions/{session_id}/SESSION_CONTEXT.md` with proper schema
- Set initial phase to "requirements"
- Return confirmation with session_id

### 4. Rite Switch (only if --rite differs)

If user specified `--rite=NAME` and it differs from Active Rite:
```bash
ari sync --rite <rite-name>
```

### 5. Invoke Entry Point Agent

Read **Available Agents** from the Session Context table (injected by SessionStart hook).
Select the appropriate entry agent based on the active rite:
- For rites with an orchestrator: Use the orchestrator as entry point
- Otherwise: Use the first agent listed in Available Agents

Use Task tool to invoke the entry agent:
- Task: "Create PRD for: <initiative>"
- Include complexity level in task description

Example:
```
Task(orchestrator, "Begin <initiative> at <COMPLEXITY> complexity")
```

### 6. Confirm Success

Output to user:
- Session ID created
- Entry agent invoked
- What happens next

## Complexity Levels

| Level | Phases | Use For |
|-------|--------|---------|
| PATCH | requirements → implementation | Single-file changes, quick fixes |
| MODULE | requirements → design → implementation | Multi-file features |
| SYSTEM | + validation | New services, APIs |
| INITIATIVE | + Session -1/0 assessment | Major initiatives |
| MIGRATION | Full lifecycle + migration planning | Cross-cutting migrations, large-scale refactors |

## Example Usage

```
/start "Add dark mode toggle"
/start "Refactor auth module" --complexity=MODULE
/start "New billing service" --complexity=SYSTEM --rite=10x-dev
```

