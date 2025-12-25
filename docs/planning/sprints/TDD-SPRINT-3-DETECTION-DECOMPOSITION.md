# TDD: Sprint 3 - Detection Module Decomposition

## Metadata
- **TDD ID**: TDD-SPRINT-3-DETECTION-DECOMPOSITION
- **Status**: Draft
- **Author**: Architect (Claude)
- **Created**: 2025-12-19
- **Last Updated**: 2025-12-19
- **PRD Reference**: [PRD-SPRINT-3-DETECTION-DECOMPOSITION](/docs/planning/sprints/PRD-SPRINT-3-DETECTION-DECOMPOSITION.md)
- **Related TDDs**: TDD-DETECTION, TDD-WORKSPACE-PROJECT-REGISTRY
- **Related ADRs**: [ADR-0142](/docs/decisions/ADR-0142-detection-package-structure.md), ADR-0094, ADR-0138

## Overview

This TDD defines the technical approach for decomposing `detection.py` (1125 lines) into a focused package of 7 modules, each under 250 lines. The decomposition is a **pure structural refactoring** with no API or behavioral changes. All 22 public symbols remain importable from `autom8_asana.models.business.detection`.

## Requirements Summary

Per PRD-SPRINT-3-DETECTION-DECOMPOSITION:

| ID | Requirement | Design Response |
|----|-------------|-----------------|
| FR-1 | Create `detection/types.py` | Section 4.1 |
| FR-2 | Create `detection/config.py` | Section 4.2 |
| FR-3 | Create `detection/tier1.py` | Section 4.3 |
| FR-4 | Create `detection/tier2.py` | Section 4.4 |
| FR-5 | Create `detection/tier3.py` | Section 4.5 |
| FR-6 | Create `detection/tier4.py` | Section 4.6 |
| FR-7 | Create `detection/facade.py` | Section 4.7 |
| FR-8 | Create `detection/__init__.py` with re-exports | Section 4.8 |
| FR-9 | Re-export 5 private functions for tests | Section 4.8.1 |
| FR-10 | Remove original `detection.py` | Section 6.4 |

| ID | NFR | Validation |
|----|-----|------------|
| NFR-1 | Each module < 250 lines | `wc -l detection/*.py` |
| NFR-2 | No import performance regression | Benchmark before/after |
| NFR-3 | mypy passes | `mypy src/autom8_asana/models/business/detection/` |
| NFR-4 | No circular imports | Fresh Python import succeeds |
| NFR-5 | Test execution time unchanged | `pytest --durations=0` |
| NFR-6 | Each module has docstring | Code review |

## System Context

```
+---------------------------------------------+
|        autom8_asana SDK                     |
|  +---------------------------------------+  |
|  |     models/business/                  |  |
|  |  +--------+  +----------+  +-------+  |  |
|  |  |business|  |  unit    |  |hydra- |  |  |
|  |  |  .py   |  |   .py    |  | tion  |  |  |
|  |  +---+----+  +----+-----+  +---+---+  |  |
|  |      |            |            |      |  |
|  |      v            v            v      |  |
|  |  +----------------------------------+ |  |
|  |  |         detection/               | |  |  <-- Decomposition Target
|  |  |  +------+ +------+ +--------+    | |  |
|  |  |  |types | |config| |tier1-4 |    | |  |
|  |  |  +------+ +------+ +--------+    | |  |
|  |  |  +------+ +--------+             | |  |
|  |  |  |facade| |__init__|             | |  |
|  |  |  +------+ +--------+             | |  |
|  |  +----------------------------------+ |  |
|  |      |            |                   |  |
|  |      v            v                   |  |
|  |  +----------+  +----------+           |  |
|  |  | registry |  | patterns |           |  |
|  |  +----------+  +----------+           |  |
|  +---------------------------------------+  |
+---------------------------------------------+
```

The detection package is imported by:
- `business.py` - uses `identify_holder_type()`
- `unit.py` - uses `identify_holder_type()`
- `hydration.py` - uses `EntityType`, `detect_entity_type_async()`
- `__init__.py` - re-exports public symbols

The detection package imports from:
- `registry.py` - `get_registry()`, `get_workspace_registry()`
- `patterns.py` - `get_pattern_config()`, `get_pattern_priority()`, `STRIP_PATTERNS`

## Design

### Component Architecture

Per ADR-0120, the package structure follows strict layering to prevent circular imports:

```
                    +------------+
                    |  types.py  |  Layer 0: Pure types (no dependencies)
                    +------------+
                          |
                    +------------+
                    | config.py  |  Layer 1: Configuration (depends on types only)
                    +------------+
                          |
    +----------+----------+----------+----------+
    |          |          |          |          |
+--------+ +--------+ +--------+ +--------+
| tier1  | | tier2  | | tier3  | | tier4  |  Layer 2: Detection tiers
+--------+ +--------+ +--------+ +--------+
    |          |          |          |
    +----------+----------+----------+
                    |
               +----------+
               | facade   |  Layer 3: Orchestration
               +----------+
                    |
               +----------+
               |__init__  |  Layer 4: Re-exports
               +----------+
```

| Module | Responsibility | Est. Lines | Layer |
|--------|----------------|------------|-------|
| `types.py` | EntityType enum, DetectionResult, EntityTypeInfo, CONFIDENCE constants | ~170 | 0 |
| `config.py` | ENTITY_TYPE_INFO dict, derived maps, helper functions | ~230 | 1 |
| `tier1.py` | Project membership detection (sync + async) | ~180 | 2 |
| `tier2.py` | Name pattern detection, helper utilities | ~150 | 2 |
| `tier3.py` | Parent inference detection | ~60 | 2 |
| `tier4.py` | Structure inspection detection (async) | ~80 | 2 |
| `facade.py` | `detect_entity_type()`, `detect_entity_type_async()`, `identify_holder_type()` | ~200 | 3 |
| `__init__.py` | Re-exports all public and test-required symbols | ~50 | 4 |

### 4.1 Module: types.py

**Purpose**: Pure type definitions with zero internal dependencies.

**Exports**:
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

**Contents**:
| Component | Lines | Description |
|-----------|-------|-------------|
| `EntityType` | 42 | Enum with 17 entity types |
| `CONFIDENCE_TIER_*` | 8 | Float constants 1.0, 0.6, 0.8, 0.9, 0.0 |
| `DetectionResult` | 46 | Frozen dataclass with `__bool__`, `is_deterministic` |
| `EntityTypeInfo` | 26 | Frozen dataclass for entity metadata |

**Internal Dependencies**: None

**External Dependencies**:
- `dataclasses.dataclass`
- `enum.Enum`

**Interface**:
```python
class EntityType(Enum):
    """Types of entities in the business model hierarchy."""
    BUSINESS = "business"
    CONTACT_HOLDER = "contact_holder"
    # ... 15 more values
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Result of entity type detection."""
    entity_type: EntityType
    confidence: float
    tier_used: int
    needs_healing: bool
    expected_project_gid: str | None

    def __bool__(self) -> bool: ...
    @property
    def is_deterministic(self) -> bool: ...

@dataclass(frozen=True, slots=True)
class EntityTypeInfo:
    """Master configuration for an entity type."""
    entity_type: EntityType
    name_pattern: str | None = None
    display_name: str | None = None
    emoji: str | None = None
    holder_attr: str | None = None
    child_type: EntityType | None = None
    has_project: bool = True
```

### 4.2 Module: config.py

**Purpose**: Master configuration and derived lookup maps.

**Exports**:
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

**Contents**:
| Component | Lines | Description |
|-----------|-------|-------------|
| `ENTITY_TYPE_INFO` | 125 | Dict mapping EntityType to EntityTypeInfo |
| `_derive_name_patterns()` | 8 | Extracts name patterns from ENTITY_TYPE_INFO |
| `_derive_parent_child_map()` | 8 | Extracts parent-child mapping |
| `NAME_PATTERNS` | 1 | Derived at module load |
| `HOLDER_NAME_MAP` | 1 | Alias for backward compatibility |
| `PARENT_CHILD_MAP` | 1 | Derived at module load |
| `get_holder_attr()` | 18 | Lookup holder attribute from EntityTypeInfo |
| `entity_type_to_holder_attr()` | 12 | Alias for semantic clarity |

**Internal Dependencies**:
- `types.py`: `EntityType`, `EntityTypeInfo`

**External Dependencies**: None

**Interface**:
```python
ENTITY_TYPE_INFO: dict[EntityType, EntityTypeInfo]

NAME_PATTERNS: dict[str, EntityType]  # e.g., {"contacts": EntityType.CONTACT_HOLDER}
HOLDER_NAME_MAP: dict[str, EntityType]  # Alias to NAME_PATTERNS
PARENT_CHILD_MAP: dict[EntityType, EntityType]  # e.g., {CONTACT_HOLDER: CONTACT}

def get_holder_attr(entity_type: EntityType) -> str | None:
    """Get holder attribute name (e.g., '_contact_holder') or None."""

def entity_type_to_holder_attr(entity_type: EntityType) -> str | None:
    """Alias for get_holder_attr()."""
```

### 4.3 Module: tier1.py

**Purpose**: Project membership detection (O(1) registry lookup).

**Exports**:
```python
__all__ = [
    "detect_by_project",
    "_detect_tier1_project_membership_async",
]
```

**Contents**:
| Component | Lines | Description |
|-----------|-------|-------------|
| `_detect_tier1_project_membership()` | 67 | Sync Tier 1 implementation |
| `detect_by_project()` | 20 | Public wrapper for sync Tier 1 |
| `_detect_tier1_project_membership_async()` | 86 | Async Tier 1 with lazy discovery |

**Internal Dependencies**:
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_1`

**External Dependencies**:
- `registry.py`: `get_registry()`, `get_workspace_registry()`
- TYPE_CHECKING: `AsanaClient`, `Task`

**Interface**:
```python
def detect_by_project(task: Task) -> DetectionResult | None:
    """Tier 1: Detect entity type by project membership (sync)."""

async def _detect_tier1_project_membership_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Async Tier 1: Detect with lazy workspace discovery."""
```

### 4.4 Module: tier2.py

**Purpose**: Name pattern detection with word boundary matching.

**Exports**:
```python
__all__ = [
    "detect_by_name",  # DEPRECATED
    "_detect_by_name_pattern",
    "_compile_word_boundary_pattern",
    "_strip_decorations",
    "_matches_pattern_with_word_boundary",
]
```

**Contents**:
| Component | Lines | Description |
|-----------|-------|-------------|
| `_compile_word_boundary_pattern()` | 13 | LRU-cached regex compilation |
| `_strip_decorations()` | 24 | Remove task name prefixes/suffixes |
| `_matches_pattern_with_word_boundary()` | 22 | Check name against patterns |
| `_detect_by_name_pattern()` | 68 | Tier 2 implementation |
| `detect_by_name()` | 42 | DEPRECATED legacy function |

**Internal Dependencies**:
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_2`
- `config.py`: `NAME_PATTERNS`, `HOLDER_NAME_MAP`

**External Dependencies**:
- `patterns.py`: `STRIP_PATTERNS`, `get_pattern_config()`, `get_pattern_priority()`
- `registry.py`: `get_registry()`
- `functools.lru_cache`, `re`, `warnings`

**Interface**:
```python
def detect_by_name(name: str | None) -> EntityType | None:
    """DEPRECATED: Use detect_entity_type() instead."""

def _detect_by_name_pattern(task: Task) -> DetectionResult | None:
    """Tier 2: Detect entity type by name pattern matching."""

@lru_cache(maxsize=128)
def _compile_word_boundary_pattern(pattern: str) -> re.Pattern[str]:
    """Compile pattern with word boundaries (cached)."""

def _strip_decorations(name: str) -> str:
    """Remove common task name decorations."""

def _matches_pattern_with_word_boundary(
    name: str, patterns: tuple[str, ...], use_word_boundary: bool
) -> str | None:
    """Check if name matches any pattern."""
```

### 4.5 Module: tier3.py

**Purpose**: Parent type inference detection.

**Exports**:
```python
__all__ = ["detect_by_parent"]
```

**Contents**:
| Component | Lines | Description |
|-----------|-------|-------------|
| `detect_by_parent()` | 45 | Infer child type from parent type |

**Internal Dependencies**:
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_3`
- `config.py`: `PARENT_CHILD_MAP`

**External Dependencies**:
- `registry.py`: `get_registry()`

**Interface**:
```python
def detect_by_parent(task: Task, parent_type: EntityType) -> DetectionResult | None:
    """Tier 3: Detect entity type by parent type inference."""
```

### 4.6 Module: tier4.py

**Purpose**: Async structure inspection detection via API call.

**Exports**:
```python
__all__ = ["detect_by_structure_async"]
```

**Contents**:
| Component | Lines | Description |
|-----------|-------|-------------|
| `detect_by_structure_async()` | 69 | Inspect subtasks to infer type |

**Internal Dependencies**:
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_4`

**External Dependencies**:
- `registry.py`: `get_registry()`
- TYPE_CHECKING: `AsanaClient`, `Task`

**Interface**:
```python
async def detect_by_structure_async(
    task: Task,
    client: AsanaClient,
) -> DetectionResult | None:
    """Tier 4: Detect entity type by subtask structure inspection."""
```

### 4.7 Module: facade.py

**Purpose**: Unified detection orchestration and utilities.

**Exports**:
```python
__all__ = [
    "detect_entity_type",
    "detect_entity_type_async",
    "identify_holder_type",
    "_matches_holder_pattern",
]
```

**Contents**:
| Component | Lines | Description |
|-----------|-------|-------------|
| `_make_unknown_result()` | 24 | Create Tier 5 UNKNOWN result |
| `detect_entity_type()` | 47 | Sync unified detection (Tiers 1-3, 5) |
| `detect_entity_type_async()` | 60 | Async unified detection (Tiers 1-5) |
| `identify_holder_type()` | 65 | Holder identification utility |
| `_matches_holder_pattern()` | 39 | Legacy holder pattern matching |

**Internal Dependencies**:
- `types.py`: `EntityType`, `DetectionResult`, `CONFIDENCE_TIER_5`
- `config.py`: `get_holder_attr()`
- `tier1.py`: `detect_by_project()`, `_detect_tier1_project_membership_async()`
- `tier2.py`: `_detect_by_name_pattern()`
- `tier3.py`: `detect_by_parent()`
- `tier4.py`: `detect_by_structure_async()`

**External Dependencies**:
- TYPE_CHECKING: `AsanaClient`, `Task`
- `logging`

**Interface**:
```python
def detect_entity_type(
    task: Task,
    parent_type: EntityType | None = None,
) -> DetectionResult:
    """Synchronous entity type detection (Tiers 1-3)."""

async def detect_entity_type_async(
    task: Task,
    client: AsanaClient,
    parent_type: EntityType | None = None,
    allow_structure_inspection: bool = False,
) -> DetectionResult:
    """Asynchronous entity type detection (Tiers 1-5)."""

def identify_holder_type(
    task: Task,
    holder_key_map: dict[str, tuple[str, str]],
    *,
    filter_to_map: bool = False,
) -> str | None:
    """Identify which holder type a task is."""

def _matches_holder_pattern(task: Task, name_pattern: str, emoji: str) -> bool:
    """Check if task matches a holder definition."""
```

### 4.8 Module: __init__.py

**Purpose**: Re-export all symbols for backward compatibility.

**Contents**:
```python
"""Entity type detection for business model hierarchy.

This package provides tiered type detection capabilities for identifying entity types.
The detection chain prioritizes deterministic project-membership detection (Tier 1),
with fallback tiers for name patterns, parent inference, and structure inspection.

Example:
    # Sync detection (Tiers 1-3, no API calls)
    result = detect_entity_type(task)

    # Async detection with optional Tier 4
    result = await detect_entity_type_async(task, client, allow_structure_inspection=True)
"""

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
    _detect_by_name_pattern,
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
    "detect_by_name",
    "detect_by_project",
    "detect_by_parent",
    "detect_by_structure_async",
    "detect_entity_type",
    "detect_entity_type_async",
    "identify_holder_type",
    "_detect_tier1_project_membership_async",
    # Private functions for test compatibility
    "_detect_by_name_pattern",
    "_compile_word_boundary_pattern",
    "_strip_decorations",
    "_matches_pattern_with_word_boundary",
    "_matches_holder_pattern",
]
```

#### 4.8.1 Private Function Re-exports

The following private functions are imported directly by tests and must be re-exported:

| Function | Imported By | Reason |
|----------|-------------|--------|
| `_detect_tier1_project_membership_async` | test_detection.py | Explicitly exported in current `__all__` |
| `_compile_word_boundary_pattern` | test_patterns.py | Tests caching behavior |
| `_strip_decorations` | test_patterns.py | Parametrized decoration stripping tests |
| `_matches_pattern_with_word_boundary` | test_patterns.py | Word boundary matching tests |
| `_matches_holder_pattern` | test_business.py | Holder pattern matching tests |
| `_detect_by_name_pattern` | test_detection.py | Internal Tier 2 tests |

### Dependency Graph

```
Layer 0 (types.py):
  - No internal imports
  - Standard library only: dataclasses, enum

Layer 1 (config.py):
  - from .types import EntityType, EntityTypeInfo

Layer 2 (tier1.py):
  - from .types import EntityType, DetectionResult, CONFIDENCE_TIER_1
  - External: registry.get_registry(), registry.get_workspace_registry()

Layer 2 (tier2.py):
  - from .types import EntityType, DetectionResult, CONFIDENCE_TIER_2
  - from .config import NAME_PATTERNS, HOLDER_NAME_MAP
  - External: patterns.STRIP_PATTERNS, patterns.get_pattern_config(),
              patterns.get_pattern_priority(), registry.get_registry()

Layer 2 (tier3.py):
  - from .types import EntityType, DetectionResult, CONFIDENCE_TIER_3
  - from .config import PARENT_CHILD_MAP
  - External: registry.get_registry()

Layer 2 (tier4.py):
  - from .types import EntityType, DetectionResult, CONFIDENCE_TIER_4
  - External: registry.get_registry()

Layer 3 (facade.py):
  - from .types import EntityType, DetectionResult, CONFIDENCE_TIER_5
  - from .config import get_holder_attr
  - from .tier1 import detect_by_project, _detect_tier1_project_membership_async
  - from .tier2 import _detect_by_name_pattern
  - from .tier3 import detect_by_parent
  - from .tier4 import detect_by_structure_async

Layer 4 (__init__.py):
  - Imports from all modules (re-exports only, no logic)
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Package vs single file | Package with 7 modules | SRP, maintainability, merge conflicts | [ADR-0142](/docs/decisions/ADR-0142-detection-package-structure.md) |
| Module granularity | One file per tier + types + config + facade | Natural boundaries from existing code | ADR-0142 |
| Re-export strategy | Full re-export in `__init__.py` | Backward compatibility for all imports | ADR-0142 |
| Private function handling | Re-export for test compatibility | 2300+ lines of tests would break otherwise | ADR-0142 |
| Extraction order | types -> config -> tiers -> facade | Dependency order prevents circular imports | ADR-0142 |

## Complexity Assessment

**Level**: Module

This is a **structural refactoring** with:
- No new functionality
- No API changes
- No behavioral changes
- Clean internal boundaries

The complexity is appropriate because:
- Changes are scoped to file organization
- Each module has clear responsibility
- Dependencies are strictly layered
- Rollback is straightforward (restore detection.py)

## Implementation Plan

### Migration Strategy

Extraction proceeds in **dependency order** to prevent circular imports at any step:

```
Phase 1: types.py    <- No dependencies, safe first step
Phase 2: config.py   <- Depends only on types.py
Phase 3a: tier1.py   <- Depends on types.py, external registry
Phase 3b: tier2.py   <- Depends on types.py, config.py, external patterns/registry
Phase 3c: tier3.py   <- Depends on types.py, config.py, external registry
Phase 3d: tier4.py   <- Depends on types.py, external registry
Phase 4: facade.py   <- Depends on all tiers, types.py, config.py
Phase 5: __init__.py <- Imports from all modules
Phase 6: Remove detection.py
```

### Phases

| Phase | Deliverable | Dependencies | Estimate | Validation |
|-------|-------------|--------------|----------|------------|
| 1 | `types.py` + skeleton `__init__.py` | None | 30 min | All tests pass |
| 2 | `config.py` | Phase 1 | 30 min | All tests pass |
| 3a | `tier1.py` | Phases 1-2 | 20 min | Tier 1 tests pass |
| 3b | `tier2.py` | Phases 1-2 | 30 min | Tier 2 tests pass |
| 3c | `tier3.py` | Phases 1-2 | 15 min | Tier 3 tests pass |
| 3d | `tier4.py` | Phases 1-2 | 15 min | Tier 4 tests pass |
| 4 | `facade.py` | Phases 1-3 | 30 min | All tests pass |
| 5 | Complete `__init__.py` | All phases | 15 min | All tests pass |
| 6 | Remove `detection.py` | All phases | 5 min | All tests pass |
| **Total** | | | **~3 hours** | |

### Phase Execution Details

#### Phase 1: Extract types.py

1. Create `detection/` directory
2. Create `detection/types.py` with:
   - `EntityType` enum (lines 70-111 of detection.py)
   - `CONFIDENCE_TIER_*` constants (lines 113-120)
   - `DetectionResult` dataclass (lines 123-168)
   - `EntityTypeInfo` dataclass (lines 173-198)
3. Create skeleton `detection/__init__.py`:
   ```python
   from autom8_asana.models.business.detection.types import (
       EntityType, EntityTypeInfo, DetectionResult,
       CONFIDENCE_TIER_1, CONFIDENCE_TIER_2, CONFIDENCE_TIER_3,
       CONFIDENCE_TIER_4, CONFIDENCE_TIER_5,
   )
   # ... remaining imports from detection.py ...
   ```
4. Update `detection.py` to import from `types.py`
5. Run tests: `pytest tests/unit/models/business/test_detection.py`

#### Phase 2: Extract config.py

1. Create `detection/config.py` with:
   - `ENTITY_TYPE_INFO` dict (lines 200-325)
   - `get_holder_attr()` (lines 331-347)
   - `entity_type_to_holder_attr()` (lines 350-361)
   - `_derive_name_patterns()` (lines 367-373)
   - `_derive_parent_child_map()` (lines 376-382)
   - `NAME_PATTERNS`, `HOLDER_NAME_MAP`, `PARENT_CHILD_MAP` derivations
2. Update `detection.py` imports
3. Update `__init__.py` re-exports
4. Run tests

#### Phase 3: Extract Tier Modules

Execute 3a-3d in order. Each step:
1. Create `tier{n}.py` with tier-specific functions
2. Update internal imports in `detection.py`
3. Update `__init__.py` re-exports
4. Run tier-specific tests

#### Phase 4: Extract facade.py

1. Create `detection/facade.py` with:
   - `_make_unknown_result()` (lines 881-904)
   - `detect_entity_type()` (lines 910-956)
   - `identify_holder_type()` (lines 959-1023)
   - `_matches_holder_pattern()` (lines 1026-1064)
   - `detect_entity_type_async()` (lines 1067-1125)
2. Update `__init__.py` with complete re-exports
3. Run full test suite

#### Phase 5: Finalize __init__.py

1. Remove all logic from `__init__.py` (pure re-exports)
2. Verify all 22 `__all__` exports work
3. Verify 5 private function exports work
4. Run: `python -c "from autom8_asana.models.business.detection import *"`

#### Phase 6: Remove detection.py

1. Delete `detection.py`
2. Run full test suite
3. Run mypy
4. Verify no import errors

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-1: Circular imports between submodules | High | Medium | Extract in strict dependency order; types.py has no deps |
| R-2: Test breakage from import path changes | High | Medium | Re-export ALL symbols from `__init__.py`; no path changes needed |
| R-3: External code breaks | Medium | Low | Same import path `autom8_asana.models.business.detection` |
| R-4: Partial extraction leaves inconsistent state | Medium | Medium | Complete each phase atomically; tests must pass between phases |
| R-5: Performance regression from import chain | Low | Low | Python caches imports; benchmark before/after |
| R-6: Missing private function export | Medium | Medium | Verify tests pass after each phase; grep for private imports |

## Rollback Plan

If extraction fails at any phase:

1. **Phase 1-5 incomplete**: Restore `detection.py` from git, delete `detection/` directory
2. **Phase 6 failed**: Restore `detection.py` from git (detection/ is orphaned but harmless)

Rollback command:
```bash
git checkout HEAD -- src/autom8_asana/models/business/detection.py
rm -rf src/autom8_asana/models/business/detection/
pytest  # Verify restoration
```

## Observability

Not applicable - this is a structural refactoring with no runtime behavioral changes.

## Testing Strategy

### Unit Testing

All existing tests must pass unchanged:

| Test File | Lines | Focus | Validation |
|-----------|-------|-------|------------|
| `test_detection.py` | 1229 | All detection logic | `pytest tests/unit/models/business/test_detection.py` |
| `test_patterns.py` | 345 | Pattern matching helpers | `pytest tests/unit/models/business/test_patterns.py` |
| `test_business.py` (partial) | 30 | `_matches_holder_pattern` | `pytest tests/unit/models/business/test_business.py` |

### Integration Testing

| Test File | Lines | Validation |
|-----------|-------|------------|
| `test_detection.py` | 724 | `pytest tests/integration/test_detection.py` |

### Validation Commands

Run after each phase:
```bash
# Unit tests
pytest tests/unit/models/business/test_detection.py -v

# Pattern tests
pytest tests/unit/models/business/test_patterns.py -v

# Integration tests
pytest tests/integration/test_detection.py -v

# Type checking
mypy src/autom8_asana/models/business/detection/

# Import validation
python -c "from autom8_asana.models.business.detection import *"

# Line count verification
wc -l src/autom8_asana/models/business/detection/*.py
```

### Exit Criteria

- [ ] All 22 `__all__` exports work from `autom8_asana.models.business.detection`
- [ ] All 5 private function imports work for tests
- [ ] All unit tests pass (1229 lines in test_detection.py)
- [ ] All pattern tests pass (345 lines in test_patterns.py)
- [ ] All integration tests pass (724 lines)
- [ ] mypy passes with no errors
- [ ] No module exceeds 250 lines
- [ ] No circular import errors
- [ ] Original `detection.py` is deleted

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| OQ-1: Should test imports be updated to use submodule paths? | Principal Engineer | Post-extraction | Decision deferred - tests work unchanged via re-exports |
| OQ-2: Should private functions be documented as "internal API"? | Architect | Post-extraction | Add note in `__init__.py` docstring |
| OQ-3: Should deprecation warnings be added for direct submodule imports? | Architect | Future sprint | Not needed if tests stay with top-level imports |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-19 | Architect (Claude) | Initial draft |
