# debt-triage-pack

> Technical debt discovery, prioritization, and paydown planning

## Overview

The debt triage team for identifying, prioritizing, and planning technical debt remediation. Focuses on strategic debt management rather than immediate cleanup.

## Switch Command

```bash
/debt
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **debt-detective** | opus | Discovers debt items |
| **prioritizer** | opus | Creates priority matrix |
| **paydown-planner** | opus | Plans remediation roadmap |

## Workflow

```
discovery → prioritization → planning
     │             │             │
     ▼             ▼             ▼
   Debt        Priority      Paydown
 Inventory      Matrix       Roadmap
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **QUICK** | Known debt items | Targeted |
| **AUDIT** | Full inventory | Comprehensive |

## Best For

- Technical debt inventory
- Prioritizing debt paydown
- Sprint planning for debt
- Identifying high-impact debt
- Creating remediation roadmaps

## Not For

- Actual code cleanup → use hygiene-pack
- New feature work → use 10x-dev-pack
- Immediate bug fixes → use /hotfix

## Quick Start

```bash
/debt                          # Switch to team
/task "Inventory auth module debt"
```

## Common Patterns

### Full Debt Audit

```bash
/debt
/task "Complete debt inventory" --complexity=AUDIT
```

### Targeted Analysis

```bash
/debt
/task "Analyze database layer debt" --complexity=QUICK
```

### Sprint Planning

```bash
/debt
/task "Plan Q1 debt paydown sprint"
```

## Integration with Hygiene

Typical flow:
1. `/debt` → Identify and prioritize
2. `/hygiene` → Execute remediation
3. Back to `/10x` → Continue feature work

## Related Commands

- `/task` - Full debt triage lifecycle
