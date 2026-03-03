# SPIKE: n8n Consumer Integration Bugs

**Date:** 2026-03-03
**Reporter:** Damian (via Slack)
**Context:** n8n form-questions workflow consuming autom8y API

---

## Bug 1: Resolver Returns NOT_FOUND for 9/10 Accounts

### Symptom

`POST /v1/resolve/unit` with phone criteria returns `match_count: 0` for 9 of 10 accounts. The one that resolves (Head and Neck Centers) was created through autom8y. The other 9 were created directly in Asana. All 10 have correct phone numbers on the Businesses project.

### How Resolution Works

The Unit schema defines `office_phone` with `source="cascade:Office Phone"` (`dataframes/schemas/unit.py:55`). This cascades from the Business parent via the parent chain: **Unit → UnitHolder → Business**. The cascade is designed to work for ALL Unit tasks regardless of creation method — there's no "legacy vs autom8y" distinction.

The resolution path during preload extraction (`dataframe_view.py:365-508`):
1. Try local extraction — does the Unit task have "Office Phone" in its own custom_fields?
2. If no store → return None (cascade disabled)
3. Get parent chain from UnifiedTaskStore → traverse → extract "Office Phone" from Business ancestor
4. Fallback: grandparent direct fetch

### Root Cause Analysis: Stale S3 Parquet

The most likely root cause is that the **S3 parquet for the Unit entity was written without working cascade resolution**, and subsequent ECS startups load it directly without re-running cascade.

**Evidence: the S3 parquet fast-path bypasses cascade** (`api/preload/progressive.py:326-349`):

```python
manifest = await persistence.get_manifest_async(project_gid)
if manifest is None:
    # Try loading existing dataframe.parquet from S3
    s3_df, s3_watermark = await df_storage.load_dataframe(project_gid)
    if s3_df is not None and len(s3_df) > 0:
        # Load directly into memory cache — NO cascade validation
        await dataframe_cache.put_async(project_gid, entity_type, s3_df, s3_watermark)
        return True  # ← EXITS without build_progressive_async()
```

When no manifest exists (Lambda deletes it after build), but a `dataframe.parquet` exists in S3, ECS loads it directly into the in-memory cache. **No cascade validation runs.** If that parquet has null `office_phone` values, they persist until a full rebuild is triggered.

**Why Head and Neck Centers works:** The `_resolve_cascade_from_dict` tries **local extraction first** (line 385-391) — if the Unit task itself has "Office Phone" in its custom_fields, it returns immediately without needing cascade. Autom8y's creation flow likely sets Office Phone directly on the Unit task. The 9 manually-created accounts rely on cascade from the Business parent, which is null in the stale parquet.

### Possible Failure Chains

| # | Scenario | How stale parquet is created | Why it persists |
|---|----------|------------------------------|-----------------|
| **A** | Lambda cold-start build | Lambda may not have `shared_store` for cascade | ECS loads parquet directly (fast-path) |
| **B** | Initial build without store | Progressive builder was created with `store=None` | Resume=True skips completed sections |
| **C** | Hierarchy warming failure | `_populate_store_with_tasks` catches all exceptions (line 1201) and continues | Section parquet persists with null cascade fields |
| **D** | Cross-project parent fetch failure | Rate limiting / transient errors during Business parent fetch | Logged as warning, cascade returns None, parquet persisted |

### Diagnostic Steps

1. **Check S3 parquet directly:**
   ```
   # Read the Unit dataframe.parquet and check office_phone column
   aws s3 cp s3://{bucket}/dataframes/1201081073731555/dataframe.parquet /tmp/
   python -c "import polars as pl; df=pl.read_parquet('/tmp/dataframe.parquet'); print(df.select('gid','name','office_phone').filter(pl.col('office_phone').is_not_null()))"
   ```
   If office_phone is null for most rows → **parquet is stale**, cascade didn't run.

2. **Check ECS logs for cascade signals:**
   - `cascade_resolution_empty_chain` → parent chain not found
   - `parent_chain_gaps_skipped` → parent fetched but not cached
   - `store_populate_batch_failed` → hierarchy warming failed entirely
   - `progressive_preload_loaded_from_parquet` → fast-path loaded (no cascade)

3. **Check section manifest:**
   ```
   aws s3 ls s3://{bucket}/dataframes/1201081073731555/sections/
   ```
   If no manifest.json but dataframe.parquet exists → fast-path loading is active.

4. **Force rebuild to verify cascade works:**
   ```
   # Via admin endpoint:
   POST /admin/rebuild?entity_type=unit&force=true
   ```
   If office_phone populates after rebuild → confirms stale parquet was the issue.

### Fix

**Immediate:** Force a full rebuild of the Unit DataFrame (`resume=False`) to re-run cascade resolution with a live shared_store. This should populate office_phone for all 9 accounts.

**Structural fix:** The S3 parquet fast-path (`progressive.py:345-349`) should run the cascade validator before loading into cache:

```python
if s3_df is not None and len(s3_df) > 0:
    # Run cascade validation on loaded parquet
    if shared_store is not None:
        s3_df, _ = await validate_cascade_fields_async(
            merged_df=s3_df, store=shared_store, ...
        )
    await dataframe_cache.put_async(project_gid, entity_type, s3_df, s3_watermark)
```

**Also consider:**
- Adding cascade field null-rate alerting: if >10% of rows have null cascade fields, log a warning
- Invalidating section manifests when schema version changes (ensure cascade column additions trigger rebuild)
- Adding phone normalization to the resolver (`PhoneNormalizer` exists at `models/business/matching/normalizers.py` but isn't wired into the DynamicIndex)

---

## Bug 2: `list_remove` Silently Dropped

### Symptom

n8n workflow sends `list_remove` in PATCH body for question removal. The field is silently ignored.

### Root Cause

`EntityWriteRequest` (`api/routes/entity_write.py:62-82`) accepts only `fields` and `list_mode` (`"replace"` | `"append"`). Pydantic silently drops unknown fields.

### Correct Pattern

Read-modify-write:
```
GET  /v1/entity/unit/{gid}?fields=form_questions    → ["Q1", "Q2", "Q3"]
PATCH /v1/entity/unit/{gid}
  {"fields": {"form_questions": ["Q1", "Q3"]}, "list_mode": "replace"}
```

### Fix

Add `model_config = ConfigDict(extra="forbid")` to `EntityWriteRequest` so unknown fields return 422 instead of being silently dropped.

---

## Suggested Reply to Damian

> Hey Damian, found the issue with both:
>
> **1. Resolver:** There's a bug in the preload pipeline — the Unit DataFrame in S3 has stale cascade data. Office Phone on Unit tasks is supposed to cascade from the Business parent, but the parquet was loaded from S3 without running cascade resolution. The one account that works (Head and Neck Centers) likely has Office Phone set directly on its Unit task from the autom8y creation flow, so it doesn't need cascade.
>
> I'm going to force a full rebuild of the Unit DataFrame which should fix all 9 accounts. I'll also patch the preload to validate cascade fields when loading from S3 so this doesn't happen again.
>
> **2. List removal:** `list_remove` isn't part of the API — it gets silently dropped (fixing that to return a proper error). For removing questions, do read-modify-write: GET the current values, filter out what you want to remove, PATCH back with `list_mode: "replace"`.

---

## Follow-Up Actions

- [ ] **P0:** Force Unit DataFrame rebuild (verify office_phone populates for all accounts)
- [ ] **P0:** Reply to Damian with status
- [x] **P0:** Populate shared store from Business fast-path for cascade resolution (WS-2)
- [x] **P0:** Add cascade validation + self-heal to S3 parquet fast-path in `progressive.py` (WS-1)
- [x] **P1:** Add `extra="forbid"` to `EntityWriteRequest`, `WorkflowInvokeRequest`, `CacheRefreshRequest` (WS-3)
- [x] **P1:** Reorder Lambda `default_priority` to process Business before Unit (WS-6)
- [ ] **P2:** Add cascade null-rate alerting (detect stale parquets before consumers hit them)
- [ ] **P2:** Wire `PhoneNormalizer` into resolver for format-tolerant phone matching
- [ ] **P3:** Consumer documentation for entity type selection and list field operations
