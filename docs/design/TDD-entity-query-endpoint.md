# TDD: Entity Query Endpoint

## Overview

This document specifies the technical design for the Entity Query Endpoint, a new `POST /v1/query/{entity_type}` endpoint that enables list/filter operations on the pre-warmed DataFrame cache. This complements the existing `/v1/resolve/{entity_type}` batch resolution endpoint by providing a way to query entities without knowing specific lookup keys upfront.

## Context

- **PRD Reference**: `docs/requirements/PRD-entity-query-endpoint.md`
- **Related TDDs**:
  - TDD-entity-resolver: Existing resolve endpoint pattern (reuse authentication, project registry)
  - TDD-dataframe-cache: DataFrameCache tiered storage (reuse cache access)
- **Related ADRs**:
  - ADR-0060: Entity Resolver Project Discovery (reuse EntityProjectRegistry)

### Constraints

- Performance: <50ms query latency (cache hit, <100 results)
- S2S JWT authentication only (no PAT support)
- Read-only: No Asana API calls for queries (cache-only)
- Equality filtering only (v1): No complex operators (>, <, LIKE, IN, OR)
- No sorting in v1 (returns cache order)

### Existing Infrastructure to Reuse

| Component | Location | Usage in Design |
|-----------|----------|-----------------|
| DataFrameCache | `cache/dataframe_cache.py` | Tiered cache access (Memory -> S3) |
| get_dataframe_cache_provider() | `cache/dataframe/factory.py` | Singleton cache provider |
| SchemaRegistry | `dataframes/models/registry.py` | Field validation |
| EntityProjectRegistry | `services/resolver.py` | Entity to project mapping |
| require_service_claims | `api/routes/internal.py` | S2S authentication |
| UniversalResolutionStrategy | `services/universal_strategy.py` | **Primary cache access with self-refresh** |
| @dataframe_cache decorator | `cache/dataframe/decorator.py` | Build lock, coalescing, circuit breaker |
| DataFrameCacheCoalescer | `cache/dataframe/coalescer.py` | Thundering herd prevention |

**CRITICAL**: The query endpoint MUST use `UniversalResolutionStrategy._get_dataframe()` for cache access, NOT direct `cache.get_async()`. This ensures:
- Self-refresh on cache miss (triggers build via legacy strategy)
- Build lock acquisition (prevents thundering herd)
- Request coalescing (concurrent requests wait for first builder)
- Circuit breaker integration (per-project failure isolation)

---

## System Design

### Architecture Diagram

```
                                    ┌─────────────────────────────────────────────────────────┐
                                    │                     FastAPI App                          │
                                    │                                                          │
  ┌──────────────┐                 │  ┌─────────────────────────────────────────────────┐    │
  │  S2S Client  │────────────────▶│  │     POST /v1/query/{entity_type}                │    │
  │  (JWT Auth)  │                 │  │              (query.py)                          │    │
  └──────────────┘                 │  └─────────────────────────────────────────────────┘    │
                                    │                          │                              │
                                    │                          ▼                              │
                                    │  ┌─────────────────────────────────────────────────┐    │
                                    │  │             EntityQueryService                   │    │
                                    │  │           (services/query.py)                    │    │
                                    │  └─────────────────────────────────────────────────┘    │
                                    │              │                     │                    │
                                    │              ▼                     ▼                    │
                                    │  ┌─────────────────┐   ┌────────────────────┐          │
                                    │  │  SchemaRegistry │   │EntityProjectRegistry│          │
                                    │  │(field validation)│  │(project GID lookup) │          │
                                    │  └─────────────────┘   └────────────────────┘          │
                                    │              │                                          │
                                    │              ▼                                          │
                                    │  ┌──────────────────────────────────────────────────┐  │
                                    │  │        UniversalResolutionStrategy               │  │
                                    │  │            ._get_dataframe()                      │  │
                                    │  │    (Cache Check -> Self-Refresh on Miss)         │  │
                                    │  └──────────────────────────────────────────────────┘  │
                                    │              │                                          │
                                    │              ▼                                          │
                                    │  ┌──────────────────────────────────────────────────┐  │
                                    │  │              Cache Lifecycle Layer               │  │
                                    │  │  ┌─────────────────────────────────────────────┐ │  │
                                    │  │  │ 1. Memory Tier Check                        │ │  │
                                    │  │  │ 2. S3 Tier Check                            │ │  │
                                    │  │  │ 3. Miss -> Acquire Build Lock               │ │  │
                                    │  │  │ 4. Coalesce Concurrent Requests             │ │  │
                                    │  │  │ 5. Build via @dataframe_cache decorator     │ │  │
                                    │  │  │ 6. Circuit Breaker (per-project isolation)  │ │  │
                                    │  │  └─────────────────────────────────────────────┘ │  │
                                    │  └──────────────────────────────────────────────────┘  │
                                    │              │                                          │
                                    │              ▼                                          │
                                    │  ┌──────────────────────────────────────────────────┐  │
                                    │  │                Polars DataFrame                   │  │
                                    │  │   .filter(where) -> .select(fields) ->           │  │
                                    │  │   .slice(offset, limit) -> .to_dicts()           │  │
                                    │  └──────────────────────────────────────────────────┘  │
                                    │                                                          │
                                    └──────────────────────────────────────────────────────────┘

Data Flow:
1. Request arrives with entity_type, where, select, limit, offset
2. Validate entity_type against SchemaRegistry
3. Validate where/select fields against entity schema
4. Get project_gid from EntityProjectRegistry
5. **Fetch DataFrame via UniversalResolutionStrategy._get_dataframe()**
   a. Check decorator-injected cache
   b. Check DataFrameCache (Memory -> S3)
   c. On miss: Trigger self-refresh via legacy strategy
   d. Legacy strategy uses @dataframe_cache decorator with coalescing
6. Apply Polars filter, select, slice operations
7. Return results with pagination metadata
```

### Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| query router | FastAPI router with `/v1/query/{entity_type}` | `api/routes/query.py` (new) |
| EntityQueryService | Orchestrates query: validates, fetches cache, applies filters | `services/query.py` (new) |
| QueryRequest | Pydantic model for request body | `api/routes/query.py` (new) |
| QueryResponse | Pydantic model for response body | `api/routes/query.py` (new) |

---

## Data Model

### Request/Response Models

```python
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Any


class QueryRequest(BaseModel):
    """Request body for entity query.

    Per PRD FR-002: Unified where clause with AND semantics.

    Attributes:
        where: Filter criteria (field -> value, AND semantics)
        select: Fields to include in response (default: gid, name, section)
        limit: Max results per page (1-1000, default 100)
        offset: Skip N results for pagination (default 0)
    """
    model_config = ConfigDict(extra="forbid")

    where: dict[str, Any] = {}
    select: list[str] | None = None
    limit: int = 100
    offset: int = 0

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Enforce limit bounds (1-1000), clamp if exceeded."""
        if v < 1:
            raise ValueError("limit must be >= 1")
        return min(v, 1000)  # Clamp to max

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        """Enforce non-negative offset."""
        if v < 0:
            raise ValueError("offset must be >= 0")
        return v


class QueryResultItem(BaseModel):
    """Single query result with dynamic fields.

    Always includes gid. Other fields depend on select parameter.
    Uses model_config extra="allow" for dynamic field handling.
    """
    model_config = ConfigDict(extra="allow")

    gid: str
    # Additional fields populated dynamically based on select


class QueryMeta(BaseModel):
    """Response metadata for pagination and context."""
    model_config = ConfigDict(extra="forbid")

    total_count: int       # Total matching records (before pagination)
    limit: int             # Limit used for this request
    offset: int            # Offset used for this request
    entity_type: str       # Entity type queried
    project_gid: str       # Project GID used


class QueryResponse(BaseModel):
    """Response body for entity query.

    Per PRD FR-003: Contains data array and metadata.
    """
    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]  # Matching records with selected fields
    meta: QueryMeta
```

### EntityQueryService

```python
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import polars as pl

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.services.universal_strategy import UniversalResolutionStrategy


@dataclass
class QueryResult:
    """Result of query operation.

    Attributes:
        data: List of matching records as dictionaries
        total_count: Total matches before pagination
        project_gid: Project GID used for query
    """
    data: list[dict[str, Any]]
    total_count: int
    project_gid: str


@dataclass
class EntityQueryService:
    """Service for querying entities from DataFrame cache.

    Per TDD-entity-query-endpoint (Revised):
    - Uses UniversalResolutionStrategy._get_dataframe() for cache access
    - This ensures full cache lifecycle: check -> miss -> self-refresh
    - Validates fields against SchemaRegistry
    - Applies Polars filter/select/slice operations
    - Returns read-only results (no Asana API calls)

    CRITICAL: Does NOT call cache.get_async() directly. Uses
    UniversalResolutionStrategy to get DataFrame, which provides:
    - Layered cache access (Memory -> S3)
    - Self-refresh on cache miss
    - Build lock acquisition (thundering herd prevention)
    - Request coalescing via @dataframe_cache decorator
    - Circuit breaker integration

    Attributes:
        strategy_factory: Factory function to create UniversalResolutionStrategy.
            Default: get_universal_strategy from services/universal_strategy.py

    Example:
        >>> service = EntityQueryService()
        >>> result = await service.query(
        ...     entity_type="offer",
        ...     project_gid="1143843662099250",
        ...     client=asana_client,
        ...     where={"section": "ACTIVE"},
        ...     select=["gid", "name", "office_phone"],
        ...     limit=100,
        ...     offset=0,
        ... )
        >>> result.total_count
        47
    """

    strategy_factory: Any = field(default=None)  # Callable[[str], UniversalResolutionStrategy]

    def __post_init__(self) -> None:
        """Initialize default strategy factory."""
        if self.strategy_factory is None:
            from autom8_asana.services.universal_strategy import get_universal_strategy
            self.strategy_factory = get_universal_strategy

    async def query(
        self,
        entity_type: str,
        project_gid: str,
        client: "AsanaClient",
        where: dict[str, Any],
        select: list[str] | None,
        limit: int,
        offset: int,
    ) -> QueryResult:
        """Query entities matching criteria with full cache lifecycle.

        CRITICAL: Uses UniversalResolutionStrategy._get_dataframe() which
        provides self-refresh on cache miss. This ensures:
        - Cache hit: Returns immediately from Memory/S3
        - Cache miss: Triggers build via legacy strategy + @dataframe_cache
        - Concurrent misses: Coalesced (first builds, others wait)
        - Repeated failures: Circuit breaker protects system

        Query flow:
        1. Create UniversalResolutionStrategy for entity_type
        2. Call strategy._get_dataframe(project_gid, client)
           - Checks decorator-injected cache
           - Checks DataFrameCache (Memory -> S3)
           - On miss: Triggers self-refresh via legacy strategy
        3. Apply filters, select, pagination
        4. Return results

        Args:
            entity_type: Entity type to query (e.g., "offer")
            project_gid: Project GID for cache key
            client: AsanaClient for build operations (if cache miss)
            where: Filter criteria (AND semantics)
            select: Fields to include (None = default set)
            limit: Max results
            offset: Skip N results

        Returns:
            QueryResult with data and metadata

        Raises:
            CacheNotWarmError: DataFrame unavailable after self-refresh attempt
        """
        # Get strategy for entity type
        strategy = self.strategy_factory(entity_type)

        # Get DataFrame via strategy (full cache lifecycle)
        # This is the CRITICAL change from the original TDD
        df = await strategy._get_dataframe(project_gid, client)

        if df is None:
            # Cache miss even after self-refresh attempt
            # This can happen if:
            # - No legacy strategy exists for entity type
            # - Build failed (circuit breaker may be open)
            raise CacheNotWarmError(
                f"DataFrame unavailable for {entity_type}. "
                "Cache warming may be in progress or build failed."
            )

        # Apply filters
        filtered_df = self._apply_filters(df, where)

        # Get total count BEFORE pagination
        total_count = len(filtered_df)

        # Apply pagination
        paginated_df = self._apply_pagination(filtered_df, offset, limit)

        # Apply select
        select_fields = select or ["gid", "name", "section"]
        selected_df = self._apply_select(paginated_df, select_fields)

        # Convert to list of dicts
        data = selected_df.to_dicts()

        return QueryResult(
            data=data,
            total_count=total_count,
            project_gid=project_gid,
        )

    def _apply_filters(
        self,
        df: pl.DataFrame,
        where: dict[str, Any],
    ) -> pl.DataFrame:
        """Apply equality filters to DataFrame.

        Per PRD FR-007: Equality filtering only.
        Multiple fields are AND-ed together.
        Null values in filter column are excluded.

        Args:
            df: Source DataFrame
            where: Field -> value equality filters

        Returns:
            Filtered DataFrame
        """
        for field_name, value in where.items():
            df = df.filter(pl.col(field_name) == value)
        return df

    def _apply_select(
        self,
        df: pl.DataFrame,
        select: list[str],
    ) -> pl.DataFrame:
        """Select only requested columns.

        Per PRD FR-002: gid always included regardless of select.

        Args:
            df: Source DataFrame
            select: Columns to include

        Returns:
            DataFrame with selected columns only
        """
        # Ensure gid is always included
        columns = list(set(["gid"] + select))
        # Filter to only columns that exist in DataFrame
        available = set(df.columns)
        valid_columns = [c for c in columns if c in available]
        return df.select(valid_columns)

    def _apply_pagination(
        self,
        df: pl.DataFrame,
        offset: int,
        limit: int,
    ) -> pl.DataFrame:
        """Apply offset/limit pagination.

        Args:
            df: Source DataFrame
            offset: Skip N rows
            limit: Take N rows

        Returns:
            Paginated DataFrame slice
        """
        return df.slice(offset, limit)


class CacheNotWarmError(Exception):
    """Raised when DataFrame cache is not available after self-refresh attempt."""
    pass
```

---

## API Contracts

### POST /v1/query/{entity_type}

```http
POST /v1/query/offer HTTP/1.1
Host: api.autom8.io
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "where": {
    "section": "ACTIVE",
    "vertical": "dental"
  },
  "select": ["gid", "name", "office_phone", "vertical", "section"],
  "limit": 100,
  "offset": 0
}
```

**Path Parameters:**

| Parameter | Type | Required | Values |
|-----------|------|----------|--------|
| entity_type | string | Yes | `unit`, `business`, `offer`, `contact`, `asset_edit`, `asset_edit_holder` |

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| where | object | No | `{}` | Filter criteria (AND semantics) |
| select | array[string] | No | `["gid", "name", "section"]` | Fields to include |
| limit | integer | No | 100 | Max results per page (1-1000) |
| offset | integer | No | 0 | Skip N results for pagination |

**Response (200 OK):**

```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Acme Dental - Facebook Campaign",
      "office_phone": "+15551234567",
      "vertical": "dental",
      "section": "ACTIVE"
    },
    {
      "gid": "1234567890123457",
      "name": "Beta Medical - Google Ads",
      "office_phone": "+15559876543",
      "vertical": "medical",
      "section": "ACTIVE"
    }
  ],
  "meta": {
    "total_count": 47,
    "limit": 100,
    "offset": 0,
    "entity_type": "offer",
    "project_gid": "1143843662099250"
  }
}
```

**Error Responses:**

| Status | Error Code | Condition |
|--------|------------|-----------|
| 401 | MISSING_AUTH | No Authorization header |
| 401 | SERVICE_TOKEN_REQUIRED | PAT token provided (S2S only) |
| 401 | JWT_INVALID | JWT validation failed |
| 404 | UNKNOWN_ENTITY_TYPE | entity_type not in allowed values |
| 422 | INVALID_FIELD | Field in where/select not in schema |
| 422 | VALIDATION_ERROR | Invalid request body |
| 503 | CACHE_NOT_WARMED | DataFrame cache not available |
| 503 | PROJECT_NOT_CONFIGURED | No project configured for entity |

---

## Sequence Diagrams

### Query Flow (Cache Hit)

```
┌──────┐  ┌─────────┐  ┌───────────────┐  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐
│Client│  │query.py │  │EntityQuerySvc │  │UniversalStrategy │  │DataFrameCache│  │SchemaRegistry│
│      │  │(router) │  │               │  │._get_dataframe() │  │              │  │              │
└──┬───┘  └────┬────┘  └──────┬────────┘  └────────┬─────────┘  └──────┬───────┘  └──────┬───────┘
   │           │              │                    │                   │                  │
   │ POST /v1/query/offer     │                    │                   │                  │
   │ {where: {section: "ACTIVE"}}                  │                   │                  │
   │──────────────────────────▶                    │                   │                  │
   │           │              │                    │                   │                  │
   │           │ require_service_claims()          │                   │                  │
   │           │──────────────▶                    │                   │                  │
   │           │              │                    │                   │                  │
   │           │ validate entity_type              │                   │                  │
   │           │─────────────────────────────────────────────────────────────────────────▶│
   │           │              │                    │                   │                  │
   │           │◀──schema exists────────────────────────────────────────────────────────────│
   │           │              │                    │                   │                  │
   │           │ query()      │                    │                   │                  │
   │           │─────────────▶│                    │                   │                  │
   │           │              │                    │                   │                  │
   │           │              │ strategy._get_dataframe()              │                  │
   │           │              │───────────────────▶│                   │                  │
   │           │              │                    │                   │                  │
   │           │              │                    │ get_async(project_gid, entity_type)  │
   │           │              │                    │──────────────────▶│                  │
   │           │              │                    │                   │                  │
   │           │              │                    │◀─CacheEntry(df)───│ (Memory/S3 hit)  │
   │           │              │                    │                   │                  │
   │           │              │◀──DataFrame────────│                   │                  │
   │           │              │                    │                   │                  │
   │           │              │ df.filter(where)   │                   │                  │
   │           │              │ df.select(fields)  │                   │                  │
   │           │              │ df.slice(offset,limit)                 │                  │
   │           │              │                    │                   │                  │
   │           │◀─QueryResult─│                    │                   │                  │
   │           │              │                    │                   │                  │
   │◀──────────│              │                    │                   │                  │
   │ 200 OK    │              │                    │                   │                  │
   │ {data: [...], meta: {...}}                    │                   │                  │
```

### Cache Miss Flow (Self-Refresh with Coalescing)

```
┌──────┐  ┌─────────┐  ┌───────────────┐  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐
│Client│  │query.py │  │EntityQuerySvc │  │UniversalStrategy │  │DataFrameCache│  │LegacyStrategy│  │ Coalescer   │
│      │  │(router) │  │               │  │._get_dataframe() │  │              │  │(@decorated)  │  │             │
└──┬───┘  └────┬────┘  └──────┬────────┘  └────────┬─────────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘
   │           │              │                    │                   │                 │                 │
   │ POST /v1/query/offer     │                    │                   │                 │                 │
   │──────────────────────────▶                    │                   │                 │                 │
   │           │              │                    │                   │                 │                 │
   │           │ query()      │                    │                   │                 │                 │
   │           │─────────────▶│                    │                   │                 │                 │
   │           │              │                    │                   │                 │                 │
   │           │              │ strategy._get_dataframe()              │                 │                 │
   │           │              │───────────────────▶│                   │                 │                 │
   │           │              │                    │                   │                 │                 │
   │           │              │                    │ get_async()       │                 │                 │
   │           │              │                    │──────────────────▶│                 │                 │
   │           │              │                    │                   │                 │                 │
   │           │              │                    │◀─None (miss)──────│                 │                 │
   │           │              │                    │                   │                 │                 │
   │           │              │                    │ Trigger self-refresh via legacy     │                 │
   │           │              │                    │────────────────────────────────────▶│                 │
   │           │              │                    │                   │                 │                 │
   │           │              │                    │                   │                 │ try_acquire()   │
   │           │              │                    │                   │                 │────────────────▶│
   │           │              │                    │                   │                 │                 │
   │           │              │                    │                   │                 │◀──True (build)──│
   │           │              │                    │                   │                 │                 │
   │           │              │                    │                   │                 │ Build DataFrame │
   │           │              │                    │                   │                 │ (Asana API)     │
   │           │              │                    │                   │                 │                 │
   │           │              │                    │                   │ put_async(df)   │                 │
   │           │              │                    │                   │◀────────────────│                 │
   │           │              │                    │                   │                 │                 │
   │           │              │                    │                   │                 │ release(success)│
   │           │              │                    │                   │                 │────────────────▶│
   │           │              │                    │                   │                 │                 │
   │           │              │                    │ get_async() (retry)│                │                 │
   │           │              │                    │──────────────────▶│                 │                 │
   │           │              │                    │                   │                 │                 │
   │           │              │                    │◀─CacheEntry(df)───│ (now warm)      │                 │
   │           │              │                    │                   │                 │                 │
   │           │              │◀──DataFrame────────│                   │                 │                 │
   │           │              │                    │                   │                 │                 │
   │           │◀─QueryResult─│                    │                   │                 │                 │
   │           │              │                    │                   │                 │                 │
   │◀──────────│              │                    │                   │                 │                 │
   │ 200 OK    │              │                    │                   │                 │                 │
   │ {data: [...], meta: {...}}                    │                   │                 │                 │
```

### Concurrent Cache Miss (Coalesced Requests)

```
┌───────┐  ┌───────┐  ┌───────────────┐  ┌──────────────────┐  ┌─────────────┐
│Client1│  │Client2│  │EntityQuerySvc │  │LegacyStrategy    │  │ Coalescer   │
│       │  │       │  │               │  │(@decorated)      │  │             │
└───┬───┘  └───┬───┘  └──────┬────────┘  └────────┬─────────┘  └──────┬──────┘
    │          │             │                    │                   │
    │ POST /query/offer      │                    │                   │
    │───────────────────────▶│                    │                   │
    │          │             │                    │                   │
    │          │ POST /query/offer                │                   │
    │          │────────────▶│                    │                   │
    │          │             │                    │                   │
    │          │             │ Client1: trigger self-refresh          │
    │          │             │───────────────────▶│                   │
    │          │             │                    │                   │
    │          │             │                    │ try_acquire()     │
    │          │             │                    │──────────────────▶│
    │          │             │                    │◀─True (acquired)──│
    │          │             │                    │                   │
    │          │             │ Client2: trigger self-refresh          │
    │          │             │───────────────────▶│                   │
    │          │             │                    │                   │
    │          │             │                    │ try_acquire()     │
    │          │             │                    │──────────────────▶│
    │          │             │                    │◀─False (wait)─────│ Client2 waits
    │          │             │                    │                   │
    │          │             │                    │ wait_async()      │
    │          │             │                    │──────────────────▶│ (blocks)
    │          │             │                    │                   │
    │          │             │                    │ Client1: Build    │
    │          │             │                    │ (Asana API call)  │
    │          │             │                    │                   │
    │          │             │                    │ release(success)  │
    │          │             │                    │──────────────────▶│
    │          │             │                    │                   │
    │          │             │                    │◀─wait complete────│ Client2 unblocks
    │          │             │                    │                   │
    │          │             │◀─DataFrame─────────│ Both clients get DataFrame
    │          │             │                    │                   │
    │◀─200 OK──│             │                    │                   │
    │          │◀─200 OK─────│                    │                   │
```

### Build Failure (503 Response)

```
┌──────┐  ┌─────────┐  ┌───────────────┐  ┌──────────────────┐
│Client│  │query.py │  │EntityQuerySvc │  │UniversalStrategy │
│      │  │(router) │  │               │  │._get_dataframe() │
└──┬───┘  └────┬────┘  └──────┬────────┘  └────────┬─────────┘
   │           │              │                    │
   │ POST /v1/query/offer     │                    │
   │──────────────────────────▶                    │
   │           │              │                    │
   │           │ query()      │                    │
   │           │─────────────▶│                    │
   │           │              │                    │
   │           │              │ strategy._get_dataframe()
   │           │              │───────────────────▶│
   │           │              │                    │
   │           │              │                    │ Cache miss, trigger build
   │           │              │                    │ Build failed or circuit open
   │           │              │                    │
   │           │              │◀──None─────────────│
   │           │              │                    │
   │           │◀─CacheNotWarmError                │
   │           │              │                    │
   │◀──────────│              │                    │
   │ 503       │              │                    │
   │ {error: "CACHE_NOT_WARMED",                   │
   │  message: "DataFrame unavailable..."}         │
```

---

## Implementation Guidance

### File Structure

```
src/autom8_asana/
├── services/
│   ├── query.py              # NEW: EntityQueryService, CacheNotWarmError
│   ├── resolver.py           # EXISTS: EntityProjectRegistry (reused)
│   └── universal_strategy.py # EXISTS: _get_dataframe() (PRIMARY CACHE ACCESS)
├── api/
│   └── routes/
│       ├── query.py          # NEW: /v1/query/{entity_type} router
│       ├── resolver.py       # EXISTS: /v1/resolve pattern (reference)
│       └── __init__.py       # MODIFIED: Add query_router
├── cache/
│   └── dataframe/
│       ├── decorator.py      # EXISTS: @dataframe_cache (coalescing, locking)
│       ├── coalescer.py      # EXISTS: DataFrameCacheCoalescer
│       └── circuit_breaker.py # EXISTS: CircuitBreaker
└── api/
    └── main.py               # MODIFIED: Include query_router
```

### Route Implementation

```python
"""Entity Query routes for list/filter operations on DataFrame cache.

Per TDD-entity-query-endpoint (Revised):
This module provides the POST /v1/query/{entity_type} endpoint for querying
entities from the DataFrame cache via UniversalResolutionStrategy.

CRITICAL CHANGE: Uses EntityQueryService which routes through
UniversalResolutionStrategy._get_dataframe() for full cache lifecycle:
- Self-refresh on cache miss
- Build lock acquisition (thundering herd prevention)
- Request coalescing via @dataframe_cache decorator
- Circuit breaker integration

Routes:
- POST /v1/query/{entity_type} - Query entities with filtering and pagination

Authentication:
- All routes require service token (S2S JWT) authentication
- PAT pass-through is NOT supported
"""

from __future__ import annotations

import time
from typing import Annotated, Any

from autom8y_log import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, field_validator

from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.client import AsanaClient
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.services.query import CacheNotWarmError, EntityQueryService
from autom8_asana.services.resolver import (
    EntityProjectRegistry,
    to_pascal_case,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/query", tags=["query"])


# Default fields when select is not specified
DEFAULT_SELECT_FIELDS = ["gid", "name", "section"]


class QueryRequest(BaseModel):
    """Request body for entity query."""
    model_config = ConfigDict(extra="forbid")

    where: dict[str, Any] = {}
    select: list[str] | None = None
    limit: int = 100
    offset: int = 0

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1:
            raise ValueError("limit must be >= 1")
        return min(v, 1000)

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 0:
            raise ValueError("offset must be >= 0")
        return v


class QueryMeta(BaseModel):
    """Response metadata."""
    model_config = ConfigDict(extra="forbid")

    total_count: int
    limit: int
    offset: int
    entity_type: str
    project_gid: str


class QueryResponse(BaseModel):
    """Response body for entity query."""
    model_config = ConfigDict(extra="forbid")

    data: list[dict[str, Any]]
    meta: QueryMeta


def _get_queryable_entities() -> set[str]:
    """Get entity types that support querying.

    Returns entity types that have both a schema and registered project.
    """
    from autom8_asana.services.resolver import get_resolvable_entities
    return get_resolvable_entities()


def _validate_fields(
    fields: list[str],
    entity_type: str,
    field_type: str,  # "where" or "select"
) -> None:
    """Validate fields against entity schema.

    Args:
        fields: Field names to validate
        entity_type: Entity type for schema lookup
        field_type: "where" or "select" for error message

    Raises:
        HTTPException: 422 if any field is invalid
    """
    registry = SchemaRegistry.get_instance()
    schema_key = to_pascal_case(entity_type)

    try:
        schema = registry.get_schema(schema_key)
    except Exception:
        schema = registry.get_schema("*")

    valid_fields = set(schema.column_names())
    invalid_fields = set(fields) - valid_fields

    if invalid_fields:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "INVALID_FIELD",
                "message": f"Unknown field(s) in {field_type} clause: {sorted(invalid_fields)}",
                "available_fields": sorted(valid_fields),
            },
        )


def _get_query_service() -> EntityQueryService:
    """Get EntityQueryService instance.

    Factory function for dependency injection.
    """
    return EntityQueryService()


@router.post("/{entity_type}", response_model=QueryResponse)
async def query_entities(
    entity_type: str,
    request_body: QueryRequest,
    request: Request,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> QueryResponse:
    """Query entities from DataFrame cache with full cache lifecycle.

    CRITICAL: This endpoint uses EntityQueryService which routes through
    UniversalResolutionStrategy._get_dataframe(). This ensures:
    - Cache hit: Returns immediately from Memory/S3 tier
    - Cache miss: Triggers self-refresh via legacy strategy
    - Concurrent misses: Coalesced (first builds, others wait)
    - Repeated failures: Circuit breaker protects system

    Authentication:
        Requires valid service token (S2S JWT).
        PAT tokens are NOT supported.

    Path Parameters:
        entity_type: Entity type to query (unit, business, offer, etc.)

    Request:
        POST /v1/query/offer
        {
            "where": {"section": "ACTIVE"},
            "select": ["gid", "name", "office_phone"],
            "limit": 100,
            "offset": 0
        }

    Response:
        {
            "data": [{"gid": "123", "name": "...", "office_phone": "..."}],
            "meta": {"total_count": 47, "limit": 100, "offset": 0, ...}
        }
    """
    start_time = time.monotonic()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(
        "entity_query_request",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "where_fields": list(request_body.where.keys()),
            "select_fields": request_body.select,
            "limit": request_body.limit,
            "offset": request_body.offset,
            "caller_service": claims.service_name,
        },
    )

    # Validate entity type
    queryable_types = _get_queryable_entities()
    if entity_type not in queryable_types:
        logger.warning(
            "unknown_entity_type",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "available": sorted(queryable_types),
            },
        )
        raise HTTPException(
            status_code=404,
            detail={
                "error": "UNKNOWN_ENTITY_TYPE",
                "message": f"Unknown entity type: {entity_type}",
                "available_types": sorted(queryable_types),
            },
        )

    # Validate where fields
    if request_body.where:
        _validate_fields(
            list(request_body.where.keys()),
            entity_type,
            "where",
        )

    # Determine select fields
    select_fields = request_body.select or DEFAULT_SELECT_FIELDS

    # Validate select fields
    _validate_fields(select_fields, entity_type, "select")

    # Get project GID from EntityProjectRegistry
    entity_registry: EntityProjectRegistry | None = getattr(
        request.app.state, "entity_project_registry", None
    )

    if entity_registry is None or not entity_registry.is_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": "Entity project registry not initialized.",
            },
        )

    project_gid = entity_registry.get_project_gid(entity_type)

    if project_gid is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "PROJECT_NOT_CONFIGURED",
                "message": f"No project configured for entity type: {entity_type}",
            },
        )

    # Get AsanaClient for potential cache build operations
    # Uses bot PAT from app state (same as resolve endpoint)
    bot_pat: str | None = getattr(request.app.state, "bot_pat", None)
    if bot_pat is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "SERVICE_NOT_CONFIGURED",
                "message": "Bot PAT not configured for cache operations.",
            },
        )

    # Execute query via EntityQueryService
    # This routes through UniversalResolutionStrategy._get_dataframe()
    # which provides full cache lifecycle (self-refresh, coalescing, circuit breaker)
    query_service = _get_query_service()

    try:
        async with AsanaClient(token=bot_pat) as client:
            result = await query_service.query(
                entity_type=entity_type,
                project_gid=project_gid,
                client=client,
                where=request_body.where,
                select=select_fields,
                limit=request_body.limit,
                offset=request_body.offset,
            )
    except CacheNotWarmError as e:
        logger.warning(
            "cache_not_warm",
            extra={
                "request_id": request_id,
                "entity_type": entity_type,
                "project_gid": project_gid,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CACHE_NOT_WARMED",
                "message": str(e),
                "entity_type": entity_type,
                "retry_after_seconds": 30,
            },
        )

    # Build response
    response = QueryResponse(
        data=result.data,
        meta=QueryMeta(
            total_count=result.total_count,
            limit=request_body.limit,
            offset=request_body.offset,
            entity_type=entity_type,
            project_gid=result.project_gid,
        ),
    )

    # Log completion
    elapsed_ms = (time.monotonic() - start_time) * 1000

    logger.info(
        "entity_query_complete",
        extra={
            "request_id": request_id,
            "entity_type": entity_type,
            "result_count": len(result.data),
            "total_count": result.total_count,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
            "project_gid": result.project_gid,
            "cache_status": "hit_or_refreshed",  # May have self-refreshed
        },
    )

    return response
```

### Router Registration

Update `api/routes/__init__.py`:

```python
from .query import router as query_router

__all__ = [
    # ... existing exports ...
    "query_router",
]
```

Update `api/main.py`:

```python
from .routes import (
    # ... existing imports ...
    query_router,
)

# In create_app():
app.include_router(query_router)
```

---

## Non-Functional Considerations

### Performance

**Targets (from PRD NFR-001):**

| Metric | Target | Approach |
|--------|--------|----------|
| Query latency (cache hit, <100 results) | <50ms | In-memory DataFrame filtering |
| Query latency (cache hit, 1000 results) | <200ms | Polars vectorized operations |
| Memory overhead per request | <5MB | Reference existing DataFrame, no copy |
| Asana API calls | 0 | Cache-only reads |

**Query Optimization:**
- Polars filter operations are vectorized and efficient
- Select before pagination to reduce memory
- Use `df.slice()` which creates a view, not a copy
- `df.to_dicts()` is efficient for small result sets

### Security

**Authentication (reuse from resolver):**
- Reuse existing `require_service_claims` dependency
- S2S JWT required, PAT tokens rejected with 401
- Caller service name logged for audit

**Input Validation:**
- Entity type: validated against SchemaRegistry
- Where fields: validated against entity schema
- Select fields: validated against entity schema
- Limit: bounded 1-1000, clamped if exceeded
- Offset: non-negative integer

**No Data Modification:**
- Query endpoint is read-only
- No Asana API calls made
- No cache writes or invalidation

### Reliability

**Graceful Degradation:**
- Cache miss returns 503 with retry guidance
- Individual field validation errors return 422 with available fields
- Empty results return 200 with empty data array

**Error Responses:**

| Code | Description |
|------|-------------|
| UNKNOWN_ENTITY_TYPE | Entity type not registered |
| INVALID_FIELD | Field not in entity schema |
| CACHE_NOT_WARMED | DataFrame not in cache |
| PROJECT_NOT_CONFIGURED | No project for entity type |

### Observability

**Structured Logging:**

```python
logger.info(
    "entity_query_complete",
    extra={
        "request_id": "req-abc123",
        "entity_type": "offer",
        "where_fields": ["section", "vertical"],
        "result_count": 47,
        "total_count": 150,
        "duration_ms": 12.5,
        "caller_service": "autom8_data",
        "cache_status": "hit",
        "project_gid": "1143843662099250",
    }
)
```

**Metrics (future):**
- `entity_query_requests_total{entity_type, status}`
- `entity_query_duration_seconds{entity_type}`
- `entity_query_cache_hit_rate{entity_type}`
- `entity_query_result_count{entity_type}`

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache miss during high traffic | Low | Medium | Return 503 with retry guidance; cache warmer runs on schedule |
| Large result sets impact memory | Low | Low | Limit max 1000 results; Polars uses views not copies |
| Invalid field names in requests | Medium | Low | Validate against SchemaRegistry; return available fields in error |
| Query latency exceeds target | Low | Low | Polars vectorized ops are fast; monitor and optimize if needed |
| Stale cache data | Medium | Low | TTL-based invalidation; Lambda warmer runs periodically |

---

## ADRs

### ADR-0061: Query Endpoint Cache Access via UniversalResolutionStrategy

**Status**: Accepted

**Context**:
The initial TDD design specified direct cache access via `cache.get_async()` for the query endpoint. This approach was identified as problematic because:
- No self-refresh on cache miss (returns 503 immediately)
- No build lock acquisition (thundering herd vulnerability)
- No request coalescing (concurrent requests all fail independently)
- No circuit breaker integration (repeated failures cascade)

Two options were evaluated:
- **Option A**: Add `query()` method to `UniversalResolutionStrategy` that reuses `_get_dataframe()`
- **Option B**: Call through existing `@dataframe_cache` decorated strategy directly

**Decision**:
Use **Option A (Modified)**: Route query operations through `UniversalResolutionStrategy._get_dataframe()` via a new `EntityQueryService`.

**Rationale**:
1. **DRY**: `UniversalResolutionStrategy._get_dataframe()` already implements the full cache lifecycle:
   - Layer 1: Check decorator-injected cache
   - Layer 2: Check DataFrameCache singleton (Memory -> S3)
   - Layer 3: On miss, trigger self-refresh via legacy strategy
2. **Self-refresh**: The legacy strategy uses `@dataframe_cache` decorator which handles:
   - `acquire_build_lock_async()` - Prevents thundering herd
   - `wait_for_build_async()` - Coalesces concurrent requests
   - Circuit breaker integration for per-project failure isolation
3. **Encapsulation**: `EntityQueryService` provides a clean API for query operations while delegating cache concerns to the established infrastructure
4. **Consistency**: All DataFrame access (resolve and query) goes through the same cache lifecycle

**Consequences**:
- Query endpoint requires `AsanaClient` even for cache hits (needed for potential self-refresh)
- Slight latency increase on cache miss (build + retry) vs. immediate 503
- Clients benefit from eventual consistency rather than hard failures

**Alternatives Rejected**:
- **Direct cache access**: Breaks established pattern, no self-refresh
- **Option B (decorated resolve)**: Awkward API (empty criteria), two-step process

### Related ADRs
- ADR-0060: Entity Resolver Project Discovery (EntityProjectRegistry)
- TDD-dataframe-cache: DataFrameCache tiered storage patterns

---

## Test Matrix

| Test Case | Entity Type | Input | Expected |
|-----------|-------------|-------|----------|
| TC-001 | offer | where.section = "ACTIVE" | Returns matching offers |
| TC-002 | offer | where.section = "NONEXISTENT" | Returns empty data array |
| TC-003 | offer | where.invalid_field = "x" | 422 INVALID_FIELD |
| TC-004 | offer | select = ["gid", "invalid"] | 422 INVALID_FIELD |
| TC-005 | offer | limit = 0 | 422 validation error |
| TC-006 | offer | limit = 2000 | Clamped to 1000, succeeds |
| TC-007 | offer | offset = -1 | 422 validation error |
| TC-008 | offer | offset > total_count | Returns empty data with correct total |
| TC-009 | unknown | any | 404 UNKNOWN_ENTITY_TYPE |
| TC-010 | offer | Empty where | Returns all (paginated) |
| TC-011 | offer | Multiple where fields | AND logic applied |
| TC-012 | offer | PAT token | 401 SERVICE_TOKEN_REQUIRED |
| TC-013 | offer | Cache miss | 503 CACHE_NOT_WARMED |
| TC-014 | offer | select omitted | Default fields returned |
| TC-015 | offer | Batch 1000 results | <200ms latency |
| TC-016 | unit | Valid query | Works with cascade fields |
| TC-017 | contact | Valid query | Works for contact entity |
| TC-018 | business | Valid query | Works for business entity |

---

## Implementation Checklist

### Phase 1: Core Endpoint (Sprint 1)

- [ ] Create `api/routes/query.py` with QueryRequest/QueryResponse models
- [ ] Implement POST /v1/query/{entity_type} endpoint
- [ ] Add entity type validation against SchemaRegistry
- [ ] Add field validation for where and select
- [ ] Integrate DataFrameCache for cache access
- [ ] Implement Polars filter/select/pagination
- [ ] Add structured logging
- [ ] Register router in main.py and __init__.py
- [ ] Unit tests for query logic
- [ ] Integration tests with mock cache

### Phase 2: Testing and Validation (Sprint 1)

- [ ] Integration tests with real cache
- [ ] Performance validation (<50ms for <100 results)
- [ ] Error handling edge cases
- [ ] API documentation updates
- [ ] Staging deployment and smoke tests

### Phase 3: Observability (Sprint 2, if needed)

- [ ] Add metrics collection
- [ ] Add alerting for latency/error rate
- [ ] Performance profiling and optimization

---

## Appendix A: Supported Entity Types and Fields

See PRD Appendix A for complete field listings. Key entities:

| Entity | Common Query Fields |
|--------|-------------------|
| unit | section, vertical, office_phone |
| business | section, vertical, office_phone |
| offer | section, vertical, office_phone, offer_id, platforms |
| contact | section, email |
| asset_edit | section, offer_id |
| asset_edit_holder | section, office_phone |

---

## File Verification Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD Document | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-entity-query-endpoint.md` | Revised |
| PRD Input | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-entity-query-endpoint.md` | Read |
| Resolver Pattern | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py` | Read |
| DataFrameCache | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe_cache.py` | Read |
| Universal Strategy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Read (Critical) |
| Schema Registry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Read |
| Entity Resolver TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-entity-resolver.md` | Read |
| @dataframe_cache Decorator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/decorator.py` | Read (Critical) |
| DataFrameCacheCoalescer | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/coalescer.py` | Read |
| CircuitBreaker | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/circuit_breaker.py` | Read |

### Revision Notes (2026-01-14)

**Problem Identified**: Original TDD specified direct cache access via `cache.get_async()` which:
- Did NOT trigger self-refresh on cache miss
- Did NOT acquire build locks (thundering herd vulnerability)
- Did NOT coalesce concurrent requests
- Did NOT integrate with circuit breaker

**Solution Applied**: Revised to route all cache access through `UniversalResolutionStrategy._get_dataframe()` which provides:
- Layered cache access (Memory -> S3 -> self-refresh)
- Build lock acquisition via `@dataframe_cache` decorator
- Request coalescing via `DataFrameCacheCoalescer`
- Circuit breaker integration for per-project failure isolation

**Key Changes**:
1. Updated Architecture Diagram to show UniversalResolutionStrategy as primary cache access
2. Added EntityQueryService with `strategy._get_dataframe()` integration
3. Revised Route Implementation to use EntityQueryService
4. Added four new sequence diagrams: Cache Hit, Cache Miss with Self-Refresh, Concurrent Coalescing, Build Failure
5. Added ADR-0061 documenting the cache lifecycle decision
