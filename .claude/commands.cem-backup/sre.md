---
description: Quick switch to sre-pack (reliability workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context
Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the SRE team pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh sre-pack`
2. Display team roster:

**sre-pack** (4 agents):
| Agent | Role |
|-------|------|
| observability-engineer | Metrics, logs, traces, dashboards, alerts |
| incident-commander | War room coordination, postmortems |
| platform-engineer | CI/CD, IaC, deployment automation |
| chaos-engineer | Fault injection, resilience testing |

3. If SESSION_CONTEXT exists, update `active_team` to `sre-pack`

## When to Use

- System reliability improvements
- Observability and monitoring work
- Incident response preparation
- Chaos engineering experiments
- Platform and infrastructure work

## Reference

Full documentation: `.claude/skills/sre-ref/skill.md`
