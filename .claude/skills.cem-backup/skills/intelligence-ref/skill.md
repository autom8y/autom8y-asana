---
name: intelligence-ref
description: |
  Reference documentation for Product Intelligence Team.
  Use when: learning about intelligence-pack agents, understanding the analytics workflow,
  invoking intelligence agents. Triggers: intelligence-pack, product intelligence,
  analytics-engineer, user-researcher, experimentation-lead, insights-analyst.
---

# Product Intelligence Team (intelligence-pack)

> Instrument. Research. Experiment. Synthesize.

## Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Agents | `~/Code/roster/teams/intelligence-pack/agents/` | Agent prompts |
| Workflow | `~/Code/roster/teams/intelligence-pack/workflow.yaml` | Phase configuration |
| Switch | `/intelligence` | Activate this team |

## Team Roster

| Agent | Model | Role | Produces |
|-------|-------|------|----------|
| **analytics-engineer** | sonnet | Builds data foundation and tracking | tracking-plan |
| **user-researcher** | opus | Captures qualitative insights | research-findings |
| **experimentation-lead** | opus | Designs A/B tests and experiments | experiment-design |
| **insights-analyst** | opus | Synthesizes data into decisions | insights-report |

## Workflow

```
instrumentation → research → experimentation → synthesis
        │            │              │              │
        ▼            ▼              ▼              ▼
  TRACK-{slug}  RESEARCH-{slug}  EXPERIMENT-{slug}  INSIGHT-{slug}
```

### Phase Details

| Phase | Agent | Input | Output |
|-------|-------|-------|--------|
| instrumentation | analytics-engineer | Feature specs | Tracking plan with events |
| research | user-researcher | Tracking plan | Qualitative findings |
| experimentation | experimentation-lead | Research findings | Experiment design |
| synthesis | insights-analyst | Experiment results | Actionable insights |

## Complexity Levels

| Level | Scope | Phases |
|-------|-------|--------|
| **METRIC** | Single metric, existing events | experimentation, synthesis |
| **FEATURE** | New feature instrumentation | All phases |
| **INITIATIVE** | Cross-feature analysis | All phases |

## Command Mapping

| Command | Maps To | Use When |
|---------|---------|----------|
| `/intelligence` | Team switch | Activating this team |
| `/architect` | experimentation-lead | Experiment design only |
| `/build` | analytics-engineer | Instrumentation only |
| `/qa` | insights-analyst | Analysis only |
| `/hotfix` | N/A | Not applicable (research team) |
| `/code-review` | N/A | Not applicable (research team) |

## When to Use This Team

**Use intelligence-pack when:**
- Instrumenting a new feature
- Running A/B tests
- Conducting user research
- Making data-driven decisions

**Don't use intelligence-pack when:**
- Building features → Use 10x-dev-pack
- Security analysis → Use security-pack
- Market research → Use strategy-pack

## Agent Summaries

### Analytics Engineer

**Purpose**: Build the data foundation

**Key Responsibilities**:
- Event taxonomy design
- Tracking plan development
- Data quality assurance
- Pipeline architecture

**Produces**: `docs/intelligence/TRACK-{slug}.md`

---

### User Researcher

**Purpose**: Capture the qualitative 'why'

**Key Responsibilities**:
- Research design
- User interviews
- Usability testing
- Synthesis

**Produces**: `docs/intelligence/RESEARCH-{slug}.md`

---

### Experimentation Lead

**Purpose**: Run the scientific method on product

**Key Responsibilities**:
- Hypothesis formation
- A/B test design
- Sample size calculation
- Statistical rigor

**Produces**: `docs/intelligence/EXPERIMENT-{slug}.md`

---

### Insights Analyst

**Purpose**: Turn data into decisions

**Key Responsibilities**:
- Result interpretation
- Story building
- Recommendation synthesis
- Stakeholder communication

**Produces**: `docs/intelligence/INSIGHT-{slug}.md`

## Cross-References

- **Related Skills**: @documentation (artifact templates)
- **Team Packs**: 10x-dev-pack (implementation), strategy-pack (strategic context)
- **Commands**: See COMMAND_REGISTRY.md
