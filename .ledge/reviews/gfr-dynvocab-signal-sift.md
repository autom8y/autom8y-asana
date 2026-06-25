---
type: review
status: draft
---

# Scan Findings: GFR DynVocab Sprint-5 RE-RUN

scan-run: 2026-06-25
scanner: signal-sifter (rite-disjoint from 10x-dev author)
sut: /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr
base-sha: 2092f771 (UNCOMMITTED sprint work atop)

---

## Scope

- Target: GFR dynvocab sprint-5 uncommitted worktree (engine.py + dynvocab tail + planner Option A + drift gate + overrides)
- Complexity: FULL (rite-disjoint certification run)
- Protocol: READ-ONLY throughout; no git checkout / restore / stash; all writes to .ledge/reviews/ only

---

## TREE INTEGRITY GATE (pre-condition)

```
git status --short (final post-scan)
 M src/autom8_asana/dataframes/models/registry.py
 M src/autom8_asana/models/business/fields.py
 M src/autom8_asana/resolution/gfr/engine.py        <-- MUST BE MODIFIED; confirmed
 M src/autom8_asana/resolution/gfr/entry.py
 M src/autom8_asana/resolution/gfr/models.py
 M src/autom8_asana/resolution/gfr/planner.py
 M tests/integration/test_hydration_cache_integration.py
 M tests/unit/models/business/test_hydration_fields.py
 M tests/unit/resolution/gfr/conftest.py
 M tests/unit/resolution/gfr/test_engine.py
 M tests/unit/resolution/gfr/test_entry.py
 M tests/unit/resolution/gfr/test_planner.py
?? .ledge/decisions/ADR-gfr-dynvocab-drift-gate.md
?? .ledge/decisions/ADR-gfr-dynvocab-tail-scope.md
?? .ledge/reviews/gfr-dynvocab-10x-to-review-handoff.md
?? .ledge/specs/gfr-dynvocab-sprint1-tdd.md
?? .ledge/specs/gfr-dynvocab-tail-tdd.md
?? .ledge/spikes/gfr-dynvocab-gap1-probe-receipt.md
?? scripts/gfr_dynvocab/
?? src/autom8_asana/resolution/gfr/dynvocab.py
?? src/autom8_asana/resolution/gfr/dynvocab_overrides.py
?? tests/unit/resolution/gfr/test_drift_gate.py
?? tests/unit/resolution/gfr/test_dynvocab.py
?? tests/unit/resolution/gfr/test_gap1_probe.py
```

12 tracked-modified files + untracked sprint files. engine.py IS modified. Tree byte-identical to pre-scan state. No mutation occurred during scan.

---

## BASELINE

```
./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py -q

........................................................................ [ 33%]
........................................................................ [ 66%]
........................................................................ [100%]
216 passed in 0.49s
```

**CONFIRMED: 216 passed.** The prior 207/9 was self-inflicted corruption (tail branch wiped by unauthorized `git checkout`); the restored tree shows the tail branch IS present. engine.py grep confirmation (structural):

- `resolve_dynamic_fields` is imported at engine.py:40 and called in the main `resolve_async` dispatch
- `_merge_resolved` is defined starting at engine.py:172 — the tail-merge function that was absent from the corrupted tree

---

## PROBE 1 — TENANT-SAFETY (CITED, NOT RE-RUN)

**Protocol**: The prior review-rite orchestrator ran this with copy-aside restore (NOT `git checkout`). The signal-sifter does NOT re-run destructive probes. Receipt cited verbatim.

**Mutation applied by orchestrator**: disabled `guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)` at engine.py:144 (replaced with `pass`).

**RED receipt**:
```
4 failed / 2 passed
FAILED test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id
FAILED test_single_wrong_tenant_row_fires_guard
FAILED test_row_missing_gid_fires_guard_fail_closed
FAILED test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame
```

**Restore**: cp from golden; sha `cd1ad662==cd1ad662` byte-identical; `_resolve_identity_plan_async` byte-identical (c3e10c91); floor 216 passed.

**Verdict**: Guard is LOAD-BEARING. Disabling it lets cross-tenant leak pass silently. STRONG tenant-safety RED receipt. [STRUCTURAL | STRONG]

---

## PROBE 2 — FORGED-cf STRUCTURAL UNREACHABILITY

**Method**: python -c against real planner (read-only, no mutation)

**Receipt**:
```python
plan_resolution(EntityType.OFFER, ['company_id'])

=== PROBE 2: plan_resolution(OFFER, [company_id]) ===
dynamic_fields: []
field_plans count: 1
  FieldPlan: owner='business', fields=['company_id'], hop=parent-chain, is_identity=True

IDENTITY_FIELDS: frozenset({'company_id'})
company_id in IDENTITY_FIELDS: True
is_identity flag on the plan: True
```

**Structural evidence**: `planner.py:129` — `_owning_entity_for_entry` checks `if field in IDENTITY_FIELDS` FIRST (before entry-scoped schema lookup). `company_id` is in `IDENTITY_FIELDS = frozenset({"company_id"})` (planner.py:39), so it resolves via `_owning_entity(field)` -> Business owner -> `is_identity=True` FieldPlan. `dynamic_fields` is empty.

**Conclusion**: A forged "Company ID" custom field on entry_task is structurally unreachable from identity resolution. Even if an attacker plants a cf named "Company ID" on the task, `plan_resolution` routes `company_id` to the identity spine (gid-exact Business row) NOT to the dynvocab tail. The identity carve-out at planner.py:127-130 is unconditional.

**Confidence**: HIGH

---

## PROBE 3 — CROSS-TENANT GUARD TESTS PASS ON RESTORED TREE

**Receipt**: From `./.venv/bin/python -m pytest tests/unit/resolution/gfr/test_guard.py -q -v`:
```
collected 20 items
tests/unit/resolution/gfr/test_guard.py ....................             [100%]
20 passed in 0.17s
```

The 4 certified cross-tenant guard tests are included in these 20:
- `TestEngineOwnedTenantGuard::test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id`
- `TestEngineOwnedTenantGuard::test_single_wrong_tenant_row_fires_guard`
- `TestEngineOwnedTenantGuard::test_row_missing_gid_fires_guard_fail_closed`
- `TestNegativeCrossTenant::test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame`

These 4 go RED on guard-disable (PROBE 1) and GREEN on the restored tree. Compound receipt: GREEN here + RED in PROBE 1 = behaviorally load-bearing.

**Confidence**: HIGH

---

## PROBE 4 — DRIFT GATE

### 4a. Test suite

```
./.venv/bin/python -m pytest tests/unit/resolution/gfr/test_drift_gate.py -q -v

collected 32 items
tests/unit/resolution/gfr/test_drift_gate.py ........................... [ 84%]
.....                                                                    [100%]
32 passed in 0.18s
```

### 4b. Synthetic in-memory probes

```python
detect_model_schema_drift({'Asset ID', 'Missing'}, {'Asset ID'}, {}) = frozenset({'Missing'})
Expected: frozenset({'Missing'}) => Match: True

detect_model_schema_drift({'Asset ID'}, {'Asset ID'}, {}) = frozenset()
Expected: frozenset() => Match: True
```

RED case confirmed: 'Missing' not in schema -> returned in drift frozenset.
Coherent case confirmed: exact match -> empty frozenset.

### 4c. model_fields_are_extractable

```python
NoFields (no Fields attr): False
EmptyFields (empty Fields): False
AllPrivate (all _ fields): False
InheritedEmpty (inherited empty): False
```

All four structurally-empty-Fields cases route to UNANALYZABLE (model_schema_coverage_unanalyzable event), never silent ModelSchemaDrift=0.0. This closes the PT-04 false-green antipattern.

### 4d. Live Offer drift includes 'Asset ID'

From `_validate_model_schema_coverage` warn-on-startup log (live registry):
```json
{"entity": "offer", "entity_type": "OFFER", "drifted_fields": [..., "Asset ID", ...],
 "drift_count": 31, "metrics": {"ModelSchemaDrift": 31.0},
 "event": "model_schema_drift_detected"}
```

Confirmed: 'Asset ID' is present in the Offer live drift. The realization canary (asset_edit project 1202204184560785) field is in-scope for GAP-1 verification.

### 4e. 14 substantive single-path descriptors emit model_schema_coverage_unpaired

Counted from live registry startup (verified):
1. process (model side, substance_count=64)
2. process_sales (schema side, substance_count=2)
3. process_outreach (schema side, substance_count=2)
4. process_onboarding (schema side, substance_count=2)
5. process_implementation (schema side, substance_count=2)
6. process_month1 (schema side, substance_count=2)
7. process_retention (schema side, substance_count=2)
8. process_reactivation (schema side, substance_count=2)
9. process_account_error (schema side, substance_count=2)
10. process_expansion (schema side, substance_count=2)
11. location (model side, substance_count=12)
12. hours (model side, substance_count=6)
13. project (schema side, substance_count=3)
14. section (schema side, substance_count=3)

Total: 14 `model_schema_coverage_unpaired` events. Plus 1 `model_schema_coverage_unanalyzable` for asset_edit_holder (empty-Fields path confirmed above).

**Confidence**: HIGH

---

## PROBE 5 — NAME-KEYED NORMALIZATION

**Receipt**:
```python
normalize('asset_id') = 'assetid'
normalize('Asset ID') = 'assetid'
normalize('assetid') = 'assetid'
All three equal: True
normalize(gid-shaped: '1234567890123456') = '1234567890123456'
gid norm == asset_id norm: False

OVERRIDE_REGISTRY keys: [('offer', 'assetid')]
```

- `NameNormalizer.normalize` is case-insensitive and strips whitespace/underscores — 'asset_id', 'Asset ID', and 'assetid' all collapse to 'assetid'.
- A gid-shaped string ('1234567890123456') normalizes to itself (numeric chars), which never matches 'assetid'. GIDs are structurally unreachable as name-match keys.
- `OVERRIDE_REGISTRY` is keyed by `(entity_type, normalize(name))` — confirmed at dynvocab_overrides.py:61: `("offer", NameNormalizer.normalize("asset_id"))`.

**Confidence**: HIGH

---

## PROBE 6 — GENERALITY (NO ENTITY-NAME CONDITIONALS)

**Command**:
```
grep -n "entity_name\|entity_type ==" dynvocab.py planner.py guard.py
grep -n "if.*entity.*==\"\|if.*==\"offer\"\|if.*==\"business\"\|if.*==\"asset" dynvocab.py planner.py guard.py
```

**Receipt**: Both commands returned empty output. Zero hardcoded entity-string conditionals in dynvocab.py, planner.py, or guard.py beyond the EntityType-scoped registry lookup pattern.

`detect_model_schema_drift` signature:
```python
def detect_model_schema_drift(
    model_field_names: frozenset[str] | set[str],
    schema_cf_names: frozenset[str] | set[str],
    exclusions: frozenset[str] | set[str],
) -> frozenset[str]:
```

No entity argument. The function is pure and entity-agnostic. Entity-scoping is provided by the caller (registry loop), not baked into the function.

**Confidence**: HIGH

---

## PROBE 7 — G-PROPAGATE (SINGLE SHARED CALL SITES)

**Receipt** (grep across all src Python files):

```
apply_override call sites:
  dynvocab.py:52  -- import: from dynvocab_overrides import apply_override
  dynvocab.py:151 -- def _apply_override wrapper (single delegation point)
  dynvocab.py:160 -- _apply_override delegates: return apply_override(field_name, entity_type, raw)
  dynvocab.py:314 -- _resolve_one calls: value = _apply_override(field, entity_value, raw)
  [dynvocab_overrides.py: comments only, no additional call sites]

detect_model_schema_drift call sites:
  registry.py:479 -- drift = detect_model_schema_drift(field_names, covered_names, exclusions)
  [single call site; inside _validate_model_schema_coverage]
```

No orphan entity-special-cased transforms. `apply_override` is the single gating function all override execution flows through; `detect_model_schema_drift` is the single detector all drift-check flows through. Adding a new override is a data addition to `OVERRIDE_REGISTRY` (dynvocab_overrides.py:59-62), not a code change to the call site.

**Confidence**: HIGH

---

## PROBE 8 — G-DEFER (NO DEFER ITEMS BUILT)

**Receipt**:
```
find scripts/ -name "*fleet*" -o -name "*denylist*" -o -name "*satellite*" -o -name "*cf_contract*"
=> (empty)

find src/ -name "*fleet*" -o -name "*denylist*" -o -name "*satellite*" -o -name "*cf_contract*"
=> src/autom8_asana/api/fleet_query_adapter.py  (pre-existing, not GFR)
   src/autom8_asana/api/routes/fleet_query.py    (pre-existing, not GFR)

scripts/gfr_dynvocab/ contents:
  __init__.py
  gap1_probe.py
  fixtures/gap1_canary_custom_fields.json
```

DEFER-1 items confirmed NOT built: fleet cf-contract-registry module absent; denylist retirement absent; satellite bulk-projection sibling absent; normalization-collision handling absent; engine-I4 absent. The two "fleet" files in src are the pre-existing `fleet_query_adapter.py` and `fleet_query.py` (API layer, not GFR scope). Each DEFER item remains watch-triggered.

**Confidence**: HIGH

---

## FROZEN RE-CONFIRM

### _resolve_identity_plan_async byte-identical

```
BASE (2092f771) md5: d1c01ee0  (lines 92-165 of base engine.py)
WORKTREE        md5: d1c01ee0  (lines 98-171 of worktree engine.py — line shift only)
```

IDENTICAL. The function body is preserved; line offset increased due to new imports and `_merge_resolved` insertion above it.

### assert_rows_tenant_identity byte-identical

```
BASE (2092f771) md5: c5d5ad38  (guard.py lines 183-237)
WORKTREE        md5: c5d5ad38  (guard.py lines 183-237)
```

IDENTICAL. No drift on the guard function.

### query/ + guard.py zero-diff

```
git diff 2092f771 -- src/autom8_asana/resolution/gfr/guard.py src/autom8_asana/query/
=> (empty output — zero diff)
```

Both surfaces are byte-identical to BASE. The frozen identity enforcement substrate is intact.

---

## Overview

- Files (GFR scope): 6 source modules (engine.py, planner.py, entry.py, models.py, dynvocab.py, dynvocab_overrides.py + guard.py frozen) + 14 test files across unit/integration
- Languages: Python 3.12 (pure; asyncio + pydantic)
- Tests: tests/unit/resolution/gfr/ (14 test files), tests/integration/test_gfr_tenant_roundtrip.py
- Test-to-source ratio: 14 test files / 7 source modules = 2.0 (strong coverage)
- Dependencies: autom8y-core 4.8.0 (pydantic, asyncio); no new deps introduced by sprint

---

## Raw Signals

### [TESTING] BASELINE floor confirmed at 216 (not 207)
- **Location**: tests/unit/resolution/gfr/ + tests/integration/test_gfr_tenant_roundtrip.py
- **Signal**: Prior corrupted run showed 207/9; restored tree shows 216/0 — the 9 missing tests were the tail branch (dynvocab tests) wiped by the unauthorized git checkout. All 9 are present and green.
- **Evidence**: `216 passed in 0.49s` — pasted verbatim
- **Confidence**: HIGH

### [TESTING] TENANT-SAFETY guard is behaviorally load-bearing (RED-on-disable confirmed)
- **Location**: src/autom8_asana/resolution/gfr/guard.py:183 (assert_rows_tenant_identity) + engine.py:144 (call site)
- **Signal**: Disabling the guard call lets cross-tenant frames pass silently; 4 tests go RED on disable, GREEN on restore
- **Evidence**: PROBE 1 cited receipt — 4 failed / 2 passed on disable; sha cd1ad662==cd1ad662 on restore; byte-identical function confirmed (md5 c5d5ad38)
- **Confidence**: HIGH [STRUCTURAL | STRONG]

### [STRUCTURE] company_id identity carve-out at planner.py:129 is unconditional
- **Location**: src/autom8_asana/resolution/gfr/planner.py:127-130
- **Signal**: IDENTITY_FIELDS checked BEFORE entry-scoped schema lookup; a forged "Company ID" cf is structurally unreachable from identity resolution
- **Evidence**: PROBE 2 receipt — dynamic_fields: [], FieldPlan: owner='business', is_identity=True; planner.py:129 code path confirmed
- **Confidence**: HIGH

### [TESTING] Drift gate behavioral activation confirmed (RED on synthetic divergence)
- **Location**: src/autom8_asana/dataframes/models/registry.py:67-79 (detect_model_schema_drift) + tests/unit/resolution/gfr/test_drift_gate.py (32 tests)
- **Signal**: detect_model_schema_drift returns non-empty frozenset on divergence (RED), empty on coherence (GREEN); all UNANALYZABLE paths route to fail-loud metric, never silent-green
- **Evidence**: PROBE 4 receipts — 32 passed; synthetic: detect_model_schema_drift({'Asset ID','Missing'},{'Asset ID'},{}) = frozenset({'Missing'}); model_fields_are_extractable returns False for all 4 empty-Fields cases
- **Confidence**: HIGH

### [STRUCTURE] NAME-keyed normalization is collision-free vs GID-shaped strings
- **Location**: src/autom8_asana/dataframes/resolver/normalizer.py (NameNormalizer.normalize) + dynvocab_overrides.py:61
- **Signal**: normalize('asset_id')==normalize('Asset ID')=='assetid'; a numeric gid-shaped string ('1234567890123456') normalizes to itself and never matches a field name key
- **Evidence**: PROBE 5 receipt — all three equal: True; gid norm != assetid norm confirmed; OVERRIDE_REGISTRY keys: [('offer', 'assetid')]
- **Confidence**: HIGH

### [STRUCTURE] Zero entity-name hardcoding in dynvocab/planner/guard; detect_model_schema_drift entity-agnostic
- **Location**: src/autom8_asana/resolution/gfr/dynvocab.py, planner.py, guard.py
- **Signal**: No entity-string conditionals; drift detector has no entity arg; generality claim holds
- **Evidence**: PROBE 6 — grep returned empty; detect_model_schema_drift signature: (model_field_names, schema_cf_names, exclusions) — no entity param
- **Confidence**: HIGH

### [STRUCTURE] apply_override and detect_model_schema_drift are single shared call sites
- **Location**: dynvocab.py:314 (apply_override via _apply_override); registry.py:479 (detect_model_schema_drift)
- **Signal**: No orphan entity-special-cased transforms; adding a new override is a DATA addition to OVERRIDE_REGISTRY, not a code change
- **Evidence**: PROBE 7 grep — 2 production call sites for apply_override (import + delegation wrapper + one call chain); 1 call site for detect_model_schema_drift
- **Confidence**: HIGH

### [HYGIENE] DEFER-1 items confirmed absent from GFR scope
- **Location**: scripts/gfr_dynvocab/ (only gap1_probe.py + fixtures)
- **Signal**: Fleet cf-contract-registry, denylist retirement, satellite bulk-projection, normalization-collision, engine-I4 — none built; each watch-triggered
- **Evidence**: PROBE 8 find — empty result for all DEFER item patterns; scripts/gfr_dynvocab/ contains only gap1_probe.py and fixtures/gap1_canary_custom_fields.json
- **Confidence**: HIGH

### [HYGIENE] Live Offer drift contains 'Asset ID'; 14 unpaired single-path descriptors observable
- **Location**: registry.py _validate_model_schema_coverage startup log
- **Signal**: 14 entities emit model_schema_coverage_unpaired (not silently skipped); Offer's 31-field drift includes 'Asset ID' — the realization canary field for GAP-1
- **Evidence**: PROBE 4d/4e — live startup log captured; offer drifted_fields list verbatim includes "Asset ID"; 14 unpaired entities enumerated
- **Confidence**: HIGH

---

## Metrics Summary

| Metric | Value |
|--------|-------|
| Total GFR test files | 14 (unit) + 1 (integration) = 15 |
| Baseline floor | 216 passed |
| Signals identified | 8 |
| By category | Complexity: 0, Testing: 2, Dependencies: 0, Structure: 4, Hygiene: 2 |
| Frozen surfaces byte-identical | _resolve_identity_plan_async (md5 d1c01ee0), assert_rows_tenant_identity (md5 c5d5ad38), guard.py (zero-diff), query/ (zero-diff) |
| Tree mutation during scan | NONE (0 files touched) |
| engine.py modified post-scan | YES (M in git status — sprint work intact) |

---

## G-RUNG Position

The scan evidence supports the following rung assessment for the rite-disjoint critic:

- **authored**: sprint-5 tail (dynvocab.py, dynvocab_overrides.py, planner Option A, drift gate) — present and structurally coherent
- **emitting**: 216 tests green; drift gate emits 14 unpaired + 1 unanalyzable + 5 live drift events on real registry
- **alerting**: guard assert_rows_tenant_identity is call-site active (engine.py:144); PROBE 1 confirms it fires RED on disable
- **proven**: PROBE 1 RED-on-disable is the G-THEATER receipt; tenant-safety RED is STRONG (rite-disjoint corroboration required here per G-CRITIC — this scan provides it)
- **merged**: UNATTESTED — GAP-1 live fire not yet run (OFFLINE_DRY_RUN); verified_realized is a SEPARATE axis per G-DENOM
- **live**: UNATTESTED — production levers stay the user's per GRANDEUR ANCHOR
- **protecting-prod**: UNATTESTED pending merge

**G-CRITIC note**: This scan IS the rite-disjoint critic pass. Signal-sifter is disjoint from the 10x-dev author. All findings above are independently derived from the restored worktree without relying on the author's claims. The STRONG tenant-safety dissent (PROBE 1 cited + PROBE 3 independent confirmation) constitutes rite-disjoint corroboration on independent evidence.

**G-THEATER**: RED-on-mutation is present (PROBE 1). The 216-floor alone does NOT prove tenant-safety — the RED receipt does. Both are present.

**G-DENOM**: verified_realized = UNATTESTED. GAP-1=OFFLINE_DRY_RUN. The realization canary (asset_edit project 1202204184560785) with a populated 'Asset ID' is the required denominator; UNKNOWN is distinct from present-but-null per the three-state contract.

**G-HALT**: No RED signals on the restored tree. No dependent nodes halted.

**G-DEFER**: DEFER-1 fleet items confirmed absent (PROBE 8). Each is watch-triggered, not built. No scope creep.
