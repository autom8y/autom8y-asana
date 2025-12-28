---
description: Sync project with skeleton_claude ecosystem
argument-hint: [init|sync|status|diff]
allowed-tools: Bash, Read
---

## Context

Auto-injected by SessionStart hook.

## Your Task

$ARGUMENTS

Manage ecosystem synchronization with skeleton_claude using the CEM (Claude Ecosystem Manager) tool.

## Behavior

**If no arguments or `sync`:**
Run `~/Code/skeleton_claude/cem sync` to pull updates from skeleton.

**If `init`:**
Run `~/Code/skeleton_claude/cem init` to initialize this project with the ecosystem.

**If `status`:**
Run `~/Code/skeleton_claude/cem status` to show current sync state.

**If `diff`:**
Run `~/Code/skeleton_claude/cem diff` to show differences with skeleton.

**If `--force`:**
Add `--force` flag to overwrite local modifications.

**If `--dry-run`:**
Add `--dry-run` flag to preview changes without applying.

## Examples

```bash
/sync              # Pull latest updates
/sync init         # Initialize project
/sync status       # Show sync state
/sync diff         # Show differences
/sync --force      # Force overwrite local changes
/sync --dry-run    # Preview what would change
```

## After Running

Report the output to the user. If there are conflicts, explain what happened and how to resolve them.

## Reference

Full CEM documentation: Run `~/Code/skeleton_claude/cem --help`
