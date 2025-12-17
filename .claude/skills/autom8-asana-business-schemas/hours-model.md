# Hours Model

> Business hours entity (sibling of Address under LocationHolder)

---

## Class Definition

```python
from __future__ import annotations
from typing import TYPE_CHECKING
from pydantic import PrivateAttr
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business import Business, LocationHolder, Address

class Hours(Task):
    """Business hours entity within a LocationHolder.

    Stores operating hours for each day of the week as
    formatted strings (e.g., "9:00 AM - 5:00 PM").
    
    Hours is a sibling subtask of Address under LocationHolder (not a child).
    
    Hierarchy:
        Business
            └── LocationHolder
                    ├── Address (sibling)
                    └── Hours (this entity)
    """

    # Cached references
    _location_holder: LocationHolder | None = PrivateAttr(default=None)
    _address: Address | None = PrivateAttr(default=None)  # Sibling reference
```

---

## Custom Fields (7 Fields)

### Field Constants

```python
class Fields:
    """Custom field name constants."""
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"
```

### Property Examples

```python
@property
def monday(self) -> str | None:
    """Monday hours (custom field)."""
    return self.get_custom_fields().get(self.Fields.MONDAY)

@monday.setter
def monday(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.MONDAY, value)

@property
def tuesday(self) -> str | None:
    """Tuesday hours (custom field)."""
    return self.get_custom_fields().get(self.Fields.TUESDAY)

# ... similar for other days
```

---

## Hours Array

Convenience method to get all hours as a list:

```python
@property
def all_days(self) -> list[tuple[str, str | None]]:
    """All days with their hours as (day, hours) tuples."""
    return [
        ("Monday", self.monday),
        ("Tuesday", self.tuesday),
        ("Wednesday", self.wednesday),
        ("Thursday", self.thursday),
        ("Friday", self.friday),
        ("Saturday", self.saturday),
        ("Sunday", self.sunday),
    ]

@property
def weekday_hours(self) -> list[str | None]:
    """Hours for Monday through Friday."""
    return [self.monday, self.tuesday, self.wednesday,
            self.thursday, self.friday]

@property
def weekend_hours(self) -> list[str | None]:
    """Hours for Saturday and Sunday."""
    return [self.saturday, self.sunday]

def to_dict(self) -> dict[str, str | None]:
    """Convert to dictionary keyed by day name."""
    return {
        "monday": self.monday,
        "tuesday": self.tuesday,
        "wednesday": self.wednesday,
        "thursday": self.thursday,
        "friday": self.friday,
        "saturday": self.saturday,
        "sunday": self.sunday,
    }
```

---

## Hours Format

Standard hours format: `"HH:MM AM/PM - HH:MM AM/PM"` or `"Closed"`

```python
CLOSED = "Closed"
HOURS_24 = "24 Hours"

def is_open(self, day: str) -> bool:
    """Check if open on a given day."""
    hours = self.get_hours_for_day(day)
    if hours is None or hours.lower() == "closed":
        return False
    return True

def get_hours_for_day(self, day: str) -> str | None:
    """Get hours by day name (case-insensitive)."""
    day_map = {
        "monday": self.monday,
        "tuesday": self.tuesday,
        "wednesday": self.wednesday,
        "thursday": self.thursday,
        "friday": self.friday,
        "saturday": self.saturday,
        "sunday": self.sunday,
    }
    return day_map.get(day.lower())
```

---

## Bulk Updates

Set all weekday or weekend hours at once:

```python
def set_weekday_hours(self, hours: str) -> None:
    """Set the same hours for all weekdays."""
    self.monday = hours
    self.tuesday = hours
    self.wednesday = hours
    self.thursday = hours
    self.friday = hours

def set_weekend_hours(self, hours: str) -> None:
    """Set the same hours for weekend."""
    self.saturday = hours
    self.sunday = hours

def set_all_hours(self, hours: str) -> None:
    """Set the same hours for all days."""
    self.set_weekday_hours(hours)
    self.set_weekend_hours(hours)
```

---

## Navigation Properties

```python
@property
def location_holder(self) -> LocationHolder | None:
    """Navigate to parent LocationHolder (cached)."""
    return self._location_holder

@property
def address(self) -> Address | None:
    """Navigate to sibling Address entity (cached)."""
    return self._address

@property
def business(self) -> Business | None:
    """Navigate to containing Business."""
    holder = self.location_holder
    if holder and holder.parent:
        return holder.parent
    return None
```

---

## Usage Example

```python
async with client.save_session() as session:
    session.track(business, prefetch_holders=True)

    # Access hours directly from location_holder (sibling of address)
    hours = business.location_holder.hours

    if hours:
        # Check if open on a day
        if hours.is_open("monday"):
            print(f"Monday: {hours.monday}")

        # Get all hours as dict
        hours_dict = hours.to_dict()

        # Set standard business hours
        hours.set_weekday_hours("9:00 AM - 5:00 PM")
        hours.set_weekend_hours("Closed")

        # Navigate to sibling Address
        address = hours.address

        # Commit changes
        session.track(hours)
        await session.commit_async()
```

---

## Related

- [address-model.md](address-model.md) - Sibling Address entity
- [business-model.md](business-model.md) - Root Business entity
