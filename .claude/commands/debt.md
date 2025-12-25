---
description: Quick switch to debt-triage-pack (technical debt workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the technical debt triage team pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh debt-triage-pack`
2. Display team roster:

**debt-triage-pack** (3 agents):
| Agent | Role |
|-------|------|
| debt-collector | Catalogs all forms of technical debt |
| risk-assessor | Scores debt by blast radius and likelihood |
| sprint-planner | Packages debt into actionable work units |

3. If SESSION_CONTEXT exists, update `active_team` to `debt-triage-pack`

## When to Use

- Technical debt inventory
- Prioritizing debt paydown
- Sprint planning for maintenance
- Risk assessment of shortcuts

## Reference

Full documentation: `.claude/skills/debt-ref/skill.md`
