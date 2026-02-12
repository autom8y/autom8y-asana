# Business Entity Models Reference

> Domain-specific models for business hierarchy and custom field management

## Overview

Business entity models extend `Task` with custom field descriptors and holder patterns for managing complex hierarchical data structures. The business hierarchy represents real-world business entities like businesses, units, offers, and processes.

All business entities:
- Inherit from `BusinessEntity` (which extends `Task`)
- Use descriptor-based custom field access
- Support holder pattern for child collections
- Include bidirectional navigation references
- Support hydration for loading complete hierarchies

## Hierarchy Structure

```
Business (root entity)
├── UnitHolder
│   └── Unit (1..n)
│       ├── OfferHolder
│       │   └── Offer (1..n)
│       └── ProcessHolder
│           └── Process (1..n)
├── LocationHolder
│   └── Location (1..n)
├── ContactHolder
│   └── Contact (1..n)
├── DNAHolder
│   └── DNA (1..n)
├── ReconciliationHolder
│   └── Reconciliation (1..n)
├── AssetEditHolder
│   └── AssetEdit (1..n)
└── VideographyHolder
    └── Videography (1..n)
```

## BusinessEntity

Base class for all business entities.

```python
class BusinessEntity(Task):
    NAME_CONVENTION: ClassVar[str]
    PRIMARY_PROJECT_GID: ClassVar[str | None]

    def _invalidate_refs(self) -> None
    @classmethod
    async def from_gid_async(cls, client: AsanaClient, gid: str) -> Self
```

Provides:
- Custom field descriptor support
- Primary project GID for entity type detection
- Reference invalidation for cached navigation
- Factory method for loading from GID

## Custom Field Descriptors

Business entities use descriptor classes for type-safe custom field access:

### TextField

```python
class TextField:
    field_name = TextField("Field Name")
```

Access text custom fields with string values.

### IntField

```python
class IntField:
    count = IntField("Count")
```

Access integer custom fields with int values.

### NumberField

```python
class NumberField:
    amount = NumberField("Amount")
```

Access numeric custom fields with float values.

### EnumField

```python
class EnumField:
    status = EnumField("Status")
```

Access single-select enum custom fields. Returns/accepts enum option names as strings.

### MultiEnumField

```python
class MultiEnumField:
    platforms = MultiEnumField("Platforms")
```

Access multi-select enum custom fields. Returns/accepts lists of enum option names.

## Business

Root entity of the business hierarchy.

```python
class Business(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    NAME_CONVENTION: ClassVar[str] = "[Business Name]"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1199848310257131"

    # Custom fields (descriptors)
    vertical = EnumField("Vertical")
    rep = TextField("Rep")
    booking_type = EnumField("Booking Type")
    mrr = NumberField("MRR")
    weekly_ad_spend = NumberField("Weekly Ad Spend")
    phone = TextField("Office Phone")
    # ... 14 additional custom fields

    # Holder properties (lazy-loaded)
    @property
    def unit_holder(self) -> UnitHolder | None
    @property
    def location_holder(self) -> LocationHolder | None
    @property
    def contact_holder(self) -> ContactHolder | None
    @property
    def dna_holder(self) -> DNAHolder | None
    @property
    def reconciliation_holder(self) -> ReconciliationHolder | None
    @property
    def asset_edit_holder(self) -> AssetEditHolder | None
    @property
    def videography_holder(self) -> VideographyHolder | None

    # Convenience shortcuts
    @property
    def units(self) -> list[Unit]
    @property
    def locations(self) -> list[Location]
    @property
    def contacts(self) -> list[Contact]
```

### Holder Key Map

```python
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "unit_holder": ("Units", "package"),
    "location_holder": ("Locations", "round_pushpin"),
    "contact_holder": ("Contacts", "telephone_receiver"),
    "dna_holder": ("DNA", "dna"),
    "reconciliation_holder": ("Reconciliations", "balance_scale"),
    "asset_edit_holder": ("Asset Edits", "framed_picture"),
    "videography_holder": ("Videography", "video_camera"),
}
```

Maps property names to task names and emoji indicators for holder detection.

## Unit

Service package or product offering entity.

```python
class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin, UpwardTraversalMixin):
    NAME_CONVENTION: ClassVar[str] = "[Unit Name]"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201081073731555"

    # Custom fields (descriptors)
    vertical = EnumField("Vertical")
    platforms = MultiEnumField("Platforms")
    booking_type = EnumField("Booking Type")
    rep = TextField("Rep")
    mrr = NumberField("MRR")
    weekly_ad_spend = NumberField("Weekly Ad Spend")
    # ... 25 additional custom fields

    # Nested holder properties
    @property
    def offer_holder(self) -> OfferHolder | None
    @property
    def process_holder(self) -> ProcessHolder | None

    # Navigation properties (descriptors)
    unit_holder = HolderRef["UnitHolder"]()
    business = ParentRef["Business"]()

    # Convenience shortcuts
    @property
    def offers(self) -> list[Offer]
    @property
    def processes(self) -> list[Process]

    # Upward traversal
    async def to_business_async(self) -> Business
```

### Holder Key Map

```python
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "offer_holder": ("Offers", "gift"),
    "process_holder": ("Processes", "gear"),
}
```

## Offer

Individual ad campaign or placement entity.

```python
class Offer(
    BusinessEntity,
    UnitNavigableEntityMixin,
    SharedCascadingFieldsMixin,
    FinancialFieldsMixin,
    UpwardTraversalMixin,
):
    NAME_CONVENTION: ClassVar[str] = "[Offer Name]"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1143843662099250"

    # Custom fields (descriptors)
    vertical = EnumField("Vertical")  # Inherited from Unit
    platforms = MultiEnumField("Platforms")  # Inherited from Unit
    booking_type = EnumField("Booking Type")
    rep = TextField("Rep")
    mrr = NumberField("MRR")
    weekly_ad_spend = NumberField("Weekly Ad Spend")
    # ... 33 additional custom fields

    # Navigation properties (descriptors)
    offer_holder = HolderRef["OfferHolder"]()

    # Complex navigation (properties)
    @property
    def unit(self) -> Unit | None
    @property
    def business(self) -> Business | None

    # Business logic
    @property
    def has_active_ads(self) -> bool

    # Upward traversal
    async def to_business_async(self) -> Business
```

### has_active_ads Property

Determines if offer has active advertising based on custom fields. Returns True if ads are running, False otherwise.

## Contact

Contact information entity.

```python
class Contact(BusinessEntity):
    NAME_CONVENTION: ClassVar[str] = "[Contact Name]"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1208031451697127"

    # Custom fields (descriptors)
    email = TextField("Email")
    phone = TextField("Phone")
    role = EnumField("Role")
    # ... additional custom fields

    # Navigation properties
    contact_holder = HolderRef["ContactHolder"]()
    business = ParentRef["Business"]()
```

## Process

Business process or workflow entity.

```python
class Process(BusinessEntity, UnitNavigableEntityMixin, SharedCascadingFieldsMixin):
    NAME_CONVENTION: ClassVar[str] = "[Process Name]"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1208031451697128"

    # Custom fields (descriptors)
    vertical = EnumField("Vertical")  # Inherited from Unit
    status = EnumField("Status")
    # ... additional custom fields

    # Navigation properties
    process_holder = HolderRef["ProcessHolder"]()
    unit = ParentRef["Unit"]()
```

## Holder Classes

Holder tasks contain child entities and provide collection access.

### HolderFactory

Base class for all holder types using factory pattern.

```python
class HolderFactory(Task):
    PRIMARY_PROJECT_GID: ClassVar[str | None]
    CHILD_TYPE: ClassVar[type[BusinessEntity]]

    def _populate_children(self, children: list[Task]) -> None
    @property
    def children(self) -> list[BusinessEntity]
```

All holder classes inherit from `HolderFactory`:
- `UnitHolder`
- `LocationHolder`
- `ContactHolder`
- `DNAHolder`
- `ReconciliationHolder`
- `AssetEditHolder`
- `VideographyHolder`
- `OfferHolder`
- `ProcessHolder`

## Mixins

Business entities compose behavior through mixins:

### SharedCascadingFieldsMixin

Provides cascading fields that propagate from parent to children:
- `vertical` (EnumField)
- `rep` (TextField)

### FinancialFieldsMixin

Provides financial tracking fields:
- `booking_type` (EnumField)
- `mrr` (NumberField)
- `weekly_ad_spend` (NumberField)

### UpwardTraversalMixin

Provides upward navigation to root business:
- `async def to_business_async(self) -> Business`

### UnitNavigableEntityMixin

Provides `business` property for entities nested under Unit:
- `@property def business(self) -> Business | None`

### UnitNestedHolderMixin

Provides holder-level `business` property access:
- `@property def business(self) -> Business | None`

## Field Inheritance and Cascading

### Inherited Fields

Fields that inherit values from parent entities when not explicitly set:

```python
class InheritedFieldDef:
    Offer.vertical  # Inherits from Unit.vertical
    Offer.platforms  # Inherits from Unit.platforms
```

### Cascading Fields

Fields that propagate updates to child entities:

```python
class CascadingFieldDef:
    Unit.platforms  # Cascades to Offer.platforms
    Unit.vertical  # Cascades to Offer.vertical
    Unit.booking_type  # Cascades to Offer.booking_type
```

## Examples

### Loading Business Hierarchy

```python
# Load fully hydrated business
business = await Business.from_gid_async(client, "business_gid")

# Navigate hierarchy
for unit in business.units:
    print(f"Unit: {unit.name}, Vertical: {unit.vertical}")
    for offer in unit.offers:
        if offer.has_active_ads:
            print(f"  Active offer: {offer.name}")
```

### Custom Field Access

```python
# Read custom fields via descriptors
vertical = unit.vertical  # Returns enum option name as string
mrr = unit.mrr  # Returns float
platforms = unit.platforms  # Returns list of enum option names

# Write custom fields via descriptors
unit.vertical = "Medical"
unit.mrr = 5000.00
unit.platforms = ["Google Ads", "Facebook"]
```

### Navigation

```python
# Upward navigation via descriptors
business = unit.business  # Returns Business or None
unit_holder = unit.unit_holder  # Returns UnitHolder or None

# Async upward traversal
business = await offer.to_business_async()

# Downward navigation via convenience properties
units = business.units  # Returns list[Unit]
offers = unit.offers  # Returns list[Offer]
```

### Holder Detection

```python
# Check if unit has offers
if unit.offer_holder:
    for offer in unit.offers:
        print(offer.name)
else:
    print("No offers holder found")
```

### Custom Field Validation

```python
# Check if field has value
if offer.weekly_ad_spend is not None:
    print(f"Weekly spend: ${offer.weekly_ad_spend}")
else:
    print("No spend data")
```

### Reference Invalidation

```python
# After parent reference changes, cached refs are auto-invalidated
unit.parent = NameGid(gid="new_unit_holder_gid")
# unit._business is now None and will be recomputed on next access
```

## Custom Field Descriptor Implementation

Descriptors provide:
- Type-safe access to custom field values
- Automatic serialization/deserialization
- Lazy loading from custom_fields list
- Write-back support via CustomFieldAccessor

```python
# Internal implementation example
class EnumField:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = obj.cf.get(self.field_name)
        return value  # Returns enum option name string

    def __set__(self, obj, value):
        obj.cf[self.field_name] = value  # Sets enum option by name
```
