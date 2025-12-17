# Cascading and Inherited Fields

> Two patterns for field values that flow across the entity hierarchy (ADR-0054)

---

## Critical Design Constraint

**`allow_override=False` is the DEFAULT behavior.**

This means:
- Parent value ALWAYS overwrites descendant value during cascade
- Descendants cannot maintain local overrides unless explicitly configured
- Only set `allow_override=True` when the specific business requirement demands it

---

## Two Distinct Patterns

| Pattern | Source of Truth | Propagation | Example Fields |
|---------|-----------------|-------------|----------------|
| **Cascading (no override)** | Owner (Business, Unit, etc.) | Explicit push down, always overwrite | Office Phone, Company ID, Vertical |
| **Cascading (with override)** | Owner + local | Explicit push down, skip non-null | Platforms |
| **Inherited** | Nearest ancestor | On-access resolution up parent chain | Manager |

---

## Multi-Level Cascading

Cascading can originate from **ANY level** in the hierarchy, not just Business (root):

| Source | Target(s) | Example Field | Override Allowed? |
|--------|-----------|---------------|-------------------|
| Business | Unit, Offer, Process, Contact | `office_phone` | NO (default) |
| Business | Unit, Offer, Process | `company_id` | NO (default) |
| Unit | Offer | `platforms` | YES (explicit opt-in) |
| Unit | Offer, Process | `vertical` | NO (default) |

---

## Pattern 1: Cascading Fields (Multi-Level)

Fields owned by any entity that are **copied** to descendants for read efficiency.

### CascadingFieldDef Declaration

```python
from dataclasses import dataclass
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource

@dataclass(frozen=True)
class CascadingFieldDef:
    """Definition of a field that cascades from owner to descendants.

    Supports MULTI-LEVEL cascading: any entity can declare cascading fields
    that propagate to its descendants.

    CRITICAL DESIGN CONSTRAINT:
    - allow_override=False is the DEFAULT
    - This means parent value ALWAYS overwrites descendant value
    - Only set allow_override=True when descendants should keep non-null values

    Attributes:
        name: Custom field name in Asana (must match exactly)
        target_types: Set of entity types to cascade to, or None for all
        allow_override: If False (DEFAULT), always overwrite descendant.
                       If True, only overwrite if descendant value is None.
        cascade_on_change: If True, change detection includes this field
        source_field: Model attribute to use if not a custom field
        transform: Optional function to transform value before cascading
    """
    name: str
    target_types: set[type] | None = None  # None = all descendants
    allow_override: bool = False  # DEFAULT: NO override - parent always wins
    cascade_on_change: bool = True
    source_field: str | None = None
    transform: Callable[[Any], Any] | None = None

    def applies_to(self, entity: "AsanaResource") -> bool:
        """Check if cascade applies to given entity."""
        if self.target_types is None:
            return True  # None means all descendants
        return type(entity) in self.target_types

    def should_update_descendant(self, descendant: "AsanaResource") -> bool:
        """Determine if descendant should be updated during cascade.

        Logic:
            - allow_override=False (DEFAULT): Always update
            - allow_override=True: Only update if descendant has null value
        """
        if not self.allow_override:
            return True  # DEFAULT: Always overwrite

        # allow_override=True: Check if descendant has a value
        current_value = descendant.get_custom_fields().get(self.name)
        return current_value is None
```

### Business Model Declaration (No Override - Default)

```python
class Business(Task):
    """Business with cascading field declarations.

    CASCADING FIELDS: All use allow_override=False (DEFAULT).
    Descendant values are ALWAYS overwritten during cascade.
    """

    class CascadingFields:
        """Fields that cascade from Business to descendants."""

        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is DEFAULT - no local overrides
        )

        COMPANY_ID = CascadingFieldDef(
            name="Company ID",
            target_types=None,  # None = all descendants
            # allow_override=False is DEFAULT
        )

        BUSINESS_NAME = CascadingFieldDef(
            name="Business Name",
            target_types={Unit, Offer},
            source_field="name",  # Maps from Task.name
            # allow_override=False is DEFAULT
        )

        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            return [cls.OFFICE_PHONE, cls.COMPANY_ID, cls.BUSINESS_NAME]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None
```

### Unit Model Declaration (Mixed Override Behaviors)

```python
class Unit(Task):
    """Unit with its own cascading fields to Offers/Processes.

    NOTE: Some fields allow override (explicit opt-in), others don't.
    """

    class CascadingFields:
        """Fields that cascade from Unit to its descendants."""

        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},  # Only cascade to Offers
            allow_override=True,   # EXPLICIT OPT-IN: Offers can keep their value
        )

        VERTICAL = CascadingFieldDef(
            name="Vertical",
            target_types={Offer, Process},
            # allow_override=False is DEFAULT - Offers always get Unit's vertical
        )

        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            return [cls.PLATFORMS, cls.VERTICAL]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None
```

### Cascade Usage - No Override (Default)

```python
# Business cascade: ALL descendants get the value (no override)
async with client.save_session() as session:
    session.track(business, recursive=True)

    business.office_phone = "555-9999"
    session.cascade_field(business, "Office Phone")

    await session.commit_async()

    # Result: Business, Unit, Offer, Process, Contact ALL have "555-9999"
    # Even if Offer had "555-1111" before, it's now "555-9999"
```

### Cascade Usage - With Override (Explicit Opt-In)

```python
# Unit cascade: Only offers with null platforms get updated
async with client.save_session() as session:
    session.track(unit, recursive=True)

    unit.platforms = ["Google", "Meta"]
    session.cascade_field(unit, "Platforms")

    await session.commit_async()

    # Result:
    # - Offer A (platforms=None): Updated to ["Google", "Meta"]
    # - Offer B (platforms=["Bing"]): KEPT as ["Bing"] (override)
    # - Offer C (platforms=None): Updated to ["Google", "Meta"]
```

---

## Pattern 2: Inherited Fields (Parent-Owned with Override)

Fields that **resolve up the parent chain** at access time, with optional local override.

### InheritedFieldDef Declaration

```python
@dataclass(frozen=True)
class InheritedFieldDef:
    """Definition of a field inherited from parent entities.

    Attributes:
        name: Custom field name in Asana
        inherit_from: Parent types in resolution order
        allow_override: Whether child can set own value
        override_flag_field: Field tracking override status
        default: Default if no ancestor has value
    """
    name: str
    inherit_from: list[str] = field(default_factory=list)
    allow_override: bool = True
    override_flag_field: str | None = None
    default: Any = None

    @property
    def override_field_name(self) -> str:
        """Name of the override flag field."""
        return self.override_flag_field or f"{self.name} Override"
```

### Entity Model Declaration

```python
class Offer(Task):
    """Offer with inherited field declarations."""

    class InheritedFields:
        """Fields inherited from parent entities."""

        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],  # Resolution order
            allow_override=True,
        )

        MANAGER = InheritedFieldDef(
            name="Manager",
            inherit_from=["Unit"],
            allow_override=False,  # Always use parent's value
        )
```

### Inherited Field Property Pattern

```python
class Offer(Task):
    @property
    def vertical(self) -> str | None:
        """Get vertical, inheriting from parent if not overridden."""
        # Check for local override
        if self._is_field_overridden("Vertical"):
            return self.get_custom_fields().get("Vertical")

        # Inherit from Unit
        if self._unit:
            return self._unit.vertical

        return None

    @vertical.setter
    def vertical(self, value: str | None) -> None:
        """Set vertical locally, marking as overridden."""
        self.get_custom_fields().set("Vertical", value)
        self.get_custom_fields().set("Vertical Override", "Yes")

    def inherit_vertical(self) -> None:
        """Clear local override, inherit from parent."""
        self.get_custom_fields().remove("Vertical")
        self.get_custom_fields().remove("Vertical Override")

    def _is_field_overridden(self, field_name: str) -> bool:
        """Check if field is locally overridden."""
        override_field = f"{field_name} Override"
        override_value = self.get_custom_fields().get(override_field)
        return override_value in ("Yes", "yes", True, "true", "1")
```

---

## Comparison

| Aspect | Cascading (no override) | Cascading (with override) | Inherited |
|--------|-------------------------|---------------------------|-----------|
| Storage | Denormalized (copy) | Denormalized (copy) | Single source + override flag |
| Read Performance | O(1) | O(1) | O(n) - may traverse parents |
| Write Performance | O(n) - update all | O(n) - update nulls only | O(1) - single entity |
| Default Behavior | Always overwrite | Skip non-null | Inherit from parent |
| `allow_override` | `False` (default) | `True` (explicit) | N/A |
| Use Case | Authoritative data | Default + local override | On-demand resolution |
| Examples | Office Phone, Company ID, Vertical | Platforms | Manager |

---

## Cascade Behavior Summary

| `allow_override` | Cascade Behavior | Use Case |
|------------------|------------------|----------|
| `False` (DEFAULT) | **Always overwrite** descendant value with parent value | `office_phone`, `company_id`, `vertical` - authoritative data |
| `True` (explicit) | **Only overwrite if descendant value is null** | `platforms` - Offer can have local value if set |

---

## When to Use Each

**Use Cascading (no override - default) When**:
- Field value MUST be consistent across hierarchy (e.g., office phone, company ID)
- Parent is the authoritative source of truth
- Local variations are NOT permitted
- Field rarely changes (monthly or less)
- Need to query/filter by field in Asana views

**Use Cascading (with override - explicit) When**:
- Field has a sensible default from parent
- Descendants MAY have their own value if explicitly set
- Null descendants should receive the parent value
- Example: Unit sets default platforms, but Offer can override if needed

**Use Inherited When**:
- Field changes frequently at different hierarchy levels
- Different branches need different values
- Always need current value (no staleness acceptable)
- Storage efficiency matters

---

## Multi-Level Cascade Scope

**Important**: Cascade scope is relative to the source entity.

```python
# cascade_field(unit, "Platforms") only affects THAT unit's offers
# NOT sibling units or their children

async with client.save_session() as session:
    session.track(unit_retail, recursive=True)
    session.track(unit_industrial, recursive=True)

    # Change platforms on retail unit only
    unit_retail.platforms = ["Google Shopping", "Amazon"]
    session.cascade_field(unit_retail, "Platforms")

    await session.commit_async()

    # Result:
    # - unit_retail's offers: Updated (respecting allow_override)
    # - unit_industrial's offers: UNCHANGED (not in scope)
```

---

## Related

- [ADR-0054](../../../../docs/decisions/ADR-0054-cascading-custom-fields.md) - Full decision record
- [cascade-operations.md](../autom8-asana-business-workflows/cascade-operations.md) - SaveSession cascade integration
- [field-inheritance-chain.md](../autom8-asana-business-relationships/field-inheritance-chain.md) - Resolution chain details
