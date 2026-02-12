---
name: wrap
description: Complete session with quality gates and summary
argument-hint: "[--skip-checks] [--no-archive]"
allowed-tools: Bash, Read, Task, Glob
disallowed-tools: Write, Edit, NotebookEdit
disable-model-invocation: true
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

## Your Task

Complete the current work session with quality validation and archival. $ARGUMENTS

## Session Resolution

Session state is pre-computed by the SessionStart hook (injected above).
Read Has Session, Session State from the context table — do not call `ari session status`.

## Pre-flight

1. Verify an active session exists (`ari session status` succeeds)
2. Check for uncommitted git changes (warn if present)

## Behavior

1. **Extract Session ID**:
   Read the Session Context table injected above. Extract the session ID from: `| Session | <session-id> |`
   You MUST pass this to Moirai — the CLI cannot discover it from a Bash subprocess.

2. **Run quality gates** (unless `--skip-checks`):
   - PRD exists and complete
   - TDD exists (if MODULE+)
   - Implementation complete
   - Tests passing

3. **Generate session summary**:
   - Total duration
   - Phases completed
   - Artifacts produced (from `$SESSION_DIR/artifacts.log`)
   - Decisions made (from handoff notes)
   - Lessons learned

4. **Delegate to Moirai** for session state mutation:
   ```
   Task(moirai, "wrap_session session_id=\"<session-id>\"")
   ```
   Or with force flag:
   ```
   Task(moirai, "wrap_session --force session_id=\"<session-id>\"")
   ```
   Moirai will:
   - Acquire lock to prevent race conditions
   - Execute `ari session wrap` (with flags if specified)
   - Validate the result and log to audit trail
   - Return structured response with session summary

4. **Display completion summary** based on Moirai's response:
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

5. **Worktree cleanup** (if in a worktree):

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

