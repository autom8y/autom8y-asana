---
type: review
artifact_class: rite-disjoint-critic-verdict
initiative: gfr-dynvocab
status: accepted
run: 2026-06-25
critic: case-reporter (rite-disjoint from 10x-dev author; sprint-5 RE-RUN — prior run invalidated)
upstream_scan: .ledge/reviews/gfr-dynvocab-signal-sift.md
upstream_assess: .ledge/reviews/gfr-dynvocab-severity-profile.md
upstream_handoff: .ledge/reviews/gfr-dynvocab-10x-to-review-handoff.md
g_rung: proven / disjoint-attested
overall_verdict: STRONG
cross_stream_concurrence: true
verified_realized: UNATTESTED (GAP-1=OFFLINE_DRY_RUN; telos deadline 2026-07-23)
self_grade_ceiling: MODERATE (self-ref rule; STRONG verdicts rest on rite-disjoint RED evidence, not author self-assessment)
---

# GFR DynVocab Sprint-5 — Rite-Disjoint Critic Verdict (RE-RUN)

**Critic stance:** Rite-disjoint, independently derived from scan + assessment artifacts. Default skeptical. Self caps MODERATE per G-CRITIC; STRONG verdicts issued where independent RED-on-mutation evidence is present.

**Date:** 2026-06-25 | **SUT:** `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr` | **Base SHA:** `2092f771` (UNCOMMITTED sprint work atop)

---

## VERDICT: STRONG — DO NOT ROUTE BACK

Both binding verdicts are grounded in independent rite-disjoint evidence. `cross_stream_concurrence` flips **true**. The ONE additive PR is merge-eligible (operator lever). Production levers stay the user's.

---

## Process-Integrity Note (for the record)

The FIRST sprint-5 run (prior agent) self-corrupted the SUT via `git checkout -- engine.py` on uncommitted working-tree sprint code. This destroyed the dynvocab tail branch in place, producing a corrupted baseline of 207 passed / 9 failed. The prior agent then mis-issued a ROUTE-BACK on a phantom "missing tail dispatch" finding — a finding that existed only because the unauthorized checkout had wiped the tail. The tree was recovered (worktree floor confirmed at 216 on the restored working tree). This document is the clean re-run on the intact SUT.

**The prior ROUTE-BACK verdict is invalid.** It was issued against a SUT that the reviewing agent had itself corrupted. It does not constitute evidence of a real defect. No findings from the prior run are carried forward.

---

## Health Report Card

| Dimension | Grade | Decisive Finding |
|-----------|-------|-----------------|
| Tail Contract | A | Three-state PRESENT / PRESENT_BUT_NULL / ABSENT implemented; governed-strict unknown-field on absence; all-or-nothing I4 via `_merge_resolved` disjointness assert; 216-floor includes tail suite |
| Planner Partition | A | Identity carve-out unconditionally first at `planner.py:129`; PROBE 2 confirms forged-Company-ID cf structurally unreachable from identity spine; `dynamic_fields=[]` for `company_id` |
| Override | A | `OVERRIDE_REGISTRY ('offer','assetid')` — single call chain `dynvocab.py:160→314`; `normalize()` collision-free vs GID-shaped strings (PROBE 5); typing_origin mis-stamp defect found and fixed by author |
| Drift Gate | A | `detect_model_schema_drift` pure entity-agnostic function; single call site `registry.py:479`; PT-04 TERMINATING — all empty-extraction paths → UNANALYZABLE, never silent green (PROBE 4c); 'Asset ID' in live Offer `drift_count=31` |
| Frozen Integrity | A | `_resolve_identity_plan_async` md5 `d1c01ee0` BASE==WORKTREE; `assert_rows_tenant_identity` md5 `c5d5ad38` BASE==WORKTREE; `guard.py` + `query/` zero-diff vs `2092f771`; PROBE 1 RED confirms guard is load-bearing |
| Generality | A | Zero entity-name hardcoding in `dynvocab.py` / `planner.py` / `guard.py` (PROBE 6 grep empty); `detect_model_schema_drift` carries no entity arg; ≥3 EntityTypes auto-covered through descriptor registry |
| **Overall** | **A** | Median A; no category below A; weakest-link model produces A; no floor-drag |

---

## GREEN / RED Matrix

### GREEN — confirmed by independent evidence

| # | Claim | Decisive Receipt | Rung |
|---|-------|-----------------|------|
| G1 | Floor 216 confirmed on restored tree | `./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py -q` → **216 passed in 0.49s**. Prior 207/9 was self-inflicted corruption by unauthorized `git checkout`. | emitting |
| G2 | `assert_rows_tenant_identity` is behaviorally load-bearing (PROBE 1 RED) | Mutation: disabled `guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)` at `engine.py:144` (replaced with `pass`). **4 FAILED:** `test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id`, `test_single_wrong_tenant_row_fires_guard`, `test_row_missing_gid_fires_guard_fail_closed`, `test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame`. Restore: cp from golden; sha `cd1ad662==cd1ad662` byte-identical; floor 216 passed. G-THEATER: RED-on-mutation IS present. The 216-floor alone does NOT prove tenant-safety. Both are present. | alerting → **proven** |
| G3 | company_id identity carve-out is unconditional (PROBE 2 structural) | `plan_resolution(EntityType.OFFER, ['company_id'])` → `dynamic_fields: []`, `FieldPlan: owner='business', is_identity=True`. `planner.py:129` `if field in IDENTITY_FIELDS` fires FIRST before entry-scoped schema lookup. A forged "Company ID" cf on entry_task is structurally unreachable from identity resolution — `company_id` routes to the identity spine (gid-exact Business row), not the dynvocab tail. | structural (corroborates proven) |
| G4 | 20/20 cross-tenant guard tests GREEN on restored tree (PROBE 3) | `./.venv/bin/python -m pytest tests/unit/resolution/gfr/test_guard.py -q -v` → **20 passed in 0.17s**. The 4 certified cross-tenant tests are included: `TestEngineOwnedTenantGuard::test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id`, `test_single_wrong_tenant_row_fires_guard`, `test_row_missing_gid_fires_guard_fail_closed`, `TestNegativeCrossTenant::test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame`. Compound with PROBE 1 RED → behaviorally load-bearing independently confirmed. | corroborates proven |
| G5 | Frozen surfaces byte-identical (PROBE 1 restore + SCAN re-confirm) | `_resolve_identity_plan_async` md5 `d1c01ee0` BASE==WORKTREE (line shift only — new imports + `_merge_resolved` insertion above). `assert_rows_tenant_identity` md5 `c5d5ad38` BASE==WORKTREE. `guard.py` + `query/` zero-diff vs `2092f771`. Certified guard function is byte-identical on the dynvocab worktree. | structural (corroborates proven) |
| G6 | Drift gate fires RED on synthetic divergence; PT-04 TERMINATING (PROBE 4b/4c) | `detect_model_schema_drift({'Asset ID','Missing'},{'Asset ID'},{})` = `frozenset({'Missing'})` — RED confirmed. Coherent case: `detect_model_schema_drift({'Asset ID'},{'Asset ID'},{})` = `frozenset()` — GREEN. All four empty-Fields cases (NoFields, EmptyFields, AllPrivate, InheritedEmpty) → `model_fields_are_extractable()` returns `False` → UNANALYZABLE, never silent `ModelSchemaDrift=0.0`. PT-04 false-green antipattern is CLOSED. | alerting (drift gate) |
| G7 | 'Asset ID' in live Offer drift; 14 substantive unpaired entities (PROBE 4d/4e) | Live startup log: `{"entity":"offer","drift_count":31,"drifted_fields":[...,"Asset ID",...]}`. 14 entities emit `model_schema_coverage_unpaired` (enumerated: process x10, location, hours, project, section). 1 `model_schema_coverage_unanalyzable` (asset_edit_holder). None collapse into silent green. Realization canary field 'Asset ID' is in-scope for GAP-1 verification. | emitting (drift gate) |
| G8 | Zero entity-name hardcoding; `detect_model_schema_drift` entity-agnostic (PROBE 6) | `grep -n "entity_name\|entity_type ==" dynvocab.py planner.py guard.py` → empty. `grep -n "if.*entity.*==\"\|if.*==\"offer\"..."` → empty. Signature: `def detect_model_schema_drift(model_field_names, schema_cf_names, exclusions)` — no entity arg. Entity-scoping provided by caller (registry loop), not baked into the function. | structural (generality) |
| G9 | Single shared call sites for critical functions (PROBE 7) | `apply_override`: one call chain — `dynvocab.py:52` (import) → `dynvocab.py:151` (wrapper def) → `dynvocab.py:160` (delegation) → `dynvocab.py:314` (production call). `detect_model_schema_drift`: single call site `registry.py:479` inside `_validate_model_schema_coverage`. Adding a new override is a DATA addition to `OVERRIDE_REGISTRY`, not a code change. | structural (propagation integrity) |
| G10 | DEFER-1 items confirmed NOT built (PROBE 8) | `find scripts/ -name "*fleet*" -o -name "*denylist*" -o -name "*satellite*" -o -name "*cf_contract*"` → empty. `find src/ ...` → only pre-existing `fleet_query_adapter.py` and `fleet_query.py` (API layer, not GFR scope). `scripts/gfr_dynvocab/` contains only `gap1_probe.py` + `fixtures/gap1_canary_custom_fields.json`. Each DEFER item remains watch-triggered, not built. Scope-collapse discipline correctly applied. | structural (defer hygiene) |

### RED — flags against the assessment

None. All claims in the severity profile are independently confirmed by this critic. No probe that should have gone RED failed to do so. No coverage gaps require re-scan. The scan applied no false positives.

---

## The Two Binding Verdicts

### Verdict (a) — DYNVOCAB TENANT-SAFETY: STRONG [STRUCTURAL | STRONG]

**Claim:** The dynvocab tail is strictly additive to the STRONG-certified identity spine. The cross-tenant guard (`assert_rows_tenant_identity`) remains behaviorally load-bearing. A forged "Company ID" custom field on `entry_task` cannot supplant the gid-exact Business read.

**Decisive RED receipt (PROBE 1, orchestrator-owned, cited — not re-run per crime-scene protocol):**

```
Mutation: assert_rows_tenant_identity(response.data, anchor.business_gid) at engine.py:144 → pass

4 FAILED:
  FAILED test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id
  FAILED test_single_wrong_tenant_row_fires_guard
  FAILED test_row_missing_gid_fires_guard_fail_closed
  FAILED test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame

Restore: cp from golden; sha cd1ad662==cd1ad662 byte-identical; 216 passed.
```

**Independent corroboration from this rite-disjoint critic (independently derived):**

- PROBE 2 structural: `planner.py:129` `if field in IDENTITY_FIELDS` fires unconditionally FIRST. `dynamic_fields=[]` for `company_id`. A forged "Company ID" cf on `entry_task` → `company_id` hits the `IDENTITY_FIELDS` carve-out before the entry-scoped predicate → `is_identity=True` FieldPlan → identity spine, never the tail.
- PROBE 3 compound: 20/20 cross-tenant guard tests GREEN on restored tree. GREEN here + RED on disable (PROBE 1) = behaviorally load-bearing confirmed by independent means.
- Frozen surfaces independently confirmed: `assert_rows_tenant_identity` md5 `c5d5ad38` BASE==WORKTREE; `guard.py` zero-diff vs `2092f771`. The certified guard function is byte-identical on the dynvocab worktree.
- Structural disjointness: the dynvocab tail operates exclusively on `dynamic_fields` (`is_identity=False` FieldPlans are never constructed for identity fields). The guard operates on identity reads. These surfaces are structurally disjoint by construction — the tail cannot touch the guard path.

**G-THEATER:** RED-on-mutation IS present (PROBE 1). The 216-floor alone does NOT prove tenant-safety. Both are present: the floor proves no regression; the RED receipt proves the guard is load-bearing.

**Evidence grade: STRONG** — rite-disjoint RED-on-mutation receipt (PROBE 1, orchestrator-owned) + independent structural corroboration (PROBE 2 + PROBE 3 + frozen-surface confirmation). No single-layer failure of any one barrier creates a cross-tenant leak (defense-in-depth: IDENTITY_FIELDS carve-out first, is_identity=False tail invisible to guard, guard call behaviorally active at engine.py:144).

**Rung: proven / disjoint-attested.**

---

### Verdict (b) — MOONSHOT FUTURE-4 COHERENCE DISSENT: STRONG CONCURRENCE [STRUCTURAL | STRONG]

**Claim:** (1) The per-repo model↔schema drift gate (Option A, `ADR-gfr-dynvocab-drift-gate`) is the correct IN-SCOPE receiver-side prevention mechanism. (2) The DEFER-1 fleet cf-contract registry (S4a FIRED) is the correct ESCALATE-ONLY one-way-door — not designed or built here, which is correct.

**Independent evidence from this rite-disjoint critic:**

*Option A correctness as receiver-side prevention:*
- PROBE 6: `detect_model_schema_drift` carries no entity arg — signature `(model_field_names, schema_cf_names, exclusions) -> frozenset[str]`. Pure comparator; entity-scoping is caller-side (registry loop). Adding a new entity is a descriptor registration, not a gate code change.
- PROBE 7: single call site `registry.py:479`. No orphan entity-special-cased transforms anywhere in the codebase.
- PROBE 4b synthetic RED: `detect_model_schema_drift({'Asset ID','Missing'},{'Asset ID'},{})` = `frozenset({'Missing'})`. RED confirmed on synthetic divergence.
- PROBE 4c PT-04 TERMINATING: all four empty-Fields cases (NoFields, EmptyFields, AllPrivate, InheritedEmpty) → UNANALYZABLE, never silent `ModelSchemaDrift=0.0`. The false-green antipattern is structurally closed.
- PROBE 4d live: 'Asset ID' in Offer `drift_count=31` — the gate is detecting real production drift at import time.
- PROBE 4e: 14 substantive single-path descriptors emit `model_schema_coverage_unpaired` (not silently skipped). 1 UNANALYZABLE (asset_edit_holder). None collapse into a silent green at any altitude.
- ADR-S4-001 honored: the drift-gate ADR explicitly records "gate that DETECTS, not codegen." The gate is read-only; remediation is a human edit.

*DEFER-1 correctness as ESCALATE-ONLY one-way-door:*
- PROBE 8: find returned empty for all DEFER-1 patterns. `scripts/gfr_dynvocab/` contains only `gap1_probe.py` + fixtures. DEFER-1 is confirmed NOT built.
- ADR §S4a escalation flag: S4a FIRED (autom8 `KeyError: 'asset_id'` at `apis/asana_api/objects/project/models/paid_content/main.py:70`; satellite `_CONTRACT_COLUMNS=("office_phone","vertical","gid")` at `getdf_signals.py:77` drops `asset_id` with structural false-green canary). Trigger documented and escalated — correctly NOT actioned inside this initiative.
- The fleet registry is a one-way door (fleet-level API commitment; multiple services bind it). Designing it inside a single 10x-dev session would be the DEFER→SHIP scope collapse. The ADR records the boundary and stops. This is correct architectural discipline per the GRANDEUR ANCHOR.

**Evidence grade: STRONG CONCURRENCE** — this critic independently confirms: Option A is the correct receiver-side gate with no silent false-green at any altitude; DEFER-1 is the correct one-way-door escalation path and it is correctly not built; S4a is FIRED and flagged for operator/strategy, not for this initiative.

**Rung: proven / disjoint-attested (drift gate attested; fleet DEFER confirmed absent).**

---

## Realization-Rung Ledger

| Rung | Status | Authority | Decisive Receipt |
|------|--------|-----------|-----------------|
| authored | RATIFIED | 10x-dev (self) | 216-floor confirms all modules compile and execute; 12 tracked files + 5 new modules structurally present in worktree |
| emitting | RATIFIED | This critic (rite-disjoint) | 14 unpaired + 1 unanalyzable + 5 live Offer drift events at import time; 216 tests cover the tail suite; guard call site active at `engine.py:144` |
| alerting | RATIFIED | This critic (rite-disjoint) | `engine.py:144` call site active; PROBE 1 confirms fires RED on disable; guard is not a dead letter; `model_schema_drift_detected` warn emits on startup |
| **proven / disjoint-attested** | **ATTESTED** | This critic (rite-disjoint, RE-RUN) | PROBE 1 RED-on-mutation (orchestrator receipt, cited) + PROBE 2 structural + PROBE 3 independent corroboration = rite-disjoint corroboration on independent evidence [STRUCTURAL | STRONG] |
| merged | UNATTESTED | Operator (MINE) | Production lever stays the user's; `cross_stream_concurrence=true` makes PR merge-eligible at operator discretion |
| live | UNATTESTED | Operator (MINE) | Merge prerequisite not met |
| protecting-prod | UNATTESTED | Operator (MINE) | Downstream of live |

**Rung named: proven / disjoint-attested.**

**verified_realized: UNATTESTED** — GAP-1=OFFLINE_DRY_RUN. This is a SEPARATE axis from the proven rung per G-DENOM. The realization canary (positively-selected real entity with populated Asset ID, asset_edit project `1202204184560785`) has not been fired live. UNKNOWN is distinct from present-but-null (three-state contract). Telos deadline: **2026-07-23**. Probe harness is structurally present at `scripts/gfr_dynvocab/gap1_probe.py`; schema-side confirmed ('Asset ID' in live Offer `drift_count=31`).

---

## DEFER Watch-Register

| DEFER Item | Status | Trigger | Disposition |
|------------|--------|---------|-------------|
| DEFER-1 fleet cf-contract registry | NOT BUILT — S4a FIRED | 2nd production consumer (autom8 `KeyError: 'asset_id'` at `apis/asana_api/objects/project/models/paid_content/main.py:70`) confirms cross-service drift class | ESCALATE-ONLY to operator/strategy. Fleet-level API commitment; one-way door. NOT designed or built in this initiative. Scope-collapse discipline correctly applied. |
| Denylist retirement (`SATELLITE_GET_DF_GID_DENYLIST`) | NOT BUILT | Monolith unblock carry-item | Cross-service; out of GFR scope. Watch: retire once modern satellite arm carries the cfs. |
| Satellite bulk-projection widening (`PROJECT_CONTRACT_COLUMNS`) | NOT BUILT | DISTINCT receiver-side surface | Not delivered by gfr-dynvocab as scoped. Drift-gate signal should drive as sibling task. |
| Normalization-collision shadow | NOT BUILT — design required | Future sprint adding cf metadata | Design-before-patch discipline. `dynvocab.py _build_manifest` first-match-wins inherited from `default.py`. No live collision documented. |
| Engine I4 — own-schema non-identity terminal | NOT BUILT — pre-existing | Enrichment-reads rung | `office_phone` on Offer → no-identity-path, harden-on-touch per ADR-gfr-dynvocab-tail-scope. Out of scope for this sprint. |

**Confirmation: none of the five DEFER items were built.** Each is watch-triggered. No scope creep.

---

## Low Findings (inherited verbatim from pattern-profiler; no re-grading)

No Critical, High, or Medium findings. Three Low / informational items:

| ID | Location | Description | Routing |
|----|----------|-------------|---------|
| LOW-1 | `registry.py:158-166` (try/except wrapper) | Drift-gate error-mode raise is swallowed by `_ensure_initialized` try/except. Error mode (`GFR_DRIFT_GATE_MODE=error`) requires direct CI invocation outside the wrapper to realize build-break semantics. ADR-disclosed caveat; warn mode (shipped default) is correct. | 10x-dev (future sprint, promotion path) |
| LOW-2 | `dynvocab.py _build_manifest` (first-match-wins) | Normalization-collision shadow — if two custom fields normalize to the same key, first-match-wins silently wins. No live instance documented. Design required before reactive patch. | 10x-dev (design-before-patch per handoff) |
| LOW-3 | `registry.py _validate_model_schema_coverage` (PROBE 4e) | 14 substantive single-path descriptors emit `model_schema_coverage_unpaired` at startup. Pre-existing gaps, not drift introduced by this sprint. Observable (warn-first, metric-alarmable), not silent. | 10x-dev (drift-drain pass, operator-scheduled) |

---

## Cross-Rite Routing

| Concern | Recommended Rite | Action |
|---------|-----------------|--------|
| **STRONG — merge-eligible (operator lever)** | Operator | `cross_stream_concurrence=true`; the ONE additive PR is merge-eligible at operator discretion. Production levers stay the user's. |
| GAP-1 live fire (verified_realized gate) | Operator-gated (MINE) | Fire `scripts/gfr_dynvocab/gap1_probe.py` against a POPULATED Asset ID on asset_edit project `1202204184560785`. G-DENOM: UNKNOWN (no matching canary found) is distinct from present-but-null (canary found, field empty). Telos deadline: 2026-07-23. |
| DEFER-1 fleet cf-contract registry (S4a FIRED) | Operator / strategy | Second production consumer confirms cross-service drift class. Fleet-level one-way-door commitment requires operator sign-off before design begins. |
| Normalization-collision shadow | 10x-dev (future sprint) | Design a collision-detection strategy before the sprint that adds cf metadata. Reactive patch is wrong approach. |
| Drift-drain pass (14 unpaired + Offer 31-field drift) | 10x-dev (operator-scheduled) | Add schema columns or register explicit exclusions for known-accepted single-path descriptors. Drift is now observable via `model_schema_drift_detected` warn. |
| Drift-gate error-mode promotion | 10x-dev (future sprint) | When operator promotes to error mode, add a direct CI invocation of `detect_model_schema_drift` outside the `_ensure_initialized` try/except wrapper to realize build-break semantics. |
| Denylist retirement + satellite bulk-projection | Operator-coordinated | Cross-service carry-items. Explicit operator scheduling required. Not in GFR scope. |

---

## Recommended Next Steps

Prioritized by impact-to-effort ratio:

1. **[Operator / merge lever] Merge the additive PR.** `cross_stream_concurrence=true` on STRONG attestation. The ONE additive PR is merge-eligible. Production levers stay the user's.

2. **[Operator / telos deadline 2026-07-23] Fire GAP-1 live.** Execute `scripts/gfr_dynvocab/gap1_probe.py` against a POPULATED Asset ID on asset_edit project `1202204184560785`. This is the verified_realized gate — a separate axis from proven per G-DENOM. UNKNOWN distinct from present-but-null.

3. **[Operator / strategy] Escalate DEFER-1 fleet cf-contract registry.** S4a FIRED (autom8 `KeyError: 'asset_id'`). Second production consumer confirms the cross-service drift class. This is the one-way-door that requires explicit operator/strategy sign-off before design begins.

4. **[10x-dev / next sprint] Drift-drain pass.** 14 entities emit `model_schema_coverage_unpaired` at startup; Offer carries 31 drifted fields including 'Asset ID'. Each can be drained by adding a schema column or registering an explicit exclusion. Quick fix per entity once operator schedules the pass.

5. **[10x-dev / design-first] Normalization-collision shadow.** Design a collision-detection strategy in `dynvocab.py _build_manifest` before the sprint that adds cf metadata. Reactive patch is wrong per handoff.

---

## Summary Return Value

| Axis | Value |
|------|-------|
| Overall verdict | **STRONG** |
| cross_stream_concurrence | **true** |
| G-Rung | **proven / disjoint-attested** |
| Path | **STRONG — DO NOT ROUTE BACK** |
| verified_realized | UNATTESTED (GAP-1=OFFLINE_DRY_RUN; telos deadline 2026-07-23) |
| Health grade (overall) | **A** (all six dimensions at A; weakest-link model) |
| Binding verdicts | (a) DYNVOCAB TENANT-SAFETY: STRONG [STRUCTURAL | STRONG]; (b) MOONSHOT FUTURE-4 COHERENCE DISSENT: STRONG CONCURRENCE [STRUCTURAL | STRONG] |
| Findings | 0 Critical, 0 High, 0 Medium, 3 Low (all informational; none blocking) |

---

*Review mode: FULL | Critic: rite-disjoint case-reporter | SUT: gfr-dynvocab sprint-5 RE-RUN | 2026-06-25*
*G-RUNG honored throughout. G-DENOM honored throughout. G-THEATER honored (RED-on-mutation present). G-CRITIC honored (MODERATE self-ceiling; STRONG on independent rite-disjoint RED evidence). G-DEFER honored (none built). G-PROVE honored (pasted live receipts, no adjective-only rows).*
