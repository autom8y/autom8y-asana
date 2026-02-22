# TDD: Offer ID Section-Timeline Enrichment

## Overview

Add `offer_id` (the Asana "Offer ID" custom field value) to the section-timelines pipeline: extraction from task data, domain model, serialization/deserialization, and API response. This is an additive, backward-compatible change that follows the existing `office_phone` pattern exactly.

## Context

- **PRD**: `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md`
- **PROMPT-0**: `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PROMPT-0-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md`
- **Constraint**: Zero additional Asana API calls. `_TASK_OPT_FIELDS` (line 77-84 of `section_timeline_service.py`) already includes `custom_fields.name` and `custom_fields.text_value`.
- **Impact**: HIGH (api_contract, data_model) -- additive, backward-compatible.

## System Design

### Data Flow

```
Asana task data (custom_fields array)
    |
    v
_extract_offer_id(task_data) -> str | None          [NEW: FR-1]
    |
    v
SectionTimeline(offer_id=..., ...)                   [MODIFIED: FR-2]
    |
    +---> _serialize_timeline() -> dict               [MODIFIED: FR-6]
    |         |
    |         v
    |     Derived cache (JSON dict with "offer_id" key)
    |         |
    |         v
    |     _deserialize_timeline() -> SectionTimeline  [MODIFIED: FR-7]
    |
    v
_compute_day_counts() -> OfferTimelineEntry           [MODIFIED: FR-5]
    |
    v
API response: {"offer_id": "OFR-1234", ...}           [MODIFIED: FR-3]
```

### Components Modified

| Component | File | Responsibility |
|-----------|------|---------------|
| Extraction helper | `section_timeline_service.py` | Extract `offer_id` from task custom_fields |
| Domain model | `section_timeline.py` | Carry `offer_id` through the pipeline |
| API response model | `section_timeline.py` | Expose `offer_id` in JSON response |
| Cache serializer | `derived.py` | Persist `offer_id` to derived cache |
| Cache deserializer | `derived.py` | Restore `offer_id` from derived cache (backward-compat) |

### Components NOT Modified (and Why)

| Component | File | Reason |
|-----------|------|--------|
| API route | `api/routes/section_timelines.py` | Returns `list[OfferTimelineEntry]` -- new field flows through automatically |
| Task opt_fields | `section_timeline_service.py` line 77-84 | Already fetches `custom_fields.name` and `custom_fields.text_value` |

---

## Implementation Specification

### Change 1: `_extract_offer_id()` -- FR-1

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py`

**Location**: After `_extract_office_phone()` (lines 140-155). Insert new function at line 157.

**Implementation**:

```python
def _extract_offer_id(task_data: dict[str, Any]) -> str | None:
    """Extract offer_id custom field from raw task data.

    Walks custom_fields array looking for the "Offer ID" field.
    Normalizes empty strings to None (DD-1: empty offer_id is
    semantically meaningless for join-key purposes).

    Args:
        task_data: Raw task dict from Asana API.

    Returns:
        Offer ID string or None.
    """
    custom_fields = task_data.get("custom_fields") or []
    for cf in custom_fields:
        if isinstance(cf, dict) and cf.get("name") == "Offer ID":
            return cf.get("text_value") or None
    return None
```

**Design Decision DD-1**: `return cf.get("text_value") or None` normalizes both `None` and `""` to `None` via Python's falsy semantics. This differs from `_extract_office_phone()` which returns raw `text_value` (including `""`). The inconsistency is acceptable because `offer_id` is a join key where empty strings are semantically meaningless. FR-9 (Could Have) in the PRD addresses the `office_phone` case separately.

---

### Change 2: `SectionTimeline` Domain Model -- FR-2

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py`

**Location**: Lines 55-59. Add `offer_id` field after `office_phone` (line 56).

**Before** (lines 55-59):
```python
    offer_gid: str
    office_phone: str | None
    intervals: tuple[SectionInterval, ...]
    task_created_at: datetime | None
    story_count: int
```

**After**:
```python
    offer_gid: str
    office_phone: str | None
    offer_id: str | None
    intervals: tuple[SectionInterval, ...]
    task_created_at: datetime | None
    story_count: int
```

**Rationale**: Placing `offer_id` after `office_phone` groups custom-field-derived values together (DD-2). All construction sites use keyword arguments, so positional ordering is irrelevant to correctness.

**Docstring update**: Add `offer_id: Internal business offer ID (Offer ID custom field), or None.` to the Attributes section in the docstring (lines 46-53).

---

### Change 3: `OfferTimelineEntry` API Response Model -- FR-3

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py`

**Location**: After `office_phone` field (lines 171-173). Insert new field at line 174.

**Before** (lines 170-173):
```python
    offer_gid: str = Field(..., description="Asana task GID")
    office_phone: str | None = Field(
        default=None, description="Office phone custom field"
    )
```

**After**:
```python
    offer_gid: str = Field(..., description="Asana task GID")
    office_phone: str | None = Field(
        default=None, description="Office phone custom field"
    )
    offer_id: str | None = Field(
        default=None,
        description="Internal business offer ID (Offer ID custom field)",
    )
```

**Backward compatibility**: This is an additive field with `default=None`. The `model_config = {"extra": "forbid"}` on line 187 applies to INPUT validation (rejecting unknown fields passed to the constructor), not to output serialization. Existing consumers parsing the response will either ignore the new field or fail if they use `extra="forbid"` on their own model (their responsibility to update).

**Docstring update**: Add `offer_id: Internal business offer ID (null if not set).` to the Attributes section (lines 162-168).

---

### Change 4: Task Loop Wiring in `get_or_compute_timelines()` -- FR-4

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py`

**4a. Extraction** (after line 519):

**Before** (line 519):
```python
            office_phone = _extract_office_phone(task.model_dump())
```

**After**:
```python
            office_phone = _extract_office_phone(task.model_dump())
            offer_id = _extract_offer_id(task.model_dump())
```

**Optimization note**: `task.model_dump()` is called twice. However, the existing `office_phone` extraction already calls it once, and adding a second call is consistent with the established pattern. If profiling reveals this as a bottleneck (unlikely -- model_dump is cheap for these small task objects), a future optimization can hoist the dump to a local variable. Not doing so now to minimize diff surface.

**4b. Cache hit path** -- `SectionTimeline` construction at lines 557-565:

**Before** (lines 557-565):
```python
                timelines.append(
                    SectionTimeline(
                        offer_gid=task_gid,
                        office_phone=office_phone,
                        intervals=tuple(intervals),
                        task_created_at=task_created_at,
                        story_count=story_count,
                    )
                )
```

**After**:
```python
                timelines.append(
                    SectionTimeline(
                        offer_gid=task_gid,
                        office_phone=office_phone,
                        offer_id=offer_id,
                        intervals=tuple(intervals),
                        task_created_at=task_created_at,
                        story_count=story_count,
                    )
                )
```

**4c. Cache miss imputation path** -- `SectionTimeline` construction at lines 577-585:

**Before** (lines 577-585):
```python
                        timelines.append(
                            SectionTimeline(
                                offer_gid=task_gid,
                                office_phone=office_phone,
                                intervals=tuple(intervals),
                                task_created_at=task_created_at,
                                story_count=0,
                            )
                        )
```

**After**:
```python
                        timelines.append(
                            SectionTimeline(
                                offer_gid=task_gid,
                                office_phone=office_phone,
                                offer_id=offer_id,
                                intervals=tuple(intervals),
                                task_created_at=task_created_at,
                                story_count=0,
                            )
                        )
```

---

### Change 5: `_compute_day_counts()` Passthrough -- FR-5

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py`

**Location**: `OfferTimelineEntry` construction at lines 690-698.

**Before** (lines 690-698):
```python
        entries.append(
            OfferTimelineEntry(
                offer_gid=timeline.offer_gid,
                office_phone=timeline.office_phone,
                active_section_days=active_days,
                billable_section_days=billable_days,
                current_section=current_section,
                current_classification=current_classification,
            )
        )
```

**After**:
```python
        entries.append(
            OfferTimelineEntry(
                offer_gid=timeline.offer_gid,
                office_phone=timeline.office_phone,
                offer_id=timeline.offer_id,
                active_section_days=active_days,
                billable_section_days=billable_days,
                current_section=current_section,
                current_classification=current_classification,
            )
        )
```

---

### Change 6: Cache Serialization -- FR-6

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py`

**Location**: `_serialize_timeline()` at lines 139-157. Add `offer_id` to the returned dict.

**Before** (lines 139-157):
```python
    return {
        "offer_gid": timeline.offer_gid,
        "office_phone": timeline.office_phone,
        "intervals": [
            {
                "section_name": iv.section_name,
                "classification": iv.classification.value
                if iv.classification
                else None,
                "entered_at": iv.entered_at.isoformat(),
                "exited_at": iv.exited_at.isoformat() if iv.exited_at else None,
            }
            for iv in timeline.intervals
        ],
        "task_created_at": (
            timeline.task_created_at.isoformat() if timeline.task_created_at else None
        ),
        "story_count": timeline.story_count,
    }
```

**After**:
```python
    return {
        "offer_gid": timeline.offer_gid,
        "office_phone": timeline.office_phone,
        "offer_id": timeline.offer_id,
        "intervals": [
            {
                "section_name": iv.section_name,
                "classification": iv.classification.value
                if iv.classification
                else None,
                "entered_at": iv.entered_at.isoformat(),
                "exited_at": iv.exited_at.isoformat() if iv.exited_at else None,
            }
            for iv in timeline.intervals
        ],
        "task_created_at": (
            timeline.task_created_at.isoformat() if timeline.task_created_at else None
        ),
        "story_count": timeline.story_count,
    }
```

**Note**: `"offer_id": timeline.offer_id` is included even when `offer_id` is `None`, producing `"offer_id": null` in JSON. This ensures round-trip fidelity.

---

### Change 7: Cache Deserialization -- FR-7

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py`

**Location**: `_deserialize_timeline()` at lines 191-199. Add `offer_id` to the `SectionTimeline` constructor.

**Before** (lines 191-199):
```python
    return SectionTimeline(
        offer_gid=data["offer_gid"],
        office_phone=data.get("office_phone"),
        intervals=tuple(intervals),
        task_created_at=(
            datetime.fromisoformat(task_created_at) if task_created_at else None
        ),
        story_count=data.get("story_count", 0),
    )
```

**After**:
```python
    return SectionTimeline(
        offer_gid=data["offer_gid"],
        office_phone=data.get("office_phone"),
        offer_id=data.get("offer_id"),
        intervals=tuple(intervals),
        task_created_at=(
            datetime.fromisoformat(task_created_at) if task_created_at else None
        ),
        story_count=data.get("story_count", 0),
    )
```

**Backward compatibility**: Uses `data.get("offer_id")` (not `data["offer_id"]`). Pre-change cache entries lack this key, so `.get()` returns `None`. This matches the existing patterns for `office_phone` (`.get()`) and `story_count` (`.get()` with default). The 5-minute TTL (`_DERIVED_TIMELINE_TTL = 300`) ensures stale entries age out quickly. No cache invalidation or migration is required at deployment.

---

### Change 8: `build_timeline_for_offer()` Legacy Path -- FR-8 (SHOULD)

**File**: `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py`

**Location**: Function signature at lines 266-273, and `SectionTimeline` construction at lines 326-332.

**8a. Signature** -- add `offer_id` parameter after `office_phone`:

**Before** (lines 266-273):
```python
async def build_timeline_for_offer(
    client: AsanaClient,
    offer_gid: str,
    office_phone: str | None,
    task_created_at: datetime | None,
    current_section_name: str | None,
    current_account_activity: AccountActivity | None,
) -> SectionTimeline:
```

**After**:
```python
async def build_timeline_for_offer(
    client: AsanaClient,
    offer_gid: str,
    office_phone: str | None,
    offer_id: str | None,
    task_created_at: datetime | None,
    current_section_name: str | None,
    current_account_activity: AccountActivity | None,
) -> SectionTimeline:
```

**8b. Docstring** -- add `offer_id: Internal business offer ID (Offer ID custom field).` to the Args section.

**8c. Constructor** -- wire `offer_id` into `SectionTimeline`:

**Before** (lines 326-332):
```python
    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        intervals=tuple(intervals),
        task_created_at=task_created_at,
        story_count=story_count,
    )
```

**After**:
```python
    return SectionTimeline(
        offer_gid=offer_gid,
        office_phone=office_phone,
        offer_id=offer_id,
        intervals=tuple(intervals),
        task_created_at=task_created_at,
        story_count=story_count,
    )
```

**Callers of `build_timeline_for_offer()`**: Only test callers exist (no production callers). Two call sites in `tests/unit/services/test_section_timeline_service.py`:
- Line 290 (`test_with_stories`) -- add `offer_id=None` (or a test value)
- Line 322 (`test_never_moved`) -- add `offer_id=None`

---

## Complete SectionTimeline Construction Site Inventory

Every `SectionTimeline(...)` construction must include `offer_id=`. Failure to update any site will produce a `TypeError` at construction time (frozen dataclass requires all fields).

| # | File | Line | Context | Change |
|---|------|------|---------|--------|
| 1 | `section_timeline_service.py` | 326 | `build_timeline_for_offer()` return | Add `offer_id=offer_id` |
| 2 | `section_timeline_service.py` | 558 | `get_or_compute_timelines()` cache hit path | Add `offer_id=offer_id` |
| 3 | `section_timeline_service.py` | 578 | `get_or_compute_timelines()` cache miss imputation | Add `offer_id=offer_id` |
| 4 | `derived.py` | 191 | `_deserialize_timeline()` | Add `offer_id=data.get("offer_id")` |
| 5 | `test_section_timeline.py` | 40 | `_timeline()` test helper | Add `offer_id` parameter with default `None` |
| 6 | `test_section_timeline_service.py` | 365 | `_build_timeline()` test helper | Add `offer_id` parameter with default `None` |
| 7 | `test_derived_cache.py` | 107 | `_make_timeline()` test helper | Add `offer_id` parameter with default `None` |
| 8 | `test_derived_cache.py` | 177 | Direct construction in `test_none_task_created_at` | Add `offer_id=None` |
| 9 | `test_derived_cache.py` | 210 | Direct construction in `test_empty_intervals` | Add `offer_id=None` |

---

## Test Plan

### New Tests

#### T1: `_extract_offer_id()` -- `TestExtractOfferId` class in `test_section_timeline_service.py`

Parallel to the existing `TestExtractOfficePhone` class (lines 247-261). Add after line 261.

| Test | Input | Expected | PRD SC |
|------|-------|----------|--------|
| `test_found` | `custom_fields` with `"Offer ID"` having `text_value="OFR-1234"` | `"OFR-1234"` | SC-1 |
| `test_not_found` | `custom_fields` without `"Offer ID"` | `None` | SC-2 |
| `test_empty_custom_fields` | `{}` (no `custom_fields` key) | `None` | SC-2 |
| `test_empty_string_normalized_to_none` | `"Offer ID"` with `text_value=""` | `None` | SC-3 |
| `test_none_text_value_returns_none` | `"Offer ID"` with `text_value=None` | `None` | EC-3 |
| `test_non_dict_entries_skipped` | `custom_fields` containing non-dict entries | `None` | EC-8 |

#### T2: `SectionTimeline.offer_id` field -- in `test_section_timeline.py`

Add to `TestSectionTimelineFrozen` class or as new tests.

| Test | Verification | PRD SC |
|------|-------------|--------|
| `test_offer_id_accessible` | Construct with `offer_id="OFR-1234"`, assert `tl.offer_id == "OFR-1234"` | SC-4 |
| `test_offer_id_none` | Construct with `offer_id=None`, assert `tl.offer_id is None` | SC-4 |
| `test_offer_id_frozen` | Attempt assignment, expect `FrozenInstanceError` | SC-4 |

#### T3: `OfferTimelineEntry.offer_id` field -- in `test_section_timeline.py`

Add to `TestOfferTimelineEntry` class.

| Test | Verification | PRD SC |
|------|-------------|--------|
| `test_offer_id_in_serialization` | Construct with `offer_id="OFR-1234"`, assert in `model_dump()` output | SC-5 |
| `test_offer_id_null_in_serialization` | Construct without `offer_id`, assert `"offer_id": None` in output | SC-5 |
| `test_offer_id_default_none` | Construct without passing `offer_id`, assert `entry.offer_id is None` | SC-5 |

#### T4: `_compute_day_counts()` passthrough -- in `test_section_timeline_service.py`

Add to `TestComputeDayCountsCurrentFields` class.

| Test | Verification | PRD SC |
|------|-------------|--------|
| `test_offer_id_passthrough` | Build `SectionTimeline` with `offer_id="OFR-1234"`, verify `OfferTimelineEntry.offer_id == "OFR-1234"` | SC-6 |
| `test_offer_id_none_passthrough` | Build with `offer_id=None`, verify `OfferTimelineEntry.offer_id is None` | SC-6 |

#### T5: Cache serialization/deserialization -- in `test_derived_cache.py`

Add to `TestSerializationRoundTrip` class.

| Test | Verification | PRD SC |
|------|-------------|--------|
| `test_offer_id_round_trip` | `offer_id="OFR-1234"` survives serialize-then-deserialize | SC-8, SC-10 |
| `test_offer_id_none_round_trip` | `offer_id=None` survives serialize-then-deserialize | SC-8, SC-10 |
| `test_backward_compat_missing_offer_id` | Deserialize a dict without `"offer_id"` key, expect `offer_id=None` | SC-9 |
| `test_serialized_includes_offer_id_key` | Serialized dict contains `"offer_id"` key (even when None) | SC-8 |

#### T6: `build_timeline_for_offer()` -- in `test_section_timeline_service.py`

Update existing tests in `TestBuildTimelineForOffer` class.

| Test | Change | PRD SC |
|------|--------|--------|
| `test_with_stories` (line 290) | Add `offer_id="OFR-TEST"` to call, assert `timeline.offer_id == "OFR-TEST"` | SC-13 |
| `test_never_moved` (line 322) | Add `offer_id=None` to call, assert `timeline.offer_id is None` | SC-13 |

#### T7: API endpoint -- in `test_section_timelines.py`

Add `offer_id` to `_mock_entries()` and add assertion.

| Test | Change | PRD SC |
|------|--------|--------|
| `_mock_entries()` | Add `offer_id="OFR-001"` to first entry, `offer_id=None` to second and third | SC-6 |
| `test_offer_id_in_response` | New test: verify `offer_id` appears in response JSON for each timeline entry | SC-6 |
| `test_offer_id_null_in_response` | New test: verify `offer_id: null` for entries without offer_id | SC-6 |

### Modified Test Helpers

These helpers construct `SectionTimeline` and must accept the new field. All use keyword arguments, so adding `offer_id: str | None = None` as a parameter with default `None` ensures all existing callers continue to work without modification.

| Helper | File | Line | Change |
|--------|------|------|--------|
| `_timeline()` | `test_section_timeline.py` | 32-46 | Add `offer_id: str \| None = None` param, pass to `SectionTimeline()` |
| `_build_timeline()` | `test_section_timeline_service.py` | 359-371 | Add `offer_id: str \| None = None` param, pass to `SectionTimeline()` |
| `_make_timeline()` | `test_derived_cache.py` | 83-113 | Add `offer_id: str \| None = None` param, pass to `SectionTimeline()` |
| `_make_task_mock()` | `test_section_timeline_service.py` | 60-88 | Add `offer_id: str \| None = None` param, add to `custom_fields` if provided |
| `_make_task_mock()` | `test_get_or_compute_timelines.py` | 102-130 | Add `offer_id: str \| None = None` param, add to `custom_fields` if provided |
| `_make_serialized_timeline()` | `test_get_or_compute_timelines.py` | 48-72 | Add `offer_id: str \| None = None` param, include in returned dict |

### Existing Test Regression

All existing tests MUST pass without modification beyond the helper updates. The `offer_id` field defaults to `None` everywhere, so test data that omits `offer_id` remains valid. The only tests that require functional changes are the `build_timeline_for_offer` callers (2 sites) which must pass the new parameter because it is a positional-or-keyword parameter in the function signature.

---

## Serialization Backward-Compatibility Strategy

### Problem

After deployment, `_deserialize_timeline()` may encounter derived cache entries written before this change. These entries lack the `"offer_id"` key.

### Solution

1. **Deserialization**: `data.get("offer_id")` returns `None` for missing keys. No exception.
2. **Serialization**: Always writes `"offer_id": timeline.offer_id` (even when `None`), producing `"offer_id": null` in JSON.
3. **TTL**: Stale entries age out within 5 minutes (`_DERIVED_TIMELINE_TTL = 300`).
4. **No migration**: No cache invalidation or migration step needed at deployment.

### Verification

The backward-compat test (T5: `test_backward_compat_missing_offer_id`) constructs a dict WITHOUT the `"offer_id"` key and verifies `_deserialize_timeline()` returns `SectionTimeline` with `offer_id=None`.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Missed `SectionTimeline` construction site | Low | High (TypeError at runtime) | Complete inventory above (9 sites). Frozen dataclass requires all fields -- missed sites produce immediate `TypeError` detectable by any test that constructs `SectionTimeline`. |
| `model_dump()` called twice per task in loop | Low | Low (negligible perf impact) | Consistent with existing pattern. `model_dump()` on these small task objects is microsecond-scale. 3,800 tasks x 2 calls = ~7ms total. Not worth optimizing now. |
| Downstream consumer breaks on new field | Low | Low (additive change) | `OfferTimelineEntry.model_config = {"extra": "forbid"}` applies to input validation only. Consumers parsing responses with their own strict models will get a clear validation error they can fix by adding the field. Feature-flagged on consumer side (`ASANA_ENRICHMENT_ENABLED`). |
| Empty-string normalization inconsistency with `_extract_office_phone()` | Medium | Low (documented, intentional) | DD-1 in PRD documents the rationale. FR-9 (Could Have) addresses the `office_phone` case separately. |

---

## ADRs

None required. This is an additive change following established patterns (`office_phone` extraction, frozen dataclass field addition, derived cache serialization). No new architectural decisions are being made.

---

## Implementation Checklist

For the principal-engineer phase, the implementation order should be:

1. Add `offer_id` field to `SectionTimeline` dataclass (Change 2)
2. Add `offer_id` field to `OfferTimelineEntry` Pydantic model (Change 3)
3. Add `_extract_offer_id()` helper function (Change 1)
4. Wire `offer_id` through `get_or_compute_timelines()` task loop (Change 4)
5. Wire `offer_id` through `_compute_day_counts()` (Change 5)
6. Wire `offer_id` through `build_timeline_for_offer()` (Change 8)
7. Update `_serialize_timeline()` (Change 6)
8. Update `_deserialize_timeline()` (Change 7)
9. Update all test helpers (9 construction sites)
10. Add new tests (T1-T7)
11. Run full test suite to verify no regressions

Steps 1-2 must come first (the type must exist before it can be referenced). Steps 3-8 can be done in any order after that. Step 9 must precede step 10. Step 11 is the final gate.

---

## Open Items

None. All requirements are fully specified.

---

## Attestation

All line numbers verified against source files read during TDD preparation:

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` | Read |
| PROMPT-0 | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PROMPT-0-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` | Read |
| section_timeline_service.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` | Read (701 lines) |
| section_timeline.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py` | Read (188 lines) |
| derived.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` | Read (200 lines) |
| test_section_timeline.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/models/test_section_timeline.py` | Read (438 lines) |
| test_section_timeline_service.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/services/test_section_timeline_service.py` | Read (641 lines) |
| test_get_or_compute_timelines.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/services/test_get_or_compute_timelines.py` | Read (804 lines) |
| test_section_timelines.py | `/Users/tomtenuta/Code/autom8y-asana/tests/api/test_section_timelines.py` | Read (203 lines) |
| test_derived_cache.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/cache/test_derived_cache.py` | Read (463 lines) |
| This TDD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` | Written |
