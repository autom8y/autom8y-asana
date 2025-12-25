# Complexity Gating Patterns

How to design complexity levels that skip phases appropriately.

---

## Core Concept

Complexity levels determine which phases run for a given piece of work.

```
SCRIPT complexity → Skip design phase
MODULE complexity → Run all phases
```

Lower complexity = fewer phases
Higher complexity = more phases

---

## Complexity Level Design

### Standard Pattern
Define 2-4 levels from simple to complex.

```yaml
complexity_levels:
  - name: SIMPLE
    scope: "Description of scope"
    phases: [phase-3, phase-4]        # Skip early phases

  - name: STANDARD
    scope: "Description of scope"
    phases: [phase-1, phase-2, phase-3, phase-4]

  - name: COMPLEX
    scope: "Description of scope"
    phases: [phase-1, phase-2, phase-3, phase-4]
```

### Level Naming by Domain

| Domain | Levels | Semantic Meaning |
|--------|--------|------------------|
| **Development** | SCRIPT, MODULE, SERVICE, PLATFORM | Code scope |
| **Documentation** | PAGE, SECTION, SITE | Document scope |
| **Hygiene** | SPOT, MODULE, CODEBASE | Refactor scope |
| **Debt** | QUICK, AUDIT | Discovery scope |
| **SRE** | ALERT, SERVICE, SYSTEM, PLATFORM | Reliability scope |

---

## Domain Examples

### Development (10x-dev-pack)
```yaml
complexity_levels:
  - name: SCRIPT
    scope: "Single file, <200 LOC"
    phases: [requirements, implementation, validation]

  - name: MODULE
    scope: "Multiple files, <2000 LOC"
    phases: [requirements, design, implementation, validation]

  - name: SERVICE
    scope: "APIs, persistence"
    phases: [requirements, design, implementation, validation]

  - name: PLATFORM
    scope: "Multi-service"
    phases: [requirements, design, implementation, validation]
```

**Pattern**: SCRIPT skips design (too small to need TDD).

### Documentation (doc-team-pack)
```yaml
complexity_levels:
  - name: PAGE
    scope: "Single document"
    phases: [writing, review]

  - name: SECTION
    scope: "Multiple related documents"
    phases: [architecture, writing, review]

  - name: SITE
    scope: "Full documentation site"
    phases: [audit, architecture, writing, review]
```

**Pattern**: PAGE skips audit and architecture. SITE runs all.

### SRE (sre-pack)
```yaml
complexity_levels:
  - name: ALERT
    scope: "Single alert/dashboard fix"
    phases: [implementation, resilience]

  - name: SERVICE
    scope: "Single service reliability"
    phases: [observation, coordination, implementation, resilience]

  - name: SYSTEM
    scope: "Multi-service SLOs/SLIs"
    phases: [observation, coordination, implementation, resilience]

  - name: PLATFORM
    scope: "Full platform reliability"
    phases: [observation, coordination, implementation, resilience]
```

**Pattern**: ALERT skips observation and coordination (known issue).

---

## Conditional Phase Syntax

### In Phase Definition
```yaml
phases:
  - name: design
    agent: architect
    produces: tdd
    next: implementation
    condition: "complexity >= MODULE"
```

### Expression Format
```
condition: "complexity >= LEVEL"
condition: "complexity == LEVEL"
condition: "complexity > LEVEL"
```

### Level Ordering
Levels are ordered by their position in `complexity_levels`:
```yaml
complexity_levels:
  - name: SCRIPT    # Level 0 (lowest)
  - name: MODULE    # Level 1
  - name: SERVICE   # Level 2
  - name: PLATFORM  # Level 3 (highest)
```

`complexity >= MODULE` means MODULE, SERVICE, or PLATFORM.

---

## Design Guidelines

### What to Skip

| Phase Type | Skip When |
|------------|-----------|
| Design | Simple work that doesn't need architecture |
| Assessment | Known issues that don't need discovery |
| Coordination | Single-focus work without handoffs |

### What Never to Skip

| Phase Type | Why |
|------------|-----|
| Implementation | Work must be done |
| Validation | Quality must be verified |
| Entry (usually) | Need to understand scope |

### Recommended Patterns

**Skip 1 phase for simple:**
```
Simple: [execute, validate]
Standard: [entry, execute, validate]
```

**Skip 2 phases for simple:**
```
Simple: [execute, validate]
Standard: [entry, design, execute, validate]
```

---

## Scope Descriptions

### Good Descriptions
Concrete, measurable criteria:

```yaml
- name: SCRIPT
  scope: "Single file, <200 LOC"

- name: SERVICE
  scope: "APIs, persistence, external integrations"

- name: PLATFORM
  scope: "Multi-service, cross-team coordination"
```

### Bad Descriptions
Vague, subjective criteria:

```yaml
- name: SMALL
  scope: "Simple work"  # Too vague

- name: MEDIUM
  scope: "Medium complexity"  # Circular
```

---

## Complexity Selection

### By User
User specifies complexity in command:
```
/task "Add login button" --complexity=SCRIPT
/task "Build auth service" --complexity=SERVICE
```

### By Agent
Entry agent assesses complexity:
```markdown
## How You Work

### Phase 1: Assess Complexity
Evaluate the scope:
- Single file change? → SCRIPT
- Multiple files, no APIs? → MODULE
- New APIs or persistence? → SERVICE
- Cross-service impact? → PLATFORM
```

---

## Anti-Patterns

### Too Many Levels
```yaml
# Bad - 6 levels is too many
complexity_levels:
  - name: TRIVIAL
  - name: TINY
  - name: SMALL
  - name: MEDIUM
  - name: LARGE
  - name: HUGE
```

Stick to 2-4 meaningful levels.

### Inconsistent Phase Lists
```yaml
# Bad - random phase ordering
complexity_levels:
  - name: SIMPLE
    phases: [validation, implementation]  # Wrong order
  - name: COMPLEX
    phases: [requirements, implementation, design]  # Wrong order
```

Phase lists should follow workflow order.

### Missing Validation
```yaml
# Bad - no validation at any level
complexity_levels:
  - name: QUICK
    phases: [implementation]  # No validation!
```

Always include validation phase.
