# TDD-PATTERNS-C: Holder Factory with `__init_subclass__`

> Technical Design Document for Initiative C of the Design Patterns Sprint

**Status**: Active
**PRD Reference**: PRD-PATTERNS-C
**Created**: 2025-12-16

---

## 1. Overview

This document specifies the technical design for the `HolderFactory` base class, which uses Python's `__init_subclass__` hook to enable declarative holder definitions. The pattern consolidates ~300 lines of duplicated code across 4 stub holders into a single reusable base class.

---

## 2. Design Goals

1. **Declarative Simplicity**: Define new holders in 3-5 lines
2. **Zero Duplication**: Eliminate copy-paste holder boilerplate
3. **Backward Compatibility**: Existing API unchanged
4. **Type Safety**: Preserve IDE support and type hints
5. **Runtime Flexibility**: Handle circular imports via deferred resolution

---

## 3. Component Design

### 3.1 HolderFactory Class

**Location**: `/src/autom8_asana/models/business/holder_factory.py`

```python
"""Holder factory base class using __init_subclass__ pattern.

Per TDD-PATTERNS-C: Declarative holder definitions with auto-configuration.
Per PRD-PATTERNS-C: Consolidates 4 near-identical holder implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import HolderMixin
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business


class HolderFactory(Task, HolderMixin[Task]):
    """Base class for holder tasks using __init_subclass__ pattern.

    Per TDD-PATTERNS-C: Automatically configures holder behavior based on
    class keyword arguments.

    Usage:
        class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
            '''Holder for DNA children.'''
            pass

    This generates:
    - CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR class vars
    - _children PrivateAttr (or custom attr name)
    - _business PrivateAttr
    - children property
    - business property
    - Optional semantic alias property
    - _populate_children method

    Class Arguments:
        child_type: Name of child class (e.g., "DNA", "Reconciliation")
        parent_ref: Name of parent reference attribute (e.g., "_dna_holder")
        children_attr: Name of children storage attribute (default: "_children")
        semantic_alias: Optional alias property for children (e.g., "reconciliations")
    """

    # ClassVars set by __init_subclass__
    CHILD_TYPE: ClassVar[type[Task]] = Task
    PARENT_REF_NAME: ClassVar[str] = ""
    CHILDREN_ATTR: ClassVar[str] = "_children"
    _CHILD_MODULE: ClassVar[str] = ""
    _CHILD_CLASS_NAME: ClassVar[str] = ""

    # Storage - inherited by all subclasses
    _children: list[Any] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    def __init_subclass__(
        cls,
        *,
        child_type: str | None = None,
        parent_ref: str | None = None,
        children_attr: str = "_children",
        semantic_alias: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Configure holder subclass automatically.

        Per FR-FACTORY-001: Accept keyword arguments in class definition.
        Per FR-FACTORY-002: Auto-generate ClassVars.

        Args:
            child_type: Name of child class (e.g., "DNA", "Reconciliation")
            parent_ref: Name of parent reference attribute (e.g., "_dna_holder")
            children_attr: Name of children storage attribute (default: "_children")
            semantic_alias: Optional alias property for children
            **kwargs: Passed to parent __init_subclass__
        """
        super().__init_subclass__(**kwargs)

        # Skip configuration for intermediate classes
        if child_type is None:
            return

        # Store configuration in ClassVars
        cls._CHILD_CLASS_NAME = child_type
        cls._CHILD_MODULE = f"autom8_asana.models.business.{child_type.lower()}"
        cls.PARENT_REF_NAME = parent_ref or f"_{child_type.lower()}_holder"
        cls.CHILDREN_ATTR = children_attr

        # Initially set CHILD_TYPE to Task (resolved at runtime)
        cls.CHILD_TYPE = Task

        # Generate semantic alias property if requested (FR-FACTORY-005)
        if semantic_alias and semantic_alias != "children":
            setattr(
                cls,
                semantic_alias,
                property(
                    lambda self: self.children,
                    doc=f"Alias for children with semantic name '{semantic_alias}'.",
                ),
            )

    @property
    def children(self) -> list[Any]:
        """All child entities.

        Per FR-FACTORY-005: Auto-generated property.

        Returns:
            List of typed child entities.
        """
        return getattr(self, self.CHILDREN_ATTR, [])

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business.

        Per FR-FACTORY-005: Auto-generated property.

        Returns:
            Business entity or None if not populated.
        """
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate children from fetched subtasks.

        Per FR-FACTORY-003: Generic implementation with dynamic import.
        Per FR-FACTORY-004: Deferred import to avoid circular dependencies.

        Algorithm:
        1. Dynamically import child class
        2. Sort subtasks by (created_at, name) for stability
        3. Convert to typed children
        4. Set bidirectional references
        5. Store in children attribute

        Args:
            subtasks: List of Task subtasks from API.
        """
        import importlib

        # Dynamic import to avoid circular imports (FR-FACTORY-004)
        module = importlib.import_module(self._CHILD_MODULE)
        child_class = getattr(module, self._CHILD_CLASS_NAME)

        # Update CHILD_TYPE for runtime type checking
        self.__class__.CHILD_TYPE = child_class

        # Sort by (created_at, name) for stability
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        # Build children list with bidirectional references
        children: list[Any] = []
        for task in sorted_tasks:
            child = child_class.model_validate(task.model_dump())

            # Set parent reference (holder -> child)
            setattr(child, self.PARENT_REF_NAME, self)

            # Propagate business reference
            child._business = self._business

            children.append(child)

        # Store in configured attribute
        setattr(self, self.CHILDREN_ATTR, children)
```

### 3.2 Migrated Holder Definitions

**Location**: `/src/autom8_asana/models/business/business.py` (replace existing classes)

```python
from autom8_asana.models.business.holder_factory import HolderFactory


class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
    """Holder task containing DNA children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per TDD-HARDENING-A/FR-STUB-004: Returns typed DNA children.
    """
    pass


class ReconciliationHolder(
    HolderFactory,
    child_type="Reconciliation",
    parent_ref="_reconciliation_holder",
    semantic_alias="reconciliations",
):
    """Holder task containing Reconciliation children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per TDD-HARDENING-A/FR-STUB-005: Returns typed Reconciliation children.
    """
    pass


class AssetEditHolder(
    HolderFactory,
    child_type="AssetEdit",
    parent_ref="_asset_edit_holder",
    children_attr="_asset_edits",
    semantic_alias="asset_edits",
):
    """Holder task containing AssetEdit children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per FR-PREREQ-002: Returns typed AssetEdit children.
    """
    pass


class VideographyHolder(
    HolderFactory,
    child_type="Videography",
    parent_ref="_videography_holder",
    semantic_alias="videography",
):
    """Holder task containing Videography children.

    Per TDD-PATTERNS-C: Migrated to HolderFactory pattern.
    Per TDD-HARDENING-A/FR-STUB-006: Returns typed Videography children.
    """
    pass


# Deprecation alias preserved (FR-FACTORY-006)
import warnings as _warnings


class ReconciliationsHolder(ReconciliationHolder):
    """Deprecated alias for ReconciliationHolder.

    .. deprecated::
        Use `ReconciliationHolder` instead. This alias will be removed
        in a future release.
    """

    def __init__(self, **kwargs: Any) -> None:
        _warnings.warn(
            "ReconciliationsHolder is deprecated, use ReconciliationHolder instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**kwargs)
```

---

## 4. Class Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Task                                    │
│  (from autom8_asana.models.task)                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ inherits
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      HolderMixin[T]                             │
│  (from autom8_asana.models.business.base)                      │
│                                                                 │
│  ClassVars:                                                     │
│    CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR, BUSINESS_REF_NAME│
│                                                                 │
│  Methods:                                                       │
│    _populate_children(subtasks)  [can be overridden]           │
│    _set_child_parent_ref(child)                                │
│    invalidate_cache()                                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ inherits (multiple)
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                     HolderFactory                               │
│  (NEW - from autom8_asana.models.business.holder_factory)      │
│                                                                 │
│  ClassVars (auto-configured):                                   │
│    _CHILD_MODULE, _CHILD_CLASS_NAME                            │
│                                                                 │
│  PrivateAttrs:                                                  │
│    _children: list[Any]                                         │
│    _business: Business | None                                   │
│                                                                 │
│  __init_subclass__(child_type, parent_ref, children_attr,      │
│                    semantic_alias)                              │
│                                                                 │
│  Properties:                                                    │
│    children -> list[Any]                                        │
│    business -> Business | None                                  │
│    [semantic_alias] -> list[Any]  (if configured)              │
│                                                                 │
│  Methods:                                                       │
│    _populate_children(subtasks)  [generic implementation]      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ inherits
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐  ┌─────────────────┐  ┌───────────────────┐
│   DNAHolder   │  │Reconciliation   │  │  AssetEditHolder  │
│               │  │    Holder       │  │                   │
│ child_type=   │  │ child_type=     │  │ child_type=       │
│   "DNA"       │  │  "Reconciliation"│ │  "AssetEdit"      │
│ parent_ref=   │  │ parent_ref=     │  │ parent_ref=       │
│ "_dna_holder" │  │ "_reconciliation│  │"_asset_edit_holder"│
│               │  │  _holder"       │  │ children_attr=    │
│               │  │ semantic_alias= │  │  "_asset_edits"   │
│               │  │ "reconciliations│  │ semantic_alias=   │
│               │  │               " │  │  "asset_edits"    │
└───────────────┘  └─────────────────┘  └───────────────────┘
                            │
                   ┌────────┴────────┐
                   ▼                 ▼
          ┌───────────────┐  ┌───────────────────┐
          │Videography    │  │ReconciliationsHolder│
          │    Holder     │  │  (deprecated alias) │
          │               │  └───────────────────┘
          │ child_type=   │
          │ "Videography" │
          │ parent_ref=   │
          │"_videography  │
          │    _holder"   │
          │semantic_alias=│
          │"videography"  │
          └───────────────┘
```

---

## 5. Sequence Diagram: `_populate_children` Flow

```
Business._fetch_holders_async           HolderFactory            importlib
         │                                    │                       │
         │ holder._populate_children(subtasks)│                       │
         │────────────────────────────────────>                       │
         │                                    │                       │
         │                                    │ import_module(        │
         │                                    │   _CHILD_MODULE)      │
         │                                    │───────────────────────>
         │                                    │                       │
         │                                    │<──────────────────────│
         │                                    │   module              │
         │                                    │                       │
         │                                    │ getattr(module,       │
         │                                    │   _CHILD_CLASS_NAME)  │
         │                                    │                       │
         │                                    │ for task in sorted:   │
         │                                    │   child = child_class.│
         │                                    │     model_validate()  │
         │                                    │   setattr(child,      │
         │                                    │     PARENT_REF_NAME,  │
         │                                    │     self)             │
         │                                    │   child._business =   │
         │                                    │     self._business    │
         │                                    │                       │
         │                                    │ setattr(self,         │
         │                                    │   CHILDREN_ATTR,      │
         │                                    │   children)           │
         │<───────────────────────────────────│                       │
         │                                    │                       │
```

---

## 6. Implementation Phases

### Phase 1: Create HolderFactory Base Class
**Files**: `src/autom8_asana/models/business/holder_factory.py`

1. Create new module with HolderFactory class
2. Implement `__init_subclass__` with all keyword arguments
3. Implement generic `_populate_children` with dynamic import
4. Implement `children` and `business` properties
5. Handle semantic alias generation

### Phase 2: Add Tests for HolderFactory
**Files**: `tests/unit/models/business/test_holder_factory.py`

1. Test `__init_subclass__` configuration
2. Test ClassVar auto-generation
3. Test `_populate_children` with mock data
4. Test semantic alias property generation
5. Test inheritance and Pydantic compatibility

### Phase 3: Migrate Stub Holders
**Files**: `src/autom8_asana/models/business/business.py`

1. Import HolderFactory
2. Replace DNAHolder class (remove ~65 lines, add 4 lines)
3. Replace ReconciliationHolder class (remove ~73 lines, add 8 lines)
4. Replace AssetEditHolder class (remove ~70 lines, add 9 lines)
5. Replace VideographyHolder class (remove ~73 lines, add 8 lines)
6. Keep ReconciliationsHolder deprecation alias

### Phase 4: Validation
**Commands**:
```bash
pytest tests/unit/models/business/
pytest tests/integration/
mypy src/autom8_asana/models/business/
```

---

## 7. Risk Mitigations

### Risk 1: Pydantic PrivateAttr Inheritance
**Concern**: Pydantic may not properly inherit PrivateAttr declarations.
**Mitigation**: Test explicitly that subclasses have `_children` and `_business` attrs available.
**Fallback**: Declare PrivateAttrs in each subclass if inheritance fails.

### Risk 2: Dynamic Import Module Resolution
**Concern**: Module path inference may fail for non-standard naming.
**Mitigation**: Use explicit module path if inference fails; log warnings on import failures.
**Implementation**:
```python
try:
    module = importlib.import_module(self._CHILD_MODULE)
except ImportError as e:
    logger.error(f"Failed to import {self._CHILD_MODULE}: {e}")
    raise
```

### Risk 3: Type Checker Limitations
**Concern**: mypy may not understand dynamic property generation.
**Mitigation**: Use `# type: ignore` sparingly; generate .pyi stubs if needed.
**Acceptance**: Type hints on base class properties provide most value.

---

## 8. Acceptance Criteria Mapping

| Requirement | Implementation | Test |
|-------------|---------------|------|
| FR-FACTORY-001 | `__init_subclass__` kwargs | `test_init_subclass_configuration` |
| FR-FACTORY-002 | ClassVar assignment in hook | `test_classvars_auto_generated` |
| FR-FACTORY-003 | `_populate_children` method | `test_populate_children_generic` |
| FR-FACTORY-004 | `importlib.import_module` | `test_dynamic_import_resolution` |
| FR-FACTORY-005 | Properties in base class | `test_children_property`, `test_semantic_alias` |
| FR-FACTORY-006 | Migration preserves API | Existing tests pass |

---

## 9. Code Reduction Analysis

### Before Migration (Current)

| Holder | Lines |
|--------|-------|
| DNAHolder | 64 |
| ReconciliationHolder | 73 |
| ReconciliationsHolder (deprecated) | 15 |
| AssetEditHolder | 70 |
| VideographyHolder | 73 |
| **Total** | **295** |

### After Migration

| Component | Lines |
|-----------|-------|
| HolderFactory base | ~90 |
| DNAHolder | 4 |
| ReconciliationHolder | 8 |
| ReconciliationsHolder (deprecated) | 15 |
| AssetEditHolder | 9 |
| VideographyHolder | 8 |
| **Total** | **134** |

**Net Reduction**: ~161 lines (55% reduction)

*Note: HolderFactory is reusable for future holders, so effective per-holder cost is 4-9 lines vs 65-73 lines.*

---

## 10. References

- **PRD**: PRD-PATTERNS-C
- **Related ADR**: ADR-0082 (Fields auto-generation pattern)
- **Similar Pattern**: BusinessEntity.__init_subclass__ (reference implementation)
- **HolderMixin**: `/src/autom8_asana/models/business/base.py`

---

*TDD-PATTERNS-C v1.0 | Design Patterns Sprint Initiative C*
