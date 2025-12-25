# Orchestrator Initialization: Sprint 3 - Detection Module Decomposition

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana`** - SDK patterns, detection system, entity type detection, tier hierarchy
  - Activates when: Working with detection patterns, entity type resolution

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing libraries, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

**How Skills Work**: Skills load automatically based on your current task. When you need detection patterns, the `autom8-asana` skill activates.

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

## The Mission: Decompose detection.py into Maintainable Tier-Based Modules

Sprint 3 addresses the detection.py god class (1016 lines) by decomposing it into focused, tier-based modules. The detection system uses a 5-tier hierarchy for entity type detection, and this structure naturally maps to separate modules. The facade pattern preserves the existing public API while enabling focused development on individual tiers.

**This is MEDIUM RISK** because the facade pattern preserves all existing behavior while only restructuring internals.

### Why This Sprint?

- **God Class**: detection.py at 1016 lines violates Single Responsibility Principle
- **Tier Coupling**: All 5 tiers are in one file, making tier-specific changes risky
- **Testing Complexity**: Hard to test individual tiers in isolation
- **Mental Model**: Developers must understand entire file to modify any tier

### Current State

**Detection Tier Hierarchy**:
```
Tier 1: Project Membership (100% accuracy, O(1), 0 API calls)
   |
Tier 2: Name Convention (~60% accuracy, O(1), 0 API calls)
   |
Tier 3: Parent Inference (~80% accuracy, O(1), 0 API calls)
   |
Tier 4: Structure Inspection (~90%, O(n), 1+ API calls)
   |
Tier 5: Unknown with self-healing flag
```

**Current Structure**:
```
src/autom8_asana/models/business/
    detection.py          # 1016 lines - EVERYTHING
```

**File Contents**:
- EntityType enum
- DetectionResult dataclass
- DetectionConfidence enum
- detect_entity_type() function (main entry point)
- Tier 1: _detect_by_project_membership()
- Tier 2: _detect_by_name_convention()
- Tier 3: _detect_by_parent_inference()
- Tier 4: _detect_by_structure_inspection()
- ProjectTypeRegistry class
- Helper functions
- Fallback logic

### Sprint Profile

| Attribute | Value |
|-----------|-------|
| Duration | 2 weeks |
| Phase | 4 (Detection Decomposition) |
| Risk Level | MEDIUM |
| Blast Radius | 1 file -> 6 files |
| Prerequisites | Sprint 2 complete (or can run in parallel) |
| Key Pattern | Facade for backward compatibility |

### Target Architecture

**After Decomposition**:
```
src/autom8_asana/models/business/detection/
    __init__.py           # Re-exports: detect_entity_type, EntityType, etc.
    types.py              # EntityType, DetectionResult, DetectionConfidence
    registry.py           # ProjectTypeRegistry
    tier1.py              # _detect_by_project_membership
    tier2.py              # _detect_by_name_convention
    tier3.py              # _detect_by_parent_inference
    tier4.py              # _detect_by_structure_inspection
    facade.py             # detect_entity_type() orchestrates tiers
```

**Line Distribution Target**:
| Module | Estimated Lines | Responsibility |
|--------|-----------------|----------------|
| types.py | ~100 | Enums, dataclasses |
| registry.py | ~150 | Project->EntityType mapping |
| tier1.py | ~100 | Project membership detection |
| tier2.py | ~120 | Name convention detection |
| tier3.py | ~150 | Parent inference detection |
| tier4.py | ~200 | Structure inspection detection |
| facade.py | ~150 | Orchestration, fallback logic |
| **Total** | ~970 | Same behavior, better structure |

### Key Constraints

- **Backward Compatibility**: `from detection import detect_entity_type` must still work
- **No Behavior Changes**: Every edge case must be preserved
- **Tier Isolation**: Each tier module is self-contained
- **Facade Pattern**: Public API through facade only
- **Test Preservation**: All existing tests must pass unchanged

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Create detection/ package structure | Must |
| Extract types (EntityType, DetectionResult, DetectionConfidence) | Must |
| Extract ProjectTypeRegistry to registry.py | Must |
| Extract Tier 1 detection to tier1.py | Must |
| Extract Tier 2 detection to tier2.py | Must |
| Extract Tier 3 detection to tier3.py | Must |
| Extract Tier 4 detection to tier4.py | Must |
| Create facade.py with detect_entity_type() | Must |
| Update __init__.py with re-exports | Must |
| Maintain backward compatibility imports | Must |
| Preserve all existing tests | Must |
| Add tier-specific unit tests | Should |
| Document module structure | Should |

### Success Criteria

1. detection.py deleted (replaced by detection/ package)
2. `from autom8_asana.models.business.detection import detect_entity_type` works
3. `from autom8_asana.models.business.detection import EntityType` works
4. All existing tests pass without modification
5. Each tier module is <250 lines
6. Each tier can be tested in isolation
7. No external API changes

### Performance Targets

| Metric | Before | After |
|--------|--------|-------|
| Tier 1 detection latency | Baseline | No regression |
| Import time | Baseline | <10% increase (from module loading) |
| Memory usage | Baseline | No regression |

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Current structure analysis, dependency map, test coverage |
| **2: Requirements** | Requirements Analyst | PRD-SPRINT-3-DETECTION-DECOMPOSITION with acceptance criteria |
| **3: Architecture** | Architect | TDD-SPRINT-3 with module boundaries and interface definitions |
| **4: Implementation P1** | Principal Engineer | Package structure, types.py, registry.py |
| **5: Implementation P2** | Principal Engineer | tier1.py, tier2.py, tier3.py |
| **6: Implementation P3** | Principal Engineer | tier4.py, facade.py, __init__.py, delete detection.py |
| **7: Validation** | QA/Adversary | Backward compatibility, tier isolation, regression testing |

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
| `detection.py` | Exact line boundaries for each tier function |
| `detection.py` | All helper functions and their callers |
| `detection.py` | Shared state or module-level variables |
| Entity files | How do entities import from detection? |
| Tests | What detection tests exist? Coverage? |

### Dependency Analysis

| Dependency | Questions |
|------------|-----------|
| Internal dependencies | What does each tier depend on? |
| Cross-tier dependencies | Do tiers call each other? |
| External dependencies | What external modules does detection use? |
| Circular risk | Any potential circular import issues? |

### Interface Analysis

| Interface | Questions |
|-----------|-----------|
| detect_entity_type() | Full signature, all parameters, return type |
| EntityType | All enum values, usage patterns |
| DetectionResult | All fields, construction patterns |
| ProjectTypeRegistry | Full API, configuration pattern |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins, the following questions need answers:

### Structure Questions

1. **Package vs module**: Should detection be a package or stay as single module with imports?
2. **Registry location**: Should ProjectTypeRegistry be in registry.py or types.py?
3. **Helper functions**: Which helpers are tier-specific vs shared?

### Interface Questions

4. **Tier interfaces**: Should each tier have a standard interface/protocol?
5. **Tier results**: Do all tiers return DetectionResult or different types?
6. **Tier chaining**: Is tier order configurable or hardcoded?

### Migration Questions

7. **Backward compat imports**: How long to maintain old import paths?
8. **Deprecation**: Should old imports issue deprecation warnings?

---

## Scope Boundaries

### Explicitly In Scope

- Create detection/ package
- Extract types to types.py
- Extract registry to registry.py
- Extract each tier to tier{N}.py
- Create facade.py
- Update __init__.py
- Maintain backward compatibility
- All existing tests pass
- Add tier-specific tests

### Explicitly Out of Scope

- New detection tiers
- Detection algorithm changes
- Performance optimization
- New detection features
- SaveSession changes (Sprint 4)
- API changes

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular import issues | Medium | Medium | Careful dependency ordering |
| Missing helper function | Low | Medium | Thorough discovery of all functions |
| Backward compat break | Low | High | Test all import paths |
| Test failures | Low | Medium | Run tests after each extraction |
| Cross-tier dependencies | Medium | Low | Document and handle explicitly |

---

## Dependencies

### Prerequisites

| Dependency | Status | Notes |
|------------|--------|-------|
| Sprint 2 complete | Optional | Can run in parallel |
| detection.py stable | Required | No pending changes |
| Test suite passing | Required | Baseline for regression |

### Blocks Future Work

| Dependent | Notes |
|-----------|-------|
| Sprint 5 (Cleanup) | May need to update detection references |

---

## File Inventory

### Files to Delete

| File | Notes |
|------|-------|
| `detection.py` | Replaced by detection/ package |

### Files to Create

| File | Purpose |
|------|---------|
| `detection/__init__.py` | Re-exports for backward compatibility |
| `detection/types.py` | EntityType, DetectionResult, DetectionConfidence |
| `detection/registry.py` | ProjectTypeRegistry |
| `detection/tier1.py` | Project membership detection |
| `detection/tier2.py` | Name convention detection |
| `detection/tier3.py` | Parent inference detection |
| `detection/tier4.py` | Structure inspection detection |
| `detection/facade.py` | detect_entity_type() main function |

### Files to Modify

| File | Changes |
|------|---------|
| Any file importing from detection | Update imports (should work via __init__.py) |

---

## Your First Task

Confirm understanding by:

1. Summarizing the Sprint 3 goal (Decompose detection god class into tier modules)
2. Listing the 7 sessions and their deliverables
3. Identifying facade pattern as key for backward compatibility
4. Confirming the target structure (detection/ package with tier modules)
5. Noting this can run in parallel with Sprint 2
6. Noting the key constraint: no behavior changes, all tests must pass

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

# Session Trigger Prompts

## Session 1: Discovery

```markdown
Begin Session 1: Detection Module Discovery

Work with the @requirements-analyst agent to analyze detection.py structure.

**Goals:**
1. Map exact line ranges for each function/class in detection.py
2. Document all imports and dependencies
3. Identify shared state (module-level variables)
4. Map cross-function dependencies
5. Document test coverage for detection
6. Identify helper functions and their scope (tier-specific vs shared)
7. Document all import patterns used by consumers

**Files to Analyze:**
- `src/autom8_asana/models/business/detection.py` - Primary target
- `tests/unit/models/business/test_detection.py` - Test patterns
- All entity files - Import patterns

**Deliverable:**
A discovery document with:
- Function/class inventory with line ranges
- Dependency graph
- Shared state documentation
- Import pattern inventory
- Test coverage map
- Proposed module boundaries

Create the analysis plan first. I'll review before you execute.
```

## Session 2: Requirements

```markdown
Begin Session 2: Detection Decomposition Requirements

Work with the @requirements-analyst agent to create PRD-SPRINT-3-DETECTION-DECOMPOSITION.

**Prerequisites:**
- Session 1 discovery complete

**Goals:**
1. Define module structure requirements
2. Define backward compatibility requirements
3. Define tier isolation requirements
4. Define facade requirements
5. Define acceptance criteria for each module
6. Define test requirements

**Key Questions:**
- What makes a tier "complete" in its module?
- How do we verify backward compatibility?
- What's the import strategy for consumers?

Create the plan first. I'll review before you execute.
```

## Session 3: Architecture

```markdown
Begin Session 3: Detection Decomposition Architecture

Work with the @architect agent to create TDD-SPRINT-3-DETECTION-DECOMPOSITION.

**Prerequisites:**
- PRD-SPRINT-3-DETECTION-DECOMPOSITION approved

**Goals:**
1. Design module interfaces
2. Design tier protocol (if any)
3. Design facade orchestration
4. Design import structure
5. Document dependency order
6. Create ADR for module boundaries

**Required ADR:**
- ADR-0119: Detection Module Decomposition Strategy

**Module Interface Template:**
```python
# Each tier module exports:
def detect_by_X(task: Task, context: DetectionContext) -> DetectionResult | None:
    """Attempt detection using tier X logic."""
    ...
```

Create the plan first. I'll review before you execute.
```

## Session 4: Implementation Phase 1

```markdown
Begin Session 4: Implementation Phase 1 - Package Structure and Types

Work with the @principal-engineer agent to create package foundation.

**Phase 1 Scope:**
1. Create detection/ package directory
2. Create detection/__init__.py (empty initially)
3. Extract EntityType to types.py
4. Extract DetectionResult to types.py
5. Extract DetectionConfidence to types.py
6. Extract ProjectTypeRegistry to registry.py
7. Update imports in original detection.py to use new modules
8. Verify tests still pass

**Hard Constraints:**
- detection.py still works (just imports from new modules)
- All existing tests pass
- No behavior changes

Create the plan first. I'll review before you execute.
```

## Session 5: Implementation Phase 2

```markdown
Begin Session 5: Implementation Phase 2 - Tier Extraction

Work with the @principal-engineer agent to extract tier modules.

**Phase 2 Scope:**
1. Extract Tier 1 (_detect_by_project_membership) to tier1.py
2. Extract Tier 2 (_detect_by_name_convention) to tier2.py
3. Extract Tier 3 (_detect_by_parent_inference) to tier3.py
4. Extract helper functions used by tiers
5. Update detection.py to import from tier modules
6. Verify tests still pass

**Extraction Order:**
1. tier1.py (simplest, fewest dependencies)
2. tier2.py (may share helpers)
3. tier3.py (depends on parent logic)

Create the plan first. I'll review before you execute.
```

## Session 6: Implementation Phase 3

```markdown
Begin Session 6: Implementation Phase 3 - Facade and Cleanup

Work with the @principal-engineer agent to complete decomposition.

**Phase 3 Scope:**
1. Extract Tier 4 (_detect_by_structure_inspection) to tier4.py
2. Create facade.py with detect_entity_type()
3. Update __init__.py with all re-exports
4. Verify backward compatibility imports work
5. Delete detection.py (or rename to detection_legacy.py for transition)
6. Verify all tests pass
7. Add tier-specific tests if coverage gaps exist

**Final Package Structure:**
```
detection/
    __init__.py    # from .facade import detect_entity_type, etc.
    types.py       # EntityType, DetectionResult, DetectionConfidence
    registry.py    # ProjectTypeRegistry
    tier1.py       # Project membership
    tier2.py       # Name convention
    tier3.py       # Parent inference
    tier4.py       # Structure inspection
    facade.py      # Main orchestration
```

Create the plan first. I'll review before you execute.
```

## Session 7: Validation

```markdown
Begin Session 7: Detection Decomposition Validation

Work with the @qa-adversary agent to validate the decomposition.

**Goals:**

**Part 1: Backward Compatibility**
- All existing imports work
- detect_entity_type() signature unchanged
- EntityType accessible from detection module
- DetectionResult accessible from detection module

**Part 2: Module Isolation**
- Each tier module can be imported independently
- No circular imports
- Clear dependency direction

**Part 3: Functional Correctness**
- All existing tests pass
- Detection behavior unchanged
- Each tier produces same results as before

**Part 4: Tier Testing**
- Each tier can be tested in isolation
- Edge cases covered per tier
- Fallback logic works

**Part 5: Structural Verification**
- Each module <250 lines
- Clear responsibility per module
- No shared mutable state

Create the plan first. I'll review before you execute.
```

---

# Context Gathering Checklist

Before starting, gather:

**Detection Structure:**
- [ ] `detection.py` full content (1016 lines)
- [ ] Function/class boundaries
- [ ] Import statements
- [ ] Module-level state

**Tier Logic:**
- [ ] Tier 1 implementation details
- [ ] Tier 2 implementation details
- [ ] Tier 3 implementation details
- [ ] Tier 4 implementation details
- [ ] Tier chaining/fallback logic

**Dependencies:**
- [ ] Internal dependencies between functions
- [ ] External module dependencies
- [ ] Shared helper functions

**Test Coverage:**
- [ ] test_detection.py structure
- [ ] Which tiers have tests
- [ ] Edge case coverage
