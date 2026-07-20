---
type: decision
artifact_role: adr
slug: adr-substrate-freshness-ownership
status: accepted
rite: sre
date: 2026-07-13
aws_account: 696318035277
aws_region: us-east-1
baseline: origin/main f713dd30
supersedes_intent_of: TELOS-asana-substrate-freshness-2026-07-13.md (C2 realization)
evidence_grade: MODERATE (self-authored; STRONG requires the rite-disjoint critic)
discipline: "Rungs named, never rounded: authored < emitting < detecting-via-canary < teeth-proven < merged < imported/applied < protecting-prod. Two-sided teeth or it is not detection."
---

# ADR — Asana substrate-freshness: owned class, SLO, and per-GID detection

## Status

**Accepted.** The freshness-class ownership is realized as an owned surface with an SLO and a
**live, teeth-proven, per-GID detection** (AL-5), codified in IaC. Rung at wave close:
**detecting-via-canary + teeth-proven + TF-merged-pending** — NOT protecting-prod (paging +
`terraform import`/apply are confirm-first, and the CI apply lane is wedged).

## Context

Third eruption of one class — `CACHE_NOT_WARMED` P0 (2026-06-08) → warmer stall (2026-07-07) →
the 2026-07-10 429 storm. The operator ruled it an **owned class with a standing owner + SLO**
(telos P3). The founding ticket — the 429 storm — is **attributed** in
`ATTRIBUTION-RECEIPT-asana-429-storm-2026-07-13.md`: a single shared bot PAT over-subscribed by
per-process-only AIMD with no cross-consumer arbitration.

**The design constraint (SCAR-015 blind spot), LIVE-proven:** on 2026-07-13 the entity-level
dead-man `offer:warm_complete:age_seconds{entity_type="offer"}` read **~11,336s ("healthy")**
while the ASR offer GID `1143843662099250` sat **74,118–86,849s (~24h) stale** on the same
instants. Per-GID starvation is **invisible** to entity-level absence. Any detection that does
not see the GID axis is theater.

## Decision

### 1. The owned surface

The **entity frames the autom8y-asana service serves from its stale-while-revalidate LKG cache**
(`cache/integration/dataframe_cache.py`), keyed **per project GID**. The offer frame lineage
(`entity_type="offer"`, cache-only, `primary_project_gid` registered at
`core/entity_registry.py`) is the inaugural member; the ASR GID `1143843662099250` is the
founding registered GID.

### 2. Named owner

The **autom8y-asana SRE lane** (this repo's `terraform/services/asana/` observability suite +
the cache-warmer lanes). The class is homed here, not in ASR — ASR is a **consumer** of the
served frame, not its producer.

### 3. The SLO (thresholds honest per the freshness semantics)

- **SLI (per registered GID):** served LKG frame age, from the `dataframe_cache_memory_lkg_serve`
  serve event (`extra.age_seconds`).
- **SLO (incident cure bar):** frame age **< 3600s** for a registered GID, sustained ≥2 warm
  cycles. This is the ASR arc's resume gate.
- **Honesty note (non-negotiable):** 3600s is **LOOSER** than the code's own FRESH threshold
  (offer TTL 180s; STALE onset **540s** = 3×180, `config.py:137` + `dataframe_cache.py:1247-1258`;
  the 900s figure is the default-TTL value, not offer's). It also sits well under the offer LKG
  serve ceiling of **16,200s** (freshness contract, `config.py:304`, applied at
  `dataframe_cache.py:684-686`). A frame at <3600s is "served-and-under-an-hour-old, still
  code-STALE," **not** "fresh." The 3600s bar is the incident recovery target, to be **tightened
  toward the TTL post-cure** (DEFER-registered).

### 4. The detection law (per-GID, cardinality-bounded) — REALIZED

Per-GID detection with the cardinality guard that forced the *class* metric to stay
entity-level: **register the GIDs that carry a freshness contract; one metric filter + one alarm
per registered GID.** The filter pattern restricts to the GID, so the metric only ever emits the
registered dimension values — bounded by construction.

**Live realization (AL-5), receipts:**
- Metric filter `asana-AL5-offer-frame-age-1143843662099250` on `/ecs/autom8y-asana-service`,
  pattern `{ ($.event="dataframe_cache_memory_lkg_serve") && ($.extra.project_gid="1143843662099250") }`
  → emits `OfferFrameAgeSeconds{project_gid}` in namespace `Autom8y/AsanaSubstrateFreshness`.
- Alarm `asana-AL5-offer-frame-stale-1143843662099250`: `Maximum > 3600` over 2×300s,
  `treat_missing_data=notBreaching`, **NON-PAGING** (`AlarmActions=[]`). **Live-emitting:** the
  alarm ingested its first real serve datapoint (3,277.9s @2026-07-13T20:02Z → `OK`,
  StateReason "[3277.9] was not greater than the threshold (3600.0)") — the full
  filter→metric→alarm pipeline is proven on production traffic, not only on the canary.
  (When no serve occurs it honestly returns `INSUFFICIENT_DATA` — see §6 residual.)
- **Two-sided teeth PROVEN (G-THEATER-clean — the RED is a broken INPUT, never a prod-code
  defect):**
  - Live canary: RED synthetic input `age=7200` → **ALARM** @19:45Z; GREEN `age=300` → **OK**
    @19:48Z (canary torn down).
  - Real-log backtest (the ASR GID's own history): age by 3h bin 07-11 12Z=**74,118**, 07-12
    00Z=**85,482**, 07-13 12Z=**86,849** (all > 3600 → would ALARM; the 86,849 reproduces the
    handoff's 86,848s receipt), vs 07-10 21Z=3,380 and 07-13 18Z=3,439 (< 3600 → OK). During the
    RED bins the entity-level metric read **8.4–11.3ks "healthy"** — **the SCAR-015 discrimination,
    proven on real simultaneous data.**
- Codified: `terraform/services/asana/observability_alarms.tf` **AL-5** (`for_each` over
  `var.substrate_freshness_gids` default `["1143843662099250"]`; `aws_cloudwatch_log_metric_filter`
  + `aws_cloudwatch_metric_alarm`; `al5_actions` gated on `paging_armed_alarms` containing
  "AL-5"). `terraform validate` = **"Success! The configuration is valid"**; `fmt` clean. Live
  resource names **match** the TF names (import-ready).

### 5. C4 — warmer dead-man disposition: RETIRE-and-supersede

`autom8-asana-cache-warmer-DMS-24h` has been **ALARM / ActionsEnabled:false since 2026-06-04**,
watching `LastSuccessTimestamp` (SampleCount) in namespace `Autom8y/AsanaCacheWarmer`. Live
`list-metrics` on that namespace returns **`[]` — the namespace is EMPTY**: the current warmer
(running 28×/6h, completing 34/34 section writes) **no longer emits that metric**. The dead-man
is **orphaned** — keyed on a dead metric, not detecting a real warm failure.

- **Naive re-arm is WRONG:** it would immediately PAGE (actions wired to the paging SNS
  `autom8y-platform-alerts`) on the orphaned metric → a false page → trained-ignore (the
  platform-alerts channel already carries 70–170 msgs/day).
- **Disposition: RETIRE and supersede** with AL-5 (per-GID freshness — the *real* signal) plus
  the AL-6 warm-liveness candidate (§6). The retire touches paging-SNS topology → **USER lever**;
  the exact command is surfaced in `observability_alarms.SURFACED.md`, not fired here.
- **Rung:** diagnosed-orphaned → **disposition-surfaced** (NOT retired — retirement is the
  operator's).

### 6. AL-6 candidate (DEFER-registered, not built) — the residual blind spot

AL-5 emits age **only when the frame is served (queried)**. A registered-but-**unqueried** GID
produces no datapoint (hence AL-5's honest `notBreaching`/`INSUFFICIENT_DATA` when the ASR
schedule is off). A starved-**AND**-unqueried GID is therefore still invisible to AL-5 alone. The
durable cure pairs AL-5 with an **AL-6 warm-liveness** dead-man (per-registered-GID
last-successful-**warm** timestamp, independent of serve traffic). AL-6 is **specified here,
watch-registered, and NOT built this wave** (it needs a warmer-side per-GID success emit —
10x-dev/platform work).

## Consequences

- The SCAR-015 recurrence (a silent GID-blind "all fresh" signal) — the telos's **intolerable
  (a)** — is now caught for registered GIDs, proven two-sided.
- Adding a GID to the class = add it to `var.substrate_freshness_gids` (one line) → a filter +
  alarm materialize on next apply. Zero-cardinality-blowup by construction.
- **G-PROPAGATE (watch-registered):** the *per-GID freshness detection pattern* (registered-GID
  metric-filter + alarm) is **fleet-generic** — every autom8y service with a per-entity warm cache
  has this blind spot. A **satellite-promotion candidate** to shared knossos altitude is
  registered (`@satellite-primitive-promotion`); the offer-frame *content* stays asana-scoped, the
  *pattern* promotes.
- Re-arm coordination: the AMP `slo_offer_freshness` re-arm is the **ASR arc's** rung, gated on
  its (a)/(b)/(c)+soak spec (monorepo PR #1018 `e7024c9c`). AL-5 does **not** re-arm it — it is a
  distinct CloudWatch surface; coordinate, do not collide (non-ruling #2).

## Rung ledger (un-rounded)

| Item | Rung at wave close |
|---|---|
| AL-5 per-GID detection (live canary) | detecting-via-canary + teeth-proven + live-emitting (first prod datapoint 20:02Z) |
| AL-5 IaC (`observability_alarms.tf`) | authored + validated → **merged-pending** (CI apply wedged; import confirm-first) |
| AL-5 paging | **NOT armed** (authored, `arm_paging` default false) — confirm-first |
| C4 warmer DMS | diagnosed-orphaned → **disposition-surfaced** (retire = USER lever) |
| AL-6 warm-liveness | **specified + DEFER-registered**, not built |

Nothing here claims `protecting-prod`.
