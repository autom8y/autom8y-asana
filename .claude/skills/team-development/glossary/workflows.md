# Workflow Glossary

Definitions and patterns for workflow design.

---

## Core Concepts

### Workflow Type
All team workflows are **sequential**. Phases execute in order, with artifacts flowing from one phase to the next.

```yaml
workflow_type: sequential  # Always sequential
```

**Why sequential?**
- Clear handoff points between agents
- Predictable artifact flow
- Easier debugging and tracking
- Complexity gating works naturally

---

### Phase
A single step in the workflow, owned by one agent.

```yaml
phases:
  - name: requirements        # Phase identifier
    agent: requirements-analyst  # Owning agent
    produces: prd             # Artifact type created
    next: design              # Next phase (or null)
    condition: "complexity >= MODULE"  # Optional gate
```

**Phase Fields:**
| Field | Required | Description |
|-------|----------|-------------|
| name | Yes | Unique identifier (lowercase, hyphenated) |
| agent | Yes | Agent filename (without .md) |
| produces | Yes | Artifact type |
| next | Yes | Next phase name or `null` for terminal |
| condition | No | Complexity gate expression |

---

### Entry Point
The first agent and artifact in the workflow.

```yaml
entry_point:
  agent: requirements-analyst
  artifact:
    type: prd
    path_template: docs/requirements/PRD-{slug}.md
```

Triggered by:
- `/start` command
- `/task` command
- `/sprint` task items

---

### Terminal Phase
The final phase in the workflow (has `next: null`).

```yaml
- name: validation
  agent: qa-adversary
  produces: test-plan
  next: null  # Terminal phase
```

Terminal phases typically:
- Produce signoff or validation reports
- Have no downstream handoff
- Trigger workflow completion

---

## Complexity Gating

### Complexity Levels
Domain-specific scope classifiers that determine which phases run.

```yaml
complexity_levels:
  - name: SCRIPT
    scope: "Single file, <200 LOC"
    phases: [requirements, implementation, validation]
  - name: MODULE
    scope: "Multiple files, <2000 LOC"
    phases: [requirements, design, implementation, validation]
```

**Naming Conventions by Domain:**

| Domain | Levels | Pattern |
|--------|--------|---------|
| Development | SCRIPT, MODULE, SERVICE, PLATFORM | Code scope |
| Documentation | PAGE, SECTION, SITE | Document scope |
| Hygiene | SPOT, MODULE, CODEBASE | Refactor scope |
| Debt | QUICK, AUDIT | Discovery scope |
| SRE | ALERT, SERVICE, SYSTEM, PLATFORM | Reliability scope |

### Conditional Phases
Phases can be skipped based on complexity.

```yaml
- name: design
  agent: architect
  produces: tdd
  next: implementation
  condition: "complexity >= MODULE"  # Skipped for SCRIPT
```

**Common Patterns:**
- Skip design phase for simple work
- Skip assessment for known issues
- Run all phases for complex work

---

## Command Mapping

How slash commands route to team agents.

### Standard Mappings

| Command | Purpose | Maps To |
|---------|---------|---------|
| `/start` | Begin workflow | Entry point agent |
| `/architect` | Design only | Design phase agent |
| `/build` | Implement only | Implementation phase agent |
| `/qa` | Validate only | Validation phase agent |
| `/hotfix` | Fast fix | Implementation or coordination agent |
| `/code-review` | Review changes | Validation agent (review mode) |

### Workflow Detection

Commands find agents by searching workflow:

```bash
# /architect - find design agent
grep -B1 "produces: tdd\|produces: doc-structure" workflow.yaml | grep "agent:"

# /build - find implementation agent
grep -B1 "produces: code\|produces: commits" workflow.yaml | grep "agent:"

# /qa - find validation agent (last phase)
grep -B1 "next: null" workflow.yaml | grep "agent:"
```

### Comment Convention
Document mappings in workflow.yaml:

```yaml
# Agent roles for command mapping:
# /architect  → architect
# /build      → principal-engineer
# /qa         → qa-adversary
# /hotfix     → principal-engineer (fast path)
# /code-review → qa-adversary (review mode)
```

---

## Workflow Examples

### 4-Phase Standard (10x-dev-pack)
```
requirements → design → implementation → validation
    PRD         TDD         Code          Test Plan
```

### 4-Phase Documentation (doc-team-pack)
```
audit → architecture → writing → review
Report   Structure    Content    Signoff
```

### 3-Phase Focused (debt-triage-pack)
```
collection → assessment → planning
  Ledger      Risk Report  Sprint Plan
```

---

## Workflow YAML Structure

Complete reference:

```yaml
name: {team-name}
workflow_type: sequential
description: {Human-readable description}

entry_point:
  agent: {first-agent}
  artifact:
    type: {artifact-type}
    path_template: docs/{category}/{PREFIX}-{slug}.md

phases:
  - name: {phase-name}
    agent: {agent-name}
    produces: {artifact-type}
    next: {next-phase | null}
    condition: "{optional-gate}"

complexity_levels:
  - name: {LEVEL}
    scope: "{description}"
    phases: [{phase-list}]

# Command mapping comments
```
