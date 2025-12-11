# ADR-0029: Task Subclass Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-09
- **Deciders**: Architect, Principal Engineer, autom8 team
- **Related**: [PRD-0003](../requirements/PRD-0003-structured-dataframe-layer.md), [TDD-0009](../design/TDD-0009-structured-dataframe-layer.md)

## Context

The legacy autom8 monolith uses class inheritance for task type specialization. Each task type (Unit, Contact, Offer, etc.) is a Python class inheriting from a base `Task` class, with type-specific columns defined via a `STRUC_COLS` class attribute:

```python
# Legacy pattern (autom8 monolith)
class Task:
    STRUC_COLS = []  # Base columns

class Unit(Task):
    STRUC_COLS = [
        "mrr",
        "weekly_ad_spend",
        "products",
        "languages",
        "discount",
    ]

class Contact(Task):
    STRUC_COLS = [
        "full_name",
        "nickname",
        "contact_phone",
        "contact_email",
        "position",
        "employee_id",
        "contact_url",
        "time_zone",
        "city",
    ]

# ... 50+ other subclasses
```

This pattern creates several challenges for the SDK:

1. **Class explosion**: 50+ task type classes, each requiring maintenance
2. **Tight coupling**: Business logic mixed with data structure definitions
3. **Limited extensibility**: Adding a new type requires code changes and deployment
4. **MVP scope conflict**: Only Unit and Contact are in MVP; others come later
5. **Schema vs. behavior conflation**: Column definitions mixed with extraction logic

PRD-0003 requires supporting MVP types (Unit, Contact) with a path to extensibility for the remaining 50+ types post-MVP.

### Forces at Play

| Force | Pull Toward |
|-------|-------------|
| Type safety for extraction | Inheritance (typed extractors) |
| Extensibility | Composition (schema registry) |
| Avoiding class explosion | Composition |
| Legacy pattern familiarity | Inheritance |
| Runtime type registration | Composition |
| IDE support/autocomplete | Inheritance |
| Clear data contracts | Composition (explicit schemas) |

## Decision

**Use schema-driven composition with targeted inheritance for extraction logic only.** Specifically:

1. **Schema definitions** (what columns exist) are **data**, not classes
2. **Extractor classes** (how to extract values) use inheritance for shared logic
3. **TaskRow models** use inheritance for type-safe Pydantic models

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SCHEMA-DRIVEN COMPOSITION                            │
└─────────────────────────────────────────────────────────────────────────────┘

  DATA LAYER (Composition)                    LOGIC LAYER (Inheritance)
  ────────────────────────                    ────────────────────────

  ┌─────────────────────┐                     ┌─────────────────────┐
  │   SchemaRegistry    │                     │   BaseExtractor     │
  │   (singleton)       │                     │   (abstract)        │
  └──────────┬──────────┘                     └──────────┬──────────┘
             │                                           │
    ┌────────┼────────┐                        ┌─────────┼─────────┐
    │        │        │                        │         │         │
    ▼        ▼        ▼                        ▼         ▼         ▼
┌───────┐┌───────┐┌───────┐              ┌─────────┐┌─────────┐┌─────────┐
│ Unit  ││Contact││ Base  │              │  Unit   ││ Contact ││ Base    │
│ Schema││Schema ││Schema │              │Extractor││Extractor││Extractor│
└───────┘└───────┘└───────┘              └─────────┘└─────────┘└─────────┘
   │         │        │                        │         │         │
   │         │        │                        │         │         │
   ▼         ▼        ▼                        ▼         ▼         ▼
  ColumnDef instances                     Extract methods with
  (name, dtype, source)                   type-specific logic
```

### Implementation

```python
# Schema definitions as DATA (composition)
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

# Registry as composition pattern
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

# Extractors use inheritance for shared logic
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

    def _derive_office(self, task: Task) -> str | None:
        """Type-specific derivation logic."""
        ...
```

## Rationale

### Why Schema-Driven Composition?

**1. Separation of concerns**: What columns exist (schema) is separate from how values are extracted (extractor). This makes each easier to test and maintain.

**2. Extensibility without code changes**: Post-MVP, new task types can be added via schema registration without new class definitions:

```python
# Post-MVP: Add new type via configuration
registry.register("NewType", DataFrameSchema(
    name="new_type",
    task_type="NewType",
    columns=[*BASE_SCHEMA.columns, ...],
))
```

**3. Avoids 50+ class explosion**: The legacy pattern would require 50+ subclasses for all task types. With composition, schemas are data structures that can be loaded from configuration.

**4. Clear data contracts**: Schemas explicitly declare the contract (columns, types, nullability). This enables:
- Schema validation at startup
- Schema export for documentation (`schema.to_dict()`)
- Schema versioning for cache compatibility

**5. IDE support preserved**: Type-specific extractors still provide autocomplete and type checking for the extraction logic that needs it.

### Why Inheritance for Extractors?

Extraction logic genuinely benefits from inheritance:

1. **Shared base field extraction**: All 12 base fields are extracted the same way
2. **Custom field helper methods**: `_extract_custom_field()` is common logic
3. **Type-specific overrides**: Derived fields (`office`, `vertical_id`) need specialized logic
4. **Clear responsibility**: Extractors know HOW to extract; schemas know WHAT to extract

### Why Pydantic Inheritance for Row Models?

```python
class TaskRow(BaseModel):
    """Base row with 12 fields."""
    gid: str
    name: str
    # ... 12 fields

class UnitRow(TaskRow):
    """Unit adds 11 fields."""
    mrr: Decimal | None = None
    # ... 11 fields
```

This provides:
- Type safety for row construction
- IDE autocomplete for field access
- Validation on construction
- Clear type hierarchy for return type annotations

## Alternatives Considered

### Alternative 1: Full Inheritance (Legacy Pattern)

- **Description**: Mirror the legacy `STRUC_COLS` pattern with class inheritance for each task type.

```python
class Task:
    STRUC_COLS: ClassVar[list[str]] = []

class Unit(Task):
    STRUC_COLS = ["mrr", "weekly_ad_spend", ...]

class Contact(Task):
    STRUC_COLS = ["full_name", "nickname", ...]
```

- **Pros**:
  - Familiar pattern from legacy code
  - IDE autocomplete on class attributes
  - Type inference from class hierarchy
- **Cons**:
  - 50+ classes for all task types
  - Schema changes require code changes
  - Mixes data (columns) with behavior
  - No runtime schema registration
  - Harder to test schemas in isolation
- **Why not chosen**: Class explosion is unmaintainable. Schema definitions should be data, not code structure. Extensibility requires composition pattern.

### Alternative 2: Pure Composition (No Inheritance)

- **Description**: No inheritance anywhere; all logic via composition and delegation.

```python
class Extractor:
    def __init__(self, schema: DataFrameSchema, field_extractors: dict):
        self._schema = schema
        self._extractors = field_extractors  # Composition

    def extract(self, task: Task) -> dict:
        return {
            col.name: self._extractors[col.name](task)
            for col in self._schema.columns
        }
```

- **Pros**:
  - Maximum flexibility
  - No inheritance complexity
  - Easy to compose extractors dynamically
- **Cons**:
  - Loses type safety for extraction logic
  - No IDE autocomplete for extractor methods
  - Derived field logic becomes awkward (where does `_derive_office` live?)
  - Less discoverable code structure
- **Why not chosen**: Extraction logic genuinely benefits from inheritance for shared methods. Pure composition loses type safety and discoverability.

### Alternative 3: Code Generation

- **Description**: Generate task type classes from schema definitions at build time.

```python
# Generate from YAML/JSON schema:
# task_types:
#   Unit:
#     columns: [mrr, weekly_ad_spend, ...]
#   Contact:
#     columns: [full_name, nickname, ...]
```

- **Pros**:
  - Schema as configuration
  - Generated code is type-safe
  - Consistent structure
- **Cons**:
  - Build step complexity
  - Generated code harder to debug
  - IDE support depends on when generation runs
  - Over-engineering for MVP scope (2 types)
- **Why not chosen**: Complexity not justified for MVP. Post-MVP, runtime schema registration is simpler than code generation.

### Alternative 4: Dynamic Attribute Access

- **Description**: Single `TaskRow` class with dynamic attribute access based on schema.

```python
class TaskRow:
    def __init__(self, schema: DataFrameSchema, data: dict):
        self._schema = schema
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"No field: {name}")
```

- **Pros**:
  - One class for all types
  - Fully dynamic
  - Schema-driven access
- **Cons**:
  - No type safety (returns `Any`)
  - No IDE autocomplete
  - No Pydantic validation
  - Debugging harder
- **Why not chosen**: Defeats the purpose of typed DataFrames. Type safety is a core requirement.

## Consequences

### Positive

- **Scalable**: Can support 50+ task types without 50+ classes
- **Extensible**: Post-MVP types can be added via schema registration
- **Testable**: Schemas can be tested in isolation from extraction logic
- **Clear contracts**: Explicit schema definitions serve as documentation
- **Type-safe extraction**: Inheritance preserves IDE support and type checking for extractors
- **Type-safe rows**: Pydantic models validate row construction
- **Separation of concerns**: What vs how are cleanly separated

### Negative

- **Indirection**: Two concepts (schema + extractor) instead of one class
- **Learning curve**: Developers must understand composition pattern
- **Dual lookup**: Builder must fetch schema AND create appropriate extractor
- **Migration complexity**: Cannot directly port legacy `STRUC_COLS` pattern

### Neutral

- **Pattern is established**: Registry + factory pattern is well-known
- **Pydantic row models**: Still have type-specific classes, but only for row models
- **MVP scope unchanged**: Still implementing Unit + Contact extractors specifically

## Compliance

### How This Decision Is Enforced

1. **Code review checklist**:
   - [ ] Schema definitions in `schemas/` package, not in extractor classes
   - [ ] Extractors inherit from `BaseExtractor`
   - [ ] No `STRUC_COLS` class attributes
   - [ ] Schema changes increment schema version

2. **Architectural tests**:
   ```python
   def test_schemas_are_registered():
       """All schema files register with SchemaRegistry."""
       for schema_file in glob("schemas/*.py"):
           # Verify schema registration
           ...

   def test_extractors_inherit_base():
       """All extractors inherit from BaseExtractor."""
       for extractor_class in get_extractor_classes():
           assert issubclass(extractor_class, BaseExtractor)
   ```

3. **Directory structure enforcement**:
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

4. **PR template**:
   - When adding a new task type:
     - [ ] Schema defined in `schemas/`
     - [ ] Extractor defined in `extractors/`
     - [ ] Schema registered in registry
     - [ ] Row model created in `models/task_row.py`
