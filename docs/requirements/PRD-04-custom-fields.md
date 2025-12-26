# PRD-04: Custom Fields Architecture

> Consolidated PRD for custom field tracking, descriptors, and remediation.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-0016 (Custom Field Tracking), PRD-0019 (Custom Field Descriptors), PRD-0024 (Custom Field Remediation)
- **Related TDD**: TDD-06-custom-fields
- **Stakeholders**: SDK Users, Business Layer Consumers, SDK Maintainers, Automation Workflows

---

## Executive Summary

The SDK's custom field system requires three integrated improvements:

1. **Change Tracking Unification**: Three independent systems track custom field modifications without coordination, causing duplicate API calls after commits and state corruption across sessions.

2. **Descriptor-Based Declaration**: 800+ lines of repetitive property boilerplate across 5 business models can be reduced to ~110 declarative lines using Python descriptors.

3. **Type Correctness**: A reality audit revealed 20+ type mismatches between SDK declarations and Asana's actual schema, causing silent data loss and runtime exceptions.

This consolidated PRD addresses all three concerns as a unified custom fields architecture initiative.

---

## Problem Statement

### Change Tracking Fragmentation

The SDK has three independent systems tracking custom field changes:

| System | Mechanism | Location | Reset Behavior |
|--------|-----------|----------|----------------|
| System 1 | ChangeTracker snapshot comparison | `persistence/tracker.py` | Reset via `mark_clean()` |
| System 2 | CustomFieldAccessor `_modifications` dict | `models/custom_field_accessor.py` | NOT reset after commit |
| System 3 | Task `_original_custom_fields` deepcopy | `models/task.py` | NEVER reset |

**Impact**: After `commit_async()`, the accessor's `_modifications` dict is not cleared, causing duplicate API calls and wasted quota.

### Property Boilerplate

The business layer contains ~800 lines of repetitive custom field property boilerplate across Business, Contact, Unit, Offer, and Process models. Each of 108 fields requires 7-8 lines:

```python
@property
def company_id(self) -> str | None:
    return self._get_text_field(self.Fields.COMPANY_ID)

@company_id.setter
def company_id(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.COMPANY_ID, value)
```

**Impact**: Adding a new field requires ~15 lines of code. Helper methods are duplicated across 5 models.

### Type Mismatches with Reality

A comprehensive audit revealed significant gaps between SDK declarations and Asana's actual schema:

- **8 type mismatches** in Unit model (e.g., `specialty` declared as enum, actually multi-enum)
- **3 type mismatches** in AssetEdit model plus missing constants
- **Fundamentally broken** Hours model (wrong field names AND types)
- **6+ mismatches** in Location model

**Impact**: Silent data loss, runtime exceptions, and integration test failures.

---

## Goals and Non-Goals

### Goals

| ID | Goal | Success Metric |
|----|------|----------------|
| G1 | Single authoritative change tracking system | `has_changes()` returns `False` after successful commit |
| G2 | Declarative custom field properties | 80% reduction in boilerplate (~700 lines removed) |
| G3 | Type-safe field access | All descriptor types return declared return types |
| G4 | Reality alignment | 100% of Priority 1 fields match Asana's actual schema |
| G5 | Arrow date parsing | DateField returns `Arrow` objects, not raw strings |
| G6 | Preserve external API | All existing property names and behaviors unchanged |

### Non-Goals

- Removal of `get_custom_fields()` method (deprecation only)
- Changes to ChangeTracker core architecture
- Custom field validation beyond type coercion
- Breaking API changes to existing properties
- Enum value validation against allowed options
- Multi-value type coercion on setters

---

## Requirements

### Change Tracking Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CT-001 | CustomFieldAccessor `_modifications` MUST be cleared after successful `commit_async()` | Must |
| CT-002 | Task `_original_custom_fields` snapshot MUST be updated after successful commit | Must |
| CT-003 | `Task.custom_fields_editor()` method MUST be added as preferred accessor | Must |
| CT-004 | `Task.get_custom_fields()` MUST emit deprecation warning | Should |
| CT-005 | Direct mutation of `task.custom_fields` list MUST emit deprecation warning | Should |
| CT-006 | `CustomFieldAccessor.set()` SHOULD skip modification when value equals current | Should |
| CT-007 | Multiple commits of same entity MUST NOT send duplicate API calls | Must |
| CT-008 | Entity reused across sessions MUST have clean state in new session | Must |
| CT-009 | Reset MUST occur only on successful commit, not on failure | Must |

### Descriptor Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| DS-001 | `CustomFieldDescriptor[T]` MUST be a generic base class | Must |
| DS-002 | Base descriptor MUST implement `__set_name__` for field name derivation | Must |
| DS-003 | Base descriptor MUST support explicit `field_name` parameter | Must |
| DS-004 | Descriptors MUST be declared WITHOUT type annotations (Pydantic compatibility) | Must |
| DS-005 | `TextField.__get__` MUST return `str | None` | Must |
| DS-006 | `EnumField` MUST extract `name` from dict value | Must |
| DS-007 | `MultiEnumField.__get__` MUST return `list[str]` (never None) | Must |
| DS-008 | `NumberField.__get__` MUST return `Decimal | None` | Must |
| DS-009 | `IntField.__get__` MUST return `int | None` | Must |
| DS-010 | `PeopleField.__get__` MUST return `list[dict[str, Any]]` | Must |
| DS-011 | `DateField.__get__` MUST return `Arrow | None` | Must |
| DS-012 | Descriptors MUST auto-register fields via `__set_name__` | Must |
| DS-013 | Known abbreviations MUST be preserved (mrr -> MRR, ai -> AI) | Must |
| DS-014 | All descriptor types MUST be in `model_config.ignored_types` | Must |

### Remediation Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| RM-001 | Unit.specialty MUST return `list[str]` (MultiEnumField) | Must |
| RM-002 | Unit.gender MUST return `list[str]` (MultiEnumField) | Must |
| RM-003 | Unit.discount MUST return `str | None` (EnumField, not NumberField) | Must |
| RM-004 | Unit.zip_codes_radius MUST return `int | None` (IntField) | Must |
| RM-005 | Unit.filter_out_x MUST return `str | None` (EnumField) | Must |
| RM-006 | Unit.form_questions MUST return `list[str]` (MultiEnumField) | Must |
| RM-007 | Unit.disabled_questions MUST return `list[str]` (MultiEnumField) | Must |
| RM-008 | Unit.disclaimers MUST return `list[str]` (MultiEnumField) | Must |
| RM-009 | Hours field names MUST match Asana exactly ("Monday" not "Monday Hours") | Must |
| RM-010 | Hours accessors MUST return `list[str]` for time values | Must |
| RM-011 | Hours stale fields (TIMEZONE, NOTES, SUNDAY_HOURS) MUST be removed | Must |
| RM-012 | AssetEdit.specialty MUST return `list[str]` | Must |
| RM-013 | AssetEdit.template_id MUST return `int | None` | Must |
| RM-014 | AssetEdit.offer_id MUST return `int | None` | Must |
| RM-015 | Location.country MUST return `str | None` (EnumField) | Must |
| RM-016 | Location stale fields (PHONE, LATITUDE, LONGITUDE) SHOULD be removed | Should |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Reset operation latency | < 1ms per entity |
| NFR-002 | Property access overhead | < 100ns vs current |
| NFR-003 | Memory overhead per descriptor | < 100 bytes |
| NFR-004 | Type safety | 100% mypy strict clean |
| NFR-005 | Test coverage | >= 90% on changed code |
| NFR-006 | Backward compatibility | 100% existing tests pass |

---

## User Stories

### US-1: Commit Without Duplicate Calls

```python
async with SaveSession(client) as session:
    session.track(task)
    task.custom_fields_editor().set("Priority", "High")
    await session.commit_async()  # First commit - API called

    await session.commit_async()  # Second commit - NO API call (state is clean)
```

### US-2: Declarative Field Definition

```python
# Before: ~15 lines per field
class Business(BusinessEntity):
    class Fields:
        COMPANY_ID = "Company ID"

    def _get_text_field(self, field_name: str) -> str | None:
        value = self.get_custom_fields().get(field_name)
        return value if isinstance(value, str) else None

    @property
    def company_id(self) -> str | None:
        return self._get_text_field(self.Fields.COMPANY_ID)

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set(self.Fields.COMPANY_ID, value)

# After: 1 line per field (Fields auto-generated)
class Business(BusinessEntity):
    company_id = TextField()
    mrr = NumberField(field_name="MRR")
    vertical = EnumField()
    rep = PeopleField()
```

### US-3: Multi-Specialty Selection (Type Correctness)

```python
# Before (broken): Returns single value, loses multi-selections
unit.specialty  # Returns "Dental" (loses "Chiro" if both selected)

# After (correct): Returns all selected values
unit.specialty  # Returns ["Dental", "Chiro"]
```

### US-4: Hours Display (Name Correctness)

```python
# Before (broken): Field name mismatch
hours.monday_hours  # Returns None (field "Monday Hours" doesn't exist)

# After (correct): Matches Asana field names
hours.monday  # Returns ["08:00:00", "17:00:00"]
```

### US-5: DateField with Arrow

```python
process = await Process.from_gid_async(client, gid)

# Before: Raw string
process.process_due_date  # "2025-12-20"

# After: Arrow object
due_date = process.process_due_date
assert isinstance(due_date, Arrow)
assert due_date.format("YYYY-MM-DD") == "2025-12-20"
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Duplicate API calls after commit | 0 | Test: commit twice, verify single API call |
| `has_changes()` after commit | `False` | Unit test assertion |
| Lines of custom field code | -700 (~80% reduction) | LOC count before/after |
| Helper method implementations | 0 (down from 25) | grep count |
| Type mismatches with Asana | 0 for Priority 1 fields | Integration test verification |
| Deprecation warnings logged | 100% for legacy patterns | Test with deprecated method |
| Test coverage | >= 90% | pytest --cov |
| mypy strict pass | 0 errors | mypy --strict |

---

## Dependencies

### Upstream

| Dependency | Status | Impact |
|------------|--------|--------|
| Pydantic v2 | Stable | Model compatibility |
| Arrow library | Stable | DateField parsing |
| ADR-0077 (Pydantic descriptor compatibility) | Accepted | Descriptor pattern |
| CustomFieldAccessor | Stable | get/set integration |
| CascadingFieldDef | Stable | Cascading field integration |

### Downstream (Blocked By This Work)

| Initiative | Reason |
|------------|--------|
| SaveSession Reliability | Correct reset behavior required first |
| Business Field Expansion | Type correctness needed before additions |

---

## Migration Strategy

### Phase 1: Descriptor Infrastructure

1. Add descriptor classes to `models/business/descriptors.py`
2. Update `BusinessEntity.model_config` with `ignored_types`
3. Add Fields auto-generation to `__init_subclass__`

### Phase 2: Change Tracking Fix

1. Add reset hook in `SaveSession._commit_entity()` after successful commit
2. Implement `CustomFieldAccessor.clear_changes()` integration
3. Add `custom_fields_editor()` method with deprecation of `get_custom_fields()`

### Phase 3: Model Migration

Migrate each model one at a time:

1. **Business** (19 fields) - Simplest, validation baseline
2. **Contact** (19 fields) - No Number fields
3. **Process** (9 fields) - Includes DateField
4. **Unit** (31 fields) - Type corrections included
5. **Offer** (39 fields) - Largest model

### Phase 4: Type Remediation

1. Apply type corrections per remediation requirements
2. Fix Hours model field names and types
3. Remove stale fields from Location model
4. Update AssetEdit constants and types

### Phase 5: Cleanup

1. Remove helper methods (`_get_text_field`, etc.)
2. Remove explicit `class Fields:` after verifying auto-generation
3. Upgrade deprecation warnings to errors in next major version

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing code using `get_custom_fields()` | Low | Medium | Deprecation warning, not removal |
| Type changes cause cascading test failures | High | Medium | Run full test suite; phased rollout |
| Hours model change breaks automation | High | High | Prioritize testing; document migration |
| DateField breaks existing date string handling | Medium | Medium | DateField optional initially |
| Fields auto-generation misses edge cases | Medium | Low | Explicit `field_name` override available |

---

## Test Strategy

### Unit Tests

- Descriptor `__get__`/`__set__` for all 7 types
- Field name derivation including abbreviations
- No-op detection in `set()`
- `clear_changes()` behavior
- Value comparison edge cases

### Integration Tests

- SaveSession commit reset verification
- Multiple commits same entity
- Cross-session entity reuse
- All model fields accessible after migration
- Dirty tracking through descriptors

### Regression Tests

- All existing business entity tests pass
- All existing custom field tests pass
- SaveSession tests unchanged (except reset)
- mypy strict mode passes

---

## Appendix: Field Type Reference

### Descriptor Types

| Descriptor | Return Type | Use Case |
|------------|-------------|----------|
| TextField | `str | None` | Text and text area fields |
| EnumField | `str | None` | Single-select dropdowns |
| MultiEnumField | `list[str]` | Multi-select fields (never None) |
| NumberField | `Decimal | None` | Currency and decimal values |
| IntField | `int | None` | Count and integer values |
| PeopleField | `list[dict[str, Any]]` | User references (never None) |
| DateField | `Arrow | None` | Date and datetime fields |

### Known Abbreviations

The following abbreviations are preserved in field name derivation:

- `mrr` -> "MRR"
- `ai` -> "AI"
- `url` -> "URL"
- `id` -> "ID"
- `num` -> "Num"
- `cal` -> "Cal"
- `vca` -> "VCA"
- `sms` -> "SMS"

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-25 | Tech Writer | Consolidated from PRD-0016, PRD-0019, PRD-0024 |
