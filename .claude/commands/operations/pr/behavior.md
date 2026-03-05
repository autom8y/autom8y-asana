---
user-invocable: false
---

# /pr Behavior Specification

> Full step-by-step sequence for pull request workflow.

## Behavior Sequence

### 1. Validate Git State

Apply Git Validation Pattern:
- Requirement: On feature branch (not main/master)
- Verb: "create PR"

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

Gather comprehensive change information from **all commits** since branch diverged:

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

**CRITICAL**: Analyze **ALL commits**, not just the latest. This ensures complete feature context.

### 3. Generate PR Description

Analyze all commits and changes to create comprehensive description:

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
- PRD: [PRD-{slug}](.ledge/specs/PRD-{slug}.md)
- TDD: [TDD-{slug}](.ledge/specs/TDD-{slug}.md)
- ADRs: [ADR-{N}](.ledge/decisions/ADR-{N}-{slug}.md)
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

## Workflow Diagram

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

**No files created locally** - `/pr` only creates GitHub PR, not local files.

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

## Design Notes

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

### Integration with Sessions

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

### Advanced Usage

**Multiple PRs in Sprint**:
```bash
/sprint "Q4 improvements" --tasks="task1,task2,task3"
# After each task completes:
/pr "Task 1: Description"
/pr "Task 2: Description"
/pr "Task 3: Description"
```

**PR to Non-Default Branch**:
```bash
/pr "Add feature" --base=develop
# For teams using develop → main workflow
```

**Stacked PRs**:
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

### AI Attribution in PR Description

**Unlike `/commit`**, `/pr` **DOES include** AI attribution in the PR description:

```markdown
---

Generated with [Claude Code](https://claude.com/claude-code)
```

**Why different from `/commit`?**

| Aspect | /commit | /pr |
|--------|---------|-----|
| Location | Git history (permanent) | PR description (metadata) |
| Attribution | User-only | AI attribution included |
| Editability | Hard to change | Easy to edit |
| Legal impact | Copyright/authorship | Documentation only |
| Visibility | Forever in repo | PR context only |

PR descriptions are **metadata** and **editable**, so AI attribution is appropriate. Git commits are **permanent record** of authorship, so user-only attribution is required.
