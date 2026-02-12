# Complete Workflow: New Feature Development

> Full 4-phase workflow for building a new feature from scratch

---

## Context

Starting a new project that needs user authentication.

## Session 1: Requirements

**Prompt:**
```
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

## Session 2: Design

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

## Session 3: Implementation

**Prompt:**
```
Act as the Principal Engineer.

Implement the design:
- TDD: /docs/design/TDD-0001-user-auth.md
- ADRs: ADR-0001 (JWT), ADR-0002 (bcrypt)

(The `standards` skill provides code conventions and repository structure.)

Start with the domain layer (User entity, AuthService),
then infrastructure (UserRepository), then API (routes).
```

## Session 4: Validation

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

