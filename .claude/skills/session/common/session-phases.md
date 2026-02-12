# Session Phases

> Workflow phase transitions and agent responsibilities.

## Overview

Sessions progress through phases that correspond to the software development lifecycle. Each phase has a primary agent responsible for that work, and transitions are triggered by agent handoffs.

## Phase Diagram

```
┌──────────────┐
│ requirements │  Analyst gathers requirements → PRD
└──────┬───────┘
       │ (MODULE+)
       ▼
┌──────────────┐
│    design    │  Architect creates TDD + ADRs
└──────┬───────┘
       │
       ▼
┌──────────────┐
│implementation│  Engineer writes code
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  validation  │  QA validates against PRD
└──────┬───────┘
       │
       ▼
    (wrap)
```

## Phase Definitions

### requirements

**Purpose**: Understand and document what needs to be built

**Primary Agent**: `requirements-analyst`

**Artifacts Produced**:
- PRD (Product Requirements Document)

**Entry Conditions**:
- Session just created via /start
- Or returning from validation phase (iteration)

**Exit Conditions**:
- PRD approved
- User invokes /handoff to next phase

**Valid Transitions**:
- → `design` (for MODULE+ complexity)
- → `implementation` (for SCRIPT complexity, skip design)
- → `requirements` (iteration, refinement)

**Typical Duration**: 10-30 minutes

---

### design

**Purpose**: Create technical architecture and design decisions

**Primary Agent**: `architect`

**Artifacts Produced**:
- TDD (Technical Design Document)
- ADRs (Architecture Decision Records)

**Entry Conditions**:
- PRD exists and approved
- Complexity is MODULE, SERVICE, or PLATFORM

**Exit Conditions**:
- TDD approved
- Key decisions documented in ADRs
- User invokes /handoff engineer

**Valid Transitions**:
- → `implementation` (proceed to coding)
- → `requirements` (design reveals missing requirements)
- → `design` (refinement, iteration)

**Typical Duration**: 30-90 minutes

---

### implementation

**Purpose**: Write code implementing the design

**Primary Agent**: `principal-engineer`

**Artifacts Produced**:
- Code (committed to git)
- Tests
- Implementation notes

**Entry Conditions**:
- PRD exists (always)
- TDD exists (if complexity > SCRIPT)
- Design approved

**Exit Conditions**:
- Code committed
- Tests passing
- Implementation complete per TDD
- User invokes /handoff qa

**Valid Transitions**:
- → `validation` (code ready for QA)
- → `requirements` (implementation reveals missing requirements)
- → `design` (implementation reveals design gaps)
- → `implementation` (refinement, bug fixes)

**Typical Duration**: 2-8 hours (or park/resume cycles)

---

### validation

**Purpose**: Validate implementation against requirements

**Primary Agent**: `qa-adversary`

**Artifacts Produced**:
- Test Plan
- Defect reports
- QA validation summary

**Entry Conditions**:
- Implementation complete
- Tests passing
- Code committed

**Exit Conditions**:
- All acceptance criteria validated
- Defects resolved or documented
- Quality gates passing
- User invokes /wrap

**Valid Transitions**:
- → Complete (all criteria met, /wrap)
- → `implementation` (defects found, need fixes)
- → `requirements` (acceptance criteria unclear)
- → `validation` (re-test after fixes)

**Typical Duration**: 30-90 minutes

---

## Transition Rules

### Forward Transitions

Standard flow progression:

```
requirements → design → implementation → validation → wrap
```

For SCRIPT complexity:
```
requirements → implementation → validation → wrap
```

### Backward Transitions (Iteration)

Common iteration patterns:

```
validation → implementation  (defect fixes)
implementation → design      (design gaps found)
design → requirements        (missing requirements)
validation → requirements    (acceptance criteria issues)
```

### Lateral Transitions

Same-phase iteration:

```
requirements → requirements  (refinement)
design → design              (architecture evolution)
implementation → implementation  (bug fixes, refactoring)
```

## Complexity-Specific Rules

### SCRIPT

- **Skip design phase**: requirements → implementation directly
- **Minimal validation**: Often skip validation for trivial scripts
- **Fast track**: Can complete in single session

### MODULE

- **Require design**: Must go through design phase
- **Standard flow**: All phases typically needed
- **Multi-session**: May park/resume during implementation

### SERVICE

- **Extended design**: Design phase may span multiple sessions
- **Careful validation**: QA phase critical for API contracts
- **Multi-session**: Almost always requires park/resume

### PLATFORM

- **Multi-session by design**: Too large for single session
- **Phased approach**: Break into MODULE-sized sessions
- **Coordination**: May require multiple rite handoffs

## Phase Transitions via Commands

| Command | Phase Impact |
|---------|--------------|
| `/start` | Sets initial phase (`requirements`) |
| `/handoff <agent>` | May change phase based on target agent |
| `/park` | Preserves current phase in `parked_phase` |
| `/resume` | Restores to phase at park time |
| `/wrap` | Exits all phases (completion) |

## Agent-to-Phase Mapping

| Agent | Sets Phase To |
|-------|---------------|
| `requirements-analyst` | `requirements` |
| `architect` | `design` |
| `principal-engineer` | `implementation` |
| `qa-adversary` | `validation` |

## Invalid Transitions

These transitions are **not allowed**:

```
requirements → validation  (skip design + implementation)
design → validation        (skip implementation)
```

**Why?** Each phase has deliverables that subsequent phases depend on. Skipping phases creates incomplete sessions.

## Phase Enforcement

Phases are **advisory**, not enforced by state machine. However:

1. **Quality gates** check phase-appropriate artifacts
2. **Handoff notes** remind agents of expected phase
3. **Wrap validation** ensures phase-appropriate completion

## Example: Phase Progression

**SESSION_CONTEXT evolution across phases:**

```yaml
# After /start
current_phase: "requirements"
last_agent: "requirements-analyst"

# After /handoff architect
current_phase: "design"
last_agent: "architect"

# After /handoff engineer
current_phase: "implementation"
last_agent: "principal-engineer"

# After /handoff qa
current_phase: "validation"
last_agent: "qa-adversary"

# After /wrap
completed_at: "2026-01-01T18:45:22Z"
```

## Cross-References

- [Session Context Schema](session-context-schema.md) - Field definitions
- [Session State Machine](session-state-machine.md) - Lifecycle states
- [Handoff Notes](../handoff-ref/handoff-notes.md) - Transition-specific templates
