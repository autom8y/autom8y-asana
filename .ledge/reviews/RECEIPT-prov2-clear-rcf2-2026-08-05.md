---
type: review
artifact_type: RECEIPT
status: accepted
initiative: substrate-v2-epoch
wave: S8-2 (WU-4 window open)
date: 2026-08-05
session: session-20260803-220334-f2a75514
main_sha: be1ec721 (WU-4 runner #309)
author: main thread (own-hands describe-alarms sweeps)
discharges: RC-F-2 quiet-side evidence (ignition kit preflight #4); C10 two-sided evidence COMPLETE
---

# RECEIPT — PROV-2 dead-man CLEAR on first live sweep (RC-F-2 quiet-side)

## The two-sided C10 evidence, now complete

| Side | Event | Timestamp (UTC) | Evidence |
|---|---|---|---|
| **FIRES** (banked 2026-07-30) | PROV-2 `asana-PROV-2-heartbeat-absence` fired within ~90s of the DP-4a apply, exactly as predicted — the dead-man alarming on a dark (never-scheduled) evaluator | 2026-07-30T13:57:33Z | describe-alarms own-hands (S8-2 preflight, 2026-08-03): ALARM since 2026-07-30T13:57:33Z |
| **HELD** | Six days continuous ALARM — no false OK, no flap — while no sweep mechanism existed (G2 recon: `ScheduledProvabilityEvaluator` had no prod scheduler) | 2026-07-30 → 2026-08-05 | same sweeps, 2026-08-03 + 2026-08-05 |
| **QUIET** (this receipt) | First live parity sweep (WU-4 runner, in-process G2-option-a drive) emitted `EvaluatorHeartbeat` (namespace `Autom8y/SubstrateProvability`, `environment=production`, run_id `6ff8683e854e494c826ccfc1090141d7`) → PROV-2 transitioned **ALARM → OK** | heartbeat 2026-08-05T09:19:45Z; **OK at 09:23:06Z** | sweep summary JSON (session scratchpad wu4) + describe-alarms own-hands 09:2xZ |

**RC-F reading:** the alarm asserts PROVABILITY of the evaluator's liveness, not liveness
itself — it alarmed the entire time the evaluator could not prove it was running, and went
quiet within one evaluation period of the first real heartbeat. It cannot read green while
broken in either direction on this axis. This is the quiet-side half the ignition kit
ordered recorded (preflight #4); with the 2026-07-30 fires-side already banked, **C10's
two-sided evidence is COMPLETE** for PT-03 Q6.

## Concurrent PROV-1 / PROV-4 ALARM — known-cause, fail-loud-correct, cure in flight

The same first sweep emitted `unprovable_count=1` and `expected_set_mismatch_count=1`
(completeness 100.0, expected_count 1): the registry side expects the offer artifact but
the v2 store is EMPTY — the sweep's v2 leg errored before publishing (polars
schema-inference ComputeError, receipted `offer-1143843662099250-091945246412-ec83614f.json`,
outcome=error; DELTA in flight). PROV-1 → ALARM 09:23:24Z, PROV-4 → ALARM 09:23:25Z.

**Disposition:** these alarms are TRUE — v2 genuinely cannot prove a number it has not
published. This is the refuse-loud posture working (P2), not an anomaly: the anomaly would
be silence. Ticket-action only (paging unarmed per DP-4a). Expected clear: the first
successful sweep publishes the offer artifact → next PROV emission zeroes both metrics.
Escalates to the operator-interrupt triad ONLY if they fail to clear after the DELTA-cured
sweep. PROV-3/5/6 remained OK throughout (5 has `ExpectedCount=1` ≥ floor — the
window-1 expected-set choice validated).

## Budget/receipt state at this receipt

Day ledger `.sos/wip/parity/budget-ledger-2026.json`: `{"2026-08-05": 663}` of cap 11,200
(≈6%). One receipt written (the error receipt). LEG A v1 (served-definition active_mrr,
live) = **$76,285.00** — the first live derivation of the pythia-ruled referent; v2 leg
pending the DELTA. First-sweep import failure (PYTHONPATH) preceded this run with ZERO
budget spent and zero prod touches — fail-closed held at every layer.
