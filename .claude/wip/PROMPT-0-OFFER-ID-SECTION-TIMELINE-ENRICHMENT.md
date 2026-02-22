# Prompt 0: Offer ID Enrichment in Section-Timelines API

## Mission

Add `offer_id` (the internal business identifier) to the section-timelines API response. This enables autom8y-data's reconciliation insight to join section timeline data to its `offers` table by business ID, aggregate `active_section_days` per vertical, and replace the supply-side `days_with_activity` metric with a contractual demand-side metric -- eliminating 40/49 false-positive overbilling anomalies in reconcile-spend reports.

Without `offer_id`, the downstream consumer can only join on `office_phone`, which collapses all verticals for multi-vertical clients into a single `active_section_days` value. This produces incorrect `expected_collection` for any client operating in more than one vertical.

## Why This Matters

### The Downstream Consumer Contract

autom8y-data's reconciliation insight will use `offer_id` to execute this join chain:

```
section_timelines.offer_id --> offers.offer_id --> offers.category (vertical)
```

Then aggregate:
```sql
MAX(active_section_days) GROUP BY (office_phone, vertical)
```

This produces a per-vertical `active_section_days` value that feeds into the corrected expected collection formula:

```
expected_collection = (weekly_budget / 7) * active_section_days
```

**Why MAX:** If ANY offer in a `(office_phone, vertical)` group was active for 7 days, that group was billable for 7 days. `MAX` captures the fullest coverage.

**Why per-vertical matters:** A client with `office_phone = +15551234567` operating in both `chiro` and `dental` may have `active_section_days = 7` for chiro but `active_section_days = 3` for dental (dental offer launched mid-period). An office_phone-only join would pick an arbitrary or MAX'd value, misattributing activity across verticals.

### Impact

| Without offer_id | With offer_id |
|---|---|
| Join on `office_phone` only | Join on `offer_id -> offers.category` |
| All verticals get same `active_section_days` | Each vertical gets its own value |
| Multi-vertical clients: incorrect proration | Multi-vertical clients: correct proration |
| 40/49 false-positive anomalies | Anomalies resolved |

## Architecture Context

### Zero Additional API Calls

The section-timeline service already fetches all required custom field data during task enumeration. The `_TASK_OPT_FIELDS` at line 77-84 of `section_timeline_service.py` includes:

```python
_TASK_OPT_FIELDS: list[str] = [
    "gid",
    "created_at",
    "memberships.section.name",
    "memberships.project.gid",
    "custom_fields.name",       # <-- already fetched
    "custom_fields.text_value",  # <-- already fetched
]
```

The existing `_extract_office_phone()` helper at line 140-155 walks the `custom_fields` array for the field named `"Office Phone"`. The new `_extract_offer_id()` helper follows the identical pattern for the field named `"Offer ID"`.

The Offer entity model confirms this custom field exists (line 180 of `models/business/offer.py`):

```python
offer_id = TextField(field_name="Offer ID")
```

### Compute-on-Read-then-Cache Architecture

Section timelines use a compute-on-read-then-cache pattern (per TDD-SECTION-TIMELINE-REMEDIATION):

1. Check derived cache for pre-computed timelines
2. On cache miss: acquire thundering-herd lock (AMB-3), enumerate tasks, batch-read cached stories, build `SectionTimeline` objects
3. Serialize timelines to derived cache (`_serialize_timeline`)
4. On subsequent requests: deserialize from cache (`_deserialize_timeline`) and compute day counts

`offer_id` must flow through the full pipeline: extraction from task data, construction of `SectionTimeline`, serialization to derived cache, deserialization from derived cache, and final output in `OfferTimelineEntry`.

### Backward Compatibility: Derived Cache

Existing derived cache entries were written WITHOUT the `offer_id` field. After deployment, `_deserialize_timeline()` will encounter cached entries missing this key. The deserialization must default `offer_id` to `None` gracefully, matching how `office_phone` is already handled via `data.get("office_phone")`.

Cache entries have a 5-minute TTL (`_DERIVED_TIMELINE_TTL = 300`), so stale entries without `offer_id` will age out quickly. No cache invalidation or migration is needed.

## Implementation Seam

### 1. Custom Field Extraction (section_timeline_service.py)

The existing `_extract_office_phone()` at line 140-155 is the exact template:

```python
def _extract_office_phone(task_data: dict[str, Any]) -> str | None:
    custom_fields = task_data.get("custom_fields") or []
    for cf in custom_fields:
        if isinstance(cf, dict) and cf.get("name") == "Office Phone":
            return cf.get("text_value")
    return None
```

Add `_extract_offer_id()` with the same pattern, matching on `"Offer ID"` instead of `"Office Phone"`.

### 2. Domain Model (section_timeline.py, line 42-59)

The `SectionTimeline` frozen dataclass currently holds:

```python
@dataclass(frozen=True)
class SectionTimeline:
    offer_gid: str
    office_phone: str | None
    intervals: tuple[SectionInterval, ...]
    task_created_at: datetime | None
    story_count: int
```

Add `offer_id: str | None` as a field. Place it after `office_phone` to keep the custom-field-derived values adjacent.

### 3. API Response Model (section_timeline.py, line 157-187)

The `OfferTimelineEntry` Pydantic model currently exposes:

```python
class OfferTimelineEntry(BaseModel):
    offer_gid: str
    office_phone: str | None
    active_section_days: int
    billable_section_days: int
    current_section: str | None
    current_classification: str | None
```

Add `offer_id: str | None = Field(default=None, description="Internal business offer ID (Offer ID custom field)")`. This is an additive, backward-compatible change to the API contract -- existing consumers ignore unknown fields or use `model_config = {"extra": "forbid"}` on their own response models (which they will update when ready).

### 4. Task Loop in get_or_compute_timelines() (section_timeline_service.py, line 505-585)

The task enumeration loop at line 510-565 extracts `office_phone` at line 519:

```python
office_phone = _extract_office_phone(task.model_dump())
```

Add `offer_id = _extract_offer_id(task.model_dump())` immediately after. Then wire `offer_id` into all three `SectionTimeline(...)` construction sites:

- **Cache hit path** (line 557-565): `SectionTimeline(offer_gid=task_gid, office_phone=office_phone, ...)` -- add `offer_id=offer_id`
- **Cache miss with imputation path** (line 577-585): same addition
- Both sites currently pass `offer_gid`, `office_phone`, `intervals`, `task_created_at`, `story_count`

### 5. build_timeline_for_offer() (section_timeline_service.py, line 266-332)

This standalone function builds a single timeline for the legacy per-offer path. It receives `office_phone` as a parameter and passes it to `SectionTimeline(...)` at line 326-332:

```python
return SectionTimeline(
    offer_gid=offer_gid,
    office_phone=office_phone,
    intervals=tuple(intervals),
    task_created_at=task_created_at,
    story_count=story_count,
)
```

Add `offer_id: str | None` as a parameter and wire it through to the constructor. Callers of `build_timeline_for_offer()` must pass the new parameter.

### 6. _compute_day_counts() (section_timeline_service.py, line 637-700)

This function builds `OfferTimelineEntry` from `SectionTimeline` objects. At line 690-698:

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

Add `offer_id=timeline.offer_id` to the `OfferTimelineEntry(...)` constructor call.

### 7. Derived Cache Serialization (cache/integration/derived.py, line 127-157)

`_serialize_timeline()` converts a `SectionTimeline` to a JSON dict. Currently serializes `offer_gid`, `office_phone`, `intervals`, `task_created_at`, `story_count`.

Add `"offer_id": timeline.offer_id` to the serialized dict.

### 8. Derived Cache Deserialization (cache/integration/derived.py, line 160-199)

`_deserialize_timeline()` reconstructs a `SectionTimeline` from a JSON dict. At line 191-198:

```python
return SectionTimeline(
    offer_gid=data["offer_gid"],
    office_phone=data.get("office_phone"),
    intervals=tuple(intervals),
    task_created_at=(...),
    story_count=data.get("story_count", 0),
)
```

Add `offer_id=data.get("offer_id")` -- using `.get()` (not `data["offer_id"]`) for backward compatibility with cached entries that predate this change. This matches the existing pattern for `office_phone` and `story_count`.

## Files to Modify

| File | Change | Risk |
|------|--------|------|
| `src/autom8_asana/services/section_timeline_service.py` | Add `_extract_offer_id()` helper. Wire `offer_id` through `get_or_compute_timelines()` task loop (3 `SectionTimeline` construction sites). Add `offer_id` param to `build_timeline_for_offer()`. Wire through `_compute_day_counts()` `OfferTimelineEntry` construction. | Low -- additive, follows existing `office_phone` pattern |
| `src/autom8_asana/models/business/section_timeline.py` | Add `offer_id: str \| None` to `SectionTimeline` dataclass and `OfferTimelineEntry` Pydantic model. | Low -- additive field on frozen dataclass and Pydantic model |
| `src/autom8_asana/cache/integration/derived.py` | Add `offer_id` to `_serialize_timeline()` output dict. Add `offer_id=data.get("offer_id")` to `_deserialize_timeline()` with backward-compat default. | Low -- `.get()` handles missing key |
| `tests/unit/models/test_section_timeline.py` | Update `_timeline()` helper to include `offer_id`. Add test for `offer_id` field on `SectionTimeline` and `OfferTimelineEntry`. | Low |
| `tests/unit/services/test_section_timeline_service.py` | Add `TestExtractOfferId` test class (parallel to existing `_extract_office_phone` tests). Update `_make_task_mock()` to accept `offer_id` param. Update `build_timeline_for_offer` tests to verify `offer_id` passthrough. | Low |
| `tests/unit/services/test_get_or_compute_timelines.py` | Update mock task data to include `offer_id` custom field. Verify `OfferTimelineEntry` results include `offer_id`. | Low |
| `tests/api/test_section_timelines.py` | Update API response assertions to include `offer_id` field. | Low |

**Files NOT modified:**

| File | Why untouched |
|------|---------------|
| `src/autom8_asana/api/routes/section_timelines.py` | No changes needed. The route calls `get_or_compute_timelines()` which returns `list[OfferTimelineEntry]`. The new `offer_id` field flows through `OfferTimelineEntry` automatically. The `SectionTimelinesResponse` wrapper uses `list[OfferTimelineEntry]` which picks up the new field. |
| `_TASK_OPT_FIELDS` | Already fetches `custom_fields.name` and `custom_fields.text_value`. No modification needed. |

## Edge Cases

1. **`offer_id` custom field absent on a task**: `_extract_offer_id()` returns `None`. This is acceptable -- the downstream consumer handles `null` `offer_id` by excluding that timeline entry from the join (same behavior as `null` `office_phone`).

2. **`offer_id` present but empty string**: The custom field `text_value` may be `""`. Treat this as equivalent to `None` -- the extraction helper should return `None` for empty strings. (Same consideration exists for `_extract_office_phone()`; follow the same convention.)

3. **Derived cache entries missing `offer_id`**: `_deserialize_timeline()` uses `data.get("offer_id")` which returns `None` for pre-change cached entries. No crash, no migration. TTL of 300 seconds means stale entries age out within 5 minutes.

4. **Serialization round-trip preserves `None`**: `_serialize_timeline()` should include `"offer_id": timeline.offer_id` even when `None`. This produces `{"offer_id": null}` in JSON, which `_deserialize_timeline()` correctly reads back as `None`.

5. **Frozen dataclass constructor ordering**: `SectionTimeline` is a frozen dataclass. Adding `offer_id` as a new field means all existing construction sites must be updated. If positional args are used anywhere (unlikely given the codebase style of keyword args), those will fail at import/test time, which is detectable.

6. **build_timeline_for_offer() callers**: Any callers of this function must pass the new `offer_id` parameter. Find all call sites and update them. The function is called from `get_or_compute_timelines()` (internal to this module) and potentially from tests.

## Verification

### Unit Tests

1. **`_extract_offer_id()` extraction**: Task with `"Offer ID"` custom field returns the text_value. Task without returns `None`. Task with empty string returns `None`.

2. **`SectionTimeline` includes `offer_id`**: Construct with `offer_id="OFR-1234"`, verify field access. Construct with `offer_id=None`, verify field access. Verify frozen (assignment raises `FrozenInstanceError`).

3. **`OfferTimelineEntry` includes `offer_id`**: Construct with and without `offer_id`. Verify JSON serialization includes the field. Verify `model_config = {"extra": "forbid"}` still works.

4. **`_compute_day_counts()` passthrough**: Given a `SectionTimeline` with `offer_id="OFR-1234"`, verify the resulting `OfferTimelineEntry` has `offer_id="OFR-1234"`.

5. **Serialization round-trip**: `_serialize_timeline(timeline)` produces dict with `"offer_id"` key. `_deserialize_timeline(dict)` reconstructs `SectionTimeline` with same `offer_id` value. Round-trip preserves `None` values.

6. **Backward-compat deserialization**: `_deserialize_timeline({"offer_gid": "123", "intervals": [], ...})` (no `offer_id` key) returns `SectionTimeline` with `offer_id=None`. No exception.

7. **Existing tests pass unchanged**: All existing timeline tests must continue to pass. The new `offer_id` field defaults to `None`, so existing test data that does not specify `offer_id` still works.

### API-Level Verification

8. **Endpoint response includes `offer_id`**: Call `GET /api/v1/offers/section-timelines?period_start=2026-02-01&period_end=2026-02-20` and verify response entries include the `offer_id` field.

9. **Sample response shape**:
```json
{
  "data": {
    "timelines": [
      {
        "offer_gid": "1208574839251234",
        "offer_id": "OFR-1234",
        "office_phone": "+15551234567",
        "active_section_days": 7,
        "billable_section_days": 7,
        "current_section": "ACTIVE",
        "current_classification": "active"
      },
      {
        "offer_gid": "1208574839255678",
        "offer_id": null,
        "office_phone": "+15559876543",
        "active_section_days": 3,
        "billable_section_days": 5,
        "current_section": "ACTIVATING",
        "current_classification": "activating"
      }
    ]
  }
}
```

### Integration Verification (Post-Deploy)

10. **autom8y-data consumer test**: After both services deploy, autom8y-data's `AsanaSectionTimelineClient` can parse the response and execute the `offer_id -> offers.offer_id -> offers.category` join chain. This is owned by the autom8y-data initiative and is not a gate for this PR.

## Downstream Consumer Context

autom8y-data's reconciliation insight computes `expected_collection = (weekly_budget / 7) * days_with_activity` where `days_with_activity` is a supply-side metric (days ads produced performance data). When ads have not deployed yet but the client IS contractually active, this understates expected_collection and produces false overbilling anomalies.

The fix: autom8y-data will call this endpoint, join on `offer_id` to resolve each timeline entry to a vertical via its `offers` table, then aggregate `MAX(active_section_days)` per `(office_phone, vertical)` to replace `days_with_activity` in the formula.

autom8y-data does NOT need `offer_gid`. It needs `offer_id` (the business identifier stored as an Asana custom field) and `active_section_days`. The `office_phone` field is used as a secondary correlation key. `billable_section_days`, `current_section`, and `current_classification` are not consumed by this use case but remain in the response for other consumers.

The autom8y-data enrichment is gated by a feature flag (`ASANA_ENRICHMENT_ENABLED`) with graceful degradation: if this endpoint is unavailable or `offer_id` is null, autom8y-data falls back to the existing `days_with_activity`-based calculation. This means autom8y-asana's change can ship independently without coordinating deployment timing.

## Scope Boundary

This initiative covers ONLY the autom8y-asana changes to add `offer_id` to the section-timelines pipeline and API response. It does NOT cover:

- The autom8y-data `AsanaSectionTimelineClient` (separate initiative in autom8y-data)
- The autom8y-data `_enrich_with_active_section_days()` enrichment step
- The autom8y-data ADR for the read-path S2S exception
- Changes to reconcile-spend Lambda
- Any changes to the Asana API calls or `_TASK_OPT_FIELDS`

## Workflow

Run as a **10x-dev orchestrated session** in `~/Code/autom8y-asana`:

1. **Requirements** -- PRD with acceptance criteria for the `offer_id` addition, covering the domain model, service layer, cache layer, and API response changes.
2. **Architecture** -- TDD specifying the exact changes to each file and function, serialization backward compatibility strategy, and test plan.
3. **Implementation** -- Add `_extract_offer_id()`, wire `offer_id` through the full pipeline, update all construction sites and serialization, add tests.
4. **QA** -- Adversarial testing: backward-compat deserialization of old cache entries, null/empty offer_id handling, serialization round-trip, existing test suite regression, API response validation.
