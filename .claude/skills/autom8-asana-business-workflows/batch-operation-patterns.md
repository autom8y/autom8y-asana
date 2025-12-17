# Batch Operation Patterns

> Efficient bulk operations for business entities

---

## Batch Create

Create multiple entities in one commit:

```python
async def batch_create_units(
    client: AsanaClient,
    business_gid: str,
    units_data: list[dict],
) -> list[Unit]:
    """Create multiple units at once."""

    async with client.save_session() as session:
        # Get business and holder
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business)
        await session.prefetch_pending()

        holder = business.unit_holder
        if not holder:
            raise ValueError("No UnitHolder")

        # Create all units
        units = []
        for data in units_data:
            unit = Unit(
                gid=f"temp_{uuid4()}",
                name=f"{data['vertical']} - ${data['mrr']:,.0f}",
                parent=holder,
            )
            unit.vertical = data['vertical']
            unit.mrr = Decimal(str(data['mrr']))
            unit.products = data.get('products', [])

            session.track(unit)
            units.append(unit)

        # Single commit for all
        result = await session.commit_async()

        # Update GIDs
        for unit in units:
            unit.gid = result.gid_map.get(unit.gid, unit.gid)

        return units
```

---

## Bulk Update Custom Fields

Update field across many entities:

```python
async def bulk_update_campaign(
    client: AsanaClient,
    entity_gids: list[str],
    campaign: str,
) -> int:
    """Set campaign field on multiple entities."""

    async with client.save_session() as session:
        count = 0

        for gid in entity_gids:
            task = await client.tasks.get(gid)
            entity = Task.model_validate(task.model_dump())
            session.track(entity)

            entity.get_custom_fields().set("Campaign", campaign)
            count += 1

        result = await session.commit_async()
        return len(result.succeeded)
```

### Batched Fetch + Update

```python
async def bulk_update_contacts_in_project(
    client: AsanaClient,
    project_gid: str,
    updates: dict,
) -> int:
    """Update all contacts in a project."""

    async with client.save_session() as session:
        # Fetch all tasks in project
        tasks = client.tasks.list(project=project_gid)

        count = 0
        async for task in tasks:
            # Filter for contacts (by custom field or naming)
            if not is_contact_task(task):
                continue

            contact = Contact.model_validate(task.model_dump())
            session.track(contact)

            for field, value in updates.items():
                setattr(contact, field, value)
            count += 1

        await session.commit_async()
        return count
```

---

## Tag Operations

Add/remove tags in batch:

```python
async def tag_all_contacts(
    client: AsanaClient,
    business_gid: str,
    tag_gid: str,
) -> int:
    """Add tag to all contacts in business."""

    async with client.save_session() as session:
        # Fetch business with contacts
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business)
        await session.prefetch_pending()

        # Add tag to each contact
        count = 0
        for contact in business.contacts:
            session.add_tag(contact.gid, tag_gid)
            count += 1

        await session.commit_async()
        return count

async def remove_tag_from_completed(
    client: AsanaClient,
    business_gid: str,
    tag_gid: str,
) -> int:
    """Remove tag from completed contacts."""

    async with client.save_session() as session:
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business)
        await session.prefetch_pending()

        count = 0
        for contact in business.contacts:
            if contact.completed:
                session.remove_tag(contact.gid, tag_gid)
                count += 1

        await session.commit_async()
        return count
```

---

## Section Operations

Move entities between sections:

```python
async def move_units_to_section(
    client: AsanaClient,
    business_gid: str,
    target_section_gid: str,
    filter_fn: Callable[[Unit], bool] = lambda u: True,
) -> int:
    """Move matching units to a section."""

    async with client.save_session() as session:
        task = await client.tasks.get(business_gid)
        business = Business.model_validate(task.model_dump())
        session.track(business)
        await session.prefetch_pending()

        count = 0
        for unit in business.units:
            if filter_fn(unit):
                session.move_to_section(unit.gid, target_section_gid)
                count += 1

        await session.commit_async()
        return count

# Usage: Move all paused units
count = await move_units_to_section(
    client,
    business_gid,
    paused_section_gid,
    filter_fn=lambda u: u.unit_status == "Paused"
)
```

---

## Parallel Processing

Process multiple businesses in parallel:

```python
async def update_all_businesses_in_project(
    client: AsanaClient,
    project_gid: str,
    update_fn: Callable[[Business], None],
) -> int:
    """Update all businesses in a project."""

    # Fetch all business GIDs
    business_gids = []
    async for task in client.tasks.list(project=project_gid):
        if is_business_task(task):
            business_gids.append(task.gid)

    # Process in parallel batches
    batch_size = 10
    total = 0

    for i in range(0, len(business_gids), batch_size):
        batch = business_gids[i:i + batch_size]

        # Process batch in parallel
        tasks = [
            process_single_business(client, gid, update_fn)
            for gid in batch
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        total += sum(1 for r in results if r is True)

    return total

async def process_single_business(
    client: AsanaClient,
    gid: str,
    update_fn: Callable[[Business], None],
) -> bool:
    """Process a single business."""
    try:
        async with client.save_session() as session:
            task = await client.tasks.get(gid)
            business = Business.model_validate(task.model_dump())
            session.track(business)

            update_fn(business)

            await session.commit_async()
            return True
    except Exception:
        return False
```

---

## Chunked Operations

Handle large datasets in chunks:

```python
async def bulk_import_chunked(
    client: AsanaClient,
    holder_gid: str,
    data: list[dict],
    chunk_size: int = 50,
) -> tuple[int, int]:
    """Import data in chunks to avoid memory issues."""

    success = 0
    failed = 0

    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]

        try:
            async with client.save_session() as session:
                for item in chunk:
                    entity = Contact(
                        gid=f"temp_{uuid4()}",
                        name=item['name'],
                        parent=NameGid(gid=holder_gid),
                    )
                    for k, v in item.items():
                        if hasattr(entity, k):
                            setattr(entity, k, v)
                    session.track(entity)

                result = await session.commit_async()
                success += len(result.succeeded)
                failed += len(result.failed)

        except Exception:
            failed += len(chunk)

    return success, failed
```

---

## Related

- [composite-savesession.md](composite-savesession.md) - Hierarchy tracking
- [workflow-patterns.md](workflow-patterns.md) - Common workflows
- [operation-hooks.md](operation-hooks.md) - Validation hooks
