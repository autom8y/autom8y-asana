# Minimal Team Example: debt-triage-pack

A 3-agent team focused on planning, not implementation.

---

## Overview

The debt-triage-pack demonstrates a minimal team composition:
- **3 agents** (no orchestrator, no implementation)
- **3 phases** (collection → assessment → planning)
- **Planning-only output** (produces plans, doesn't execute them)

This pattern works when:
- Domain has clear, linear flow
- No implementation phase needed
- Single type of output (plans)
- Work is handed off to other teams for execution

---

## Directory Structure

```
~/Code/roster/teams/debt-triage-pack/
├── agents/
│   ├── debt-collector.md
│   ├── risk-assessor.md
│   └── sprint-planner.md
└── workflow.yaml
```

---

## workflow.yaml

```yaml
name: debt-triage-pack
workflow_type: sequential
description: Technical debt discovery, risk assessment, and paydown planning

entry_point:
  agent: debt-collector
  artifact:
    type: debt-ledger
    path_template: docs/debt/LEDGER-{slug}.md

phases:
  - name: collection
    agent: debt-collector
    produces: debt-ledger
    next: assessment

  - name: assessment
    agent: risk-assessor
    produces: risk-report
    next: planning

  - name: planning
    agent: sprint-planner
    produces: sprint-plan
    next: null

complexity_levels:
  - name: QUICK
    scope: "Known debt items, immediate assessment"
    phases: [assessment, planning]

  - name: AUDIT
    scope: "Full codebase debt discovery"
    phases: [collection, assessment, planning]

# Agent roles for command mapping:
# /architect   → risk-assessor (closest to design)
# /build       → (N/A - planning only team)
# /qa          → (N/A - planning only team)
# /hotfix      → (N/A - planning only team)
# /code-review → (N/A - planning only team)
```

---

## Agent Configurations

### debt-collector.md (Entry Agent)

```yaml
---
name: debt-collector
description: |
  Discovers and catalogs technical debt across the codebase.
  Invoke when auditing debt, inventorying issues, or starting debt triage.
  Produces debt-ledger.
tools: Bash, Glob, Grep, Read, TodoWrite
model: claude-haiku-4-5
color: orange
---
```

**Key characteristics**:
- Uses `haiku` model (assessment/discovery role)
- `orange` color (entry agent)
- Read-heavy tools (discovery, not modification)

### risk-assessor.md (Middle Agent)

```yaml
---
name: risk-assessor
description: |
  Evaluates technical debt risk and prioritizes remediation.
  Invoke when prioritizing debt, assessing risk, or ranking issues.
  Produces risk-report.
tools: Bash, Glob, Grep, Read, TodoWrite
model: claude-sonnet-4-5
color: cyan
---
```

**Key characteristics**:
- Uses `sonnet` model (analysis role)
- `cyan` color (design/planning agent)
- Analysis-focused, no write tools

### sprint-planner.md (Terminal Agent)

```yaml
---
name: sprint-planner
description: |
  Creates actionable sprint plans for debt paydown.
  Invoke when planning sprints, scheduling debt work, or creating paydown plans.
  Produces sprint-plan.
tools: Bash, Glob, Grep, Read, Write, TodoWrite
model: claude-sonnet-4-5
color: pink
---
```

**Key characteristics**:
- Uses `sonnet` model (planning role)
- `pink` color (terminal/output agent)
- Has `Write` tool (produces final artifact)

---

## Workflow Diagram

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│debt-collector │────▶│ risk-assessor │────▶│sprint-planner │
│   (haiku)     │     │   (sonnet)    │     │   (sonnet)    │
│   orange      │     │     cyan      │     │     pink      │
└───────────────┘     └───────────────┘     └───────────────┘
        │                    │                     │
        ▼                    ▼                     ▼
   debt-ledger          risk-report          sprint-plan
```

---

## Complexity Levels

| Level | Phases | Use When |
|-------|--------|----------|
| QUICK | assessment → planning | Debt items already known |
| AUDIT | collection → assessment → planning | Full codebase discovery |

QUICK skips collection because the debt is already identified.

---

## Command Mapping

This team has limited command support because it's planning-only:

| Command | Agent | Notes |
|---------|-------|-------|
| `/debt` | (team switch) | Activates debt-triage-pack |
| `/architect` | risk-assessor | Closest to design role |
| `/build` | N/A | No implementation |
| `/qa` | N/A | No validation |
| `/hotfix` | N/A | No implementation |

---

## Key Design Decisions

### Why 3 Agents?

1. **Focused domain**: Debt triage is a single concern
2. **No implementation**: Plans are executed by other teams
3. **Linear flow**: Each phase has one clear successor
4. **Minimal overhead**: No orchestrator needed

### Why No Validation Phase?

The output is a plan, not code. Validation happens when:
- 10x-dev-pack implements the debt fixes
- hygiene-pack executes refactoring
- QA validates the actual changes

### Model Assignment Rationale

| Agent | Model | Why |
|-------|-------|-----|
| debt-collector | haiku | Fast discovery, high volume |
| risk-assessor | sonnet | Nuanced analysis needed |
| sprint-planner | sonnet | Careful planning required |

---

## Integration Points

### Quick-Switch Command

`.claude/commands/debt.md`:
```yaml
---
description: Quick switch to debt-triage-pack (technical debt workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---
```

### Cross-Team Handoffs

Sprint plans produced by this team are consumed by:
- **10x-dev-pack**: For feature-related debt
- **hygiene-pack**: For refactoring debt
- **sre-pack**: For reliability debt

---

## When to Use This Pattern

Use a 3-agent pattern when:
- [ ] Domain is focused and specialized
- [ ] No implementation phase needed
- [ ] Output is plans, reports, or assessments
- [ ] Linear flow without branches
- [ ] Other teams handle execution

Don't use when:
- [ ] Implementation is part of the workflow
- [ ] Validation of output is needed
- [ ] Domain has multiple concerns
- [ ] Coordination between sub-tasks required
