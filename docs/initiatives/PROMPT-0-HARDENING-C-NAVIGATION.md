# Orchestrator Initialization: Architecture Hardening - Initiative C (Navigation Patterns)

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
- **`standards`** - Tech stack decisions, code conventions, repository structure
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources
- **`autom8-asana-business-relationships`** - Holder patterns, lazy loading, bidirectional navigation

**How Skills Work**: Skills load automatically based on your current task.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Unify Navigation and Relationship Patterns Across Entity Types

This initiative addresses **three related maintainability issues**: copy-paste navigation logic, inconsistent holder initialization, and manual reference invalidation. These form a cohesive system that should be unified.

### Why This Initiative?

- **DRY principle**: Navigation logic duplicated across entity types
- **Bug propagation**: Fix in one entity doesn't propagate to others
- **Stale data risk**: Manual `_invalidate_refs()` is error-prone
- **Maintainability**: New entity types require copy-paste pattern replication
- **Foundation for D**: Resolution framework extraction needs stable patterns

### Issues Addressed

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 4 | Manual reference invalidation | `_invalidate_refs()` must be called explicitly, easy to forget | Medium |
| 6 | Copy-paste navigation logic | Each entity duplicates property patterns | Medium |
| 7 | Inconsistent holder initialization | `HOLDER_KEY_MAP` + `__getattr__` magic | Medium |

### Current State

**Navigation Logic Duplication**:
- Each entity type (Task, Project, Portfolio, etc.) has similar navigation properties
- Properties like `parent`, `subtasks`, `projects`, `custom_fields` are copy-pasted
- Different entities have slightly different implementations for similar concepts
- No shared abstraction for relationship traversal

**Holder Initialization Inconsistency**:
- `HOLDER_KEY_MAP` maps holder names to classes
- `__getattr__` magic provides lazy access
- Some entities use explicit initialization, others use magic
- Unclear when holder is populated vs needs fetching

**Manual Reference Invalidation**:
- After mutating operations, references may become stale
- `_invalidate_refs()` must be called explicitly
- Easy to forget, leading to stale data bugs
- No automatic invalidation on mutation

### Target State

```
Unified Navigation:
  - Descriptor-based navigation properties
  - Shared implementation across entity types
  - Consistent lazy loading behavior
  - Type-safe relationship traversal

Unified Holders:
  - Single initialization pattern
  - Clear lazy vs eager distinction
  - Predictable behavior across entities

Auto-Invalidation:
  - References invalidated automatically on mutation
  - Clear invalidation scope rules
  - Observable invalidation events (optional)
```

### Key Constraints

- **Backward compatibility**: Existing navigation code must continue to work
- **Performance**: No regression in lazy loading performance
- **Type safety**: Descriptors must work with type checkers
- **Testability**: Navigation patterns must be independently testable
- **Extensibility**: New entity types should inherit navigation automatically

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Create navigation descriptor base class | Must |
| Migrate navigation properties to descriptors | Must |
| Unify holder initialization pattern | Must |
| Implement automatic reference invalidation | Must |
| Document navigation patterns | Must |
| Maintain backward compatibility | Must |
| Type-safe descriptors (mypy-compatible) | Should |
| Observable invalidation events | Could |

### Success Criteria

1. Navigation properties use shared descriptor implementation
2. Zero copy-paste navigation code between entity types
3. Single holder initialization pattern across all entities
4. References auto-invalidate on mutation (configurable)
5. New entity types inherit navigation via descriptors
6. Full backward compatibility for existing navigation code
7. Type checker compatibility maintained
8. Documentation for navigation pattern usage

### Dependencies

**Depends On:**
- Initiative A (Foundation) - For logging/exception patterns

**Blocks:**
- Initiative D (Resolution Framework) - Needs stable navigation patterns

**Can Run Parallel With:**
- Initiative B (Custom Fields) - Different code areas
- Initiative E (Hydration) - Different code areas

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Navigation pattern audit, holder analysis, invalidation mapping |
| **2: Requirements** | Requirements Analyst | PRD-HARDENING-C with acceptance criteria |
| **3: Architecture** | Architect | TDD-HARDENING-C + ADRs for descriptor pattern, auto-invalidation |
| **4: Implementation P1** | Principal Engineer | Navigation descriptors, holder unification |
| **5: Implementation P2** | Principal Engineer | Auto-invalidation, entity migration |
| **6: Validation** | QA/Adversary | Navigation testing, backward compatibility verification |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### Navigation Pattern Analysis

| Entity Type | Questions to Answer |
|-------------|---------------------|
| Task | What navigation properties exist? How implemented? |
| Project | What navigation properties exist? How implemented? |
| Portfolio | What navigation properties exist? How implemented? |
| Section | What navigation properties exist? How implemented? |
| Other entities | What patterns are consistent/inconsistent? |

### Copy-Paste Detection

| Pattern | Questions to Answer |
|---------|---------------------|
| `parent` property | How many implementations? Differences? |
| `subtasks` property | How many implementations? Differences? |
| `projects` property | How many implementations? Differences? |
| Lazy loading logic | Duplicated in how many places? |

### Holder Analysis

| Area | Questions to Answer |
|------|---------------------|
| `HOLDER_KEY_MAP` | What keys exist? What classes? |
| `__getattr__` magic | How does lazy access work? |
| Initialization patterns | When are holders created? |
| Population timing | When are holders populated? |

### Invalidation Analysis

| Area | Questions to Answer |
|------|---------------------|
| `_invalidate_refs()` | What does it invalidate? |
| Mutation operations | Which operations should trigger invalidation? |
| Invalidation scope | What should be invalidated on mutation? |
| Current bugs | Known stale data issues? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Descriptor Design Questions

1. **Descriptor base class**: Single base or hierarchy (ReadOnly, ReadWrite, LazyLoad)?
2. **Type safety approach**: Generic descriptors? Protocol-based? Type vars?
3. **Caching strategy**: Per-instance cache? Shared cache? No cache?
4. **Error handling**: What happens on missing relationship?

### Holder Questions

5. **Initialization timing**: Eager on entity creation vs lazy on first access?
6. **Holder vs property**: When to use Holder class vs descriptor property?
7. **Nested holders**: How to handle holder-of-holders patterns?

### Invalidation Questions

8. **Invalidation trigger**: On property set? On explicit mutation? Both?
9. **Invalidation scope**: Just direct references? Transitive? Configurable?
10. **Invalidation notification**: Events? Callbacks? Silent?

---

## Your First Task

Confirm understanding by:

1. Summarizing the Navigation Patterns goal in 2-3 sentences
2. Listing the 6 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which entity types must be analyzed before PRD-HARDENING-C
5. Listing which open questions you need answered before Session 2
6. Acknowledging this initiative depends on A and blocks D

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery

```markdown
Begin Session 1: Navigation Pattern Discovery

Work with the @requirements-analyst agent to audit navigation patterns across entities.

**Goals:**
1. Document navigation properties per entity type
2. Identify copy-paste patterns
3. Analyze holder initialization patterns
4. Map invalidation logic and gaps
5. Document current behavior and bugs

**Entities to Analyze:**
- Task (primary, most complete)
- Project
- Portfolio
- Section
- User
- Team
- Workspace

**Files to Analyze:**
- `src/autom8_asana/models/*.py` - Entity definitions
- `src/autom8_asana/models/business/*.py` - Business layer entities
- Holder implementations
- Relationship skill documentation

**Deliverable:**
A discovery document with:
- Navigation property inventory per entity
- Copy-paste pattern detection
- Holder initialization comparison
- Invalidation gap analysis
- Recommended descriptor design

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements

```markdown
Begin Session 2: Navigation Requirements Definition

Work with the @requirements-analyst agent to create PRD-HARDENING-C.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define navigation descriptor requirements
2. Define holder unification requirements
3. Define auto-invalidation requirements
4. Define backward compatibility requirements
5. Define acceptance criteria for each

**Key Questions to Address:**
- What descriptor patterns should be used?
- How should holders be unified?
- When should invalidation trigger?
- What backward compatibility is required?

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture

```markdown
Begin Session 3: Navigation Architecture Design

Work with the @architect agent to create TDD-HARDENING-C and required ADRs.

**Prerequisites:**
- PRD-HARDENING-C approved

**Goals:**
1. Design descriptor base classes
2. Design holder unification strategy
3. Design auto-invalidation mechanism
4. Document entity migration approach

**Required ADRs:**
- ADR: Navigation Descriptor Pattern
- ADR: Auto-Invalidation Strategy

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Descriptors & Holders

Work with the @principal-engineer agent to implement core patterns.

**Prerequisites:**
- PRD-HARDENING-C approved
- TDD-HARDENING-C approved
- ADRs documented

**Phase 1 Scope:**
1. Implement navigation descriptor base class(es)
2. Implement type-safe descriptor variants
3. Unify holder initialization pattern
4. Unit tests for descriptors

**Explicitly OUT of Phase 1:**
- Entity migration (Phase 2)
- Auto-invalidation (Phase 2)
- Integration tests (Phase 2)

Create the plan first. I'll review before you execute.
```

### Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Migration & Invalidation

Work with the @principal-engineer agent to complete migration.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Migrate Task entity to descriptors
2. Migrate other entities to descriptors
3. Implement auto-invalidation mechanism
4. Remove duplicate navigation code
5. Integration tests

Create the plan first. I'll review before you execute.
```

### Session 6: Validation

```markdown
Begin Session 6: Navigation Patterns Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation complete

**Goals:**

**Part 1: Descriptor Validation**
- Verify all entities use shared descriptors
- Verify no copy-paste navigation code remains
- Verify type checker compatibility

**Part 2: Holder Validation**
- Verify unified initialization pattern
- Verify lazy loading works correctly
- Verify no runtime errors

**Part 3: Invalidation Validation**
- Verify auto-invalidation triggers
- Verify correct invalidation scope
- Verify no stale data after mutations

**Part 4: Backward Compatibility**
- Verify existing navigation code works
- Verify no import breakages
- Verify performance unchanged

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Codebase:**
- [ ] `src/autom8_asana/models/task.py` - Primary entity
- [ ] `src/autom8_asana/models/project.py` - Project entity
- [ ] `src/autom8_asana/models/*.py` - All entity models
- [ ] Holder implementations
- [ ] Current descriptor patterns (if any)

**Documentation:**
- [ ] Relationship skill documentation
- [ ] Holder pattern documentation
- [ ] Lazy loading documentation

**Tests:**
- [ ] Navigation test patterns
- [ ] Holder test patterns

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Meta Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md` | Parent initiative |
| Relationship Skill | `.claude/skills/autom8-asana-business-relationships/` | Current patterns |
| Holder Pattern | `.claude/skills/autom8-asana-business-relationships/holder-pattern.md` | Holder docs |
| Initiative A | `/docs/initiatives/PROMPT-0-HARDENING-A-FOUNDATION.md` | Dependency |
| Initiative D | `/docs/initiatives/PROMPT-0-HARDENING-D-RESOLUTION.md` | Depends on this |

---

*This is Initiative C of the Architecture Hardening Sprint. It depends on Initiative A and blocks Initiative D. Can run in parallel with Initiatives B and E.*
