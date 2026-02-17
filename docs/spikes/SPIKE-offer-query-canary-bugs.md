# SPIKE: Offer Query Canary Bugs

**Date:** 2026-02-17
**Status:** Complete
**Timebox:** 1 session
**Decision Informs:** OfferExtractor implementation, MRR aggregation correctness, query API completeness

## Question

What bugs and architectural gaps exist in the offer DataFrame extraction and query pipeline, as exposed by a simple one-off script attempting to "sum MRR across active offer section tasks"?

## Context

A one-off shell script attempted to:
1. Use `OFFER_CLASSIFIER.active_sections()` to find active offer sections
2. Fetch tasks from those sections via the Asana API
3. Build an offer DataFrame using `SectionDataFrameBuilder(task_type="Offer")`
4. Sum the `mrr` column with Polars

The script crashed at step 3 and required bypassing the entire DataFrame/extractor layer to get a result. This spike documents every bug, gap, and misalignment uncovered.

## Findings

### B1: No OfferExtractor — schema exists, extractor doesn't

**Severity:** Bug (crash)
**Root Cause:** Wiring gap between schema registration and extractor factory

The `OFFER_SCHEMA` is registered in `SchemaRegistry._ensure_initialized()` (registry.py:129):
```python
self._schemas["Offer"] = OFFER_SCHEMA
```

But the extractor factory in `DataFrameBuilder._create_extractor()` (base.py:526-542) has no `case "Offer":` branch:
```python
match task_type:
    case "Unit":     return UnitExtractor(...)
    case "Contact":  return ContactExtractor(...)
    case "*":        return DefaultExtractor(...)
    case _:          return DefaultExtractor(...)  # <-- Offer falls here
```

`DefaultExtractor._create_row()` calls `TaskRow.model_validate(data)`, but `TaskRow` has `extra="forbid"` and rejects the 12 offer-specific columns (office, office_phone, vertical, specialty, offer_id, platforms, language, cost, mrr, weekly_ad_spend, vertical_id, name-override).

**Impact:** `section.to_dataframe(task_type="Offer")` crashes with `ValidationError: 11 validation errors for TaskRow`.

**Fix Required:**
1. Create `OfferRow(TaskRow)` in `task_row.py` with 12 offer-specific fields
2. Create `OfferExtractor(BaseExtractor)` in `extractors/offer.py` with `_create_row() -> OfferRow`
3. Add `case "Offer":` to `_create_extractor()` match statement
4. Wire derived field methods: `_extract_office`, `_extract_name`, `_extract_vertical_id`, `_extract_office_async`

**Pattern to follow:** `UnitExtractor` + `UnitRow` — 1:1 mapping with 11 Unit-specific fields plus derived methods for office, vertical_id, max_pipeline_stage.

---

### B2: `cascade:MRR` source annotation is semantically misleading

**Severity:** Documentation/accuracy issue
**Root Cause:** Schema says `cascade:MRR` but MRR is present directly on offer tasks

In `OFFER_SCHEMA` (offer.py:80-85):
```python
ColumnDef(
    name="mrr",
    dtype="Utf8",
    source="cascade:MRR",  # Cascades from Offer's ancestor Unit
    description="Monthly Recurring Revenue (cascades from Unit)",
)
```

**Actual behavior observed:** When fetching offer tasks from the Business Offers project (GID `1143843662099250`), the MRR custom field **is present directly** on the task's `custom_fields` list with a `number_value`. The script successfully read MRR from 80/81 active offer tasks without any parent chain traversal.

**Two possible explanations:**
1. MRR is a project-level custom field attached to the Business Offers project, so Asana includes it on every task in that project — it's not actually "cascaded" via the parent chain at extraction time
2. The cascade annotation was added for logical documentation purposes (MRR "belongs" to the Unit conceptually) but doesn't reflect the API data source

**Questions to resolve:**
- Is `cascade:MRR` triggering unnecessary parent chain API calls via `CascadingFieldResolver` when the data is already local?
- Should the source be `cf:MRR` (direct) with a comment noting it logically cascades?
- Does the `cascade:` prefix impose async-only extraction (`extract_async`) when sync would suffice?

**MRR dtype mismatch:** OFFER_SCHEMA declares `mrr` as `dtype="Utf8"`, while UNIT_SCHEMA declares it as `dtype="Decimal"`. If MRR is the same custom field in both projects, the dtype should be consistent. The Utf8 declaration forces unnecessary string casting for aggregation.

---

### B3: No MRR deduplication by `(office_phone, vertical)` pair

**Severity:** Data correctness bug
**Root Cause:** Multiple offers share the same Unit's MRR value

**The domain model hierarchy:**
```
Business
  └── UnitHolder
      └── Unit (MRR lives here: e.g., $5,000/month)
          └── OfferHolder
              ├── Offer A (inherits Unit's MRR = $5,000)
              ├── Offer B (inherits Unit's MRR = $5,000)
              └── Offer C (inherits Unit's MRR = $5,000)
```

Naively summing MRR across offers **triple-counts** the Unit's MRR when that Unit has 3 active offers. The one-off script reported `$106,226` total MRR across 80 tasks — this number is inflated by the sibling multiplier.

**Correct approaches:**
1. **Deduplicate by `(office_phone, vertical)` pair** — the PVP key that identifies a unique Unit. Use `df.unique(subset=["office_phone", "vertical"])` before summing
2. **Query at Unit level instead** — use `UNIT_SCHEMA` where MRR is `cf:MRR` (direct, Decimal), then filter to units that have active offers via a join
3. **Use the `QueryEngine.execute_aggregate()` endpoint** — it supports `group_by` + `sum` natively:
   ```json
   POST /v1/query/unit/aggregate
   {
     "group_by": ["office_phone", "vertical"],
     "aggregations": [{"column": "mrr", "agg": "sum"}],
     "where": {"field": "is_completed", "op": "eq", "value": false}
   }
   ```

**The join infrastructure exists:** `hierarchy.py` defines `unit → offer` relationship with `default_join_key="office_phone"`, and `QueryEngine.execute_rows()` supports `request.join` for cross-entity enrichment.

---

### B4: Existing query infrastructure was entirely bypassed

**Severity:** Architectural gap (usability)
**Root Cause:** No ergonomic one-shot API for ad-hoc aggregation queries outside the HTTP API

The project has a complete query stack built for exactly this kind of query:

| Layer | Component | Purpose | Status |
|-------|-----------|---------|--------|
| API Route | `POST /v1/query/{type}/aggregate` | HTTP endpoint for aggregation | Implemented (query_v2.py:126) |
| Engine | `QueryEngine.execute_aggregate()` | group_by + agg + WHERE + HAVING | Implemented (engine.py:266) |
| Compiler | `AggregationCompiler` | Compiles AggSpec to pl.Expr | Implemented |
| Models | `AggregateRequest`, `AggSpec`, `AggFunction` | Request/response types | Implemented |
| Cache | `EntityQueryService.get_dataframe()` | DataFrame cache with self-refresh | Implemented |
| Index | `SectionIndex` | Section name resolution | Implemented |
| Joins | `execute_join()` + `EntityRelationship` | Cross-entity enrichment | Implemented |
| Guards | `QueryLimits` | Depth/group/limit bounds | Implemented |

**But all of this requires:**
- A running API server with JWT authentication, OR
- Manual wiring of `UniversalResolutionStrategy` + `EntityQueryService` + `QueryEngine` in a script

There is no ergonomic script-level entry point like:
```python
from autom8_asana.query import quick_aggregate
result = quick_aggregate("unit", group_by=["vertical"], agg={"mrr": "sum"})
```

The `ProgressiveProjectBuilder` builds and persists DataFrames to S3, and the `QueryEngine` reads from that cache. For a one-off script, this cache may not be warm, requiring a full build cycle first.

**Recommendation:** Add a `query_cli` utility or `QueryEngine.from_token()` factory that wires the full stack from a PAT for ad-hoc usage.

---

### B5: `TaskRow` model `extra="forbid"` blocks extensibility

**Severity:** Design tension
**Root Cause:** Strict Pydantic model prevents fallback extraction for unknown task types

`TaskRow` (task_row.py:37): `model_config = ConfigDict(frozen=True, extra="forbid", strict=True)`

This is correct for type safety — `UnitRow` and `ContactRow` explicitly declare their fields. But the fallback path (`case _:` → `DefaultExtractor` → `TaskRow.model_validate()`) crashes when schema has extra columns.

**The contract violation:** `OFFER_SCHEMA` declares 12 columns beyond the base 12, but no `OfferRow` exists to receive them. The schema and row model are out of sync.

**Pattern to enforce:** Every schema registered in `SchemaRegistry` MUST have a corresponding:
1. `{Type}Row(TaskRow)` model in `task_row.py`
2. `{Type}Extractor(BaseExtractor)` in `extractors/{type}.py`
3. `case "{Type}":` branch in `_create_extractor()`

Currently: `Business`, `AssetEdit`, `AssetEditHolder` schemas are also registered but may lack extractors (not verified in this spike).

---

### B6: `is_completed` vs `completed` naming inconsistency

**Severity:** Minor (confusion risk)
**Root Cause:** Base schema column is `is_completed` but Asana API field and Task model use `completed`

- `BASE_SCHEMA` column: `name="is_completed"`, `source="completed"` (the Asana API field)
- `TaskRow` model: `is_completed: bool`
- Asana Task model: `completed: bool`
- One-off script used: `pl.col("completed")` — would fail on a properly-built DataFrame where the column is `is_completed`

**Impact:** Confusion for anyone writing Polars filters against offer DataFrames. The column rename from API field to schema field is intentional but undiscoverable.

---

## Comparison Matrix: MRR Aggregation Approaches

| Approach | Correct? | Deduplication | API Calls | Complexity | Works Today? |
|----------|----------|---------------|-----------|------------|-------------|
| Raw custom field extraction | No | None (overcounts) | N (1 per section) | Low | Yes |
| `section.to_dataframe("Offer")` | Crash | N/A | N/A | Medium | No (B1) |
| `section.to_dataframe("Unit")` | Yes | Native (1 row per unit) | N (1 per section) | Medium | Yes |
| `QueryEngine.execute_aggregate("unit")` | Yes | Via `group_by` | 0 (cache) | Low | If cache warm |
| Unit DataFrame + join to active offers | Yes | Via join key | 0 (cache) | Medium | If cache warm |

## Recommendations

### Immediate (Bugs)

1. **Create `OfferRow` + `OfferExtractor`** — Mirror the UnitRow/UnitExtractor pattern. This unblocks `to_dataframe(task_type="Offer")` for all downstream consumers.

2. **Audit `cascade:MRR` source** — If MRR is directly on offer tasks in Asana, change to `cf:MRR` with `dtype="Decimal"` to match UNIT_SCHEMA. If it truly cascades, add integration tests verifying the cascade resolver is needed.

3. **Audit other registered schemas** — Verify that `Business`, `AssetEdit`, `AssetEditHolder` schemas have matching extractors and row models.

### Near-term (Usability)

4. **Add script-level query utility** — A `QueryEngine.from_pat(token, entity_type)` or standalone `query_cli.py` that wires `AsanaClient` → `EntityQueryService` → `QueryEngine` for ad-hoc use.

5. **Document the `is_completed` column rename** — Add note to BASE_SCHEMA ColumnDef or a dev guide entry.

### Strategic (Correctness)

6. **Enforce schema-extractor-row invariant** — Add a test that iterates `SchemaRegistry.list_task_types()` and asserts each has a corresponding extractor via `_create_extractor()` and row model that accepts all schema columns.

7. **MRR aggregation should default to Unit level** — Any dashboard or API consumer summing MRR should query at Unit level with `group_by=["office_phone", "vertical"]`, not at Offer level.

## Follow-up Actions

| # | Action | Priority | Blocked By |
|---|--------|----------|------------|
| 1 | Create OfferRow + OfferExtractor | P1 | Nothing |
| 2 | Audit cascade:MRR vs cf:MRR | P1 | Nothing |
| 3 | Audit Business/AssetEdit/AssetEditHolder extractors | P2 | Nothing |
| 4 | Add schema-extractor-row invariant test | P2 | Nothing |
| 5 | Add script-level query utility | P2 | Nothing |
| 6 | Document is_completed naming | P3 | Nothing |
| 7 | Establish MRR aggregation best practice doc | P3 | #2 |
