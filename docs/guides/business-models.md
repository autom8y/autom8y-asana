# Business Entity Models

A guide to working with Business, Unit, Offer, Contact, and other domain entities in the autom8_asana SDK.

## Overview

The Business Model layer provides a strongly-typed interface to Asana tasks representing business domain entities. Rather than working with generic tasks, you interact with specialized classes like `Business`, `Contact`, `Unit`, and `Offer` that expose domain-specific properties and relationships.

Key features:

- **Type-safe entity classes** - Business entities inherit from `BusinessEntity` base class
- **Custom field descriptors** - Declarative property access to Asana custom fields
- **Holder pattern** - Typed collections for entity children with lazy loading
- **Navigation properties** - Traverse entity hierarchies with cached references
- **Detection system** - Automatic entity type identification from Asana tasks

The model layer sits between raw Asana API responses and your application logic, transforming Asana tasks into domain entities.

## Entity Hierarchy

Business entities form a four-level hierarchy:

```
Business (Level 0 - Root)
  |
  +-- ContactHolder (Level 1)
  |     +-- Contact (Level 2)
  |
  +-- UnitHolder (Level 1)
  |     +-- Unit (Level 2)
  |           +-- OfferHolder (Level 3)
  |           |     +-- Offer (Level 4)
  |           +-- ProcessHolder (Level 3)
  |                 +-- Process (Level 4)
  |
  +-- LocationHolder (Level 1)
  |     +-- Location (Level 2)
  |     +-- Hours (Level 2)
  |
  +-- DNAHolder (Level 1)
  +-- ReconciliationHolder (Level 1)
  +-- AssetEditHolder (Level 1)
  +-- VideographyHolder (Level 1)
```

**Holders** are organizational containers that group related children. Each holder maintains a cached list of typed children populated during hydration.

**Maximum depth**: 4 levels from Business root (Business → UnitHolder → Unit → OfferHolder → Offer).

## Entity Types

### Business

Root entity representing a customer account. Contains 7 holder subtasks for different entity types.

**Primary project GID**: `1200653012566782`

**Custom fields**: 19 fields including `company_id`, `office_phone`, `owner_name`, `facebook_page_id`, `stripe_id`, `vertical`, `rep`, `booking_type`, `mrr`, `weekly_ad_spend`

**Holders**:
- `contact_holder` - Contact entities (people)
- `unit_holder` - Unit entities (service packages)
- `location_holder` - Location and Hours entities
- `dna_holder` - DNA entities (business characteristics)
- `reconciliation_holder` - Reconciliation entities
- `asset_edit_holder` - Asset edit entities
- `videography_holder` - Videography entities

**Example**:

```python
business = await Business.from_gid_async(client, gid, hydrate=True)

# Access custom fields
print(f"Company: {business.company_id}")
print(f"Phone: {business.office_phone}")
print(f"MRR: ${business.mrr}")

# Navigate to contacts
for contact in business.contacts:
    print(f"Contact: {contact.full_name}")

# Navigate to units
for unit in business.units:
    print(f"Unit: {unit.name} - {unit.vertical}")
```

### Contact

Person entity within a ContactHolder. Represents individuals associated with a business.

**Primary project GID**: `1200775689604552`

**Custom fields**: 19 fields including `contact_email`, `contact_phone`, `position`, `nickname`, `city`, `time_zone`

**Navigation properties**:
- `business` - Parent Business entity
- `contact_holder` - Containing ContactHolder

**Owner detection**: Contacts with `position` matching "owner", "ceo", "founder", "president", or "principal" are flagged as owners via `is_owner` property.

**Name parsing**: Provides `first_name`, `last_name`, `full_name`, `display_name`, `preferred_name` properties derived from task name.

**Example**:

```python
contact_holder = business.contact_holder
owner = contact_holder.owner  # First contact with is_owner=True

if owner:
    print(f"Owner: {owner.full_name}")
    print(f"Email: {owner.contact_email}")
    print(f"Phone: {owner.contact_phone}")
    print(f"Preferred name: {owner.preferred_name}")
```

### Unit

Service package entity within a UnitHolder. Represents distinct product offerings or account segments.

**Primary project GID**: `1201081073731555`

**Custom fields**: 31 fields including `vertical`, `platforms`, `products`, `ad_account_id`, `discount`, `mrr`, `weekly_ad_spend`, `booking_type`, `currency`, `min_age`, `max_age`, `gender`

**Nested holders**:
- `offer_holder` - Offer entities (ad campaigns)
- `process_holder` - Process entities (workflows)

**Navigation properties**:
- `business` - Ancestor Business entity
- `unit_holder` - Containing UnitHolder
- `offer_holder` - Nested OfferHolder
- `process_holder` - Nested ProcessHolder

**Example**:

```python
for unit in business.units:
    print(f"Unit: {unit.name}")
    print(f"Vertical: {unit.vertical}")
    print(f"MRR: ${unit.mrr}")

    # Navigate to offers
    for offer in unit.offers:
        if offer.has_active_ads:
            print(f"  Active offer: {offer.name}")
```

### Offer

Ad campaign entity within an OfferHolder. Represents individual advertising placements and is the unit of work for ad status determination.

**Primary project GID**: `1143843662099250`

**Custom fields**: 39 fields including `ad_id`, `campaign_id`, `asset_id`, `platforms`, `vertical`, `offer_headline`, `cost`, `budget_allocation`, `landing_page_url`, `form_id`, `language`, `specialty`

**Navigation properties**:
- `business` - Ancestor Business entity
- `unit` - Parent Unit entity
- `offer_holder` - Containing OfferHolder

**Ad status**: `has_active_ads` property returns `True` if offer has `active_ads_url` or `ad_id` set.

**Example**:

```python
unit = business.units[0]
offers = unit.offers

active_offers = [o for o in offers if o.has_active_ads]
print(f"Active offers: {len(active_offers)}/{len(offers)}")

for offer in active_offers:
    print(f"Offer: {offer.name}")
    print(f"Platform: {offer.platforms}")
    print(f"Weekly spend: ${offer.weekly_ad_spend}")
```

### Process

Workflow entity within a ProcessHolder. Represents operational processes associated with a Unit.

**Primary project GID**: Not documented

**Custom fields**: 9 fields including `vertical`, `process_due_date`

**Navigation properties**:
- `business` - Ancestor Business entity
- `unit` - Parent Unit entity
- `process_holder` - Containing ProcessHolder

### Asset

Asset metadata entity. Not typically accessed directly in current SDK version.

### Other Entities

**Location**: Physical location entity with address fields.

**Hours**: Business hours entity specifying operating hours.

**DNA**: Business characteristics entity.

**Reconciliation**: Financial reconciliation entity.

**AssetEdit**: Asset editing tracking entity.

**Videography**: Videography-related entity.

These entities follow the same holder pattern but may have limited field definitions in the current SDK.

## Custom Field Descriptors

Custom field descriptors provide declarative property access to Asana custom fields with automatic type conversion.

### TextField

Returns `str | None`. Coerces non-string values to string.

```python
class Business(BusinessEntity):
    company_id = TextField()  # Derives field name "Company ID"
    office_phone = TextField()
    stripe_id = TextField()
```

**Usage**:

```python
business.company_id = "ACME-001"
print(business.company_id)  # "ACME-001"
```

### EnumField

Returns `str | None`. Extracts name from enum dict: `{"gid": "123", "name": "Value"}` → `"Value"`.

```python
class Business(BusinessEntity):
    vertical = EnumField()
    booking_type = EnumField()
```

**Usage**:

```python
print(business.vertical)  # "Home Services" or None
business.vertical = "Legal"
```

### MultiEnumField

Returns `list[str]`, never `None`. Extracts names from list of enum dicts.

```python
class Unit(BusinessEntity):
    platforms = MultiEnumField()
    products = MultiEnumField()
```

**Usage**:

```python
print(unit.platforms)  # ["Meta", "TikTok"] or []
unit.platforms = ["Meta", "Google"]
```

### NumberField

Returns `Decimal | None`. Converts to float on write for API compatibility.

```python
class Business(BusinessEntity):
    mrr = NumberField(field_name="MRR")
    weekly_ad_spend = NumberField()
```

**Usage**:

```python
from decimal import Decimal

print(business.mrr)  # Decimal("2500.00") or None
business.mrr = Decimal("3000.50")
```

### IntField

Returns `int | None`. Truncates decimal values to integer.

```python
class Unit(BusinessEntity):
    min_age = IntField()
    max_age = IntField()
    radius = IntField()
```

**Usage**:

```python
print(unit.min_age)  # 25 or None
unit.min_age = 18
unit.max_age = 65
```

### PeopleField

Returns `list[dict[str, Any]]`, never `None`. Each dict contains Asana user fields like `gid`, `name`, `email`.

```python
class Business(BusinessEntity):
    rep = PeopleField()
```

**Usage**:

```python
print(business.rep)  # [{"gid": "123", "name": "John Doe", "email": "john@example.com"}] or []
```

### DateField

Returns `Arrow | None`. Parses ISO 8601 date strings. Converts Arrow to ISO string on write.

```python
from autom8_asana.models.business.descriptors import DateField

class Process(BusinessEntity):
    process_due_date = DateField()
```

**Usage**:

```python
import arrow

due = process.process_due_date
if due:
    print(due.format('MMMM D, YYYY'))  # "December 16, 2025"
    print(due.humanize())               # "in 2 days"

process.process_due_date = arrow.now().shift(days=7)
```

### Field Name Derivation

When `field_name` is not explicitly provided, descriptors derive the Asana field name from property name:

- Convert `snake_case` to `Title Case`
- Preserve known abbreviations as uppercase: `mrr` → `"MRR"`, `ad_id` → `"Ad ID"`, `num_ai_copies` → `"Num AI Copies"`

**Explicit override**:

```python
meta_spend_sub_id = TextField(field_name="Meta Spend Sub ID")
```

### Fields Class Auto-Generation

Each entity class automatically generates a `Fields` inner class containing field name constants:

```python
class Business(BusinessEntity):
    company_id = TextField()
    mrr = NumberField(field_name="MRR")

# Auto-generated Fields class
print(Business.Fields.COMPANY_ID)  # "Company ID"
print(Business.Fields.MRR)          # "MRR"
```

Use `Fields` constants for programmatic field access:

```python
field_name = Business.Fields.COMPANY_ID
value = business.get_custom_fields().get(field_name)
```

## Holder Pattern

Holders organize related child entities under a parent. Each holder maintains a cached list of typed children populated during hydration.

### HolderMixin

Base class for all holders. Provides `_populate_children()` method for child entity construction.

**Configuration ClassVars**:

- `CHILD_TYPE` - Type of child entities (e.g., `Contact`)
- `PARENT_REF_NAME` - PrivateAttr name on child for holder ref (e.g., `"_contact_holder"`)
- `BUSINESS_REF_NAME` - PrivateAttr name on child for business ref (default `"_business"`)
- `CHILDREN_ATTR` - PrivateAttr name for children list (e.g., `"_contacts"`)
- `PRIMARY_PROJECT_GID` - Optional project GID for registry detection

**Example definition**:

```python
from autom8_asana.models.business.base import HolderMixin

class ContactHolder(Task, HolderMixin[Contact]):
    CHILD_TYPE: ClassVar[type[Contact]] = Contact
    PARENT_REF_NAME: ClassVar[str] = "_contact_holder"
    CHILDREN_ATTR: ClassVar[str] = "_contacts"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201500116978260"

    _business: Business | None = PrivateAttr(default=None)
    _contacts: list[Contact] = PrivateAttr(default_factory=list)

    @property
    def contacts(self) -> list[Contact]:
        return self._contacts
```

### Lazy Loading

Holders are populated lazily by default. Child entities are not fetched until explicitly requested.

```python
# Business loaded without hydration
business = await Business.from_gid_async(client, gid, hydrate=False)
print(business.contact_holder)  # None - not populated

# Business loaded with hydration
business = await Business.from_gid_async(client, gid, hydrate=True)
print(business.contact_holder)  # ContactHolder instance
print(len(business.contacts))   # 3 contacts
```

### Eager Loading

Use `hydrate=True` on entity factory methods to populate all holders in a single operation:

```python
business = await Business.from_gid_async(client, gid, hydrate=True)

# All holders populated
assert business.contact_holder is not None
assert business.unit_holder is not None

# Navigate entire hierarchy
for unit in business.units:
    for offer in unit.offers:
        print(f"{offer.name}: {offer.has_active_ads}")
```

### Navigation Properties

Holders provide convenience properties for accessing children:

**ContactHolder**:

```python
contact_holder = business.contact_holder

contacts: list[Contact] = contact_holder.contacts
owner: Contact | None = contact_holder.owner  # First contact with is_owner=True
```

**UnitHolder**:

```python
unit_holder = business.unit_holder

units: list[Unit] = unit_holder.units
```

**OfferHolder**:

```python
offer_holder = unit.offer_holder

offers: list[Offer] = offer_holder.offers
active_offers: list[Offer] = offer_holder.active_offers  # Offers with has_active_ads=True
```

**ProcessHolder**:

```python
process_holder = unit.process_holder

processes: list[Process] = process_holder.processes
```

### Business Shortcuts

Business entity provides direct access to common holder children without explicit holder navigation:

```python
business = await Business.from_gid_async(client, gid, hydrate=True)

# Shortcut properties (equivalent to accessing via holder)
contacts = business.contacts          # business.contact_holder.contacts
units = business.units                # business.unit_holder.units
address = business.address            # business.location_holder.primary_location
locations = business.locations        # business.location_holder.locations
hours = business.hours                # business.location_holder.hours
```

### Bidirectional References

Holders set bidirectional references during `_populate_children()`:

- Child → Holder: `child._contact_holder = self`
- Child → Business: `child._business = self._business`

This enables upward navigation from any entity:

```python
contact = business.contacts[0]

# Navigate back to business
assert contact.business is business
assert contact.contact_holder is business.contact_holder
```

## Entity Detection

The SDK automatically determines entity type from Asana tasks using a 5-tier detection system.

### Detection Tiers

**Tier 1 (Project Membership)** - O(1), zero API calls:

Check if task belongs to entity's primary project. Target: 95% of detections.

```python
if task.gid in task.memberships:
    if task.memberships[task.gid].project.gid == Business.PRIMARY_PROJECT_GID:
        return EntityType.BUSINESS
```

**Tier 2 (Name Pattern)** - <5ms, zero API calls:

Match task name against entity naming conventions.

```python
if task.name.startswith("[") and task.name.endswith("]"):
    return EntityType.OFFER
```

**Tier 3 (Parent Context)** - <10ms, may require parent fetch:

Infer type from parent task type.

```python
parent = await client.tasks.get_async(task.parent.gid)
if parent.entity_type == EntityType.CONTACT_HOLDER:
    return EntityType.CONTACT
```

**Tier 4 (Structure Inspection)** - Variable, requires async subtask fetch:

Examine subtask structure to identify entity type.

**Tier 5 (Unknown)** - Fallback:

Return `EntityType.UNKNOWN` with healing flag.

### Detection API

**Synchronous detection** (Tiers 1-3 only):

```python
from autom8_asana.models.business.detection import detect_entity_type

task = await client.tasks.get_async(gid)
result = detect_entity_type(task)

print(f"Entity type: {result.entity_type}")
print(f"Detected via tier: {result.tier_used}")
print(f"Needs healing: {result.needs_healing}")
```

**Async detection** (Tiers 1-5, includes structure inspection):

```python
from autom8_asana.models.business.detection import detect_entity_type_async

task = await client.tasks.get_async(gid)
result = await detect_entity_type_async(task, client)
```

### Primary Project GIDs

Each entity type declares its primary Asana project for Tier 1 detection:

```python
class Business(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1200653012566782"

class Contact(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1200775689604552"

class Unit(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201081073731555"

class Offer(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1143843662099250"
```

**Best practice**: Ensure all production tasks belong to their primary project for fast detection.

### Holder Detection

Holder type identification uses the same detection system with `identify_holder_type()`:

```python
from autom8_asana.models.business.detection import identify_holder_type

holder_key = identify_holder_type(task, business.HOLDER_KEY_MAP, filter_to_map=True)

if holder_key == "contact_holder":
    holder = ContactHolder.model_validate(task.model_dump())
```

## Working with Entities

### Creating Entities

Create new entities using model constructors. Entities require at minimum `gid`, `name`, and `resource_type`.

**Create with placeholder GID**:

```python
from autom8_asana.models.business import Business, Contact

business = Business(
    gid="",  # Empty GID for new entity
    name="Acme Corporation",
    resource_type="task",
)

contact = Contact(
    gid="",
    name="John Doe",
    resource_type="task",
)
```

**Set custom fields**:

```python
business.company_id = "ACME-001"
business.office_phone = "+1-555-0100"
business.vertical = "Home Services"
business.mrr = Decimal("5000.00")

contact.contact_email = "john@example.com"
contact.contact_phone = "+1-555-0101"
contact.position = "Owner"
```

**Persist via SaveSession** (see [Entity Lifecycle Reference](../reference/REF-entity-lifecycle.md)):

```python
from autom8_asana.persistence import SaveSession

async with SaveSession(client) as session:
    session.track(business)
    session.track(contact)

    result = await session.commit()

    if result.is_success:
        print(f"Business GID: {business.gid}")  # Real GID assigned
        print(f"Contact GID: {contact.gid}")    # Real GID assigned
```

### Reading Entities

**Load single entity**:

```python
# With hydration (all holders populated)
business = await Business.from_gid_async(client, gid, hydrate=True)

# Without hydration (metadata only)
business = await Business.from_gid_async(client, gid, hydrate=False)
```

**Load multiple entities** (batch operation):

```python
businesses = await client.batch_get_businesses([gid1, gid2, gid3])
```

**Navigate hierarchy**:

```python
business = await Business.from_gid_async(client, gid, hydrate=True)

# Downward navigation
for unit in business.units:
    for offer in unit.offers:
        print(f"Offer: {offer.name}")

# Upward navigation
offer = business.units[0].offers[0]
unit = offer.unit
business_ref = offer.business

assert business_ref is business
```

### Updating Entities

**Modify entity and persist**:

```python
from autom8_asana.persistence import SaveSession

business = await Business.from_gid_async(client, gid, hydrate=False)

async with SaveSession(client) as session:
    await session.track(business)

    # Modify fields
    business.office_phone = "+1-555-0200"
    business.mrr = Decimal("6000.00")

    result = await session.commit()

    if result.is_success:
        print("Business updated successfully")
```

**Bulk update with navigation**:

```python
business = await Business.from_gid_async(client, gid, hydrate=True)

async with SaveSession(client) as session:
    await session.track(business, prefetch=True)

    # Update all contacts
    for contact in business.contacts:
        contact.time_zone = "America/New_York"

    # Update all offers
    for unit in business.units:
        for offer in unit.offers:
            if offer.has_active_ads:
                offer.budget_allocation = Decimal("1000.00")

    result = await session.commit()
    print(f"Updated {len(result.successful)} entities")
```

### Upward Traversal

Entities deep in the hierarchy can navigate up to Business using `to_business_async()`:

```python
offer = await client.get_offer(offer_gid)  # Offer alone, no hierarchy

# Fetch full Business hierarchy from Offer
business = await offer.to_business_async(client)

# Offer now has references to full hierarchy
assert offer.business is business
assert offer.unit in business.units
```

**How it works**:

1. Traverse upward to find Business GID (via parent references)
2. Fetch full Business hierarchy with `hydrate=True`
3. Update entity references to point to hydrated hierarchy

**Supported entities**: `Contact`, `Unit`, `Offer`, `Process` (via `UpwardTraversalMixin`)

## Example Workflows

### Load and Inspect Business

```python
async with AsyncClient() as client:
    business = await Business.from_gid_async(client, gid, hydrate=True)

    print(f"Business: {business.name}")
    print(f"Company ID: {business.company_id}")
    print(f"MRR: ${business.mrr}")

    owner = business.contact_holder.owner
    if owner:
        print(f"Owner: {owner.full_name} ({owner.contact_email})")

    print(f"\nUnits: {len(business.units)}")
    for unit in business.units:
        print(f"  {unit.name} - {unit.vertical}")
        print(f"    Offers: {len(unit.offers)}")
        print(f"    Active: {len([o for o in unit.offers if o.has_active_ads])}")
```

### Update Contact Information

```python
async with AsyncClient() as client:
    business = await Business.from_gid_async(client, gid, hydrate=True)

    owner = business.contact_holder.owner
    if not owner:
        print("No owner contact found")
        return

    async with SaveSession(client) as session:
        await session.track(owner)

        owner.contact_email = "newemail@example.com"
        owner.contact_phone = "+1-555-0999"
        owner.time_zone = "America/Los_Angeles"

        result = await session.commit()

        if result.is_success:
            print(f"Updated owner: {owner.full_name}")
```

### Find Active Offers Across Units

```python
async with AsyncClient() as client:
    business = await Business.from_gid_async(client, gid, hydrate=True)

    active_offers = []
    for unit in business.units:
        for offer in unit.offers:
            if offer.has_active_ads:
                active_offers.append((unit, offer))

    print(f"Active offers: {len(active_offers)}")
    for unit, offer in active_offers:
        print(f"  {unit.name} / {offer.name}")
        print(f"    Platform: {offer.platforms}")
        print(f"    Weekly spend: ${offer.weekly_ad_spend}")
```

### Create Business with Contacts

```python
from decimal import Decimal
from autom8_asana.persistence import SaveSession

async with AsyncClient() as client:
    # Create business
    business = Business(
        gid="",
        name="New Business LLC",
        resource_type="task",
    )
    business.company_id = "NEW-001"
    business.office_phone = "+1-555-1000"
    business.vertical = "Legal"
    business.mrr = Decimal("3000.00")

    # Create owner contact
    owner = Contact(
        gid="",
        name="Jane Smith",
        resource_type="task",
        parent=business,
    )
    owner.contact_email = "jane@newbusiness.com"
    owner.position = "Owner"

    async with SaveSession(client) as session:
        session.track(business)
        session.track(owner)

        result = await session.commit()

        if result.is_success:
            print(f"Created business: {business.gid}")
            print(f"Created owner: {owner.gid}")
```

## See Also

- [Entity Lifecycle Pattern](../reference/REF-entity-lifecycle.md) - Full lifecycle: Define → Detect → Populate → Navigate → Persist
- [Entity Type Table](../reference/REF-entity-type-table.md) - Complete entity hierarchy reference
- [SaveSession Lifecycle](../reference/REF-savesession-lifecycle.md) - Change tracking and persistence
- [TDD-0027: Business Model Architecture](../design/TDD-0027-business-model-architecture.md) - Design decisions and rationale
