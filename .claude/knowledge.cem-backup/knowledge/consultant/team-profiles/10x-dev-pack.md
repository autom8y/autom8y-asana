# 10x-dev-pack

> Full-cycle feature development from requirements to validation

## Overview

The primary development team for building new features and functionality. This team takes work from initial requirements through design, implementation, and testing using a structured handoff workflow.

## Switch Command

```bash
/10x
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **orchestrator** | opus | Coordinates multi-phase workflows |
| **requirements-analyst** | opus | Clarifies intent, produces PRD |
| **architect** | opus | Designs solutions, produces TDD/ADRs |
| **principal-engineer** | sonnet | Implements with craft |
| **qa-adversary** | opus | Validates, finds problems |

## Workflow

```
requirements → design → implementation → validation
     │            │            │              │
     ▼            ▼            ▼              ▼
   PRD         TDD/ADR       Code          Test Report
```

## Complexity Levels

| Level | When to Use | Phases |
|-------|-------------|--------|
| **SCRIPT** | Single file, utility | requirements, implementation |
| **MODULE** | Component, moderate scope | All 4 |
| **SERVICE** | New service, APIs | All 4 |
| **PLATFORM** | Cross-cutting, architecture | All 4 + extra |

## Best For

- New feature development
- API implementation
- Component creation
- Full-cycle work with structured handoffs

## Not For

- Pure documentation → use doc-team-pack
- Code cleanup without new features → use hygiene-pack
- Security-only work → use security-pack
- Quick spikes → use /spike command

## Quick Start

```bash
/10x                           # Switch to team
/start "Feature name"          # Initialize session
# Work through phases...
/wrap                          # Finalize
/pr                            # Create PR
```

## Common Patterns

### Standard Feature

```bash
/10x
/task "Add user preferences page" --complexity=MODULE
```

### Design Only

```bash
/10x
/architect                     # Just produce TDD
```

### Implementation Only

```bash
/10x
/build                         # Assumes TDD exists
```

## Related Commands

- `/task` - Full lifecycle
- `/architect` - Design only
- `/build` - Implementation only
- `/qa` - Validation only
- `/sprint` - Multi-task coordination
