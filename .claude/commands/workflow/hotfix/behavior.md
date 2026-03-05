---
user-invocable: false
---

# /hotfix Behavior Specification

> Full step-by-step sequence for rapid fix workflow.

## Behavior Sequence

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
- Save to: `.ledge/specs/HOTFIX-{slug}.md`

### 4. Diagnose → Fix Workflow

Apply Agent Invocation Pattern:
- Agent: Principal Engineer
- Mode: "HOTFIX MODE (Rapid fix required)"

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

## Workflow Diagram

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

## State Changes

### Files Created

| File Type | Location | Condition |
|-----------|----------|-----------|
| Fix code | Project-specific | Always |
| Tests | Project-specific | Always (minimal) |
| Hotfix TDD | `.ledge/specs/HOTFIX-{slug}.md` | Only if CRITICAL |
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

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Can't reproduce issue | Insufficient information | Escalate, gather more data, may need `/task` |
| Fix too complex | Requires architectural change | Abort hotfix, use `/task` with full workflow |
| QA validation fails | Fix doesn't resolve issue | Iterate quickly or escalate |
| Time budget exceeded | Fix taking > 60 min | Re-assess: Continue or escalate to `/task` |

---

## Design Notes

### Time Budget Philosophy

Apply Time-Boxing Pattern:
- Severity-based time limits
- Checkpoints at intervals
- Hard stop at max time

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

### Quality vs Speed Tradeoff

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
