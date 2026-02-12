---
user-invocable: false
---

# Worktree Troubleshooting

> Common issues and solutions for git worktree management.

## Common Issues

### "Failed to create git worktree"

**Cause:** Git worktree add failed.

**Check:**
- Is this a git repository?
- Does the target path already exist?
- Is the from_ref valid?

**Fix:**
```bash
# Verify git repository
git status

# Check if path exists
ls worktrees/

# Verify ref exists
git rev-parse HEAD
```

### "Failed to initialize ecosystem in worktree"

**Cause:** Knossos sync failed or ari not found.

**Check:**
- Is `$KNOSSOS_HOME` set correctly?
- Is `ari` in PATH?

**Fix:**
```bash
# Verify knossos exists
ls -la $KNOSSOS_HOME/cmd/ari

# Build ari if needed
CGO_ENABLED=0 go build -o ~/bin/ari $KNOSSOS_HOME/cmd/ari
```

### "Worktree has uncommitted changes"

**Cause:** Trying to remove worktree with uncommitted changes.

**Fix:** Either commit/stash changes or use `--force`:
```bash
# Option 1: Commit changes
cd worktrees/wt-{id}
git add . && git commit -m "WIP: worktree work"

# Option 2: Force remove
/worktree remove wt-{id} --force
```

### Cannot find worktree after creation

**Cause:** Worktree created but user didn't `cd` into it.

**Fix:** Follow the instructions in the output:
```bash
cd worktrees/wt-{id} && claude
```

### Worktree shows stale session

**Cause:** Session was not properly closed before leaving worktree.

**Fix:**
```bash
# Navigate to worktree
cd worktrees/wt-{id}

# Check session status
ari session status

# Wrap or park the session
/wrap
# or
/park
```

### Git worktree prune warnings

**Cause:** Orphaned worktree references in git.

**Fix:**
```bash
/worktree gc
# or manually
git worktree prune
```

### Rite not active in worktree

**Cause:** Rite swap failed during creation or was never set.

**Fix:**
```bash
cd worktrees/wt-{id}
ari sync --rite <rite-name>
```

## Diagnostic Commands

```bash
# List all git worktrees
git worktree list

# Check worktree metadata
cat worktrees/wt-{id}/.claude/.worktree-meta.json

# Verify sync state
cd worktrees/wt-{id} && ari sync --dry-run

# Check session state
cd worktrees/wt-{id} && ari session status
```
