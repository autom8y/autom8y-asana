# TDD: Custom Field Reality Remediation

## Metadata
- **TDD ID**: TDD-0030
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **PRD Reference**: [PRD-0024](../requirements/PRD-0024-custom-field-remediation.md)
- **Related TDDs**: [TDD-0023](TDD-0023-custom-field-descriptors.md) (Custom Field Descriptors)
- **Related ADRs**: [ADR-0081](../decisions/ADR-0081-custom-field-descriptor-pattern.md), [ADR-0114](../decisions/ADR-0114-hours-backward-compat.md)

## Overview

This TDD defines the implementation approach for correcting 20+ field type mismatches and missing fields across 4 business models (Unit, AssetEdit, Hours, Location). The changes use existing descriptor infrastructure to swap field types without altering the descriptor pattern itself.

## Requirements Summary

Per PRD-0024, Priority 1 scope:

| Model | Type Mismatches | Missing Fields | Key Changes |
|-------|-----------------|----------------|-------------|
| Unit | 8 | 1 | EnumField -> MultiEnumField (specialty, gender), NumberField -> EnumField (discount) |
| AssetEdit | 3 | 1 constant | enum -> multi_enum (specialty), TextField -> IntField (template_id, offer_id), add PRIMARY_PROJECT_GID |
| Hours | 6 name + 6 type | 0 | "Monday Hours" -> "Monday", text -> multi_enum, remove 3 stale fields |
| Location | 1 | 8 | text -> EnumField (country), remove 3 stale, add 8 missing |

## System Context

```
                    +------------------+
                    |   Asana API      |
                    | (Custom Fields)  |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  SDK Task Model  |
                    |  (raw fields)    |
                    +--------+---------+
                             |
    +--------------------+---+---+--------------------+
    |                    |       |                    |
+---v----+         +-----v--+ +--v-----+        +-----v----+
|  Unit  |         | Hours  | |Location|        |AssetEdit |
+--------+         +--------+ +--------+        +----------+
| Descriptors      | Properties        | Descriptors       |
| (ADR-0081)       | (legacy)          | (manual)          |
+------------------+-------------------+-------------------+
```

**Key Insight**: Unit uses the descriptor pattern (ADR-0081). Hours and Location use legacy manual property accessors. AssetEdit uses a hybrid with manual Fields class + properties.

## Design

### Component Architecture

| Component | Current State | Target State | Change Type |
|-----------|--------------|--------------|-------------|
| `unit.py` | 31 field descriptors | Same count, 8 type changes + 1 add | Type swap |
| `asset_edit.py` | Manual properties + Fields class | Same pattern, 3 type changes + constant | Type swap + add |
| `hours.py` | Legacy properties + Fields class | Legacy properties (new types), simplified Fields | Breaking refactor |
| `location.py` | Legacy properties + Fields class | Legacy properties, updated Fields | Additive + removal |

### Design Decision: Descriptor Pattern Scope

Per ADR-0081, descriptors are used on entities with many fields. For this remediation:

- **Unit**: Keep descriptors (31 fields, established pattern)
- **AssetEdit**: Keep manual pattern (hybrid approach, extending Process)
- **Hours**: Keep legacy pattern (6 fields, specialized time handling)
- **Location**: Keep legacy pattern (12 fields, address-specific helpers)

**Rationale**: Minimize scope. Type corrections do not require pattern migration.

### Component 1: Unit Model Changes

**File**: `/src/autom8_asana/models/business/unit.py`

#### Type Changes (8 fields)

```python
# BEFORE                          # AFTER
specialty = EnumField()           specialty = MultiEnumField()
gender = EnumField()              gender = MultiEnumField()
discount = NumberField()          discount = EnumField()
zip_codes_radius = TextField()    zip_codes_radius = IntField()
filter_out_x = TextField()        filter_out_x = EnumField(field_name="Filter Out x%")
form_questions = TextField()      form_questions = MultiEnumField()
disabled_questions = TextField()  disabled_questions = MultiEnumField()
disclaimers = TextField()         disclaimers = MultiEnumField()
```

#### New Field (1 field)

```python
# Add after custom_disclaimer
internal_notes = TextField()
```

#### Return Type Changes

| Field | Before | After |
|-------|--------|-------|
| `specialty` | `str \| None` | `list[str]` |
| `gender` | `str \| None` | `list[str]` |
| `discount` | `Decimal \| None` | `str \| None` |
| `zip_codes_radius` | `str \| None` | `int \| None` |
| `filter_out_x` | `str \| None` | `str \| None` |
| `form_questions` | `str \| None` | `list[str]` |
| `disabled_questions` | `str \| None` | `list[str]` |
| `disclaimers` | `str \| None` | `list[str]` |
| `internal_notes` | N/A | `str \| None` |

### Component 2: AssetEdit Model Changes

**File**: `/src/autom8_asana/models/business/asset_edit.py`

#### Add Class Constant

```python
class AssetEdit(Process):
    # Per TDD-DETECTION: Primary project GID for entity type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = "1202204184560785"
```

#### Type Changes (3 fields)

The `specialty` property currently returns `str | None` via `_get_enum_field()`. Change to return `list[str]` via `_get_multi_enum_field()`:

```python
# BEFORE
@property
def specialty(self) -> str | None:
    """Specialty type (enum custom field)."""
    return self._get_enum_field(self.Fields.SPECIALTY)

# AFTER
@property
def specialty(self) -> list[str]:
    """Specialty types (multi-enum custom field)."""
    return self._get_multi_enum_field(self.Fields.SPECIALTY)
```

For `template_id` and `offer_id`, change to use `_get_int_field()`:

```python
# BEFORE
@property
def template_id(self) -> str | None:
    return self._get_text_field(self.Fields.TEMPLATE_ID)

@property
def offer_id(self) -> str | None:
    return self._get_text_field(self.Fields.OFFER_ID)

# AFTER
@property
def template_id(self) -> int | None:
    """Template identifier (number custom field)."""
    return self._get_int_field(self.Fields.TEMPLATE_ID)

@property
def offer_id(self) -> int | None:
    """Offer identifier (number custom field).

    Key field for EXPLICIT_OFFER_ID resolution strategy.
    Contains the numeric ID of the associated Offer.
    """
    return self._get_int_field(self.Fields.OFFER_ID)
```

**BREAKING CHANGE**: `offer_id` is used in resolution strategies. Update `_resolve_unit_via_offer_id_async()` to convert int to string for task lookup:

```python
# In _resolve_unit_via_offer_id_async and _resolve_offer_directly_async
offer_gid = str(self.offer_id) if self.offer_id is not None else None
```

### Component 3: Hours Model Overhaul

**File**: `/src/autom8_asana/models/business/hours.py`

Per [ADR-0114](../decisions/ADR-0114-hours-backward-compat.md), we adopt a clean break approach with deprecated aliases.

#### Fields Class Changes

```python
class Fields:
    """Custom field name constants matching Asana reality.

    Per PRD-0024: Field names are "Monday", "Tuesday", etc. (not "Monday Hours").
    Per Audit: Fields are multi_enum type containing time strings like "08:00:00".
    """
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    # Note: Sunday not found in Asana project per audit

    # REMOVED: SUNDAY_HOURS, TIMEZONE, NOTES (not in Asana)
```

#### Property Changes

Replace `_get_text_field` with `_get_multi_enum_field`:

```python
def _get_multi_enum_field(self, field_name: str) -> list[str]:
    """Get multi-enum custom field value as list of strings."""
    value: Any = self.get_custom_fields().get(field_name)
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = item.get("name")
            if name is not None:
                result.append(str(name))
        elif isinstance(item, str):
            result.append(item)
    return result

@property
def monday(self) -> list[str]:
    """Monday operating hours (multi-enum time values).

    Returns list of time strings, e.g., ["08:00:00", "17:00:00"]
    representing open and close times. Empty list if not set.
    """
    return self._get_multi_enum_field(self.Fields.MONDAY)

@monday.setter
def monday(self, value: list[str] | None) -> None:
    self.get_custom_fields().set(self.Fields.MONDAY, value)

# ... similar for tuesday through saturday
```

#### Helper Properties (Optional Enhancement)

```python
@property
def monday_open(self) -> str | None:
    """Monday opening time (first value from multi-enum)."""
    times = self.monday
    return times[0] if times else None

@property
def monday_close(self) -> str | None:
    """Monday closing time (last value from multi-enum)."""
    times = self.monday
    return times[-1] if times and len(times) > 1 else None
```

#### Deprecated Aliases

Per ADR-0114, provide deprecated property aliases for backward compatibility:

```python
@property
def monday_hours(self) -> list[str]:
    """Deprecated: Use .monday instead."""
    import warnings
    warnings.warn(
        "monday_hours is deprecated, use monday instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return self.monday

# ... similar for other days
```

#### Updated Computed Properties

```python
@property
def weekday_hours(self) -> dict[str, list[str]]:
    """All weekday hours as a dictionary.

    Returns:
        Dict mapping day names to list of time strings.
    """
    return {
        "monday": self.monday,
        "tuesday": self.tuesday,
        "wednesday": self.wednesday,
        "thursday": self.thursday,
        "friday": self.friday,
    }

@property
def all_hours(self) -> dict[str, list[str]]:
    """All hours as a dictionary.

    Returns:
        Dict mapping day names to list of time strings.
    """
    return {
        "monday": self.monday,
        "tuesday": self.tuesday,
        "wednesday": self.wednesday,
        "thursday": self.thursday,
        "friday": self.friday,
        "saturday": self.saturday,
    }

def is_open_on(self, day: str) -> bool:
    """Check if business is open on a given day.

    Args:
        day: Day name (lowercase, e.g., "monday").

    Returns:
        True if hours are set for that day (non-empty list).
    """
    hours = self.all_hours.get(day.lower())
    return bool(hours)  # Empty list = closed
```

#### Removed Properties

Remove these properties and their setters:
- `sunday_hours` (field does not exist in Asana)
- `timezone` (field does not exist in Asana)
- `hours_notes` (field does not exist in Asana)
- `weekend_hours` (only contained sunday, which doesn't exist)

### Component 4: Location Model Changes

**File**: `/src/autom8_asana/models/business/location.py`

#### Fields Class Updates

```python
class Fields:
    """Custom field name constants matching Asana reality.

    Per PRD-0024: Updated to match actual Asana project schema.
    """
    # Existing (corrected)
    STREET_NUMBER = "Street #"      # Was STREET
    STREET_NAME = "Street Name"     # NEW
    CITY = "City"                   # Unchanged
    STATE = "State"                 # Unchanged
    ZIP_CODE = "Zip Code"           # Unchanged
    COUNTRY = "Country"             # Type: enum (not text)

    # NEW fields
    TIME_ZONE = "Time Zone"
    SUITE = "Suite"
    NEIGHBORHOOD = "Neighborhood"
    OFFICE_LOCATION = "Office Location"
    MIN_RADIUS = "Min Radius"
    MAX_RADIUS = "Max Radius"

    # REMOVED: PHONE, LATITUDE, LONGITUDE (not in Asana project)
```

#### Type Change: Country

```python
# Add helper method
def _get_enum_field(self, field_name: str) -> str | None:
    """Get enum custom field value, extracting name from dict."""
    value: Any = self.get_custom_fields().get(field_name)
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("name")
    if isinstance(value, str):
        return value
    return str(value)

@property
def country(self) -> str | None:
    """Country code (enum custom field).

    Returns enum value like "US", "CA", "SE", "AU", "United Kingdom, GB".
    """
    return self._get_enum_field(self.Fields.COUNTRY)
```

#### New Properties

```python
@property
def time_zone(self) -> str | None:
    """Time zone (enum custom field)."""
    return self._get_enum_field(self.Fields.TIME_ZONE)

@time_zone.setter
def time_zone(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.TIME_ZONE, value)

@property
def street_number(self) -> int | None:
    """Street number (number custom field)."""
    return self._get_number_field_int(self.Fields.STREET_NUMBER)

@street_number.setter
def street_number(self, value: int | None) -> None:
    self.get_custom_fields().set(self.Fields.STREET_NUMBER, value)

@property
def street_name(self) -> str | None:
    """Street name (text custom field)."""
    return self._get_text_field(self.Fields.STREET_NAME)

@street_name.setter
def street_name(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.STREET_NAME, value)

@property
def suite(self) -> str | None:
    """Suite/unit number (text custom field)."""
    return self._get_text_field(self.Fields.SUITE)

@suite.setter
def suite(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.SUITE, value)

@property
def neighborhood(self) -> str | None:
    """Neighborhood name (text custom field)."""
    return self._get_text_field(self.Fields.NEIGHBORHOOD)

@neighborhood.setter
def neighborhood(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.NEIGHBORHOOD, value)

@property
def office_location(self) -> str | None:
    """Office location description (text custom field)."""
    return self._get_text_field(self.Fields.OFFICE_LOCATION)

@office_location.setter
def office_location(self, value: str | None) -> None:
    self.get_custom_fields().set(self.Fields.OFFICE_LOCATION, value)

@property
def min_radius(self) -> int | None:
    """Minimum service radius (number custom field)."""
    return self._get_number_field_int(self.Fields.MIN_RADIUS)

@min_radius.setter
def min_radius(self, value: int | None) -> None:
    self.get_custom_fields().set(self.Fields.MIN_RADIUS, value)

@property
def max_radius(self) -> int | None:
    """Maximum service radius (number custom field)."""
    return self._get_number_field_int(self.Fields.MAX_RADIUS)

@max_radius.setter
def max_radius(self, value: int | None) -> None:
    self.get_custom_fields().set(self.Fields.MAX_RADIUS, value)

def _get_number_field_int(self, field_name: str) -> int | None:
    """Get number custom field value as integer."""
    value: Any = self.get_custom_fields().get(field_name)
    if value is None:
        return None
    return int(value)
```

#### Updated full_address Property

```python
@property
def full_address(self) -> str:
    """Formatted full address.

    Returns:
        Formatted address string combining available fields.
    """
    parts: list[str] = []

    # Street line: "123 Main Street, Suite 100"
    street_parts: list[str] = []
    if self.street_number:
        street_parts.append(str(self.street_number))
    if self.street_name:
        street_parts.append(self.street_name)
    if street_parts:
        street_line = " ".join(street_parts)
        if self.suite:
            street_line += f", {self.suite}"
        parts.append(street_line)

    # City, State, Zip
    city_state_zip: list[str] = []
    if self.city:
        city_state_zip.append(self.city)
    if self.state:
        city_state_zip.append(self.state)
    if city_state_zip:
        line = ", ".join(city_state_zip)
        if self.zip_code:
            line += f" {self.zip_code}"
        parts.append(line)
    elif self.zip_code:
        parts.append(self.zip_code)

    # Country
    if self.country:
        parts.append(self.country)

    return ", ".join(parts)
```

#### Removed Properties

Remove these properties and their setters:
- `street` (replaced by `street_number` + `street_name`)
- `phone` (field does not exist in Asana)
- `latitude` (field does not exist in Asana)
- `longitude` (field does not exist in Asana)

### API Contracts

No API changes. All changes are internal to SDK model layer.

### Data Flow

```
Asana API Response
       |
       v
Task.custom_fields (raw list[dict])
       |
       v
BusinessEntity.get_custom_fields() -> CustomFieldAccessor
       |
       v
Descriptor/Property __get__
       |
       +--> EnumField._get_value() -> str | None
       +--> MultiEnumField._get_value() -> list[str]
       +--> IntField._get_value() -> int | None
       +--> TextField._get_value() -> str | None
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Hours backward compatibility | Deprecated aliases + clean break | Gradual migration path, clear deprecation warnings | ADR-0114 |
| Preserve descriptor pattern | Keep for Unit only | Minimize change scope, other models have fewer fields | N/A |
| Int coercion for zip_codes_radius | Coerce string -> int via IntField | IntField already handles this safely | N/A |
| Offer ID as int | Return int, convert to str for API calls | Matches Asana reality, explicit conversion is safer | N/A |

## Complexity Assessment

**Complexity Level**: Module

**Justification**:
- Changes are confined to 4 model files
- No new patterns introduced
- Uses existing descriptor infrastructure
- No API changes
- No data migration required (Asana is source of truth)

## Implementation Plan

### Phase 1: Unit Model (Low Risk)

| Task | Estimate |
|------|----------|
| Change 8 descriptor types | 0.5h |
| Add internal_notes field | 0.25h |
| Update unit tests | 1h |
| mypy verification | 0.25h |

**Dependencies**: None

### Phase 2: AssetEdit Model (Medium Risk)

| Task | Estimate |
|------|----------|
| Add PRIMARY_PROJECT_GID | 0.25h |
| Change specialty to multi_enum | 0.5h |
| Change template_id to int | 0.5h |
| Change offer_id to int | 0.5h |
| Update resolution methods for int -> str conversion | 0.5h |
| Update tests | 1h |

**Dependencies**: Phase 1 (Unit changes may affect tests)

### Phase 3: Hours Model (High Risk)

| Task | Estimate |
|------|----------|
| Refactor Fields class (rename + remove stale) | 0.5h |
| Add _get_multi_enum_field helper | 0.25h |
| Change 6 day properties to multi_enum | 1h |
| Add deprecated aliases | 0.5h |
| Add helper properties (open/close) | 0.5h |
| Update computed properties | 0.5h |
| Remove stale properties | 0.25h |
| Update tests (breaking changes) | 2h |

**Dependencies**: None (isolated model)

### Phase 4: Location Model (Medium Risk)

| Task | Estimate |
|------|----------|
| Update Fields class | 0.5h |
| Add _get_enum_field helper | 0.25h |
| Change country to enum | 0.25h |
| Add 8 new properties | 1h |
| Update full_address | 0.5h |
| Remove stale properties | 0.25h |
| Update tests | 1.5h |

**Dependencies**: None (isolated model)

### Total Estimate: ~13 hours

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking consumer code using old Hours property names | High | High | Deprecated aliases with warnings per ADR-0114 |
| Breaking consumer code expecting str from offer_id | Medium | Medium | Document in changelog, explicit int -> str conversion in resolution |
| Type errors in downstream code expecting str from specialty | Medium | Medium | Run mypy across codebase before merge |
| Tests fail against live Asana | Medium | Low | Integration tests to verify against real data |
| Missing fields in Location cause None dereference | Low | Low | All new properties return None when unset |

## Observability

- **Metrics**: None needed (no runtime behavior change)
- **Logging**: Existing descriptor logging sufficient
- **Alerting**: None needed

## Testing Strategy

### Unit Testing

1. **Type verification tests**: Assert return types match expectations
   ```python
   def test_unit_specialty_returns_list():
       unit = Unit.model_validate(task_data)
       assert isinstance(unit.specialty, list)
   ```

2. **Empty/None handling**: Assert graceful handling of missing values
   ```python
   def test_hours_monday_empty_when_unset():
       hours = Hours.model_validate(task_data_no_fields)
       assert hours.monday == []
   ```

3. **Deprecation warnings**: Assert deprecated aliases emit warnings
   ```python
   def test_hours_monday_hours_deprecated():
       hours = Hours.model_validate(task_data)
       with pytest.warns(DeprecationWarning):
           _ = hours.monday_hours
   ```

### Integration Testing

1. **Live Asana verification**: Test against real Asana data
   - Fetch Unit with multi-enum specialty, verify list returned
   - Fetch Hours task, verify multi-enum time values

2. **Resolution with int offer_id**: Test AssetEdit resolution still works with int offer_id

### Regression Testing

1. Run full test suite before merge
2. mypy strict mode on changed files

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should Location.street be kept as deprecated alias? | Architect | Implementation | Decision: No, street_number + street_name provide better semantics |
| Should Hours include Sunday property (returns empty)? | Product | Implementation | Decision: No, field doesn't exist in Asana per audit |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Architect | Initial draft |
