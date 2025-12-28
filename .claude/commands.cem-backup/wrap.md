---
description: Complete session with quality gates and summary
argument-hint: [--skip-checks] [--no-archive]
allowed-tools: Bash, Read, Write, Task, Glob
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Complete the current work session with quality validation and archival. $ARGUMENTS

## Session Resolution

```bash
# Uses portable hash from session-manager
TTY_HASH=$(.claude/hooks/lib/session-manager.sh tty-hash | grep -o '"tty_hash": "[^"]*"' | cut -d'"' -f4)
SESSION_ID=$(cat ".claude/sessions/.tty-map/$TTY_HASH" 2>/dev/null)
SESSION_DIR=".claude/sessions/$SESSION_ID"
```

## Pre-flight

1. Verify TTY has an active session mapping
2. Verify `$SESSION_DIR/SESSION_CONTEXT.md` exists
3. Check for uncommitted git changes (warn if present)

## Behavior

1. **Run quality gates** (unless `--skip-checks`):
   - PRD exists and complete
   - TDD exists (if MODULE+)
   - Implementation complete
   - Tests passing

2. **Generate session summary**:
   - Total duration
   - Phases completed
   - Artifacts produced (from `$SESSION_DIR/artifacts.log`)
   - Decisions made (from handoff notes)
   - Lessons learned

3. **Execute atomic wrap mutation**:
   ```bash
   ARCHIVE="true"
   [[ "$1" == "--no-archive" ]] && ARCHIVE="false"
   .claude/hooks/lib/session-manager.sh mutate wrap "$ARCHIVE"
   ```
   This will:
   - Acquire lock to prevent race conditions
   - Create backup of SESSION_CONTEXT.md
   - Add completed_at timestamp to frontmatter
   - Archive session directory (unless --no-archive)
   - Clear TTY mapping
   - Validate the result
   - Log to audit trail (.claude/sessions/.audit/session-mutations.log)
   - Rollback on failure

4. **Display completion summary**:
   ```
   Session Complete: {initiative}
   Session ID: {session-id}
   Duration: {total time}

   Artifacts:
   - PRD: /docs/requirements/PRD-{slug}.md
   - TDD: /docs/design/TDD-{slug}.md
   - Code: /src/...

   Quality: All gates passed
   Archived to: .claude/.archive/sessions/{session-id}/

   Next session: Use /start for new work
   ```

6. **Worktree cleanup** (if in a worktree):

   Check if running in an isolated worktree:
   ```bash
   GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
   if [[ -f "$GIT_DIR" ]] && grep -q "^gitdir:" "$GIT_DIR" 2>/dev/null; then
     IS_WORKTREE=true
     WT_META=".claude/.worktree-meta.json"
     WT_ID=$(jq -r '.worktree_id' "$WT_META" 2>/dev/null)
   fi
   ```

   If in worktree, prompt user:
   ```
   This session ran in an isolated worktree: {wt_id}
   Remove worktree? (y/n)
   - [y] Run: git worktree remove --force "$(pwd)"
   - [n] Worktree preserved for future use
   ```

   **Important:** If user says yes, they must `cd` back to the main project first:
   ```
   cd {parent_project} && git worktree remove --force {worktree_path}
   ```

## Quality Gates

| Gate | Check |
|------|-------|
| PRD | File exists at expected path |
| TDD | File exists (if MODULE+) |
| Code | Implementation files exist |
| Tests | Test files exist and pass |

## Reference

Full documentation: `.claude/skills/wrap-ref/skill.md`
