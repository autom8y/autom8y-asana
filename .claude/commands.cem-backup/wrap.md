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
TTY_HASH=$(echo "${TTY:-${TERM_SESSION_ID:-unknown}}" | md5 -q)
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

3. **Archive session** (unless `--no-archive`):
   ```bash
   mkdir -p .claude/.archive/sessions
   mv "$SESSION_DIR" ".claude/.archive/sessions/$SESSION_ID"
   ```

4. **Clear TTY mapping**:
   ```bash
   rm -f ".claude/sessions/.tty-map/$TTY_HASH"
   ```

5. **Display completion summary**:
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

## Quality Gates

| Gate | Check |
|------|-------|
| PRD | File exists at expected path |
| TDD | File exists (if MODULE+) |
| Code | Implementation files exist |
| Tests | Test files exist and pass |

## Reference

Full documentation: `.claude/skills/wrap-ref/skill.md`
