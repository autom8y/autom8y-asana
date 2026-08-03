---
type: decision
decision_subtype: uv-p
id: UV-P-6
artifact_id: UV-P-6-real-section-counts
status: accepted
discharged_at: "2026-08-03"
discharged_by: WU-1 O4 leg-2 window-open re-snapshot (principal-engineer, session-20260803-220334-f2a75514)
discharge_receipt: .ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md § O4 leg-2 — window-open re-snapshot (2026-08-03, S8-2 WU-1)
initiative: substrate-v2-epoch
date: "2026-07-30"
registered_by: S8-0 pre-gate hardening (principal-engineer)
owner: WS-B/S8-2
consumer: per-day budget counter (PerDayBudgetLedger) cap calibration
---

# UV-P-6 — real per-entity section counts are UNVERIFIED

## Premise (the open UV-P)

The per-day P10 budget model (`tests/harness/substrate_gate/budget.py`,
`PerDayBudgetLedger`) charges one unit per upstream fetch ATTEMPT and refuses at a
per-day cap. Calibrating that cap to a real API-allowance requires the **real per-entity
section counts** — how many section artifacts a rebuild fetches per (project, entity).
Those counts are **UNVERIFIED**.

The wave-2 → S8 handoff named this as an open UV-P but never REGISTERED it:

> "Per-day budget counter (net-new): ... Real section counts for the model = an open
> UV-P (S2/S4 entry, still open)."
> — `.ledge/handoffs/HANDOFF-wave2-to-s8-cutover-gate-2026-07-29.md:100-102`

This artifact registers it so it cannot silently ride into cap calibration as a guess.

## Why it matters (consumer)

`PerDayBudgetLedger.cap` is a hard REFUSE threshold. If it is set against a guessed
section count, the budget either (a) refuses real work early (cap too low) or (b) fails
to protect the daily allowance (cap too high). The cap must be derived from the real
per-entity section fan-out, not assumed.

## Partial observation from the S8-0 recapture (does NOT discharge)

The S8-0 fixture recapture (`.ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md`)
observed, for the OFFER entity of project 1143843662099250 ONLY:

- **33** section artifacts under `offer/sections/` (S3 LIST).
- **15** distinct `section` names in the assembled offer frame (row_count 4180).

This is a single-entity, single-project first data point. It informs but does **NOT**
discharge UV-P-6, which requires the full per-entity fan-out across the entity classes a
rebuild serves, captured at the S8-2 arm window.

## Discharge route

Derive the real per-entity section counts from the **live S3 section listing** during
the O4 leg-2 window-open re-snapshot at **S8-2 arm** (`aws s3 ls .../<entity>/sections/`
per entity class; no Asana call). Feed the observed counts into the budget counter's cap
calibration. On discharge, flip this artifact `status: accepted` and cite the
S8-2 re-snapshot receipt.

## Owner / status

- **Owner:** WS-B / S8-2.
- **Consumer:** `PerDayBudgetLedger` cap calibration.
- **Status:** `accepted` — DISCHARGED 2026-08-03 by the WU-1 O4 leg-2 re-snapshot (see below).

## Discharge — 2026-08-03 (WU-1 O4 leg-2, S8-2 arm window)

**Method:** live S3 LIST (`aws s3 ls s3://autom8-s3/dataframes/{primary_project_gid}/{entity}/sections/`)
by principal-engineer's own hands, primary_project_gid per `entity_registry.py` /
`project_registry.py`. **0 Asana calls; `aws s3 ls`/`aws s3 cp` + `sts get-caller-identity` only.**
Full evidence, cadence, and calibration arithmetic in
`.ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md`
§ *O4 leg-2 — window-open re-snapshot (2026-08-03, S8-2 WU-1)*.

**Real per-entity section counts (the number this UV-P demanded):**

| governed entity | primary_project_gid | S3 section parquets |
|-----------------|---------------------|--------------------:|
| business | 1200653012566782 | 5 |
| unit | 1201081073731555 | 13 |
| offer | 1143843662099250 | 33 (manifest `total_sections` 34; 1 empty section carries no parquet) |
| contact | 1200775689604552 | 4 |
| asset_edit | 1202204184560785 | 18 |
| process (dynamic; 9 pipelines) | `None` (per-pipeline GIDs) | 25 (sales 4 · outreach 0\* · onboarding 4 · implementation 5 · retention 4 · reactivation 6 · account_error 0\* · expansion 0\* · month1 2) |

`*` **Discharge caveat carried into WU-2:** `process.primary_project_gid` is `None` — process is
served across 9 pipeline projects, and three of them (outreach/account_error/expansion) write their
frame *monolithically* with no `sections/` subdir. **`section_count == 0` ≠ `attempts == 0`** (a
monolithic non-empty frame is ≥1 paginated fetch). The section-count proxy under-counts fetch fan-out
for those pipelines; the budget model must not equate zero sections with zero attempts.

**Cap-calibration inputs produced (for `PerDayBudgetLedger.cap`):**

- Per-governed-sweep fan-out (every-section-verified upper bound) = **~98–102 attempts/sweep**
  (offer 34 + asset_edit 18 + unit 13 + business 5 + contact 4 + process ~25–28).
- Single-rebuild MAX fan-out = **offer @ 34** (cap sanity floor).
- Observed warm-sweep interval ≈ **26 min** (full-substrate sweep 16:04:55→16:31:04 UTC), consistent
  with the C8 ~17–25 min baseline → sweeps/day 48–72.
- Per-day governed attempts (upper bound) ≈ **4 900–7 400/day**; recommended starting cap **~11 200/day**
  (2× headroom for WU-4 paced parity + retry jitter; below the Asana 1500 req/min hard limit).
- **Key WU-2 input still to pin:** does an "attempt" = every-sweep freshness *verify* (→ ~102/sweep)
  or only an upstream *GET* on a hash-DIRTY section (→ far fewer; FIX-1 hash-CLEAN skip)? Both bounds
  are now on record so the cap is derived from data, not a guess — which is exactly what this UV-P demanded.

**asset_edit / process SLA re-ratification (C8 §Ratification hook):** observed cadence (≈26 min sweep)
puts asset_edit and every process pipeline at 2× cadence ≈ 52 min < the provisional 3600 s SLA →
**3600 s CONFIRMED adequate**; the `provisional` qualifier is dischargeable by the operator (no value
change needed).
