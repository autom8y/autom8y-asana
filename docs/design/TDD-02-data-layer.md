# TDD-02: Data Layer Architecture

> Consolidated Technical Design Document covering Pydantic models, Polars dataframes, and schema design.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-0002, TDD-0009, TDD-0009.1
- **Related ADRs**: ADR-0010, ADR-0011, ADR-0012

---

## Overview

The Data Layer provides typed data structures and transformation capabilities for the autom8_asana SDK. It encompasses three interconnected concerns:

1. **Core Models**: Pydantic-based models for Asana resources with type-safe reference handling and pagination infrastructure
2. **DataFrame Layer**: Polars-based typed dataframe generation with schema-driven extraction
3. **Dynamic Resolution**: Runtime custom field resolution eliminating static GID dependencies

The architecture prioritizes type safety, forward compatibility with Asana API changes, and performance optimization through lazy evaluation and caching.

---

## Design Goals

| Goal | Description | Key Mechanism |
|------|-------------|---------------|
| **Type Safety** | Compile-time and runtime type checking for all data structures | Pydantic models, Polars dtypes |
| **Forward Compatibility** | SDK survives Asana API additions without code changes | `extra="ignore"` configuration |
| **Performance** | 20-30% improvement over legacy `struc()` method | Polars, lazy evaluation, caching |
| **Extensibility** | New task types without code changes | Schema registry, dynamic resolution |
| **Memory Efficiency** | Handle large projects (10,000+ tasks) efficiently | Arrow columnar format, single-page buffering |

---

## Model Architecture

### Base Model Configuration

All Asana API resource models inherit from `AsanaResource` with standardized Pydantic v2 configuration:

```python
from pydantic import BaseModel, ConfigDict

class AsanaResource(BaseModel):
    model_config = ConfigDict(
        extra="ignore",           # Forward compatibility - new API fields don't break
        populate_by_name=True,    # Support field aliases (API vs Python names)
        str_strip_whitespace=True # Normalize string inputs
    )

    gid: str
    resource_type: str
```

**Configuration Rationale:**

| Setting | Purpose | Benefit |
|---------|---------|---------|
| `extra="ignore"` | Discard unknown fields from API | Production resilience to API changes |
| `populate_by_name=True` | Accept both alias and field name | API format flexibility |
| `str_strip_whitespace=True` | Normalize string inputs | Data cleanliness |

### NameGid Reference Model

Lightweight frozen model for Asana resource references (assignee, followers, projects):

```python
class NameGid(BaseModel):
    model_config = ConfigDict(
        frozen=True,     # Immutable - enables hashing
        extra="ignore",  # Forward compatibility
    )

    gid: str
    name: str | None = None
    resource_type: str | None = None

    def __hash__(self) -> int:
        return hash(self.gid)  # Identity by GID

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NameGid):
            return self.gid == other.gid
        return NotImplemented
```

**Why NameGid is standalone (not inheriting from AsanaResource):**

| Property | NameGid | AsanaResource |
|----------|---------|---------------|
| Purpose | Reference to resource | Full resource representation |
| Frozen | Yes (immutable) | No (mutable) |
| Hashable | Yes (dict keys, sets) | No |
| Equality | By GID only | By all fields |

**Usage patterns enabled:**

```python
# Deduplicate followers across tasks
all_followers = {f for task in tasks for f in task.followers or []}

# Use as dict keys
user_task_count = {task.assignee: 0 for task in tasks if task.assignee}

# Access via attributes, not dict
print(task.assignee.name)  # Not task.assignee["name"]
```

### PageIterator for Pagination

Generic async iterator for automatic pagination of Asana list operations:

```python
class PageIterator(Generic[T]):
    """Async iterator for paginated API responses.

    Features:
    - Single-page buffer for memory efficiency
    - Lazy fetching as iteration progresses
    - Helper methods: collect(), first(), take(n)
    """

    def __init__(
        self,
        fetch_page: Callable[[str | None], Awaitable[tuple[list[T], str | None]]],
        page_size: int = 100,
    ) -> None:
        self._fetch_page = fetch_page
        self._buffer: list[T] = []
        self._next_offset: str | None = None
        self._exhausted = False

    async def __anext__(self) -> T:
        if not self._buffer and not self._exhausted:
            await self._fetch_next_page()
        if self._buffer:
            return self._buffer.pop(0)
        raise StopAsyncIteration

    async def collect(self) -> list[T]:
        """Collect all items into a list."""
        return [item async for item in self]

    async def first(self) -> T | None:
        """Get the first item, or None if empty."""
        try:
            return await self.__anext__()
        except StopAsyncIteration:
            return None

    async def take(self, n: int) -> list[T]:
        """Take up to n items."""
        result = []
        async for item in self:
            if len(result) >= n:
                break
            result.append(item)
        return result
```

### ItemLoader Protocol

Protocol for lazy loading additional resource data (SDK provides protocol; consumers implement):

```python
class ItemLoader(Protocol):
    """Protocol for lazy loading additional resource data.

    SDK provides the protocol; autom8 monolith or other consumers
    implement based on their caching and API access patterns.
    """

    async def load_async(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Load additional data for a resource."""
        ...

    def load(
        self,
        resource: AsanaResource,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sync version of load_async."""
        ...
```

---

## DataFrame Layer

### Package Structure

```
src/autom8_asana/dataframes/
├── __init__.py              # Public API exports
├── models/
│   ├── task_row.py          # TaskRow, UnitRow, ContactRow
│   ├── schema.py            # ColumnDef, DataFrameSchema
│   └── registry.py          # SchemaRegistry singleton
├── schemas/
│   ├── base.py              # BASE_SCHEMA (12 columns)
│   ├── unit.py              # UNIT_SCHEMA (23 columns)
│   └── contact.py           # CONTACT_SCHEMA (21 columns)
├── extractors/
│   ├── base.py              # BaseExtractor (abstract)
│   ├── unit.py              # UnitExtractor
│   └── contact.py           # ContactExtractor
├── builders/
│   ├── section.py           # SectionDataFrameBuilder
│   └── project.py           # ProjectDataFrameBuilder
├── resolver/
│   ├── protocol.py          # CustomFieldResolver protocol
│   ├── normalizer.py        # NameNormalizer
│   ├── default.py           # DefaultCustomFieldResolver
│   └── mock.py              # MockCustomFieldResolver (testing)
├── cache_integration.py     # Bridge to STRUC cache
├── coercion.py              # TypeCoercer for schema enforcement
└── deprecation.py           # struc() wrapper
```

### Schema Definition

Schemas are data structures, not classes:

```python
from dataclasses import dataclass
import polars as pl

@dataclass(frozen=True)
class ColumnDef:
    """Single column definition."""
    name: str
    dtype: pl.DataType
    nullable: bool = True
    source: str | None = None       # Resolution source (cf:, gid:, attribute)
    extractor: Callable | None = None
    description: str | None = None

@dataclass
class DataFrameSchema:
    """Complete schema with columns and versioning."""
    name: str
    task_type: str
    columns: list[ColumnDef]
    version: str = "1.0.0"

    def to_polars_schema(self) -> dict[str, pl.DataType]:
        """Convert to Polars schema dict for DataFrame construction."""
        return {col.name: col.dtype for col in self.columns}
```

### Column Source Convention

The `source` attribute uses prefixes to indicate resolution strategy:

| Prefix | Meaning | Example |
|--------|---------|---------|
| `None` | Derived field (custom extractor logic) | `source=None` |
| `"cf:{name}"` | Custom field by name (dynamic resolution) | `source="cf:MRR"` |
| `"gid:{gid}"` | Explicit GID (bypass resolution) | `source="gid:123456"` |
| No prefix | Attribute path on task model | `source="created_at"` |

### Schema Registry

Singleton registry for task-type to schema mapping:

```python
class SchemaRegistry:
    """Singleton with lazy initialization and runtime registration."""

    _instance: ClassVar["SchemaRegistry | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def get_schema(self, task_type: str) -> DataFrameSchema:
        """Get schema for task type, falling back to base schema."""
        self._ensure_initialized()
        return self._schemas.get(task_type) or self._schemas["*"]

    def register(self, task_type: str, schema: DataFrameSchema) -> None:
        """Register schema for task type (enables post-MVP extensibility)."""
        self._schemas[task_type] = schema
```

### Row Models

Typed Pydantic models for extracted rows:

```python
class TaskRow(BaseModel):
    """Base row model for all task types (12 columns)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    gid: str
    name: str
    type: str
    date: date | None = None
    created: datetime
    due_on: date | None = None
    is_completed: bool
    completed_at: datetime | None = None
    url: str
    last_modified: datetime
    section: str | None = None
    tags: list[str] = Field(default_factory=list)

class UnitRow(TaskRow):
    """Unit-specific row with 11 additional fields."""
    type: str = "Unit"

    # Direct custom fields
    mrr: Decimal | None = None
    weekly_ad_spend: Decimal | None = None
    products: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    discount: Decimal | None = None

    # Derived fields
    office: str | None = None
    vertical: str | None = None
    vertical_id: str | None = None
    specialty: str | None = None
    max_pipeline_stage: str | None = None

class ContactRow(TaskRow):
    """Contact-specific row with 9 additional fields."""
    type: str = "Contact"

    full_name: str | None = None
    nickname: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    position: str | None = None
    employee_id: str | None = None
    contact_url: str | None = None
    time_zone: str | None = None
    city: str | None = None
```

### Public API

```python
class Project:
    def to_dataframe(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
        sections: list[str] | None = None,
        completed: bool | None = None,
        since: date | None = None,
        lazy: bool | None = None,
        incremental: bool = False,
    ) -> pl.DataFrame:
        """Generate typed DataFrame from project tasks.

        Args:
            task_type: Filter to specific type (Unit, Contact). None = all.
            concurrency: Max concurrent extraction workers.
            use_cache: Whether to use STRUC cache.
            sections: Filter by section names.
            completed: Filter by completion status.
            since: Filter by modified_at >= since.
            lazy: Evaluation mode. None = auto (100-task threshold).
            incremental: Use story-based incremental refresh.

        Returns:
            Polars DataFrame with schema-defined columns.
        """
        ...

    def struc(self, ...) -> "pd.DataFrame":
        """DEPRECATED: Use to_dataframe() instead."""
        warnings.warn(
            "struc() is deprecated. Use to_dataframe() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.to_dataframe(...).to_pandas()
```

---

## Dynamic Resolution

### Problem Statement

Static GID placeholders create environment coupling:

```python
# Legacy approach - requires manual GID population per environment
MRR_GID = "PLACEHOLDER_MRR_GID"  # Must be replaced before use
value = extract_by_gid(task, MRR_GID)
```

### Solution: Name-Based Resolution

Dynamic resolution maps schema field names to GIDs at runtime using the task's existing `custom_fields` list:

```python
class NameNormalizer:
    """Normalize field names for matching.

    Examples:
    - "Weekly Ad Spend" -> "weeklyadspend"
    - "weekly_ad_spend" -> "weeklyadspend"
    - "MRR" -> "mrr"
    """

    @staticmethod
    @lru_cache(maxsize=1024)
    def normalize(name: str) -> str:
        if not name:
            return ""
        return re.sub(r'[^a-z0-9]', '', name.lower())
```

### CustomFieldResolver Protocol

```python
class CustomFieldResolver(Protocol):
    """Protocol for custom field name resolution."""

    def build_index(self, custom_fields: list[CustomField]) -> None:
        """Build name->gid index from first task's custom_fields."""
        ...

    def resolve(self, field_name: str) -> str | None:
        """Resolve field name to GID. Returns None if not found."""
        ...

    def get_value(
        self,
        task: Task,
        field_name: str,
        expected_type: type | None = None,
    ) -> Any:
        """Extract custom field value, optionally coerced to type."""
        ...

    def has_field(self, field_name: str) -> bool:
        """Check if field is resolvable."""
        ...
```

### Default Implementation

```python
class DefaultCustomFieldResolver:
    """Builds index from first task, uses for all lookups."""

    def __init__(self, strict: bool = False):
        self._strict = strict
        self._index: dict[str, str] = {}  # normalized_name -> gid
        self._built = False
        self._lock = threading.RLock()

    def build_index(self, custom_fields: list[CustomField]) -> None:
        if self._built:
            return

        with self._lock:
            if self._built:
                return

            for cf in custom_fields:
                if cf.gid and cf.name:
                    normalized = NameNormalizer.normalize(cf.name)
                    self._index[normalized] = cf.gid

            self._built = True

    def resolve(self, field_name: str) -> str | None:
        # Handle gid: prefix (explicit GID)
        if field_name.startswith("gid:"):
            return field_name[4:]

        # Handle cf: prefix (explicit custom field name)
        lookup_name = field_name[3:] if field_name.startswith("cf:") else field_name

        normalized = NameNormalizer.normalize(lookup_name)
        return self._index.get(normalized)
```

### Resolution Flow

```
First Task
    |
    | task.custom_fields = [
    |   {gid: "123", name: "MRR", type: "number"},
    |   {gid: "456", name: "Weekly Ad Spend", ...},
    | ]
    v
resolver.build_index(task.custom_fields)
    |
    | Result: _index = {"mrr": "123", "weeklyadspend": "456"}
    v
Subsequent Tasks
    |
    | Extraction for ColumnDef(name="mrr", source="cf:MRR")
    v
resolver.get_value(task, "cf:MRR", Decimal)
    |
    | 1. resolve("cf:MRR") -> "123"
    | 2. Find cf with gid="123" in task.custom_fields
    | 3. Extract and coerce to Decimal
    v
Return: Decimal("5000.0")
```

---

## Schema Enforcement

### TypeCoercer

Strict type enforcement with logged fallbacks:

```python
class TypeCoercer:
    """Type coercion with logging for schema enforcement."""

    def coerce(
        self,
        value: Any,
        target_dtype: pl.DataType,
        field_name: str,
        task_gid: str,
    ) -> Any:
        if value is None:
            return None

        try:
            return self._coerce_to_type(value, target_dtype)
        except (ValueError, TypeError, InvalidOperation) as e:
            self._log_coercion_warning(
                field_name=field_name,
                task_gid=task_gid,
                expected_type=target_dtype,
                actual_value=value,
                error=str(e),
            )
            return None  # Fallback to null
```

### Coercion Rules

| Expected Type | Actual Type | Behavior |
|---------------|-------------|----------|
| `pl.Decimal` | `str` (numeric) | Parse as Decimal |
| `pl.Decimal` | `str` (non-numeric) | -> `null`, warn |
| `pl.Datetime` | `str` (ISO format) | Parse as datetime |
| `pl.Datetime` | `str` (invalid) | -> `null`, warn |
| `pl.Boolean` | `str` ("true"/"false") | Parse as bool |
| `pl.Boolean` | `int` (0/1) | Convert to bool |
| `pl.Utf8` | `int` | Stringify |
| `pl.List(pl.Utf8)` | `str` | Wrap in list |

### Lazy vs Eager Evaluation

Threshold-based selection (default: 100 tasks):

```python
if lazy is not None:
    use_lazy = lazy
else:
    use_lazy = task_count > 100

if use_lazy:
    lf = pl.LazyFrame([row.to_dict() for row in rows], schema=schema)
    df = lf.collect()  # Query optimization applied
else:
    df = pl.DataFrame([row.to_dict() for row in rows], schema=schema)
```

---

## Testing Strategy

### Unit Testing (Target: 90% coverage)

| Component | Focus Areas |
|-----------|-------------|
| NameGid | Validation, serialization, hashing, equality by GID |
| PageIterator | Empty results, single page, multi-page, helper methods |
| TaskRow models | Validation, to_dict(), field access |
| ColumnDef/Schema | Creation, to_polars_schema(), validation |
| SchemaRegistry | Singleton behavior, registration, get_schema() |
| NameNormalizer | All naming conventions (Title, snake, CAPS, hyphenated) |
| Resolver | Build index, resolve with prefixes, missing field handling |
| TypeCoercer | Each coercion rule, failure logging |

### Integration Testing (Target: 80% coverage)

| Scenario | Validation |
|----------|------------|
| End-to-end extraction | Mock tasks through full pipeline to DataFrame |
| Cache integration | Hit/miss flows with mocked CacheProvider |
| Concurrent extraction | Multiple tasks with semaphore limiting |
| Lazy vs eager | Both paths produce identical results |
| Deprecation wrapper | struc() produces pandas DataFrame with warning |
| Resolver with mock | Extraction works without Asana connection |

### Performance Targets

| Scenario | Target |
|----------|--------|
| 100 tasks, cold cache | < 5s |
| 100 tasks, warm cache | < 1s |
| 1000 tasks, cold cache | < 30s |
| 1000 tasks, warm cache | < 5s |
| Memory per 1000 tasks | < 100MB |
| Cache hit improvement | >= 50% reduction |

---

## Cross-References

### Related ADRs

| ADR | Topic | Relationship |
|-----|-------|--------------|
| ADR-0010 | Pydantic Model Foundation | Base configuration for all models |
| ADR-0011 | Entity Identity and Tracking | NameGid design, GID-based tracking |
| ADR-0012 | DataFrame Layer Architecture | Polars, schema-driven composition |
| ADR-0013 | Custom Field Type Safety | Type handling for custom fields |
| ADR-0014 | Backward Compatibility | struc() deprecation pattern |

### Related TDDs

| TDD | Topic | Relationship |
|-----|-------|--------------|
| TDD-01 | SDK Architecture | Foundation this layer builds on |
| TDD-03 | Caching | STRUC entry type, cache integration |
| TDD-05 | SaveSession | Entity tracking, change detection |

### Implementation Dependencies

```
TDD-02 Data Layer
    ├── depends on: TDD-01 SDK Architecture (AsanaResource base)
    ├── depends on: TDD-03 Caching (STRUC cache integration)
    └── consumed by: TDD-05 SaveSession (change tracking)
```

---

## Migration Notes

### From dict access to NameGid

```python
# Before
task.assignee["gid"]
task.assignee["name"]

# After
task.assignee.gid
task.assignee.name
```

### From struc() to to_dataframe()

```python
# Before (pandas)
df = project.struc(task_type="Unit")
df["mrr"].sum()

# After (Polars)
df = project.to_dataframe(task_type="Unit")
df.select(pl.col("mrr").sum())

# Compatibility bridge
df = project.to_dataframe(task_type="Unit").to_pandas()
```

### From static GIDs to dynamic resolution

```python
# Before (static)
MRR_GID = "1234567890"
value = extract_by_gid(task, MRR_GID)

# After (dynamic)
ColumnDef(name="mrr", source="cf:MRR", ...)
# Resolution happens automatically via CustomFieldResolver
```
