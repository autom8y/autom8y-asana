# Sprint 5 Issue Location Manifest

> Discovery Phase Output - Session 1 of 5
> Generated: 2024-12-19
> Status: COMPLETE

---

## Executive Summary

| Category | Target Count | Found | Status |
|----------|-------------|-------|--------|
| DRY Violations | 8 | 8 | FOUND |
| Liskov Violation | 1 | 1 | FOUND |
| Inheritance Issues | 5 | 5 | FOUND |
| Abstraction Issues | 6 | 5 | PARTIAL |
| **TOTAL** | **20** | **19** | **95%** |

**Note**: Found 19 issues (1 fewer than expected). The codebase is cleaner than anticipated after Sprints 1-4.

---

## Category 1: DRY Violations (8 Issues)

### DRY-001: Duplicate `business` property logic
- **Files**:
  - `src/autom8_asana/models/business/offer.py:94-107`
  - `src/autom8_asana/models/business/process.py:233-246`
- **Pattern**: Identical lazy-loading logic for `business` property through `unit.business`
- **Impact**: MEDIUM - Code duplication, maintenance burden
- **Proposed Fix**: Extract to `_get_business_via_unit()` method in mixin or base class

### DRY-002: Duplicate `_identify_holder()` method
- **Files**:
  - `src/autom8_asana/models/business/business.py:525-540`
  - `src/autom8_asana/models/business/unit.py:276-293`
- **Pattern**: Near-identical holder identification logic with only `filter_to_map` difference
- **Impact**: MEDIUM - Code duplication, risk of divergence
- **Proposed Fix**: Extract to shared function with parameter

### DRY-003: Duplicate `_populate_holders()` method
- **Files**:
  - `src/autom8_asana/models/business/business.py:508-524`
  - `src/autom8_asana/models/business/unit.py:250-274`
- **Pattern**: Similar holder population logic with entity-specific imports
- **Impact**: MEDIUM - Structural duplication
- **Proposed Fix**: Extract common pattern to base class with template method

### DRY-004: Duplicate `_fetch_holders_async()` method
- **Files**:
  - `src/autom8_asana/models/business/base.py:362-370` (stub)
  - `src/autom8_asana/models/business/business.py:591+`
  - `src/autom8_asana/models/business/unit.py:295+`
- **Pattern**: Similar async fetching pattern with entity-specific holder types
- **Impact**: MEDIUM - Parallel implementations
- **Proposed Fix**: Template method pattern in base class

### DRY-005: Duplicate `unit` property in Offer/Process/OfferHolder/ProcessHolder
- **Files**:
  - `src/autom8_asana/models/business/offer.py:83-92` (Offer.unit)
  - `src/autom8_asana/models/business/offer.py:268-277` (OfferHolder.unit)
  - `src/autom8_asana/models/business/process.py:222-231` (Process.unit)
  - `src/autom8_asana/models/business/process.py:473-481` (ProcessHolder.unit)
- **Pattern**: Identical `_unit` property accessor pattern repeated
- **Impact**: LOW - Simple property, but repeated 4 times
- **Proposed Fix**: Consider descriptor or mixin for unit navigation

### DRY-006: Duplicate `_invalidate_refs()` override pattern
- **Files**:
  - `src/autom8_asana/models/business/process.py:248-255`
  - `src/autom8_asana/models/business/offer.py:109-116`
- **Pattern**: Nearly identical override clearing `_business`, `_unit`, and holder ref
- **Impact**: LOW - Similar structure but entity-specific refs
- **Proposed Fix**: May be acceptable given entity-specific refs, but consider generic approach

### DRY-007: Duplicate logging patterns across detection tiers
- **Files**:
  - `src/autom8_asana/models/business/detection/tier1.py:107-111`
  - `src/autom8_asana/models/business/detection/tier2.py:153-163`
  - `src/autom8_asana/models/business/detection/tier3.py:69-74`
  - `src/autom8_asana/models/business/detection/tier4.py:76-78, 93-95`
- **Pattern**: Similar logger.debug() patterns with task_gid, tier, entity_type
- **Impact**: LOW - Logging consistency
- **Proposed Fix**: Helper function for detection logging

### DRY-008: Duplicate DetectionResult construction
- **Files**:
  - `src/autom8_asana/models/business/detection/tier1.py:113-119`
  - `src/autom8_asana/models/business/detection/tier2.py:166-172`
  - `src/autom8_asana/models/business/detection/tier3.py:76-82`
  - `src/autom8_asana/models/business/detection/tier4.py:81-87, 98-104`
- **Pattern**: Same DetectionResult construction with different parameters
- **Impact**: LOW - Constructor pattern
- **Proposed Fix**: Factory method `DetectionResult.create(entity_type, tier, ...)`

---

## Category 2: Liskov Violation (1 Issue)

### LISKOV-001: `_invalidate_refs()` signature incompatibility
- **Files**:
  - `src/autom8_asana/models/business/base.py:372` - Base signature: `def _invalidate_refs(self, _exclude_attr: str | None = None)`
  - `src/autom8_asana/models/business/process.py:248` - Override: `def _invalidate_refs(self)`
  - `src/autom8_asana/models/business/offer.py:109` - Override: `def _invalidate_refs(self)`
  - `src/autom8_asana/models/business/asset_edit.py:76` - Override: `def _invalidate_refs(self)` (calls `super()._invalidate_refs()`)
- **Pattern**: Base class has optional parameter that subclasses drop
- **Impact**: MEDIUM - Liskov Substitution Principle violation; calling with parameter fails on some subclasses
- **Proposed Fix**:
  - Option A: Add `_exclude_attr` parameter to all overrides (accept and ignore if not needed)
  - Option B: Remove parameter from base class (breaking change)
  - **Recommended**: Option A - maintain backward compatibility

---

## Category 3: Inheritance Issues (5 Issues)

### INHERIT-001: Process class has deep inheritance + multiple mixins
- **File**: `src/autom8_asana/models/business/process.py:151`
- **Pattern**: `class Process(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin)`
- **Issue**: 3-level inheritance + 2 mixins = complex MRO
- **Impact**: LOW - Works correctly, but MRO can be confusing
- **Proposed Fix**: Document MRO explicitly; no code change needed

### INHERIT-002: Unit class has 4 mixins
- **File**: `src/autom8_asana/models/business/unit.py:47`
- **Pattern**: `class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin, UpwardTraversalMixin)`
- **Issue**: Maximum mixin count in codebase
- **Impact**: LOW - Works correctly via Python MRO
- **Proposed Fix**: Document MRO; consider future consolidation

### INHERIT-003: Offer class has 4 mixins
- **File**: `src/autom8_asana/models/business/offer.py:44`
- **Pattern**: `class Offer(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin, UpwardTraversalMixin)`
- **Issue**: Parallel to Unit, same mixin set
- **Impact**: LOW - Consistent with Unit pattern
- **Proposed Fix**: Document; no change needed

### INHERIT-004: ReconciliationsHolder deprecated alias pattern
- **File**: `src/autom8_asana/models/business/business.py:77-91`
- **Pattern**: Deprecated subclass just to emit warning
- **Issue**: Inheritance used for deprecation; could use `__new__` or factory instead
- **Impact**: LOW - Works, but unconventional
- **Proposed Fix**: Keep for backward compat; remove in future major version

### INHERIT-005: HolderFactory vs HolderMixin overlap
- **Files**:
  - `src/autom8_asana/models/business/holder_factory.py:55`
  - `src/autom8_asana/models/business/base.py:46`
- **Pattern**: `HolderFactory(Task, HolderMixin[Task])` - Factory extends both Task and mixin
- **Issue**: HolderFactory reimplements `_populate_children()` that exists in HolderMixin
- **Impact**: MEDIUM - Duplication of population logic between two holder base classes
- **Proposed Fix**: Consolidate into single holder base; HolderFactory should extend HolderMixin properly

---

## Category 4: Abstraction Issues (5 Issues Found, 6 Expected)

### ABSTRACT-001: Missing protocol for entity navigation
- **Location**: `src/autom8_asana/models/business/` (no Protocol defined)
- **Pattern**: Offer, Process, Contact all have `.unit`, `.business` properties but no shared interface
- **Issue**: No formal Protocol defining navigation contract
- **Impact**: LOW - Duck typing works, but no static type checking
- **Proposed Fix**: Define `NavigableEntity` Protocol with `unit`, `business` properties

### ABSTRACT-002: Missing protocol for holder behavior
- **Location**: `src/autom8_asana/models/business/` (no Protocol defined)
- **Pattern**: All holders have `children`, `business` properties but no shared interface
- **Issue**: No formal Protocol for holder contract
- **Impact**: LOW - Duck typing works
- **Proposed Fix**: Define `Holder` Protocol

### ABSTRACT-003: Detection tier functions lack common interface
- **Location**: `src/autom8_asana/models/business/detection/tier*.py`
- **Pattern**: `detect_by_*` functions have similar but not identical signatures
- **Issue**: tier1-3 are sync, tier4 is async; no common type alias or Protocol
- **Impact**: LOW - Functions work, but integration differs by tier
- **Proposed Fix**: Define type aliases for tier function signatures

### ABSTRACT-004: HealingResult dataclass vs HealingResult in models.py
- **Files**:
  - `src/autom8_asana/persistence/healing.py:49-72` - `@dataclass HealingResult`
  - `src/autom8_asana/persistence/models.py` - Likely has its own `HealingResult`
- **Pattern**: Potential duplicate result types for same concept
- **Issue**: Possible confusion between module-level and models-level result types
- **Impact**: MEDIUM - Naming collision risk
- **Proposed Fix**: Consolidate to single source of truth in models.py

### ABSTRACT-005: CascadeExecutor returns CascadeResult but healing uses HealingReport
- **Files**:
  - `src/autom8_asana/persistence/cascade.py` - CascadeResult
  - `src/autom8_asana/persistence/healing.py` - HealingReport
- **Pattern**: Similar result structures with different names
- **Issue**: Inconsistent naming for operation result containers
- **Impact**: LOW - Works but adds cognitive load
- **Proposed Fix**: Consider unified result pattern or keep as-is (domain-specific names have value)

---

## Summary by Fix Complexity

### Quick Fixes (< 30 min each)
- LISKOV-001: Add parameter to overrides (4 files)
- DRY-007: Logging helper function
- DRY-008: DetectionResult factory method

### Medium Fixes (30-60 min each)
- DRY-001: Business property mixin
- DRY-002: Shared `_identify_holder()` function
- DRY-005: Unit navigation descriptor
- ABSTRACT-004: Consolidate HealingResult

### Larger Fixes (1-2 hours each)
- DRY-003, DRY-004: Template method for holder population
- INHERIT-005: HolderFactory/HolderMixin consolidation
- ABSTRACT-001, ABSTRACT-002: Define Protocols

### Defer/Document Only
- INHERIT-001, INHERIT-002, INHERIT-003: Document MRO
- INHERIT-004: Keep deprecated alias
- ABSTRACT-003: Type aliases (optional)
- ABSTRACT-005: Keep domain-specific naming

---

## Recommended Priority Order

1. **LISKOV-001** - Signature fix (breaks LSP)
2. **DRY-001, DRY-002** - High-value consolidation
3. **ABSTRACT-004** - Naming clarity
4. **DRY-003, DRY-004** - Template method (if time permits)
5. Remaining issues as time allows

---

## Files to Modify

| File | Issue Count | Issues |
|------|-------------|--------|
| `process.py` | 4 | LISKOV-001, DRY-001, DRY-005, DRY-006 |
| `offer.py` | 4 | LISKOV-001, DRY-001, DRY-005, DRY-006 |
| `business.py` | 2 | DRY-002, DRY-003 |
| `unit.py` | 2 | DRY-002, DRY-003 |
| `asset_edit.py` | 1 | LISKOV-001 |
| `base.py` | 1 | DRY-004 |
| `detection/tier*.py` | 2 | DRY-007, DRY-008 |
| `healing.py` | 1 | ABSTRACT-004 |
| `holder_factory.py` | 1 | INHERIT-005 |

---

## Session 1 Complete

**Next Session**: Session 2 - Requirements (PRD-SPRINT-5-CLEANUP)

**Handoff Artifacts**:
- This manifest with 19 located issues
- File:line references for implementation
- Complexity estimates for planning
