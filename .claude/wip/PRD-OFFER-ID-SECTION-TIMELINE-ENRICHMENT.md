# PRD: Offer ID Section-Timeline Enrichment

## Overview

Add the `offer_id` field (the Asana "Offer ID" custom field value) to the `GET /api/v1/offers/section-timelines` API response. This enables autom8y-data's reconciliation insight to join section timeline data to its `offers` table by business ID, aggregate `active_section_days` per vertical, and replace a supply-side metric with a demand-side metric -- eliminating 40 of 49 false-positive overbilling anomalies in reconcile-spend reports.

## Impact Assessment

```yaml
impact: high
impact_categories: [api_contract, data_model]
```

**Rationale**: Adds a new field to the `OfferTimelineEntry` API response model (additive, backward-compatible) and to the `SectionTimeline` frozen dataclass (domain model change). Also modifies the derived cache serialization format (backward-compatible via `.get()` default).

## Background

### Problem

The `GET /api/v1/offers/section-timelines` endpoint currently returns `offer_gid` (the Asana task GID) and `office_phone` but NOT `offer_id` (the internal business identifier stored as an Asana custom field). The downstream consumer (autom8y-data's reconciliation insight) needs `offer_id` to execute this join chain:

```
section_timelines.offer_id --> offers.offer_id --> offers.category (vertical)
```

Without `offer_id`, the downstream consumer can only join on `office_phone`, which collapses all verticals for multi-vertical clients into a single `active_section_days` value. This produces incorrect `expected_collection` for any client operating in more than one vertical (e.g., a client with both `chiro` and `dental` offers).

### Quantified Impact

| Metric | Without offer_id | With offer_id |
|--------|-----------------|---------------|
| Join key | `office_phone` only | `offer_id -> offers.category` |
| Multi-vertical proration | Incorrect (all verticals get same value) | Correct (per-vertical value) |
| False-positive anomalies | 40/49 | Resolved |

### Why Now

The autom8y-data reconciliation insight is being built now. This is the supply-side prerequisite: autom8y-asana must expose `offer_id` before autom8y-data can consume it. The downstream consumer has graceful degradation (feature flag `ASANA_ENRICHMENT_ENABLED`), so this change can ship independently without deployment coordination.

### Architecture Context

Zero additional Asana API calls are required. The `_TASK_OPT_FIELDS` already includes `custom_fields.name` and `custom_fields.text_value`. The existing `_extract_office_phone()` helper extracts a custom field by walking the same `custom_fields` array. The Offer entity model confirms the "Offer ID" custom field exists (`offer_id = TextField(field_name="Offer ID")` in `models/business/offer.py`).

## User Stories

### US-1: Vertical-Aware Reconciliation Join

**As** the autom8y-data reconciliation insight, **I want** each section-timeline entry to include the business `offer_id`, **so that** I can join timeline data to the `offers` table by business ID, resolve each entry to a vertical via `offers.category`, and compute per-vertical `active_section_days` instead of collapsing all verticals into a single value per `office_phone`.

**Acceptance Criteria:**
- AC-1.1: `GET /api/v1/offers/section-timelines` response entries include an `offer_id` field.
- AC-1.2: `offer_id` contains the text value of the Asana "Offer ID" custom field on the task, or `null` if the field is absent or empty.
- AC-1.3: No additional Asana API calls are made to retrieve `offer_id`.
- AC-1.4: Existing response fields (`offer_gid`, `office_phone`, `active_section_days`, `billable_section_days`, `current_section`, `current_classification`) are unchanged.

### US-2: Backward-Compatible Cache Transition

**As** the section-timeline service operator, **I want** the derived cache to handle entries written before the `offer_id` field was added, **so that** deployment does not require cache invalidation or produce errors during the 5-minute TTL transition window.

**Acceptance Criteria:**
- AC-2.1: Deserializing a cached entry that lacks the `offer_id` key produces a `SectionTimeline` with `offer_id=None` (no exception).
- AC-2.2: Serializing a `SectionTimeline` with `offer_id=None` produces a JSON dict containing `"offer_id": null`.
- AC-2.3: A round-trip serialize-then-deserialize preserves the `offer_id` value (including `None`).
- AC-2.4: No cache invalidation or migration is required at deployment time.

## Functional Requirements

### Must Have

- **FR-1: Custom Field Extraction Helper** -- Add `_extract_offer_id(task_data: dict[str, Any]) -> str | None` to `section_timeline_service.py`. Must follow the `_extract_office_phone()` pattern: walk `custom_fields` array, match on `name == "Offer ID"`, return `text_value`. Normalize empty strings (`""`) to `None` (see Design Decision DD-1 below).

- **FR-2: Domain Model Extension** -- Add `offer_id: str | None` field to the `SectionTimeline` frozen dataclass in `models/business/section_timeline.py`. Place after `office_phone` to group custom-field-derived values.

- **FR-3: API Response Model Extension** -- Add `offer_id: str | None = Field(default=None, description="Internal business offer ID (Offer ID custom field)")` to the `OfferTimelineEntry` Pydantic model. This is an additive, backward-compatible API contract change. The `model_config = {"extra": "forbid"}` on `OfferTimelineEntry` is unaffected (the field is explicitly declared).

- **FR-4: Task Loop Wiring** -- In `get_or_compute_timelines()`, extract `offer_id` via `_extract_offer_id(task.model_dump())` alongside the existing `office_phone` extraction. Wire `offer_id` into all `SectionTimeline(...)` construction sites within this function:
  - Cache-hit path (stories found in cache)
  - Cache-miss imputation path (no cached stories, imputed from current section)

- **FR-5: Day Count Passthrough** -- In `_compute_day_counts()`, pass `offer_id=timeline.offer_id` to the `OfferTimelineEntry(...)` constructor.

- **FR-6: Cache Serialization** -- Add `"offer_id": timeline.offer_id` to the dict produced by `_serialize_timeline()` in `cache/integration/derived.py`.

- **FR-7: Cache Deserialization** -- Add `offer_id=data.get("offer_id")` to the `SectionTimeline(...)` constructor in `_deserialize_timeline()`. Use `.get()` (not `data["offer_id"]`) for backward compatibility with pre-change cached entries.

### Should Have

- **FR-8: Legacy Path Wiring** -- Add `offer_id: str | None` parameter to `build_timeline_for_offer()` and wire it to the `SectionTimeline(...)` constructor. This function is the legacy single-offer path (not called from `get_or_compute_timelines()` in production, only from tests), but keeping it consistent prevents drift. Update all callers (currently only tests).

### Could Have

- **FR-9: Empty String Normalization for `_extract_office_phone()`** -- Apply the same empty-string-to-`None` normalization to the existing `_extract_office_phone()` helper for consistency. Currently `_extract_office_phone()` returns `""` if the Asana field contains an empty string. This is a separate concern and should not block this initiative.

### Won't Have (This Initiative)

- Changes to autom8y-data `AsanaSectionTimelineClient`
- Changes to autom8y-data `_enrich_with_active_section_days()` enrichment step
- Changes to reconcile-spend Lambda
- Changes to Asana API calls or `_TASK_OPT_FIELDS`
- API route changes (the route transparently passes through `OfferTimelineEntry` fields)

## Non-Functional Requirements

- **NFR-1: Performance** -- Zero additional Asana API calls. The `_extract_offer_id()` helper is O(n) over the `custom_fields` array (typically 10-20 elements per task). No measurable latency impact on the endpoint (<1ms additional CPU for 3,800 offers).

- **NFR-2: Backward Compatibility** -- The API change is purely additive. Existing consumers that do not read `offer_id` are unaffected. The `OfferTimelineEntry.model_config = {"extra": "forbid"}` applies to input validation, not to output serialization -- existing consumers parsing the response with their own models will either ignore the new field or fail explicitly if they use `extra="forbid"` on their own model (which is their responsibility to update).

- **NFR-3: Cache Transition** -- Pre-change derived cache entries (missing `offer_id`) must deserialize without error. The 5-minute TTL (`_DERIVED_TIMELINE_TTL = 300`) ensures stale entries age out quickly. No cache invalidation or migration step is required at deployment.

- **NFR-4: Test Coverage** -- All new code paths must have unit test coverage. Existing tests must continue to pass without modification (the new field defaults to `None`, so test data that omits `offer_id` remains valid).

## Design Decisions

### DD-1: Empty String Normalization

`_extract_offer_id()` normalizes empty strings to `None`. The existing `_extract_office_phone()` does NOT do this -- it returns whatever `text_value` is, including `""`. For `offer_id`, empty strings are semantically meaningless (an offer without an ID is not joinable), so normalization to `None` is the correct choice. This creates a minor inconsistency with `_extract_office_phone()`, which FR-9 (Could Have) addresses separately.

**Implementation**: `return cf.get("text_value") or None` handles both `None` and `""` cases via Python's falsy semantics.

### DD-2: Field Placement in SectionTimeline

`offer_id: str | None` is placed immediately after `office_phone: str | None` in the `SectionTimeline` dataclass to group custom-field-derived values together. All construction sites use keyword arguments, so positional ordering is irrelevant to correctness but matters for readability.

## Edge Cases

| ID | Case | Expected Behavior |
|----|------|------------------|
| EC-1 | `"Offer ID"` custom field absent on a task | `_extract_offer_id()` returns `None`. The timeline entry has `offer_id=null` in the API response. Downstream consumer excludes it from the join. |
| EC-2 | `"Offer ID"` custom field present but `text_value` is empty string `""` | `_extract_offer_id()` returns `None` (per DD-1). Same downstream behavior as EC-1. |
| EC-3 | `"Offer ID"` custom field present but `text_value` is `None` | `_extract_offer_id()` returns `None`. |
| EC-4 | Derived cache entry written before this change (missing `"offer_id"` key) | `_deserialize_timeline()` uses `data.get("offer_id")` which returns `None`. No exception. Entry ages out within 5 minutes. |
| EC-5 | Serialization round-trip with `offer_id=None` | `_serialize_timeline()` writes `"offer_id": null`. `_deserialize_timeline()` reads it back as `None`. Lossless. |
| EC-6 | Serialization round-trip with `offer_id="OFR-1234"` | `_serialize_timeline()` writes `"offer_id": "OFR-1234"`. `_deserialize_timeline()` reads it back as `"OFR-1234"`. Lossless. |
| EC-7 | `custom_fields` array is `None` or missing on the task | `_extract_offer_id()` uses `task_data.get("custom_fields") or []`, falls through to `return None`. Same pattern as `_extract_office_phone()`. |
| EC-8 | `custom_fields` entry is not a dict (malformed data) | `isinstance(cf, dict)` guard skips non-dict entries. Same pattern as `_extract_office_phone()`. |
| EC-9 | Frozen dataclass construction missing `offer_id` kwarg | `TypeError` at construction time. All construction sites MUST be updated. Detectable at import/test time. |

## Success Criteria

These are testable by QA Adversary:

- [ ] **SC-1**: `_extract_offer_id()` returns the `text_value` when a custom field named `"Offer ID"` exists with a non-empty value.
- [ ] **SC-2**: `_extract_offer_id()` returns `None` when no `"Offer ID"` custom field exists on the task.
- [ ] **SC-3**: `_extract_offer_id()` returns `None` when `"Offer ID"` custom field has an empty string `text_value`.
- [ ] **SC-4**: `SectionTimeline` frozen dataclass accepts `offer_id: str | None` and exposes it as a read-only attribute.
- [ ] **SC-5**: `OfferTimelineEntry` Pydantic model includes `offer_id` field that serializes to JSON correctly (both non-null and null values).
- [ ] **SC-6**: `GET /api/v1/offers/section-timelines` response entries include the `offer_id` field.
- [ ] **SC-7**: Existing API response fields are unchanged in structure and semantics.
- [ ] **SC-8**: `_serialize_timeline()` output dict includes `"offer_id"` key.
- [ ] **SC-9**: `_deserialize_timeline()` with a dict missing `"offer_id"` returns `SectionTimeline` with `offer_id=None` (no exception).
- [ ] **SC-10**: Serialize-then-deserialize round-trip preserves `offer_id` value for both `None` and non-null cases.
- [ ] **SC-11**: All existing test suites pass without modification (new field defaults to `None`).
- [ ] **SC-12**: Zero additional Asana API calls -- verified by absence of new entries in `_TASK_OPT_FIELDS` and no new `client.*` calls.
- [ ] **SC-13**: `build_timeline_for_offer()` accepts and passes through `offer_id` parameter (FR-8, SHOULD).

## Out of Scope

| Item | Rationale |
|------|-----------|
| autom8y-data `AsanaSectionTimelineClient` changes | Separate initiative in autom8y-data. |
| autom8y-data `_enrich_with_active_section_days()` | Downstream consumer, not this service's concern. |
| autom8y-data ADR for read-path S2S exception | Architectural decision in autom8y-data. |
| reconcile-spend Lambda changes | Downstream consumer. |
| Asana API call changes or `_TASK_OPT_FIELDS` modification | Not needed -- `custom_fields.name` and `custom_fields.text_value` already fetched. |
| `_extract_office_phone()` empty-string normalization (FR-9) | Separate concern. Filed as Could Have, not a gate for this work. |
| Cache invalidation or migration | Not needed -- 5-minute TTL handles transition. |
| API route file changes | Not needed -- `OfferTimelineEntry` changes flow through automatically. |

## Files to Modify

| File | Change Summary |
|------|---------------|
| `src/autom8_asana/services/section_timeline_service.py` | FR-1 (extraction helper), FR-4 (task loop wiring), FR-5 (day count passthrough), FR-8 (legacy path) |
| `src/autom8_asana/models/business/section_timeline.py` | FR-2 (domain model), FR-3 (API model) |
| `src/autom8_asana/cache/integration/derived.py` | FR-6 (serialization), FR-7 (deserialization) |
| `tests/unit/models/test_section_timeline.py` | Test coverage for FR-2, FR-3 |
| `tests/unit/services/test_section_timeline_service.py` | Test coverage for FR-1, FR-5, FR-8 |
| `tests/unit/services/test_get_or_compute_timelines.py` | Test coverage for FR-4 |
| `tests/api/test_section_timelines.py` | Test coverage for SC-6 |

**Files NOT modified** (and why):
- `src/autom8_asana/api/routes/section_timelines.py` -- Route returns `list[OfferTimelineEntry]` from `get_or_compute_timelines()`. The new field flows through automatically.
- `_TASK_OPT_FIELDS` -- Already includes `custom_fields.name` and `custom_fields.text_value`.

## Requirements Traceability

| Requirement | Source | Stakeholder |
|-------------|--------|-------------|
| FR-1 through FR-7 | PROMPT-0 Sections 1-8 | autom8y-data reconciliation insight (downstream consumer) |
| FR-8 | PROMPT-0 Section 5 | Code consistency / drift prevention |
| DD-1 | PROMPT-0 Edge Case 2 | Data quality (empty strings are semantically null for join keys) |
| NFR-1 | PROMPT-0 "Zero Additional API Calls" | Performance / cost |
| NFR-3 | PROMPT-0 "Backward Compatibility: Derived Cache" | Operational safety |

## Open Questions

None. All requirements are fully specified by PROMPT-0 and confirmed by source code inspection.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PROMPT-0 | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PROMPT-0-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` | Read |
| SectionTimeline model | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py` | Read |
| section_timeline_service | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` | Read |
| derived cache | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` | Read |
| Offer model (field confirmation) | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/offer.py` | Read (lines 175-183) |
| This PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` | Written |
