---
type: decision
decision_subtype: decision-packet
artifact_id: DP-4a-READY-provability-alarms-apply
id: DP-4a
title: "DP-4a-READY — apply the substrate-v2 provability alarm suite (PROV-1..6) before the parity window arms"
created_at: "2026-07-30"
author: main-thread orchestrator (S8 corridor session session-20260730-141905-058c4fd7)
status: proposed
lifecycle_status: READY-FOR-OPERATOR
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S8
door: "#4 (charter one-way-door register) — terraform apply; operator-reserved (P9)"
blocks: "S8-2 (bounded live-parity window) — alarms must be LIVE during the window (C10: >=1 observed FIRED alarm is cutover evidence)"
---

# DP-4a-READY — provability-alarms terraform apply (PROV-1..6)

> **Operator lever. HALT-holder for S8-2.** The parity window does not arm until this
> applies. Everything below is surfaced, not executed (P9: terraform applies are
> operator-reserved regardless of access).

## What applies

`terraform/services/asana/substrate_v2_provability_alarms.tf` — the RC-F suite,
AUTHORED-NOT-APPLIED since PR #282 (QA-s6 GO after the dead-metric fix):

| Alarm | Metric | Meaning |
|---|---|---|
| asana-PROV-1-unprovable | UnprovableCount > 0 | provability sweep found a stale/corrupt/missing artifact — fires ON unprovability, silent on all-provable |
| asana-PROV-2-* (dead-man) | evaluator heartbeat absent | the dead-man DONE RIGHT (no-data alarm on the sweep's own heartbeat) |
| asana-PROV-3/4/5 | sweep-family metrics | per tf :104-246 |
| **asana-PROV-6-future-dated-proof** | **FutureDatedProofCount > 0** | **the D6b binding — ALREADY AUTHORED in the suite** (tf :248-264). No new terraform needed for D6b; this apply discharges it. |

## The exact lever (operator hands)

```bash
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/terraform/services/asana
terraform plan  -target=aws_cloudwatch_metric_alarm.prov1_unprovable \
                -target=aws_cloudwatch_metric_alarm.prov2_heartbeat_deadman \
                -target=aws_cloudwatch_metric_alarm.prov3_staleness \
                -target=aws_cloudwatch_metric_alarm.prov4_coverage \
                -target=aws_cloudwatch_metric_alarm.prov5_refusal \
                -target=aws_cloudwatch_metric_alarm.prov6_future_dated_proof
terraform apply <same -target set>
```

(Resource names per the tf; verify with `terraform plan` first — if your standing
apply pipeline for this dir applies whole-dir, that is equivalent: the only
un-applied resources in this file are the PROV set. Run through the SAME root/
pipeline you used for `observability_alarms.tf` (AL-5) — this file lives beside it
by design.)

**Variables:** safe defaults hold — `arm_paging=false`, `paging_armed_alarms=[]`
(every alarm lands in TICKET mode, no pager). **Recommendation: apply with
defaults; arm paging for NONE during the window.** C10's "observed FIRED alarm"
evidence is the CloudWatch state transition, not a page.

## Sequencing fact you must expect (not a defect)

**PROV-2 (dead-man) will go ALARM shortly after apply** — the v2 provability
evaluator is not yet scheduled anywhere (it is dark-built code; its heartbeat
only exists when sweeps run). This is the dead-man PROVING it is not the
DMS-24h class (a dead-man that actually fires on absence). It clears when the
S8-2 window begins driving evaluator sweeps. We will record the transition as
C10 evidence (alarm-fires side) plus the RC-F-2 quiet side once sweeps run.
If an always-red alarm in the console is unacceptable for the days before S8-2
arms, apply DP-4a immediately before arming instead — the constraint is only:
**LIVE before the first parity fetch.**

## Framing-ambiguity resolution (of-record)

The frame/shape called this "[CROSS-REPO] parent-repo terraform" (shape :237,
frame T5). What LANDED (PR #282) is **in-repo**:
`autom8y-asana/terraform/services/asana/substrate_v2_provability_alarms.tf`,
beside the already-applied `observability_alarms.tf`. **Of-record: the in-repo
landing IS the artifact; the parent-repo framing is superseded by the landed
reality** (same pattern as AL-5). DP-4b (warmer-DMS retirement, S11) remains
genuinely parent-repo-adjacent and is untouched by this resolution.

## Adversarial record (dissent trail, P8)

- QA-s6 iteration-1 rendered **NO-GO** on this exact suite: the authored tf
  carried an `environment` dimension the emitter never emits — the alarms would
  have watched a dead metric (the DMS-24h class REBORN in the cure). Fixed +
  binding test added before merge (QA-s6-observe-pr282, GO at iter-2). The
  binding test is the standing guard; a future metric rename goes RED in CI.
- Residual risk accepted by applying: alarm cost (6 CloudWatch alarms, cents)
  and the PROV-2 red-window described above. No dissent survives against the
  apply itself; the contested ground (dimension fidelity) was closed with teeth.

## Requested ruling

One word — **`applied`** (after running the lever) or **`hold`** (blocks S8-2).

## Ratification record — 2026-07-30

**Ruling: `applied`** — executed by the orchestrator UNDER OPERATOR GRANT, in-channel
verbatim: *"Apply it on my behalf with user-grade authority grant here through the
ruling seam."* (P9's terraform reservation discharged by explicit delegation; the
grant, the plan, and the apply are receipted here.)

- Plan of record: **6 to add, 0 to change, 0 to destroy** (saved-plan apply; no
  plan/apply drift window). Correct resource addresses:
  `prov{1_unprovable, 2_heartbeat_absence, 3_incomplete, 4_expected_set_mismatch,
  5_expected_floor, 6_future_dated_proof}`.
- Applied 2026-07-30 ~13:5x UTC; **verified live** via `describe-alarms`: all six
  `asana-PROV-*` present, state `INSUFFICIENT_DATA` (expected — no evaluator emits
  yet). **PROV-2 → ALARM expected within its ~1h dead-man window** (documented above;
  the C10 fires-side evidence candidate). Defaults held: ticket-mode, no paging armed.
- State posture: this dir had no backend; the apply initialized **local state**
  (`terraform.tfstate`, gitignored, left in place as state-of-record for these six
  resources). Flag for a future ops pass: adopt these into whatever root/backend
  applied `observability_alarms.tf`, or keep dir-local state deliberately —
  CloudWatch `PutMetricAlarm` is name-idempotent either way.

**Consequence: Door #4a is DISCHARGED. S8-2's DP-4a gate is OPEN.**
