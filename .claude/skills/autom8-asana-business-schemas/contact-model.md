# Contact Model

> Contact entity with owner detection and 19 custom fields

---

## Class Definition

```python
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from pydantic import PrivateAttr
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business import Business, ContactHolder

class Contact(Task):
    """Contact entity within a ContactHolder.

    Represents a person associated with a Business. One contact
    can be designated as the "owner" via the position field.
    """

    # Cached upward references (ADR-0052)
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)
```

---

## Owner Detection

The owner contact is identified by position field matching:

```python
# Owner position values (case-insensitive)
OWNER_POSITIONS: ClassVar[set[str]] = {
    "owner", "ceo", "founder", "president", "principal"
}

@property
def is_owner(self) -> bool:
    """Check if this contact is the business owner."""
    position = self.position
    if position is None:
        return False
    return position.lower() in self.OWNER_POSITIONS

# On ContactHolder
@property
def owner(self) -> Contact | None:
    """Get the owner contact (if any)."""
    for contact in self.contacts:
        if contact.is_owner:
            return contact
    return None
```

---

## Navigation Properties

Contacts navigate upward to their holders and Business (ADR-0052):

```python
@property
def business(self) -> Business | None:
    """Navigate to containing Business (cached)."""
    if self._business is None:
        self._business = self._resolve_business()
    return self._business

@property
def contact_holder(self) -> ContactHolder | None:
    """Navigate to containing ContactHolder (cached)."""
    if self._contact_holder is None and self.parent:
        self._contact_holder = self.parent
    return self._contact_holder

def _resolve_business(self) -> Business | None:
    """Walk up the tree to find Business root."""
    current = self.parent
    while current is not None:
        if isinstance(current, Business):
            return current
        current = getattr(current, 'parent', None)
    return None

def _invalidate_refs(self) -> None:
    """Invalidate cached references on hierarchy change."""
    self._business = None
    self._contact_holder = None
```

---

## Custom Fields (19 Fields)

### Field Constants

```python
class Fields:
    """Custom field name constants."""
    BUILD_CALL_LINK = "Build Call Link"
    CAMPAIGN = "Campaign"
    CITY = "City"
    CONTACT_EMAIL = "Contact Email"
    CONTACT_PHONE = "Contact Phone"
    CONTACT_URL = "Contact URL"
    CONTENT = "Content"
    DASHBOARD_USER = "Dashboard User"
    EMPLOYEE_ID = "Employee ID"
    MEDIUM = "Medium"
    NICKNAME = "Nickname"
    POSITION = "Position"
    PREFIX = "Prefix"
    PROFILE_PHOTO_URL = "Profile Photo URL"
    SOURCE = "Source"
    SUFFIX = "Suffix"
    TERM = "Term"
    TIME_ZONE = "Time Zone"
    TEXT_COMMUNICATION = "Text Communication"
```

### Key Property Examples

```python
@property
def contact_phone(self) -> str | None:
    """Contact phone number (custom field)."""
    return self.get_custom_fields().get(self.Fields.CONTACT_PHONE)

@property
def contact_email(self) -> str | None:
    """Contact email address (custom field)."""
    return self.get_custom_fields().get(self.Fields.CONTACT_EMAIL)

@property
def position(self) -> str | None:
    """Job position/title (enum custom field)."""
    value = self.get_custom_fields().get(self.Fields.POSITION)
    if isinstance(value, dict):
        return value.get("name")
    return value

@property
def nickname(self) -> str | None:
    """Preferred nickname (custom field)."""
    return self.get_custom_fields().get(self.Fields.NICKNAME)
```

---

## Name Parsing

Contact names can be parsed into components:

```python
from nameparser import HumanName

def parse_name(self) -> HumanName:
    """Parse full_name into components."""
    return HumanName(self.full_name or "")

@property
def first_name(self) -> str | None:
    """First name (derived or custom field)."""
    # Check custom field first
    value = self.get_custom_fields().get(self.Fields.FIRST_NAME)
    if value:
        return value
    # Fall back to parsing full_name
    parsed = self.parse_name()
    return parsed.first or None

@property
def last_name(self) -> str | None:
    """Last name (derived or custom field)."""
    value = self.get_custom_fields().get(self.Fields.LAST_NAME)
    if value:
        return value
    parsed = self.parse_name()
    return parsed.last or None
```

---

## Name Parsing

Contact names are derived from the Task `name` property (standard Asana field), combined with custom fields like prefix and suffix:

```python
from nameparser import HumanName

@property
def full_name(self) -> str:
    """Full name derived from Task.name."""
    return self.name or ""

def parse_name(self) -> HumanName:
    """Parse Task.name into components."""
    return HumanName(self.name or "")

@property
def first_name(self) -> str | None:
    """First name (parsed from Task.name)."""
    parsed = self.parse_name()
    return parsed.first or None

@property
def last_name(self) -> str | None:
    """Last name (parsed from Task.name)."""
    parsed = self.parse_name()
    return parsed.last or None

@property
def display_name(self) -> str:
    """Display name with optional prefix/suffix."""
    parts = []
    if self.prefix:
        parts.append(self.prefix)
    parts.append(self.name or "")
    if self.suffix:
        parts.append(self.suffix)
    return " ".join(parts).strip()

@property
def preferred_name(self) -> str:
    """Nickname if set, otherwise first name."""
    return self.nickname or self.first_name or self.name or ""
```

---

## ContactHolder

The holder that contains Contact children:

```python
class ContactHolder(Task):
    """Holder task containing Contact children."""

    _contacts: list[Contact] = PrivateAttr(default_factory=list)

    @property
    def contacts(self) -> list[Contact]:
        """All Contact children."""
        return self._contacts

    @property
    def owner(self) -> Contact | None:
        """Get the owner contact (if any)."""
        for contact in self._contacts:
            if contact.is_owner:
                return contact
        return None

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate contacts from fetched subtasks."""
        self._contacts = [
            Contact.model_validate(t.model_dump())
            for t in subtasks
        ]
        # Set parent references
        for contact in self._contacts:
            contact._contact_holder = self
```

---

## Usage Example

```python
async with client.save_session() as session:
    session.track(business, prefetch_holders=True)

    # Find owner contact
    owner = business.contact_holder.owner
    if owner:
        print(f"Owner: {owner.full_name}, {owner.position}")

    # Iterate contacts
    for contact in business.contacts:
        # Navigate up to business
        assert contact.business is business

        # Access fields
        print(f"{contact.full_name}: {contact.contact_email}")
```

---

## Related

- [business-model.md](business-model.md) - Parent Business entity
- [custom-fields-glossary.md](custom-fields-glossary.md) - All 19 Contact fields
- [autom8-asana-business-relationships](../autom8-asana-business-relationships/) - Navigation patterns
