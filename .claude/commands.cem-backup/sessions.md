---
description: List and manage active sessions
argument-hint: [--list] [--switch ID] [--cleanup]
allowed-tools: Bash, Read, Write
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

List and manage work sessions. $ARGUMENTS

## Behavior

### --list (default)

Show all sessions in `.claude/sessions/`:

```bash
for dir in .claude/sessions/session-*; do
  [ -d "$dir" ] || continue
  SESSION_ID=$(basename "$dir")

  # Extract metadata from SESSION_CONTEXT.md
  INITIATIVE=$(grep -m1 "^initiative:" "$dir/SESSION_CONTEXT.md" 2>/dev/null | cut -d: -f2 | tr -d ' "')
  CREATED=$(grep -m1 "^created_at:" "$dir/SESSION_CONTEXT.md" 2>/dev/null | cut -d: -f2- | tr -d ' "')
  PARKED=$(grep -m1 "^parked_at:" "$dir/SESSION_CONTEXT.md" 2>/dev/null)
  AUTO_PARKED=$(grep -m1 "^auto_parked_at:" "$dir/SESSION_CONTEXT.md" 2>/dev/null)

  if [ -n "$PARKED" ] || [ -n "$AUTO_PARKED" ]; then
    STATUS="PARKED"
  else
    STATUS="ACTIVE"
  fi

  echo "$SESSION_ID | $STATUS | $INITIATIVE | $CREATED"
done
```

Output format:
```
Sessions in this repository:

ID                              | Status | Initiative           | Created
--------------------------------|--------|----------------------|--------------------
session-20251224-143052-a1b2    | ACTIVE | Add dark mode        | 2025-12-24T14:30:52Z
session-20251224-150000-c3d4    | PARKED | Fix login bug        | 2025-12-24T15:00:00Z

Current terminal mapped to: session-20251224-143052-a1b2
```

### --switch {id}

Switch this terminal to a different session:

```bash
TTY_HASH=$(echo "${TTY:-${TERM_SESSION_ID:-unknown}}" | md5 -q)
echo "$SESSION_ID" > ".claude/sessions/.tty-map/$TTY_HASH"
```

### --cleanup

Remove sessions older than 7 days that are parked:

```bash
CUTOFF=$(date -v-7d +%Y%m%d 2>/dev/null || date -d "7 days ago" +%Y%m%d)
for dir in .claude/sessions/session-*; do
  # Extract date from session ID (session-YYYYMMDD-HHMMSS-xxxx)
  SESSION_DATE=$(basename "$dir" | cut -d- -f2)
  if [ "$SESSION_DATE" -lt "$CUTOFF" ]; then
    # Only cleanup parked sessions
    if grep -q "^parked_at:" "$dir/SESSION_CONTEXT.md" 2>/dev/null; then
      mv "$dir" ".claude/.archive/sessions/"
      echo "Archived: $(basename $dir)"
    fi
  fi
done
```

## Examples

```
/sessions              # List all sessions
/sessions --list       # Same as above
/sessions --switch session-20251224-150000-c3d4
/sessions --cleanup    # Archive old parked sessions
```
