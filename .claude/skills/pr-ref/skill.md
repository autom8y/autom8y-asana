---
name: pr-ref
description: "Pull request workflow with summary, test plan, and checklist. Creates PR via gh pr create. For shipping completed work. Triggers: /pr, create pull request, open PR, ship feature."
---

# /pr - Pull Request Workflow

> **Category**: Development Workflows | **Phase**: Shipping | **Complexity**: Low

## Purpose

Create a pull request with comprehensive description, test plan, and checklist. This command analyzes all changes since branch divergence, generates appropriate PR content, and creates the PR via GitHub CLI.

Use this when:
- Feature implementation is complete and tested
- Ready to ship to production
- Need formal code review
- Want documented test plan for reviewers

---

## Usage

```bash
/pr "pr-title" [--base=BRANCH]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `pr-title` | Yes | - | Pull request title |
| `--base` | No | main | Base branch to merge into |

---

## Behavior

### 1. Validate Git State

Check current git state:

```bash
# Current branch
git rev-parse --abbrev-ref HEAD

# Ensure not on main/master
if [[ $current_branch == "main" || $current_branch == "master" ]]; then
  echo "Error: Cannot create PR from main branch"
  exit 1
fi

# Check if branch tracks remote
git rev-parse --abbrev-ref @{upstream}

# Check for uncommitted changes
git status --porcelain
```

**If uncommitted changes**: Prompt to commit first or error.

**If on main/master**: Error - cannot PR from protected branch.

**If not tracking remote**: Will push with `-u` flag.

### 2. Analyze Changes

Gather comprehensive change information:

```bash
# Get base branch (default: main)
BASE_BRANCH=${base:-main}

# All commits in this branch
git log $BASE_BRANCH...HEAD --oneline

# Full diff from branch point
git diff $BASE_BRANCH...HEAD

# Changed files
git diff --name-status $BASE_BRANCH...HEAD

# Check if tests exist
find . -name "*test*" -o -name "*spec*"

# Check if docs updated
git diff $BASE_BRANCH...HEAD --name-only | grep -E '\.(md|rst|txt)$'
```

### 3. Generate PR Description

Analyze all commits (not just latest!) and changes to create:

```markdown
## Summary

[2-4 bullet points summarizing what changed and why]
- High-level description of feature/fix
- Key technical decisions
- User-facing impact

## Changes

[Organized by category]

### Added
- New feature/capability

### Changed
- Modified behavior

### Fixed
- Bug fixes

### Documentation
- Doc updates

## Technical Details

[Implementation highlights]
- Key architectural decisions (link to ADRs if exist)
- Technology choices
- Performance considerations
- Security implications

## Test Plan

[Comprehensive testing checklist]

### Automated Tests
- [ ] Unit tests passing (coverage: X%)
- [ ] Integration tests passing
- [ ] E2E tests passing (if applicable)

### Manual Testing
- [ ] Tested feature scenario 1
- [ ] Tested feature scenario 2
- [ ] Tested edge cases (empty, null, boundary)
- [ ] Tested error handling

### Validation
- [ ] All PRD acceptance criteria met
- [ ] No regressions in existing features
- [ ] Documentation updated
- [ ] Migration plan (if applicable)

## Reviewer Notes

[Context for reviewers]
- What to focus on during review
- Areas of uncertainty or complexity
- Known limitations or trade-offs

## Related

[Links to related items]
- PRD: [PRD-{slug}](../docs/requirements/PRD-{slug}.md)
- TDD: [TDD-{slug}](../docs/design/TDD-{slug}.md)
- ADRs: [ADR-{N}](../docs/decisions/ADR-{N}-{slug}.md)
- Issues: Fixes #{issue-number}

---

Generated with [Claude Code](https://claude.com/claude-code)
```

### 4. Create Pull Request

Execute GitHub CLI to create PR:

```bash
gh pr create \
  --title "{pr-title}" \
  --base "{base-branch}" \
  --body "$(cat <<'EOF'
{generated-pr-description}
EOF
)"
```

### 5. Display PR URL

Show created PR information:

```
Pull Request Created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Title: {pr-title}
Branch: {current-branch} → {base-branch}
URL: https://github.com/{owner}/{repo}/pull/{number}

Summary:
{summary-bullets}

Test Plan: {test-count} items
Documentation: {doc-status}

Next Steps:
- Review PR description for accuracy
- Request reviewers if needed: gh pr edit {number} --add-reviewer @user
- Monitor CI checks
- Address review feedback
- Merge when approved

View PR: gh pr view {number} --web
```

---

## Workflow

```mermaid
graph LR
    A[/pr invoked] --> B{On main?}
    B -->|Yes| C[Error: Switch branch]
    B -->|No| D{Uncommitted?}
    D -->|Yes| E[Commit first]
    D -->|No| F[Analyze Changes]
    F --> G[Generate Description]
    G --> H{Remote tracking?}
    H -->|No| I[Push with -u]
    H -->|Yes| J[Ensure up to date]
    I --> K[Create PR via gh]
    J --> K
    K --> L[Display PR URL]
```

---

## Deliverables

1. **Pull Request**: Created on GitHub with comprehensive description
2. **Test Plan**: Checklist for reviewers to verify
3. **Links to Artifacts**: PRD, TDD, ADRs referenced
4. **PR URL**: For sharing and tracking

---

## Examples

### Example 1: Feature PR After /task

```bash
/task "Add user authentication"
# ... implementation complete ...

/pr "Add JWT-based authentication"
```

Output:
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
- PRD: /docs/requirements/PRD-user-authentication.md
- TDD: /docs/design/TDD-user-authentication.md
- ADR-0042: JWT vs Sessions
- ADR-0043: Token expiration strategy

Next Steps:
- Request reviews: gh pr edit 142 --add-reviewer @security-team
- Monitor CI checks
- Address feedback

View PR: gh pr view 142 --web
```

### Example 2: PR After Phased Workflow

```bash
/architect "payment processing"
# Design review happens...

/build "payment processing"
# Implementation...

/qa "payment processing"
# Validation passes...

/pr "Add payment processing service" --base=develop
```

Output:
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
- PRD: /docs/requirements/PRD-payment-processing.md
- TDD: /docs/design/TDD-payment-processing.md
- ADR-0050: Async vs Sync Processing
- ADR-0051: Stripe vs Square API
- TEST Plan: /docs/testing/TEST-payment-processing.md

Security Review: Required (PCI compliance)

Next Steps:
- Request security review: gh pr edit 143 --add-reviewer @security-team
- Request infra review: gh pr edit 143 --add-reviewer @infra-team
- Deploy to staging for integration testing
- Load test in staging environment

View PR: gh pr view 143 --web
```

### Example 3: Hotfix PR

```bash
/hotfix "Fix double-charge bug in payment retry"
# Quick fix implemented and tested...

/pr "Fix: Prevent double-charge on payment retry" --base=main
```

Output:
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

### Example 4: PR with Uncommitted Changes Error

```bash
/pr "Add caching layer"
```

Output:
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

## When to Use vs Alternatives

| Use /pr when... | Use alternative when... |
|-------------------|-------------------------|
| Ready to ship feature | Still implementing → Use `/build` or `/task` |
| All tests passing | Tests failing → Fix first |
| QA validation complete | Needs testing → Use `/qa` |
| On feature branch | On main → Switch branch first |

### After /task vs After Phased Workflow

Both workflows end with `/pr`:

**After /task**:
```bash
/task "feature"  # PRD → TDD → Code → QA
/pr "feature"    # Ship
```

**After phased**:
```bash
/architect "feature"  # Design
/build "feature"      # Implement
/qa "feature"         # Validate
/pr "feature"         # Ship
```

Both produce same quality PR, different paths.

---

## Complexity Level

**LOW** - This command:
- Analyzes git history
- Generates PR description
- Invokes `gh pr create`
- No agent coordination needed

**Recommended for**:
- Shipping any completed feature
- After QA validation passes
- When ready for code review
- Production deployments

**Not recommended for**:
- Work-in-progress (use draft PRs manually)
- Exploratory branches
- Before implementation complete

---

## Prerequisites

- Git repository initialized
- Not on main/master branch
- All changes committed (no uncommitted work)
- GitHub CLI (`gh`) installed and authenticated
- Remote repository exists
- Tests passing (recommended)

---

## Success Criteria

- PR created on GitHub
- Description includes summary, test plan, links
- PR URL returned
- Branch pushed to remote (if wasn't already)
- Ready for review

---

## State Changes

### Git Changes

| Action | When |
|--------|------|
| Push branch to remote | If not already tracking remote |
| Create PR on GitHub | Always |
| No commits made | Never (must commit first) |

### Files Created

| File Type | Location | Always? |
|-----------|----------|---------|
| Pull Request | GitHub | Yes |
| No local files | - | Never |

---

## Related Commands

- `/task` - Build feature before PR (prerequisite)
- `/qa` - Validate before PR (recommended)
- `/commit` - Commit changes before PR (prerequisite)
- `/review` - Review someone else's PR (different use case)

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Workflow patterns
- [standards](../standards/SKILL.md) - PR conventions

---

## Notes

### PR Description Quality

Good PR descriptions help reviewers:
1. **Context**: Why this change?
2. **Scope**: What changed?
3. **Testing**: How verified?
4. **Risks**: What could go wrong?
5. **Links**: Where's the design?

Invest in PR description - it's documentation that outlives the code.

### Test Plan as Reviewer Checklist

Test plan serves two purposes:
1. **For PR author**: Checklist before creating PR
2. **For reviewers**: Verification steps during review

Reviewers can check off items as they verify, ensuring nothing missed.

### Analyzing All Commits

`/pr` analyzes **all commits** since branch diverged, not just the latest commit. This ensures:
- Complete feature context
- All changes included in summary
- Nothing overlooked
- Accurate scope representation

### Draft PRs

For work-in-progress, create draft PR manually:
```bash
gh pr create --draft --title "WIP: Feature"
```

Use `/pr` only for ready-to-review work.

### PR Templates

If repository has `.github/pull_request_template.md`, the generated description should align with that template structure.

### CI/CD Integration

After PR creation:
1. CI checks run automatically
2. Monitor: `gh pr checks`
3. View status: `gh pr view`
4. Merge when ready: `gh pr merge` (or via UI)

### Reviewer Assignment

Assign reviewers after PR creation:
```bash
gh pr edit {number} --add-reviewer @user1,@user2
gh pr edit {number} --add-reviewer team/security
```

Or use GitHub's auto-assign rules.

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| On main/master | Cannot PR from protected branch | Switch to feature branch |
| Uncommitted changes | Working directory not clean | Commit changes first |
| No remote | Repository not pushed | Add remote: `git remote add origin URL` |
| gh not installed | GitHub CLI missing | Install: `brew install gh` |
| Not authenticated | gh not logged in | Authenticate: `gh auth login` |
| No commits | Branch identical to base | Make some changes first |

---

## Integration with Sessions

Works with or without sessions:

**With session**:
```bash
/start "Feature development"
/task "implement feature"
/pr "Add feature"
/wrap
```

**Without session**:
```bash
# After completing work
/pr "Add feature"
```

---

## Advanced Usage

### Multiple PRs in Sprint

```bash
/sprint "Q4 improvements" --tasks="task1,task2,task3"
# After each task completes:
/pr "Task 1: Description"
/pr "Task 2: Description"
/pr "Task 3: Description"
```

### PR to Non-Default Branch

```bash
/pr "Add feature" --base=develop
# For teams using develop → main workflow
```

### Stacked PRs

For dependent changes:
```bash
# First PR
git checkout -b feature-base
# ... implement ...
/pr "Part 1: Foundation"

# Second PR (depends on first)
git checkout -b feature-extension
# ... implement ...
/pr "Part 2: Extension" --base=feature-base
```

---

## Metrics to Track

- PR creation time (from first commit to PR)
- PR size (lines changed, files modified)
- Time to first review
- Time to merge
- Review cycle count
- Test plan comprehensiveness
