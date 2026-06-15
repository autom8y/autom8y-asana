---
type: handoff
handoff_type: implementation   # 10x-dev Phase-1 BUILD complete → operator (merge + UK rulings + eunomia STRONG) → Phase-2
station: Phase-1→Phase-2 rite-switch seam (10x-dev → operator-gated → 10x-dev/framing Phase-2)
source_rite: 10x-dev
target: operator (merge #114/#115, UK-2/UK-3 rulings, eunomia STRONG critic, ASANA_PAT probe) → next /frame 10x-dev/framing (Phase-2)
date: 2026-06-09
initiative: field-provenance-&-population-contract (FPC)
extends: .ledge/handoffs/HANDOFF-eunomia-fpc-strong-cert-2026-06-09.md ; .know/telos/dataframe-resolution-coherence.md
evidence_grade: MODERATE (10x-dev-authored; self-validated by qa-adversary — STRONG requires the operator's rite-disjoint eunomia critic, N7) ; CR-3-safe
status: proposed
discipline: >
  Phase-1 observability pillars BUILT as two scoped PRs (merge = operator). Every receipt re-fired
  from origin/main + S3 + DuckDB, never inherited. The 571 coherence canary STILL fires RED by
  construction (no fetch-path touched) — Phase-1 did NOT and must NOT claim the cure (that is Phase-2).
  Production levers (UK-2/UK-3 rulings, merges, ASANA_PAT probe, re-warm) stay the operator's.
---

# FPC Phase-1 Build — 10x-dev, rung-honest seam

## Verdict (rung-honest, G-RUNG)
**Phase-1 CR-3-safe observability pillars are BUILT and adversarially GO — PRs OPEN, NOT merged, FPC NOT live, 571 NOT cured.**
The rung tops at **"Phase-1 quick-wins authored + adversarially-validated (MODERATE) + PRs open (merge = operator)."** STRONG requires the rite-disjoint eunomia critic (N7), which is the operator's rite switch.

## What landed (two scoped PRs off origin/main `50ebfe33`)

| PR | Branch / HEAD | Pillars | Test receipt |
|---|---|---|---|
| **#114** | `fpc/phase1-dtype-parity` @ `e64bdedb` | (C2) FieldContract SSOT maps `dataframes/contracts/field_contract_maps.py` (`DTYPE_MAP`/`FIELDCLASS_MAP` — sole propagation point) + generated parity check `tests/unit/dataframes/test_field_contract_parity.py`; (C1) D3 `asset_edit.score` Float64→Decimal; (D-1) registered `asset_edit.{offer_id,template_id,videos_paid}` | `11 passed, 2 xfailed`; broken-fixture-RED + neuter teeth proven; broader dataframes suite `1352 passed` |
| **#115** | `fpc/phase1-population-floor` @ `cca1242f` | (C3) floor `_VALUE_COLUMNS_BY_ENTITY += {"unit": ("mrr",)}`; (C4) below-floor WARN fixture | `6 passed`; C4 proven to depend on C3 (revert → 5 fail); G-DENOM only-mrr asserted |

## Proof obligations DISCHARGED (G-THEATER, all re-fired by qa-adversary independently)
- **Parity checker has teeth, no false-negative:** mutation (inject drift into a GREEN cell → RED) + neuter (vacuous checker → suite collapses) both confirmed; introspection proven live + MRO-correct (the `Process.score` shadow trap is genuinely avoided via `getattr_static`).
- **D1/D2 are genuinely-failing strict-xfails** (markers stripped → hard FAIL, not hidden XPASS) — drift recorded + visible, HELD on UK-2, will XPASS-fail loudly the moment a UK-2 reconcile lands.
- **D3 is byte-identical at runtime** (`"Decimal"` and `"Float64"` both → `pl.Float64`; end-to-end materialized frames equal) — the SSOT label fix cannot regress the data plane.
- **Coherence canary STILL `gun=571, coherent=0`** (live DuckDB over `/tmp/u8u`+`/tmp/u8o`, 2001 joined) — Phase-1 touched NO fetch-path file (verified by grep across all 7 changed files). The standing RED is the CORRECT Phase-1 state.
- **G-DENOM:** floor assesses `unit.mrr` ONLY; weekly_ad_spend/discount stay LegitimatelySparse; no blanket null-fill anywhere (the $8,775/7-row fossil anti-precedent honored).

## HELD / DEFERRED (watch-registered, G-DEFER — NOT scope-crept)
- **D1 `unit.discount`** (schema Decimal vs EnumField) + **D2 `offer.cost`** (schema Utf8 vs NumberField): HELD on **UK-2** (PRD-0024 discount/cost canonical direction). Both ruling-direction edits pre-staged in the architect spec — a UK-2 ruling unblocks a single known edit + strips the matching xfail.
- **offer_id Utf8↔Int64 cross-frame** coherence: HELD on **UK-3** (is offer↔asset_edit joined on offer_id at the DataFrame level?). The per-(entity,name) contract closes intra-cell drift, NOT cross-frame join-key — needs a dedicated cross-frame coherence test if UK-3 says a join exists.
- **Phase-2 path-canon cure (unit-MRR cell-0)** — Branch-A-VIABLE; the throughline DEPLOY node; gated on the ASANA_PAT probe magnitude + operator re-warm.
- Phase-3 in-repo generator + schema-FROM-model derivation (one-way-door); SEAM-2 rebind; 06-11 soak tail; AMBER observability.

## Operator-gated levers (surfaced — NOT executed)
```
# MERGE the Phase-1 PRs (strict=true; verify /files scope first):
env -u GITHUB_TOKEN gh pr merge 114 --squash   # fpc/phase1-dtype-parity (parity SSOT + D3 + D-1)
env -u GITHUB_TOKEN gh pr merge 115 --squash   # fpc/phase1-population-floor (unit:('mrr',) floor)
# UK-2 ruling (PRD-0024): discount/cost canonically ENUM-STRING or NUMERIC? → unblocks D1/D2 (one staged edit each).
# UK-3: is offer_id a DataFrame-level join key? → conditions the offer_id-normalize severity.
# eunomia STRONG critic (N7): switch to eunomia rite (restart CC) → /cross-rite-handoff for the Phase-1 BUILD
#   rite-disjoint STRONG-cert (lifts the MODERATE self-ref ceiling). OR accept MODERATE for merge + post-merge cert.
# ASANA_PAT live-source parity probe (parallel, Phase-2 prep): one get_async on the null-unit set → flips
#   verified_realized FLAG-ADVISORY → verified + sets the Phase-2 cure magnitude (can only shrink, never invert Branch A).
# OPTIONAL post-merge: re-warm under the merged branches + re-fire the 571 canary (residual qa gap — structurally
#   a no-op since no fetch-path touched, but the only receipt qa could not fully close without a live re-warm).
```

## Routing
- **Operator:** merge #114/#115 (or hold for eunomia STRONG), rule UK-2/UK-3, fire the ASANA_PAT probe.
- **Next `/frame` → 10x-dev/framing (Phase-2):** path-canon cache-reuse cure (Branch-A-VIABLE) = the throughline DEPLOY node — `coherent ≥ 100` post-deploy is the receipt that converts the SEAM-1+FPC throughline from design-altitude (N≥2) to deploy-empirical. Gated on the probe magnitude + re-warm.
- **Do NOT dispatch Phase-2 specialists from here.** This is a STOP at the seam.

*10x-dev rite, FPC Phase-1 BUILD, 2026-06-09. Pillars BUILT + adversarially GO (MODERATE); PRs #114/#115 OPEN (merge = operator); 571 canary STILL RED (cure NOT claimed); FPC NOT live. Every receipt re-fired from origin/main + S3 + DuckDB, never inherited. STRONG + merges + UK rulings + probe stay the operator's.*
