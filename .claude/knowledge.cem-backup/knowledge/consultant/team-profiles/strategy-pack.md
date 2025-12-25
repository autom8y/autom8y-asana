# strategy-pack

> Market research, competitive analysis, and business planning

## Overview

The strategy team for business analysis and planning. Handles market research, competitive intelligence, business model analysis, and strategic roadmap development.

## Switch Command

```bash
/strategy
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **market-researcher** | sonnet | Maps market terrain and trends |
| **competitive-analyst** | opus | Tracks competitors |
| **business-model-analyst** | opus | Stress-tests unit economics |
| **roadmap-strategist** | opus | Connects vision to execution |

## Workflow

```
market-research → competitive-analysis → business-modeling → strategic-planning
       │                  │                    │                    │
       ▼                  ▼                    ▼                    ▼
   MARKET-*          COMPETE-*            FINANCE-*           STRATEGY-*
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **TACTICAL** | Single decision, existing data | Short-term |
| **STRATEGIC** | New market entry, major bet | Medium-term |
| **TRANSFORMATION** | Business model change | Long-term |

## Best For

- Market sizing (TAM/SAM/SOM)
- Competitive intelligence
- Pricing analysis
- Go-to-market planning
- Strategic roadmaps
- OKR development

## Not For

- Feature development → use 10x-dev-pack
- User research → use intelligence-pack
- Technical feasibility → use rnd-pack

## Quick Start

```bash
/strategy                      # Switch to team
/task "Competitive analysis for enterprise segment"
```

## Common Patterns

### Market Research

```bash
/strategy
/task "Size the SMB market for our product" --complexity=STRATEGIC
```

### Competitive Analysis

```bash
/strategy
/task "Track competitor pricing changes"
```

### Business Model

```bash
/strategy
/task "Stress-test freemium model economics"
```

### Strategic Roadmap

```bash
/strategy
/task "Create H2 strategic roadmap" --complexity=STRATEGIC
```

## Integration with Other Teams

```bash
# Strategy informs development:
/strategy                      # Define market opportunity
/10x                          # Build to capture it

# Strategy uses intelligence:
/intelligence                  # User research
/strategy                      # Strategic synthesis
```

## Related Commands

- `/task` - Full strategy lifecycle
