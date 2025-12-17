# Prompt 0: Business Model Hierarchy Migration

> **Purpose**: Migrate the Business model hierarchy from legacy `autom8/apis/asana_api/objects/task/models` to `autom8_asana` SDK
>
> **Complexity**: High - 7 holder subtasks, nested holders, 18+ custom fields, SQL integration
>
> **Target Agent Workflow**: @orchestrator → @requirements-analyst → @architect → @principal-engineer → @qa-adversary

---

## Executive Summary

The autom8_asana SDK needs to support the Business model hierarchy—a sophisticated data structure that models chiropractic businesses in Asana. This is the **core domain model** for the autom8 platform, where Asana tasks represent real-world business entities with complex relationships.

**Key Architecture**: Business tasks have 7 "holder" subtasks, each containing specific child models:

```
Business (root task)
├─ ContactHolder (subtask)
│  └─ Contact[] (children)
├─ UnitHolder (subtask)
│  └─ Unit[] (children)
│     ├─ OfferHolder (nested subtask)
│     │  └─ Offer[] (nested children)
│     └─ ProcessHolder (nested subtask)
│        └─ Process[] (nested children)
├─ LocationHolder (subtask)
│  ├─ Location (child)
│  └─ Hours (child)
├─ DnaHolder (subtask)
├─ ReconciliationsHolder (subtask)
├─ AssetEditHolder (subtask)
└─ VideographyHolder (subtask)
```

This is **NOT** a simple CRUD task model. This is a rich domain model with:
- **Bidirectional navigation**: `business.contact_holder.contact`, `contact.business`
- **SQL integration**: Custom fields fall back to legacy database values
- **Custom field typed accessors**: 18 custom fields on Business alone
- **Thread-safe lazy loading**: Holders loaded on-demand with locking
- **Emoji-based naming conventions**: Each holder has an emoji indicator

---

## 1. Legacy Schema Analysis

### 1.1 File Structure (Legacy)

**Location**: `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/task/models`

```
models/
├── __init__.py                    # 57 model imports
├── business/main.py               # Business (root)
├── contact_holder/main.py         # Holder #1
├── contact/main.py                # Child model
├── unit_holder/main.py            # Holder #2
├── unit/main.py                   # Child model (has nested holders!)
├── location_holder/main.py        # Holder #3
├── location/main.py               # Child model
├── hours/main.py                  # Child model (under LocationHolder)
├── dna_holder/                    # Holder #4
├── reconciliations_holder/        # Holder #5
├── asset_edit_holder/             # Holder #6
├── videography_holder/            # Holder #7
├── offer_holder/                  # Nested holder (under Unit)
├── offer/main.py                  # Nested child
├── process_holder/                # Nested holder (under Unit)
└── process/                       # Nested child (24+ subclasses!)
```

### 1.2 Business Model Schema

**File**: `business/main.py` (~850 lines)

**Key Attributes**:
```python
@dataclass
class Business(Task):
    PRIMARY_PROJECT_GID = Businesses.PROJECT_GID

    # 7 holders with emoji indicators
    HOLDER_KEY_MAP = OrderedDict([
        ("contact_holder", ("Contacts", "🧑")),
        ("unit_holder", ("Units", "🔎")),
        ("location_holder", ("Location", "🏠")),
        ("dna_holder", ("PLAYS/REQUESTS", "✅")),
        ("reconciliations_holder", ("Reconciliations", "🧾")),
        ("asset_edit_holder", ("Asset Edits", "🎥")),
        ("videography_holder", ("Videography", "🎬")),
    ])

    # 18 custom fields with typed accessors
    ASANA_FIELDS = {
        "aggression_level": AggressionLevel,
        "booking_type": BookingType,
        "company_id": CompanyId,
        "facebook_page_id": FacebookPageId,
        "fallback_page_id": FallbackPageId,
        "google_cal_id": GoogleCalId,
        "num_reviews": NumReviews,
        "office_phone": OfficePhone,
        "owner_name": OwnerName,
        "owner_nickname": OwnerNickname,
        "rep": Rep,
        "review_1": Review1,
        "review_2": Review2,
        "reviews_link": ReviewsLink,
        "stripe_id": StripeId,
        "stripe_link": StripeLink,
        "twilio_phone_num": TwilioPhoneNum,
        "vca_status": VcaStatus,
        "vertical": Vertical,
    }
```

**SQL Integration Pattern**:
```python
@property
def sql_record(self) -> Optional[SqlChiropractors]:
    """Thread-safe lazy-loaded SQL record lookup by office_phone."""
    if not hasattr(self, "_sql_record"):
        with self._sql_lock:
            if not hasattr(self, "_sql_record"):
                self._sql_record = self._get_record_from_db(
                    self.data.custom_fields.get("office_phone", {}).get("display_value")
                )
    return self._sql_record
```

**Holder Access Pattern** (Thread-safe):
```python
@thread_safe_property
def ts_contact_holder(self) -> "ContactHolder":
    return self._get_contact_holder()

@property
def contact_holder(self) -> "ContactHolder":
    return self.ts_contact_holder

def _get_contact_holder(self) -> "ContactHolder":
    attr = "contact_holder"
    return self.get_holder(f"_{attr}", self.HOLDER_KEY_MAP[attr])
```

**Relationship Navigation** (Convenience properties):
```python
@property
def contact(self) -> "Contact":
    """Navigate: Business → ContactHolder → Contact (first/owner)."""
    contact_holder = self.contact_holder
    if not contact_holder:
        LOG.warning(f"{self.name} has no contact_holder yet")
        return None
    return contact_holder.contact

@property
def unit(self) -> "Unit":
    """Navigate: Business → UnitHolder → Unit (first)."""
    unit_holder = self.unit_holder
    if not unit_holder:
        LOG.warning(f"{self.name} has no unit_holder yet")
        return None
    return unit_holder.unit

@property
def location(self) -> "Location":
    """Navigate: Business → LocationHolder → Location."""
    return self.location_holder.location

@property
def hours(self) -> "Hours":
    """Navigate: Business → LocationHolder → Hours."""
    return self.location_holder.hours
```

**Custom Field Accessor Pattern** (with SQL fallback):
```python
@thread_safe_property
def office_phone_field(self) -> OfficePhone:
    if not hasattr(self, "_office_phone_field"):
        self._office_phone_field = OfficePhone(task=self)
    return self._office_phone_field

@property
def office_phone(self) -> str:
    return self.office_phone_field.get()

@office_phone.setter
def office_phone(self, value):
    self.office_phone_field.set(value)
```

**Custom Field with Default/Fallback**:
```python
@classmethod
def default_company_id(cls) -> str:
    return "sql_record.guid"

@thread_safe_property
def company_id_field(self) -> CompanyId:
    if not hasattr(self, "_company_id_field"):
        self._company_id_field = CompanyId(
            task=self,
            default=self.default_company_id(),
            override=True
        )
    return self._company_id_field

@property
def company_id(self) -> str:
    return self.company_id_field.get()

@company_id.setter
def company_id(self, value):
    self.company_id_field.set(value)
```

---

### 1.3 Holder Models

#### ContactHolder Schema

**File**: `contact_holder/main.py` (~699 lines)

```python
@dataclass
class ContactHolder(Task):
    PRIMARY_PROJECT_GID = ContactHolderProject.PROJECT_GID
    NAME_CONVENTION = "[self.parent.name] Contacts 🧑"

    # 23 custom fields
    ASANA_FIELDS = {
        "ad_id": AdId,
        "before_appt": BeforeAppt,
        "booking_calls": BookingCalls,
        "booking_texts": BookingTexts,
        # ... 19 more
    }

    # Supports multiple contacts as subtasks
    HAS_SUB_MODELS = True
    SUB_MODEL_CLASS = Contact
    SUB_MODEL_PROJECT = ContactsProject
```

**Child Access**:
```python
@property
def contact(self) -> "Contact":
    """Returns the 'owner' contact or first contact."""
    from apis.asana_api.objects.task.models import Contact

    if not hasattr(self, "_contact") or self._contact is None:
        self._contact = None
        try:
            for t in self.subtasks:
                if isinstance(t.task, Contact):
                    if FMTS.snake_lower(t.task.position) == "owner":
                        self._contact = t.task
                        break
            if self._contact is None:
                _contact = next(iter(self.subtasks), None)
                self._contact = _contact.task if _contact else None
        except Exception:
            raise Exception(f"ContactHolder {self} has no contacts")

    return self._contact

@property
def contacts(self) -> list["Contact"]:
    """Returns all contacts (excludes videographer position)."""
    from apis.asana_api.objects.task.models import Contact

    if not hasattr(self, "_contacts") or not self._contacts:
        self._contacts = [
            t.task
            for t in self.subtasks
            if isinstance(t.task, Contact)
            and FMTS.snake_lower(t.task.position_field._display_value) != "videographer"
        ]
    return self._contacts
```

**Upward Navigation**:
```python
@property
def business(self) -> "Business":
    if not hasattr(self, "_business"):
        self._business = self.parent_task
    return self._business
```

#### UnitHolder Schema

**File**: `unit_holder/main.py` (~878 lines)

```python
@dataclass
class UnitHolder(Task):
    PRIMARY_PROJECT_GID = PrimaryProject.PROJECT_GID
    NAME_CONVENTION = "[self.parent.name] Business Units 🔎"

    # 39 custom fields (GHL calendars, ad accounts, insurance)
    ASANA_FIELDS = {
        "medicare": Medicare,
        "medicaid": Medicaid,
        "tricare": Tricare,
        "ad_account_id_list": AdAccountIdList,
        "meta_ad_account_id": MetaAdAccountId,
        "tiktok_ad_account_id": TikTokAdAccountId,
        # ... 33 more (mostly GHL calendar IDs)
    }

    SUB_MODEL_CLASS = Unit
    HAS_SUB_MODELS = True
    SUB_MODEL_PROJECT = BusinessUnitsProject
```

**Multiple Units**:
```python
@property
def units(self) -> list["Unit"]:
    return self.ts_units

@thread_safe_property
def ts_units(self) -> list["Unit"]:
    return self._get_units()

def _get_units(self) -> list["Unit"]:
    if not hasattr(self, "_units"):
        self._units = [getattr(o, "task") for o in self.subtasks]
    return self._units

@property
def unit(self) -> "Unit":
    """Returns first unit (convenience property)."""
    units = self.units
    if not units:
        LOG.warning(f"{self.name} has no units yet")
        return None
    return next(iter(units))
```

#### LocationHolder Schema

**File**: `location_holder/main.py` (~90 lines)

**CRITICAL**: LocationHolder has 2 children (Location + Hours), not a list!

```python
@dataclass
class LocationHolder(Task):
    NAME_CONVENTION = "[self.parent.name] Location 🏠"

    HOLDER_KEY_MAP = OrderedDict([
        ("location", ("📍",)),
        ("hours", ("Hours", "⏰")),
    ])

    HOLDER_PROJECT_MAP = {
        "location": LocationsProject,
        "hours": HoursProject,
    }

@property
def location(self) -> "Location":
    return self.ts_location

@property
def hours(self) -> "Hours":
    return self.ts_hours
```

---

### 1.4 Child Models

#### Contact Schema

**File**: `contact/main.py` (~785 lines)

```python
@dataclass
class Contact(Task):
    PRIMARY_PROJECT_GID = Contacts.PROJECT_GID
    NAME_CONVENTION = "[self.parent.parent.name] Team"

    # 21 custom fields (name components, contact info, UTM tracking)
    ASANA_FIELDS = {
        "build_call_link": BuildCallLink,
        "campaign": Campaign,
        "city": City,
        "contact_email": ContactEmail,
        "contact_phone": ContactPhone,
        "contact_url": ContactUrl,
        # ... 15 more
    }
```

**Upward Navigation** (3 levels):
```python
@property
def contact_holder(self) -> "ContactHolder":
    if not hasattr(self, "_contact_holder"):
        try:
            self._contact_holder = self.holder
        except Exception as e:
            LOG.error(f"Error getting contact holder for {self}: {e}", exc_info=True)
            self._contact_holder = None
    return self._contact_holder

@property
def business(self) -> "Business":
    if not hasattr(self, "_business"):
        try:
            self._business = self.contact_holder.business
        except Exception as e:
            LOG.error(f"Error getting business for {self}: {e}")
            self._business = None
    return self._business

@property
def unit(self):
    """Navigate all the way: Contact → Business → Unit."""
    if not hasattr(self, "_unit"):
        try:
            self._unit = self.business.unit
        except Exception:
            self._unit = None
    return self._unit
```

**HumanName Parsing** (complex name handling):
```python
@thread_safe_property
def human_name(self) -> HumanName:
    """Returns the parsed HumanName object."""
    if not hasattr(self, "_human_name") or not self._human_name:
        self._human_name = HumanName(self.full_name)
    return self._human_name

@property
def nickname(self) -> Optional[str]:
    return self.nickname_field.get()

@thread_safe_property
def nickname_field(self) -> Nickname:
    if not hasattr(self, "_nickname_field"):
        has_prefix = bool(self.human_name.title)
        is_office = False
        if self.position:
            is_office = FMTS.snake_upper(self.position) in ["OFFICE"]

        nickname = self.data.custom_fields["nickname"]["display_value"]
        default = None
        if not is_office:
            if nickname and has_prefix and self.human_name.title in nickname:
                pass
            else:
                if nickname and nickname in self.full_name:
                    default = nickname if not has_prefix else f"{self.prefix} {nickname}"
                else:
                    default = (
                        self.human_name.first
                        if not has_prefix
                        else f"{self.prefix} {self.human_name.last}"
                    )
        else:
            default = self.full_name

        self._nickname_field = Nickname(
            task=self, default=default, override=default is not None
        )
    return self._nickname_field
```

#### Unit Schema (NESTED HOLDERS!)

**File**: `unit/main.py` (~1505 lines - massive!)

**Critical**: Unit has its own nested holders!

```python
@dataclass
class Unit(Task):
    PRIMARY_PROJECT_GID = BusinessUnits.PROJECT_GID
    NAME_CONVENTION = "[self.parent.parent.name] — [self.vertical.vertical_name]"

    # Unit has 2 nested holders!
    HOLDER_KEY_MAP = OrderedDict([
        ("offer_holder", ("Offers", "🎟️")),
        ("process_holder", ("Processes", "🚧")),
    ])

    # 44 custom fields (targeting, demographics, pricing, products)
    ASANA_FIELDS = {
        "mrr": MRR,
        "ad_account_id": AdAccountId,
        "currency": Currency,
        "custom_disclaimer": CustomDisclaimer,
        "disabled_questions": DisabledQuestions,
        "disclaimers": Disclaimers,
        "discount": Discount,
        # ... 37 more
    }
```

**Nested Holder Access**:
```python
@property
def offer_holder(self) -> "OfferHolder":
    attr = "offer_holder"
    return self.get_holder(f"_{attr}", self.HOLDER_KEY_MAP[attr])

@property
def process_holder(self) -> "ProcessHolder":
    attr = "process_holder"
    return self.get_holder(f"_{attr}", self.HOLDER_KEY_MAP[attr])

@property
def offer(self) -> "Offer":
    """Convenience: Unit → OfferHolder → Offer (first)."""
    try:
        return self.offer_holder.offer
    except IndexError as e:
        LOG.error(f"Error retrieving offer from unit: {e}", exc_info=True)
        return None
```

**Demographics Model** (composed object):
```python
@property
def demographics(self) -> DemographicsModel:
    if not hasattr(self, "_demographics") or not isinstance(
        self._demographics, DemographicsModel
    ):
        attr_map = {
            "_max_age": self.max_age,
            "_min_age": self.min_age,
            "_gender": self.gender,
            "_radius": self.radius,
            "_filter_out_x": self.filter_out_x,
            "_zip_code": self.business.location.zip_code,
            "_state": self.business.location.state,
            "_country": self.business.location.country,
            "_zip_code_list": self.zip_code_list,
            "_excluded_zips": self.excluded_zips,
        }
        self._demographics = DemographicsModel(**attr_map)

    return self._demographics
```

#### Location Schema

**File**: `location/main.py` (~387 lines)

```python
@dataclass
class Location(Task):
    PRIMARY_PROJECT_GID = Locations.PROJECT_GID
    NAME_CONVENTION = "[self.parent.parent.name] — [city], [state] 📍"

    # 11 custom fields (address components)
    ASANA_FIELDS = {
        "city": City,
        "country": Country,
        "max_radius": MaxRadius,
        "min_radius": MinRadius,
        "neighborhood": Neighborhood,
        "office_location": OfficeLocation,
        "state": State,
        "street_name": StreetName,
        "street_num": StreetNum,
        "suite": Suite,
        "time_zone": TimeZone,
        "zip_code": ZipCode,
    }
```

**Computed Properties**:
```python
@property
def address(self) -> str:
    if not self.line_1 and not self.line_2:
        return ""
    return f"{self.line_1},\n{self.line_2}"

@property
def line_1(self) -> str:
    if not self.street_name:
        return ""
    line_1 = (
        f"{self.street_num} {self.street_name}"
        if self.street_num
        else self.street_name
    )
    if self.suite:
        line_1 += f" {self.suite}"
    return line_1

@property
def line_2(self) -> str:
    line = ""
    if not self.city and not self.state and not self.zip_code:
        return line
    if self.city:
        line += self.city
    if self.state:
        line += f", {self.state}" if line else self.state
    if self.zip_code:
        line += f" {self.zip_code}" if line else self.zip_code
    return line

@property
def stripe_address(self) -> dict:
    return {
        "line1": self.line_1,
        "line2": self.line_2,
        "city": self.city,
        "state": self.state,
        "postal_code": self.zip_code,
        "country": self.country,
    }
```

**Geocoding Integration**:
```python
@thread_safe_property
def lat_lng(self) -> tuple[float, float]:
    if not hasattr(self, "_lat_lng"):
        if not self.address:
            return None, None
        results = FUNCS.GEOCODER.geocode_address(self.address)
        if not results:
            LOG.info(
                f"No geocoding results found for: {self.address}. Falling back to ZIP centroid."
            )
            # ZIP centroid fallback
            if self.zip_code:
                lat, lng = FUNCS.GEOCODER.get_lat_lng_from_zip(
                    self.zip_code, country_code=self.country
                )
                self._lat_lng = lat, lng
            else:
                return None, None
        else:
            location = results[0]["geometry"]["location"]
            self._lat_lng = location["lat"], location["lng"]
    return self._lat_lng
```

#### Hours Schema

**File**: `hours/main.py` (~235 lines)

```python
@dataclass
class Hours(Task):
    PRIMARY_PROJECT_GID = PrimaryProject.PROJECT_GID
    NAME_CONVENTION = "[self.parent.parent.name] Hours ⏰"

    # 6 custom fields (days of the week)
    ASANA_FIELDS = {
        "monday": Monday,
        "tuesday": Tuesday,
        "wednesday": Wednesday,
        "thursday": Thursday,
        "friday": Friday,
        "saturday": Saturday,
    }

@property
def monday(self) -> list[str]:
    return self.monday_field.get()

@property
def hours_array(self) -> dict[str, list[str]]:
    """Convert to standardized format: {day: [open, hours...]}"""
    if not hasattr(self, "_hours_array") or not self._hours_array:
        self._hours_array = self.convert_hours_dict_to_array(
            {
                field: getattr(self, field)
                for field in self.ASANA_FIELDS
                if str(field).endswith("day")
            }
        )
    return self._hours_array

@staticmethod
def convert_hours_dict_to_array(hours: dict) -> dict[str, list[str]]:
    hours_array = {}
    for day, hours in hours.items():
        hours_array[day] = ["0", "00:00:00", "00:00:00", "00:00:00", "00:00:00"]
        if hours:
            hours_array[day] = ["1"] + hours + ["00:00:00"] * (4 - len(hours))
    return FMTS.format_keys(hours_array, FMTS.to_title)
```

#### Offer Schema (partial - complex)

**File**: `offer/main.py` (300+ lines shown, ~1500+ total)

```python
@dataclass
class Offer(Task):
    NAME_CONVENTION = "[Offer Name]"
    PRIMARY_PROJECT_GID = BusinessOffers.PROJECT_GID

    # 38 custom fields (campaign config, targeting, budget)
    ASANA_FIELDS = {
        "mrr": MRR,
        "active_ads_url": ActiveAdsURL,
        "ad_account_url": AdAccountUrl,
        "ad_id": AdId,
        "ad_set_id": AdSetId,
        "algo_version": AlgoVersion,
        # ... 32 more
    }
```

**Managers** (complex business logic):
```python
_ad_manager: Optional["AdManager"] = field(init=False)
_offer_holder: Optional["OfferHolder"] = field(init=False)
_unit: Optional["Unit"] = field(init=False)
_business: Optional["Business"] = field(init=False)

def _optimize(
    self,
    disable_update: bool = False,
    disable_approval: bool = False,
    action: str = None,
    debug: bool = False,
):
    """Complex optimization workflow with ad factory, approvals, etc."""
    # ... sophisticated logic
```

---

## 2. Migration Requirements

### 2.1 Must-Have Features (P0)

**Critical Path** (blocking GA readiness):

1. **Business Model with 7 Holders**
   - Business as root Task subclass
   - 7 holder access properties (thread-safe)
   - HOLDER_KEY_MAP with emoji naming
   - Upward/downward navigation (bidirectional)

2. **Contact Workflow**
   - ContactHolder with multiple Contact children
   - Owner contact detection (position field)
   - Contact → Business navigation
   - 21 custom fields with UTM tracking

3. **Unit Workflow with Nested Holders**
   - UnitHolder with multiple Unit children
   - Unit → OfferHolder → Offer (nested)
   - Unit → ProcessHolder → Process (nested)
   - 44 custom fields (targeting, demographics)

4. **Location + Hours**
   - LocationHolder with Location + Hours children
   - Address line composition
   - Geocoding integration
   - Business hours array format

5. **Custom Field Infrastructure**
   - Typed accessor pattern (field + property + setter)
   - SQL fallback support
   - Default/override system
   - Thread-safe lazy loading

6. **SQL Integration**
   - `sql_record` property pattern
   - Custom field fallback to SQL columns
   - Thread-safe DB queries with locking

### 2.2 Should-Have Features (P1)

**Important but can be iterated**:

1. **Offer Management**
   - OfferHolder with Offer children
   - Campaign configuration fields
   - Ad manager integration hooks
   - Optimization workflows (stub methods)

2. **Process Management**
   - ProcessHolder with Process children
   - Pipeline stage tracking
   - Process subclass extensibility

3. **Remaining Holders**
   - DnaHolder (PLAYS/REQUESTS)
   - ReconciliationsHolder
   - AssetEditHolder
   - VideographyHolder

4. **Computed Properties**
   - Demographics composition
   - Stripe address formatting
   - Hours array conversion
   - Phone/vertical pairs

### 2.3 Nice-to-Have Features (P2)

**Future iterations**:

1. **Manager Classes**
   - AdManager, AdFactory
   - ReconcileBudget
   - AlgoOptimization
   - InsightsExport

2. **Advanced SQL Queries**
   - Complex joins
   - Aggregations
   - Pandas DataFrame integration

3. **Caching Strategies**
   - TTL customization by section
   - Cache invalidation hooks

---

## 3. Implementation Strategy

### 3.1 Phased Approach

**Phase 1: Foundation** (Week 1)
- Business model with HOLDER_KEY_MAP
- Thread-safe holder properties
- Custom field accessor infrastructure
- SQL integration pattern

**Phase 2: Contact Workflow** (Week 2)
- ContactHolder + Contact models
- 21 custom fields
- Upward navigation
- Position-based owner detection

**Phase 3: Unit Workflow** (Week 2-3)
- UnitHolder + Unit models
- Nested OfferHolder + ProcessHolder
- 44 custom fields
- Demographics composition

**Phase 4: Location** (Week 3)
- LocationHolder model
- Location + Hours children
- Address composition
- Geocoding integration

**Phase 5: Remaining Holders** (Week 4)
- DnaHolder
- ReconciliationsHolder
- AssetEditHolder
- VideographyHolder

### 3.2 Design Decisions Needed

**ADR Topics** (for @architect):

1. **Holder Pattern Implementation**
   - Should holders be a mixin/protocol or Task subclass?
   - Thread safety: class-level vs instance-level locking?
   - Lazy loading: when to fetch subtasks?

2. **Custom Field System**
   - Extend existing CustomFieldAccessor or new pattern?
   - How to handle SQL fallbacks in SDK context?
   - Default/override resolution order?

3. **Navigation Properties**
   - Bidirectional references: cached or computed?
   - Circular import prevention strategy?
   - Lazy vs eager loading trade-offs?

4. **SQL Integration**
   - Should SDK have SQL dependency at all?
   - Plugin architecture for fallback providers?
   - Mock/stub for SDK-only users?

5. **Nested Holders (Unit → OfferHolder/ProcessHolder)**
   - Recursive holder pattern?
   - Depth limits?
   - Performance implications?

### 3.3 Testing Strategy

**Coverage Requirements**:

1. **Unit Tests**
   - Each model standalone (no DB required)
   - Custom field accessor logic
   - Navigation property resolution
   - Thread safety (concurrent access)

2. **Integration Tests**
   - Full hierarchy creation
   - Bidirectional navigation
   - SQL fallback behavior
   - SaveSession with nested models

3. **Validation Tests**
   - NAME_CONVENTION template rendering
   - Emoji indicators in task names
   - Required vs optional holders
   - Holder creation on-demand

### 3.4 Migration Path for Existing Code

**Compatibility Layer**:

```python
# Legacy import
from apis.asana_api.objects.task.models import Business

# Should also work with:
from autom8_asana.models import Business
```

**Import Aliases** (during transition):
```python
# Old location
apis.asana_api.objects.task.models.Business

# New location
autom8_asana.models.business.Business

# Compatibility shim
from autom8_asana.models import Business as NewBusiness
Business = NewBusiness  # Alias for gradual migration
```

---

## 4. Key Patterns to Preserve

### 4.1 Thread-Safe Holder Loading

**Pattern**:
```python
def _get_contact_holder(self) -> "ContactHolder":
    attr = "contact_holder"
    return self.get_holder(f"_{attr}", self.HOLDER_KEY_MAP[attr])

@thread_safe_property
def ts_contact_holder(self) -> "ContactHolder":
    return self._get_contact_holder()

@property
def contact_holder(self) -> "ContactHolder":
    return self.ts_contact_holder
```

**Rationale**: Double-return pattern allows both thread-safe and non-thread-safe access.

### 4.2 Custom Field with SQL Fallback

**Pattern**:
```python
@classmethod
def default_owner_name(cls) -> str:
    return "contact_holder.owner_name"

@thread_safe_property
def owner_name_field(self) -> OwnerName:
    if not hasattr(self, "_owner_name_field"):
        self._owner_name_field = OwnerName(
            task=self,
            default=self.default_owner_name(),
            fallback="sql_record.owner_name",
            override=True
        )
    return self._owner_name_field

@property
def owner_name(self) -> str:
    return self.owner_name_field.get()

@owner_name.setter
def owner_name(self, value):
    self.owner_name_field.set(value)
```

**Rationale**:
- `default`: Computed value from other fields
- `fallback`: SQL column when Asana field is empty
- `override`: Force default even if Asana has a value

### 4.3 Bidirectional Navigation

**Pattern**:
```python
# Downward (parent → child)
class Business(Task):
    @property
    def contact(self) -> "Contact":
        return self.contact_holder.contact

# Upward (child → parent)
class Contact(Task):
    @property
    def business(self) -> "Business":
        return self.contact_holder.business

# Cross-navigation (sibling via parent)
class Contact(Task):
    @property
    def unit(self):
        return self.business.unit
```

**Rationale**: Rich navigation without requiring N+1 queries.

### 4.4 NAME_CONVENTION Template Rendering

**Pattern**:
```python
class Business(Task):
    # No explicit NAME_CONVENTION (uses task name directly)
    pass

class ContactHolder(Task):
    NAME_CONVENTION = "[self.parent.name] Contacts 🧑"

class Contact(Task):
    NAME_CONVENTION = "[self.parent.parent.name] Team"

class Unit(Task):
    NAME_CONVENTION = "[self.parent.parent.name] — [self.vertical.vertical_name]"

class Location(Task):
    NAME_CONVENTION = "[self.parent.parent.name] — [city], [state] 📍"
```

**Rationale**:
- Emoji indicators for visual recognition
- Parent name inheritance
- Context-specific suffixes

---

## 5. Critical Questions for Architect

**Before implementation begins, resolve**:

1. **SQL Dependency**: Should `autom8_asana` SDK have SQL imports, or should SQL integration be a separate plugin?
   - **Implication**: If SQL is required, SDK becomes autom8-specific (not general-purpose)
   - **Options**:
     - A) Bundle SQL (fast, couples SDK to autom8)
     - B) Plugin system (flexible, more complex)
     - C) Stub/mock SQL for SDK-only users (compromise)

2. **Legacy Import Compatibility**: Should we support `from apis.asana_api.objects.task.models import Business` in SDK?
   - **Implication**: Namespace collision risk
   - **Options**:
     - A) New namespace only (`from autom8_asana.models import Business`)
     - B) Compatibility shim for 6-month transition period
     - C) Gradual migration with deprecation warnings

3. **Thread Safety**: Class-level locking or instance-level for holder properties?
   - **Implication**: Performance vs safety trade-off
   - **Current**: Instance-level `_sql_lock` on Business
   - **Question**: Extend to all holders?

4. **Nested Holder Depth**: Should we limit nesting (e.g., max 2 levels: Unit → OfferHolder)?
   - **Current**: Unit has nested holders, but Offer doesn't
   - **Future**: Could Process have nested holders too?
   - **Question**: Set explicit depth limit?

5. **Custom Field Fallback Resolution**: What's the priority order?
   1. Asana custom field value (if not empty)
   2. Default (computed from other fields)
   3. Fallback (SQL column)
   4. None

   **Question**: Should override=True bypass Asana value? (Current: yes)

6. **Holder Auto-Creation**: When should holders be auto-created?
   - **Current**: `save()` method creates missing holders
   - **Question**: Should SDK support this, or require explicit creation?

---

## 6. Success Criteria

**Definition of Done**:

1. **Functional Parity**
   - All 7 holders accessible from Business
   - ContactHolder → Contact[] working
   - UnitHolder → Unit[] working
   - LocationHolder → Location + Hours working
   - Bidirectional navigation operational

2. **Custom Field Coverage**
   - Business: 18 fields with typed accessors
   - ContactHolder: 23 fields
   - Contact: 21 fields
   - UnitHolder: 39 fields
   - Unit: 44 fields
   - Location: 11 fields
   - Hours: 6 fields

3. **SQL Integration**
   - `sql_record` pattern working (or stubbed)
   - Fallback resolution functional
   - Thread-safe DB queries

4. **Test Coverage**
   - Unit tests: >90% coverage
   - Integration tests: All navigation paths
   - Thread safety tests: Concurrent access scenarios

5. **Documentation**
   - ADRs for all design decisions
   - TDD with implementation specs
   - Migration guide from legacy

6. **Performance**
   - Holder loading: <100ms per holder
   - Custom field access: <10ms (cached)
   - Full hierarchy load: <1s for Business with all children

---

## 7. Out of Scope (Explicitly Excluded)

**Do NOT implement in this phase**:

1. **Manager Classes**
   - AdManager, AdFactory, ReconcileBudget
   - These are business logic, not data models
   - Can be separate package later

2. **Process Subclasses**
   - 24+ Process subclasses (AdApproval, Expansion, Month1, etc.)
   - Extremely complex, domain-specific
   - Phase 2 work

3. **Advanced Insights**
   - Performance reports
   - CHI (Customer Health Index)
   - Optimization algorithms

4. **Webhooks for Model Events**
   - Auto-update on holder creation
   - Cascade deletes
   - Event-driven updates

5. **Caching Beyond Base SDK**
   - TTL customization
   - Cache warming
   - Invalidation strategies

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Circular import issues (bidirectional refs) | High | High | Use TYPE_CHECKING, forward references |
| Thread safety bugs (concurrent holder access) | Medium | High | Comprehensive concurrency tests |
| SQL fallback complexity | Medium | Medium | Plugin architecture or mock layer |
| Performance degradation (deep nesting) | Low | Medium | Lazy loading, caching |
| Legacy compatibility breaks | High | Medium | 6-month deprecation period |
| Incomplete understanding of Process subclasses | High | Low | Defer to Phase 2 |

---

## 9. Deliverables Checklist

**@requirements-analyst** produces:
- [ ] PRD-0010: Business Model Hierarchy Migration
- [ ] User stories for 7 holder workflows
- [ ] Acceptance criteria with navigation scenarios
- [ ] Custom field requirements matrix

**@architect** produces:
- [ ] TDD-0015: Business Model Technical Design
- [ ] ADR-0050: Holder Pattern Implementation
- [ ] ADR-0051: SQL Integration Strategy
- [ ] ADR-0052: Navigation Property Design
- [ ] ADR-0053: Custom Field Fallback Resolution
- [ ] ADR-0054: Thread Safety Approach

**@principal-engineer** produces:
- [ ] `src/autom8_asana/models/business.py`
- [ ] `src/autom8_asana/models/contact_holder.py`
- [ ] `src/autom8_asana/models/contact.py`
- [ ] `src/autom8_asana/models/unit_holder.py`
- [ ] `src/autom8_asana/models/unit.py`
- [ ] `src/autom8_asana/models/location_holder.py`
- [ ] `src/autom8_asana/models/location.py`
- [ ] `src/autom8_asana/models/hours.py`
- [ ] `src/autom8_asana/models/offer_holder.py` (stub)
- [ ] `src/autom8_asana/models/offer.py` (stub)
- [ ] `src/autom8_asana/models/process_holder.py` (stub)
- [ ] `src/autom8_asana/models/process.py` (stub)
- [ ] `tests/unit/models/test_business.py`
- [ ] `tests/unit/models/test_contact_holder.py`
- [ ] `tests/unit/models/test_unit.py`
- [ ] `tests/integration/test_business_hierarchy.py`

**@qa-adversary** produces:
- [ ] Test plan covering all navigation paths
- [ ] Thread safety validation tests
- [ ] SQL fallback behavior tests
- [ ] Performance benchmarks
- [ ] Migration validation checklist

---

## 10. Next Steps

**Immediate Actions**:

1. **Invoke @orchestrator** with this Prompt 0
2. **@orchestrator creates phased execution plan**
3. **@requirements-analyst** produces PRD-0010 with acceptance criteria
4. **@architect** resolves open questions (#1-6) via ADRs
5. **Begin Phase 1: Business + ContactHolder** (highest value path)

**Context to Provide to Agents**:

- Legacy file paths: `/Users/tomtenuta/Code/autom8/apis/asana_api/objects/task/models`
- SDK target: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models`
- This Prompt 0 document
- Existing SDK structure (Task, CustomFieldAccessor, SaveSession)

---

**Ready to begin migration. Awaiting @orchestrator invocation.**
