---
user-invocable: false
---

# Worktree Examples

> Workflow scenarios for git worktree management.

## Typical Workflow

### 1. Starting Parallel Work

From main project, when you want parallel work:

```bash
# In main terminal, already working on feature-auth
/worktree create "billing-sprint" --rite=10x-dev

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
- Different rite configuration
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

## Integration Points

### With /start

When `/start` detects an existing session, it offers these options and references worktree:

```
A session already exists in this terminal.

Options:
1. /continue - Resume the parked session
2. /park + /start - Park current, then start new
3. /wrap - Complete current session first

See also: /worktree for parallel work in isolated worktrees
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
[wt-20251224-150000-xyz] billing-sprint (rite: 10x-dev)
  session-20251224-150000-c3d4 | ACTIVE | billing-sprint
```

### With Knossos

Worktree status can be checked via metadata:

```
Worktree Status
------------------------

[WORKTREE]    wt-20251224-150000-xyz
Name:         billing-sprint
Rite:         10x-dev

Knossos:      /Users/user/Code/knossos
...
```

## Best Practices

1. **Name worktrees descriptively** - Use meaningful names for easy identification
2. **Clean up regularly** - Run `/worktree cleanup` periodically
3. **One session per worktree** - Worktrees are designed for single sessions
4. **Use for different rites** - Primary use case is parallel rite work
5. **Don't commit worktree changes to main** - Worktrees are ephemeral
