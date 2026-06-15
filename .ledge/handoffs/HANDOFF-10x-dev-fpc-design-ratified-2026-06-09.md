---
type: handoff
handoff_type: assessment   # 10x-dev design phase → eunomia (STRONG critique) + operator (UK-2 ruling + live probe) → Phase-1 build
station: design→build rite-switch seam
source_rite: 10x-dev (FPC design phase)
target: eunomia (rite-disjoint STRONG design critique) + operator (UK-2 ruling, live A-vs-B/cache probe) ; then 10x-dev/framing Phase-1 build
date: 2026-06-09
initiative: field-provenance-&-population-contract (FPC)
extends: .know/telos/dataframe-resolution-coherence.md ; .ledge/handoffs/HANDOFF-arch-to-10x-dev-fpc-opportunity-matrix-2026-06-09.md
evidence_grade: MODERATE (self-ref ceiling; STRONG requires the HELD eunomia rite-disjoint critic). Design ratified-PENDING-CONDITIONS; spike-proven (mechanism only).
status: proposed
discipline: >
  Design + spike artifacts only — no Phase-1 code landed, no consumer rebound, no schema edited.
  Every receipt re-fired live from origin/main 50ebfe33 + DuckDB. The path-canonicalization pillar
  was adversarially REFUTED as likely-inert for the 571 population (Axis-2) — banked honestly, not
  rounded up. Production levers (eunomia critique, UK-2 ruling, live Asana probe, re-warm, merge) stay
  the operator's.
---

# FPC Design-Ratified (MODERATE-with-conditions) — design→build seam HANDOFF

## Rung statement (G-RUNG — not rounded up)

| Element | Rung | Receipt |
|---|---|---|
| FPC opportunity matrix | **MAPPED** (prior) | `.ledge/reviews/fpc-*-2026-06-09.md` |
| FPC design (TDD/ADR/shape) | **ratified-PENDING-CONDITIONS** (MODERATE) | `.ledge/specs/TDD-field-provenance-population-contract-2026-06-09.md`, `.ledge/decisions/ADR-…`, `.sos/wip/frames/…shape.md` |
| path-canonicalization | **spike-proven (MECHANISM only); live efficacy REFUTED-PENDING** | `.ledge/spikes/SPIKE-fpc-path-canonicalization-2026-06-09.md`; PoC `seam2-unit-econ/tests/spikes/test_fpc_path_canonicalization_spike.py` (6 passed/2 skipped; zero-new-calls proven + 2 mutations RED) |
| FPC design STRONG-cert | **NOT DONE** | eunomia rite-disjoint critic HELD (operator lever) |
| Phase-1 build | **NOT STARTED** | gated: N2 ratified + eunomia STRONG + UK-2 ruled |
| unit-MRR cell-0 cure | **authored, UNMERGED** | `seam2-unit-econ` worktree (Phase-2) |

## What was ratified

**FieldContract SSOT (ADR Option C, chosen over A/B/D).** One declarative contract per `(entity,field)` —
`entity, name, value_type, canonical_source, resolution{per-entity mode+cascade_precedence}, fetch_requirement,
recovery[](cache_reuse), population_policy(TOTAL/ACTIVE_SUBSET/LEGITIMATELY_SPARSE), active_subset_floor,
coherence_consumers`. From ONE contract DERIVES: schema dtype, model field-class, opt_fields, the floor-set,
and a GENERATED verification matrix (coherence + parity + population tests per cell). G-PROPAGATE realized:
neither dtype nor field-class is independently declared → intra-cell drift becomes *unrepresentable*.
FM-A..FM-E dispositioned (server-non-determinism = stated-assumption; dual-source precedence = `cascade_precedence`
field, withheld pending UK-5; model-only NumberFields = coverage-gap test; observer-not-gate = deliberate
availability-first consequence; un-warmed holders = warm-after-Phase-2 sequencing).

**The 5-pillar leverage order holds — but the value re-centers on observability (see the Axis-2 reframe):**
①drift-eradication+parity-test (4.0) · ②offer_id-normalize (3.0) · ③population-floor-extension (2.5) ·
④path-canonicalization (2.5 — **questioned**) · ⑤coherence-observatory.

## 🔴 THE LOAD-BEARING FORK (Axis-2, adversarially refuted — read before Phase-2)

The spike proved path-canonicalization is **field-agnostic + ZERO-new-calls + has G-THEATER teeth** (one
mechanism heals mrr + weekly_ad_spend + offer.cost; 2 mutations fired RED). **BUT the qa-adversary REFUTED
its applicability to the actual 571 population**, corroborated by my own cache probe:

- The live warmer GETs **ancestors/parents only** (`hierarchy_warmer.py:148-186`) and writes the
  **list-path-stripped** copy for the row itself (`unified.py:493-503 put_batch_async data=task`). Only
  `freshness.py:448` GETs a row by its own gid — and only for **newly-added** units, not the steady-state 571.
- My S3 probe: the smoking-gun unit gids (offer-mrr present / unit-mrr null) have **no self-keyed full-task
  GET copy** in the body stores. Prior SEAM-2 probe: 8/8 sampled null rows were `number_value` AND
  `display_value` **both null**.
- ∴ **for the 571, cache-reuse has nothing to reuse → "zero new calls" is true but vacuous (zero heals).**

**The fork the design must NOT obscure:** healing the 571 via the receiver requires EITHER
(a) a deliberate **GET-on-null pass = the rejected N+1**, which crosses the **CR-3 line** (single-worker /
0.25-vCPU / SlowAPI-100-min — would regress the just-stabilized bulk-fanout), OR (b) the source is
**genuinely null-at-source** (MRR not entered in Asana) → **no code mechanism heals it; the FPC's correct
role is to make it OBSERVABLE (population floor + coherence invariant fire RED), never to fabricate it
(G-DENOM, the $8,775/7-row fossil anti-precedent).**

**Reframe banked:** the FPC's durable, CR-3-safe value is the **observability half** (pillars ①②③⑤ — drift
eradication, generated parity test, population floor, coherence observatory) — making "present-but-null",
"path-dependent value", and "schema/model drift" *impossible to hide*. The path-canon "heal" (④) is
**operator-probe-gated and may be out-of-scope for the receiver** (it's an upstream data-entry / N+1-budget
decision, not a free win).

## Self-critique conditions banked (MODERATE-PASS-WITH-CONDITIONS — clear before STRONG)

1. **[Axis-2, BLOCKING Phase-2 framing]** Establish (operator/eunomia live receipt) what fraction of the 571
   null unit gids have a cached GET-copy with non-null `number_value`. If ~0, path-canon cache-reuse is inert
   → surface the N+1-vs-null-at-source fork explicitly; do NOT frame Phase-2 as a free zero-cost cure.
2. **[Axis-1, gate Phase-3]** The `FieldContract (value_type, provenance)` key cannot represent D1-class cells
   (enum source / numeric schema dtype, e.g. `unit.discount`). Add a third axis (Asana `resource_subtype`) or
   a per-cell override escape hatch.
3. **[Axis-1, ADR correction]** The per-cell `(entity,name)` contract does NOT close `offer_id` Utf8↔Int64
   *cross-frame* drift — remove it from "impossible by construction" or add a cross-cell join-key-class constraint.
4. **[Axis-4, G-THEATER half-gap]** Coherence-RED (571) is proven + reproduced; the **parity-RED on a synthetic
   drift cell is asserted-only** (no FieldContract/parity generator exists yet). Either demonstrate a minimal
   parity-RED in the spike worktree, or downgrade the parity pillar to "parity-RED deferred to Phase-3 build."

## Operator-gated levers (surfaced — NOT executed)

```
# N4 — eunomia rite-disjoint STRONG design critique (a rite switch). Highest-value attack named by the
#   self-critic: the Axis-2 cache-population premise — demand the live receipt (how many of the 571 null
#   unit gids carry a GET-copy with non-null number_value; if ~0, the path-canon cure is inert).
# UK-2 — PRD-0024 ruling: is discount/cost canonically ENUM-STRING or NUMERIC? BLOCKS Phase-1 drift direction.
# UK-3 — is a DataFrame-level offer_id join planned? (conditions the offer_id normalize; HIGH if yes).
# LIVE A-vs-B PROBE — ASANA_PAT GET of a sample of the 571 null unit tasks: number_value present (path-stripped,
#   Branch A) vs null (null-at-source, Branch B). The single receipt that decides whether ANY code heals the 571.
# Phase-1 BUILD (after eunomia STRONG + UK-2) — drift reconcile D3 (→Decimal, clear) + D1/D2 (UK-2 direction) +
#   generated parity test + floor extension (unit:("mrr",); weekly_ad_spend/discount LegitimatelySparse) +
#   offer_id normalize (UK-3). Each a scoped PR; merge is yours.
```

## DEFER / watch-registered (NOT scope-crept)

- **GATE-FPC-PHASE1** — eunomia STRONG + UK-2 ruling (both operator); D3 direction is clear (→Decimal).
- **FORK-FPC-PATH-CANON** — Axis-2: cache-reuse likely inert for the 571; N+1 (CR-3-risk) vs null-at-source (data-entry). Operator live-probe decides.
- **DEFER-UNIT-MRR-CELL0** — the cell-0 cure (defense-parity + discount→Utf8 + guard) authored/unmerged in `seam2-unit-econ`; its live efficacy is the SAME Axis-2 fork.
- **DEFER-UK-1** (model-only NumberFields), **UK-5** (vertical cascade precedence) — Phase-3.
- **DEFER-SEAM2-CONSUMER-REBIND** (cross-repo), **06-11 soak tail**, **AMBER observability** — unchanged.
- **N≥2 throughline** — SEAM-1 + FPC = the 2nd instance of "data-plane contracts implicit"; promote at the eunomia STRONG gate.

## Routing

- **Next: operator runs the eunomia STRONG critique (rite switch)** + rules **UK-2** + (decisively) the **live A-vs-B/cache probe**. Those three resolve whether Phase-1 builds and whether path-canon (④) is even viable.
- **Then `/frame` → 10x-dev** Phase-1 quick-wins (drift+parity+floor+offer_id), each a scoped PR.
- Production-mutating levers stay the operator's. No next-rite specialists dispatched from here.

*10x-dev FPC design phase, 2026-06-09. Design ratified at MODERATE-with-conditions; path-canonicalization
spike-proven as a mechanism but adversarially refuted as likely-inert for the live 571 (the value re-centers
on the observability pillars). STRONG needs eunomia (HELD). Every claim re-fired live; the stale local checkout
was never trusted; the coherence invariant fires RED=571 (G-THEATER). STOP — the build is gated on operator levers.*
