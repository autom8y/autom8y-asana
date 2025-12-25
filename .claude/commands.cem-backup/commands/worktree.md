---
description: Manage isolated worktrees for parallel Claude sessions
argument-hint: <create|list|remove|cleanup|status> [args]
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context

Git worktrees provide true filesystem isolation for parallel Claude sessions. Each worktree has its own `.claude/` directory with independent agents, sessions, sprints, and team configuration.

## Your Task

$ARGUMENTS

## Commands

### create [name] [--team=PACK] [--from=REF]

Create a new isolated worktree:

```bash
.claude/hooks/lib/worktree-manager.sh create "$NAME" --team="$TEAM"
```

**What happens:**
1. Creates git worktree with detached HEAD (no branch pollution)
2. Initializes CEM (fresh sync from skeleton_claude)
3. Sets team if specified
4. Creates initial session
5. Returns path for user to `cd` into

**Output to user:**
- Worktree ID and path
- Instructions: `cd <path> && claude`

### list

Show all worktrees:

```bash
.claude/hooks/lib/worktree-manager.sh list
```

Display as table:
| ID | Name | Team | Created | Session | Changes |

### status [id]

Detailed worktree info:

```bash
.claude/hooks/lib/worktree-manager.sh status "$ID"
```

### remove <id> [--force]

Remove a worktree:

```bash
.claude/hooks/lib/worktree-manager.sh remove "$ID" [--force]
```

**Pre-checks:**
- Warn if uncommitted changes exist
- Require --force to override

### cleanup [--force]

Remove stale worktrees (7+ days old, no changes):

```bash
.claude/hooks/lib/worktree-manager.sh cleanup [--force]
```

### gc

Garbage collect orphaned refs:

```bash
.claude/hooks/lib/worktree-manager.sh gc
```

## Examples

```bash
# Create worktree for auth sprint with 10x team
/worktree create "auth-sprint" --team=10x-dev-pack

# Create worktree from specific branch
/worktree create "hotfix" --from=release-1.2

# List all worktrees
/worktree list

# Remove specific worktree
/worktree remove wt-20251224-143052-abc

# Cleanup stale worktrees
/worktree cleanup
```

## Typical Workflow

1. In main project, want parallel work:
   ```
   /worktree create "feature-x" --team=10x-dev-pack
   ```

2. Open new terminal, navigate to worktree:
   ```bash
   cd ~/Code/project/worktrees/wt-20251224-150000-xyz
   claude
   ```

3. Work in complete isolation (different team, sprint, session)

4. When done:
   ```
   /wrap  # Will offer to remove worktree
   ```

## Reference

Full documentation: `.claude/skills/worktree-ref/skill.md`
