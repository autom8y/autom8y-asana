---
description: Initialize a new work session with context capture
argument-hint: [initiative] [--complexity=LEVEL] [--team=PACK]
allowed-tools: Bash, Read, Write, Task, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Initialize a new work session. $ARGUMENTS

## Pre-flight

1. Check this terminal has no active session (via TTY mapping)
2. Validate team pack if specified

## Session Creation

This project uses **TTY-based session isolation**. Each terminal gets its own session:

```bash
# Generate unique session ID
SESSION_ID="session-$(date +%Y%m%d-%H%M%S)-$(openssl rand -hex 4)"

# Create session directory
mkdir -p .claude/sessions/$SESSION_ID

# Map this TTY to the new session
TTY_HASH=$(echo "${TTY:-${TERM_SESSION_ID:-unknown}}" | md5 -q)
mkdir -p .claude/sessions/.tty-map
echo "$SESSION_ID" > ".claude/sessions/.tty-map/$TTY_HASH"
```

## Behavior

1. **Gather parameters** (prompt if not provided):
   - Initiative name (e.g., "Add dark mode toggle")
   - Complexity: SCRIPT | MODULE | SERVICE | PLATFORM
   - Team: defaults to ACTIVE_TEAM

2. **Switch team** if `--team` differs from current:
   ```bash
   ~/Code/roster/swap-team.sh <team-name>
   ```

3. **Create SESSION_CONTEXT.md** at `.claude/sessions/{id}/SESSION_CONTEXT.md`:
   ```yaml
   ---
   session_id: "{generated-id}"
   created_at: "{timestamp}"
   initiative: "{initiative}"
   complexity: "{level}"
   active_team: "{team}"
   current_phase: "requirements"
   ---

   # Session: {initiative}

   ## Artifacts
   - PRD: pending
   - TDD: pending (if MODULE+)

   ## Blockers
   None yet.

   ## Next Steps
   1. Complete requirements gathering
   ```

4. **Load workflow for active team**:
   ```bash
   # Read from ACTIVE_WORKFLOW.yaml (copied by swap-team.sh)
   ENTRY_AGENT=$(grep -A2 "^entry_point:" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
   ARTIFACT_PATH=$(grep -A5 "^entry_point:" .claude/ACTIVE_WORKFLOW.yaml | grep "path_template:" | awk '{print $2}')
   ```

5. **Invoke entry point agent** via Task tool:
   - Agent: Read from workflow `entry_point.agent`
   - Create artifact at: `entry_point.artifact.path_template` (replace {slug} with initiative slug)

6. **Progress through phases** based on complexity:
   - Read applicable phases from workflow `complexity_levels[].phases`
   - For each phase after entry, invoke the corresponding agent
   - Each agent produces its artifact before handoff to next phase

## Workflow-Driven Complexity

Each team defines its own complexity levels in `workflow.yaml`. Examples:

**10x-dev-pack**: SCRIPT | MODULE | SERVICE | PLATFORM
**doc-team-pack**: PAGE | SECTION | SITE
**hygiene-pack**: SPOT | MODULE | CODEBASE
**debt-triage-pack**: QUICK | AUDIT

The workflow config determines which phases apply at each complexity level.

## Reference

Full documentation: `.claude/skills/start-ref/skill.md`
