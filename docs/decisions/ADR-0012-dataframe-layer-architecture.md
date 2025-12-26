# ADR-0012: DataFrame Layer Architecture

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0028, ADR-0029, ADR-0033, ADR-0098
- **Related**: reference/DATA-MODEL.md

## Context

The autom8_asana SDK needs to provide typed DataFrame output for task data extraction. The legacy `struc()` method returns pandas DataFrame, but several factors create pressure to evolve:

1. **Performance requirements**: Target 20-30% improvement over legacy `struc()`
2. **Type safety**: SDK emphasizes type safety via Pydantic models and strict typing
3. **Memory efficiency**: Large projects (10,000+ tasks) need efficient memory handling
4. **Lazy evaluation**: Threshold-based lazy evaluation for performance optimization
5. **Task type scalability**: Legacy autom8 monolith uses class inheritance for 50+ task types
6. **Entity hierarchy**: Business > Unit > Process hierarchy with dual project membership

The legacy pattern uses class inheritance for each task type with columns defined via `STRUC_COLS` class attribute, creating:
- Class explosion (50+ classes)
- Tight coupling (business logic mixed with data structure)
- Limited extensibility (adding types requires code changes)

## Decision

Implement a **schema-driven DataFrame layer using Polars with strict type enforcement**:

1. **Polars as primary DataFrame library** for performance and type safety
2. **Schema-driven composition** for data definitions, targeted inheritance for extraction logic
3. **Strict dtype enforcement** with logged coercion fallbacks
4. **Dual membership model** for entity hierarchy and pipeline visibility

### Polars DataFrame Layer

```python
import polars as pl

class Project:
    def to_dataframe(
        self,
        task_type: str | None = None,
        concurrency: int = 10,
        use_cache: bool = True,
        lazy: bool | None = None,
    ) -> pl.DataFrame:
        """Generate typed DataFrame from project tasks.

        Returns:
            Polars DataFrame with schema-defined columns.
        """
        ...

    def struc(self, ...) -> "pd.DataFrame":
        """DEPRECATED: Use to_dataframe() instead."""
        warnings.warn(...)
        return self.to_dataframe(...).to_pandas()
```

**Version Requirements:**
- Minimum Polars version: `>= 0.20.0`
- Python version: `>= 3.12`

### Schema-Driven Architecture

```python
from dataclasses import dataclass
import polars as pl

@dataclass(frozen=True)
class ColumnDef:
    """Single column definition - data, not behavior."""
    name: str
    dtype: pl.DataType
    nullable: bool = True
    source: str | None = None

@dataclass
class DataFrameSchema:
    """Schema is a data structure, not a class."""
    name: str
    task_type: str
    columns: list[ColumnDef]
    version: str = "1.0.0"

# Schemas defined as data, registered at runtime
BASE_SCHEMA = DataFrameSchema(
    name="base",
    task_type="*",
    columns=[
        ColumnDef("gid", pl.Utf8, nullable=False),
        ColumnDef("name", pl.Utf8, nullable=False),
        # ... 12 base columns
    ],
)

UNIT_SCHEMA = DataFrameSchema(
    name="unit",
    task_type="Unit",
    columns=[
        *BASE_SCHEMA.columns,  # Inherit base columns
        ColumnDef("mrr", pl.Decimal),
        ColumnDef("weekly_ad_spend", pl.Decimal),
        # ... 11 Unit-specific columns
    ],
)

# Registry uses composition pattern
class SchemaRegistry:
    _schemas: dict[str, DataFrameSchema] = {}

    @classmethod
    def register(cls, task_type: str, schema: DataFrameSchema) -> None:
        cls._schemas[task_type] = schema

    @classmethod
    def get_schema(cls, task_type: str) -> DataFrameSchema:
        if task_type not in cls._schemas:
            raise SchemaNotFoundError(task_type)
        return cls._schemas[task_type]
```

### Extractor Inheritance

```python
class BaseExtractor(ABC):
    """Inheritance for extraction LOGIC, not schema."""

    def __init__(self, schema: DataFrameSchema):
        self._schema = schema

    def _extract_base_fields(self, task: Task) -> dict:
        """Shared logic for 12 base fields."""
        return {
            "gid": task.gid,
            "name": task.name,
            "url": f"https://app.asana.com/0/0/{task.gid}",
            # ...
        }

    @abstractmethod
    def extract(self, task: Task) -> TaskRow:
        """Type-specific extraction logic."""
        ...

class UnitExtractor(BaseExtractor):
    """Unit-specific extraction with derived fields."""

    def extract(self, task: Task) -> UnitRow:
        base = self._extract_base_fields(task)
        return UnitRow(
            **base,
            mrr=self._extract_custom_field(task, MRR_GID),
            office=self._derive_office(task),  # Derived field logic
            vertical_id=self._derive_vertical_id(task),
        )
```

### Type Coercion with Logging

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
        """Coerce value to target type, fallback to null on failure."""
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

**Coercion Rules:**

| Expected Type | Actual Type | Coercion Behavior |
|---------------|-------------|-------------------|
| `pl.Decimal` | `str` (numeric) | Parse as Decimal |
| `pl.Decimal` | `str` (non-numeric) | -> `null`, warn |
| `pl.Datetime` | `str` (ISO format) | Parse as datetime |
| `pl.Datetime` | `str` (invalid) | -> `null`, warn |
| `pl.Boolean` | `str` ("true"/"false") | Parse as bool |
| `pl.Boolean` | `int` (0/1) | Convert to bool |
| `pl.Utf8` | `int` | Stringify |
| `pl.List(pl.Utf8)` | `str` | Wrap in list |

### Dual Membership Model

Process entities maintain two project memberships:

1. **Hierarchy membership** (via subtask relationship):
   - Process is subtask of ProcessHolder
   - Navigation works via cached refs: `process.unit.business`
   - EntityType detection uses parent inference

2. **Pipeline membership** (via add_to_project):
   - Process added to pipeline project
   - Section membership tracked in `memberships` array
   - ProcessType detection uses ProcessProjectRegistry lookup

**Multiple pipeline membership** returns `None` with warning log - treated as error condition.

## Rationale

### Why Polars Over pandas?

| Criterion | Polars | pandas | Winner |
|-----------|--------|--------|--------|
| **Execution speed** | 10-100x faster for common ops | Baseline | Polars |
| **Memory efficiency** | Arrow columnar, zero-copy | NumPy-backed, copies | Polars |
| **Lazy evaluation** | Native LazyFrame with query optimization | No native support | Polars |
| **Type strictness** | Enforced dtypes, early error detection | Permissive, silent coercion | Polars |
| **Multithreading** | Parallel by default | GIL-limited | Polars |
| **API consistency** | Method chaining, no index confusion | Mixed paradigms | Polars |

**Performance benchmarks:**

| Operation | Polars | pandas | Speedup |
|-----------|--------|--------|---------|
| CSV read (1GB) | ~2s | ~15s | 7.5x |
| Group-by aggregation | ~100ms | ~2s | 20x |
| Filter + select | ~50ms | ~500ms | 10x |
| Join (1M x 1M rows) | ~1s | ~10s | 10x |

These align with the 20-30% performance improvement target.

### Why Schema-Driven Composition?

**Separation of concerns**: What columns exist (schema) is separate from how values are extracted (extractor).

**Extensibility without code changes**: Post-MVP, new task types can be added via schema registration:
```python
# Post-MVP: Add new type via configuration
registry.register("NewType", DataFrameSchema(
    name="new_type",
    task_type="NewType",
    columns=[*BASE_SCHEMA.columns, ...],
))
```

**Avoids class explosion**: 50+ task types would mean 50+ subclasses. Schemas as data enable runtime registration without code changes.

**Clear data contracts**: Schemas explicitly declare the contract (columns, types, nullability).

### Why Strict Polars Dtypes?

**Type safety propagates to consumers**: DataFrame consumers can trust that `mrr` is always `Decimal`, not sometimes `str`:
```python
# Safe: mrr is always Decimal or null
df.select(pl.col("mrr") * 12)  # Annual revenue

# Unsafe (if types were permissive): Would fail at runtime
# pl.col("mrr") = "N/A" -> "N/AN/AN/A..."
```

**Catches data quality issues**: Type coercion failures indicate data quality problems (e.g., "N/A" in a number field). Logging these as warnings surfaces issues without breaking extraction.

**Null is type-safe**: Polars handles null values correctly. `null` is valid for any nullable column and propagates safely through operations.

### Why Dual Membership?

| Approach | Hierarchy Preserved | Pipeline Visible | Complexity |
|----------|--------------------:|:----------------:|:----------:|
| Subtask only | Yes | No (not in board view) | Low |
| Project only | No (loses navigation) | Yes | Medium |
| Dual membership | Yes | Yes | Medium |

Dual membership is the only approach that satisfies both requirements:
- Preserves full hierarchy navigation: `process.unit.business`
- Enables pipeline board view in Asana UI
- Leverages existing SaveSession.add_to_project()

## Alternatives Considered

### Alternative 1: pandas

- **Description**: Use pandas as DataFrame library, matching legacy `struc()`
- **Pros**: Zero migration effort; extensive ecosystem; more tutorials
- **Cons**: 10-100x slower; no native lazy evaluation; permissive typing hides errors; higher memory footprint
- **Why not chosen**: Performance requirements and user decision override familiarity concerns

### Alternative 2: Full Inheritance (Legacy Pattern)

- **Description**: Mirror legacy `STRUC_COLS` pattern with class inheritance for each task type
- **Pros**: Familiar pattern; IDE autocomplete on class attributes
- **Cons**: 50+ classes for all task types; schema changes require code changes; mixes data with behavior
- **Why not chosen**: Class explosion is unmaintainable; schema definitions should be data, not code structure

### Alternative 3: Pure Composition (No Inheritance)

- **Description**: No inheritance anywhere; all logic via composition and delegation
- **Pros**: Maximum flexibility; no inheritance complexity
- **Cons**: Loses type safety for extraction logic; no IDE autocomplete for extractor methods; derived field logic becomes awkward
- **Why not chosen**: Extraction logic genuinely benefits from inheritance for shared methods

### Alternative 4: Strict Failure (Fail Fast)

- **Description**: Raise exception on any type mismatch; abort extraction
- **Pros**: Forces data quality fixes; no silent data loss; clear failure mode
- **Cons**: One bad task fails entire project; fragile in production; violates error handling requirements
- **Why not chosen**: Production systems need robustness - one bad field shouldn't prevent all extraction

### Alternative 5: Project-Only Model

- **Description**: Move Process out of hierarchy into pipeline project only
- **Pros**: Simpler membership model
- **Cons**: Breaks navigation (`process.unit.business`); loses hierarchy benefits; unacceptable breaking change
- **Why not chosen**: Hierarchy navigation is essential to existing SDK patterns

## Consequences

### Positive

- **Performance**: 10-100x speedup for common operations enables meeting performance requirements
- **Memory efficiency**: Arrow backend reduces memory footprint for large projects
- **Native lazy evaluation**: Supports threshold-based optimization without workarounds
- **Type safety**: Strict dtype enforcement catches errors at DataFrame construction
- **Modern API**: Method chaining and consistent API reduce boilerplate
- **Scalable**: Can support 50+ task types without 50+ classes
- **Extensible**: Post-MVP types can be added via schema registration
- **Testable**: Schemas can be tested in isolation from extraction logic
- **Clear contracts**: Explicit schema definitions serve as documentation
- **Type-safe extraction**: Inheritance preserves IDE support and type checking for extractors
- **Preserves hierarchy navigation**: `process.unit.business` continues to work
- **Enables pipeline board view**: Process appears in Asana board view

### Negative

- **Learning curve**: Team members need to learn Polars idioms
- **Ecosystem integration**: Some libraries expect pandas (conversion overhead ~10-20ms)
- **Conversion overhead**: `.to_pandas()` for backward compatibility
- **Breaking change for legacy**: Consumers expecting pandas must migrate
- **Indirection**: Two concepts (schema + extractor) instead of one class
- **Dual lookup**: Builder must fetch schema AND create appropriate extractor
- **Data loss to null**: Uncoercible values become null (information lost)
- **Warning volume**: High-volume extractions may produce many warnings
- **Process memberships array grows**: 2+ entries per process
- **Multi-pipeline detection**: Adds complexity, requires consumer handling

### Neutral

- **pandas interoperability**: `.to_pandas()` and `pl.from_pandas()` enable bidirectional conversion
- **Documentation updates**: SDK docs must cover Polars API patterns
- **Testing adjustments**: Test assertions use Polars matchers instead of pandas
- **Pattern is established**: Registry + factory pattern is well-known
- **Pydantic row models**: Still have type-specific classes, but only for row models
- **Coercion logic complexity**: Rules for each type must be implemented and tested
- **Membership parsing**: Slightly more complex for dual membership

## Compliance

### DataFrame Library

1. **Code review checklist**: New DataFrame code uses Polars, not pandas
2. **No direct pandas imports**: In `dataframes/` package except for `struc()` wrapper
3. **Type annotations**: Public API returns `polars.DataFrame`, not `pandas.DataFrame`
4. **Test coverage**: Integration tests verify Polars output; deprecation tests verify pandas conversion

### Schema Architecture

1. **Code review checklist**: Schema definitions in `schemas/` package; extractors inherit from `BaseExtractor`
2. **Directory structure**:
   ```
   dataframes/
   ├── schemas/      # DATA definitions only
   │   ├── base.py
   │   ├── unit.py
   │   └── contact.py
   └── extractors/   # LOGIC only
       ├── base.py
       ├── unit.py
       └── contact.py
   ```

### Type Enforcement

1. **All extraction paths**: Use `TypeCoercer` for type handling
2. **Coercion failures**: Logged as warnings (not errors)
3. **Extraction continues**: After coercion failure
4. **Metrics**: `dataframe_coercion_failures_total` counter; `dataframe_coercion_success_rate` gauge; alert if success rate < 99%

### Dual Membership

1. **add_to_pipeline()**: Uses `SaveSession.add_to_project()`
2. **ProcessProjectRegistry**: Lookup for pipeline project GIDs
3. **Multi-pipeline detection**: Returns None with warning log including process_gid and project GIDs
