---
description: Quick switch to security-pack (security assessment workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---

## Context

Auto-injected by SessionStart hook (project, team, session, git).

## Your Task

Switch to the Security Team pack and display the team roster.

## Behavior

1. Execute: `~/Code/roster/swap-team.sh security-pack`

2. Display team roster:

**security-pack** (4 agents):

| Agent | Role |
|-------|------|
| threat-modeler | Maps attack vectors with STRIDE/DREAD |
| compliance-architect | Translates regulations to requirements |
| penetration-tester | Probes systems for vulnerabilities |
| security-reviewer | Final gate before merge |

3. If an active session exists (hook-injected context shows session info):
   - The active_team is automatically updated via team-validator hook

## When to Use

- Security review of new features or changes
- Compliance mapping and audit preparation
- Penetration testing and vulnerability assessment
- Pre-release security signoff

## Workflow

```
threat-modeling → compliance-design → penetration-testing → security-review
```

## Reference

Full documentation: `.claude/skills/security-ref/skill.md`
