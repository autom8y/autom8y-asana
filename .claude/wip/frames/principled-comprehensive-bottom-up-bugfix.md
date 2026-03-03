# Principled Comprehensive Bottom-Up Bugfix

**Date:** 2026-03-03
**Trigger:** Damian bug report (n8n form-questions workflow)
**Spike:** `docs/spikes/SPIKE-n8n-consumer-bugs.md`

---

## Situation

Two bugs surfaced through n8n consumer integration. The spike identified root causes. This frame decomposes the fix work bottom-up: starting from the lowest-level data corruption, moving through the structural defenses that should have prevented it, and finishing with API contract hardening at the boundary.

## Bug Inventory

| # | Symptom | Root Cause | Severity |
|---|---------|-----------|----------|
| B1 | `POST /v1/resolve/unit` returns NOT_FOUND for 9/10 accounts by phone | S3 parquet fast-path loads stale DataFrame without cascade validation; `office_phone` is null for cascade-dependent rows | P0 |
| B2 | `list_remove` field silently dropped on PATCH | `EntityWriteRequest` lacks `extra="forbid"`; Pydantic discards unknown fields | P1 |

## Failure Chain Analysis (B1)

The cascade bug is not a single point failure. It is an emergent failure from multiple layers that each behaved "correctly" in isolation but combined to produce a silent data corruption path.

```
Lambda cold-start build
  -> builds DataFrame WITH cascade (or fails silently at hierarchy warming)
  -> writes parquet to S3
  -> deletes manifest

ECS startup (progressive preload)
  -> no manifest found
  -> loads dataframe.parquet from S3 directly  <-- THE GAP
  -> puts into memory cache with NO cascade validation
  -> index built from DataFrame with null office_phone
  -> resolver queries index -> NOT_FOUND
```

The cascade validator (`cascade_validator.py`) exists and works correctly. It runs inside `build_progressive_async()`. But the S3 fast-path at `progressive.py:345-375` returns `True` before reaching the builder, bypassing it entirely.

## Workstream Decomposition

Bottom-up ordering: fix the data first, then the structural gap, then the API boundary, then add detection for future regressions.

### WS-1: Cascade Validation on S3 Fast-Path (P0, ~2h)

**The core fix.** The S3 parquet fast-path in `api/preload/progressive.py:345-375` must run cascade validation before caching the loaded DataFrame.

**What changes:**
- After loading `s3_df` from S3 (line 345), invoke `validate_cascade_fields_async()` when `shared_store` is available and the entity type has cascade fields
- Need to construct or obtain a `CascadeViewPlugin` instance for the validator (the validator requires it for field extraction)
- If the shared store is not yet populated (Business hasn't loaded), the validation degrades gracefully (returns the same DataFrame unchanged)
- Log a new event `progressive_preload_cascade_validated` with correction counts

**Key constraint:** The Business project loads first (lines 459-483) before other entities. So by the time Unit parquet loading runs, the shared store should contain Business data. However, if Business itself was loaded from S3 fast-path (likely), the store may be empty. This means:
1. Business fast-path: no cascade needed (Business is the cascade source, not a consumer)
2. Unit/Contact/Offer fast-path: shared store may or may not have Business data depending on whether Business went through fast-path or builder

**Design decision:** If cascade validation corrects rows, re-persist the corrected DataFrame to S3 so subsequent startups get clean data (self-healing). This prevents the stale parquet from persisting indefinitely.

**Files:**
- `src/autom8_asana/api/preload/progressive.py` -- add validation call in fast-path
- `src/autom8_asana/dataframes/builders/cascade_validator.py` -- may need to make `cascade_plugin` optional or provide a factory

**Tests:**
- Unit test: mock S3 load returning DataFrame with null cascade fields, verify validation runs
- Unit test: verify Business entity skips cascade validation (no cascade fields to validate)
- Unit test: verify self-healing write-back when corrections applied

### WS-2: Shared Store Population for Fast-Path (P0, ~1h)

**Supporting fix for WS-1.** When Business loads via S3 fast-path, its tasks are NOT populated into `shared_store`. The store only gets populated during `build_progressive_async()` via `_populate_store_with_tasks()`. This means cascade validation in WS-1 would find an empty store and no-op.

**What changes:**
- After loading Business DataFrame from S3 fast-path, populate the shared store with Business task data so downstream entity cascade validation can resolve
- This does NOT require re-fetching from Asana API -- the Business DataFrame itself contains the data needed (gid, custom_fields with Office Phone, Vertical, etc.)
- However, the store expects task dicts (API shape), not DataFrame rows. Need a lightweight adapter: iterate Business DataFrame rows, construct minimal task dicts with `gid` and `custom_fields` keys, call `store.put_batch_async()` (without hierarchy warming, since Business is root)

**Alternative:** Instead of populating the store from the DataFrame, fetch Business tasks from Asana API during preload for cascade purposes only. This is more correct but adds API calls and latency. The DataFrame-to-dict adapter is sufficient for cascade field extraction.

**Files:**
- `src/autom8_asana/api/preload/progressive.py` -- add store population after Business fast-path load

**Tests:**
- Unit test: verify store is populated after Business fast-path load
- Unit test: verify downstream entity cascade validation finds Business data in store

### WS-3: EntityWriteRequest Extra Forbid (P1, ~15min)

**Straightforward API contract fix.**

**What changes:**
- Add `model_config = ConfigDict(extra="forbid")` to `EntityWriteRequest` at `api/routes/entity_write.py:62`
- Consumers sending unknown fields (e.g., `list_remove`) will get a 422 Validation Error instead of silent drop

**Files:**
- `src/autom8_asana/api/routes/entity_write.py` -- add ConfigDict import and model_config

**Tests:**
- Unit test: verify unknown fields produce 422
- Unit test: verify valid payloads still work

### WS-4: Cascade Null-Rate Alerting (P2, ~1h)

**Detection layer.** Even with the WS-1 fix, future cascade regressions should be detectable before consumers hit them.

**What changes:**
- After any DataFrame is cached (both fast-path and builder path), compute null rate for CASCADE_CRITICAL_FIELDS
- If null rate exceeds threshold (e.g., >50% for a field that should cascade), emit a warning log event `cascade_null_rate_elevated`
- This is observability, not blocking -- the DataFrame still loads

**Files:**
- `src/autom8_asana/dataframes/builders/cascade_validator.py` -- add `check_cascade_null_rate()` function
- `src/autom8_asana/api/preload/progressive.py` -- call after cache put

**Tests:**
- Unit test: verify warning emitted when null rate exceeds threshold
- Unit test: verify no warning when null rate is normal

### WS-5: PhoneNormalizer in Resolver Index (P2, ~1.5h)

**Defense in depth.** The DynamicIndex builds lookup keys by lowercasing values (`str(row[col]).lower()` at `dynamic_index.py:238`). Phone numbers stored as `+15551234567` match only if the query criterion is identical. If a consumer sends `(555) 123-4567` or `555-123-4567`, it will not match even when the data is correct.

The `PhoneNormalizer` already exists at `models/business/matching/normalizers.py` and handles E.164 normalization with US default country code. It is unused in the resolution path.

**What changes:**
- During DynamicIndex construction for columns that are phone fields (detectable by column name pattern or schema metadata), normalize values through `PhoneNormalizer` before indexing
- During resolver criterion normalization (`_normalize_criterion_fields`), normalize phone values through `PhoneNormalizer` before lookup
- This makes resolution format-tolerant: `+15551234567`, `(555) 123-4567`, `555.123.4567` all resolve to the same key

**Note:** The `ResolutionCriterion.validate_e164` validator already requires E.164 format on input. So this workstream's benefit is: (a) protecting against format mismatches in stored data, and (b) enabling future relaxation of the strict E.164 input requirement. Lower priority accordingly.

**Files:**
- `src/autom8_asana/services/dynamic_index.py` -- add normalizer support to `from_dataframe`
- `src/autom8_asana/services/resolver.py` -- normalize phone values in criterion before lookup

**Tests:**
- Unit test: verify index built with normalized phone values
- Unit test: verify format-variant queries resolve to same entry

## Dependency Graph

```
WS-2 (store population)
  |
  v
WS-1 (cascade validation on fast-path) --> WS-4 (null-rate alerting)

WS-3 (extra=forbid)  [independent]

WS-5 (phone normalizer) [independent]
```

WS-1 depends on WS-2 to be effective (without store data, validation no-ops). These two should be implemented together or WS-2 first. WS-3, WS-4, WS-5 are independent and can be done in any order.

## Execution Plan

| Phase | Workstreams | Approach | Est. Time |
|-------|------------|----------|-----------|
| A | WS-2 + WS-1 | Single worktree, implement together | ~3h |
| B | WS-3 | Standalone commit on main | ~15min |
| C | WS-4 | Standalone commit on main | ~1h |
| D | WS-5 | Standalone commit on main | ~1.5h |

Phase A is the P0 critical path. Phase B is quick and should be done immediately after A. Phases C and D are P2 hardening.

## Verification Strategy

After WS-1+WS-2 are implemented:
1. Run existing cascade validator tests: `pytest tests/unit/dataframes/builders/test_cascade_validator.py`
2. Run new tests for the fast-path integration
3. Full preload-related test suite to verify no regressions
4. After deploy: check ECS logs for `progressive_preload_cascade_validated` event with non-zero correction counts
5. After deploy: re-run Damian's n8n workflow against `POST /v1/resolve/unit` with the 9 failing phone numbers

After WS-3:
1. Run entity write test suite
2. Verify n8n workflow gets 422 instead of silent drop for `list_remove`

## Operational Follow-Up (Outside Code Scope)

- **Force rebuild:** Before this code ships, force a Unit DataFrame rebuild via admin endpoint to unblock Damian immediately. This is an operational action, not a code change.
- **Reply to Damian:** Explain both bugs and the workaround for list removal (read-modify-write pattern).

---

## Next Commands

Priority-ordered commands to execute this initiative:

1. **Reply to Damian** (manual, do immediately)

2. **Force Unit DataFrame rebuild** (operational, unblocks Damian before code ships):
   ```
   POST /admin/rebuild?entity_type=unit&force=true
   ```

3. **Phase A -- Core cascade fix (WS-2 + WS-1):**
   ```
   /build WS-2+WS-1: Add shared store population for Business fast-path load, then add cascade validation to S3 parquet fast-path in progressive.py. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md for full spec. Key files: api/preload/progressive.py, dataframes/builders/cascade_validator.py. Tests required.
   ```

4. **Phase B -- EntityWriteRequest hardening (WS-3):**
   ```
   /build WS-3: Add extra="forbid" to EntityWriteRequest in api/routes/entity_write.py. Add ConfigDict import, set model_config = ConfigDict(extra="forbid"). Add test for 422 on unknown fields. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md
   ```

5. **Phase C -- Cascade null-rate alerting (WS-4):**
   ```
   /build WS-4: Add cascade null-rate alerting. Add check_cascade_null_rate() to cascade_validator.py, call from progressive.py after cache put. Emit warning log when null rate for cascade fields exceeds 50%. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md
   ```

6. **Phase D -- Phone normalizer in resolver (WS-5):**
   ```
   /build WS-5: Wire PhoneNormalizer into DynamicIndex construction and resolver criterion normalization. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md for spec.
   ```

---

## First-Principles Reframe

**Date:** 2026-03-03
**Author:** Architect agent

The original 5 workstreams correctly identify the immediate bugs and their fixes. This reframe digs deeper: what systemic conditions allowed silent failure, which other code paths share the same vulnerability, and what architectural invariants are missing that would prevent this class of bug from recurring.

---

### 1. First-Order Analysis: Confirming Immediate Bugs

#### B1: S3 fast-path bypasses cascade validation -- CONFIRMED

At `src/autom8_asana/api/preload/progressive.py:345-375`, when `manifest is None` but `s3_df` exists, the DataFrame loads directly into the in-memory cache via `dataframe_cache.put_async()` at line 369. Execution returns `True` at line 375, completely bypassing `build_progressive_async()` at line 416 and its Step 5.5 cascade validation at lines 466-503.

The cascade validator (`src/autom8_asana/dataframes/builders/cascade_validator.py:41-155`) is structurally sound. It iterates `CASCADE_CRITICAL_FIELDS` (currently only `office_phone`), finds rows with null values, resolves parent chains via `UnifiedTaskStore`, and applies corrections. The problem is purely one of invocation: it is only called from inside `build_progressive_async()`, never from the fast-path.

#### B2: EntityWriteRequest silently drops unknown fields -- CONFIRMED

At `src/autom8_asana/api/routes/entity_write.py:62-82`, `EntityWriteRequest(BaseModel)` has no `model_config`. Pydantic v2 defaults to `extra="ignore"`, silently discarding any fields not declared on the model. A consumer sending `{"fields": {...}, "list_remove": ["Q2"]}` gets back a 200 with `list_remove` silently dropped.

#### B1 additional detail: shared_store is empty on fast-path -- CONFIRMED

The `shared_store` is created at `progressive.py:245-247` as an empty `UnifiedTaskStore`. It only gets populated during `build_progressive_async()` via `_populate_store_with_tasks()` at `progressive.py:664-665`, which calls `store.put_batch_async()` with `warm_hierarchy=True` at `progressive.py:1194-1199`. When Business loads via fast-path (lines 345-375), `_populate_store_with_tasks()` is never called. The store remains empty, so even if cascade validation were added to the fast-path, it would find no parent chain data and no-op.

---

### 2. Second-Order Analysis: Systemic Conditions

#### A. Cache Boundary Data Integrity -- ALL Population Paths Audited

There are **six distinct paths** that populate the DataFrame cache. Only one runs cascade validation:

| # | Path | File | Cascade? | Store populated? |
|---|------|------|----------|------------------|
| 1 | Progressive builder | `progressive.py:416` -> `build_progressive_async()` | YES (Step 5.5, line 466-503) | YES (`_populate_store_with_tasks`, line 664) |
| 2 | S3 fast-path | `progressive.py:345-375` | NO | NO |
| 3 | Legacy preload | `legacy.py:182-296` (incremental) / `legacy.py:328-345` (full rebuild) | NO -- uses `client.unified_store` on the ProgressiveProjectBuilder, but never runs Step 5.5 because the builder is a fresh instance with its own store | Partially -- each builder uses `client.unified_store`, a per-client store that is NOT the shared_store |
| 4 | SWR refresh | `cache/dataframe/factory.py:40-128` (`_swr_build_callback`) | DEPENDS -- delegates to `build_progressive_async(resume=True)` which runs Step 5.5 IF the store was populated during the build. But the SWR callback creates a fresh `AsanaClient` with its own `unified_store`, and Business data from the preload shared_store is NOT available. If the SWR rebuild only fetches Unit sections (resume=True, Business already complete), cascade validation runs but finds an empty parent chain and no-ops. | NO cross-project data -- `client.unified_store` is per-client |
| 5 | Admin incremental rebuild | `admin.py:279-309` (`_perform_incremental_rebuild`) | DEPENDS -- same issue as SWR. Creates a fresh `AsanaClient` per entity type. Each client's `unified_store` starts empty. If rebuilding Unit, the Business parent chain is not in this client's store. | NO cross-project data |
| 6 | `@dataframe_cache` decorator build | `cache/dataframe/decorator.py:163-258` | NO -- calls `strategy._build_dataframe()` which returns `(df, watermark)` and calls `cache.put_async()` directly. No cascade validation. | NO -- builds via resolution strategy, not progressive builder |

**Finding A-1 (CRITICAL):** Paths 2, 3, 4, 5, and 6 all bypass cascade validation. The SWR refresh (path 4) and admin rebuild (path 5) nominally call `build_progressive_async()` which includes Step 5.5, but they use a per-client `unified_store` that does not contain cross-project Business data. Cascade validation finds an empty hierarchy and no-ops.

**Finding A-2 (MODERATE):** The legacy preload at `src/autom8_asana/api/preload/legacy.py` is the ADR-011 degraded-mode fallback. It loads DataFrames from S3 (line 182), does incremental catch-up or full rebuild, and puts them into the cache (lines 293, 350). It never creates a `shared_store` for cross-project cascade resolution. However, its fallback nature (only fires when S3 is unavailable, `progressive.py:253-272`) means it is rarely exercised. The fact that it also skips cascade validation reinforces the systemic pattern: cascade validation is an afterthought bolted onto one path, not an architectural invariant.

**Finding A-3 (LOW):** The Lambda `CacheWarmer` at `src/autom8_asana/lambda_handlers/cache_warmer.py` does NOT directly build DataFrames. It delegates to `CacheWarmer.warm_entity_async()` -> `_warm_entity_type_async()` at `cache/dataframe/warmer.py:298-402`, which calls `strategy._build_dataframe(project_gid, client)`. The resolution strategy builds via the `@dataframe_cache` decorator or directly. The warmer then calls `cache.put_async()` at `warmer.py:360-365`. No cascade validation runs in this path either. However, the Lambda processes entity types sequentially (line 665 of `cache_warmer.py`), and the default priority is `["unit", "business", ...]`. Since unit is built before business, the store cannot possibly have Business data when Unit is warmed. Even if cascade ran, it would fail.

**Finding A-4 (IMPORTANT):** The Lambda's entity ordering at `cache_warmer.py:577-585` lists `"unit"` FIRST, `"business"` SECOND. This is the opposite of what cascade requires. The progressive preload at `progressive.py:459-466` correctly processes Business first. This ordering mismatch means Lambda-built Unit parquets are always built without cascade data.

#### B. Entity Type Detection Fragility -- Weak Heuristic Impact Assessment

**CascadeViewPlugin weak heuristic** at `cascade_view.py:452-470`:

```python
def _detect_entity_type_from_dict(self, task_data: dict[str, Any]) -> EntityType:
    if task_data.get("parent") is None:
        return EntityType.BUSINESS
    return EntityType.UNKNOWN
```

**Proper detection system** at `models/business/detection/facade.py:186-221` (`detect_entity_type_from_dict`):
- Creates a `Task` model via `model_validate(data)`
- Runs full Tier 1-3 detection (project membership, name patterns, parent inference)
- Returns entity type string value or None

**Finding B-1 (LOW -- not a current bug, but a correctness risk):** The weak heuristic is used only by `CascadeViewPlugin._traverse_parent_chain()` at `cascade_view.py:263`, which is the RUNTIME cascade resolution path (resolving a single task's cascade fields during API requests). During preload extraction, the `DataFrameViewPlugin._resolve_cascade_from_dict()` at `dataframe_view.py:365-508` does NOT use `_detect_entity_type_from_dict` at all. Instead, it searches the parent chain for the field value directly without type detection. So the weak heuristic does not affect preload extraction.

**Finding B-2 (LOW):** The `_resolve_office_from_dict` method at `dataframe_view.py:661-681` DOES use the proper `detect_entity_type_from_dict` from the detection facade (imported at line 663). So the office field resolution uses the 4-tier detection system, not the weak heuristic.

**Finding B-3 (LOW -- theoretical risk):** A Business task with a `parent` field (e.g., if someone adds a parent relationship to a Business task in Asana) would be misclassified as UNKNOWN by the weak heuristic. Cascade resolution would then miss it as an owner. However, Business tasks in this codebase are always root tasks (no parent), so this is theoretical. The proper detection system at the facade would correctly identify it via Tier 1 project membership.

**Conclusion on B:** The weak heuristic is a code smell but not a current bug source. It only affects runtime resolution via CascadeViewPlugin, and even there, the fallback logic at `cascade_view.py:282-300` (checking if the last parent in the chain is root) provides a safety net. Replacing it with the proper detection system is a hygiene improvement, not a critical fix. The original WS decomposition correctly omits this from scope.

#### C. Silent Exception Swallowing -- Broad Catches in Build Pipeline

**Finding C-1 (CRITICAL -- the root cause multiplier):** `_populate_store_with_tasks` at `progressive.py:1201` catches ALL exceptions and logs a warning. If hierarchy warming fails (rate limit, transient API error, timeout), the build continues. Cascade fields end up null in the DataFrame. The DataFrame is then persisted to S3 via `write_final_artifacts_async()` at line 509-515. Future fast-path loads perpetuate this stale data.

**Finding C-2 (MODERATE):** `_fetch_and_persist_section` -- the section-level fetch loop is inside `build_progressive_async()` but the broad catch is at `progressive.py:443-453` (the `process_project` wrapper in the preload orchestrator, not the builder itself). Inside the builder, individual section failures are handled at `progressive.py:688-718` with per-section error logging. A section fetch failure causes that section's tasks to be missing from the DataFrame, but does not abort the build. This is intentional fault isolation.

**Finding C-3 (MODERATE):** `validate_cascade_fields_async` is itself wrapped in a broad catch at `progressive.py:495-503`. If cascade validation throws (e.g., `store.get_parent_chain_async()` raises), the build continues with the uncorrected DataFrame. This is intentional -- cascade validation is "additive" -- but combined with C-1, it means BOTH the initial cascade resolution AND the post-build validation pass can fail silently.

**Finding C-4 (LOW):** The Lambda handler has broad catches at multiple levels (`cache_warmer.py:828`, `cache_warmer.py:928`, `cache_warmer.py:1032`), but these are at the correct boundary layer. Per-entity failures are isolated and logged. The Lambda continues to process remaining entity types. This is appropriate fault isolation.

**Conclusion on C:** The critical issue is C-1. Silent hierarchy warming failure produces a parquet with null cascade fields. This parquet is persisted to S3 and becomes the "source of truth" for future fast-path loads. The cascading effect is: (1) warming fails silently -> (2) parquet written with null cascade -> (3) fast-path loads stale parquet -> (4) cascade validation (if added) finds empty store -> (5) null cascade persists indefinitely. WS-1 and WS-2 fix step (3)-(4), but C-1 means step (1)-(2) can still produce stale parquets. The null-rate alerting in WS-4 is the only detection for this failure mode.

#### D. Pydantic Extra Field Handling -- Full Route Model Audit

Complete audit of all `BaseModel` subclasses in `src/autom8_asana/api/routes/`:

| Model | File:Line | `extra` config | Risk |
|-------|-----------|----------------|------|
| `ResolutionCriterion` | `resolver_models.py:31` | `extra="allow"` | INTENTIONAL -- accepts arbitrary criteria fields per SPIKE-dynamic-api-criteria |
| `ResolutionRequest` | `resolver_models.py:100` | `extra="forbid"` | OK |
| `ResolutionResultModel` | `resolver_models.py:142` | `extra="forbid"` | OK (response model) |
| `ResolutionMeta` | `resolver_models.py:165` | `extra="forbid"` | OK (response model) |
| `ResolutionResponse` | `resolver_models.py:189` | `extra="forbid"` | OK (response model) |
| `QueryRequest` | `query.py:102` | `extra="forbid"` | OK |
| `QueryMeta` | `query.py:127` | `extra="forbid"` | OK (response model) |
| `QueryResponse` | `query.py:138` | `extra="forbid"` | OK (response model) |
| `SchemaFieldInfo` | `resolver_schema.py:43` | `extra="forbid"` | OK (response model) |
| `EntitySchemaResponse` | `resolver_schema.py:57` | `extra="forbid"` | OK (response model) |
| `SectionTimelinesResponse` | `section_timelines.py:42` | `extra="forbid"` | OK (response model) |
| **`EntityWriteRequest`** | **`entity_write.py:62`** | **NONE (defaults to "ignore")** | **BUG -- silently drops unknown fields** |
| `FieldWriteResult` | `entity_write.py:85` | NONE | LOW (response model) |
| `EntityWriteResponse` | `entity_write.py:94` | NONE | LOW (response model) |
| **`CacheRefreshRequest`** | **`admin.py:31`** | **NONE (defaults to "ignore")** | **LOW -- admin-only, S2S auth, but inconsistent** |
| `CacheRefreshResponse` | `admin.py:43` | NONE | LOW (response model) |
| `ServiceClaims` | `internal.py:31` | NONE | LOW (internal auth, extra fields are harmless) |
| **`WorkflowInvokeRequest`** | **`workflows.py:44`** | **NONE (defaults to "ignore")** | **MODERATE -- consumer-facing, silently drops unknown params** |
| `WorkflowInvokeResponse` | `workflows.py:72` | NONE | LOW (response model) |

**Finding D-1 (BUG):** `EntityWriteRequest` -- confirmed, already identified in B2.

**Finding D-2 (MODERATE):** `WorkflowInvokeRequest` at `workflows.py:44` -- accepts `entity_ids`, `dry_run`, and `params`. No `extra` config. If a consumer sends `{"entity_ids": [...], "timeout": 60}`, the `timeout` field is silently dropped. While `params` is a catch-all dict for workflow-specific parameters, fields sent alongside (not inside) `params` are silently dropped.

**Finding D-3 (LOW):** `CacheRefreshRequest` at `admin.py:31` -- admin-only endpoint behind S2S JWT. Low risk because only internal operators call it, but inconsistent with the codebase pattern.

**Finding D-4 (OBSERVATION):** Response models (`FieldWriteResult`, `EntityWriteResponse`, `CacheRefreshResponse`, `WorkflowInvokeResponse`) without `extra` config are not a risk because extra fields in responses are additive (the server controls what it sends). However, for schema consistency, they should use `extra="forbid"` as response model contracts.

---

### 3. Third-Order Analysis: Missing Architectural Invariants

#### E. No Cache Integrity Gate

**Current state:** `dataframe_cache.put_async()` at `cache/integration/dataframe_cache.py:571` is a pure storage operation. It accepts any `pl.DataFrame` and stores it keyed by `(project_gid, entity_type)`. There is no validation of the DataFrame's contents. Six different code paths call `put_async()`, and only one (the progressive builder path) runs cascade validation beforehand.

**Proposed invariant: CacheIntegrityGate**

A `CacheIntegrityGate` would be a validation layer that sits between DataFrame producers and the cache. It enforces schema and cascade invariants before allowing data into the cache.

Two design options:

**Option 1: Wrap `put_async()`** -- Add an optional `validate` parameter to `dataframe_cache.put_async()` or wrap it with a validating decorator. When `validate=True` (default), run cascade null-rate checks and schema validation before storing. Callers that have already validated can pass `validate=False`.

Pro: Single enforcement point, no caller changes needed.
Con: `put_async` becomes a policy-aware method (violates SRP). Also, some callers intentionally put raw DataFrames (e.g., intermediate SWR builds).

**Option 2: Validate on S3 write** -- Move validation to `S3DataFrameStorage.save_dataframe()`. Since the parquet on S3 is the durable artifact that fast-path loads, validating at write time ensures stale parquets cannot be created.

Pro: Eliminates the root cause (stale parquets in S3). Fast-path loads are always valid.
Con: Adds latency to every S3 write. Does not protect the in-memory cache tier.

**Recommended: Option 1 with "check-and-warn" semantics.** The gate should LOG warnings (not block writes) when cascade null rates exceed thresholds. This is WS-4 generalized. Blocking writes would risk making the system unavailable when cascade data is legitimately unavailable (e.g., Business project API outage). The observability from warnings enables operator intervention.

**Implementation:** Add a `_check_integrity(df, entity_type)` method to `DataFrameCache` called from `put_async()`. This method checks cascade null rates per `CASCADE_CRITICAL_FIELDS` and logs structured warnings. It is a 30-line addition, not a new class.

#### F. No Parquet Provenance Metadata

**Current state:** Parquet files in S3 have no metadata about how they were built. The fast-path at `progressive.py:345` calls `df_storage.load_dataframe(project_gid)` which returns a raw `(DataFrame, watermark)` tuple. There is no way to know whether cascade ran, what store state was available, or what schema version produced the parquet.

**Proposed invariant: Parquet provenance via Polars metadata**

Polars DataFrames (and by extension Parquet files) support custom metadata on columns and at the file level. A lightweight provenance header would include:

```python
PROVENANCE_KEY = "autom8_provenance"
provenance = {
    "build_mode": "progressive_builder" | "lambda_warmer" | "swr_refresh" | "admin_rebuild",
    "cascade_validated": True | False,
    "cascade_corrections": 0,  # number of rows corrected
    "store_state": "populated" | "empty" | "partial",
    "schema_version": "2026-03-03",
    "builder_version": "1.0",
    "built_at": "2026-03-03T12:00:00Z",
}
```

The fast-path could then read provenance and decide:
- If `cascade_validated == False` and entity type has cascade fields, trigger a rebuild instead of loading.
- If `schema_version` mismatches current schema, trigger a rebuild.

**Implementation complexity:** MODERATE. Requires:
1. Write provenance to Polars DataFrame metadata during `write_final_artifacts_async()` (~10 lines).
2. Read provenance during `load_dataframe()` (~10 lines).
3. Fast-path decision logic based on provenance (~20 lines).

**Risk:** Existing parquets in S3 have no provenance. The fast-path must handle `provenance == None` gracefully (treat as "unknown provenance, proceed with existing behavior or trigger rebuild").

#### G. Business-First Ordering: Undocumented, Unenforced

**Current state:** The progressive preload at `progressive.py:459-466` splits projects into `business_configs` and `other_configs`, processing business first. This ordering is critical because cascade resolution for Unit/Contact/Offer depends on Business data being in the shared store.

The ordering is a code convention with a comment: `# Process Business first for cascade dependencies` (line 459). There is no enforced invariant. If someone:
- Reorders `project_configs` before the split
- Adds a new entity type that needs cascade from a non-Business source
- The Business fast-path fails silently (returns True but store is empty)

...all downstream cascade resolution breaks with no error.

**Finding G-1 (CRITICAL):** The Lambda cache warmer at `cache_warmer.py:577-585` has `default_priority = ["unit", "business", ...]`, processing Unit BEFORE Business. This is the opposite of the required cascade ordering. If the Lambda builds a Unit parquet, cascade fields will be null because Business data is not yet available.

**Finding G-2:** The Lambda warm path goes through `CacheWarmer._warm_entity_type_async()` -> `strategy._build_dataframe()`, which uses the `@dataframe_cache` decorator's build method. This path does NOT use the progressive builder and does NOT use a shared store. Each entity type is warmed independently with no cross-entity cascade resolution.

**Proposed invariant:** Add an assertion or configuration-driven dependency declaration:

```python
# In entity project registry or cascade config:
CASCADE_DEPENDENCIES = {
    "unit": ["business"],      # Unit cascade requires Business data
    "contact": ["business"],   # Contact cascade requires Business data
    "offer": ["business"],     # Offer cascade requires Business data
}
```

Any build path processing cascade-dependent entities must verify that dependencies are satisfied (either in the shared store or in the cache). The Lambda's `default_priority` should be reordered to respect cascade dependencies.

---

### 4. Reframed Workstream Decomposition

The original 5 workstreams are necessary but not sufficient. They fix the immediate bugs (B1, B2) and add detection (WS-4, WS-5), but they leave the systemic conditions intact. A broadened decomposition:

#### WS-1: Cascade Validation on S3 Fast-Path (P0, ~2h) -- CONFIRMED, UNCHANGED

Unchanged from original frame. Add `validate_cascade_fields_async()` call after S3 parquet load at `progressive.py:345-375`.

#### WS-2: Shared Store Population for Fast-Path (P0, ~1h) -- CONFIRMED, UNCHANGED

Unchanged from original frame. Populate `shared_store` from Business DataFrame after Business fast-path load.

#### WS-3: EntityWriteRequest Extra Forbid (P1, ~30min) -- EXPANDED

Original scope plus:
- Add `model_config = ConfigDict(extra="forbid")` to `WorkflowInvokeRequest` at `workflows.py:44`
- Add `model_config = ConfigDict(extra="forbid")` to `CacheRefreshRequest` at `admin.py:31`
- Document that `ResolutionCriterion.extra="allow"` is intentional (already has a comment, but add a code comment referencing this audit)

Expanded from 15min to 30min.

#### WS-4: Cascade Null-Rate Alerting (P2, ~1h) -- CONFIRMED, UNCHANGED

Unchanged from original frame. Post-cache-put null rate check.

#### WS-5: PhoneNormalizer in Resolver Index (P2, ~1.5h) -- CONFIRMED, UNCHANGED

Unchanged from original frame. Defense in depth.

#### WS-6: Lambda Cascade Ordering Fix (P1, ~30min) -- NEW

**Problem:** Lambda `default_priority` at `cache_warmer.py:577-585` processes Unit before Business. This means Lambda-built Unit parquets always have null cascade fields.

**Fix:**
- Reorder `default_priority` to `["business", "unit", "offer", "contact", "asset_edit", "asset_edit_holder", "unit_holder"]`
- Add a comment explaining the cascade dependency ordering
- Add `CASCADE_DEPENDENCIES` dict (or equivalent) as documentation

**Files:**
- `src/autom8_asana/lambda_handlers/cache_warmer.py` -- reorder priority list
- Optionally add a dependency check before processing cascade-dependent entity types

**Tests:**
- Unit test: verify `default_priority` starts with business
- Unit test: verify cascade-dependent entities are processed after their dependencies

#### WS-7: Parquet Provenance Metadata (P3, ~2h) -- NEW

**Problem:** No way to detect stale parquets. The fast-path loads any parquet blindly.

**Fix:**
- Write provenance metadata to Polars DataFrame during `write_final_artifacts_async()`
- Read provenance during `load_dataframe()`
- Fast-path checks `cascade_validated` field; if False and entity type has cascade fields, skip fast-path and proceed to builder or Lambda delegation

**Files:**
- `src/autom8_asana/dataframes/section_persistence.py` -- write provenance
- `src/autom8_asana/dataframes/storage.py` -- read provenance
- `src/autom8_asana/api/preload/progressive.py` -- provenance check in fast-path

**Tests:**
- Unit test: verify provenance written to parquet metadata
- Unit test: verify fast-path rejects parquets without cascade validation for cascade-dependent entities
- Unit test: verify backward compatibility (missing provenance treated as "proceed with existing behavior")

#### WS-8: SWR + Admin Cross-Entity Cascade (P3, ~1.5h) -- NEW

**Problem:** SWR refresh and admin incremental rebuild create per-client `unified_store` instances that lack cross-entity Business data. Cascade validation in these paths no-ops because the store is empty.

**Fix:**
- For SWR refresh (`_swr_build_callback` at `cache/dataframe/factory.py:40`): Before building a cascade-dependent entity, check if Business data is available in the DataFrameCache. If so, populate the builder's `unified_store` from the cached Business DataFrame (same adapter pattern as WS-2).
- For admin incremental rebuild (`_perform_incremental_rebuild` at `admin.py:205`): Same approach -- pre-populate the client's `unified_store` with Business data from cache before building cascade-dependent entities.
- This is a generalization of WS-2's pattern applied to two additional code paths.

**Files:**
- `src/autom8_asana/cache/dataframe/factory.py` -- SWR build callback
- `src/autom8_asana/api/routes/admin.py` -- admin incremental rebuild

**Tests:**
- Unit test: verify SWR rebuild for Unit entity populates store with Business data
- Unit test: verify admin rebuild for Unit entity populates store with Business data

---

### 5. Dependency Graph

```
WS-2 (store population for fast-path)
  |
  v
WS-1 (cascade validation on fast-path) --> WS-4 (null-rate alerting)
                                        --> WS-7 (parquet provenance)

WS-3 (extra=forbid audit)  [independent]

WS-5 (phone normalizer)    [independent]

WS-6 (Lambda ordering fix) [independent, but synergistic with WS-7]

WS-8 (SWR + admin cascade) [depends on WS-2 pattern, but independent implementation]
```

Critical path: WS-2 -> WS-1 (must ship together for P0 fix)
Quick wins: WS-3, WS-6 (can ship independently, minimal risk)
Hardening: WS-4, WS-5, WS-7, WS-8 (P2/P3, ship after P0 stabilizes)

---

### 6. Risk Assessment

#### If we only do the original 5 WS (WS-1 through WS-5):

**Fixed:**
- B1 (Unit resolver NOT_FOUND) -- fixed via WS-1 + WS-2
- B2 (EntityWriteRequest silent drop) -- fixed via WS-3
- Cascade null-rate detection -- added via WS-4
- Phone normalization defense -- added via WS-5

**Remaining risks:**
- Lambda-built parquets still have null cascade fields because Lambda processes Unit before Business (Finding A-4 / G-1). If Lambda rebuilds while ECS is running, the new parquet overwrites the corrected one. Next ECS restart loads the stale Lambda parquet via fast-path. **Risk: P0 fix is undone by Lambda.**
- SWR refresh builds with empty store, producing parquets without cascade data. SWR is triggered automatically when TTL expires. **Risk: P0 fix is undone by SWR refresh within hours.**
- Admin rebuild produces parquets without cascade data. Operator triggers rebuild to fix stale data, gets another stale parquet. **Risk: confusing operational experience.**
- No provenance: stale parquets are indistinguishable from valid ones. The only detection is WS-4 null-rate alerting after the fact.
- `WorkflowInvokeRequest` silently drops unknown fields (Finding D-2).

#### If we do all 8 WS:

**Fixed:**
- All of the above, plus:
- Lambda cascade ordering ensures Lambda-built parquets have correct cascade data
- SWR and admin rebuild populate store before cascade-dependent builds
- Parquet provenance enables the fast-path to reject invalid parquets
- All request models have explicit `extra` config (consistency)

**Remaining risks (acceptable):**
- The weak heuristic in `CascadeViewPlugin._detect_entity_type_from_dict` (Finding B-1) -- low risk, cosmetic
- Broad catch in `_populate_store_with_tasks` (Finding C-1) -- fundamental to fault isolation, narrowing it risks cascading failures. Mitigated by WS-4 null-rate alerting.
- 7 remaining structural import cycles (from REM-ASANA-ARCH) -- architectural debt, not related to cascade

---

## Reframed Next Commands

Priority-ordered commands to execute this initiative:

1. **Reply to Damian** (manual, do immediately)

2. **Force Unit DataFrame rebuild** (operational, unblocks Damian before code ships):
   ```
   POST /admin/rebuild?entity_type=unit&force=true
   ```

3. **Phase A -- Core cascade fix (WS-2 + WS-1), P0:**
   ```
   /build WS-2+WS-1: Add shared store population for Business fast-path load, then add cascade validation to S3 parquet fast-path in progressive.py. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md for full spec including first-principles reframe. Key files: api/preload/progressive.py, dataframes/builders/cascade_validator.py. Tests required.
   ```

4. **Phase B -- Request model hardening (WS-3 expanded) + Lambda ordering (WS-6), P1:**
   ```
   /build WS-3+WS-6: (a) Add extra="forbid" to EntityWriteRequest (entity_write.py:62), WorkflowInvokeRequest (workflows.py:44), and CacheRefreshRequest (admin.py:31). Add ConfigDict import where needed. Add test for 422 on unknown fields. (b) Reorder Lambda default_priority in cache_warmer.py:577 to put "business" first for cascade dependency ordering. Add test. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md
   ```

5. **Phase C -- Cascade null-rate alerting (WS-4), P2:**
   ```
   /build WS-4: Add cascade null-rate alerting. Add check_cascade_null_rate() to cascade_validator.py, call from progressive.py after cache put (both fast-path and builder path). Emit warning log when null rate for cascade fields exceeds 50%. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md
   ```

6. **Phase D -- Phone normalizer in resolver (WS-5), P2:**
   ```
   /build WS-5: Wire PhoneNormalizer into DynamicIndex construction and resolver criterion normalization. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md for spec.
   ```

7. **Phase E -- Parquet provenance (WS-7), P3:**
   ```
   /build WS-7: Add parquet provenance metadata. Write provenance dict (build_mode, cascade_validated, schema_version) to Polars DataFrame metadata during write_final_artifacts_async(). Read during load_dataframe(). Fast-path checks cascade_validated for cascade-dependent entities. See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md
   ```

8. **Phase F -- SWR + Admin cross-entity cascade (WS-8), P3:**
   ```
   /build WS-8: Pre-populate unified_store with Business data from cache before SWR refresh and admin incremental rebuild of cascade-dependent entities. Apply WS-2 adapter pattern to _swr_build_callback (cache/dataframe/factory.py) and _perform_incremental_rebuild (admin.py). See .claude/wip/frames/principled-comprehensive-bottom-up-bugfix.md
   ```
