---
type: review
status: accepted
artifact_id: EVIDENCE-tick-terminal-census-2026-08-12
initiative: asana-native-insight-delivery / offers-freshness-axis-contract
date: 2026-08-12
run_by: main thread (operator-authorized overnight campaign)
grade: STRONG
method: CloudWatch Logs Insights, read-only, zero mutations
---

# EVIDENCE — terminal-event census per ASR tick since the cure deployed

Run to discharge the falsifier pythia named in its visionary consult
(2026-08-12T20:27:35Z): *"one Logs Insights query over 2026-08-11T20:00Z→now,
counting terminal events per tick. If every tick terminates at
`readiness_gate_abort`, the claim closes at STRONG and you can strike the
'separate outage' line. If any tick shows a different terminal cause, I am wrong
and there is a real second incident."*

## Method

```
log group : /aws/lambda/autom8y-account-status-recon
window    : 2026-08-11T20:00:00Z → 2026-08-12T20:36:20Z  (epoch 1786478400 → 1786566980)
query     : fields @timestamp, @message
          | filter @message like /Aborting|readiness_gate_abort|verdict_published|
                                  reconciliation_complete|REPORT|posted|Slack/
          | sort @timestamp asc | limit 500
queryId   : bf15fa66-2ea9-4622-ac30-b82fcb8e4dbc      status: Complete      rows: 35
```

Read-only. No mutation, no invoke, no write of any kind.

## Result — 7 ticks, 7 identical terminal causes

Seven invocations in the window, one per 4h, matching `cron(0 */4 * * ? *)`.
**Every one terminates at `readiness_gate_abort`.** Zero ticks show any other
terminal cause. Each carries a distinct `invocation_id`, so these are seven
independent runs, not one run counted seven times.

| # | tick (UTC) | `invocation_id` | terminal cause | offers staleness reported |
|---|---|---|---|---|
| 1 | 2026-08-11 20:01 | `f418d9a9…` | `readiness_gate_abort` | 1385 min |
| 2 | 2026-08-12 00:0x | `aba84962…` | `readiness_gate_abort` | 271 min |
| 3 | 2026-08-12 04:0x | `d095e10c…` | `readiness_gate_abort` | 511 min |
| 4 | 2026-08-12 08:01 | `605a2ccb…` | `readiness_gate_abort` | 751 min |
| 5 | 2026-08-12 12:0x | `d74a5321…` | `readiness_gate_abort` | 923 min |
| 6 | 2026-08-12 16:0x | `f990af8e…` | `readiness_gate_abort` | 364 min |
| 7 | 2026-08-12 20:0x | `7b3c8cdb…` | `readiness_gate_abort` | 507 min |

Abort threshold reported in every message: **120 min** — consistent with the
deployed `3600s × 2.0 warn_multiplier = 7200s`.

## Finding 1 — pythia's correction (a) is CONFIRMED at STRONG

**There is no separate ASR outage.** The ~24h of "has not successfully
reconciled" is the **ruled P-3 posture**, dated to the first tick after the cure
landed, exactly as pythia reconstructed it from three receipts it had in hand:
last `PipelineReadiness{Status=pass}` 2026-08-11T19:34Z → cure image `c21cab9`
to ECR 19:54:44Z → first `readiness_gate_abort` 20:01:22Z.

Pythia graded its own reconstruction MODERATE on ~2 of 6 ticks sampled. The
census covers **7 of 7**. The grade rises to **STRONG**.

**Consequence**: the line in `.sos/wip/STAGE1-observability-truth-2026-08-12.md`
(:573-574) flagging *"an ASR reconciliation outage, separate from and larger than
this work item… NOT triaged here — routing it is owed to the operator"* is
**OVER-CALLED and is hereby struck**. It is not a separate incident and it is not
an operator triage item. The detector was right, the reading of it was wrong.
No operator action is owed.

## Finding 2 — R-08 closes from ARMED to OBSERVED, at zero risk

S3 (`RAILS-insight-delivery-verified-2026-08-12.md`) graded the `#account-health`
Slack rail **VERIFIED-IN-CODE-AND-TERRAFORM**, deliberately *not* "verified
live", and carried **UV-P-S3-4** for the gap between *armed* and *observed*.

This census closes that gap **without posting anything**. Every one of the seven
ticks emits, on the live rail:

```
{"channel": "#account-health", "block_count": 3, "abort_reason": "readiness_gate_abort",
 "invocation_id": "…", "event": "slack_post_attempt"}
{"channel": "#account-health", "block_count": 3, "abort_reason": "readiness_gate_abort",
 "invocation_id": "…", "event": "report_posted"}
```

`event: slack_post_attempt` **and** `event: report_posted`, naming `#account-health`
explicitly, 6×/day, right now, during the pause. **UV-P-S3-4 is DISCHARGED by
observation.** R-08's rung rises to **VERIFIED-LIVE**.

> ### ⚠ CORRECTION to this document (2026-08-12T21:4xZ) — my own error, same class
>
> This section originally quoted the event as **`slack_post`**. **There is no
> such event.** Re-extracting every `"event"` value from the retained query
> result gives exactly four: `readiness_gate_abort`, **`slack_post_entered`**,
> **`slack_post_attempt`**, `report_posted`.
>
> **How it happened**: the display of my own query truncated each message at 165
> characters, mid-token, at `…"event": "slack_pos`. I completed the token by
> inference rather than re-reading the retained JSON. **A true observation
> carrying a false transcription** — structurally the identical error class PT-01
> diagnosed across three of four spine seats, committed by the coordinator, in a
> receipt staged for verbatim inheritance into an operator briefing. Caught by
> PT-02, not by me.
>
> **The finding is unaffected and is slightly strengthened**: the real sequence
> is `slack_post_entered` → `slack_post_attempt` → `report_posted`, a three-stage
> emission in which `report_posted` sits *after* the wire call. The S3 critic
> independently established that `report_posted` cannot fire under `dry_run`
> (which returns at `orchestrator.py:1246`, before the `try` at `:1247`) and
> cannot fire on Slack's `ok:false` (`client.py:187` raises). So the rung stands
> at VERIFIED-LIVE on a better-specified receipt than the one first written.

This also independently confirms frame SVR-8 and pythia's "the rail is already
warm" item: the delivery mechanism the insight initiative wants to establish
already exists, already runs on a cadence, and is **one payload change from
carrying a readout** — not one build away.

## Finding 3 — the staleness series is non-monotonic, which is itself a receipt

`1385 → 271 → 511 → 751 → 923 → 364 → 507` min.

This does **not** ratchet. It falls 1114 min between ticks 1 and 2, climbs at
almost exactly +240 min per 4h tick across 2→3→4→5 (pure aging, no new content),
falls again to 364 at tick 6, then climbs to 507.

Two things follow:

1. **The gate is reading a genuinely moving content axis.** A cache-put-anchored
   quantity — the pre-cure defect — could not fall by 1114 min between two
   consecutive scheduled builds. This is independent live corroboration of the
   `ATTEST-rel6` REALIZED-MECHANISM finding, from a different direction (organic
   series shape rather than cross-tick discriminator).
2. **The sawtooth W-1 measured is visible in production in real time.** The
   inter-cohort spread is not an artifact of the 29-day reconstruction; it is
   what the axis does live. The two drops are new content landing; the +240/4h
   runs are the axis aging untouched.

## What this evidence does NOT establish

- It does not make the gate passable. Every tick still aborts, correctly, and the
  P-3 posture stands unchanged. Nothing here touches ADR-007 or the K-lane.
- It does not speak to *why* offers content goes quiet for 15h — only that the
  gate reports it faithfully.
- It samples one 24.6h window. The claim "no separate outage" is scoped to that
  window, which is the window in which the "separate outage" was alleged.
