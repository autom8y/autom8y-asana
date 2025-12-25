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
TTY_HASH=$(echo "${TTY:-${TERM_SESSION_ID:-unknown}}" | md5 -q)
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

2. **Add park metadata** to SESSION_CONTEXT.md:
   ```yaml
   parked_at: "2025-12-24T15:30:00Z"
   park_reason: "{user reason or 'Manual park'}"
   git_status_at_park: "{clean|uncommitted changes}"
   ```

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
