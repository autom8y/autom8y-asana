---
type: handoff
handoff_type: assessment   # eunomia STRONG-cert → 10x-dev/framing (Phase-1) + operator (UK-2, live-source probe)
station: critique→build rite-switch seam (eunomia → 10x-dev)
source_rite: eunomia
target: 10x-dev/framing (FPC Phase-1) + operator (UK-2 ruling, ASANA_PAT live-source parity probe)
date: 2026-06-09
initiative: field-provenance-&-population-contract (FPC)
extends: .ledge/handoffs/HANDOFF-10x-dev-fpc-design-ratified-2026-06-09.md ; .know/telos/dataframe-resolution-coherence.md
evidence_grade: STRONG (rite-disjoint — eunomia ≠ 10x-dev/arch; every receipt re-fired from origin/main + S3, not inherited) ; design-where-earned
status: proposed
discipline: >
  eunomia rite-disjoint critique. Critique + certify + resolve only — no Phase-1 code landed, no consumer
  rebound. Axis-2 keystone RESOLVED from the S3 cache substrate (Branch A). One N4 anomaly (571 "anchor in
  flux") was traced by Potnia to a frame-identity artifact (N4 read a stale Jan representation, not the
  canonical v2 frame) and corrected — the correction itself vindicates the FPC thesis. Production levers
  (UK-2, ASANA_PAT, merges, re-warm) stay the operator's.
---

# FPC Design — eunomia rite-disjoint STRONG-Certification (where earned)

## Verdict

**Execution-altitude: PARTIAL→PASS-where-earned** (the sole PARTIAL driver — N4's 571 "anchor in flux" — was a
frame-misidentification, corrected below; the canonical-frame 571 anchor HOLDS). **Product-altitude: FLAG-ADVISORY**
(verified_realized carries a deferred operator-gated live-source receipt). **The DESIGN earns STRONG via the
rite-disjoint re-derivation** (eunomia ≠ author); eunomia's own auditor self-assessment caps MODERATE per
self-ref-evidence-grade-rule — the STRONG attaches to the design-under-critique.

## STRONG-certification matrix (pillar × verdict, every receipt eunomia-re-fired)

| Pillar | Verdict | Re-fired basis |
|---|---|---|
| **FieldContract SSOT derivation** | **STRONG (80/82); LEAKY-WHERE for D1-class** | `(value_type,provenance)` derives both schema dtype + model field-class for unambiguous cells; cannot represent D1 (Asana numeric storage ⊥ enum domain). Condition-2 REAL. |
| **Drift-eradication** | **STRONG (design)** | 4 signals re-confirmed @ origin/main: D1 `unit.py:38`/`:118`, D2 `offer.py:70`/`:136`, D3 `asset_edit.py:148`/`:192`, offer_id `offer.py:42`(Utf8)/`asset_edit.py:127`(Int64). |
| **Generated parity-test** | **STRONG-by-demonstration; in-repo generator Phase-3-gated** | N3 built a minimal parity-RED checker (DTYPE/FIELDCLASS maps) firing RED on D1+D2+synthetic, GREEN on unit.mrr — **condition-4 CLOSED**, not merely deferred. |
| **Population-floor** | **STRONG (design, CR-3-safe)** | floor dict `{"offer":("mrr","offer_id")}` confirmed; 80/82 unguarded; weekly_ad_spend/discount stay LegitimatelySparse (G-DENOM). |
| **Coherence-observatory** | **STRONG mechanism + 571 anchor HOLDS** | canonical v2 `1201081073731555/unit/sections/` re-pulled fresh (06-09) = 0/3021 mrr → gun=571/coherent=0 reproduced. (N4's 355/90/1346 was a stale-Jan non-canonical frame — corrected.) |
| **Path-canonicalization ④** | **VIABLE (Branch A)** | N2: 15/15 null-unit GET-copies carry the unit's OWN non-null number_value (2/15 diverge from offer → offer-bleed refuted). Value is path-stripped, NOT null-at-source. The cure works. |

## Axis-2 KEYSTONE — RESOLVED: Branch A (the headline result)

The 10x-dev self-critique leaned toward Branch B (null-at-source / cache-reuse inert). **eunomia's S3-cache probe
inverts it to Branch A:** the cached per-task GET-copy (`asana-cache/tasks/<gid>/task.json`, canonical read-point
`cache/backends/s3.py:271`) carries non-null `number_value` for **15/15** sampled null-unit gids (1185, 550, 485, …),
and **2/15 diverge from the offer-join value** (gid `1200585406043690` unit=550 vs offer=600) — proving each body
holds the unit's OWN MRR, not offer-bleed or section-aggregate. **∴ the value is path-stripped (present on GET,
dropped on the v2-frame materialization) — path-canonicalization cache-reuse CAN heal the 571.** The cure is not inert.

**Residual (operator ASANA_PAT lever — can only reduce cure magnitude, never invert Branch A):** the cached bodies
are `modified_at 2026-03-29 / cached 2026-04-30`; whether the *current live* Asana source still carries the value
needs one `get_async` probe. The exact `coherent` lift needs an operator re-warm + re-run of the canary on the
live v2 frame.

## The N4 anomaly — traced + corrected (a finding in itself)

N4 re-fired the gun and reported it had "moved" (571→355/90, coherent 0→1346, unit.mrr 692/2601). **Potnia traced
this to a frame-identity artifact:** N4 read a **stale January representation** (`LastModified 2026-01-11`), NOT the
canonical v2 frame. The canonical v2 `/unit/sections/` frame, re-pulled fresh this pass (06-09 10:47–10:51), is
**still 0/3021 mrr → gun=571 reproducible**; the flat key `unit:1201081073731555` N4 cited **does not exist** under
`dataframes/`. **The 571 anchor HOLDS.** That a rigorous rite-disjoint critic read a divergent uncontracted
representation is the strongest possible vindication of the FPC: FM-1 (identity not contracted) bit the auditor
itself — exactly what the entity-identity + coherence contract makes impossible.

## The 4 conditions — REAL + correctly dispositioned (eunomia re-confirmed)

1. **Axis-2 cache-population** — RESOLVED Branch A (above). Disposition correct.
2. **value_type-key gap (D1)** — REAL; the `(value_type,provenance)` key cannot represent enum-source/numeric-schema; add a 3rd axis (Asana `resource_subtype`) or per-cell override. Gate Phase-3. Correct.
3. **offer_id cross-frame** — REAL; per-`(entity,name)` contract closes intra-cell drift, NOT cross-frame join-key coherence; ADR "impossible by construction" overstated for offer_id. Correct.
4. **parity-RED** — **UPGRADED**: N3 demonstrated the broken-fixture-RED (no longer assertion-only); in-repo generator remains Phase-3. Correct.

## Throughline (SEAM-1 + FPC = "data-plane contracts implicit")

**Design-altitude node EARNED** — N≥2 (SEAM-1 entity-identity + FPC field-provenance), attested by the rite-disjoint
design critique. **Deploy-empirical node PENDING** (Phase-2 `coherent≥100` post-deploy receipt unfired). Honest rung:
*design-node minted; deploy-node deferred* — not rounded to closed.

## Operator-gated levers (surfaced — NOT executed)

```
# UK-2 — PRD-0024 ruling: discount/cost canonically ENUM-STRING or NUMERIC? Blocks Phase-1 D1/D2 drift direction.
#   (D3 asset_edit.score → Decimal is clear, NOT UK-2-blocked.)
# ASANA_PAT live-source probe — one get_async on the current null-unit set: confirm the cached non-null number_value
#   still matches live source. Converts FLAG-ADVISORY → verified_realized; sets the Phase-2 cure magnitude.
# UK-3 — offer_id DataFrame-level join planned? (conditions the offer_id normalize severity).
# Phase-1 BUILD (after UK-2) — drift reconcile (D3 clear; D1/D2 per UK-2) + generated parity test (N3 proved the
#   mechanism) + floor extension (unit:("mrr",); was/discount LegitimatelySparse) + offer_id normalize (UK-3).
# Phase-2 — path-canon cache-reuse recovery (now Branch-A-VIABLE) + operator re-warm + re-fire the 571 canary.
# Phase-3 one-way-door — schema-derivation requires arch/dataframe-owner sign-off (ADR §Reversibility).
```

## Routing

- **Next `/frame` → 10x-dev/framing** for FPC Phase-1 quick-wins (each a scoped PR; merge = operator), gated on UK-2.
- **Operator:** the ASANA_PAT live-source probe (cheap, decisive for verified_realized) + the UK-2 ruling.
- Phase-2 is now **Branch-A-VIABLE** (the cure heals) — the highest-value follow-on once Phase-1 + the live probe clear.
- No next-rite specialists dispatched from here.

*eunomia rite, FPC STRONG-certification, 2026-06-09. Design STRONG-certified-where-earned (rite-disjoint); Axis-2
RESOLVED Branch A (cure viable); 571 anchor HOLDS on the canonical frame (N4's flux was a frame-identity artifact,
corrected — and vindicates the FPC). Every receipt re-fired from origin/main + S3, never inherited. Phase-1 gated on
UK-2; FPC NOT live. Production levers stay the operator's.*
