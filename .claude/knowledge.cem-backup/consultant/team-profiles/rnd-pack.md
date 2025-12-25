# rnd-pack

> Technology exploration, prototyping, and innovation

## Overview

The R&D team for exploring new technologies, building prototypes, and designing future architecture. Focuses on learning and feasibility rather than production code.

## Switch Command

```bash
/rnd
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **technology-scout** | sonnet | Watches the horizon for trends |
| **integration-researcher** | sonnet | Maps integration paths |
| **prototype-engineer** | sonnet | Builds decision-ready demos |
| **moonshot-architect** | opus | Designs future systems |

## Workflow

```
scouting → integration-analysis → prototyping → future-architecture
    │              │                  │                │
    ▼              ▼                  ▼                ▼
 SCOUT-*      INTEGRATE-*         PROTO-*        MOONSHOT-*
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **SPIKE** | Quick feasibility check | Time-boxed |
| **EVALUATION** | Full technology evaluation | Thorough |
| **MOONSHOT** | Paradigm shift exploration | Extensive |

## Best For

- Technology evaluation
- Proof of concept builds
- Integration feasibility
- Future architecture design
- Innovation exploration

## Not For

- Production features → use 10x-dev-pack
- Bug fixes → use /hotfix
- Business analysis → use strategy-pack

## Quick Start

```bash
/rnd                           # Switch to team
/task "Evaluate GraphQL for our API"
```

## Common Patterns

### Technology Spike

```bash
/rnd
/task "Quick feasibility check for WebSockets" --complexity=SPIKE
```

### Full Evaluation

```bash
/rnd
/task "Evaluate Kubernetes migration" --complexity=EVALUATION
```

### Prototype

```bash
/rnd
/task "Prototype real-time collaboration feature"
```

### Future Architecture

```bash
/rnd
/task "Design 2-year architecture vision" --complexity=MOONSHOT
```

## From R&D to Production

When prototype succeeds:
```bash
/rnd                           # Complete prototype
/10x                          # Productionize with full workflow
```

## Related Commands

- `/task` - Full R&D lifecycle
- `/spike` - Quick spikes (lighter than full R&D)
