---
description: Resume a parked work session with full context
argument-hint: [--session=ID] [--agent=NAME]
allowed-tools: Bash, Read, Write, Task
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Resume a parked work session with full context restoration. $ARGUMENTS

## Session Resolution

1. **If `--session=ID` specified**: Use that session directly
2. **If TTY already mapped**: Resume that session
3. **If no mapping**: List available parked sessions for selection

```bash
# Check for existing TTY mapping
TTY_HASH=$(echo "${TTY:-${TERM_SESSION_ID:-unknown}}" | md5 -q)
MAPPED_SESSION=$(cat ".claude/sessions/.tty-map/$TTY_HASH" 2>/dev/null)

# List parked sessions if no mapping
if [ -z "$MAPPED_SESSION" ]; then
  for dir in .claude/sessions/session-*; do
    if grep -q "^parked_at:" "$dir/SESSION_CONTEXT.md" 2>/dev/null; then
      echo "$dir"
    fi
  done
fi
```

## Pre-flight

1. Identify target session (from arg, TTY mapping, or user selection)
2. Verify session is parked (`parked_at` or `auto_parked_at` field exists)
3. Map this TTY to the resumed session

## Behavior

1. **Set TTY mapping** to the resumed session:
   ```bash
   echo "$SESSION_ID" > ".claude/sessions/.tty-map/$TTY_HASH"
   ```

2. **Read SESSION_CONTEXT.md** and restore full context:
   - Initiative and complexity
   - Current phase and last agent
   - Artifacts and blockers
   - Parking summary

3. **Validate environment**:
   - Check git branch matches (warn if changed)
   - Check team matches (warn if different)

4. **Remove park metadata**:
   - Clear `parked_at` field
   - Clear `park_reason` field
   - Clear `auto_parked_at` and `auto_parked_reason` if present
   - Update `resumed_at` timestamp

5. **Display resumption summary**:
   ```
   Session resumed: {initiative}
   Session ID: {session-id}
   Parked for: {duration}
   Current phase: {phase}
   Last agent: {agent}

   Next steps:
   - {next_step_1}
   - {next_step_2}
   ```

6. **Optionally invoke agent** if `--agent` specified:
   - Use Task tool to delegate to specified agent
   - Pass full session context

## Example

```
/continue
/continue --session=session-20251224-143052-a1b2
/continue --agent=architect
```

## Reference

Full documentation: `.claude/skills/resume/skill.md`
