# Business Model Relationships

> Holder pattern, lazy loading, bidirectional navigation, composite entities

---

## Activation Triggers

**Use this skill when**:
- Implementing holder pattern for parent-child task relationships
- Working with lazy loading of subtasks and holder children
- Implementing bidirectional navigation (child to parent, parent to child)
- Understanding composite patterns (Unit with nested holders)
- Designing reference caching strategies

**Keywords**: holder, parent_task, subtasks, lazy load, bidirectional, navigation, contact_holder, unit_holder, location_holder, get_holder, parent, child, recursive, prefetch, inheritance chain, field inheritance, resolve_inherited

**File patterns**: `**/models/holder*.py`, `**/*holder*.py`, `**/persistence/session.py`

---

## Architecture Decisions

This skill implements four key ADRs:

| ADR | Decision | Summary |
|-----|----------|---------|
| ADR-0050 | Holder Lazy Loading | Fetch on `SaveSession.track()` with `prefetch_holders=True` |
| ADR-0052 | Bidirectional Caching | Cache upward refs with explicit invalidation |
| ADR-0053 | Composite SaveSession | Optional `recursive=True` flag (default False) |

---

## Quick Reference

| I need to... | See |
|--------------|-----|
| Understand holder pattern | [holder-pattern.md](holder-pattern.md) |
| Implement lazy loading | [lazy-loading.md](lazy-loading.md) |
| Navigate parent/child relationships | [bidirectional-navigation.md](bidirectional-navigation.md) |
| Handle nested holders (Unit) | [composite-pattern.md](composite-pattern.md) |
| Understand relationship patterns | [patterns-relationships.md](patterns-relationships.md) |
| Understand inherited field resolution | [field-inheritance-chain.md](field-inheritance-chain.md) |

---

## Relationship Hierarchy

```
Business
    |
    +-- ContactHolder (holder)
    |       |
    |       +-- Contact (child) --> .business (upward)
    |       +-- Contact (child) --> .contact_holder (upward)
    |
    +-- UnitHolder (holder)
    |       |
    |       +-- Unit (child, also has holders)
    |               |
    |               +-- OfferHolder (nested holder)
    |               +-- ProcessHolder (nested holder)
    |
    +-- LocationHolder (holder)
            |
            +-- Address (sibling) --> .hours (sibling ref)
            +-- Hours (sibling) --> .address (sibling ref)
```

Note: Address and Hours are **siblings** under LocationHolder (single-location business model).

---

## Core Concepts

### Downward Navigation

Parent to children - via holder properties:

```python
# Business -> Holders -> Children
business.contact_holder         # ContactHolder task
business.contact_holder.contacts  # list[Contact]
business.contacts               # Shortcut: same list

# With nested holders
unit.offer_holder              # OfferHolder task
unit.offers                    # list[Offer]
```

### Upward Navigation

Children to parents - via cached references:

```python
# Contact -> ContactHolder -> Business
contact.contact_holder         # Parent ContactHolder
contact.business              # Root Business (cached)

# Unit -> UnitHolder -> Business
unit.unit_holder              # Parent UnitHolder
unit.business                 # Root Business (cached)
```

### Lazy Loading

Holders populated on `SaveSession.track()`:

```python
async with client.save_session() as session:
    # Holders fetched here (prefetch_holders=True by default)
    session.track(business)

    # Now accessible
    for contact in business.contacts:
        print(contact.full_name)
```

---

## Key Pattern: Holder Detection

Holders identified by name and emoji:

```python
HOLDER_KEY_MAP = {
    "contact_holder": ("Contacts", "person"),
    "unit_holder": ("Units", "package"),
}

def _identify_holder(self, task: Task) -> str | None:
    """Identify which holder type a task is."""
    for prop_name, (name_pattern, emoji) in self.HOLDER_KEY_MAP.items():
        if task.name == name_pattern:
            return prop_name
        if self._has_emoji(task, emoji):
            return prop_name
    return None
```

---

## Progressive References

| Document | Lines | Content |
|----------|-------|---------|
| [holder-pattern.md](holder-pattern.md) | ~180 | HOLDER_KEY_MAP, holder tasks, children lists |
| [lazy-loading.md](lazy-loading.md) | ~150 | SaveSession prefetch, async context, timing |
| [bidirectional-navigation.md](bidirectional-navigation.md) | ~160 | Upward/downward navigation, caching, invalidation |
| [composite-pattern.md](composite-pattern.md) | ~120 | Nested holders, recursive depth, Unit pattern |
| [patterns-relationships.md](patterns-relationships.md) | ~100 | Common patterns, anti-patterns, best practices |
| [field-inheritance-chain.md](field-inheritance-chain.md) | ~140 | Inherited field resolution via parent chain (ADR-0054) |

---

## When to Use Other Skills

| Need | Use Instead |
|------|-------------|
| Model field definitions | [autom8-asana-business-schemas](../autom8-asana-business-schemas/) |
| Custom field accessor patterns | [autom8-asana-business-fields](../autom8-asana-business-fields/) |
| SaveSession commit workflows | [autom8-asana-business-workflows](../autom8-asana-business-workflows/) |
| Core SDK patterns | [autom8-asana-domain](../autom8-asana-domain/) |
