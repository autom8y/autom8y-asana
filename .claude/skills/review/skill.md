---
name: review
description: "Code review workflow with structured feedback. Uses QA Adversary perspective to review PRs. For reviewing others' code. Triggers: /review, code review, review PR, review code."
---

# /review - Code Review Workflow

> **Category**: Development Workflows | **Phase**: Review | **Complexity**: Low

## Purpose

Perform structured code review of a pull request or branch using QA Adversary perspective. This command analyzes code quality, correctness, security, and maintainability, providing actionable feedback.

Use this when:
- Reviewing someone else's pull request
- Reviewing code before merging
- Need structured review feedback
- Want both functional and quality review

---

## Usage

```bash
/review PR_NUMBER
/review BRANCH_NAME
/review --current  # Review current branch vs main
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `PR_NUMBER` | One of | - | GitHub PR number to review |
| `BRANCH_NAME` | these | - | Git branch to review |
| `--current` | three | - | Review current branch vs main |

---

## Behavior

### 1. Fetch PR or Branch Changes

Depending on input, fetch the code to review:

**For PR Number**:
```bash
# Fetch PR metadata
gh pr view {PR_NUMBER}

# Get PR branch
PR_BRANCH=$(gh pr view {PR_NUMBER} --json headRefName -q .headRefName)

# Get base branch
BASE_BRANCH=$(gh pr view {PR_NUMBER} --json baseRefName -q .baseRefName)

# Fetch changes
git fetch origin $PR_BRANCH
git diff origin/$BASE_BRANCH...origin/$PR_BRANCH
```

**For Branch Name**:
```bash
# Assume base is main
git fetch origin {BRANCH_NAME}
git diff origin/main...origin/{BRANCH_NAME}
```

**For Current Branch**:
```bash
# Get current branch
CURRENT=$(git rev-parse --abbrev-ref HEAD)

# Diff against main
git diff main...HEAD
```

### 2. Analyze PR Context

Gather review context:

```bash
# Get PR description
gh pr view {PR_NUMBER} --json title,body,author

# Get changed files
git diff --name-status {BASE}...{HEAD}

# Get commit messages
git log {BASE}...{HEAD} --oneline

# Look for related docs
find /docs -name "*{pr-slug}*" -type f

# Check test files
git diff {BASE}...{HEAD} --name-only | grep -E 'test|spec'
```

### 3. Invoke QA Adversary for Review

Delegate to QA Adversary with review perspective:

```markdown
Act as **QA/Adversary** in code review mode.

PR: {PR_NUMBER} - {PR_TITLE}
Author: {AUTHOR}
Branch: {HEAD_BRANCH} → {BASE_BRANCH}

Review this code with both functional and quality lenses:

## 1. Functional Correctness
- Does code do what PR description says?
- Are edge cases handled?
- Is error handling appropriate?
- Would this work in production?

## 2. Code Quality
- Is code readable and maintainable?
- Are names clear and consistent?
- Is complexity appropriate?
- Are there code smells?
- Does it follow project standards?

## 3. Testing
- Are tests comprehensive?
- Do tests cover edge cases?
- Are error paths tested?
- Is test quality good (clear, isolated, deterministic)?

## 4. Security
- Input validation present?
- Auth/authz correct?
- Data exposure risks?
- Injection vulnerabilities?
- Secret management proper?

## 5. Performance
- Inefficient algorithms?
- N+1 queries?
- Memory leaks?
- Unnecessary allocations?
- Would this scale?

## 6. Documentation
- Is code self-documenting?
- Are complex parts explained?
- Is API documentation updated?
- Are ADRs linked if decisions made?

## 7. Architecture
- Does this fit system design?
- Are boundaries clean?
- Dependencies appropriate?
- Would this be easy to change later?

Provide structured feedback:

### Blocking Issues (Must Fix Before Merge)
[Critical problems that prevent merge]

### Strong Suggestions (Should Fix)
[Important issues that should be addressed]

### Nits (Nice to Have)
[Minor improvements, optional]

### Positive Feedback
[What was done well - reinforce good practices]

### Questions
[Clarifications needed from author]

For each item:
- Location: File and line number
- Issue: What's wrong
- Why: Impact of the issue
- Suggestion: How to fix

Be specific and actionable. Provide examples where helpful.
```

### 4. Generate Review Report

Create structured review output:

```
Code Review: PR #{NUMBER} - {TITLE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Author: {AUTHOR}
Branch: {HEAD} → {BASE}
Files Changed: {COUNT} (+{ADDITIONS} -{DELETIONS})
Commits: {COUNT}

Review Summary:
{SUMMARY-PARAGRAPH}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCKING ISSUES ({COUNT})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{If any blocking issues:}
🛑 1. {TITLE}
   Location: {FILE}:{LINE}
   Issue: {DESCRIPTION}
   Why: {IMPACT}
   Fix: {SUGGESTION}

{Repeat for each blocking issue}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRONG SUGGESTIONS ({COUNT})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  1. {TITLE}
   Location: {FILE}:{LINE}
   Issue: {DESCRIPTION}
   Why: {IMPACT}
   Fix: {SUGGESTION}

{Repeat for each suggestion}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NITS ({COUNT})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 1. {TITLE}
   Location: {FILE}:{LINE}
   Suggestion: {DESCRIPTION}

{Repeat for nits}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSITIVE FEEDBACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ {WHAT-WAS-DONE-WELL-1}
✅ {WHAT-WAS-DONE-WELL-2}
✅ {WHAT-WAS-DONE-WELL-3}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ 1. {QUESTION-ABOUT-DESIGN-CHOICE}
❓ 2. {QUESTION-ABOUT-IMPLEMENTATION}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{APPROVE / REQUEST CHANGES / COMMENT}

{If REQUEST CHANGES:}
Must address {COUNT} blocking issues before approval.

{If APPROVE:}
Good to merge after addressing suggestions (optional).

{If COMMENT:}
Questions need clarification before decision.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next Steps:
{If blocking:} Address blocking issues, then re-request review
{If suggestions:} Consider strong suggestions, iterate if needed
{If approved:} Merge when ready

Post review to PR:
  gh pr review {NUMBER} --comment --body "..."
  gh pr review {NUMBER} --approve --body "..."
  gh pr review {NUMBER} --request-changes --body "..."
```

---

## Workflow

```mermaid
graph LR
    A[/review invoked] --> B{PR or Branch?}
    B -->|PR| C[Fetch via gh]
    B -->|Branch| D[Fetch via git]
    B -->|Current| E[Diff vs main]
    C --> F[Get Context]
    D --> F
    E --> F
    F --> G[QA Adversary Review]
    G --> H[Structure Feedback]
    H --> I{Blocking Issues?}
    I -->|Yes| J[REQUEST CHANGES]
    I -->|No| K{Questions?}
    K -->|Yes| L[COMMENT]
    K -->|No| M[APPROVE]
```

---

## Deliverables

1. **Structured Review**: Categorized feedback (blocking/suggestions/nits)
2. **Specific Locations**: File and line numbers for each issue
3. **Actionable Recommendations**: Clear how-to-fix guidance
4. **Review Decision**: Approve, Request Changes, or Comment
5. **Review Summary**: Optional posting to GitHub PR

---

## Examples

### Example 1: Review PR with Issues

```bash
/review 142
```

Output:
```
Code Review: PR #142 - Add user authentication
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Author: @developer
Branch: feature/auth → main
Files Changed: 12 (+847 -23)
Commits: 8

Review Summary:
This PR implements JWT-based authentication with good test coverage.
The core logic is sound, but there are security concerns around token
validation and a potential race condition in concurrent login handling.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCKING ISSUES (2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛑 1. JWT signature not validated
   Location: src/auth/token_manager.py:45
   Issue: jwt.decode() called without verify=True
   Why: Allows forged tokens to be accepted
   Fix: Add verify=True and verify_signature=True to decode call
   Example:
     jwt.decode(token, key, algorithms=['HS256'], verify=True)

🛑 2. Race condition in token refresh
   Location: src/auth/authentication_handler.py:78
   Issue: Check-then-act pattern without locking
   Why: Concurrent refreshes could create multiple tokens
   Fix: Use database transaction or distributed lock
   Example:
     with self.lock:
         if not self.is_token_valid(old_token):
             return self.create_token(user)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRONG SUGGESTIONS (3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  1. Password validation too weak
   Location: src/auth/validators.py:12
   Issue: Only checks length, no complexity requirements
   Why: Weak passwords reduce security
   Fix: Add checks for uppercase, lowercase, numbers, special chars
   Consider: Use library like zxcvbn for strength estimation

⚠️  2. Insufficient error logging
   Location: src/auth/authentication_handler.py:multiple
   Issue: Exceptions caught but not logged
   Why: Production debugging will be difficult
   Fix: Add structured logging with context
   Example:
     logger.error("Auth failed", extra={"user": user.id, "reason": str(e)})

⚠️  3. Missing rate limiting tests
   Location: tests/auth/test_rate_limiter.py
   Issue: Only tests successful rate limiting, not edge cases
   Why: Edge cases like time boundary conditions not covered
   Fix: Add tests for:
     - Requests at exact limit boundary
     - Clock skew scenarios
     - Distributed rate limit state

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NITS (4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 1. Inconsistent naming
   Location: src/auth/token_manager.py:multiple
   Suggestion: Methods use both "validate" and "verify" - pick one term

💡 2. Magic number
   Location: src/auth/token_manager.py:34
   Suggestion: Extract 3600 to constant TOKEN_EXPIRY_SECONDS

💡 3. TODO comment
   Location: src/auth/user_store.py:56
   Suggestion: Either implement or create issue, don't leave TODO

💡 4. Verbose test names
   Location: tests/auth/test_authentication_handler.py:multiple
   Suggestion: Test names are very long, could be more concise

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSITIVE FEEDBACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Excellent test coverage - 94% is impressive
✅ Good separation of concerns - TokenManager vs AuthHandler clean
✅ Clear ADR for JWT choice - well-reasoned decision
✅ Error messages are user-friendly and don't leak internals
✅ Type hints throughout - great for maintainability

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ Why choose 15min for access token expiry? Is this in PRD?
   (Seems short - might cause UX issues)

❓ How is token secret rotated? Is there a plan for key rotation?
   (Important for long-term security)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATION: REQUEST CHANGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Must address 2 blocking security issues before approval.

The blocking issues are critical:
1. JWT signature validation prevents token forgery
2. Race condition fix prevents token state corruption

Strong suggestions should also be addressed if possible - they
significantly improve security and maintainability.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next Steps:
1. Fix blocking issues (JWT validation, race condition)
2. Consider strong suggestions (password strength, logging, tests)
3. Push updated code
4. Re-request review

Post review to PR:
  gh pr review 142 --request-changes --body-file review.md
```

### Example 2: Review Approves Clean Code

```bash
/review feature/caching
```

Output:
```
Code Review: Branch feature/caching → main
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Branch: feature/caching → main
Files Changed: 6 (+423 -12)
Commits: 4

Review Summary:
Well-designed caching layer with clean interfaces and comprehensive
tests. Code follows project standards and includes good documentation.
Minor nits but nothing blocking.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCKING ISSUES (0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

None found. Code is ready to merge.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRONG SUGGESTIONS (0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

None. Code quality is high.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NITS (2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 1. Could extract constant
   Location: src/cache/manager.py:23
   Suggestion: TTL default of 300 could be a named constant

💡 2. Docstring formatting
   Location: src/cache/strategies.py:45
   Suggestion: Multi-line docstring should have closing """ on new line

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POSITIVE FEEDBACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Excellent use of observer pattern - clean design
✅ Interfaces well-defined and documented
✅ Test coverage is thorough (92%)
✅ Edge cases handled (cache full, eviction, TTL edge cases)
✅ Performance considered - O(1) lookups maintained
✅ Good ADR for LRU vs LFU decision
✅ Code is very readable and self-documenting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

None - implementation is clear.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATION: APPROVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Excellent work! Code is clean, well-tested, and ready to merge.

The nits are truly minor - feel free to address or ignore as you see
fit. The core implementation is solid.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next Steps:
Merge when ready! Consider squashing commits for cleaner history.

Post review to PR:
  gh pr review {NUMBER} --approve --body "LGTM! Excellent implementation."
```

### Example 3: Review Current Branch

```bash
/review --current
```

Output:
```
Code Review: Current Branch (feature/api-refactor) → main
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Branch: feature/api-refactor → main
Files Changed: 23 (+1,247 -834)
Commits: 15

Review Summary:
Large refactoring that improves API consistency but introduces breaking
changes. Need to verify migration plan exists and breaking changes are
documented.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCKING ISSUES (1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛑 1. Breaking changes not documented
   Location: Multiple API files
   Issue: Renamed endpoints and changed response formats
   Why: Existing clients will break without migration guide
   Fix: Create MIGRATION.md documenting:
     - What changed
     - Migration steps
     - Deprecation timeline
     - Example before/after code

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRONG SUGGESTIONS (2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  1. Consider feature flag
   Location: Overall approach
   Issue: All changes deployed at once
   Why: High risk for large refactor
   Fix: Wrap new API behavior in feature flag for gradual rollout

⚠️  2. Missing integration tests
   Location: tests/ directory
   Issue: Unit tests updated but no integration test for full flow
   Why: Refactors often break integration points
   Fix: Add end-to-end test covering full API request/response cycle

...
[Rest of review]
```

---

## When to Use vs Alternatives

| Use /review when... | Use alternative when... |
|-------------------|-------------------------|
| Reviewing someone else's PR | Validating your own work → Use `/qa` |
| Want structured feedback | Quick glance sufficient |
| Code ready for merge consideration | Still in draft/WIP |
| Formal review process | Pair programming/informal review |

### /review vs /qa

- `/review`: Review **someone else's** code (external perspective)
- `/qa`: Validate **your own** implementation (testing focus)

Both use QA Adversary, different contexts.

---

## Complexity Level

**LOW** - This command:
- Fetches code changes via git/gh
- Invokes QA Adversary in review mode
- Produces structured feedback
- No code modification

**Recommended for**:
- All pull request reviews
- Pre-merge validation
- Learning code review skills
- Consistent review quality

**Not recommended for**:
- Reviewing your own code (use `/qa`)
- WIP/draft code (premature)
- Trivial changes (overkill)

---

## Prerequisites

- Git repository with remote
- GitHub CLI (`gh`) for PR reviews
- Code to review exists (PR or branch)
- Access to repository

---

## Success Criteria

- Review covers all changed files
- Feedback is specific and actionable
- Issues categorized by severity
- Recommendation made (approve/changes/comment)
- Review can be posted to GitHub

---

## State Changes

### No Code Changes

This command is **read-only**:
- Analyzes code
- Provides feedback
- Does NOT modify code
- Does NOT commit changes

### Optional GitHub Interaction

Can post review to GitHub (manual):
```bash
gh pr review {NUMBER} --approve
gh pr review {NUMBER} --request-changes
gh pr review {NUMBER} --comment
```

---

## Related Commands

- `/qa` - Validate your own implementation (different use case)
- `/pr` - Create PR for review (prerequisite)
- `/task` - Build feature that will be reviewed

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Workflow patterns
- [standards](../standards/SKILL.md) - Code quality standards

---

## Notes

### Review Philosophy

Good code reviews:
1. **Specific**: Point to exact locations, not vague "improve code quality"
2. **Actionable**: Suggest fixes, not just identify problems
3. **Balanced**: Praise good work, not just criticism
4. **Respectful**: Assume good intent, focus on code not person
5. **Educational**: Explain why, help author learn

### QA Adversary in Review Mode

QA Adversary reviews with:
- **Functional lens**: Does code work correctly?
- **Quality lens**: Is code maintainable?
- **Security lens**: Are there vulnerabilities?
- **Performance lens**: Will this scale?

This multi-lens approach catches more issues than single-perspective reviews.

### Blocking vs Suggestions vs Nits

**Blocking** (must fix):
- Security vulnerabilities
- Correctness bugs
- Breaking changes without migration
- Data loss risks

**Strong Suggestions** (should fix):
- Code quality issues affecting maintainability
- Missing error handling
- Insufficient testing
- Performance problems

**Nits** (nice to have):
- Style inconsistencies
- Minor naming improvements
- Documentation formatting
- Trivial refactors

### Positive Feedback Importance

Always include positive feedback:
- Reinforces good practices
- Builds team morale
- Shows you read code carefully
- Balances criticism

### Review Speed vs Depth

Balance thoroughness with velocity:
- **Small PRs** (< 200 lines): Deep review, 30-60 min
- **Medium PRs** (200-500 lines): Focus on critical paths, 1-2 hours
- **Large PRs** (> 500 lines): Request split or focus on architecture

### Posting Review to GitHub

After `/review` generates feedback:

```bash
# Save review to file
/review 142 > review.md

# Post to GitHub
gh pr review 142 --approve --body-file review.md
gh pr review 142 --request-changes --body-file review.md
gh pr review 142 --comment --body-file review.md
```

Or copy/paste specific sections into GitHub UI.

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| PR not found | Invalid PR number | Verify PR exists: `gh pr list` |
| Branch not found | Branch doesn't exist | Check branch name: `git branch -a` |
| No changes | Branch identical to base | Nothing to review |
| gh not installed | GitHub CLI missing | Install: `brew install gh` |
| Not authenticated | gh not logged in | Authenticate: `gh auth login` |
| No access | Can't fetch PR/branch | Check repository permissions |

---

## Advanced Usage

### Review Multiple PRs in Batch

```bash
# Get all open PRs
gh pr list

# Review each
/review 140
/review 141
/review 142
```

### Review with Context

```bash
# Review PR with related docs
/review 142
# Then read:
# - /docs/requirements/PRD-{feature}.md
# - /docs/design/TDD-{feature}.md
# For fuller context
```

### Compare Review vs QA

```bash
# Self-validation during development
/qa "my feature"

# External review before merge
# (Someone else runs:)
/review {my-branch}
```

---

## Integration with Development Workflow

### Typical Flow

**PR Author**:
```bash
/task "implement feature"
/qa "feature"  # Self-validation
/pr "Add feature"
# Request reviews from team
```

**Reviewer**:
```bash
/review 142  # Review PR
# Post feedback
```

**PR Author** (after feedback):
```bash
# Address blocking issues
/build "feature"  # Implement fixes
/qa "feature"     # Re-validate
# Push changes
# Re-request review
```

**Reviewer**:
```bash
/review 142  # Verify fixes
# Approve
```

---

## Metrics to Track

- Reviews per week
- Time to complete review
- Issues found per review
- Blocking vs suggestion vs nit ratio
- Review cycle count (before approval)
- False positive rate (issues marked not actually issues)
