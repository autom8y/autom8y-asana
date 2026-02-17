# TDD: Entity DataFrame Completeness & Extensibility

```yaml
id: TDD-ENTITY-EXT-001
status: DRAFT
date: 2026-02-17
author: architect
prd: PRD-ENTITY-EXT-001
impact: high
impact_categories: [data_model, api_contract]
```

---

## 1. Architecture Decision Record (ADR)

### ADR-001: Wiring Architecture Selection

**Status:** DECIDED

**Context:** 4 of 6 entity DataFrame schemas crash when consumers call `to_dataframe()` because `_create_extractor()` has no matching `case` branch and falls through to `DefaultExtractor`, which uses `TaskRow(extra="forbid")` and rejects entity-specific columns. Three candidate architectures were evaluated to prevent this class of bug and reduce future boilerplate.

**Decision:** **Option C (test-only enforcement) with SchemaExtractor as the core mechanism.** No wiring architecture changes to EntityDescriptor or new registry abstractions.

**Rationale:** The analysis below demonstrates why this is the correct decision for this system at this time.

### 1.1 MUST-PASS Criteria Evaluation

| # | Criterion | (a) Descriptor-Driven | (b) DataFrameTriad | (c) Test-Only + SchemaExtractor |
|---|-----------|----------------------|--------------------|---------------------------------|
| MP-1 | No circular import deadlocks | PASS -- deferred imports in function bodies | PASS -- `triads/__init__.py` imports at module load within `dataframes/`; no cross to `core/` | PASS -- SchemaExtractor lives in `dataframes/extractors/`; zero new cross-boundary imports |
| MP-2 | All 8588+ tests pass without modification | PASS -- additive fields on EntityDescriptor | CONDITIONAL -- requires verifying no test imports `from dataframes.triads`; new `__init__.py` runs `_register_all()` at import | PASS -- only new file is `extractors/schema.py` and a modified `case _:` branch; no test logic changes |
| MP-3 | All 5 broken schemas produce DataFrames | PASS -- requires creating 5 extractors or a generic fallback | PASS -- same requirement | PASS -- SchemaExtractor IS the generic fallback; wired in `case _:` |

**Verdict:** All three options pass MUST-PASS criteria. Option C passes with the least risk and fewest moving parts.

### 1.2 EVALUATION Criteria Scoring Matrix

| # | Criterion | Weight | (a) Descriptor | (b) Triad | (c) Test-Only |
|---|-----------|--------|----------------|-----------|---------------|
| EV-1 | Startup time impact | HIGH | **3/5** -- `_validate_registry_integrity()` would resolve up to 21 dotted-path imports at module load time. Measurable Lambda cold start regression. | **4/5** -- `_register_all()` triggers schema/extractor imports when `triads/__init__.py` loads. Deferred if never imported. | **5/5** -- Zero import-time cost. SchemaExtractor is imported only in `_create_extractor()` when actually needed. Completeness test runs only in CI. |
| EV-2 | IDE refactoring support | MEDIUM | **2/5** -- 3 new dotted-path strings per entity (68 total across 17 descriptors). Not discoverable by IDE rename/find-all-references. | **5/5** -- Real Python imports in triad files. IDE rename, find-references, and import validation all work. | **4/5** -- SchemaExtractor uses real imports. No dotted-path strings. The only string is the `task_type` passed to `_create_extractor()`, which is already the status quo. |
| EV-3 | God-object trajectory | MEDIUM | **2/5** -- EntityDescriptor grows from 21 to 25 fields. Sets precedent for activity_classifier_path, query_config, etc. At 30+ fields, becomes a maintenance liability. | **4/5** -- EntityDescriptor stays at 21 fields. TriadRegistry is a new 30-line abstraction, but scoped to dataframes/. | **5/5** -- EntityDescriptor unchanged. No new abstractions. The schema itself is the source of truth for its own extraction. |
| EV-4 | Test isolation | MEDIUM | **2/5** -- DataFrame tests using auto-wired `_create_extractor()` now transitively depend on entity_registry initialization. Requires registry fixtures in tests that previously needed none. | **3/5** -- DataFrame tests can import components directly, but TriadRegistry adds a new singleton to reset in conftest. | **5/5** -- DataFrame tests remain completely independent of entity_registry. SchemaExtractor is a regular class imported directly. No new singletons. |
| EV-5 | Incremental deployability | LOW | **4/5** -- Each phase (6 total) is independently deployable. But requires 6 PRs for full migration. | **3/5** -- Requires creating TriadRegistry infrastructure before any consumer can use it. 4-5 PRs. | **5/5** -- Single PR. SchemaExtractor + wiring change + completeness test + BUSINESS_SCHEMA fix. Done. |
| EV-6 | Matches existing patterns | LOW | **4/5** -- Extends `model_class_path` pattern already on EntityDescriptor. | **2/5** -- Introduces TriadRegistry, a new registry abstraction that does not exist in the codebase. | **4/5** -- SchemaExtractor follows the existing BaseExtractor/UnitExtractor/ContactExtractor inheritance pattern. `_create_extractor()` fallback modification follows existing match/case pattern. |

**Weighted Score Summary:**

| Option | HIGH (x3) | MEDIUM (x2) | LOW (x1) | Total |
|--------|-----------|-------------|----------|-------|
| (a) Descriptor | 9 | 12 | 8 | 29 |
| (b) Triad | 12 | 24 | 5 | 41 |
| (c) Test-Only | 15 | 28 | 9 | **52** |

### 1.3 The Deciding Argument

The first-principles analysis (ANALYSIS-entity-extensibility-first-principles.md) identifies the critical insight that makes most wiring architecture moot:

> **SchemaExtractor makes the problem disappear at the source.** If `_create_extractor()` falls back to SchemaExtractor instead of DefaultExtractor, then any entity with a registered schema "just works" without any extractor, row model, or match/case branch. The 4 broken schemas are fixed by one class and one line change.

The remaining value proposition of Options (a) and (b) is "reducing shotgun surgery when adding future entities." But:

1. The entity count is 18 with near-zero growth rate (0-2 per year).
2. SchemaExtractor eliminates the need for per-entity extractors and row models for entities with only `cf:`, `cascade:`, and direct-attribute sources. This covers 4 of 7 schema-bearing entities and any realistic future entity.
3. A parametrized completeness test catches any remaining wiring gaps in CI.

The auto-wiring architecture (4-6 days of work) would save 0-20 minutes of future manual wiring. The ROI is negative.

### 1.4 Counter-Arguments Acknowledged

**"EntityDescriptor was built for this."** True -- the module docstring says "Adding a new entity type means adding one entry here." But SchemaExtractor achieves the same outcome (zero per-entity boilerplate for most entities) without adding fields to the descriptor. The descriptor's aspiration is satisfied by making the extraction layer generic, not by centralizing more metadata.

**"The completeness test is a weaker guard than import-time validation."** Agreed -- import-time validation catches issues at startup while the test catches them only in CI. However, per R1.1, import-time validation MUST NOT crash startup. So it can only warn. A warning that might be overlooked in logs is arguably weaker than a test that fails CI and blocks deployment. The completeness test is a hard gate; the import-time warning is a soft signal. We implement both.

**"Option (b) gives real imports and IDE support."** True, and this is the strongest argument for the Triad approach. However, the tradeoff is introducing a new abstraction layer (TriadRegistry, DataFrameTriad, triads/ directory with per-entity files) for a system with ~7 schema-bearing entities. The cognitive overhead of a new registry exceeds the IDE refactoring benefit at this scale.

---

## 2. SchemaExtractor Design

### 2.1 Class Hierarchy

```
BaseExtractor (ABC)
  |
  +-- UnitExtractor        (existing, hand-coded, 23 fields)
  +-- ContactExtractor     (existing, hand-coded, 25 fields)
  +-- DefaultExtractor     (existing, 12 base fields only)
  +-- SchemaExtractor      (NEW, any schema, dynamic row model)
```

### 2.2 File Location

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/schema.py`

### 2.3 Full Class Specification

```python
"""Schema-driven generic extractor using dynamic Pydantic row models.

Per TDD-ENTITY-EXT-001: SchemaExtractor dynamically generates a Pydantic
row model from any DataFrameSchema, eliminating the need for per-entity
extractor and row model boilerplate for entities whose schemas contain
only cf:, cascade:, gid:, and direct-attribute sources.

Entities with custom derived field logic (source=None columns needing
traversal or computation) still require hand-coded extractors (e.g.,
UnitExtractor for _extract_office_async).
"""

from __future__ import annotations

import datetime as dt
import threading
from typing import TYPE_CHECKING, Any

from pydantic import Field, create_model

from autom8_asana.dataframes.extractors.base import BaseExtractor
from autom8_asana.dataframes.models.task_row import TaskRow

if TYPE_CHECKING:
    from autom8_asana.dataframes.models.schema import DataFrameSchema


# Module-level cache: schema task_type -> dynamically created model class
_MODEL_CACHE: dict[str, type[TaskRow]] = {}
_MODEL_CACHE_LOCK = threading.Lock()

# Dtype string -> (Python type, default value) mapping
# Covers all dtype strings used in existing schemas (PRD Section 10)
DTYPE_MAP: dict[str, tuple[type, Any]] = {
    "Utf8": (str, None),
    "String": (str, None),
    "Int64": (int, None),
    "Float64": (float, None),
    "Boolean": (bool, None),
    "Date": (dt.date, None),
    "Datetime": (dt.datetime, None),
    "Decimal": (float, None),  # Polars maps Decimal->Float64; Python float suffices
    "List[Utf8]": (list[str], []),  # Default empty list, not None
    "List[String]": (list[str], []),
}


class SchemaExtractor(BaseExtractor):
    """Generic extractor that works with any DataFrameSchema.

    Dynamically generates a Pydantic row model from the schema's ColumnDefs,
    enabling extraction for any entity type without a dedicated extractor class.

    The dynamic model:
    - Inherits from TaskRow (gets the 12 base fields and to_dict())
    - Adds Optional fields for each schema column beyond the base 12
    - Uses create_model() for field generation, cached per schema task_type
    - Sets model_config with extra="allow" on the dynamic subclass to
      accept the entity-specific columns that TaskRow(extra="forbid") rejects

    Thread Safety:
        The dynamic model is generated once per schema task_type and cached
        in a module-level dict protected by threading.Lock. Concurrent calls
        to _build_dynamic_row_model() are safe.

    Attributes:
        schema: DataFrameSchema defining columns to extract
        resolver: Optional CustomFieldResolver for cf:/gid: fields
        client: Optional AsanaClient for cascade: field resolution
    """

    def _create_row(self, data: dict[str, Any]) -> TaskRow:
        """Create a dynamically-generated row model from extracted data.

        Sets the type field to schema.task_type and converts None lists
        to empty lists for List-typed fields (matching UnitRow/ContactRow
        behavior).

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            Instance of the dynamically-generated TaskRow subclass
        """
        # Set type to match schema
        data["type"] = self._schema.task_type

        # Convert None lists to empty lists for all List-typed columns
        for col in self._schema.columns:
            if col.dtype in ("List[Utf8]", "List[String]") and data.get(col.name) is None:
                data[col.name] = []

        model_class = self._build_dynamic_row_model()
        return model_class.model_validate(data)

    def _extract_type(self, task: Any) -> str:
        """Return the schema's task_type as the type discriminator.

        Args:
            task: Task to extract from (unused -- type is schema-defined)

        Returns:
            Schema task_type string (e.g., "Offer", "AssetEdit")
        """
        return self._schema.task_type

    def _build_dynamic_row_model(self) -> type[TaskRow]:
        """Build or retrieve cached Pydantic model matching the schema.

        Uses pydantic.create_model() to generate a TaskRow subclass with
        fields for each column beyond the base 12. The model is cached
        per schema task_type in a thread-safe module-level dict.

        Returns:
            Dynamically-generated type[TaskRow] with all schema columns
        """
        cache_key = self._schema.task_type

        # Fast path: check cache without lock
        if cache_key in _MODEL_CACHE:
            return _MODEL_CACHE[cache_key]

        # Slow path: build model under lock
        with _MODEL_CACHE_LOCK:
            # Double-checked locking
            if cache_key in _MODEL_CACHE:
                return _MODEL_CACHE[cache_key]

            base_field_names = set(TaskRow.model_fields.keys())
            extra_fields: dict[str, Any] = {}

            for col in self._schema.columns:
                if col.name in base_field_names:
                    continue  # Skip base 12 fields -- already on TaskRow

                python_type, default = DTYPE_MAP.get(col.dtype, (str, None))

                if col.dtype in ("List[Utf8]", "List[String]"):
                    # List fields use Field(default_factory=list) for safety
                    extra_fields[col.name] = (
                        python_type | None,
                        Field(default_factory=list),
                    )
                else:
                    # All other fields are Optional with None default
                    extra_fields[col.name] = (python_type | None, None)

            model_name = f"{self._schema.task_type}SchemaRow"

            # Create model with extra="allow" to accept dynamic fields
            # that TaskRow's extra="forbid" would reject
            DynamicModel = create_model(
                model_name,
                __base__=TaskRow,
                __config__=None,  # Will be overridden below
                **extra_fields,
            )
            # Override the model_config to allow extra fields on THIS subclass
            # while keeping TaskRow's config for its own direct usage
            DynamicModel.model_config["extra"] = "ignore"
            DynamicModel.model_config["strict"] = False

            _MODEL_CACHE[cache_key] = DynamicModel
            return DynamicModel
```

### 2.4 Design Decisions

**Why `extra="ignore"` instead of `extra="forbid"` on the dynamic model?**
The dynamic model declares fields for every column in the schema. However, during extraction, `BaseExtractor.extract()` builds a `data` dict keyed by schema column names. If any unexpected keys appear (e.g., from future schema changes during a rolling deploy), `extra="ignore"` prevents a crash. This is strictly more resilient than `extra="forbid"` and acceptable because the dynamic model is not a long-lived contract -- it exists only to validate and transport extraction data.

**Why `strict=False`?**
TaskRow uses `strict=True`, which means Pydantic does not coerce types (e.g., string "123" is not accepted for an `int` field). For the dynamic model, the extraction pipeline may produce string values for Int64/Float64 fields from custom field resolution. Setting `strict=False` allows Pydantic to coerce these values, which is consistent with how BaseExtractor's `_extract_attribute()` already returns raw attribute values without type conversion for most fields.

**Why module-level cache with Lock instead of instance-level?**
Multiple SchemaExtractor instances may be created for the same schema type (e.g., one per builder invocation). The module-level cache ensures `create_model()` runs exactly once per schema type across all instances. The `threading.Lock` protects against concurrent first-access from the ThreadPoolExecutor used in cache warming.

**Why `_extract_type()` override?**
BaseExtractor's `_extract_type()` falls back to `task.resource_subtype` first, then `schema.task_type`. For entity-typed tasks (Offer, Business, etc.), `resource_subtype` is typically "default_task" (the Asana API default), not the entity type. SchemaExtractor overrides to always return `schema.task_type`, matching the behavior of UnitExtractor and ContactExtractor.

### 2.5 How source=None (Derived) Fields Are Handled

BaseExtractor._extract_column() and _extract_column_async() already handle source=None fields:

```python
if col.source is None:
    method_name = f"_extract_{col.name}"
    if hasattr(self, method_name):
        method = getattr(self, method_name)
        return method(task)
    return None  # <-- This line
```

SchemaExtractor inherits this behavior unchanged. For derived fields:
- `_extract_type()` is overridden to return `schema.task_type`
- `_extract_name()` is inherited from BaseExtractor (returns `task.name`)
- `_extract_date()` is inherited from BaseExtractor (returns `due_on`)
- `_extract_section()` is inherited from BaseExtractor (extracts from memberships)
- `_extract_url()` is inherited from BaseExtractor (constructs from GID)
- All other source=None fields (e.g., Offer's `office`, `vertical_id`) return `None`

This means derived fields like `office` and `vertical_id` will be `None` in the DataFrame -- which is the correct behavior per PRD FR-6 ("Derived fields (source=None) return None in SchemaExtractor -- no traversal logic").

### 2.6 How List[Utf8] Fields Default to []

In `_create_row()`, before calling `model_validate()`, all columns with `dtype in ("List[Utf8]", "List[String]")` that have `None` values are replaced with `[]`. This matches the existing pattern in UnitExtractor (lines 67-72) and ContactExtractor (lines 57-58).

The dynamic model also uses `Field(default_factory=list)` for list fields, providing a second safety net if a list column is missing from the data dict entirely.

### 2.7 Thread Safety Analysis

| Concern | Mitigation |
|---------|------------|
| Concurrent `_build_dynamic_row_model()` calls | Module-level `_MODEL_CACHE_LOCK` (threading.Lock) with double-checked locking |
| Concurrent `_create_row()` calls | `model_validate()` is stateless and thread-safe in Pydantic v2 |
| Cache warming ThreadPoolExecutor | Multiple threads may create SchemaExtractor instances for the same schema type; module-level cache ensures `create_model()` executes once |
| Dict mutation after cache population | Once cached, the model class is never mutated. `_MODEL_CACHE` is append-only. |

---

## 3. _create_extractor() Wiring

### 3.1 Current Implementation (lines 526-542 of builders/base.py)

```python
def _create_extractor(self, task_type: str) -> BaseExtractor:
    match task_type:
        case "Unit":
            return UnitExtractor(self._schema, self._resolver, client=self._client)
        case "Contact":
            return ContactExtractor(self._schema, self._resolver, client=self._client)
        case "*":
            return DefaultExtractor(self._schema, self._resolver, client=self._client)
        case _:
            return DefaultExtractor(self._schema, self._resolver, client=self._client)
```

### 3.2 Modified Implementation

```python
def _create_extractor(self, task_type: str) -> BaseExtractor:
    match task_type:
        case "Unit":
            return UnitExtractor(self._schema, self._resolver, client=self._client)
        case "Contact":
            return ContactExtractor(
                self._schema, self._resolver, client=self._client
            )
        case "*":
            return DefaultExtractor(
                self._schema, self._resolver, client=self._client
            )
        case _:
            # For entity types with schemas that have columns beyond the
            # base 12, use SchemaExtractor which dynamically generates a
            # Pydantic row model. For truly unknown types with no schema
            # (or base-only schemas), fall back to DefaultExtractor.
            from autom8_asana.dataframes.extractors.schema import SchemaExtractor
            from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

            base_col_names = {c.name for c in BASE_COLUMNS}
            schema_col_names = {c.name for c in self._schema.columns}
            has_extra_columns = bool(schema_col_names - base_col_names)

            if has_extra_columns:
                return SchemaExtractor(
                    self._schema, self._resolver, client=self._client
                )
            return DefaultExtractor(
                self._schema, self._resolver, client=self._client
            )
```

### 3.3 Decision Logic

| Condition | Extractor Used | Why |
|-----------|---------------|-----|
| `task_type == "Unit"` | UnitExtractor | Hand-coded; has `_extract_office_async()` traversal logic |
| `task_type == "Contact"` | ContactExtractor | Hand-coded; existing working extractor |
| `task_type == "*"` | DefaultExtractor | Wildcard/base schema; only 12 base fields |
| Schema has extra columns | SchemaExtractor | Dynamic row model accepts entity-specific fields |
| Schema has NO extra columns | DefaultExtractor | Base-only schema; TaskRow(extra="forbid") works |

### 3.4 Import Strategy

The `SchemaExtractor` import is deferred (inside the `case _:` branch body, not at module scope) to:
1. Avoid increasing module load time for code paths that never hit the default case
2. Keep the import graph clean -- `builders/base.py` already imports from `extractors/` at module scope for UnitExtractor/ContactExtractor/DefaultExtractor; adding SchemaExtractor there would be fine but the deferred pattern is more conservative
3. `BASE_COLUMNS` import is also deferred because it is only needed in the decision branch

### 3.5 Why Not Remove the UnitExtractor/ContactExtractor Cases?

UnitExtractor has non-trivial derived field logic (`_extract_office_async()`). ContactExtractor is pure boilerplate but already exists, is tested, and its removal would be churn with no benefit. Keeping explicit cases for existing extractors is free and provides clarity. SchemaExtractor handles the "everything else" case.

---

## 4. Completeness Test Design

### 4.1 File Location

`/Users/tomtenuta/Code/autom8_asana/tests/unit/dataframes/test_schema_extractor_completeness.py`

### 4.2 Test Implementation

```python
"""Parametrized completeness test for schema-extractor-row triad.

Per TDD-ENTITY-EXT-001 US-6: Iterates all registered schemas and verifies
each can produce a DataFrame row without crashing. This test would have
caught bugs B1-B4 (schema registered without capable extractor) and
prevents all future instances of this class of wiring gap.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock

import pytest

from autom8_asana.dataframes.builders.base import DataFrameBuilder
from autom8_asana.dataframes.extractors.default import DefaultExtractor
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS


def _make_mock_task() -> MagicMock:
    """Create a minimal mock task that satisfies BaseExtractor's base 12 fields."""
    task = MagicMock()
    task.gid = "1234567890"
    task.name = "Test Task"
    task.resource_subtype = "default_task"
    task.created_at = "2026-01-01T00:00:00Z"
    task.due_on = "2026-01-15"
    task.completed = False
    task.completed_at = None
    task.modified_at = "2026-01-01T00:00:00Z"
    task.tags = []
    task.memberships = []
    task.custom_fields = []
    return task


def _get_base_column_names() -> set[str]:
    """Return the set of base 12 column names."""
    return {c.name for c in BASE_COLUMNS}


@pytest.fixture
def schema_registry() -> SchemaRegistry:
    """Get an initialized SchemaRegistry."""
    return SchemaRegistry.get_instance()


class TestSchemaExtractorCompleteness:
    """Verify every registered schema can produce a row without crashing."""

    def test_all_schemas_have_capable_extractors(
        self, schema_registry: SchemaRegistry
    ) -> None:
        """AC-6.1 through AC-6.4: Every schema type can extract without crash.

        Parametrized dynamically over SchemaRegistry.list_task_types() so
        adding a new schema automatically includes it with zero test code
        changes.
        """
        base_col_names = _get_base_column_names()
        task_types = schema_registry.list_task_types()

        # Sanity: we expect at least 6 non-wildcard schemas
        assert len(task_types) >= 6, (
            f"Expected at least 6 registered schemas, got {len(task_types)}: "
            f"{task_types}"
        )

        for task_type in task_types:
            schema = schema_registry.get_schema(task_type)
            schema_col_names = set(schema.column_names())
            extra_columns = schema_col_names - base_col_names

            # Create a concrete builder subclass for testing
            extractor = DataFrameBuilder._create_extractor(
                _make_builder_stub(schema), task_type
            )

            # AC-6.3: Schemas with extra columns must NOT use DefaultExtractor
            if extra_columns:
                assert not isinstance(extractor, DefaultExtractor), (
                    f"{task_type} has {len(extra_columns)} extra columns "
                    f"({', '.join(sorted(extra_columns))}) but falls through "
                    f"to DefaultExtractor, which will crash on "
                    f"TaskRow(extra='forbid')"
                )

            # AC-6.2: Extractor can create a row without crash
            mock_task = _make_mock_task()
            row = extractor.extract(mock_task)
            assert row is not None, f"{task_type}: extract() returned None"

            # Verify row has all schema columns
            row_dict = row.to_dict()
            for col_name in schema.column_names():
                assert col_name in row_dict, (
                    f"{task_type}: column {col_name!r} missing from "
                    f"extracted row"
                )


def _make_builder_stub(schema):
    """Create a minimal builder-like object for calling _create_extractor."""
    stub = MagicMock()
    stub._schema = schema
    stub._resolver = None
    stub._client = None
    return stub
```

### 4.3 What It Asserts

| Assertion | PRD Mapping |
|-----------|-------------|
| At least 6 registered schemas exist | Sanity check against schema count regression |
| Schemas with extra columns do NOT use DefaultExtractor | AC-6.3 |
| Every schema type can extract a mock task without crash | AC-6.2 |
| Extracted row contains all schema column names | AC-6.2 (column completeness) |
| Test is additive -- adding a schema auto-includes it | AC-6.4 (parametrized over `list_task_types()`) |

### 4.4 Mock/Fixture Strategy

The test uses `MagicMock` for Task objects because:
1. Importing the actual `Task` model would pull in Asana model dependencies
2. BaseExtractor accesses tasks via `getattr(task, source)` -- MagicMock handles this naturally
3. Custom fields are not populated (resolver is None), so cf: columns will extract as None -- which is fine; we test that extraction does not crash, not that values are correct

The SchemaRegistry is accessed via `SchemaRegistry.get_instance()` with the `reset_registries` conftest fixture ensuring isolation.

---

## 5. Import-Time Validation Design

### 5.1 Location

The validation check is added to `SchemaRegistry._ensure_initialized()` in `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py`. This is the natural location because:
1. SchemaRegistry is where schemas are registered -- it knows which schemas exist
2. It already has a `_lock` and `_initialized` guard for thread safety
3. It does not import from `core/entity_registry.py` -- no circular dependency risk
4. The validation runs on first access, not at module load -- no Lambda cold start impact

### 5.2 Implementation

Add the following at the end of `_ensure_initialized()`, after all schemas are registered:

```python
def _ensure_initialized(self) -> None:
    """Lazy initialization of built-in schemas."""
    if self._initialized:
        return

    with self._lock:
        if self._initialized:
            return

        # ... existing schema imports and registrations ...

        self._initialized = True

        # Import-time validation: warn about schemas without capable extractors
        try:
            self._validate_extractor_coverage()
        except Exception:
            # Per R1.1: Validation MUST NOT crash startup
            # If validation itself fails, log and continue
            import logging
            logging.getLogger(__name__).warning(
                "schema_validation_failed",
                exc_info=True,
            )


def _validate_extractor_coverage(self) -> None:
    """Warn about schemas that lack dedicated extractors.

    Per TDD-ENTITY-EXT-001 US-7: Emits structured warnings for schemas
    registered without hand-coded extractors. SchemaExtractor will handle
    these at runtime, but the warning makes the situation visible in logs.

    This method is called inside _ensure_initialized() and MUST NOT raise
    exceptions that propagate to callers.
    """
    from autom8_asana.dataframes.extractors.base import BaseExtractor
    from autom8_asana.dataframes.extractors.contact import ContactExtractor
    from autom8_asana.dataframes.extractors.default import DefaultExtractor
    from autom8_asana.dataframes.extractors.unit import UnitExtractor
    from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

    # Known hand-coded extractors by task_type
    dedicated_extractors: dict[str, type[BaseExtractor]] = {
        "Unit": UnitExtractor,
        "Contact": ContactExtractor,
        "*": DefaultExtractor,
    }

    base_col_names = {c.name for c in BASE_COLUMNS}

    for task_type, schema in self._schemas.items():
        if task_type in dedicated_extractors:
            continue  # Has a hand-coded extractor -- no warning

        if task_type == "*":
            continue  # Base schema, always uses DefaultExtractor

        schema_col_names = {c.name for c in schema.columns}
        extra_columns = schema_col_names - base_col_names

        if extra_columns:
            from autom8y_log import get_logger
            get_logger(__name__).warning(
                "schema_using_generic_extractor",
                extra={
                    "entity": task_type,
                    "schema_name": schema.name,
                    "extra_column_count": len(extra_columns),
                    "note": "SchemaExtractor will handle extraction; "
                            "add a dedicated extractor only if custom "
                            "derived field logic is needed",
                },
            )
```

### 5.3 What Triggers a Warning vs What Is Acceptable

| Situation | Behavior |
|-----------|----------|
| Schema with dedicated extractor (Unit, Contact) | No warning (AC-7.4) |
| Schema using SchemaExtractor fallback (Offer, Business, AssetEdit, AssetEditHolder) | WARNING emitted (AC-7.1, AC-7.2) |
| Base schema ("*") | No warning |
| Schema with no extra columns beyond base 12 | No warning (DefaultExtractor is correct) |
| Validation code itself throws an exception | Caught by outer try/except; logged as warning, not propagated (R1.1) |

### 5.4 Try/Except Pattern for Safety (R1.1)

The outer `try/except Exception` in `_ensure_initialized()` ensures that if `_validate_extractor_coverage()` itself fails (e.g., due to an import error in one of the extractor modules), the application starts normally. The validation is advisory, not a gate. This satisfies NFR-7: "Malformed validation paths produce warnings, never crash startup."

---

## 6. BUSINESS_SCHEMA Duplicate Column Fix

### 6.1 Root Cause

`/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/business.py` line 59:

```python
*[c for c in BUSINESS_COLUMNS if c not in BASE_COLUMNS],
```

This uses **ColumnDef object identity** (via `dataclass(frozen=True)` default equality). The business `name` ColumnDef (`source=None`) is a different object than the base `name` ColumnDef (`source="name"`), so the filter passes both through.

Compare with `offer.py` line 100, which correctly uses **name-based dedup**:

```python
*[c for c in OFFER_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
```

### 6.2 Fix

Change line 59 of `business.py` from:

```python
columns=[
    *BASE_COLUMNS,
    *[c for c in BUSINESS_COLUMNS if c not in BASE_COLUMNS],
],
```

to:

```python
columns=[
    *BASE_COLUMNS,
    *[c for c in BUSINESS_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
],
```

This removes the duplicate `name` column. After the fix, BUSINESS_SCHEMA will have 17 columns (12 base + 5 unique business columns: company_id, office_phone, stripe_id, booking_type, facebook_page_id). The business-specific `name` with `source=None` is correctly deduplicated because the base `name` column already exists.

### 6.3 Impact

- Column count changes from 18 to 17
- The base `name` column (with `source="name"`, i.e., `getattr(task, "name")`) is preserved
- The business-specific `name` override (with `source=None`, i.e., derived) is removed
- This matches the PRD: "BUSINESS_SCHEMA contains a duplicate name column ... the schema should use name-based dedup like OFFER_SCHEMA does"

---

## 7. Circular Import Analysis

### 7.1 Current Import Graph (Relevant Subset)

```
core/entity_registry.py
  imports at module scope: autom8y_log, models.business.detection.types (deferred via _bind_entity_types)
  does NOT import: dataframes/*

dataframes/extractors/base.py
  imports at module scope: dataframes.models.schema, dataframes.models.task_row
  does NOT import: core/entity_registry

dataframes/extractors/schema.py (NEW)
  imports at module scope: dataframes.extractors.base, dataframes.models.task_row, pydantic, threading
  does NOT import: core/entity_registry

dataframes/builders/base.py
  imports at module scope: dataframes.extractors (UnitExtractor, ContactExtractor, DefaultExtractor)
  NEW deferred import: dataframes.extractors.schema.SchemaExtractor (inside case _ branch)
  does NOT import: core/entity_registry

dataframes/models/registry.py
  imports at module scope: dataframes.models.schema
  deferred imports: dataframes.schemas/*.py (inside _ensure_initialized)
  NEW deferred imports: dataframes.extractors.* (inside _validate_extractor_coverage)
  does NOT import: core/entity_registry
```

### 7.2 Proof: No Circular Dependency

The chosen architecture introduces zero new cross-boundary imports between `core/` and `dataframes/`. All new imports are within the `dataframes/` package:

1. `builders/base.py` imports `extractors/schema.py` (deferred, within `dataframes/`)
2. `models/registry.py` imports `extractors/*.py` (deferred, within `dataframes/`)
3. `extractors/schema.py` imports `extractors/base.py` and `models/task_row.py` (at module scope, within `dataframes/`)

There is no path from `core/entity_registry.py` to `dataframes/` or vice versa in the new code. The existing zero-import boundary between `core/` and `dataframes/` is preserved.

### 7.3 Constraints on Schema/Extractor Modules

To maintain the circular-import-free property:

- Schema modules (`dataframes/schemas/*.py`) MUST NOT import from `core/entity_registry.py`
- Extractor modules (`dataframes/extractors/*.py`) MAY import from `models/business/` (UnitExtractor already does) but MUST NOT import from `core/entity_registry.py`
- `dataframes/models/registry.py` MUST NOT import from `core/entity_registry.py`

These constraints are already satisfied by the existing codebase and are preserved by this design.

---

## 8. Ordered Task List for Principal Engineer

Each task is independently testable. Tasks must be executed in order due to dependencies.

### Task 1: Fix BUSINESS_SCHEMA Duplicate Column

**Files to modify:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/business.py`

**What to implement:**
Change the column dedup filter from object equality to name-based dedup (Section 6.2 of this TDD).

**How to verify:**
```python
from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA
# Column count should be 17, not 18
assert len(BUSINESS_SCHEMA.columns) == 17
# No duplicate column names
names = [c.name for c in BUSINESS_SCHEMA.columns]
assert len(names) == len(set(names))
```

Run: `.venv/bin/pytest tests/unit/dataframes/ -x -q --timeout=60 -k "business or schema"`

---

### Task 2: Implement SchemaExtractor

**Files to create:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/schema.py`

**Files to modify:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/__init__.py` (add export)

**What to implement:**
The SchemaExtractor class exactly as specified in Section 2.3 of this TDD. Add `SchemaExtractor` to `__init__.py` `__all__` list and import.

**How to verify:**
Write a focused unit test in `tests/unit/dataframes/test_schema_extractor.py`:

```python
"""Unit tests for SchemaExtractor."""
from autom8_asana.dataframes.extractors.schema import SchemaExtractor, DTYPE_MAP, _MODEL_CACHE
from autom8_asana.dataframes.schemas.offer import OFFER_SCHEMA
from autom8_asana.dataframes.schemas.asset_edit import ASSET_EDIT_SCHEMA
from autom8_asana.dataframes.schemas.asset_edit_holder import ASSET_EDIT_HOLDER_SCHEMA
from autom8_asana.dataframes.schemas.business import BUSINESS_SCHEMA
from autom8_asana.dataframes.schemas.base import BASE_SCHEMA
from unittest.mock import MagicMock


class TestSchemaExtractor:
    def test_offer_extraction_does_not_crash(self):
        """AC-1.1: Offer extraction succeeds."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = _make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert len(d) == len(OFFER_SCHEMA.columns)

    def test_asset_edit_extraction_does_not_crash(self):
        """AC-3.1: AssetEdit extraction succeeds."""
        extractor = SchemaExtractor(ASSET_EDIT_SCHEMA)
        task = _make_mock_task()
        row = extractor.extract(task)
        assert row is not None
        d = row.to_dict()
        assert len(d) == len(ASSET_EDIT_SCHEMA.columns)

    def test_asset_edit_holder_extraction_does_not_crash(self):
        """AC-4.1: AssetEditHolder extraction succeeds."""
        extractor = SchemaExtractor(ASSET_EDIT_HOLDER_SCHEMA)
        task = _make_mock_task()
        row = extractor.extract(task)
        assert row is not None

    def test_business_extraction_does_not_crash(self):
        """AC-2.1: Business extraction succeeds."""
        extractor = SchemaExtractor(BUSINESS_SCHEMA)
        task = _make_mock_task()
        row = extractor.extract(task)
        assert row is not None

    def test_extract_type_returns_schema_task_type(self):
        """AC-5.3: _extract_type returns schema.task_type."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = _make_mock_task()
        assert extractor._extract_type(task) == "Offer"

    def test_dynamic_model_cached(self):
        """AC-5.6: Model created once per schema type."""
        _MODEL_CACHE.clear()
        ext1 = SchemaExtractor(OFFER_SCHEMA)
        ext2 = SchemaExtractor(OFFER_SCHEMA)
        model1 = ext1._build_dynamic_row_model()
        model2 = ext2._build_dynamic_row_model()
        assert model1 is model2

    def test_list_fields_default_to_empty_list(self):
        """AC-5.2: List fields default to [] not None."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = _make_mock_task()
        row = extractor.extract(task)
        d = row.to_dict()
        assert d["platforms"] == []

    def test_derived_fields_return_none(self):
        """AC-5.3: source=None fields without custom extractors return None."""
        extractor = SchemaExtractor(OFFER_SCHEMA)
        task = _make_mock_task()
        row = extractor.extract(task)
        d = row.to_dict()
        # office and vertical_id have source=None with no _extract method
        assert d["office"] is None
        assert d["vertical_id"] is None

    def test_dtype_map_covers_all_used_types(self):
        """FR-11: All dtypes in existing schemas are mapped."""
        required_dtypes = {"Utf8", "Int64", "Float64", "Boolean", "Date",
                          "Datetime", "Decimal", "List[Utf8]"}
        assert required_dtypes.issubset(DTYPE_MAP.keys())


def _make_mock_task():
    task = MagicMock()
    task.gid = "1234567890"
    task.name = "Test Task"
    task.resource_subtype = "default_task"
    task.created_at = "2026-01-01T00:00:00Z"
    task.due_on = "2026-01-15"
    task.completed = False
    task.completed_at = None
    task.modified_at = "2026-01-01T00:00:00Z"
    task.tags = []
    task.memberships = []
    task.custom_fields = []
    return task
```

Run: `.venv/bin/pytest tests/unit/dataframes/test_schema_extractor.py -x -q --timeout=60`

---

### Task 3: Wire SchemaExtractor into _create_extractor()

**Files to modify:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/base.py`

**What to implement:**
Replace the `case _:` branch in `_create_extractor()` (lines 537-542) with the logic specified in Section 3.2 of this TDD.

**How to verify:**
```python
# Existing extractors preserved (AC-5.4)
assert isinstance(_create_extractor("Unit"), UnitExtractor)
assert isinstance(_create_extractor("Contact"), ContactExtractor)
assert isinstance(_create_extractor("*"), DefaultExtractor)

# SchemaExtractor used for schemas with extra columns (AC-5.1)
from autom8_asana.dataframes.extractors.schema import SchemaExtractor
assert isinstance(_create_extractor("Offer"), SchemaExtractor)
assert isinstance(_create_extractor("AssetEdit"), SchemaExtractor)
```

Run: `.venv/bin/pytest tests/unit/dataframes/ -x -q --timeout=60`

---

### Task 4: Add Completeness Test

**Files to create:**
- `/Users/tomtenuta/Code/autom8_asana/tests/unit/dataframes/test_schema_extractor_completeness.py`

**What to implement:**
The completeness test as specified in Section 4.2 of this TDD.

**How to verify:**
Run: `.venv/bin/pytest tests/unit/dataframes/test_schema_extractor_completeness.py -x -v --timeout=60`

All registered schema types should pass. If any fail, it means the wiring from Task 3 is incomplete.

---

### Task 5: Add Import-Time Validation Warnings

**Files to modify:**
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py`

**What to implement:**
The `_validate_extractor_coverage()` method and its invocation from `_ensure_initialized()`, as specified in Section 5.2 of this TDD.

**How to verify:**
Write a test in `tests/unit/dataframes/test_schema_extractor_completeness.py` (append to existing):

```python
class TestImportTimeValidation:
    def test_warning_emitted_for_generic_extractors(self, caplog):
        """AC-7.1, AC-7.2: Warning emitted for schemas using SchemaExtractor."""
        import logging
        with caplog.at_level(logging.WARNING):
            registry = SchemaRegistry.get_instance()
            # Force re-initialization
            registry._initialized = False
            registry._schemas = {}
            registry._ensure_initialized()

        # Should have warnings for Offer, Business, AssetEdit, AssetEditHolder
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        # At least one warning about generic extractor should be present
        assert any("schema_using_generic_extractor" in str(m) for m in warning_messages) or \
               any("generic_extractor" in str(getattr(r, 'extra', {})) for r in caplog.records)

    def test_no_warning_for_dedicated_extractors(self, caplog):
        """AC-7.4: No warning for Unit and Contact."""
        import logging
        with caplog.at_level(logging.WARNING):
            registry = SchemaRegistry.get_instance()
            registry._initialized = False
            registry._schemas = {}
            registry._ensure_initialized()

        # No warnings should mention Unit or Contact
        for record in caplog.records:
            extra = getattr(record, 'extra', {})
            if isinstance(extra, dict):
                entity = extra.get('entity', '')
                assert entity not in ('Unit', 'Contact'), (
                    f"Unexpected warning for {entity}"
                )
```

Run: `.venv/bin/pytest tests/unit/dataframes/test_schema_extractor_completeness.py -x -v --timeout=60`

---

### Task 6: Schema Audit and Verification

**Files to verify (read-only):**
- All schema files in `dataframes/schemas/`
- SchemaRegistry to confirm all 7 schemas (including "*") are registered

**What to implement:**
Add a test to verify the schema inventory matches expectations:

```python
class TestSchemaAudit:
    def test_known_schema_inventory(self, schema_registry):
        """FR-14: All schemas are accounted for."""
        task_types = set(schema_registry.list_task_types())
        expected = {"Unit", "Contact", "Offer", "Business", "AssetEdit", "AssetEditHolder"}
        assert task_types == expected, (
            f"Schema inventory mismatch. "
            f"Extra: {task_types - expected}. "
            f"Missing: {expected - task_types}"
        )

    def test_wildcard_base_schema_exists(self, schema_registry):
        """The '*' base schema must always be registered."""
        schema = schema_registry.get_schema("*")
        assert schema.task_type == "*"
        assert len(schema.columns) == 12
```

**How to verify:**
Run: `.venv/bin/pytest tests/unit/dataframes/test_schema_extractor_completeness.py -x -v --timeout=60`

---

### Task 7: Full Regression Test

**Files to modify:** None (verification only)

**What to do:**
Run the full test suite to verify zero regressions:

```bash
.venv/bin/pytest tests/ -x -q --timeout=60
```

All 8588+ tests must pass. Pay particular attention to:
- `tests/unit/dataframes/` -- all DataFrame tests
- Any test that creates a `SectionDataFrameBuilder` or calls `_create_extractor()`
- Any test that accesses `SchemaRegistry`

---

### Task 8: Deferred Work Items

**Files to create:**
- `/Users/tomtenuta/Code/autom8_asana/.claude/wip/TODO.md`

**What to implement:**
Log deferred items:
- cascade:MRR source annotation investigation (B2 from canary bugs)
- Traversal unification initiative (generalized parent-chain walker for derived fields)
- MRR dedup documentation (aggregate at Unit level, not Offer)
- Query CLI utility
- B6: is_completed naming documentation
- Audit Business/AssetEdit/AssetEditHolder for traversal needs (when to graduate from SchemaExtractor to hand-coded extractor)

---

## 9. Risk Mitigations (Concrete)

### R1.1: Import-Time Validation Crash

**Exact try/except pattern** (from Section 5.2):

```python
# In _ensure_initialized(), after self._initialized = True:
try:
    self._validate_extractor_coverage()
except Exception:
    import logging
    logging.getLogger(__name__).warning(
        "schema_validation_failed",
        exc_info=True,
    )
```

The outer try/except catches ANY exception from the validation path, including ImportError (if an extractor module has a broken import), AttributeError (if module structure changes), and any other unexpected failure. The warning uses `exc_info=True` to include the traceback in logs for debugging without crashing the application.

### R3.1: Dual-Wiring Avoidance

There is **no dual-wiring** in the chosen architecture. The SchemaExtractor approach does not introduce a second wiring mechanism -- it modifies the existing `_create_extractor()` fallback. The flow is:

1. `_create_extractor()` checks explicit cases (Unit, Contact, *)
2. For all other types, it checks if the schema has extra columns
3. If yes: SchemaExtractor (new)
4. If no: DefaultExtractor (existing)

There is exactly one code path for extractor selection. No descriptor fields, no triad registry, no parallel wiring. The risk of dual-wiring divergence does not exist.

### R4.1: Circular Import Prevention

The chosen architecture adds zero cross-boundary imports between `core/` and `dataframes/`. See Section 7 for the full import graph analysis. The constraint is:

> **Schema, extractor, and row model modules MUST NOT import from `core/entity_registry.py`.**

This is already true for all existing modules and is preserved by the new SchemaExtractor module.

### R5.1: BaseExtractor Method Shadowing

SchemaExtractor overrides only `_extract_type()`. It does NOT override `_extract_name()`, `_extract_gid()`, or any other base field method. The base 12 fields are handled entirely by BaseExtractor's inherited methods.

For derived fields (source=None) on entity-specific columns (e.g., Offer's `office`), BaseExtractor's dispatch logic already handles this:

```python
if col.source is None:
    method_name = f"_extract_{col.name}"
    if hasattr(self, method_name):
        method = getattr(self, method_name)
        return method(task)
    return None  # Falls through to None for fields with no extract method
```

SchemaExtractor does not define `_extract_office()` or `_extract_vertical_id()`, so these return `None` via the fallback. This is correct per FR-6.

### R6.1: Thread-Unsafe Dynamic Model Cache

Mitigated by:
1. Module-level `_MODEL_CACHE_LOCK = threading.Lock()`
2. Double-checked locking pattern in `_build_dynamic_row_model()`
3. Cache is append-only (models are never removed or modified)

### R7.1: BUSINESS_SCHEMA Duplicate Column

Fixed in Task 1. The dedup filter is changed from object equality to name-based dedup. See Section 6 for the exact fix.

---

## 10. Rollback Strategy

Each change can be reverted independently:

| Task | Rollback Method | Dependencies |
|------|----------------|--------------|
| Task 1: BUSINESS_SCHEMA fix | Revert the single-line change in `business.py` | None -- standalone fix |
| Task 2: SchemaExtractor | Delete `extractors/schema.py`, remove export from `__init__.py` | Must revert Task 3 first |
| Task 3: _create_extractor() wiring | Restore original `case _:` branch (DefaultExtractor fallback) | Must revert Task 4 first (completeness test would fail) |
| Task 4: Completeness test | Delete `test_schema_extractor_completeness.py` | None -- test-only file |
| Task 5: Import-time validation | Remove `_validate_extractor_coverage()` and its call from `_ensure_initialized()` | None -- advisory only |
| Task 6: Schema audit | Delete audit test methods | None -- test-only |

**Full rollback order** (if entire feature must be reverted): Tasks 4, 3, 2, 5, 6, 1. Or simply revert the entire PR.

The BUSINESS_SCHEMA fix (Task 1) is independently valuable and should be retained even if the rest is reverted -- it fixes a latent bug (duplicate column names) regardless of SchemaExtractor.

---

## 11. Handoff Checklist

- [x] TDD covers all PRD requirements (FR-1 through FR-16)
- [x] Component boundaries and responsibilities are clear (SchemaExtractor, _create_extractor, completeness test, validation)
- [x] Data model defined (dynamic Pydantic model from schema)
- [x] API contracts specified (_create_extractor decision logic, SchemaExtractor interface)
- [x] ADR documents the wiring architecture decision with scoring matrix
- [x] Risks identified with concrete mitigations (R1.1, R3.1, R4.1, R5.1, R6.1, R7.1)
- [x] Principal Engineer can implement without architectural questions
- [x] All artifacts verified via Read tool

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/TDD-entity-extensibility.md` | This file |
| PRD | `/Users/tomtenuta/Code/autom8_asana/.claude/artifacts/PRD-entity-extensibility.md` | Read |
| Sprint plan | `/Users/tomtenuta/.claude/plans/jaunty-zooming-star.md` | Read |
| Extensibility spike | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-entity-extensibility-architecture.md` | Read |
| First-principles analysis | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/ANALYSIS-entity-extensibility-first-principles.md` | Read |
| Counter-proposal | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/COUNTER-entity-extensibility-plugin-architecture.md` | Read |
| Option A steel-man | `/Users/tomtenuta/Code/autom8_asana/docs/design/ARCH-descriptor-driven-auto-wiring.md` | Read |
| BaseExtractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/base.py` | Read |
| UnitExtractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/unit.py` | Read |
| ContactExtractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/contact.py` | Read |
| DefaultExtractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/default.py` | Read |
| extractors/__init__.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/extractors/__init__.py` | Read |
| TaskRow/UnitRow/ContactRow | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/task_row.py` | Read |
| DataFrameSchema/ColumnDef | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/schema.py` | Read |
| SchemaRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/models/registry.py` | Read |
| DataFrameBuilder / _create_extractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/base.py` | Read |
| SectionDataFrameBuilder._get_extractor | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/section.py` | Read |
| OFFER_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/offer.py` | Read |
| BUSINESS_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/business.py` | Read |
| ASSET_EDIT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/asset_edit.py` | Read |
| ASSET_EDIT_HOLDER_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/asset_edit_holder.py` | Read |
| BASE_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/base.py` | Read |
| CONTACT_SCHEMA | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/contact.py` | Read |
| EntityDescriptor/EntityRegistry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/core/entity_registry.py` | Read |
| ENTITY_RELATIONSHIPS | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/query/hierarchy.py` | Read |
| _build_cascading_field_registry | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/fields.py` | Read |
| Root conftest | `/Users/tomtenuta/Code/autom8_asana/tests/conftest.py` | Read |
