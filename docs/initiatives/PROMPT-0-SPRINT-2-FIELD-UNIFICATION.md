# Orchestrator Initialization: Sprint 2 - CustomFieldAccessor/Descriptor Unification

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, SaveSession, Business entities, CustomFieldAccessor, CascadingDescriptor
  - Activates when: Working with field access patterns, accessor/descriptor unification

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

**How Skills Work**: Skills load automatically based on your current task. When you need accessor/descriptor patterns, the `autom8-asana` skill activates.

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

## The Mission: Resolve the Accessor/Descriptor Architectural Duality

Sprint 2 addresses the KEYSTONE DECISION of the architectural remediation: resolving the duality between `CustomFieldAccessor` and `CascadingDescriptor`. Currently, field access is scattered across 4+ modules with two competing patterns. This sprint will unify these patterns, centralize field name resolution, and establish a single source of truth for custom field access.

**This is HIGH RISK** because it touches the foundational field access pattern used by ALL business entities.

### Why This Sprint?

- **Architectural Duality**: Two patterns (`CustomFieldAccessor` and `CascadingDescriptor`) do similar things differently
- **Scattered Resolution**: Field name resolution logic exists in 4+ modules
- **Consumer Confusion**: Unclear which pattern to use when adding new fields
- **Maintenance Burden**: Changes require understanding both systems

### Current State

**CustomFieldAccessor Pattern**:
```python
# In custom_field_accessor.py
class CustomFieldAccessor:
    def get(self, field_name: str) -> Any:
        # Looks up field by name in task.custom_fields
        ...

# Usage in entities
@property
def vertical(self) -> str | None:
    return self._get_custom_field("Vertical")
```

**CascadingDescriptor Pattern**:
```python
# In base.py
class CascadingDescriptor:
    def __get__(self, obj, objtype=None) -> Any:
        # First checks local, then cascades to parent
        ...

# Usage in entities
class Contact(BusinessEntity):
    vertical = CascadingDescriptor("Vertical", cascade_from="unit")
```

**The Problem**: Both patterns:
- Resolve field names to Asana custom field GIDs
- Handle fallback/cascade logic
- Deal with None values
- But do so independently, creating duplication and inconsistency

### Sprint Profile

| Attribute | Value |
|-----------|-------|
| Duration | 2 weeks |
| Phase | 3 (Accessor/Descriptor Unification) |
| Risk Level | HIGH |
| Blast Radius | ALL entity files + persistence |
| Prerequisites | Sprint 1 complete, Design Spike complete |
| KEYSTONE DECISION | Do descriptors replace accessor or wrap it? |

### The Keystone Decision

**Option A: Descriptors Wrap Accessor**
- Accessor remains the low-level field access mechanism
- Descriptors use accessor internally, add cascade logic
- Accessor is "private", descriptors are "public API"
- Pros: Lower risk, accessor is proven, clear layering
- Cons: Two codepaths still exist, just layered

**Option B: Descriptors Replace Accessor**
- Accessor is deprecated and removed
- All field access goes through descriptors
- Descriptors handle both direct access and cascade
- Pros: Single pattern, cleaner mental model
- Cons: Higher risk, accessor has consumers

**Option C: Hybrid (Recommended)**
- Accessor handles raw field access (get/set custom fields)
- Descriptors handle entity-level access with cascade
- Clear separation: accessor = infrastructure, descriptor = domain
- Both are public but with different use cases

### Target Architecture

```
                       Entity Code
                           |
                           v
                  +-------------------+
                  | CascadingDescriptor|  <- Public API for entity fields
                  +-------------------+
                           |
              +------------+------------+
              |                         |
              v                         v
    +-------------------+      +-------------------+
    | Local Field       |      | Cascade to Parent |
    | (via Accessor)    |      | (recursive call)  |
    +-------------------+      +-------------------+
              |
              v
    +-------------------+
    | CustomFieldAccessor|  <- Infrastructure for raw field access
    +-------------------+
              |
              v
    +-------------------+
    | Field Name        |  <- CENTRALIZED (currently scattered)
    | Resolution        |
    +-------------------+
              |
              v
    +-------------------+
    | task.custom_fields|  <- Asana data
    +-------------------+
```

### Key Constraints

- **No Breaking Changes**: All existing field access must continue to work
- **Deprecation Path**: If accessor becomes private, deprecate with warning first
- **Centralized Resolution**: Field name -> GID mapping in ONE location
- **Clear Documentation**: When to use which pattern must be obvious
- **Test Coverage**: All field access patterns must have tests

### Requirements Summary (Pending Design Spike)

| Requirement | Priority |
|-------------|----------|
| Complete design spike: wrap vs replace vs hybrid | Must |
| Document decision in ADR-0117 | Must |
| Centralize field name resolution | Must |
| Refactor descriptors to use accessor (if wrap) | Must |
| Refactor entities to use descriptors (if replace) | Must |
| Deprecate accessor (if replace) | Should |
| Add migration guide for consumers | Must |
| Update all entity field access | Must |
| Add comprehensive tests for unified pattern | Must |

### Success Criteria

1. Field name resolution in exactly 1 module
2. Clear pattern for new field additions (documented)
3. All existing tests pass
4. No consumer-facing API breaks
5. Deprecation warnings for any removed patterns
6. ADR documents the decision and rationale

### Performance Targets

| Metric | Before | After |
|--------|--------|-------|
| Field access latency | Baseline | No regression |
| Modules with field resolution | 4+ | 1 |
| Patterns for field access | 2 | 1 (or 2 with clear layering) |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **0: Design Spike** | Architect | ADR-0117 with wrap/replace/hybrid decision |
| **1: Discovery** | Requirements Analyst | Current usage patterns, consumer inventory, edge cases |
| **2: Requirements** | Requirements Analyst | PRD-SPRINT-2-FIELD-UNIFICATION with acceptance criteria |
| **3: Architecture** | Architect | TDD-SPRINT-2 with detailed design |
| **4: Implementation P1** | Principal Engineer | Centralized field resolution module |
| **5: Implementation P2** | Principal Engineer | Descriptor/Accessor unification |
| **6: Implementation P3** | Principal Engineer | Entity updates, deprecation warnings |
| **7: Validation** | QA/Adversary | Pattern verification, regression testing |

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

### Codebase Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `custom_field_accessor.py` | Full API surface, all callers, edge case handling |
| `base.py` (CascadingDescriptor) | Full API surface, cascade logic, fallback behavior |
| Entity files (Contact, Unit, etc.) | Which pattern used where? Any mixed usage? |
| Persistence layer | Does SaveSession interact with field access? |
| Field name mappings | Where are field names defined? Multiple locations? |

### Usage Pattern Analysis

| Pattern | Questions to Answer |
|---------|---------------------|
| Direct accessor usage | Which entities call accessor directly? |
| Descriptor usage | Which fields use descriptors? |
| Mixed usage | Any entities using both patterns for different fields? |
| Consumer patterns | Do external consumers access fields directly? |

### Edge Case Analysis

| Area | Questions |
|------|-----------|
| Null handling | How does each pattern handle None values? |
| Missing fields | Behavior when field doesn't exist? |
| Cascade failures | What if cascade target doesn't have field? |
| Write operations | How does each pattern handle field writes? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Design Questions (from Design Spike)

1. **Wrap vs Replace vs Hybrid**: Which approach minimizes risk while achieving unification?
2. **Accessor scope**: Should accessor be public or private after unification?
3. **Write path**: How do field writes work in unified model?

### Technical Questions

4. **Cascade depth**: Is there a max cascade depth? Should there be?
5. **Circular cascades**: How are circular cascade chains prevented?
6. **Performance**: Does unification add overhead to field access?

### Migration Questions

7. **Consumer impact**: Do any external consumers use accessor directly?
8. **Deprecation timeline**: How long before removing deprecated patterns?
9. **Migration tooling**: Should we provide automated migration?

---

## Scope Boundaries

### Explicitly In Scope

- Design spike for wrap/replace/hybrid decision
- ADR documenting the decision
- Centralized field name resolution
- Descriptor/Accessor unification
- Entity field access updates
- Deprecation path for removed patterns
- Comprehensive tests
- Migration documentation

### Explicitly Out of Scope

- Detection module changes (Sprint 3)
- SaveSession changes (Sprint 4)
- New field additions
- Performance optimization beyond preventing regression
- External consumer migration assistance

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking field access for entities | Medium | High | Comprehensive tests before/after |
| Consumer code breaks | Medium | High | Deprecation period with warnings |
| Performance regression | Low | Medium | Benchmark before/after |
| Scope creep into persistence | Medium | Medium | Strict scope boundaries |
| Design spike doesn't converge | Low | High | Timebox spike; escalate if blocked |

---

## Dependencies

### Prerequisites

| Dependency | Status | Notes |
|------------|--------|-------|
| Sprint 1 complete | Required | Mixins may affect field access |
| Design spike complete | Required | Can't proceed without keystone decision |
| Test suite passing | Required | Baseline for regression testing |

### Blocks Future Work

| Dependent | Notes |
|-----------|-------|
| Sprint 3 (Detection) | May need to update detection field access |
| Sprint 4 (SaveSession) | May need to update persistence field handling |

---

## Design Spike: Accessor/Descriptor Unification

**Goal**: Make keystone decision before Sprint 2 execution.

**Duration**: 2-4 hours (run during Sprint 1 or between sprints)

**Tasks**:
1. Document all CustomFieldAccessor methods and callers
2. Document all CascadingDescriptor methods and callers
3. Identify overlap and divergence
4. Prototype "wrap" approach with 1 entity
5. Prototype "replace" approach with 1 entity
6. Prototype "hybrid" approach with 1 entity
7. Compare: lines of code, test coverage, migration effort
8. Write ADR-0117 with recommendation

**Output**: ADR-0117-ACCESSOR-DESCRIPTOR-UNIFICATION

**Decision Criteria**:
- Lowest risk option wins if tied
- Clear mental model for developers
- Minimal migration burden for consumers
- No performance regression

---

## Your First Task

Confirm understanding by:

1. Summarizing the Sprint 2 goal (Resolve accessor/descriptor duality, centralize field resolution)
2. Noting this is HIGH RISK and requires design spike first
3. Listing the 8 sessions (including Session 0: Design Spike)
4. Identifying the KEYSTONE DECISION: wrap vs replace vs hybrid
5. Confirming you will wait for design spike completion before Session 1
6. Noting the key constraint: no breaking changes, deprecation path required

**Do NOT begin any session yet. Design spike must complete first.**

---

# Session Trigger Prompts

## Session 0: Design Spike

```markdown
Begin Session 0: Accessor/Descriptor Design Spike

Work with the @architect agent to make the keystone decision.

**Goals:**
1. Document CustomFieldAccessor full API and usage
2. Document CascadingDescriptor full API and usage
3. Identify all field name resolution locations
4. Prototype wrap approach
5. Prototype replace approach
6. Prototype hybrid approach
7. Compare approaches on risk, complexity, migration
8. Write ADR-0117 with recommendation

**Files to Analyze:**
- `src/autom8_asana/models/custom_field_accessor.py`
- `src/autom8_asana/models/business/base.py`
- All entity files for usage patterns
- Tests for both patterns

**Deliverable:**
ADR-0117-ACCESSOR-DESCRIPTOR-UNIFICATION with:
- Context (current duality problem)
- Decision (wrap/replace/hybrid)
- Consequences (what changes, what stays)
- Migration plan

Create the analysis plan first. I'll review before you execute.
```

## Session 1: Discovery

```markdown
Begin Session 1: Field Access Discovery

Work with the @requirements-analyst agent to map current field access patterns.

**Prerequisites:**
- ADR-0117 complete with decision

**Goals:**
1. Inventory all field access patterns per entity
2. Map field name resolution locations (target: identify all 4+)
3. Document consumer usage patterns
4. Identify edge cases in current implementations
5. Document cascade chain configurations
6. Map test coverage for field access

**Files to Analyze:**
- All entity files in `src/autom8_asana/models/business/`
- `custom_field_accessor.py`
- `base.py`
- Persistence layer field access

**Deliverable:**
A discovery document with:
- Field access inventory per entity
- Field resolution location map
- Edge case registry
- Test coverage analysis
- Migration complexity estimate

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Field Unification Requirements

Work with the @requirements-analyst agent to create PRD-SPRINT-2-FIELD-UNIFICATION.

**Prerequisites:**
- Session 1 discovery complete
- ADR-0117 decision made

**Goals:**
1. Define unified field access requirements
2. Define centralized resolution requirements
3. Define deprecation requirements (if applicable)
4. Define migration requirements
5. Define backward compatibility requirements
6. Define acceptance criteria for unification

**Key Questions:**
- What's the new canonical pattern for field access?
- How do consumers migrate?
- What's the deprecation timeline?
- How do we verify no regression?

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Field Unification Architecture

Work with the @architect agent to create TDD-SPRINT-2-FIELD-UNIFICATION.

**Prerequisites:**
- PRD-SPRINT-2-FIELD-UNIFICATION approved
- ADR-0117 approved

**Goals:**
1. Design centralized field resolution module
2. Design unified field access pattern
3. Design deprecation mechanism
4. Design migration path
5. Document integration with existing patterns

**Required ADRs:**
- ADR-0117 (from spike - may need updates)
- ADR-0118: Field Resolution Centralization (if needed)

Create the plan first. I'll review before you execute.
```

## Session 4-6: Implementation

```markdown
Begin Session 4/5/6: Field Unification Implementation

Work with the @principal-engineer agent to implement unification.

**Session 4: Centralized Resolution**
- Create field_resolution.py (or similar)
- Move all field name mappings to single location
- Update accessor and descriptor to use centralized resolution

**Session 5: Pattern Unification**
- Implement chosen pattern (wrap/replace/hybrid)
- Update descriptors or accessor per ADR-0117
- Maintain backward compatibility

**Session 6: Entity Updates + Deprecation**
- Update all entities to use unified pattern
- Add deprecation warnings where needed
- Update tests

Create the plan first for each session. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Field Unification Validation

Work with the @qa-adversary agent to validate the unification.

**Goals:**

**Part 1: Functional Validation**
- All field access works correctly
- Cascade chains work correctly
- Fallback behavior preserved

**Part 2: Centralization Validation**
- Field resolution in exactly 1 module
- No scattered field name mappings

**Part 3: Backward Compatibility**
- All existing tests pass
- Deprecated patterns still work
- Deprecation warnings issued

**Part 4: Edge Case Testing**
- Null handling
- Missing fields
- Deep cascade chains
- Circular cascade prevention

**Part 5: Performance Validation**
- No regression in field access latency
- Memory usage unchanged

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Accessor Context:**
- [ ] `custom_field_accessor.py` - Full implementation
- [ ] All callers of CustomFieldAccessor
- [ ] Field name mappings in accessor

**Descriptor Context:**
- [ ] `base.py` - CascadingDescriptor implementation
- [ ] All descriptor usage in entities
- [ ] Cascade chain configurations

**Field Resolution Context:**
- [ ] All locations with field name -> GID mappings
- [ ] Field name constants/enums
- [ ] Custom field configurations

**Consumer Context:**
- [ ] External consumers of field access (if any)
- [ ] Internal patterns for field access
- [ ] Test patterns for field access
