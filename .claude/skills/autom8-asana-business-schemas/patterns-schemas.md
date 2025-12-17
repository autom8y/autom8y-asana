# Schema Patterns

> Pydantic v2 patterns for Task subclasses

---

## Base Task Extension

All business entities inherit from Task:

```python
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from pydantic import PrivateAttr, ConfigDict
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business import Business

class Contact(Task):
    """Contact entity - extends Task with business-specific behavior."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",  # Ignore unknown fields from API
    )

    # Class-level constants
    OWNER_POSITIONS: ClassVar[set[str]] = {"owner", "ceo", "founder"}

    # Private attributes (not serialized)
    _business: Business | None = PrivateAttr(default=None)
```

---

## TYPE_CHECKING Imports

Prevent circular imports using `TYPE_CHECKING`:

```python
from __future__ import annotations  # Required for forward refs
from typing import TYPE_CHECKING

# Only imported during type checking, not at runtime
if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.contact_holder import ContactHolder

class Contact(Task):
    # Type hints work, no circular import at runtime
    _business: Business | None = PrivateAttr(default=None)
```

---

## PrivateAttr for Cached References

Use `PrivateAttr` for non-serialized state:

```python
from pydantic import PrivateAttr

class Contact(Task):
    # These are NOT serialized in model_dump()
    # They persist across property access within same instance
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)

    # For lists
    _children: list[Task] = PrivateAttr(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        # PrivateAttr values are set to defaults automatically
```

---

## Custom Field Property Pattern

Properties delegate to CustomFieldAccessor (ADR-0051):

```python
class Business(Task):
    """Typed property pattern for custom fields."""

    class Fields:
        """Field name constants for discoverability."""
        COMPANY_ID = "Company ID"
        MRR = "MRR"
        BOOKING_TYPE = "Booking Type"

    # String field
    @property
    def company_id(self) -> str | None:
        """Company identifier (custom field)."""
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

    # Numeric field with Decimal conversion
    @property
    def mrr(self) -> Decimal | None:
        """Monthly recurring revenue (custom field)."""
        value = self.get_custom_fields().get(self.Fields.MRR)
        return Decimal(str(value)) if value is not None else None

    @mrr.setter
    def mrr(self, value: Decimal | None) -> None:
        self.get_custom_fields().set(
            self.Fields.MRR,
            float(value) if value else None
        )

    # Enum field with dict extraction
    @property
    def booking_type(self) -> str | None:
        """Booking type (enum custom field)."""
        value = self.get_custom_fields().get(self.Fields.BOOKING_TYPE)
        if isinstance(value, dict):
            return value.get("name")
        return value
```

---

## HOLDER_KEY_MAP Pattern

Define holder types with detection criteria:

```python
from typing import ClassVar

class Business(Task):
    """Entity with holder subtasks."""

    # Map: property_name -> (task_name, emoji_name)
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "person"),
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "map"),
    }

    def _matches_holder(self, task: Task, name_pattern: str, emoji: str) -> bool:
        """Check if task matches holder criteria."""
        # Match by name
        if task.name == name_pattern:
            return True
        # Match by emoji indicator
        if hasattr(task, 'custom_emoji') and task.custom_emoji:
            emoji_name = task.custom_emoji.get('name', '')
            if emoji_name == emoji:
                return True
        return False
```

---

## Model Validation Pattern

Create typed instances from API responses:

```python
# From API response dict
response = {"gid": "123", "name": "Acme Corp", "custom_fields": [...]}
business = Business.model_validate(response)

# From existing Task
task = await client.tasks.get("123")
business = Business.model_validate(task.model_dump())

# With extra fields ignored
business = Business.model_validate(response)  # extra="ignore" handles unknown
```

---

## Serialization for SaveSession

Models serialize for change tracking:

```python
# SaveSession uses model_dump for snapshot comparison
snapshot = entity.model_dump(exclude_none=True)

# Later comparison
current = entity.model_dump(exclude_none=True)
if snapshot != current:
    # Entity has changes

# Custom fields are in the dump
{
    "gid": "123",
    "name": "Acme Corp",
    "custom_fields": [
        {"gid": "cf_1", "name": "Company ID", "text_value": "ACME-001"}
    ]
}
```

---

## Navigation Property Pattern

Cached upward navigation (ADR-0052):

```python
class Contact(Task):
    _business: Business | None = PrivateAttr(default=None)

    @property
    def business(self) -> Business | None:
        """Navigate to containing Business (cached)."""
        if self._business is None:
            self._business = self._resolve_business()
        return self._business

    def _resolve_business(self) -> Business | None:
        """Walk up parent chain to find Business."""
        current = self.parent
        while current is not None:
            if isinstance(current, Business):
                return current
            current = getattr(current, 'parent', None)
        return None

    def _invalidate_refs(self) -> None:
        """Invalidate cached refs on hierarchy change."""
        self._business = None
```

---

## Children Population Pattern

Holders populate their children from subtasks:

```python
class ContactHolder(Task):
    _contacts: list[Contact] = PrivateAttr(default_factory=list)

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Convert subtasks to typed children."""
        self._contacts = []
        for task in subtasks:
            contact = Contact.model_validate(task.model_dump())
            contact._contact_holder = self
            self._contacts.append(contact)
```

---

## Module Organization

```
src/autom8_asana/models/business/
    __init__.py          # Public exports
    business.py          # Business(Task)
    contact_holder.py    # ContactHolder(Task)
    contact.py           # Contact(Task)
    unit_holder.py       # UnitHolder(Task)
    unit.py              # Unit(Task)
    location_holder.py   # LocationHolder(Task) - contains Address + Hours
    address.py           # Address(Task) - sibling of Hours
    hours.py             # Hours(Task) - sibling of Address
    fields.py            # Field name constants, enums
```

---

## Related

- [custom-fields-glossary.md](custom-fields-glossary.md) - All field definitions
- [autom8-asana-business-relationships](../autom8-asana-business-relationships/) - Navigation patterns
- [autom8-asana-business-fields](../autom8-asana-business-fields/) - Field accessor details
