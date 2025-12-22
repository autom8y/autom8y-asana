# PRD: Custom Field Reality Remediation

## Metadata
- **PRD ID**: PRD-0024
- **Status**: Draft
- **Author**: Requirements Analyst
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **Stakeholders**: SDK consumers, automation workflows, integration tests
- **Related PRDs**: PRD-0010 (Business Model Layer), PRD-0016 (Custom Field Tracking)
- **Source Document**: `/docs/analysis/CUSTOM-FIELD-REALITY-AUDIT.md`

## Problem Statement

**What problem are we solving?**

A comprehensive audit of Asana's actual custom field schema revealed significant gaps between what our SDK models declare and what Asana actually stores. The SDK currently has:

- **8 type mismatches** in Unit model (e.g., `specialty` declared as `EnumField` but is actually `multi_enum`)
- **3 type mismatches** in AssetEdit model plus a missing `PRIMARY_PROJECT_GID`
- **Fundamentally broken** Hours model (wrong field names AND wrong field types)
- **6+ mismatches** in Location model (stale fields, missing fields, wrong types)

**For whom?**

1. **SDK consumers**: Developers who call `unit.specialty` expect it to behave like an enum, but when they set a single value, Asana silently fails or truncates because it expects a list.
2. **Automation workflows**: Field cascading and inheritance logic produces unexpected results when field types don't match reality.
3. **Integration tests**: Tests pass locally but fail against real Asana because modeled types don't match actual API responses.

**What's the impact of not solving it?**

1. **Silent data loss**: Setting `unit.specialty = "Dental"` when Asana expects `["Dental"]` may silently fail or overwrite existing multi-selections.
2. **Runtime exceptions**: Type coercion fails when API returns `number` but model expects `str`.
3. **Broken business logic**: Hours model is unusable - it looks for fields that don't exist (`"Monday Hours"` vs `"Monday"`).
4. **Integration test failures**: Any test touching these fields will fail against live Asana.
5. **Developer distrust**: SDK becomes unreliable, forcing consumers to bypass it and use raw API calls.

## Goals & Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| Type correctness | All Priority 1 fields match Asana's actual type | 100% |
| Field name accuracy | All field constants match Asana's actual names | 100% |
| Test coverage | New/updated integration tests pass against live Asana | All pass |
| No regression | Existing unit tests continue to pass | 100% |
| Type safety | mypy passes with strict mode | 0 errors |

## Scope

### In Scope (Priority 1)

**1. Unit Model Fixes** (`/src/autom8_asana/models/business/unit.py`)

| Field | Current Type | Correct Type | Change Required |
|-------|--------------|--------------|-----------------|
| `specialty` | `EnumField` | `MultiEnumField` | Type change |
| `gender` | `EnumField` | `MultiEnumField` | Type change |
| `discount` | `NumberField` | `EnumField` | Type change |
| `zip_codes_radius` | `TextField` | `IntField` | Type change |
| `filter_out_x` | `TextField` | `EnumField` | Type change |
| `form_questions` | `TextField` | `MultiEnumField` | Type change |
| `disabled_questions` | `TextField` | `MultiEnumField` | Type change |
| `disclaimers` | `TextField` | `MultiEnumField` | Type change |
| `internal_notes` | NOT DEFINED | `TextField` | Add new field |

**2. AssetEdit Model Fixes** (file to be identified via codebase search)

| Field | Current Type | Correct Type | Change Required |
|-------|--------------|--------------|-----------------|
| `specialty` | `enum` property | `multi_enum` property | Type change |
| `template_id` | `TextField` | `IntField` | Type change |
| `offer_id` | `TextField` | `IntField` | Type change |
| `PRIMARY_PROJECT_GID` | NOT DEFINED | `"1202204184560785"` | Add constant |

**3. Hours Model Overhaul** (`/src/autom8_asana/models/business/hours.py`)

| Issue | Current | Correct | Change Required |
|-------|---------|---------|-----------------|
| Field names | `"Monday Hours"`, `"Tuesday Hours"`, ... | `"Monday"`, `"Tuesday"`, ... | Rename all 6 constants |
| Field types | `text` (implied via `_get_text_field`) | `multi_enum` | Change accessor return types |
| Return type | `str \| None` | `list[str] \| None` | Update property signatures |
| Stale fields | `TIMEZONE`, `NOTES`, `SUNDAY_HOURS` | Remove | Delete from Fields class |

**4. Location Model Fixes** (`/src/autom8_asana/models/business/location.py`)

| Issue | Current | Correct | Change Required |
|-------|---------|---------|-----------------|
| `country` type | text (implied) | `EnumField` | Type change |
| Stale fields | `PHONE`, `LATITUDE`, `LONGITUDE` | Remove | Delete (not in Asana project) |
| Missing fields | - | `TIME_ZONE`, `STREET_NUMBER`, `STREET_NAME`, `SUITE`, `NEIGHBORHOOD`, `OFFICE_LOCATION`, `MIN_RADIUS`, `MAX_RADIUS` | Add new fields |

### Out of Scope (Priority 2+)

| Item | Rationale | Future Work |
|------|-----------|-------------|
| **AssetEditHolder custom fields** | Breaks holder pattern architecture; requires ADR | PRD-TBD: Holder Pattern Extension |
| **Specialty field duality** | Two different GIDs/types across projects; needs architectural decision | ADR-TBD: Shared Field Strategy |
| **Missing Business fields** (16 fields) | Additive, not correctness; lower impact | PRD-TBD: Business Field Expansion |
| **Missing Contact fields** (2 fields) | Additive, not correctness | PRD-TBD: Contact Field Expansion |
| **Missing Offer fields** (5 fields) | Additive, TikTok/Sub ID fields | PRD-TBD: Offer Field Expansion |
| **Process subclasses** (Sales has 67+ fields) | Major architectural change | PRD-TBD: Process Specialization |
| **Unit stale field** (`booking_type`) | Needs verification if on Business instead | Discovery needed |

## Requirements

### Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-001 | Unit.specialty returns `list[str]` for multi-enum values | Must | `unit.specialty` returns a list; setting `["Dental", "Chiro"]` persists both values |
| FR-002 | Unit.gender returns `list[str]` for multi-enum values | Must | `unit.gender` returns a list; multiple gender selections preserved |
| FR-003 | Unit.discount returns enum string (e.g., "10%", "20%", "None") | Must | `unit.discount` returns enum selection, not a number |
| FR-004 | Unit.zip_codes_radius returns `int` | Must | `unit.zip_codes_radius` returns integer value |
| FR-005 | Unit.filter_out_x returns enum string | Must | `unit.filter_out_x` returns enum selection |
| FR-006 | Unit.form_questions returns `list[str]` | Must | Multi-select values returned as list |
| FR-007 | Unit.disabled_questions returns `list[str]` | Must | Multi-select values returned as list |
| FR-008 | Unit.disclaimers returns `list[str]` | Must | Multi-select values returned as list |
| FR-009 | Unit.internal_notes accessor exists | Should | New TextField property added |
| FR-010 | AssetEdit.specialty returns `list[str]` | Must | Same behavior as Unit.specialty |
| FR-011 | AssetEdit.template_id returns `int` | Must | Returns integer, not string |
| FR-012 | AssetEdit.offer_id returns `int` | Must | Returns integer, not string (critical for resolution) |
| FR-013 | AssetEdit.PRIMARY_PROJECT_GID defined | Must | `AssetEdit.PRIMARY_PROJECT_GID == "1202204184560785"` |
| FR-014 | Hours field names match Asana exactly | Must | `Fields.MONDAY == "Monday"` (not "Monday Hours") |
| FR-015 | Hours accessors return `list[str]` for time values | Must | `hours.monday` returns `["08:00:00", "17:00:00"]` |
| FR-016 | Hours stale fields removed | Must | `TIMEZONE`, `NOTES`, `SUNDAY_HOURS` removed from Fields class |
| FR-017 | Location.country returns enum string | Must | Returns "US", "CA", "SE", "AU", etc. |
| FR-018 | Location stale fields removed | Should | `PHONE`, `LATITUDE`, `LONGITUDE` removed |
| FR-019 | Location missing fields added | Should | `time_zone`, `street_number`, `street_name`, `suite`, `neighborhood`, `office_location`, `min_radius`, `max_radius` properties added |

### Non-Functional Requirements

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-001 | Type safety | mypy strict passes | `mypy --strict src/autom8_asana/models/business/` exits 0 |
| NFR-002 | Test coverage | Lines touched have tests | pytest-cov shows coverage on changed lines |
| NFR-003 | Backward compatibility | No breaking changes to return types where possible | Review of consuming code |
| NFR-004 | Documentation | Docstrings updated for changed types | All changed properties have accurate docstrings |

## User Stories / Use Cases

### US-001: Unit Multi-Specialty Selection
**As a** SDK consumer building targeting logic,
**I want** `unit.specialty` to return all selected specialties,
**So that** I can properly filter offers for multi-specialty practices.

```python
# Current broken behavior
unit.specialty  # Returns "Dental" (loses "Chiro" if both selected)

# Expected correct behavior
unit.specialty  # Returns ["Dental", "Chiro"]
```

### US-002: Hours Display
**As a** SDK consumer building a business profile page,
**I want** to read actual operating hours from the Hours model,
**So that** I can display when the business is open.

```python
# Current broken behavior
hours.monday_hours  # Returns None (field "Monday Hours" doesn't exist)

# Expected correct behavior
hours.monday  # Returns ["08:00:00", "17:00:00"] (open and close times)
```

### US-003: AssetEdit Resolution by Offer ID
**As a** SDK consumer linking assets to offers,
**I want** `asset_edit.offer_id` to return an integer,
**So that** I can match it against `offer.gid` (which is numeric in context).

```python
# Current broken behavior
asset_edit.offer_id  # Returns "1234567890" (string)

# Expected correct behavior
asset_edit.offer_id  # Returns 1234567890 (int)
```

### US-004: Location Country Validation
**As a** SDK consumer validating business locations,
**I want** `location.country` to return the enum value,
**So that** I can reliably branch logic by country code.

```python
# Current assumption
location.country  # Returns free text (could be "USA", "United States", etc.)

# Expected correct behavior
location.country  # Returns "US" (enum value from Asana)
```

## Assumptions

| Assumption | Basis |
|------------|-------|
| Asana's custom field schema is stable | Audit reflects current production state |
| Multi-enum fields store multiple selections | Asana API documentation and audit verification |
| Hours values are time strings like "08:00:00" | Raw API response sample in audit |
| Location Country enum values include US, CA, SE, AU, GB | Raw API response sample in audit |
| Sunday Hours field does not exist in Asana | Not found in fetched data (may need pagination verification) |
| AssetEdit exists as a separate model file | To be confirmed via codebase search |

## Dependencies

| Dependency | Owner | Status |
|------------|-------|--------|
| Custom field descriptors (ADR-0081) | Architect | Complete |
| MultiEnumField descriptor | SDK Team | Exists in codebase |
| IntField descriptor | SDK Team | Exists in codebase |
| EnumField descriptor | SDK Team | Exists in codebase |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should Hours accessors provide helper methods for parsing time strings? | Architect | TBD | Consider `get_open_time()`, `get_close_time()` helpers |
| Is Unit.booking_type truly stale or moved to Business? | Requirements Analyst | TBD | Verify via Business project audit |
| Should Location.country setter accept both enum value and display name? | Architect | TBD | May need mapping for backward compat |
| What happens to existing tests that use old Hours field names? | QA | TBD | May need test fixture updates |

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing consumer code | High | Medium | Document migration path; consider deprecation period |
| Hours model change breaks automation | High | High | Prioritize Hours testing; may need rollback plan |
| Type changes cause cascading test failures | Medium | High | Run full test suite before merge |
| Enum options change over time | Low | Low | Use string storage, validate on read |

## Implementation Notes

### Hours Model Refactor Strategy

The Hours model requires the most significant changes. Recommended approach:

1. **Rename Fields class constants** (non-breaking if consumers use properties):
   ```python
   class Fields:
       MONDAY = "Monday"  # Was "Monday Hours"
       TUESDAY = "Tuesday"
       # ...
   ```

2. **Change return type** to `list[str] | None`:
   ```python
   @property
   def monday(self) -> list[str] | None:
       """Monday operating hours (multi-enum time values)."""
       return self._get_multi_enum_field(self.Fields.MONDAY)
   ```

3. **Add helper properties** for common use cases:
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

4. **Deprecate old property names** if backward compatibility needed:
   ```python
   @property
   def monday_hours(self) -> list[str] | None:
       """Deprecated: Use .monday instead."""
       import warnings
       warnings.warn("monday_hours is deprecated, use monday", DeprecationWarning)
       return self.monday
   ```

### Unit Model Type Changes

For multi-enum fields, the descriptor handles the type conversion:

```python
# Before
specialty = EnumField()  # Returns str | None

# After
specialty = MultiEnumField()  # Returns list[str] | None
```

For enum fields that were incorrectly typed as other types:

```python
# Before
discount = NumberField()  # Returns Decimal | None

# After
discount = EnumField()  # Returns str | None (e.g., "10%", "20%", "None")
```

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Requirements Analyst | Initial draft from Custom Field Reality Audit |
