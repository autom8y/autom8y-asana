# Search API Reference

Complete API reference for the Search Interface v2.0.

**Module**: `autom8_asana.search`

**Public Exports**: `SearchService`, `SearchCriteria`, `SearchResult`, `SearchHit`, `FieldCondition`

---

## Overview

The Search API provides field-based entity lookup from cached Polars DataFrames. It uses vectorized filter expressions for sub-millisecond query performance.

**Key characteristics**:
- Project-scoped: All searches require a `project_gid`
- Async-first: Primary API is async with sync wrappers
- Graceful degradation: Returns empty results on errors instead of raising
- Automatic caching: 5-minute TTL for project DataFrames

```python
from autom8_asana.search import (
    SearchService,
    SearchCriteria,
    SearchResult,
    SearchHit,
    FieldCondition,
)
```

---

## SearchService

Primary interface for search operations. Accessed via `AsanaClient.search`.

### Constructor

```python
SearchService(
    cache: CacheProvider,
    dataframe_integration: DataFrameCacheIntegration | None = None
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `cache` | `CacheProvider` | Cache provider for storage operations |
| `dataframe_integration` | `DataFrameCacheIntegration` | Optional DataFrame cache integration |

Typically instantiated automatically via `AsanaClient`.

---

### Primary Methods

#### find_async

Find entities matching criteria.

```python
async def find_async(
    project_gid: str,
    criteria: dict[str, str] | SearchCriteria,
    *,
    entity_type: str | None = None,
    limit: int | None = None,
) -> SearchResult
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_gid` | `str` | Required | Project GID to search within |
| `criteria` | `dict[str, str]` or `SearchCriteria` | Required | Field-value pairs or SearchCriteria object |
| `entity_type` | `str` | `None` | Filter by entity type (e.g., "Offer", "Unit") |
| `limit` | `int` | `None` | Maximum results to return |

**Returns**: `SearchResult` with matching entities and metadata.

**Example**:

```python
# Simple dict criteria (AND matching)
result = await client.search.find_async(
    "1143843662099250",
    {"Vertical": "Medical", "Status": "Active"}
)

for hit in result.hits:
    print(f"{hit.gid}: {hit.name}")

# With entity type filter and limit
result = await client.search.find_async(
    "1143843662099250",
    {"Vertical": "Medical"},
    entity_type="Offer",
    limit=10
)
```

---

#### find_one_async

Find a single entity matching criteria.

```python
async def find_one_async(
    project_gid: str,
    criteria: dict[str, str],
    *,
    entity_type: str | None = None,
) -> SearchHit | None
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_gid` | `str` | Required | Project GID to search within |
| `criteria` | `dict[str, str]` | Required | Field-value pairs for matching |
| `entity_type` | `str` | `None` | Filter by entity type |

**Returns**: `SearchHit` if exactly one match, `None` if no match.

**Raises**: `ValueError` if multiple matches found.

**Example**:

```python
# Find single entity by unique field
hit = await client.search.find_one_async(
    "1143843662099250",
    {"Office Phone": "555-1234"}
)

if hit:
    print(f"Found: {hit.gid}")
else:
    print("No match found")
```

---

#### find / find_one

Synchronous wrappers for `find_async` and `find_one_async`. Same signatures and behavior.

```python
result = client.search.find("proj123", {"Vertical": "Medical"})
hit = client.search.find_one("proj123", {"Phone": "555-1234"})
```

---

### Convenience Methods

Entity-typed methods that return GID lists directly. Field names use snake_case kwargs that are automatically converted to Title Case.

#### find_offers_async

```python
async def find_offers_async(
    project_gid: str,
    **field_values: str
) -> list[str]
```

Filters by `entity_type="Offer"` and returns GIDs.

**Example**:

```python
# snake_case "office_phone" matches column "Office Phone"
gids = await client.search.find_offers_async(
    "1143843662099250",
    office_phone="555-1234",
    vertical="Medical"
)
```

#### find_units_async

```python
async def find_units_async(
    project_gid: str,
    **field_values: str
) -> list[str]
```

Filters by `entity_type="Unit"` and returns GIDs.

#### find_businesses_async

```python
async def find_businesses_async(
    project_gid: str,
    **field_values: str
) -> list[str]
```

Filters by `entity_type="Business"` and returns GIDs.

#### Sync Variants

All convenience methods have sync wrappers:

```python
gids = client.search.find_offers("proj123", vertical="Medical")
gids = client.search.find_units("proj123", status="Active")
gids = client.search.find_businesses("proj123", region="West")
```

---

### Cache Management

#### set_project_dataframe

Pre-populate the search cache with a DataFrame.

```python
def set_project_dataframe(project_gid: str, df: pl.DataFrame) -> None
```

**Example**:

```python
# After building DataFrame via ProjectDataFrameBuilder
df = await builder.build_with_parallel_fetch_async(client)
client.search.set_project_dataframe(project_gid, df)

# Now searches use the cached DataFrame
result = await client.search.find_async(project_gid, {"Status": "Active"})
```

#### clear_project_cache

Clear cached DataFrames.

```python
def clear_project_cache(project_gid: str | None = None) -> None
```

| Parameter | Effect |
|-----------|--------|
| Specific GID | Clears that project's cache |
| `None` | Clears all project caches |

#### DEFAULT_PROJECT_DF_TTL

Class constant: `300` (5 minutes). Cached DataFrames expire after this duration.

---

## Model Classes

### FieldCondition

Single field condition for search queries.

```python
class FieldCondition(BaseModel):
    field: str
    value: str | list[str]
    operator: Literal["eq", "contains", "in"] = "eq"
```

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `field` | `str` | Required | Field name to match |
| `value` | `str` or `list[str]` | Required | Value(s) to match |
| `operator` | `str` | `"eq"` | Match operator |

**Operators**:

| Operator | Behavior | Example Value |
|----------|----------|---------------|
| `eq` | Exact equality match | `"Medical"` or `["Medical", "Dental"]` |
| `contains` | Substring match | `"Clinic"` |
| `in` | Value in list | `["Active", "Pending"]` |

**Examples**:

```python
# Exact match
FieldCondition(field="Vertical", value="Medical")

# Substring search
FieldCondition(field="Name", value="Clinic", operator="contains")

# Multiple values (OR within field)
FieldCondition(field="Status", value=["Active", "Pending"], operator="in")
```

---

### SearchCriteria

Query specification for complex searches.

```python
class SearchCriteria(BaseModel):
    conditions: list[FieldCondition] = []
    combinator: Literal["AND", "OR"] = "AND"
    project_gid: str
    entity_type: str | None = None
    limit: int | None = None
```

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `conditions` | `list[FieldCondition]` | `[]` | List of field conditions |
| `combinator` | `str` | `"AND"` | How to combine conditions |
| `project_gid` | `str` | Required | Project to search |
| `entity_type` | `str` | `None` | Entity type filter |
| `limit` | `int` | `None` | Maximum results |

**Example**:

```python
criteria = SearchCriteria(
    project_gid="1143843662099250",
    conditions=[
        FieldCondition(field="Vertical", value="Medical"),
        FieldCondition(field="Status", value=["Active", "Pending"], operator="in"),
    ],
    combinator="AND",
    entity_type="Offer",
    limit=50
)

result = await client.search.find_async("1143843662099250", criteria)
```

---

### SearchHit

Single search result.

```python
class SearchHit(BaseModel):
    gid: str
    entity_type: str | None = None
    name: str | None = None
    matched_fields: dict[str, str] = {}
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `gid` | `str` | Entity GID |
| `entity_type` | `str` | Entity type if detected |
| `name` | `str` | Entity name if available |
| `matched_fields` | `dict[str, str]` | Field names to matched values |

**Example**:

```python
for hit in result.hits:
    print(f"GID: {hit.gid}")
    print(f"Type: {hit.entity_type}")
    print(f"Name: {hit.name}")
    print(f"Matched: {hit.matched_fields}")
```

---

### SearchResult

Aggregated search results with metadata.

```python
class SearchResult(BaseModel):
    hits: list[SearchHit] = []
    total_count: int = 0
    query_time_ms: float = 0.0
    from_cache: bool = False
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `hits` | `list[SearchHit]` | Matching entities |
| `total_count` | `int` | Number of matches |
| `query_time_ms` | `float` | Query execution time in milliseconds |
| `from_cache` | `bool` | Whether results came from cached DataFrame |

**Example**:

```python
result = await client.search.find_async(project_gid, criteria)

print(f"Found {result.total_count} matches in {result.query_time_ms:.2f}ms")
print(f"From cache: {result.from_cache}")

for hit in result.hits:
    print(f"  - {hit.gid}: {hit.name}")
```

---

## Field Name Normalization

The search API automatically normalizes field names for flexible matching.

### Case-Insensitive Matching

Field names match regardless of case:

```python
# All match column "Vertical"
{"Vertical": "Medical"}
{"vertical": "Medical"}
{"VERTICAL": "Medical"}
```

### Snake Case to Title Case

Convenience method kwargs convert snake_case to Title Case:

```python
# "office_phone" matches column "Office Phone"
await client.search.find_offers_async(
    project_gid,
    office_phone="555-1234"
)
```

**Conversion examples**:

| Kwarg | Matches Column |
|-------|----------------|
| `vertical` | `Vertical` |
| `office_phone` | `Office Phone` |
| `due_date` | `Due Date` |

---

## Error Handling

### Graceful Degradation

The Search API returns empty results rather than raising exceptions for most errors:

- Cache miss: Returns empty `SearchResult` with `from_cache=False`
- Invalid field name: Condition ignored, other conditions still apply
- Empty criteria: Returns empty result

```python
# No exception - returns empty result
result = await client.search.find_async(
    "nonexistent_project",
    {"Field": "value"}
)
assert result.total_count == 0
```

### Explicit Errors

`find_one_async` raises `ValueError` when multiple matches exist:

```python
try:
    hit = await client.search.find_one_async(
        project_gid,
        {"Vertical": "Medical"}  # Multiple matches
    )
except ValueError as e:
    print(f"Use find_async instead: {e}")
```

### Logging

Enable debug logging for search diagnostics:

```python
import logging
logging.getLogger("autom8_asana.search.service").setLevel(logging.DEBUG)
```

---

## Related Documentation

- [User Guide](../guides/search-query-builder.md): Getting started and tutorials
- [Cookbook](../guides/search-cookbook.md): Common patterns and recipes
- [Migration Guide](../migration/MIGRATION-search-v2.md): Upgrading from prior patterns
