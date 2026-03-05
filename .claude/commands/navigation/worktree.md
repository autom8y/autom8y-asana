---
name: worktree
description: Manage isolated worktrees for parallel Claude sessions
argument-hint: "<create|list|remove|cleanup|status> [args]"
allowed-tools: Bash, Read
model: sonnet
disable-model-invocation: true
context: fork
---

## Context

Git worktrees provide true filesystem isolation for parallel Claude sessions. Each worktree has its own `.claude/` directory (CC primitives), `.knossos/` (framework state), and `.sos/` (session state).

## Pre-flight

1. **Git repository required**:
   - Verify in git repository: `git rev-parse --git-dir`
   - If not: ERROR "Not in a git repository. Worktrees require git."

2. **Git worktree support**:
   - Check git version supports worktrees (2.5+)

## Your Task

$ARGUMENTS

## Commands

### create [name] [--rite=NAME]

Create a new isolated worktree:

```bash
ari worktree create "<name>" --rite "<rite-name>"
```

**What happens:**
1. Creates git worktree with detached HEAD (no branch pollution)
2. Initializes ecosystem (fresh materialize from knossos)
3. Sets rite if specified
4. Creates initial session
5. Returns path for user to `cd` into

**Output to user:**
- Worktree ID and path
- Instructions: `cd <path> && claude`

### list

Show all worktrees:

```bash
ari worktree list
```

Display as table:
| ID | Name | Rite | Created | Session | Changes |

### status [id]

Detailed worktree info:

```bash
ari worktree status "<id>"
```

### remove <id> [--force]

Remove a worktree:

```bash
ari worktree remove "<id>" --force
```

**Pre-checks:**
- Warn if uncommitted changes exist
- Require --force to override

### cleanup [--older-than=7d]

Remove stale worktrees (7+ days old, no changes):

```bash
ari worktree cleanup --older-than=7d
```

## Examples

```bash
# Create worktree for auth sprint with 10x rite
/worktree create "auth-sprint" --rite=10x-dev

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
   /worktree create "feature-x" --rite=10x-dev
   ```

2. Open new terminal, navigate to worktree:
   ```bash
   cd ~/Code/project/worktrees/wt-20251224-150000-xyz
   claude
   ```

3. Work in complete isolation (different rite, sprint, session)

4. When done:
   ```
   /wrap  # Will offer to remove worktree
   ```

## Reference

Full documentation: `.claude/commands/navigation/worktree/INDEX.md`

## Sigil

### On Success

End your response with:

🌿 branched · next: {hint}

**Fork-context note**: This command may run without conversation history. To resolve the hint, read session state from disk if needed.

Resolve hint based on subcommand:
- `create` → `next: cd {worktree_path} && claude`
- `list`, `status`, `remove`, `cleanup` → output `🌿 branched` without hint (informational subcommands).

### On Failure

❌ worktree failed: {brief reason} · fix: {recovery}

Infer recovery: not in git repo → `git init`; git version too old → upgrade git; worktree already exists → use a different name; uncertain → `/consult`.
