---
name: commit-conventions
description: "Releaser-specific commit conventions extending platform conventions. Use when: committing version bumps, release publishes, or changelog entries in releaser rite context. Triggers: release commit, version bump, chore(deps), chore(release), publish commit."
---

# Releaser Commit Conventions

Extends platform `conventions` skill with release-specific commit formats.

## Release Commit Formats

| Action | Format | Example |
|--------|--------|---------|
| Dependency bump | `chore(deps): bump {dependency} to {version}` | `chore(deps): bump @autom8y/sdk to 2.1.0` |
| Package publish | `chore(release): publish {package} v{version}` | `chore(release): publish core-sdk v1.3.0` |

## Constraint Style Matching

When bumping consumer dependency versions, preserve the consumer's existing constraint style:

| Style | Before | After |
|-------|--------|-------|
| exact | `1.2.3` | `1.3.0` |
| range | `>=1.2.0` | `>=1.3.0` |
| compatible | `^1.2.3` | `^1.3.0` |

## PR Conventions

- PR title: descriptive, references packages affected
- PR body: list repos bumped, versions changed, link to publish confirmation
- Auto-merge: `gh pr merge --auto --squash {pr-number}` only when plan specifies `auto_merge_pr`

## Safety (supplements platform conventions)

- NEVER publish without the plan specifying the action
- NEVER skip CI checks or add `[skip ci]` to commits
- ALWAYS verify publish success before bumping consumers
