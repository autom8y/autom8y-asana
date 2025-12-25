# sre-pack

> Site reliability, incident response, and operations

## Overview

The SRE team for operational concerns including incident response, postmortem analysis, reliability engineering, and capacity planning.

## Switch Command

```bash
/sre
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **incident-commander** | opus | Leads incident response |
| **postmortem-author** | opus | Analyzes and documents |
| **reliability-engineer** | sonnet | Implements fixes/alerts |
| **capacity-planner** | opus | Plans capacity needs |

## Workflow

```
response → analysis → remediation → planning
    │          │           │            │
    ▼          ▼           ▼            ▼
 Incident   Postmortem   Fixes/      Capacity
 Timeline     Doc       Alerts        Plan
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **TASK** | Single operational task | One system |
| **PROJECT** | Multi-step work | Related systems |
| **PLATFORM** | Infrastructure-wide | Entire platform |

## Best For

- Incident response
- Postmortem writing
- Reliability improvements
- Capacity planning
- Monitoring setup
- Alert tuning

## Not For

- Feature development → use 10x-dev-pack
- Security incidents → use security-pack (coordinate with SRE)
- Code quality → use hygiene-pack

## Quick Start

```bash
/sre                           # Switch to team
/task "Post-incident review for auth outage"
```

## Common Patterns

### Incident Response

```bash
/sre
/task "Respond to payment service outage" --complexity=TASK
```

### Postmortem

```bash
/sre
/task "Write postmortem for yesterday's incident"
```

### Capacity Planning

```bash
/sre
/task "Plan Q2 capacity needs" --complexity=PLATFORM
```

## Emergency Pattern

For active incidents:
```bash
/sre
# incident-commander takes lead
# Skip normal workflow for speed
# Document as you go
```

## Related Commands

- `/task` - Full SRE lifecycle
- `/hotfix` - Can be used for quick operational fixes
