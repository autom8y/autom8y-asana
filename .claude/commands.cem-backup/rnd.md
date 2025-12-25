---
description: Quick switch to rnd-pack (innovation lab workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the Innovation Lab (R&D) pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh rnd-pack`

2. Display team roster:

**rnd-pack** (4 agents):

| Agent | Role |
|-------|------|
| technology-scout | Watches the technology horizon |
| integration-researcher | Maps integration paths |
| prototype-engineer | Builds decision-ready demos |
| moonshot-architect | Designs future systems |

3. If SESSION_CONTEXT exists at `.claude/SESSION_CONTEXT.yaml`:
   - Update `active_team` field to `rnd-pack`

## When to Use

- Evaluating new technologies
- Building proof-of-concept prototypes
- Long-term architecture planning
- Innovation and R&D exploration

## Workflow

```
scouting → integration-analysis → prototyping → future-architecture
```

## Reference

Full documentation: `.claude/skills/rnd-ref/skill.md`
