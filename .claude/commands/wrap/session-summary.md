---
user-invocable: false
---

# Session Summary Template

> Template for wrap-generated session summaries.

## Template

```markdown
# Session Summary: {initiative}

**Session ID**: {session_id}
**Started**: {created_at}
**Completed**: {now}
**Duration**: {total duration}
**Complexity**: {complexity}
**Rite**: {active_rite}

## Accomplishments

Initiative: {initiative}

Artifacts delivered:
- ✓ PRD: /docs/requirements/PRD-{slug}.md
- ✓ TDD: /docs/design/TDD-{slug}.md
- ✓ ADRs: {count} architecture decisions
- ✓ Implementation: {count} files, {LOC} lines
- ✓ Tests: {count} tests, {coverage}% coverage
- ✓ Test Plan: /docs/testing/TP-{slug}.md

## Key Decisions

Architecture Decisions:
{list ADRs with one-line summaries}

Implementation Decisions:
{list from handoff notes or commits}

## Quality Metrics

- PRD Quality Gate: ✓ Passed
- TDD Quality Gate: ✓ Passed
- Code Quality Gate: ✓ Passed
- Validation Quality Gate: ✓ Passed

Test Results:
- Unit tests: {passed}/{total}
- Integration tests: {passed}/{total}
- Coverage: {percentage}%

Static Analysis:
- Type safety: {result}
- Linting: {result}

## Session Workflow

Agent transitions:
{chronological list of handoffs}

Total handoffs: {handoff_count}
Park/resume cycles: {resume_count}

## Blockers Resolved

{list from SESSION_CONTEXT, marked resolved}

## Open Questions Answered

{list from SESSION_CONTEXT}

## Next Session Starting Point

Recommended next steps:
1. {suggestion}
2. {suggestion}
3. {suggestion}

Potential follow-up initiatives:
- {related work identified}
- {scope deferred}
- {technical debt}

## Session Metadata

- Parks: {resume_count}
- Handoffs: {handoff_count}
- Rite switches: {count}
- Total time active: {active duration}
```

---

## Field Sources

| Field | Source |
|-------|--------|
| session_id | SESSION_CONTEXT.session_id |
| created_at | SESSION_CONTEXT.created_at |
| duration | created_at → now |
| complexity | SESSION_CONTEXT.complexity |
| artifacts | SESSION_CONTEXT.artifacts array |
| handoff_count | SESSION_CONTEXT.handoff_count |
| resume_count | SESSION_CONTEXT.resume_count |
| ADRs | Scan /docs/decisions/ |
| Test results | Run test suite |

---

## Summary Location

```
/docs/sessions/SUMMARY-{session_id}.md
```

---

## Index Entry Format

```markdown
| Date | Session ID | Initiative | Complexity | Duration | Artifacts |
|------|------------|------------|------------|----------|-----------|
| 2025-12-24 | session-20251224-100000 | {initiative} | {complexity} | {duration} | PRD, TDD, Code |
```
