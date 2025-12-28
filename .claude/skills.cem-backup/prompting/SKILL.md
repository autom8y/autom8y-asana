---
name: prompting
description: "Copy-paste prompt patterns for agent invocation and workflow execution. Use when: invoking agents, starting sessions, creating PRDs/TDDs, implementing features, validating work. Triggers: how to invoke, prompt pattern, agent invocation, copy paste prompt, workflow example, session start, PRD prompt, TDD prompt."
---

# Prompting Patterns

> Copy-paste templates for 10x workflow

## Quick Reference: Agent Invocation

| Agent | Basic Invocation | Use When |
|-------|-----------------|----------|
| **Requirements Analyst** | `Act as Requirements Analyst. Create PRD for: {feature}` | Defining what to build |
| **Architect** | `Act as Architect. Create TDD from PRD-{NNNN}` | Designing architecture |
| **Principal Engineer** | `Act as Principal Engineer. Implement TDD-{NNNN}` | Writing code |
| **QA/Adversary** | `Act as QA/Adversary. Validate PRD-{NNNN}` | Testing, validation |
| **Orchestrator** | `Act as Orchestrator. Coordinate: {initiative}` | Multi-phase initiatives |

**New sessions**: Skills activate automatically based on your task.

## Workflow Shortcuts

### Full Feature (4-Phase)

```
Let's build: {feature}
Phase 1: Act as Analyst, create PRD
Phase 2: Act as Architect, create TDD + ADRs
Phase 3: Act as Engineer, implement
Phase 4: Act as QA, validate
I'll approve each phase.
```

### Quick Fix

```
Simple bug fix, abbreviated workflow.
Bug: {description}
Act as Engineer: fix it.
Then act as QA: add regression test.
```

### Spike/Exploration

```
Exploratory work, skip PRD/TDD.
Test: {concept}
Act as Engineer, prototype to answer: {question}
```

## Progressive Patterns by Phase

- **Discovery**: [patterns/discovery.md](patterns/discovery.md) - Session init, PRD creation, requirements
- **Implementation**: [patterns/implementation.md](patterns/implementation.md) - TDD, ADRs, coding, refactoring
- **Validation**: [patterns/validation.md](patterns/validation.md) - Testing, validation, maintenance

## Complete Workflow Examples

- [new-feature.md](workflows/new-feature.md) - Full 4-phase feature development
- [legacy-migration.md](workflows/legacy-migration.md) - Migration workflow
- [quick-fix.md](workflows/quick-fix.md) - Abbreviated bug fix
- [spike-exploration.md](workflows/spike-exploration.md) - Exploratory spike
- [feature-extension.md](workflows/feature-extension.md) - Extend existing feature
- [refactoring.md](workflows/refactoring.md) - Refactor without behavior change

## Cross-Skill Integration

- [10x-workflow](../10x-workflow/SKILL.md) - Pipeline flow, quality gates
- [documentation](../documentation/SKILL.md) - PRD/TDD/ADR templates
- [standards](../standards/SKILL.md) - Code conventions
