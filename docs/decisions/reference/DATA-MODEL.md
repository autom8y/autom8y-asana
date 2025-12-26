# ADR Summary: Data Model & Entities

> Consolidated decision record for entity models, schemas, typing, and Pydantic configuration. Individual ADRs archived.

## Overview

The autom8_asana SDK uses a layered model architecture built on Pydantic v2, with GID-based entity identity and strict type enforcement. The system spans three layers: (1) Pydantic models for API resources with forward-compatible field handling, (2) typed DataFrame schemas for analytical workloads, and (3) custom field descriptors for type-safe business logic.

The design philosophy prioritizes type safety without fragility. Models use `extra="ignore"` to survive API additions, strict Polars dtypes for analytical consistency, and GID-based identity to prevent duplicate tracking bugs. This creates a resilient foundation that catches errors early while adapting gracefully to Asana's evolving API.

Entity hierarchies (Business > Unit > Process) are modeled through composition rather than inheritance for flexibility. Custom fields use descriptor patterns for type-safe access with automatic change tracking. The entire model layer is designed for both interactive use (properties, IDE autocomplete) and automated processing (DataFrames, batch operations).

## Key Decisions

### 1. Foundation: Pydantic v2 Configuration
**Context**: Need robust model validation with forward compatibility for Asana's evolving API.

**Decision**: Use Pydantic v2 with `extra="ignore"` as the default for all models. Unknown fields from API responses are silently discarded rather than causing validation failures.

**Rationale**: Asana regularly adds new fields to API responses. Strict validation (`extra="forbid"`) would break production systems whenever Asana adds a field. Ignoring unknown fields provides forward compatibility while maintaining type safety for explicitly modeled fields.

**Source ADRs**: ADR-0005, ADR-SDK-005

**Configuration Standards**:
```python
class AsanaResource(BaseModel):
    model_config = ConfigDict(
        extra="ignore",           # Forward compatibility
        populate_by_name=True,    # Support field aliases
        str_strip_whitespace=True # Clean inputs
    )
```

**Settings Architecture**: Configuration uses composite Pydantic Settings pattern with domain-specific subsettings (`AsanaSettings`, `CacheSettings`, `RedisSettings`). Singleton pattern with `reset_settings()` enables test isolation. Dynamic env vars (e.g., `ASANA_PROJECT_{name}`) use direct `os.environ.get()` since field names must be known at class definition time.

### 2. Identity: GID-Based Entity Tracking
**Context**: The same Asana resource fetched multiple times created separate Python objects, leading to duplicate tracking and race conditions in SaveSession.

**Decision**: Use GID (Global ID) as the primary tracking key instead of Python's `id()` function. `ChangeTracker` maintains `dict[str, AsanaResource]` keyed by GID, with fallback to `__id_{id(entity)}` for truly GID-less entities.

**Rationale**: Asana guarantees GID uniqueness. Two Python objects with the same GID represent the same resource and should be tracked once. This prevents duplicate API operations and race conditions where updates to different Python objects of the same resource overwrite each other.

**Source ADR**: ADR-0078

**GID Validation**: Validate GID format at `track()` time using pattern `^(temp_\d+|\d+)$`. Reject empty strings (`ValidationError`), allow `None` for new entities, support temporary GIDs (`temp_1`) for dependency resolution.

**Source ADR**: ADR-0049

**Key Generation**:
```python
def _get_key(self, entity: AsanaResource) -> str:
    gid = getattr(entity, 'gid', None)
    if gid:
        return gid  # Real or temp_ GID
    return f"__id_{id(entity)}"  # Fallback for GID-less
```

### 3. Reference Model: NameGid as Frozen Standalone
**Context**: API returns lightweight resource references (assignee, followers, projects) as `{gid, name, resource_type}` dicts.

**Decision**: `NameGid` is a standalone frozen Pydantic model, NOT inheriting from `AsanaResource`. It's hashable (equality by GID) and immutable.

**Rationale**: References are identifiers, not full resources. They should be immutable, hashable for deduplication, and semantically distinct from mutable `AsanaResource` instances. Frozen status enables use in sets and as dict keys.

**Source ADR**: ADR-0006

**Implementation**:
```python
class NameGid(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    gid: str
    name: str | None = None
    resource_type: str | None = None

    def __hash__(self) -> int:
        return hash(self.gid)  # Equality by GID only
```

### 4. DataFrame Layer: Polars with Strict Schema Enforcement
**Context**: Need typed DataFrame output for analytical workloads with performance 20-30% better than legacy pandas-based `struc()` method.

**Decision**: Use Polars as the primary DataFrame library. Return `pl.DataFrame` from `to_dataframe()` with strict dtype enforcement and logged coercion fallbacks.

**Rationale**: Polars provides 10-100x speedup for common operations, native lazy evaluation for query optimization, strict type enforcement matching SDK philosophy, and lower memory footprint via Arrow columnar backend. User explicitly chose Polars over pandas during requirements gathering.

**Source ADRs**: ADR-0028, ADR-0033

**Schema Enforcement**: When extracted data doesn't match schema type, attempt coercion (e.g., string "5000" to Decimal). If coercion fails, set to `null` and log warning. Continue extraction (don't fail entire batch). Type coercion success rate target: 99%.

**Type Coercion Example**:
```python
# String to Decimal succeeds
coerce("5000.00", pl.Decimal) -> Decimal("5000.00")

# Invalid string returns null with warning
coerce("N/A", pl.Decimal) -> None  # + warning logged
```

### 5. Entity Hierarchy: Schema-Driven Composition Over Inheritance
**Context**: Legacy autom8 monolith uses class inheritance for 50+ task types. Each type defines columns via `STRUC_COLS` class attribute.

**Decision**: Schema definitions are data (composition), extractor classes use inheritance for shared logic, TaskRow models use inheritance for type safety.

**Rationale**: Class explosion is unmaintainable at scale. Schemas as data enable runtime registration without code changes. Post-MVP can add new task types via configuration. Extraction logic genuinely benefits from inheritance (shared base field extraction, custom field helpers).

**Source ADR**: ADR-0029

**Architecture**:
```
DATA LAYER (Composition)          LOGIC LAYER (Inheritance)
SchemaRegistry                    BaseExtractor
  ├── Base Schema                   ├── UnitExtractor
  ├── Unit Schema                   ├── ContactExtractor
  └── Contact Schema                └── BaseExtractor methods
```

**Dual Membership**: Process entities maintain two project memberships: (1) hierarchy via subtask relationship for navigation (`process.unit.business`), (2) pipeline project for board visibility and state tracking. Detection uses hierarchy project for EntityType and pipeline project for ProcessType. Multiple pipeline membership returns `None` with warning.

**Source ADR**: ADR-0098

### 6. Custom Fields: Typed Descriptors with Auto-Generated Constants
**Context**: 80+ business custom fields (MRR, company_id, booking_type) across Business, Contact, Unit models need type-safe access.

**Decision**: Use custom field descriptor pattern for properties that delegate to `CustomFieldAccessor` for storage. Auto-generate `Fields` class constants from descriptors using `__set_name__` + `__init_subclass__` pattern.

**Rationale**: Properties provide type safety and IDE autocomplete. Delegation to existing `CustomFieldAccessor` preserves change tracking integration with SaveSession. Auto-generation eliminates duplication between descriptor definitions and field constants.

**Source ADRs**: ADR-0030, ADR-0051, ADR-0082

**MVP Custom Fields**: Static GID constants (e.g., `MRR_GID = "1205511992584993"`) for MVP simplicity. Post-MVP extends to configuration-based field mappings for environment-specific GIDs and customer customization.

**Descriptor Pattern**:
```python
class Business(Task):
    company_id = TextField()  # Auto-generates Fields.COMPANY_ID = "Company ID"
    mrr = NumberField()       # Auto-generates Fields.MRR = "MRR"

    # Properties delegate to CustomFieldAccessor for change tracking
    # Fields class auto-generated via __init_subclass__
```

**Fields Generation**: Descriptors register field names during `__set_name__`, then `__init_subclass__` collects registrations and generates `Fields` class. Extends existing manual `Fields` classes to preserve backward compatibility.

### 7. Date Handling: Arrow Integration for Rich API
**Context**: 8 date-like custom fields across business models currently stored as ISO 8601 strings (e.g., "2025-12-16").

**Decision**: Use Arrow library for `DateField`, returning `Arrow | None`. Serialize to ISO date format for Asana API compatibility.

**Rationale**: User explicitly requested Arrow. Provides timezone handling, humanization ("2 hours ago"), flexible parsing, and rich comparison operations. More intuitive API than stdlib datetime with minimal dependency cost.

**Source ADR**: ADR-0083

**Usage**:
```python
due = process.process_due_date  # Returns Arrow | None
if due:
    print(due.humanize())       # "in 2 days"
    print(due.format("MMMM D"))  # "December 16"

process.process_due_date = arrow.now().shift(days=7)  # Setter accepts Arrow
```

### 8. Backward Compatibility: Hours Model Deprecation Strategy
**Context**: Hours model requires fundamental changes: field name changes ("Monday Hours" -> "Monday"), type changes (text -> multi_enum), and removal of non-existent fields (timezone, sunday_hours).

**Decision**: Deprecated aliases with clean break on types. New properties use correct names and return types. Old names emit `DeprecationWarning` and delegate to new properties. No type compatibility layer (aliases return new types).

**Rationale**: Deprecation warnings make migration path obvious. Returning correct types prevents silent data loss. Alternative of type-compatible aliases would perpetuate incorrect behavior (joining list elements) or lose data (first element only).

**Source ADR**: ADR-0114

**Migration Path**:
```python
# Before (deprecated)
hours.monday_hours  # Returns list[str], warns about deprecation

# After (correct)
hours.monday  # Returns list[str] like ["08:00:00", "17:00:00"]
```

## Related Patterns

### Type Coercion
Schema enforcement uses `TypeCoercer` class for consistent handling across field types. Coercion failures log structured warnings with field name, task GID, expected type, and actual value. Metrics track coercion success rate (target: 99%).

### Field Name Derivation
Auto-generation uses snake_case to Title Case conversion with abbreviation handling:
```python
company_id -> "Company ID"
mrr -> "MRR"  # Abbreviation preserved
num_ai_copies -> "Num AI Copies"
```

### GID Transition
When temp GID becomes real GID after CREATE, tracker re-keys all data structures and records transition in `_gid_transitions` map for lookup by either GID.

## Cross-References

- **Related Summaries**: ADR-SUMMARY-CUSTOM-FIELDS (descriptor patterns), ADR-SUMMARY-PATTERNS (entity patterns)
- **Tech Stack**: Pydantic v2, Polars >= 0.20.0, Arrow >= 1.3.0
- **Settings**: ADR-SDK-005 for Pydantic Settings standards and composite pattern

## Archived Individual ADRs

| ADR | Title | Date | Key Decision |
|-----|-------|------|--------------|
| ADR-0005 | Pydantic v2 with extra="ignore" | 2025-12-08 | Forward compatibility via ignored unknown fields |
| ADR-0006 | NameGid as Standalone Frozen Model | 2025-12-08 | Frozen, hashable references with GID-based equality |
| ADR-0028 | Polars DataFrame Library | 2025-12-09 | Polars for 10-100x speedup and native lazy evaluation |
| ADR-0029 | Task Subclass Strategy | 2025-12-09 | Schema-driven composition with targeted inheritance |
| ADR-0030 | Custom Field Typing | 2025-12-09 | Static GID constants for MVP, configurable post-MVP |
| ADR-0033 | Schema Enforcement | 2025-12-09 | Strict Polars dtypes with logged coercion fallbacks |
| ADR-0049 | GID Validation Strategy | 2025-12-10 | Regex validation at track() time, supports temp GIDs |
| ADR-0051 | Custom Field Type Safety | 2025-12-11 | Property accessors delegating to CustomFieldAccessor |
| ADR-0078 | GID-Based Entity Identity Strategy | 2025-12-16 | GID as tracking key instead of id() |
| ADR-0082 | Fields Class Auto-Generation | 2025-12-16 | Two-phase registration via __set_name__ + __init_subclass__ |
| ADR-0083 | DateField Arrow Integration | 2025-12-16 | Arrow library for rich date handling |
| ADR-0098 | Dual Membership Model | 2025-12-17 | Hierarchy + pipeline project membership |
| ADR-0114 | Hours Model Backward Compatibility | 2025-12-18 | Deprecated aliases, clean break on types |
| ADR-SDK-005 | Pydantic Settings Standards | 2025-12-23 | Composite settings with env_prefix namespacing |

## Migration Guidance

### From dict[str, Any] to NameGid
```python
# Before
assignee_gid = task.assignee["gid"]  # Untyped dict access

# After
assignee_gid = task.assignee.gid  # Typed property access
```

### From pandas to Polars
```python
# Legacy (deprecated)
df = project.struc()  # Returns pandas.DataFrame

# New
df = project.to_dataframe()  # Returns polars.DataFrame

# Conversion if needed
pandas_df = df.to_pandas()
```

### Custom Field Property Updates
```python
# Before (direct CustomFieldAccessor)
business.get_custom_fields().set("Company ID", "ABC123")

# After (typed property)
business.company_id = "ABC123"  # Type-safe, change tracked
```

### Hours Model
```python
# Before (deprecated, emits warning)
hours.monday_hours  # Returns list[str], not str!

# After
times = hours.monday  # Returns list[str]
opening = times[0] if times else None
```

## Compliance Checklist

Model Development:
- [ ] New models inherit from `AsanaResource` or appropriate base
- [ ] `extra="ignore"` configuration preserved
- [ ] Custom field properties use descriptor pattern
- [ ] GID fields validated at track() time
- [ ] Fields class auto-generated from descriptors

DataFrame Layer:
- [ ] Schemas defined as data (composition), not classes
- [ ] Type coercion failures logged as warnings
- [ ] Extraction continues on individual field failures
- [ ] Polars dtypes strictly enforced

Testing:
- [ ] Settings reset via fixture before/after each test
- [ ] GID-based tracking tested for duplicate scenarios
- [ ] Type coercion success rate monitored (target: 99%)
- [ ] Deprecation warnings verified in tests
