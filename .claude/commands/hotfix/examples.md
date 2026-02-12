---
user-invocable: false
---

# /hotfix Examples

> Usage scenarios with sample outputs.

## Example 1: Critical Production Issue

**Command**:
```bash
/hotfix "API returning 500 errors on login endpoint" --severity=CRITICAL
```

**Output**:
```
HOTFIX MODE: CRITICAL
Issue: API returning 500 errors on login endpoint
Time budget: 60 minutes

[DIAGNOSE - 8 min]
✓ Issue reproduced
✓ Root cause: Null pointer in JWT validation
✓ Scope: Single endpoint, affects all users

[FIX - 12 min]
✓ Added null check in jwt-validator.ts
✓ Added defensive guard clause
✓ Code: /src/auth/jwt-validator.ts (5 lines changed)

[TEST - 7 min]
✓ Login working with valid tokens
✓ Graceful error with invalid tokens
✓ Quick regression: Logout, refresh endpoints OK

[QA VALIDATION - 10 min]
✓ Issue resolved: Login working
✓ Smoke tests: All auth endpoints functional
✓ No obvious regressions detected
✓ Rollback plan: Revert commit abc123

Total time: 37 minutes
Status: READY FOR DEPLOYMENT

⚠ Follow-up:
- Create /task "Improve JWT validation error handling"
- Add comprehensive test coverage
- Review all null pointer risks in auth module
```

---

## Example 2: High Severity Performance Issue

**Command**:
```bash
/hotfix "Dashboard load time increased from 200ms to 5s"
```

**Output**:
```
HOTFIX MODE: HIGH
Issue: Dashboard load time increased from 200ms to 5s
Time budget: 45 minutes

[DIAGNOSE - 15 min]
✓ Profiled dashboard query
✓ Root cause: Missing database index on user_activity table
✓ Scope: Dashboard only, degraded UX but functional

[FIX - 10 min]
✓ Added index: CREATE INDEX idx_user_activity_date ON user_activity(created_at)
✓ Migration: /migrations/20251224_add_activity_index.sql
✓ Tested on staging

[TEST - 8 min]
✓ Dashboard load time: 180ms (back to normal)
✓ Query plan verified: Index being used
✓ Checked other queries: No negative impact

[QA VALIDATION - 8 min]
✓ Performance restored
✓ Quick regression: Other dashboards unaffected
✓ Rollback: DROP INDEX script provided

Total time: 41 minutes
Status: READY FOR DEPLOYMENT

Follow-up:
- Audit all high-traffic queries for missing indexes
- Add performance regression tests
```

---

## Example 3: Medium Severity Bug

**Command**:
```bash
/hotfix "Email notifications showing wrong timestamp"
```

**Output**:
```
HOTFIX MODE: MEDIUM
Issue: Email notifications showing wrong timestamp
Time budget: 30 minutes

[DIAGNOSE - 5 min]
✓ Issue: Timezone not being applied to email templates
✓ Root cause: Template using UTC instead of user timezone

[FIX - 8 min]
✓ Updated email template to use user.timezone
✓ File: /templates/email/notification.hbs
✓ Added helper function: formatWithTimezone()

[TEST - 5 min]
✓ Email sent with correct timezone (PST, EST tested)
✓ Quick check: All email types rendering correctly

[QA VALIDATION - 6 min]
✓ Timestamp now showing user's local time
✓ Edge case: Null timezone defaults to UTC (acceptable)
✓ Rollback: Revert template changes

Total time: 24 minutes
Status: READY FOR DEPLOYMENT

No critical follow-up needed (fix is complete).
```

---

## Edge Case Examples

### Edge Case: Can't Reproduce Issue

**Scenario**: User runs `/hotfix "Intermittent 404 on checkout"` but issue doesn't occur.

**Behavior**:
```
HOTFIX MODE: HIGH
Issue: Intermittent 404 on checkout
Time budget: 45 minutes

[DIAGNOSE - 20 min]
✗ Unable to reproduce issue
- Attempted reproduction in staging: No 404s
- Checked production logs: No recent 404s on checkout
- Checked monitoring: No errors reported

Error: Cannot reproduce issue

Resolution:
- Insufficient information to proceed with hotfix
- Gather more data:
  - Production logs with timestamps
  - User agents/browsers affected
  - URL patterns causing 404
  - Recent deploys or config changes

Recommendation: Escalate to /task for proper investigation
```

**Notes**: If issue can't be reproduced quickly, abort hotfix and use full `/task` workflow with proper investigation.

---

### Edge Case: Fix Too Complex

**Scenario**: User runs `/hotfix "Memory leak in worker pool"` but root cause requires architectural change.

**Behavior**:
```
HOTFIX MODE: CRITICAL
Issue: Memory leak in worker pool
Time budget: 60 minutes

[DIAGNOSE - 25 min]
✓ Issue reproduced: Memory grows unbounded
✓ Root cause: Workers not being released after task completion
✓ Scope: Entire worker pool architecture

[ASSESSMENT]
✗ Fix requires architectural change to worker lifecycle
✗ Current architecture doesn't support proper cleanup
✗ Band-aid fix would create more tech debt

Error: Fix too complex for hotfix workflow

Resolution:
- Abort hotfix (too risky for time-boxed approach)
- Immediate mitigation: Restart workers every hour (workaround)
- Create /task "Redesign worker pool lifecycle" with full PRD/TDD
- Schedule emergency review of worker architecture

Recommendation: Use /task with MODULE complexity for proper fix
```

**Notes**: Some issues can't be hotfixed safely. Recognize when to abort and use proper workflow.

---

### Edge Case: Time Budget Exceeded

**Scenario**: User runs `/hotfix "Race condition in cache invalidation"` but diagnosis takes longer than expected.

**Behavior**:
```
HOTFIX MODE: HIGH
Issue: Race condition in cache invalidation
Time budget: 45 minutes

[DIAGNOSE - 45 min]
✓ Issue reproduced intermittently
✓ Root cause: Race between cache update and invalidation
✗ Multiple components involved (cache, queue, API)

Warning: Time budget exceeded (45/45 min)

Assessment:
- Diagnosis complete but fix is complex
- Multiple components need coordination
- Risk of introducing new race conditions

Recommendation: Escalate to /task
- Document findings in /docs/investigations/
- Create /task "Fix cache invalidation race condition"
- Apply temporary workaround: Disable cache for affected endpoint

Status: HOTFIX ABORTED (escalated to /task)
```

**Notes**: If time budget is exceeded before fix is complete, stop and escalate. Document findings for next phase.

---

## Example Commit Message

**Good hotfix commit message**:

```
HOTFIX: Fix null pointer in JWT validation causing login 500s

Problem:
- Login endpoint returning 500 errors
- Affecting all users since deploy at 2pm
- Root cause: Null check missing in jwt-validator.ts

Solution:
- Added null guard clause before accessing token.claims
- Returns 401 Unauthorized instead of crashing

Testing:
- Verified login works with valid tokens
- Verified graceful error with invalid tokens
- Quick regression on other auth endpoints

Rollback:
- git revert abc123def
- No DB changes, safe to rollback immediately

Follow-up:
- Task #1234: Comprehensive JWT validation improvements
- Add full test coverage for auth edge cases
```

**This gives enough context for code review and future debugging.**
