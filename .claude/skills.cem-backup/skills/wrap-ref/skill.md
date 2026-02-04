---
name: wrap-ref
description: "Complete and finalize work session. Validates artifacts, runs quality gates, generates session summary. Archives SESSION_CONTEXT, records accomplishments and decisions. Triggers: /wrap, finish session, complete session, finalize work, end session."
---

# /wrap - Complete and Finalize Session

> **Category**: Session Lifecycle | **Phase**: Session Completion

## Purpose

Complete and finalize the current work session by validating artifacts, running quality gates, generating a comprehensive session summary, and cleaning up session state. Ensures all deliverables meet quality standards, records accomplishments and decisions, and provides a clear handoff point for future work.

Use `/wrap` when:
- All session goals achieved and artifacts complete
- Work is ready for production deployment or next phase
- Session scope exhausted (no more work to do)
- Formal session closure needed for audit/tracking

---

## Usage

```bash
/wrap [--skip-checks] [--archive]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--skip-checks` | No | false | Skip quality gate validation (use with caution) |
| `--archive` | No | true | Archive SESSION_CONTEXT instead of deleting |

---

## Behavior

When `/wrap` is invoked, the following sequence occurs:

### 1. Pre-flight Validation

- **Check for active session**: Verify session exists (uses `get_session_dir()` from session-utils.sh)
  - If missing → Error: "No active session to wrap. Already completed or never started"
- **Check not parked**: Verify `parked_at` field not set
  - If parked → Warning: "Session is parked. Resume before wrapping? [y/n]"
  - If yes → Auto-invoke `/resume`, then continue wrap

### 2. Run Quality Gates (unless --skip-checks)

Validate artifacts based on session complexity:

#### All Complexity Levels

**PRD Quality Gate**:
- ✓ PRD file exists at documented path
- ✓ PRD contains all required sections (Problem, Solution, Requirements, Acceptance Criteria)
- ✓ Acceptance criteria are testable and specific
- ✓ No blocking questions remain unanswered

If PRD missing or incomplete:
```
⚠ Quality Gate Failure: PRD

Issues:
- PRD file not found at /docs/requirements/PRD-{slug}.md
  OR
- PRD missing required sections: {list missing sections}
  OR
- PRD has {count} unanswered blocking questions

Resolution:
1. Complete PRD before wrapping
2. Use --skip-checks to wrap anyway (not recommended)
3. Use /handoff requirements-analyst to fix PRD

Continue wrap? [y/n]:
```

#### MODULE+ Complexity

**TDD Quality Gate**:
- ✓ TDD file exists at documented path
- ✓ TDD traces to PRD requirements
- ✓ All architecture decisions have ADRs
- ✓ Interfaces and data flow defined
- ✓ Complexity level justified

**ADR Quality Gate**:
- ✓ All major decisions documented
- ✓ ADRs follow template format
- ✓ Context, decision, consequences captured

If TDD/ADR missing or incomplete:
```
⚠ Quality Gate Failure: TDD/ADRs

Issues:
- TDD references 3 architecture decisions but only 1 ADR found
  OR
- TDD missing component interfaces section
  OR
- ADR-0042 missing "Consequences" section

Resolution:
1. Complete TDD and ADRs before wrapping
2. Use --skip-checks to wrap anyway (not recommended)
3. Use /handoff architect to address issues

Continue wrap? [y/n]:
```

#### Implementation Phase (if engineer was last_agent)

**Code Quality Gate**:
- ✓ All code committed (git status clean)
- ✓ Tests exist and passing
- ✓ Type safety validated (mypy/tsc clean)
- ✓ Linting clean (flake8/eslint/golangci-lint)
- ✓ TDD specifications satisfied

Run validation:
```bash
# Git status check
git status --porcelain

# Test execution (language-specific)
pytest tests/ --cov  # Python
npm test            # TypeScript
go test ./...       # Go

# Type checking (if applicable)
mypy src/           # Python
tsc --noEmit        # TypeScript

# Linting (if applicable)
flake8 src/         # Python
eslint src/         # TypeScript
golangci-lint run   # Go
```

If validation fails:
```
⚠ Quality Gate Failure: Implementation

Issues:
- Uncommitted changes: 3 files modified
  - src/api/client.py
  - tests/test_retry.py
  - README.md
- Tests failing: 2/15 failed
  - test_retry_exponential_backoff
  - test_max_retries_exceeded
- mypy errors: 1 type safety issue in src/api/client.py:42

Resolution:
1. Commit all changes: git add . && git commit -m "..."
2. Fix failing tests
3. Address type safety issues
4. Re-run /wrap

OR use --skip-checks to wrap anyway (not recommended)

Continue wrap? [y/n]:
```

#### Validation Phase (if qa was last_agent)

**Test Plan Quality Gate**:
- ✓ Test Plan exists
- ✓ All PRD acceptance criteria validated
- ✓ Edge cases covered
- ✓ Performance tested (if applicable)
- ✓ All defects resolved or documented

If Test Plan incomplete:
```
⚠ Quality Gate Failure: Validation

Issues:
- Test Plan shows 2 open defects:
  - DEF-001: Theme not persisted on logout (Critical)
  - DEF-002: Flash of wrong theme (Medium)
- 1 acceptance criterion not tested:
  - "Theme preference syncs across devices"

Resolution:
1. Address critical defects before wrapping
2. Document medium/low defects as known issues
3. Complete validation of all acceptance criteria
4. Re-run /wrap

OR use --skip-checks to wrap anyway (not recommended)

Continue wrap? [y/n]:
```

### 3. Optional: Invoke QA for Final Review

If `last_agent` is not `qa-adversary`, offer final QA review:

```
All quality gates passed.

Final QA review before wrapping? [y/n]:
```

If yes, invoke QA Adversary via Task tool:
```markdown
Act as **QA Adversary**.

Perform final production readiness review for session: {initiative}

Artifacts:
{list all artifacts}

Complexity: {complexity}
Phase: {current_phase}

Validate:
1. All PRD acceptance criteria met
2. Code quality and test coverage adequate
3. No critical defects or blockers
4. Documentation complete
5. Production deployment readiness

Produce Test Plan at /docs/testing/TP-{slug}.md if not exists.
Report any issues that should block session wrap.
```

Wait for QA response. If issues found, abort wrap and surface defects.

### 4. Generate Session Summary

Create comprehensive session summary:

```markdown
# Session Summary: {initiative}

**Session ID**: {session_id}
**Started**: {created_at}
**Completed**: {now}
**Duration**: {created_at → now}
**Complexity**: {complexity}
**Team**: {active_team}

## Accomplishments

Initiative: {initiative}

Artifacts delivered:
- ✓ PRD: /docs/requirements/PRD-{slug}.md
- ✓ TDD: /docs/design/TDD-{slug}.md
- ✓ ADRs: {count} architecture decisions
  {list ADR files}
- ✓ Implementation: {count} files, {LOC} lines
  {list main code files}
- ✓ Tests: {count} tests, {coverage}% coverage
- ✓ Test Plan: /docs/testing/TP-{slug}.md

## Key Decisions

Architecture Decisions:
{list ADRs with one-line summaries}

Implementation Decisions:
{list from SESSION_CONTEXT handoff notes or commit messages}

## Quality Metrics

- PRD Quality Gate: ✓ Passed
- TDD Quality Gate: ✓ Passed
- Code Quality Gate: ✓ Passed
- Validation Quality Gate: ✓ Passed

Test Results:
- Unit tests: {passed}/{total} passed
- Integration tests: {passed}/{total} passed
- Coverage: {percentage}%

Static Analysis:
- Type safety: {mypy/tsc result}
- Linting: {flake8/eslint/golangci-lint result}

## Session Workflow

Agent transitions:
{chronological list of handoffs from SESSION_CONTEXT}

Total handoffs: {handoff_count}
Park/resume cycles: {resume_count}

## Blockers Resolved

{list from SESSION_CONTEXT blockers array, marked as resolved}

## Open Questions Answered

{list from SESSION_CONTEXT open questions}

## Next Session Starting Point

Recommended next steps:
1. {suggestion based on session outcome}
2. {suggestion based on session outcome}
3. {suggestion based on session outcome}

Potential follow-up initiatives:
- {related work identified during session}
- {scope deferred from this session}
- {technical debt to address}

## Session Metadata

- Sessions started: 1
- Parks: {resume_count or 0}
- Handoffs: {handoff_count}
- Team switches: {count team changes}
- Total time active: {created_at → now minus park durations}
```

### 5. Archive or Delete SESSION_CONTEXT

If `--archive` (default):
- Move session directory to `.claude/.archive/sessions/{session_id}/`
- Preserve full session history for auditing

If not `--archive`:
- Delete session directory `.claude/sessions/{session_id}/`
- Session state removed (summary still available)

Create archive directory if needed:
```bash
mkdir -p .claude/.archive
```

### 6. Save Session Summary

Write session summary to:
```
/docs/sessions/SUMMARY-{session_id}.md
```

Create directory if needed:
```bash
mkdir -p /docs/sessions
```

### 7. Update Session Index

If `/docs/sessions/INDEX.md` exists, append entry:

```markdown
| Date | Session ID | Initiative | Complexity | Duration | Artifacts |
|------|------------|------------|------------|----------|-----------|
| 2025-12-24 | session-20251224-100000 | {initiative} | {complexity} | {duration} | PRD, TDD, Code, Tests |
```

If index doesn't exist, create it with header:

```markdown
# Session Index

Historical record of all completed work sessions.

| Date | Session ID | Initiative | Complexity | Duration | Artifacts |
|------|------------|------------|------------|----------|-----------|
| 2025-12-24 | session-20251224-100000 | {initiative} | {complexity} | {duration} | PRD, TDD, Code, Tests |
```

### 8. Confirmation

Display confirmation message:

```
Session wrapped: {initiative}

Duration: {created_at → now}
Quality gates: All passed ✓

Artifacts delivered:
✓ PRD, TDD, 2 ADRs, Implementation, Tests, Test Plan

Session summary: /docs/sessions/SUMMARY-{session_id}.md
Archived context: .claude/.archive/SESSION_CONTEXT-{session_id}.md

Next session starting point:
1. {first recommendation}
2. {second recommendation}

To start new session: /start
To view all sessions: cat /docs/sessions/INDEX.md
```

---

## State Changes

### Files Created

- `/docs/sessions/SUMMARY-{session_id}.md` - Session summary report
- `/docs/sessions/INDEX.md` - Session index (if first wrap)
- `.claude/.archive/sessions/{session_id}/` - Archived session directory (if --archive)

### Files Modified

- `/docs/sessions/INDEX.md` - New entry appended

### Files Deleted

- `.claude/sessions/{session_id}/` - Session directory removed or moved to archive

---

## Examples

### Example 1: Simple Wrap (SCRIPT Complexity)

```bash
/wrap
```

Output:
```
Running quality gates...

✓ PRD Quality Gate: Passed
  - PRD complete: /docs/requirements/PRD-api-retry.md
  - Acceptance criteria testable: 3/3
  - No blocking questions

✓ Code Quality Gate: Passed
  - Git status: Clean (all changes committed)
  - Tests: 8/8 passing
  - Type safety: mypy clean
  - Linting: flake8 clean

All quality gates passed ✓

Session wrapped: Add retry logic to API client

Duration: 4 hours
Quality gates: All passed ✓

Artifacts delivered:
✓ PRD, Implementation (1 file, 85 LOC), Tests (8 tests)

Session summary: /docs/sessions/SUMMARY-session-20251224-100000.md

Next session starting point:
1. Monitor retry behavior in production logs
2. Consider adding retry metrics/observability
3. Document retry configuration in operations guide

To start new session: /start
```

### Example 2: Wrap with Quality Gate Failure

```bash
/wrap
```

Output:
```
Running quality gates...

✓ PRD Quality Gate: Passed
✓ TDD Quality Gate: Passed
⚠ Code Quality Gate: Failed

Issues:
- Uncommitted changes: 2 files
  - src/theme/toggle.py (modified)
  - tests/test_toggle.py (modified)
- Tests: 14/15 passing (1 failed)
  - FAILED: test_theme_persistence_on_logout

Resolution:
1. Commit changes: git add . && git commit
2. Fix failing test: test_theme_persistence_on_logout
3. Re-run /wrap

Continue wrap anyway? [y/n]: n

Wrap aborted. Fix issues and retry.

Current status:
- Phase: implementation
- Last agent: principal-engineer
- Next: Fix failing test and commit changes

Commands:
- /park - Save state while fixing
- /handoff - Get help from another agent
```

### Example 3: Wrap with Skip Checks

```bash
/wrap --skip-checks
```

Output:
```
⚠ Skipping quality gates (--skip-checks flag)

This is not recommended. Quality issues may exist in deliverables.

Continue wrap without validation? [y/n]: y

Session wrapped: Multi-tenant authentication

Duration: 2 days
⚠ Quality gates: SKIPPED

Artifacts delivered:
✓ PRD, TDD, 3 ADRs, Implementation, Tests

⚠ Warning: Session wrapped without quality validation.
Review artifacts manually before considering production-ready.

Session summary: /docs/sessions/SUMMARY-session-20251223-140000.md

To start new session: /start
```

### Example 4: Wrap with Final QA Review

```bash
/wrap
```

Output:
```
Running quality gates...

✓ PRD Quality Gate: Passed
✓ TDD Quality Gate: Passed
✓ Code Quality Gate: Passed

All quality gates passed ✓

Last agent: principal-engineer

Final QA review before wrapping? [y/n]: y

Invoking QA Adversary for production readiness review...

[QA Adversary performs review]

✓ QA Review Complete
  - All acceptance criteria validated
  - Edge cases tested
  - Performance acceptable
  - No critical defects
  - Production ready ✓

Test Plan created: /docs/testing/TP-dark-mode.md

Session wrapped: Add dark mode toggle

Duration: 1 day
Quality gates: All passed ✓
QA Review: Production ready ✓

Artifacts delivered:
✓ PRD, TDD, 2 ADRs, Implementation, Tests (15 tests, 94% coverage), Test Plan

Session summary: /docs/sessions/SUMMARY-session-20251224-090000.md

Next session starting point:
1. Deploy dark mode feature to staging
2. Monitor user adoption metrics
3. Consider extending to mobile app

To start new session: /start
```

---

## Prerequisites

- Active session exists (`.claude/sessions/{session_id}/SESSION_CONTEXT.md`)
- Quality gates passing (unless `--skip-checks`)
- All artifacts present and complete

---

## Success Criteria

- All quality gates pass (or explicitly skipped)
- Session summary generated with complete metadata
- SESSION_CONTEXT archived or deleted
- Session index updated
- User receives clear next steps

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| No active session | No session for current project | Session already completed or never started |
| Quality gates failing | Artifacts incomplete or invalid | Fix issues, re-run wrap, or use --skip-checks |
| Session parked | `parked_at` field set | Use `/resume` first, then `/wrap` |
| Git dirty | Uncommitted changes | Commit changes or use --skip-checks |
| Tests failing | Test suite errors | Fix tests or use --skip-checks |

---

## Related Commands

- `/start` - Begin new session
- `/park` - Pause session (must resume before wrapping)
- `/status` - Check session state before wrapping
- `/handoff` - Fix issues with specific agent before wrapping

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Quality gates and lifecycle
- [documentation](../documentation/SKILL.md) - Artifact quality gates (PRD, TDD, ADR, Test Plan)

---

## Agent Delegation

This command optionally uses the Task tool to invoke:

- **QA Adversary** - For final production readiness review (if last_agent != qa)

Quality gate validation is automated (no agent invocation), but final QA review is delegated to QA Adversary agent for comprehensive validation.

---

## Design Notes

### Why Quality Gates?

Quality gates prevent:
1. **Incomplete work**: Wrapping before artifacts are production-ready
2. **Technical debt**: Shipping without tests, docs, or type safety
3. **Scope creep**: Closing sessions with unresolved blockers
4. **Knowledge loss**: Missing decisions or context in documentation

Gates ensure consistent quality across all sessions and teams.

### Why Allow --skip-checks?

Sometimes wrapping is necessary despite quality issues:
1. **Exploratory work**: Spikes/prototypes don't need full rigor
2. **External blockers**: Session can't complete but needs parking
3. **Emergency fixes**: Production incidents prioritize speed over process

`--skip-checks` is the escape hatch, but requires explicit intent.

### Why Archive by Default?

Archiving SESSION_CONTEXT preserves:
1. **Audit trail**: Full session history including park/resume cycles
2. **Debugging**: If issues arise later, session context helps root cause
3. **Process improvement**: Historical data for retrospectives
4. **Compliance**: Some orgs require work tracking for SOC2/ISO

Deletion (`--no-archive`) is available but discouraged unless sensitive data exists.

### Why Session Summaries?

Session summaries serve multiple audiences:
1. **Future self**: "What did I do in this session?"
2. **Team members**: "What changed and why?"
3. **Stakeholders**: "What was delivered?"
4. **Project managers**: "How long did this take?"

Summaries are the "commit message for a work session" - essential for long-term maintainability.

### Why Session Index?

The index provides:
1. **Discoverability**: Find all past sessions quickly
2. **Metrics**: Track session duration, complexity distribution
3. **Patterns**: Identify frequently revisited areas (tech debt indicators)
4. **History**: Chronological project evolution

It's the "git log for work sessions" - low overhead, high value.
