---
title: "TRIAGE — four muted SEV1 deadmen, asana surface (read-only)"
date: 2026-09-15
rite: sre
seat: observability-engineer
grant: operator user-grade, READ-ONLY triage (class A)
mutates: nothing
feeds: "operator decision W-4 — unmute the SEV1 deadmen the triage proves real (yes / no / only ___)"
region: us-east-1
---

# TRIAGE — four muted SEV1 deadmen on the asana surface

**Read-only.** No alarm state was set, nothing was unmuted, no producer was invoked, nothing was
written to AWS. Every AWS call in this triage is a `describe*` / `list*` / `lookup*` /
`get-metric-statistics` read. The AWS account id appears nowhere in this document (`<ACCOUNT>`).

**This document does not decide W-4.** It supplies the evidence W-4 rests on, and names the lane
that must be sent a coherence notice before any unmute is put to the operator.

---

## 0. Method, and two corrections to the charge

**Positive controls.** Every zero below is printed beside a control run through the *identical* call
on a subject known to be written:

| control | call | result |
|---|---|---|
| `autom8-asana-conversation-audit-freshness-prober` | `get-metric-statistics AWS/Lambda Invocations`, daily, 09-05..09-15 | **1 invocation every single day, 11 of 11 days** — members: 09-05:1 09-06:1 09-07:1 09-08:1 09-09:1 09-10:1 09-11:1 09-12:1 09-13:1 09-14:1 09-15:1 |
| `autom8-email-booking-intake-office-floor` (the charge's named live control) | same call | 09-14:21 09-15:23 — alive and hourly, **but the function only exists from 09-14**, so it cannot control the 09-05..09-13 span; the freshness-prober above does |
| `Autom8y/AdLeadGate` / `AdLeadGateRefusedAnomaly` | `get-metric-statistics` on a **custom** namespace, daily, 09-05..09-15 | data every day: 4818, 4973, 7499, 15857, 15824, 12269, 8461, 5075, 5448, 12006, 9967 — the custom-namespace read path is not broken |
| EventBridge rule state | `events list-rules` | `autom8-asana-conversation-audit-freshness-prober-schedule` **ENABLED**, `autom8-email-booking-intake-office-floor-schedule` **ENABLED** — a DISABLED reading below is a real state, not an empty response |
| CloudTrail | `lookup-events` per call | each lookup prints its scanned-event count (23, 7, 8, 3, 27, 15, 6) — all non-zero, so "no matching event" is a real absence, not a dead query |
| `logs describe-metric-filters` | all log groups | **109 filters returned** (control), of which **0** produce any of the four watched metrics — these are `PutMetricData` metrics from Lambda code, not log-derived |

**Correction 1 — the charge's timestamps are local, not UTC.** The AWS CLI renders timestamps in the
session's local zone (`-04:00`). The charge's "11:24Z", "12:32Z", "10:30Z", "20:01Z", "02:01Z" are
EDT wall-clock. In UTC the four alarms entered ALARM at **08-19T15:24Z**, **09-05T14:30Z**,
**09-06T00:01Z**, **09-06T06:01Z**, and the story-warm `ConfigurationUpdate` was **09-08T16:32Z**.
All times in this document are UTC and were converted explicitly.

**Correction 2 — the dark window is one window, not four.** All four watched series stop in the same
hour: **last datapoint 2026-09-05T06:00Z** for every one of them.

---

## 1. Verdicts

| alarm | verdict | the muted pager is hiding… |
|---|---|---|
| `asana-PROV-9-offer-artifact-uncovered` | **STALE BY DESIGN**, with a live-fault rider | …a producer paused by ruling **and** a substantive finding: while the producer ran, the artifact read UNPROVABLE on **804 of 804** datapoints |
| `autom8y-asana-story-warm-dead` | **STALE BY DESIGN** | …a lane whose schedule a human disabled by ruling on 09-05T06:24:56Z |
| `asana-r7-active-offer-roster-floor` | **STALE BY DESIGN** | …nothing: the roster read 94–100 against a floor of 50 until the moment its producer was paused |
| `asana-r7-evaluator-dead` | **STALE BY DESIGN** (decay edge — no hand touched this row) | …nothing: the evaluator ran 4×/day until its schedule was disabled |

**None of the four is a REAL OUTAGE in the sense W-4 asks about** (a producer dead or failing while
nobody looks). **None is STALE DRIFT** — the drift test below is two-sided and clean. The answer W-4
is shaped toward is therefore *no* for all four as written; §6 gives the two rows that nonetheless
need a decision, for reasons other than "the alarm is right".

---

## 2. Per-alarm findings

### 2.1 `asana-PROV-9-offer-artifact-uncovered`

| field | finding |
|---|---|
| **watches** | ns `Autom8y/SubstrateProvability`, metric `ArtifactProvable`, dims `{environment=production, project_gid=…9250 (16-digit offer project gid, redacted to stay clear of the merge-surface 12-digit sweep), entity_type=offer}`, `Minimum < 1`, period 900s, 4 of 4 periods, `treat_missing_data=breaching` |
| **producer** | `autom8-asana-prov-sweep` Lambda (container, handler `autom8_asana.lambda_handlers.prov_sweep.handler`), emitting from `src/autom8_asana/substrate/observe.py:434` (`METRIC_ARTIFACT_PROVABLE`). Not log-derived: 0 of 109 metric filters produce it. Stack: `autom8y` `terraform/services/asana/substrate_prov_sweep.tf` |
| **producer alive?** | **DEAD BY RULING.** `Invocations` 09-01:96 09-02:96 09-03:96 09-04:79 09-05:26 then **nothing** 09-06..09-15; `Errors` **0 throughout** — it did not fail, it stopped. Rule `autom8-asana-prov-sweep-schedule` (`rate(15 minutes)`) reads **DISABLED**. Control: freshness-prober 1/day all 11 days through the same call; control rule ENABLED. Note the function was re-deployed as recently as `LastModified=2026-09-15T21:40Z` — **the code ships, the schedule does not run** |
| **muted by / when** | **Born muted, by CI, never once armed.** `PutMetricAlarm` **2026-08-19T15:22:40Z**, `actionsEnabled=false`, `type=AssumedRole role=github-actions-terraform pid=AROA*** session=GitHub***`. `describe-alarm-history --history-item-type ConfigurationUpdate` holds exactly one item: *created* at 15:22:39Z. No later write of any kind. ALARM 2 minutes after birth (15:24:06Z) |
| **verdict** | **STALE BY DESIGN — with a live-fault rider that must not be lost.** The *current* ALARM is missing-data from a ruled pause. But between 08-27T17:00Z and 09-05T06:00Z, when the producer was alive, `ArtifactProvable` emitted **804 datapoints and every single one was 0.0** (daily min=max=0.0 on all ten days). Condition (a) of the alarm's own description — *"the artifact was evaluated and read UNPROVABLE"* — was continuously true for the entire life of its producer, alongside `EvaluatedCount=1` and `EvaluatorHeartbeat=1`. **This alarm has never once read provable.** |
| **fix-observation** | Re-enabling the sweep will **not** turn this green, and green is not the test anyway. The fix is observed when: (i) `ArtifactProvable{prod,…,offer}` `Minimum = 1.0` sustained across **4 consecutive 900s periods** (one full window), *and* (ii) `EvaluatedCount == ExpectedCount == 1` per sweep with `EvaluatorHeartbeat` at 96/day, *and* (iii) `MaxStalenessAgeSeconds` on the **3-dimension** set reads a real, moving watermark age rather than 0.0 (`observe.py:193` returns 0.0 for an empty verdict list — 0.0 is the *best* value that gauge can take, which is exactly the vacuity PROV-9 exists to catch). A green produced by re-pointing dimensions, by flipping `treat_missing_data`, or by an empty verdict list reading 0.0 is the F-2 failure, not the cure |
| **owning lane** | **offer-axis / substrate-v2 freshness lane**, `autom8y` repo. Alarm: `terraform/services/asana/offer_freshness_prov_alarms.tf` (`3a066a5a`, 2026-08-19, *"AL-5 re-home to PROV MaxStalenessAgeSeconds (SPR-D2)"*, #1643). Producer stack: `substrate_prov_sweep.tf` (`11e1a4dd`, 2026-08-27, #1745). Release conditions held at `terraform/services/asana/environments/production.tfvars:383-400`. Tags: `Service=asana, Environment=production, ManagedBy=terraform` |

**The alarm predates its own producer by 8 days — CONFIRMED, and it is worse than the lead said.**
Alarm created 2026-08-19T15:22:40Z. `CreateFunction20150331` for `autom8-asana-prov-sweep`:
**2026-08-27T17:22:50Z–17:22:59Z** (five events, `role=github-actions-terraform`). First
`ArtifactProvable` datapoint after that: the **08-27T17:00Z** hour bucket, 3 samples, `Maximum=0.0`.
So the alarm sat in ALARM for 8 days against a producer that did not exist, and then its producer
arrived and reported 0.0 from its very first bucket.

**PROV-9's own release conditions, re-read against live state** (`production.tfvars:392-400` requires
all three):
- **(a) EMIT-1 — `MaxStalenessAgeSeconds` on `{environment, project_gid, entity_type}`: NOW LIVE.**
  `list-metrics` returns that 3-dimension series today. The tfvars comment ("emitted with
  `{environment}` ONLY") is **stale** — both series now exist.
- **(b) EMIT-2 — the prov_sweep schedule driving the evaluator: SHIPPED 08-27, THEN REVOKED 09-05.**
- **(c) PROV-9 observed CLEARING to OK on real per-artifact datapoints: NEVER SATISFIED, 0 for 804.**

### 2.2 `autom8y-asana-story-warm-dead`

| field | finding |
|---|---|
| **watches** | ns `autom8y/cache-warmer`, metric `StoryWarmSuccess`, dim `{environment=staging}` (documented production label drift — `ASANA_CW_ENVIRONMENT` unset falls back to the "staging" default; the alarm deliberately watches the series the production lane actually writes), `Sum <= 0`, period 7200s, 2 of 2 periods, `treat_missing_data=breaching` |
| **producer** | `autom8-asana-cache-warmer` Lambda, hourly; emitter `src/autom8_asana/lambda_handlers/story_warmer.py:459` — `emit_metric("StoryWarmSuccess", stats["success"])`, emitted unconditionally once per run (explicit 0 on an all-fail run, **absent** when the lane never ran). Rule `autom8-asana-cache-warmer-schedule`, `cron(0 * * * ? *)` |
| **producer alive?** | **DEAD BY RULING.** `Invocations` 09-01:63 09-02:61 09-03:56 09-04:52 09-05:16 then **nothing** 09-06..09-15. Rule reads **DISABLED**. Metric: hourly `StoryWarmSuccess` ran continuously (daily sums 91k–148k in late July, 7k–18k after 08-14) through **09-05T06:00Z**, then nothing. Controls as in §0 |
| **muted by / when** | **Hand-muted by a human, 3 days after it began firing, and it is the only one of the four muted imperatively.** `EnableAlarmActions` **2026-08-14T15:27:19Z** then `DisableAlarmActions` **2026-09-08T16:32:09Z**, both `type=AssumedRole role=AWSReservedSSO_AdministratorAccess_072d916d21d2219c pid=AROA*** session=tomten***`. The 09-08T16:32:09Z `ConfigurationUpdate` in alarm history is that same mute, to the second |
| **verdict** | **STALE BY DESIGN.** The lane delivered without interruption until its schedule was disabled by hand at 09-05T06:24:56Z; the alarm fired correctly at 09-05T14:30Z on the resulting silence, and was muted on 09-08. Nothing about the warmer failed — `StoryWarmFailure` being routinely nonzero is the documented baseline this alarm was deliberately designed *not* to watch |
| **fix-observation** | Re-enabling `autom8-asana-cache-warmer-schedule` should be judged by: (i) `StoryWarmSuccess{staging}` hourly `Sum` back at or above its observed floor (pre-pause hourly minimum ≈ 97–200, never zero in the 7-day replay the alarm header cites) for **≥2 consecutive 2h buckets**, *and* (ii) `Invocations ≈ 24/day` on the function, *and* (iii) the downstream thing the warm exists for — story cache freshness on the served surface — actually moving. **Named trap:** if anyone "fixes" the `environment` label drift by setting `ASANA_CW_ENVIRONMENT=production`, the `{staging}` series this alarm watches goes dark **forever** and the alarm re-enters ALARM on a healthy lane. The label fix and the dimension re-point must land in the same change (the alarm's own header says so) |
| **owning lane** | **sre lane / nightly-smoke-resurrection CURE-2**, and it is the only one of the four owned by **`autom8y-asana`**, not `autom8y`: `terraform/services/asana/story_warm_dead_alarm.tf` (`04e5cb24`, 2026-08-14, #373). Tags: **NONE** — the other three carry `ManagedBy=terraform`; this one carries no tags at all |

**Two structural cautions on this row, both load-bearing for W-4:**

1. **The mute is undeclared and will self-revert.** `story_warm_dead_alarm.tf` **does not set
   `actions_enabled` at all** (the resource block at `:80` declares `alarm_actions` at `:98` and no
   `actions_enabled` attribute). The mute exists only as an imperative CLI act. The fleet's own
   precedent, written into `production.tfvars:355-357` and proven on 2026-08-08, is that
   *"`aws cloudwatch disable-alarm-actions` is reconciled straight back"* by the next apply.
   So this alarm is presently scheduled to re-arm itself, silently, whenever its file is next
   applied — and re-arm into a lane that is paused by ruling, i.e. **straight onto the live SMS
   topic**. This is a decision the operator has to make in one direction or the other; leaving it is
   choosing the unplanned outcome. `[UV-P: the AWS provider defaults aws_cloudwatch_metric_alarm.actions_enabled to true, so an apply would set it true | METHOD: terraform plan against the asana state, or provider schema read | REASON: read-only triage; no plan was run and no apply lane was exercised]`
2. **No CI lane visibly applies it.** The only workflow in `autom8y-asana` referencing terraform is
   `.github/workflows/nightly-live-smoke.yml`. Combined with the absent tags, this row looks like
   the same custody shape `offer_freshness_prov_alarms.tf` documents for AL-5 (an alarm held outside
   the CI-managed state). `[UV-P: which terraform state holds autom8y-asana-story-warm-dead, and whether any lane can apply it | METHOD: state-file provenance probe / CI lane audit in autom8y-asana | REASON: out of scope for a read-only alarm triage; needs the owning lane's word]`

### 2.3 `asana-r7-active-offer-roster-floor`

| field | finding |
|---|---|
| **watches** | ns `Autom8y/AsanaOfferDivergence`, metric `ActiveOfferRosterSize`, dim `{environment=production}`, `Minimum < 50`, period 21600s (6h), 1 of 1 period, `treat_missing_data=breaching` |
| **producer** | `autom8-asana-traffic-offer-divergence` Lambda, handler `autom8_asana.lambda_handlers.traffic_offer_divergence_tripwire.handler`; `METRIC_ROSTER_SIZE` at `src/autom8_asana/lambda_handlers/traffic_offer_divergence_tripwire.py:173`. Rule `autom8-asana-traffic-offer-divergence-schedule`, `cron(0 */6 * * ? *)` |
| **producer alive?** | **DEAD BY RULING.** `Invocations` 09-01:4 09-02:4 09-03:4 09-04:4 09-05:2 then **nothing**; `Errors` **0 throughout**. Rule reads **DISABLED**. Controls as in §0 |
| **muted by / when** | **CI, by ruled tfvar, 2026-08-08T10:55:27Z.** `PutMetricAlarm` with `actionsEnabled=false`, `role=github-actions-terraform pid=AROA*** session=GitHub***` — the apply whose own header says *"THIS APPLY DISARMS FIVE CURRENTLY-ARMED ALARMS. That is INTENTIONAL and RULED."* No `ConfigurationUpdate` in the 30-day alarm-history retention window, consistent with nothing having touched it since |
| **verdict** | **STALE BY DESIGN.** And the strongest of the four: while the producer ran, the watched value was **healthy** — `ActiveOfferRosterSize` read 94–100 every day from 08-04 through 09-05 against a floor of 50. It never approached breach. The ALARM is purely the `breaching` treatment of a ruled pause |
| **fix-observation** | Judge a re-enable by: (i) `ActiveOfferRosterSize{production}` datapoints at **4/day** (the 6h cadence) with value **≥ ~94**, restoring the observed baseline, *and* (ii) the tripwire's `TrafficOfficesEvaluated` and the by-class series re-populating, *and* (iii) the tfvars' own condition — the slow-burn threshold re-derived against the then-current two-leg baseline. A green here without 4 datapoints/day is an alarm watching a re-pointed or notBreaching metric, not a restored roster |
| **owning lane** | **R7 traffic-vs-offer divergence lane (WS-E)**, `autom8y` repo: `terraform/services/asana/traffic_offer_divergence_alarm.tf` (`b4864f92`, 2026-08-05, #1359 "WS-E HALF-2"; suppression `02426f42`, 2026-08-08). Producer: `traffic_offer_divergence_lambda.tf`. Release conditions: `production.tfvars:366-369`. Tags: `Service=asana, Environment=production, ManagedBy=terraform` |

### 2.4 `asana-r7-evaluator-dead`

| field | finding |
|---|---|
| **watches** | ns `Autom8y/AsanaOfferDivergence`, metric `LastRunEpoch`, dim `{environment=production}`, `Maximum < 1`, period 21600s (6h), 2 of 2 periods, `treat_missing_data=breaching`. Detects **absence only** — a live epoch value can never trip the comparison |
| **producer** | Same Lambda as §2.3; `METRIC_LAST_RUN_EPOCH` at `traffic_offer_divergence_tripwire.py:177`, emitted on **every** path including the skipped/gate-off path (`:810`, `:1088`) so the dead-man tracks invocation, not outcome |
| **producer alive?** | **DEAD BY RULING** — same producer, same evidence as §2.3. `LastRunEpoch` ran 4/day with a monotonically advancing epoch from 08-04 through the **09-05T06:00Z** bucket, then nothing. Controls as in §0 |
| **muted by / when** | **CI, 2026-08-08T10:55:27Z**, same `PutMetricAlarm` apply as §2.3 (`actionsEnabled=false`, `role=github-actions-terraform`). **Nothing has written this row since** — its `AlarmConfigurationUpdatedTimestamp` is still 2026-08-08T10:55:27Z while its state moved to ALARM on 2026-09-06T06:01:51Z. My CloudTrail read independently corroborates the "decay edge" the alarm-plane cards named: **this row's state moved while no writer touched its configuration** |
| **verdict** | **STALE BY DESIGN** (by decay rather than by a hand on this row: the deliberate act was against its *producer*, not against the alarm) |
| **fix-observation** | (i) `LastRunEpoch{production}` datapoints at **4/day** with the epoch value advancing ~21600 per datapoint, *and* (ii) `Invocations = 4/day` on the function, *and* (iii) the transition the tfvars requires — the dead-man **observed clearing to OK on real datapoints** before any arm. The ordering is the fleet's own, and it is not optional: **enable the producer → watch the fuse re-light → only then arm.** Never arm first |
| **owning lane** | Same as §2.3 — R7 / WS-E lane, `autom8y` repo, `traffic_offer_divergence_alarm.tf`; release conditions `production.tfvars:366-369` |

---

## 3. The common cause: one pause, one hour, three schedules

All four watched series stop at the **2026-09-05T06:00Z** hour. CloudTrail, `us-east-1`:

| UTC | event | target | principal |
|---|---|---|---|
| 2026-09-04T18:41:26Z | `DisableRule` | `autom8-asana-cache-warmer-schedule` | `type=AssumedRole role=AWSReservedSSO_AdministratorAccess_… pid=AROA*** session=tomten***` |
| 2026-09-04T18:41:27Z | `DisableRule` | `autom8-asana-prov-sweep-schedule` | same human SSO principal |
| 2026-09-04T18:41:28Z | `DisableRule` | `autom8-asana-traffic-offer-divergence-schedule` | same human SSO principal |
| 2026-09-04T22:51:19Z | `PutRule` **State=ENABLED** | all three, same second | `role=github-actions-terraform pid=AROA*** session=GitHub***` — **CI re-armed what the human had just paused** |
| 2026-09-05T06:24:56Z / :24:59Z / :25:01Z | `DisableRule` | all three again | the same human SSO principal |

That is the divergence `legacy-sunset-wsp-iac-state-switch.md` (H-02) records and cures: the pause was
imperative, an apply reconciled it away 4h10m later, and the durable fix was the
`schedule_enabled = false` literal committed at `05642e89` (2026-09-05T01:33Z) —
`substrate_prov_sweep.tf:86`, `traffic_offer_divergence_lambda.tf:141`, `main.tf:479`. Today all
eleven `autom8-asana-*` schedules read DISABLED except `conversation-audit-freshness-prober`.

The governing ruling is cited by name in the terraform as
**`ADR-decommission-recurring-jobs-single-prod-2026-09-04`**, released only by *"the enable act that
re-opens this job, citing H-02 by name. Never by a date."*
`[UV-P: the ADR document itself | METHOD: locate ADR-decommission-recurring-jobs-single-prod-2026-09-04 in whichever repo holds it | REASON: the file is NOT present on autom8y origin/main — only three files cite it by name; I read the citations, not the ruling]`

---

## 4. The drift test (why no verdict is STALE DRIFT)

`list-metrics` **without** a namespace filter, for each watched metric name — this is the test that
would catch "the producer runs but the metric moved":

| metric | every series that exists | reading |
|---|---|---|
| `ArtifactProvable` | `Autom8y/SubstrateProvability{production, …9250, offer}` — **one series, the alarm's own** | no drift |
| `ActiveOfferRosterSize` | `Autom8y/AsanaOfferDivergence{production}`, `{staging}`, `{development}` | alarm watches `production`; no relocation |
| `LastRunEpoch` | `Autom8y/AsanaOfferDivergence{production}`, `{staging}`, `{development}` | same |
| `StoryWarmSuccess` | `autom8y/cache-warmer{staging}` **plus** `autom8/lambda{staging}` and `autom8/lambda{development}` | **lead checked and closed** — see below |

The `autom8/lambda` `StoryWarmSuccess` series are **not** a relocated production lane: sporadic
(7 days of data in a month), 2–4 samples in a scattered hour, and **`Sum = 0.0` on every one** —
against a production lane whose daily sums were 7k–148k. They also stop (last data 09-06T17:00Z).
`[UV-P: which code path writes StoryWarmSuccess into the autom8/lambda namespace at value 0 | METHOD: log-group / handler trace on the emitting function | REASON: the alarm does not watch that namespace, so it does not change any verdict here]`

---

## 5. Leads from the charge — checked, not inherited

| lead | status |
|---|---|
| CARDS maps PROV-9 to `autom8-asana-prov-sweep`, whose schedule was DISABLED | **CONFIRMED by my own probe**, independently of the card: rule `autom8-asana-prov-sweep-schedule` reads DISABLED live; invocations stop 09-05; `substrate_prov_sweep.tf:86` carries the durable literal |
| `autom8-asana-prov-sweep` created 2026-08-27, so PROV-9 may predate its own producer | **CONFIRMED, with the exact instants.** Alarm `PutMetricAlarm` 2026-08-19T15:22:40Z; `CreateFunction` 2026-08-27T17:22:50–59Z; first datapoint 08-27T17:00Z bucket. The alarm predates its producer by **8 days 2 hours**. Nuance the lead did not have: 7 `ArtifactProvable` datapoints exist on **08-05**, before the alarm was created, from the pre-stack in-process evaluator |
| `autom8y-asana-story-warm-dead` was proven to page in August (#373) | **PARTLY CONFIRMED.** The alarm was authored by `04e5cb24` (2026-08-14, #373) and `EnableAlarmActions` fired at 2026-08-14T15:27:19Z by the human SSO principal — arming is receipted. `[UV-P: that a page was actually DELIVERED to the SMS subscriber in August | METHOD: SNS delivery-status logs for autom8y-platform-sre-sev1, or the #373 receipt | REASON: not observable from describe-alarms/CloudTrail; delivery is an SNS-side fact]` |
| The alarm-plane cards' own disposition for the three `autom8y`-owned rows | **Independently corroborated.** The cards' DISCRIMINATOR reaches LEAVE-PAUSED for all three; my evidence agrees and adds the 804/804 zero-reading for PROV-9, which strengthens rather than weakens that disposition |

---

## 6. Coherence notices owed before any unmute, and what W-4 is actually choosing

**Send a coherence notice to, in this order:**

1. **The offer-axis / substrate-v2 lane** (`autom8y`, `offer_freshness_prov_alarms.tf` +
   `production.tfvars:383-400`) — PROV-9. Two facts they may not hold: release condition **(a)
   EMIT-1 is now satisfied** (the 3-dimension `MaxStalenessAgeSeconds` series exists, so their tfvars
   comment is stale), and **(c) has never been satisfied — 804 of 804 datapoints read 0.0.**
2. **The R7 / WS-E lane** (`autom8y`, `traffic_offer_divergence_alarm.tf` +
   `production.tfvars:366-369`) — both r7 rows. Their release condition (b) is **unreachable while
   their own producer is disabled**; the sequencing they wrote (producer → fuse re-lights → arm) is
   the sequencing any unmute must follow.
3. **The sre / nightly-smoke-resurrection lane** (`autom8y-asana`, `story_warm_dead_alarm.tf`, #373)
   — the mute of their alarm is **undeclared in their own IaC** and is scheduled to self-revert on
   the next apply of that file, onto a lane that is paused by ruling.
4. **The legacy-sunset WS-P / H-02 lane** — it owns the pause that made all four silent, and it is
   the lane that holds the release act (`ADR-decommission-recurring-jobs-single-prod-2026-09-04`).

**What W-4 is choosing.** On this evidence, *"unmute the ones the triage proves real"* selects
**none of the four**: every one of them is dark because a producer was deliberately paused, and
unmuting any of them pages a human, on a live SMS topic, for a state the fleet ruled into existence
and has not yet ruled out of existence. The two things that do need an operator word are **not**
unmutes:

- **PROV-9's 804 zero readings** — either the offer artifact genuinely is not provable, or the
  serve-gate's `is_provable` cannot yet return true for it. That is a real, unreported finding about
  the offer axis; it is invisible today only because the sweep is off, and it will page the instant
  anyone satisfies (b) without understanding (c).
  `[UV-P: which of those two explanations holds | METHOD: read the sweep's own verdict payload / is_provable inputs for the offer artifact in the 08-27..09-05 run window (logs), or re-run the evaluator read-only | REASON: CloudWatch cannot separate "evaluated and genuinely unprovable" from "evaluated under an unshipped contract" — both emit 0.0]`
- **The story-warm mute's IaC drift** — declare it or retire the alarm; an undeclared mute on a
  paged alarm is a page waiting for an unrelated apply to schedule it.

**Fleet obligation F-2, restated for whoever acts next.** None of these four may be judged by its
alarm going green. Each has a metric-side observation in §2 — a datapoint *count* at the producer's
cadence and a *value* in its known-good band — and green without that observation means the alarm was
re-pointed, re-treated, or deleted, not that observation was restored.
