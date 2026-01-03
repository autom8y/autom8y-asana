---
name: rnd-ref
description: "Innovation Lab (R&D) reference with technology scouting, prototyping, and moonshot architecture workflows. Use when: learning about rnd-pack agents, understanding the innovation workflow, invoking R&D agents. Triggers: rnd-pack, innovation lab, technology-scout, integration-researcher, prototype-engineer, moonshot-architect."
---

# Innovation Lab (rnd-pack)

> Scout. Integrate. Prototype. Envision.

## Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| Agents | `$ROSTER_HOME/teams/rnd-pack/agents/` | Agent prompts |
| Workflow | `$ROSTER_HOME/teams/rnd-pack/workflow.yaml` | Phase configuration |
| Switch | `/rnd` | Activate this team |

## Team Roster

| Agent | Model | Role | Produces |
|-------|-------|------|----------|
| **technology-scout** | sonnet | Watches the technology horizon | tech-assessment |
| **integration-researcher** | sonnet | Maps integration paths | integration-map |
| **prototype-engineer** | sonnet | Builds decision-ready demos | prototype |
| **moonshot-architect** | opus | Designs future systems | moonshot-plan |

## Workflow

```
scouting → integration-analysis → prototyping → future-architecture
    │              │                  │                │
    ▼              ▼                  ▼                ▼
SCOUT-{slug}  INTEGRATE-{slug}    PROTO-{slug}   MOONSHOT-{slug}
```

### Phase Details

| Phase | Agent | Input | Output |
|-------|-------|-------|--------|
| scouting | technology-scout | Technology question | Tech assessment |
| integration-analysis | integration-researcher | Tech assessment | Integration map |
| prototyping | prototype-engineer | Integration map | Working prototype |
| future-architecture | moonshot-architect | Prototype learnings | Long-term plan |

## Complexity Levels

| Level | Scope | Phases |
|-------|-------|--------|
| **SPIKE** | Quick feasibility check | scouting, prototyping |
| **EVALUATION** | Full technology evaluation | All phases |
| **MOONSHOT** | Paradigm shift exploration | All phases |

## Command Mapping

| Command | Maps To | Use When |
|---------|---------|----------|
| `/rnd` | Team switch | Activating this team |
| `/architect` | integration-researcher | Integration analysis only |
| `/build` | prototype-engineer | Prototyping only |
| `/qa` | moonshot-architect | Future architecture only |
| `/hotfix` | N/A | Not applicable (R&D team) |
| `/code-review` | N/A | Not applicable (R&D team) |

## When to Use This Team

**Use rnd-pack when:**
- Evaluating new technologies
- Building proof-of-concept prototypes
- Planning long-term architecture
- Exploring paradigm shifts

**Don't use rnd-pack when:**
- Building production features → Use 10x-dev-pack
- Security assessment → Use security-pack
- Business analysis → Use strategy-pack

## Agent Summaries

### Technology Scout

**Purpose**: Watch the horizon for opportunities and threats

**Key Responsibilities**:
- Horizon scanning
- Technology evaluation
- Opportunity identification
- Risk assessment

**Produces**: `docs/rnd/SCOUT-{slug}.md`

---

### Integration Researcher

**Purpose**: Map how new capabilities plug in

**Key Responsibilities**:
- Dependency mapping
- API analysis
- Effort estimation
- Migration planning

**Produces**: `docs/rnd/INTEGRATE-{slug}.md`

---

### Prototype Engineer

**Purpose**: Build throwaway code that enables decisions

**Key Responsibilities**:
- Rapid prototyping
- Feasibility validation
- Constraint discovery
- Knowledge transfer

**Produces**: `docs/rnd/PROTO-{slug}.md`

---

### Moonshot Architect

**Purpose**: Design systems for futures that haven't happened

**Key Responsibilities**:
- Scenario planning
- Future architecture design
- Assumption stress-testing
- Migration path design

**Produces**: `docs/rnd/MOONSHOT-{slug}.md`

## Cross-References

- **Related Skills**: @standards (architectural principles)
- **Team Packs**: 10x-dev-pack (implementation), strategy-pack (strategic context)
- **Commands**: See COMMAND_REGISTRY.md
