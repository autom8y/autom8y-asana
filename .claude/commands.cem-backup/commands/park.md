---
description: Pause work session and preserve state for later
argument-hint: [reason]
allowed-tools: Bash, Read, Write
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Pause the current work session and save state for later resumption. $ARGUMENTS

## Session Resolution

This terminal's session is resolved via TTY mapping:
```bash
# Uses portable hash from session-manager
TTY_HASH=$(.claude/hooks/lib/session-manager.sh tty-hash | grep -o '"tty_hash": "[^"]*"' | cut -d'"' -f4)
SESSION_ID=$(cat ".claude/sessions/.tty-map/$TTY_HASH" 2>/dev/null)
SESSION_DIR=".claude/sessions/$SESSION_ID"
SESSION_FILE="$SESSION_DIR/SESSION_CONTEXT.md"
```

## Pre-flight

1. Verify TTY has an active session mapping
2. Verify `$SESSION_DIR/SESSION_CONTEXT.md` exists
3. Check session not already parked (no `parked_at` field)

## Behavior

1. **Capture state**:
   - Current phase and last agent
   - Artifacts produced so far (from `$SESSION_DIR/artifacts.log`)
   - Git status (warn about uncommitted changes)
   - Open questions and blockers

2. **Execute atomic park mutation**:
   ```bash
   REASON="${1:-Manual park}"
   .claude/hooks/lib/session-manager.sh mutate park "$REASON"
   ```
   This will:
   - Acquire lock to prevent race conditions
   - Create backup of SESSION_CONTEXT.md
   - Add park metadata to frontmatter (parked_at, park_reason, git_status_at_park)
   - Validate the result
   - Log to audit trail (.claude/sessions/.audit/session-mutations.log)
   - Rollback on failure

3. **Generate parking summary**:
   - Duration so far
   - Progress (completed/in-progress artifacts)
   - Next steps when resuming

4. **Display summary** to user

## Example

```
/park "Waiting for stakeholder feedback on PRD"
```

Output:
```
Session parked at 2025-12-24 15:30

Progress: PRD complete, TDD in progress
Duration: 2h 15m
Reason: Waiting for stakeholder feedback on PRD

Resume with: /continue
```

## Reference

Full documentation: `.claude/skills/park-ref/skill.md`
