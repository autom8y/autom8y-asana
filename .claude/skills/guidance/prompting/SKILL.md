---
name: prompting
description: "Agent invocation and workflow prompt patterns. Use when: invoking specialist agents, starting orchestrated sessions, needing copy-paste prompt templates. Triggers: how to invoke, prompt pattern, agent invocation, workflow example, session start."
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

### Orchestrator Consultation Pattern

The orchestrator is NOT invoked to execute. It is CONSULTED for direction.

See the `orchestrator-templates` skill for the complete consultation loop pattern, or reference the orchestrator agent prompt directly.

**Quick Pattern**:
```
1. Build CONSULTATION_REQUEST (YAML)
2. Task tool -> orchestrator with request
3. Parse CONSULTATION_RESPONSE
4. Task tool -> specialist with prompt from response
5. Build checkpoint request, return to step 2
```

## Task Tool Architecture

**Critical**: Only the main agent has Task tool permissions.

Subagents (including orchestrators) cannot invoke the Task tool. When the main agent delegates work:

1. **Select the most specific specialized subagent** - never use generalist agents when specialists exist
2. **Provide complete context** - subagents cannot delegate further or fetch missing context
3. **Expect atomic completion** - subagent returns when work is done, main agent decides next step

**Anti-pattern**: Subagent trying to spawn another subagent
**Correct pattern**: Subagent completes its work, returns to main agent, main agent delegates to next specialist

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
- **Implementation**: [patterns/implementation.md](patterns/implementation.md) - TDD, ADRs, coding
- **Validation**: [patterns/validation.md](patterns/validation.md) - Testing, QA gates
- **Maintenance**: [patterns/maintenance.md](patterns/maintenance.md) - Bug investigation, feature additions
- **Meta-Prompts**: [patterns/meta-prompts.md](patterns/meta-prompts.md) - Process audits, retrospectives

## Complete Workflow Examples

- [new-feature.md](workflows/new-feature.md) - Full 4-phase feature development
- [legacy-migration.md](workflows/legacy-migration.md) - Migration workflow
- [quick-fix.md](workflows/quick-fix.md) - Abbreviated bug fix
- [spike-exploration.md](workflows/spike-exploration.md) - Exploratory spike
- [feature-extension.md](workflows/feature-extension.md) - Extend existing feature
- [refactoring.md](workflows/refactoring.md) - Refactor without behavior change

## Cross-Skill Integration

- [standards](../standards/INDEX.lego.md) - Code conventions
- Rite-specific skills - Each rite provides documentation templates and workflow definitions

## When Patterns Don't Fit

Not every task needs the full workflow. Escape hatches:

| Situation | Approach |
|-----------|----------|
| **Trivial fix** | Skip PRD/TDD, use `quick-fix` workflow |
| **Exploration** | Use `spike-exploration`, no artifacts required |
| **Unclear scope** | Start with discovery only, defer implementation |
| **Pattern mismatch** | Adapt the closest pattern, document deviations in ADR |

**Principle**: Patterns are starting points, not constraints. If a pattern adds friction without value, simplify.
