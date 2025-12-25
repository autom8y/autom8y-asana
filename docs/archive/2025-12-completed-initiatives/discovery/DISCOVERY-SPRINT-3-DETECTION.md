# DISCOVERY: Sprint 3 - Detection Module Decomposition

**Session**: S1 Discovery - Detection Module Decomposition
**Initiative**: Sprint 3 - Decompose detection.py god class
**Date**: 2025-12-19
**Analyst**: Requirements Analyst

---

## Executive Summary

`detection.py` is a 1125-line module that has grown to contain multiple concerns:
- Type definitions (EntityType enum, DetectionResult dataclass, EntityTypeInfo)
- Configuration data (ENTITY_TYPE_INFO master dict, derived maps)
- Detection logic across 4 tiers + fallback
- Helper utilities for holder identification and pattern matching

The module is **well-structured internally** but has **tight coupling** between tiers that will require careful extraction. Key finding: **ProjectTypeRegistry is NOT in detection.py** - it was already extracted to `registry.py`.

---

## 1. Structure Analysis

### 1.1 File Statistics

| Metric | Value |
|--------|-------|
| Total Lines | 1125 |
| Classes | 3 (EntityType, DetectionResult, EntityTypeInfo) |
| Public Functions | 13 |
| Private Functions | 9 |
| Constants | 6 |
| Derived Maps | 3 |

### 1.2 Component Catalog by Line Range

#### Types & Enums (Lines 1-169)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `EntityType` | Enum | 70-111 | All entity types (17 values including UNKNOWN) |
| `CONFIDENCE_TIER_*` | Constants | 113-120 | Confidence levels (1-5) |
| `DetectionResult` | Dataclass | 123-168 | Immutable result with `__bool__` and `is_deterministic` |

#### Master Configuration (Lines 170-401)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `EntityTypeInfo` | Dataclass | 173-198 | Single source of truth for entity metadata |
| `ENTITY_TYPE_INFO` | Dict | 201-325 | Master configuration (17 entity type definitions) |
| `get_holder_attr()` | Function | 331-347 | Lookup holder attribute from EntityTypeInfo |
| `entity_type_to_holder_attr()` | Function | 350-361 | Alias for `get_holder_attr()` |
| `_derive_name_patterns()` | Function | 367-373 | Derives NAME_PATTERNS from master config |
| `_derive_parent_child_map()` | Function | 376-382 | Derives PARENT_CHILD_MAP from master config |
| `NAME_PATTERNS` | Dict | 390 | Derived at module load |
| `HOLDER_NAME_MAP` | Dict | 395 | Alias to NAME_PATTERNS (backward compat) |
| `PARENT_CHILD_MAP` | Dict | 400 | Derived at module load |

#### Tier 2 Helper Functions (Lines 403-444, 628-691)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `detect_by_name()` | Function | 403-443 | **DEPRECATED** - legacy name detection |
| `_compile_word_boundary_pattern()` | Function | 628-640 | Cached regex compilation |
| `_strip_decorations()` | Function | 643-666 | Remove task name decorations |
| `_matches_pattern_with_word_boundary()` | Function | 669-690 | Word boundary matching |

#### Tier 1: Project Membership (Lines 449-625)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `_detect_tier1_project_membership()` | Function | 449-515 | Sync Tier 1 implementation |
| `detect_by_project()` | Function | 518-537 | Public wrapper for sync Tier 1 |
| `_detect_tier1_project_membership_async()` | Function | 540-625 | Async Tier 1 with lazy discovery |

#### Tier 2: Name Pattern Detection (Lines 693-760)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `_detect_by_name_pattern()` | Function | 693-760 | Tier 2 name pattern matching |

#### Tier 3: Parent Inference (Lines 763-807)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `detect_by_parent()` | Function | 763-807 | Tier 3 parent type inference |

#### Tier 4: Structure Inspection (Lines 810-878)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `detect_by_structure_async()` | Function | 810-878 | Async structure inspection |

#### Tier 5: Unknown Fallback (Lines 881-904)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `_make_unknown_result()` | Function | 881-904 | Create UNKNOWN result |

#### Unified Detection Functions (Lines 907-1126)
| Component | Type | Lines | Description |
|-----------|------|-------|-------------|
| `detect_entity_type()` | Function | 910-956 | Sync unified detection (Tiers 1-3, 5) |
| `identify_holder_type()` | Function | 959-1023 | Holder identification utility |
| `_matches_holder_pattern()` | Function | 1026-1064 | Legacy holder pattern matching |
| `detect_entity_type_async()` | Function | 1067-1125 | Async unified detection (Tiers 1-5) |

### 1.3 Tier Mapping

| Tier | Confidence | API Required | Functions |
|------|------------|--------------|-----------|
| 1 | 1.0 | No (sync), Optional (async discovery) | `_detect_tier1_project_membership()`, `detect_by_project()`, `_detect_tier1_project_membership_async()` |
| 2 | 0.6 | No | `_detect_by_name_pattern()`, helpers |
| 3 | 0.8 | No | `detect_by_parent()` |
| 4 | 0.9 | Yes | `detect_by_structure_async()` |
| 5 | 0.0 | No | `_make_unknown_result()` |

---

## 2. Internal Dependency Map

### 2.1 Function Call Graph

```
detect_entity_type() [Public Entry Point - Sync]
    |
    +-> detect_by_project()
    |       +-> _detect_tier1_project_membership()
    |               +-> registry.get_registry()
    |               +-> registry.ProjectTypeRegistry.lookup()
    |
    +-> _detect_by_name_pattern()
    |       +-> _strip_decorations()
    |       |       +-> patterns.STRIP_PATTERNS
    |       +-> _matches_pattern_with_word_boundary()
    |       |       +-> _compile_word_boundary_pattern()
    |       +-> patterns.get_pattern_config()
    |       +-> patterns.get_pattern_priority()
    |       +-> registry.get_registry().get_primary_gid()
    |
    +-> detect_by_parent()
    |       +-> PARENT_CHILD_MAP (derived from ENTITY_TYPE_INFO)
    |       +-> registry.get_registry().get_primary_gid()
    |
    +-> _make_unknown_result()

detect_entity_type_async() [Public Entry Point - Async]
    |
    +-> _detect_tier1_project_membership_async()
    |       +-> registry.get_workspace_registry()
    |       +-> WorkspaceProjectRegistry.lookup_or_discover_async()
    |
    +-> detect_entity_type() [reuses sync path]
    |
    +-> detect_by_structure_async()
            +-> registry.get_registry().get_primary_gid()

identify_holder_type() [Utility]
    +-> detect_entity_type()
    +-> get_holder_attr()
    +-> _matches_holder_pattern()
```

### 2.2 Shared State

| State | Location | Used By |
|-------|----------|---------|
| `ENTITY_TYPE_INFO` | Module-level dict | `get_holder_attr()`, `_derive_*()` |
| `NAME_PATTERNS` | Module-level dict (derived) | `detect_by_name()` (deprecated) |
| `PARENT_CHILD_MAP` | Module-level dict (derived) | `detect_by_parent()` |
| `HOLDER_NAME_MAP` | Alias to NAME_PATTERNS | `identify_holder_type()` fallback |
| LRU cache | `_compile_word_boundary_pattern` | `_matches_pattern_with_word_boundary()` |

### 2.3 Cross-Tier Coupling

**Tight Coupling Identified:**

1. **Tier 1 <-> Registry**: Tier 1 imports `get_registry()` and `get_workspace_registry()` from `registry.py`
2. **Tier 2 <-> Patterns**: Tier 2 imports `get_pattern_config()`, `get_pattern_priority()`, `STRIP_PATTERNS` from `patterns.py`
3. **All Tiers <-> Registry**: All tiers call `registry.get_registry().get_primary_gid()` for `expected_project_gid`
4. **Unified Functions <-> All Tiers**: `detect_entity_type()` and `detect_entity_type_async()` orchestrate tier calls

**Clean Boundaries:**
- Tier 3 is self-contained (only uses `PARENT_CHILD_MAP` and registry)
- Tier 4 is self-contained (only calls subtasks API and registry)
- Tier 5 is self-contained (only creates result)

---

## 3. External Dependency Map

### 3.1 What detection.py Imports

```python
# Standard library
from __future__ import annotations
import logging
import re
import warnings
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING

# Internal (TYPE_CHECKING only)
if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task

# Runtime internal imports (deferred)
# These occur inside functions to avoid circular imports:
from autom8_asana.models.business.registry import get_registry, get_workspace_registry
from autom8_asana.models.business.patterns import (
    STRIP_PATTERNS,
    get_pattern_config,
    get_pattern_priority,
)
```

### 3.2 What Imports detection.py

#### Source Files (src/autom8_asana/)

| File | Imports |
|------|---------|
| `models/business/__init__.py` | `HOLDER_NAME_MAP`, `EntityType`, `detect_by_name`, `detect_entity_type_async` |
| `models/business/patterns.py` | `EntityType` (TYPE_CHECKING) |
| `models/business/registry.py` | `EntityType` (TYPE_CHECKING and runtime) |
| `models/business/hydration.py` | `EntityType`, `detect_entity_type_async` |
| `models/business/business.py` | `identify_holder_type` |
| `models/business/unit.py` | `identify_holder_type` |

#### Test Files (tests/)

| File | Imports |
|------|---------|
| `unit/models/business/test_detection.py` | **Most symbols** including private `_detect_tier1_project_membership_async` |
| `unit/models/business/test_patterns.py` | `EntityType`, private helpers `_compile_word_boundary_pattern`, `_strip_decorations`, `_matches_pattern_with_word_boundary` |
| `unit/models/business/test_business.py` | `_matches_holder_pattern` (private) |
| `unit/models/business/test_registry.py` | `EntityType` |
| `unit/models/business/test_hydration.py` | `DetectionResult`, `EntityType`, `detect_entity_type_async` |
| `unit/models/business/test_hydration_combined.py` | `EntityType` |
| `unit/models/business/test_workspace_registry.py` | `EntityType` |
| `unit/models/business/test_upward_traversal.py` | `EntityType` |
| `unit/persistence/test_healing.py` | `DetectionResult`, `EntityType` |
| `integration/test_detection.py` | Multiple public symbols |
| `integration/test_hydration.py` | `EntityType` |
| `integration/test_workspace_registry.py` | `EntityType` |

### 3.3 Public API Surface

**`__all__` exports (26 symbols):**

```python
__all__ = [
    # Types
    "EntityType",
    "EntityTypeInfo",
    "DetectionResult",
    # Constants
    "ENTITY_TYPE_INFO",
    "HOLDER_NAME_MAP",
    "NAME_PATTERNS",
    "PARENT_CHILD_MAP",
    "CONFIDENCE_TIER_1",
    "CONFIDENCE_TIER_2",
    "CONFIDENCE_TIER_3",
    "CONFIDENCE_TIER_4",
    "CONFIDENCE_TIER_5",
    # Functions
    "get_holder_attr",
    "entity_type_to_holder_attr",
    "detect_by_name",            # DEPRECATED
    "detect_by_project",
    "detect_by_parent",
    "detect_by_structure_async",
    "detect_entity_type",
    "detect_entity_type_async",
    "identify_holder_type",
    "_detect_tier1_project_membership_async",  # EXPOSED (unusual for private)
]
```

**Note:** `_detect_tier1_project_membership_async` is exported despite being "private" (prefixed with `_`). This is intentional per TDD-WORKSPACE-PROJECT-REGISTRY for testing.

---

## 4. Test Coverage Baseline

### 4.1 Test Files

| Test File | Lines | Focus |
|-----------|-------|-------|
| `tests/unit/models/business/test_detection.py` | ~1229 | Primary detection tests |
| `tests/unit/models/business/test_patterns.py` | ~345 | Pattern matching tests |
| `tests/integration/test_detection.py` | ~724 | Integration scenarios |
| `tests/unit/models/business/test_business.py` (partial) | ~30 | `_matches_holder_pattern` |

### 4.2 Coverage by Component

| Component | Direct Tests | Coverage Level |
|-----------|--------------|----------------|
| `EntityType` | Yes | HIGH - all values tested |
| `DetectionResult` | Yes | HIGH - immutability, `__bool__`, `is_deterministic` |
| `EntityTypeInfo` | Indirect | MEDIUM - tested via derived maps |
| `ENTITY_TYPE_INFO` | Indirect | MEDIUM - tested via lookups |
| `detect_by_project()` | Yes | HIGH - multiple scenarios |
| `_detect_tier1_project_membership_async()` | Yes | HIGH - discovery tested |
| `_detect_by_name_pattern()` | Indirect | HIGH - via `detect_entity_type()` |
| `detect_by_parent()` | Yes | HIGH - all inference rules |
| `detect_by_structure_async()` | Yes | MEDIUM - Business/Unit structures |
| `detect_entity_type()` | Yes | HIGH - short-circuit, fallback |
| `detect_entity_type_async()` | Yes | HIGH - async path tested |
| `identify_holder_type()` | Indirect | LOW - no direct tests found |
| `_matches_holder_pattern()` | Yes | MEDIUM - basic cases |
| `_strip_decorations()` | Yes | HIGH - parametrized tests |
| `_compile_word_boundary_pattern()` | Yes | MEDIUM - caching tested |
| `_matches_pattern_with_word_boundary()` | Yes | HIGH - parametrized |
| `detect_by_name()` | Yes | HIGH - deprecation warning tested |

### 4.3 Coverage Gaps

1. **`identify_holder_type()`**: No direct unit tests; only tested indirectly via Business/Unit
2. **`entity_type_to_holder_attr()`**: Alias; may not need separate tests
3. **`_make_unknown_result()`**: No direct tests; tested via fallback scenarios
4. **Edge cases in `ENTITY_TYPE_INFO`**: Not all 17 entity types exhaustively tested

### 4.4 Private Function Test Imports

**Risk**: Tests import private functions directly, creating coupling:

```python
# test_detection.py
from autom8_asana.models.business.detection import (
    _detect_tier1_project_membership_async,  # Private but exported
)

# test_patterns.py
from autom8_asana.models.business.detection import (
    _compile_word_boundary_pattern,     # Private
    _matches_pattern_with_word_boundary, # Private
    _strip_decorations,                  # Private
)

# test_business.py
from autom8_asana.models.business.detection import _matches_holder_pattern
```

**Implication**: Extraction must either:
1. Re-export private functions from new modules, OR
2. Update test imports to use new locations

---

## 5. Extraction Boundary Analysis

### 5.1 Proposed Module Structure

```
src/autom8_asana/models/business/
    detection/
        __init__.py       # Re-exports for backward compatibility
        types.py          # EntityType, DetectionResult, EntityTypeInfo
        config.py         # ENTITY_TYPE_INFO, derived maps, helper functions
        tier1.py          # Project membership detection
        tier2.py          # Name pattern detection
        tier3.py          # Parent inference detection
        tier4.py          # Structure inspection detection
        facade.py         # detect_entity_type, detect_entity_type_async, identify_holder_type
```

### 5.2 Module Breakdown

#### `types.py` (New)

**Contains:**
- `EntityType` enum
- `DetectionResult` dataclass
- `EntityTypeInfo` dataclass
- `CONFIDENCE_TIER_*` constants

**Dependencies:** None (pure types)

**Exports:**
```python
__all__ = [
    "EntityType",
    "DetectionResult",
    "EntityTypeInfo",
    "CONFIDENCE_TIER_1",
    "CONFIDENCE_TIER_2",
    "CONFIDENCE_TIER_3",
    "CONFIDENCE_TIER_4",
    "CONFIDENCE_TIER_5",
]
```

**Estimated Lines:** ~170

#### `config.py` (New)

**Contains:**
- `ENTITY_TYPE_INFO` master dict
- `get_holder_attr()` / `entity_type_to_holder_attr()`
- `_derive_name_patterns()` / `_derive_parent_child_map()`
- `NAME_PATTERNS` / `HOLDER_NAME_MAP` / `PARENT_CHILD_MAP`

**Dependencies:**
- `types.py`: `EntityType`, `EntityTypeInfo`

**Exports:**
```python
__all__ = [
    "ENTITY_TYPE_INFO",
    "NAME_PATTERNS",
    "HOLDER_NAME_MAP",
    "PARENT_CHILD_MAP",
    "get_holder_attr",
    "entity_type_to_holder_attr",
]
```

**Estimated Lines:** ~230

#### `tier1.py` (New)

**Contains:**
- `_detect_tier1_project_membership()`
- `detect_by_project()`
- `_detect_tier1_project_membership_async()`

**Dependencies:**
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_1`
- `registry.py`: `get_registry()`, `get_workspace_registry()`

**Exports:**
```python
__all__ = [
    "detect_by_project",
    "_detect_tier1_project_membership_async",
]
```

**Estimated Lines:** ~180

#### `tier2.py` (New)

**Contains:**
- `detect_by_name()` (deprecated)
- `_compile_word_boundary_pattern()`
- `_strip_decorations()`
- `_matches_pattern_with_word_boundary()`
- `_detect_by_name_pattern()`

**Dependencies:**
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_2`
- `config.py`: `NAME_PATTERNS`, `HOLDER_NAME_MAP`
- `patterns.py`: `STRIP_PATTERNS`, `get_pattern_config()`, `get_pattern_priority()`
- `registry.py`: `get_registry()`

**Exports:**
```python
__all__ = [
    "detect_by_name",  # DEPRECATED
    # Private helpers exposed for testing
    "_compile_word_boundary_pattern",
    "_strip_decorations",
    "_matches_pattern_with_word_boundary",
]
```

**Estimated Lines:** ~150

#### `tier3.py` (New)

**Contains:**
- `detect_by_parent()`

**Dependencies:**
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_3`
- `config.py`: `PARENT_CHILD_MAP`
- `registry.py`: `get_registry()`

**Exports:**
```python
__all__ = ["detect_by_parent"]
```

**Estimated Lines:** ~60

#### `tier4.py` (New)

**Contains:**
- `detect_by_structure_async()`

**Dependencies:**
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_4`
- `registry.py`: `get_registry()`

**Exports:**
```python
__all__ = ["detect_by_structure_async"]
```

**Estimated Lines:** ~80

#### `facade.py` (New)

**Contains:**
- `_make_unknown_result()`
- `detect_entity_type()`
- `detect_entity_type_async()`
- `identify_holder_type()`
- `_matches_holder_pattern()`

**Dependencies:**
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_5`
- `config.py`: `get_holder_attr()`
- `tier1.py`: `detect_by_project()`, `_detect_tier1_project_membership_async()`
- `tier2.py`: `_detect_by_name_pattern()`
- `tier3.py`: `detect_by_parent()`
- `tier4.py`: `detect_by_structure_async()`

**Exports:**
```python
__all__ = [
    "detect_entity_type",
    "detect_entity_type_async",
    "identify_holder_type",
    "_matches_holder_pattern",  # For test compatibility
]
```

**Estimated Lines:** ~200

#### `__init__.py` (Re-export Facade)

**Contains:** Re-exports all public symbols for backward compatibility

```python
from autom8_asana.models.business.detection.types import (
    EntityType,
    EntityTypeInfo,
    DetectionResult,
    CONFIDENCE_TIER_1,
    CONFIDENCE_TIER_2,
    CONFIDENCE_TIER_3,
    CONFIDENCE_TIER_4,
    CONFIDENCE_TIER_5,
)
from autom8_asana.models.business.detection.config import (
    ENTITY_TYPE_INFO,
    NAME_PATTERNS,
    HOLDER_NAME_MAP,
    PARENT_CHILD_MAP,
    get_holder_attr,
    entity_type_to_holder_attr,
)
from autom8_asana.models.business.detection.tier1 import (
    detect_by_project,
    _detect_tier1_project_membership_async,
)
from autom8_asana.models.business.detection.tier2 import (
    detect_by_name,
    _compile_word_boundary_pattern,
    _strip_decorations,
    _matches_pattern_with_word_boundary,
)
from autom8_asana.models.business.detection.tier3 import detect_by_parent
from autom8_asana.models.business.detection.tier4 import detect_by_structure_async
from autom8_asana.models.business.detection.facade import (
    detect_entity_type,
    detect_entity_type_async,
    identify_holder_type,
    _matches_holder_pattern,
)

__all__ = [...]  # Same as current
```

---

## 6. Key Questions Answered

### Q1: Is ProjectTypeRegistry a singleton? How is state managed?

**Answer:** Yes, `ProjectTypeRegistry` is a singleton implemented via `__new__`:

```python
class ProjectTypeRegistry:
    _instance: ClassVar[ProjectTypeRegistry | None] = None

    def __new__(cls) -> ProjectTypeRegistry:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._gid_to_type = {}
            instance._type_to_gid = {}
            instance._initialized = False
            cls._instance = instance
        return cls._instance
```

**State Location:** `registry.py` (NOT in detection.py)

**Test Reset:** `ProjectTypeRegistry.reset()` sets `_instance = None`

### Q2: Are the tier boundaries clean, or is there cross-tier coupling?

**Answer:** **Partial coupling exists:**

1. **Clean:** Tiers 3, 4, 5 are self-contained with minimal dependencies
2. **Coupled:** Tier 2 depends on external `patterns.py` module
3. **Shared:** All tiers depend on `registry.py` for `get_primary_gid()`
4. **Orchestrated:** `detect_entity_type()` and `detect_entity_type_async()` call multiple tiers

**Coupling Mitigation:** Extraction to submodules with clear imports will maintain current structure while improving organization.

### Q3: What is the fallback chain between tiers?

**Answer:** Per ADR-0094:

```
Sync Path (detect_entity_type):
  Tier 1 (project) -> Tier 2 (name) -> Tier 3 (parent) -> Tier 5 (unknown)

Async Path (detect_entity_type_async):
  Async Tier 1 (project + discovery) -> Tier 2 (name) -> Tier 3 (parent) -> Tier 4 (structure, optional) -> Tier 5 (unknown)
```

**Short-circuit:** Each tier returns immediately on success; later tiers only execute on failure.

### Q4: Are there any private/internal functions that tests import directly?

**Answer:** Yes, several:

| Function | Test File | Risk Level |
|----------|-----------|------------|
| `_detect_tier1_project_membership_async` | test_detection.py | LOW (exported in `__all__`) |
| `_compile_word_boundary_pattern` | test_patterns.py | MEDIUM |
| `_strip_decorations` | test_patterns.py | MEDIUM |
| `_matches_pattern_with_word_boundary` | test_patterns.py | MEDIUM |
| `_matches_holder_pattern` | test_business.py | MEDIUM |

**Extraction Impact:** Test imports will need updating. Options:
1. Re-export from `detection/__init__.py` (backward compatible)
2. Update test imports to new module paths (cleaner)

---

## 7. Risks and Mitigations

### R1: Circular Import Risk

**Risk:** Splitting detection.py may introduce circular imports between submodules.

**Mitigation:**
- `types.py` has NO dependencies - import freely
- Use TYPE_CHECKING for type hints where needed
- Deferred imports (inside functions) where necessary

### R2: Test Breakage

**Risk:** 1200+ lines of tests import from detection.py; extraction may break imports.

**Mitigation:**
- Re-export ALL current symbols from `detection/__init__.py`
- Run test suite after each extraction step
- Update test imports in follow-up PR if desired

### R3: Backward Compatibility

**Risk:** External code importing from `autom8_asana.models.business.detection` may break.

**Mitigation:**
- `detection/__init__.py` maintains same import path
- All `__all__` exports remain available
- No API changes, only internal reorganization

### R4: Partial Extraction Instability

**Risk:** Extracting some modules while others remain may create inconsistent state.

**Mitigation:**
- Extract in dependency order: types -> config -> tiers -> facade
- Each extraction is a complete PR with tests passing
- Rollback possible at any step

---

## 8. Recommendations

### Phase 1: Extract Types (Low Risk)
1. Create `detection/types.py` with EntityType, DetectionResult, EntityTypeInfo, constants
2. Update imports in detection.py to use new module
3. Re-export from `detection/__init__.py`
4. Validate: All tests pass

### Phase 2: Extract Config (Medium Risk)
1. Create `detection/config.py` with ENTITY_TYPE_INFO and derived maps
2. Update imports in detection.py
3. Re-export from `detection/__init__.py`
4. Validate: All tests pass

### Phase 3: Extract Tiers (Medium Risk)
1. Create `detection/tier1.py`, `tier2.py`, `tier3.py`, `tier4.py`
2. Move tier-specific functions
3. Update internal imports
4. Re-export from `detection/__init__.py`
5. Validate: All tests pass

### Phase 4: Create Facade (Low Risk)
1. Create `detection/facade.py` with orchestration functions
2. Move `detect_entity_type()`, `detect_entity_type_async()`, `identify_holder_type()`
3. Re-export from `detection/__init__.py`
4. Remove original `detection.py` (now a directory)
5. Validate: All tests pass, external imports unchanged

---

## 9. Appendix: Symbol Export Verification

Current `__all__` in detection.py (must be preserved):

```python
__all__ = [
    "EntityType",
    "EntityTypeInfo",
    "DetectionResult",
    "ENTITY_TYPE_INFO",
    "HOLDER_NAME_MAP",
    "NAME_PATTERNS",
    "PARENT_CHILD_MAP",
    "CONFIDENCE_TIER_1",
    "CONFIDENCE_TIER_2",
    "CONFIDENCE_TIER_3",
    "CONFIDENCE_TIER_4",
    "CONFIDENCE_TIER_5",
    "get_holder_attr",
    "entity_type_to_holder_attr",
    "detect_by_name",
    "detect_by_project",
    "detect_by_parent",
    "detect_by_structure_async",
    "detect_entity_type",
    "detect_entity_type_async",
    "identify_holder_type",
    "_detect_tier1_project_membership_async",
]
```

All 22 symbols must remain importable from `autom8_asana.models.business.detection` after extraction.

---

## 10. Related Documents

- **ADR-0094**: Detection Fallback Chain Design
- **ADR-0115**: ProcessHolder Detection Strategy
- **ADR-0117**: Tier 2 Pattern Enhancement (word boundaries)
- **TDD-DETECTION**: Detection system technical design
- **TDD-WORKSPACE-PROJECT-REGISTRY**: Async Tier 1 with discovery

---

*Document generated by Requirements Analyst for Sprint 3 Discovery*
