---
user-invocable: false
---

# /wrap Examples

> Usage scenarios for completing work sessions.

## Example 1: Simple Wrap (SCRIPT Complexity)

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
  - Git status: Clean
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

To start new session: /start
```

---

## Example 2: Wrap with Quality Gate Failure

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

---

## Example 3: Wrap with Skip Checks

```bash
/wrap --skip-checks
```

Output:
```
⚠ Skipping quality gates (--skip-checks flag)

This is not recommended. Quality issues may exist.

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

---

## Example 4: Wrap with Final QA Review

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
✓ PRD, TDD, 2 ADRs, Implementation, Tests (94% coverage), Test Plan

Session summary: /docs/sessions/SUMMARY-session-20251224-090000.md

Next session starting point:
1. Deploy dark mode feature to staging
2. Monitor user adoption metrics

To start new session: /start
```
