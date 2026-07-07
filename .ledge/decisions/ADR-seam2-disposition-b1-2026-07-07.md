---
type: decision
status: accepted
initiative: asana-realization-tail-convergence
workstream: B — Offer-Economics Grain Convergence
sprint: B1-probe-rule
decided_at: 2026-07-07
decided_by: data-analyst rite (PT-B-FORK, potnia) on rite-disjoint probe evidence
self_assessment_cap: MODERATE
supersedes_disposition: seam2 telos deadline annotation "PENDING-B1-redundancy-probe"
---

# ADR — seam2 offer-economics fork: DEFER (RETIRE refuted → GENUINE-GAP → BUILD blocked)

## Decision

The seam2 monolith-rebind fork (retire-vs-build), left `PENDING-B1-redundancy-probe`
at the A1 ledger-truth reconcile, is **RULED: DEFER** — the RETIRE arm is **decisively
refuted** (the operator-plane does NOT obviate the rebind); BUILD is the standing lean but
is **BLOCKED** pending two substrate triggers. No code is authored this sprint
(PROBE-GATED HARD, crusade shape edge E1).

## The question (define phase, model-provenance-author)

REDUNDANT (→ RETIRE) iff operator-plane surfaces the **offer's own realized sale-economics**
— offer sale-revenue (the $79,485-class; Σ `payments.amount_cents` attributed to the offer)
AND unit sold-band — as first-class summable metrics, at **offer-entity grain**, over the
ruled **ACTIVE-62 offer subset**, **reachable by all three consumers** (C1 ad_reporting,
C2 payments/mrr, C3 OfferHolders) without the monolith rebind. GAP (→ BUILD) iff any of
{sale-quantity, offer-grain, ACTIVE-denominator, reachability} is absent.

## Evidence (grain-integrity-engineer probe · DuckDB + code, fresh 2026-07-06 snapshot)

- **RETIRE refuted — operator-plane surfaces ad-performance, not sale-revenue.**
  `offer_level_stats` emits spend/leads/scheds/convs/ltv/cpl/cps/ecps/conversion_rate/roas
  (`library.py:1302-1316`) at **composite** grain `offer_id × office_phone × vertical`
  (`library.py:1324-1328`) — NOT offer-entity sale-revenue. `ltv` is a LEADS-fact cohort
  estimate (`library.py ~1337`), not realized money. `offer_cost` is a **display dimension**
  (`library.py:1406,:1454`), not a summed metric. The 06-29 buildout (#215 `dafbb136`) is
  **authz-only** ("no new insight, route, schema"). The only payments-summing surface,
  `reconciliation.collected` (`library.py:635-652`), is **office-grain** AND
  **operator-excluded** (financial-PII / OD-5-reserved) — served-path-unreachable on both axes.
- **Substrate blockers (why BUILD can't start):**
  - **T1 (PRIMARY) — payments→offer attribution absent.** `payments` carry NO `offer_id`;
    `attribution_method` is **NULL for all 42,269 rows** ($10,399,185.91 total, 481 offices).
    Offer-entity sale-revenue is not *assemblable* without an attribution ruling.
  - **T2 — ACTIVE denominator empty.** `account_status` (ACTIVE-only registry [SD-02]) is
    **0 rows in every snapshot including 2026-07-06** — the ruled ACTIVE-62 subset and the
    $79,485 marquee cannot be computed.
- **Grain integrity (G1) — a naive path is a fabrication.** `payments ⋈ business_offers` on
  `office_phone` (non-unique: 270 dup values, avg 2.44, max 17) **inflates 3.6×**
  ($10.2M → $33.76M). No naive `office_phone`-keyed offer-revenue path is grain-legal.
- **Rite-disjoint adversary: GENUINE-GAP.** All four RETIRE steelmen refused; no fabricated
  coverage found (every claimed absence verified in code/data); minor provenance/​freshness
  nits flagged, non-verdict-affecting.

## Consequence

- **seam2 stays `shipped: MISSING`** — nothing landed; DEFER is a disposition, not a
  realization. verified_realized remains eunomia's at PT-E.
- **RETIRE arm CLOSED** — the operator-plane-obviates-the-rebind hypothesis is refuted on
  code-level evidence; do not re-open without new operator-plane sale-revenue surface.
- **BUILD (B2 → monolith HANDOFF) is the standing lean, gated on BOTH triggers:**
  - **T1**: a model-provenance-author payments→offer **attribution ruling** exists (the
    grain-legal key + method), and
  - **T2**: `account_status`/ACTIVE registry is **populated** so the ACTIVE-62 denominator +
    $79,485 marquee are computable at a fresh SHA.
  When T1∧T2 clear, re-enter B (re-probe or proceed to B2 build under the attribution ruling
  with G1 asserted).
- **Grain discipline carried**: any future offer-revenue assembly MUST assert row-multiplicity
  and reject silent fan-out (the `compute_metric`/Query-Engine inflation-guard promotion,
  Track-B item, inherits this).

## Provenance / limits

Probe ran against `autom8y-data` offline snapshots (`data/offline/current` → 2026-07-06) +
post-06-29 commits by direct `git show`; `analyst.duckdb` was empty (0 tables). DEFINE-cited
1496/1315 counts are stale (fresh: offers 1501 / business_offers 1320). Grade
`[STRUCTURAL | MODERATE]` — rite-disjoint adversary corroborated GENUINE-GAP; STRONG is
eunomia's at PT-E.
