---
name: hotfix-ref
description: "Rapid fix workflow for urgent production issues. Skip PRD, minimal TDD, focus on: diagnose → fix → test → ship. Triggers: /hotfix, urgent fix, production issue, emergency fix, quick fix."
---

# /hotfix - Rapid Fix Workflow

> **Category**: Development | **Phase**: Emergency Response | **Complexity**: Low

## Purpose

Execute a rapid fix workflow for urgent production issues, skipping heavyweight documentation in favor of speed while maintaining essential quality checks.

This command is optimized for time-critical situations where production is broken or degraded and a fast, focused fix is needed.

---

## Usage

```bash
/hotfix "issue-description" [--severity=LEVEL]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `issue-description` | Yes | - | What's broken and needs fixing |
| `--severity` | No | HIGH | CRITICAL \| HIGH \| MEDIUM |

---

## Behavior

### 1. Rapid Assessment

Quick diagnostic phase:

**Prompt user**:
- What's broken? (symptoms)
- Impact? (users affected, severity)
- Time constraint? (SLA, deadline)

**Auto-classify severity**:
- **CRITICAL**: Production down, data loss, security breach
- **HIGH**: Feature broken, performance degraded, errors increasing
- **MEDIUM**: Minor issue, workaround exists, low impact

### 2. Skip PRD (Intentional)

For hotfixes, **PRD is skipped** because:
- Time is critical
- Problem is concrete (not exploratory)
- Fix scope is narrow
- Risk of delay > risk of incomplete planning

**Document intent inline** in code/commit message instead.

### 3. Minimal TDD (Optional)

**Skip TDD by default** for hotfixes.

**Only create TDD if**:
- Severity is CRITICAL and fix involves architectural change
- Multiple systems affected (need coordination)
- Fix has cascading implications

**If TDD created**:
- Lightweight, 1-page max
- Focus on: root cause, fix approach, rollback plan
- Save to: `/docs/design/HOTFIX-{slug}.md`

### 4. Diagnose → Fix Workflow

**Invoke Principal Engineer** for the full cycle:

```markdown
Act as **Principal Engineer**.

HOTFIX MODE: Rapid fix required
Issue: {issue-description}
Severity: {CRITICAL|HIGH|MEDIUM}

Execute hotfix workflow:

1. DIAGNOSE (5-10 min)
   - Reproduce issue
   - Identify root cause
   - Confirm scope of fix

2. FIX (15-30 min)
   - Implement minimal fix
   - Focus on immediate resolution
   - Avoid scope creep

3. TEST (5-10 min)
   - Verify fix resolves issue
   - Test critical paths
   - Quick regression check

4. DOCUMENT (2-5 min)
   - Add inline comments explaining fix
   - Note any technical debt created
   - Document rollback steps

Deliverables:
- Fix implementation
- Tests (minimal but critical)
- Inline documentation
- Rollback plan

Time budget: 30-60 minutes total
```

### 5. Fast QA Validation

**Invoke QA Adversary** for rapid validation:

```markdown
Act as **QA/Adversary**.

HOTFIX VALIDATION (Fast Track)
Issue: {issue-description}
Fix: {code-locations}
Severity: {severity}

Execute rapid validation:

1. Verify fix resolves the reported issue
2. Quick smoke test of critical paths
3. Check for obvious regressions
4. Validate rollback plan exists

Time budget: 10-15 minutes

If critical defects found: BLOCK deployment
If minor issues found: Document as follow-up tasks
If passes: Approve for immediate deployment
```

### 6. Ship Checklist

Before considering hotfix complete:

**Required**:
- [ ] Issue reproduced and root cause identified
- [ ] Fix implemented and tested
- [ ] Critical paths still working
- [ ] Rollback plan documented
- [ ] Commit message explains what/why

**Optional** (if time permits):
- [ ] Monitoring/alerting in place
- [ ] Runbook updated
- [ ] Follow-up task created for proper fix
- [ ] Post-mortem scheduled

### 7. Hotfix Summary

Display completion summary:

```
Hotfix Complete: {issue-description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Severity: {severity}
Time to fix: {elapsed-time}

Artifacts:
✓ Fix: {implementation-files}
✓ Tests: {test-files}
✓ Rollback plan: {location or inline}

Quality Checks:
✓ Issue resolved
✓ Smoke tests passing
✓ Rollback plan documented

Ready for deployment.

⚠ Follow-up required:
- Create proper fix with full PRD/TDD workflow
- Schedule post-mortem (if CRITICAL severity)
- Review and refactor hotfix code
```

---

## Workflow

```mermaid
graph LR
    A[/hotfix invoked] --> B[Assess severity]
    B --> C{Critical?}
    C -->|Yes| D[Minimal TDD]
    C -->|No| E[Skip TDD]
    D --> F[Diagnose]
    E --> F
    F --> G[Fix]
    G --> H[Test]
    H --> I[Fast QA]
    I --> J{Pass?}
    J -->|No| K[Block/Fix]
    K --> G
    J -->|Yes| L[Ship]
```

---

## Deliverables

Minimal deliverables for speed:

1. **Fix implementation**: Focused code changes
2. **Tests**: Critical path coverage (minimal)
3. **Inline docs**: Comments explaining fix
4. **Rollback plan**: How to undo if needed
5. **Commit message**: Clear explanation of what/why

**NOT produced** (intentionally skipped):
- PRD (too slow for hotfix)
- Full TDD (unless CRITICAL severity)
- Comprehensive test suite (defer to follow-up)
- ADRs (unless architectural change)

---

## Examples

### Example 1: Critical Production Issue

```bash
/hotfix "API returning 500 errors on login endpoint" --severity=CRITICAL
```

Output:
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

### Example 2: High Severity Performance Issue

```bash
/hotfix "Dashboard load time increased from 200ms to 5s"
```

Output:
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

### Example 3: Medium Severity Bug

```bash
/hotfix "Email notifications showing wrong timestamp"
```

Output:
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

## When to Use vs Alternatives

| Use /hotfix when... | Use alternative when... |
|---------------------|-------------------------|
| Production is broken | Non-urgent → Use `/task` |
| Time is critical (< 1 hour) | Can take hours/days → Use `/task` |
| Issue is well-defined | Unclear problem → Use `/spike` |
| Need immediate resolution | Planning new feature → Use `/task` or `/sprint` |

### /hotfix vs /task

- `/hotfix`: Skip PRD/TDD, minimal QA, 30-60 min
- `/task`: Full workflow, all quality gates, hours/days

### /hotfix vs /spike

- `/hotfix`: MUST produce production fix
- `/spike`: NO production code, research only

### When NOT to use /hotfix

**Don't use /hotfix for**:
- New features (not urgent, use `/task`)
- Exploratory work (use `/spike`)
- Refactoring (not urgent, use `/task`)
- "Would be nice" fixes (use `/task`)

**Only use /hotfix for**:
- Production broken or severely degraded
- Users actively impacted
- Time-sensitive fixes
- Clear problem with focused solution

---

## Complexity Level

**LOW** - This command:
- Skips heavy documentation
- Focuses on single problem
- Minimal agent coordination
- Time-boxed execution

**Recommended for**:
- Production incidents
- Urgent bug fixes
- Performance degradations
- Security patches

**Not recommended for**:
- Feature development
- Architectural changes (unless truly urgent)
- Anything that can wait for proper `/task` workflow

---

## State Changes

### Files Created

| File Type | Location | Condition |
|-----------|----------|-----------|
| Fix code | Project-specific | Always |
| Tests | Project-specific | Always (minimal) |
| Hotfix TDD | `/docs/design/HOTFIX-{slug}.md` | Only if CRITICAL |
| Migration | Project-specific | If DB changes |
| Rollback script | Inline or separate file | Always documented |

### No Heavy Artifacts

Intentionally NOT created:
- ❌ PRD
- ❌ Full TDD (unless CRITICAL)
- ❌ ADRs (unless architectural)
- ❌ Comprehensive test plan

These can be created in follow-up `/task` if needed.

---

## Prerequisites

- 10x-dev-pack active (or at minimum: Engineer + QA agents)
- Clear understanding of the issue
- Access to production logs/monitoring (for diagnosis)

---

## Success Criteria

- Issue resolved in < 60 minutes
- Critical paths tested and working
- Rollback plan documented
- Code committed with clear message
- Follow-up task created (if needed)

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Can't reproduce issue | Insufficient information | Escalate, gather more data, may need `/task` |
| Fix too complex | Requires architectural change | Abort hotfix, use `/task` with full workflow |
| QA validation fails | Fix doesn't resolve issue | Iterate quickly or escalate |
| Time budget exceeded | Fix taking > 60 min | Re-assess: Continue or escalate to `/task` |

---

## Related Commands

- `/task` - Proper fix with full workflow (use for follow-up)
- `/spike` - Research if root cause unclear
- `/sprint` - Multi-fix coordination (if multiple related hotfixes)
- `/start` - Session initialization (not needed for hotfix)

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination (simplified for hotfix)
- [standards](../standards/SKILL.md) - Code quality (relaxed for hotfix, enforce in follow-up)

---

## Notes

### Time Budget Philosophy

Hotfixes are strictly time-boxed:

| Severity | Target Time | Max Time |
|----------|-------------|----------|
| CRITICAL | 30 min | 60 min |
| HIGH | 45 min | 90 min |
| MEDIUM | 30 min | 60 min |

**If exceeding max time**: Stop and escalate to full `/task` workflow.

### Technical Debt Awareness

Hotfixes often create technical debt:

- Quick fixes may not be optimal
- Test coverage may be incomplete
- Documentation may be minimal

**Always create follow-up task**:

```bash
# After hotfix completes
/task "Proper fix for {issue}" --complexity=MODULE
```

This ensures hotfix is revisited with full workflow.

### Rollback Plan Requirements

Every hotfix MUST have rollback plan:

**Minimum rollback documentation**:
- Git commit to revert: `git revert {commit-hash}`
- DB migrations to undo (if applicable)
- Config changes to reverse (if applicable)
- Feature flags to toggle (if applicable)

**Document in**:
- Commit message
- Inline code comments
- Separate ROLLBACK.md (for complex fixes)

### Post-Mortem Trigger

For CRITICAL severity hotfixes:

**Automatically schedule post-mortem**:
- What happened?
- Why did it happen?
- How was it fixed?
- How do we prevent recurrence?

Create calendar event or task tracker item.

---

## Hotfix vs Emergency Change

**Hotfix** (use `/hotfix`):
- Code/config change
- Deployed through normal pipeline (fast-tracked)
- Tests run (minimal but required)
- Code review (optional but recommended)

**Emergency Change** (use manual process):
- Infrastructure change (restart service, scale up)
- Bypass normal pipeline
- No code changes
- Ops team handles

Use `/hotfix` for code fixes, not ops interventions.

---

## Integration with Git

Recommended git workflow for hotfixes:

```bash
# Create hotfix branch
git checkout -b hotfix/login-500-error

# Make fix
/hotfix "API returning 500 on login"

# Commit (done by Principal Engineer during /hotfix)
# Message should include: what, why, rollback

# Push and create PR
git push origin hotfix/login-500-error
gh pr create --title "HOTFIX: Fix login 500 error" --body "..."

# Fast-track review and merge
# Deploy immediately
```

For CRITICAL fixes, consider:
- Merge directly to main (skip PR if necessary)
- Deploy immediately
- Create PR retroactively for audit trail

---

## Quality vs Speed Tradeoff

`/hotfix` intentionally trades some quality for speed:

| Aspect | /task | /hotfix |
|--------|-------|---------|
| PRD | Required | Skipped |
| TDD | MODULE+ | Only if CRITICAL |
| Test coverage | Comprehensive | Critical paths only |
| Code review | Always | Optional (fast-track) |
| Documentation | Full | Inline comments |
| Time to deploy | Hours/days | < 60 min |

**Post-hotfix**: Use `/task` to "do it right" with full quality gates.

---

## Monitoring and Alerting

After hotfix deployed:

**Verify fix in production**:
- [ ] Metrics show issue resolved
- [ ] Error rates back to normal
- [ ] Performance metrics acceptable
- [ ] No new errors introduced

**Set up alerting** (if not exists):
- Alert if issue recurs
- Monitor related metrics
- Track success rate

This prevents hotfix from being a band-aid on recurring issue.

---

## Example Commit Message

Good hotfix commit message:

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

This gives enough context for code review and future debugging.
