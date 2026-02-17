# Smell Report: SchemaExtractor Subsystem

**Date**: 2026-02-17
**Scope**: 5 source files + 3 test files from the SchemaExtractor sprint
**Assessment**: Post-SchemaExtractor Hygiene Pass
**Status**: Ready for Architect Enforcer

---

## Executive Summary

The SchemaExtractor subsystem is well-structured overall. SchemaExtractor correctly
inherits from BaseExtractor and follows the established extractor pattern for
`_create_row` and `_extract_type` overrides. The wiring in `builders/base.py` and
`extractors/__init__.py` is consistent with sibling extractors. The test coverage
is strong (44 tests across 3 files).

**Findings**: 8 smells identified (0 critical, 2 high, 4 medium, 2 low).
The highest-ROI items are the duplicated `_make_mock_task` fixture and the
`_create_row` None-to-empty-list boilerplate.

---

## Findings (Ranked by ROI)

### SM-001: Triplicated `_make_mock_task()` fixture across test files (HIGH)

**Category**: DRY Violation
**Severity**: HIGH
**Locations**:
- `tests/unit/dataframes/test_schema_extractor.py:26-40`
- `tests/unit/dataframes/test_schema_extractor_completeness.py:23-37`
- `tests/unit/dataframes/test_schema_extractor_adversarial.py:27-41`

**Evidence**: Identical 15-line function copied verbatim in all 3 files:
```python
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
```

This same function also appears in at least 4 other test files in `tests/unit/dataframes/builders/`.
There is no `conftest.py` in `tests/unit/dataframes/` to provide shared fixtures.

**Note**: The existing `test_extractors.py` uses real `Task` model fixtures via pytest
(`minimal_task`, `full_task`) rather than `MagicMock`. The SchemaExtractor tests chose
MagicMock instead, creating a parallel fixture pattern in the same test directory.

**Blast Radius**: 3 files, ~45 lines of duplicated code; any change to mock task shape
requires updating 7+ files.
**Fix Complexity**: Trivial -- create `tests/unit/dataframes/conftest.py` with a shared
`make_mock_task` fixture (or parametrized factory).
**ROI Score**: 9/10

---

### SM-002: `_create_row` None-to-empty-list boilerplate repeated in every extractor (HIGH)

**Category**: DRY Violation
**Severity**: HIGH
**Locations**:
- `src/autom8_asana/dataframes/extractors/default.py:39-41`
- `src/autom8_asana/dataframes/extractors/contact.py:57-58`
- `src/autom8_asana/dataframes/extractors/unit.py:67-72`
- `src/autom8_asana/dataframes/extractors/schema.py:89-92`

**Evidence**: Every extractor's `_create_row` manually converts None to `[]` for list
fields. DefaultExtractor handles `tags`; ContactExtractor handles `tags`;
UnitExtractor handles `tags`, `products`, `languages`; SchemaExtractor does it
dynamically by iterating schema columns:

```python
# DefaultExtractor (default.py:39-41)
if data.get("tags") is None:
    data["tags"] = []

# ContactExtractor (contact.py:57-58)
if data.get("tags") is None:
    data["tags"] = []

# UnitExtractor (unit.py:67-72)
if data.get("tags") is None:
    data["tags"] = []
if data.get("products") is None:
    data["products"] = []
if data.get("languages") is None:
    data["languages"] = []

# SchemaExtractor (schema.py:89-92) -- dynamic but same pattern
for col in self._schema.columns:
    if col.dtype in ("List[Utf8]", "List[String]") and data.get(col.name) is None:
        data[col.name] = []
```

SchemaExtractor already has the generalized solution. The hand-coded extractors
duplicate a subset of it.

**Blast Radius**: 4 files; any new list field added to Unit/Contact schemas requires
remembering to add the None-to-[] conversion.
**Fix Complexity**: Moderate -- could be factored into `BaseExtractor._normalize_list_fields(data)`
using the schema's column defs. SchemaExtractor's approach is already generic.
**ROI Score**: 8/10

**Boundary Note**: This is an Architect Enforcer concern -- the fix touches the
BaseExtractor contract and affects all extractor subclasses.

---

### SM-003: `business.py` schema uses lowercase `task_type="business"` (MEDIUM)

**Category**: Naming Inconsistency
**Severity**: MEDIUM
**Location**: `src/autom8_asana/dataframes/schemas/business.py:56`

**Evidence**: All other schemas use PascalCase for `task_type`:
```
unit.py:        task_type="Unit"
contact.py:     task_type="Contact"
offer.py:       task_type="Offer"
asset_edit.py:  task_type="AssetEdit"
asset_edit_holder.py: task_type="AssetEditHolder"
business.py:    task_type="business"   # <-- lowercase outlier
```

The registry maps it under `"Business"` (PascalCase key, `registry.py:127`), but the
schema's `task_type` is `"business"`. This means:
- `SchemaExtractor._extract_type()` returns `"business"` (lowercase) for Business rows
- The `_MODEL_CACHE` key for Business rows is `"business"` (lowercase)
- Test `test_business_type_set_correctly` (test_schema_extractor.py:157) explicitly
  asserts `d["type"] == "business"` -- the test encodes the inconsistency

**Blast Radius**: Downstream consumers reading the `type` column see `"business"` when
all other types are PascalCase. Any `df.filter(pl.col("type") == "Business")` would
miss Business rows.
**Fix Complexity**: Trivial -- change to `task_type="Business"` and update version;
bump test assertion.
**ROI Score**: 7/10

**Boundary Note**: Changing `task_type` affects the cache key and `_MODEL_CACHE`, so
this should be validated by Architect Enforcer for downstream impact.

---

### SM-004: `_TestBuilder` duplicated between test files (MEDIUM)

**Category**: DRY Violation
**Severity**: MEDIUM
**Locations**:
- `tests/unit/dataframes/test_schema_extractor_completeness.py:45-58`
- `tests/unit/dataframes/test_schema_extractor_adversarial.py:70-81`

**Evidence**: Nearly identical concrete `DataFrameBuilder` subclass created inline:
```python
class _TestBuilder(DataFrameBuilder):
    def __init__(self, schema: DataFrameSchema) -> None:
        super().__init__(schema)
    def get_tasks(self) -> list:
        return []
    def _get_project_gid(self) -> str | None:
        return None
    def _get_extractor(self) -> BaseExtractor:
        return self._create_extractor(self._schema.task_type)
```

**Blast Radius**: 2 files, ~24 lines.
**Fix Complexity**: Trivial -- move to shared `conftest.py` (same as SM-001).
**ROI Score**: 6/10

---

### SM-005: Mutable default `[]` in DTYPE_MAP is misleading dead data (MEDIUM)

**Category**: Complexity / Naming
**Severity**: MEDIUM
**Location**: `src/autom8_asana/dataframes/extractors/schema.py:44-45`

**Evidence**:
```python
DTYPE_MAP: dict[str, tuple[type, Any]] = {
    ...
    "List[Utf8]": (list[str], []),  # Default empty list, not None
    "List[String]": (list[str], []),
}
```

The `default` value (second element of tuple) is `[]` for list types, but
`_build_dynamic_row_model()` never uses this default for list fields -- it always
creates `Field(default_factory=list)` instead (schema.py:141-144). The `[]` in
DTYPE_MAP is never consumed and creates a false impression that it is the actual
default used.

Additionally, `[]` as a module-level default is a classic mutable default footgun
in Python. While it's never mutated here (since it's not used), it sets a bad
precedent.

**Blast Radius**: Low -- no runtime impact, but misleads future maintainers.
**Fix Complexity**: Trivial -- change `[]` to `None` and update the comment.
**ROI Score**: 5/10

---

### SM-006: Mixed logging approaches in `registry.py` (MEDIUM)

**Category**: Import Hygiene / Naming
**Severity**: MEDIUM
**Locations**:
- `src/autom8_asana/dataframes/models/registry.py:141` (`import logging`)
- `src/autom8_asana/dataframes/models/registry.py:173` (`from autom8y_log import get_logger`)

**Evidence**: The `_ensure_initialized` method uses stdlib `logging` for the
validation-failure catch block (line 141), while `_validate_extractor_coverage`
uses `autom8y_log.get_logger` (line 173). Both are in the same class:

```python
# _ensure_initialized catch block (line 141-146):
except Exception:
    import logging
    logging.getLogger(__name__).warning("schema_validation_failed", exc_info=True)

# _validate_extractor_coverage (line 173-175):
from autom8y_log import get_logger
get_logger(__name__).warning("schema_using_generic_extractor", extra={...})
```

This mixes two logging approaches in the same file. The codebase standardizes on
`autom8y_log.get_logger` (used in `unit.py` and elsewhere).

**Blast Radius**: Low -- both produce output, but structured logging context may
differ between the two approaches.
**Fix Complexity**: Trivial -- replace `import logging` with `from autom8y_log import get_logger`.
**ROI Score**: 4/10

---

### SM-007: Schema column deduplication uses inconsistent strategies (LOW)

**Category**: Naming / DRY
**Severity**: LOW
**Locations**:
- `src/autom8_asana/dataframes/schemas/unit.py:94` -- uses object identity: `c not in BASE_COLUMNS`
- `src/autom8_asana/dataframes/schemas/business.py:59` -- uses name matching: `c.name not in {col.name for col in BASE_COLUMNS}`
- `src/autom8_asana/dataframes/schemas/offer.py:100` -- uses name matching
- `src/autom8_asana/dataframes/schemas/contact.py:111-113` -- uses name matching
- `src/autom8_asana/dataframes/schemas/asset_edit.py:187-189` -- uses name matching
- `src/autom8_asana/dataframes/schemas/asset_edit_holder.py:30-32` -- uses name matching

**Evidence**: `unit.py` uses `c not in BASE_COLUMNS` (object identity/equality) while
all other schemas including the newly fixed `business.py` use `c.name not in {col.name for col in BASE_COLUMNS}` (name-based dedup). The business.py fix introduced name-based dedup
to resolve a duplicate "name" column issue, but unit.py was not updated to match.

Unit schema works correctly because UNIT_COLUMNS does not contain a column named
"name" -- so object identity dedup happens to produce the same result. However, if
someone adds a "name" override column to UNIT_COLUMNS in the future (as business.py
has), the dedup would fail.

**Blast Radius**: Currently zero (unit.py has no overlapping column names). Latent risk
for future schema changes.
**Fix Complexity**: Trivial -- change unit.py line 94 to use name-based dedup.
**ROI Score**: 3/10

---

### SM-008: SchemaExtractor not listed in `__init__.py` docstring public API section (LOW)

**Category**: Naming / Documentation
**Severity**: LOW
**Location**: `src/autom8_asana/dataframes/extractors/__init__.py:7-9`

**Evidence**: The module docstring lists the public API but omits SchemaExtractor:
```python
"""...
Public API:
    - BaseExtractor: Abstract base with 12 base field extraction methods
    - UnitExtractor: Unit task extraction with 23 fields
    - ContactExtractor: Contact task extraction with 21 fields
"""
```

SchemaExtractor is exported in `__all__` (line 32) and imported (line 27), but the
docstring was not updated. DefaultExtractor is also missing from the docstring.

**Blast Radius**: None -- purely a documentation inconsistency.
**Fix Complexity**: Trivial -- add SchemaExtractor and DefaultExtractor to the docstring.
**ROI Score**: 2/10

---

## Smells NOT Found (Clean Areas)

The following areas were assessed and found to be clean:

1. **Import hygiene in schema.py**: All imports are used. `TYPE_CHECKING` guard for
   `DataFrameSchema` is correct. No circular dependency introduced.

2. **Import hygiene in builders/base.py**: SchemaExtractor is lazily imported inside
   `_create_extractor` (line 543) to avoid circular imports. This is correct --
   `__init__.py` eagerly imports it, but `builders/base.py` uses the lazy pattern
   since it already imports from `extractors/__init__.py` at the top level.

3. **SchemaExtractor naming conventions**: Class name follows `{Type}Extractor` pattern.
   Method names `_create_row`, `_extract_type` match the abstract interface. The dynamic
   model naming `{TaskType}SchemaRow` is clear and consistent.

4. **Thread safety**: Double-checked locking in `_build_dynamic_row_model()` is correctly
   implemented with fast-path check outside the lock and verification inside.

5. **`_create_extractor` fallback logic**: The `case _:` branch correctly checks for
   extra columns before choosing SchemaExtractor vs DefaultExtractor. The
   `BASE_COLUMNS` import is appropriately lazy.

6. **`__init__.py` exports**: SchemaExtractor is properly exported in `__all__` and
   the import is alphabetically ordered with siblings.

7. **Registry validation**: `_validate_extractor_coverage` correctly identifies schemas
   without dedicated extractors. The `try/except` wrapper in `_ensure_initialized`
   ensures validation failures cannot crash startup (R1.1).

8. **Test quality**: The 3 test files cover the full spectrum: happy paths (14 tests),
   completeness/wiring (6 tests), and adversarial edge cases (24 tests). Parametrized
   completeness test auto-discovers new schemas. Thread safety is tested with 12
   concurrent threads.

---

## Cross-Reference Map

| Smell | Related To | Notes |
|-------|-----------|-------|
| SM-001 | SM-004 | Both solved by creating shared conftest.py |
| SM-002 | SM-005 | SM-005's dead defaults are conceptually related to SM-002's list handling |
| SM-003 | SM-007 | Both are naming inconsistencies in the schema layer |
| SM-006 | -- | Standalone registry hygiene issue |
| SM-008 | -- | Standalone documentation gap |

---

## Boundary Concerns for Architect Enforcer

1. **SM-002** (list normalization in BaseExtractor): Factoring None-to-[] into the base
   class changes the contract for all extractors. Architect Enforcer should evaluate
   whether this should be in `BaseExtractor.extract()` (before `_create_row`) or in
   a new `_normalize_data()` hook.

2. **SM-003** (Business task_type casing): Changing `task_type` from `"business"` to
   `"Business"` affects the `_MODEL_CACHE` key, the `type` column in all Business
   DataFrames, and any downstream code filtering on `type == "business"`. Architect
   Enforcer should assess blast radius in consumers.

---

## Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| schema.py (source) | `src/autom8_asana/dataframes/extractors/schema.py` | Read |
| base.py extractor (source) | `src/autom8_asana/dataframes/extractors/base.py` | Read |
| builders/base.py (source) | `src/autom8_asana/dataframes/builders/base.py` | Read |
| registry.py (source) | `src/autom8_asana/dataframes/models/registry.py` | Read |
| business.py schema (source) | `src/autom8_asana/dataframes/schemas/business.py` | Read |
| extractors/__init__.py (source) | `src/autom8_asana/dataframes/extractors/__init__.py` | Read |
| default.py (sibling) | `src/autom8_asana/dataframes/extractors/default.py` | Read |
| contact.py (sibling) | `src/autom8_asana/dataframes/extractors/contact.py` | Read |
| unit.py (sibling) | `src/autom8_asana/dataframes/extractors/unit.py` | Read |
| test_schema_extractor.py | `tests/unit/dataframes/test_schema_extractor.py` | Read |
| test_schema_extractor_completeness.py | `tests/unit/dataframes/test_schema_extractor_completeness.py` | Read |
| test_schema_extractor_adversarial.py | `tests/unit/dataframes/test_schema_extractor_adversarial.py` | Read |
| test_extractors.py (baseline) | `tests/unit/dataframes/test_extractors.py` | Read |
| All schema files | `src/autom8_asana/dataframes/schemas/*.py` (7 files) | Read |
