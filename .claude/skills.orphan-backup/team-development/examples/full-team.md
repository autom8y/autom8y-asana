# Full Team Example: 10x-dev-pack

A 5-agent team with orchestrator for complete development lifecycle.

---

## Overview

The 10x-dev-pack demonstrates the full team composition:
- **5 agents** (4 phases + orchestrator)
- **4 phases** (requirements → design → implementation → validation)
- **Full lifecycle** (from requirements to tested code)
- **Orchestrator** for complex, multi-phase coordination

This pattern works when:
- Complex multi-phase initiatives
- Long-running projects (PLATFORM complexity)
- Multiple handoffs requiring coordination
- Need for explicit phase management

---

## Directory Structure

```
~/Code/roster/teams/10x-dev-pack/
├── agents/
│   ├── orchestrator.md
│   ├── requirements-analyst.md
│   ├── architect.md
│   ├── principal-engineer.md
│   └── qa-adversary.md
└── workflow.yaml
```

---

## workflow.yaml

```yaml
name: 10x-dev-pack
workflow_type: sequential
description: Full-lifecycle software development with PRD/TDD/Code/Test pipeline

entry_point:
  agent: requirements-analyst
  artifact:
    type: prd
    path_template: docs/requirements/PRD-{slug}.md

phases:
  - name: requirements
    agent: requirements-analyst
    produces: prd
    next: design

  - name: design
    agent: architect
    produces: tdd
    next: implementation
    condition: "complexity >= MODULE"

  - name: implementation
    agent: principal-engineer
    produces: code
    next: validation

  - name: validation
    agent: qa-adversary
    produces: test-plan
    next: null

complexity_levels:
  - name: SCRIPT
    scope: "Single file, <200 LOC, no new APIs"
    phases: [requirements, implementation, validation]

  - name: MODULE
    scope: "Multiple files, <2000 LOC, internal APIs"
    phases: [requirements, design, implementation, validation]

  - name: SERVICE
    scope: "New service, external APIs, persistence"
    phases: [requirements, design, implementation, validation]

  - name: PLATFORM
    scope: "Multi-service, cross-team coordination"
    phases: [requirements, design, implementation, validation]

# Agent roles for command mapping:
# /architect   → architect
# /build       → principal-engineer
# /qa          → qa-adversary
# /hotfix      → principal-engineer (fast path)
# /code-review → qa-adversary (review mode)
```

---

## Agent Configurations

### orchestrator.md (Coordinator)

```yaml
---
name: orchestrator
description: |
  Coordinates multi-phase development initiatives.
  Invoke for complex projects, PLATFORM complexity, or multi-sprint work.
  Manages handoffs between agents.
tools: Bash, Glob, Grep, Read, Write, Task, TodoWrite
model: claude-opus-4-5
color: purple
---
```

**Key characteristics**:
- Uses `opus` model (highest capability for coordination)
- `purple` color (coordinator role)
- Has `Task` tool (can spawn sub-agents)
- Not part of phases (manages phases)

### requirements-analyst.md (Entry Agent)

```yaml
---
name: requirements-analyst
description: |
  Clarifies intent and captures requirements.
  Invoke when starting features, defining scope, or writing PRDs.
  Produces prd.
tools: Bash, Glob, Grep, Read, Write, WebFetch, WebSearch, AskUserQuestion, TodoWrite
model: claude-opus-4-5
color: pink
---
```

**Key characteristics**:
- Uses `opus` model (nuanced requirement capture)
- `pink` color (requirements/entry)
- Has `AskUserQuestion` (clarifies with user)
- Has `WebSearch`, `WebFetch` (research)

### architect.md (Design Agent)

```yaml
---
name: architect
description: |
  Designs solutions and makes architectural decisions.
  Invoke for system design, API design, or technical planning.
  Produces tdd, adr.
tools: Bash, Glob, Grep, Read, Write, TodoWrite
model: claude-opus-4-5
color: cyan
---
```

**Key characteristics**:
- Uses `opus` model (deep design thinking)
- `cyan` color (design/architecture)
- Conditional phase (skipped for SCRIPT)
- Produces multiple artifacts (TDD, ADR)

### principal-engineer.md (Implementation Agent)

```yaml
---
name: principal-engineer
description: |
  Implements solutions with craft and discipline.
  Invoke for coding, refactoring, or building features.
  Produces code.
tools: Bash, Glob, Grep, Read, Edit, Write, NotebookEdit, Task, TodoWrite
model: claude-sonnet-4-5
color: green
---
```

**Key characteristics**:
- Uses `sonnet` model (balanced for coding)
- `green` color (implementation)
- Has `Edit` tool (modifies existing code)
- Has `Task` tool (can delegate sub-tasks)

### qa-adversary.md (Validation Agent)

```yaml
---
name: qa-adversary
description: |
  Validates quality and finds problems before production.
  Invoke for testing, code review, or quality validation.
  Produces test-plan.
tools: Bash, Glob, Grep, Read, Edit, Write, TodoWrite
model: claude-opus-4-5
color: red
---
```

**Key characteristics**:
- Uses `opus` model (thorough adversarial thinking)
- `red` color (validation/testing)
- Terminal phase (`next: null`)
- Adversarial mindset

---

## Workflow Diagram

```
                         ┌─────────────────┐
                         │   orchestrator  │
                         │     (opus)      │
                         │     purple      │
                         └────────┬────────┘
                                  │ coordinates
                                  ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  requirements-   │───▶│    architect     │───▶│    principal-    │───▶│   qa-adversary   │
│    analyst       │    │     (opus)       │    │     engineer     │    │     (opus)       │
│    (opus)        │    │      cyan        │    │    (sonnet)      │    │      red         │
│     pink         │    │                  │    │     green        │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘    └──────────────────┘
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
       PRD                     TDD                    Code                  Test Plan
```

---

## Complexity Levels

| Level | Phases | Skips | Use When |
|-------|--------|-------|----------|
| SCRIPT | req → impl → val | design | Single file, <200 LOC |
| MODULE | req → design → impl → val | (none) | Multi-file, <2000 LOC |
| SERVICE | req → design → impl → val | (none) | APIs, persistence |
| PLATFORM | req → design → impl → val | (none) | Multi-service |

SCRIPT skips design because small changes don't need formal TDD.

---

## Command Mapping

| Command | Agent | Use Case |
|---------|-------|----------|
| `/10x` | (team switch) | Activate 10x-dev-pack |
| `/architect` | architect | Design-only session |
| `/build` | principal-engineer | Implementation-only |
| `/qa` | qa-adversary | Validation-only |
| `/hotfix` | principal-engineer | Fast fix (skip design) |
| `/code-review` | qa-adversary | Review mode |

---

## Orchestrator Role

The orchestrator is special:
- **Not a phase**: Manages phases, doesn't participate in them
- **Invoked for**: PLATFORM complexity, multi-sprint work
- **Responsibilities**:
  - Track progress across phases
  - Manage handoffs
  - Coordinate cross-cutting concerns
  - Handle phase failures

### When Orchestrator Activates

```
Complexity = PLATFORM?  ──▶  Orchestrator coordinates
Complexity < PLATFORM?  ──▶  Agents self-coordinate via handoffs
```

---

## Model Assignment Rationale

| Agent | Model | Reasoning |
|-------|-------|-----------|
| orchestrator | opus | Complex coordination, judgment |
| requirements-analyst | opus | Nuanced requirement capture |
| architect | opus | Deep design thinking |
| principal-engineer | sonnet | Balanced coding capability |
| qa-adversary | opus | Thorough adversarial analysis |

The team uses opus heavily because:
- Development decisions have high impact
- Nuance matters in requirements and design
- QA needs adversarial depth

principal-engineer uses sonnet because:
- Coding is more mechanical
- Design decisions already made
- Speed matters for implementation

---

## Conditional Phase: Design

The design phase is conditional:

```yaml
- name: design
  agent: architect
  produces: tdd
  next: implementation
  condition: "complexity >= MODULE"
```

This means:
- **SCRIPT**: requirements → implementation → validation
- **MODULE+**: requirements → design → implementation → validation

Rationale: Small changes don't need formal TDD.

---

## Integration Points

### Quick-Switch Command

`.claude/commands/10x.md`:
```yaml
---
description: Quick switch to 10x-dev-pack (full development workflow)
allowed-tools: Bash, Read
model: claude-haiku-4-5
---
```

### Artifacts Produced

| Phase | Artifact | Path |
|-------|----------|------|
| requirements | PRD | `docs/requirements/PRD-{slug}.md` |
| design | TDD | `docs/design/TDD-{slug}.md` |
| design | ADR | `docs/decisions/ADR-{number}-{slug}.md` |
| implementation | Code | Various source files |
| validation | Test Plan | `docs/tests/TEST-{slug}.md` |

### Cross-Team Handoffs

Work discovered during development routes to:
- **doc-team-pack**: Documentation gaps
- **hygiene-pack**: Code quality issues
- **debt-triage-pack**: Technical debt
- **sre-pack**: Reliability concerns

---

## When to Use This Pattern

Use a 5-agent pattern when:
- [ ] Full development lifecycle needed
- [ ] Multiple phases with distinct outputs
- [ ] High-complexity work (SERVICE, PLATFORM)
- [ ] Multiple handoffs requiring coordination
- [ ] Quality gates between phases

The orchestrator is optional:
- [ ] Include for PLATFORM complexity
- [ ] Include for multi-sprint initiatives
- [ ] Omit for simpler work (agents self-coordinate)

---

## Comparison: 3 vs 4 vs 5 Agents

| Team | Agents | Phases | Orchestrator | Use Case |
|------|--------|--------|--------------|----------|
| debt-triage | 3 | 3 | No | Planning only |
| sre-pack | 4 | 4 | No | Standard lifecycle |
| 10x-dev | 5 | 4 | Yes | Full lifecycle |

The extra agent in 10x-dev is the orchestrator, which coordinates but doesn't own a phase.
