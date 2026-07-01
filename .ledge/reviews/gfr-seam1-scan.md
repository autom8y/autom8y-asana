---
type: review
status: proposed
---
# GFR SEAM-1 Read-Gate Scan: Option E Re-Assertion Coverage

**Rite**: SIGNAL-SIFTER on CERT-1 (PT-01)
**Date**: 2026-06-25
**Scope**: `src/autom8_asana/dataframes/storage.py` — all `legacy_fallback_enabled` read-gates
**G-PROVE receipts**: all grep/read commands issued live against HEAD at `/Users/tomtenuta/Code/a8/repos/autom8y-asana`

---

## Live Receipts

**Receipt 1 — grep for all legacy_fallback_enabled occurrences:**
```
grep -n 'legacy_fallback_enabled' storage.py
334: legacy (gated by legacy_fallback_enabled). Project GID stays the first
352:     legacy_fallback_enabled: bool = True,
364:             legacy_fallback_enabled: SEAM-1 dual-read switch (Decision 2B).
376:     self._legacy_fallback_enabled = legacy_fallback_enabled
983:         ``legacy_fallback_enabled`` so the operator can retire it post-migration.
1010:             if not self._legacy_fallback_enabled:
1195:             if data is None and self._legacy_fallback_enabled:
1291:             if data is None and self._legacy_fallback_enabled:
1372:             if data is None and self._legacy_fallback_enabled:
```
Four runtime gates confirmed at :1010, :1195, :1291, :1372.

**Receipt 2 — GidLookupIndex key shape (from_dataframe / serialize):**
File: `src/autom8_asana/services/gid_lookup.py:292`
Key built as: `"pv1:" + ":".join(parts)` where parts are values of `key_columns` (e.g., `["office_phone", "vertical"]`).
The `"gid"` column value is the MAP VALUE, not part of the key.
The index is keyed on `(phone, vertical)` — NOT on `(project_gid, entity_type, gid)`.
There is no entity_type dimension in the key, and no gid dimension in the key.

**Receipt 3 — Index S3 path keying:**
File: `src/autom8_asana/dataframes/storage.py:422-424`
```python
def _index_key(self, project_gid: str, entity_type: str | None = None) -> str:
    return f"{self._entity_segment(project_gid, entity_type)}/gid_lookup_index.json"
```
Legacy index S3 path: `{prefix}{project_gid}/gid_lookup_index.json` (entity-agnostic)
v2 index S3 path: `{prefix}{project_gid}/{entity_type}/gid_lookup_index.json`

---

## Read-Gate Enumeration Table

| Gate | Method | File:Line | What it reads (v2 first / legacy fallback) | Fallback-row risk | Re-assertion chokepoint? |
|------|---------|-----------|---------------------------------------------|-------------------|--------------------------|
| G-1 | `_load_dataframe_impl` | `storage.py:1010` | v2: `{prefix}{project_gid}/{entity_type}/dataframe.parquet` + watermark; on miss, falls back to legacy `{prefix}{project_gid}/dataframe.parquet` + watermark | A legacy DataFrame is multi-tenant (all entities for a project share one frame). On fallback, any row's gid could belong to a different tenant that happened to be in the same project. | **NO chokepoint exists today.** Gate G-1 (`:1010`) governs whether the fallback fires, but the return value is the raw `(DataFrame, watermark, wm_dict)` tuple. No gid-equality check is performed on any returned row. The caller (`load_dataframe` at `:1096` and `load_dataframe_with_metadata` at `:1118`) pass the tuple straight through. Option E's re-assertion CONTRACT is absent from this gate and its callers. |
| G-2 | `get_watermark` | `storage.py:1195` | v2: `{prefix}{project_gid}/{entity_type}/watermark.json`; on miss, falls back to legacy `{prefix}{project_gid}/watermark.json` | The legacy watermark is entity-agnostic (a single timestamp for all entity types under the project). Serving it on fallback is not a cross-tenant row risk per se — it is a metadata artifact, not a row. | **LOW risk / not a row-serving gate.** A stale or wrong-entity watermark can cause freshness misclassification but does not directly serve a business-gid row to the caller. Option E's gid-re-assertion is not applicable to watermark-only reads. |
| G-3 | `load_index` | `storage.py:1291` | v2: `{prefix}{project_gid}/{entity_type}/gid_lookup_index.json`; on miss, falls back to legacy `{prefix}{project_gid}/gid_lookup_index.json` | The legacy GidLookupIndex maps `pv1:{phone}:{vertical}` -> gid. The index is built from the entity-agnostic (multi-tenant) DataFrame. On fallback, the loaded index can contain gid entries from multiple tenants (any tenant's phone+vertical that existed in the legacy frame). When the GFR engine subsequently looks up a gid via this index, it receives whatever gid the legacy frame stored for that (phone, vertical) key — which could be a cross-tenant gid. | **NO chokepoint exists today.** The fallback index dict is returned raw at `:1297` with zero validation. The caller receives the full multi-tenant mapping. Option E's re-assertion must fire on the gid value resolved from this index, but no such check exists at or downstream of this gate in the current storage layer. |
| G-4 | `load_section` | `storage.py:1372` | v2: `{prefix}{project_gid}/{entity_type}/sections/{section_gid}.parquet`; on miss, falls back to legacy `{prefix}{project_gid}/sections/{section_gid}.parquet` | A legacy section parquet is entity-agnostic. On fallback it can contain rows across entity types (and thus tenants) that share the project partition. | **NO chokepoint exists today.** The fallback bytes are deserialized and returned as a DataFrame at `:1378`. No gid-equality check is performed on any row before returning. Option E's re-assertion CONTRACT is absent from this gate and its callers. |

---

## Index Keying Analysis (Task 2)

**Finding**: The legacy `GidLookupIndex` is keyed on `(office_phone, vertical)` -> gid. The S3 path for the legacy index is `{prefix}{project_gid}/gid_lookup_index.json` — per-project, entity-agnostic (no `entity_type` segment).

This means:
- A single legacy index can contain gid entries for multiple entity types (Business, Lead, etc.) that share the same project_gid.
- More critically: two distinct tenants (two different rows with the same `(office_phone, vertical)` key but different gids) produce a collision in the index — the last writer wins. On index load via fallback (Gate G-3), the caller receives whichever gid survived that collision.
- The index key shape does NOT encode entity_type, so a v2 miss -> legacy fallback serves an entity-agnostic index that cannot be narrowed by entity_type at the storage layer.

**Consequence for Option E**: The re-assertion burden at Gate G-3 is higher than at G-1 or G-4. The caller must (a) retrieve the gid from the loaded index, then (b) assert that gid == the parent-chain-anchored business_gid for the entity being resolved. The storage layer currently performs neither step on fallback.

---

## Coverage Summary

Option E's gid-re-assertion contract (ADR `gfr-seam1-ride-options.md:207-210`) specifies:
> "the served row's gid MUST equal the parent-chain-anchored `business_gid`... If the gids do not match, REJECT the fallback row."

**Gates where fallback CAN serve a row without re-assertion firing:**

| Gate | Can serve a fallback row? | Re-assertion present? | Gap? |
|------|--------------------------|----------------------|------|
| G-1 `_load_dataframe_impl:1010` | YES — returns full DataFrame | NO | GAP |
| G-2 `get_watermark:1195` | Watermark only, not a row | N/A | Not applicable |
| G-3 `load_index:1291` | YES — returns index (gid map) | NO | GAP |
| G-4 `load_section:1372` | YES — returns section DataFrame | NO | GAP |

**Three of four gates (G-1, G-3, G-4) can serve legacy-fallback data (rows or gid mappings) to their callers with zero re-assertion firing.**

---

## Finding: Option E Is Not Built

Option E is ADOPTED (PROPOSED) in the ADR but is NOT implemented in `resolution/gfr/` (confirmed by PV pre-flight: the 9 GFR modules at `autom8y-asana-wt-gfr` do not modify `storage.py`). The re-assertion contract described in the ADR is an unbuilt specification. The storage layer exposes the raw fallback data at all three row-serving gates with no re-assertion hook.

**This is expected** — the engine is at `proven-PENDING` (pre-built). The enumeration below is the input the engine author needs to place the re-assertion correctly.

---

## Structural Observation for 10x-dev (route, do not patch)

For Option E's re-assertion to cover EVERY fallback-served row, it must fire at a chokepoint upstream of the caller that uses the fallback data. There are two architectural options:

**Option E-inline (at the storage layer)**: Add a gid-equality predicate inside `_load_dataframe_impl`, `load_index`, and `load_section` on the fallback branch. This requires the storage layer to know the `target_gid` (the anchored business_gid the GFR engine is resolving for), which currently is not passed in. The storage layer's method signature does not include a `target_gid` parameter — it would need to be added or the check moved to the caller.

**Option E-caller (at the GFR engine layer)**: The GFR engine calls `storage.load_dataframe` / `storage.load_index` / `storage.load_section` and then filters the result. The engine knows the `target_gid`. The re-assertion fires in the engine after the storage call returns, before the row is trusted. This is the lower-coupling approach and matches the ADR's framing ("one check on the miss path" in the engine, not a storage-layer concern).

Either way: **no current chokepoint exists** at which the re-assertion fires automatically. The contract must be built explicitly. All three row-serving gates (G-1, G-3, G-4) bypass re-assertion today.

---

*Artifact authored by SIGNAL-SIFTER, CERT-1 (PT-01), 2026-06-25. Evidence: live grep + Read against HEAD. Write-only to `.ledge/reviews/`; no engine files touched.*

---

## CERT-1-STRONG-EVIDENCE (GAP-1 Vector-A Guard — RED-on-Bypass Proof)

**Appended**: 2026-06-25 by SIGNAL-SIFTER on CERT-1 (GAP-1 Vector-A guard -> STRONG)
**G-PROVE**: all receipts live-issued against worktree `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr`, branch `feat/gfr-engine`, HEAD 70c3e8c6.

---

### Task 1: GFR Unit Suite (Pre-Probe Baseline)

Command: `cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr && ./.venv/bin/python -m pytest tests/unit/resolution/gfr/ -q -p no:cacheprovider`

Result:
```
................................................................................................ [ 100%]
96 passed in 0.36s
```

**96 unit tests GREEN. Baseline confirmed.**

---

### Task 2: RED-on-Bypass Mutation Probe (STRONG-Eligibility Proof)

#### Mutation Applied

File mutated: `src/autom8_asana/resolution/gfr/engine.py:138`

Original (the guard call):
```python
    guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)
```

Bypassed (commented out via python3 in-place rewrite):
```python
    # BYPASS-PROBE: guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)
```

Method: `python3 - <<'PY'` heredoc rewrite using `str.replace` — no `sed -i`, no Edit tool. Ephemeral.

#### RED Transcript

Command: `cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr && ./.venv/bin/python -m pytest tests/unit/resolution/gfr/test_engine.py tests/unit/resolution/gfr/test_guard.py tests/integration/test_gfr_tenant_roundtrip.py -q -p no:cacheprovider`

Result (exit code 1):
```
..FFF.................................F.....                             [100%]
=================================== FAILURES ===================================

FAILED tests/unit/resolution/gfr/test_engine.py::TestEngineOwnedTenantGuard::test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id
  E           Failed: DID NOT RAISE <class 'autom8_asana.resolution.gfr.errors.GuardViolationError'>
  (unfiltered frame with B_WRONG as data[0] passed through; engine would have read G_WRONG company_id silently)

FAILED tests/unit/resolution/gfr/test_engine.py::TestEngineOwnedTenantGuard::test_single_wrong_tenant_row_fires_guard

FAILED tests/unit/resolution/gfr/test_engine.py::TestEngineOwnedTenantGuard::test_row_missing_gid_fires_guard_fail_closed

FAILED tests/integration/test_gfr_tenant_roundtrip.py::TestNegativeCrossTenant::test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame

4 failed, 40 passed in 0.29s
```

**4 tests went RED with the guard bypassed:**
- 3 unit tests in `TestEngineOwnedTenantGuard` — the engine-owned guard tests
- 1 integration sprint-F test — `TestNegativeCrossTenant::test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame`

The key failure surface: `DID NOT RAISE GuardViolationError` — the unfiltered multi-tenant frame (data[0] = wrong tenant's row with gid B_WRONG, company_id G_WRONG) leaked through to the engine's data[0] read path without interception. This is the exact Vector-A cross-tenant leak scenario the guard closes.

#### Restore + GREEN Re-Verification

Command: `git -C /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr checkout -- src/autom8_asana/resolution/gfr/engine.py src/autom8_asana/resolution/gfr/guard.py`

Result: `RESTORED`

Re-run command: `cd /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr && ./.venv/bin/python -m pytest tests/unit/resolution/gfr/test_engine.py tests/unit/resolution/gfr/test_guard.py tests/integration/test_gfr_tenant_roundtrip.py -q -p no:cacheprovider`

Result:
```
............................................                             [100%]
44 passed in 0.20s
```

Clean tree check: `git -C /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr status --porcelain`

Result: `` (empty — clean tree confirmed)

**44 tests GREEN post-restore. Tree is clean.**

---

### Task 3: Guard Structure Confirmation — Every-Row + Fail-Closed

**Location**: `src/autom8_asana/resolution/gfr/guard.py:183-237`
**Call site**: `src/autom8_asana/resolution/gfr/engine.py:138`

**Every-row iteration confirmed** (guard.py:220-222):
```python
for index, row in enumerate(rows):
    row_gid = row.get(_ROW_GID_KEY)
    if row_gid != business_gid:
```
The guard iterates ALL rows in the result set via `enumerate(rows)`. There is no early exit on success of data[0] alone — every subsequent row is checked. A drifted provider returning a frame with 5 rows would have all 5 checked; violation at row 3 raises just as definitively as violation at row 0.

**Fail-closed on missing gid confirmed** (guard.py:221-222):
```python
row_gid = row.get(_ROW_GID_KEY)
if row_gid != business_gid:
```
`row.get(_ROW_GID_KEY)` returns `None` when the key is absent. `None != business_gid` (which is a non-None string) evaluates `True`, triggering `GuardViolationError`. The guard does NOT trust-by-omission: a row with no gid key fails identically to a row with the wrong gid. This is the fail-closed invariant documented in the guard's docstring ("a row missing it cannot be proven to belong to the anchored tenant and is therefore a violation").

**Engine call site** (engine.py:138):
```python
guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)
```
Called immediately after `execute_rows` returns data and BEFORE the engine reads `response.data[0].get("company_id")` at engine.py:146. The guard intercepts the entire response before any field is consumed.

---

### CERT-1 Verdict: STRONG-ELIGIBLE

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Unit suite GREEN pre-probe | PASS | 96 passed |
| Guard call disabled -> leak tests RED | PASS | 4 failed; `DID NOT RAISE GuardViolationError` explicit |
| Restore + suite GREEN post-restore | PASS | 44 passed |
| Clean tree post-restore | PASS | `git status --porcelain` empty |
| Every-row iteration confirmed | PASS | `for index, row in enumerate(rows)` at guard.py:220 |
| Fail-closed on missing gid confirmed | PASS | `row.get(key)` -> None != business_gid fires violation |
| Guard fires BEFORE data[0] read | PASS | engine.py:138 precedes engine.py:146 |

The GAP-1 guard (`assert_rows_tenant_identity`) is STRUCTURALLY NECESSARY and EMPIRICALLY PROVEN by the RED-on-bypass: disabling it allows a cross-tenant frame to be consumed silently. The engine-owned guard is the only layer asserting tenant identity at engine altitude — the substrate filter (`df.filter`) is the substrate's contract, not the engine's, and a drifted provider bypasses it. The guard closes that gap with engine-owned enforcement on every row, fail-closed.

**CERT-1 advances to STRONG.** [STRUCTURAL | STRONG — rite-disjoint critic (signal-sifter) on 10x-dev's engine; RED-on-bypass probe is the proof instrument; CERT-1 is STRONG-eligible per the standing grant and the mutation-probe protocol.]

*CERT-2 and CERT-3 are not re-litigated by this section per G-HALT.*
