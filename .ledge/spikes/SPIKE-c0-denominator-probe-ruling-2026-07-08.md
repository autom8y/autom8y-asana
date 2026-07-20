---
type: spike
subtype: c0-denominator-probe-ruling
status: accepted
initiative: north-star-per-offer-economics
generated_at: 2026-07-08
generator: Explore agent swarm (5 read-only scouts) + main-thread synthesis, at OPERATOR DIRECTION
gates: "C-0 CODE-HALF DISCHARGED (read-only code inspection); LIVE-PROD-HALF PENDING (iris live-probe)"
self_assessment_cap: MODERATE
supersedes_premise: "SPIKE-north-facing-crusades-2026-07-08.md Blocker-A framing ('payment→offer_id join, build a producer')"
---

# C-0 Denominator Probe — Ruling

The C-0 probe the frame/shape gated the arc on. Executed via a 5-scout read-only Explore
swarm across **autom8y-data** and **autom8y-asana**, at operator direction, after a
stakeholder interview corrected two foundational premises (business = marketing agency
optimizing client-side campaign offers; per-offer **revenue** is NOT attributable —
payments live at `(office_phone, vertical)`, 1:many over offers — so the offer-grain
signal is **cost efficiency (CPS/eCPS) on ACTUAL ad spend**, not revenue).

## The one finding that reshapes the arc

**The per-offer CPS/eCPS pipeline very largely ALREADY EXISTS in autom8y-data.** This is
not a producer-build. It is a **dimension-feed + definition-ratification + coverage-trust +
surface-exposure** problem. Confirmed by first-party code reads (file:line below), NOT
premise-propagation.

## What already exists (do not rebuild)

- **The metrics.** `cps = spend / scheds` (`autom8y-data .../analytics/core/metrics/library.py:1939-1987`,
  null-when-zero via `CostDivisionFormula` at `.../registry/composite.py:261-340`) and
  `ecps = spend / effective_scheds` (`library.py:2504-2519`). Full cost family alongside:
  `cpl, cpa, cpc, cpm`, per-20k-impression normalizations (`cps20m, ecps20m`), and
  population threshold flags (`crossed_cps_150`, `pct_accounts_cpl_over_50`). Central
  `MetricRegistry` (`.../registry/metric_registry.py`).
- **An offer-grain insight.** `offer_level_stats` (`library.py:1295-1375`, ARMED
  `.../primitives/drilldown/arming_manifest.py:619-685`, 2026-06-18) already declares
  `grouping_dimensions=[offer_id, office_phone, vertical]` and computes
  `{cps, ecps, cpl, roas, conversion_rate}`. Sibling `asset_level_stats` (`library.py:522-614`).
- **The exposure contract, with an `offer` frame.** `POST /api/v1/data-service/insights`
  (`autom8y-data .../analytics/routes/data_service.py:175-397`) takes `frame_type ∈
  {offer, unit, business, asset, question}` + `phone_vertical_pairs` + `period`; the
  `EntityMetrics` response **already carries `cps` and `ecps` fields**
  (`.../api/data_service_models/_insights.py:187-190`).
- **Asana already consumes it.** `DataServiceClient` insights path
  (`autom8y-asana .../clients/data/_endpoints/insights.py:142-286`); factories (`leads`,
  `campaigns`, `ads`, `adsets`) expose `cps` at `frame_type="offer"`
  (`.../query/data_service_entities.py:59-178`); joinable via
  `JoinSpec(source="data-service", select=["cps","ecps"])` (`.../query/join.py:21-66`).
- **A leadership surface already renders CPS.** The insights HTML report
  (`autom8y-asana .../automation/workflows/insights/formatter.py:70-112`) renders CPS in
  KPI cards + period tables (LIFETIME/QUARTER/MONTH/WEEK).

## The REAL gaps (the actual work)

### GAP-1 — Offer-grain SPEND is dark (the true Blocker-A; a DIMENSION-FEED, not a build)
The spend→offer chain is `ads_insights.spend → ad.creative_id → ad_creatives.asset_id →
assets.offer_id → offers.offer_id` (`autom8y-data .../core/models/_advertising.py`:
AdInsight 101-122, Ad.creative_id 21-42, AdCreative.asset_id 227-277, Asset.offer_id
127-209). It breaks in two places:
- **`assets.offer_id` exists but is UNPOPULATED** from Asana context. **Asana already
  KNOWS the linkage** — `AssetEdit` extracts `(office_phone, vertical, asset_id, offer_id)`
  (`autom8y-asana .../dataframes/schemas/asset_edit.py:106-132`) — but **never pushes it**
  (`gid_push.py:312-405` pushes only phone/vertical/GID; account-status `557-627` has no
  offer_id). **This is the dimension asana must feed** — rides existing `gid_push` rails.
- **`ad_creatives.asset_id` is sparsely populated (~18.7% per an in-code figure, 2,589 /
  44,523)** — so even with the offer link, only a fraction of spend has offer lineage.
  ⚠️ **This % is code-inspected, NOT live-prod-confirmed — iris must verify against prod.**

### GAP-2 — The eCPS "effective" definition is DRIFTED across the stack (CENTRAL RATIFICATION ITEM)
Three different meanings of the "e" are live simultaneously:
- **Code (metric):** `ecps` "effective" = a **status FILTER**. `effective_scheds =
  COUNT_DISTINCT(appointments WHERE status IN [scheduled, confirmed, pending, patient,
  requested, rescheduled])` (`library.py:1021-1048`) — excludes no-shows/cancelled. NOT modeling.
- **Code (the modeling that DOES exist, but is NOT wired to eCPS):** `solid_scheds`
  (`library.py:2291-2351`) via `ProbabilisticDenominatorFormula`
  (`.../registry/composite.py:1684-1863`) weights appointments by **per-status show
  probability** (pending 0.30, fut_confirmed 0.80, fut_scheduled 0.50, fut_requested 0.40,
  fut_rescheduled 0.55) — this IS "modeling over expectations," but it currently feeds
  RATE metrics, **not eCPS**.
- **Display:** the report labels `ecps` → **"Expected CPS"** and tooltips `cps` → **"Cost
  Per Show"** (`formatter.py:70-112`) — inconsistent with the metric definitions
  ("Effective cost per schedule", "cost per scheduled appointment").
- **Stakeholder (this interview):** the "e" = "our mathematical way to minimize [poor
  deep-funnel truth] via **modeling over expectations**" — which matches `solid_scheds`
  **semantics, NOT the shipped `effective_scheds` filter.**

→ **The "correct, central" eCPS may be `spend / solid_scheds` (expectation-weighted), not
the shipped `spend / effective_scheds` (filter).** This is exactly the definition the
data-analyst + DRE rites must ratify WITH the stakeholder before the number is trusted.
Do NOT resolve by inference — this is institutional/stakeholder truth.

### GAP-3 — Coverage/population trust (C-2 is load-bearing, not optional)
Because offer-grain spend coverage is partial (GAP-1's ~18.7%), the offer-grain number
needs a **population/coverage floor** or it silently under-counts spend. This revives the
original slate's C-2 (population-receipt guardrail, `POPULATION_WARN_THRESHOLD=0.80`,
ACTIVE-scoped) as a **correctness multiplier the number cannot ship without.**

### GAP-4 — Surface exposure + observability
`cps`/`ecps` are NOT in `PHASE_1_DEFAULT_COLUMNS` of the exports route
(`autom8y-asana .../api/routes/exports.py:110-118`) nor the offer DataFrame schema — they
surface only via explicit join or the HTML report. If the leadership surface is the
exports pipe, cps/ecps must be added AND OBS-EXPORTS-001 (still open) closed. If it is the
existing HTML insights report, it largely exists — pending GAP-1's spend population.

### GAP-5 — Routing constraint (production path)
Offer-grain output must come via the **`/query` SQL-GROUP-BY path, NOT the `/drill`
endpoint** — the multi-fact drill is grain-locked to `(office_phone, vertical)` by design
(SCAR-027 + safe_merge grain-uniqueness invariant; `.../primitives/drilldown/per_fact_merge.py:196,291`).

## Reshaped arc (supersedes the framed C-1 "producer build")

| Was (framed) | Is (ruled) | Rite / repo |
|---|---|---|
| C-1 build a per-offer revenue producer | **Feed the asset↔offer dimension** (asana pushes `AssetEdit` enrollment → populate `assets.offer_id`) | 10x-dev / autom8y-asana |
| (implicit) | **Ratify the eCPS definition centrally** (effective-filter vs expectation-model / `solid_scheds`) | data-analyst + DRE / autom8y-data + stakeholder |
| C-2 guardrail (parallel-cheap, optional) | **Coverage floor is load-bearing** (offer-grain spend is partial) | data-analyst / autom8y-data |
| C-4 obs (parked) | **Surface-exposure + OBS** (add cps/ecps to the leadership surface) | ops / autom8y-asana |

## Evidence grade & honest boundary

`[STRUCTURAL | MODERATE]` — five independent read-only scouts, first-party file:line
reads, cross-checked. **C-0 CODE-HALF is discharged.** The **LIVE-PROD-HALF is NOT**: the
scouts inspected CODE, not live DB state. Still owed to **iris** (live-probe):
1. Is `assets.offer_id` actually empty in prod, and what is the REAL `ad_creatives.asset_id`
   coverage (the 18.7% is an in-code figure)?
2. Is `offer_level_stats` / the `offer` frame actually being requested in prod today, and
   does its offer-grain spend come back null?
3. Is `STATUS_PUSH_ENABLED` on and the SD-02 registry populating (carried from the spike)?

Self-assessment caps MODERATE; the definitional ratification (GAP-2) and live-prod
confirmation belong to the data-analyst/DRE rites + iris + stakeholder, not to this probe.
