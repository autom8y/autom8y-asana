# Worktree Management Reference

> Per-session git worktree isolation for parallel Claude sessions

## Overview

Git worktrees provide true filesystem isolation for parallel Claude sessions. Each worktree has its own `.claude/` directory with independent agents, sessions, sprints, and team configuration.

**The Problem**: Claude Code requires a local `.claude/` directory structure that cannot be configured per-terminal. When multiple terminals work on the same project with different teams/sprints, they collide on shared files.

**The Solution**: Git worktrees create separate working directories that share the same git database but have independent file systems.

---

## Architecture

### Directory Structure

```
~/Code/project/                     # Main working tree
  .git/                             # Shared git database
  .claude/                          # Main ecosystem
  worktrees/                        # Worktree container
    .gitignore                      # Ignore all worktrees from git
    wt-20251224-143052-abc/         # Per-session worktree
      .claude/                      # Independent ecosystem
        .worktree-meta.json         # Worktree metadata
        agents/                     # Team agents (isolated)
        sessions/                   # Single session
        ACTIVE_TEAM                 # Team state (isolated)
        SPRINT_CONTEXT              # Sprint state (isolated)
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Detached HEAD** | No branch pollution, ephemeral by design |
| **Fresh CEM init** | Each worktree syncs independently |
| **Auto-session creation** | Worktree comes ready with session |
| **Subdirectory structure** | Clean organization under `worktrees/` |
| **7-day cleanup threshold** | Stale worktrees auto-cleaned |

---

## Commands

### `/worktree create [name] [--team=PACK] [--from=REF]`

Create a new isolated worktree with full ecosystem initialization.

**Parameters:**
- `name` - Descriptive name for the worktree (default: "unnamed")
- `--team=PACK` - Team pack to use (default: current team)
- `--from=REF` - Git ref to base worktree on (default: HEAD)

**What Happens:**
1. Creates git worktree with detached HEAD (no branch pollution)
2. Initializes CEM (fresh sync from skeleton_claude)
3. Sets team if specified via swap-team.sh
4. Creates initial session via session-manager.sh
5. Returns path for user to `cd` into

**Example:**
```bash
/worktree create "auth-sprint" --team=10x-dev-pack
# Output:
# {
#   "success": true,
#   "worktree_id": "wt-20251224-143052-abc",
#   "path": "worktrees/wt-20251224-143052-abc",
#   "instructions": "cd worktrees/wt-20251224-143052-abc && claude"
# }
```

### `/worktree list`

Show all worktrees with status information.

**Output:**
```json
{
  "worktrees": [
    {
      "id": "wt-20251224-143052-abc",
      "path": "worktrees/wt-20251224-143052-abc",
      "name": "auth-sprint",
      "team": "10x-dev-pack",
      "created_at": "2025-12-24T14:30:52Z",
      "has_changes": false,
      "session_status": "active"
    }
  ],
  "count": 1
}
```

### `/worktree status [id]`

Detailed status of a specific worktree or all worktrees.

**With ID:**
```json
{
  "worktree_id": "wt-20251224-143052-abc",
  "created_at": "2025-12-24T14:30:52Z",
  "name": "auth-sprint",
  "from_ref": "HEAD",
  "team": "10x-dev-pack",
  "complexity": "MODULE",
  "parent_project": "/Users/user/Code/project"
}
```

### `/worktree remove <id> [--force]`

Remove a specific worktree.

**Pre-checks:**
- Warns if uncommitted changes exist
- Requires `--force` to override

**Example:**
```bash
/worktree remove wt-20251224-143052-abc
# Error: Worktree has uncommitted changes. Use --force to override.

/worktree remove wt-20251224-143052-abc --force
# { "success": true, "removed": "wt-20251224-143052-abc" }
```

### `/worktree cleanup [--force]`

Remove stale worktrees (7+ days old, no uncommitted changes).

**Example:**
```bash
/worktree cleanup
# { "removed": 2, "skipped": 1, "cutoff_days": 7 }
```

### `/worktree gc`

Garbage collect orphaned worktree refs.

**Example:**
```bash
/worktree gc
# { "pruned": true, "remaining_worktrees": 3 }
```

---

## Typical Workflow

### 1. Starting Parallel Work

From main project, when you want parallel work:

```bash
# In main terminal, already working on feature-auth
/worktree create "billing-sprint" --team=10x-dev-pack

# Output tells you what to do next
# "cd worktrees/wt-20251224-150000-xyz && claude"
```

### 2. Working in Worktree

Open new terminal and navigate:

```bash
cd ~/Code/project/worktrees/wt-20251224-150000-xyz
claude
```

Now you're in a completely isolated environment:
- Different team configuration
- Different sprint context
- Different session state
- Changes don't affect main project

### 3. Completing Worktree Session

When done with the isolated work:

```bash
/wrap
# "This session ran in an isolated worktree: wt-20251224-150000-xyz"
# "Remove worktree? (y/n)"
```

If removing:
```bash
cd ~/Code/project
git worktree remove --force worktrees/wt-20251224-150000-xyz
```

---

## Integration Points

### With /start

When `/start` detects an existing session, it now offers worktree as an option:

```
A session already exists in this terminal.

Options:
1. /continue - Resume the parked session
2. /park + /start - Park current, then start new
3. /wrap - Complete current session first
4. /worktree create "<name>" - Start in ISOLATED worktree (parallel work)
```

### With /wrap

When completing a session in a worktree, `/wrap` offers cleanup:

```
Session Complete: billing-sprint
...
This session ran in an isolated worktree: wt-20251224-150000-xyz
Remove worktree? (y/n)
```

### With /sessions

The `--all` flag shows sessions across all worktrees:

```bash
/sessions --all

=== Main Project ===
session-20251224-143052-a1b2 | ACTIVE | feature-auth | 2025-12-24T14:30:52Z

=== Worktrees ===
[wt-20251224-150000-xyz] billing-sprint (team: 10x-dev-pack)
  session-20251224-150000-c3d4 | ACTIVE | billing-sprint
```

### With CEM

`cem status` detects and displays worktree info:

```
Claude Ecosystem Status
━━━━━━━━━━━━━━━━━━━━━━━━

[WORKTREE]    wt-20251224-150000-xyz
Name:         billing-sprint
Team:         10x-dev-pack

Skeleton:     /Users/user/Code/skeleton_claude
...
```

---

## Worktree Metadata

Each worktree stores metadata in `.claude/.worktree-meta.json`:

```json
{
  "worktree_id": "wt-20251224-143052-abc",
  "created_at": "2025-12-24T14:30:52Z",
  "name": "auth-sprint",
  "from_ref": "HEAD",
  "team": "10x-dev-pack",
  "complexity": "MODULE",
  "parent_project": "/Users/user/Code/project"
}
```

---

## Implementation Details

### worktree-manager.sh

Core script at `.claude/hooks/lib/worktree-manager.sh` (~250 lines).

**Functions:**
- `generate_worktree_id()` - Creates unique ID: `wt-YYYYMMDD-HHMMSS-xxxx`
- `ensure_worktrees_dir()` - Creates `worktrees/` with `.gitignore`
- `is_worktree()` - Detects if in a worktree
- `cmd_create()` - Full creation flow
- `cmd_list()` - JSON listing with status
- `cmd_status()` - Detailed info
- `cmd_remove()` - Safe removal with change check
- `cmd_cleanup()` - Stale worktree cleanup
- `cmd_gc()` - Git worktree prune

### CEM Integration

CEM functions in `cem` script:
- `is_worktree()` - Detect worktree context
- `get_worktree_info()` - Read metadata
- `get_worktree_id()` - Extract ID from metadata

---

## Troubleshooting

### "Failed to create git worktree"

**Cause:** Git worktree add failed.

**Check:**
- Is this a git repository?
- Does the target path already exist?
- Is the from_ref valid?

### "Failed to initialize CEM in worktree"

**Cause:** CEM script not found or failed.

**Check:**
- Is `$HOME/Code/skeleton_claude/cem` executable?
- Does skeleton_claude exist?

### "Worktree has uncommitted changes"

**Cause:** Trying to remove worktree with uncommitted changes.

**Fix:** Either commit/stash changes or use `--force`.

### Cannot find worktree after creation

**Cause:** Worktree created but user didn't `cd` into it.

**Fix:** Follow the instructions in the output:
```bash
cd worktrees/wt-{id} && claude
```

---

## Best Practices

1. **Name worktrees descriptively** - Use meaningful names for easy identification
2. **Clean up regularly** - Run `/worktree cleanup` periodically
3. **One session per worktree** - Worktrees are designed for single sessions
4. **Use for different teams** - Primary use case is parallel team work
5. **Don't commit worktree changes to main** - Worktrees are ephemeral
