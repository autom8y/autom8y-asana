---
name: conventions
description: "Platform operational conventions for agents performing git operations. Use when: committing code, creating PRs, pushing branches, or any git workflow. Triggers: git commit, git push, pull request, PR, conventional commits, commit message, attribution."
---

# Git Operations Conventions

Platform conventions for agents performing git operations. Follow these rules when committing, pushing, or creating PRs via Bash tool.

## Commit Message Format

Use **conventional commits**: `type(scope): subject`

**Types** (choose one):

| Type | When |
|------|------|
| `feat` | New feature, new export, new API endpoint |
| `fix` | Bug fix, error handling, edge case patch |
| `docs` | Documentation, comments, docstrings |
| `style` | Formatting, whitespace (no behavior change) |
| `refactor` | Restructure, rename, extract (no behavior change) |
| `test` | Test files, test utilities |
| `chore` | Dependencies, build config, CI, maintenance |
| `perf` | Optimization, caching, lazy loading |
| `ci` | GitHub Actions, pipeline config |
| `build` | Webpack, bundler, compiler config |

**Scope**: Detect from changed file paths (e.g., `src/auth/` -> `auth`).

**Subject rules**:
- Imperative mood: "add" not "added" or "adds"
- No period at end
- Max 50 characters
- Lowercase after colon

**Body** (for complex commits): wrap at 72 characters, explain "why" not "what".

## Attribution Policy

| Operation | Attribution | Rationale |
|-----------|-------------|-----------|
| `git commit` | **User-only** — NO Co-Authored-By, NO "Generated with", NO AI markers | User owns the intellectual work; git history is permanent record |
| `gh pr create` | AI attribution OK in PR body | PR metadata is editable, visible to reviewers |

## Push Safety

- **NEVER** force-push (`--force`, `-f`) to main/master
- **NEVER** use `--no-verify` on commits or pushes
- **NEVER** use `git reset --hard` or `git clean -fd`
- Push to feature branches; create PRs for main

## PR Format

- Title: short, under 70 characters, imperative mood
- Body: `## Summary` (1-3 bullets) + `## Test plan` (verification steps)
- Analyze ALL commits in the branch, not just the latest

## Deep Reference

For full behavioral specifications, load these companion skills:
- `commit:behavior` — complete commit workflow with edge cases
- `pr:behavior` — complete PR workflow with analysis steps
- `hotfix:behavior` — rapid fix workflow with severity classification
