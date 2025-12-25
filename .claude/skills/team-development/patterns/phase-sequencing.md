# Phase Sequencing Patterns

How to design sequential workflow phases.

---

## Core Principle

**All workflows are sequential.**

```
Phase 1 → Phase 2 → Phase 3 → Phase 4
   │          │          │          │
   ▼          ▼          ▼          ▼
Artifact   Artifact   Artifact   Artifact
```

No parallel phases. No branching. Each phase:
1. Receives input from previous phase
2. Produces an artifact
3. Hands off to next phase

---

## Phase Design Rules

### Rule 1: One Agent Per Phase
Each phase is owned by exactly one agent.

```yaml
# Good
- name: design
  agent: architect
  produces: tdd

# Bad - multiple agents
- name: design
  agents: [architect, senior-engineer]  # Not supported
```

### Rule 2: One Artifact Per Phase
Each phase produces exactly one artifact type.

```yaml
# Good
- name: requirements
  produces: prd

# Bad - multiple artifacts
- name: requirements
  produces: [prd, scope-doc]  # Not supported
```

### Rule 3: Clear Handoff Points
The `next` field creates explicit handoffs.

```yaml
phases:
  - name: requirements
    next: design       # Explicit handoff

  - name: design
    next: implementation

  - name: implementation
    next: validation

  - name: validation
    next: null         # Terminal phase
```

---

## Standard Phase Patterns

### 4-Phase Development
```
requirements → design → implementation → validation
    PRD         TDD         Code         Test Plan
```

### 4-Phase Documentation
```
audit → architecture → writing → review
Report   Structure    Content   Signoff
```

### 4-Phase Quality
```
assessment → planning → execution → audit
  Report      Plan      Commits    Signoff
```

### 3-Phase Planning
```
collection → assessment → planning
  Inventory    Analysis    Plan
```

---

## Phase Naming Conventions

### Standard Names
Use consistent phase names across teams:

| Phase Type | Standard Names |
|------------|---------------|
| Entry | requirements, assessment, audit, collection, observation |
| Design | design, architecture, planning, coordination |
| Execute | implementation, writing, execution |
| Validate | validation, review, audit, resilience |

### Naming Rules
- Lowercase
- Single word preferred
- Verb or noun describing the activity
- Unique within workflow

---

## Artifact Flow

### Input/Output Pattern
Each phase's output becomes next phase's input.

```
requirements → prd → design → tdd → implementation → code → validation → test-plan
```

### Artifact Dependencies
Document in agent prompts:

```markdown
## Position in Workflow

**Upstream**: Requirements Analyst (PRD)
**Downstream**: Principal Engineer (uses TDD)
```

---

## Terminal Phases

### Characteristics
- Has `next: null`
- Produces final artifact (signoff, report, plan)
- Typically validation or review phase
- Triggers workflow completion

### Examples
```yaml
# Development
- name: validation
  agent: qa-adversary
  produces: test-plan
  next: null

# Documentation
- name: review
  agent: doc-reviewer
  produces: review-signoff
  next: null

# Planning-only (debt-triage)
- name: planning
  agent: sprint-planner
  produces: sprint-plan
  next: null
```

---

## Conditional Phases

### Complexity Gating
Skip phases based on work complexity.

```yaml
- name: design
  agent: architect
  produces: tdd
  next: implementation
  condition: "complexity >= MODULE"  # Skipped for SCRIPT
```

### Common Patterns

| Phase | Skip When |
|-------|-----------|
| Design | Simple work (SCRIPT, PAGE, SPOT, ALERT) |
| Assessment | Known issues (not discovery) |
| Coordination | Single-phase work |

### Complexity Expressions
```
condition: "complexity >= MODULE"   # At or above MODULE
condition: "complexity >= SERVICE"  # Only SERVICE and PLATFORM
condition: "complexity == PLATFORM" # Only PLATFORM
```

---

## Anti-Patterns

### Parallel Phases
```yaml
# Bad - not supported
phases:
  - name: design
    parallel_with: requirements  # Not supported
```

### Phase Loops
```yaml
# Bad - creates infinite loop
- name: validation
  next: requirements  # Loop back not supported
```

### Skip-Ahead
```yaml
# Bad - skipping phases
- name: requirements
  next: validation  # Skipping design and implementation
```

### Orphan Phases
```yaml
# Bad - unreachable phase
- name: extra-review
  agent: reviewer
  # Not referenced by any phase's `next`
```

---

## Workflow Validation

### Check Sequence
1. First phase has no `next` pointing to it? (entry point)
2. Each phase's `next` references an existing phase?
3. Exactly one phase has `next: null`? (terminal)
4. All phases reachable from entry point?

### Verification Script
```bash
# Entry point agent matches first phase
grep "entry_point:" workflow.yaml
grep "^  - name:" workflow.yaml | head -1

# Terminal phase has next: null
grep -A1 "next: null" workflow.yaml

# Phase count matches
grep -c "^  - name:" workflow.yaml
```
