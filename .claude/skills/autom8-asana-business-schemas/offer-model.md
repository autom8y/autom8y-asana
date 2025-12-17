# Offer Model

> Offer entity with 39 custom fields - the unit of work for ad status

---

## Class Definition

```python
from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from decimal import Decimal
from pydantic import PrivateAttr
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business import Business, Unit, OfferHolder

class Offer(Task):
    """Offer entity within an OfferHolder.

    Offers represent individual ad campaigns/placements and are the
    unit of work for determining account status (are ads running or not).
    
    Hierarchy:
        Business
            └── UnitHolder
                  └── Unit
                        └── OfferHolder
                              └── Offer (this entity)
    """

    NAME_CONVENTION: ClassVar[str] = "[Offer Name]"

    # Cached references
    _business: Business | None = PrivateAttr(default=None)
    _unit: Unit | None = PrivateAttr(default=None)
    _offer_holder: OfferHolder | None = PrivateAttr(default=None)
```

---

## Custom Fields (39 Fields)

### Field Constants

```python
class Fields:
    """Custom field name constants."""
    # Financial (5)
    MRR = "MRR"
    COST = "Cost"
    WEEKLY_AD_SPEND = "Weekly Ad Spend"
    VOUCHER_VALUE = "Voucher Value"
    BUDGET_ALLOCATION = "Budget Allocation"

    # Ad Platform IDs (7)
    AD_ID = "Ad ID"
    AD_SET_ID = "Ad Set ID"
    CAMPAIGN_ID = "Campaign ID"
    ASSET_ID = "Asset ID"
    AD_ACCOUNT_URL = "Ad Account URL"
    ACTIVE_ADS_URL = "Active Ads URL"
    PLATFORMS = "Platforms"

    # Content (8)
    OFFER_HEADLINE = "Offer Headline"
    INCLUDED_ITEM_1 = "Included Item 1"
    INCLUDED_ITEM_2 = "Included Item 2"
    INCLUDED_ITEM_3 = "Included Item 3"
    LANDING_PAGE_URL = "Landing Page URL"
    PREVIEW_LINK = "Preview Link"
    LEAD_TESTING_LINK = "Lead Testing Link"
    NUM_AI_COPIES = "Num AI Copies"

    # Configuration (9)
    FORM_ID = "Form ID"
    LANGUAGE = "Language"
    SPECIALTY = "Specialty"
    VERTICAL = "Vertical"
    TARGETING = "Targeting"
    TARGETING_STRATEGIES = "Targeting Strategies"
    OPTIMIZE_FOR = "Optimize For"
    CAMPAIGN_TYPE = "Campaign Type"
    OFFICE_PHONE = "Office Phone"

    # Scheduling (4)
    APPT_DURATION = "Appt Duration"
    CALENDAR_DURATION = "Calendar Duration"
    CUSTOM_CAL_URL = "Custom Cal URL"
    OFFER_SCHEDULE_LINK = "Offer Schedule Link"

    # Notes (2)
    INTERNAL_NOTES = "Internal Notes"
    EXTERNAL_NOTES = "External Notes"

    # Metadata (4)
    OFFER_ID = "Offer ID"
    ALGO_VERSION = "Algo Version"
    TRIGGERED_BY = "Triggered By"
    REP = "Rep"
```

---

## Navigation Properties

Offers navigate upward through the hierarchy:

```python
@property
def offer_holder(self) -> OfferHolder | None:
    """Navigate to containing OfferHolder (cached)."""
    if self._offer_holder is None and self.parent:
        self._offer_holder = self.parent
    return self._offer_holder

@property
def unit(self) -> Unit | None:
    """Navigate to containing Unit (cached)."""
    if self._unit is None:
        holder = self.offer_holder
        if holder and holder.parent:
            self._unit = holder.parent
    return self._unit

@property
def business(self) -> Business | None:
    """Navigate to containing Business (cached)."""
    if self._business is None:
        unit = self.unit
        if unit:
            self._business = unit.business
    return self._business
```

---

## Key Property Examples

```python
@property
def mrr(self) -> Decimal | None:
    """Monthly recurring revenue (custom field)."""
    value = self.get_custom_fields().get(self.Fields.MRR)
    return Decimal(str(value)) if value is not None else None

@property
def weekly_ad_spend(self) -> Decimal | None:
    """Weekly ad spend (custom field)."""
    value = self.get_custom_fields().get(self.Fields.WEEKLY_AD_SPEND)
    return Decimal(str(value)) if value is not None else None

@property
def platforms(self) -> list[str]:
    """Active platforms (multi-enum custom field)."""
    value = self.get_custom_fields().get(self.Fields.PLATFORMS)
    if value is None:
        return []
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

@property
def campaign_type(self) -> str | None:
    """Campaign type (enum custom field)."""
    value = self.get_custom_fields().get(self.Fields.CAMPAIGN_TYPE)
    if isinstance(value, dict):
        return value.get("name")
    return value

@property
def rep(self) -> list[dict]:
    """Sales representative (people field)."""
    value = self.get_custom_fields().get(self.Fields.REP)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []
```

---

## Ad Status Determination

Offers are the unit of work for determining if ads are running:

```python
@property
def has_active_ads(self) -> bool:
    """Check if this offer has active ads."""
    return bool(self.active_ads_url or self.ad_id)

@property
def active_ads_url(self) -> str | None:
    """URL to active ads (custom field)."""
    return self.get_custom_fields().get(self.Fields.ACTIVE_ADS_URL)

@property
def ad_id(self) -> str | None:
    """Ad identifier (custom field)."""
    return self.get_custom_fields().get(self.Fields.AD_ID)
```

---

## OfferHolder

The holder that contains Offer children:

```python
class OfferHolder(Task):
    """Holder task containing Offer children."""

    _offers: list[Offer] = PrivateAttr(default_factory=list)

    @property
    def offers(self) -> list[Offer]:
        """All Offer children."""
        return self._offers

    @property
    def active_offers(self) -> list[Offer]:
        """Offers with active ads."""
        return [o for o in self._offers if o.has_active_ads]

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate offers from fetched subtasks."""
        self._offers = [
            Offer.model_validate(t.model_dump())
            for t in subtasks
        ]
        for offer in self._offers:
            offer._offer_holder = self
```

---

## Usage Example

```python
async with client.save_session() as session:
    # Track with recursive to get nested holders
    session.track(business, recursive=True)

    # Access offers through unit
    for unit in business.units:
        print(f"Unit: {unit.vertical}")
        
        for offer in unit.offers:
            # Check ad status
            if offer.has_active_ads:
                print(f"  Active: {offer.name}")
                print(f"    Platforms: {', '.join(offer.platforms)}")
                print(f"    Ad Spend: ${offer.weekly_ad_spend}/week")
            else:
                print(f"  Inactive: {offer.name}")

            # Navigate up
            assert offer.unit is unit
            assert offer.business is business
```

---

## Related

- [unit-model.md](unit-model.md) - Parent Unit entity with OfferHolder
- [custom-fields-glossary.md](custom-fields-glossary.md) - All 39 Offer fields
- [autom8-asana-business-relationships](../autom8-asana-business-relationships/) - Composite pattern

