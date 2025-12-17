---
name: initiative-scoping
description: "Prompt -1 and Prompt 0 templates for initiative kickoff. Use when: starting new projects, scoping major initiatives, writing kickoff documents, defining project boundaries. Triggers: prompt 0, prompt -1, initiative scoping, project kickoff, new project, major initiative, scoping document, initialization prompt."
status: complete
---

# Initiative Scoping (Prompt -1/0)

> Templates for the two critical initialization prompts that start new initiatives.

## Quick Decision Framework

| Scenario | Use Prompt -1? | Use Prompt 0? | Rationale |
|----------|----------------|---------------|-----------|
| New feature (complex) | Yes | Yes | Full scoping validates readiness |
| New feature (simple) | No | Yes | Skip scoping, init orchestrator |
| Major refactoring | Yes | Yes | Risk assessment critical |
| Bug fix (isolated) | No | No | Direct implementation |
| Bug fix (cross-cutting) | Yes | Yes | Dependencies need validation |
| Sprint planning | Yes | Maybe | Scope first, orchestrate if complex |
| Exploration/spike | No | No | Direct implementation |

## Initiative Flow

```
Problem/Idea
    |
    v
+-------------+
| Prompt -1   |  Scope & validate
| (Scoping)   |  Go/No-Go decision
+-------------+
    |
    v
+-------------+
| Prompt 0    |  Initialize orchestrator
| (Init)      |  Set up 4-agent workflow
+-------------+
    |
    v
Sessions 1-N (Execution)
```

## Prompt -1 Overview

**Purpose**: Validate initiative readiness before committing to the full 4-agent workflow.

**Key Sections**:
- Problem Validation (is it real? who's affected?)
- Scope Boundaries (in/out of scope)
- Complexity Assessment (right-size the workflow)
- Dependencies & Blockers
- Risk Assessment
- Go/No-Go Decision

**Output**: GO / CONDITIONAL GO / NO-GO recommendation

See: [prompt-minus-1.md](prompt-minus-1.md)

## Prompt 0 Overview

**Purpose**: Initialize the Orchestrator with full context to coordinate the 4-agent workflow.

**Key Sections**:
- Context & Documentation to read
- Mission statement & success criteria
- Current state & target architecture
- Session-phased approach (7 sessions)
- Discovery phase requirements
- Open questions

**Output**: Orchestrator confirmation and Session 1 readiness

See: [prompt-0.md](prompt-0.md)

## Common Workflows

**Full Initiative** (new feature, migration):
1. Create Prompt -1 to validate scope
2. Get GO decision
3. Create Prompt 0 with Prompt -1 context
4. Orchestrator runs Sessions 1-7

**Quick Start** (validated scope, simple feature):
1. Skip Prompt -1
2. Create Prompt 0 directly
3. Orchestrator runs Sessions 1-7

**Abbreviated** (bug fix, small task):
1. Skip both prompts
2. Use `prompting` skill for direct agent invocation

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Pipeline flow after initialization
- [documentation](../documentation/SKILL.md) - PRD/TDD templates for Sessions 2-3
- [prompting](../prompting/SKILL.md) - Agent invocation patterns

## Agent Configuration

The Orchestrator is initialized by Prompt 0 and coordinates:

| Agent | Session | Deliverable |
|-------|---------|-------------|
| Requirements Analyst | 1-2 | Discovery doc, PRD |
| Architect | 3 | TDD, ADRs |
| Principal Engineer | 4-6 | Implementation |
| QA/Adversary | 7 | Validation report |
