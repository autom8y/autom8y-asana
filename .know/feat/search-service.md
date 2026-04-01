---
domain: feat/search-service
generated_at: "2026-04-01T18:15:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/search/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Search Service over Cached DataFrames

## Purpose and Design Rationale

Lightweight, project-scoped lookup layer over cached Polars DataFrames. Translates field-value criteria into vectorized Polars filter expressions and returns matching entity GIDs without any Asana API calls.

**Separate from `query/`**: The query engine is a general-purpose composable engine for S2S consumers (RowsRequest, AggregateRequest, predicate AST). The search service targets a narrower pattern: SDK consumers with a `project_gid` looking up GIDs by field values. Does not import from `query/` at all.

**ADR-SEARCH-001**: Uses Polars filter expressions (not a separate inverted index). DataFrame already in memory; scanning is cheaper than maintaining a secondary structure.

## Conceptual Model

### Two-Tier Internal Cache

**Tier 1**: In-memory dict `_project_df_cache: dict[str, tuple[pl.DataFrame, float]]` keyed by `project_gid`. TTL: 5 minutes. Plain Python dict on service instance.

**Tier 2**: `DataFrameCacheIntegration` (injected, optional). Currently **not used** to retrieve DataFrames -- `_get_project_df_async` returns `(None, False)` on cache miss. Callers must pre-populate via `set_project_dataframe()`.

### Search Flow

```
find_async(project_gid, criteria)
  -> _get_project_df_async (check TTL cache)
  -> normalize criteria -> FieldCondition list
  -> _build_column_index (NameNormalizer on each col)
  -> _build_filter_expr (condition_to_expr per operator, AND-combined)
  -> optional entity_type filter (looks for type/entity_type/resource_subtype cols)
  -> df.filter(expr) -> head(limit) -> _extract_hits -> SearchResult
```

### Operators

`eq` (equality; list becomes `is_in`), `contains` (substring; list becomes OR `str.contains`), `in` (value-in-list). Multiple conditions AND-combined. OR combinator declared in model but **not implemented**.

### Convenience Methods

`find_offers_async`, `find_units_async`, `find_businesses_async` -- kwargs API with `snake_case` -> `"Title Case"` normalization, hardcoded entity_type. Return `list[str]` (GIDs only).

## Implementation Map

| File | Role |
|------|------|
| `src/autom8_asana/search/service.py` | `SearchService` (~750 lines): find_async, find_one_async, convenience methods, set_project_dataframe, clear_project_cache, internal filter/extract helpers |
| `src/autom8_asana/search/models.py` | `FieldCondition`, `SearchCriteria`, `SearchHit`, `SearchResult` (all Pydantic models) |
| `src/autom8_asana/search/__init__.py` | Explicit `__all__` with 5 public symbols |
| `src/autom8_asana/client.py:643-686` | `AsanaClient.search` property: lazy-init with `_search_lock`, TYPE_CHECKING import |

### Dependencies

`polars` (filter execution), `autom8_asana.dataframes.resolver.normalizer.NameNormalizer` (field name normalization, LRU-cached maxsize=1024).

## Boundaries and Failure Modes

### Does Not

- Build DataFrames (callers must pre-populate via `set_project_dataframe()`)
- Call Asana API (zero HTTP calls)
- Persist state (in-memory only, lost on process restart)
- Implement OR combination (model field exists, no code path)
- Implement aggregate queries (that's `query/engine.py`)

### Failure Modes

| Scenario | Behavior |
|----------|----------|
| project_gid not in cache | Empty SearchResult (from_cache=False) |
| Cache TTL expired | Entry evicted, empty result |
| Field name not found | Condition silently dropped |
| Polars error during filter | Caught by broad except, warning logged, empty result |
| find_one_async >1 result | Raises ValueError |
| Sync wrappers in async context | `RuntimeError` from `asyncio.run()` (NOT `SyncInAsyncContextError`) |

### Hollow `DataFrameCacheIntegration`

The injected `_df_integration` is structurally present but functionally dormant. `_get_project_df_async` has no path to invoke it. This is acknowledged in source comments.

## Knowledge Gaps

1. OR combinator unimplemented despite model declaration.
2. `DataFrameCacheIntegration` role in search is hollow -- no activation code path.
3. No test files observed for `search/`.
4. `set_project_dataframe()` usage sites not traced -- unclear which callers pre-populate.
5. Sync wrappers use `asyncio.run()` directly (not `@async_method` convention).
