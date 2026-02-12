---
name: sessions
description: List and manage active sessions
argument-hint: "[--list] [--switch ID] [--cleanup] [--all]"
allowed-tools: Bash, Read, Write
model: sonnet
disable-model-invocation: true
context: fork
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

List and manage work sessions. $ARGUMENTS

## Behavior

### --list (default)

Show all sessions in current directory `.claude/sessions/`:

```bash
for dir in .claude/sessions/session-*; do
  [ -d "$dir" ] || continue
  SESSION_ID=$(basename "$dir")

  # Extract metadata from SESSION_CONTEXT.md
  INITIATIVE=$(grep -m1 "^initiative:" "$dir/SESSION_CONTEXT.md" 2>/dev/null | cut -d: -f2- | tr -d ' "')
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

### --all

Show sessions across all worktrees (main + worktrees/):

```bash
# Get project root (main worktree)
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

echo "=== Main Project ==="
for dir in "$PROJECT_ROOT/.claude/sessions/session-*"; do
  [ -d "$dir" ] || continue
  # ... same as --list
done

echo ""
echo "=== Worktrees ==="
for wt in "$PROJECT_ROOT/worktrees"/wt-*; do
  [ -d "$wt" ] || continue
  WT_ID=$(basename "$wt")
  WT_NAME=$(jq -r '.name // "unnamed"' "$wt/.claude/.worktree-meta.json" 2>/dev/null)
  WT_RITE=$(jq -r '.rite // "none"' "$wt/.claude/.worktree-meta.json" 2>/dev/null)

  echo ""
  echo "[$WT_ID] $WT_NAME (rite: $WT_RITE)"
  for dir in "$wt/.claude/sessions/session-*"; do
    [ -d "$dir" ] || continue
    SESSION_ID=$(basename "$dir")
    INITIATIVE=$(grep -m1 "^initiative:" "$dir/SESSION_CONTEXT.md" 2>/dev/null | cut -d: -f2- | tr -d ' "')
    PARKED=$(grep -m1 "^parked_at:" "$dir/SESSION_CONTEXT.md" 2>/dev/null)
    AUTO_PARKED=$(grep -m1 "^auto_parked_at:" "$dir/SESSION_CONTEXT.md" 2>/dev/null)
    [ -n "$PARKED" ] || [ -n "$AUTO_PARKED" ] && STATUS="PARKED" || STATUS="ACTIVE"
    echo "  $SESSION_ID | $STATUS | $INITIATIVE"
  done
done
```

### --switch {id}

Switch this terminal to a different session:

```bash
# Session resolution is handled internally by ari
ari session resume "$SESSION_ID"
```

> For full subcommand list: `ari session --help`

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
/sessions              # List sessions in current directory
/sessions --list       # Same as above
/sessions --all        # List sessions across all worktrees
/sessions --switch session-20251224-150000-c3d4
/sessions --cleanup    # Archive old parked sessions
```
