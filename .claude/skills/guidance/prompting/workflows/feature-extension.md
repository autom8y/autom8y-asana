# Complete Workflow: Extend Existing Feature

> Adding capability to an existing, documented system

---

## Context

Adding password reset to existing auth system.

## Session 1: Requirements

**Prompt:**
```
Act as the Requirements Analyst.

Check /docs/INDEX.md for existing artifacts.
We have existing auth (PRD-0001, TDD-0001).

I need to add password reset:
- User requests reset with email
- System sends reset link
- User clicks link and sets new password

Should this be:
A) Amendment to PRD-0001
B) New PRD-0002 that references PRD-0001

Help me decide, then create the appropriate document.
```

**Expected Output:** Analysis that this should be PRD-0002 (new capability, not change to existing), then new PRD created with:
- References to PRD-0001 for context
- New requirements for reset flow
- Integration points with existing auth

## Session 2: Design Extension

**Prompt:**
```
Act as the Architect.

PRD-0002 approved: /docs/requirements/PRD-0002-password-reset.md

This extends existing auth (TDD-0001).

Create TDD-0002 that:
- References TDD-0001 for existing components
- Adds new components (ResetTokenService, email integration)
- Defines how new components integrate with existing AuthService
- Creates ADR for reset token strategy (separate from JWT?)
```

---

## Decision Framework: Amend vs. New Document

| Situation | Decision |
|-----------|----------|
| Bug fix or clarification | Amend existing |
| New user-facing capability | New document |
| Significant scope increase | New document |
| Changes existing acceptance criteria | New document + deprecate old |

