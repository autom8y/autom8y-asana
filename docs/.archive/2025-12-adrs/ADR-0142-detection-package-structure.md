# ADR-0142: Detection Package Structure

## Metadata
- **Status**: Proposed
- **Author**: Architect (Claude)
- **Date**: 2025-12-19
- **Deciders**: SDK Team
- **Related**: PRD-SPRINT-3-DETECTION, TDD-SPRINT-3-DETECTION-DECOMPOSITION, ADR-0094 (Detection Fallback Chain), ADR-0117 (Tier 2 Pattern Enhancement)

## Context

`detection.py` has grown to **1125 lines** containing 4 distinct concerns in a single file:

1. **Type definitions** (EntityType enum, DetectionResult dataclass, EntityTypeInfo) - ~170 lines
2. **Configuration data** (ENTITY_TYPE_INFO master dict, derived maps) - ~230 lines
3. **Detection logic** across 5 tiers (22 functions total) - ~600 lines
4. **Helper utilities** for holder identification and pattern matching - ~125 lines

This violates the Single Responsibility Principle and creates:
- Cognitive load: Engineers must navigate 1100+ lines to modify tier-specific logic
- Merge conflicts: Multiple engineers touching the same file
- Test coupling: 2300+ lines of tests import from one monolith module
- Onboarding friction: New team members must understand entire file to modify any part

The SDK has a **250-line soft limit** per module (per project conventions). `detection.py` exceeds this by 4.5x.

### Constraints

1. **Backward compatibility**: All 22 exported symbols must remain importable from `autom8_asana.models.business.detection`
2. **Test stability**: 2300+ lines of tests must pass unchanged
3. **No circular imports**: Python's import system requires strict layering
4. **Private function access**: 5 private functions are imported directly by tests

## Decision

We will convert `detection.py` from a **single file** to a **package directory** with 7 focused modules:

```
src/autom8_asana/models/business/
    detection/                    # Package (replaces detection.py)
        __init__.py               # Re-exports for backward compatibility (~50 lines)
        types.py                  # Types and constants (~170 lines)
        config.py                 # Configuration data (~230 lines)
        tier1.py                  # Project membership detection (~180 lines)
        tier2.py                  # Name pattern detection (~150 lines)
        tier3.py                  # Parent inference detection (~60 lines)
        tier4.py                  # Structure inspection detection (~80 lines)
        facade.py                 # Unified detection orchestration (~200 lines)
```

### Module Dependency Graph (Strict Layering)

```
                    +-----------+
                    |  types.py |  (no dependencies - pure types)
                    +-----------+
                          |
                    +-----------+
                    | config.py |  (imports types.py only)
                    +-----------+
                          |
          +---------------+---------------+
          |               |               |
    +-----------+   +-----------+   +-----------+
    | tier1.py  |   | tier2.py  |   | tier3.py  |
    +-----------+   +-----------+   +-----------+
          |               |               |
          |         +-----------+         |
          |         | tier4.py  |         |
          |         +-----------+         |
          |               |               |
          +---------------+---------------+
                          |
                    +-----------+
                    | facade.py |  (imports all tiers)
                    +-----------+
                          |
                    +-----------+
                    |__init__.py|  (re-exports all public symbols)
                    +-----------+
```

### Re-export Strategy

`__init__.py` will re-export all 22 symbols from `__all__` plus 5 private functions used by tests:

```python
# detection/__init__.py
from autom8_asana.models.business.detection.types import (
    EntityType, EntityTypeInfo, DetectionResult,
    CONFIDENCE_TIER_1, CONFIDENCE_TIER_2, CONFIDENCE_TIER_3,
    CONFIDENCE_TIER_4, CONFIDENCE_TIER_5,
)
from autom8_asana.models.business.detection.config import (
    ENTITY_TYPE_INFO, NAME_PATTERNS, HOLDER_NAME_MAP, PARENT_CHILD_MAP,
    get_holder_attr, entity_type_to_holder_attr,
)
# ... remaining imports ...

__all__ = [
    # All 22 original exports + 5 private functions for test compatibility
]
```

This ensures:
- `from autom8_asana.models.business.detection import EntityType` continues to work
- No changes required to any import statements in the codebase
- Python's package import system handles the file-to-directory migration transparently

## Rationale

### Why Package Over Single File?

| Criterion | Single File | Package |
|-----------|-------------|---------|
| **Cognitive load** | Must read 1100+ lines | Open only the relevant module |
| **Merge conflicts** | High probability | Low - separate files per concern |
| **Testing isolation** | All tests touch one module | Tier-specific tests possible |
| **Navigation** | Scroll to find functions | File name = function category |
| **Maintenance** | Any change touches 1 file | Changes scoped to concern |

The SDK already uses this pattern for:
- `autom8_asana/cache/` (multiple backends)
- `autom8_asana/batch/` (batch operations)
- `autom8_asana/persistence/` (SaveSession components)

### Why These Module Boundaries?

The boundaries follow the natural structure already present in the code:

1. **types.py**: Types have zero dependencies - pure definitions
2. **config.py**: Configuration depends only on types
3. **tier{1-4}.py**: Each tier is logically independent with distinct responsibilities:
   - Tier 1: Registry lookup (sync + async variants)
   - Tier 2: String pattern matching (word boundaries, stripping)
   - Tier 3: Parent-child inference (PARENT_CHILD_MAP)
   - Tier 4: Async structure inspection (API call)
4. **facade.py**: Orchestrates tiers - natural aggregation point

### Why Not Fine-Grained Modules?

Considered: Separate `helpers.py`, `tier5.py`, `enums.py`.

Rejected because:
- Tier 5 is 24 lines (single function) - not worth a separate file
- Helpers are tier-specific - live with their tier
- Enums/constants belong with types

## Alternatives Considered

### Alternative 1: Keep Single File with Regions

- **Description**: Add comment regions (`# region Tier 1`) for navigation
- **Pros**: No structural changes, zero risk
- **Cons**: Still violates SRP, merge conflicts persist, cognitive load unchanged
- **Why not chosen**: Symptoms persist; doesn't address root cause

### Alternative 2: Extract Types Only

- **Description**: Create `detection_types.py`, keep logic in `detection.py`
- **Pros**: Minimal change, addresses type-import convenience
- **Cons**: Main file still 950+ lines, SRP still violated
- **Why not chosen**: Incomplete solution; would need follow-up refactoring

### Alternative 3: One File Per Function

- **Description**: Create 22 files, one per function
- **Pros**: Maximum granularity, pure SRP
- **Cons**: Navigation overhead, excessive files, import complexity
- **Why not chosen**: Over-engineering; tier-based grouping more intuitive

## Consequences

### Positive

- **Improved maintainability**: Each module has single responsibility
- **Reduced cognitive load**: Engineers work with 60-230 line files, not 1125
- **Better code review**: Changes scoped to concern-specific files
- **Easier onboarding**: Module names indicate purpose
- **Test isolation opportunity**: Can test tiers independently (future work)
- **Merge conflict reduction**: Parallel work on different tiers possible

### Negative

- **More files**: 7 files instead of 1 (acceptable trade-off for clarity)
- **One-time migration effort**: Must extract carefully to preserve behavior
- **Slightly longer import chains**: Internal imports span files (mitigated by re-exports)

### Neutral

- **No API changes**: All existing imports continue to work
- **No behavior changes**: Pure structural refactoring
- **Test updates optional**: Tests can use new paths in follow-up work

## Compliance

How do we ensure this decision is followed?

1. **CI verification**: All tests must pass after each phase of extraction
2. **Import validation**: `python -c "from autom8_asana.models.business.detection import *"` succeeds
3. **Line count check**: `wc -l detection/*.py` shows all modules <250 lines
4. **mypy check**: `mypy src/autom8_asana/models/business/detection/` passes
5. **Circular import check**: Module imports without error on fresh Python session
