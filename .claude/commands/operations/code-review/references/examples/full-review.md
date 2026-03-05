---
user-invocable: false
---

# Full Review Example: PR with Issues

This example demonstrates a review that results in REQUEST CHANGES due to security issues.

## Input

```bash
/review 142
```

## Output

```
Code Review: PR #142 - Add user authentication

Author: @developer
Branch: feature/auth -> main
Files Changed: 12 (+847 -23)
Commits: 8

Review Summary:
This PR implements JWT-based authentication with good test coverage.
The core logic is sound, but there are security concerns around token
validation and a potential race condition in concurrent login handling.

---
BLOCKING ISSUES (2)
---

1. JWT signature not validated
   Location: src/auth/token_manager.py:45
   Issue: jwt.decode() called without verify=True
   Why: Allows forged tokens to be accepted
   Fix: Add verify=True and verify_signature=True to decode call
   Example:
     jwt.decode(token, key, algorithms=['HS256'], verify=True)

2. Race condition in token refresh
   Location: src/auth/authentication_handler.py:78
   Issue: Check-then-act pattern without locking
   Why: Concurrent refreshes could create multiple tokens
   Fix: Use database transaction or distributed lock
   Example:
     with self.lock:
         if not self.is_token_valid(old_token):
             return self.create_token(user)

---
STRONG SUGGESTIONS (3)
---

1. Password validation too weak
   Location: src/auth/validators.py:12
   Issue: Only checks length, no complexity requirements
   Why: Weak passwords reduce security
   Fix: Add checks for uppercase, lowercase, numbers, special chars
   Consider: Use library like zxcvbn for strength estimation

2. Insufficient error logging
   Location: src/auth/authentication_handler.py:multiple
   Issue: Exceptions caught but not logged
   Why: Production debugging will be difficult
   Fix: Add structured logging with context
   Example:
     logger.error("Auth failed", extra={"user": user.id, "reason": str(e)})

3. Missing rate limiting tests
   Location: tests/auth/test_rate_limiter.py
   Issue: Only tests successful rate limiting, not edge cases
   Why: Edge cases like time boundary conditions not covered
   Fix: Add tests for:
     - Requests at exact limit boundary
     - Clock skew scenarios
     - Distributed rate limit state

---
NITS (4)
---

1. Inconsistent naming
   Location: src/auth/token_manager.py:multiple
   Suggestion: Methods use both "validate" and "verify" - pick one term

2. Magic number
   Location: src/auth/token_manager.py:34
   Suggestion: Extract 3600 to constant TOKEN_EXPIRY_SECONDS

3. TODO comment
   Location: src/auth/user_store.py:56
   Suggestion: Either implement or create issue, don't leave TODO

4. Verbose test names
   Location: tests/auth/test_authentication_handler.py:multiple
   Suggestion: Test names are very long, could be more concise

---
POSITIVE FEEDBACK
---

- Excellent test coverage - 94% is impressive
- Good separation of concerns - TokenManager vs AuthHandler clean
- Clear ADR for JWT choice - well-reasoned decision
- Error messages are user-friendly and don't leak internals
- Type hints throughout - great for maintainability

---
QUESTIONS
---

1. Why choose 15min for access token expiry? Is this in PRD?
   (Seems short - might cause UX issues)

2. How is token secret rotated? Is there a plan for key rotation?
   (Important for long-term security)

---
RECOMMENDATION: REQUEST CHANGES
---

Must address 2 blocking security issues before approval.

The blocking issues are critical:
1. JWT signature validation prevents token forgery
2. Race condition fix prevents token state corruption

Strong suggestions should also be addressed if possible - they
significantly improve security and maintainability.

---

Next Steps:
1. Fix blocking issues (JWT validation, race condition)
2. Consider strong suggestions (password strength, logging, tests)
3. Push updated code
4. Re-request review

Post review to PR:
  gh pr review 142 --request-changes --body-file review.md
```

## Why This Example

This example demonstrates:
- **Blocking issues**: Security vulnerabilities that prevent merge
- **Strong suggestions**: Code quality improvements that should be addressed
- **Nits**: Minor style issues that are optional
- **Positive feedback**: Reinforcing good practices
- **Questions**: Design clarifications needed from author
- **REQUEST CHANGES recommendation**: Due to security concerns

Note: Additional examples (clean approval, current branch review) follow similar patterns with different outcomes. The structure remains consistent; only the content and recommendation change.
