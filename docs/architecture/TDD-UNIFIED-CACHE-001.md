# TDD: Unified Task Cache Architecture

**TDD ID**: TDD-UNIFIED-CACHE-001
**Version**: 1.0
**Date**: 2026-01-02
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: N/A (Technical initiative from user discovery session)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Current State Analysis](#current-state-analysis)
4. [Goals and Non-Goals](#goals-and-non-goals)
5. [Proposed Architecture](#proposed-architecture)
6. [Component Designs](#component-designs)
7. [Data Flow](#data-flow)
8. [API Contracts](#api-contracts)
9. [Migration Strategy](#migration-strategy)
10. [Implementation Phases](#implementation-phases)
11. [Risk Assessment](#risk-assessment)
12. [ADRs](#adrs)
13. [Success Criteria](#success-criteria)
14. [Appendices](#appendices)

---

## Overview

This TDD defines a first-principles architecture that unifies task caching and DataFrame materialization as views of the same underlying data. The design addresses the fragmentation between multiple cache layers currently operating in the autom8_asana SDK, consolidating 4-6 API calls per operation into a single S3-backed source of truth with configurable freshness guarantees.

### Solution Summary

**Single Source of Truth (SSoT)**: All task data flows through a unified cache layer backed by S3, with optional Redis as a hot tier. DataFrames become materialized views with configurable freshness policies rather than independent data stores.

**Key Insight**: Related data (subtasks, stories, attachments) share the root task's `modified_at` timestamp. This allows batch freshness checks to validate entire entity hierarchies with a single lightweight API call per root task.

---

## Problem Statement

### Current State Challenges

1. **Fragmented Cache Layers**: Multiple independent cache implementations exist:
   - `TieredCacheProvider` (Redis hot + S3 cold)
   - `TaskCacheCoordinator` (Task-level cache for DataFrame builds)
   - `DataFrameCacheIntegration` (Row-level cache for extracted data)
   - `StalenessCheckCoordinator` (Lightweight staleness detection)
   - `WatermarkRepository` (Incremental sync tracking)

2. **Redundant API Calls**: A typical DataFrame build executes 4-6 API calls:
   - Section enumeration (1 call)
   - Task batch fetch (1+ calls)
   - Parent chain traversal for cascade resolution (1-3 calls per unique ancestor)
   - Stories/attachments (if requested)

3. **Inconsistent Freshness**: Different layers use different freshness detection:
   - Task cache uses `modified_at` comparison
   - DataFrame cache uses schema version + `modified_at`
   - Staleness coordinator uses TTL extension with progressive backoff
   - Watermark uses timestamps for incremental sync

4. **No Unified Parent Chain**: `CascadingFieldResolver` fetches parents individually during extraction, even when parent data may already exist in other cache layers.

### Root Cause

The current architecture evolved incrementally, with each new requirement adding a cache layer rather than extending a unified foundation. This creates:
- Duplicate storage of the same task data
- Inconsistent staleness semantics
- No shared parent chain resolution
- Multiple code paths for similar operations

---

## Current State Analysis

### Cascade Tooling Audit

**Files Examined**:
- `/src/autom8_asana/models/business/fields.py` - `CASCADING_FIELD_REGISTRY`
- `/src/autom8_asana/dataframes/resolver/cascading.py` - `CascadingFieldResolver`
- `/src/autom8_asana/dataframes/schemas/unit.py` - `cascade:` prefix usage

**Findings**:

| Component | Status | Action |
|-----------|--------|--------|
| `CascadingFieldDef` | Well-designed, preserveable | Keep as-is |
| `CASCADING_FIELD_REGISTRY` | Static, lazy-built from Business/Unit | Keep as-is |
| `CascadingFieldResolver._parent_cache` | Simple dict, per-instance | Unify with SSoT |
| `cascade:` prefix in schemas | Clean abstraction | Keep, enhance |
| `extract_async()` in BaseExtractor | Good async pattern | Keep, wire to unified cache |

**Cascade Tooling Verdict**: The cascade tooling is well-architected. The only gap is that `CascadingFieldResolver._parent_cache` is per-instance and doesn't share with `TaskCacheCoordinator`. Unification should connect these.

### Caching Infrastructure Audit

**Current Cache Hierarchy**:

```
                    ┌─────────────────────────────────────────────────┐
                    │                 TieredCacheProvider              │
                    │          (Redis hot + S3 cold, ADR-0026)         │
                    ├─────────────────────────────────────────────────┤
                    │  - Promotion on cold hit                         │
                    │  - Write-through to both tiers                   │
                    │  - CacheEntry with version/TTL                   │
                    └─────────────────────────────────────────────────┘
                                          │
          ┌───────────────────────────────┼───────────────────────────────┐
          ▼                               ▼                               ▼
┌─────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────┐
│ TaskCacheCoordinator│     │ DataFrameCacheIntegration│    │StalenessCheckCoord  │
│ (Task objects)      │     │ (Extracted rows)         │    │(TTL extension)      │
├─────────────────────┤     ├─────────────────────────┤     ├─────────────────────┤
│ EntryType.TASK      │     │ EntryType.DATAFRAME     │     │ LightweightChecker  │
│ lookup_tasks_async  │     │ get_cached_row_async    │     │ RequestCoalescer    │
│ populate_tasks_async│     │ cache_row_async         │     │ batch modified_at   │
└─────────────────────┘     └─────────────────────────┘     └─────────────────────┘
```

**Current EntryTypes** (from `cache/entry.py`):
- `TASK` - Raw task data
- `STORIES` - Task stories
- `ATTACHMENTS` - Task attachments
- `DATAFRAME` - Extracted DataFrame rows
- `CUSTOM_FIELDS` - Project custom field definitions

**Identified Redundancies**:

| Data Type | Cached In | Redundant Storage |
|-----------|-----------|-------------------|
| Task data | TaskCacheCoordinator | Also stored in DataFrameCacheIntegration as extracted rows |
| Parent tasks | CascadingFieldResolver._parent_cache | Not shared with TaskCacheCoordinator |
| modified_at | Multiple places | Queried separately by staleness coordinator |

### DataFrame Materialization Audit

**Build Methods** (from `dataframes/builders/project.py`):

1. `build_with_parallel_fetch_async()` - Main entry point:
   - Phase 1: Enumerate section GIDs (lightweight)
   - Phase 2: Batch cache lookup via `TaskCacheCoordinator`
   - Phase 3: Fetch missing tasks from API (cold/partial/warm paths)
   - Phase 4: Populate cache with fetched tasks
   - Phase 5: Extract rows using `BaseExtractor.extract_async()`
   - Cache extracted rows via `DataFrameCacheIntegration`

2. `refresh_incremental()` - Delta sync:
   - Uses `modified_since` for incremental fetch
   - Merges deltas into existing DataFrame
   - Tracks watermarks in `WatermarkRepository`

**Observation**: The two-phase cache strategy (Task cache + Row cache) creates double storage. A unified approach could store Task data once and derive rows on-demand.

### Entity Hierarchy Audit

**Hierarchy Structure**:
```
Business (root)
├── ContactHolder → Contact[]
├── UnitHolder → Unit[]
│   └── Unit
│       ├── OfferHolder → Offer[]
│       │   └── Offer
│       │       └── ProcessHolder → Process[]
│       └── ProcessHolder → Process[]
├── LocationHolder → Location[], Hours
├── DNAHolder → DNA[]
├── ReconciliationHolder → Reconciliation[]
├── AssetEditHolder → AssetEdit[]
└── VideographyHolder → Videography[]
```

**Cascading Field Flow**:
- Business owns: `OFFICE_PHONE`, `COMPANY_ID`, `BUSINESS_NAME`, `PRIMARY_CONTACT_PHONE`
- Unit owns: (via mixins) `VERTICAL`, `REP`, `BOOKING_TYPE`
- Resolution: Child → Parent → Grandparent (up to 5 levels)

**Key Insight**: All entities in a hierarchy share the root Business's `modified_at` as the staleness indicator. If `Business.modified_at` hasn't changed, the entire hierarchy is fresh.

---

## Goals and Non-Goals

### Goals

| ID | Goal | Success Metric |
|----|------|----------------|
| G1 | Single source of truth for task data | One cache entry per task GID (not per task+context) |
| G2 | DataFrame as materialized view | DataFrames derived from cached tasks, not stored separately |
| G3 | Unified parent chain cache | CascadingFieldResolver uses same cache as TaskCacheCoordinator |
| G4 | Batch freshness checks | Single batch API call validates N tasks (using Asana Batch API) |
| G5 | Configurable freshness | STRICT (always validate), EVENTUAL (TTL-based), IMMEDIATE (bypass) |
| G6 | S3-backed cold storage | 7-day retention in S3 for cold start resilience |
| G7 | Preserve cascade tooling | No changes to `cascade:` syntax or `CascadingFieldDef` semantics |
| G8 | API call reduction | 4-6 calls → 1-2 calls for warm cache path |

### Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Real-time sync | Asana webhooks are out of scope; polling-based freshness is acceptable |
| NG2 | Multi-instance consistency | Single-instance deployment assumed; distributed cache coherence deferred |
| NG3 | Schema migration automation | Schema changes require explicit cache invalidation |
| NG4 | Custom field definition caching | Out of scope; focus on task data |

---

## Proposed Architecture

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            PUBLIC API LAYER                                    │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ProjectDataFrameBuilder              Entity Resolution               Cascade │
│        │                                    │                             │   │
│        │ build_with_parallel_fetch_async()  │ resolve()        resolve_async()│
│        ▼                                    ▼                             ▼   │
│  ┌──────────────────────────────────────────────────────────────────────────┐ │
│  │                         MATERIALIZATION LAYER                            │ │
│  │                                                                          │ │
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐  │ │
│  │  │ DataFrameViewPlugin│  │ EntityViewPlugin   │  │ CascadeViewPlugin  │  │ │
│  │  │ (extracts rows)    │  │ (typed models)     │  │ (parent chains)    │  │ │
│  │  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘  │ │
│  │            │                       │                       │             │ │
│  │            ▼                       ▼                       ▼             │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐    │ │
│  │  │                      VIEW COORDINATOR                            │    │ │
│  │  │  - Configurable freshness (STRICT/EVENTUAL/IMMEDIATE)           │    │ │
│  │  │  - View-specific invalidation                                   │    │ │
│  │  │  - Lazy computation with caching                                │    │ │
│  │  └────────────────────────────────┬─────────────────────────────────┘    │ │
│  └───────────────────────────────────┼──────────────────────────────────────┘ │
│                                      │                                        │
└──────────────────────────────────────┼────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        UNIFIED CACHE LAYER                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        UnifiedTaskStore                                │  │
│  │                                                                        │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │  │
│  │  │ TaskCache        │  │ HierarchyIndex   │  │ FreshnessCoordinator │  │  │
│  │  │ (GID → TaskData) │  │ (parent→children)│  │ (batch modified_at)  │  │  │
│  │  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘  │  │
│  │           │                     │                       │              │  │
│  │           ▼                     ▼                       ▼              │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │                     CacheEntry (unified)                         │  │  │
│  │  │  - key: task_gid (NOT task_gid:project_gid)                     │  │  │
│  │  │  - data: full task payload                                       │  │  │
│  │  │  - version: modified_at                                          │  │  │
│  │  │  - metadata: {entity_type, parent_gid, project_gids[]}          │  │  │
│  │  └──────────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
│                                      ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        TieredCacheProvider (existing)                  │  │
│  │  ┌─────────────────────┐              ┌─────────────────────┐          │  │
│  │  │   Redis (hot tier)  │◄────────────►│   S3 (cold tier)    │          │  │
│  │  │   - 5 min default TTL│  promotion  │   - 7 day retention │          │  │
│  │  │   - Write-through    │             │   - Compressed      │          │  │
│  │  └─────────────────────┘              └─────────────────────┘          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Task GID as Primary Key**: Cache entries keyed by `task_gid` only, not `task_gid:project_gid`. Multi-homing tracked in metadata.

2. **Views over Storage**: DataFrames are computed views, not stored data. Extraction happens on-demand with optional row-level caching as an optimization.

3. **Hierarchy-Aware Freshness**: Parent-child relationships tracked to enable batch staleness checks per root entity.

4. **Plugin Architecture**: View types (DataFrame, Entity, Cascade) are plugins that consume the unified cache.

---

## Component Designs

### Component 1: UnifiedTaskStore

**Location**: `src/autom8_asana/cache/unified.py`

**Responsibilities**:
1. Single point of entry for all task data caching
2. Hierarchy relationship tracking
3. Batch freshness coordination
4. View invalidation signaling

**Interface**:

```python
class UnifiedTaskStore:
    """Single source of truth for task data with hierarchy awareness.

    Per TDD-UNIFIED-CACHE-001: Consolidates TaskCacheCoordinator,
    CascadingFieldResolver cache, and parent chain resolution.

    Attributes:
        cache: TieredCacheProvider (Redis + S3)
        hierarchy_index: HierarchyIndex for parent-child relationships
        freshness: FreshnessCoordinator for batch staleness checks
    """

    def __init__(
        self,
        cache: CacheProvider,
        batch_client: BatchClient | None = None,
        freshness_mode: FreshnessMode = FreshnessMode.EVENTUAL,
    ) -> None:
        """Initialize unified store with cache and freshness configuration."""
        ...

    async def get_async(
        self,
        gid: str,
        freshness: FreshnessMode | None = None,
    ) -> Task | None:
        """Get single task, respecting freshness mode.

        Args:
            gid: Task GID to retrieve.
            freshness: Override default freshness mode.

        Returns:
            Task if found and fresh, None if stale or missing.
        """
        ...

    async def get_batch_async(
        self,
        gids: list[str],
        freshness: FreshnessMode | None = None,
    ) -> dict[str, Task | None]:
        """Get multiple tasks with batch freshness check.

        Per G4: Single batch API call validates N tasks.

        Args:
            gids: Task GIDs to retrieve.
            freshness: Override default freshness mode.

        Returns:
            Dict mapping GID to Task or None.
        """
        ...

    async def put_async(
        self,
        task: Task,
        ttl: int | None = None,
    ) -> None:
        """Store task in cache with hierarchy indexing.

        Args:
            task: Task to cache.
            ttl: Optional TTL override.
        """
        ...

    async def put_batch_async(
        self,
        tasks: list[Task],
        ttl: int | None = None,
    ) -> int:
        """Store multiple tasks with batch write.

        Args:
            tasks: Tasks to cache.
            ttl: Optional TTL override.

        Returns:
            Count of successfully cached tasks.
        """
        ...

    async def get_parent_chain_async(
        self,
        gid: str,
        max_depth: int = 5,
    ) -> list[Task]:
        """Get parent chain for cascade resolution.

        Per G3: Uses same cache as task lookups.

        Args:
            gid: Starting task GID.
            max_depth: Maximum chain depth.

        Returns:
            List of parent tasks from immediate parent to root.
        """
        ...

    async def check_freshness_batch_async(
        self,
        gids: list[str],
    ) -> dict[str, bool]:
        """Batch check if cached tasks are fresh.

        Uses Asana Batch API to fetch modified_at for all GIDs
        in a single request (chunked by 10 per Asana limit).

        Args:
            gids: Task GIDs to check.

        Returns:
            Dict mapping GID to freshness status (True = fresh).
        """
        ...

    def invalidate(
        self,
        gid: str,
        cascade: bool = False,
    ) -> None:
        """Invalidate cached task.

        Args:
            gid: Task GID to invalidate.
            cascade: If True, also invalidate children.
        """
        ...
```

### Component 2: HierarchyIndex

**Location**: `src/autom8_asana/cache/hierarchy.py`

**Responsibilities**:
1. Track parent-child relationships
2. Enable cascade invalidation
3. Support upward traversal for cascade resolution

**Interface**:

```python
@dataclass
class HierarchyEntry:
    """Hierarchy relationship for a task."""
    gid: str
    parent_gid: str | None
    children_gids: set[str]
    entity_type: str | None
    root_gid: str  # Business GID for hierarchy


class HierarchyIndex:
    """Index of task hierarchy relationships.

    Maintains bidirectional parent-child mappings for efficient
    traversal in both directions. Used for cascade invalidation
    and parent chain resolution.
    """

    def __init__(self) -> None:
        """Initialize empty index."""
        self._entries: dict[str, HierarchyEntry] = {}
        self._lock = threading.Lock()

    def register(
        self,
        task: Task,
        entity_type: str | None = None,
    ) -> None:
        """Register task and update relationships.

        Args:
            task: Task to register.
            entity_type: Optional detected entity type.
        """
        ...

    def get_parent_gid(self, gid: str) -> str | None:
        """Get immediate parent GID."""
        ...

    def get_children_gids(self, gid: str) -> set[str]:
        """Get immediate children GIDs."""
        ...

    def get_ancestor_chain(
        self,
        gid: str,
        max_depth: int = 5,
    ) -> list[str]:
        """Get ancestor GIDs from parent to root."""
        ...

    def get_descendant_gids(
        self,
        gid: str,
        max_depth: int | None = None,
    ) -> set[str]:
        """Get all descendant GIDs (for cascade invalidation)."""
        ...

    def get_root_gid(self, gid: str) -> str | None:
        """Get Business root GID for this task's hierarchy."""
        ...
```

### Component 3: FreshnessCoordinator

**Location**: `src/autom8_asana/cache/freshness_coordinator.py`

**Responsibilities**:
1. Batch modified_at checks via Asana Batch API
2. Request coalescing to reduce API calls
3. Progressive TTL extension for stable data

**Interface**:

```python
class FreshnessMode(Enum):
    """Freshness validation modes."""
    STRICT = "strict"      # Always validate against API
    EVENTUAL = "eventual"  # TTL-based with lazy validation
    IMMEDIATE = "immediate"  # Return cached without validation


@dataclass
class FreshnessResult:
    """Result of freshness check."""
    gid: str
    is_fresh: bool
    cached_version: datetime | None
    current_version: datetime | None
    action: Literal["use_cache", "fetch", "extend_ttl"]


class FreshnessCoordinator:
    """Coordinates batch freshness checks.

    Replaces separate LightweightChecker + StalenessCheckCoordinator
    with a unified approach that leverages hierarchy relationships.
    """

    def __init__(
        self,
        batch_client: BatchClient,
        coalesce_window_ms: int = 50,
        max_batch_size: int = 100,
    ) -> None:
        """Initialize coordinator with batch client."""
        ...

    async def check_batch_async(
        self,
        entries: list[CacheEntry],
        mode: FreshnessMode = FreshnessMode.EVENTUAL,
    ) -> list[FreshnessResult]:
        """Check freshness for batch of cache entries.

        For EVENTUAL mode:
        1. Check if TTL expired
        2. If expired, batch fetch modified_at via Asana Batch API
        3. Compare versions and return results

        For STRICT mode:
        1. Always batch fetch modified_at
        2. Compare versions

        For IMMEDIATE mode:
        1. Return is_fresh=True without API call

        Args:
            entries: Cache entries to check.
            mode: Freshness validation mode.

        Returns:
            List of FreshnessResult with recommended actions.
        """
        ...

    async def check_hierarchy_async(
        self,
        root_gid: str,
        mode: FreshnessMode = FreshnessMode.EVENTUAL,
    ) -> FreshnessResult:
        """Check freshness using root entity's modified_at.

        Optimized path for hierarchy-aware caching. If the root
        Business hasn't changed, all descendants are fresh.

        Args:
            root_gid: Root Business GID.
            mode: Freshness validation mode.

        Returns:
            Single FreshnessResult for the entire hierarchy.
        """
        ...
```

### Component 4: DataFrameViewPlugin

**Location**: `src/autom8_asana/dataframes/views/dataframe_view.py`

**Responsibilities**:
1. Extract DataFrame rows from cached tasks
2. Apply schema-based transformation
3. Optional row-level caching as optimization

**Interface**:

```python
class DataFrameViewPlugin:
    """Materializes DataFrames from unified cache.

    Per G2: DataFrames are derived views, not stored data.
    Extraction uses existing BaseExtractor infrastructure.
    """

    def __init__(
        self,
        store: UnifiedTaskStore,
        schema: DataFrameSchema,
        resolver: CustomFieldResolver | None = None,
        row_cache: DataFrameCacheIntegration | None = None,
    ) -> None:
        """Initialize view plugin.

        Args:
            store: Unified task store for source data.
            schema: Schema for extraction.
            resolver: Custom field resolver (cf: prefix).
            row_cache: Optional row cache for optimization.
        """
        ...

    async def materialize_async(
        self,
        task_gids: list[str],
        project_gid: str | None = None,
        freshness: FreshnessMode = FreshnessMode.EVENTUAL,
    ) -> pl.DataFrame:
        """Materialize DataFrame from cached tasks.

        1. Fetch tasks from unified store (with freshness)
        2. Extract rows using schema
        3. Optionally cache extracted rows
        4. Build and return DataFrame

        Args:
            task_gids: Task GIDs to include.
            project_gid: Optional project context for section extraction.
            freshness: Freshness mode for cache lookups.

        Returns:
            Polars DataFrame with extracted data.
        """
        ...

    async def materialize_incremental_async(
        self,
        existing_df: pl.DataFrame,
        watermark: datetime,
        project_gid: str,
    ) -> tuple[pl.DataFrame, datetime]:
        """Materialize delta updates since watermark.

        1. Get changed GIDs from unified store
        2. Extract rows for changed tasks
        3. Merge with existing DataFrame
        4. Return updated DataFrame and new watermark

        Args:
            existing_df: Current DataFrame to update.
            watermark: Last sync timestamp.
            project_gid: Project context.

        Returns:
            Tuple of (updated DataFrame, new watermark).
        """
        ...
```

### Component 5: CascadeViewPlugin

**Location**: `src/autom8_asana/dataframes/views/cascade_view.py`

**Responsibilities**:
1. Resolve cascading fields using unified cache
2. Replace per-instance parent cache in CascadingFieldResolver

**Interface**:

```python
class CascadeViewPlugin:
    """Resolves cascading fields using unified cache.

    Per G3: CascadingFieldResolver uses same cache as TaskCacheCoordinator.
    Replaces the per-instance _parent_cache in CascadingFieldResolver.
    """

    def __init__(
        self,
        store: UnifiedTaskStore,
        registry: dict[str, CascadingFieldEntry] | None = None,
    ) -> None:
        """Initialize cascade plugin.

        Args:
            store: Unified task store for parent chain.
            registry: Cascading field registry (uses default if None).
        """
        ...

    async def resolve_async(
        self,
        task: Task,
        field_name: str,
        max_depth: int = 5,
    ) -> Any:
        """Resolve cascading field value.

        Uses unified store for parent chain traversal.
        Result is cached in unified store for reuse.

        Args:
            task: Starting task.
            field_name: Field to resolve (e.g., "Office Phone").
            max_depth: Maximum parent chain depth.

        Returns:
            Field value from ancestor or None.
        """
        ...

    async def prefetch_parents_async(
        self,
        tasks: list[Task],
    ) -> None:
        """Prefetch parent chains for batch efficiency.

        Collects unique parent GIDs across all tasks and
        fetches them in a single batch operation.

        Args:
            tasks: Tasks whose parents should be prefetched.
        """
        ...
```

---

## Data Flow

### Sequence: DataFrame Build with Unified Cache

```
┌──────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Caller  │     │ProjectDFBuilder  │     │DataFrameViewPlugin│    │UnifiedTaskStore │
└────┬─────┘     └────────┬─────────┘     └────────┬──────────┘    └───────┬─────────┘
     │                    │                        │                       │
     │ build_with_parallel_fetch_async()           │                       │
     │───────────────────>│                        │                       │
     │                    │                        │                       │
     │                    │ enumerate_section_gids()                       │
     │                    │────────────────────────────────────────────────────────────>
     │                    │                        │                       │   (Asana API)
     │                    │<───────────────────────────────────────────────────────────
     │                    │     {section_gid: [task_gids]}                 │
     │                    │                        │                       │
     │                    │ materialize_async(task_gids)                   │
     │                    │───────────────────────>│                       │
     │                    │                        │                       │
     │                    │                        │ get_batch_async(gids) │
     │                    │                        │──────────────────────>│
     │                    │                        │                       │
     │                    │                        │                       │──┐ check_freshness_batch
     │                    │                        │                       │<─┘
     │                    │                        │                       │
     │                    │                        │                       │ [Cache HIT for fresh]
     │                    │                        │                       │ [API fetch for stale/miss]
     │                    │                        │                       │──────────────────────────>
     │                    │                        │                       │<─────────────────────────
     │                    │                        │                       │
     │                    │                        │<──────────────────────│
     │                    │                        │   {gid: Task}         │
     │                    │                        │                       │
     │                    │                        │ extract_rows()        │
     │                    │                        │ (cascade: resolution) │
     │                    │                        │──────────────────────>│ get_parent_chain_async()
     │                    │                        │<──────────────────────│
     │                    │                        │                       │
     │                    │<───────────────────────│                       │
     │                    │   pl.DataFrame         │                       │
     │                    │                        │                       │
     │<───────────────────│                        │                       │
     │   pl.DataFrame     │                        │                       │
```

### Sequence: Cascade Field Resolution

```
┌──────────┐     ┌───────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│Extractor │     │CascadeViewPlugin  │     │UnifiedTaskStore  │     │  Asana API      │
└────┬─────┘     └─────────┬─────────┘     └────────┬─────────┘     └───────┬─────────┘
     │                     │                        │                       │
     │ resolve_async(task, "Office Phone")          │                       │
     │────────────────────>│                        │                       │
     │                     │                        │                       │
     │                     │ Check registry for field def                   │
     │                     │────┐                   │                       │
     │                     │<───┘ (Business, CascadingFieldDef)             │
     │                     │                        │                       │
     │                     │ get_parent_chain_async(task.gid)               │
     │                     │───────────────────────>│                       │
     │                     │                        │                       │
     │                     │                        │ Check hierarchy index │
     │                     │                        │────┐                  │
     │                     │                        │<───┘ parent_gid       │
     │                     │                        │                       │
     │                     │                        │ get_async(parent_gid) │
     │                     │                        │────┐                  │
     │                     │                        │<───┘ [Cache HIT]      │
     │                     │                        │                       │
     │                     │                        │  (repeat for chain)   │
     │                     │                        │                       │
     │                     │<───────────────────────│                       │
     │                     │   [UnitHolder, Business]                       │
     │                     │                        │                       │
     │                     │ Extract field from Business                    │
     │                     │────┐                   │                       │
     │                     │<───┘ "555-123-4567"    │                       │
     │                     │                        │                       │
     │<────────────────────│                        │                       │
     │   "555-123-4567"    │                        │                       │
```

---

## API Contracts

### UnifiedTaskStore Methods

| Method | Input | Output | Behavior |
|--------|-------|--------|----------|
| `get_async` | `gid: str, freshness: FreshnessMode` | `Task \| None` | Single task lookup with freshness |
| `get_batch_async` | `gids: list[str], freshness: FreshnessMode` | `dict[str, Task \| None]` | Batch lookup with single freshness check |
| `put_async` | `task: Task, ttl: int \| None` | `None` | Store task with hierarchy indexing |
| `put_batch_async` | `tasks: list[Task], ttl: int \| None` | `int` | Batch store, returns count |
| `get_parent_chain_async` | `gid: str, max_depth: int` | `list[Task]` | Ancestor chain for cascade |
| `check_freshness_batch_async` | `gids: list[str]` | `dict[str, bool]` | Batch staleness check |
| `invalidate` | `gid: str, cascade: bool` | `None` | Invalidate task (and descendants) |

### FreshnessMode Behavior

| Mode | Cache TTL Expired | Cache TTL Valid |
|------|-------------------|-----------------|
| `STRICT` | Fetch modified_at, compare | Fetch modified_at, compare |
| `EVENTUAL` | Fetch modified_at, compare | Return cached |
| `IMMEDIATE` | Return cached | Return cached |

### View Plugin Methods

| Method | Input | Output | Behavior |
|--------|-------|--------|----------|
| `materialize_async` | `gids, project_gid, freshness` | `pl.DataFrame` | Extract DataFrame from cache |
| `resolve_async` | `task, field_name, max_depth` | `Any` | Resolve cascading field |
| `prefetch_parents_async` | `tasks: list[Task]` | `None` | Batch prefetch parent chain |

---

## Migration Strategy

### Phase 1: Foundation (Non-Breaking)

**Scope**: Create new unified components without modifying existing code paths.

**Deliverables**:
1. `UnifiedTaskStore` implementation
2. `HierarchyIndex` implementation
3. `FreshnessCoordinator` implementation (replacing separate LightweightChecker + StalenessCheckCoordinator)

**Rollback**: Delete new files, no existing code modified.

### Phase 2: View Plugins (Non-Breaking)

**Scope**: Create view plugins that consume unified store.

**Deliverables**:
1. `DataFrameViewPlugin` implementation
2. `CascadeViewPlugin` implementation
3. Unit tests for all plugins

**Rollback**: Delete plugin files.

### Phase 3: Integration (Breaking Changes)

**Scope**: Wire unified store into existing components.

**Changes**:
1. `ProjectDataFrameBuilder.build_with_parallel_fetch_async()` uses `DataFrameViewPlugin`
2. `CascadingFieldResolver` delegates to `CascadeViewPlugin`
3. `TaskCacheCoordinator` becomes thin wrapper over `UnifiedTaskStore`

**Rollback**: Revert integration code, keep unified components.

### Phase 4: Deprecation

**Scope**: Mark legacy components as deprecated.

**Changes**:
1. Deprecation warnings on direct `TaskCacheCoordinator` usage
2. Deprecation warnings on per-instance `CascadingFieldResolver._parent_cache`
3. Documentation updates

### Phase 5: Removal

**Scope**: Remove deprecated code paths (future release).

**Changes**:
1. Remove `TaskCacheCoordinator` (replaced by `UnifiedTaskStore`)
2. Remove redundant `DataFrameCacheIntegration` (replaced by `DataFrameViewPlugin`)
3. Remove per-instance parent caching from `CascadingFieldResolver`

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

| Task | Description | Effort |
|------|-------------|--------|
| 1.1 | Create `UnifiedTaskStore` skeleton | 4h |
| 1.2 | Implement `HierarchyIndex` | 4h |
| 1.3 | Implement `FreshnessCoordinator` | 6h |
| 1.4 | Unit tests for foundation | 4h |
| 1.5 | Integration tests with mock data | 4h |

### Phase 2: View Plugins (Week 2)

| Task | Description | Effort |
|------|-------------|--------|
| 2.1 | Create `DataFrameViewPlugin` | 6h |
| 2.2 | Create `CascadeViewPlugin` | 4h |
| 2.3 | Wire plugins to unified store | 4h |
| 2.4 | Unit tests for plugins | 4h |
| 2.5 | Property-based tests for consistency | 4h |

### Phase 3: Integration (Week 3)

| Task | Description | Effort |
|------|-------------|--------|
| 3.1 | Modify `ProjectDataFrameBuilder` | 6h |
| 3.2 | Modify `CascadingFieldResolver` | 4h |
| 3.3 | Create `TaskCacheCoordinator` adapter | 2h |
| 3.4 | Integration tests with real hierarchy | 4h |
| 3.5 | Performance benchmarks | 4h |

### Phase 4: Documentation and Cleanup (Week 4)

| Task | Description | Effort |
|------|-------------|--------|
| 4.1 | API documentation | 4h |
| 4.2 | Migration guide | 2h |
| 4.3 | Deprecation warnings | 2h |
| 4.4 | ADR documentation | 2h |

---

## Risk Assessment

| Risk ID | Risk | Probability | Impact | Mitigation |
|---------|------|-------------|--------|------------|
| RISK-001 | Performance regression from unified cache | Medium | High | Benchmark Phase 3; maintain parallel paths |
| RISK-002 | Hierarchy index memory growth | Low | Medium | LRU eviction policy; size limits |
| RISK-003 | Freshness batch API rate limits | Medium | Medium | Request coalescing; backpressure |
| RISK-004 | Breaking change to downstream consumers | Medium | High | Phased migration; adapter pattern |
| RISK-005 | S3 latency for cold cache | Low | Low | Redis hot tier; pre-warming |
| RISK-006 | Cascade invalidation complexity | Medium | Medium | Explicit cascade=True flag; logging |

---

## ADRs

### ADR-UNIFIED-001: Single Key per Task

**Status**: Proposed

**Context**: Current architecture uses composite keys (`task_gid:project_gid`) for DataFrame cache entries, creating duplicates for multi-homed tasks.

**Decision**: Use `task_gid` as the sole cache key. Track project memberships in metadata for invalidation.

**Consequences**:
- Positive: Single storage per task, reduced redundancy
- Positive: Simpler cache key semantics
- Negative: Must track project memberships separately for invalidation
- Negative: Migration required for existing cache entries

### ADR-UNIFIED-002: Views over Storage

**Status**: Proposed

**Context**: Current approach caches both raw Task data and extracted DataFrame rows, creating redundancy and staleness issues.

**Decision**: Treat DataFrames as materialized views computed on-demand from cached Task data. Row caching is an optional optimization, not a requirement.

**Consequences**:
- Positive: Single source of truth for task data
- Positive: Consistent staleness semantics
- Positive: Reduced storage overhead
- Negative: Extraction cost on every access (mitigated by row cache optimization)
- Negative: Schema changes require re-extraction (no migration needed)

### ADR-UNIFIED-003: Hierarchy-Aware Freshness

**Status**: Proposed

**Context**: Related data (subtasks, stories, attachments) share the root task's `modified_at`. Current approach checks each task individually.

**Decision**: Track hierarchy relationships and use root entity's `modified_at` for batch staleness checks.

**Consequences**:
- Positive: Single API call validates entire hierarchy
- Positive: Reduced API calls for hierarchy-heavy operations
- Negative: Requires hierarchy index maintenance
- Negative: May return stale if child modified without parent change (rare in Asana)

---

## Success Criteria

Migration complete when:

- [ ] `UnifiedTaskStore` replaces `TaskCacheCoordinator` for task data
- [ ] `CascadeViewPlugin` replaces per-instance parent cache in `CascadingFieldResolver`
- [ ] DataFrame builds use `DataFrameViewPlugin` for extraction
- [ ] API calls reduced: 4-6 calls → 1-2 calls for warm cache path
- [ ] All existing tests pass (no regression)
- [ ] Performance benchmarks meet or exceed current latency
- [ ] Single cache entry per task GID (not per context)
- [ ] Hierarchy relationships tracked in `HierarchyIndex`
- [ ] Batch freshness checks operational via `FreshnessCoordinator`
- [ ] ruff check and mypy pass

---

## Appendices

### Appendix A: Current API Call Breakdown

**Scenario**: Build Unit DataFrame for project with 100 Units

**Before (Current Architecture)**:

| Step | API Calls | Description |
|------|-----------|-------------|
| 1 | 1 | List sections for project |
| 2 | 1 | List tasks per section (paginated) |
| 3 | 10 | Batch fetch tasks by GID (10 per batch) |
| 4 | 100 | Parent fetch for cascade resolution (worst case) |
| **Total** | **112** | |

**After (Unified Architecture)**:

| Step | API Calls | Description |
|------|-----------|-------------|
| 1 | 1 | List sections + task GIDs (cached) |
| 2 | 1 | Batch freshness check (100 GIDs, 10 per request) |
| 3 | 0-10 | Fetch stale/missing tasks only |
| **Total** | **2-12** | (Warm cache: 2, Cold cache: 12) |

### Appendix B: Cache Entry Schema

```python
@dataclass(frozen=True)
class UnifiedCacheEntry:
    """Unified cache entry for task data.

    Key: task_gid (not composite)
    """
    key: str  # task_gid only
    data: dict[str, Any]  # Full task payload
    entry_type: EntryType = EntryType.TASK
    version: datetime  # modified_at
    cached_at: datetime
    ttl: int | None
    metadata: dict[str, Any] = field(default_factory=dict)
    # Metadata includes:
    # - entity_type: str | None (Business, Unit, Offer, etc.)
    # - parent_gid: str | None
    # - project_gids: list[str] (for multi-homed tasks)
    # - root_gid: str | None (Business root for hierarchy)
```

### Appendix C: Related Existing Infrastructure

| Component | File | Relationship |
|-----------|------|--------------|
| `TieredCacheProvider` | `cache/tiered.py` | Underlying storage (kept) |
| `RedisCacheProvider` | `cache/backends/redis.py` | Hot tier (kept) |
| `S3CacheProvider` | `cache/backends/s3.py` | Cold tier (kept) |
| `CacheEntry` | `cache/entry.py` | Entry schema (extended) |
| `TaskCacheCoordinator` | `dataframes/builders/task_cache.py` | Replaced by UnifiedTaskStore |
| `DataFrameCacheIntegration` | `dataframes/cache_integration.py` | Replaced by DataFrameViewPlugin |
| `CascadingFieldResolver` | `dataframes/resolver/cascading.py` | Adapted to use CascadeViewPlugin |
| `StalenessCheckCoordinator` | `cache/staleness_coordinator.py` | Replaced by FreshnessCoordinator |
| `LightweightChecker` | `cache/lightweight_checker.py` | Absorbed into FreshnessCoordinator |
| `WatermarkRepository` | `dataframes/watermark.py` | Kept for incremental sync |

---

## Artifact Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/architecture/TDD-UNIFIED-CACHE-001.md` | Pending |
| CascadingFieldDef | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/fields.py` | Yes |
| CascadingFieldResolver | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/resolver/cascading.py` | Yes |
| TieredCacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/tiered.py` | Yes |
| TaskCacheCoordinator | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/task_cache.py` | Yes |
| DataFrameCacheIntegration | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/cache_integration.py` | Yes |
| ProjectDataFrameBuilder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py` | Yes |
| Business model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py` | Yes |
| UNIT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/unit.py` | Yes |

---

**End of TDD**
