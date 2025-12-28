---
description: Quick switch to hygiene-pack (code quality workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the code hygiene team pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh hygiene-pack`
2. Display team roster:

**hygiene-pack** (4 agents):
| Agent | Role |
|-------|------|
| code-smeller | Finds rot, DRY violations, complexity hotspots |
| architect-enforcer | Evaluates smells through architectural lens |
| janitor | Executes refactoring with atomic commits |
| audit-lead | Verifies cleanup, signs off on changes |

3. If SESSION_CONTEXT exists, update `active_team` to `hygiene-pack`

## When to Use

- Code quality audits
- Refactoring initiatives
- Reducing technical debt
- Enforcing architectural patterns

## Reference

Full documentation: `.claude/skills/hygiene-ref/skill.md`
