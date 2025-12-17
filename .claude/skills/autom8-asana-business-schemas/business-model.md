# Business Model

> Root entity of the business hierarchy with 7 holder properties

---

## Class Definition

```python
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from pydantic import PrivateAttr
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business import (
        ContactHolder, UnitHolder, LocationHolder,
        Contact, Unit, Address, Hours
    )

class Business(Task):
    """Business entity - root of the holder hierarchy.

    A Business task contains 7 holder subtasks, each managing
    a collection of domain-specific child tasks.
    """

    # Holder type detection map: property_name -> (task_name, emoji)
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "person"),
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "map"),
        "dna_holder": ("DNA", "dna"),
        "reconciliations_holder": ("Reconciliations", "abacus"),
        "asset_edit_holder": ("Asset Edit", "scissors"),
        "videography_holder": ("Videography", "video_camera"),
    }

    # Private cached holder references (populated by SaveSession.track)
    _contact_holder: ContactHolder | None = PrivateAttr(default=None)
    _unit_holder: UnitHolder | None = PrivateAttr(default=None)
    _location_holder: LocationHolder | None = PrivateAttr(default=None)
    _dna_holder: Task | None = PrivateAttr(default=None)
    _reconciliations_holder: Task | None = PrivateAttr(default=None)
    _asset_edit_holder: Task | None = PrivateAttr(default=None)
    _videography_holder: Task | None = PrivateAttr(default=None)
```

---

## Holder Properties

Each holder property returns the cached holder task (populated by `SaveSession.track()`):

```python
@property
def contact_holder(self) -> ContactHolder | None:
    """ContactHolder subtask containing Contact children."""
    return self._contact_holder

@property
def unit_holder(self) -> UnitHolder | None:
    """UnitHolder subtask containing Unit children."""
    return self._unit_holder

@property
def location_holder(self) -> LocationHolder | None:
    """LocationHolder subtask containing Address + Hours (siblings)."""
    return self._location_holder

# Convenience shortcuts for single-location business
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

# Convenience shortcuts
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
```

---

## Custom Fields (19 Fields)

Business has 19 typed custom field properties. See [custom-fields-glossary.md](custom-fields-glossary.md) for full list.

### Field Constants

```python
class Fields:
    """Custom field name constants for IDE discoverability."""
    AGGRESSION_LEVEL = "Aggression Level"
    BOOKING_TYPE = "Booking Type"
    COMPANY_ID = "Company ID"
    FACEBOOK_PAGE_ID = "Facebook Page ID"
    FALLBACK_PAGE_ID = "Fallback Page ID"
    GOOGLE_CAL_ID = "Google Cal ID"
    NUM_REVIEWS = "Num Reviews"
    OFFICE_PHONE = "Office Phone"
    OWNER_NAME = "Owner Name"
    OWNER_NICKNAME = "Owner Nickname"
    REP = "Rep"
    REVIEW_1 = "Review 1"
    REVIEW_2 = "Review 2"
    REVIEWS_LINK = "Reviews Link"
    STRIPE_ID = "Stripe ID"
    STRIPE_LINK = "Stripe Link"
    TWILIO_PHONE_NUM = "Twilio Phone Num"
    VCA_STATUS = "VCA Status"
    VERTICAL = "Vertical"
```

---

## Cascading Fields (ADR-0054)

Business owns fields that cascade to descendants for read efficiency:

```python
from autom8_asana.models.business.fields import CascadingFieldDef

class Business(Task):
    """Business with cascading field declarations."""

    class CascadingFields:
        """Fields that cascade from Business to descendants."""

        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            targets=["Unit", "Offer", "Process"],
        )

        COMPANY_ID = CascadingFieldDef(
            name="Company ID",
            targets=["*"],  # All descendants
        )

        BUSINESS_NAME = CascadingFieldDef(
            name="Business Name",
            targets=["Unit", "Offer"],
            source_field="name",  # Maps from Task.name
        )

        PRIMARY_CONTACT_PHONE = CascadingFieldDef(
            name="Primary Contact Phone",
            targets=["Unit", "Offer", "Process"],
        )

        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            return [
                cls.OFFICE_PHONE,
                cls.COMPANY_ID,
                cls.BUSINESS_NAME,
                cls.PRIMARY_CONTACT_PHONE,
            ]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None
```

### Cascade Usage

```python
async with client.save_session() as session:
    session.track(business)
    business.office_phone = "555-9999"

    # Explicitly cascade to descendants
    session.cascade_field(business, "Office Phone")

    # Saves Business, then batch updates descendants
    await session.commit_async()
```

See [cascading-inherited-fields.md](../autom8-asana-business-fields/cascading-inherited-fields.md) for patterns.

### Property Examples

```python
@property
def company_id(self) -> str | None:
    """Company identifier (custom field)."""
    return self.get_custom_fields().get(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

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
```

---

## Holder Population

Holders are populated by `SaveSession.track()` with `prefetch_holders=True` (ADR-0050):

```python
def _populate_holders(self, subtasks: list[Task]) -> None:
    """Populate holder properties from fetched subtasks.

    Called by SaveSession after fetching Business subtasks.
    Matches subtasks to holders via name and emoji indicators.
    """
    for subtask in subtasks:
        for holder_name, (name_pattern, emoji) in self.HOLDER_KEY_MAP.items():
            # Match by name or emoji indicator
            if subtask.name == name_pattern or self._has_emoji(subtask, emoji):
                # Convert to typed holder if applicable
                holder = self._create_typed_holder(holder_name, subtask)
                setattr(self, f"_{holder_name}", holder)
                break

def _create_typed_holder(self, holder_name: str, task: Task) -> Task:
    """Create typed holder from generic Task."""
    if holder_name == "contact_holder":
        return ContactHolder.model_validate(task.model_dump())
    elif holder_name == "unit_holder":
        return UnitHolder.model_validate(task.model_dump())
    elif holder_name == "location_holder":
        return LocationHolder.model_validate(task.model_dump())
    return task  # Return as-is for stub holders
```

---

## Usage Example

```python
async with client.save_session() as session:
    # Track business with holder prefetch
    session.track(business, prefetch_holders=True)

    # Access holders and children
    for contact in business.contacts:
        print(f"Contact: {contact.full_name}")

    # Modify business fields
    business.company_id = "ACME-001"
    business.mrr = Decimal("5000.00")

    # Commit changes
    result = await session.commit_async()
```

---

## Related

- [contact-model.md](contact-model.md) - Contact entity details
- [unit-model.md](unit-model.md) - Unit entity with nested holders
- [address-model.md](address-model.md) - Address entity (sibling of Hours)
- [hours-model.md](hours-model.md) - Hours entity (sibling of Address)
- [custom-fields-glossary.md](custom-fields-glossary.md) - All field definitions
- [autom8-asana-business-relationships](../autom8-asana-business-relationships/) - Holder pattern details
