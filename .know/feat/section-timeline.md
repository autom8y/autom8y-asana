---
domain: feat/section-timeline
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/api/routes/section_timelines.py"
  - "./src/autom8_asana/services/section_timeline_service.py"
  - "./src/autom8_asana/models/business/section_timeline.py"
  - "./tests/unit/api/test_section_timelines.py"
  - "./tests/unit/services/test_section_timeline_service.py"
  - "./tests/unit/models/test_section_timeline.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# Feature: Section Timeline Service (Offer Lifecycle History)

## 1. Purpose and Design Rationale

### Why This Feature Exists

The Section Timeline Service answers the question: **how long has each offer been in each stage of its sales lifecycle?** Stakeholders need period-scoped counts of calendar days that each offer spent in ACTIVE and ACTIVATING sections — the raw inputs for billing and operational reporting. Without this feature, reconstructing that history requires replaying every Asana task's section-changed story stream on every request, which cannot complete within HTTP timeout constraints at production scale.

The feature is specified by **TDD-SECTION-TIMELINE-001 / FR-6**: expose timeline data for all offers in the Business Offers project under `GET /api/v1/offers/section-timelines`.

### Design Decision: Compute-on-Read-Then-Cache Architecture

**The original design** computed timelines per-request by fetching stories from the Asana API in real time. This caused **SCAR-015**: the endpoint returned HTTP 504 at approximately 3,800 offers because per-request I/O (fetching stories for every offer) exceeded the 60-second ALB timeout.

**The remediation (TDD-SECTION-TIMELINE-REMEDIATION)** adopted a compute-on-read-then-cache architecture:
1. On cold cache: enumerate tasks from Asana API once, batch-read pre-cached stories (already warmed by the story warmer Lambda), compute timelines, store derived entry in cache.
2. On warm cache: deserialize pre-computed timelines, compute day counts (pure CPU, no I/O).
3. No warm-up pipeline or readiness gates required — the endpoint is self-healing.

The architecture explicitly separates I/O (task enumeration + story batch read, performed once at cold-miss time) from CPU (day counting, performed on every request). The scar-tissue rationale is preserved in `.know/scar-tissue.md` entry SCAR-015 and the agent-relevance tag for architect: "I/O-heavy data must be pre-computed at warm-up; request path pure-CPU."

**Fix commit**: `b85a604a`. Fix location: `src/autom8_asana/services/section_timeline_service.py` (full service rewrite).

### Stakeholder Decision: Transition Day Ownership (2026-02-19)

The transition day (the calendar date when an offer moves from one section to another) belongs exclusively to the **new** section being entered, not the section being exited. This is implemented in `SectionTimeline._count_days_for_classifications`: `interval_end = interval.exited_at.date() - timedelta(days=1)`. This decision is documented inline at `models/business/section_timeline.py:140`.

### Design Decision: Classification Filter Post-Cache

The `classification` query parameter (e.g., `?classification=active`) filters which entries are returned. By design, the derived cache **always stores all timelines** regardless of any filter. Filtering is applied as an O(n) pass in `_compute_day_counts` after cache retrieval. This keeps the cache universal and avoids per-filter cache keys.

---

## 2. Conceptual Model

### Key Terminology

| Term | Definition |
|------|------------|
| **SectionInterval** | A time span during which an offer occupied a specific Asana section. Has a start time (`entered_at`) and optional end time (`exited_at=None` for the current section). |
| **SectionTimeline** | The complete ordered history of `SectionInterval` values for one offer. Carries `offer_gid`, `office_phone`, `offer_id`, `task_created_at`, and `story_count`. |
| **OfferTimelineEntry** | The API response model for one offer. Contains `offer_gid`, `office_phone`, `offer_id`, `active_section_days`, `billable_section_days`, `current_section`, `current_classification`. |
| **AccountActivity** | StrEnum: `ACTIVE`, `ACTIVATING`, `INACTIVE`, `IGNORED`. Maps section names to business classifications. |
| **SectionClassifier** | Frozen dataclass. O(1) dict-based mapping of lowercase section name → `AccountActivity`. Parameterizable — the service accepts `classifier_name="offer"` or `"unit"`. |
| **OFFER_CLASSIFIER** | The `SectionClassifier` instance for the Business Offers project. Singleton imported from `models.business.activity`. |
| **active_section_days** | Count of unique calendar dates in the query period where the offer was in an `ACTIVE` section. |
| **billable_section_days** | Count of unique calendar dates in the query period where the offer was in `ACTIVE` or `ACTIVATING`. |
| **cross-project noise** | Section-changed stories from non-Business-Offers projects. Filtered when both `new_section` and `old_section` classify as `None` (AC-1.3). |
| **imputation** | When an offer has no section-changed stories (never moved), a single interval is synthesized from `task.created_at` using the current section classification (AC-3.1/AC-3.2). |
| **derived cache** | A cache layer (`cache.integration.derived`) that stores pre-computed serialized timelines keyed by `(project_gid, classifier_name)`. TTL not agent-visible; managed by the cache integration layer. |
| **thundering herd prevention (AMB-3)** | An `asyncio.Lock` per `(project_gid, classifier_name)` pair prevents multiple concurrent requests from each triggering a full cold-miss computation. Uses an `OrderedDict` with LRU eviction (max 256 entries). |

### State / Lifecycle

A `SectionInterval` sequence represents the offer's lifecycle in one project:

```
task.created_at
    │
    ▼
[first section_changed story] → open interval
    │
    ▼
[each subsequent story] → closes previous interval, opens new one
    │
    ▼
[last story] → open interval (exited_at=None, extends to period_end)
```

If no section-changed stories exist → single imputed interval from `task.created_at`.

### Classification Values

`AccountActivity` values and their billing semantics:
- `ACTIVE` → counts for both `active_section_days` AND `billable_section_days`
- `ACTIVATING` → counts for `billable_section_days` only
- `INACTIVE` → counts for neither
- `IGNORED` → counts for neither
- `None` (unregistered section) → excluded from all counts (AC-2.4)

### Inter-Feature Relationships

**Consumes**:
- `cache.integration.stories.read_stories_batch` — reads pre-cached task stories in bulk
- `cache.integration.derived` — `get_cached_timelines`, `store_derived_timelines`, `serialize_timeline`, `deserialize_timeline`
- `models.business.activity.OFFER_CLASSIFIER` / `CLASSIFIERS` registry
- `models.story.Story` — domain model for Asana stories
- `clients` — `client.stories.list_for_task_cached_async`, `client.tasks.list_async`

**Provides**:
- `GET /api/v1/offers/section-timelines` — consumed by BI/reporting tools and stakeholder dashboards

**Does NOT interact with**:
- Entity resolution pipeline
- DataFrame build pipeline
- Persistence/save pipeline
- Export pipeline

---

## 3. Implementation Map

### File Inventory

| File | Size | Responsibility |
|------|------|----------------|
| `src/autom8_asana/api/routes/section_timelines.py` | 200 LOC | Route handler, request validation, response shaping |
| `src/autom8_asana/services/section_timeline_service.py` | 738 LOC | Orchestration, caching, interval building, day-count computation |
| `src/autom8_asana/models/business/section_timeline.py` | 226 LOC | Domain types: `SectionInterval`, `SectionTimeline`, `OfferTimelineEntry` |
| **Total** | **1,164 LOC** | |
| `tests/unit/api/test_section_timelines.py` | 256 LOC | Route-level: classification param validation (S-1), response fields (S-3), offer_id (SC-6) |
| `tests/unit/services/test_section_timeline_service.py` | 821 LOC | Service functions + `_compute_day_counts` + SCAR-015 regression |
| `tests/unit/models/test_section_timeline.py` | 488 LOC | Domain model immutability, day counting, edge cases |

### Route Layer (`api/routes/section_timelines.py`)

- **Router**: `pat_router(prefix="/api/v1/offers", tags=["offers"])` — PAT auth, no JWT
- **Endpoint**: `GET /api/v1/offers/section-timelines`
- **Query parameters**: `period_start: date`, `period_end: date` (required); `classification: str | None` (optional, case-insensitive)
- **Validation (inline)**:
  - `period_start > period_end` → 422 `VALIDATION_ERROR`
  - `classification` not in `AccountActivity` values → 422 `VALIDATION_ERROR`
- **Delegates to**: `get_or_compute_timelines()` from service
- **Error path**: Any exception from service → 502 `UPSTREAM_ERROR` (broad catch, all exceptions)
- **Structured log event**: `section_timelines_served` with `offer_count`, period, classification, `duration_ms`
- **Response**: `SuccessResponse[SectionTimelinesResponse]` where `SectionTimelinesResponse.timelines: list[OfferTimelineEntry]`
- **OpenAPI extra**: `x-fleet-envelope-exempt: True`

### Service Layer (`services/section_timeline_service.py`)

**Module-level constants**:
- `BUSINESS_OFFERS_PROJECT_GID = "1143843662099250"` — exported, imported by route
- `_STORY_OPT_FIELDS` — 5 story fields fetched from Asana API
- `_TASK_OPT_FIELDS` — 6 task fields fetched from Asana API
- `_computation_locks: OrderedDict[str, asyncio.Lock]` — max 256 entries, LRU eviction

**Key functions**:

| Function | Signature | Role |
|----------|-----------|------|
| `get_or_compute_timelines` | `async (client, project_gid, classifier_name, period_start, period_end, classification_filter) → list[OfferTimelineEntry]` | Main entry point; implements 7-step compute-on-read-then-cache flow |
| `_compute_day_counts` | `(timelines, period_start, period_end, classifier, classification_filter) → list[OfferTimelineEntry]` | Pure-CPU; derives `current_section`/`current_classification`; applies filter |
| `build_timeline_for_offer` | `async (client, offer_gid, ...) → SectionTimeline` | Per-offer timeline builder; used in single-offer path |
| `_build_intervals_from_stories` | `(stories, classifier, entity_gid) → (list[SectionInterval], int)` | Walks sorted stories, opens/closes intervals |
| `_build_imputed_interval` | `(task_created_at, account_activity, section_name) → list[SectionInterval]` | Single-interval synthesis for never-moved offers |
| `_is_cross_project_noise` | `(story, classifier) → bool` | True when both sides classify as None (AC-1.3) |
| `_extract_office_phone` / `_extract_offer_id` | `(task_data: dict) → str \| None` | Custom field extraction from raw task dicts |
| `_parse_datetime` | `(value: str \| None) → datetime \| None` | Asana ISO 8601 → Python datetime (strips `Z`) |
| `_get_computation_lock` | `(project_gid, classifier_name) → asyncio.Lock` | LRU lock registry |

**7-step `get_or_compute_timelines` data flow**:
```
1. get_cached_timelines(project_gid, classifier_name, cache)
   → cache hit: deserialize_timeline + _compute_day_counts → return

2. _get_computation_lock(project_gid, classifier_name) → acquire lock
   → re-check cache after lock (second-chance hit)

3. client.tasks.list_async(project=project_gid).collect()
   → raw task list (Asana API call)

4. read_stories_batch(task_gids, cache)
   → dict[task_gid, list[raw_story_dict]] (pure cache read, no API)

4a. Bounded self-healing: if misses ≤ 50, fetch inline via
    client.stories.list_for_task_cached_async (semaphore=5)
    If misses > 50: log warning, proceed with partial data

5. For each task: validate stories → filter section_changed → filter
   cross-project noise → sort → _build_intervals_from_stories
   → impute if no intervals → build SectionTimeline

6. serialize_timeline + store_derived_timelines → derived cache
   (failure is non-fatal: log warning, return computed results uncached)

7. _compute_day_counts → list[OfferTimelineEntry] → return
```

### Domain Model Layer (`models/business/section_timeline.py`)

**`SectionInterval`** — `frozen=True` dataclass:
- `section_name: str`, `classification: AccountActivity | None`, `entered_at: datetime`, `exited_at: datetime | None`

**`SectionTimeline`** — `frozen=True` dataclass:
- Fields: `offer_gid`, `office_phone`, `offer_id`, `intervals: tuple[SectionInterval, ...]`, `task_created_at`, `story_count`
- Methods: `active_days_in_period(start, end) → int` — ACTIVE only; `billable_days_in_period(start, end) → int` — ACTIVE+ACTIVATING
- Shared private implementation: `_count_days_for_classifications(start, end, frozenset[AccountActivity]) → int` using `set[date]` for dedup

**`OfferTimelineEntry`** — Pydantic `BaseModel` (API response):
- Fields: `offer_gid`, `office_phone: OfficePhoneField | None`, `offer_id: str | None`, `active_section_days: int (ge=0)`, `billable_section_days: int (ge=0)`, `current_section: str | None`, `current_classification: str | None`
- Config: `extra="forbid"`

### Test Coverage

| File | Coverage Focus |
|------|---------------|
| `tests/unit/models/test_section_timeline.py` | Frozen immutability, `active_days_in_period`, `billable_days_in_period`, all edge cases (AC-4.4 dedup, AC-4.5 open interval, EC-6 transition day, EC-7 single day, EC-10 inclusive bounds, imputation scenarios), `OfferTimelineEntry` serialization |
| `tests/unit/services/test_section_timeline_service.py` | `_parse_datetime`, `_is_cross_project_noise` (AC-1.3/1.4), `_build_intervals_from_stories` (AC-2.3/2.5/2.6), `_build_imputed_interval` (AC-3.1-3.4), `_extract_office_phone`/`_extract_offer_id` (DD-1, EC-3/8), `build_timeline_for_offer` (FR-1/2/3), `_compute_day_counts` (S-1/S-3), **SCAR-015 regression** (4,000 offers < 5s) |
| `tests/unit/api/test_section_timelines.py` | Classification param validation (S-1), response field presence (S-3), `offer_id` in response (SC-6), null fields |

**SCAR-015 regression test** is `@pytest.mark.scar` at `tests/unit/services/test_section_timeline_service.py:TestScaleBoundary::test_timeline_computation_under_threshold_at_production_scale`. It exercises the Step 5 hot loop with 4,000 tasks and asserts completion under 5 seconds.

---

## 4. Boundaries and Failure Modes

### What This Feature Does NOT Do

- Does NOT fetch stories from the Asana API on the request path (all story I/O happens either at story-warmer Lambda warm-up time or at bounded cold-miss self-healing time)
- Does NOT compute timelines for non-Business-Offers projects (hardcoded `BUSINESS_OFFERS_PROJECT_GID = "1143843662099250"`)
- Does NOT support entity types other than offers via the HTTP endpoint (classifier_name is hardcoded to `"offer"` in the route handler)
- Does NOT persist computed day counts; they are always re-derived from cached timelines per request
- Does NOT paginate; returns all timelines for the project matching the filter
- Does NOT support date-range filtering of which timelines to include, only day-count computation within the period

### Known Failure Modes

**SCAR-015 (resolved): Timeline 504 at ~3,800 offers**

The original per-request I/O pattern exceeded ALB 60-second timeout at approximately 3,800 offers. Fix: compute-on-read-then-cache architecture (TDD-SECTION-TIMELINE-REMEDIATION, commit `b85a604a`). The SCAR-015 regression test guards this at 4,000 offers / 5s threshold.

**Cold-cache miss path: Asana API task enumeration can fail**

Step 3 (`client.tasks.list_async`) is the only Asana API call on the cold path. If it fails, the exception propagates to `get_or_compute_timelines` and is re-raised, surfacing as a 502 `UPSTREAM_ERROR` at the route layer.

**Story cache gap above 50 offers**

If more than 50 tasks have no cached stories (step 4a threshold), the service logs `story_cache_gap_above_threshold` as a warning and proceeds with partial data. Offers without cached stories and without sufficient imputation data (`task_created_at` or `section_name` absent) are **silently excluded** from the result — they produce no timeline entry. The caller receives fewer entries than tasks exist without explicit error.

**Derived cache store failure (non-fatal)**

If `store_derived_timelines` raises an exception, the service logs `timeline_derived_cache_store_failed` as a warning and returns the computed results uncached. Subsequent requests will re-trigger full computation until the store succeeds.

**Missing or expired cache provider**

`get_or_compute_timelines` resolves the cache provider via `getattr(client, "_cache_provider", None)`. If `None`, the function logs `timeline_no_cache_provider` and returns an empty list without raising — callers receive a silent empty response.

**Unknown classifier name**

`CLASSIFIERS.get(classifier_name)` returns `None` for unregistered names. The service logs `unknown_classifier_name` (error level) and returns an empty list.

**Unknown section names**

`SectionClassifier.classify()` returns `None` for sections not in its mapping. Intervals with `classification=None` are excluded from all day counts (AC-2.4). The service logs `unknown_section_in_timeline` (warning level) with `section_name`, `story_gid`, and `offer_gid` for correlation (AC-2.3).

### Configuration Boundaries

- `BUSINESS_OFFERS_PROJECT_GID` — hardcoded string constant; changing it requires a code deployment
- `_computation_locks` LRU cap — `_COMPUTATION_LOCK_MAX_SIZE = 256`; benign if exceeded (oldest lock evicted, new one created)
- Inline story fetch semaphore — `asyncio.Semaphore(5)` for bounded self-healing
- Inline story fetch threshold — `MAX_INLINE_STORY_FETCHES = 50`
- Story cache age — `max_cache_age_seconds=7200` in `build_timeline_for_offer`; stories cached within 2 hours are used without refresh
- Classification filter values — must be a valid `AccountActivity.value` string; validated at route layer with 422 on violation

### Interaction Points and Boundary Clarity

| External Boundary | Nature | Clarity |
|-------------------|--------|---------|
| `cache.integration.derived` | `get_cached_timelines`, `store_derived_timelines`, `serialize_timeline`, `deserialize_timeline` — lazy import inside `get_or_compute_timelines` | Clear; cache integration owns serialization contract |
| `cache.integration.stories.read_stories_batch` | Bulk story retrieval from cache; returns `dict[gid, list[dict]]` | Clear; returns raw dicts, service model-validates |
| `client._cache_provider` | Private attribute access via `getattr`; `_PooledClientWrapper` proxies via `__getattr__` | Fragile — private attribute name; if `AsanaClient` renames `_cache_provider`, this silently returns `None` |
| `models.business.activity.CLASSIFIERS` | Module-level registry dict; `CLASSIFIERS["offer"]` = `OFFER_CLASSIFIER` | Clear; registry is frozen at import time |
| `models.business.activity.extract_section_name` | Extracts current section name from task memberships | Clear; utility function, no state |

### Security Notes

The route is authenticated via PAT (`pat_router`). The `classification` filter value is user-supplied and sanitized via `classification.lower()` + explicit allowlist check before use. No user-supplied values pass into SQL, cache keys, or regex patterns — no injection surface.

---

```metadata
domain: feat/section-timeline
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.93
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 92
    weight: 0.30
  conceptual_model:
    grade: A
    pct: 91
    weight: 0.25
  implementation_map:
    grade: A
    pct: 95
    weight: 0.25
  boundaries_and_failure_modes:
    grade: A
    pct: 91
    weight: 0.20
overall_grade: A
overall_pct: 93
notes: >
  1,164 LOC across 3 source files; 3 test files with comprehensive coverage.
  SCAR-015 (504 timeout at 3,800 offers) fully documented with fix history
  and regression test. Compute-on-read-then-cache architecture clearly
  mapped. One fragile boundary noted: _cache_provider private attribute
  access. Story cache gap > 50 silent-exclusion behavior documented.
  Transition day stakeholder decision (2026-02-19) captured inline.
```
