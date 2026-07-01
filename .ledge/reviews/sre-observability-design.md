---
type: review
artifact_role: observability-design
slug: sre-observability-design
status: DESIGN-ONLY
rite: sre
agent: observability-engineer
phase: analysis (observe->coordinate); NO MUTATION
head: f4f924d2684386093ef656ecde5e98613cdffce8
date: 2026-06-24
aws_account: 696318035277
aws_region: us-east-1
discipline: "No claim without a pasted LIVE receipt. Rungs named, never rounded up: authored < emitting < alerting < proven < merged < live < protecting-prod. G-DENOM: no proven-zero from silence."
upstream: [asana-coherence-case-file.md, asana-coherence-critic-verdict.md (CONCUR-WITH-FLAGS), PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md]
---

# Observability Restoration Design — autom8y-asana push-seam + bridge fleet

> **DESIGN + CLASSIFY ONLY.** No alarm armed, no metric deployed, no PR opened, no prod mutated.
> Every alarm below is IaC *design*. Arming the paging tier is a confirm-first user lever (G).

## Executive Summary

Three premise gaps closed with live receipts at HEAD `f4f924d2`:
(a) the ENABLED insights-export daily bridge is **NOT dark at the Lambda layer** — it invokes
daily (Sum=1/day) with **zero Errors** all 7 days; the darkness is the custom
`LastSuccessTimestamp` dead-man going stale, which is **emission gated on `result.succeeded > 0`
by design** (`workflow_handler.py:319`,`:330-339`) — so "dark since 06-18" = ran-but-produced-zero-
successes (or the IAM/namespace PutMetricData denial flagged in `cache_warmer.py:81`), NOT a crash.
(b) the recon invocation gap 06-20..23 is fully explained: EventBridge rule
`autom8y-account-status-recon-schedule` is **State=DISABLED** (`cron(0 */4 * * ? *)`). (c) FORK-1
retire: on the LIVE service log groups (non-silence PROVEN — 18,888,558 records on ECS;
951 on the legacy monolith), `deprecated_query_endpoint_used` matched **0** since 2026-06-01.
The two log groups the mission named do NOT exist; they resolve to **legacy DEAD groups** (last
events 2025-07-21 and 2023-07-27) — a G-DENOM trap that would have manufactured a false proven-zero.

The structural defect is a family of **silent skip denominators on the StatusPush seam**: every
skip reason returns without emitting a CloudWatch metric, so an idle/misconfigured push-seam is
invisible. The restoration is a `StatusPushSkipped` counter dimensioned by `skip_reason`, a paging-
when-armed `recon-invocation-gap` alarm, a `LastSuccessTimestamp`-stale freshness alarm, and a NEW
**prod** `BridgeFleetHealth` dimension (only `{staging, insights-export}` exists today).

---

## §A — Live receipts (pasted)

### (a) insights-export — Errors + Invocations 7d + dark-since-06-18 root cause

`aws cloudwatch get-metric-statistics AWS/Lambda Errors --dimensions Name=FunctionName,Value=autom8-asana-insights-export --period 86400 --statistics Sum` (2026-06-17..24):

```
Errors:      06-17=0  06-18=0  06-19=0  06-20=0  06-21=0  06-22=0  06-23=0   (Unit=Count)
Invocations: 06-17=2  06-18=1  06-19=1  06-20=1  06-21=1  06-22=1  06-23=1   (Unit=Count)
```

**Verdict:** The ENABLED daily bridge is **alive and erroring zero** at the Lambda layer every day
of the window. It is NOT dark — it INVOKES daily. The "dark since 06-18" signal is the custom
freshness dead-man, not the function.

**Emission-path root cause (code, proven):** `LastSuccessTimestamp` is emitted ONLY through
`emit_success_timestamp(...)` and is **gated twice on genuine success**:
- per-workflow DMS: `workflow_handler.py:319` — `if config.dms_namespace and result.succeeded > 0: emit_success_timestamp(config.dms_namespace)` (insights-export `dms_namespace="Autom8y/AsanaInsights"`, `insights_export.py:56`).
- fleet DMS: `workflow_handler.py:330-339` — `if config.fleet_namespace:` always emits `BridgeFleetHealth` (1.0 if `succeeded>0` else 0.0), and emits `emit_success_timestamp(fleet_namespace)` **only `if result.succeeded > 0`**.
The comment at `:312-318` is explicit: without the succeeded-gate "a total batch failure
(succeeded=0, failed=total) would still publish a FRESH LastSuccessTimestamp -> a silent-green
dead-man." **So a stale LST is the designed signal for "ran, but succeeded==0."** A second, equally
live hypothesis is the IAM/namespace PutMetricData denial documented at `cache_warmer.py:81`
("LastSuccessTimestamp PutMetricData was silently denied/dropped while the alarm..."). Both are
consistent with Errors=0 + Invocations=1/day. **G-DENOM:** I do NOT assert which — both are
non-falsified from metrics alone; the discriminator is a Logs Insights read of the
`lambda_insights_export_*` success/skip lines (designed in §B, not run as a mutation).

### (b) recon schedule — the 06-20..23 gap is a DISABLED rule

`aws events describe-rule --name autom8y-account-status-recon-schedule`:

```
ScheduleExpression: cron(0 */4 * * ? *)     (every 4 hours -> 6 fires/day expected)
State:              DISABLED                 <-- this is the gap cause
Targets:            autom8y-account-status-recon  (+ DLQ autom8y-account-status-recon-dlq, retry x2)
```

`aws cloudwatch get-metric-statistics AWS/Lambda Invocations --dimensions Name=FunctionName,Value=autom8y-account-status-recon` (Sum/day):

```
30d trail: 05-25=8 05-26=7 ... 06-04=6 06-05=4 06-06=2 06-08=1 06-09=1 06-12=1 06-16=20 06-18=3 06-19=3 06-24=2
7d window: 06-18=3  06-19=3  (no datapoint 06-20,06-21,06-22,06-23)  06-24=2
```

**Verdict:** With State=DISABLED, the cron never fires; the only invocations are manual/other-source.
The 06-20..23 zero is a **true gap, not silence** (G-DENOM satisfied): the metric is NON-SILENT on
06-18/19/24 (it emits Invocations when the function runs), and the log group
`/aws/lambda/autom8y-account-status-recon` exists (storedBytes=181,815). The trail shows the regular
6/day cadence collapsed after ~06-04 and the rule is now off. **This explains the gap.**

### (c) FORK-1 retire — non-silence proven on LIVE groups, deprecated endpoint = 0

**G-DENOM trap caught:** the two groups named in the brief do NOT exist:
- `/aws/lambda/autom8_asana_handler_router_prod` -> `ResourceNotFoundException`.
- `/aws/lambda/lambda-python-asana_handler-prod` -> not present.
The closest real names are LEGACY/DEAD and would have manufactured a false proven-zero:
- `/aws/lambda/autom8_asana_handler_prod` — last event **2025-07-21** (~11 mo stale).
- `/aws/lambda/lambda-python-dev-asana-model-app` — last event **2023-07-27** (~3 yr stale).
A 2026-06-01..now Logs Insights `stats count(*)` over both returned **recordsScanned=0** — i.e.,
silent because dead, NOT because the endpoint is unused. Retiring on that would be absence-of-evidence.

The deprecated `/v1/query/{entity_type}` endpoint actually serves from the **live ECS FastAPI service**
(`api/main.py:470` mount; header+log at `routes/query.py:881,:885`). FORK-1 was therefore re-run
against the LIVE groups (each proven non-silent first):

```
GROUP /ecs/autom8y-asana-service  (last event 2026-06-24 ~10:03 UTC = LIVE)
  non-silence:  recordsScanned=18,888,562   total_records=18,888,558      <-- emphatically non-silent
  deprecated:   filter @message like /deprecated_query_endpoint_used/  ->  recordsMatched=0

GROUP /aws/lambda/lambda-python-auto-asst-app-prod  (last event 2026-06-22 = LIVE legacy monolith)
  non-silence:  recordsScanned=951          total_records=951
  deprecated:   recordsMatched=0
```

**Verdict:** Both live groups are NON-SILENT and BOTH show **zero** `deprecated_query_endpoint_used`
since 2026-06-01. This is a G-DENOM-VALID proven-zero (the denominator is real, not silent). FORK-1
retire gate **PASSES** on the evidence available — see §D for the rung and the one residual caveat.

---

## §B (1) — StatusPush* / skip-reason METRIC SPEC

**Contract owner:** push-seam (`gid_push.py::push_status_to_data_service`) + orchestrator
(`push_orchestrator.py`). **Today's reality (proven):** the seam emits `StatusPushSuccess` /
`StatusPushFailure` (`push_orchestrator.py:193,:198`) **only inside `if all_entries:`**
(`push_orchestrator.py:183`). Every skip path is metric-silent. The four skip emit sites
(all log-only, no `emit_metric`; `grep emit_metric gid_push.py` = NONE per critic verdict H-3):

| skip_reason value | emit site (file:line) | current behavior | returns |
|---|---|---|---|
| `feature_disabled` | `gid_push.py:491-496` | `logger.info("status_push_disabled")` | `False` |
| `url_absent` (the brief's gid_push.py:498-504 defensive path) | `gid_push.py:499-504` | `logger.warning("status_push_skipped", reason="AUTOM8Y_DATA_URL not configured")` | `False` |
| `invalid_key` / empty-key | `gid_push.py:507-512` | `logger.warning("status_push_skipped", reason="AUTOM8Y_DATA_API_KEY not available")` | `False` |
| `three_way_denominator_null` (empty-denominator) | **`push_orchestrator.py:183` (`if all_entries:` false branch — NO else)** + the empty-vertical row-drop docstring `push_orchestrator.py:41-42` ("Others are silently skipped") + `gid_push.py:514-519` (`no_entries_to_push`, returns `True`) | NO metric, NO skip log on the orchestrator branch | `True`/none |

**Spec — `StatusPushSkipped` (new counter):**
- **Metric name:** `StatusPushSkipped`  · **Namespace:** `Autom8y/AsanaBridgeFleet` (shared bridge namespace, NOT a per-service orphan — see G-PROPAGATE §G).
- **Value:** `1` per skip.  · **Unit:** `Count`.
- **MANDATORY dimension:** `skip_reason ∈ {feature_disabled, url_absent, invalid_key, three_way_denominator_null}` — the metric MUST emit on **all** skip reasons, including the empty-denominator orchestrator branch and the url-absent defensive path at `gid_push.py:498-504`.
- **Emit obligation (design):** insert `emit_metric("StatusPushSkipped", 1, dimensions={"skip_reason": <reason>})` immediately preceding each `return False`/skip at `gid_push.py:496`, `:504`, `:512`; AND add an `else:` to `push_orchestrator.py:183` emitting `skip_reason="three_way_denominator_null"`. (Implementation routes to Platform Engineer; this phase specifies only the contract.)
- **Min label set (anti "missing context"):** every emit carries `skip_reason`; orchestrator-side emits SHOULD also carry `invocation_id` (already in scope at `push_orchestrator.py:179`) as a structured-log correlation key, NOT as a metric dimension (cardinality).

**Two-sided RED-first fixture obligation — per reason.** For each of the four `skip_reason` values,
the test suite MUST contain a pair that is RED before the emit lands:
- **(+) positive:** drive the exact precondition (e.g. unset `AUTOM8Y_DATA_URL` for `url_absent`;
  all three contributing caches return `None`/empty-df for `three_way_denominator_null`) and assert
  `StatusPushSkipped{skip_reason=X}==1` AND `StatusPushSuccess`/`Failure` were NOT emitted.
- **(-) negative (two-sided):** drive the happy path for that reason's complement (URL present, key
  present, `all_entries` non-empty) and assert `StatusPushSkipped{skip_reason=X}==0` — proving the
  counter does not over-fire. Each fixture must FAIL on today's code (no emit exists) — that is the
  RED-first proof the metric is wired, not decorative.

---

## §B (2) — ALARM SUITE (IaC DESIGN — NOT deployed)

Paging column honors G (confirm-first): "PAGE (confirm-first)" = designed to page but MUST NOT be
armed to a pager without explicit user confirmation; "TICKET" = non-paging, dashboard/ticket only.

| # | Alarm | Metric (namespace) | Threshold | Period / eval | Datapoints | Paging when armed | Runbook |
|---|---|---|---|---|---|---|---|
| AL-1 | StatusPushSkipped > 0 | `StatusPushSkipped` (Autom8y/AsanaBridgeFleet), per `skip_reason` | `Sum > 0` | 1h | 1/1 | **TICKET** first 14d (baseline unknown — could be benign `three_way_denominator_null`); promote `url_absent`/`invalid_key` to **PAGE (confirm-first)** after baseline, since those = a real misconfig | RB-STATUSPUSH-SKIP |
| AL-2 | recon-invocation-gap | `AWS/Lambda Invocations` dims `FunctionName=autom8y-account-status-recon` | `Sum < 1` over N hours | **8h** (rule fires q4h when enabled -> 2 expected/8h; alarm at <1) | 1/1, `treatMissingData=breaching` | **PAGE (confirm-first)** — but ONLY after the rule is re-ENABLED; while State=DISABLED this alarm would page on an intended-off state (cause-not-symptom). Until enable: **TICKET**. | RB-RECON-GAP |
| AL-3 | insights-export LastSuccessTimestamp-stale | `LastSuccessTimestamp` (Autom8y/AsanaInsights) | `age(now - latest) > 26h` (daily cadence + 2h grace) | 1h, `treatMissingData=breaching` | 1/1 | **PAGE (confirm-first)** — this is the symptom-of-record for the (a) darkness; freshness dead-man is user-facing-data staleness | RB-INSIGHTS-STALE |
| AL-4 | PROD BridgeFleetHealth | `BridgeFleetHealth` dims `{environment=production, workflow_id=*}` (**dimension does NOT exist today** — only `{staging, insights-export}`) | `Min < 1` (0.0 = ran-but-failed) | 1h | 1/1 | **PAGE (confirm-first)** per `workflow_id` once the prod dim is emitting | RB-BRIDGEFLEET |

**AL-4 dimension gap (proven):** `aws cloudwatch list-metrics --namespace Autom8y/AsanaBridgeFleet`
returns exactly two series: `LastSuccessTimestamp[]` (undimensioned) and
`BridgeFleetHealth{environment:staging, workflow_id:insights-export}`. **There is no `production`
environment dimension and no workflow other than `insights-export`.** The emit code
(`workflow_handler.py:256-262,:330-337`) dimensions only `{workflow_id}` — `environment` is absent
from the emit, which is why the only observed `environment` value is `staging`. Restoring prod
fleet health requires adding `environment` to the dimension set at the emit site (Platform Engineer).

**Symptom-not-cause discipline [SR:SRC-001 Beyer 2016 | STRONG]:** AL-2 (recon-gap) and AL-3
(LST-stale) and AL-4 (BridgeFleetHealth) are all customer/data-impact symptoms (stale data, missing
reconciliation, failed bridge run). AL-1 (`StatusPushSkipped`) is a borderline cause-metric and is
therefore TICKET-first; only the misconfig reasons (`url_absent`,`invalid_key`) graduate to PAGE,
because those map 1:1 to "status data is not reaching autom8_data" (a symptom).

---

## §C (3) — Four Golden Signals + draft SLO / error budget

**Seam 1 — StatusPush push-seam (asana -> autom8_data status sync):**

| Golden Signal | SLI (ratio, user-facing) | Source |
|---|---|---|
| Latency | p95 push round-trip ms | `_push_to_data_service` (designed metric `StatusPushLatency`, not yet emitted) |
| Traffic | StatusPush attempts / interval (Success+Failure+Skipped) | derived |
| Errors | `StatusPushFailure / (Success+Failure)` | `push_orchestrator.py:193,:198` (live) |
| Saturation | concurrent push inflight / pool | data-client pool (designed) |

- **Draft SLI:** `successful_status_pushes / attempted_status_pushes` where attempted = Success+Failure
  (skips with `three_way_denominator_null`/`no_entries` excluded from denominator — they are not failures).
- **Draft SLO:** **99.0%** push success over rolling 30d. **Error budget:** 1.0% = ~**7.2h/month**
  equivalent of failed pushes. Burn-rate (multi-window) [SR:SRC-002 Beyer 2018 | STRONG]:
  fast-burn 2%/1h (page-confirm), slow-burn 5%/6h (ticket).
- **Rung today:** `emitting` for Success/Failure; **NOT alerting** (no alarm armed). Skipped seam is
  not even `emitting` (the gap this design closes).

**Seam 2 — Bridge fleet (insights-export + future prod workflows):**

| Golden Signal | SLI | Source |
|---|---|---|
| Latency | `WorkflowDuration` p95 (Seconds) | `workflow_handler.py:281-286` (live) |
| Traffic | `WorkflowExecutionCount` / day | `workflow_handler.py:134-138` (live) |
| Errors | `WorkflowExecutionError` count; `1 - WorkflowSuccessRate/100` | `:114-118`, `:287-292` (live) |
| Saturation | n/a (scheduled batch) — use freshness instead | — |

- **Draft SLI (freshness, the right SLI for a daily batch):** fraction of days where
  `LastSuccessTimestamp` advanced within the 26h freshness window.
- **Draft SLO:** **freshness met 29/30 days (96.7%)**; **error budget = 1 stale day / 30d.**
  Plus a run-quality SLO: `WorkflowSuccessRate >= 95%` per run.
- **Rung today:** duration/count/error/success-rate `emitting`; freshness dead-man `emitting` but
  **succeeded-gated** (the (a) finding) and **NOT alerting**. The (a) staleness since 06-18 has
  **already consumed the freshness error budget** for the current window — flag to Incident Commander.

---

## §D (4) — FORK-1 retire RECOMMENDATION + evidence verdict

**Recommendation: RETIRE `/v1/query/{entity_type}` — gate PASSES, at rung `proven` (usage), NOT `live`-removed.**

Evidence (G-DENOM-correct, two live non-silent groups):
- ECS service (the actual host): 18,888,558 records 2026-06-01..now, **0** `deprecated_query_endpoint_used`.
- Legacy monolith: 951 records, **0** matches.
- Non-silence established on BOTH before reading the zero -> the zero is a real proven-zero, not absence-of-evidence.
- `Sunset: 2026-06-01` header lapsed (`query.py:881`); `Deprecation: true` set.

**Rung honesty (not rounded up):** "endpoint not exercised since 2026-06-01" is `proven`. Removal is
`authored`-only until a PR lands. **Residual caveat (one, explicit):** the signal is a `logger.info`
line (`query.py:885`), not a metric — if any caller hit the route on a code path that bypasses that
log line (it should not — the log is unconditional at the handler), it would be invisible. Mitigation
before physical removal: (i) flip the route to return `410 Gone` for one cadence and watch ECS 4xx +
the `deprecated_query_endpoint_used` count stay 0, then (ii) remove the mount (`api/main.py:470`).
This keeps retire at confirm-first and the production-mutating lever with the user.

**Verdict:** RETIRE-licensed by evidence; execute as 410-canary-then-unmount, not silent delete.

---

## §E (5) — Corrected premise matrix S1-S5 (live receipts)

| # | Restated premise | Live verdict | Rung | Receipt |
|---|---|---|---|---|
| **S1** | insights-export ENABLED daily bridge "dark since 06-18" = a Lambda failure | **FALSE (re-cast).** Lambda invokes daily, Errors=0 all 7d. Darkness = `LastSuccessTimestamp` succeeded-gate (`workflow_handler.py:319,:330-339`) OR PutMetricData IAM/namespace denial (`cache_warmer.py:81`). | symptom `proven` (stale LST); cause `emitting`-only (two live hypotheses, undiscriminated) | CW Errors 0×7 / Invocations 1/day (§A-a) |
| **S2** | recon 06-20..23 invocation gap is unexplained | **EXPLAINED.** Rule `autom8y-account-status-recon-schedule` **State=DISABLED** (`cron(0 */4 * * ? *)`). Gap is a true gap (metric non-silent on 06-18/19/24). | `proven` | `describe-rule` State=DISABLED + Invocations trail (§A-b) |
| **S3** | FORK-1 deprecated `/v1/query` retire provable on `*_handler_router_prod` / `lambda-python-asana_handler-prod` | **GROUPS DO NOT EXIST** (named ones); legacy aliases are DEAD (2025-07-21 / 2023-07-27). On LIVE groups: non-silent (18.9M + 951), **0** deprecated hits since 06-01. RETIRE-licensed. | usage `proven`; removal `authored` | `start-query` recordsScanned/Matched (§A-c) |
| **S4** | StatusPush seam is observable on skip | **FALSE.** All four skip reasons are metric-silent; `StatusPush*` emits only inside `if all_entries:` (`push_orchestrator.py:183`); url-absent/invalid-key/disabled are log-only (`gid_push.py:496,:504,:512`); empty-denominator branch has no `else`. | gap `proven` | code reads (§B-1) + critic H-3 GREEN |
| **S5** | prod BridgeFleetHealth exists | **FALSE.** Only `{environment:staging, workflow_id:insights-export}`; emit code dimensions `{workflow_id}` only, no `environment`. No prod dim, no other workflow. | gap `proven` | `list-metrics Autom8y/AsanaBridgeFleet` (§B-2 AL-4) |

---

## §F — Handoff routing

**To Incident Commander (analysis -> coordinate):** S1 freshness budget already consumed (insights
data stale since 06-18 — confirm whether downstream consumers depend on it); S2 recon rule DISABLED
(intended maintenance, or an outage?) — prioritization decision; FORK-1 retire is a confirm-first
production lever (410-canary plan in §D). All four alarms are DESIGN; arming the paging tier needs IC
+ user sign-off.

**To Platform Engineer (instrumentation):** (1) wire `StatusPushSkipped{skip_reason}` at the four
sites in §B-1; (2) add `environment` to the `BridgeFleetHealth`/DMS emit dimensions
(`workflow_handler.py:256-262,:330-339`); (3) IaC the four alarms in §B-2 (un-armed); (4) confirm the
`LastSuccessTimestamp` PutMetricData IAM grant per `cache_warmer.py:81` to discriminate S1's two
hypotheses. Implementation complexity: S/M (metric inserts S; alarm IaC M; IAM probe S).

## §G — Discipline ledger (G-RUNG / G-DENOM / G-PROPAGATE)

- **G-RUNG:** rung named per item, never rounded up. S1 cause held at `emitting`/undiscriminated;
  S3 usage `proven` but removal `authored`; no item claims `live`/`protecting-prod`. No alarm armed
  (DESIGN), so nothing claims `alerting`.
- **G-DENOM:** caught the named-but-dead log-group trap (recordsScanned=0 on dead groups is silence,
  not zero); re-ran on live non-silent groups before reading the deprecated zero; recon 06-20..23
  zero validated against a non-silent metric.
- **G-PROPAGATE:** `StatusPushSkipped{skip_reason}` contract + the prod `BridgeFleetHealth`
  `environment` dimension belong in the **shared bridge observability runbook** (namespace
  `Autom8y/AsanaBridgeFleet`), not a per-service orphan. Filed for the shared obs runbook so every
  bridge workflow (conversation-audit, payment-reconciliation, insights-export) inherits the skip
  contract and the prod fleet dimension uniformly.

**Evidence-grade footing:** Four Golden Signals, symptom-not-cause alerting, percentile latency,
multi-window burn-rate, and error-budget policy are STRONG [SR:SRC-001 Beyer 2016; SR:SRC-002
Beyer 2018]. Threshold values (26h freshness grace, 8h recon window, 99.0% / 96.7% SLO targets)
are [PLATFORM-HEURISTIC] — operational defaults pending baseline, not literature-derived.
