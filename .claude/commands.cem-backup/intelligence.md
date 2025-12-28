---
description: Quick switch to intelligence-pack (product analytics workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the Product Intelligence Team pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh intelligence-pack`

2. Display team roster:

**intelligence-pack** (4 agents):

| Agent | Role |
|-------|------|
| analytics-engineer | Builds data foundation and tracking |
| user-researcher | Captures qualitative insights |
| experimentation-lead | Designs A/B tests and experiments |
| insights-analyst | Synthesizes data into decisions |

3. If an active session exists (hook-injected context shows session info):
   - The active_team is automatically updated via team-validator hook

## When to Use

- Instrumenting new features with analytics
- Designing and running A/B tests
- User research and interview planning
- Data-driven product decisions

## Workflow

```
instrumentation → research → experimentation → synthesis
```

## Reference

Full documentation: `.claude/skills/intelligence-ref/skill.md`
