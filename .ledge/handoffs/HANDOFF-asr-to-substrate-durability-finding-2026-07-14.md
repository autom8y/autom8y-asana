---
type: handoff
status: proposed
handoff_type: assessment
from: ASR arc (account-status-recon session) — rite-disjoint W3-receipt verifier
to: dedicated asana-substrate session
date: 2026-07-14
re: HANDOFF-asr-to-substrate-session-2026-07-13.md (W3 receipt contract)
---

# HANDOFF — ASR arc → substrate session: the C3 cure is TRANSIENT, receipt NOT met

## Verdict (rite-disjoint, per the W3 receipt contract)
The C3 cure BIT hard but does **not HOLD**. The W3 receipt (GID `1143843662099250`
age <3600s across ≥2 consecutive warm cycles, sustained) is **NOT met** — it was
transiently touched ~03:00–04:30Z then regressed. Do not close C3 on the dip.

## The overnight evidence (live CloudWatch, 2026-07-14, all read-only)
`Autom8y/AsanaSubstrateFreshness OfferFrameAgeSeconds{project_gid=1143843662099250}`, Maximum/300s:

| Time (UTC) | Age (s) | Read |
|---|---|---|
| 2026-07-13 23:05 | 3717.8 | just over the bar |
| 2026-07-13 23:05→00:30 | 3594.8 → 1344.4 | **cure biting — dipped to ~22min** |
| 2026-07-14 03:00 | 2830.0 | fresh |
| 2026-07-14 05:00 | **14229.4** | **re-staled to ~4h** |
| 2026-07-14 05:00 → 08:51 (now) | *no emission* | sparse/absent ~4h |

- The frame **oscillates 1344s ↔ 14229s** — the warm succeeds periodically but the
  429 storm re-stales it between cycles. This is the arc's recurring "a self-heal is
  not a fix" signature.
- **Gap set REGREW to full**: `hierarchy_gap_warming` `parent_gids_count` was shrinking
  3291→676 last night; the only warm event in the last 3h is a single
  `hierarchy_gap_warming_failed` with `parent_gids_count: 3291` — the incremental
  progress was wiped; the gap-fill lane is still 429-starved.

## ★Instrument defect in AL-5 (surface + fix on your side)
`asana-AL5-offer-frame-stale-1143843662099250` reads **OK right now while the frame is
~4h stale.** Config (live): `OfferFrameAgeSeconds > 3600, EvaluationPeriods=2, Period=300,
TreatMissingData=notBreaching`, but emission is **~hourly-sparse**. Two consecutive 300s
periods can essentially never both carry a breaching datapoint, and missing periods read
notBreaching → **AL-5 is structurally blind to this sparse metric and under-fires.** It
cures SCAR-015's *granularity* blindness but inherits a *sparsity* blindness. Fix options:
match Period to the emission cadence (e.g. 3600s), or use `M out of N` with a wider window,
or emit the age metric continuously. Until fixed, AL-5 OK ≠ frame fresh — read the metric
datapoints, not the alarm state.

## What this means for the keystone
C3 (warm-cadence improvement) is necessary but **insufficient** under the sustained storm —
the durable cure is the one you surfaced as pending: **F1a budget-partition** (cross-consumer
Asana rate-budget arbitration; "measured sizing pending"). The oscillation is the evidence
that per-cycle warming can't outrun the storm; the storm needs partitioning, not just a
faster warmer. If C1 attribution pointed at a cross-initiative consumer (the EBI hypothesis),
F1a sizing is likely an operator-adjudicated cross-initiative decision, not asana-local.

## The receipt the ASR arc still waits on (unchanged)
Two consecutive `OfferFrameAgeSeconds{GID}` datapoints <3600s **plus** a
`hierarchy_gap_warming_partial|complete` event with `fetched>0` — SUSTAINED, not a dip.
Nothing is owed by the ASR arc here; this is a report from the receipt-verifier that the
cure needs a durability follow-through.

## ★RATIFIED F1a MANDATE (operator interview #2, 2026-07-14 — BINDING in-arc per R5 portability)

The operator ratified the F1a posture — **PROTECTED FLOOR, MEASURED** (ledger:
`services/account-status-recon/.ledge/decisions/RULINGS-asr-operator-interview-2026-07-14.md`
R-2, under the new owned-commons + yield-default principle P-B):

1. The shared Asana API budget is the arc's **first registered commons**, owned by THIS
   (substrate) session, with the arbitration default: internal consumers yield to client-felt;
   **operator adjudicates ties**.
2. The substrate warmer gets a **PROTECTED-MINIMUM quota** — blanket-yield is overruled
   because substrate freshness is commons-SERVING (the offer frame is upstream of client-felt
   surfaces); an oscillating substrate starves everyone eventually.
3. The floor's **SIZE comes from your pending F1a measurement** ("measured sizing") — proceed
   with that mandate; genuine trade-offs against client-felt consumers escalate to the
   operator, not adjudicated locally.
4. Sequencing note: the ASR arc will fire an opportunistic PROOF canary on the next transient
   fresh window (ratified two-canary doctrine R-1) — it needs no coordination from you and
   mutates nothing of yours; the CLEAN canary that follows your durable cure is the one that
   consumes your sustained W3 receipt.
