---
description: Quick switch to strategy-pack (business strategy workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the Strategy Team pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh strategy-pack`

2. Display team roster:

**strategy-pack** (4 agents):

| Agent | Role |
|-------|------|
| market-researcher | Maps market terrain and trends |
| competitive-analyst | Tracks competitors and predicts moves |
| business-model-analyst | Stress-tests unit economics |
| roadmap-strategist | Connects vision to execution |

3. If SESSION_CONTEXT exists at `.claude/SESSION_CONTEXT.yaml`:
   - Update `active_team` field to `strategy-pack`

## When to Use

- Market analysis and sizing
- Competitive intelligence gathering
- Pricing and business model analysis
- Strategic roadmap planning

## Workflow

```
market-research → competitive-analysis → business-modeling → strategic-planning
```

## Reference

Full documentation: `.claude/skills/strategy-ref/skill.md`
