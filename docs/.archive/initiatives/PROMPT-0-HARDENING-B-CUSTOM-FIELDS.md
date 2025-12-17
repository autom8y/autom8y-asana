# Orchestrator Initialization: Architecture Hardening - Initiative B (Custom Field Unification)

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
- **`standards`** - Tech stack decisions, code conventions, repository structure
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`autom8-asana-domain`** - SDK patterns, SaveSession, custom field handling
- **`autom8-asana-business-fields`** - Field accessor patterns, cascading fields

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

## The Mission: Unify the Dual Custom Field Change Tracking Systems

This initiative addresses the **highest-value correctness issue**: two parallel systems tracking custom field changes, causing confusion, bugs, and inconsistent behavior. Unification is critical for reliable SaveSession operation.

### Why This Initiative?

- **Correctness**: Two systems can disagree, leading to dropped changes or double-applies
- **Maintainability**: Developers must understand and maintain two systems
- **DX confusion**: `get_custom_fields()` naming implies fetch, not local access
- **SaveSession reliability**: Transaction semantics depend on accurate change tracking
- **Prerequisite for F**: SaveSession reliability initiative needs unified tracking

### Issues Addressed

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 2 | Dual custom field change tracking | Two parallel systems tracking same changes | High |
| 10 | `get_custom_fields()` naming | Method name implies API fetch, actually returns local data | Low |

### Current State

**Dual Tracking Systems**:
1. **Snapshot-based**: `_original_data` snapshot compared at commit time
2. **Explicit dirty flags**: `_dirty_fields` set tracking modified fields

**Problems with current state**:
- Both systems must be kept in sync
- Edge cases where they disagree
- Unclear which system is authoritative
- Code duplication in detection logic
- Confusion about when to use which approach

**Naming Issues**:
- `get_custom_fields()` sounds like an API call
- `Fields` vs `CascadingFields` distinction unclear
- Inconsistent access patterns across entity types

### Target State

```
Single authoritative change tracking system:
  - One mechanism for detecting custom field changes
  - Clear API for marking fields dirty
  - Consistent behavior across all entity types
  - Naming that reflects actual behavior

Naming clarity:
  - Methods named for what they do (access vs fetch)
  - Clear distinction between local data and API calls
  - Consistent patterns across entity types
```

### Key Constraints

- **Backward compatibility**: Existing code using current APIs must continue to work
- **SaveSession integration**: Changes must integrate with existing SaveSession
- **Performance**: No regression in change detection performance
- **Migration path**: Clear deprecation for removed APIs
- **Test coverage**: Comprehensive tests for change tracking edge cases

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Unify to single change tracking mechanism | Must |
| Choose authoritative system (snapshot or dirty flags) | Must |
| Eliminate redundant tracking code | Must |
| Rename `get_custom_fields()` to reflect actual behavior | Must |
| Deprecate old access patterns with warnings | Must |
| Document change tracking behavior clearly | Must |
| Maintain backward compatibility during transition | Must |
| Comprehensive test coverage for edge cases | Should |
| Migration guide for consumers | Should |

### Success Criteria

1. Single authoritative system for custom field change tracking
2. All change detection flows through unified mechanism
3. `get_custom_fields()` renamed to `custom_fields` property (or similar)
4. Old method names deprecated with warnings
5. Zero regressions in SaveSession custom field handling
6. Test coverage for: concurrent modifications, nested fields, null handling
7. Documentation updated with change tracking mental model
8. Migration guide for existing code

### Dependencies

**Depends On:**
- Initiative A (Foundation) - For structured logging during debugging
- Initiative A (Foundation) - For standardized exceptions

**Blocks:**
- Initiative F (SaveSession Reliability) - Needs unified tracking for transaction semantics

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Change tracking audit, naming inventory, edge case catalog |
| **2: Requirements** | Requirements Analyst | PRD-HARDENING-B with acceptance criteria |
| **3: Architecture** | Architect | TDD-HARDENING-B + ADR for tracking strategy choice |
| **4: Implementation P1** | Principal Engineer | Unified tracking mechanism, tests |
| **5: Implementation P2** | Principal Engineer | Naming fixes, deprecations, migration support |
| **6: Validation** | QA/Adversary | Edge case testing, SaveSession integration verification |

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

### Change Tracking System Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/models/task.py` | How is `_original_data` used? When populated? |
| `src/autom8_asana/models/custom_field_accessor.py` | How are dirty flags managed? |
| `src/autom8_asana/persistence/tracker.py` | How does tracking integrate with SaveSession? |
| `src/autom8_asana/persistence/session.py` | How are changes detected at commit? |

### Dual System Interaction Points

| Interaction | Questions to Answer |
|-------------|---------------------|
| Initial load | How are both systems initialized? |
| Field modification | How do both systems record changes? |
| Commit detection | Which system is checked? Both? One? |
| Reset after commit | How are both systems reset? |
| Conflict scenarios | What happens when systems disagree? |

### Naming Audit

| Method/Property | Questions to Answer |
|-----------------|---------------------|
| `get_custom_fields()` | What does it actually return? From where? |
| `Fields` vs `CascadingFields` | What's the distinction? When to use each? |
| `set_custom_field()` | Does it mark dirty? In which system? |
| Custom field properties | How are individual fields accessed? |

### Edge Cases to Document

| Edge Case | Questions to Answer |
|-----------|---------------------|
| Concurrent modifications | Multiple changes to same field |
| Nested field values | Enum options, multi-select values |
| Null/empty handling | Setting to null vs empty vs undefined |
| Type coercion | String "123" vs int 123 for number fields |
| Unchanged values | Setting field to its current value |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Tracking Strategy Questions

1. **Authoritative system**: Snapshot comparison vs dirty flags - which becomes primary?
2. **Snapshot timing**: When should snapshot be taken? On load? On track? On first modification?
3. **Dirty flag granularity**: Field-level? Value-level? Nested value-level?
4. **Detection method**: Deep comparison vs shallow? Performance implications?

### Naming Questions

5. **`get_custom_fields()` replacement**: Property? `local_custom_fields()`? `custom_field_values`?
6. **Deprecation strategy**: Warnings for how long? Hard removal when?
7. **`Fields` naming**: Keep or rename to clarify purpose?

### Integration Questions

8. **SaveSession impact**: How to minimize disruption to existing SaveSession?
9. **Backward compatibility layer**: Full shim or minimal support?
10. **Test migration**: How to update tests without breaking CI during transition?

---

## Your First Task

Confirm understanding by:

1. Summarizing the Custom Field Unification goal in 2-3 sentences
2. Listing the 6 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files must be analyzed before PRD-HARDENING-B
5. Listing which open questions you need answered before Session 2
6. Acknowledging this initiative depends on Initiative A and blocks Initiative F

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery

```markdown
Begin Session 1: Custom Field Change Tracking Discovery

Work with the @requirements-analyst agent to understand the dual tracking systems.

**Goals:**
1. Document how snapshot-based tracking works
2. Document how dirty flag tracking works
3. Map where both systems interact
4. Identify disagreement scenarios
5. Catalog naming inconsistencies
6. Document edge cases and current behavior

**Files to Analyze:**
- `src/autom8_asana/models/task.py` - Model with custom fields
- `src/autom8_asana/models/custom_field_accessor.py` - Field accessor
- `src/autom8_asana/persistence/tracker.py` - Entity tracker
- `src/autom8_asana/persistence/session.py` - SaveSession
- Relevant test files for existing behavior

**Deliverable:**
A discovery document with:
- Tracking system comparison diagram
- Interaction point map
- Edge case catalog with current behavior
- Naming inconsistency inventory
- Recommendation for authoritative system

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements

```markdown
Begin Session 2: Custom Field Unification Requirements

Work with the @requirements-analyst agent to create PRD-HARDENING-B.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define unified tracking mechanism requirements
2. Define naming convention requirements
3. Define backward compatibility requirements
4. Define test coverage requirements
5. Define migration path requirements
6. Define acceptance criteria for each

**Key Questions to Address:**
- Which tracking system becomes authoritative?
- What's the deprecation timeline?
- How to handle edge cases?
- What test coverage is required?

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture

```markdown
Begin Session 3: Custom Field Architecture Design

Work with the @architect agent to create TDD-HARDENING-B and required ADRs.

**Prerequisites:**
- PRD-HARDENING-B approved

**Goals:**
1. Design unified tracking mechanism
2. Design migration strategy
3. Design backward compatibility layer
4. Document change detection algorithm

**Required ADRs:**
- ADR: Unified Custom Field Change Tracking Strategy
- ADR: Custom Field Naming Convention

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Unified Tracking

Work with the @principal-engineer agent to implement unified tracking.

**Prerequisites:**
- PRD-HARDENING-B approved
- TDD-HARDENING-B approved
- ADRs documented

**Phase 1 Scope:**
1. Implement unified change tracking mechanism
2. Update CustomFieldAccessor to use unified system
3. Update SaveSession integration
4. Comprehensive unit tests for tracking
5. Edge case tests

**Explicitly OUT of Phase 1:**
- Naming changes (Phase 2)
- Deprecation warnings (Phase 2)
- Migration documentation (Phase 2)

Create the plan first. I'll review before you execute.
```

### Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Naming & Migration

Work with the @principal-engineer agent to complete naming and migration.

**Prerequisites:**
- Phase 1 complete and tested

**Phase 2 Scope:**
1. Rename `get_custom_fields()` to approved name
2. Add deprecation warnings for old names
3. Update all internal usage
4. Create backward compatibility shims
5. Update documentation
6. Create migration guide

Create the plan first. I'll review before you execute.
```

### Session 6: Validation

```markdown
Begin Session 6: Custom Field Unification Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation complete

**Goals:**

**Part 1: Tracking Validation**
- Verify single authoritative system
- Verify all edge cases handled correctly
- Verify SaveSession integration unchanged

**Part 2: Naming Validation**
- Verify new names work correctly
- Verify deprecation warnings fire
- Verify backward compatibility

**Part 3: Integration Testing**
- Test with real Asana API
- Test SaveSession end-to-end
- Test concurrent modifications

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Codebase:**
- [ ] `src/autom8_asana/models/task.py` - Task model with custom fields
- [ ] `src/autom8_asana/models/custom_field_accessor.py` - Field accessor
- [ ] `src/autom8_asana/persistence/tracker.py` - Entity tracking
- [ ] `src/autom8_asana/persistence/session.py` - SaveSession
- [ ] Related test files

**Documentation:**
- [ ] ADR-0036 (Change Tracking via Snapshot Comparison)
- [ ] ADR-0064 (Dirty Detection Strategy)
- [ ] TDD-0010 (Save Orchestration)
- [ ] Custom field skill documentation

**Related PRDs:**
- [ ] PRD-0005 (Save Orchestration)
- [ ] PRD-SDKUX (SDK Usability)

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Meta Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md` | Parent initiative |
| ADR-0036 | `/docs/decisions/ADR-0036-change-tracking-strategy.md` | Current tracking decision |
| ADR-0064 | `/docs/decisions/ADR-0064-dirty-detection-strategy.md` | Dirty flag decision |
| Custom Field Skill | `.claude/skills/autom8-asana-business-fields/` | Field patterns |
| Initiative A | `/docs/initiatives/PROMPT-0-HARDENING-A-FOUNDATION.md` | Dependency |

---

*This is Initiative B of the Architecture Hardening Sprint. It depends on Initiative A and blocks Initiative F. Can run in parallel with Initiative E.*
