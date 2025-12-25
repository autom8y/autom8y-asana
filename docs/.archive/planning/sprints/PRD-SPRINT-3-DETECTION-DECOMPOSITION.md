# PRD: Detection Module Decomposition

## Metadata

- **PRD ID**: PRD-SPRINT-3-DETECTION
- **Status**: Completed
- **Author**: Requirements Analyst
- **Created**: 2025-12-19
- **Last Updated**: 2025-12-25
- **Completed**: 2025-12-22
- **Stakeholders**: Principal Engineer, Architect
- **Related PRDs**: PRD-DETECTION, PRD-TECH-DEBT-REMEDIATION
- **Discovery Document**: [DISCOVERY-SPRINT-3-DETECTION](/docs/analysis/DISCOVERY-SPRINT-3-DETECTION.md)

---

## Problem Statement

### The Problem

`detection.py` has grown to **1125 lines** containing **4 distinct concerns** in a single file:

1. **Type definitions** (EntityType enum, DetectionResult dataclass, EntityTypeInfo)
2. **Configuration data** (ENTITY_TYPE_INFO master dict, 3 derived maps)
3. **Detection logic** across 5 tiers (22 functions total)
4. **Helper utilities** for holder identification and pattern matching

### Quantified Pain

| Metric | Current State | Impact |
|--------|---------------|--------|
| File Size | 1125 lines | Cognitive load; slow navigation |
| Classes | 3 mixed with 22 functions | Unclear boundaries |
| Test Files | 3 files, ~2300 lines | Tightly coupled to single module |
| Concerns | 4 in one file | Violates Single Responsibility |
| Import Surface | 22 symbols exported | Consumers import from one module |

### Who is Affected

- **Engineers**: Navigating 1100+ lines to find/modify tier-specific logic
- **Code Reviewers**: Difficulty understanding scope of changes
- **Test Authors**: Cannot test tiers in isolation; all tests import from monolith
- **Future Maintainers**: Adding new entity types requires touching multiple concerns

### Impact of Not Solving

1. **Continued growth**: Each new entity type adds ~20 lines to ENTITY_TYPE_INFO
2. **Merge conflicts**: Multiple engineers modifying same file
3. **Test fragility**: Changes to Tier 1 may break Tier 4 tests due to shared imports
4. **Onboarding friction**: New team members must understand entire file to modify any part

---

## Goals & Success Metrics

### Primary Goal

Decompose `detection.py` into a **package of focused modules** while maintaining **100% backward compatibility** for existing imports.

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| SM-1: Test Pass Rate | 100% | `pytest` runs without failures |
| SM-2: Import Compatibility | 100% | All existing `from autom8_asana.models.business.detection import X` work |
| SM-3: Max Module Size | <250 lines | `wc -l` on each new module |
| SM-4: Tier Isolation | Each tier in own file | File count = 7 (types, config, tier1-4, facade) |
| SM-5: No New Dependencies | 0 new external deps | No new items in pyproject.toml |

---

## Scope

### In Scope

| ID | Item | Description |
|----|------|-------------|
| IS-1 | Package Conversion | Convert `detection.py` (file) to `detection/` (package) |
| IS-2 | Type Extraction | Extract EntityType, DetectionResult, EntityTypeInfo to `types.py` |
| IS-3 | Config Extraction | Extract ENTITY_TYPE_INFO, derived maps to `config.py` |
| IS-4 | Tier Separation | Create `tier1.py`, `tier2.py`, `tier3.py`, `tier4.py` |
| IS-5 | Facade Creation | Create `facade.py` with unified detection functions |
| IS-6 | Re-export Layer | Create `__init__.py` that re-exports all 22 public symbols |
| IS-7 | Private Function Export | Re-export 5 private functions used by tests |

### Out of Scope

| ID | Item | Rationale |
|----|------|-----------|
| OS-1 | ProjectTypeRegistry Changes | Already in `registry.py`; discovered during S1 |
| OS-2 | WorkspaceProjectRegistry Changes | Already in `registry.py` |
| OS-3 | patterns.py Modifications | Separate module; not part of detection.py |
| OS-4 | Test File Reorganization | Follow-up work; not blocking decomposition |
| OS-5 | API Changes | Strictly internal refactor; no signature changes |
| OS-6 | New Detection Features | Decomposition only; no functional changes |
| OS-7 | Deprecation Removal | `detect_by_name()` remains deprecated but present |

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Create `detection/types.py` containing EntityType enum, DetectionResult dataclass, EntityTypeInfo dataclass, and CONFIDENCE_TIER_* constants | Must | File exists; contains listed components; no dependencies on other detection submodules |
| FR-2 | Create `detection/config.py` containing ENTITY_TYPE_INFO dict, NAME_PATTERNS, HOLDER_NAME_MAP, PARENT_CHILD_MAP, get_holder_attr(), entity_type_to_holder_attr() | Must | File exists; contains listed components; imports only from types.py |
| FR-3 | Create `detection/tier1.py` containing _detect_tier1_project_membership(), detect_by_project(), _detect_tier1_project_membership_async() | Must | File exists; Tier 1 tests pass in isolation |
| FR-4 | Create `detection/tier2.py` containing detect_by_name(), _compile_word_boundary_pattern(), _strip_decorations(), _matches_pattern_with_word_boundary(), _detect_by_name_pattern() | Must | File exists; Tier 2 tests pass in isolation |
| FR-5 | Create `detection/tier3.py` containing detect_by_parent() | Must | File exists; Tier 3 tests pass in isolation |
| FR-6 | Create `detection/tier4.py` containing detect_by_structure_async() | Must | File exists; Tier 4 tests pass in isolation |
| FR-7 | Create `detection/facade.py` containing detect_entity_type(), detect_entity_type_async(), identify_holder_type(), _matches_holder_pattern(), _make_unknown_result() | Must | File exists; orchestration logic works correctly |
| FR-8 | Create `detection/__init__.py` that re-exports all 22 symbols from current `__all__` | Must | All imports from `autom8_asana.models.business.detection` continue to work |
| FR-9 | Re-export 5 private functions (_detect_tier1_project_membership_async, _compile_word_boundary_pattern, _strip_decorations, _matches_pattern_with_word_boundary, _matches_holder_pattern) for test compatibility | Must | Tests importing private functions do not break |
| FR-10 | Remove original `detection.py` file after package creation | Must | No `detection.py` file exists; only `detection/` directory |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-1 | Module Size | Each module < 250 lines | `wc -l detection/*.py` |
| NFR-2 | Import Performance | No measurable regression | `python -c "from autom8_asana.models.business.detection import *"` timing |
| NFR-3 | Type Checking | mypy passes | `mypy src/autom8_asana/models/business/detection/` |
| NFR-4 | No Circular Imports | All modules import cleanly | `python -c "import autom8_asana.models.business.detection"` succeeds |
| NFR-5 | Test Execution Time | No regression > 5% | `pytest tests/unit/models/business/test_detection.py --durations=0` |
| NFR-6 | Documentation | Each module has docstring | Docstrings present in all 7 files |

---

## User Stories / Use Cases

### UC-1: Engineer Modifying Tier 2 Logic

**As a** SDK engineer
**I want to** modify name pattern detection without reading 1100 lines
**So that** I can quickly understand and change Tier 2 behavior

**Current Flow:**
1. Open `detection.py` (1125 lines)
2. Search for `_detect_by_name_pattern` (line 693)
3. Scroll through unrelated Tier 1, Tier 3, Tier 4 code
4. Make change; run all detection tests

**Target Flow:**
1. Open `detection/tier2.py` (~150 lines)
2. Find `_detect_by_name_pattern` immediately
3. Make change; run Tier 2 tests

### UC-2: Adding New Entity Type

**As a** SDK engineer
**I want to** add a new entity type (e.g., INVOICE_HOLDER)
**So that** the detection system recognizes invoice tasks

**Current Flow:**
1. Open `detection.py`
2. Add to EntityType enum (line ~90)
3. Add to ENTITY_TYPE_INFO (line ~250)
4. Possibly add to PARENT_CHILD_MAP derivation
5. Navigate through 800+ lines of detection functions

**Target Flow:**
1. Edit `detection/types.py` - add enum value
2. Edit `detection/config.py` - add to ENTITY_TYPE_INFO
3. Done (derived maps auto-update)

### UC-3: Code Review

**As a** code reviewer
**I want to** review a Tier 1 detection change
**So that** I can approve with confidence it doesn't break other tiers

**Current Flow:**
- Review diff of `detection.py` (may touch multiple concerns)
- Verify other tiers not affected
- Run full test suite

**Target Flow:**
- Review diff of `detection/tier1.py` only
- Scope is self-evident
- Run Tier 1 tests with confidence

---

## Assumptions

| ID | Assumption | Basis |
|----|------------|-------|
| A-1 | Python allows file-to-package migration | Standard Python behavior; directory replaces file with same name |
| A-2 | All 22 exported symbols are the complete public API | Verified from current `__all__` in discovery |
| A-3 | Private functions used by tests should remain accessible | Tests currently import them; breaking tests is unacceptable |
| A-4 | No external code imports detection.py beyond SDK and tests | Internal SDK module; not published externally |
| A-5 | Extraction order (types -> config -> tiers -> facade) prevents circular imports | types.py has no deps; each subsequent module only imports from earlier modules |

---

## Dependencies

| ID | Dependency | Owner | Status |
|----|------------|-------|--------|
| D-1 | `registry.py` module stable | Already extracted | Complete |
| D-2 | `patterns.py` module stable | Already extracted | Complete |
| D-3 | Test suite passing | QA | Must pass before and after |
| D-4 | mypy type checking | Build system | Must pass |

---

## Risks

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R-1 | Circular imports between submodules | Medium | High | Extract in dependency order; types.py has no deps |
| R-2 | Test breakage from changed import paths | Medium | High | Re-export ALL symbols from `__init__.py`; preserve private exports |
| R-3 | External code breaks | Low | Medium | No API changes; same import path works |
| R-4 | Partial extraction leaves inconsistent state | Medium | Medium | Complete each phase as atomic PR; all tests must pass |
| R-5 | Performance regression from additional imports | Low | Low | Benchmark before/after; Python import caching mitigates |

---

## Acceptance Criteria

| ID | Criterion | Validation Method |
|----|-----------|-------------------|
| AC-1 | All existing imports work unchanged | `from autom8_asana.models.business.detection import EntityType, detect_entity_type, ...` succeeds |
| AC-2 | All 1229 lines of unit tests pass | `pytest tests/unit/models/business/test_detection.py` returns 0 |
| AC-3 | All 345 lines of pattern tests pass | `pytest tests/unit/models/business/test_patterns.py` returns 0 |
| AC-4 | All 724 lines of integration tests pass | `pytest tests/integration/test_detection.py` returns 0 |
| AC-5 | No module exceeds 250 lines | `wc -l detection/*.py` all < 250 |
| AC-6 | mypy type checking passes | `mypy src/autom8_asana/models/business/detection/` returns 0 |
| AC-7 | No circular import errors | `python -c "from autom8_asana.models.business.detection import *"` succeeds |
| AC-8 | Original detection.py removed | `ls src/autom8_asana/models/business/detection.py` returns "not found" |
| AC-9 | Package structure matches specification | 7 files: `__init__.py`, `types.py`, `config.py`, `tier1.py`, `tier2.py`, `tier3.py`, `tier4.py`, `facade.py` |
| AC-10 | Private test imports work | Tests importing `_strip_decorations`, `_compile_word_boundary_pattern`, etc. pass |

---

## Implementation Phases

Per discovery recommendations, extraction should proceed in dependency order:

### Phase 1: Extract Types (Low Risk)

**Deliverable**: `detection/types.py` + `detection/__init__.py` skeleton

**Contents**:
- EntityType enum (~42 lines)
- DetectionResult dataclass (~46 lines)
- EntityTypeInfo dataclass (~26 lines)
- CONFIDENCE_TIER_* constants (~8 lines)

**Validation**: All tests pass; imports work

### Phase 2: Extract Config (Medium Risk)

**Deliverable**: `detection/config.py`

**Contents**:
- ENTITY_TYPE_INFO dict (~125 lines)
- Derived maps and functions (~105 lines)

**Validation**: All tests pass; derived maps identical

### Phase 3: Extract Tiers (Medium Risk)

**Deliverable**: `detection/tier1.py`, `tier2.py`, `tier3.py`, `tier4.py`

**Contents**:
- Tier 1: ~180 lines (project membership)
- Tier 2: ~150 lines (name patterns)
- Tier 3: ~60 lines (parent inference)
- Tier 4: ~80 lines (structure inspection)

**Validation**: All tier-specific tests pass

### Phase 4: Create Facade (Low Risk)

**Deliverable**: `detection/facade.py` + final `__init__.py`

**Contents**:
- Unified detection functions (~200 lines)
- Complete re-export layer

**Validation**: Full test suite passes; original `detection.py` removed

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| OQ-1 | Should private functions be documented as "internal API" in __init__.py? | Architect | Before Phase 1 | TBD |
| OQ-2 | Should test imports be updated to use submodule paths in follow-up PR? | Principal Engineer | After Phase 4 | TBD |
| OQ-3 | Should deprecation warnings be added for direct submodule imports? | Architect | After Phase 4 | TBD |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Requirements Analyst | Initial draft from S1 Discovery |

---

## Appendix A: Symbol Export Checklist

All 22 symbols must be importable from `autom8_asana.models.business.detection`:

**Types (3)**:
- [ ] `EntityType`
- [ ] `EntityTypeInfo`
- [ ] `DetectionResult`

**Constants (8)**:
- [ ] `ENTITY_TYPE_INFO`
- [ ] `HOLDER_NAME_MAP`
- [ ] `NAME_PATTERNS`
- [ ] `PARENT_CHILD_MAP`
- [ ] `CONFIDENCE_TIER_1`
- [ ] `CONFIDENCE_TIER_2`
- [ ] `CONFIDENCE_TIER_3`
- [ ] `CONFIDENCE_TIER_4`
- [ ] `CONFIDENCE_TIER_5`

**Functions (11)**:
- [ ] `get_holder_attr`
- [ ] `entity_type_to_holder_attr`
- [ ] `detect_by_name` (deprecated)
- [ ] `detect_by_project`
- [ ] `detect_by_parent`
- [ ] `detect_by_structure_async`
- [ ] `detect_entity_type`
- [ ] `detect_entity_type_async`
- [ ] `identify_holder_type`
- [ ] `_detect_tier1_project_membership_async`

**Private Functions for Tests (5)**:
- [ ] `_compile_word_boundary_pattern`
- [ ] `_strip_decorations`
- [ ] `_matches_pattern_with_word_boundary`
- [ ] `_matches_holder_pattern`
- [ ] `_detect_by_name_pattern` (if needed)

---

## Appendix B: File Size Estimates

| Module | Estimated Lines | Contents |
|--------|-----------------|----------|
| `__init__.py` | ~50 | Re-exports only |
| `types.py` | ~170 | Enums, dataclasses, constants |
| `config.py` | ~230 | ENTITY_TYPE_INFO, derived maps |
| `tier1.py` | ~180 | Project membership detection |
| `tier2.py` | ~150 | Name pattern detection |
| `tier3.py` | ~60 | Parent inference |
| `tier4.py` | ~80 | Structure inspection |
| `facade.py` | ~200 | Unified functions |
| **Total** | ~1120 | Same as original (minor overhead) |

---

## Related Documents

- **Discovery**: [DISCOVERY-SPRINT-3-DETECTION](/docs/analysis/DISCOVERY-SPRINT-3-DETECTION.md)
- **ADR-0094**: Detection Fallback Chain Design
- **ADR-0115**: ProcessHolder Detection Strategy
- **ADR-0117**: Tier 2 Pattern Enhancement
- **TDD-DETECTION**: Detection system technical design
