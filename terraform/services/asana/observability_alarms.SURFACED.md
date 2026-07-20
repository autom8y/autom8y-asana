# SURFACED operator levers — observability alarm suite (AL-1..AL-5 + C4 DMS retire)

> Every command below is a **PROD-BEHAVIOR MUTATION**. None has been executed by
> the build that authored `observability_alarms.tf`. They are printed here for
> operator review and confirm-first execution. G-RUNG: authoring the alarm IaC
> is `authored`; running these moves it to `alerting` / `live` / `protecting-prod`.
> A metric proven in a test fixture is `emitting`, **not** `proven` in prod.

Account `696318035277` / region `us-east-1`. Source: N1 §B-2, postmortem §4/§5.

---

## L-1 — Apply the alarm IaC (creates the alarms, UN-ARMED)

Creating the alarms is itself a prod mutation (new CloudWatch resources). It is
safe-because-un-armed (no SNS action wired with the default vars), but it is NOT
fired by this change. Run from the directory containing `observability_alarms.tf`
once it is wired into the real apply pipeline (this repo holds the authored HCL;
the live apply pipeline is cross-repo — see Handoff note):

```
# DO NOT FIRE — operator review first.
terraform init
terraform plan -out=alarms.tfplan          # expect: 7 alarms to add (AL-1..AL-4), 0 SNS actions;
                                            # AL-5 adopts the LIVE canary via L-6 import FIRST (else plan shows +2 AL-5 resources)
terraform apply alarms.tfplan               # creates AL-1..4 alarms in INSUFFICIENT_DATA, no paging
```

Expected post-apply: AL-1 (×4 skip_reason), AL-2, AL-3, AL-4 (×1 workflow) all
present via `aws cloudwatch describe-alarms --alarm-name-prefix asana-AL` with
empty `AlarmActions`.

## L-2 — Arm the PAGE tier (confirm-first; per-alarm opt-in)

```
# DO NOT FIRE — requires IC + operator sign-off (G: confirm-first).
terraform apply \
  -var 'arm_paging=true' \
  -var 'page_sns_topic_arn=arn:aws:sns:us-east-1:696318035277:<PAGER_TOPIC>' \
  -var 'paging_armed_alarms=["AL-3"]'        # start narrow; add AL-1/AL-2/AL-4 as baseline allows
```

Per N1 §B-2: AL-1 is TICKET-first (baseline unknown); `url_absent`/`invalid_key`
graduate to PAGE after baseline. AL-2 paging additionally requires `recon_rule_enabled=true`
(see L-4) so it does not page on the intended-off cron.

## L-3 — (AI-3) Grant `cloudwatch:PutMetricData` to the insights-export role

Without this, the LastSuccessTimestamp / BridgeFleetHealth metrics that AL-3/AL-4
watch cannot publish (postmortem CF-2 — verbatim AccessDenied 06-17). IaC the
policy; do not hand-edit. Surfaced shape:

```
# DO NOT FIRE — IAM mutation, IaC-owned, confirm-first.
# Add to the insights-export role's IaC policy document:
#   Effect: Allow  Action: cloudwatch:PutMetricData  Resource: "*"
#   (CloudWatch PutMetricData does not support resource-level scoping;
#    constrain via the cloudwatch:namespace condition key if desired.)
# Verify after deploy (read-only):
aws logs filter-log-events \
  --log-group-name /aws/lambda/autom8-asana-insights-export \
  --filter-pattern '"metric_emit_error"' --max-items 5   # expect: none post-grant
```

## L-4 — (AI-1) Re-enable the recon EventBridge schedule (IC decision)

`autom8y-account-status-recon-schedule` is `State=DISABLED` (postmortem Symptom 1
= EXPECTED). Whether to re-enable is an Incident Commander decision (business-
required vs intentional pause). If re-enabling:

```
# DO NOT FIRE — re-enables a prod cron; IC decision required.
aws events enable-rule --name autom8y-account-status-recon-schedule --region us-east-1
# Verify (read-only):
aws events describe-rule --name autom8y-account-status-recon-schedule \
  --region us-east-1 --query State        # expect: ENABLED
# THEN arm AL-2 paging (L-2 with recon_rule_enabled=true).
```

## L-5 — (AI-5 deploy) Deploy the `environment` BridgeFleetHealth dimension

The `environment` dimension code change (AI-5) is SAFE-AUTONOMOUS to author but
PROD-MUTATING to deploy. AL-4 stays in INSUFFICIENT_DATA until a prod series
exists. The Lambda deploy is the operator lever (cross-repo pipeline).

## L-6 — (AL-5) Import the LIVE per-GID freshness canary + arm

Unlike AL-1..AL-4 (authored-only), the AL-5 metric filter + alarm for the ASR offer
GID `1143843662099250` are **already live** — created via the AWS API as an in-lane,
non-paging observability canary with two-sided teeth proven (RED age=7200s→ALARM
19:45Z; GREEN age=300s→OK 19:48Z; real-log backtest breaching 07-11→07-13), 2026-07-13.
The live resource names **match** the TF names, so a future apply adopts them via
`terraform import` rather than colliding:

```
# DO NOT FIRE — reconciles the live canary into TF state (confirm-first; the CI apply lane is wedged).
terraform import 'aws_cloudwatch_log_metric_filter.al5_offer_frame_age["1143843662099250"]' \
  '/ecs/autom8y-asana-service:asana-AL5-offer-frame-age-1143843662099250'
terraform import 'aws_cloudwatch_metric_alarm.al5_offer_frame_stale["1143843662099250"]' \
  'asana-AL5-offer-frame-stale-1143843662099250'
terraform plan          # expect: 0 changes for AL-5 (live == TF); AL-1..4 still to-add
```

Arm AL-5 paging (confirm-first — NEW paging wiring):

```
# DO NOT FIRE — wires a pager to the per-GID freshness alarm (G: confirm-first).
terraform apply -var 'arm_paging=true' \
  -var 'page_sns_topic_arn=arn:aws:sns:us-east-1:696318035277:<PAGER_TOPIC>' \
  -var 'paging_armed_alarms=["AL-5"]'
```

Register another GID for per-GID detection: add it to `var.substrate_freshness_gids`
(default `["1143843662099250"]`). Byte-verbatim revert of the live canary (in-lane,
non-paging — safe to run without confirmation):

```
aws logs delete-metric-filter --region us-east-1 \
  --log-group-name /ecs/autom8y-asana-service \
  --filter-name asana-AL5-offer-frame-age-1143843662099250
aws cloudwatch delete-alarms --region us-east-1 \
  --alarm-names asana-AL5-offer-frame-stale-1143843662099250
```

## L-7 — (C4) Retire the orphaned warmer dead-man

`autom8-asana-cache-warmer-DMS-24h` is orphaned — it watches `LastSuccessTimestamp`
in the now-EMPTY namespace `Autom8y/AsanaCacheWarmer` (`list-metrics` = `[]`); the
current warmer no longer emits it. Superseded by AL-5 (+ the AL-6 warm-liveness
candidate). Its actions wire to the paging SNS `autom8y-platform-alerts`, so the retire
touches paging topology → confirm-first:

```
# DO NOT FIRE — deletes a paging-wired alarm (confirm-first).
aws cloudwatch delete-alarms --region us-east-1 --alarm-names autom8-asana-cache-warmer-DMS-24h
# Verify (read-only): describe-alarms --alarm-names autom8-asana-cache-warmer-DMS-24h -> no MetricAlarms.
```

---

### Rung ledger for these levers

| Lever | Action class | Rung before | Rung after firing |
|---|---|---|---|
| L-1 apply | PROD-MUTATING (create alarms) | `authored` | `alerting` (un-armed) |
| L-2 arm   | PROD-MUTATING (wire pager)    | `alerting`  | `protecting-prod` |
| L-3 IAM   | PROD-MUTATING (policy)        | `authored`  | `live` |
| L-4 enable| PROD-MUTATING (cron)          | `authored`  | `live` |
| L-5 deploy| PROD-MUTATING (lambda)        | `emitting`(code) | `emitting`(prod series) |
| L-6 import| PROD-MUTATING (TF import)     | `detecting-via-canary` | `merged`+`imported` (0-diff) |
| L-6 arm   | PROD-MUTATING (wire pager)    | `detecting-via-canary` | `protecting-prod` |
| L-7 retire| PROD-MUTATING (delete paging alarm) | `disposition-surfaced` | `retired` |
