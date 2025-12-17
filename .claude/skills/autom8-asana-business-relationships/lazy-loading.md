# Lazy Loading

> When and how holder subtasks are fetched (ADR-0050)

---

## Decision Summary

**Fetch holder subtasks on `SaveSession.track()` with `prefetch_holders=True` flag.**

This decision balances:
- Async context availability (SaveSession is async)
- Batch efficiency (multiple holders in one operation)
- Predictable timing (developers know when network calls happen)
- Memory efficiency (only tracked entities are populated)

---

## Why Not On Property Access?

Properties in Python should be synchronous:

```python
# BAD: Would require await on property
contact_holder = await business.contact_holder

# BAD: Returns coroutine, confusing
holder = business.contact_holder  # Returns coroutine object

# GOOD: Property returns cached value
holder = business.contact_holder  # Returns ContactHolder | None
```

Async properties break Python conventions and IDE support.

---

## The Prefetch Pattern

```python
async with client.save_session() as session:
    # prefetch_holders=True by default for Business entities
    session.track(business)

    # At this point, holders are still None
    # They're queued for prefetch

    # Prefetch happens before commit or on explicit call
    await session.prefetch_pending()

    # Now holders are populated
    for contact in business.contacts:
        print(contact.full_name)

    await session.commit_async()
```

---

## SaveSession.track() with Prefetch

```python
class SaveSession:
    def __init__(self, client: AsanaClient):
        self._client = client
        self._tracker = ChangeTracker()
        self._pending_prefetch: list[Business] = []

    def track(
        self,
        entity: T,
        prefetch_holders: bool = True,
    ) -> T:
        """Track entity with optional holder prefetch.

        Args:
            entity: AsanaResource to track
            prefetch_holders: If True and entity is Business,
                            queue for holder prefetch

        Returns:
            The tracked entity (for chaining)
        """
        self._tracker.track(entity)

        if prefetch_holders and isinstance(entity, Business):
            self._pending_prefetch.append(entity)

        return entity
```

---

## Prefetch Execution

Prefetch can happen:
1. **Explicitly**: `await session.prefetch_pending()`
2. **At commit**: Before `commit_async()` executes saves

```python
async def prefetch_pending(self) -> None:
    """Fetch holder subtasks for all pending Business entities."""
    if not self._pending_prefetch:
        return

    # Process each business
    for business in self._pending_prefetch:
        await self._prefetch_business_holders(business)

    self._pending_prefetch.clear()

async def _prefetch_business_holders(self, business: Business) -> None:
    """Fetch and populate holders for a single Business."""
    # Get direct subtasks (holders)
    holder_tasks = await self._client.tasks.get_subtasks_async(
        business.gid,
        opt_fields=["name", "custom_emoji", "gid"]
    )

    # Populate holder references
    business._populate_holders(list(holder_tasks))

    # Fetch children for each holder
    for holder_key in business.HOLDER_KEY_MAP:
        holder = getattr(business, f"_{holder_key}", None)
        if holder is not None:
            await self._prefetch_holder_children(holder)

async def _prefetch_holder_children(self, holder: Task) -> None:
    """Fetch children for a holder task."""
    children = await self._client.tasks.get_subtasks_async(
        holder.gid,
        opt_fields=["name", "custom_fields", "gid", "parent"]
    )
    holder._populate_children(list(children))
```

---

## Skipping Prefetch

For performance-sensitive cases:

```python
async with client.save_session() as session:
    # Skip holder prefetch
    session.track(business, prefetch_holders=False)

    # Holders are not populated
    assert business.contact_holder is None

    # Can still modify business itself
    business.company_id = "NEW-ID"
    await session.commit_async()
```

---

## Manual Fetch Outside SaveSession

For standalone use without SaveSession:

```python
async def fetch_business_with_holders(
    client: AsanaClient,
    business_gid: str
) -> Business:
    """Fetch business and populate all holders."""
    # Get business task
    task = await client.tasks.get(business_gid)
    business = Business.model_validate(task.model_dump())

    # Fetch holders
    await business.fetch_holders_async(client)

    return business

# On Business model
async def fetch_holders_async(self, client: AsanaClient) -> None:
    """Standalone method to fetch holders."""
    subtasks = await client.tasks.get_subtasks_async(self.gid)
    self._populate_holders(list(subtasks))

    for holder_key in self.HOLDER_KEY_MAP:
        holder = getattr(self, f"_{holder_key}", None)
        if holder:
            children = await client.tasks.get_subtasks_async(holder.gid)
            holder._populate_children(list(children))
```

---

## Before vs After Prefetch

| State | `business.contact_holder` | `business.contacts` |
|-------|---------------------------|---------------------|
| Before `track()` | `None` | `[]` |
| After `track()`, before prefetch | `None` | `[]` |
| After `prefetch_pending()` | `ContactHolder` | `[Contact, ...]` |

---

## Batch Optimization

Multiple businesses can be prefetched in parallel:

```python
async def prefetch_pending(self) -> None:
    """Batch prefetch for multiple businesses."""
    tasks = [
        self._prefetch_business_holders(b)
        for b in self._pending_prefetch
    ]
    await asyncio.gather(*tasks)
    self._pending_prefetch.clear()
```

---

## Related

- [holder-pattern.md](holder-pattern.md) - What holders contain
- [bidirectional-navigation.md](bidirectional-navigation.md) - Navigation after prefetch
- [patterns-relationships.md](patterns-relationships.md) - Common usage patterns
