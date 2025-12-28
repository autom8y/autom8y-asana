# PRD-06: Business Domain Architecture

> Consolidated PRD for business models, process pipelines, and automation.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-0010-business-model-layer, PRD-PROCESS-PIPELINE, PRD-PROCESS-PIPELINE-AMENDMENT, PRD-AUTOMATION-LAYER, PRD-PIPELINE-AUTOMATION-ENHANCEMENT
- **Related TDD**: TDD-08-business-domain
- **Implementation**: `src/autom8_asana/models/business/`, `src/autom8_asana/persistence/`

---

## Executive Summary

The Business Domain layer provides domain-specific abstractions for the autom8_asana SDK, transforming it from a low-level API wrapper into a business automation platform. This consolidated PRD covers three interconnected capabilities:

1. **Business Model Layer**: Typed entity hierarchy (Business, Contact, Unit, Offer, Process, Address, Hours) with 127 custom field accessors, holder patterns, and bidirectional navigation.

2. **Process Pipeline**: ProcessType and ProcessSection enums enabling pipeline state tracking, section-based state transitions, and typed process classification.

3. **Automation Layer**: Post-commit hooks, automation rules (including PipelineConversionRule), field seeding, and template-based process creation for automated pipeline handoffs.

---

## Problem Statement

### Business Model Challenges

The SDK provides low-level Asana API access but lacks domain-specific abstractions. Developers must:

- Manually navigate task hierarchies with no typed navigation between Business, Unit, Offer, Contact entities
- Resolve custom fields by string names with no IDE autocomplete or type safety for 127 business-specific fields
- Manually manage parent-child relationships with no holder pattern abstraction
- Implement field propagation logic with no cascading field support for data consistency
- Handle lazy loading manually with no integrated prefetch patterns

### Pipeline Challenges

Process entities exist only as hierarchy children with a stub ProcessType.GENERIC. The SDK lacks:

- Type distinction between sales, onboarding, implementation, and other process types
- Pipeline state tracking based on project section membership
- State transition helpers for moving processes between pipeline stages
- Factory patterns for creating complete entity hierarchies (BusinessSeeder)

### Automation Challenges

Pipeline automation logic must be orchestrated externally, forcing consumers to:

- Implement their own webhook handlers and boilerplate for entity creation
- Manually coordinate multi-step workflows and field seeding
- Handle edge cases like duplicate prevention, field inheritance, and section matching
- Write brittle external scripts for pipeline conversions

### Impact of Not Solving

- **Development velocity**: Each integration reimplements hierarchy navigation and field access patterns
- **Type safety**: Runtime errors from typos in field names; no IDE support
- **Data consistency**: Manual cascade propagation leads to stale field values
- **Operational burden**: Manual copying of subtasks, field re-entry, and assignee assignment for every conversion

---

## Goals and Non-Goals

### Goals

| Goal | Success Metric | Target |
|------|----------------|--------|
| Type-safe field access | Fields accessible via typed properties | 127/127 fields with IDE autocomplete |
| Hierarchy navigation | Bidirectional navigation available | All 7 entity types navigable up/down |
| Data consistency | Cascading field propagation | Business and Unit cascades execute correctly |
| API efficiency | Holder prefetch on track() | Single batch fetch per hierarchy level |
| Pipeline visibility | process.pipeline_state property | Returns state without API call |
| Easy creation | BusinessSeeder creates hierarchy | Full hierarchy in single call |
| Zero-code conversion | Template-based automation | 100% for standard conversions |
| Automation isolation | Failures don't break commits | 100% isolation |

### Non-Goals

- **Workflow orchestration logic**: Business rules for when/how to transition states belong in consumers
- **Webhook server implementation**: SDK receives events, doesn't host endpoints
- **State machine enforcement**: SDK enables transitions, does not enforce valid sequences
- **Cross-workspace automation**: Rules operate within single workspace
- **Undo/rollback mechanisms**: Automation actions are forward-only

---

## Requirements

### FR-MODEL: Entity Model Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-MODEL-001 | Business model extends Task with HOLDER_KEY_MAP defining 7 holder types | Must | Implemented |
| FR-MODEL-002 | Business has holder properties (contact_holder, unit_holder, location_holder, dna_holder, reconciliation_holder, asset_edit_holder, videography_holder) | Must | Implemented |
| FR-MODEL-003 | Business has convenience shortcuts (contacts, units, address, hours) | Should | Implemented |
| FR-MODEL-004 | Contact model with owner detection via OWNER_POSITIONS set | Must | Implemented |
| FR-MODEL-005 | Contact provides name parsing via nameparser integration | Should | Implemented |
| FR-MODEL-006 | Unit model with nested HOLDER_KEY_MAP for OfferHolder and ProcessHolder | Must | Implemented |
| FR-MODEL-007 | Unit has convenience shortcuts (offers, processes, active_offers) | Should | Implemented |
| FR-MODEL-008 | Offer model with ad status determination (has_active_ads property) | Must | Implemented |
| FR-MODEL-009 | Process model as base type for process entities | Must | Implemented |
| FR-MODEL-010 | Address model with sibling navigation to Hours | Must | Implemented |
| FR-MODEL-011 | Hours model with day-of-week field accessors and convenience methods | Must | Implemented |
| FR-MODEL-012 | All models use Pydantic v2 with PrivateAttr for cached references | Must | Implemented |

### FR-HOLDER: Holder Pattern Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-HOLDER-001 | ContactHolder with _contacts PrivateAttr and typed contacts property | Must | Implemented |
| FR-HOLDER-002 | ContactHolder provides owner property returning Contact with is_owner=True | Must | Implemented |
| FR-HOLDER-003 | UnitHolder with _units PrivateAttr and typed units property | Must | Implemented |
| FR-HOLDER-004 | OfferHolder with _offers PrivateAttr, offers property, and active_offers filter | Must | Implemented |
| FR-HOLDER-005 | ProcessHolder with _children PrivateAttr for Process entities | Must | Implemented |
| FR-HOLDER-006 | LocationHolder with _address and _hours PrivateAttrs for sibling entities | Must | Implemented |
| FR-HOLDER-007 | Stub holders (DNA, Reconciliation, AssetEdit, Videography) return as plain Task | Must | Implemented |
| FR-HOLDER-008 | All holders implement _populate_children(subtasks: list[Task]) method | Must | Implemented |
| FR-HOLDER-009 | Holder detection uses name match first, emoji fallback second | Must | Implemented |

### FR-FIELD: Custom Field Accessor Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-FIELD-001 | Each model class has inner Fields class with field name constants | Must | Implemented |
| FR-FIELD-002 | Text fields expose typed str property with getter/setter | Must | Implemented |
| FR-FIELD-003 | Number fields expose typed Decimal property with conversion | Must | Implemented |
| FR-FIELD-004 | Enum fields expose typed str property extracting name from dict | Must | Implemented |
| FR-FIELD-005 | Multi-enum fields expose typed list[str] property | Must | Implemented |
| FR-FIELD-006 | People fields expose typed list[dict] property | Must | Implemented |
| FR-FIELD-007 | Business model implements all 19 custom field accessors | Must | Implemented |
| FR-FIELD-008 | Contact model implements all 19 custom field accessors | Must | Implemented |
| FR-FIELD-009 | Unit model implements all 31 custom field accessors | Must | Implemented |
| FR-FIELD-010 | Address model implements all 12 custom field accessors | Must | Implemented |
| FR-FIELD-011 | Hours model implements all 7 custom field accessors | Must | Implemented |
| FR-FIELD-012 | Offer model implements all 39 custom field accessors | Must | Implemented |
| FR-FIELD-013 | Field setters trigger change tracking via CustomFieldAccessor.set() | Must | Implemented |

### FR-CASCADE: Cascading Field Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-CASCADE-001 | CascadingFieldDef supports multi-level cascading with allow_override parameter | Must | Implemented |
| FR-CASCADE-002 | Business declares CascadingFields (OFFICE_PHONE, COMPANY_ID, BUSINESS_NAME, PRIMARY_CONTACT_PHONE) | Must | Implemented |
| FR-CASCADE-003 | Unit declares CascadingFields (PLATFORMS, VERTICAL, BOOKING_TYPE) | Must | Implemented |
| FR-CASCADE-004 | CascadingFieldDef.target_types=None means cascade to all descendants | Must | Implemented |
| FR-CASCADE-005 | When allow_override=False, cascade ALWAYS overwrites descendant value | Must | Implemented |
| FR-CASCADE-006 | When allow_override=True, cascade only overwrites if descendant value is None | Must | Implemented |

### FR-TYPE: ProcessType and ProcessSection Enums

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-TYPE-001 | ProcessType enum includes SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION | Must | Implemented |
| FR-TYPE-002 | ProcessType.GENERIC preserved for backward compatibility | Must | Implemented |
| FR-TYPE-003 | ProcessType values are lowercase strings (str, Enum) | Must | Implemented |
| FR-SECTION-001 | ProcessSection enum includes OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT, OTHER | Must | Implemented |
| FR-SECTION-002 | ProcessSection.from_name() matches section names case-insensitively | Must | Implemented |
| FR-SECTION-003 | ProcessSection.from_name() returns OTHER for unrecognized names | Must | Implemented |

### FR-STATE: Pipeline State Access

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-STATE-001 | Process.pipeline_state property returns ProcessSection or None | Must | Implemented |
| FR-STATE-002 | pipeline_state extracts state from cached memberships without API call | Must | Implemented |
| FR-STATE-003 | pipeline_state uses canonical project membership (not separate registry) | Must | Corrected |
| FR-STATE-004 | pipeline_state returns None if process not in canonical project | Must | Implemented |
| FR-STATE-005 | process_type property returns detected ProcessType from canonical project | Must | Implemented |

### FR-TRANS: State Transition Helpers

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-TRANS-001 | Process.move_to_state() queues move_to_section action | Must | Implemented |
| FR-TRANS-002 | move_to_state looks up section GID in canonical project | Must | Implemented |
| FR-TRANS-003 | move_to_state raises ValueError if process not in project | Must | Implemented |
| FR-TRANS-004 | move_to_state raises ValueError if section not found | Must | Implemented |
| FR-TRANS-005 | Section GID lookup uses cached data or lazy fetch | Should | Implemented |

### FR-SEED: BusinessSeeder Factory

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-SEED-001 | BusinessSeeder.seed_async() creates Business entity if not found | Must | Implemented |
| FR-SEED-002 | BusinessSeeder uses three-tier matching: exact company_id, composite Fellegi-Sunter matching, or create new | Must | Implemented |
| FR-SEED-003 | BusinessSeeder creates Unit under Business if not exists | Must | Implemented |
| FR-SEED-004 | BusinessSeeder creates ProcessHolder under Unit if not exists | Must | Implemented |
| FR-SEED-005 | BusinessSeeder creates Process in ProcessHolder | Must | Implemented |
| FR-SEED-006 | BusinessSeeder returns SeederResult with all created/found entities | Must | Implemented |
| FR-SEED-007 | BusinessSeeder uses SaveSession for all operations | Must | Implemented |
| FR-SEED-008 | BusinessSeeder is async-first with optional sync wrapper | Must | Implemented |
| FR-SEED-009 | BusinessSeeder accepts optional Contact data to seed | Should | Implemented |
| FR-SEED-010 | BusinessSeeder is idempotent for same input | Must | Implemented |

### FR-M: Composite Matching Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-M-001 | MatchingEngine uses Fellegi-Sunter log-odds model for probabilistic matching | Must | Implemented |
| FR-M-002 | Composite field comparison across email, phone, name, domain, address | Must | Implemented |
| FR-M-003 | Normalizers transform input fields to canonical form before comparison | Must | Implemented |
| FR-M-004 | Blocking rules reduce candidate set for O(n) performance | Must | Implemented |
| FR-M-005 | Configuration via SEEDER_* environment variables | Must | Implemented |
| FR-M-006 | Term frequency adjustment for common value discrimination | Should | Implemented |
| FR-M-007 | Fuzzy matching with configurable Jaro-Winkler thresholds | Must | Implemented |
| FR-M-008 | Match result includes field-level comparison detail | Must | Implemented |
| FR-M-009 | Graceful degradation on search failures | Must | Implemented |
| FR-M-010 | Three-tier matching: exact company_id, composite matching, create new | Must | Implemented |
| FR-M-011 | Audit logging for match decisions | Should | Implemented |
| FR-M-012 | 12-factor configuration via pydantic-settings | Must | Implemented |

### FR-AUTO: Automation Engine Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-AUTO-001 | AutomationEngine evaluates rules after SaveSession commit | Must | Draft |
| FR-AUTO-002 | Post-commit hooks receive full SaveResult | Must | Draft |
| FR-AUTO-003 | PipelineConversionRule triggers when Process section changes to CONVERTED | Must | Draft |
| FR-AUTO-004 | Template discovery finds templates using fuzzy section matching | Must | Draft |
| FR-AUTO-005 | Field seeding populates new Process from Business/Unit cascade | Must | Draft |
| FR-AUTO-006 | AutomationConfig added to AsanaConfig | Must | Draft |
| FR-AUTO-007 | AutomationResult included in SaveResult | Must | Draft |
| FR-AUTO-008 | Rule registry allows custom automation rules | Should | Draft |
| FR-AUTO-009 | Max cascade depth prevents circular trigger chains | Should | Draft |
| FR-AUTO-010 | Visited set prevents same entity triggering same rule twice | Should | Draft |

### FR-ENHANCE: Pipeline Enhancement Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-DUP-001 | TasksClient provides duplicate_async() wrapping Asana duplicate endpoint | Must | Gap |
| FR-DUP-002 | duplicate_async() accepts include parameter for attributes to copy | Must | Gap |
| FR-DUP-003 | duplicate_async() supports subtasks in include parameter | Must | Gap |
| FR-WAIT-001 | SubtaskWaiter utility polls for subtask creation completion | Must | Gap |
| FR-WAIT-002 | Wait timeout configurable with 2.0 second default | Must | Gap |
| FR-SEED-W-001 | FieldSeeder.write_fields_async() persists seeded values to API | Must | Gap |
| FR-HIER-001 | New Process set as subtask of ProcessHolder using set_parent() | Must | Planned |
| FR-HIER-002 | New Process inserted after source Process in ProcessHolder | Must | Planned |
| FR-ASSIGN-001 | New Process assignee determined from rep field (Unit.rep with Business.rep fallback) | Must | Planned |
| FR-COMMENT-001 | New Process receives onboarding comment with conversion context | Must | Planned |
| FR-ERR-001 | Each enhancement step wrapped with graceful degradation | Must | Planned |

---

## Non-Functional Requirements

| ID | Requirement | Target | Status |
|----|-------------|--------|--------|
| NFR-001 | Type safety - mypy passes with zero errors | Zero errors | Verified |
| NFR-002 | Test coverage on business model code | >80% line coverage | Verified |
| NFR-003 | API efficiency - holder prefetch uses single batch call | Single batch | Verified |
| NFR-004 | Cascade performance | <5s for 100 descendants | Verified |
| NFR-005 | Memory efficiency - no leaks from circular refs | Weak refs/invalidation | Verified |
| NFR-006 | Backward compatibility | Existing tests pass | Verified |
| NFR-007 | pipeline_state access latency | <1ms (in-memory) | Verified |
| NFR-008 | process_type detection latency | <1ms (dict lookup) | Verified |
| NFR-009 | BusinessSeeder.seed_async() latency | <500ms dev, <200ms prod | Verified |
| NFR-010 | Automation evaluation latency | <100ms per rule | Draft |
| NFR-011 | Automation failure isolation | 100% isolation | Draft |
| NFR-012 | Full conversion time | <3.0s end-to-end | Planned |

---

## User Stories

### UC-001: Navigating Business Hierarchy

```python
# Navigate with typed properties and prefetch for efficiency
async with client.save_session() as session:
    session.track(business, prefetch_holders=True)

    # Downward navigation with type safety
    for contact in business.contacts:
        print(f"Contact: {contact.full_name}, Owner: {contact.is_owner}")

    for unit in business.units:
        for offer in unit.offers:
            if offer.has_active_ads:
                print(f"Active: {offer.name}, Platform: {offer.platforms}")

    # Upward navigation
    offer = business.units[0].offers[0]
    assert offer.unit is business.units[0]
    assert offer.business is business
```

### UC-002: Accessing Typed Custom Fields

```python
# IDE autocomplete and type safety for custom fields
unit = business.units[0]

# IDE shows available fields
print(unit.mrr)        # Decimal | None
print(unit.vertical)   # str | None (extracted from enum dict)
print(unit.platforms)  # list[str] (extracted from multi-enum)

# Setters trigger change tracking
unit.mrr = Decimal("5000.00")
unit.vertical = "Legal"
assert unit.get_custom_fields().has_changes()
```

### UC-003: Cascading Field Updates

```python
# Propagate field values to descendants efficiently
async with client.save_session() as session:
    session.track(business, recursive=True)

    business.office_phone = "555-9999"
    session.cascade_field(business, "Office Phone")

    result = await session.commit_async()
    # All Units, Offers, Processes now have office_phone = "555-9999"
```

### UC-004: Query Pipeline State

```python
# Access pipeline state without API call
process = await client.tasks.get_async(process_gid)

# Property reads from cached memberships
state = process.pipeline_state  # ProcessSection.ACTIVE
ptype = process.process_type    # ProcessType.SALES

# Filter by state for dashboard
active_processes = [p for p in processes if p.pipeline_state == ProcessSection.ACTIVE]
```

### UC-005: Pipeline State Transition

```python
# Move process through pipeline stages
async with client.save_session() as session:
    session.track(process)
    process.move_to_state(session, ProcessSection.CONVERTED)
    result = await session.commit_async()
```

### UC-006: Create Business Hierarchy

```python
# Create complete hierarchy from external trigger (Calendly, form, etc.)
seeder = BusinessSeeder(client)
result = await seeder.seed_async(
    business_data=BusinessData(name="Acme Corp", company_id="ACME-001"),
    process_type=ProcessType.SALES,
)

# Access all created entities
print(result.business.gid)
print(result.unit.gid)
print(result.process_holder.gid)
print(result.process.gid)
```

### UC-007: Sales to Onboarding Conversion (Automation)

**Flow**:
1. User moves Sales Process to "Converted" section
2. System triggers PipelineConversionRule on commit
3. Rule finds "Onboarding Template" in Onboarding project
4. Rule duplicates template with all subtasks
5. Rule waits for subtasks to be fully created
6. Rule places new Process under ProcessHolder
7. Rule writes seeded fields (Contact Phone, Vertical, etc.)
8. Rule sets assignee from Unit.rep
9. Rule adds onboarding comment with source context

**Outcome**: Onboarding Process exists with complete checklist, correct hierarchy, populated fields, assigned owner, and audit trail.

### UC-008: Composite Matching User Stories

The following user stories describe the personas and use cases for the composite matching capability:

| Persona | Story | Acceptance Criteria |
|---------|-------|---------------------|
| **Pipeline Operator** (Webhook Handler) | As a pipeline operator, I need to detect duplicate businesses regardless of data source, so that webhook payloads from Calendly, forms, and APIs all resolve to the same Business entity. | Given a webhook payload with business data, when BusinessSeeder processes the request, then it matches against existing businesses using composite field comparison. |
| **Data Steward** (Quality Assurance) | As a data steward, I require multiple corroborating fields to prevent false matches, so that "Smith LLC" in Chicago is not incorrectly merged with "Smith LLC" in New York. | Given two businesses with the same name but different addresses, when the matching engine evaluates them, then the match score falls below the threshold and they remain separate. |
| **Sales Representative** | As a sales representative, I want all interactions consolidated under one business record, so that I see the complete history when preparing for a call. | Given a new lead with email and phone matching an existing business, when the seeder runs, then the lead is associated with the existing business rather than creating a duplicate. |
| **Operations Manager** | As an operations manager, I need to reduce time spent manually merging duplicate records, so that my team focuses on revenue-generating activities. | Given the matching engine is enabled, when duplicates would have been created, then the system prevents them automatically with no manual intervention required. |
| **DevOps Engineer** | As a DevOps engineer, I must configure all matching thresholds via environment variables, so that I can tune behavior without code changes. | Given SEEDER_* environment variables are set, when the matching engine initializes, then it uses those values for thresholds, weights, and blocking rules. |
| **Finance Analyst** | As a finance analyst, I need accurate business counts without duplicate inflation, so that MRR and pipeline reports reflect reality. | Given the matching engine prevents duplicates, when I run a business count report, then the count accurately represents unique businesses. |
| **Customer Success Manager** | As a customer success manager, I want to see all contacts at a company in one place, so that I know who to reach out to for renewals. | Given contacts are correctly associated with matched businesses, when I view a business record, then all related contacts appear regardless of data source. |
| **API Integration Developer** | As an API integration developer, I need a simple boolean response (matched/created), so that I can log outcomes without parsing complex structures. | Given a seeder API call, when it completes, then the response includes a clear matched vs created indicator and the business GID. |
| **Security Auditor** | As a security auditor, I require match decisions logged without PII exposure, so that I can trace matching logic during compliance reviews. | Given matching occurs, when I review audit logs, then I see field comparison weights and scores but not raw PII values. |
| **Marketing Campaign Manager** | As a marketing campaign manager, I need process creation to be idempotent based on UTM fields, so that the same ad click does not create duplicate processes. | Given a process creation request with UTM parameters, when the request is repeated, then no duplicate process is created. |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Field accessor coverage | 127/127 fields | IDE autocomplete verification |
| Entity type coverage | 7/7 types navigable | Bidirectional navigation tests |
| Type safety | Zero mypy errors | `mypy src/autom8_asana/models/business/` |
| Test coverage | >80% line coverage | pytest-cov report |
| Pipeline state accuracy | 100% correct | Integration tests with live Asana |
| BusinessSeeder idempotency | 100% | Same input produces same result |
| Subtask duplication rate | 100% | Template subtasks present on new Process |
| Field propagation rate | 100% | Seeded fields written to API |
| Assignee assignment rate | 90%+ | New Process has assignee from rep |
| Graceful degradation | 100% | No conversion failures from enhancement errors |

---

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Task model (task.py) | SDK Core | Available |
| CustomFieldAccessor | SDK Core | Available |
| SaveSession | SDK Core | Available (extended) |
| BatchClient | SDK Core | Available |
| Pydantic v2 | External | Available |
| nameparser | External | Available |
| ProjectTypeRegistry | SDK Core | Available |
| WorkspaceProjectRegistry | SDK Core | Available |
| set_parent() with insert_after | SDK Core | Available |
| create_comment_async() | SDK Core | Available |
| duplicate_async() | SDK Core | Gap - Must implement |
| SubtaskWaiter | SDK Core | Gap - Must implement |
| FieldSeeder.write_fields_async() | SDK Core | Gap - Must implement |

---

## Architectural Corrections

### ProcessProjectRegistry Removal

The original PRD-PROCESS-PIPELINE assumed pipeline projects were separate from canonical entity projects. This was incorrect:

- **Incorrect model**: Process in hierarchy AND separate "pipeline project"
- **Correct model**: Canonical project IS the pipeline; sections represent pipeline states

**Impact**:
- ProcessProjectRegistry was never implemented (superseded by ADR-0101)
- add_to_pipeline() method removed
- Detection uses WorkspaceProjectRegistry for dynamic discovery
- pipeline_state reads from canonical project membership

See ADR-0101-process-pipeline-correction for full details.

---

## Appendices

### Appendix A: Field Count by Entity

| Entity | Text | Number | Enum | Multi-enum | People | Total |
|--------|------|--------|------|------------|--------|-------|
| Business | 13 | 1 | 4 | 0 | 1 | 19 |
| Contact | 15 | 0 | 4 | 0 | 0 | 19 |
| Unit | 17 | 10 | 3 | 4 | 0 | 31 |
| Address | 11 | 2 | 0 | 0 | 0 | 12 |
| Hours | 7 | 0 | 0 | 0 | 0 | 7 |
| Offer | 25 | 7 | 5 | 2 | 1 | 39 |
| **Total** | **88** | **20** | **16** | **6** | **2** | **127** |

### Appendix B: Cascading Field Definitions

| Source | Field | Targets | Allow Override |
|--------|-------|---------|----------------|
| Business | Office Phone | Unit, Offer, Process, Contact | NO |
| Business | Company ID | All descendants | NO |
| Business | Business Name | Unit, Offer | NO |
| Business | Primary Contact Phone | Unit, Offer, Process | NO |
| Unit | Platforms | Offer | YES |
| Unit | Vertical | Offer, Process | NO |
| Unit | Booking Type | Offer | NO |

### Appendix C: Holder Types and Children

| Holder | Parent | Children Type | Cardinality |
|--------|--------|---------------|-------------|
| ContactHolder | Business | Contact | 0..n |
| UnitHolder | Business | Unit | 0..n |
| LocationHolder | Business | Address, Hours | 1, 1 (siblings) |
| OfferHolder | Unit | Offer | 0..n |
| ProcessHolder | Unit | Process | 0..n |
| DNAHolder | Business | Task (stub) | 0..n |
| ReconciliationHolder | Business | Task (stub) | 0..n |
| AssetEditHolder | Business | Task (stub) | 0..n |
| VideographyHolder | Business | Task (stub) | 0..n |

### Appendix D: Package Structure

```
src/autom8_asana/
+-- models/
|   +-- business/
|   |   +-- __init__.py          # Public exports
|   |   +-- base.py              # BusinessTask mixin
|   |   +-- business.py          # Business(Task)
|   |   +-- contact.py           # Contact, ContactHolder
|   |   +-- unit.py              # Unit, UnitHolder
|   |   +-- offer.py             # Offer, OfferHolder
|   |   +-- process.py           # Process, ProcessHolder, ProcessType, ProcessSection
|   |   +-- location.py          # Address, Hours, LocationHolder
|   |   +-- fields.py            # CascadingFieldDef, InheritedFieldDef
|   |   +-- descriptors.py       # TextField, EnumField, NumberField, etc.
|   |   +-- mixins.py            # SharedCascadingFieldsMixin, FinancialFieldsMixin
|   |   +-- detection/           # 4-tier entity type detection
|   |   +-- registry.py          # Entity type registration
|   |   +-- hydration.py         # Efficient entity conversion
|   |   +-- holder_factory.py    # HolderFactory pattern
|   |   +-- seeder/              # BusinessSeeder and matching
|   |   |   +-- __init__.py      # Public exports
|   |   |   +-- seeder.py        # BusinessSeeder orchestration
|   |   |   +-- matching.py      # MatchingEngine, Fellegi-Sunter implementation
|   |   |   +-- normalizers.py   # Field normalization (email, phone, name, domain)
|   |   |   +-- config.py        # SeederConfig with pydantic-settings
|   |   |   +-- types.py         # MatchResult, FieldComparison, BusinessData
|   +-- task.py                  # Base Task model
+-- persistence/
|   +-- session.py               # SaveSession with prefetch/recursive/cascade
|   +-- cascade.py               # CascadeOperation, CascadeExecutor
+-- automation/                  # Future: AutomationEngine, rules
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from 5 source PRDs |
| 1.1 | 2025-12-28 | Tech Writer | Added FR-M composite matching requirements, updated FR-SEED-002 for three-tier matching, added UC-008 user stories for 10 personas, added seeder module to Appendix D |
