# Composite Pattern

> Nested holders within Unit entities

---

## What is Composite?

Some entities have their own holders, creating nested hierarchies:

```
Business
    |
    +-- UnitHolder
            |
            +-- Unit (has nested holders)
                    |
                    +-- OfferHolder --> Offer[]
                    +-- ProcessHolder --> Process[]
```

Unit is **composite** - it's both a child (of UnitHolder) and a parent (of OfferHolder, ProcessHolder).

---

## Unit's HOLDER_KEY_MAP

Unit defines its own holders:

```python
class Unit(Task):
    """Unit with nested OfferHolder and ProcessHolder."""

    # Unit is a child but also has its own holders
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "offer_holder": ("Offers", "gift"),
        "process_holder": ("Processes", "gear"),
    }

    # Cached holders
    _offer_holder: Task | None = PrivateAttr(default=None)
    _process_holder: Task | None = PrivateAttr(default=None)

    @property
    def offer_holder(self) -> Task | None:
        """OfferHolder subtask."""
        return self._offer_holder

    @property
    def process_holder(self) -> Task | None:
        """ProcessHolder subtask."""
        return self._process_holder

    @property
    def offers(self) -> list[Task]:
        """All Offer children."""
        if self._offer_holder is None:
            return []
        return getattr(self._offer_holder, '_children', [])

    @property
    def processes(self) -> list[Task]:
        """All Process children."""
        if self._process_holder is None:
            return []
        return getattr(self._process_holder, '_children', [])
```

---

## Recursive Prefetch

Prefetching must handle nested holders:

```python
async def _prefetch_unit_holders(self, unit: Unit) -> None:
    """Fetch nested holders for a Unit."""
    # Get Unit's direct subtasks (its holders)
    subtasks = await self._client.tasks.get_subtasks_async(unit.gid)
    unit._populate_holders(list(subtasks))

    # Fetch children of each nested holder
    for holder_key in unit.HOLDER_KEY_MAP:
        holder = getattr(unit, f"_{holder_key}", None)
        if holder:
            children = await self._client.tasks.get_subtasks_async(holder.gid)
            holder._children = list(children)
```

---

## Depth Control

Limit recursion depth for performance:

```python
MAX_HOLDER_DEPTH = 3  # Business -> Holder -> Unit -> Holder -> Child

async def _prefetch_recursive(
    self,
    entity: Task,
    depth: int = 0
) -> None:
    """Recursively prefetch holders up to MAX_DEPTH."""
    if depth >= MAX_HOLDER_DEPTH:
        return

    if not hasattr(entity, 'HOLDER_KEY_MAP'):
        return

    # Fetch this entity's holders
    subtasks = await self._client.tasks.get_subtasks_async(entity.gid)
    entity._populate_holders(list(subtasks))

    # Recurse into holders
    for holder_key in entity.HOLDER_KEY_MAP:
        holder = getattr(entity, f"_{holder_key}", None)
        if holder:
            children = await self._client.tasks.get_subtasks_async(holder.gid)
            holder._populate_children(list(children))

            # Recurse into children that have their own holders
            for child in getattr(holder, '_children', []):
                if hasattr(child, 'HOLDER_KEY_MAP'):
                    await self._prefetch_recursive(child, depth + 1)
```

---

## Hierarchy Depths

| Entity | Depth | Parent | Children |
|--------|-------|--------|----------|
| Business | 0 | None | 7 holders |
| ContactHolder | 1 | Business | Contact[] |
| Contact | 2 | ContactHolder | None |
| UnitHolder | 1 | Business | Unit[] |
| Unit | 2 | UnitHolder | 2 holders |
| OfferHolder | 3 | Unit | Offer[] |
| Offer | 4 | OfferHolder | None |
| ProcessHolder | 3 | Unit | Process[] |
| Process | 4 | ProcessHolder | None |

---

## Navigation Through Composites

Navigate across the hierarchy:

```python
# From Process up to Business
process = unit.processes[0]
unit = process.parent.parent  # ProcessHolder -> Unit
business = unit.business

# From Business down to Process
business.units[0].processes[0]

# Cross-navigation: Process to Contact
process = unit.processes[0]
contacts = process.business.contacts  # Via Business root
```

---

## Composite SaveSession Pattern

Tracking a composite with `recursive=True`:

```python
async with client.save_session() as session:
    # recursive=True tracks entire subtree
    session.track(business, recursive=True)

    # All entities now tracked:
    # - Business
    # - ContactHolder, UnitHolder, LocationHolder, etc.
    # - All Contacts, Units, Address, Hours
    # - Unit's OfferHolders, ProcessHolders
    # - All Offers, Processes

    # Modify at any level
    business.company_id = "NEW-ID"
    business.contacts[0].full_name = "Updated Contact"
    business.units[0].mrr = Decimal("6000")
    business.units[0].processes[0].name = "Updated Process"

    # All changes saved in dependency order
    await session.commit_async()
```

---

## Selective Tracking

Track specific branches instead of full tree:

```python
async with client.save_session() as session:
    # Track business without recursion
    session.track(business)

    # Track only contacts branch
    session.track(business.contact_holder, recursive=True)

    # Units not tracked, won't be saved
    business.units[0].mrr = Decimal("999")  # Change ignored

    await session.commit_async()
```

---

## Memory Considerations

Full recursive tracking can be expensive:

| Scenario | Entities Tracked |
|----------|------------------|
| Business only | 1 |
| Business + holders | ~8 |
| Business + holders + children | ~50-500 |
| Full recursive (with nested) | ~500-5000 |

Use selective tracking for large hierarchies:

```python
# Instead of tracking everything
# session.track(business, recursive=True)

# Track only what you're modifying
session.track(business)
session.track(specific_contact)
session.track(specific_unit)
```

---

## Related

- [holder-pattern.md](holder-pattern.md) - Basic holder structure
- [lazy-loading.md](lazy-loading.md) - When nested holders load
- [patterns-relationships.md](patterns-relationships.md) - Best practices
