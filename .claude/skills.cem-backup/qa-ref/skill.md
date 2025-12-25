---
name: qa-ref
description: "Validation-only session with test plan and execution. Invokes QA Adversary to test completed work. Triggers: /qa, validate implementation, test plan, quality assurance, adversarial testing."
---

# /qa - Validation-Only Session

> **Category**: Development Workflows | **Phase**: Validation | **Complexity**: Low

## Purpose

Run a validation-only session that tests completed implementation against requirements. Invokes QA Adversary to create test plan, execute tests, and report defects.

Use this when:
- Implementation is complete and needs validation
- Following up after `/build` session
- Want independent QA review
- Need test plan documentation
- Before shipping to production

---

## Usage

```bash
/qa "feature-or-system-description"
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `feature-or-system-description` | Yes | - | What to validate (must match implementation) |

---

## Behavior

### 1. Validate Prerequisites

Check that implementation and requirements exist:

```bash
# Look for PRD (requirements)
find /docs/requirements -name "PRD-{feature-slug}.md"

# Look for TDD (design)
find /docs/design -name "TDD-{feature-slug}.md"

# Look for implementation (code files)
# Check project structure for relevant source files
```

**If PRD not found**: Error - cannot validate without acceptance criteria.

**If implementation not found**: Error - cannot test what doesn't exist.

**If TDD not found**: Warn but proceed (can validate against PRD only).

### 2. Invoke QA Adversary

Once prerequisites confirmed, delegate to QA:

```markdown
Act as **QA/Adversary**.

Feature: {feature-description}
PRD: /docs/requirements/PRD-{feature-slug}.md
TDD: /docs/design/TDD-{feature-slug}.md (if exists)
Implementation: {code-locations}

Validate the implementation through adversarial testing:

1. Review PRD acceptance criteria - these define success
2. Review TDD specification - implementation should match
3. Identify test scenarios covering:
   - Functional correctness (happy paths)
   - Edge cases (boundaries, empty, null, max)
   - Error handling (failures, timeouts, invalid inputs)
   - Security (injection, auth, data exposure)
   - Performance (meets NFRs, degrades gracefully)
   - Integration (with other components)

4. Create Test Plan at: /docs/testing/TEST-{feature-slug}.md
   - Test scenarios
   - Expected results
   - Actual results
   - Pass/Fail for each

5. Execute tests:
   - Run existing unit/integration tests
   - Manual testing of edge cases
   - Security review
   - Performance validation

6. Report findings:
   - All acceptance criteria met? (Yes/No)
   - Defects found (Critical/High/Medium/Low)
   - Test coverage assessment
   - Production readiness (Ship/No-Ship)

If defects found:
- Document severity and impact
- Create defect report in test plan
- Recommend fixes
- DO NOT fix yourself - hand back to Engineer

Final deliverable: Test Plan with production readiness decision
```

**Quality Gate**: All acceptance criteria met, no critical defects, production ready.

### 3. Validation Results

Display test results:

```
Validation Complete: {feature-description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Requirements (Validated Against):
✓ PRD: /docs/requirements/PRD-{slug}.md
✓ TDD: /docs/design/TDD-{slug}.md (if exists)

Implementation (Tested):
✓ Code: {list-of-files}
✓ Tests: {test-coverage}%

Test Artifacts:
✓ Test Plan: /docs/testing/TEST-{slug}.md
✓ Test Scenarios: {count} scenarios
✓ Test Results: {passed} passed, {failed} failed

Quality Assessment:
{status-by-severity}
✓ Critical: {count} (must be 0 to ship)
✓ High: {count}
✓ Medium: {count}
✓ Low: {count}

Production Readiness: {SHIP / NO-SHIP}

{If NO-SHIP:}
Defects Found:
1. [Critical] {description}
   Impact: {impact}
   Location: {file:line}

Next Steps:
- Fix critical/high defects
- Re-run `/qa` after fixes
- Use `/pr` when validation passes

{If SHIP:}
Next Steps:
- Use `/pr` to create pull request
- Or commit with `/commit` (if desired)
```

---

## Workflow

```mermaid
graph LR
    A[/qa invoked] --> B{PRD exists?}
    B -->|No| C[Error: Need requirements]
    B -->|Yes| D{Implementation exists?}
    D -->|No| E[Error: Nothing to test]
    D -->|Yes| F[QA Adversary]
    F --> G[Create Test Plan]
    G --> H[Execute Tests]
    H --> I{Defects?}
    I -->|Critical/High| J[NO-SHIP: Fix & Retest]
    I -->|None/Low| K[SHIP: Ready for PR]
```

---

## Deliverables

1. **Test Plan**: Comprehensive test documentation at `/docs/testing/TEST-{slug}.md`
2. **Test Results**: Pass/fail for all scenarios
3. **Defect Report**: Issues found with severity classification
4. **Production Readiness Decision**: Ship or No-Ship with justification

**Does NOT produce**: Code fixes (defects handed back to Engineer)

---

## Examples

### Example 1: Validation Passes (Ship)

```bash
/qa "user authentication API service"
```

Output:
```
Feature: user authentication API service

[Prerequisites Check]
✓ PRD found: /docs/requirements/PRD-user-auth-api.md
✓ TDD found: /docs/design/TDD-user-auth-api.md
✓ Implementation found: /src/auth/

[Validation]
✓ QA Adversary testing...

✓ Test Plan created: /docs/testing/TEST-user-auth-api.md

Test Scenarios (24 total):
✓ Functional: 8/8 passed
  - Valid credentials: Login successful
  - Invalid credentials: Rejection with clear error
  - Token generation: JWT with correct claims
  - Token refresh: Old token invalidated

✓ Edge Cases: 6/6 passed
  - Empty credentials: Validation error
  - Malformed token: Rejection
  - Expired token: Refresh required
  - Concurrent logins: Handled correctly

✓ Error Handling: 5/5 passed
  - Database unavailable: Graceful degradation
  - Rate limit exceeded: 429 with retry-after
  - Invalid refresh token: Clear error

✓ Security: 4/4 passed
  - SQL injection: Parameterized queries safe
  - Password exposure: Hashed, never logged
  - Token leakage: Secure HTTP-only cookies

✓ Performance: 1/1 passed
  - Login latency: 45ms avg (requirement: <200ms)

Defects Found:
- [Low] Error message could be more specific for expired tokens

Production Readiness: SHIP ✓

All acceptance criteria met. No critical or high defects.

Next: Use `/pr "Add user authentication API"` to create pull request.
```

### Example 2: Validation Fails (No-Ship)

```bash
/qa "payment processor"
```

Output:
```
Feature: payment processor

[Prerequisites Check]
✓ PRD found: /docs/requirements/PRD-payment-processor.md
✓ TDD found: /docs/design/TDD-payment-processor.md
✓ Implementation found: /src/payments/

[Validation]
✓ QA Adversary testing...

✓ Test Plan created: /docs/testing/TEST-payment-processor.md

Test Scenarios (18 total):
✓ Functional: 6/6 passed
✗ Edge Cases: 2/4 passed
✗ Error Handling: 1/3 passed
✓ Security: 3/3 passed
✗ Performance: 0/2 passed

Defects Found:

[Critical] Double-charge vulnerability
  Severity: Critical
  Impact: Can charge customer twice on retry
  Location: /src/payments/processor.py:45
  Scenario: Network timeout during charge confirmation
  Expected: Idempotent processing with request IDs
  Actual: Retry without idempotency check

[High] Database deadlock on concurrent payments
  Severity: High
  Impact: Payment processing fails under load
  Location: /src/payments/processor.py:78
  Scenario: Multiple concurrent payments from same account
  Expected: Serializable isolation or optimistic locking
  Actual: Deadlock after 5 seconds

[Medium] Error message exposes internal details
  Severity: Medium
  Impact: Potential security information leak
  Location: /src/payments/errors.py:23
  Expected: Generic error for customers
  Actual: Full stack trace in API response

Production Readiness: NO-SHIP ✗

Critical defects must be resolved before shipping.

Next Steps:
1. Hand defect report to Principal Engineer
2. Fix critical and high severity issues
3. Re-run `/qa "payment processor"` after fixes
4. Consider adding performance tests to CI
```

### Example 3: Missing Prerequisites

```bash
/qa "new feature"
```

Output:
```
Error: Cannot validate without requirements

Feature: new feature

[Prerequisites Check]
✗ PRD not found: /docs/requirements/PRD-new-feature.md
✗ Cannot validate without acceptance criteria

Suggestions:
1. Run `/task "new feature"` for full lifecycle (PRD → Code → QA)
2. Run `/architect "new feature"` to create PRD and TDD first
3. Verify feature name matches existing PRD file name

Current PRD files:
- /docs/requirements/PRD-user-auth-api.md
- /docs/requirements/PRD-payment-processor.md
- /docs/requirements/PRD-cache-invalidation.md
```

### Example 4: Iterative Testing

```bash
# First QA run - finds issues
/qa "data export feature"
# Output: 2 High defects found, NO-SHIP

# Engineer fixes issues
/build "data export feature"
# Fixes applied

# Second QA run - validates fixes
/qa "data export feature"
# Output: Previous defects resolved, 1 new Medium found, SHIP with caveat

# Ship decision
/pr "Add data export feature"
```

---

## When to Use vs Alternatives

| Use /qa when... | Use alternative when... |
|-------------------|-------------------------|
| Implementation complete, needs validation | Building from scratch → Use `/task` |
| After `/build` session | Integrated workflow → Use `/task` |
| Independent QA review needed | Designer validates own work → Use `/task` |
| Test plan documentation required | Ad-hoc testing sufficient |

### /build + /qa vs /task

**Two-phase** (`/build` then `/qa`):
- Independent validation
- Formal test plan
- Separate implementer from tester
- Better for high-risk features

**Single-phase** (`/task`):
- Faster for low-risk features
- One person owns quality
- Less formal documentation
- Better for simple features

### /qa vs Manual Testing

- `/qa`: Structured, documented, repeatable
- Manual: Ad-hoc, undocumented, one-time

Use `/qa` for production-critical features requiring audit trail.

---

## Complexity Level

**LOW** - This command:
- Invokes 1 agent (QA Adversary)
- Validates existing code
- Produces test plan
- No implementation changes

**Recommended for**:
- Pre-production validation
- Independent QA review
- High-risk features
- Compliance requirements (audit trail)

**Not recommended for**:
- Trivial changes (manual testing sufficient)
- When integrated workflow preferred (use `/task`)
- Features without acceptance criteria
- Work-in-progress implementations

---

## Prerequisites

- **PRD must exist** at `/docs/requirements/PRD-{feature-slug}.md`
- Implementation complete (code files exist)
- TDD optional but helpful
- 10x-dev-pack or team with QA Adversary
- Tests should be passing (QA validates beyond unit tests)

---

## Success Criteria

- Test plan created
- All test scenarios executed
- All acceptance criteria validated
- Defects classified by severity
- Production readiness decision made (Ship/No-Ship)

---

## State Changes

### Files Created

| File Type | Location | Always? |
|-----------|----------|---------|
| Test Plan | `/docs/testing/TEST-{slug}.md` | Yes |
| Defect Reports | Embedded in test plan | If defects found |

### No Code Changes

This command intentionally does NOT:
- Fix defects
- Modify implementation
- Write new tests

Defects are documented and handed back to Engineer for fixes.

---

## Related Commands

- `/build` - Implement before QA validation (prerequisite)
- `/task` - Integrated workflow including QA (alternative)
- `/pr` - Create pull request after QA approval
- `/review` - Review someone else's PR (different from self-QA)

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns
- [documentation](../documentation/SKILL.md) - Test Plan templates
- [standards](../standards/SKILL.md) - Testing conventions

---

## Notes

### Adversarial Testing Philosophy

QA Adversary thinks like an attacker and a confused user:
- What breaks this?
- What inputs weren't considered?
- What happens when components fail?
- How would I exploit this?

This mindset finds bugs developers miss.

### Test Plan as Documentation

Test plan serves multiple purposes:
1. **Validation record**: What was tested, results
2. **Regression suite**: Scenarios to re-test
3. **Compliance artifact**: Audit trail for regulated systems
4. **Knowledge transfer**: What edge cases matter

Invest in test plan quality for long-term value.

### Ship vs No-Ship Decision

QA makes production readiness call:

**SHIP**:
- All Critical defects resolved
- High defects acceptable risk or have workarounds
- Medium/Low defects documented for future fix

**NO-SHIP**:
- Any Critical defects
- Multiple High defects
- High defects in critical paths
- Acceptance criteria not met

When in doubt, escalate to Orchestrator for ship decision.

### Iterative QA Workflow

Typical cycle:
```
/build → /qa → defects found → /build (fixes) → /qa → SHIP
```

Each `/qa` run produces updated test plan showing:
- Original defects
- Fix verification
- New issues discovered
- Progression toward production readiness

### QA vs Code Review

- **QA** (`/qa`): Functional validation against requirements
- **Review** (`/review`): Code quality, maintainability, standards

Both are valuable, different perspectives:
- QA asks: "Does it work correctly?"
- Review asks: "Is it well-built?"

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| PRD not found | No acceptance criteria | Run `/architect` or `/task` first |
| Implementation not found | Nothing to test | Run `/build` or `/task` first |
| Tests not passing | Unit tests failing | Fix tests before QA validation |
| Missing QA agent | Team doesn't have QA | Switch to 10x-dev-pack with `/10x` |
| Acceptance criteria ambiguous | Can't determine pass/fail | Escalate to Analyst for clarification |

---

## Integration with Sessions

Works with or without sessions:

**Phased workflow with sessions**:
```bash
/start "Auth system"
/architect "authentication service"
/build "authentication service"
/qa "authentication service"
# If SHIP:
/pr "Add authentication service"
/wrap
```

**Ad-hoc validation**:
```bash
/qa "authentication service"
# Standalone validation of existing implementation
```

---

## Metrics to Track

- Test scenarios per feature
- Defect density (defects per KLOC)
- Defect severity distribution
- Time to validate (first /qa to SHIP decision)
- Re-test cycles (how many /qa runs until SHIP)
- Test coverage achieved vs target
