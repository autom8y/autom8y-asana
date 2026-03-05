---
user-invocable: false
---

# /pr Examples

> Usage scenarios with sample outputs.

## Example 1: Feature PR After /task

**Command**:
```bash
/task "Add user authentication"
# ... implementation complete ...

/pr "Add JWT-based authentication"
```

**Output**:
```
Pull Request Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: Add JWT-based authentication
Branch: feature/auth → main
URL: https://github.com/myorg/myapp/pull/142

Summary:
- Implements JWT-based authentication with refresh tokens
- Adds rate limiting to prevent brute force attacks
- Includes comprehensive test coverage (94%)

Changes:
  Added: 8 files
  Modified: 3 files
  Tests: 12 new test files

Test Plan: 18 items
- Automated: Unit, integration, security tests
- Manual: Login flows, token refresh, rate limiting

Documentation: Updated (README.md, API.md)

Related:
- PRD: .ledge/specs/PRD-user-authentication.md
- TDD: .ledge/specs/TDD-user-authentication.md
- ADR-0042: JWT vs Sessions
- ADR-0043: Token expiration strategy

Next Steps:
- Request reviews: gh pr edit 142 --add-reviewer @security-team
- Monitor CI checks
- Address feedback

View PR: gh pr view 142 --web
```

---

## Example 2: PR After Phased Workflow

**Command**:
```bash
/architect "payment processing"
# Design review happens...

/build "payment processing"
# Implementation...

/qa "payment processing"
# Validation passes...

/pr "Add payment processing service" --base=develop
```

**Output**:
```
Pull Request Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: Add payment processing service
Branch: feature/payments → develop
URL: https://github.com/myorg/myapp/pull/143

Summary:
- Implements async payment processing with idempotency
- Integrates with Stripe API
- Includes retry logic and error handling
- Adds monitoring and alerting

Changes:
  Added: 15 files (payment service, queue, handlers)
  Modified: 5 files (API gateway, config)
  Tests: 24 test files (unit, integration, E2E)

Test Plan: 32 items
- Automated: Full test suite passing
- Manual: Payment flows, failure scenarios, retries
- Load testing: 1000 req/sec sustained

Documentation: Complete
- README.md updated with setup instructions
- API documentation for new endpoints
- Runbook for payment monitoring

Related:
- PRD: .ledge/specs/PRD-payment-processing.md
- TDD: .ledge/specs/TDD-payment-processing.md
- ADR-0050: Async vs Sync Processing
- ADR-0051: Stripe vs Square API
- TEST Plan: .ledge/specs/TEST-payment-processing.md

Security Review: Required (PCI compliance)

Next Steps:
- Request security review: gh pr edit 143 --add-reviewer @security-team
- Request infra review: gh pr edit 143 --add-reviewer @infra-team
- Deploy to staging for integration testing
- Load test in staging environment

View PR: gh pr view 143 --web
```

---

## Example 3: Hotfix PR

**Command**:
```bash
/hotfix "Fix double-charge bug in payment retry"
# Quick fix implemented and tested...

/pr "Fix: Prevent double-charge on payment retry" --base=main
```

**Output**:
```
Pull Request Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: Fix: Prevent double-charge on payment retry
Branch: hotfix/double-charge → main
URL: https://github.com/myorg/myapp/pull/144

Summary:
- HOTFIX: Adds idempotency key to payment retry logic
- Prevents double-charging customers on network timeout
- Production incident INC-2847

Changes:
  Modified: 1 file (payment processor)
  Tests: 3 new test cases for retry scenarios

Test Plan: 8 items
- Automated: All tests passing
- Manual: Verified retry doesn't double-charge
- Verified in staging with network simulation

Urgency: HIGH - Production issue affecting customers

Testing:
- Unit tests added for retry with idempotency
- Integration test simulates network timeout
- Manually tested in staging with multiple retries
- No double-charges observed

Rollback Plan:
- Safe to rollback - only adds idempotency check
- No database migrations
- No config changes

Next Steps:
- IMMEDIATE REVIEW REQUESTED
- Deploy to production after approval
- Monitor payment metrics for 24h
- Update incident INC-2847 with resolution

View PR: gh pr view 144 --web
```

---

## Example 4: PR with Uncommitted Changes Error

**Command**:
```bash
/pr "Add caching layer"
```

**Output**:
```
Error: Uncommitted changes detected

You have uncommitted changes:
  M src/cache/manager.py
  M tests/cache/test_manager.py
  ?? src/cache/config.py

Please commit changes first:
  git add .
  git commit -m "Add caching layer"

Or use Claude Code commit command:
  /commit "Add caching layer"

Then re-run: /pr "Add caching layer"
```

---

## Edge Case Examples

### Edge Case: On Main Branch

**Scenario**: User tries to create PR from main branch.

**Command**:
```bash
# Currently on main branch
/pr "Add feature"
```

**Output**:
```
Error: Cannot create PR from main branch

Current branch: main

Switch to a feature branch first:
  git checkout -b feature/my-feature

Or if branch exists:
  git checkout feature/my-feature

Then re-run: /pr "Add feature"
```

**Notes**: PRs from protected branches (main/master) are blocked.

---

### Edge Case: No Remote Configured

**Scenario**: User tries to create PR but no remote repository exists.

**Command**:
```bash
/pr "Add feature"
```

**Output**:
```
Error: No remote repository configured

Add remote repository:
  git remote add origin https://github.com/user/repo.git

Or:
  git remote add origin git@github.com:user/repo.git

Then push branch:
  git push -u origin feature/my-feature

Then re-run: /pr "Add feature"
```

**Notes**: Detects missing remote via `git remote -v`.

---

### Edge Case: GitHub CLI Not Authenticated

**Scenario**: User has `gh` installed but not authenticated.

**Command**:
```bash
/pr "Add feature"
```

**Output**:
```
Error: GitHub CLI not authenticated

Authenticate with GitHub:
  gh auth login

Follow the prompts to authenticate.

Then re-run: /pr "Add feature"
```

**Notes**: Detects via `gh auth status`.

---

### Edge Case: No Commits on Branch

**Scenario**: User creates branch but makes no commits.

**Command**:
```bash
git checkout -b feature/empty
/pr "Add feature"
```

**Output**:
```
Error: No commits on this branch

Current branch: feature/empty
Base branch: main

Commits ahead: 0

Make some changes and commit first:
  # Make changes
  git add .
  git commit -m "Add feature"

Then re-run: /pr "Add feature"
```

**Notes**: Compares branch to base with `git log main...HEAD --oneline`.

---

### Edge Case: Branch Not Pushed to Remote

**Scenario**: User has commits but branch not pushed.

**Command**:
```bash
/pr "Add feature"
```

**Output**:
```
Branch not tracking remote. Pushing to origin...

Pushing feature/my-feature → origin/feature/my-feature

Counting objects: 15, done.
Delta compression using up to 8 threads.
Compressing objects: 100% (12/12), done.
Writing objects: 100% (15/15), 2.34 KiB | 2.34 MiB/s, done.
Total 15 (delta 8), reused 0 (delta 0)
To github.com:user/repo.git
 * [new branch]      feature/my-feature -> feature/my-feature

Pull Request Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: Add feature
Branch: feature/my-feature → main
URL: https://github.com/user/repo/pull/145

[... rest of output ...]
```

**Notes**: Automatically pushes if branch not tracking remote.

---

### Edge Case: PR to Non-Default Branch

**Scenario**: User wants to PR to develop instead of main.

**Command**:
```bash
/pr "Add feature" --base=develop
```

**Output**:
```
Pull Request Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: Add feature
Branch: feature/my-feature → develop
URL: https://github.com/user/repo/pull/146

[... rest of output ...]
```

**Notes**: Supports custom base branch for teams using develop → main workflow.

---

## Workflow Integration Examples

### After /task Workflow

```bash
# Full workflow
/task "implement user profile editing"

# Implementation happens (PRD, TDD, code, QA)
# All tests pass, feature complete

/pr "Add user profile editing"
```

---

### After Phased Workflow

```bash
# Design phase
/architect "notification system"
# Review design, approve

# Implementation phase
/build "notification system"
# Code complete

# Validation phase
/qa "notification system"
# Tests pass

# Ship
/pr "Add real-time notification system"
```

---

### Multiple PRs in Sprint

```bash
/sprint "Q4 performance improvements" --tasks="caching,indexing,lazy-loading"

# After each task completes
/pr "Add Redis caching layer"
/pr "Add database indexes for slow queries"
/pr "Implement lazy loading for images"
```

---

## Troubleshooting

### "gh: command not found"

**Error**:
```
Error: GitHub CLI not installed

gh: command not found
```

**Resolution**:
```bash
# macOS
brew install gh

# Linux
sudo apt install gh  # Debian/Ubuntu
sudo dnf install gh  # Fedora

# Windows
winget install GitHub.cli
```

---

### "refused to create PR (already exists)"

**Error**:
```
Error: Pull request already exists

PR #142 already exists for this branch:
https://github.com/user/repo/pull/142

To update the PR:
1. Make more commits on this branch
2. Push: git push
3. PR will update automatically

Or view existing PR:
  gh pr view 142 --web
```

**Notes**: Can't create duplicate PRs for same branch. Update existing PR by pushing more commits.

---

### PR Template Not Applied

**Scenario**: Repository has PR template but generated description doesn't match.

**Behavior**: `/pr` generates its own structured description. If repository template is required:

**Manual adjustment**:
```bash
# After PR created
gh pr edit 145 --body "$(cat .github/pull_request_template.md)"

# Then manually fill in template sections
gh pr view 145 --web
```

**Or**: Edit PR description via GitHub UI to match template.
