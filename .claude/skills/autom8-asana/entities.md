# Business Entities

> Entity hierarchy, detection system, custom field access patterns, and pipeline participation.

---

## Table of Contents

1. [Entity Hierarchy](#entity-hierarchy)
2. [Entity Reference](#entity-reference)
3. [Process and Pipeline](#process-and-pipeline)
4. [Detection System](#detection-system)
5. [Holder Pattern](#holder-pattern)
6. [Custom Field Access](#custom-field-access)
7. [Navigation](#navigation)
8. [Cascading vs Inherited Fields](#cascading-vs-inherited-fields)

---

## Entity Hierarchy

All business entities inherit from Task. Asana sees them as tasks with subtasks. The SDK provides typed wrappers.

```
Business (root, 19 fields)
    +-- ContactHolder --> Contact[] (19 fields)
    +-- UnitHolder --> Unit[] (31 fields, composite)
    |                    +-- OfferHolder --> Offer[] (39 fields)
    |                    +-- ProcessHolder --> Process[] (pipeline participants)
    +-- LocationHolder
    |       +-- Address (12 fields, sibling)
    |       +-- Hours (7 fields, sibling)
    +-- DNAHolder, ReconciliationHolder, VideographyHolder (stubs)
```

**Total**: 127 custom fields across all entity types.

**Note**: Process entities are special - they participate in the **7-stage pipeline** (Lead > Sales > Onboarding > Production > Retention > Offboarding > Archive). Pipeline advancement triggers automation rules. See [Process and Pipeline](#process-and-pipeline).

---

## Entity Reference

### Business

Root entity with 7 holders.

| Aspect | Detail |
|--------|--------|
| Fields | 19 |
| Key fields | company_id, mrr, office_phone, owner_name, vertical |
| Cascading | office_phone, company_id (to all descendants) |

```python
business.contacts     # -> ContactHolder.contacts
business.units        # -> UnitHolder.units
business.address      # -> LocationHolder.address
```

### Contact

Person associated with a Business.

| Aspect | Detail |
|--------|--------|
| Fields | 19 |
| Key fields | contact_email, contact_phone, position, full_name |
| Navigation | .contact_holder, .business |

Owner detection via `OWNER_POSITIONS = {"owner", "ceo", "founder", "president", "principal"}`:

```python
contact.is_owner           # bool
contact_holder.owner       # Contact | None
```

### Unit

Composite entity with nested holders (OfferHolder, ProcessHolder).

| Aspect | Detail |
|--------|--------|
| Fields | 31 |
| Key fields | mrr, vertical, products, platforms, ad_account_id |
| Cascading | platforms (to Offer, allow_override=True), vertical |

```python
unit.offers          # list[Offer]
unit.active_offers   # Offers with active ads
unit.processes       # list[Process]
```

### Offer

Ad campaign/placement - most fields (39).

| Aspect | Detail |
|--------|--------|
| Fields | 39 |
| Key fields | mrr, weekly_ad_spend, platforms, ad_id, campaign_id |
| Navigation | .offer_holder, .unit, .business |

### Address / Hours

Siblings under LocationHolder (not parent-child):

```python
address = business.location_holder.address
hours = address.hours  # Sibling access
```

---

## Process and Pipeline

Processes are the **core business value driver**. They represent work moving through the 7-stage pipeline from lead acquisition to offboarding.

### ProcessType Enum

The 7 pipeline stages representing business lifecycle:

| ProcessType | Stage | Description |
|-------------|-------|-------------|
| `LEAD` | 1 | Initial contact, qualification |
| `SALES` | 2 | Active sales engagement |
| `ONBOARDING` | 3 | New customer setup |
| `PRODUCTION` | 4 | Active service delivery |
| `RETENTION` | 5 | Renewal, upsell |
| `OFFBOARDING` | 6 | Service termination |
| `ARCHIVE` | 7 | Historical record |

```python
from autom8_asana.models.business.process import ProcessType

process.process_type  # -> ProcessType.SALES
process.process_type.next()  # -> ProcessType.ONBOARDING
process.process_type.is_active  # -> True (not ARCHIVE)
```

### ProcessSection Enum

Visual state within a pipeline project (Asana sections):

| ProcessSection | Meaning |
|----------------|---------|
| `BACKLOG` | Not yet started |
| `IN_PROGRESS` | Currently being worked |
| `BLOCKED` | Waiting on external factor |
| `REVIEW` | Pending approval |
| `COMPLETE` | Done, ready for next stage |

### Pipeline State

Process entities expose a computed `pipeline_state` property:

```python
@property
def pipeline_state(self) -> PipelineState:
    """Current position in the overall pipeline."""
    return PipelineState(
        process_type=self.process_type,
        section=self.section,
        is_terminal=self.process_type == ProcessType.ARCHIVE,
    )
```

### Pipeline Advancement

When a Process reaches the `COMPLETE` section, it becomes eligible for **pipeline conversion** - automatic creation of a new Process in the next stage.

```
Process (SALES, COMPLETE)
        |
        v
  [AutomationEngine detects advancement]
        |
        v
  PipelineConversionRule triggers
        |
        v
  TemplateDiscovery finds ONBOARDING template
        |
        v
  New Process (ONBOARDING, BACKLOG) created
        |
        v
  FieldSeeder propagates fields from parent
```

See [automation.md](automation.md) for the full automation flow.

### Process Entity

| Aspect | Detail |
|--------|--------|
| Parent | ProcessHolder (under Unit) |
| Fields | process_type, vertical, various stage-specific fields |
| Key property | `pipeline_state` (computed) |
| Navigation | `.process_holder`, `.unit`, `.business` |

```python
unit.processes               # All processes for this unit
unit.active_processes        # Processes not in ARCHIVE
process.is_advancement_ready # In COMPLETE section, not terminal
```

---

## Detection System

Given a raw Asana task, the detection system identifies entity type using a 5-tier approach.

### The 5 Tiers

| Tier | Method | Confidence | Cost |
|------|--------|------------|------|
| 1 | Project membership | 100% | O(1) |
| 2 | Name pattern | 60% | O(1) |
| 3 | Parent inference | 80% | O(1) |
| 4 | Structure inspection | 90% | O(n) async |
| 5 | Unknown fallback | 0% | O(1) |

### Usage

```python
from autom8_asana.models.business.detection import detect_entity_type

result = detect_entity_type(task)

if result:  # Not UNKNOWN
    print(f"{result.entity_type.name} (tier {result.tier_used})")

if result.needs_healing:
    # Task should join expected project for future O(1) lookups
    await add_task_to_project(task.gid, result.expected_project_gid)
```

### With Known Parent

When iterating holder children, provide parent type for Tier 3:

```python
for child in holder_subtasks:
    result = detect_entity_type(child, parent_type=EntityType.CONTACT_HOLDER)
    # -> EntityType.CONTACT via Tier 3 inference
```

### DetectionResult

```python
@dataclass(frozen=True)
class DetectionResult:
    entity_type: EntityType      # Detected type or UNKNOWN
    confidence: float            # 0.0 - 1.0
    tier_used: int               # 1-5
    needs_healing: bool          # Should join expected project?
    expected_project_gid: str | None
```

### ProjectTypeRegistry

Singleton for O(1) Tier 1 lookups:

```python
from autom8_asana.models.business.registry import get_registry

registry = get_registry()
entity_type = registry.lookup("1200653012566782")  # -> EntityType.BUSINESS
```

Auto-populated from entity class `PRIMARY_PROJECT_GID` attributes.

---

## Holder Pattern

Holders group related children under a parent.

### HOLDER_KEY_MAP

Each entity defines its holders:

```python
class Business(Task):
    HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
        "contact_holder": ("Contacts", "person"),     # (name, emoji)
        "unit_holder": ("Units", "package"),
        "location_holder": ("Location", "map"),
    }
```

### Holder Types

| Holder | Contains | Under |
|--------|----------|-------|
| ContactHolder | Contact[] | Business |
| UnitHolder | Unit[] | Business |
| LocationHolder | Address, Hours | Business |
| OfferHolder | Offer[] | Unit |
| ProcessHolder | Process[] | Unit |

### Hydration Flow

```
1. session.track(business)
   --> Queues for prefetch

2. await session.prefetch_pending()
   --> API: get_subtasks(business.gid)
   --> Matches subtasks to HOLDER_KEY_MAP
   --> Creates typed holders

3. For each holder:
   --> API: get_subtasks(holder.gid)
   --> holder._populate_children(subtasks)
```

---

## Custom Field Access

All custom fields use typed property pattern:

```python
class Business(Task):
    class Fields:
        COMPANY_ID = "Company ID"
        MRR = "MRR"

    @property
    def company_id(self) -> str | None:
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

### Field Types

| Type | API Returns | Property Returns |
|------|-------------|------------------|
| Text | `str` | `str | None` |
| Number | `float` | `Decimal | None` |
| Enum | `{"gid": "...", "name": "..."}` | `str | None` |
| Multi-enum | `[{"gid": "...", "name": "..."}]` | `list[str]` |
| Date | `"YYYY-MM-DD"` | `date | None` |

---

## Navigation

### Downward (parent to children)

```python
business.contacts                    # All contacts
business.contact_holder.owner        # Owner contact
business.units                       # All units
business.units[0].offers             # Unit's offers
business.address                     # Shortcut to LocationHolder.address
```

### Upward (child to parent)

Children cache parent references:

```python
contact.contact_holder               # Parent holder
contact.business                     # Root business (cached)
offer.unit                           # Grandparent unit
offer.business                       # Root business
```

### Siblings

```python
business.location_holder.address.hours  # Address -> Hours
business.location_holder.hours.address  # Hours -> Address
```

---

## Cascading vs Inherited Fields

### Cascading Fields

Owner pushes value to descendants. Stored redundantly for O(1) read.

```python
business.office_phone = "555-9999"
session.cascade_field(business, "Office Phone")
# All Units, Offers, Processes get "555-9999"
```

| Behavior | Use Case |
|----------|----------|
| `allow_override=False` (default) | Always overwrite (office_phone) |
| `allow_override=True` | Skip non-null descendants (platforms) |

### Inherited Fields

Resolved from parent chain at read time. No storage on child.

```python
@property
def vertical(self) -> str | None:
    if self._is_field_overridden("Vertical"):
        return self.get_custom_fields().get("Vertical")
    if self._unit:
        return self._unit.vertical
    return None
```

---

## Key Files

| File | Purpose |
|------|---------|
| `models/business/detection.py` | EntityType, DetectionResult, detect_entity_type |
| `models/business/registry.py` | ProjectTypeRegistry |
| `models/business/business.py` | Business root entity |
| `models/business/contact.py` | Contact entity |
| `models/business/unit.py` | Unit composite entity |
| `models/business/offer.py` | Offer entity |
| `models/business/process.py` | Process entity, ProcessType, ProcessSection, PipelineState |
