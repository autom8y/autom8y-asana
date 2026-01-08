# TDD: Dynamic Schema-Driven Resolver Architecture

**TDD ID**: TDD-DYNAMIC-RESOLVER-001
**Version**: 1.0
**Date**: 2026-01-08
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: PRD-dynamic-resolver-architecture
**Sprint**: Dynamic Schema-Driven Resolver
**Task**: TASK-002

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Proposed Architecture](#proposed-architecture)
5. [Component Designs](#component-designs)
6. [Interface Contracts](#interface-contracts)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Non-Functional Considerations](#non-functional-considerations)
9. [Migration Strategy](#migration-strategy)
10. [Test Strategy](#test-strategy)
11. [Implementation Phases](#implementation-phases)
12. [Risk Assessment](#risk-assessment)
13. [ADRs](#adrs)
14. [Success Criteria](#success-criteria)

---

## Overview

This TDD specifies the technical design for replacing the per-entity resolution strategy pattern with a universal schema-driven resolver. The design enables dynamic entity discovery from existing registries, flexible lookup criteria using any schema column, and consistent multi-match support across all entity types.

### Solution Summary

| Component | Purpose |
|-----------|---------|
| `DynamicIndex` | Generic O(1) lookup index for any column combination |
| `DynamicIndexKey` | Composite key for versioned cache-friendly lookups |
| `DynamicIndexCache` | LRU-cached index instances per (entity_type, column_combo) |
| `EnhancedResolutionResult` | Multi-match result with backwards-compatible `gid` property |
| `UniversalResolutionStrategy` | Single strategy replacing per-entity strategies |
| `get_resolvable_entities()` | Dynamic entity discovery from SchemaRegistry + ProjectTypeRegistry |
| `validate_criterion_for_entity()` | Schema-aware criterion field validation |

### Traceability

| PRD Requirement | Component | Section |
|-----------------|-----------|---------|
| FR-001 Dynamic Entity Discovery | `get_resolvable_entities()` | 5.1 |
| FR-002 Schema-Aware Criterion Validation | `validate_criterion_for_entity()` | 5.2 |
| FR-003 DynamicIndex Multi-Column Support | `DynamicIndex`, `DynamicIndexKey` | 5.3 |
| FR-004 Multi-Match Response Structure | `EnhancedResolutionResult` | 5.4 |
| FR-005 UniversalResolutionStrategy | `UniversalResolutionStrategy` | 5.5 |
| FR-006 Backwards-Compatible Field Mapping | `LEGACY_FIELD_MAPPING` | 5.6 |
| NFR-001 Performance (<5ms p95) | `DynamicIndex` O(1) lookup | 8.1 |
| NFR-002 Memory Efficiency | `DynamicIndexCache` LRU eviction | 5.7 |

---

## Problem Statement

### Current State

The existing resolver architecture requires **4+ manual code changes** to add a new resolvable entity type:

1. Add entity to `SUPPORTED_ENTITY_TYPES` set in `api/routes/resolver.py:240`
2. Create strategy class in `services/resolver.py`
3. Register strategy in `RESOLUTION_STRATEGIES` dictionary
4. Update cache warmer priority list

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py`

```python
# Line 240: Hardcoded entity type set
SUPPORTED_ENTITY_TYPES = {"unit", "business", "offer", "contact"}
```

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py`

```python
# Lines 1461-1493: Manual strategy registration
def register_strategies() -> None:
    unit_strategy = UnitResolutionStrategy()
    RESOLUTION_STRATEGIES["unit"] = unit_strategy
    # ... more manual registrations
```

### Pain Points

| Pain Point | Current Impact |
|------------|----------------|
| Fixed lookup fields per entity | Unit: phone+vertical only; Contact: email/phone only |
| Single-GID response (except Contact) | Forces callers to handle ambiguity themselves |
| No self-documenting API | Clients must consult external docs for valid fields |
| Tribal knowledge for new entities | Slow onboarding, error-prone changes |

### Technical Debt

The current architecture duplicates information that already exists:

| Existing Registry | Information Available | Currently Unused By |
|-------------------|----------------------|---------------------|
| `SchemaRegistry` | Entity types with schemas | `SUPPORTED_ENTITY_TYPES` |
| `ProjectTypeRegistry` | Entity types with projects | `RESOLUTION_STRATEGIES` |
| `DataFrameSchema.columns` | Valid fields per entity | Criterion validation |

---

## Goals and Non-Goals

### Goals

| ID | Goal | Rationale |
|----|------|-----------|
| G1 | Zero-touch entity registration | Add schema + project = resolvable |
| G2 | Flexible lookup criteria | Any schema column usable |
| G3 | Consistent multi-match support | All entity types return `gids[]` |
| G4 | Self-documenting responses | `meta.available_fields` in every response |
| G5 | Backwards compatibility | Existing `gid` property preserved |
| G6 | O(1) lookup performance | Hash-based index for all column combos |
| G7 | Memory-bounded indexes | LRU eviction prevents unbounded growth |

### Non-Goals

| ID | Non-Goal | Reason |
|----|----------|--------|
| NG1 | Platform SDK extraction | Deferred to Phase 2 per SPIKE-platform-schema-lookup-abstraction |
| NG2 | Real-time schema reload | Startup discovery sufficient |
| NG3 | Cross-entity join resolution | Use navigation hydration for relationships |
| NG4 | Fuzzy matching | Deferred to FR-010 (Could Have) |
| NG5 | Resolution confidence scoring | Binary match/no-match sufficient |

---

## Proposed Architecture

### System Diagram

```
POST /v1/resolve/{entity_type}
         |
         v
+--------------------------------------------------+
|              get_resolvable_entities()            |
|        (SchemaRegistry + ProjectTypeRegistry)     |
+--------------------------------------------------+
         |
         v
+--------------------------------------------------+
|          validate_criterion_for_entity()          |
|               (Schema-aware validation)           |
+--------------------------------------------------+
         |
         v
+--------------------------------------------------+
|          UniversalResolutionStrategy              |
|                                                   |
|  +-------------+  +---------------------------+   |
|  |LegacyMapper |  | DynamicIndexCache        |   |
|  |(phone->     |  | (entity, cols) -> Index   |   |
|  | office_phone)|  +---------------------------+   |
|  +-------------+            |                     |
|                             v                     |
|                  +---------------------------+    |
|                  |      DynamicIndex         |    |
|                  | (O(1) hash-based lookup)  |    |
|                  +---------------------------+    |
+--------------------------------------------------+
         |
         v
+--------------------------------------------------+
|            EnhancedResolutionResult               |
|  { gids: [...], match_count: N, gid: first }     |
+--------------------------------------------------+
```

### Component Interaction Flow

```
                    ┌─────────────────┐
                    │  Resolution     │
                    │  Request        │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ SchemaRegistry  │ │ProjectTypeRegistry│ │ DataFrameCache │
│ (list_task_types│ │ (has_project)    │ │ (get DataFrame)│
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └──────────┬────────┘                   │
                    │                            │
                    ▼                            │
         ┌─────────────────────┐                │
         │get_resolvable_entities│               │
         │ (intersection)        │               │
         └──────────┬────────────┘               │
                    │                            │
                    ▼                            │
         ┌─────────────────────┐                │
         │validate_criterion_for│◀──────────────┘
         │_entity (schema cols) │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ UniversalResolution │
         │     Strategy        │
         └──────────┬──────────┘
                    │
          ┌─────────┼─────────┐
          │         │         │
          ▼         ▼         ▼
    ┌───────┐ ┌───────────┐ ┌──────────────┐
    │Legacy │ │ Dynamic   │ │ Enhanced     │
    │Mapper │ │ Index     │ │ Resolution   │
    │       │ │ Cache     │ │ Result       │
    └───────┘ └───────────┘ └──────────────┘
```

---

## Component Designs

### 5.1 Dynamic Entity Discovery

**Module**: `src/autom8_asana/services/resolver.py`

Replaces `SUPPORTED_ENTITY_TYPES` with runtime discovery.

```python
"""Dynamic entity discovery from existing registries.

Per TDD-DYNAMIC-RESOLVER-001 / FR-001:
Derives resolvable entities from SchemaRegistry + ProjectTypeRegistry.
Eliminates hardcoded SUPPORTED_ENTITY_TYPES.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.services.resolver import EntityProjectRegistry

logger = get_logger(__name__)


def get_resolvable_entities(
    schema_registry: "SchemaRegistry | None" = None,
    project_registry: "EntityProjectRegistry | None" = None,
) -> set[str]:
    """Derive resolvable entities from existing registries.

    An entity is resolvable if and only if:
    1. It has a schema registered in SchemaRegistry
    2. It has a project registered in EntityProjectRegistry

    Args:
        schema_registry: SchemaRegistry instance (uses singleton if None).
        project_registry: EntityProjectRegistry instance (uses singleton if None).

    Returns:
        Set of entity type strings that are resolvable.

    Example:
        >>> entities = get_resolvable_entities()
        >>> "unit" in entities
        True
        >>> "unknown" in entities
        False

    Note:
        Results are cached via @lru_cache. Call get_resolvable_entities.cache_clear()
        to refresh after runtime schema changes.
    """
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.services.resolver import EntityProjectRegistry

    if schema_registry is None:
        schema_registry = SchemaRegistry.get_instance()
    if project_registry is None:
        project_registry = EntityProjectRegistry.get_instance()

    resolvable = set()

    # Get all task types with schemas (excludes "*" base schema)
    for task_type in schema_registry.list_task_types():
        entity_type = task_type.lower()  # "Unit" -> "unit"

        # Check if entity has a registered project
        if project_registry.get_project_gid(entity_type) is not None:
            resolvable.add(entity_type)
            logger.debug(
                "entity_discovered_resolvable",
                extra={
                    "entity_type": entity_type,
                    "task_type": task_type,
                },
            )

    logger.info(
        "resolvable_entities_discovered",
        extra={
            "count": len(resolvable),
            "entities": sorted(resolvable),
        },
    )

    return resolvable


def is_entity_resolvable(entity_type: str) -> bool:
    """Check if a single entity type is resolvable.

    Args:
        entity_type: Entity type to check (e.g., "unit").

    Returns:
        True if entity has both schema and project registered.
    """
    return entity_type.lower() in get_resolvable_entities()
```

### 5.2 Schema-Aware Criterion Validation

**Module**: `src/autom8_asana/services/resolver.py`

Validates criterion fields against entity schema.

```python
"""Schema-aware criterion validation.

Per TDD-DYNAMIC-RESOLVER-001 / FR-002:
Validates criterion fields against DataFrameSchema columns.
Returns helpful error messages with available alternatives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autom8y_log import get_logger

logger = get_logger(__name__)


@dataclass
class CriterionValidationResult:
    """Result of criterion validation against schema.

    Attributes:
        is_valid: True if all criterion fields are valid schema columns.
        errors: List of validation error messages.
        unknown_fields: Fields in criterion not in schema.
        available_fields: All valid fields from schema.
        normalized_criterion: Criterion with legacy fields mapped to schema names.
    """
    is_valid: bool
    errors: list[str]
    unknown_fields: list[str]
    available_fields: list[str]
    normalized_criterion: dict[str, Any]


def validate_criterion_for_entity(
    entity_type: str,
    criterion: dict[str, Any],
) -> CriterionValidationResult:
    """Validate criterion fields against entity schema.

    Per FR-002: Schema-Aware Criterion Validation

    Validation rules:
    - Unknown field: Return error with available_fields list
    - Type mismatch: Coerce string to target type or error
    - Empty criteria: Valid (returns empty results)

    Also applies legacy field mapping (FR-006) before validation.

    Args:
        entity_type: Entity type identifier (e.g., "unit").
        criterion: Dictionary of field -> value lookup criteria.

    Returns:
        CriterionValidationResult with validation status and details.

    Example:
        >>> result = validate_criterion_for_entity(
        ...     "unit",
        ...     {"phone": "+15551234567", "vertical": "dental"}
        ... )
        >>> result.is_valid
        True
        >>> result.normalized_criterion
        {"office_phone": "+15551234567", "vertical": "dental"}
    """
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    # Apply legacy field mapping first
    normalized = _apply_legacy_mapping(entity_type, criterion)

    # Get schema for entity type
    schema_registry = SchemaRegistry.get_instance()
    schema_key = entity_type.title()  # "unit" -> "Unit"

    try:
        schema = schema_registry.get_schema(schema_key)
    except Exception:
        # Fall back to base schema if entity-specific not found
        schema = schema_registry.get_schema("*")

    # Get valid column names
    available_fields = schema.column_names()
    available_set = set(available_fields)

    # Check for unknown fields
    criterion_fields = set(normalized.keys())
    unknown_fields = list(criterion_fields - available_set)

    errors: list[str] = []

    if unknown_fields:
        errors.append(
            f"Unknown field(s) for {entity_type}: {unknown_fields}. "
            f"Valid fields: {sorted(available_fields)}"
        )

    # Type coercion validation
    for field, value in normalized.items():
        if field in available_set:
            column_def = schema.get_column(field)
            if column_def is not None:
                coercion_error = _validate_type(field, value, column_def.dtype)
                if coercion_error:
                    errors.append(coercion_error)

    return CriterionValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        unknown_fields=unknown_fields,
        available_fields=available_fields,
        normalized_criterion=normalized,
    )


def _apply_legacy_mapping(
    entity_type: str,
    criterion: dict[str, Any],
) -> dict[str, Any]:
    """Apply legacy field name mapping for backwards compatibility.

    Per FR-006: Backwards-Compatible Field Mapping

    Args:
        entity_type: Entity type for entity-specific mappings.
        criterion: Original criterion dict.

    Returns:
        New dict with legacy fields mapped to schema column names.
    """
    # Import here to avoid circular dependency
    from autom8_asana.services.resolver import LEGACY_FIELD_MAPPING

    # Get entity-specific mappings (fall back to empty dict)
    entity_mappings = LEGACY_FIELD_MAPPING.get(entity_type, {})

    # Also apply global mappings
    global_mappings = LEGACY_FIELD_MAPPING.get("*", {})

    # Entity-specific takes precedence over global
    combined = {**global_mappings, **entity_mappings}

    result = {}
    for field, value in criterion.items():
        # Map legacy field to schema column if mapping exists
        mapped_field = combined.get(field, field)
        result[mapped_field] = value

    return result


def _validate_type(field: str, value: Any, dtype: str) -> str | None:
    """Validate and coerce value to target dtype.

    Args:
        field: Field name for error messages.
        value: Value to validate.
        dtype: Target Polars dtype string.

    Returns:
        Error message if invalid, None if valid.
    """
    # String types accept anything (coerce to string)
    if dtype in ("Utf8", "String"):
        return None

    # Integer types
    if dtype in ("Int64", "Int32"):
        try:
            int(value)
            return None
        except (ValueError, TypeError):
            return f"Field '{field}' expects integer, got: {type(value).__name__}"

    # Float types
    if dtype in ("Float64", "Decimal"):
        try:
            float(value)
            return None
        except (ValueError, TypeError):
            return f"Field '{field}' expects number, got: {type(value).__name__}"

    # Boolean
    if dtype == "Boolean":
        if isinstance(value, bool):
            return None
        if isinstance(value, str) and value.lower() in ("true", "false", "1", "0"):
            return None
        return f"Field '{field}' expects boolean, got: {value}"

    # Default: accept (be permissive for unknown types)
    return None
```

### 5.3 DynamicIndex

**Module**: `src/autom8_asana/services/dynamic_index.py` (new file)

Generic O(1) lookup index for any column combination.

```python
"""Dynamic index for O(1) lookup on arbitrary column combinations.

Per TDD-DYNAMIC-RESOLVER-001 / FR-003:
Replaces hardcoded GidLookupIndex with generic multi-column support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)


@dataclass(frozen=True)
class DynamicIndexKey:
    """Composite key for any column combination.

    Per FR-003: Versioned key format for cache compatibility.

    Attributes:
        columns: Tuple of column names (sorted for consistency).
        values: Tuple of values in same order as columns.

    Example:
        >>> key = DynamicIndexKey(
        ...     columns=("office_phone", "vertical"),
        ...     values=("+15551234567", "dental"),
        ... )
        >>> key.cache_key
        'idx1:office_phone=+15551234567:vertical=dental'
    """
    columns: tuple[str, ...]
    values: tuple[str, ...]

    @property
    def cache_key(self) -> str:
        """Generate versioned cache key string.

        Format: 'idx1:col1=val1:col2=val2'

        The 'idx1' prefix enables future format versioning.
        Columns are always sorted to ensure consistent keys
        regardless of criterion field order.

        Returns:
            Versioned cache key string.
        """
        pairs = ":".join(
            f"{col}={val}"
            for col, val in zip(self.columns, self.values)
        )
        return f"idx1:{pairs}"

    @classmethod
    def from_criterion(
        cls,
        criterion: dict[str, Any],
        normalize: bool = True,
    ) -> DynamicIndexKey:
        """Create key from criterion dict.

        Args:
            criterion: Field -> value mapping.
            normalize: If True, lowercase string values for case-insensitive matching.

        Returns:
            DynamicIndexKey instance.
        """
        # Sort columns for consistent key generation
        sorted_columns = tuple(sorted(criterion.keys()))

        values = []
        for col in sorted_columns:
            value = criterion[col]
            if normalize and isinstance(value, str):
                value = value.lower()
            values.append(str(value))

        return cls(columns=sorted_columns, values=tuple(values))


@dataclass
class DynamicIndex:
    """Generic O(1) lookup index for any column combination.

    Per TDD-DYNAMIC-RESOLVER-001 / FR-003:
    - O(n) construction from DataFrame
    - O(1) hash-based lookup after construction
    - Supports multi-match (returns list of GIDs)
    - Column-combination agnostic

    Attributes:
        key_columns: Columns used for lookup key.
        value_column: Column containing GID values.
        created_at: Index creation timestamp.
        entry_count: Number of entries in index.

    Example:
        >>> index = DynamicIndex.from_dataframe(
        ...     df=unit_df,
        ...     key_columns=["office_phone", "vertical"],
        ...     value_column="gid",
        ... )
        >>>
        >>> gids = index.lookup({"office_phone": "+15551234567", "vertical": "dental"})
        >>> print(gids)  # ["1234567890123456"]
    """

    # Public attributes
    key_columns: tuple[str, ...]
    value_column: str
    created_at: datetime
    entry_count: int = field(init=False)

    # Internal lookup dict
    _lookup: dict[str, list[str]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.entry_count = len(self._lookup)

    def __len__(self) -> int:
        """Return number of unique keys in index."""
        return len(self._lookup)

    def lookup(self, criteria: dict[str, Any]) -> list[str]:
        """Return all matching GIDs for criteria.

        Args:
            criteria: Field -> value mapping to look up.

        Returns:
            List of matching GID strings (empty if no match).

        Example:
            >>> gids = index.lookup({"office_phone": "+15551234567"})
            >>> len(gids)
            1
        """
        key = DynamicIndexKey.from_criterion(criteria)
        return self._lookup.get(key.cache_key, [])

    def lookup_single(self, criteria: dict[str, Any]) -> str | None:
        """Return first matching GID (backwards-compatible single lookup).

        Args:
            criteria: Field -> value mapping.

        Returns:
            First matching GID or None.
        """
        gids = self.lookup(criteria)
        return gids[0] if gids else None

    def contains(self, criteria: dict[str, Any]) -> bool:
        """Check if criteria exists in index.

        Args:
            criteria: Field -> value mapping.

        Returns:
            True if at least one match exists.
        """
        key = DynamicIndexKey.from_criterion(criteria)
        return key.cache_key in self._lookup

    def available_columns(self) -> list[str]:
        """Return columns this index can look up.

        Returns:
            List of column names used in index key.
        """
        return list(self.key_columns)

    @classmethod
    def from_dataframe(
        cls,
        df: "pl.DataFrame",
        key_columns: list[str],
        value_column: str = "gid",
    ) -> DynamicIndex:
        """Build index from DataFrame.

        Per FR-003: O(n) scan of DataFrame on first access.

        Args:
            df: Polars DataFrame containing entity data.
            key_columns: Columns to use as lookup key.
            value_column: Column containing GID values.

        Returns:
            DynamicIndex instance with O(1) lookup capability.

        Raises:
            KeyError: If required columns are missing from DataFrame.

        Example:
            >>> index = DynamicIndex.from_dataframe(
            ...     df=pl.DataFrame({
            ...         "office_phone": ["+15551234567", "+15559876543"],
            ...         "vertical": ["dental", "medical"],
            ...         "gid": ["123", "456"],
            ...     }),
            ...     key_columns=["office_phone", "vertical"],
            ... )
        """
        # Validate columns exist
        all_columns = set(key_columns) | {value_column}
        missing = all_columns - set(df.columns)
        if missing:
            raise KeyError(f"Missing required columns: {missing}")

        # Sort key columns for consistent key generation
        sorted_key_columns = tuple(sorted(key_columns))

        # Build lookup dictionary
        from collections import defaultdict
        lookup: dict[str, list[str]] = defaultdict(list)

        # Filter out rows with null values in key or value columns
        valid_df = df.filter(
            df[value_column].is_not_null()
        )
        for col in key_columns:
            valid_df = valid_df.filter(valid_df[col].is_not_null())

        # Build index
        for row in valid_df.iter_rows(named=True):
            # Create key from row values
            key_values = tuple(
                str(row[col]).lower()
                for col in sorted_key_columns
            )
            key = DynamicIndexKey(
                columns=sorted_key_columns,
                values=key_values,
            )

            gid = str(row[value_column])
            lookup[key.cache_key].append(gid)

        index = cls(
            key_columns=sorted_key_columns,
            value_column=value_column,
            created_at=datetime.now(timezone.utc),
            _lookup=dict(lookup),
        )

        logger.info(
            "dynamic_index_built",
            extra={
                "key_columns": list(sorted_key_columns),
                "value_column": value_column,
                "entry_count": len(lookup),
                "row_count": len(valid_df),
            },
        )

        return index
```

### 5.4 EnhancedResolutionResult

**Module**: `src/autom8_asana/services/resolution_result.py` (new file)

Multi-match result with backwards compatibility.

```python
"""Enhanced resolution result supporting multi-match.

Per TDD-DYNAMIC-RESOLVER-001 / FR-004:
Returns all matching GIDs while preserving backwards-compatible `gid` property.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnhancedResolutionResult:
    """Rich resolution result supporting multi-match.

    Per FR-004: Multi-Match Response Structure

    Attributes:
        gids: All matching GIDs (plural).
        match_count: Explicit count of matches.
        match_context: Optional additional fields per match.
        error: Error code if resolution failed.

    Backwards Compatibility:
        The `gid` property returns the first match (or None),
        matching the current API contract. New clients should
        use `gids` for full match list.

    Example:
        >>> result = EnhancedResolutionResult(
        ...     gids=["123", "456"],
        ...     match_count=2,
        ... )
        >>> result.gid  # Backwards compatible
        "123"
        >>> result.is_unique
        False
        >>> result.is_multi_match
        True
    """

    gids: list[str] = field(default_factory=list)
    match_count: int = 0
    match_context: list[dict[str, Any]] | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        """Ensure match_count matches gids length."""
        if self.match_count == 0 and self.gids:
            self.match_count = len(self.gids)

    @property
    def gid(self) -> str | None:
        """Backwards-compatible single GID property.

        Returns first match or None. New code should use `gids` instead.

        Returns:
            First matching GID or None if no matches.
        """
        return self.gids[0] if self.gids else None

    @property
    def is_unique(self) -> bool:
        """True if exactly one match found.

        Returns:
            True if match_count == 1.
        """
        return self.match_count == 1

    @property
    def is_multi_match(self) -> bool:
        """True if multiple matches found.

        Returns:
            True if match_count > 1.
        """
        return self.match_count > 1

    @property
    def is_found(self) -> bool:
        """True if at least one match found.

        Returns:
            True if match_count > 0 and no error.
        """
        return self.match_count > 0 and self.error is None

    @classmethod
    def not_found(cls) -> EnhancedResolutionResult:
        """Factory for NOT_FOUND result.

        Returns:
            Result with empty gids and NOT_FOUND error.
        """
        return cls(gids=[], match_count=0, error="NOT_FOUND")

    @classmethod
    def error_result(cls, error_code: str) -> EnhancedResolutionResult:
        """Factory for error result.

        Args:
            error_code: Error code string.

        Returns:
            Result with specified error.
        """
        return cls(gids=[], match_count=0, error=error_code)

    @classmethod
    def from_gids(
        cls,
        gids: list[str],
        context: list[dict[str, Any]] | None = None,
    ) -> EnhancedResolutionResult:
        """Factory from list of GIDs.

        Args:
            gids: List of matching GID strings.
            context: Optional context data per match.

        Returns:
            Result with gids populated, NOT_FOUND if empty.
        """
        if not gids:
            return cls.not_found()

        return cls(
            gids=gids,
            match_count=len(gids),
            match_context=context,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response dict.

        Returns:
            Dict suitable for JSON serialization.
        """
        result: dict[str, Any] = {
            "gids": self.gids,
            "match_count": self.match_count,
            "gid": self.gid,  # Backwards compat
        }

        if self.error:
            result["error"] = self.error

        if self.match_context:
            result["context"] = self.match_context

        return result
```

### 5.5 UniversalResolutionStrategy

**Module**: `src/autom8_asana/services/resolver.py` (modification)

Single strategy class handling all entity types.

```python
"""Universal resolution strategy for all entity types.

Per TDD-DYNAMIC-RESOLVER-001 / FR-005:
Single strategy class replacing UnitResolutionStrategy, BusinessResolutionStrategy,
OfferResolutionStrategy, and ContactResolutionStrategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.services.dynamic_index import DynamicIndex

logger = get_logger(__name__)


@dataclass
class UniversalResolutionStrategy:
    """Schema-driven resolution for any entity type.

    Per FR-005: Replaces all per-entity strategies with a single
    universal strategy that derives lookup behavior from schemas.

    Attributes:
        index_cache: Reference to DynamicIndexCache for index management.

    Key Features:
        - Dynamic criterion validation against schema
        - Arbitrary column combination lookups
        - Consistent multi-match handling for all entities
        - Legacy field mapping for backwards compatibility
        - Integrates with existing DataFrameCache

    Example:
        >>> strategy = UniversalResolutionStrategy(
        ...     index_cache=DynamicIndexCache(),
        ... )
        >>>
        >>> results = await strategy.resolve(
        ...     entity_type="unit",
        ...     criteria=[{"phone": "+15551234567", "vertical": "dental"}],
        ...     project_gid="1234567890",
        ...     client=asana_client,
        ... )
    """

    index_cache: "DynamicIndexCache"

    async def resolve(
        self,
        entity_type: str,
        criteria: list[dict[str, Any]],
        project_gid: str,
        client: "AsanaClient",
    ) -> list["EnhancedResolutionResult"]:
        """Resolve criteria to entity GIDs.

        Per FR-005: Schema-driven resolution for any entity type.

        Resolution flow:
        1. Validate and normalize criteria against schema
        2. Get or build DynamicIndex for criterion columns
        3. Perform O(1) lookups for each criterion
        4. Return EnhancedResolutionResult with all matches

        Args:
            entity_type: Entity type (e.g., "unit", "contact").
            criteria: List of criterion dicts.
            project_gid: Target project GID.
            client: AsanaClient for DataFrame building.

        Returns:
            List of EnhancedResolutionResult in same order as input.
        """
        import time
        from autom8_asana.services.resolution_result import EnhancedResolutionResult

        start_time = time.monotonic()

        if not criteria:
            return []

        results: list[EnhancedResolutionResult] = []

        for criterion in criteria:
            # Validate criterion
            validation = validate_criterion_for_entity(entity_type, criterion)

            if not validation.is_valid:
                logger.warning(
                    "criterion_validation_failed",
                    extra={
                        "entity_type": entity_type,
                        "errors": validation.errors,
                    },
                )
                results.append(
                    EnhancedResolutionResult.error_result("INVALID_CRITERIA")
                )
                continue

            # Get normalized criterion (with legacy field mapping applied)
            normalized = validation.normalized_criterion

            # Determine key columns from criterion fields
            key_columns = sorted(normalized.keys())

            try:
                # Get or build index for this column combination
                index = await self._get_or_build_index(
                    entity_type=entity_type,
                    project_gid=project_gid,
                    key_columns=key_columns,
                    client=client,
                )

                if index is None:
                    results.append(
                        EnhancedResolutionResult.error_result("INDEX_UNAVAILABLE")
                    )
                    continue

                # Perform lookup
                gids = index.lookup(normalized)
                results.append(EnhancedResolutionResult.from_gids(gids))

            except Exception as e:
                logger.warning(
                    "resolution_lookup_failed",
                    extra={
                        "entity_type": entity_type,
                        "criterion": criterion,
                        "error": str(e),
                    },
                )
                results.append(
                    EnhancedResolutionResult.error_result("LOOKUP_ERROR")
                )

        # Log batch completion
        elapsed_ms = (time.monotonic() - start_time) * 1000
        resolved_count = sum(1 for r in results if r.is_found)
        multi_match_count = sum(1 for r in results if r.is_multi_match)

        logger.info(
            "universal_resolution_complete",
            extra={
                "entity_type": entity_type,
                "criteria_count": len(criteria),
                "resolved_count": resolved_count,
                "multi_match_count": multi_match_count,
                "duration_ms": round(elapsed_ms, 2),
                "project_gid": project_gid,
            },
        )

        return results

    async def _get_or_build_index(
        self,
        entity_type: str,
        project_gid: str,
        key_columns: list[str],
        client: "AsanaClient",
    ) -> "DynamicIndex | None":
        """Get index from cache or build from DataFrame.

        Args:
            entity_type: Entity type for DataFrame schema.
            project_gid: Project to fetch data from.
            key_columns: Columns for index key.
            client: AsanaClient for DataFrame building.

        Returns:
            DynamicIndex if available, None on failure.
        """
        from autom8_asana.services.dynamic_index import DynamicIndex

        # Try cache first
        index = self.index_cache.get(
            entity_type=entity_type,
            key_columns=key_columns,
        )

        if index is not None:
            return index

        # Cache miss - need to build index
        # Get DataFrame from DataFrameCache (via @dataframe_cache decorator)
        df = await self._get_dataframe(entity_type, project_gid, client)

        if df is None:
            return None

        # Build index
        try:
            index = DynamicIndex.from_dataframe(
                df=df,
                key_columns=key_columns,
                value_column="gid",
            )

            # Cache the index
            self.index_cache.put(
                entity_type=entity_type,
                key_columns=key_columns,
                index=index,
            )

            return index

        except KeyError as e:
            logger.error(
                "index_build_missing_columns",
                extra={
                    "entity_type": entity_type,
                    "key_columns": key_columns,
                    "error": str(e),
                },
            )
            return None

    async def _get_dataframe(
        self,
        entity_type: str,
        project_gid: str,
        client: "AsanaClient",
    ) -> Any:
        """Get DataFrame for entity type.

        Delegates to existing strategy's build method via DataFrameCache.

        Args:
            entity_type: Entity type.
            project_gid: Project GID.
            client: AsanaClient.

        Returns:
            Polars DataFrame or None.
        """
        # Import here to avoid circular imports
        from autom8_asana.cache.dataframe.factory import get_dataframe_cache_provider

        cache = get_dataframe_cache_provider()
        entry = await cache.get_async(project_gid, entity_type)

        if entry is not None:
            return entry.dataframe

        # Cache miss - trigger build via existing strategy
        # This maintains compatibility with @dataframe_cache decorator
        strategy = get_strategy(entity_type)
        if strategy is None:
            return None

        # Use strategy's resolve with empty criteria to trigger cache population
        # The @dataframe_cache decorator will build and cache the DataFrame
        await strategy.resolve([], project_gid, client)

        # Try cache again
        entry = await cache.get_async(project_gid, entity_type)
        return entry.dataframe if entry else None
```

### 5.6 Legacy Field Mapping

**Module**: `src/autom8_asana/services/resolver.py` (modification)

Backwards-compatible field name mapping.

```python
"""Legacy field mapping for backwards compatibility.

Per TDD-DYNAMIC-RESOLVER-001 / FR-006:
Maps legacy API field names to schema column names.
"""

# Global mappings applied to all entity types
# Entity-specific mappings override global

LEGACY_FIELD_MAPPING: dict[str, dict[str, str]] = {
    # Global mappings
    "*": {},

    # Unit-specific mappings
    "unit": {
        "phone": "office_phone",           # Legacy name -> schema column
    },

    # Business-specific mappings (same as Unit)
    "business": {
        "phone": "office_phone",
    },

    # Offer-specific mappings
    "offer": {
        "phone": "office_phone",
    },

    # Contact-specific mappings
    "contact": {
        "contact_email": "email",          # Alias for schema column
        "contact_phone": "phone",          # Alias for schema column
    },
}
```

### 5.7 DynamicIndexCache

**Module**: `src/autom8_asana/services/dynamic_index.py` (addition)

LRU cache for DynamicIndex instances.

```python
"""LRU cache for DynamicIndex instances.

Per TDD-DYNAMIC-RESOLVER-001 / NFR-002:
Memory-bounded cache with LRU eviction per (entity_type, column_combo).
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.services.dynamic_index import DynamicIndex

logger = get_logger(__name__)


@dataclass
class IndexCacheKey:
    """Cache key for DynamicIndex instances.

    Attributes:
        entity_type: Entity type (e.g., "unit").
        columns: Frozen set of column names (order-independent).
    """
    entity_type: str
    columns: frozenset[str]

    def __hash__(self) -> int:
        return hash((self.entity_type, self.columns))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IndexCacheKey):
            return NotImplemented
        return (
            self.entity_type == other.entity_type and
            self.columns == other.columns
        )


@dataclass
class DynamicIndexCache:
    """LRU cache for DynamicIndex instances.

    Per NFR-002: Memory Efficiency
    - Max indexes per entity: 5 (most common column combinations)
    - LRU eviction threshold: 10 indexes per entity type
    - Cache TTL for unused indexes: 1 hour

    Attributes:
        max_per_entity: Maximum indexes per entity type.
        ttl_seconds: Time-to-live for cached indexes.

    Example:
        >>> cache = DynamicIndexCache(max_per_entity=5)
        >>>
        >>> # Store index
        >>> cache.put("unit", ["office_phone", "vertical"], index)
        >>>
        >>> # Retrieve (moves to front of LRU)
        >>> index = cache.get("unit", ["office_phone", "vertical"])
    """

    max_per_entity: int = 5
    ttl_seconds: int = 3600  # 1 hour

    # Internal state
    _cache: OrderedDict[IndexCacheKey, tuple["DynamicIndex", datetime]] = field(
        default_factory=OrderedDict, init=False
    )
    _entity_counts: dict[str, int] = field(
        default_factory=dict, init=False
    )
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False
    )

    # Statistics
    _stats: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions_lru": 0,
            "evictions_ttl": 0,
        }

    def get(
        self,
        entity_type: str,
        key_columns: list[str],
    ) -> "DynamicIndex | None":
        """Get cached index for entity type and columns.

        Args:
            entity_type: Entity type identifier.
            key_columns: Columns the index was built for.

        Returns:
            DynamicIndex if cached and not stale, None otherwise.
        """
        key = IndexCacheKey(
            entity_type=entity_type,
            columns=frozenset(key_columns),
        )

        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            index, cached_at = self._cache[key]

            # Check TTL
            age = (datetime.now(timezone.utc) - cached_at).total_seconds()
            if age > self.ttl_seconds:
                self._evict_key(key)
                self._stats["evictions_ttl"] += 1
                self._stats["misses"] += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._stats["hits"] += 1

            return index

    def put(
        self,
        entity_type: str,
        key_columns: list[str],
        index: "DynamicIndex",
    ) -> None:
        """Store index in cache.

        Args:
            entity_type: Entity type identifier.
            key_columns: Columns the index was built for.
            index: DynamicIndex to cache.
        """
        key = IndexCacheKey(
            entity_type=entity_type,
            columns=frozenset(key_columns),
        )

        with self._lock:
            # Remove existing if present
            if key in self._cache:
                self._evict_key(key)

            # Check entity limit
            count = self._entity_counts.get(entity_type, 0)
            while count >= self.max_per_entity:
                self._evict_lru_for_entity(entity_type)
                count = self._entity_counts.get(entity_type, 0)

            # Add entry
            self._cache[key] = (index, datetime.now(timezone.utc))
            self._entity_counts[entity_type] = count + 1

            logger.debug(
                "index_cache_put",
                extra={
                    "entity_type": entity_type,
                    "columns": list(key_columns),
                    "entry_count": index.entry_count,
                },
            )

    def invalidate(
        self,
        entity_type: str | None = None,
        key_columns: list[str] | None = None,
    ) -> int:
        """Invalidate cached indexes.

        Args:
            entity_type: Specific entity type or None for all.
            key_columns: Specific columns or None for all of entity.

        Returns:
            Number of entries invalidated.
        """
        with self._lock:
            if entity_type is None:
                # Clear all
                count = len(self._cache)
                self._cache.clear()
                self._entity_counts.clear()
                return count

            if key_columns is not None:
                # Specific entry
                key = IndexCacheKey(
                    entity_type=entity_type,
                    columns=frozenset(key_columns),
                )
                if key in self._cache:
                    self._evict_key(key)
                    return 1
                return 0

            # All entries for entity type
            count = 0
            keys_to_remove = [
                k for k in self._cache
                if k.entity_type == entity_type
            ]
            for key in keys_to_remove:
                self._evict_key(key)
                count += 1
            return count

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            return {
                **self._stats,
                "total_entries": len(self._cache),
                "entity_types": len(self._entity_counts),
            }

    def _evict_key(self, key: IndexCacheKey) -> None:
        """Evict a specific key (internal, assumes lock held)."""
        if key in self._cache:
            del self._cache[key]
            self._entity_counts[key.entity_type] = max(
                0,
                self._entity_counts.get(key.entity_type, 1) - 1,
            )

    def _evict_lru_for_entity(self, entity_type: str) -> None:
        """Evict LRU entry for entity type (internal, assumes lock held)."""
        for key in self._cache:
            if key.entity_type == entity_type:
                self._evict_key(key)
                self._stats["evictions_lru"] += 1
                break
```

---

## Interface Contracts

### 6.1 Public API Changes

#### Request Schema (Enhanced)

```json
{
  "criteria": [
    {
      "<any_schema_column>": "<value>",
      "office_phone": "+15551234567",
      "vertical": "dental"
    }
  ],
  "context_fields": ["name", "modified_at"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `criteria` | `array[object]` | Yes | Lookup criteria (max 1000 items) |
| `criteria[*].<field>` | `string` | Varies | Any valid schema column |
| `context_fields` | `array[string]` | No | Additional fields to return (FR-008) |

#### Response Schema (Enhanced)

```json
{
  "results": [
    {
      "gids": ["1234567890123456"],
      "match_count": 1,
      "gid": "1234567890123456",
      "context": [
        {
          "gid": "1234567890123456",
          "name": "Acme Dental",
          "modified_at": "2026-01-07T10:30:00Z"
        }
      ]
    }
  ],
  "meta": {
    "entity_type": "unit",
    "project_gid": "1201081073731555",
    "resolved_count": 1,
    "unresolved_count": 0,
    "available_fields": ["gid", "name", "office_phone", "vertical", "mrr"],
    "criteria_schema": ["office_phone", "vertical"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `results[*].gids` | `array[string]` | All matching GIDs (NEW) |
| `results[*].match_count` | `integer` | Number of matches (NEW) |
| `results[*].gid` | `string\|null` | First match (backwards compat) |
| `results[*].context` | `array[object]` | Optional context per match (FR-008) |
| `meta.available_fields` | `array[string]` | Valid fields for entity (NEW) |
| `meta.criteria_schema` | `array[string]` | Fields used in request (NEW) |

#### Error Response (422 - Invalid Criterion)

```json
{
  "detail": "Invalid criterion field 'foo' for entity type 'unit'",
  "error_code": "INVALID_CRITERION_FIELD",
  "available_fields": ["gid", "name", "office_phone", "vertical", "mrr"]
}
```

### 6.2 DynamicIndex Public API

| Method | Signature | Returns | Complexity |
|--------|-----------|---------|------------|
| `from_dataframe` | `(df: DataFrame, key_columns: list[str], value_column: str = "gid") -> DynamicIndex` | DynamicIndex | O(n) |
| `lookup` | `(criteria: dict[str, Any]) -> list[str]` | List of GIDs | O(1) |
| `lookup_single` | `(criteria: dict[str, Any]) -> str \| None` | Single GID | O(1) |
| `contains` | `(criteria: dict[str, Any]) -> bool` | Existence check | O(1) |
| `available_columns` | `() -> list[str]` | Column names | O(1) |

### 6.3 DynamicIndexCache Public API

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `(entity_type: str, key_columns: list[str]) -> DynamicIndex \| None` | Get cached index |
| `put` | `(entity_type: str, key_columns: list[str], index: DynamicIndex) -> None` | Store index |
| `invalidate` | `(entity_type: str \| None, key_columns: list[str] \| None) -> int` | Invalidate entries |
| `get_stats` | `() -> dict[str, int]` | Cache statistics |

---

## Data Flow Diagrams

### 7.1 Entity Discovery Flow

```
                    ┌─────────────────┐
                    │   API Startup   │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ SchemaRegistry  │ │ProjectTypeRegistry│ │EntityProject    │
│ .list_task_types│ │ (discover)       │ │Registry.register│
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └──────────┬────────┘                   │
                    │                            │
                    ▼                            │
         ┌─────────────────────┐                │
         │get_resolvable_entities│◀──────────────┘
         │ returns: {"unit",    │
         │  "business", "offer",│
         │  "contact"}          │
         └─────────────────────┘
```

### 7.2 Resolution Flow (Cache Hit)

```
┌────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Request      │───▶│ validate_       │───▶│ Universal       │
│ {phone, vert}  │    │ criterion       │    │ Strategy        │
└────────────────┘    └─────────────────┘    └────────┬────────┘
                                                      │
                                          normalized criterion
                                                      │
                                                      ▼
                                          ┌─────────────────────┐
                                          │  DynamicIndexCache  │
                                          │  .get(unit, [phone, │
                                          │       vertical])    │
                                          └──────────┬──────────┘
                                                     │
                                              HIT    │
                                                     ▼
                                          ┌─────────────────────┐
                                          │   DynamicIndex      │
                                          │   .lookup(criteria) │
                                          └──────────┬──────────┘
                                                     │
                                              O(1)   │
                                                     ▼
                                          ┌─────────────────────┐
                                          │EnhancedResolution   │
                                          │Result {gids: [...]} │
                                          └─────────────────────┘
```

### 7.3 Resolution Flow (Cache Miss)

```
┌────────────────┐
│   Request      │
│ {name, email}  │  (new column combo)
└───────┬────────┘
        │
        ▼
┌─────────────────────┐
│  DynamicIndexCache  │
│  .get(contact,      │
│   [name, email])    │
└──────────┬──────────┘
           │ MISS
           ▼
┌─────────────────────┐
│  DataFrameCache     │
│  .get(contact)      │
└──────────┬──────────┘
           │ DataFrame
           ▼
┌─────────────────────┐
│  DynamicIndex       │
│  .from_dataframe(   │
│   df, [name,email]) │
└──────────┬──────────┘
           │ O(n) build
           ▼
┌─────────────────────┐
│  DynamicIndexCache  │
│  .put(contact,      │
│   [name,email], idx)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  index.lookup()     │
│  O(1)               │
└─────────────────────┘
```

---

## Non-Functional Considerations

### 8.1 Performance Targets

Per NFR-001:

| Metric | Target | Approach |
|--------|--------|----------|
| Single criterion lookup (index hit) | < 5ms p95 | O(1) hash lookup |
| Index construction (1,000 rows) | < 50ms | Single DataFrame scan |
| Index construction (100,000 rows) | < 500ms | Optimized iteration |
| Memory per index (1,000 entries) | < 1MB | String key storage only |

### 8.2 Memory Efficiency

Per NFR-002:

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Max indexes per entity | 5 | Most common column combos |
| LRU eviction threshold | 10 total | Prevent unbounded growth |
| Cache TTL for unused | 1 hour | Balance freshness vs. rebuild cost |

### 8.3 Backwards Compatibility

Per FR-006:

| Legacy Field | Schema Column | Entity Types |
|--------------|---------------|--------------|
| `phone` | `office_phone` | unit, business, offer |
| `vertical` | `vertical` | all |
| `offer_id` | `offer_id` | offer |
| `contact_email` | `email` | contact |
| `contact_phone` | `phone` | contact |

### 8.4 Observability

**Metrics**:

| Metric | Type | Labels |
|--------|------|--------|
| `dynamic_index_build_duration_seconds` | Histogram | entity_type, columns |
| `dynamic_index_lookup_duration_seconds` | Histogram | entity_type |
| `dynamic_index_cache_hits_total` | Counter | entity_type |
| `dynamic_index_cache_misses_total` | Counter | entity_type |
| `dynamic_index_cache_evictions_total` | Counter | entity_type, reason |

**Logging**:

| Event | Level | When |
|-------|-------|------|
| `entity_discovered_resolvable` | DEBUG | Entity passes eligibility |
| `resolvable_entities_discovered` | INFO | Discovery complete |
| `dynamic_index_built` | INFO | Index constructed |
| `index_cache_put` | DEBUG | Index cached |
| `criterion_validation_failed` | WARN | Invalid criterion |
| `index_build_missing_columns` | ERROR | Schema mismatch |

---

## Migration Strategy

### 9.1 Phased Migration

**Phase 1: Foundation (Week 1)**

- [ ] Create `DynamicIndexKey` and `DynamicIndex` classes
- [ ] Create `EnhancedResolutionResult` dataclass
- [ ] Create `DynamicIndexCache` with LRU eviction
- [ ] Add `get_resolvable_entities()` function
- [ ] Add `validate_criterion_for_entity()` function
- [ ] Unit tests for all new components

**Phase 2: Universal Strategy (Week 2)**

- [ ] Create `UniversalResolutionStrategy` class
- [ ] Integrate with existing `DataFrameCache`
- [ ] Migrate Unit resolution to use `UniversalResolutionStrategy`
- [ ] Add deprecation warnings to legacy `UnitResolutionStrategy`
- [ ] Integration tests for Unit via new strategy

**Phase 3: Complete Migration (Week 3)**

- [ ] Migrate Business, Offer, Contact to `UniversalResolutionStrategy`
- [ ] Remove `SUPPORTED_ENTITY_TYPES` constant
- [ ] Update API route to use `get_resolvable_entities()`
- [ ] Update response models for new fields
- [ ] Add `context_fields` support (FR-008)
- [ ] Remove deprecated per-entity strategy classes

### 9.2 Replacing SUPPORTED_ENTITY_TYPES

**Before** (`api/routes/resolver.py:240`):

```python
SUPPORTED_ENTITY_TYPES = {"unit", "business", "offer", "contact"}

# In endpoint:
if entity_type not in SUPPORTED_ENTITY_TYPES:
    raise HTTPException(status_code=404, ...)
```

**After**:

```python
# Dynamic discovery
def _get_supported_entity_types() -> set[str]:
    from autom8_asana.services.resolver import get_resolvable_entities
    return get_resolvable_entities()

# In endpoint:
if entity_type not in _get_supported_entity_types():
    raise HTTPException(
        status_code=404,
        detail={
            "error": "UNKNOWN_ENTITY_TYPE",
            "message": f"Unknown entity type: {entity_type}",
            "available_types": sorted(_get_supported_entity_types()),
        },
    )
```

### 9.3 Replacing Per-Entity Strategies

**Current strategy dispatch**:

```python
RESOLUTION_STRATEGIES: dict[str, ResolutionStrategy] = {}

def register_strategies() -> None:
    unit_strategy = UnitResolutionStrategy()
    RESOLUTION_STRATEGIES["unit"] = unit_strategy
    RESOLUTION_STRATEGIES["business"] = BusinessResolutionStrategy(unit_strategy)
    RESOLUTION_STRATEGIES["offer"] = OfferResolutionStrategy()
    RESOLUTION_STRATEGIES["contact"] = ContactResolutionStrategy()
```

**Migration path**:

```python
# Phase 2: Add universal strategy
_universal_strategy: UniversalResolutionStrategy | None = None

def get_strategy(entity_type: str) -> ResolutionStrategy | None:
    """Get resolution strategy for entity type.

    Migration: Returns UniversalResolutionStrategy for all entity types
    once migration is complete.
    """
    global _universal_strategy

    # After Phase 3: Use universal for everything
    if _universal_strategy is not None:
        if is_entity_resolvable(entity_type):
            return _universal_strategy
        return None

    # During migration: Fall back to legacy
    return RESOLUTION_STRATEGIES.get(entity_type)
```

---

## Test Strategy

### 10.1 Unit Tests

**Module**: `tests/unit/services/test_dynamic_index.py`

```python
"""Unit tests for DynamicIndex."""

import pytest
import polars as pl
from datetime import datetime, timezone

from autom8_asana.services.dynamic_index import (
    DynamicIndex,
    DynamicIndexKey,
    DynamicIndexCache,
)


class TestDynamicIndexKey:
    """Tests for DynamicIndexKey."""

    def test_cache_key_format(self):
        """Cache key has versioned format."""
        key = DynamicIndexKey(
            columns=("office_phone", "vertical"),
            values=("+15551234567", "dental"),
        )

        assert key.cache_key == "idx1:office_phone=+15551234567:vertical=dental"

    def test_cache_key_sorted_columns(self):
        """Cache key sorts columns for consistency."""
        key1 = DynamicIndexKey.from_criterion(
            {"vertical": "dental", "office_phone": "+15551234567"}
        )
        key2 = DynamicIndexKey.from_criterion(
            {"office_phone": "+15551234567", "vertical": "dental"}
        )

        assert key1.cache_key == key2.cache_key


class TestDynamicIndex:
    """Tests for DynamicIndex."""

    def test_from_dataframe_single_column(self):
        """Build index from single column."""
        df = pl.DataFrame({
            "email": ["a@test.com", "b@test.com"],
            "gid": ["123", "456"],
        })

        index = DynamicIndex.from_dataframe(df, ["email"])

        assert len(index) == 2
        assert index.lookup({"email": "a@test.com"}) == ["123"]

    def test_from_dataframe_multi_column(self):
        """Build index from multiple columns."""
        df = pl.DataFrame({
            "office_phone": ["+15551234567", "+15559876543"],
            "vertical": ["dental", "medical"],
            "gid": ["123", "456"],
        })

        index = DynamicIndex.from_dataframe(
            df, ["office_phone", "vertical"]
        )

        result = index.lookup({
            "office_phone": "+15551234567",
            "vertical": "dental",
        })

        assert result == ["123"]

    def test_multi_match_returns_all(self):
        """Multiple matches return all GIDs."""
        df = pl.DataFrame({
            "email": ["same@test.com", "same@test.com"],
            "gid": ["123", "456"],
        })

        index = DynamicIndex.from_dataframe(df, ["email"])
        result = index.lookup({"email": "same@test.com"})

        assert sorted(result) == ["123", "456"]

    def test_missing_columns_raises(self):
        """Missing columns raise KeyError."""
        df = pl.DataFrame({"gid": ["123"]})

        with pytest.raises(KeyError, match="Missing required columns"):
            DynamicIndex.from_dataframe(df, ["nonexistent"])


class TestDynamicIndexCache:
    """Tests for DynamicIndexCache."""

    def test_lru_eviction(self):
        """LRU eviction when at capacity."""
        cache = DynamicIndexCache(max_per_entity=2)

        # Add 3 indexes for same entity
        for i in range(3):
            index = self._make_index()
            cache.put("unit", [f"col{i}"], index)

        # First should be evicted
        assert cache.get("unit", ["col0"]) is None
        assert cache.get("unit", ["col1"]) is not None
        assert cache.get("unit", ["col2"]) is not None

    def _make_index(self) -> DynamicIndex:
        df = pl.DataFrame({"col": ["a"], "gid": ["123"]})
        return DynamicIndex.from_dataframe(df, ["col"])
```

**Module**: `tests/unit/services/test_resolution_result.py`

```python
"""Unit tests for EnhancedResolutionResult."""

import pytest
from autom8_asana.services.resolution_result import EnhancedResolutionResult


class TestEnhancedResolutionResult:
    """Tests for EnhancedResolutionResult."""

    def test_gid_property_backwards_compat(self):
        """gid property returns first match."""
        result = EnhancedResolutionResult(gids=["123", "456"])

        assert result.gid == "123"
        assert result.gids == ["123", "456"]

    def test_gid_property_empty(self):
        """gid property returns None when empty."""
        result = EnhancedResolutionResult(gids=[])

        assert result.gid is None

    def test_is_unique(self):
        """is_unique is True for single match."""
        single = EnhancedResolutionResult.from_gids(["123"])
        multi = EnhancedResolutionResult.from_gids(["123", "456"])

        assert single.is_unique is True
        assert multi.is_unique is False

    def test_not_found_factory(self):
        """not_found factory creates correct result."""
        result = EnhancedResolutionResult.not_found()

        assert result.gids == []
        assert result.match_count == 0
        assert result.error == "NOT_FOUND"
```

### 10.2 Integration Tests

**Module**: `tests/integration/services/test_universal_resolution.py`

```python
"""Integration tests for UniversalResolutionStrategy."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from autom8_asana.services.resolver import (
    UniversalResolutionStrategy,
    get_resolvable_entities,
    validate_criterion_for_entity,
)
from autom8_asana.services.dynamic_index import DynamicIndexCache


class TestUniversalResolution:
    """Integration tests for universal resolution."""

    @pytest.mark.asyncio
    async def test_resolve_unit_with_legacy_fields(self):
        """Resolves unit with legacy 'phone' field."""
        # Setup
        cache = DynamicIndexCache()
        strategy = UniversalResolutionStrategy(index_cache=cache)

        mock_client = AsyncMock()

        # Test
        results = await strategy.resolve(
            entity_type="unit",
            criteria=[{"phone": "+15551234567", "vertical": "dental"}],
            project_gid="test-project",
            client=mock_client,
        )

        # Legacy 'phone' should map to 'office_phone'
        # (Full test would mock DataFrameCache)
        assert len(results) == 1


class TestEntityDiscovery:
    """Integration tests for entity discovery."""

    def test_get_resolvable_entities_integration(self):
        """Discovery finds entities with both schema and project."""
        entities = get_resolvable_entities()

        # After startup, these should be discovered
        assert "unit" in entities
        assert "contact" in entities


class TestCriterionValidation:
    """Integration tests for criterion validation."""

    def test_validate_with_schema_columns(self):
        """Validation passes for valid schema columns."""
        result = validate_criterion_for_entity(
            "unit",
            {"office_phone": "+15551234567", "vertical": "dental"},
        )

        assert result.is_valid
        assert not result.errors

    def test_validate_with_legacy_mapping(self):
        """Legacy fields are mapped and validated."""
        result = validate_criterion_for_entity(
            "unit",
            {"phone": "+15551234567", "vertical": "dental"},
        )

        assert result.is_valid
        assert result.normalized_criterion["office_phone"] == "+15551234567"

    def test_validate_unknown_field(self):
        """Unknown fields produce helpful error."""
        result = validate_criterion_for_entity(
            "unit",
            {"unknown_field": "value"},
        )

        assert not result.is_valid
        assert "unknown_field" in result.unknown_fields
        assert "office_phone" in result.available_fields
```

### 10.3 Test Matrix

| Test Case | Entity | Input | Expected |
|-----------|--------|-------|----------|
| TC-001 | unit | phone+vertical | gids=[...], match_count>0 |
| TC-002 | unit | unknown field | 422, available_fields |
| TC-003 | contact | email | gids=[...] (multi-match) |
| TC-004 | offer | offer_id | gids=[...] |
| TC-005 | business | phone+vertical | gids=[...] via Unit |
| TC-006 | any | empty criteria | 200, empty results |
| TC-007 | unknown | any | 404, available_types |
| TC-008 | unit | schema column direct | gids=[...] |
| TC-009 | contact | legacy contact_email | gids=[...], maps to email |
| TC-010 | any | context_fields | gids+context |

---

## Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Foundation** | 5 days | DynamicIndex, DynamicIndexKey, DynamicIndexCache, EnhancedResolutionResult, get_resolvable_entities, validate_criterion_for_entity |
| **Phase 2: Universal Strategy** | 4 days | UniversalResolutionStrategy, Unit migration, deprecation warnings |
| **Phase 3: Complete Migration** | 3 days | Remaining entity migration, remove SUPPORTED_ENTITY_TYPES, context_fields support |
| **Phase 4: Cleanup** | 2 days | Remove deprecated strategies, documentation, QA |

**Total**: 14 days (2.5 weeks)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression | Low | High | Benchmark before/after; index caching matches current |
| Breaking existing clients | Low | High | Backwards-compatible response (preserve `gid` property) |
| Schema column explosion | Medium | Medium | LRU eviction; document common column combos |
| Index memory growth | Medium | Medium | Per-entity limits; TTL eviction |
| Discovery timing issues | Low | Medium | Fail-fast at startup if discovery incomplete |
| Legacy field mapping gaps | Medium | Low | Comprehensive mapping table; validation errors guide users |

---

## ADRs

### ADR-DYNAMIC-RESOLVER-001: Replace Per-Entity Strategies with Universal Strategy

**Context**: The current architecture requires 4+ code changes to add a new resolvable entity type, including creating a dedicated strategy class. This tribal knowledge slows onboarding and creates maintenance burden.

**Decision**: Replace `UnitResolutionStrategy`, `BusinessResolutionStrategy`, `OfferResolutionStrategy`, and `ContactResolutionStrategy` with a single `UniversalResolutionStrategy` that derives behavior from schemas.

**Consequences**:
- Positive: Zero-code entity registration (add schema + project = resolvable)
- Positive: Flexible lookup criteria (any schema column valid)
- Positive: Consistent multi-match across all entities
- Negative: Loss of entity-specific optimizations (can be added later if needed)
- Neutral: Migration requires backwards-compatible response format

### ADR-DYNAMIC-RESOLVER-002: Dynamic Entity Discovery via Existing Registries

**Context**: `SUPPORTED_ENTITY_TYPES` is hardcoded while `SchemaRegistry` and `EntityProjectRegistry` already contain the necessary information to determine resolvability.

**Decision**: Derive resolvable entities at runtime from the intersection of SchemaRegistry (has schema) and EntityProjectRegistry (has project).

**Consequences**:
- Positive: New entities automatically resolvable after schema + project registration
- Positive: Single source of truth for entity eligibility
- Negative: Discovery happens at startup; runtime changes require restart
- Neutral: Cached via `@lru_cache`; invalidation requires explicit call

### ADR-DYNAMIC-RESOLVER-003: DynamicIndex Column-Agnostic Design

**Context**: `GidLookupIndex` is hardcoded to `phone/vertical` pairs. Different entities need different lookup columns (Contact: email, Offer: offer_id).

**Decision**: Create generic `DynamicIndex` that accepts any column combination via `from_dataframe(df, key_columns)`.

**Consequences**:
- Positive: Same index pattern works for all entity types
- Positive: Users can query by any column combination
- Negative: Index per column combo may increase memory (mitigated by LRU cache)
- Neutral: O(n) index build on first access; O(1) thereafter

### ADR-DYNAMIC-RESOLVER-004: EnhancedResolutionResult Multi-Match Support

**Context**: Current API returns single `gid` for most entities but Contact can have multiple matches. This inconsistency creates client complexity.

**Decision**: All entity types return `gids: list[str]` with `match_count`. Preserve backwards-compatible `gid` property returning first match.

**Consequences**:
- Positive: Consistent multi-match handling across all entities
- Positive: Explicit `match_count` without array iteration
- Positive: Backwards compatible (existing `gid` consumers unaffected)
- Negative: Response payload slightly larger (acceptable)
- Neutral: Client migration optional

---

## Success Criteria

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| Single lookup latency | < 5ms p95 | Prometheus histogram |
| Index build (10K rows) | < 100ms | Build timing logs |
| Memory per index | < 2MB | Memory profiling |
| Code changes for new entity | 0 | Add schema + project = resolvable |
| Backwards compatibility | 100% | Existing test suite passes |

### Qualitative

| Criterion | Validation |
|-----------|------------|
| Zero-touch entity registration | Add schema + project, entity becomes resolvable |
| Self-documenting API | `meta.available_fields` in every response |
| Consistent multi-match | All entities return `gids[]` |
| Clean migration | Legacy strategies deprecated, removed |
| Comprehensive tests | Unit + integration coverage for all components |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD Document | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-dynamic-resolver-architecture.md` | Pending |
| PRD Reference | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-resolver-architecture.md` | Yes |
| Spike Reference | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-dynamic-resolver-architecture.md` | Yes |
| Spike Reference | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-platform-schema-lookup-abstraction.md` | Yes |

---

## Appendix A: File Structure

```
src/autom8_asana/
├── services/
│   ├── resolver.py                    # MODIFIED: Add UniversalResolutionStrategy,
│   │                                  #   get_resolvable_entities, legacy mappings
│   ├── dynamic_index.py               # NEW: DynamicIndex, DynamicIndexKey,
│   │                                  #   DynamicIndexCache
│   ├── resolution_result.py           # NEW: EnhancedResolutionResult
│   └── gid_lookup.py                  # UNCHANGED (deprecated Phase 3)
├── api/
│   └── routes/
│       └── resolver.py                # MODIFIED: Dynamic entity validation,
│                                      #   enhanced response format
```

## Appendix B: Existing Infrastructure Reference

| Component | Location | Usage in Design |
|-----------|----------|-----------------|
| `SchemaRegistry` | `dataframes/models/registry.py` | Entity schema lookup |
| `EntityProjectRegistry` | `services/resolver.py:102-243` | Project GID lookup |
| `DataFrameCache` | `cache/dataframe_cache.py` | DataFrame retrieval |
| `GidLookupIndex` | `services/gid_lookup.py` | Pattern for DynamicIndex |
| `@dataframe_cache` | `cache/dataframe/decorator.py` | DataFrame caching |
| `ResolutionStrategy` | `services/resolver.py:249-284` | Protocol definition |

## Appendix C: API Examples

### Current API (Preserved)

```bash
POST /v1/resolve/unit
{
  "criteria": [
    {"phone": "+15551234567", "vertical": "dental"}
  ]
}

Response:
{
  "results": [
    {"gid": "1234567890123456"}
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 0,
    "entity_type": "unit",
    "project_gid": "..."
  }
}
```

### Enhanced API (New Fields)

```bash
POST /v1/resolve/unit
{
  "criteria": [
    {"office_phone": "+15551234567", "vertical": "dental"}
  ],
  "context_fields": ["name"]
}

Response:
{
  "results": [
    {
      "gids": ["1234567890123456"],
      "match_count": 1,
      "gid": "1234567890123456",
      "context": [
        {"gid": "1234567890123456", "name": "Acme Dental"}
      ]
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 0,
    "entity_type": "unit",
    "project_gid": "...",
    "available_fields": ["gid", "name", "office_phone", "vertical", "mrr", "..."],
    "criteria_schema": ["office_phone", "vertical"]
  }
}
```

### Dynamic Entity Discovery

```bash
POST /v1/resolve/new_entity_type
# Returns 404 with dynamically generated list:
{
  "detail": {
    "error": "UNKNOWN_ENTITY_TYPE",
    "message": "Unknown entity type: new_entity_type",
    "available_types": ["unit", "business", "offer", "contact"]
  }
}
```

After adding schema + project registration:

```bash
POST /v1/resolve/new_entity_type
# Now works! Entity discovered automatically.
{
  "results": [...],
  "meta": {
    "entity_type": "new_entity_type",
    "available_fields": [...],
    ...
  }
}
```
