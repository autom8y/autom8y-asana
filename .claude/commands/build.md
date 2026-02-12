---
name: build
description: "Implementation session from approved TDD. Use when: user says /build, wants to implement from existing design, code from TDD. Triggers: /build, implement design, code from TDD, build approved design."
argument-hint: "<feature-description>"
context: fork
---

# /build - Implementation from Approved TDD

Implement code from an approved TDD without re-doing the design phase. Assumes TDD already exists and has been reviewed.

## Behavior

### 1. Validate Prerequisites

Check that design artifacts exist:

```bash
find docs/design -name "TDD-*.md" | grep -i "{feature-slug}"
```

- **TDD not found**: Error. Suggest `/architect` first or `/task` for integrated workflow.
- **PRD not found**: Warn but proceed (TDD may be sufficient).

### 2. Invoke Principal Engineer

Delegate to Principal Engineer with the approved TDD:

```
Act as **Principal Engineer**.

Feature: {feature-description}
PRD: docs/requirements/PRD-{feature-slug}.md (if exists)
TDD: docs/design/TDD-{feature-slug}.md

Implement the solution following the approved TDD:

1. Read TDD thoroughly - this is your specification
2. Read PRD for acceptance criteria context
3. Follow project standards
4. Write tests first or alongside implementation
5. Implement with production quality (type safety, error handling, logging)
6. Verify all tests pass
7. Update implementation notes if you deviate from TDD

Guidelines:
- Build exactly what TDD specifies
- If TDD is ambiguous, document assumption in implementation ADR
- If TDD has design flaw, stop and escalate to Architect
- If acceptance criteria untestable, escalate to Analyst
```

**Quality gate**: Tests pass, code follows standards, TDD fully implemented.

### 3. Display Completion Summary

Show artifacts created (source files, test files, implementation ADRs) and suggest next steps: `/qa` to validate, `/commit`, or `/pr`.

## When to Use

| Use /build when | Use alternative when |
|-----------------|---------------------|
| TDD approved and exists | No TDD yet --> `/architect` first |
| Phased workflow (design then code) | Want integrated workflow --> `/task` |
| Design has been reviewed | Design + implementation together --> `/task` |

## Escalation

Engineer may escalate:
- **To Architect**: TDD ambiguous, design won't work as specified, interface contracts unclear
- **To Analyst**: Acceptance criteria untestable, requirements conflict

When escalation happens, implementation pauses. Re-run `/build` after fixes.
