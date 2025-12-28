# Search Query Builder Guide

Find Asana entities by field values using the Search Interface v2.0.

**Prerequisites**: Read [Core Concepts](concepts.md) to understand the SDK mental model.

---

## Introduction

The Search Interface provides field-based GID lookup from cached project DataFrames. Use it when you need to find entities by custom field values rather than iterating through all tasks.

**When to use Search**:
- Finding entities by phone number, email, or other identifiers
- Filtering entities by status, vertical, or category
- Looking up entities by any custom field value

**Performance**: Sub-millisecond query execution on cached DataFrames using Polars filter expressions.

---

## Quick Start

Find entities matching field values in under 30 seconds:

```python
import asyncio
from autom8_asana import AsanaClient

async def search_example():
    async with AsanaClient() as client:
        # Find all entities where Vertical = "Medical"
        result = await client.search.find_async(
            "1143843662099250",  # project_gid
            {"Vertical": "Medical"}
        )

        print(f"Found {result.total_count} matches")
        for hit in result.hits:
            print(f"  {hit.gid}: {hit.name}")

asyncio.run(search_example())
```

**Output**:
```
Found 4 matches
  task1: Medical Clinic Offer
  task2: Dental Practice Unit
  task3: Healthcare Business
  task5: Medical Lab Unit
```

---

## Basic Usage

### Finding Entities by Field Value

Pass a dictionary of field-value pairs. All conditions combine with AND logic.

```python
# Single field match
result = await client.search.find_async(
    project_gid,
    {"Vertical": "Medical"}
)

# Multiple fields (AND matching)
result = await client.search.find_async(
    project_gid,
    {"Vertical": "Medical", "Status": "Active"}
)
```

### Using Convenience Methods

Entity-typed methods filter by type and return GID lists directly. Use snake_case for field names.

```python
# Find Offer GIDs by field values
offer_gids = await client.search.find_offers_async(
    project_gid,
    office_phone="555-1234",
    vertical="Medical"
)

# Find Unit GIDs
unit_gids = await client.search.find_units_async(
    project_gid,
    status="Active"
)

# Find Business GIDs
business_gids = await client.search.find_businesses_async(
    project_gid,
    region="West"
)
```

**Field name conversion**: Snake_case kwargs convert to Title Case automatically. `office_phone` matches the column `Office Phone`.

---

## Advanced Usage

### SearchCriteria for Complex Queries

Build explicit criteria for more control:

```python
from autom8_asana.search import SearchCriteria, FieldCondition

criteria = SearchCriteria(
    project_gid="1143843662099250",
    conditions=[
        FieldCondition(field="Vertical", value="Medical"),
        FieldCondition(field="Status", value="Active"),
    ],
    combinator="AND",
    entity_type="Offer",
    limit=10
)

result = await client.search.find_async(project_gid, criteria)
```

### FieldCondition Operators

Three operators control how values match:

| Operator | Use Case | Example |
|----------|----------|---------|
| `eq` | Exact match (default) | `FieldCondition(field="Status", value="Active")` |
| `contains` | Substring match | `FieldCondition(field="Name", value="Clinic", operator="contains")` |
| `in` | Value in list | `FieldCondition(field="Status", value=["Active", "Pending"], operator="in")` |

```python
# Find entities with "Clinic" in the name
criteria = SearchCriteria(
    project_gid=project_gid,
    conditions=[
        FieldCondition(field="Name", value="Clinic", operator="contains")
    ]
)

# Find entities in any of several statuses
criteria = SearchCriteria(
    project_gid=project_gid,
    conditions=[
        FieldCondition(field="Status", value=["Active", "Pending", "Review"], operator="in")
    ]
)
```

### Limiting Results

Control the maximum number of results:

```python
# Get first 5 matches
result = await client.search.find_async(
    project_gid,
    {"Vertical": "Medical"},
    limit=5
)
```

### Entity Type Filtering

Filter by entity type without using convenience methods:

```python
# Only Offers matching criteria
result = await client.search.find_async(
    project_gid,
    {"Vertical": "Medical"},
    entity_type="Offer"
)
```

---

## Working with Results

### SearchResult Structure

Every search returns a `SearchResult` with metadata:

```python
result = await client.search.find_async(project_gid, criteria)

print(f"Matches: {result.total_count}")
print(f"Query time: {result.query_time_ms:.2f}ms")
print(f"From cache: {result.from_cache}")
```

### SearchHit Structure

Each match is a `SearchHit` with entity details:

```python
for hit in result.hits:
    print(f"GID: {hit.gid}")
    print(f"Name: {hit.name}")
    print(f"Type: {hit.entity_type}")
    print(f"Matched fields: {hit.matched_fields}")
```

The `matched_fields` dictionary shows which criteria values matched:

```python
# After searching {"Vertical": "Medical", "Status": "Active"}
# hit.matched_fields = {"Vertical": "Medical", "Status": "Active"}
```

---

## Async vs Sync APIs

### Async (Recommended)

Use async methods for production code:

```python
async def process_search():
    async with AsanaClient() as client:
        result = await client.search.find_async(project_gid, criteria)
        hit = await client.search.find_one_async(project_gid, criteria)
        gids = await client.search.find_offers_async(project_gid, vertical="Medical")
```

### Sync Wrappers

Sync methods available for scripts and testing:

```python
result = client.search.find(project_gid, criteria)
hit = client.search.find_one(project_gid, criteria)
gids = client.search.find_offers(project_gid, vertical="Medical")
```

---

## Error Handling

### Graceful Degradation

The Search API returns empty results instead of raising exceptions for most errors:

```python
# No cached DataFrame - returns empty result
result = await client.search.find_async(
    "uncached_project",
    {"Field": "value"}
)
assert result.total_count == 0
assert result.from_cache is False
```

### Multiple Match Detection

`find_one_async` raises `ValueError` when multiple matches exist:

```python
try:
    hit = await client.search.find_one_async(
        project_gid,
        {"Vertical": "Medical"}  # Matches multiple entities
    )
except ValueError as e:
    # "Multiple matches found (4). Use find_async() for queries with multiple results."
    result = await client.search.find_async(project_gid, {"Vertical": "Medical"})
```

### Debug Logging

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger("autom8_asana.search.service").setLevel(logging.DEBUG)
```

---

## Related Documentation

- [Search API Reference](../reference/REF-search-api.md): Complete method signatures and parameters
- [Search Cookbook](search-cookbook.md): Common patterns and recipes
- [Migration Guide](../migration/MIGRATION-search-v2.md): Upgrading from prior patterns
