# Complete Workflow: Legacy Migration

> Migration workflow for moving code from a monolith to a new service

---

## Context

Migrating a payment processing module from a monolith to a new service.

## Session 1: Discovery

**Prompt:**
```
Act as the Requirements Analyst.

I'm migrating our payment processing from the legacy monolith.
Here's the current code:

{paste legacy payment code}

Create a PRD that:
1. Documents all current behavior as requirements (preserve these)
2. Identifies implicit behavior that should become explicit
3. Notes improvements to make during migration
4. Defines how we'll validate parity with legacy
```

**Expected Output:** PRD capturing:
- Current payment flows as FRs
- Edge cases discovered in legacy code
- Tech debt to address (e.g., better error handling)
- Acceptance criteria for parity testing

## Session 2: Migration Design

**Prompt:**
```
Act as the Architect.

PRD-0001 captures legacy behavior: /docs/requirements/PRD-0001-payment-migration.md

Design the migration:
1. Target architecture for new payment service
2. Adapter strategy for backward compatibility during transition
3. Data migration approach
4. Parallel running strategy
5. Rollback plan

Create ADRs for:
- Why we're migrating (ADR-0001)
- Target architecture choices (ADR-0002)
- Migration strategy (ADR-0003)
```

## Session 3: Phased Implementation

**Prompt:**
```
Act as the Principal Engineer.

Implement Phase 1 of the migration (from TDD-0001):
- New payment service with core processing logic
- Adapter that maintains legacy API compatibility
- Feature flag for gradual rollout

Don't migrate data yet—that's Phase 2.
```

## Session 4: Parity Validation

**Prompt:**
```
Act as the QA/Adversary.

We need to validate the new payment service matches legacy behavior.

Create a parity test plan:
1. Capture requests/responses from legacy system
2. Replay against new system
3. Compare results
4. Document any intentional differences (from PRD improvements section)

What test cases do we need to be confident in parity?
```

