# intelligence-pack

> Analytics, experimentation, and user research

## Overview

The product intelligence team for data-driven decisions. Handles instrumentation, user research, A/B testing, and insights synthesis.

## Switch Command

```bash
/intelligence
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **analytics-engineer** | sonnet | Builds tracking/data foundation |
| **user-researcher** | opus | Captures qualitative insights |
| **experimentation-lead** | opus | Designs A/B tests |
| **insights-analyst** | opus | Synthesizes data into decisions |

## Workflow

```
instrumentation → research → experimentation → synthesis
       │             │              │              │
       ▼             ▼              ▼              ▼
   TRACK-*      RESEARCH-*     EXPERIMENT-*    INSIGHT-*
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **METRIC** | Single metric, existing events | One measurement |
| **FEATURE** | New feature instrumentation | Feature scope |
| **INITIATIVE** | Cross-feature analysis | Multi-feature |

## Best For

- Event tracking setup
- A/B test design
- User research planning
- Metric definition
- Experiment analysis
- Data-driven decisions

## Not For

- Feature implementation → use 10x-dev-pack
- Market research → use strategy-pack
- Technical feasibility → use rnd-pack

## Quick Start

```bash
/intelligence                  # Switch to team
/task "Instrument checkout funnel"
```

## Common Patterns

### Feature Instrumentation

```bash
/intelligence
/task "Add tracking to new onboarding flow" --complexity=FEATURE
```

### A/B Test

```bash
/intelligence
/task "Design A/B test for pricing page"
```

### User Research

```bash
/intelligence
/task "Plan user interviews for navigation redesign"
```

## Integration with Development

```bash
# Before feature launch:
/intelligence                  # Define metrics
/10x                          # Build feature with tracking
/intelligence                  # Analyze results
```

## Related Commands

- `/task` - Full intelligence lifecycle
