# Holder Pattern

> How Business entities organize children into holder subtasks

---

## What is a Holder?

A **holder** is a Task subtask that groups related children:

```
Business Task: "Acme Corp"
    |
    +-- Subtask: "Contacts" (ContactHolder)
    |       +-- Subtask: "John Smith" (Contact)
    |       +-- Subtask: "Jane Doe" (Contact)
    |
    +-- Subtask: "Units" (UnitHolder)
            +-- Subtask: "Legal - $5,000" (Unit)
```

Holders provide:
- **Organization**: Group related tasks under descriptive parent
- **Type safety**: Each holder contains specific entity types
- **Navigation**: Easy traversal up and down hierarchy

---

## HOLDER_KEY_MAP

Entities with holders define `HOLDER_KEY_MAP`:

```python
from typing import ClassVar

class Business(Task):
    """Business with 7 holder types."""

    # Map: property_name -> (task_name, emoji_indicator)
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "person"),
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "map"),
        "dna_holder": ("DNA", "dna"),
        "reconciliations_holder": ("Reconciliations", "abacus"),
        "asset_edit_holder": ("Asset Edit", "scissors"),
        "videography_holder": ("Videography", "video_camera"),
    }
```

### Detection Priority

1. **Name match**: Exact match on task name ("Contacts")
2. **Emoji match**: Custom emoji name matches ("person")

```python
def _matches_holder(self, task: Task, holder_key: str) -> bool:
    """Check if task matches a holder definition."""
    name_pattern, emoji = self.HOLDER_KEY_MAP[holder_key]

    # Check name first
    if task.name == name_pattern:
        return True

    # Fall back to emoji
    if hasattr(task, 'custom_emoji') and task.custom_emoji:
        return task.custom_emoji.get('name') == emoji

    return False
```

---

## Holder Properties

Each holder has a typed property:

```python
class Business(Task):
    # Private storage (populated by prefetch)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)
    _unit_holder: UnitHolder | None = PrivateAttr(default=None)

    @property
    def contact_holder(self) -> ContactHolder | None:
        """ContactHolder subtask containing Contact children."""
        return self._contact_holder

    @property
    def unit_holder(self) -> UnitHolder | None:
        """UnitHolder subtask containing Unit children."""
        return self._unit_holder
```

### Convenience Shortcuts

Direct access to children:

```python
@property
def contacts(self) -> list[Contact]:
    """All Contact children (via ContactHolder)."""
    if self._contact_holder is None:
        return []
    return self._contact_holder.contacts

@property
def units(self) -> list[Unit]:
    """All Unit children (via UnitHolder)."""
    if self._unit_holder is None:
        return []
    return self._unit_holder.units

# Single-location business: Address and Hours are siblings
@property
def address(self) -> Address | None:
    """Business address (via LocationHolder)."""
    if self._location_holder is None:
        return None
    return self._location_holder.address

@property
def hours(self) -> Hours | None:
    """Business hours (via LocationHolder)."""
    if self._location_holder is None:
        return None
    return self._location_holder.hours
```

---

## Holder Task Classes

Each holder type is a Task subclass:

```python
class ContactHolder(Task):
    """Holder task containing Contact children."""

    # Children storage
    _contacts: list[Contact] = PrivateAttr(default_factory=list)

    @property
    def contacts(self) -> list[Contact]:
        """All Contact children."""
        return self._contacts

    @property
    def owner(self) -> Contact | None:
        """Owner contact (if any)."""
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
        # Set back-references
        for contact in self._contacts:
            contact._contact_holder = self
```

### LocationHolder (Special Case)

LocationHolder contains two **sibling** entities (not a list):

```python
class LocationHolder(Task):
    """Holder with Address and Hours as siblings."""

    _address: Address | None = PrivateAttr(default=None)
    _hours: Hours | None = PrivateAttr(default=None)

    @property
    def address(self) -> Address | None:
        return self._address

    @property
    def hours(self) -> Hours | None:
        return self._hours

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate address and hours from sibling subtasks."""
        for subtask in subtasks:
            if subtask.name == "Address":
                self._address = Address.model_validate(subtask.model_dump())
            elif subtask.name == "Hours":
                self._hours = Hours.model_validate(subtask.model_dump())
        # Link siblings
        if self._address and self._hours:
            self._address._hours = self._hours
            self._hours._address = self._address
```

---

## Holder Population Flow

```
1. SaveSession.track(business, prefetch_holders=True)
       |
       v
2. API call: get_subtasks(business.gid)
       |
       v
3. Returns: [Task("Contacts"), Task("Units"), Task("Location"), ...]
       |
       v
4. business._populate_holders(subtasks)
       |
       v
5. For each holder:
   - Match to HOLDER_KEY_MAP entry
   - Create typed holder instance
   - Store in _contact_holder, _unit_holder, etc.
       |
       v
6. For each holder with children:
   - API call: get_subtasks(holder.gid)
   - holder._populate_children(subtasks)
```

---

## Population Implementation

```python
class Business(Task):
    def _populate_holders(self, subtasks: list[Task]) -> None:
        """Populate holder properties from fetched subtasks."""
        for subtask in subtasks:
            holder_key = self._identify_holder(subtask)
            if holder_key:
                holder = self._create_typed_holder(holder_key, subtask)
                setattr(self, f"_{holder_key}", holder)

    def _identify_holder(self, task: Task) -> str | None:
        """Identify which holder type a task is."""
        for key, (name, emoji) in self.HOLDER_KEY_MAP.items():
            if self._matches_holder(task, key):
                return key
        return None

    def _create_typed_holder(self, key: str, task: Task) -> Task:
        """Create typed holder from generic Task."""
        holder_classes = {
            "contact_holder": ContactHolder,
            "unit_holder": UnitHolder,
            "location_holder": LocationHolder,
        }
        holder_class = holder_classes.get(key, Task)
        holder = holder_class.model_validate(task.model_dump())
        return holder
```

---

## Adding to Holder

Add new children to a holder:

```python
# Create new contact
new_contact = Contact(
    gid=f"temp_{uuid4()}",
    name="New Contact",
    parent=business.contact_holder,
)

# Set custom fields
new_contact.full_name = "New Person"
new_contact.contact_email = "new@example.com"

# Track for saving
async with client.save_session() as session:
    session.track(business)
    session.track(new_contact)
    await session.commit_async()
```

---

## Related

- [lazy-loading.md](lazy-loading.md) - When holders are populated
- [bidirectional-navigation.md](bidirectional-navigation.md) - Navigating from children
- [composite-pattern.md](composite-pattern.md) - Nested holders (Unit)
