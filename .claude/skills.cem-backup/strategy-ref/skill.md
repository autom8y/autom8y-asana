---
name: strategy-ref
description: |
  Reference documentation for Strategy Team.
  Use when: learning about strategy-pack agents, understanding the strategy workflow,
  invoking strategy agents. Triggers: strategy-pack, strategy team, market-researcher,
  competitive-analyst, business-model-analyst, roadmap-strategist.
---

# Strategy Team (strategy-pack)

> Research. Analyze. Model. Strategize.

## Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Agents | `~/Code/roster/teams/strategy-pack/agents/` | Agent prompts |
| Workflow | `~/Code/roster/teams/strategy-pack/workflow.yaml` | Phase configuration |
| Switch | `/strategy` | Activate this team |

## Team Roster

| Agent | Model | Role | Produces |
|-------|-------|------|----------|
| **market-researcher** | sonnet | Maps market terrain and trends | market-analysis |
| **competitive-analyst** | opus | Tracks competitors and predicts moves | competitive-intel |
| **business-model-analyst** | opus | Stress-tests unit economics | financial-model |
| **roadmap-strategist** | opus | Connects vision to execution | strategic-roadmap |

## Workflow

```
market-research → competitive-analysis → business-modeling → strategic-planning
       │                  │                    │                    │
       ▼                  ▼                    ▼                    ▼
 MARKET-{slug}     COMPETE-{slug}       FINANCE-{slug}      STRATEGY-{slug}
```

### Phase Details

| Phase | Agent | Input | Output |
|-------|-------|-------|--------|
| market-research | market-researcher | Strategic question | Market analysis |
| competitive-analysis | competitive-analyst | Market context | Competitive intel |
| business-modeling | business-model-analyst | Competitive context | Financial model |
| strategic-planning | roadmap-strategist | Financial model | Strategic roadmap |

## Complexity Levels

| Level | Scope | Phases |
|-------|-------|--------|
| **TACTICAL** | Single decision, existing data | business-modeling, strategic-planning |
| **STRATEGIC** | New market entry, major bet | All phases |
| **TRANSFORMATION** | Business model change | All phases |

## Command Mapping

| Command | Maps To | Use When |
|---------|---------|----------|
| `/strategy` | Team switch | Activating this team |
| `/architect` | competitive-analyst | Competitive analysis only |
| `/build` | business-model-analyst | Financial modeling only |
| `/qa` | roadmap-strategist | Strategic planning only |
| `/hotfix` | N/A | Not applicable (strategy team) |
| `/code-review` | N/A | Not applicable (strategy team) |

## When to Use This Team

**Use strategy-pack when:**
- Market sizing and analysis
- Competitive intelligence
- Pricing and business model analysis
- Strategic roadmap planning

**Don't use strategy-pack when:**
- Building features → Use 10x-dev-pack
- Product analytics → Use intelligence-pack
- Technology evaluation → Use rnd-pack

## Agent Summaries

### Market Researcher

**Purpose**: Map the market terrain

**Key Responsibilities**:
- Market sizing (TAM/SAM/SOM)
- Segment analysis
- Trend identification
- Buyer research

**Produces**: `docs/strategy/MARKET-{slug}.md`

---

### Competitive Analyst

**Purpose**: Know competitors better than they know themselves

**Key Responsibilities**:
- Competitor monitoring
- Competitive intelligence
- Market positioning
- Predictive analysis

**Produces**: `docs/strategy/COMPETE-{slug}.md`

---

### Business Model Analyst

**Purpose**: Stress-test how we make money

**Key Responsibilities**:
- Unit economics analysis
- Pricing analysis
- Margin analysis
- Scenario modeling

**Produces**: `docs/strategy/FINANCE-{slug}.md`

---

### Roadmap Strategist

**Purpose**: Connect vision to execution

**Key Responsibilities**:
- Strategic prioritization
- Resource allocation
- OKR design
- Roadmap construction

**Produces**: `docs/strategy/STRATEGY-{slug}.md`

## Cross-References

- **Related Skills**: @documentation (artifact templates)
- **Team Packs**: intelligence-pack (product analytics), rnd-pack (technology strategy)
- **Commands**: See COMMAND_REGISTRY.md
