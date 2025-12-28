---
description: Structured review with categorized feedback
argument-hint: <pr-number-or-branch> [--focus=AREA]
allowed-tools: Bash, Read, Glob, Grep
model: claude-opus-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git, workflow).

**Review-specific**:
- Recent PRs: !`gh pr list --limit 5 2>/dev/null || echo "gh CLI not available"`

## Your Task

Review changes with structured, categorized feedback. $ARGUMENTS

## Workflow Resolution

Use the validation agent in review mode:

```bash
# Get validation agent from workflow (last phase)
REVIEW_AGENT=$(grep -B1 "next: null" .claude/ACTIVE_WORKFLOW.yaml | grep "agent:" | awk '{print $2}')
```

## Behavior

1. **Get changes to review**:
   - If PR number: `gh pr diff <number>`
   - If branch: `git diff main...<branch>`

2. **Invoke validation agent** (review mode) via Task tool:
   - Review all changed files/content
   - Apply multiple lenses
   - Agent varies by team:
     - 10x-dev-pack → qa-adversary
     - doc-team-pack → doc-reviewer
     - hygiene-pack → audit-lead

3. **Categorize feedback**:

   **Blocking Issues** (must fix):
   - Critical errors
   - Security vulnerabilities
   - Breaking changes

   **Suggestions** (should consider):
   - Improvements
   - Better patterns
   - Maintainability

   **Nits** (optional polish):
   - Style preferences
   - Naming tweaks
   - Minor documentation

4. **Provide recommendation**:
   - APPROVE: No blockers, good to merge
   - REQUEST CHANGES: Blockers found
   - COMMENT: Suggestions only, author decides

## Review Lenses

| Lens | Focus |
|------|-------|
| Functional | Does it work correctly? |
| Quality | Is it maintainable? |
| Security | Any vulnerabilities? |
| Accuracy | Is it correct? |

## Example

```
/code-review 123
/code-review feature/auth --focus=security
```

## Reference

Full documentation: `.claude/skills/review/skill.md`
