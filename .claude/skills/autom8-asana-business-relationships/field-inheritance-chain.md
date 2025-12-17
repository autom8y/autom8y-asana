# Field Inheritance Chain

> How inherited fields resolve through the holder relationship hierarchy (ADR-0054)

---

## Overview

Inherited fields resolve their value by traversing up the parent chain until a value is found. This leverages the existing holder relationship structure for field value resolution.

---

## Resolution Chain

The inheritance chain follows the holder hierarchy:

```
Offer
    |
    v (inherit from)
Unit
    |
    v (inherit from)
Business
    |
    v (fallback)
InheritedFieldDef.default
```

---

## Resolution Algorithm

```python
def resolve_inherited_field(entity, field_def: InheritedFieldDef) -> Any:
    """Resolve inherited field value from parent chain.

    Args:
        entity: Entity to resolve field for
        field_def: Inherited field definition

    Returns:
        Resolved value (local, inherited, or default)
    """
    # Step 1: Check for local override
    if field_def.allow_override and entity._is_field_overridden(field_def.name):
        return entity.get_custom_fields().get(field_def.name)

    # Step 2: Traverse parent chain in declared order
    for parent_type in field_def.inherit_from:
        parent = _get_parent_of_type(entity, parent_type)
        if parent is not None:
            value = parent.get_custom_fields().get(field_def.name)
            if value is not None:
                return value

    # Step 3: Return default
    return field_def.default
```

---

## Relationship to Holder Pattern

Inherited fields use the same navigation as holder relationships:

| Entity | Parent Via | Holder Type | Navigates To |
|--------|-----------|-------------|--------------|
| Offer | `._unit` | OfferHolder | Unit |
| Process | `._unit` | ProcessHolder | Unit |
| Unit | `._business` | UnitHolder | Business |
| Contact | `._business` | ContactHolder | Business |

### Cached Reference Reuse

Inherited field resolution uses the same cached parent references:

```python
class Offer(Task):
    _unit: Unit | None = PrivateAttr(default=None)

    @property
    def unit(self) -> Unit | None:
        """Navigate to parent Unit (cached)."""
        if self._unit is None:
            self._unit = self._resolve_unit()
        return self._unit

    @property
    def vertical(self) -> str | None:
        """Vertical (inherited from Unit)."""
        if self._is_field_overridden("Vertical"):
            return self.get_custom_fields().get("Vertical")

        # Uses cached _unit reference
        if self._unit:
            return self._unit.vertical

        return None
```

---

## Multi-Level Inheritance

Fields can inherit through multiple levels:

```python
# Offer inherits from Unit, which inherits from Business
class Offer(Task):
    @property
    def vertical(self) -> str | None:
        """Vertical - resolves: Offer -> Unit -> Business."""
        if self._is_field_overridden("Vertical"):
            return self.get_custom_fields().get("Vertical")

        if self._unit:
            return self._unit.vertical  # Unit.vertical may also inherit

        return None


class Unit(Task):
    @property
    def vertical(self) -> str | None:
        """Vertical - resolves: Unit -> Business."""
        local = self.get_custom_fields().get("Vertical")
        if local is not None:
            return local

        if self._business:
            return self._business.get_custom_fields().get("Default Vertical")

        return "General"  # Default
```

---

## Override Flag Pattern

For fields that allow override, track with a companion field:

```python
# In Asana custom fields:
# "Vertical" - the actual value
# "Vertical Override" - "Yes" if locally set, empty if inherited

def _is_field_overridden(self, field_name: str) -> bool:
    """Check if field is locally overridden."""
    override_field = f"{field_name} Override"
    override_value = self.get_custom_fields().get(override_field)
    return override_value in ("Yes", "yes", True, "true", "1")

def inherit_vertical(self) -> None:
    """Clear local override, return to inheriting from parent."""
    self.get_custom_fields().remove("Vertical")
    self.get_custom_fields().remove("Vertical Override")
```

---

## Caching Inherited Values

For performance, inherited values can be cached at read time:

```python
class Offer(Task):
    _cached_vertical: str | None = PrivateAttr(default=None)
    _vertical_resolved: bool = PrivateAttr(default=False)

    @property
    def vertical(self) -> str | None:
        """Vertical with resolution caching."""
        if not self._vertical_resolved:
            self._cached_vertical = self._resolve_vertical()
            self._vertical_resolved = True
        return self._cached_vertical

    def _invalidate_inherited_cache(self) -> None:
        """Invalidate cached inherited values."""
        self._vertical_resolved = False
        self._cached_vertical = None
```

---

## Inheritance vs Cascading

| Aspect | Inherited | Cascading |
|--------|-----------|-----------|
| Storage | Value at source only | Copy on every descendant |
| Read | O(depth) traversal | O(1) direct access |
| Write | O(1) at source | O(n) batch update |
| Staleness | Never stale | Eventual consistency |
| Override | Per-entity flag | N/A (source always wins) |

### When to Use Each

- **Inherited**: Values that vary by branch (Vertical per Unit)
- **Cascading**: Values that must be identical everywhere (Office Phone)

---

## Testing Inherited Fields

```python
def test_offer_inherits_vertical_from_unit():
    """Offer.vertical should resolve from Unit if not overridden."""
    unit = Unit(gid="u1")
    unit.get_custom_fields().set("Vertical", "Legal")

    offer = Offer(gid="o1")
    offer._unit = unit

    assert offer.vertical == "Legal"


def test_offer_override_breaks_inheritance():
    """Offer can override inherited vertical."""
    unit = Unit(gid="u1")
    unit.get_custom_fields().set("Vertical", "Legal")

    offer = Offer(gid="o1")
    offer._unit = unit
    offer.vertical = "Medical"  # Sets override flag

    assert offer.vertical == "Medical"
    assert offer._is_field_overridden("Vertical")


def test_inherit_clears_override():
    """inherit_vertical() clears local override."""
    offer = Offer(gid="o1")
    offer._unit = Unit(gid="u1")
    offer._unit.get_custom_fields().set("Vertical", "Legal")
    offer.vertical = "Medical"

    offer.inherit_vertical()

    assert offer.vertical == "Legal"  # Back to inherited
    assert not offer._is_field_overridden("Vertical")
```

---

## Related

- [ADR-0054](../../../../docs/decisions/ADR-0054-cascading-custom-fields.md) - Full decision record
- [bidirectional-navigation.md](bidirectional-navigation.md) - Parent reference caching
- [holder-pattern.md](holder-pattern.md) - Holder relationship structure
- [cascading-inherited-fields.md](../autom8-asana-business-fields/cascading-inherited-fields.md) - Field definition patterns
