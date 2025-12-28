# TDD-08: Business Domain Architecture

> Consolidated TDD for process pipelines, automation, entity detection, and business model layer.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-PROCESS-PIPELINE, TDD-AUTOMATION-LAYER, TDD-DETECTION, TDD-PIPELINE-AUTOMATION-ENHANCEMENT, TDD-0027-business-model-architecture, TDD-0028-business-model-implementation
- **Related ADRs**: ADR-0015, ADR-0016, ADR-0017, ADR-0020, ADR-0021, ADR-0022, ADR-0023, ADR-0058

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

Find-or-create pattern for complete hierarchy creation with composite matching:

```python
class BusinessSeeder:
    def __init__(
        self,
        client: AsanaClient,
        *,
        matching_config: MatchingConfig | None = None,
    ) -> None:
        """Initialize with optional matching configuration override."""
        self._client = client
        self._matching_config = matching_config or MatchingConfig.from_env()
        self._matching_engine = MatchingEngine(self._matching_config)

    async def seed_async(
        self,
        business: BusinessData,
        process: ProcessData,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """
        1. Find existing Business via tiered matching:
           a. Tier 1: Exact company_id match
           b. Tier 2: Composite Fellegi-Sunter matching
        2. Find or create Unit under Business
        3. Find or create ProcessHolder under Unit
        4. Create Process in ProcessHolder
        5. Add Process to pipeline project
        6. Optional: Create Contact
        """
```

### BusinessData (Extended for v2)

```python
class BusinessData(BaseModel):
    """Input data for Business entity creation.

    Core fields (v1):
    """
    name: str
    company_id: str | None = None
    business_address_line_1: str | None = None
    business_city: str | None = None
    business_state: str | None = None
    business_zip: str | None = None
    vertical: str | None = None

    # New fields for v2 composite matching (optional, backward compatible)
    email: str | None = None    # Business email
    phone: str | None = None    # Business phone
    domain: str | None = None   # Website domain
```

### Matching Integration Flow

```
seed_async(business, process, contact)
           |
           v
    _find_business_async(business)
           |
    +------+------+
    |             |
    v             v (no company_id match)
  Tier 1:      Tier 2:
  company_id   _find_by_composite_match()
  exact             |
  match       +-----+-----+
    |         |           |
    v         v           v
  Return    Get        Apply
  existing  candidates  MatchingEngine
  Business  via Search  .find_best_match()
              |           |
              v           v
            Blocking    Return best
            filter      match or None
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

## 8. Composite Matching Architecture

### Overview

The BusinessSeeder v2 introduces Fellegi-Sunter probabilistic matching for robust business deduplication. Instead of relying solely on exact company_id matches, the system now evaluates multiple corroborating fields using a log-odds scoring algorithm.

```
+----------------------------------------------------------------------+
|                      MATCHING PIPELINE                               |
+----------------------------------------------------------------------+
|  Input: "Acme Corp, info@acme.com, 555-123-4567"                    |
|                              |                                       |
|                              v                                       |
|  +----------------------------------------------------------+       |
|  | TIER 1: Exact company_id match                           |       |
|  | - O(1) lookup via SearchService                          |       |
|  | - If match found -> Return existing Business             |       |
|  +----------------------------------------------------------+       |
|                              | (no match)                            |
|                              v                                       |
|  +----------------------------------------------------------+       |
|  | TIER 2: Composite Fellegi-Sunter matching                |       |
|  |                                                          |       |
|  |  1. Get candidates via SearchService                     |       |
|  |  2. Apply blocking rules (O(n) candidate filtering)      |       |
|  |  3. Normalize fields via Normalizer chain                |       |
|  |  4. Compare fields via Comparator patterns               |       |
|  |  5. Accumulate log-odds scores                           |       |
|  |  6. Convert to probability                               |       |
|  |  7. If probability >= 0.80 -> Return existing Business   |       |
|  +----------------------------------------------------------+       |
|                              | (no match)                            |
|                              v                                       |
|  +----------------------------------------------------------+       |
|  | TIER 3: Create new Business                              |       |
|  | - Proceed with find-or-create pattern                    |       |
|  +----------------------------------------------------------+       |
+----------------------------------------------------------------------+
```

### MatchingEngine Class Design

The `MatchingEngine` orchestrates field comparison using the Fellegi-Sunter statistical model:

```python
class MatchingEngine:
    """Fellegi-Sunter probabilistic matching engine.

    Per FR-M-001: Probabilistic matching using log-odds accumulation.
    Per FR-M-002: Composite field comparison with configurable weights.
    """

    def __init__(self, config: MatchingConfig | None = None) -> None:
        """Initialize with optional configuration override."""

    def compute_match(
        self,
        query: BusinessData,
        candidate: Candidate,
    ) -> MatchResult:
        """Compute match score between query and candidate."""

    def find_best_match(
        self,
        query: BusinessData,
        candidates: list[Candidate],
    ) -> MatchResult | None:
        """Find best matching candidate above threshold."""
```

**Component Interactions**:

```
+------------------+     +-------------------+     +------------------+
|   BusinessData   | --> |   MatchingEngine  | --> |   MatchResult    |
|   (query input)  |     |                   |     |   (decision)     |
+------------------+     +-------------------+     +------------------+
                               |
         +---------------------+---------------------+
         |                     |                     |
         v                     v                     v
+------------------+  +------------------+  +------------------+
|   Normalizers    |  |   Comparators    |  |  BlockingRules   |
| - Phone (E.164)  |  | - Exact          |  | - Domain         |
| - Email          |  | - Fuzzy (JW)     |  | - PhonePrefix    |
| - BusinessName   |  | - TF-adjusted    |  | - NameToken      |
| - Domain         |  +------------------+  +------------------+
| - Address        |
+------------------+
```

### Normalizer Chain

Normalizers transform raw field values into canonical forms before comparison:

| Normalizer | Input Example | Output | Transformation |
|------------|---------------|--------|----------------|
| `PhoneNormalizer` | `(555) 123-4567` | `+15551234567` | E.164 format, digits only |
| `EmailNormalizer` | `John.Doe@GMAIL.COM` | `john.doe@gmail.com` | Lowercase, trim |
| `BusinessNameNormalizer` | `ACME Corp, Inc.` | `acme corp` | Strip suffixes, normalize case |
| `DomainNormalizer` | `www.Example.COM/` | `example.com` | Strip www, protocol, path |
| `AddressNormalizer` | `New York` / `NY` | `ny` | State to 2-letter abbreviation |

**Legal Suffix Stripping**:

The `BusinessNameNormalizer` removes legal suffixes that cause false negatives:
- inc, llc, ltd, corp, corporation, company, co
- llp, lp, pllc, incorporated, limited, pc, pa, pllp

### Comparator Patterns

Three comparison strategies handle different field types:

**ExactComparator**:
```python
# Returns (1.0, 1.0) for exact match, (0.0, 0.0) for non-match
# Used for: email, phone, domain
```

**FuzzyComparator**:
```python
# Uses Jaro-Winkler similarity with graduated weight levels
# Thresholds (configurable via SEEDER_FUZZY_* env vars):
#   >= 0.95: Full weight (1.0 multiplier)
#   >= 0.90: 75% weight (0.75 multiplier)
#   >= 0.80: 50% weight (0.50 multiplier)
#   <  0.80: Non-match (0.0 multiplier)
# Used for: name
```

**TermFrequencyAdjuster**:
```python
# Reduces weight for common values
# Common domains (gmail.com, yahoo.com): 5% frequency -> reduced weight
# Common cities (new york, los angeles): 2% frequency -> reduced weight
# Formula: adjusted_weight = base_weight * (1.0 - min(frequency * 10, 0.8))
```

### Blocking Strategy for O(n) Candidate Reduction

Without blocking, comparing a query against N existing records requires N comparisons. The matching engine uses blocking rules to reduce the candidate set before expensive comparison:

```
+-------------------------------------------------------------------+
|                    BLOCKING RULES (OR logic)                      |
+-------------------------------------------------------------------+
|                                                                   |
|  DomainBlockingRule         PhonePrefixBlockingRule              |
|  +-------------------+      +------------------------+           |
|  | Exact domain      |      | First 6 digits of      |           |
|  | match required    |  OR  | normalized phone       |           |
|  | (~90% reduction)  |      | must match             |           |
|  +-------------------+      +------------------------+           |
|                                       |                          |
|                             +---------+---------+                |
|                             |                   |                |
|                       NameTokenBlockingRule     |                |
|                       +-------------------+     |                |
|                       | Shared significant|     |                |
|                       | tokens (>3 chars, |  OR |                |
|                       | not stop words)   |     |                |
|                       +-------------------+     |                |
|                                                                   |
|  CompositeBlockingRule: Pass if ANY rule matches                 |
+-------------------------------------------------------------------+
```

**Performance characteristics**:
- Domain blocking: ~90% reduction for businesses with domain data
- Phone prefix blocking: ~95% reduction for businesses with phone data
- Name token blocking: Variable reduction based on name uniqueness
- Composite rule: OR logic preserves candidates that match on any dimension

### Log-Odds Scoring Algorithm

The Fellegi-Sunter model uses log-odds accumulation for principled score combination:

```
                        Field Comparison Results
                                 |
         +--------+--------+--------+--------+
         |        |        |        |        |
      Email    Phone    Name    Domain   Address
      match    match    fuzzy   match    match
         |        |        |        |        |
         v        v        v        v        v
       +8.0     +7.0    +6.0*   +5.0**   +4.0
                        0.85           (TF adj)
                                 |
         +-----------------------+
         |
         v
    Sum log-odds = 8.0 + 7.0 + (6.0 * 0.75) + 1.0 + 4.0 = 24.5
                                 |
                                 v
    Convert: probability = exp(24.5) / (1 + exp(24.5)) = 0.9999
                                 |
                                 v
    Decision: probability (0.9999) >= threshold (0.80) -> MATCH
```

**Weight table (defaults)**:

| Field | Match Weight | Non-Match Weight | Rationale |
|-------|--------------|------------------|-----------|
| Email | +8.0 | -4.0 | Highly unique identifier |
| Phone | +7.0 | -4.0 | Unique but formatting varies |
| Name | +6.0 | -3.0 | Common names reduce uniqueness |
| Domain | +5.0 | -2.0 | Multiple businesses share domains |
| Address | +4.0 | -2.0 | Often incomplete or abbreviated |

**Null handling**: Fields with null values on either side contribute zero weight (neutral). This prevents penalizing records with missing data.

**Minimum evidence threshold**: Requires at least 2 non-null field comparisons (configurable via `SEEDER_MIN_FIELDS`) to prevent matching on insufficient evidence.

### Configuration Integration

All matching parameters are configurable via environment variables:

```python
class MatchingConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SEEDER_")

    match_threshold: float = 0.80    # Probability threshold for match
    min_fields: int = 2              # Minimum non-null comparisons

    email_weight: float = 8.0        # Log-odds weights
    phone_weight: float = 7.0
    name_weight: float = 6.0
    domain_weight: float = 5.0
    address_weight: float = 4.0

    fuzzy_exact_threshold: float = 0.95    # Jaro-Winkler thresholds
    fuzzy_high_threshold: float = 0.90
    fuzzy_medium_threshold: float = 0.80

    tf_enabled: bool = True          # Term frequency adjustment
```

See [REF-seeder-matching-config](../reference/REF-seeder-matching-config.md) for complete configuration reference.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| Multi-field comparison | Email, phone, name, domain, address weighted by reliability |
| Fuzzy name matching | Jaro-Winkler handles typos, abbreviations, legal suffix variations |
| Configurable thresholds | All weights via `SEEDER_*` environment variables |
| Minimum evidence | Requires 2+ matching fields to prevent false positives |
| Term frequency adjustment | Common values (gmail.com) contribute less weight |
| O(n) performance | Blocking rules prevent quadratic comparison explosion |
| Graceful degradation | Falls back to exact matching if composite fails |
| Backward compatible | Existing API unchanged, new fields optional |

### MatchResult Audit Trail

Every match decision includes a complete audit trail:

```python
@dataclass
class MatchResult:
    is_match: bool              # Boolean decision
    score: float                # Normalized probability 0.0-1.0
    raw_score: float            # Sum of log-odds before conversion
    threshold: float            # Applied threshold
    fields_compared: int        # Non-null field count
    comparisons: list[FieldComparison]  # Per-field details
    match_type: str             # "exact" | "composite" | "no_match"
    candidate_gid: str | None   # Matched entity GID

@dataclass
class FieldComparison:
    field_name: str             # email, phone, name, etc.
    left_value: str | None      # Query value (normalized)
    right_value: str | None     # Candidate value (normalized)
    comparison_type: str        # "exact" | "fuzzy" | "composite"
    similarity: float | None    # 0.0-1.0 for fuzzy, None for exact
    weight_applied: float       # Actual weight after TF adjustment
    contributed: bool           # True if field affected score
```

### Error Handling and Graceful Degradation

The matching system fails gracefully to preserve seeder reliability:

```python
try:
    match_result = await self._find_by_composite_match(data)
    if match_result:
        return match_result
except Exception as e:
    # Graceful degradation - log and continue to create new
    logger.warning(
        "Composite matching failed, will create new business",
        extra={"query_name": data.name, "error": str(e)},
    )
```

Failure modes:
- **SearchService unavailable**: Falls back to creating new business
- **Candidate retrieval fails**: Logs warning, proceeds with creation
- **Comparator exception**: Catches and returns no-match result
- **Configuration invalid**: Raises at startup (fail-fast via Pydantic validation)

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
| ADR-0058 | Composite Matching for Business Deduplication |

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
|   |   +-- matching/              # Composite matching module (v2)
|   |   |   +-- __init__.py        # Public exports: MatchingEngine, MatchingConfig
|   |   |   +-- engine.py          # MatchingEngine, log_odds_to_probability()
|   |   |   +-- config.py          # MatchingConfig (Pydantic settings)
|   |   |   +-- models.py          # MatchResult, FieldComparison, Candidate
|   |   |   +-- normalizers.py     # Phone, Email, BusinessName, Domain, Address normalizers
|   |   |   +-- comparators.py     # ExactComparator, FuzzyComparator, TermFrequencyAdjuster
|   |   |   +-- blocking.py        # BlockingRule protocol, Domain/Phone/NameToken rules
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
| 1.1 | 2025-12-28 | Tech Writer | Added Section 8: Composite Matching Architecture; updated Section 6 with MatchingEngine integration; added matching/* to package structure; added ADR-0058 to related ADRs |
