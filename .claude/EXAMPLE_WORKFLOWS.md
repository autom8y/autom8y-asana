# Example Workflows

> Concrete examples showing the skeleton in action. Copy and adapt these patterns.

---

## Example 1: New Feature (User Authentication)

### Context
Starting a new project that needs user authentication.

### Session 1: Requirements

**Prompt:**
```
Read .claude/CLAUDE.md and .claude/PROJECT_CONTEXT.md.

Act as the Requirements Analyst.

I need user authentication for my API. Users should be able to:
- Register with email/password
- Login and receive a token
- Access protected endpoints with that token

Create PRD-0001 for this feature.
```

**Expected Output:** PRD with clear requirements, acceptance criteria like:
- FR-001: User can register with valid email and password (8+ chars)
- FR-002: User can login with correct credentials and receive JWT
- FR-003: Protected endpoints reject requests without valid token
- FR-004: Protected endpoints reject expired tokens

### Session 2: Design

**Prompt:**
```
Act as the Architect.

PRD-0001 is approved: /docs/requirements/PRD-0001-user-auth.md

Check /docs/decisions/ for existing ADRs (this is a new project, so none).

Create TDD-0001 with:
- Component design
- API contracts
- Data model
- Security considerations

Create ADRs for:
- Token format choice (JWT vs. opaque)
- Password hashing algorithm
- Session storage approach
```

**Expected Output:** 
- TDD with components (AuthService, UserRepository, AuthMiddleware)
- API specs for /register, /login endpoints
- ADR-0001: Use JWT for stateless auth
- ADR-0002: Use bcrypt for password hashing

### Session 3: Implementation

**Prompt:**
```
Act as the Principal Engineer.

Implement the design:
- TDD: /docs/design/TDD-0001-user-auth.md
- ADRs: ADR-0001 (JWT), ADR-0002 (bcrypt)

Follow CODE_CONVENTIONS.md and REPOSITORY_MAP.md.

Start with the domain layer (User entity, AuthService), 
then infrastructure (UserRepository), then API (routes).
```

### Session 4: Validation

**Prompt:**
```
Act as the QA/Adversary.

Implementation is complete:
- Code: /src/domain/services/auth_service.py, /src/api/routes/auth_router.py
- PRD: /docs/requirements/PRD-0001-user-auth.md
- TDD: /docs/design/TDD-0001-user-auth.md

Create TP-0001 and validate:
1. All acceptance criteria from PRD
2. Security: password not logged, tokens properly validated, timing attacks mitigated
3. Edge cases: duplicate email, invalid password format, expired token
```

---

## Example 2: Legacy Migration (Payment Processing)

### Context
Migrating a payment processing module from a monolith to a new service.

### Session 1: Discovery

**Prompt:**
```
Read .claude/CLAUDE.md and .claude/PROJECT_CONTEXT.md.

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

### Session 2: Migration Design

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

### Session 3: Phased Implementation

**Prompt:**
```
Act as the Principal Engineer.

Implement Phase 1 of the migration (from TDD-0001):
- New payment service with core processing logic
- Adapter that maintains legacy API compatibility
- Feature flag for gradual rollout

Don't migrate data yet—that's Phase 2.
```

### Session 4: Parity Validation

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

---

## Example 3: Quick Bug Fix

### Context
A bug was reported—login fails for emails with plus signs.

### Session (Abbreviated Flow)

**Prompt:**
```
Read .claude/CLAUDE.md.

This is a bug fix—abbreviated workflow.

Bug: Login fails for emails containing '+' (e.g., user+tag@example.com)
Expected: These are valid emails and should work
Actual: 400 error "invalid email format"

Relevant files:
- /src/api/models/auth_models.py (request validation)
- /src/domain/services/auth_service.py (login logic)

Act as Engineer: Find and fix the bug.
Then act as QA: Add a regression test.
```

**Expected Output:**
1. Root cause: Email regex too restrictive
2. Fix: Update regex or use proper email validation library
3. Test: `test_login_with_plus_sign_email_succeeds`

---

## Example 4: Exploratory Prototype

### Context
Exploring whether to use GraphQL instead of REST for a new feature.

### Session (Spike Mode)

**Prompt:**
```
This is exploratory—skip full workflow.

I want to explore: GraphQL vs REST for our analytics queries

Build two quick prototypes:
1. REST endpoint: GET /analytics/dashboard?date_from=X&date_to=Y
2. GraphQL query: dashboard(dateFrom, dateTo) { metrics { ... } }

Use real query logic from /src/domain/services/analytics_service.py

After building both, compare:
- Code complexity
- Query flexibility  
- Performance characteristics
- Client experience

Help me decide which to use for the full implementation.
```

**Expected Output:**
- Two prototype implementations
- Comparison analysis
- Recommendation with rationale
- If GraphQL chosen: Draft ADR for the decision

---

## Example 5: Adding Feature to Existing System

### Context
Adding password reset to existing auth system.

### Session 1: Requirements

**Prompt:**
```
Read .claude/CLAUDE.md and /docs/INDEX.md.

We have existing auth (PRD-0001, TDD-0001).

Act as the Requirements Analyst.

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

### Session 2: Design Extension

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

## Example 6: Refactoring (No Behavior Change)

### Context
Analytics service has grown too large—needs decomposition.

### Session

**Prompt:**
```
Read .claude/CLAUDE.md.

Act as the Architect, then Engineer.

/src/domain/services/analytics_service.py is 800 lines and does too much:
- Dashboard metrics
- Report generation  
- Data export
- Alert threshold checking

Design a decomposition:
1. What services should this become?
2. What's the dependency structure?
3. How do we migrate incrementally without breaking things?

Create ADR-0010 for the decomposition decision.
Then implement Phase 1 as Engineer.

Constraint: All existing tests must pass after each change.
No behavior changes—this is purely structural.
```

**Expected Output:**
- ADR documenting why we're splitting and how
- Phased migration plan
- Phase 1 implementation (extract first service)
- Verification that tests still pass

---

## Document Index After Examples

After running these examples, your /docs/INDEX.md might look like:

```markdown
# Documentation Index

## PRDs
| ID | Title | Status | Date |
|----|-------|--------|------|
| PRD-0001 | User Authentication | Approved | 2024-01-15 |
| PRD-0002 | Password Reset | Approved | 2024-01-20 |

## TDDs
| ID | Title | PRD | Status | Date |
|----|-------|-----|--------|------|
| TDD-0001 | Auth Service Design | PRD-0001 | Approved | 2024-01-16 |
| TDD-0002 | Password Reset Design | PRD-0002 | Approved | 2024-01-21 |

## ADRs
| ID | Title | Status | Date |
|----|-------|--------|------|
| ADR-0001 | Use JWT for session tokens | Accepted | 2024-01-16 |
| ADR-0002 | Use bcrypt for password hashing | Accepted | 2024-01-16 |
| ADR-0003 | Reset tokens separate from auth JWTs | Accepted | 2024-01-21 |
| ADR-0010 | Analytics service decomposition | Accepted | 2024-02-01 |

## Test Plans
| ID | Title | PRD | TDD | Status |
|----|-------|-----|-----|--------|
| TP-0001 | Auth Service Tests | PRD-0001 | TDD-0001 | Approved |
| TP-0002 | Password Reset Tests | PRD-0002 | TDD-0002 | Approved |
```

---

## Common Patterns Across Examples

### 1. Always Load Context First
Every session starts with reading CLAUDE.md and relevant existing docs.

### 2. Explicit Agent Invocation
"Act as the {Role}" makes expectations clear.

### 3. Reference Existing Work
New features reference existing PRDs/TDDs/ADRs rather than starting from scratch.

### 4. Phased Delivery
Large work is broken into phases with clear deliverables.

### 5. Abbreviated Flow When Appropriate
Bug fixes and spikes don't need full ceremony—but acknowledge you're skipping it.

### 6. Validation Before Ship
QA phase happens even for small changes (at minimum: regression test).