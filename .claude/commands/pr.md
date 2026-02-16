---
description: Create pull request with comprehensive description
argument-hint: "[title] [--base=BRANCH]"
allowed-tools: Bash, Read, Glob, Grep
model: sonnet
---

## Context
Auto-injected by SessionStart hook (project, rite, session, git).

**PR-specific**:
- Base branch: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main"`
- Commits ahead: !`git rev-list --count HEAD ^origin/main 2>/dev/null || echo "unknown"`
- Changed files: !`git diff --name-only origin/main 2>/dev/null | head -10 || echo "none"`

## Your Task

Create a GitHub pull request with auto-generated description. $ARGUMENTS

## Behavior

1. **Analyze changes**:
   - All commits since branch divergence
   - Files changed
   - Related PRD/TDD/ADR artifacts

2. **Generate PR description**:
   ```markdown
   ## Summary
   [Auto-generated from commits and artifacts]

   ## Changes
   - [List of key changes]

   ## Test Plan
   - [Derived from test plan if exists]

   ## Artifacts
   - PRD: [link if exists]
   - TDD: [link if exists]

   ## Checklist
   - [ ] Tests pass
   - [ ] Code reviewed
   - [ ] Documentation updated
   ```

3. **Create PR** via `gh pr create`:
   ```bash
   gh pr create --title "..." --body "..."
   ```

4. **Return PR URL**

## Example

```
/pr "Add user authentication"
/pr --base=develop
```

## Reference

Full documentation: `.claude/commands/operations/pr/INDEX.md`
