# Architectural Analysis: Process Entities as Pipeline Events

> **Status**: Research Complete
> **Date**: 2025-12-17
> **Author**: Architect Agent
> **Purpose**: Capture business logic for Process entities and identify gaps between current SDK and required functionality

---

## Executive Summary

Process entities represent **workflow events** (not dimensions) that track pipeline stages like Outreach, Sales, Onboarding, Implementation, Retention, and Reactivation. They enable sales teams to operate within Asana while maintaining pipeline orientation across teams.

**Key Architectural Insight**: Processes are fundamentally different from other business entities (Contact, Unit, Offer) because they:
1. Are **event-oriented** rather than dimensional
2. Use **section membership** as primary state indicator (state machine pattern)
3. Have **dedicated Process Projects** with standardized structure
4. Are the **integration point** for external systems (Calendly, webhooks, etc.)

---

## Table of Contents

1. [Current SDK Implementation](#1-current-sdk-implementation)
2. [Business Context: Pipeline Events](#2-business-context-pipeline-events)
3. [Process Project Pattern](#3-process-project-pattern)
4. [Integration Pattern Analysis](#4-integration-pattern-analysis)
5. [Architectural Gap Analysis](#5-architectural-gap-analysis)
6. [New Abstractions Required](#6-new-abstractions-required)
7. [SDK Pattern Mapping](#7-sdk-pattern-mapping)
8. [Recommendations](#8-recommendations)

---

## 1. Current SDK Implementation

### 1.1 Process Entity (`/src/autom8_asana/models/business/process.py`)

**File Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py`

```
Lines 67-189: class Process(BusinessEntity)
Lines 190-266: class ProcessHolder(Task, HolderMixin["Process"])
Lines 35-65: class ProcessType(str, Enum)
```

**Current State**:
- Process extends `BusinessEntity` with 8 custom field descriptors (lines 146-163)
- ProcessHolder follows standard holder pattern (lines 190-266)
- ProcessType enum is stub with only `GENERIC` value (lines 35-65)
- Forward-compatible comments reference Phase 2 subclasses (lines 38-64)

**Hierarchy Position** (lines 67-87):
```
Business
    +-- UnitHolder
          +-- Unit
                +-- ProcessHolder
                      +-- Process (this entity)
```

**Custom Fields** (lines 146-163):
| Field | Type | Line |
|-------|------|------|
| `started_at` | TextField | 150 |
| `process_completed_at` | TextField | 151 |
| `process_notes` | TextField | 152 |
| `status` | EnumField | 155 |
| `priority` | EnumField | 156 |
| `vertical` | EnumField | 157 |
| `process_due_date` | TextField | 160 |
| `assigned_to` | PeopleField | 163 |

**Navigation** (lines 103-140):
- `process_holder` - HolderRef descriptor (line 103)
- `unit` - Property navigating through holder (lines 107-116)
- `business` - Property navigating through unit (lines 118-131)

**Key Constraint** (lines 91-92):
```python
PRIMARY_PROJECT_GID: ClassVar[str | None] = None
```
ProcessHolder has **no dedicated project** - children of Unit hierarchy.

### 1.2 ProcessType Enum Status

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/process.py` (lines 35-65)

Currently only `GENERIC` is enabled. Phase 2 placeholders include:
- AUDIT, BUILD, CREATIVE, DELIVERY, ONBOARDING, OPTIMIZATION
- QA, REPORTING, RESEARCH, SETUP, STRATEGY, SUPPORT, TRAINING

**Missing from stakeholder list**:
- SALES, OUTREACH, IMPLEMENTATION, RETENTION, REACTIVATION

**process_type property** (lines 167-188):
- Always returns `ProcessType.GENERIC`
- Comments indicate future detection from custom field or name pattern

### 1.3 Detection System Integration

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/detection.py`

**ProcessHolder EntityTypeInfo** (lines 274-282):
```python
EntityType.PROCESS_HOLDER: EntityTypeInfo(
    entity_type=EntityType.PROCESS_HOLDER,
    name_pattern="processes",
    display_name="Processes",
    emoji="gear",
    holder_attr="_process_holder",
    child_type=EntityType.PROCESS,
    has_project=False,  # ProcessHolder has no dedicated project
)
```

**Process EntityTypeInfo** (lines 300-304):
```python
EntityType.PROCESS: EntityTypeInfo(
    entity_type=EntityType.PROCESS,
    display_name="Process",
    has_project=True,  # Process entities CAN have dedicated projects
)
```

**Critical Gap**: `has_project=True` for Process but no `PRIMARY_PROJECT_GID` defined.

---

## 2. Business Context: Pipeline Events

### 2.1 Event vs Dimension Distinction

Per stakeholder input, Processes are **events** not **dimensions**:

| Dimension Entities | Event Entities |
|-------------------|----------------|
| Business, Contact, Unit, Offer | Process |
| Describe "what exists" | Describe "what happened" |
| Relatively static | Move through pipeline stages |
| Identity-based | State-based |
| Section = category | Section = workflow state |

### 2.2 Process Types (Stakeholder-Defined)

Pipeline workflow stages:
1. **Outreach** - Initial contact
2. **Sales** - Active selling
3. **Onboarding** - New customer setup
4. **Implementation** - Service deployment
5. **Retention** - Ongoing management
6. **Reactivation** - Win-back campaigns

### 2.3 Purpose

Enables:
- Sales team to operate without Salesforce
- Pipeline orientation and task coordination
- Cross-team visibility (Sales -> Onboarding -> Implementation)
- Webhook-driven automation

---

## 3. Process Project Pattern

### 3.1 Pipeline-Oriented Sections

Each process type has a **dedicated Asana project** with standardized sections:

| Section | Purpose | State Semantics |
|---------|---------|-----------------|
| OPPORTUNITY | New leads | Initial state |
| DELAYED | Blocked/waiting | Hold state |
| ACTIVE | In progress | Working state |
| SCHEDULED | Future commitment | Scheduled state |
| CONVERTED | Success | Terminal state (positive) |
| DID NOT CONVERT | Failed | Terminal state (negative) |
| OTHER | Misc | Catch-all |

**Section = Process State**: Moving a Process to a section represents a state transition.

### 3.2 Custom Fields on Process Projects

Process projects share consistent custom fields cascaded from parent:
- `office_phone` - Inherited from Business
- `vertical` - Inherited from Business/Unit
- Other business dimensions for filtering/reporting

This enables:
- Consistent views across pipeline stages
- Field inheritance from Business hierarchy
- Relationship linking back to source entities

### 3.3 Dual Project Membership

Process entities have **dual project membership**:
1. **Implicit**: As subtask under ProcessHolder (under Unit)
2. **Explicit**: As task in Process Project (e.g., "Sales Pipeline")

This is the **ProcessProject pattern** - not currently modeled in SDK.

---

## 4. Integration Pattern Analysis

### 4.1 Calendly -> Sales Pipeline Example

External system integration flow:
```
1. Calendly booking occurs (external trigger)
2. Legacy system parses form data
3. Legacy system Googles business info (enrichment)
4. SDK creates full Business entity structure:
   - Business (root)
   - Unit (if applicable)
   - Sales Process under ProcessHolder
5. Process is assigned to sales rep
6. Due date set for scheduled call
7. Comment added with lead notes
8. Rep works lead, moves to CONVERTED section
9. Webhook fires on section change
10. Legacy system advances to Onboarding process
```

### 4.2 Section Movement as Trigger

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (lines 1121-1195)

The SDK already supports `move_to_section()`:
```python
def move_to_section(
    self,
    task: AsanaResource,
    section: AsanaResource | str,
    *,
    insert_before: str | None = None,
    insert_after: str | None = None,
) -> SaveSession:
```

**Gap**: No abstraction for "section represents state" or "section change triggers workflow".

### 4.3 Webhook Integration Point

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/webhooks.py`

The SDK supports webhook operations:
- Create webhook on resource
- Filter by action/fields
- Signature verification

**Gap**: No event parsing, no process-specific event handling.

---

## 5. Architectural Gap Analysis

### 5.1 Missing from Process Entity

| Gap | Current State | Required |
|-----|--------------|----------|
| ProcessType enum | Only GENERIC | SALES, OUTREACH, ONBOARDING, etc. |
| Process subclasses | None | SalesProcess, OnboardingProcess, etc. |
| PRIMARY_PROJECT_GID | None | Per-ProcessType project GIDs |
| Section membership | Not tracked | Required for state |
| ProcessProject relation | Not modeled | Required for dual membership |

### 5.2 Missing Abstractions

| Abstraction | Description | SDK Pattern |
|-------------|-------------|-------------|
| **ProcessProject** | Dedicated project per process type | New entity type |
| **ProcessSection** | Section as pipeline state | Enum or entity |
| **ProcessState** | State machine for process lifecycle | New pattern |
| **ProcessFactory** | Create process with entity seeding | Factory method |

### 5.3 Missing Operations

| Operation | Description | Current Support |
|-----------|-------------|-----------------|
| Create Process with dual membership | Add to ProcessHolder AND ProcessProject | Manual (two operations) |
| Advance process state | Move to section, trigger webhook | Manual |
| Seed Business structure | Create Business + Unit + Process | Manual |
| Detect process type from project | Determine SalesProcess vs OnboardingProcess | Not supported |

### 5.4 Integration Gaps

| Gap | Impact |
|-----|--------|
| No webhook event parsing | Consumers must parse raw events |
| No process transition hooks | Cannot react to state changes |
| No process creation helpers | Seeding is manual |
| No project section mapping | Cannot infer state from section |

---

## 6. New Abstractions Required

### 6.1 ProcessType Expansion

```python
class ProcessType(str, Enum):
    """Process types representing workflow stages."""

    # Sales funnel
    OUTREACH = "outreach"
    SALES = "sales"

    # Customer lifecycle
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"

    # Legacy/existing placeholders
    AUDIT = "audit"
    BUILD = "build"
    CREATIVE = "creative"
    # ... etc

    # Fallback
    GENERIC = "generic"
```

### 6.2 ProcessSection Enum (State Machine)

```python
class ProcessSection(str, Enum):
    """Standard sections in Process Projects (pipeline states)."""

    OPPORTUNITY = "opportunity"
    DELAYED = "delayed"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"
```

### 6.3 ProcessProject Model

New entity type representing process-type-specific projects:

```python
class ProcessProject:
    """Represents a dedicated Asana project for a process type.

    E.g., "Sales Pipeline" project for SALES process type.
    """

    process_type: ProcessType
    project_gid: str
    sections: dict[ProcessSection, str]  # Section name -> GID mapping
```

### 6.4 Process Enhancement

```python
class Process(BusinessEntity):
    # ... existing fields ...

    # New: Process type (not just GENERIC)
    @property
    def process_type(self) -> ProcessType:
        """Detect process type from process project membership."""

    # New: Current pipeline state from section
    @property
    def pipeline_state(self) -> ProcessSection | None:
        """Get current state from section membership."""

    # New: Process project reference
    @property
    def process_project(self) -> ProcessProject | None:
        """Get associated process project."""
```

### 6.5 Entity Seeding Pattern

Factory for Calendly-style integrations:

```python
class BusinessSeeder:
    """Seeds complete Business structures for integrations.

    Example:
        seeder = BusinessSeeder(client)
        result = await seeder.seed_async(
            business_name="Acme Corp",
            process_type=ProcessType.SALES,
            assigned_to="sales_rep_gid",
            due_date=datetime.now() + timedelta(days=1),
            notes="Lead from Calendly booking",
        )
        # Creates: Business -> Unit -> ProcessHolder -> SalesProcess
        # Adds Process to Sales Pipeline project
    """
```

---

## 7. SDK Pattern Mapping

### 7.1 Existing Patterns to Apply

| Pattern | File Reference | Application to Process |
|---------|---------------|----------------------|
| **HolderMixin** | `/src/autom8_asana/models/business/base.py` | ProcessHolder already uses |
| **DetectionResult** | `/src/autom8_asana/models/business/detection.py` | Extend for process type detection |
| **ProjectTypeRegistry** | `/src/autom8_asana/models/business/registry.py` | Register ProcessProject GIDs |
| **SaveSession.move_to_section** | `/src/autom8_asana/persistence/session.py:1121-1195` | Use for state transitions |
| **CascadingFieldDef** | `/src/autom8_asana/models/business/fields.py` | Define cascading from Business to Process |

### 7.2 Section Handling (Current SDK)

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`

SDK provides:
- `SectionsClient.get_async()` - Get section by GID
- `SectionsClient.list_for_project_async()` - List sections in project
- `SectionsClient.add_task()` - Add task to section

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/section.py`

Section model has:
- `name`, `gid`, `project` (NameGid)
- `to_dataframe()` methods

**Gap**: No semantic mapping from section name to ProcessSection enum.

### 7.3 Task Membership Pattern

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

Tasks have `memberships` attribute:
```python
memberships: list[dict[str, Any]] | None
```

Each membership contains:
- `project.gid`
- `section.gid` (if in a section)

This is the key to dual membership detection.

---

## 8. Recommendations

### 8.1 Phase 1: Foundation (Low Risk)

1. **Expand ProcessType enum**
   - Add SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION
   - Maintain GENERIC as fallback
   - Location: `/src/autom8_asana/models/business/process.py:35-65`

2. **Add ProcessSection enum**
   - Standard sections: OPPORTUNITY, DELAYED, ACTIVE, SCHEDULED, CONVERTED, DID_NOT_CONVERT
   - Location: New file or in `process.py`

3. **Implement process_type detection**
   - Detect from project membership (like entity detection Tier 1)
   - Fallback to name pattern matching
   - Location: `/src/autom8_asana/models/business/process.py:167-188`

### 8.2 Phase 2: Process Projects (Medium Risk)

1. **Create ProcessProjectRegistry**
   - Map ProcessType -> Project GID
   - Similar to ProjectTypeRegistry pattern
   - Location: New module `/src/autom8_asana/models/business/process_registry.py`

2. **Add pipeline_state property to Process**
   - Extract section from memberships
   - Map section name to ProcessSection enum
   - Return current state or None

3. **Add dual membership support**
   - Helper to add Process to both ProcessHolder and ProcessProject
   - Consider SaveSession extension

### 8.3 Phase 3: Integration (Higher Risk)

1. **BusinessSeeder factory**
   - Atomic creation of Business + hierarchy + Process
   - Supports integration patterns (Calendly, etc.)

2. **Webhook event helpers**
   - Parse section change events
   - Identify process transitions

3. **Process transition operations**
   - `advance_to_section()` helper
   - Optional webhook trigger awareness

### 8.4 Out of Scope for SDK

- Workflow orchestration logic (belongs in consumer)
- Salesforce integration specifics (consumer concern)
- Business rules for state transitions (consumer concern)

---

## Appendix A: File Reference Summary

| File | Lines | Content |
|------|-------|---------|
| `/src/autom8_asana/models/business/process.py` | 1-266 | Process, ProcessHolder, ProcessType |
| `/src/autom8_asana/models/business/detection.py` | 1-806 | EntityType, detection functions |
| `/src/autom8_asana/models/business/unit.py` | 1-535 | Unit with ProcessHolder navigation |
| `/src/autom8_asana/models/business/business.py` | 1-788 | Business root entity |
| `/src/autom8_asana/persistence/session.py` | 1-2052 | SaveSession, move_to_section |
| `/src/autom8_asana/clients/sections.py` | 1-342 | SectionsClient |
| `/src/autom8_asana/clients/webhooks.py` | 1-476 | WebhooksClient |
| `/src/autom8_asana/models/section.py` | 1-174 | Section model |
| `/src/autom8_asana/models/project.py` | 1-235 | Project model |

## Appendix B: Custom Field Summary

### Process (9 fields per REF-custom-field-catalog.md)

| Property | Field Type | Cascading? |
|----------|-----------|------------|
| status | Enum | No |
| priority | Enum | No |
| vertical | Enum | Yes (from Unit/Business) |
| process_due_date | Text | No |
| started_at | Text | No |
| process_completed_at | Text | No |
| process_notes | Text | No |
| assigned_to | People | No |

Note: `vertical` is shared across Business, Unit, Offer, and Process - key cascading field.

## Appendix C: Related ADRs

| ADR | Title | Relevance |
|-----|-------|-----------|
| ADR-0035 | Unit of Work Pattern | SaveSession for process operations |
| ADR-0042 | Action Operation Types | MOVE_TO_SECTION support |
| ADR-0054 | Cascading Custom Fields | Vertical inheritance |
| ADR-0068 | Type Detection Strategy | Process type detection basis |
| ADR-0093 | Project Type Registry | Extend for ProcessProject |
| ADR-0094 | Detection Fallback Chain | Apply to process type |

---

*End of architectural analysis.*
