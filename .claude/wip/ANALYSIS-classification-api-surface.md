# Architectural Analysis: Classification-Linked API Surface Fragmentation

**Status**: ANALYSIS (ready for stakeholder review)
**Date**: 2026-02-20
**Author**: Architect Agent

---

## 1. Current State Assessment

The system has three independent API surfaces that serve related but disconnected purposes. This section documents each with file:line references to ground the analysis.

### 1.1 Query Router (S2S-only, DataFrame cache)

**Endpoint**: `POST /v1/query/{entity_type}/rows`
**File**: `src/autom8_asana/api/routes/query.py:139-201`
**Auth**: S2S JWT via `require_service_claims` (line 144)
**Prefix**: `/v1/query` (no `/api` prefix, line 58)
**Response envelope**: `RowsResponse` -- flat `{data: [...], meta: {...}}` (defined in `src/autom8_asana/query/models.py:241-248`)

The `section` parameter on `RowsRequest` (query/models.py:204) accepts a **single section name** (e.g., `"ACTIVE"`), not a classification group. The `QueryEngine._resolve_section()` (query/engine.py:400-423) resolves this to a `pl.col("section") == section_name_filter` comparison (engine.py:127). This means:

- To query all 23 ACTIVE-classified sections, a consumer must issue 23 separate requests or use a predicate tree with an `{or: []}` group containing 23 `{field: "section", op: "in", value: [...]}` comparisons.
- The `SectionClassifier.sections_for(AccountActivity.ACTIVE)` method exists at `models/business/activity.py:80-90` and returns exactly this set, but the query engine has no integration with it.

### 1.2 Section-Timelines Endpoint (Dual-mode auth)

**Endpoint**: `GET /api/v1/offers/section-timelines`
**File**: `src/autom8_asana/api/routes/section_timelines.py:50-138`
**Auth**: Dual-mode via `AsanaClientDualMode` (line 56) -- accepts both JWT and PAT
**Prefix**: `/api/v1/offers` (line 33)
**Response envelope**: `SuccessResponse[SectionTimelinesResponse]` -- standard `{data: {timelines: [...]}, meta: {request_id, timestamp}}` (line 53, models.py:96-109)

Returns ALL offers (3,774 entries). No filtering by classification, section, or GID set. The service (`services/section_timeline_service.py:335-610`) resolves the classifier internally (`CLASSIFIERS.get(classifier_name)` at line 377) and uses it for interval classification but never for filtering the result set. The derived cache (cache/integration/derived.py) stores ALL timelines as a single cache entry keyed by `timeline:{project_gid}:{classifier_name}`.

### 1.3 DataFrames Endpoint (Dual-mode auth)

**Endpoint**: `GET /api/v1/dataframes/project/{gid}` and `GET /api/v1/dataframes/section/{gid}`
**File**: `src/autom8_asana/api/routes/dataframes.py:137-222` and `255-312`
**Auth**: Dual-mode via `AsanaClientDualMode` (line 169)
**Prefix**: `/api/v1/dataframes` (line 58)
**Response envelope**: `SuccessResponse` or Polars-JSON with `{data: [...], meta: {request_id, timestamp, pagination}}` (line 126-134)

Provides raw DataFrame access by project or section GID. No classification awareness.

### 1.4 Auth Scheme Summary

| Endpoint Group | Auth Dependency | Accepts PAT | Accepts JWT | File:Line |
|---|---|---|---|---|
| Query router | `require_service_claims` | NO | YES | query.py:144 |
| Resolver | `require_service_claims` | NO | YES | resolver.py:156 |
| Entity write | `require_service_claims` | NO | YES | entity_write.py:9 |
| Internal | `require_service_claims` | NO | YES | internal.py:91 |
| Section-timelines | `AsanaClientDualMode` | YES | YES | section_timelines.py:56 |
| DataFrames | `AsanaClientDualMode` | YES | YES | dataframes.py:169 |
| Tasks/Sections/etc. | `AsanaClientDualMode` | YES | YES | tasks.py:34-38 |
| Health | None | N/A | N/A | -- |

### 1.5 URL Pattern Summary

| Surface | Pattern | Method | Prefix |
|---|---|---|---|
| Query rows | `/v1/query/{entity_type}/rows` | POST | No `/api` |
| Query aggregate | `/v1/query/{entity_type}/aggregate` | POST | No `/api` |
| Resolver | `/v1/resolve/{entity_type}` | POST | No `/api` |
| Section-timelines | `/api/v1/offers/section-timelines` | GET | `/api` |
| DataFrames | `/api/v1/dataframes/project/{gid}` | GET | `/api` |
| Tasks CRUD | `/api/v1/tasks/{gid}` | GET/POST/PUT/DELETE | `/api` |
| Entity write | `/api/v1/entity/{type}/{gid}` | PATCH | `/api` |
| Internal | `/api/v1/internal/...` | Various | `/api` |

---

## 2. Auth Unification Analysis

### 2.1 Why the Divergence Exists

The auth divergence is **intentional by design lineage, but accidental in its consumer impact**.

**S2S-only endpoints** (query, resolver, entity write) were built as internal service interfaces. They exist for autom8-data and other internal services to call asana-satellite. The `require_service_claims` dependency (internal.py:91-182) explicitly rejects PAT tokens (line 112-129) because these endpoints:
1. Use the bot PAT for Asana API calls (not the user's token)
2. Serve cached/aggregated data that may cross user permission boundaries
3. Need caller identification for audit logging (`claims.service_name`)

**Dual-mode endpoints** (section-timelines, dataframes, tasks) were built as user-facing or dual-purpose interfaces. The `get_auth_context` dependency (dependencies.py:127-286) detects token type via dot-counting (dual_mode.py:37-56) and routes accordingly:
- PAT mode: uses the user's own token for Asana API calls
- JWT mode: validates JWT, then uses bot PAT for Asana API calls

### 2.2 The Actual Problem

The problem is not that the auth schemes differ -- the problem is that **the data a consumer needs spans both auth boundaries**. The consumer journey documented in the brief:

```
1. Obtain S2S JWT
2. POST /v1/query/offer/rows (section=ACTIVE) -> offer GIDs
3. Obtain PAT
4. GET /api/v1/offers/section-timelines -> ALL 3,774 entries
5. Client-side join by offer_gid
6. Filter to ~83 ACTIVE entries
```

This is a real DX problem, but the fix is **not** auth unification. The fix is data composition.

### 2.3 Should All Endpoints Accept Both Auth Modes?

**No.** Here is the tradeoff analysis:

| Approach | Pros | Cons |
|---|---|---|
| **Unify all to dual-mode** | Single token for all calls | Bot PAT data leaks through PAT-auth calls; audit trail broken for S2S-only paths; query router serves cached data that may exceed individual PAT permissions |
| **Add PAT to query router** | Consumers can use PAT for everything | Query router uses DataFrame cache built from bot PAT; returning bot-PAT-sourced data to PAT-authenticated users is a permission escalation |
| **Add S2S to section-timelines** | Internal services can call timelines | Already works -- `AsanaClientDualMode` accepts JWT via `get_auth_context` |
| **Keep as-is, fix data access** | Preserves security boundaries | DX burden remains if no composable endpoint exists |

The section-timelines endpoint already accepts JWT through the dual-mode auth chain. The real issue is that the query router (S2S-only) and the section-timelines endpoint (dual-mode) return disjoint data sets with no server-side composition path.

**Recommendation: DEFER auth unification.** The section-timelines endpoint already accepts both modes. The query router's S2S restriction is a correct security boundary. The consumer DX problem is solved by adding server-side filtering to section-timelines, not by relaxing auth.

### 2.4 Security Risk of Misguided Unification

If the query router were made dual-mode:
- A PAT-authenticated user would receive data from the bot PAT's DataFrame cache
- That cache contains data from ALL sections, including sections the user's PAT may not have project access to
- This is a **privilege escalation vector**, not just a DX issue

---

## 3. Classification Filter Pattern

### 3.1 Current State: Classification Is Disconnected from Query

The `SectionClassifier` (activity.py:53-130) provides:
- `classify(section_name)` -> `AccountActivity` (line 69-78)
- `sections_for(*categories)` -> `frozenset[str]` (line 80-90)
- `active_sections()` -> frozenset of 23 section names (line 92-94)
- `billable_sections()` -> frozenset of 28 section names (line 96-98)

But no API endpoint exposes classification as a filter parameter. The query engine filters by individual section name (engine.py:127), and the timeline endpoint returns everything.

### 3.2 Design Options

#### Option A: Classification Filter as Query Sugar (Recommended)

Add `classification` as a virtual filter parameter to the query router's `RowsRequest`. The engine would expand it to an IN predicate using `SectionClassifier.sections_for()`.

```
POST /v1/query/offer/rows
{
  "classification": "active",  // NEW: expanded to section IN [23 names]
  "select": ["gid", "name", "section", "office_phone"]
}
```

Implementation:
- Add `classification: str | None = None` to `RowsRequest` (query/models.py:198)
- In `QueryEngine.execute_rows()` (engine.py:61), before section resolution: look up `CLASSIFIERS.get(entity_type)`, call `sections_for(AccountActivity(classification))`, inject an IN predicate
- Mutually exclusive with `section` param (error if both provided)

Effort: ~0.5 day. Fully backward-compatible. No schema changes.

#### Option B: Classification Filter as DI Dependency

Create a `ClassificationFilter` FastAPI dependency that any endpoint can inject:

```python
class ClassificationFilter:
    entity_type: str
    classification: AccountActivity
    section_names: frozenset[str]

async def get_classification_filter(
    classification: str | None = Query(None),
    entity_type: str = Path(...),
) -> ClassificationFilter | None:
    ...
```

This is over-engineered for the current consumer count (query + timelines). It introduces a cross-cutting concern for a problem that currently affects exactly 2 endpoints.

Effort: ~1 day. Adds dependency injection complexity.

#### Option C: Classification-Aware Section-Timelines Only

Add `?classification=ACTIVE` to the section-timelines endpoint only. Post-cache filter: compute all timelines from the derived cache, then filter to entries whose current section classifies as the requested category.

Implementation challenge: The derived cache stores `SectionTimeline` objects with interval history but NOT the task's current section classification. The current section would need to be either:
1. Stored alongside each timeline at computation time (adds to cache schema)
2. Looked up per-entry at response time (O(n) classify against `OfferTimelineEntry`)

Wait -- the `OfferTimelineEntry` response model has `offer_gid`, `office_phone`, `active_section_days`, and `billable_section_days`. It does NOT carry the current section name. The SectionTimeline domain model has intervals, but the last interval's section_name IS the current section. This could be extracted during `_compute_day_counts()`.

Effort: ~0.5 day for post-cache filtering, ~0.25 day to surface current_section in the response.

### 3.3 Recommended Approach: Option A + Option C (Parallel)

Both are small, independent, and together eliminate the 5-step consumer journey:

1. **Option A (query classification sugar)**: Enables `POST /v1/query/offer/rows {classification: "active"}` to get GIDs + metadata in one call, using the existing S2S path.
2. **Option C (timelines classification filter)**: Enables `GET /api/v1/offers/section-timelines?classification=active&period_start=...&period_end=...` to return only ~83 entries instead of 3,774.

After both: A consumer with S2S JWT can get ACTIVE offers with their billing days in a single call to section-timelines (which already accepts JWT). No client-side join needed.

### 3.4 Entity Type Generalization

The `CLASSIFIERS` dict (activity.py:264-267) already maps `"offer"` and `"unit"` to classifiers. The pattern generalizes to any entity type with a registered classifier. However:

- Currently only offers have section-timelines
- Units have a classifier but no timeline endpoint
- Businesses have no classifier (they aggregate from child units)

**Recommendation**: Build the classification filter parameter as entity-type-aware from day one (use `CLASSIFIERS.get(entity_type)` rather than hardcoding `OFFER_CLASSIFIER`), but do NOT build unit timeline or business timeline endpoints until there is demand.

---

## 4. API Surface Harmonization

### 4.1 URL Pattern Divergence

Two URL pattern families coexist:

| Family | Pattern | Auth | Purpose |
|---|---|---|---|
| **Internal** | `/v1/{verb}/{entity_type}` | S2S-only | Machine-to-machine operations |
| **Resource** | `/api/v1/{resource}/...` | Dual-mode | CRUD and read operations |

This split has a logic: internal surfaces omit `/api` because they were designed before the API gateway layer and are accessed directly by internal services. Resource endpoints use `/api` because they sit behind the gateway.

**Assessment**: This is not a defect, it is a naming convention boundary. Renaming would break existing S2S consumers. However, the inconsistency is confusing for new developers.

### 4.2 Response Envelope Divergence

| Endpoint | Envelope | Models File |
|---|---|---|
| Query /rows | `{data: [...], meta: {total_count, returned_count, query_ms, ...}}` | query/models.py:241-248 |
| Query /aggregate | `{data: [...], meta: {group_count, aggregation_count, ...}}` | query/models.py:189-196 |
| Section-timelines | `{data: {timelines: [...]}, meta: {request_id, timestamp}}` | api/models.py:96-109 |
| DataFrames | `{data: [...], meta: {request_id, timestamp, pagination}}` | api/models.py:96-109 |
| Tasks CRUD | `{data: {...}, meta: {request_id, timestamp}}` | api/models.py:96-109 |

The query router uses its own `RowsMeta`/`AggregateMeta` models (query/models.py) with query-specific fields (query_ms, freshness, staleness_ratio). The resource endpoints use the shared `SuccessResponse[T]` envelope (api/models.py:96-109).

**Assessment**: The divergence is defensible. Query responses need query-specific metadata (timing, freshness, pagination counts) that do not apply to CRUD responses. Forcing them into the same envelope would either bloat the shared model or require optional fields everywhere.

### 4.3 HTTP Method Divergence

The query router uses POST for reads because the request body carries a complex predicate tree that does not fit in query parameters. Section-timelines uses GET because its parameters (period_start, period_end) are simple scalars. This is correct REST practice.

If classification filtering or GID-set filtering is added to section-timelines and the filter parameters grow complex (e.g., a list of 83 GIDs), a POST variant would be appropriate:

```
POST /api/v1/offers/section-timelines/query
{
  "classification": "active",
  "period_start": "2026-01-01",
  "period_end": "2026-01-31",
  "offer_gids": ["gid1", "gid2", ...]  // optional
}
```

But this should be deferred until there is a concrete consumer need for GID-set filtering. Classification filtering alone fits cleanly in query parameters.

---

## 5. Server-Side Filtering for Section-Timelines

### 5.1 Current Caching Architecture

The derived cache (cache/integration/derived.py) stores ALL timelines as a single entry keyed by `timeline:{project_gid}:{classifier_name}` with a 5-minute TTL (derived.py:32). The `get_or_compute_timelines()` function (section_timeline_service.py:335-610):

1. Checks derived cache for pre-computed timelines (line 400-404)
2. On miss: acquires computation lock, enumerates ALL tasks, batch-reads stories, builds timelines, stores in cache (line 406-607)
3. Calls `_compute_day_counts()` (line 613-643) to project the requested period

Day counts are period-dependent (they depend on period_start/period_end), so the cache stores raw SectionTimeline objects and day-count projection happens on every request. This is the correct architecture -- it separates the expensive computation (timeline building) from the cheap projection (day counting).

### 5.2 Adding Classification Filtering

Filtering by classification should happen AFTER cache read, DURING the `_compute_day_counts()` projection step. This preserves the single cache entry and avoids cache key explosion.

```python
def _compute_day_counts(
    timelines: list[SectionTimeline],
    period_start: date,
    period_end: date,
    classification: AccountActivity | None = None,  # NEW
    classifier: SectionClassifier | None = None,      # NEW
) -> list[OfferTimelineEntry]:
    entries: list[OfferTimelineEntry] = []
    for timeline in timelines:
        # NEW: If classification filter specified, check last interval
        if classification is not None and classifier is not None:
            if not timeline.intervals:
                continue
            last_section = timeline.intervals[-1].section_name
            current_cls = classifier.classify(last_section)
            if current_cls != classification:
                continue
        # ... existing day count logic ...
```

**Cache impact**: None. The derived cache stores all timelines unchanged. Filtering is post-cache, O(n) where n = ~3,774. This is negligible CPU.

**Response size impact**: 414KB -> ~9KB for ACTIVE (83/3,774 entries, ~97.8% reduction).

### 5.3 Adding GID-Set Filtering

For targeted queries where a consumer already has a GID list:

```
GET /api/v1/offers/section-timelines?period_start=...&period_end=...&offer_gids=gid1,gid2,gid3
```

This is a comma-separated query parameter. FastAPI handles this natively. Post-cache filter: `if offer_gids and timeline.offer_gid not in offer_gid_set: continue`.

For large GID sets (>50), a POST variant would be needed. This should be deferred.

---

## 6. Recommendations

### SHOULD (High Impact, Low Effort)

**S-1: Add `?classification=` filter to section-timelines endpoint** (~0.5 day)
- Add optional `classification` query parameter to `get_offer_section_timelines()`
- Post-cache filter in `_compute_day_counts()` using the last interval's section classification
- Eliminates 97.8% of response payload for the primary consumer use case
- No cache key changes, no schema changes, fully backward-compatible
- Files: `section_timelines.py`, `section_timeline_service.py`

**S-2: Add `classification` virtual filter to query router's RowsRequest** (~0.5 day)
- Add `classification: str | None = None` to `RowsRequest`
- Expand to IN predicate via `CLASSIFIERS.get(entity_type).sections_for()`
- Makes "give me all ACTIVE offers" a single field instead of 23-section OR predicate
- Mutually exclusive with `section` param
- Files: `query/models.py`, `query/engine.py`

**S-3: Surface `current_section` and `current_classification` in OfferTimelineEntry** (~0.25 day)
- Add two optional fields to the response model
- Derived from last interval's `section_name` and its classification
- Enables consumers to group/filter client-side without needing the classifier's mapping
- Files: `models/business/section_timeline.py`, `services/section_timeline_service.py`

### COULD (Medium Impact, Low Effort)

**C-1: Add `?offer_gids=` filter to section-timelines endpoint** (~0.25 day)
- Comma-separated query parameter, post-cache set-membership filter
- For targeted queries when consumer already has GIDs from another source
- Files: `section_timelines.py`, `section_timeline_service.py`

**C-2: Document the auth boundary rationale in an ADR** (~0.25 day)
- Captures why S2S-only and dual-mode coexist
- Prevents future developers from "fixing" this by making everything dual-mode
- Files: `docs/decisions/ADR-0068-auth-boundary-query-vs-resource.md`

**C-3: Add `include_in_schema=True` to section-timelines and query routers** (~0.1 day)
- Both currently have `include_in_schema=False` (query.py:58) or default True
- Generating OpenAPI docs would make the API surface self-documenting
- Low effort but depends on whether these are meant to be internal-only

### DEFER (Low Urgency or High Effort)

**D-1: URL pattern unification** -- DEFER indefinitely
- Renaming `/v1/query/...` to `/api/v1/query/...` would break existing S2S consumers
- The split has a logic (internal vs. resource-facing)
- Cost: migration effort + consumer coordination
- Trigger: major version bump or API gateway consolidation

**D-2: Response envelope unification** -- DEFER indefinitely
- Query-specific metadata (query_ms, freshness) does not belong in generic SuccessResponse
- Forcing unification would either bloat the shared model or lose query observability
- The two envelope families serve different purposes

**D-3: POST variant for section-timelines** -- DEFER until concrete need
- Only needed if GID-set filtering exceeds URL length limits
- Classification filtering fits in query parameters
- Trigger: consumer with >50 GID filter requirement

**D-4: ClassificationFilter as reusable DI dependency** -- DEFER
- Over-engineered for 2 endpoints
- Build if/when 3+ endpoints need classification filtering
- The `CLASSIFIERS` dict already provides the shared lookup

---

## 7. Anti-Patterns to Avoid

### DO NOT unify auth schemes across all endpoints
The S2S-only restriction on the query router is a correct security boundary. The DataFrame cache contains data from the bot PAT, which may include entities the requesting PAT user cannot access. Relaxing this creates a privilege escalation vector.

### DO NOT create per-classification cache keys
Storing `timeline:1143843662099250:offer:active` as a separate cache entry from `timeline:1143843662099250:offer` would:
- Multiply cache storage by 4x (one per classification)
- Require cache invalidation logic per classification
- Solve a problem that post-cache filtering handles in O(n) with n=3,774

### DO NOT add a "combined query + timelines" composite endpoint
Creating a single endpoint that returns both DataFrame query results AND timeline data couples two independent subsystems (Polars DataFrames + Story-based timelines). If consumers need both, they should call both endpoints -- the auth is already compatible (both accept JWT via dual-mode).

### DO NOT rename URL prefixes for consistency
The `/v1/query/` vs. `/api/v1/` split reflects a real architectural boundary (internal S2S vs. gateway-fronted). Unifying would break consumers for cosmetic benefit.

### DO NOT add classification as a WHERE predicate column
Adding "classification" as a virtual column in the DataFrame schema would require either:
- Materializing it at cache build time (coupling cache to classifier, which changes independently)
- Computing it at query time for every row (O(n) classify for each query)

The `classification` parameter on RowsRequest is the correct approach: it expands to a concrete IN predicate at query planning time.

---

## 8. Summary: Consumer Journey After Recommendations

### Before (5 steps, 2 auth schemes, client-side join)
```
1. Obtain S2S JWT
2. POST /v1/query/offer/rows {section: "ACTIVE"} -> only 1 of 23 active sections
3. Obtain PAT
4. GET /api/v1/offers/section-timelines -> ALL 3,774 entries
5. Client-side join + filter to ~83 ACTIVE offers
```

### After S-1 + S-2 (1 step, 1 auth scheme, server-side filter)
```
1. Obtain S2S JWT (or PAT -- section-timelines accepts both)
2. GET /api/v1/offers/section-timelines?classification=active&period_start=...&period_end=...
   -> 83 ACTIVE entries with billing days, ~9KB response
```

Or if the consumer needs DataFrame-style fields:
```
1. Obtain S2S JWT
2. POST /v1/query/offer/rows {classification: "active", select: ["gid", "name", "section", "office_phone"]}
   -> all offers in the 23 ACTIVE sections
```

Total estimated effort for S-1 + S-2 + S-3: **~1.25 days**.

---

## Appendix: File Reference

| File | Purpose |
|---|---|
| `src/autom8_asana/api/routes/query.py` | Query router (S2S-only) |
| `src/autom8_asana/api/routes/section_timelines.py` | Section-timelines endpoint (dual-mode) |
| `src/autom8_asana/api/routes/dataframes.py` | DataFrames endpoint (dual-mode) |
| `src/autom8_asana/api/routes/internal.py` | S2S auth dependency (`require_service_claims`) |
| `src/autom8_asana/api/routes/resolver.py` | Entity resolver (S2S-only) |
| `src/autom8_asana/api/routes/entity_write.py` | Entity write (S2S-only) |
| `src/autom8_asana/api/routes/__init__.py` | Route registration |
| `src/autom8_asana/api/dependencies.py` | Dual-mode auth dependency chain |
| `src/autom8_asana/api/models.py` | Shared response envelope (SuccessResponse) |
| `src/autom8_asana/api/main.py` | App factory, router mounting |
| `src/autom8_asana/auth/dual_mode.py` | Token type detection (dot-counting) |
| `src/autom8_asana/models/business/activity.py` | SectionClassifier, OFFER_CLASSIFIER, CLASSIFIERS |
| `src/autom8_asana/models/business/section_timeline.py` | SectionTimeline, OfferTimelineEntry domain models |
| `src/autom8_asana/services/section_timeline_service.py` | Timeline computation + caching |
| `src/autom8_asana/services/query_service.py` | EntityQueryService, section resolution |
| `src/autom8_asana/query/models.py` | RowsRequest, RowsResponse, predicate models |
| `src/autom8_asana/query/engine.py` | QueryEngine, section filtering |
| `src/autom8_asana/metrics/resolve.py` | SectionIndex (name -> GID resolution) |
| `src/autom8_asana/cache/integration/derived.py` | Derived timeline cache operations |
