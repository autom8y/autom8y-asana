# Unit Model

> Unit entity with nested holders and 31 custom fields

---

## Class Definition

```python
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from decimal import Decimal
from pydantic import PrivateAttr
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business import Business, UnitHolder

class Unit(Task):
    """Unit entity within a UnitHolder.

    Units represent service packages or product offerings. Each Unit
    can contain nested OfferHolder and ProcessHolder subtasks.
    """

    # Nested holder type detection (recursive HOLDER_KEY_MAP)
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "offer_holder": ("Offers", "gift"),
        "process_holder": ("Processes", "gear"),
    }

    # Cached references
    _business: Business | None = PrivateAttr(default=None)
    _unit_holder: UnitHolder | None = PrivateAttr(default=None)
    _offer_holder: Task | None = PrivateAttr(default=None)
    _process_holder: Task | None = PrivateAttr(default=None)
```

---

## Nested Holders

Units contain their own holders (composite pattern). **Offers are the unit of work** for determining ad status (are ads running or not).

```python
@property
def offer_holder(self) -> OfferHolder | None:
    """OfferHolder subtask containing Offer children.
    
    Offers determine account status - each represents an ad campaign.
    See offer-model.md for the 39 Offer fields.
    """
    return self._offer_holder

@property
def process_holder(self) -> Task | None:
    """ProcessHolder subtask containing Process children."""
    return self._process_holder

@property
def offers(self) -> list[Offer]:
    """All Offer children (via OfferHolder)."""
    if self._offer_holder is None:
        return []
    return self._offer_holder.offers

@property
def active_offers(self) -> list[Offer]:
    """Offers with active ads running."""
    if self._offer_holder is None:
        return []
    return [o for o in self._offer_holder.offers if o.has_active_ads]

@property
def processes(self) -> list[Task]:
    """All Process children (via ProcessHolder)."""
    if self._process_holder is None:
        return []
    return getattr(self._process_holder, '_children', [])
```

---

## Navigation Properties

Units navigate upward to their UnitHolder and Business:

```python
@property
def business(self) -> Business | None:
    """Navigate to containing Business (cached)."""
    if self._business is None:
        self._business = self._resolve_business()
    return self._business

@property
def unit_holder(self) -> UnitHolder | None:
    """Navigate to containing UnitHolder (cached)."""
    if self._unit_holder is None and self.parent:
        self._unit_holder = self.parent
    return self._unit_holder

def _resolve_business(self) -> Business | None:
    """Walk up the tree to find Business root."""
    current = self.parent
    while current is not None:
        if isinstance(current, Business):
            return current
        current = getattr(current, 'parent', None)
    return None
```

---

## Cascading Fields (ADR-0054)

Units can declare their own cascading fields that propagate to their descendants (Offers, Processes).

**Critical Design Constraint**: `allow_override=False` is the DEFAULT. Only use `allow_override=True` when the business requirement specifically demands that descendants can maintain their own values.

```python
from autom8_asana.models.business.fields import CascadingFieldDef

class Unit(Task):
    """Unit with cascading field declarations to its children.

    MULTI-LEVEL CASCADING: Unit can cascade fields to its Offers/Processes,
    independent of Business-level cascading.
    """

    class CascadingFields:
        """Fields that cascade from Unit to its descendants.

        NOTE: Some fields allow override (explicit opt-in), others don't.
        """

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

        BOOKING_TYPE = CascadingFieldDef(
            name="Booking Type",
            target_types={Offer},
            # allow_override=False is DEFAULT
        )

        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            return [cls.PLATFORMS, cls.VERTICAL, cls.BOOKING_TYPE]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None
```

### Cascade Usage from Unit

```python
async with client.save_session() as session:
    session.track(unit, recursive=True)

    # Set unit's platforms (with override opt-in)
    unit.platforms = ["Google", "Meta"]
    session.cascade_field(unit, "Platforms")

    await session.commit_async()

    # Results:
    # - Offers with platforms=None: Updated to ["Google", "Meta"]
    # - Offers with existing platforms: KEPT their original value

async with client.save_session() as session:
    session.track(unit, recursive=True)

    # Set unit's vertical (no override - default)
    unit.vertical = "Retail"
    session.cascade_field(unit, "Vertical")

    await session.commit_async()

    # Results:
    # - ALL Offers and Processes get "Retail" regardless of current value
```

---

## Inherited Fields (ADR-0054)

Units inherit certain fields from Business unless locally set:

```python
from autom8_asana.models.business.fields import InheritedFieldDef

class Unit(Task):
    """Unit with inherited field declarations."""

    class InheritedFields:
        """Fields inherited from parent entities."""

        DEFAULT_VERTICAL = InheritedFieldDef(
            name="Default Vertical",
            inherit_from=["Business"],  # Inherit from Business
            allow_override=True,
            default="General",
        )

        @classmethod
        def all(cls) -> list[InheritedFieldDef]:
            return [cls.DEFAULT_VERTICAL]
```

See [cascading-inherited-fields.md](../autom8-asana-business-fields/cascading-inherited-fields.md) for patterns.

---

## Custom Fields (31 Fields)

### Field Constants

```python
class Fields:
    """Custom field name constants."""
    # Financial
    MRR = "MRR"
    WEEKLY_AD_SPEND = "Weekly Ad Spend"
    DISCOUNT = "Discount"
    CURRENCY = "Currency"
    META_SPEND = "Meta Spend"
    META_SPEND_SUB_ID = "Meta Spend Sub ID"
    TIKTOK_SPEND = "Tiktok Spend"
    TIKTOK_SPEND_SUB_ID = "Tiktok Spend Sub ID"
    SOLUTION_FEE_SUB_ID = "Solution Fee Sub ID"

    # Ad Account / Platform
    AD_ACCOUNT_ID = "Ad Account ID"
    PLATFORMS = "Platforms"
    TIKTOK_PROFILE = "Tiktok Profile"

    # Product / Service
    PRODUCTS = "Products"
    LANGUAGES = "Languages"
    VERTICAL = "Vertical"
    SPECIALTY = "Specialty"
    REP = "Rep"

    # Demographics / Targeting
    RADIUS = "Radius"
    MIN_AGE = "Min Age"
    MAX_AGE = "Max Age"
    GENDER = "Gender"
    ZIP_CODE_LIST = "Zip Code List"
    ZIP_CODES_RADIUS = "Zip Codes Radius"
    EXCLUDED_ZIPS = "Excluded Zips"

    # Form / Lead Settings
    FORM_QUESTIONS = "Form Questions"
    DISABLED_QUESTIONS = "Disabled Questions"
    DISCLAIMERS = "Disclaimers"
    CUSTOM_DISCLAIMER = "Custom Disclaimer"
    SMS_LEAD_VERIFICATION = "Sms Lead Verification"
    WORK_EMAIL_VERIFICATION = "Work Email Verification"
    FILTER_OUT_X = "Filter Out X"
```

### Property Examples

```python
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

@property
def weekly_ad_spend(self) -> Decimal | None:
    """Weekly advertising spend (custom field)."""
    value = self.get_custom_fields().get(self.Fields.WEEKLY_AD_SPEND)
    return Decimal(str(value)) if value is not None else None

@property
def products(self) -> list[str]:
    """Product list (multi-enum custom field)."""
    value = self.get_custom_fields().get(self.Fields.PRODUCTS)
    if value is None:
        return []
    # Handle multi-enum format from API
    if isinstance(value, list):
        return [v.get("name") if isinstance(v, dict) else v for v in value]
    return []

@property
def vertical(self) -> str | None:
    """Business vertical (enum custom field)."""
    value = self.get_custom_fields().get(self.Fields.VERTICAL)
    if isinstance(value, dict):
        return value.get("name")
    return value
```

---

## UnitHolder

The holder that contains Unit children:

```python
class UnitHolder(Task):
    """Holder task containing Unit children."""

    _units: list[Unit] = PrivateAttr(default_factory=list)

    @property
    def units(self) -> list[Unit]:
        """All Unit children."""
        return self._units

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate units from fetched subtasks."""
        self._units = [
            Unit.model_validate(t.model_dump())
            for t in subtasks
        ]
        for unit in self._units:
            unit._unit_holder = self
```

---

## Name Convention

Unit names follow the pattern `"{vertical} - ${mrr}"`:

```python
def update_name(self) -> None:
    """Update task name from field values."""
    vertical = self.vertical or "Unknown"
    mrr = self.mrr or Decimal("0")
    self.name = f"{vertical} - ${mrr:,.2f}"
```

---

## Usage Example

```python
async with client.save_session() as session:
    session.track(business, prefetch_holders=True)

    # Iterate units
    for unit in business.units:
        # Access financial fields
        print(f"{unit.vertical}: ${unit.mrr} MRR, ${unit.weekly_ad_spend}/week")

        # Access multi-enum fields
        print(f"  Products: {', '.join(unit.products)}")

        # Navigate to nested holders (if prefetched)
        for process in unit.processes:
            print(f"  Process: {process.name}")
```

---

## Related

- [business-model.md](business-model.md) - Parent Business entity
- [offer-model.md](offer-model.md) - Child Offer entity (39 fields, ad status)
- [custom-fields-glossary.md](custom-fields-glossary.md) - All 31 Unit fields
- [autom8-asana-business-relationships](../autom8-asana-business-relationships/) - Composite pattern
