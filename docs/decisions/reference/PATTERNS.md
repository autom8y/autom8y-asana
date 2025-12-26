# ADR Summary: Reusable Patterns

> Consolidated decision record for code patterns, protocols, descriptors, and design patterns. Individual ADRs archived.

## Overview

This codebase employs a rich vocabulary of patterns to manage complexity at scale. From protocols that enable dependency injection to descriptors that eliminate boilerplate, these patterns form the technical DNA of the SDK. Rather than one-off implementations, the patterns establish reusable solutions that compose together—protocols define interfaces, descriptors manage attribute access, factories handle creation, state machines control transitions, and integration patterns connect layers.

The evolution follows a clear arc: early adoption of protocols for extensibility (2025-12-08), progressive refinement through descriptor patterns for DRY principles (2025-12-16), and culmination in sophisticated integration patterns for cache and staleness detection (2025-12-24). Each pattern solves a specific architectural problem while maintaining consistency with the codebase's async-first, type-safe philosophy.

The pattern families represent different layers of abstraction: protocols operate at the boundary layer (cache, observability, automation), descriptors handle the domain layer (navigation, custom fields), factories manage creation complexity (seeder, action methods), and integration patterns orchestrate cross-cutting concerns (caching, batch operations, staleness checking).

## Key Decisions

### 1. Protocol-Based Extensibility: Clean Boundaries via typing.Protocol

**Context**: SDK needs extensible integration points for caching, logging, observability, and automation rules without requiring inheritance.

**Decision**: Use `typing.Protocol` with structural subtyping for all dependency injection points. Protocol instances accept any object matching the required method signatures.

**Rationale**:
- Enables duck-typing (no inheritance required)
- Consumers can integrate existing systems without modification
- Type checkers validate compliance statically
- Matches existing Python patterns (`CacheProvider`, `LogProvider`)

**Key Protocols**:
- **CacheProvider** (ADR-0016): Extended from 3 to 11 methods for versioned caching
- **ObservabilityHook** (ADR-0085): Async methods for metrics/tracing integration
- **AutomationRule** (ADR-0103): Runtime-checkable protocol for trigger/execute pattern

**Source ADRs**: ADR-0007 (Client Pattern), ADR-0016 (Cache Protocol), ADR-0085 (ObservabilityHook), ADR-0103 (Automation Rule)

---

### 2. Descriptor Patterns: Eliminate Boilerplate via Python Descriptors

**Context**: Business layer contained ~950 lines of repetitive navigation and custom field property code across 10 entities (800 lines for custom fields, 150 lines for navigation).

**Decision**: Use Python descriptor protocol (`__get__`, `__set__`, `__set_name__`) with Generic type parameters for declarative attribute access.

**Rationale**:
- **DRY**: 7-8 lines per field reduced to 1 declarative line
- **Type Safety**: Generic[T] preserves IDE autocomplete and mypy inference
- **Pydantic Compatibility**: `ignored_types` config allows descriptors in BaseModel subclasses
- **Proven Pattern**: Used by Django ORM, SQLAlchemy, Pydantic itself

**Descriptor Families**:

**Navigation** (ADR-0075, ADR-0077):
```python
# Before: 12 lines of property boilerplate
@property
def business(self) -> Business | None:
    if self._business is None and self._contact_holder is not None:
        self._business = self._contact_holder._business
    return self._business

# After: 1 line
business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
```
- `ParentRef[T]`: Upward navigation with lazy resolution via holder chain
- `HolderRef[T]`: Direct holder property access

**Custom Fields** (ADR-0081, ADR-0117):
```python
# Before: 7-8 lines per field × 108 fields = 800+ lines
@property
def company_id(self) -> str | None:
    return self._get_text_field(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

# After: 1 line per field
company_id = TextField()  # Field name auto-derived from property name
```
- **Hierarchy**: `CustomFieldDescriptor[T]` base with 7 type-specific subclasses
- **Unification** (ADR-0117): Descriptors delegate to `CustomFieldAccessor` infrastructure layer
- **Mixin Strategy** (ADR-0141): Shared fields grouped into `SharedCascadingFieldsMixin`, `FinancialFieldsMixin`

**Pydantic v2 Compatibility** (ADR-0077):
```python
class BusinessEntity(Task):
    model_config = ConfigDict(
        ignored_types=(ParentRef, HolderRef, TextField, EnumField),  # Skip descriptor instances
        extra="allow",  # Allow __set__ delegation
    )
```

**Source ADRs**: ADR-0075 (Navigation Descriptor), ADR-0077 (Pydantic Compatibility), ADR-0081 (Custom Field Descriptor), ADR-0117 (Accessor/Descriptor Unification), ADR-0141 (Field Mixin Strategy)

---

### 3. Factory Patterns: Encapsulate Complex Creation

**Context**: Multi-step entity creation and action method generation required complex boilerplate or manual orchestration.

**Decision**: Use factory classes and descriptor-based method generation for creation complexity.

**BusinessSeeder Factory** (ADR-0099):
```python
# Encapsulates: Business -> Unit -> ProcessHolder -> Process creation
seeder = BusinessSeeder(client)
result = await seeder.seed_async(
    business=BusinessData(name="Acme Corp"),
    process=ProcessData(name="Sales Opportunity", process_type=ProcessType.SALES)
)
# Returns: SeederResult with all entities + creation flags
```
- **Pattern**: Find-or-create with idempotency
- **Result**: Typed dataclass with entities and metadata
- **Integration**: Uses SaveSession internally for transactional execution

**Action Method Factory** (ADR-0122):
```python
# Before: 920 lines for 18 action methods (51 lines each on average)
def add_tag(self, task, tag) -> SaveSession:
    self._ensure_open()
    # ... 10 lines of boilerplate ...
    return self

# After: 13 lines total for 13 methods
add_tag = ActionBuilder("add_tag")
remove_tag = ActionBuilder("remove_tag")
# ActionBuilder reads ACTION_REGISTRY and generates method body
```
- **Descriptor-Based**: `ActionBuilder.__get__()` returns generated bound method
- **Variants**: NO_TARGET, TARGET_REQUIRED, POSITIONING (3 method signatures)
- **Registry**: Centralized `ACTION_REGISTRY` defines all action configurations

**Source ADRs**: ADR-0099 (BusinessSeeder Factory), ADR-0122 (Action Method Factory)

---

### 4. State Patterns: Explicit State Management

**Context**: Process entities move through pipeline stages; ProcessSection needs state extraction from Asana memberships.

**Decision**: Use enum-based state machine with section membership as source of truth, no enforced transitions.

**ProcessSection State Machine** (ADR-0097):
```python
class ProcessSection(str, Enum):
    OPPORTUNITY = "opportunity"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"  # Fallback for unknown sections

@classmethod
def from_name(cls, name: str | None) -> ProcessSection | None:
    # Case-insensitive matching with aliases ("Lost" -> DID_NOT_CONVERT)
    # Returns OTHER for unrecognized, None for None input
```
- **Source of Truth**: Section membership in Asana (task.memberships)
- **No Enforcement**: SDK provides state extraction, consumers implement transition rules
- **Fuzzy Matching**: Handles "Did Not Convert" vs "Lost" vs "Didn't Convert"

**State Transition Composition** (ADR-0100):
```python
# Process.move_to_state() wraps SaveSession.move_to_section()
process.move_to_state(session, ProcessSection.CONVERTED)
# Looks up section GID via ProcessProjectRegistry
# Delegates to session.move_to_section()
# Returns session for fluent chaining
```
- **Composition Over Extension**: Helper method on Process, not new SaveSession method
- **Registry Lookup**: ProcessProjectRegistry.get_section_gid(process_type, section)
- **Error Handling**: ValueError for unconfigured sections (fail fast with actionable message)

**Source ADRs**: ADR-0097 (ProcessSection State Machine), ADR-0100 (State Transition Composition)

---

### 5. Loading Patterns: Deferred Fetching for Performance

**Context**: Business holders (contacts, units, etc.) contain subtasks that shouldn't be fetched eagerly.

**Decision**: Lazy loading triggered on `SaveSession.track()` with async prefetch in session context.

**Holder Lazy Loading** (ADR-0050):
```python
# Holders fetched when entity tracked, not on property access
async with client.save_session() as session:
    session.track(business)  # Triggers holder prefetch
    await session.prefetch_holders()  # Explicit prefetch point
    # business.contact_holder now populated
```
- **Why Not Property Access**: Async properties break Python conventions
- **Why Not Init**: Task construction should be cheap, no network calls
- **Batch-Friendly**: Multiple businesses can be prefetched in parallel

**Minimal Stub Model** (ADR-0087):
```python
# Stub holders return typed minimal models instead of raw Task
class DNA(BusinessEntity):  # Minimal typed model
    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    @property
    def business(self) -> Business | None:
        return self._business

# Usage: type-safe iteration
for dna in business.dna_holder.children:  # list[DNA], not list[Task]
    print(dna.business.name)  # Navigate to root
```
- **Purpose**: Type safety for stub holders without known custom fields
- **Contents**: Bidirectional navigation only (holder → entity, entity → root)
- **Exclusions**: No custom field accessors (domain unknown)

**Source ADRs**: ADR-0050 (Holder Lazy Loading), ADR-0087 (Minimal Stub Model)

---

### 6. Integration Patterns: Cross-Layer Orchestration

**Context**: Caching, staleness checking, and client operations require coordination across SDK layers.

**Decision**: Standardized integration patterns with graceful degradation and batch optimization.

**Client Cache Integration** (ADR-0119, ADR-0124):
```python
# 6-step pattern for all SDK clients
async def get_async(self, entity_gid: str, ...) -> Model | dict:
    validate_gid(entity_gid, "entity_gid")

    # 1. Check cache first
    cached_entry = self._cache_get(entity_gid, EntryType.ENTITY)
    if cached_entry is not None:
        return cached_entry.data if raw else Model.model_validate(cached_entry.data)

    # 2. Fetch from API on miss
    data = await self._http.get(f"/entities/{entity_gid}", params=params)

    # 3. Store in cache
    self._cache_set(entity_gid, data, EntryType.ENTITY, ttl=TTL)

    # 4. Return response
    return data if raw else Model.model_validate(data)
```
- **BaseClient Helpers**: `_cache_get()`, `_cache_set()`, `_cache_invalidate()` for reuse
- **Graceful Degradation**: Cache errors log warnings, never propagate
- **TTL Strategy**: Entity-type-specific TTLs (Task 300s, Project 900s, User 3600s)
- **Versioning**: Uses `modified_at` when available, `datetime.now()` fallback

**Batch Cache Population** (ADR-0116):
```python
# Check-Fetch-Populate pattern for bulk operations
cache_keys = [make_key(gid, project_gid) for gid in expected_gids]
cached_entries = cache.get_batch(cache_keys, EntryType.DATAFRAME)

# Partition hits/misses
cache_hits = {k: v for k, v in cached_entries.items() if v and not v.is_stale()}
cache_misses = {k for k in cache_keys if k not in cache_hits}

# Fetch only misses
if cache_misses:
    fetched = await parallel_fetch(cache_misses)
    cache.set_batch({make_key(t.gid, project_gid): entry(t) for t in fetched})
```
- **Purpose**: Minimize API calls for large projects (3,500 tasks)
- **Batch API**: `get_batch()` / `set_batch()` for O(1) latency vs O(n)
- **Partial Cache**: Fetch only missing/stale entries

**Staleness Check Integration** (ADR-0134):
```python
# Enhanced cache lookup with staleness checking
async def _cache_get_with_staleness_async(
    self, key: str, entry_type: EntryType
) -> CacheEntry | None:
    entry = self._cache.get_versioned(key, entry_type)

    if entry is None:
        return None  # Cache miss

    if not entry.is_expired():
        return entry  # Cache hit

    # Expired - attempt lightweight staleness check
    if self._staleness_coordinator and entry_type in (EntryType.TASK, EntryType.PROJECT):
        result = await self._staleness_coordinator.check_and_get_async(entry)
        if result:
            return result  # Unchanged, TTL extended

    return None  # Changed or check failed
```
- **Constructor Injection**: Coordinator passed to BaseClient, opt-in via config
- **Entity Type Filter**: Only TASK/PROJECT (have `modified_at`)
- **Graceful Degradation**: Staleness check errors fall back to full fetch

**Source ADRs**: ADR-0116 (Batch Cache Population), ADR-0119 (Client Cache Integration Pattern), ADR-0124 (Client Cache Pattern), ADR-0134 (Staleness Check Integration)

---

### 7. Resilience Patterns: Fault Tolerance and Recovery

**Context**: SDK must gracefully handle API failures, circuit breaking, and error classification.

**Decision**: Composition-based circuit breaker with error mixins for classification.

**Circuit Breaker Pattern** (ADR-0048):
```python
# Composition-based, per-client instance
client = AsanaClient(
    token="...",
    circuit_breaker=CircuitBreakerConfig(
        enabled=True,
        failure_threshold=5,
        recovery_timeout=60.0,
    )
)

# State machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
# Check before request for fast failure
```
- **Opt-In**: Disabled by default (backward compatible)
- **Scope**: Per-client (no global state)
- **Triggers**: HTTP 5xx, 429 after retries, network errors

**RetryableErrorMixin** (ADR-0091):
```python
class RateLimitError(AsanaError, RetryableErrorMixin):
    is_retryable: bool = True

class ValidationError(AsanaError):
    is_retryable: bool = False
```
- **Purpose**: Declarative retry classification
- **Integration**: RetryHandler checks `is_retryable` attribute
- **Mixin**: Adds `is_retryable` flag without deep hierarchy

**Source ADRs**: ADR-0048 (Circuit Breaker Pattern), ADR-0091 (RetryableErrorMixin)

---

### 8. Hook Patterns: Event Lifecycle Integration

**Context**: SDK needs extensible hooks for synchronous/async event handling and observability.

**Decision**: Protocol-based hooks with sync-first design and async support.

**Synchronous Event Hooks** (ADR-0041):
```python
class SaveSessionHook(Protocol):
    def on_commit_start(self, session: SaveSession) -> None: ...
    def on_commit_end(self, session: SaveSession, result: CommitResult) -> None: ...
    def on_error(self, session: SaveSession, error: Exception) -> None: ...
```
- **Sync-First**: Primary methods are synchronous for simplicity
- **Async Support**: Optional `on_commit_start_async()` variants for I/O
- **Use Case**: Logging, metrics, cache invalidation

**ObservabilityHook** (ADR-0085):
```python
class ObservabilityHook(Protocol):
    async def on_request_start(self, method: str, path: str, correlation_id: str) -> None: ...
    async def on_request_end(self, method: str, path: str, status: int, duration_ms: float) -> None: ...
    async def on_rate_limit(self, retry_after_seconds: int) -> None: ...
    async def on_circuit_breaker_state_change(self, old_state: str, new_state: str) -> None: ...
```
- **Async-Only**: All methods async for non-blocking telemetry
- **Null Object**: `NullObservabilityHook` for zero-cost when unused
- **Integration**: Plugs into transport layer, circuit breaker, rate limiter

**Source ADRs**: ADR-0041 (Sync Hooks with Async Support), ADR-0085 (ObservabilityHook Protocol)

---

### 9. Discovery Patterns: Runtime Configuration and Lookup

**Context**: Template tasks, project-to-entity type mapping, and section discovery require runtime lookup.

**Decision**: Registry patterns for O(1) lookup with import-time population.

**Project-to-EntityType Registry** (ADR-0093):
```python
class ProjectTypeRegistry:  # Singleton
    _instance: ProjectTypeRegistry | None = None

    def register(self, project_gid: str, entity_type: EntityType) -> None: ...
    def get_entity_type(self, project_gid: str) -> EntityType | None: ...

# Auto-populated via __init_subclass__
class Business(BusinessEntity):
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "123456"  # Auto-registers

# Environment override
ASANA_PROJECT_BUSINESS=789012  # Overrides class attribute
```
- **Population**: Import-time via `__init_subclass__` hook
- **Override Hierarchy**: Env var > class attribute > None
- **O(1) Lookup**: Dict-based for deterministic detection

**Template Discovery Pattern** (ADR-0106):
```python
class TemplateDiscovery:
    async def find_template_section_async(self, project_gid: str) -> Section | None:
        # Fuzzy match: section name contains "template" (case-insensitive)
        # Patterns: ["template", "templates", "template tasks"]

    async def find_template_task_async(
        self, project_gid: str, template_name: str | None = None
    ) -> Task | None:
        # Returns first task in template section or specific match by name
```
- **Fuzzy Matching**: Section names vary ("Template", "Templates", "Process Templates")
- **First Match**: Returns first qualifying section/task
- **Error Handling**: Returns None, descriptive error in AutomationResult

**Source ADRs**: ADR-0093 (Project-Entity Registry), ADR-0106 (Template Discovery)

---

### 10. Cascade Patterns: Hierarchical Field Inheritance

**Context**: Custom fields cascade from parent to child entities (Business → Unit → Offer → Process) with override capabilities.

**Decision**: Declarative cascade definitions with rep field priority rules.

**Rep Field Cascade** (ADR-0113):
```python
def resolve_rep(unit: Unit | None, business: Business | None) -> str | None:
    # Unit.rep takes precedence (specificity principle)
    if unit and unit.rep:
        return unit.rep[0]["gid"]

    # Fall back to Business.rep
    if business and business.rep:
        return business.rep[0]["gid"]

    return None  # No rep found, log warning
```
- **Cascade Order**: Unit → Business (more specific wins)
- **Use Case**: Assign rep to new Process during pipeline conversion
- **Graceful Fallback**: Empty rep doesn't fail conversion

**Source ADRs**: ADR-0113 (Rep Field Cascade)

---

### 11. Detection Enhancement Patterns: Robust Identification

**Context**: Name-based entity type detection fails on decorated task names ("Acme Corp - Chiropractic Offers").

**Decision**: Word boundary-aware regex matching with decoration stripping.

**Tier 2 Pattern Matching** (ADR-0138):
```python
PATTERN_CONFIG = {
    EntityType.CONTACT_HOLDER: PatternSpec(
        patterns=["contacts", "contact"],  # Singular + plural
        word_boundary=True,  # Match whole words only
        strip_decorations=True,  # Remove [URGENT] prefixes, (Primary) suffixes
    ),
}

def _strip_decorations(name: str) -> str:
    # Strip: [URGENT], >>, (Primary), "1. ", "- "
    return regex.sub(STRIP_PATTERNS, "", name).strip()

def _matches_pattern(name: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if re.search(rf"\b{re.escape(pattern)}\b", name, re.IGNORECASE):
            return True
    return False
```
- **Test Cases**:
  - "Contact List" → CONTACT_HOLDER (singular match)
  - "Recontact Team" → None (word boundary prevents false positive)
  - "[URGENT] Contacts" → CONTACT_HOLDER (decoration stripped)
- **Performance**: Regex patterns compiled with `@lru_cache`

**Source ADRs**: ADR-0138 (Tier 2 Pattern Matching Enhancement)

---

## Evolution Timeline

| Date | Decision | Impact |
|------|----------|--------|
| 2025-12-08 | ADR-0007: Consistent Client Pattern | Established protocol-first extensibility across resource clients |
| 2025-12-09 | ADR-0016: Cache Protocol Extension | Extended CacheProvider to 11 methods for versioned caching |
| 2025-12-10 | ADR-0048: Circuit Breaker Pattern | Added resilience layer for cascading failure prevention |
| 2025-12-11 | ADR-0050: Holder Lazy Loading | Deferred subtask fetching to SaveSession context |
| 2025-12-16 | ADR-0075: Navigation Descriptor | Eliminated 150 lines of navigation boilerplate |
| 2025-12-16 | ADR-0077: Pydantic Descriptor Compatibility | Enabled descriptors in Pydantic v2 via ignored_types |
| 2025-12-16 | ADR-0081: Custom Field Descriptor | Reduced 800 lines to 110 declarative lines (86% reduction) |
| 2025-12-16 | ADR-0085: ObservabilityHook Protocol | Standardized metrics/tracing integration |
| 2025-12-16 | ADR-0087: Minimal Stub Model | Added type safety for stub holders without domain knowledge |
| 2025-12-17 | ADR-0091: RetryableErrorMixin | Declarative retry classification via mixin |
| 2025-12-17 | ADR-0093: Project-EntityType Registry | O(1) deterministic detection via import-time registration |
| 2025-12-17 | ADR-0097: ProcessSection State Machine | Enum-based state with fuzzy section matching |
| 2025-12-17 | ADR-0099: BusinessSeeder Factory | Idempotent hierarchy creation with find-or-create |
| 2025-12-17 | ADR-0100: State Transition Composition | Process.move_to_state() wraps SaveSession primitive |
| 2025-12-18 | ADR-0103: Automation Rule Protocol | Runtime-checkable protocol for trigger/execute |
| 2025-12-18 | ADR-0106: Template Discovery Pattern | Fuzzy section matching for template tasks |
| 2025-12-18 | ADR-0113: Rep Field Cascade | Unit-first cascade for assignee resolution |
| 2025-12-19 | ADR-0116: Batch Cache Population | Check-Fetch-Populate for 3,500-task projects |
| 2025-12-19 | ADR-0117: Accessor/Descriptor Unification | Confirmed layered architecture (descriptors → accessor) |
| 2025-12-19 | ADR-0122: Action Method Factory | Reduced 920 lines to 150 via descriptor-based generation |
| 2025-12-19 | ADR-0138: Tier 2 Pattern Enhancement | Word boundary matching with decoration stripping |
| 2025-12-19 | ADR-0141: Field Mixin Strategy | Coarse-grained mixins for shared field composition |
| 2025-12-22 | ADR-0124: Client Cache Pattern | Standardized 6-step cache integration for all clients |
| 2025-12-23 | ADR-0119: Client Cache Integration | Extended pattern to Projects, Sections, Users, CustomFields |
| 2025-12-24 | ADR-0134: Staleness Check Integration | Enhanced cache lookup with coordinator pattern |

---

## Cross-References

**Related Summaries**:
- **ADR-SUMMARY-SAVESESSION**: Unit of Work pattern for transactional operations
- **ADR-SUMMARY-CACHE**: Caching strategy and versioning decisions
- **ADR-SUMMARY-DETECTION**: Multi-tier entity type detection system

**Superseded ADRs**:
- ADR-0100 superseded by ADR-0101 (Process Pipeline Correction)

---

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0007 | Consistent Client Pattern Across Resource Types | 2025-12-08 | All clients follow TasksClient naming/structure |
| ADR-0016 | Cache Protocol Extension | 2025-12-09 | Extended CacheProvider from 3 to 11 methods |
| ADR-0041 | Synchronous Event Hooks with Async Support | Date N/A | Sync-first hooks with optional async variants |
| ADR-0048 | Circuit Breaker Pattern for Transport Layer | 2025-12-10 | Opt-in composition-based circuit breaker |
| ADR-0050 | Holder Lazy Loading Strategy | 2025-12-11 | Fetch holders on SaveSession.track() |
| ADR-0075 | Navigation Descriptor Pattern | 2025-12-16 | ParentRef[T] / HolderRef[T] for 150-line reduction |
| ADR-0077 | Pydantic v2 Descriptor Compatibility | 2025-12-16 | ignored_types + extra="allow" config |
| ADR-0081 | Custom Field Descriptor Pattern | 2025-12-16 | TextField, EnumField, etc. (86% code reduction) |
| ADR-0085 | ObservabilityHook Protocol Design | 2025-12-16 | Async-only protocol for metrics/tracing |
| ADR-0087 | Minimal Stub Model Pattern | 2025-12-16 | Typed minimal models for stub holders |
| ADR-0091 | RetryableErrorMixin for Error Classification | 2025-12-17 | Mixin adds is_retryable flag |
| ADR-0093 | Project-to-EntityType Registry Pattern | 2025-12-17 | Singleton with __init_subclass__ population |
| ADR-0097 | ProcessSection State Machine Pattern | 2025-12-17 | Enum-based state with fuzzy matching |
| ADR-0099 | BusinessSeeder Factory Pattern | 2025-12-17 | Find-or-create for hierarchy creation |
| ADR-0100 | State Transition Composition with SaveSession | 2025-12-17 | Process.move_to_state() helper method |
| ADR-0103 | Automation Rule Protocol | 2025-12-18 | Runtime-checkable Protocol for rules |
| ADR-0106 | Template Discovery Pattern | 2025-12-18 | Fuzzy section name matching |
| ADR-0113 | Rep Field Cascade Pattern | 2025-12-18 | Unit.rep → Business.rep cascade |
| ADR-0116 | Batch Cache Population Pattern | 2025-12-19 | Check-Fetch-Populate for bulk operations |
| ADR-0117 | CustomFieldAccessor/Descriptor Unification Strategy | 2025-12-19 | Confirmed layered design (no refactoring) |
| ADR-0119 | Client Cache Integration Pattern | 2025-12-23 | Extended pattern to 5 SDK clients |
| ADR-0122 | Action Method Factory Pattern | 2025-12-19 | Descriptor-based method generation (83% reduction) |
| ADR-0124 | Client Cache Integration Pattern | 2025-12-22 | 6-step standardized cache integration |
| ADR-0134 | Staleness Check Integration Pattern | 2025-12-24 | Constructor injection with coordinator |
| ADR-0138 | Detection Tier 2 Pattern Matching Enhancement | 2025-12-19 | Word boundary regex with decoration stripping |
| ADR-0141 | Field Mixin Strategy for Sprint 1 Pattern Completion | 2025-12-19 | Coarse-grained mixins (SharedCascading, Financial) |

---

## Pattern Index by Use Case

**When you need to...**

| Need | Pattern | Reference |
|------|---------|-----------|
| Add a new SDK client | Consistent Client Pattern | ADR-0007 |
| Support a new cache backend | CacheProvider Protocol Extension | ADR-0016 |
| Integrate metrics/tracing | ObservabilityHook Protocol | ADR-0085 |
| Add navigation properties | ParentRef/HolderRef Descriptors | ADR-0075, ADR-0077 |
| Add custom field properties | CustomFieldDescriptor subclass | ADR-0081 |
| Create entity hierarchies | BusinessSeeder Factory | ADR-0099 |
| Add SaveSession action methods | ActionBuilder descriptor | ADR-0122 |
| Detect entity types | Project Registry + Tier 2 Pattern Matching | ADR-0093, ADR-0138 |
| Move processes between states | ProcessSection enum + move_to_state() | ADR-0097, ADR-0100 |
| Find template tasks | TemplateDiscovery fuzzy matching | ADR-0106 |
| Handle cascading fields | Rep Field Cascade pattern | ADR-0113 |
| Optimize cache for large datasets | Batch Cache Population | ADR-0116 |
| Add staleness checking | Staleness Check Integration | ADR-0134 |
| Share fields across entities | Field Mixin Strategy | ADR-0141 |
| Make errors retryable | RetryableErrorMixin | ADR-0091 |
| Add resilience to API calls | Circuit Breaker Pattern | ADR-0048 |

---

## Pattern Composition Examples

Patterns compose together to solve complex problems:

**Example 1: Cache-Optimized Entity Fetch**
```python
# Combines: Client Cache Integration (ADR-0124) + Staleness Check (ADR-0134) + Graceful Degradation
client = AsanaClient(
    cache_provider=RedisCacheProvider(),
    staleness_coordinator=StalenessCheckCoordinator(),
)

# Flow:
# 1. BaseClient helpers (ADR-0124) check cache
# 2. If expired, StalenessCheckCoordinator (ADR-0134) checks modified_at
# 3. If unchanged, TTL extended and cached entry returned
# 4. If changed or error, full fetch with graceful degradation
task = await client.tasks.get_async("123456")
```

**Example 2: Business Hierarchy Creation with Observability**
```python
# Combines: BusinessSeeder Factory (ADR-0099) + ObservabilityHook (ADR-0085) + SaveSession
client = AsanaClient(observability_hook=DataDogHook())
seeder = BusinessSeeder(client)

# Flow:
# 1. BusinessSeeder (ADR-0099) orchestrates find-or-create
# 2. SaveSession batches operations
# 3. ObservabilityHook (ADR-0085) emits metrics at each step
result = await seeder.seed_async(
    business=BusinessData(name="Acme Corp"),
    process=ProcessData(name="Opportunity", process_type=ProcessType.SALES)
)
```

**Example 3: Descriptor-Based Domain Model**
```python
# Combines: Field Mixins (ADR-0141) + Navigation Descriptors (ADR-0075) + Custom Field Descriptors (ADR-0081)
class Unit(BusinessEntity, SharedCascadingFieldsMixin, FinancialFieldsMixin):
    # Navigation (ADR-0075)
    business: Business | None = ParentRef[Business](holder_attr="_unit_holder")

    # Custom fields inherited from mixins (ADR-0141)
    # - vertical, rep from SharedCascadingFieldsMixin
    # - booking_type, mrr, weekly_ad_spend from FinancialFieldsMixin

    # Entity-specific custom fields (ADR-0081)
    market = TextField()

# Usage: all patterns work together seamlessly
unit.vertical  # EnumField descriptor from mixin
unit.business  # ParentRef descriptor navigates up
unit.market  # TextField descriptor for entity-specific field
```

---

## Compliance and Evolution

**Quality Gates**:
- [ ] New patterns must include rationale section explaining why chosen
- [ ] Descriptor patterns must preserve type hints for IDE support
- [ ] Protocol patterns must use `typing.Protocol` for structural subtyping
- [ ] Integration patterns must implement graceful degradation
- [ ] All patterns must have unit test coverage

**When to Create New Patterns**:
1. **Duplication threshold**: 3+ instances of similar code
2. **Abstraction clarity**: Pattern name clearly communicates intent
3. **Composition benefit**: Pattern composes cleanly with existing patterns
4. **Maintenance win**: Pattern reduces future maintenance burden

**Pattern Lifecycle**:
1. **Proposed**: Initial ADR with alternatives and rationale
2. **Accepted**: Implemented and tested
3. **Refined**: Modified based on usage learnings
4. **Superseded**: Replaced by improved pattern (original archived)

---

*This summary consolidates 27 individual ADRs. For implementation details, refer to source ADRs listed in each section.*
