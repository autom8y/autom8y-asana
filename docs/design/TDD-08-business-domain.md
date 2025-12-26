# TDD-08: Business Domain Architecture

> Consolidated TDD for process pipelines, automation, entity detection, and business model layer.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-PROCESS-PIPELINE, TDD-AUTOMATION-LAYER, TDD-DETECTION, TDD-PIPELINE-AUTOMATION-ENHANCEMENT, TDD-0027-business-model-architecture, TDD-0028-business-model-implementation
- **Related ADRs**: ADR-0015, ADR-0016, ADR-0017, ADR-0020, ADR-0021, ADR-0022, ADR-0023

---

## Overview

The Business Domain layer provides a complete model hierarchy for business entities, process pipelines, automation rules, and entity type detection. This architecture sits between SDK consumers and the core autom8_asana SDK, offering:

1. **Business Entity Hierarchy**: Task subclasses (Business, Contact, Unit, Offer, Process) with typed custom field accessors and holder navigation patterns
2. **Process Pipelines**: ProcessType and ProcessSection enums for tracking entities through workflow states via section membership
3. **Automation Layer**: Rule-based automation triggered by state changes (e.g., Sales to Onboarding conversion on CONVERTED state)
4. **Entity Detection**: Tiered detection system for determining entity types from project membership, name patterns, and structure inspection
5. **Self-Healing**: Automatic repair of entities missing expected project memberships

---

## System Context

```
+----------------------------------+
|        SDK Consumers             |
|  (Automation scripts, APIs)      |
+----------------------------------+
              |
              v
+----------------------------------+
|     Business Domain Layer        |  <-- THIS TDD
|  Business, Unit, Contact, Offer  |
|  Process, Automation, Detection  |
+----------------------------------+
              |
              v
+----------------------------------+
|       autom8_asana SDK           |
|  Task, SaveSession, BatchClient  |
+----------------------------------+
              |
              v
+----------------------------------+
|         Asana REST API           |
+----------------------------------+
```

---

## 1. Business Entity Hierarchy

### Entity Class Design

All business entities inherit from `Task`, leveraging existing SDK infrastructure for change tracking and persistence:

```
AsanaResource
    |
    +-- Task
           |
           +-- Business (root entity, 7 holder properties)
           +-- ContactHolder -> Contact[]
           +-- UnitHolder -> Unit[]
           +-- Unit -> OfferHolder, ProcessHolder
           +-- OfferHolder -> Offer[]
           +-- ProcessHolder -> Process[]
           +-- LocationHolder -> Address, Hours
```

### Holder Detection Pattern

Holders are identified by name pattern with emoji fallback:

```python
HOLDER_KEY_MAP: ClassVar[dict[str, tuple[str, str]]] = {
    "contact_holder": ("Contacts", "busts_in_silhouette"),
    "unit_holder": ("Units", "package"),
    "location_holder": ("Location", "round_pushpin"),
    "dna_holder": ("DNA", "dna"),
    "reconciliations_holder": ("Reconciliations", "abacus"),
    "asset_edit_holder": ("Asset Edit", "art"),
    "videography_holder": ("Videography", "video_camera"),
}
```

### Custom Field Type Safety

Typed property accessors delegate to `CustomFieldAccessor` for IDE support and change tracking:

```python
class Business(Task):
    class Fields:
        COMPANY_ID = "Company ID"
        BOOKING_TYPE = "Booking Type"
        MRR = "MRR"

    @property
    def company_id(self) -> str | None:
        return self.get_custom_fields().get(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

### Bidirectional Navigation

Upward references are cached with explicit invalidation for O(1) access:

```python
class Contact(Task):
    _business: Business | None = PrivateAttr(default=None)
    _contact_holder: Task | None = PrivateAttr(default=None)

    @property
    def business(self) -> Business | None:
        if self._business is None:
            self._business = self._resolve_business()
        return self._business
```

---

## 2. Process Pipeline Architecture

### ProcessType Enum

Pipeline types representing workflow stages:

| Value | Environment Variable | Purpose |
|-------|---------------------|---------|
| SALES | ASANA_PROCESS_PROJECT_SALES | Sales pipeline opportunities |
| OUTREACH | ASANA_PROCESS_PROJECT_OUTREACH | Outreach campaigns |
| ONBOARDING | ASANA_PROCESS_PROJECT_ONBOARDING | Customer onboarding |
| IMPLEMENTATION | ASANA_PROCESS_PROJECT_IMPLEMENTATION | Service implementation |
| RETENTION | ASANA_PROCESS_PROJECT_RETENTION | Customer retention |
| REACTIVATION | ASANA_PROCESS_PROJECT_REACTIVATION | Customer reactivation |
| GENERIC | (none) | Fallback for unregistered |

### ProcessSection Enum

Pipeline states represented by section membership:

| Value | Asana Section Name | Meaning |
|-------|-------------------|---------|
| OPPORTUNITY | Opportunity | Initial lead state |
| DELAYED | Delayed | Temporarily paused |
| ACTIVE | Active | Currently working |
| SCHEDULED | Scheduled | Future action planned |
| CONVERTED | Converted | Success outcome |
| DID_NOT_CONVERT | Did Not Convert | Failed outcome |
| OTHER | (any unrecognized) | Fallback for custom sections |

### State Query and Transition

```python
class Process(BusinessEntity):
    @property
    def pipeline_state(self) -> ProcessSection | None:
        """Get current state from section membership (no API call)."""
        # Extract from cached memberships via ProcessProjectRegistry

    @property
    def process_type(self) -> ProcessType:
        """Determine type from pipeline project membership."""
        # Returns GENERIC if not in registered pipeline

    def add_to_pipeline(
        self,
        session: SaveSession,
        process_type: ProcessType,
        section: ProcessSection | None = None,
    ) -> SaveSession:
        """Queue addition to pipeline project."""

    def move_to_state(
        self,
        session: SaveSession,
        target_state: ProcessSection,
    ) -> SaveSession:
        """Queue state transition via section move."""
```

### Dual Membership Model

Processes maintain membership in both:
1. **Hierarchy project**: Business -> Unit -> ProcessHolder -> Process
2. **Pipeline project**: Sales Pipeline, Onboarding Pipeline, etc.

This preserves navigation while enabling pipeline tracking.

---

## 3. Automation Layer

### Architecture Overview

```
SaveSession.commit_async()
        |
        v (Phase 5: Automation)
+-----------------------------------+
|       AutomationEngine            |
|  - evaluate_async(save_result)    |
|  - register(rule)                 |
+-----------------------------------+
        |
        v
+-----------------------------------+
|    Registered Rules               |
|  - PipelineConversionRule         |
|  - Custom rules via Protocol      |
+-----------------------------------+
        |
        v
+-----------------------------------+
|    AutomationResult               |
|  - rule_id, success, error        |
|  - entities_created/updated       |
+-----------------------------------+
```

### AutomationRule Protocol

```python
@runtime_checkable
class AutomationRule(Protocol):
    id: str
    name: str
    trigger: TriggerCondition

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool: ...

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult: ...
```

### TriggerCondition

Declarative trigger specification:

```python
TriggerCondition(
    entity_type="Process",
    event="section_changed",
    filters={"section": "converted", "process_type": "sales"}
)
```

### PipelineConversionRule

Built-in Sales to Onboarding conversion:

1. Triggers when Process moves to CONVERTED section
2. Discovers template in target pipeline project
3. Duplicates template with subtasks
4. Seeds fields from hierarchy cascade and carry-through
5. Places in ProcessHolder with correct positioning
6. Assigns from rep field cascade
7. Adds onboarding comment

### Loop Prevention

Two-layer protection via AutomationContext:
- **Depth tracking**: `max_cascade_depth` (default: 5)
- **Visited set**: `(entity_gid, rule_id)` pairs prevent same trigger twice

### Failure Isolation

Per NFR-003: Automation failures do not fail primary commits. All exceptions are captured in `AutomationResult.error`.

---

## 4. Entity Detection System

### Tiered Detection Strategy

```
detect_entity_type(task)
        |
        v
+-----------------------------------+
| TIER 1: Project Membership        |
|   O(1) registry lookup, no API    |
+-----------------------------------+
        | (if not found)
        v
+-----------------------------------+
| TIER 2: Name Pattern Matching     |
|   String ops, no API              |
+-----------------------------------+
        | (if not matched)
        v
+-----------------------------------+
| TIER 3: Parent Type Inference     |
|   Logic only, no API              |
+-----------------------------------+
        | (if cannot infer)
        v
+-----------------------------------+
| TIER 4: Structure Inspection      |
|   Async, requires API (optional)  |
+-----------------------------------+
        | (if still unknown)
        v
+-----------------------------------+
| TIER 5: UNKNOWN Fallback          |
|   Returns needs_healing=True      |
+-----------------------------------+
```

### ProjectTypeRegistry

Singleton mapping project GIDs to EntityType:

```python
class ProjectTypeRegistry:
    def register(self, project_gid: str, entity_type: EntityType) -> None
    def lookup(self, project_gid: str) -> EntityType | None
    def get_primary_gid(self, entity_type: EntityType) -> str | None
```

Auto-populated via `BusinessEntity.__init_subclass__` with environment variable overrides.

### DetectionResult

```python
@dataclass(frozen=True, slots=True)
class DetectionResult:
    entity_type: EntityType
    tier_used: int  # 1-5
    needs_healing: bool
    expected_project_gid: str | None

    @property
    def is_deterministic(self) -> bool:
        return self.tier_used == 1
```

### Self-Healing Integration

When `auto_heal=True` on SaveSession:

1. Detection returns `needs_healing=True` if detected via Tier 2+
2. SaveSession queues `HealingOperation` with expected project GID
3. After CRUD operations, healing executes via `add_to_project` action
4. Results reported in `SaveResult.healed_entities` and `SaveResult.healing_failures`

---

## 5. Cascading and Inherited Fields

### CascadingFieldDef

Fields that propagate from parent to descendants:

```python
class CascadingFieldDef:
    name: str
    target_types: set[type] | None  # None = all descendants
    allow_override: bool = False    # Default: parent ALWAYS wins
    source_field: str | None = None
    transform: Callable | None = None
```

**Override Behavior**:
- `allow_override=False` (default): Parent value always overwrites
- `allow_override=True`: Only cascade if descendant value is null

### InheritedFieldDef

Fields resolved from nearest ancestor:

```python
class InheritedFieldDef:
    name: str
    inherit_from: list[str]  # e.g., ["Unit", "Business"]
    allow_override: bool
    override_flag_field: str
```

### SaveSession.cascade_field()

```python
session.cascade_field(business, "Office Phone")
# Queues cascade operation, executed after CRUD in commit_async()
```

### Field Declarations

| Entity | Cascading Fields | Override? |
|--------|-----------------|-----------|
| Business | Office Phone, Company ID, Business Name | NO (default) |
| Unit | Platforms, Vertical, Booking Type | Platforms=YES, others=NO |

---

## 6. BusinessSeeder Factory

Find-or-create pattern for complete hierarchy creation:

```python
class BusinessSeeder:
    async def seed_async(
        self,
        business: BusinessData,
        process: ProcessData,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """
        1. Find existing Business by company_id/name
        2. Find or create Unit under Business
        3. Find or create ProcessHolder under Unit
        4. Create Process in ProcessHolder
        5. Add Process to pipeline project
        6. Optional: Create Contact
        """
```

### SeederResult

```python
@dataclass
class SeederResult:
    business: Business
    unit: Unit
    process_holder: ProcessHolder
    process: Process
    contact: Contact | None
    created_business: bool  # True if new, False if found
    created_unit: bool
    created_process_holder: bool
```

---

## 7. Pipeline Automation Enhancement

### Task Duplication

```python
async def duplicate_async(
    self,
    task_gid: str,
    *,
    name: str,
    include: list[str] | None = None,  # ["subtasks", "notes"]
) -> Task:
    """Wrap Asana's POST /tasks/{task_gid}/duplicate."""
```

### SubtaskWaiter

Polling-based wait for subtask creation after duplication:

```python
class SubtaskWaiter:
    async def wait_for_subtasks_async(
        self,
        task_gid: str,
        expected_count: int,
        timeout: float = 2.0,
        poll_interval: float = 0.2,
    ) -> bool:
        """Poll until count matches or timeout."""
```

### FieldSeeder.write_fields_async()

```python
async def write_fields_async(
    self,
    target_task_gid: str,
    fields: dict[str, Any],
    target_project_gid: str | None = None,
) -> WriteResult:
    """Persist seeded field values via single API call."""
```

---

## Testing Strategy

### Unit Tests

| Component | Coverage Target |
|-----------|-----------------|
| ProcessType, ProcessSection enums | 100% |
| ProjectTypeRegistry | 100% |
| DetectionResult | 100% |
| CascadingFieldDef, InheritedFieldDef | 100% |
| Business model field accessors | >90% |
| AutomationRule implementations | >90% |

### Integration Tests

- Full hierarchy creation with BusinessSeeder
- Pipeline conversion flow (Sales to Onboarding)
- Cascade propagation via batch API
- Detection across all tiers
- Self-healing with SaveSession

### Performance Targets

| Operation | Target |
|-----------|--------|
| Tier 1 detection | <1ms |
| pipeline_state access | <1ms (no API) |
| process_type access | <1ms (no API) |
| Cascade to 50 descendants | <3s |
| Full pipeline conversion | <3s |

---

## Observability

### Metrics

| Metric | Description |
|--------|-------------|
| `detection.tier_used` | Distribution of which tier succeeded |
| `automation.evaluations_total` | Total rule evaluations |
| `automation.executions_total` | Executions by rule_id, success |
| `automation.execution_duration_ms` | Rule execution latency |
| `cascade.entity_count` | Entities updated per cascade |
| `healing.operations_total` | Healing operations attempted |

### Logging

```python
# Detection
logger.debug("Detected %s via project membership", entity_type.name,
             extra={"task_gid": task.gid, "project_gid": project_gid, "tier": 1})

# Automation
logger.info("Rule %s executed successfully", rule.name,
            extra={"rule_id": rule.id, "entities_created": result.entities_created})

# Cascade
logger.info("cascade: field=%s source=%s target_count=%d", field, source_gid, count)
```

### Alerting

- Alert if detection Tier 5 (UNKNOWN) exceeds 5%
- Alert if automation failures exceed 5%
- Alert if cascade partial failures exceed 10%

---

## Cross-References

### Related ADRs

| ADR | Decision |
|-----|----------|
| ADR-0015 | Process Pipeline Architecture |
| ADR-0016 | Business Entity Seeding |
| ADR-0017 | Automation Architecture |
| ADR-0020 | Entity Type Detection Architecture |
| ADR-0021 | Detection Pattern Matching |
| ADR-0022 | Self-Healing Resolution |
| ADR-0023 | Detection Package Structure |

### Related TDDs

| TDD | Relationship |
|-----|--------------|
| TDD-04 | SaveSession integration for cascades and healing |
| TDD-03 | TasksClient for duplicate_async, subtasks_async |

### Source Documents (Archived)

The following TDDs were consolidated into this document:
- TDD-PROCESS-PIPELINE (Partially Superseded)
- TDD-AUTOMATION-LAYER
- TDD-DETECTION
- TDD-PIPELINE-AUTOMATION-ENHANCEMENT
- TDD-0027-business-model-architecture
- TDD-0028-business-model-implementation

---

## Package Structure

```
src/autom8_asana/
+-- models/
|   +-- business/
|   |   +-- __init__.py            # Public exports
|   |   +-- base.py                # HolderMixin, BusinessEntity base
|   |   +-- fields.py              # CascadingFieldDef, InheritedFieldDef
|   |   +-- business.py            # Business model + holders
|   |   +-- contact.py             # Contact, ContactHolder
|   |   +-- unit.py                # Unit, UnitHolder
|   |   +-- offer.py               # Offer, OfferHolder
|   |   +-- process.py             # Process, ProcessHolder, ProcessType, ProcessSection
|   |   +-- location.py            # Address, Hours, LocationHolder
|   |   +-- registry.py            # ProjectTypeRegistry
|   |   +-- detection.py           # detect_entity_type(), DetectionResult
|   |   +-- seeder.py              # BusinessSeeder, SeederResult
|
+-- automation/
|   +-- __init__.py                # Public exports
|   +-- base.py                    # AutomationRule, TriggerCondition, Action
|   +-- config.py                  # AutomationConfig
|   +-- engine.py                  # AutomationEngine
|   +-- context.py                 # AutomationContext (loop prevention)
|   +-- pipeline.py                # PipelineConversionRule
|   +-- templates.py               # TemplateDiscovery
|   +-- seeding.py                 # FieldSeeder
|   +-- waiter.py                  # SubtaskWaiter
|
+-- persistence/
|   +-- cascade.py                 # CascadeOperation, CascadeExecutor
|   +-- session.py                 # Extended: prefetch_holders, recursive, cascade_field
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from 6 source TDDs |
