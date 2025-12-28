# Migration Guide: Search Interface v2.0

Upgrade from prior search patterns to the new SearchService API.

---

## What's New in Search v2.0

The Search Interface v2.0 provides a unified API for field-based entity lookup:

| Feature | Description |
|---------|-------------|
| **SearchService** | Single entry point for all search operations |
| **Polars-backed** | Vectorized filter expressions for sub-millisecond performance |
| **Async-first** | Primary API is async with sync wrappers |
| **Field normalization** | Automatic case-insensitive and snake_case matching |
| **Graceful degradation** | Empty results on errors instead of exceptions |
| **Entity convenience methods** | `find_offers_async()`, `find_units_async()`, `find_businesses_async()` |

---

## Breaking Changes

**None.** Search v2.0 is a new feature. Existing code continues to work.

If you were using manual DataFrame filtering or loop-based searching, the new API offers a cleaner, faster alternative.

---

## Migration Paths

### From Manual DataFrame Filtering

**Before** (direct Polars filter expressions):

```python
import polars as pl

# Build DataFrame
df = await builder.build_with_parallel_fetch_async(client)

# Manual filter
medical_offers = df.filter(
    (pl.col("Vertical") == "Medical") &
    (pl.col("type") == "Offer")
)

# Extract GIDs
gids = medical_offers["gid"].to_list()
```

**After** (SearchService):

```python
# Cache DataFrame for search
client.search.set_project_dataframe(project_gid, df)

# Use SearchService
result = await client.search.find_async(
    project_gid,
    {"Vertical": "Medical"},
    entity_type="Offer"
)

gids = [hit.gid for hit in result.hits]
```

**Benefits**:
- Automatic field name normalization
- Consistent return types (`SearchResult`, `SearchHit`)
- Query timing and cache status metadata
- Graceful error handling

---

### From Loop-Based Searching

**Before** (iterating tasks):

```python
# Fetch all tasks
tasks = await client.tasks.find_all_async(project_gid)

# Filter in Python
matching = []
for task in tasks:
    if task.custom_fields.get("Vertical") == "Medical":
        if task.custom_fields.get("Status") == "Active":
            matching.append(task.gid)
```

**After** (SearchService):

```python
# Build and cache DataFrame (typically done once)
df = await builder.build_with_parallel_fetch_async(client)
client.search.set_project_dataframe(project_gid, df)

# Search with criteria
result = await client.search.find_async(
    project_gid,
    {"Vertical": "Medical", "Status": "Active"}
)

matching = [hit.gid for hit in result.hits]
```

**Benefits**:
- Vectorized operations instead of Python loops
- Sub-millisecond performance vs. per-task iteration
- Cached DataFrame reuse across multiple searches

---

### From No Search (Getting Started)

If you are new to searching in autom8_asana:

1. **Build a project DataFrame** using `ProjectDataFrameBuilder`
2. **Cache it** with `client.search.set_project_dataframe()`
3. **Search** with `client.search.find_async()` or convenience methods

```python
from autom8_asana import AsanaClient
from autom8_asana.dataframes import ProjectDataFrameBuilder

async def main():
    async with AsanaClient() as client:
        # Step 1: Build DataFrame
        builder = ProjectDataFrameBuilder(project_gid, schema=your_schema)
        df = await builder.build_with_parallel_fetch_async(client)

        # Step 2: Cache for search
        client.search.set_project_dataframe(project_gid, df)

        # Step 3: Search
        result = await client.search.find_async(
            project_gid,
            {"Status": "Active"}
        )

        for hit in result.hits:
            print(f"{hit.gid}: {hit.name}")
```

See [Search Query Builder Guide](../guides/search-query-builder.md) for complete usage.

---

## API Mapping Table

| Old Pattern | New Pattern |
|-------------|-------------|
| `df.filter(pl.col("Field") == val)` | `search.find_async(project_gid, {"Field": val})` |
| `df.filter(...).select("gid").to_list()` | `[hit.gid for hit in result.hits]` |
| `for task in tasks: if task.field == val` | `search.find_async(project_gid, {"field": val})` |
| Manual entity type check | `entity_type="Offer"` parameter |
| `df.head(n)` after filter | `limit=n` parameter |
| Column case matching | Automatic normalization |

---

## Cache Pre-Population

The SearchService requires a cached DataFrame to search. Two approaches:

### Automatic (via DataFrameCacheIntegration)

If configured, SearchService can access the DataFrame cache layer. Typically done during client initialization.

### Manual (Recommended)

Pre-populate after building:

```python
# After building DataFrame
df = await builder.build_with_parallel_fetch_async(client)

# Cache for search (5-minute TTL)
client.search.set_project_dataframe(project_gid, df)

# Clear when done or before rebuild
client.search.clear_project_cache(project_gid)
```

**TTL**: Cached DataFrames expire after 300 seconds (5 minutes). The constant is `SearchService.DEFAULT_PROJECT_DF_TTL`.

---

## Testing Your Migration

### Validation Checklist

- [ ] Build DataFrame successfully
- [ ] Cache DataFrame with `set_project_dataframe()`
- [ ] Verify `find_async()` returns expected results
- [ ] Confirm `from_cache=True` in SearchResult
- [ ] Test field name normalization (snake_case, case-insensitive)
- [ ] Verify convenience methods (`find_offers_async`, etc.)

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Empty results | DataFrame not cached | Call `set_project_dataframe()` |
| Empty results | Wrong project_gid | Verify GID matches cached DataFrame |
| Field not matching | Spelling mismatch | Check exact column name in DataFrame |
| Multiple matches | find_one_async with non-unique field | Use find_async instead |
| Stale results | Cache expired (TTL) | Rebuild and re-cache DataFrame |

### Debug Logging

Enable debug logging to trace search operations:

```python
import logging
logging.getLogger("autom8_asana.search.service").setLevel(logging.DEBUG)
```

---

## Related Documentation

- [Search Query Builder Guide](../guides/search-query-builder.md): Getting started
- [Search API Reference](../reference/REF-search-api.md): Complete method signatures
- [Search Cookbook](../guides/search-cookbook.md): Common patterns and recipes
