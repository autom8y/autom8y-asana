# Complete Workflow: Quick Bug Fix

> Abbreviated workflow for simple bug fixes

---

## Context

A bug was reported—login fails for emails with plus signs.

## Session (Abbreviated Flow)

**Prompt:**
```
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

## When to Use Abbreviated Flow

- Bug is localized to specific files
- Root cause is likely straightforward
- No architectural changes needed
- Can be verified with a single test

