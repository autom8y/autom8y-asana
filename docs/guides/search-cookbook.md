# Search Cookbook

Copy-paste recipes for common search scenarios.

**Prerequisites**: Familiarity with [Search Query Builder Guide](search-query-builder.md).

---

## Common Patterns

### Find Entity by Phone Number

CRM-style lookup by unique identifier:

```python
import asyncio
from autom8_asana import AsanaClient

async def find_by_phone(project_gid: str, phone: str):
    async with AsanaClient() as client:
        hit = await client.search.find_one_async(
            project_gid,
            {"Office Phone": phone}
        )

        if hit:
            print(f"Found: {hit.gid} - {hit.name}")
            return hit.gid
        else:
            print(f"No entity with phone {phone}")
            return None

# Usage
gid = asyncio.run(find_by_phone("proj123", "555-1234"))
```

**Handling multiple matches**: If the phone number is not unique, use `find_async` instead:

```python
async def find_all_by_phone(project_gid: str, phone: str):
    async with AsanaClient() as client:
        result = await client.search.find_async(
            project_gid,
            {"Office Phone": phone}
        )

        if result.total_count > 1:
            print(f"Warning: {result.total_count} entities share phone {phone}")

        return [hit.gid for hit in result.hits]
```

---

### Find All Active Offers in a Vertical

Pipeline filtering with compound criteria:

```python
async def find_active_medical_offers(project_gid: str):
    async with AsanaClient() as client:
        result = await client.search.find_async(
            project_gid,
            {"Vertical": "Medical", "Status": "Active"},
            entity_type="Offer"
        )

        print(f"Found {result.total_count} active Medical offers")

        for hit in result.hits:
            print(f"  {hit.gid}: {hit.name}")
            print(f"    Matched: {hit.matched_fields}")

        return [hit.gid for hit in result.hits]
```

**Using convenience method**:

```python
async def find_active_medical_offers_simple(project_gid: str):
    async with AsanaClient() as client:
        gids = await client.search.find_offers_async(
            project_gid,
            vertical="Medical",
            status="Active"
        )
        return gids
```

---

### Find Single Entity by Unique Identifier

Lookup by a field that should be unique:

```python
async def find_by_unique_id(project_gid: str, unique_id: str):
    async with AsanaClient() as client:
        try:
            hit = await client.search.find_one_async(
                project_gid,
                {"Unique ID": unique_id}
            )

            if hit is None:
                print(f"No entity with ID {unique_id}")
                return None

            return hit.gid

        except ValueError as e:
            # Multiple matches - data integrity issue
            print(f"ERROR: Multiple entities share ID {unique_id}")
            raise
```

---

### Search Multiple Values (OR Within Field)

Find entities in any of several statuses:

```python
from autom8_asana.search import SearchCriteria, FieldCondition

async def find_actionable_offers(project_gid: str):
    async with AsanaClient() as client:
        criteria = SearchCriteria(
            project_gid=project_gid,
            conditions=[
                FieldCondition(
                    field="Status",
                    value=["Active", "Pending", "Review"],
                    operator="in"
                )
            ],
            entity_type="Offer"
        )

        result = await client.search.find_async(project_gid, criteria)

        print(f"Found {result.total_count} actionable offers")
        return [hit.gid for hit in result.hits]
```

---

### Substring Matching

Find entities with partial name match:

```python
from autom8_asana.search import SearchCriteria, FieldCondition

async def find_clinics(project_gid: str):
    async with AsanaClient() as client:
        criteria = SearchCriteria(
            project_gid=project_gid,
            conditions=[
                FieldCondition(
                    field="Name",
                    value="Clinic",
                    operator="contains"
                )
            ]
        )

        result = await client.search.find_async(project_gid, criteria)

        for hit in result.hits:
            print(f"{hit.gid}: {hit.name}")

        return result.hits
```

**Performance note**: Substring matching is slower than exact match. For large DataFrames, prefer exact match when possible.

---

### Pre-populating Cache for Batch Operations

When running multiple searches against the same project:

```python
import polars as pl

async def batch_search_workflow(project_gid: str, phone_numbers: list[str]):
    async with AsanaClient() as client:
        # Step 1: Build and cache DataFrame once
        df = await build_project_dataframe(client, project_gid)  # Your builder logic
        client.search.set_project_dataframe(project_gid, df)

        # Step 2: Run multiple searches (all use cached DataFrame)
        results = {}
        for phone in phone_numbers:
            hit = await client.search.find_one_async(
                project_gid,
                {"Office Phone": phone}
            )
            if hit:
                results[phone] = hit.gid

        print(f"Matched {len(results)}/{len(phone_numbers)} phone numbers")
        return results
```

---

## Integration Patterns

### Search + Update Workflow

Find entities, modify them, and save:

```python
from autom8_asana.persistence import SaveSession

async def update_vertical_status(project_gid: str, vertical: str, new_status: str):
    async with AsanaClient() as client:
        # Step 1: Search for entities
        result = await client.search.find_async(
            project_gid,
            {"Vertical": vertical},
            entity_type="Offer"
        )

        if result.total_count == 0:
            print(f"No offers in vertical {vertical}")
            return

        print(f"Updating {result.total_count} offers")

        # Step 2: Fetch full entities and update
        async with SaveSession(client) as session:
            for hit in result.hits:
                task = await client.tasks.get_async(hit.gid)
                session.track(task)
                # Update custom field (varies by your schema)
                task.custom_fields["Status"] = new_status

            save_result = await session.commit_async()

            if save_result.success:
                print(f"Updated {result.total_count} offers to status {new_status}")
            else:
                print(f"Failed: {save_result.failed}")
```

---

### Search with DataFrame Builder

Build DataFrame, cache it, search multiple times:

```python
async def search_with_fresh_data(project_gid: str):
    async with AsanaClient() as client:
        # Step 1: Build fresh DataFrame (using your project's builder)
        from autom8_asana.dataframes import ProjectDataFrameBuilder

        builder = ProjectDataFrameBuilder(project_gid, schema=your_schema)
        df = await builder.build_with_parallel_fetch_async(client)

        # Step 2: Cache for search
        client.search.set_project_dataframe(project_gid, df)

        # Step 3: Run searches
        medical = await client.search.find_offers_async(
            project_gid,
            vertical="Medical"
        )
        dental = await client.search.find_offers_async(
            project_gid,
            vertical="Dental"
        )

        print(f"Medical: {len(medical)}, Dental: {len(dental)}")
```

---

## Performance Tips

### Cache Pre-Population

For repeated searches on the same project:

```python
# BAD: Each search may rebuild DataFrame
for phone in phone_list:
    result = await client.search.find_async(project_gid, {"Phone": phone})

# GOOD: Build once, search many times
df = await builder.build_with_parallel_fetch_async(client)
client.search.set_project_dataframe(project_gid, df)

for phone in phone_list:
    result = await client.search.find_async(project_gid, {"Phone": phone})
```

### Batch Criteria vs Multiple Searches

When checking multiple values for the same field:

```python
# LESS EFFICIENT: Multiple searches
for status in ["Active", "Pending", "Review"]:
    result = await client.search.find_async(project_gid, {"Status": status})
    process(result)

# MORE EFFICIENT: Single search with IN operator
from autom8_asana.search import SearchCriteria, FieldCondition

criteria = SearchCriteria(
    project_gid=project_gid,
    conditions=[
        FieldCondition(
            field="Status",
            value=["Active", "Pending", "Review"],
            operator="in"
        )
    ]
)
result = await client.search.find_async(project_gid, criteria)
```

### Async for Concurrent Operations

Run independent searches in parallel:

```python
import asyncio

async def parallel_searches(project_gid: str):
    async with AsanaClient() as client:
        # Run all searches concurrently
        results = await asyncio.gather(
            client.search.find_offers_async(project_gid, vertical="Medical"),
            client.search.find_offers_async(project_gid, vertical="Dental"),
            client.search.find_units_async(project_gid, status="Active"),
        )

        medical_offers, dental_offers, active_units = results
        print(f"Medical: {len(medical_offers)}, Dental: {len(dental_offers)}, Active Units: {len(active_units)}")
```

---

## Troubleshooting

### Empty Results When Expecting Matches

**Check field name casing**: Field names are normalized, but verify spelling:

```python
# These all match column "Office Phone"
{"Office Phone": "555-1234"}
{"office_phone": "555-1234"}
{"office phone": "555-1234"}
```

**Verify DataFrame is cached**: Check if the project has a cached DataFrame:

```python
# Returns from_cache=False if no DataFrame cached
result = await client.search.find_async(project_gid, {"Field": "value"})
if not result.from_cache:
    print("No cached DataFrame - pre-populate with set_project_dataframe()")
```

**Confirm project_gid**: Ensure you are searching the correct project.

---

### Multiple Matches When Expecting One

**Use more specific criteria**:

```python
# Too broad - may return multiple
await client.search.find_one_async(project_gid, {"Vertical": "Medical"})

# More specific - likely unique
await client.search.find_one_async(
    project_gid,
    {"Vertical": "Medical", "Office Phone": "555-1234", "Status": "Active"}
)
```

**Use limit parameter**:

```python
result = await client.search.find_async(
    project_gid,
    {"Vertical": "Medical"},
    limit=1
)
if result.hits:
    first_match = result.hits[0]
```

---

### Search Is Slow

**Pre-populate cache**: Avoid rebuilding DataFrame on each search:

```python
client.search.set_project_dataframe(project_gid, df)
```

**Check DataFrame size**: Very large DataFrames (100K+ rows) may benefit from filtering at the source.

**Use exact match over contains**: Substring matching is slower than equality.

---

## Related Documentation

- [Search Query Builder Guide](search-query-builder.md): Core concepts and usage
- [Search API Reference](../reference/REF-search-api.md): Complete method signatures
- [Migration Guide](../migration/MIGRATION-search-v2.md): Upgrading from prior patterns
