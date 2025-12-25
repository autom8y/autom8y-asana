# PRD: Business Model Layer Implementation

## Metadata

- **PRD ID**: PRD-BIZMODEL
- **Status**: Implemented
- **Author**: Requirements Analyst
- **Created**: 2025-12-11
- **Last Updated**: 2025-12-25
- **Stakeholders**: SDK Users, Automation Engineers, API Consumers
- **Related PRDs**: PRD-0001 (SDK Extraction), PRD-0005 (Save Orchestration)
- **Related ADRs**: ADR-0050 (Holder Lazy Loading), ADR-0051 (Custom Field Type Safety), ADR-0052 (Bidirectional Reference Caching), ADR-0053 (Composite SaveSession Support), ADR-0054 (Cascading Custom Fields)
- **Related TDDs**: TDD-BIZMODEL, TDD-PATTERNS-C (HolderFactory), TDD-HARDENING-A/B/C
- **Discovery Document**: `docs/initiatives/DISCOVERY-BIZMODEL-001.md`
- **Implementation**: `src/autom8_asana/models/business/` and `src/autom8_asana/persistence/`

---

## Implementation Summary

**Status**: All requirements implemented and tested as of December 2025.

### What Was Built

#### Core Models (7 Entity Types)
All entity types implemented in `src/autom8_asana/models/business/`:
- **Business** (`business.py`) - Root entity with 7 holder properties and 19 custom fields
- **Contact** (`contact.py`) - Contact entity with owner detection and name parsing
- **Unit** (`unit.py`) - Unit entity with nested OfferHolder and ProcessHolder
- **Offer** (`offer.py`) - Offer entity with ad status determination and 39 custom fields
- **Process** (`process.py`) - Base process entity with extensible pattern for subclasses
- **Location/Address** (`location.py`) - Address entity with sibling Hours navigation
- **Hours** (`hours.py`) - Hours entity with day-of-week accessors and convenience methods

#### Holder Infrastructure (7 Types)
- **Typed Holders**: ContactHolder, UnitHolder, LocationHolder, OfferHolder, ProcessHolder
- **Stub Holders**: DNAHolder, ReconciliationHolder, AssetEditHolder, VideographyHolder
- **HolderFactory Pattern** (`holder_factory.py`) - Eliminates boilerplate for all holders per TDD-PATTERNS-C

#### Custom Field System (127 Fields)
- **Field Descriptors** (`descriptors.py`) - TextField, EnumField, NumberField, MultiEnumField, PeopleField
- **Shared Mixins** (`mixins.py`) - SharedCascadingFieldsMixin, FinancialFieldsMixin
- **Field Definitions** (`fields.py`) - CascadingFieldDef, InheritedFieldDef
- Field count distribution: Business (19), Contact (19), Unit (31), Offer (39), Address (12), Hours (7)

#### Persistence Extensions
Implemented in `src/autom8_asana/persistence/`:
- **SaveSession Extensions** (`session.py`) - `prefetch_holders`, `recursive`, `cascade_field` methods
- **Cascade Infrastructure** (`cascade.py`) - CascadeOperation, CascadeExecutor with batch updates
- **Hydration System** (`models/business/hydration.py`) - Efficient entity type detection and conversion

#### Additional Capabilities
- **Detection System** (`models/business/detection/`) - 4-tier entity type detection (tier1-4.py)
- **Registry** (`models/business/registry.py`) - Entity type registration and lookup
- **Navigation** - Bidirectional upward/downward traversal through hierarchy
- **Validation** - Type safety verified with mypy, comprehensive test coverage

### Deviations from Original PRD

1. **Enhanced beyond scope**: Detection system (4 tiers) and registry not in original PRD
2. **HolderFactory pattern**: Adopted during implementation to reduce duplication (TDD-PATTERNS-C)
3. **Naming refinement**: ReconciliationsHolder renamed to ReconciliationHolder (TDD-HARDENING-C)
4. **Additional entity types**: DNA, Reconciliation, AssetEdit, Videography, Resolution entities implemented
5. **Process subclasses**: Audit, Build, Creative, Discovery, Listing, SEO, Setup entities implemented (originally Phase 2)

### Quality Verification

- **Type Safety**: mypy passes with zero errors (NFR-001)
- **Test Coverage**: Comprehensive integration and unit tests across business model and persistence
- **Backward Compatibility**: All existing persistence tests pass unchanged (NFR-006)
- **Performance**: Holder prefetch uses efficient batch operations (NFR-003)

---

## Problem Statement

### What Problem Are We Solving?

The autom8_asana SDK provides low-level Asana API access but lacks domain-specific abstractions for the business model hierarchy. Developers must:

1. **Manually navigate task hierarchies** - No typed navigation between Business, Unit, Offer, Contact entities
2. **Resolve custom fields by string names** - No IDE autocomplete or type safety for 127 business-specific fields
3. **Manually manage parent-child relationships** - No holder pattern abstraction for grouping related entities
4. **Implement field propagation logic** - No cascading field support for maintaining data consistency across hierarchy levels
5. **Handle lazy loading manually** - No integrated prefetch patterns for efficient API usage

### For Whom?

- **SDK Consumers**: Developers building automation workflows on top of the SDK
- **Internal Operations**: Teams managing Business entities through code rather than Asana UI
- **Integration Engineers**: Building pipelines that read/write Business hierarchy data

### Impact of Not Solving

- **Development velocity**: Each integration must reimplement hierarchy navigation and field access patterns
- **Type safety**: Runtime errors from typos in field names; no IDE support
- **Data consistency**: Manual cascade propagation leads to stale field values across hierarchy
- **API efficiency**: Without lazy loading, excessive API calls or premature fetches

---

## Goals and Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| **Type-safe field access** | Fields accessible via typed properties | 127/127 fields with IDE autocomplete |
| **Hierarchy navigation** | Bidirectional navigation available | All 7 entity types navigable up/down |
| **Data consistency** | Cascading field propagation | Business and Unit cascades execute correctly |
| **API efficiency** | Holder prefetch on track() | Single batch fetch per hierarchy level |
| **Developer experience** | Code completion coverage | All models, holders, and fields discoverable |
| **Test coverage** | Business model code coverage | >80% line coverage |
| **Type safety** | mypy passes | Zero type errors in business model code |

---

## Scope

### In Scope

#### Models (7 Entity Types)
- Business (root entity with 7 holders)
- Contact (child of ContactHolder)
- Unit (child of UnitHolder, with nested OfferHolder and ProcessHolder)
- Offer (child of OfferHolder under Unit)
- Process (base type, child of ProcessHolder under Unit)
- Address (sibling of Hours under LocationHolder)
- Hours (sibling of Address under LocationHolder)

#### Holders (7 Types)
- ContactHolder, UnitHolder, LocationHolder (fully typed)
- OfferHolder, ProcessHolder (fully typed)
- DNAHolder, ReconciliationsHolder, AssetEditHolder, VideographyHolder (stub - return as plain Task)

#### Custom Fields (127 Total)
- Business: 19 fields
- Contact: 19 fields
- Unit: 31 fields
- Address: 12 fields
- Hours: 7 fields
- Offer: 39 fields

#### Infrastructure
- SaveSession extensions (prefetch_holders, recursive tracking, cascade_field)
- CascadeOperation and CascadeExecutor classes
- CascadingFieldDef and InheritedFieldDef dataclasses

### Out of Scope

- **Process Subclasses** (Phase 2): 24+ Process subclass types (Audit, Build, Creative, etc.)
- **CascadeReconciler**: Drift detection and repair tooling
- **Multi-location Business**: LocationHolder contains single Address/Hours pair (siblings)
- **DNA, Reconciliations, AssetEdit, Videography Children**: Return as plain Task, no typed children
- **Custom field GID resolution at definition time**: Runtime resolution via existing CustomFieldAccessor

---

## Requirements

### FR-MODEL: Model Class Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-MODEL-001 | Business model extends Task with HOLDER_KEY_MAP defining 7 holder types | Must | Business class inherits from Task; HOLDER_KEY_MAP contains 7 entries mapping property names to (name, emoji) tuples |
| FR-MODEL-002 | Business model has holder properties (contact_holder, unit_holder, location_holder, dna_holder, reconciliations_holder, asset_edit_holder, videography_holder) returning typed or stub holders | Must | All 7 holder properties defined; typed holders return correct class; stub holders return Task |
| FR-MODEL-003 | Business model has convenience shortcuts (contacts, units, address, hours) | Should | `business.contacts` returns `list[Contact]`; `business.units` returns `list[Unit]`; `business.address` returns `Address | None`; `business.hours` returns `Hours | None` |
| FR-MODEL-004 | Contact model extends Task with owner detection via OWNER_POSITIONS set | Must | Contact.is_owner returns True when position field matches owner/ceo/founder/president/principal (case-insensitive) |
| FR-MODEL-005 | Contact model provides name parsing via nameparser integration | Should | Contact exposes first_name, last_name, display_name, preferred_name properties derived from Task.name |
| FR-MODEL-006 | Unit model extends Task with nested HOLDER_KEY_MAP for OfferHolder and ProcessHolder | Must | Unit.HOLDER_KEY_MAP contains offer_holder and process_holder entries |
| FR-MODEL-007 | Unit model has convenience shortcuts (offers, processes, active_offers) | Should | `unit.offers` returns `list[Offer]`; `unit.processes` returns `list[Task]`; `unit.active_offers` returns offers with has_active_ads=True |
| FR-MODEL-008 | Offer model extends Task with ad status determination | Must | Offer.has_active_ads returns True when active_ads_url or ad_id is set |
| FR-MODEL-009 | Process model extends Task as base type for process entities | Must | Process class exists, inherits from Task, no specialized behavior in Phase 1 |
| FR-MODEL-010 | Address model extends Task with sibling navigation to Hours | Must | Address._hours PrivateAttr populated during LocationHolder population; address.hours returns sibling Hours entity |
| FR-MODEL-011 | Hours model extends Task with day-of-week field accessors and convenience methods | Must | Hours has monday through sunday properties; all_days, weekday_hours, weekend_hours, to_dict methods; set_weekday_hours, set_weekend_hours, set_all_hours mutators |
| FR-MODEL-012 | All models use Pydantic v2 with PrivateAttr for cached references | Must | Models inherit from Task (Pydantic BaseModel); cached references (_business, _holder, etc.) use PrivateAttr(default=None) |

### FR-HOLDER: Holder Pattern Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-HOLDER-001 | ContactHolder extends Task with _contacts PrivateAttr and contacts property returning list[Contact] | Must | ContactHolder.contacts returns typed list; _contacts populated by _populate_children |
| FR-HOLDER-002 | ContactHolder provides owner property returning Contact with is_owner=True or None | Must | ContactHolder.owner iterates contacts, returns first with is_owner=True |
| FR-HOLDER-003 | UnitHolder extends Task with _units PrivateAttr and units property returning list[Unit] | Must | UnitHolder.units returns typed list; _units populated by _populate_children |
| FR-HOLDER-004 | OfferHolder extends Task with _offers PrivateAttr, offers property, and active_offers filter | Must | OfferHolder.offers returns typed list; active_offers filters by has_active_ads |
| FR-HOLDER-005 | ProcessHolder extends Task with _children PrivateAttr for Process entities | Must | ProcessHolder holds list of Task (Process in Phase 2); _populate_children creates typed children |
| FR-HOLDER-006 | LocationHolder extends Task with _address and _hours PrivateAttrs for sibling entities | Must | LocationHolder.address and LocationHolder.hours return singular entities; siblings linked via _populate_children |
| FR-HOLDER-007 | Stub holders (DNA, Reconciliations, AssetEdit, Videography) return as plain Task | Must | Business.dna_holder returns Task | None; no typed children |
| FR-HOLDER-008 | All holders implement _populate_children(subtasks: list[Task]) method | Must | Method converts Task instances to typed children and sets back-references |
| FR-HOLDER-009 | Holder detection uses name match first, emoji fallback second | Must | _matches_holder checks task.name == name_pattern, then checks custom_emoji.name == emoji |

### FR-FIELD: Custom Field Accessor Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-FIELD-001 | Each model class has inner Fields class with field name constants | Must | Business.Fields.COMPANY_ID = "Company ID"; enables IDE autocomplete for field names |
| FR-FIELD-002 | Text fields expose typed str | None property with getter/setter delegating to CustomFieldAccessor | Must | `company_id` property: getter returns `get_custom_fields().get(Fields.COMPANY_ID)`, setter calls `set()` |
| FR-FIELD-003 | Number fields expose typed Decimal | None property with conversion | Must | `mrr` property: getter converts float to Decimal(str(value)); setter converts Decimal to float |
| FR-FIELD-004 | Enum fields expose typed str | None property extracting name from dict | Must | `vertical` property: if value is dict, return value.get("name"); else return value |
| FR-FIELD-005 | Multi-enum fields expose typed list[str] property extracting names from list[dict] | Must | `platforms` property: returns [v.get("name") if isinstance(v, dict) else v for v in value] |
| FR-FIELD-006 | People fields expose typed list[dict] property | Must | `rep` property: returns value as list or empty list if None |
| FR-FIELD-007 | Business model implements all 19 custom field accessors per custom-fields-glossary.md | Must | All fields from glossary have typed property accessors with getters and setters |
| FR-FIELD-008 | Contact model implements all 19 custom field accessors per custom-fields-glossary.md | Must | All fields from glossary have typed property accessors |
| FR-FIELD-009 | Unit model implements all 31 custom field accessors per custom-fields-glossary.md | Must | All fields from glossary have typed property accessors |
| FR-FIELD-010 | Address model implements all 12 custom field accessors per custom-fields-glossary.md | Must | All fields from glossary have typed property accessors |
| FR-FIELD-011 | Hours model implements all 7 custom field accessors per custom-fields-glossary.md | Must | All fields from glossary have typed property accessors |
| FR-FIELD-012 | Offer model implements all 39 custom field accessors per custom-fields-glossary.md | Must | All fields from glossary have typed property accessors |
| FR-FIELD-013 | Field setters trigger change tracking via CustomFieldAccessor.set() | Must | After setting property, get_custom_fields().has_changes() returns True |

### FR-CASCADE: Cascading Field Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CASCADE-001 | CascadingFieldDef dataclass supports multi-level cascading with allow_override parameter (default=False) | Must | CascadingFieldDef(name, target_types, allow_override=False); applies_to() checks type membership; should_update_descendant() returns True when allow_override=False OR current value is None |
| FR-CASCADE-002 | Business model declares CascadingFields inner class with OFFICE_PHONE, COMPANY_ID, BUSINESS_NAME, PRIMARY_CONTACT_PHONE definitions | Must | Business.CascadingFields.all() returns 4 CascadingFieldDef instances; get(name) returns matching def |
| FR-CASCADE-003 | Unit model declares CascadingFields inner class with PLATFORMS (allow_override=True), VERTICAL (allow_override=False), BOOKING_TYPE (allow_override=False) definitions | Must | Unit.CascadingFields.all() returns 3 CascadingFieldDef instances with correct override settings |
| FR-CASCADE-004 | CascadingFieldDef.target_types=None means cascade to all descendants | Must | When target_types is None, applies_to() returns True for any entity type |
| FR-CASCADE-005 | When allow_override=False (default), cascade ALWAYS overwrites descendant value | Must | should_update_descendant() returns True regardless of current value |
| FR-CASCADE-006 | When allow_override=True, cascade only overwrites if descendant value is None | Must | should_update_descendant() checks get_custom_fields().get(name) and returns True only if None |
| FR-CASCADE-007 | CascadingFieldDef supports source_field for non-custom-field sources (e.g., Task.name) | Should | source_field="name" maps from model attribute instead of custom field |
| FR-CASCADE-008 | Cascade scope is relative to source entity (unit cascade only affects that unit's children) | Must | cascade_field(unit_a, "Platforms") does not affect unit_b's offers |

### FR-INHERIT: Inherited Field Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-INHERIT-001 | InheritedFieldDef dataclass supports parent chain resolution | Must | InheritedFieldDef(name, inherit_from, allow_override, default) dataclass defined |
| FR-INHERIT-002 | Offer model inherits vertical from Unit via parent chain resolution | Should | Offer.vertical property checks local override flag, falls back to Unit.vertical |
| FR-INHERIT-003 | Inherited field properties check override flag before traversing parent chain | Should | _is_field_overridden(field_name) checks "{field_name} Override" custom field |
| FR-INHERIT-004 | Inherited fields support inherit_vertical()/inherit_manager() methods to clear local override | Could | Method removes local value and override flag, causing next read to resolve from parent |

### FR-SESSION: SaveSession Integration Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-SESSION-001 | SaveSession.track() accepts optional prefetch_holders: bool parameter (default=False) | Must | track(entity, prefetch_holders=True) adds entity to _pending_prefetch list |
| FR-SESSION-002 | SaveSession.track() accepts optional recursive: bool parameter (default=False) | Must | track(entity, recursive=True) calls _track_recursive to track all descendants |
| FR-SESSION-003 | SaveSession._pending_prefetch list stores entities awaiting holder prefetch | Must | List initialized in __init__; populated by track() when prefetch_holders=True |
| FR-SESSION-004 | SaveSession._pending_cascades list stores CascadeOperation instances | Must | List initialized in __init__; populated by cascade_field() |
| FR-SESSION-005 | SaveSession.cascade_field(entity, field_name, target_types=None) queues cascade operation | Must | Method creates CascadeOperation with resolved field value and appends to _pending_cascades; returns self for chaining |
| FR-SESSION-006 | cascade_field() raises ValueError if entity has temp GID | Must | Cannot cascade from entity without real Asana GID |
| FR-SESSION-007 | commit_async() executes prefetch before validation (Phase 1 of commit) | Must | _execute_prefetch() called before CRUD operations; holder subtasks fetched via API |
| FR-SESSION-008 | commit_async() executes cascades after CRUD operations (Phase 2 of commit) | Must | _execute_cascades() called after CRUD; CascadeExecutor processes all pending cascades |
| FR-SESSION-009 | Existing track(entity) behavior unchanged when parameters not provided | Must | track(entity) without parameters behaves identically to pre-extension behavior; existing tests pass |
| FR-SESSION-010 | SaveSession.prefetch_pending() async method available for explicit prefetch control | Should | await session.prefetch_pending() forces immediate prefetch of tracked entities with prefetch_holders=True |

### FR-CASCADE-EXEC: Cascade Executor Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CASCADE-EXEC-001 | CascadeOperation dataclass captures source, field_name, field_gid, new_value, target_types, allow_override | Must | Dataclass defined with all required fields; field_gid populated during execution |
| FR-CASCADE-EXEC-002 | CascadeExecutor collects descendant GIDs scoped to source entity | Must | Descendants collected via tracked entities or API; respects source entity scope |
| FR-CASCADE-EXEC-003 | CascadeExecutor applies allow_override filtering before batch update | Must | When allow_override=True, skip descendants where current value is not None |
| FR-CASCADE-EXEC-004 | CascadeExecutor resolves field name to GID at execution time | Must | Uses CustomFieldAccessor resolution; handles case-insensitive names |
| FR-CASCADE-EXEC-005 | CascadeExecutor executes batch updates via BatchClient (chunks of 10) | Must | Updates chunked per Asana API limits; uses existing BatchClient infrastructure |
| FR-CASCADE-EXEC-006 | CascadeExecutor handles rate limits with exponential backoff | Must | 429 responses trigger retry with backoff per ADR-0010 |
| FR-CASCADE-EXEC-007 | CascadeExecutor reports partial failures in SaveResult | Must | result.partial=True if some updates failed; result.failed contains error details |

### FR-NAV: Navigation Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-NAV-001 | Contact provides upward navigation: contact_holder, business properties | Must | Properties return cached PrivateAttr values; _resolve_business() walks parent chain |
| FR-NAV-002 | Unit provides upward navigation: unit_holder, business properties | Must | Properties return cached PrivateAttr values |
| FR-NAV-003 | Offer provides upward navigation: offer_holder, unit, business properties | Must | Properties return cached PrivateAttr values; chain through holders |
| FR-NAV-004 | Address provides upward and sibling navigation: location_holder, business, hours properties | Must | Properties return cached values; hours is sibling reference |
| FR-NAV-005 | Hours provides upward and sibling navigation: location_holder, business, address properties | Must | Properties return cached values; address is sibling reference |
| FR-NAV-006 | All entities implement _invalidate_refs() to clear cached navigation on hierarchy change | Should | Method sets all cached PrivateAttrs to None |

---

## Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Type safety | mypy passes with zero errors | Run `mypy src/autom8_asana/models/business/` |
| NFR-002 | Test coverage | >80% line coverage on business model code | pytest-cov report for models/business/ |
| NFR-003 | API efficiency | Holder prefetch uses single batch call per level | Verify via mock/spy in tests |
| NFR-004 | Cascade performance | <5 seconds for 100 descendant cascade | Benchmark test with 100-entity hierarchy |
| NFR-005 | Memory efficiency | No memory leaks from circular references | PrivateAttrs use weak refs or explicit invalidation |
| NFR-006 | Backward compatibility | Existing SaveSession tests pass unchanged | pytest tests/unit/persistence/ passes |
| NFR-007 | Documentation | All public APIs have docstrings | ruff DOC checks pass |
| NFR-008 | Import organization | No circular imports in models/business/ | mypy import checks pass; models use TYPE_CHECKING guards |

---

## User Stories / Use Cases

### UC-001: Navigating Business Hierarchy

```python
# As a developer, I want to navigate the business hierarchy with typed properties
async with client.save_session() as session:
    session.track(business, prefetch_holders=True)

    # Downward navigation with type safety
    for contact in business.contacts:
        print(f"Contact: {contact.full_name}, Owner: {contact.is_owner}")

    for unit in business.units:
        for offer in unit.offers:
            if offer.has_active_ads:
                print(f"Active offer: {offer.name}, Platform: {offer.platforms}")

    # Upward navigation
    offer = business.units[0].offers[0]
    assert offer.unit is business.units[0]
    assert offer.business is business
```

### UC-002: Accessing Typed Custom Fields

```python
# As a developer, I want IDE autocomplete and type safety for custom fields
unit = business.units[0]

# IDE shows available fields
print(unit.mrr)  # Decimal | None
print(unit.vertical)  # str | None (extracted from enum dict)
print(unit.platforms)  # list[str] (extracted from multi-enum)

# Setters trigger change tracking
unit.mrr = Decimal("5000.00")
unit.vertical = "Legal"
assert unit.get_custom_fields().has_changes()
```

### UC-003: Cascading Field Updates

```python
# As a developer, I want to propagate field values to descendants efficiently
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Update business field
    business.office_phone = "555-9999"

    # Cascade to all descendants (allow_override=False by default)
    session.cascade_field(business, "Office Phone")

    result = await session.commit_async()
    # All Units, Offers, Processes now have office_phone = "555-9999"
```

### UC-004: Unit-Level Cascade with Override

```python
# As a developer, I want Unit-level cascades that respect existing Offer values
async with client.save_session() as session:
    session.track(unit, recursive=True)

    # Set default platforms on unit
    unit.platforms = ["Google", "Meta"]

    # Cascade with override (platforms has allow_override=True)
    session.cascade_field(unit, "Platforms")

    result = await session.commit_async()
    # Offers with platforms=None: Updated to ["Google", "Meta"]
    # Offers with existing platforms: KEPT their original value
```

### UC-005: Accessing Business Hours

```python
# As a developer, I want to access address and hours with sibling navigation
async with client.save_session() as session:
    session.track(business, prefetch_holders=True)

    address = business.address  # via location_holder
    hours = business.hours      # sibling of address

    # Access hours fields
    print(f"Monday: {hours.monday}")
    print(f"Open today: {hours.is_open('monday')}")

    # Navigate between siblings
    assert hours.address is address
    assert address.hours is hours

    # Bulk set hours
    hours.set_weekday_hours("9:00 AM - 5:00 PM")
    hours.set_weekend_hours("Closed")
```

---

## Assumptions

| # | Assumption | Basis |
|---|------------|-------|
| 1 | Task model is designed for subclassing | Confirmed in discovery; Pydantic v2 with extra="ignore" |
| 2 | CustomFieldAccessor already provides change tracking | Existing implementation; uses _modifications dict |
| 3 | Custom field GIDs vary between environments | Will resolve by name at runtime (existing pattern) |
| 4 | Single-location business model | LocationHolder contains one Address + one Hours (siblings) |
| 5 | Holder tasks named consistently | "Contacts", "Units", "Location" etc. with emoji fallback |
| 6 | 127 fields are comprehensive | Per custom-fields-glossary.md in skills documentation |
| 7 | Existing ~125 persistence tests must pass | Backward compatibility requirement |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Task model (task.py) | SDK Core | Available |
| CustomFieldAccessor (custom_field_accessor.py) | SDK Core | Available |
| SaveSession (session.py) | SDK Core | Available, requires extension |
| BatchClient | SDK Core | Available |
| Pydantic v2 | External | Available |
| nameparser | External | To be added to dependencies |

---

## Open Questions

| # | Question | Owner | Due Date | Resolution |
|---|----------|-------|----------|------------|
| 1 | Should Business.from_gid() be async factory method or classmethod? | Architect | Session 3 | TBD |
| 2 | How should holder children be sorted (by name, created_at, custom field)? | Architect | Session 3 | TBD |
| 3 | Should cascade errors fail the entire commit or be partial? | Architect | Session 3 | TBD |
| 4 | CascadeReconciler: implement in Phase 1 or defer? | Architect | Session 3 | Deferred (Out of Scope) |
| 5 | Process model: minimal base or forward-compatible for Phase 2 subclasses? | Architect | Session 3 | TBD |

---

## Implementation Phases

Based on discovery document recommendations:

| Phase | Components | Dependencies |
|-------|------------|--------------|
| **P1** | Business, ContactHolder, Contact models + 19+19 fields | Task model |
| **P2** | UnitHolder, Unit, OfferHolder, Offer, ProcessHolder, Process + 31+39 fields | P1 |
| **P3** | LocationHolder, Address, Hours + cascade infrastructure + 12+7 fields | P1, P2 |

---

## Package Structure

```
src/autom8_asana/
+-- models/
|   +-- business/
|   |   +-- __init__.py          # Public exports
|   |   +-- base.py              # BusinessTask mixin with HOLDER_KEY_MAP support
|   |   +-- business.py          # Business(Task)
|   |   +-- contact.py           # Contact(Task), ContactHolder(Task)
|   |   +-- unit.py              # Unit(Task), UnitHolder(Task)
|   |   +-- offer.py             # Offer(Task), OfferHolder(Task)
|   |   +-- process.py           # Process(Task), ProcessHolder(Task)
|   |   +-- location.py          # Address(Task), Hours(Task), LocationHolder(Task)
|   |   +-- fields.py            # CascadingFieldDef, InheritedFieldDef, field enums
|   +-- task.py                  # Existing (unchanged)
+-- persistence/
|   +-- session.py               # Extend with prefetch/recursive/cascade
|   +-- cascade.py               # NEW: CascadeOperation, CascadeExecutor
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-11 | Requirements Analyst | Initial draft |
| 1.1 | 2025-12-25 | Tech Writer | Updated status to Implemented; added Implementation Summary documenting completed work in src/autom8_asana/models/business/ and persistence/; noted deviations and enhancements beyond original scope |

---

## Appendices

### Appendix A: Field Count Summary by Entity

| Entity | Text | Number | Enum | Multi-enum | People | Date | Total |
|--------|------|--------|------|------------|--------|------|-------|
| Business | 13 | 1 | 4 | 0 | 1 | 0 | 19 |
| Contact | 15 | 0 | 4 | 0 | 0 | 0 | 19 |
| Unit | 17 | 10 | 3 | 4 | 0 | 0 | 31 |
| Address | 11 | 2 | 0 | 0 | 0 | 0 | 12 |
| Hours | 7 | 0 | 0 | 0 | 0 | 0 | 7 |
| Offer | 25 | 7 | 5 | 2 | 1 | 0 | 39 |
| **Total** | **88** | **20** | **16** | **6** | **2** | **0** | **127** |

### Appendix B: Cascading Field Definitions

| Source | Field | Targets | Allow Override |
|--------|-------|---------|----------------|
| Business | Office Phone | Unit, Offer, Process, Contact | NO (default) |
| Business | Company ID | All descendants | NO (default) |
| Business | Business Name | Unit, Offer | NO (default) |
| Business | Primary Contact Phone | Unit, Offer, Process | NO (default) |
| Unit | Platforms | Offer | YES (explicit) |
| Unit | Vertical | Offer, Process | NO (default) |
| Unit | Booking Type | Offer | NO (default) |

### Appendix C: Holder Types and Children

| Holder | Parent | Children Type | Cardinality |
|--------|--------|---------------|-------------|
| ContactHolder | Business | Contact | 0..n |
| UnitHolder | Business | Unit | 0..n |
| LocationHolder | Business | Address, Hours | 1, 1 (siblings) |
| OfferHolder | Unit | Offer | 0..n |
| ProcessHolder | Unit | Process | 0..n |
| DNAHolder | Business | Task (stub) | 0..n |
| ReconciliationsHolder | Business | Task (stub) | 0..n |
| AssetEditHolder | Business | Task (stub) | 0..n |
| VideographyHolder | Business | Task (stub) | 0..n |

---

## Quality Gates Checklist

- [x] Problem statement is clear and compelling
- [x] Scope explicitly defines in/out
- [x] All requirements are specific and testable
- [x] Acceptance criteria defined for each requirement
- [x] Assumptions documented
- [x] No open questions blocking design (owners assigned, deferred items identified)
