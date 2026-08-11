---
type: handoff
artifact_type: HANDOFF
subtype: daily-parity-digest (CATCH-UP: days 1-7) + CEILING SURFACING PACKET
initiative: substrate-v2-epoch
wave: S8-2 (P5 live-parity window)
date: 2026-08-11
window_clock_start: 2026-08-05T09:19:45Z
hard_ceiling: 2026-08-12T09:19:45Z
status: accepted
supersedes_gap: no daily digests were authored 2026-08-06..2026-08-10 (G5 law breached — recorded here, not papered over)
authored_by: main thread, from the six-lens reorientation swarm (workflow wf_7d35d1fd-a20, 2026-08-11)
---

# S8-2 PARITY DIGEST — catch-up (days 1–7) + MANDATORY ceiling surfacing

**MISSION (verbatim):** "every business number the asana dataframe substrate serves is provably
current or loudly refused — delivered by a substrate-v2 designed whole and small enough that its
correctness is legible, with v1 deleted and the doctrine packaged so any autom8y-* repo can
reconstruct the same guarantees as a template application, not a research project."
**PREDICATE (verbatim, NOT "PRs merged"):** "Verified-realized" = P5 cutover-gate receipts clean
(adversarial fixture replay + bounded live-parity window, every divergence explained) AND a
rite-disjoint attester re-derives active_mrr by their own hands matching live Asana within
freshness-SLA across >=2 warm cycles AND v1 planes/bridges/flags enumerate to zero AND doctrine
landed at fleet-constitution level.

## ⛔ THE SURFACING (rubric §2/§4 — operator decision REQUIRED before 2026-08-12T09:19:45Z)

- Elapsed at authoring: ~6d 1h. Remaining to the hard ceiling: **< 23 hours**.
- Warm cycles observed in parity: **ZERO** (no sweep ran after 2026-08-05; observation #1 never
  served; all 10 receipts carry `v2 = null`).
- P5 conjunct 1 (≥2 DISTINCT warm cycles) is a **hard fail and mathematically unreachable**
  inside the remaining window — no sweep cadence rescues it.
- The rubric prescribes exactly this case:
  - §2 (`RULING-pythia-s8-2-adjudication-rubric-2026-08-03.md:74`): a window that cannot complete
    the ≥2-cycle + ~3-day-floor requirement within the original 7-day ceiling **"converts from
    auto-close to an operator-surfaced decision (extend-or-hold)."**
  - §4 (`:136`): "Never calendar-close thin; never fake-complete. A ceiling breach converts the
    auto-close to an operator decision."
- **This document is that surfacing.** The window does NOT auto-close and is NOT fake-completed.
  The operator's word decides: **EXTEND** (restart the clock under the preconditions below) or
  **HOLD** (window closed un-passed; no cutover; corridor awaits re-ignition).

## Day 1 full ledger (2026-08-05 — attempts 0–10, now completely on record)

| # | UTC | Outcome | One-line cause | Charged |
|---|---|---|---|---|
| 0 | 09:12 | env-fail (zero touch) | PYTHONPATH missing | 0 |
| 1 | 09:19:45 | error (receipted) | **WINDOW CLOCK START.** LEG A v1=$76,285 live; v2 died on polars bare-inference (→ #313) | 663 |
| 2 | 11:03 | error | AWS session creds expired pre-touch | 0 |
| 3 | 11:48 | refused-staged_rejected | null value cols; root: missing bootstrap → later disproven as sole cause | 666 |
| 4 | 12:04 | error | creds expired (~15-min validity tokens) | 0 |
| 5 | 12:18 | refused-staged_rejected | nulls; root: fresh-per-page store → parent-refetch storm | 661 |
| 6 | 12:18+ | refused-fetch_refused | C16: 3/34 sections timed out (shared-store cure #1 landed; crossings ↓456) | 456 |
| 7 | 13:18 | refused-staged_rejected | nulls; "dedup lost" — later resolved: 588 IS the true unique-parent cardinality | 661 |
| 8 | 13:22 | refused-staged_rejected | instrumentation run: extraction near data-true floor; validator denominator defect exposed | 661 |
| 9 | 13:57 | refused-staged_rejected | ancestor pre-warm landed (5,661 tasks; parents 588→297); floor still whole-frame | 440 |
| 10 | 16:19:51 | **refused-staged_rejected `['offer_id']` ONLY** | post-#318 floor fix (merged 16:12): stack proven end-to-end; residual = the 2-offer DATA INCIDENT | 440 |

Budget day-1: **4,648 / 11,200 (41.5%)**, honest at every layer; ledger `{"2026-08-05": 4648}`,
zero entries since. Receipts: 10 files under `.sos/wip/parity/receipts/2026-08-05/`.

## ⚑ Standing PROMINENT flag (rubric §3, carried from day 1)

O4 leg-2 corpus drift −$5,000/−6.17% — {delta+explanation} EXPLAINED-BENIGN, exemplar re-pinned
(#303). Label discipline: 3-section sums are "exemplar aggregates," never active_mrr
(RULING-pythia-f305-1).

## The single serving blocker (operator-actionable, ~2 minutes in Asana)

Two real classifier-active offers missing their **Offer ID** custom field (operator ruled the
field expected-present, 2026-08-05):
- `1213234683414144` — "$75 Brain & Body Consultation" (OPTIMIZE QUANTITY - Request Asset Edit)
- `1216414611774709` — "$37 New Patient Chiropractic Exam & Spinal Screening" (OPTIMIZE QUANTITY - Update Offer Name)

QA receipt of record (`QA-s8-2-budget-hardening-pr301-2026-08-03.md:834-845`): "fix the two
offers' data → the next sweep's floor passes → observation #1 serves." This is substrate-v2's
first live catch — a true data wound v1 serves through silently.

## Dark-days record (2026-08-06 → 2026-08-11)

No sweeps, no digests (G5 breach — this artifact is the honest repair), no corridor activity.
The Claude Code process exited post-day-1; the corridor session `session-20260803-220334-f2a75514`
auto-parked. Parallel workstreams landed #319/#321–#334 (scheduling-stratum / enrollment-intake
arc): **zero bytes on the substrate/metrics/cache/clients/offer-schema seams** (verified per-seam,
reorientation swarm LENS 5) — the sweep composition HOLDS at `55f81e0b`. Test GREEN at tip
(run 31442380824, 2026-08-10). PROV-1/PROV-4 were last read ALARM (2026-08-05 09:23Z, truthful
empty-store alarms); PROV-2 OK (RC-F-2 banked); no read since — re-verify at restart.

## Restart preconditions (if the operator's word is EXTEND)

1. **Rite**: `ari sync --rite=10x-dev` + CC restart — ACTIVE_RITE is currently `sre`; corridor
   execution under it violates T2 (shape :723-734, risk R5 CRITICAL). No sweep before this.
2. **Data**: the 2 Offer IDs populated (above).
3. **Re-verify**: PROV-1..6 states (`aws cloudwatch describe-alarms --alarm-names asana-PROV-1-unprovable
   asana-PROV-2-heartbeat-absence asana-PROV-3-incomplete asana-PROV-4-expected-set-mismatch
   asana-PROV-5-expected-floor asana-PROV-6-future-dated-proof --region us-east-1`).
4. **Runner**: the session-scoped sweep script was reaped with its scratchpad. Re-author from the
   records: the LIVE INVOCATION RUNBOOK (QA receipt §PR-#309 section) + the five-invariant
   composition catalog (memory + this file's ledger) + the merged cures (#313, #318). All 16
   seams verified byte-identical at `55f81e0b`.
5. **Clock**: per rubric §2 the restarted count begins at the first post-restart warm cycle; the
   original ceiling is breached, so the EXTEND word must set the new bound (the rubric's
   ceiling-from-original-arm rule was written for wound-restarts; a dormancy-driven extension is
   the operator's call to define — recommend: fresh 7-day ceiling from the EXTEND word, floor
   unchanged at ~3 days).

## Un-entangled (recorded, not actioned here)

The July-dated untracked `.ledge/` artifacts (fleet-delegation R4 packet, F1a procession tail,
floodgates DEFECT et al.) belong to parallel initiatives — committed separately or left, per
their own arcs. The `warmer_cache_degraded_alarm.tf` untracked file documents a 07-21 CLI-applied
alarm (unrelated). UNIT_HOLDER_SCHEMA v1.1.0 (+google_cal_id) is off-seam.
