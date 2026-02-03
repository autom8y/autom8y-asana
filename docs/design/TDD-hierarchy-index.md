# TDD: HierarchyIndex + Cross-Entity Joins (Sprint 2, Part 1)

## Metadata

| Field | Value |
|-------|-------|
| **TDD ID** | TDD-hierarchy-index |
| **PRD** | PRD-dynamic-query-service |
| **Status** | Draft |
| **Created** | 2026-02-03 |
| **Author** | Architect |
| **Sprint** | 2 of 3 |
| **Scope** | HierarchyIndex for entity relationships, `join` parameter on `/rows` |
| **Depends On** | TDD-query-engine-foundation (Sprint 1, COMPLETE) |

---

## 1. System Context

### 1.1 What We Are Building

Two tightly related capabilities that enable cross-entity data enrichment:

1. **EntityHierarchy**: A DataFrame-level index that maps parent-child relationships between entity types (Business -> Unit, Business -> Contact, Unit -> Offer) using FK columns discovered from cached DataFrames. This is distinct from the existing `cache/hierarchy.py` `HierarchyIndex` which tracks task-level GID relationships for cascade field resolution.

2. **JoinSpec on /rows**: An optional `join` parameter on the existing `POST /v1/query/{entity_type}/rows` endpoint that enriches result rows with columns from a related entity type via hierarchy traversal.

### 1.2 Architectural Position

```
                +-----------------+
                |   API Gateway   |
                |  (S2S JWT Auth) |
                +--------+--------+
                         |
              POST /v1/query/{et}/rows
              {where, section, join: {entity_type, select}}
                         |
                         v
              +------------------------+
              |     QueryEngine        |
              | .execute_rows()        |
              |   |                    |
              |   +-- PredicateCompiler|
              |   +-- SectionIndex     |
              |   +-- EntityHierarchy  | <-- NEW
              |   +-- JoinExecutor     | <-- NEW
              +--------+---------------+
                       |
            +----------+------------------+
            |                             |
    EntityQueryService            EntityQueryService
    .get_dataframe(primary)       .get_dataframe(join_target)
            |                             |
    +-------+-------+            +--------+--------+
    | DataFrameCache |            | DataFrameCache  |
    | (e.g., offer)  |            | (e.g., business)|
    +----------------+            +-----------------+
```

### 1.3 Relationship to Existing HierarchyIndex

The existing `cache/hierarchy.py::HierarchyIndex` is a **task-level GID-to-GID** bidirectional tree used for cascade field resolution and cache invalidation. It operates on raw Asana task dicts with `parent.gid` fields, within a single project context.

The new `query/hierarchy.py::EntityHierarchy` is a **DataFrame-level entity-type-to-entity-type** relationship mapper. It discovers FK relationships by inspecting entity DataFrames and the Asana subtask hierarchy that connects different entity types. The two are complementary and do not overlap.

### 1.4 How Entity Relationships Work in This Codebase

The Asana domain model in this codebase uses a subtask hierarchy where Business tasks are parents, with Unit, Contact, and other entities as subtasks (children). Specifically:

| Parent Entity | Child Entity | Relationship Mechanism |
|---------------|-------------|----------------------|
| Business | Unit | Asana subtask hierarchy (Unit.parent.gid -> Business.gid) |
| Business | Contact | Asana subtask hierarchy (Contact.parent.gid -> Business.gid) |
| Unit | Offer | Asana subtask hierarchy (Offer.parent.gid -> Unit.gid) |
| Business | AssetEditHolder | Asana subtask hierarchy |
| AssetEditHolder | AssetEdit | Asana subtask hierarchy |

However, each entity type lives in its **own project** with its own DataFrame cache. The parent GIDs in the Asana hierarchy cross project boundaries. The cached DataFrames do not contain a `parent_gid` column -- instead, the cascade field extraction at build time follows the parent chain to resolve fields like `office_phone` and `vertical` that originate from ancestor entities.

**Key Discovery**: The DataFrames do not have explicit FK columns. The relationship information exists in the `cache/hierarchy.py::HierarchyIndex` which is populated at cache build time from the raw Asana task parent references. For Sprint 2 cross-entity joins, we must construct the relationship mapping by leveraging shared column values (e.g., `office_phone` appears in both Offer and Business schemas because it cascades from Business).

### 1.5 Revised Approach: Shared Column Matching

Given that no FK columns exist in the DataFrames, the cross-entity join must use **shared identifying columns** that cascade from parent to child. The most reliable shared identifier is `office_phone`, which cascades from Business to all descendant entity types.

For Sprint 2, we implement a simpler but effective approach:

1. The user specifies which entity type to join and which columns to select.
2. The system identifies a **join key** -- a column that exists in both the primary entity's DataFrame and the join target's DataFrame. The default join key is `office_phone` (the primary identifying cascade field).
3. The join is executed as a DataFrame left-join on the shared column.

This avoids needing to reconstruct the Asana subtask hierarchy at query time.

---

## 2. Architecture Decisions

### ADR-HI-001: Scope Expansion -- Cross-Entity Joins Now In-Scope

**Context**: The original PRD (PRD-dynamic-query-service, "Out of Scope" section) explicitly states: "Cross-entity joins: Queries operate on a single entity type per request. Join-like behavior (e.g., 'offers for businesses in vertical X') requires multiple API calls." Sprint 2 planning has since added cross-entity column enrichment as in-scope.

**Decision**: Add a limited `join` parameter to `/rows` that performs lookup-based column enrichment, NOT a full SQL-style join.

**Rationale**:
- The most common API consumer use case is "give me offers with their business's booking_type" -- this requires two API calls today.
- The enrichment model (append columns from a related entity) is dramatically simpler than a full join and avoids combinatorial explosion of result sets.
- The join is constrained to single-hop, single-target enrichment with explicit column selection. This is semantically closer to a SQL `LEFT JOIN ... ON ... SELECT specific_columns` than a general join.
- Performance impact is one additional DataFrame load per request, which is acceptable since DataFrames are cached in memory.

**Consequences**:
- The `/rows` endpoint gains optional join capability.
- The PRD "Out of Scope" section should be annotated with a reference to this ADR.
- Future sprints may extend join depth if needed, but Sprint 2 limits to depth=1.

### ADR-HI-002: Join Mechanism -- DataFrame Left-Join on Shared Column

**Context**: Two approaches for column enrichment: (A) lookup-based enrichment via an explicit hierarchy mapping, (B) DataFrame left-join on a shared identifying column.

**Options Considered**:
1. **Hierarchy-based lookup**: Build an EntityHierarchy from cached `HierarchyIndex` GID mappings, traverse parent chains at query time, perform per-row lookups into target DataFrame by GID. Requires access to the `HierarchyIndex` populated during cache build.
2. **Shared column join**: Identify a column present in both source and target DataFrames (cascaded during extraction), perform a Polars `join()` operation. No hierarchy traversal needed.
3. **GID-based join with parent_gid extraction**: Add a `parent_gid` column to DataFrames at build time, join on that. Requires schema changes.

**Decision**: Option 2 -- Shared column join with configurable join key.

**Rationale**:
- The cascade field extraction already copies identifying columns (like `office_phone`) from parent entities to child entities during DataFrame build. These columns are the natural join keys.
- A Polars `join()` is vectorized and operates in microseconds on in-memory DataFrames, whereas per-row GID lookups through a hierarchy would be O(n * depth).
- The `HierarchyIndex` in `cache/hierarchy.py` is populated during the DataFrame build lifecycle and is not readily accessible from the query path without coupling to the cache internals.
- Option 3 requires schema and extractor changes which are out of scope for Sprint 2.

**Consequences**:
- Join results depend on cascade field extraction correctness. If `office_phone` is null for a child entity, it will not match the parent.
- The join key must be explicitly specified or defaulted. For the initial release, `office_phone` is the default since it is the most universally cascaded identifier.
- More sophisticated GID-based joins can be added in a future sprint if needed.

### ADR-HI-003: EntityHierarchy Data Structure -- Static Relationship Registry

**Context**: How to model the relationships between entity types.

**Decision**: Use a static `ENTITY_RELATIONSHIPS` dict defining known entity type relationships with their default join keys.

**Rationale**:
- The entity type relationships in this codebase are fixed and known at development time (Business -> Unit -> Offer, Business -> Contact).
- A dynamic discovery mechanism adds complexity without value since entity types are registered in SchemaRegistry at initialization.
- A static registry makes relationships explicit and documentable.

**Consequences**:
- Adding a new entity type relationship requires a code change (adding to the dict). This is acceptable given the pace of entity type additions.
- The registry is trivially testable.

### ADR-HI-004: Module Location -- `query/hierarchy.py`

**Context**: Where to place the entity relationship registry and join execution logic.

**Decision**: New module `query/hierarchy.py` for the relationship registry, new module `query/join.py` for the JoinSpec model and join execution.

**Rationale**:
- Consistent with ADR-QE-001 which established `query/` as the package for query engine capabilities.
- Keeps the existing `cache/hierarchy.py` (task-level GID relationships) separate from entity-level relationships.
- `hierarchy.py` and `join.py` are separate files because the relationship registry is a static data structure while join execution has I/O and Polars operations.

**Consequences**:
- Two new files in the `query/` package.
- `query/__init__.py` updated to export new public API.

---

## 3. EntityHierarchy Design

### 3.1 Relationship Registry (`query/hierarchy.py`)

```python
"""Entity relationship registry for cross-entity joins.

Defines the known parent-child relationships between entity types
and their default join keys (shared columns used for matching).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityRelationship:
    """A directed relationship between two entity types.

    Attributes:
        parent_type: The parent entity type (e.g., "business").
        child_type: The child entity type (e.g., "offer").
        default_join_key: The column name present in both entity DataFrames
            that can be used to match rows (e.g., "office_phone").
        description: Human-readable description of the relationship.
    """

    parent_type: str
    child_type: str
    default_join_key: str
    description: str


# Known entity type relationships with their default join keys.
# These are derived from the Asana subtask hierarchy and cascade field
# extraction: parent fields cascade to children during DataFrame build.
ENTITY_RELATIONSHIPS: list[EntityRelationship] = [
    EntityRelationship(
        parent_type="business",
        child_type="unit",
        default_join_key="office_phone",
        description="Business is parent of Unit (office_phone cascades)",
    ),
    EntityRelationship(
        parent_type="business",
        child_type="contact",
        default_join_key="office_phone",
        description="Business is parent of Contact (office_phone cascades)",
    ),
    EntityRelationship(
        parent_type="business",
        child_type="offer",
        default_join_key="office_phone",
        description="Business is grandparent of Offer via Unit (office_phone cascades)",
    ),
    EntityRelationship(
        parent_type="unit",
        child_type="offer",
        default_join_key="office_phone",
        description="Unit is parent of Offer (office_phone cascades from Business)",
    ),
]


def find_relationship(
    source_type: str,
    target_type: str,
) -> EntityRelationship | None:
    """Find a relationship between two entity types.

    Searches for a direct relationship in either direction
    (source as parent or source as child of target).

    Args:
        source_type: The primary entity type being queried.
        target_type: The entity type to join with.

    Returns:
        EntityRelationship if found, None otherwise.
    """
    for rel in ENTITY_RELATIONSHIPS:
        if (rel.parent_type == source_type and rel.child_type == target_type) or \
           (rel.child_type == source_type and rel.parent_type == target_type):
            return rel
    return None


def get_join_key(
    source_type: str,
    target_type: str,
    explicit_key: str | None = None,
) -> str | None:
    """Determine the join key for two entity types.

    Args:
        source_type: The primary entity type.
        target_type: The join target entity type.
        explicit_key: User-specified join key (overrides default).

    Returns:
        Column name to join on, or None if no relationship exists.
    """
    if explicit_key is not None:
        return explicit_key

    rel = find_relationship(source_type, target_type)
    if rel is None:
        return None
    return rel.default_join_key


def get_joinable_types(source_type: str) -> list[str]:
    """Return entity types that can be joined with the source type.

    Args:
        source_type: The primary entity type.

    Returns:
        List of entity type names that have a relationship with source.
    """
    result: list[str] = []
    for rel in ENTITY_RELATIONSHIPS:
        if rel.parent_type == source_type:
            result.append(rel.child_type)
        elif rel.child_type == source_type:
            result.append(rel.parent_type)
    return sorted(set(result))
```

### 3.2 Estimated LOC

| Component | LOC |
|-----------|-----|
| `EntityRelationship` dataclass | ~15 |
| `ENTITY_RELATIONSHIPS` constant | ~25 |
| `find_relationship()` | ~15 |
| `get_join_key()` | ~12 |
| `get_joinable_types()` | ~12 |
| Module docstring + imports | ~10 |
| **Total** | **~89** |

---

## 4. JoinSpec and Join Execution Design

### 4.1 JoinSpec Pydantic Model (`query/join.py`)

```python
"""Cross-entity join models and execution for /rows enrichment.

Implements lookup-based column enrichment: given primary entity rows,
load a related entity DataFrame and append selected columns via
a shared column join.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator

from autom8_asana.query.errors import (
    JoinError,
    UnknownFieldError,
)
from autom8_asana.query.hierarchy import find_relationship, get_join_key

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema


class JoinSpec(BaseModel):
    """Specification for a cross-entity join on /rows.

    Example:
        {
            "entity_type": "business",
            "select": ["booking_type", "stripe_id"],
            "on": "office_phone"
        }
    """

    model_config = ConfigDict(extra="forbid")

    entity_type: str
    select: list[str] = Field(min_length=1, max_length=10)
    on: str | None = None  # Explicit join key; defaults to relationship default

    @field_validator("select")
    @classmethod
    def validate_select_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("select must contain at least one column")
        return v


# Guard: maximum join depth (hops through relationships)
MAX_JOIN_DEPTH: int = 1


@dataclass
class JoinResult:
    """Result of a join operation.

    Attributes:
        df: The enriched DataFrame with join columns appended.
        join_key: The column used for joining.
        matched_count: Number of primary rows that found a match.
        unmatched_count: Number of primary rows with no match (null join cols).
    """

    df: pl.DataFrame
    join_key: str
    matched_count: int
    unmatched_count: int
```

### 4.2 Join Execution

```python
def execute_join(
    primary_df: pl.DataFrame,
    target_df: pl.DataFrame,
    join_key: str,
    select_columns: list[str],
    target_entity_type: str,
) -> JoinResult:
    """Execute a left join to enrich primary rows with target columns.

    The join works as follows:
    1. Validate that join_key exists in both DataFrames.
    2. Select only join_key + requested columns from target DataFrame.
    3. Deduplicate target on join_key (take first occurrence).
    4. Left join primary onto deduplicated target.
    5. Return enriched DataFrame with matched/unmatched counts.

    Args:
        primary_df: The filtered primary entity DataFrame.
        target_df: The full target entity DataFrame.
        join_key: Column name present in both DataFrames.
        select_columns: Columns to select from target (will be prefixed).
        target_entity_type: For column name prefixing.

    Returns:
        JoinResult with enriched DataFrame.

    Raises:
        JoinError: If join_key missing from either DataFrame.
    """
    # 1. Validate join key exists in both DataFrames
    if join_key not in primary_df.columns:
        raise JoinError(
            f"Join key '{join_key}' not found in primary entity DataFrame. "
            f"Available: {sorted(primary_df.columns)}"
        )
    if join_key not in target_df.columns:
        raise JoinError(
            f"Join key '{join_key}' not found in target entity '{target_entity_type}' "
            f"DataFrame. Available: {sorted(target_df.columns)}"
        )

    # 2. Select join key + requested columns from target
    target_cols = [join_key] + [c for c in select_columns if c != join_key]
    available_target = set(target_df.columns)
    missing = [c for c in select_columns if c not in available_target]
    if missing:
        raise JoinError(
            f"Columns {missing} not found in target entity '{target_entity_type}'. "
            f"Available: {sorted(available_target)}"
        )

    target_subset = target_df.select(target_cols)

    # 3. Deduplicate target on join key (take first match)
    # Multiple target rows may share the same join key value.
    # We take the first occurrence to avoid row multiplication.
    target_deduped = target_subset.unique(subset=[join_key], keep="first")

    # 4. Filter out null join keys (they can never match)
    target_deduped = target_deduped.filter(pl.col(join_key).is_not_null())
    primary_non_null = primary_df.filter(pl.col(join_key).is_not_null())

    # 5. Rename target columns to avoid collision (prefix with entity type)
    rename_map = {
        col: f"{target_entity_type}_{col}"
        for col in select_columns
        if col != join_key
    }
    target_renamed = target_deduped.rename(rename_map)
    renamed_cols = list(rename_map.values())

    # 6. Left join
    enriched = primary_df.join(
        target_renamed,
        on=join_key,
        how="left",
    )

    # 7. Compute match statistics
    if renamed_cols:
        first_join_col = renamed_cols[0]
        matched_count = enriched.filter(
            pl.col(first_join_col).is_not_null()
        ).height
    else:
        matched_count = enriched.height

    unmatched_count = enriched.height - matched_count

    return JoinResult(
        df=enriched,
        join_key=join_key,
        matched_count=matched_count,
        unmatched_count=unmatched_count,
    )
```

### 4.3 Estimated LOC

| Component | LOC |
|-----------|-----|
| `JoinSpec` model | ~25 |
| `JoinResult` dataclass | ~15 |
| `MAX_JOIN_DEPTH` constant | ~2 |
| `execute_join()` function | ~70 |
| Module docstring + imports | ~15 |
| **Total** | **~127** |

---

## 5. Integration with Existing QueryEngine

### 5.1 RowsRequest Model Extension

Add `join` field to the existing `RowsRequest` in `query/models.py`:

```python
class RowsRequest(BaseModel):
    """POST /v1/query/{entity_type}/rows request body."""

    model_config = ConfigDict(extra="forbid")

    where: PredicateNode | None = None
    section: str | None = None
    select: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    order_by: str | None = None
    order_dir: Literal["asc", "desc"] = "asc"
    join: JoinSpec | None = None  # NEW: cross-entity join specification
```

### 5.2 RowsMeta Extension

Add join metadata to `RowsMeta`:

```python
class RowsMeta(BaseModel):
    """Response metadata for /rows endpoint."""

    model_config = ConfigDict(extra="forbid")

    total_count: int
    returned_count: int
    limit: int
    offset: int
    entity_type: str
    project_gid: str
    query_ms: float
    join_entity: str | None = None       # NEW
    join_key: str | None = None          # NEW
    join_matched: int | None = None      # NEW
    join_unmatched: int | None = None    # NEW
```

### 5.3 QueryEngine.execute_rows() Extension

The `execute_rows` method in `query/engine.py` is extended with join processing after the primary filter and before pagination:

```python
async def execute_rows(
    self,
    entity_type: str,
    project_gid: str,
    client: AsanaClient,
    request: RowsRequest,
    section_index: SectionIndex | None = None,
) -> RowsResponse:
    """Execute a /rows query with optional join enrichment."""
    start = time.monotonic()

    # Steps 1-7: Existing flow (depth guard, section, load DF, compile, filter)
    # ... (unchanged) ...

    # NEW: Step 7.5 -- Join enrichment (after filter, before pagination)
    join_meta: dict[str, Any] = {}
    if request.join is not None:
        from autom8_asana.query.hierarchy import find_relationship, get_join_key
        from autom8_asana.query.join import execute_join, JoinError

        # Validate relationship exists
        rel = find_relationship(entity_type, request.join.entity_type)
        if rel is None:
            from autom8_asana.query.errors import JoinError as JoinErrorType
            raise JoinErrorType(
                f"No relationship between '{entity_type}' and "
                f"'{request.join.entity_type}'. "
                f"Joinable types: {get_joinable_types(entity_type)}"
            )

        # Validate join target columns against target schema
        target_schema = registry.get_schema(
            to_pascal_case(request.join.entity_type)
        )
        for col_name in request.join.select:
            if target_schema.get_column(col_name) is None:
                raise UnknownFieldError(
                    field=col_name,
                    available=target_schema.column_names(),
                )

        # Determine join key
        join_key = get_join_key(
            entity_type,
            request.join.entity_type,
            request.join.on,
        )

        # Load target entity DataFrame
        target_project_gid = (
            EntityProjectRegistry.get_instance()
            .get_project_gid(request.join.entity_type)
        )
        if target_project_gid is None:
            raise JoinError(
                f"No project configured for join target: "
                f"{request.join.entity_type}"
            )

        target_df = await self.query_service.get_dataframe(
            request.join.entity_type,
            target_project_gid,
            client,
        )

        # Execute join
        join_result = execute_join(
            primary_df=df,
            target_df=target_df,
            join_key=join_key,
            select_columns=request.join.select,
            target_entity_type=request.join.entity_type,
        )
        df = join_result.df
        join_meta = {
            "join_entity": request.join.entity_type,
            "join_key": join_result.join_key,
            "join_matched": join_result.matched_count,
            "join_unmatched": join_result.unmatched_count,
        }

    # Steps 8-12: Existing flow (total_count, pagination, select, response)
    # Total count is computed on the (possibly enriched) DataFrame
    total_count = len(df)
    # ... (rest unchanged, but RowsMeta now includes join_meta fields) ...
```

### 5.4 Sequence Diagram: /rows with Join

```
Client                Route Handler           QueryEngine            EntityQueryService
  |                       |                       |                       |
  |  POST /rows           |                       |                       |
  |  {where, join: {...}} |                       |                       |
  |---------------------->|                       |                       |
  |                       |-- execute_rows ------>|                       |
  |                       |                       |-- get_dataframe ------>|
  |                       |                       |   (primary: offer)     |
  |                       |                       |<-- offer DataFrame ----|
  |                       |                       |                       |
  |                       |                       |-- compile predicate    |
  |                       |                       |-- filter primary DF    |
  |                       |                       |                       |
  |                       |                       |-- find_relationship    |
  |                       |                       |   (offer -> business)  |
  |                       |                       |                       |
  |                       |                       |-- get_dataframe ------>|
  |                       |                       |   (target: business)   |
  |                       |                       |<-- business DataFrame -|
  |                       |                       |                       |
  |                       |                       |-- execute_join         |
  |                       |                       |   left join on         |
  |                       |                       |   office_phone         |
  |                       |                       |                       |
  |                       |                       |-- paginate + select    |
  |                       |                       |                       |
  |                       |<-- RowsResponse ------|                       |
  |<-- 200 JSON ----------|                       |                       |
```

---

## 6. Error Handling

### 6.1 New Error Type

Add `JoinError` to `query/errors.py`:

```python
@dataclass
class JoinError(QueryEngineError):
    """Cross-entity join failed."""

    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "JOIN_ERROR",
            "message": self.message,
        }
```

### 6.2 Error to HTTP Status Mapping

| Error | HTTP Status | Condition |
|-------|:-----------:|-----------|
| `JoinError` (no relationship) | 422 | Entity types have no known relationship |
| `JoinError` (missing join key) | 422 | Join key column not found in DataFrame |
| `JoinError` (missing columns) | 422 | Requested select columns not in target schema |
| `JoinError` (no project) | 503 | Target entity project not configured |
| `UnknownFieldError` | 422 | Join select column not in target schema |

---

## 7. Module Structure

### 7.1 New Files

| File | Purpose | LOC Estimate |
|------|---------|:-----------:|
| `query/hierarchy.py` | Entity relationship registry | ~89 |
| `query/join.py` | JoinSpec model + join execution | ~127 |
| `tests/unit/query/test_hierarchy.py` | Relationship registry tests | ~80 |
| `tests/unit/query/test_join.py` | Join execution tests | ~200 |

### 7.2 Modified Files

| File | Changes | LOC Delta |
|------|---------|:---------:|
| `query/models.py` | Add `join: JoinSpec \| None` to `RowsRequest`, add join fields to `RowsMeta` | +10 |
| `query/engine.py` | Add join processing block in `execute_rows()` | +45 |
| `query/errors.py` | Add `JoinError` dataclass | +15 |
| `query/__init__.py` | Export new public API | +8 |
| `api/routes/query_v2.py` | Handle `JoinError` in error mapping | +3 |

### 7.3 Total Estimated LOC

| Category | LOC |
|----------|:---:|
| New implementation files | ~216 |
| Modified implementation files | ~81 |
| New test files | ~280 |
| **Grand Total** | **~577** |

---

## 8. Data Flow: Join Column Naming

Join columns from the target entity are prefixed with the target entity type to avoid name collisions. For example, joining offer with business selecting `booking_type`:

**Request**:
```json
{
    "where": [{"field": "section", "op": "eq", "value": "Active"}],
    "select": ["gid", "name", "office_phone"],
    "join": {
        "entity_type": "business",
        "select": ["booking_type", "company_id"]
    }
}
```

**Response row**:
```json
{
    "gid": "offer-123",
    "name": "Acme Dental Offer",
    "office_phone": "+15551234567",
    "business_booking_type": "Online",
    "business_company_id": "CMP-001"
}
```

The prefix convention is `{target_entity_type}_{column_name}`. This is deterministic and avoids ambiguity when the same column name exists in both schemas (e.g., `name` exists in both Offer and Business).

---

## 9. Design Constraints

1. **Additive to Sprint 1**: No modifications to existing compiler, predicate models, or guards. The `join` field is `Optional[JoinSpec]` on `RowsRequest`.
2. **Reuses SchemaRegistry**: Join target column validation uses the same `SchemaRegistry.get_schema()` path.
3. **Reuses EntityQueryService.get_dataframe()**: Join target DataFrame is loaded through the same cache lifecycle as the primary entity.
4. **Join results are not paginated separately**: The join enriches primary rows; pagination applies to the enriched result.
5. **Performance**: One additional DataFrame load per request when `join` is specified. Both DataFrames are memory-cached; the Polars join is vectorized.
6. **MAX_JOIN_DEPTH=1**: Only single-hop joins are supported in Sprint 2.

---

## 10. Test Plan

### 10.1 Unit Tests: EntityHierarchy (`tests/unit/query/test_hierarchy.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-H001 | `find_relationship("offer", "business")` | Returns the offer-business relationship |
| TC-H002 | `find_relationship("business", "offer")` | Returns the same relationship (bidirectional lookup) |
| TC-H003 | `find_relationship("offer", "contact")` | Returns None (no direct relationship) |
| TC-H004 | `get_join_key("offer", "business")` | Returns `"office_phone"` (default) |
| TC-H005 | `get_join_key("offer", "business", "name")` | Returns `"name"` (explicit override) |
| TC-H006 | `get_join_key("offer", "contact")` | Returns None (no relationship) |
| TC-H007 | `get_joinable_types("offer")` | Returns `["business", "unit"]` |
| TC-H008 | `get_joinable_types("business")` | Returns `["contact", "offer", "unit"]` |
| TC-H009 | `get_joinable_types("asset_edit")` | Returns `[]` (no relationships defined) |

### 10.2 Unit Tests: JoinSpec Model (`tests/unit/query/test_join.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-J001 | Valid JoinSpec parsing | Parses successfully |
| TC-J002 | JoinSpec with explicit `on` key | `on` field populated |
| TC-J003 | JoinSpec with empty select | Pydantic validation error |
| TC-J004 | JoinSpec with >10 select columns | Pydantic validation error |
| TC-J005 | JoinSpec with extra fields | Rejected (extra="forbid") |

### 10.3 Unit Tests: Join Execution (`tests/unit/query/test_join.py`)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-JE001 | Basic left join on shared column | Enriched DF with target columns prefixed |
| TC-JE002 | Join with null join key values | Null rows get null join columns |
| TC-JE003 | Join with no matches | All join columns are null, unmatched_count = row_count |
| TC-JE004 | Join with all matches | matched_count = row_count |
| TC-JE005 | Join key missing from primary DF | JoinError raised |
| TC-JE006 | Join key missing from target DF | JoinError raised |
| TC-JE007 | Select column missing from target DF | JoinError raised |
| TC-JE008 | Target has duplicate join key values | Deduplication takes first row |
| TC-JE009 | Column name collision avoided by prefix | Target columns prefixed with entity type |
| TC-JE010 | Empty primary DataFrame | Returns empty enriched DF |
| TC-JE011 | Empty target DataFrame | All join columns are null |

### 10.4 Integration Tests: /rows with Join (`tests/unit/query/test_engine.py` additions)

| ID | Test Case | Expected |
|----|-----------|----------|
| TC-EJ001 | /rows with valid join spec | 200, response includes prefixed join columns |
| TC-EJ002 | /rows with join + predicate filter | 200, filter applied before join |
| TC-EJ003 | /rows with join to unknown entity type | 422 JOIN_ERROR |
| TC-EJ004 | /rows with join to unrelated entity type | 422 JOIN_ERROR with joinable types |
| TC-EJ005 | /rows with join selecting invalid column | 422 UNKNOWN_FIELD |
| TC-EJ006 | /rows with join, target cache not warm | 503 CACHE_NOT_WARMED |
| TC-EJ007 | /rows with join meta in response | join_entity, join_key, join_matched in meta |
| TC-EJ008 | /rows without join (backward compat) | 200, identical to Sprint 1 behavior |
| TC-EJ009 | /rows with join and explicit `on` key | Join uses specified key |
| TC-EJ010 | /rows with join + section scoping | Section filter applied to primary, join still works |

---

## 11. Performance Considerations

### 11.1 Latency Impact of Join

| Step | Expected Time | Notes |
|------|:------------:|-------|
| Existing /rows flow | ~19ms | Per Sprint 1 analysis |
| Load target DataFrame | ~0.5ms | Memory-tier cache hit |
| Polars left join | ~1-5ms | Vectorized, in-memory |
| Column rename + select | ~0.1ms | Metadata-only operation |
| **Total with join** | **~21-25ms** | Within 50ms p50 target |

### 11.2 Memory Impact

The join operation temporarily holds two DataFrames in memory. Both are already cached (memory tier), so the marginal memory increase is the join result DataFrame, which is the same size as the primary DataFrame plus the selected target columns. For typical request sizes (100-1000 rows after filter), this is negligible.

### 11.3 Deduplication Cost

The `unique(subset=[join_key], keep="first")` call on the target DataFrame runs once per request. For DataFrames with thousands of rows, this is sub-millisecond in Polars. The deduplication prevents row multiplication in the join result.

---

## 12. Security Considerations

- **No new injection vectors**: The join key and select columns are validated against SchemaRegistry before use. No string interpolation or dynamic expression construction.
- **Same auth requirements**: The `/rows` endpoint continues to require S2S JWT. The join does not bypass authentication or authorization.
- **Target DataFrame access**: Loading the join target DataFrame uses the same `EntityQueryService.get_dataframe()` pipeline, which requires a valid `project_gid` from `EntityProjectRegistry`. There is no way to access entity data outside the registered projects.
- **Column enumeration via error messages**: `JoinError` messages include available column names for the target entity. This is consistent with `UNKNOWN_FIELD` errors in Sprint 1 and does not expose sensitive data (column names are not secrets).

---

## 13. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| **office_phone null for many rows** | Medium | Medium | Document that join match rate depends on cascade field completeness. `join_matched`/`join_unmatched` counts in response meta make this visible. |
| **Column name collision after prefix** | Low | Low | Prefix convention `{entity_type}_{column}` is deterministic. Only collides if primary schema has `business_booking_type` (no current schema does). |
| **Multiple rows with same office_phone** | Medium | Low | Target deduplication (`unique(keep="first")`) prevents row multiplication. Document that deduplication is non-deterministic for tie-breaking. |
| **Performance regression for non-join requests** | Very Low | None | The `join` field is `Optional`; when `None`, no additional DataFrame load or join occurs. Zero overhead for existing queries. |
| **Missing relationship in registry** | Low | Medium | `JoinError` with descriptive message and list of joinable types guides the user. New relationships can be added with a code change. |
| **Schema drift between entities** | Low | Medium | Column validation against `SchemaRegistry` at query time catches missing columns. Schema versions in `DataFrameSchema` track changes. |

---

## 14. Future Considerations (Not in Sprint 2)

1. **Multi-hop joins**: Currently limited to depth=1. A future sprint could allow chaining (e.g., offer -> unit -> business) by traversing the relationship registry.
2. **GID-based joins**: If a `parent_gid` column is added to DataFrames during extraction, GID-based joins would be more precise than shared column matching.
3. **Join caching**: Frequently requested joins (e.g., offer+business) could be pre-computed and cached. Deferred until usage patterns are established.
4. **Aggregate with join**: The `/aggregate` endpoint could support `join` to enable "sum(mrr) group by business.booking_type". Deferred to Sprint 3.
5. **Configurable deduplication strategy**: Currently `keep="first"`. A future enhancement could allow `keep="last"` or aggregation of duplicate matches.

---

## Attestation Table

| File | Absolute Path | Read |
|------|---------------|:----:|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-dynamic-query-service.md` | Yes |
| Sprint 1 TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-dynamic-query-service.md` | Yes |
| Sprint 1 TDD (foundation) | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-query-engine-foundation.md` | Yes |
| Query __init__ | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/__init__.py` | Yes |
| Query models | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/models.py` | Yes |
| Query compiler | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/compiler.py` | Yes |
| Query engine | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/engine.py` | Yes |
| Query guards | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/guards.py` | Yes |
| Query errors | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/errors.py` | Yes |
| EntityQueryService | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/query_service.py` | Yes |
| SchemaRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Yes |
| DataFrameSchema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Yes |
| SectionIndex | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/metrics/resolve.py` | Yes |
| Resolver (to_pascal_case) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Yes |
| Base Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/base.py` | Yes |
| Offer Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/offer.py` | Yes |
| Business Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/business.py` | Yes |
| Contact Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/contact.py` | Yes |
| Unit Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/unit.py` | Yes |
| AssetEdit Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/asset_edit.py` | Yes |
| AssetEditHolder Schema | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/asset_edit_holder.py` | Yes |
| Cache HierarchyIndex | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy.py` | Yes |
| Hierarchy Warmer | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy_warmer.py` | Yes |
