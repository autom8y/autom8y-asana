# Address Model

> Address entity (sibling of Hours under LocationHolder)

---

## Class Definition

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from pydantic import PrivateAttr
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business import Business, LocationHolder, Hours

class Address(Task):
    """Address entity within a LocationHolder.

    Represents the physical address for a Business. Address is a
    sibling subtask of Hours under LocationHolder (not a parent).
    
    Hierarchy:
        Business
            └── LocationHolder
                    ├── Address (this entity)
                    └── Hours (sibling)
    """

    # Cached references
    _business: Business | None = PrivateAttr(default=None)
    _location_holder: LocationHolder | None = PrivateAttr(default=None)
    _hours: Hours | None = PrivateAttr(default=None)  # Sibling reference
```

---

## Custom Fields (12 Fields)

### Field Constants

```python
class Fields:
    """Custom field name constants."""
    CITY = "City"
    COUNTRY = "Country"
    MAX_RADIUS = "Max Radius"
    MIN_RADIUS = "Min Radius"
    NEIGHBORHOOD = "Neighborhood"
    OFFICE_LOCATION = "Office Location"
    STATE = "State"
    STREET_NAME = "Street Name"
    STREET_NUM = "Street Num"
    SUITE = "Suite"
    TIME_ZONE = "Time Zone"
    ZIP_CODE = "Zip Code"
```

---

## Navigation Properties

Address navigates to its parent holder and sibling Hours:

```python
@property
def business(self) -> Business | None:
    """Navigate to containing Business (cached)."""
    if self._business is None:
        self._business = self._resolve_business()
    return self._business

@property
def location_holder(self) -> LocationHolder | None:
    """Navigate to containing LocationHolder (cached)."""
    if self._location_holder is None and self.parent:
        self._location_holder = self.parent
    return self._location_holder

@property
def hours(self) -> Hours | None:
    """Navigate to sibling Hours entity (cached)."""
    return self._hours

def _resolve_business(self) -> Business | None:
    """Walk up the tree to find Business root."""
    holder = self.location_holder
    if holder and holder.parent:
        return holder.parent
    return None
```

---

## LocationHolder

The holder that contains Address and Hours as siblings:

```python
class LocationHolder(Task):
    """Holder task containing Address and Hours as siblings."""

    _address: Address | None = PrivateAttr(default=None)
    _hours: Hours | None = PrivateAttr(default=None)

    @property
    def address(self) -> Address | None:
        """The Address child (singular)."""
        return self._address

    @property
    def hours(self) -> Hours | None:
        """The Hours child (singular)."""
        return self._hours

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate address and hours from fetched subtasks."""
        for subtask in subtasks:
            if subtask.name == "Address" or self._has_emoji(subtask, "house"):
                self._address = Address.model_validate(subtask.model_dump())
                self._address._location_holder = self
            elif subtask.name == "Hours" or self._has_emoji(subtask, "clock"):
                self._hours = Hours.model_validate(subtask.model_dump())
                self._hours._location_holder = self
        
        # Link siblings to each other
        if self._address and self._hours:
            self._address._hours = self._hours
            self._hours._address = self._address
```

---

## Usage Example

```python
async with client.save_session() as session:
    session.track(business, prefetch_holders=True)

    # Access via location_holder
    address = business.location_holder.address
    hours = business.location_holder.hours

    if address:
        # Access address fields
        print(f"Address: {address.name}")

    if hours:
        # Access hours (sibling of address)
        print(f"Monday: {hours.monday}")

    # Navigate between siblings
    if address and address.hours:
        print(f"Hours sibling: {address.hours.name}")
```

---

## Related

- [hours-model.md](hours-model.md) - Sibling Hours entity
- [business-model.md](business-model.md) - Parent Business entity
- [custom-fields-glossary.md](custom-fields-glossary.md) - All Address fields

