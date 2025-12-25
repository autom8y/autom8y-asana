---
description: Quick switch to doc-team-pack (documentation workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the documentation team pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh doc-team-pack`
2. Display team roster:

**doc-team-pack** (4 agents):
| Agent | Role |
|-------|------|
| doc-auditor | Inventories docs, finds rot and gaps |
| information-architect | Designs taxonomy and navigation |
| tech-writer | Writes clear, scannable documentation |
| doc-reviewer | Verifies accuracy against codebase |

3. If SESSION_CONTEXT exists, update `active_team` to `doc-team-pack`

## When to Use

- Documentation audits and cleanup
- Creating new documentation
- Restructuring doc organization
- Technical writing tasks

## Reference

Full documentation: `.claude/skills/docs-ref/skill.md`
