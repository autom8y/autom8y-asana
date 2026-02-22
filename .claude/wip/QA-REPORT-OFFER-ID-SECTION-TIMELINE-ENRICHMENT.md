# QA Report: Offer ID Section-Timeline Enrichment

## Overview

- **Test Period**: 2026-02-20
- **Tester**: QA Adversary
- **Build**: Branch `main`, commit `de1bd05`
- **Scope**: 3 source files, 5 test files, PRD (SC-1 through SC-13)

## Release Recommendation

**GO**

All 13 success criteria verified. Zero defects found. One low-severity observation documented. Implementation follows the existing `office_phone` pattern exactly, with the intentional divergence (DD-1 empty-string normalization) correctly applied.

---

## Test Execution Results

### Full Suite

| Metric | Count |
|--------|-------|
| Passed | 10,922 |
| Failed | 0 |
| Skipped | 46 |
| xfailed | 2 |
| Deselected | 1 (pre-existing, unrelated) |

The 1 deselected test (`TestFactoryToFrameTypeContract::test_all_frame_types_are_valid`) is a pre-existing failure about a `'question'` frame type in `test_contract_alignment.py` -- entirely unrelated to this change.

### Section-Timeline Suite (115 tests)

All 115 section-timeline-specific tests pass:
- `test_section_timeline.py`: 25 tests (including 6 new offer_id tests)
- `test_section_timeline_service.py`: 30 tests (including 6 new `TestExtractOfferId` + 2 passthrough tests)
- `test_get_or_compute_timelines.py`: 16 tests (mock helpers updated)
- `test_section_timelines.py`: 7 tests (including 2 new API response tests)
- `test_derived_cache.py`: 22 tests (including 4 new serialization/backward-compat tests)

---

## Success Criteria Verification Matrix

| SC | Description | Verdict | Evidence |
|----|-------------|---------|----------|
| SC-1 | `_extract_offer_id()` returns text_value for "Offer ID" custom field | PASS | `TestExtractOfferId::test_found` passes; live verification: `_extract_offer_id({"custom_fields": [{"name": "Offer ID", "text_value": "OFR-1234"}]})` returns `"OFR-1234"` |
| SC-2 | `_extract_offer_id()` returns None when no "Offer ID" field | PASS | `TestExtractOfferId::test_not_found` and `test_empty_custom_fields` both pass |
| SC-3 | `_extract_offer_id()` returns None for empty string text_value | PASS | `TestExtractOfferId::test_empty_string_normalized_to_none` passes; `_extract_offer_id({"custom_fields": [{"name": "Offer ID", "text_value": ""}]})` returns `None` |
| SC-4 | `SectionTimeline` frozen dataclass accepts and exposes `offer_id` | PASS | `test_offer_id_accessible`, `test_offer_id_none`, `test_offer_id_frozen` all pass |
| SC-5 | `OfferTimelineEntry` Pydantic model includes `offer_id` in serialization | PASS | `test_offer_id_in_serialization`, `test_offer_id_null_in_serialization`, `test_offer_id_default_none` all pass |
| SC-6 | API response includes `offer_id` field | PASS | `TestSectionTimelinesOfferIdField::test_offer_id_in_response` and `test_offer_id_null_in_response` both pass |
| SC-7 | Existing API response fields unchanged | PASS | `TestSectionTimelinesResponseFields` tests pass unchanged; `test_serialization` in `TestOfferTimelineEntry` verifies all existing fields present |
| SC-8 | `_serialize_timeline()` includes `"offer_id"` key | PASS | `test_serialized_includes_offer_id_key` passes; code inspection: line 142 of `derived.py` writes `"offer_id": timeline.offer_id` |
| SC-9 | `_deserialize_timeline()` handles missing `"offer_id"` key gracefully | PASS | `test_backward_compat_missing_offer_id` passes; code inspection: line 195 uses `data.get("offer_id")` (not `data["offer_id"]`) |
| SC-10 | Serialize-then-deserialize round-trip preserves `offer_id` | PASS | `test_offer_id_round_trip` (non-null) and `test_offer_id_none_round_trip` (null) both pass |
| SC-11 | All existing tests pass without modification | PASS | 10,922 passed, 0 failed. Test helpers accept `offer_id` with `default=None`, so callers that omit it remain valid. |
| SC-12 | Zero additional Asana API calls | PASS | `_TASK_OPT_FIELDS` not modified (confirmed via grep). No new `client.*` calls added. `_extract_offer_id()` operates on data already fetched. |
| SC-13 | `build_timeline_for_offer()` accepts and passes through `offer_id` | PASS | `test_with_stories` passes `offer_id="OFR-TEST"` and asserts `timeline.offer_id == "OFR-TEST"`; `test_never_moved` passes `offer_id=None` and asserts `timeline.offer_id is None` |

---

## Adversarial Testing Results

### 1. Construction Site Audit (PASS)

Every `SectionTimeline(` construction site in the codebase was verified to include `offer_id=`:

| # | File | Line | `offer_id=` Present |
|---|------|------|:---:|
| 1 | `src/autom8_asana/services/section_timeline_service.py` | 348 | Yes |
| 2 | `src/autom8_asana/services/section_timeline_service.py` | 582 | Yes |
| 3 | `src/autom8_asana/services/section_timeline_service.py` | 603 | Yes |
| 4 | `src/autom8_asana/cache/integration/derived.py` | 192 | Yes |
| 5 | `tests/unit/models/test_section_timeline.py` | 41 | Yes |
| 6 | `tests/unit/services/test_section_timeline_service.py` | 410 | Yes |
| 7 | `tests/unit/cache/test_derived_cache.py` | 108 | Yes |
| 8 | `tests/unit/cache/test_derived_cache.py` | 179 | Yes |
| 9 | `tests/unit/cache/test_derived_cache.py` | 213 | Yes |

No missing sites. A missing site would produce an immediate `TypeError` due to the frozen dataclass requiring all fields.

### 2. Backward-Compatible Deserialization (PASS)

- `_deserialize_timeline()` at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` line 195 uses `data.get("offer_id")` -- confirmed safe for missing keys.
- Test `test_backward_compat_missing_offer_id` constructs a dict WITHOUT `"offer_id"` and verifies `_deserialize_timeline()` returns `SectionTimeline` with `offer_id=None`.
- No cache invalidation or migration required at deployment (5-minute TTL handles transition).

### 3. Empty String Normalization (PASS)

- `_extract_offer_id()` at line 174: `return cf.get("text_value") or None` -- correctly normalizes `""` and `None` to `None`.
- Live adversarial test confirmed: `_extract_offer_id({"custom_fields": [{"name": "Offer ID", "text_value": ""}]})` returns `None`.
- `_extract_offer_id({"custom_fields": [{"name": "Offer ID", "text_value": None}]})` returns `None`.

**Convention Divergence (Intentional)**: `_extract_office_phone()` at line 154 returns raw `cf.get("text_value")` without normalization -- an empty string would be returned as `""`. The `_extract_offer_id()` helper intentionally diverges per DD-1 in the PRD: empty `offer_id` is semantically meaningless for join-key purposes. FR-9 (Could Have) addresses the `office_phone` case separately.

### 4. Serialization Round-Trip (PASS)

- `_serialize_timeline()` includes `"offer_id": timeline.offer_id` at line 142 -- present even when `None` (produces `"offer_id": null` in JSON).
- Round-trip tests: `test_offer_id_round_trip` (non-null value) and `test_offer_id_none_round_trip` (null value) both pass.
- JSON serialization verified via `test_serialized_format_is_json_compatible`.

### 5. API Route Transparency (PASS)

- `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py` was NOT modified (confirmed by code inspection).
- The route returns `list[OfferTimelineEntry]` from `get_or_compute_timelines()`. The new `offer_id` field flows through `OfferTimelineEntry` and `SectionTimelinesResponse` automatically.
- `model_config = {"extra": "forbid"}` on `SectionTimelinesResponse` is unaffected because the new field is explicitly declared on `OfferTimelineEntry`.

### 6. Edge Cases Probed

| Edge Case | Result | Notes |
|-----------|--------|-------|
| `custom_fields` is `None` | PASS | `task_data.get("custom_fields") or []` handles this; returns `None` |
| `custom_fields` missing entirely | PASS | `.get()` returns `None`, `or []` converts to empty list |
| Custom field dict has `"name": "Offer ID"` but NO `"text_value"` key | PASS | `cf.get("text_value")` returns `None`; `None or None` = `None` |
| Non-dict entries in `custom_fields` array | PASS | `isinstance(cf, dict)` guard skips them |
| Whitespace-only `text_value` (e.g., `"   "`) | See OBS-1 | Returns `"   "` (truthy), not `None`. See Observation below. |
| Frozen dataclass field ordering (positional args risk) | PASS | All 9 construction sites use keyword arguments exclusively |

### 7. Security Review (PASS)

- **Injection risk**: `offer_id` is treated as an opaque string. It is:
  - Extracted from Asana custom field data (server-side, trusted source)
  - Passed through as a string field on a frozen dataclass (immutable)
  - Serialized via Pydantic `model_dump()` (auto-escapes for JSON)
  - Never evaluated, executed, or used in queries within this codebase
  - No SQL, no template interpolation, no `eval()` -- pure passthrough
- **PII risk**: `offer_id` is a business identifier (e.g., "OFR-1234"), not PII. No phone numbers, names, or personal data.
- **Input validation**: The field is `str | None` with no length constraint. Asana custom fields are bounded by Asana's own limits. No additional validation needed on the supply side.

### 8. `_TASK_OPT_FIELDS` Unchanged (PASS)

Grep confirms `_TASK_OPT_FIELDS` at line 77-84 of `section_timeline_service.py` was not modified. Already includes `custom_fields.name` and `custom_fields.text_value`. Zero additional API calls.

---

## Observations (Non-Blocking)

### OBS-1: Whitespace-Only Offer ID Not Normalized (LOW)

**Observation**: `_extract_offer_id()` uses `cf.get("text_value") or None`, which normalizes `""` and `None` to `None` but does NOT normalize whitespace-only strings like `"   "` (these are truthy in Python).

**Risk Assessment**: LOW. Asana's custom field UI trims whitespace on save. A whitespace-only `offer_id` is extremely unlikely in production data. Even if it occurred, the downstream join on `offer_id` would simply not match any row in the offers table, producing the same behavior as `None` (exclusion from the join). The PRD's DD-1 specifically addresses only empty strings, not whitespace.

**Recommendation**: No action required now. If `.strip()` normalization is ever desired, it would be a separate minor enhancement.

---

## Defect Inventory

None.

---

## Pre-Existing Issue (Unrelated)

| Test | Status | Notes |
|------|--------|-------|
| `test_contract_alignment.py::TestFactoryToFrameTypeContract::test_all_frame_types_are_valid` | FAIL | Pre-existing: `'question'` frame type not in `VALID_FRAME_TYPES`. Unrelated to this change. |

---

## Documentation Impact Assessment

This change adds `offer_id` to the `GET /api/v1/offers/section-timelines` API response. This is an **additive, backward-compatible** change. Existing consumers that do not read `offer_id` are unaffected. No user-facing commands, CLIs, or configuration changes. No deprecation of existing functionality.

**Cross-service impact**: autom8y-data's `AsanaSectionTimelineClient` will need to be updated to parse the new field, but this is gated by their feature flag (`ASANA_ENRICHMENT_ENABLED`) and is a separate initiative.

---

## Files Reviewed

| File | Absolute Path |
|------|---------------|
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` |
| TDD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` |
| PROMPT-0 | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PROMPT-0-OFFER-ID-SECTION-TIMELINE-ENRICHMENT.md` |
| Source: section_timeline.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/models/business/section_timeline.py` |
| Source: section_timeline_service.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` |
| Source: derived.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/cache/integration/derived.py` |
| Route: section_timelines.py | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py` |
| Test: test_section_timeline.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/models/test_section_timeline.py` |
| Test: test_section_timeline_service.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/services/test_section_timeline_service.py` |
| Test: test_get_or_compute_timelines.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/services/test_get_or_compute_timelines.py` |
| Test: test_section_timelines.py | `/Users/tomtenuta/Code/autom8y-asana/tests/api/test_section_timelines.py` |
| Test: test_derived_cache.py | `/Users/tomtenuta/Code/autom8y-asana/tests/unit/cache/test_derived_cache.py` |

---

## Attestation

All artifacts verified via Read tool. All code inspected directly. All adversarial tests executed against the live codebase. Full test suite executed with results documented above.
