---
user-invocable: false
---

# Worktree Behavior Reference

> Full command reference and implementation details for git worktree management.

## Commands

### `/worktree create [name] [--rite=NAME] [--from=REF]`

Create a new isolated worktree with full ecosystem initialization.

**Parameters:**
- `name` - Descriptive name for the worktree (default: "unnamed")
- `--rite=NAME` - Rite to use (default: current rite)
- `--from=REF` - Git ref to base worktree on (default: HEAD)

**What Happens:**
1. Creates git worktree with detached HEAD (no branch pollution)
2. Initializes ecosystem (fresh sync from knossos)
3. Sets rite if specified via `ari sync --rite <name>`
4. Creates initial session via `ari session create`
5. Returns path for user to `cd` into

**Example:**
```bash
/worktree create "auth-sprint" --rite=10x-dev
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
      "rite": "10x-dev",
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
  "rite": "10x-dev",
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

## Worktree Metadata

Each worktree stores metadata in `.knossos/.worktree-meta.json`:

```json
{
  "worktree_id": "wt-20251224-143052-abc",
  "created_at": "2025-12-24T14:30:52Z",
  "name": "auth-sprint",
  "from_ref": "HEAD",
  "rite": "10x-dev",
  "complexity": "MODULE",
  "parent_project": "/Users/user/Code/project"
}
```

## Implementation Details

### ari worktree

Worktree management via the `ari worktree` subcommands.

**Commands:**
- `ari worktree create` - Full creation flow with unique ID: `wt-YYYYMMDD-HHMMSS-xxxx`
- `ari worktree list` - JSON listing with status
- `ari worktree status` - Detailed info
- `ari worktree remove` - Safe removal with change check
- `ari worktree cleanup` - Stale worktree cleanup and git worktree prune

### Worktree Detection

Worktree context is detected via `.knossos/.worktree-meta.json` presence. Use `ari worktree status` for metadata.
