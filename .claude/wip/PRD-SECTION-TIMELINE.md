# PRD: SectionTimeline Primitive

```yaml
id: PRD-SECTION-TIMELINE-001
status: DRAFT
date: 2026-02-19
author: requirements-analyst
impact: high
impact_categories: [api_contract]
```

---

## 1. Problem Statement

The reconciliation pipeline computes `expected_collection` using `days_with_activity` -- the count of calendar days where an offer had actual ad spend. This metric is self-referential: if ads go dark, spend drops to zero, `days_with_activity` shrinks, expected spend drops proportionally, and the anomaly becomes invisible. The pipeline cannot distinguish "no spend because inactive" from "no spend because something broke."

We need an independent measure of how long an offer *should* have been spending, derived from a source orthogonal to ad spend data: the number of calendar days the offer occupied an ACTIVE-classified Asana section.

### Scope Boundary

This PRD covers only the SectionTimeline primitive itself -- domain models, service, HTTP endpoint, and pre-warm infrastructure. Integration with reconcile-spend, Rules 6 & 7, or ThreeWayComparison is explicitly out of scope. Those consumers will be specified in a separate PRD once this primitive is validated.

---

## 2. Stakeholders

| Stakeholder | Interest |
|-------------|----------|
| Reconciliation pipeline (future consumer) | Independent baseline for expected_collection that does not collapse when ads go dark |
| Operations team | Visibility into how long each offer has been in an active section, independent of ad platform data |
| API consumers (autom8_data, internal tools) | Programmatic access to section timeline data for all offers |

---

## 3. User Stories

### US-1: Timeline Reconstruction from Section History

**As** a reconciliation system,
**I want** a chronological timeline of which Asana section each offer occupied and when,
**so that** I can compute calendar-day counts independent of ad spend data.

### US-2: Active and Billable Day Counts

**As** an API consumer,
**I want** both `active_section_days` and `billable_section_days` for each offer over a date range,
**so that** I can use the appropriate metric for different downstream calculations.

### US-3: Full Project Coverage

**As** an operations analyst,
**I want** timeline data for ALL offers in the Business Offers project regardless of their current section,
**so that** I can audit inactive and ignored offers alongside active ones.

---

## 4. Functional Requirements

### Must Have

#### FR-1: Story Ingestion

Fetch and filter Asana stories to extract section-change events.

- **AC-1.1**: Stories are fetched via `StoriesClient.list_for_task_cached()` using the existing incremental append-only cache infrastructure.
- **AC-1.2**: Only stories with `resource_subtype == "section_changed"` are retained; all other subtypes are discarded.
- **AC-1.3**: Cross-project noise filter: if BOTH `OFFER_CLASSIFIER.classify(new_section.name)` AND `OFFER_CLASSIFIER.classify(old_section.name)` return `None`, the story is skipped. This filters stories from non-Business-Offers projects where both sections are unregistered.
- **AC-1.4**: One-sided filter retention: if only one side (old or new) classifies as `None` while the other classifies to a known `AccountActivity`, the story is retained. This preserves transitions between registered and unregistered sections.
- **AC-1.5**: The `new_section` and `old_section` fields on the `Story` model (existing `NameGid | None` fields) provide the section name via `.name`.

#### FR-2: Timeline Reconstruction

Walk filtered stories chronologically to produce an ordered list of `SectionInterval` values.

- **AC-2.1**: Each `SectionInterval` contains: `started_at: datetime`, `ended_at: datetime | None` (None = open/current interval), `section_name: str`, `classification: AccountActivity | None`.
- **AC-2.2**: `classification` is computed via `OFFER_CLASSIFIER.classify(section_name)`.
- **AC-2.3**: If `classify()` returns `None` (unknown/unregistered section), the interval is created with `classification=None` and a `WARNING`-level log is emitted including the section name and offer GID.
- **AC-2.4**: Intervals with `classification=None` are excluded from both `active_section_days` and `billable_section_days` counts.
- **AC-2.5**: Stories are processed in chronological order (`created_at` ascending). Each story closes the previous interval (`ended_at = story.created_at`) and opens a new one (`started_at = story.created_at`).
- **AC-2.6**: The final interval in the sequence has `ended_at=None`, representing the current (open) state.

#### FR-3: Never-Moved Task Imputation

Handle offers that have never had a `section_changed` story.

- **AC-3.1**: If zero `section_changed` stories remain after filtering (AC-1.2 through AC-1.4), impute a single interval `[task.created_at, None]` (open-ended).
- **AC-3.2**: The imputed interval uses the offer's current section via `Offer.account_activity` for classification.
- **AC-3.3**: If the current classification is `INACTIVE` or `IGNORED`, the imputed interval contributes 0 active days and 0 billable days.
- **AC-3.4**: If the current classification is `ACTIVE`, the imputed interval contributes active and billable days for the full overlap with the query period.
- **AC-3.5**: If the current classification is `ACTIVATING`, the imputed interval contributes 0 active days but billable days for the full overlap with the query period.

#### FR-4: Day Counting

Compute two day-count fields from the timeline and a query period.

- **AC-4.1**: `active_section_days`: count of unique calendar dates within `[period_start, period_end]` (inclusive on both ends) where ANY interval with `classification == ACTIVE` overlaps that date.
- **AC-4.2**: `billable_section_days`: count of unique calendar dates within `[period_start, period_end]` (inclusive on both ends) where ANY interval with `classification in {ACTIVE, ACTIVATING}` overlaps that date.
- **AC-4.3**: Both fields are always present in every response entry. There is no query parameter to toggle or select fields.
- **AC-4.4**: Use `set[date]` for deduplication to handle multi-interval same-day overlaps correctly. If an offer transitions from ACTIVE to ACTIVATING on the same day, that day counts once in both fields.
- **AC-4.5**: Open intervals (`ended_at=None`) are treated as extending to `period_end` for counting purposes. Days beyond `period_end` are never counted.

#### FR-5: Offer Enumeration

Enumerate all offers in the Business Offers project.

- **AC-5.1**: All tasks in project GID `1143843662099250` are enumerated regardless of their current section classification (ACTIVE, ACTIVATING, INACTIVE, IGNORED all included).
- **AC-5.2**: Each response entry contains: `offer_gid: str`, `office_phone: str | None`, `active_section_days: int`, `billable_section_days: int`.
- **AC-5.3**: `office_phone` is sourced from the `Offer.office_phone` custom field descriptor (existing `TextField` on the Offer model).
- **AC-5.4**: Offers with `office_phone == None` are included in results with `office_phone: null`.

#### FR-6: HTTP Endpoint

Expose timeline data via a new API route.

- **AC-6.1**: Route: `GET /api/v1/offers/section-timelines`.
- **AC-6.2**: Required query parameters: `period_start` (YYYY-MM-DD), `period_end` (YYYY-MM-DD).
- **AC-6.3**: Response uses `SuccessResponse[list[OfferTimelineEntry]]` envelope per existing API patterns (`api/models.py`).
- **AC-6.4**: Invalid date format returns 422 with error code `VALIDATION_ERROR`.
- **AC-6.5**: `period_start > period_end` returns 422 with error code `VALIDATION_ERROR` and message indicating the constraint.
- **AC-6.6**: Asana API failure (upstream error) returns 502 with error code `UPSTREAM_ERROR`.
- **AC-6.7**: Timeline not ready (pre-warm incomplete) returns 503 with error code `TIMELINE_NOT_READY`, includes `Retry-After` header (value: 30 seconds), and `retry_after_seconds: 30` in error details. Uses `raise_api_error()` with `headers={"Retry-After": "30"}` per existing pattern.
- **AC-6.8**: Authentication follows the existing dual-mode pattern (`require_service_claims` for S2S JWT authentication).
- **AC-6.9**: Route uses `RequestId` dependency (`Annotated[str, Depends(get_request_id)]`) for error correlation.

#### FR-7: Pre-Warm / Readiness Gate

Background story cache warming at startup with readiness gating.

- **AC-7.1**: A background `asyncio.Task` is launched during application lifespan (after entity discovery, following the existing `cache_warming` pattern in `lifespan.py`).
- **AC-7.2**: The pre-warm task iterates over all offers in project `1143843662099250` and calls `StoriesClient.list_for_task_cached()` for each, populating the incremental story cache.
- **AC-7.3**: Progress is tracked as a ratio: `offers_with_cached_stories / total_offers`.
- **AC-7.4**: If the endpoint is called when fewer than 50% of offers have cached stories, it returns 503 `TIMELINE_NOT_READY` per AC-6.7.
- **AC-7.5**: The pre-warm task is stored on `app.state` and cancelled on shutdown, following the existing `cache_warming_task` pattern.
- **AC-7.6**: Pre-warm failures for individual offers are logged at WARNING level and do not abort the overall pre-warm. The offer is counted as not-warmed.

---

## 5. Non-Functional Requirements

- **NFR-1: Latency** -- Endpoint response time under 5 seconds for a 30-day period with pre-warmed caches, measured at p95.
- **NFR-2: Observability** -- Structured logging for: pre-warm progress (INFO), individual offer processing errors (WARNING), unknown section encounters (WARNING), endpoint request completion (INFO with timing).
- **NFR-3: Cache Efficiency** -- Story fetches use the existing incremental cache; full re-fetch from Asana API should only occur on first warm or cache eviction, not on every request.

---

## 6. Domain Model Summary

| Model | Type | Fields |
|-------|------|--------|
| `SectionInterval` | `dataclass(frozen=True)` | `started_at: datetime`, `ended_at: datetime | None`, `section_name: str`, `classification: AccountActivity | None` |
| `SectionTimeline` | `dataclass` | `offer_gid: str`, `intervals: list[SectionInterval]` |
| `OfferTimelineEntry` | `pydantic.BaseModel` | `offer_gid: str`, `office_phone: str | None`, `active_section_days: int`, `billable_section_days: int` |

---

## 7. Edge Case Matrix

| EC ID | Condition | Expected Behavior | Test Type |
|-------|-----------|-------------------|-----------|
| EC-1 | Never-moved offer, currently ACTIVE | `active_section_days == period length`, `billable_section_days == period length` | Unit |
| EC-2 | Never-moved offer, currently INACTIVE | `active_section_days == 0`, `billable_section_days == 0` | Unit |
| EC-3 | Cross-project story (both old/new section classify as None) | Story filtered out, not counted in any interval | Unit |
| EC-4 | One-sided None (e.g., ACTIVE to unregistered section) | Interval retained with `classification=None`, excluded from counts, WARNING logged | Unit |
| EC-5 | Offer with null `office_phone` | `office_phone: null` in response, offer included in results | Unit |
| EC-6 | Offer goes INACTIVE mid-period | `active_section_days` counts only days before transition | Unit |
| EC-7 | `period_start == period_end` | Valid single-day query; returns 0 or 1 for each count | Unit |
| EC-8 | `period_start > period_end` | 422 `VALIDATION_ERROR` | Unit |
| EC-9 | Future period (both dates in the future) | Valid; open intervals (`ended_at=None`) counted up to `period_end` | Unit |
| EC-10 | Interval boundary exactly on `period_start` or `period_end` | Date is included (boundaries are inclusive) | Unit |

---

## 8. Success Criteria

- **SC-1**: POC offer `1205925604226368` with a 7-day window where the offer is ACTIVE returns `active_section_days=7` and `billable_section_days=7`.
- **SC-2**: All 10 edge cases (EC-1 through EC-10) have passing unit tests.
- **SC-3**: Endpoint returns 503 with `Retry-After: 30` header when fewer than 50% of offers have warmed story caches.
- **SC-4**: Endpoint returns valid `SuccessResponse` with both `active_section_days` and `billable_section_days` for all offers in the Business Offers project.
- **SC-5**: Cross-project noise stories (EC-3) never contribute to day totals.
- **SC-6**: Unknown sections are logged at WARNING level and never counted in either day total.

---

## 9. Out of Scope

- **reconcile-spend integration**: No changes to the reconciliation pipeline or its consumption of timeline data.
- **Rules 6 & 7**: No modifications to reconciliation rules.
- **ThreeWayComparison / report changes**: No changes to comparison logic or reporting outputs.
- **Shadow mode / feature flags**: The endpoint is available immediately once deployed; no gradual rollout.
- **Unit-level timelines**: This PRD covers Offer-level timelines only. Unit (project GID `1201081073731555`) timelines are a separate future effort.
- **HTTP client changes**: No modifications to `AsanaClient`, `StoriesClient`, or transport layer.

---

## 10. Open Questions

None. All requirements are specified with testable acceptance criteria.

---

## 11. Existing Codebase Anchors

These existing components are directly referenced by this PRD:

| Component | Location | Usage |
|-----------|----------|-------|
| `OFFER_CLASSIFIER` | `src/autom8_asana/models/business/activity.py` | Section name to `AccountActivity` classification |
| `AccountActivity` enum | `src/autom8_asana/models/business/activity.py` | ACTIVE, ACTIVATING, INACTIVE, IGNORED values |
| `SectionClassifier.classify()` | `src/autom8_asana/models/business/activity.py` | O(1) section classification |
| `StoriesClient.list_for_task_cached()` | `src/autom8_asana/clients/stories.py` | Incremental story cache with append-only semantics |
| `Story` model | `src/autom8_asana/models/story.py` | `resource_subtype`, `new_section`, `old_section` (both `NameGid | None`) |
| `Offer` model | `src/autom8_asana/models/business/offer.py` | `office_phone` (TextField), `account_activity` property, `PRIMARY_PROJECT_GID = "1143843662099250"` |
| `SuccessResponse[T]` | `src/autom8_asana/api/models.py` | Standard API response envelope |
| `raise_api_error()` | `src/autom8_asana/api/errors.py` | Error response with `headers` kwarg for `Retry-After` |
| `RequestId` | `src/autom8_asana/api/dependencies.py` | `Annotated[str, Depends(get_request_id)]` |
| Lifespan pattern | `src/autom8_asana/api/lifespan.py` | `asyncio.create_task()` + `app.state` storage + shutdown cancellation |
| Error code `CACHE_NOT_WARMED` | `src/autom8_asana/api/routes/query.py:180` | Precedent for 503 + retry_after_seconds pattern |

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD-SECTION-TIMELINE | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-SECTION-TIMELINE.md` | Yes (Read-verified) |
