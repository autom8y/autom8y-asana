# Agent Glossary

Definitions and patterns for agent roles in team packs.

---

## Role Types

### Entry Agents
First agent in workflow, responsible for initial assessment or requirements gathering.

| Examples | Team | Purpose |
|----------|------|---------|
| requirements-analyst | 10x-dev | Clarify intent, produce PRD |
| doc-auditor | doc-team | Inventory docs, identify gaps |
| code-smeller | hygiene | Detect code quality issues |
| debt-collector | debt-triage | Inventory technical debt |
| observability-engineer | sre | Assess monitoring coverage |

**Characteristics:**
- Typically uses **orange** or **pink** color
- Model: **haiku** (assessment) or **sonnet** (requirements)
- Produces: Reports, audits, inventories, PRDs

---

### Design Agents
Second phase, responsible for planning and architecture.

| Examples | Team | Purpose |
|----------|------|---------|
| architect | 10x-dev | Technical design, ADRs |
| information-architect | doc-team | Document structure |
| architect-enforcer | hygiene | Refactor planning |
| risk-assessor | debt-triage | Evaluate debt risk |
| incident-commander | sre | Reliability planning |

**Characteristics:**
- Typically uses **cyan** color
- Model: **opus** (complex decisions) or **sonnet** (planning)
- Produces: TDDs, plans, designs, structures

---

### Implementation Agents
Third phase, responsible for execution and building.

| Examples | Team | Purpose |
|----------|------|---------|
| principal-engineer | 10x-dev | Write code |
| tech-writer | doc-team | Write documentation |
| janitor | hygiene | Execute refactoring |
| sprint-planner | debt-triage | Plan debt sprints |
| platform-engineer | sre | Build infrastructure |

**Characteristics:**
- Typically uses **green** color
- Model: **sonnet** (balanced execution) or **opus** (complex code)
- Produces: Code, content, changes, infrastructure

---

### Validation Agents
Final phase, responsible for testing and review.

| Examples | Team | Purpose |
|----------|------|---------|
| qa-adversary | 10x-dev | Adversarial testing |
| doc-reviewer | doc-team | Review documentation |
| audit-lead | hygiene | Audit refactoring |
| chaos-engineer | sre | Resilience testing |

**Characteristics:**
- Typically uses **red** color
- Model: **opus** (adversarial thinking)
- Produces: Test plans, signoffs, resilience reports

---

### Coordination Agents
Optional orchestrator for complex multi-phase work.

| Examples | Team | Purpose |
|----------|------|---------|
| orchestrator | 10x-dev | Multi-phase coordination |

**Characteristics:**
- Uses **purple** color
- Model: **opus** (complex coordination)
- Produces: Phase tracking, handoff management

---

## Model Assignment Guide

| Role Complexity | Model | Rationale |
|-----------------|-------|-----------|
| Simple assessment | haiku | Fast pattern detection, low cost |
| Balanced work | sonnet | Good quality/cost tradeoff |
| Complex reasoning | opus | Deep thinking, adversarial analysis |

**By Role:**
- **Orchestration**: opus (complex multi-step reasoning)
- **Senior/Architecture**: opus (structural decisions)
- **Mid-level/Implementation**: sonnet (balanced execution)
- **Assessment/Detection**: haiku (fast analysis)
- **Validation/Adversarial**: opus (creative breaking)

---

## Color Assignment Guide

Colors provide quick visual identification in workflows and diagrams.

| Color | Role Type | Semantic Meaning |
|-------|-----------|------------------|
| purple | Coordination | Orchestration, oversight |
| pink | Requirements | Specification, intent |
| orange | Assessment | Detection, analysis |
| cyan | Design | Architecture, planning |
| green | Execution | Building, implementation |
| red | Validation | Testing, adversarial |
| blue | Documentation | Writing, content |

**Rule:** Each agent in a team should have a unique color.

---

## Tool Allocation

Standard tool sets by role type:

### Full Suite (Orchestration/Senior)
```
Bash, Glob, Grep, Read, Edit, Write, Task, WebFetch, TodoWrite, WebSearch
```

### Standard (Implementation)
```
Bash, Glob, Grep, Read, Edit, Write, Task, TodoWrite
```

### Minimal (Assessment)
```
Bash, Glob, Grep, Read, TodoWrite
```

---

## Agent Markdown Structure

Every agent file follows 11 standard sections:

1. **YAML Frontmatter** - name, description, tools, model, color
2. **Title & Overview** - H1 + 2-3 sentences
3. **Core Responsibilities** - 4-6 bullet points
4. **Position in Workflow** - ASCII diagram
5. **Domain Authority** - You decide / escalate / route
6. **How You Work** - 4-6 numbered phases
7. **What You Produce** - Artifact table
8. **Templates** - Markdown templates for artifacts
9. **Handoff Criteria** - Checkbox list
10. **The Acid Test** - Single pivotal question
11. **Anti-Patterns** - 3-5 failure modes

See [templates/agent.md.template](../templates/agent.md.template) for full template.
