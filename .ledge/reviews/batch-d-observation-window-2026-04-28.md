---
type: review
status: draft
station: P7.B-OBSERVATION
procession_id: cache-freshness-procession-2026-04-27
parent_telos: verify-active-mrr-provenance
parent_telos_field: verified_realized
verification_deadline: 2026-05-27
authored_on: 2026-04-28
authored_by: sre.platform-engineer (Step 5 baseline + observation manifest)
deploy_chain_actual: hotfix #31 → manual workflow_dispatch satellite-receiver run 25042293710 → terraform apply
disposition: BASELINE-CAPTURED-AWAITING-OBSERVATION-WINDOW-CLEAR
t0_timestamp: 2026-04-28T08:35:32Z
---

# Batch-D Observation Window Manifest

This artifact is the **operator-facing observation window protocol** for the
4 Batch-D alarms post-apply. The deploy chain unblocked via three
sequential PRs:

1. **autom8y-asana #31** (test skip) — unblocked Test/Dispatch
2. **autom8y #166** (a8 ref bump merge-SHA) — unblocked Receiver Terraform
3. **manual workflow_dispatch** of `satellite-receiver.yml` (run `25042293710`) on autom8y main HEAD `ab359ca5` — fired the deploy on current main with the fixes

Per PT-1 XC-2 staging discipline: alarms are LIVE with `actions_enabled=false`
(silent observation). After this window's exit criteria clear, operator
authors the `actions_enabled=true` flip Terraform PR.

## §1 T0 baseline anchor (captured 2026-04-28T08:35:32Z)

| Alarm | T0 State | Threshold | Cmp | Period | Eval/Datapoints | ActionsEnabled | Namespace | Metric |
|---|---|---|---|---|---|---|---|---|
| `cache_freshness_warning` | **OK** ("no datapoints, missing→NonBreaching") | 21600 | `>` | 300s | 1 / — | **False** | `Autom8y/FreshnessProbe` | `MaxParquetAgeSeconds` |
| `cache_freshness_sustained_p1` | **OK** ("no datapoints, missing→NonBreaching") | 21600 | `>` | 300s | 6 / 6 | **False** | `Autom8y/FreshnessProbe` | `MaxParquetAgeSeconds` |
| `cache_warmer_failure_offer` | **OK** ("no datapoints, missing→NonBreaching") | 1 | `>=` | 3600s | 1 / — | **False** | `autom8y/cache-warmer` | `WarmFailure` (dim `entity_type=offer`) |
| `cache_warmer_dms_24h` | **OK** ("4 of 24 datapoints non-breaching, 20 missing→Breaching") | 1 | `<` | 3600s | 24 / 24 | **False** | `Autom8y/AsanaCacheWarmer` | `LastSuccessTimestamp` |

**Lambda config at T0**:
- `FunctionName`: `autom8-asana-cache-warmer`
- `LastModified`: `2026-04-28T08:33:05Z` (post-apply)
- `CodeSha256`: `a7bd0e4bd3c901d4355609b8faac4831d0529d70f15648a8049db0acc45bb75d`
- **`ImageUri`: `696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/asana:9110e80`** (carries autom8y-asana hotfix-merge SHA = c00ed989 cache-freshness impl)

**EventBridge schedule at T0**:
- Rule: `autom8-asana-cache-warmer-schedule`
- Schedule: `cron(0 */4 * * ? *)` (every 4h at :00 UTC, per ADR-004)
- State: ENABLED

## §2 Per-alarm acceptable-anomaly thresholds

| Alarm | Acceptable transient | Blocker |
|---|---|---|
| `cache_freshness_warning` | `INSUFFICIENT_DATA` until first CLI invocation emits a `MaxParquetAgeSeconds` datapoint (operator/dev-driven; not Lambda-emitted). `ALARM` for ≤ 6h after first apply if SLO-1 was already in deficit pre-apply. | `ALARM` persists past 12h after first datapoint → warmer not making progress; investigate Stale-1 runbook. |
| `cache_freshness_sustained_p1` | `INSUFFICIENT_DATA` during first 30 min (eval needs 6 datapoints × 5 min). Acceptable to remain OK indefinitely if no CLI invocations. | `ALARM` at any point indicates 30-min-sustained 6h+ staleness; Stale-1 runbook escalated path. |
| `cache_warmer_failure_offer` | `INSUFFICIENT_DATA` until first warmer cycle emits a `WarmFailure` datapoint (rare; only fires on actual failure). | `ALARM` in steady state → real warmer failures on `entity_type=offer`; Warmer-1 runbook. |
| `cache_warmer_dms_24h` | T0 baseline shows 4 historical datapoints from pre-apply era plus 20 missing. Should improve as new 4h-cron warmer cycles emit `LastSuccessTimestamp` (expect 6 emits per 24h). After 24h post-apply, expect SampleCount per-period ≥ 1 for at least 6 hours of the window. | `ALARM` past T+24h → DMS heartbeat absent; warmer not running successfully on new cron; DMS-1 runbook. |

## §3 Check schedule (operator-runnable)

### T+24h check (target: 2026-04-29T08:35Z)

```bash
# Alarm state snapshot
aws cloudwatch describe-alarms \
  --alarm-names \
    autom8-asana-cache-freshness-warning \
    autom8-asana-cache-freshness-sustained-p1 \
    autom8-asana-cache-warmer-failure-offer \
    autom8-asana-cache-warmer-DMS-24h \
  --query 'MetricAlarms[*].[AlarmName,StateValue,StateReason,StateUpdatedTimestamp]' \
  --output table

# DMS cadence check: warmer should fire 6× over 24h on new cron
aws cloudwatch get-metric-statistics \
  --namespace Autom8y/AsanaCacheWarmer \
  --metric-name LastSuccessTimestamp \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d "24 hours ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 14400 \
  --statistics SampleCount

# Warmer-side dedup metric (optional, informational)
aws cloudwatch get-metric-statistics \
  --namespace autom8y/cache-warmer \
  --metric-name CoalescerDedupCount \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d "24 hours ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

**T+24h verdict template**: `[OK | TRANSIENT-EXPECTED | BLOCKER]` per alarm + cadence verification.

### T+48h check (target: 2026-04-30T08:35Z)

Same commands. Records state-progression. By now expect DMS to be firmly OK with 12 datapoints from new 4h cron.

### T+72h check (target: 2026-05-01T08:35Z)

Same commands. Final pre-flip verdict.

## §4 Flip-gate criteria (proceed to Step 6 only if ALL true at T+72h)

```
1. cache_freshness_warning: StateValue=OK
2. cache_freshness_sustained_p1: StateValue=OK
3. cache_warmer_dms_24h: StateValue=OK with at-least-6-non-breaching datapoints in trailing 24h
   (i.e., 4h-cron is producing LastSuccessTimestamp emissions reliably)
4. cache_warmer_failure_offer: StateValue ∈ {OK, INSUFFICIENT_DATA} — NOT ALARM
5. EventBridge cron actually firing every 4h: aws events describe-rule shows ScheduleExpression=cron(0 */4 * * ? *) AND warmer Lambda invocation count ≥ 18 in trailing 72h (3 days × 6 fires/day)
6. No state-flapping observed across 24/48/72h checks (alarms transition cleanly)
```

If ALL true → proceed to Step 6.

## §5 Abort criteria (rollback BEFORE flip-on if observed)

```
1. cache_warmer_dms_24h enters ALARM at any point past T+24h → warmer not running successfully despite cron change. Investigate DMS-1 runbook BEFORE flipping.
2. cache_warmer_failure_offer enters ALARM with non-zero WarmFailure datapoints during T+0 to T+72h → warmer genuinely failing on entity_type=offer. Investigate Warmer-1.
3. cache_freshness_warning OR cache_freshness_sustained_p1 fails to clear within 12h of first warmer-cycle emission (i.e., first new cron fire) → MaxParquetAgeSeconds isn't dropping below 21600s threshold; check S3 parquet mtimes vs cron execution.
4. ECS service-update issue (unrelated; tracked separately) prevents next satellite-receiver run from succeeding cleanly → not a rollback trigger but document the cross-concern.
```

If any abort criterion triggers: HALT flip-on, surface to oncall, investigate root cause, do NOT flip alarm `actions_enabled` to `true` until resolved.

## §6 Step 6 operator-action note (deferred; pre-authored guidance)

When §4 flip-gate criteria all clear at T+72h:

```bash
# Open new branch off autom8y main
cd /Users/tomtenuta/Code/a8/repos/autom8y
git fetch origin main
git worktree add .worktrees/batch-d-flip-on -b batch-d/alarm-flip-on-2026-XX-XX origin/main
cd .worktrees/batch-d-flip-on/terraform/services/asana

# Edit main.tf: remove `actions_enabled = false` lines from 4 alarm resources
# (cache_freshness_warning, cache_freshness_sustained_p1,
#  cache_warmer_failure_offer, cache_warmer_dms_24h)

# Verify: 4 lines removed
git diff main.tf

# Open PR
gh pr create --title "terraform(asana): Batch-D alarm flip-on (post observation window)" \
  --body "Observation window cleared all flip-gate criteria per
.ledge/reviews/batch-d-observation-window-2026-04-28.md §4. Removes
actions_enabled=false from 4 alarms; alarms now route to platform_alerts_topic."
```

After PR merges → satellite-receiver re-runs → `terraform apply` flips alarms to live.

## §7 Step 7 — `/cross-rite-handoff --to=thermia`

Once Step 6 applied + 24h post-flip clean:

```
/cross-rite-handoff --to=thermia
```

Thermia rite re-engages for Track B in-anger-probes (Probes 1, 2, 3, 5).
Probe templates in `.ledge/reviews/P7B-readiness-checklist-2026-04-28.md` §3.
Final `## Verification Attestation` verdict authored at
`.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` per dossier §V.5.
Then PT-A5 Pythia sprint_close + /sos wrap.

## §8 Cross-concern: ECS service-update bug (parallel, NOT blocking this observation)

The same `satellite-receiver` run (`25042293710`) that successfully applied
the cache-warmer Lambda + Batch-D alarms + 4h cron ALSO attempted to update
the autom8y-asana FastAPI ECS service. That update FAILED with:

```
Error: updating ECS Service ...autom8y-asana-service:
  ClientException: advancedConfiguration field is required for all
  loadBalancers when using the canary deployment strategy

with module.service.module.ecs.aws_ecs_service.service,
on .terraform/modules/service/terraform/modules/primitives/ecs-fargate-service/main.tf line 202
```

**Root cause**: `module "service"` block in `autom8y/terraform/services/asana/main.tf` (the FastAPI ECS service, NOT the cache-warmer Lambda) does NOT set `enable_advanced_configuration = true`. PR #165 enabled this for SMS but not asana. The new a8 service-stateless module (post-PR #28 merge to a8) requires the field for canary deployment to pass.

**Impact on this observation window**: NONE. The cache-warmer Lambda + Batch-D alarms + cron applied successfully. The FastAPI ECS service is a separate component. The Lambda runs the cache-warming + freshness CLI; ECS hosts the FastAPI service. They're independent.

**Resolution path** (separate PR, not in observation-window scope): add `enable_advanced_configuration = true` to `module "service"` in `terraform/services/asana/main.tf` (mirror the SMS pattern at PR #165). File as parallel cleanup; track in autom8y main repo.

## §9 Receipts

- Hotfix unblock: PR autom8y-asana#31 merged at `9110e806` (2026-04-27T23:21:12Z).
- a8 ref-bump fix: PR autom8y#166 merged at `ab359ca5` (2026-04-28T08:18:47Z).
- Receiver dispatch (manual workflow_dispatch on current main): run `25042293710` at 2026-04-28T08:27:16Z; terminated at 2026-04-28T08:33:18Z (5min 47s elapsed; jobs partial-success).
- Per-job: Validate Payload ✓, Checkout Satellite Code ✓, Build Service ✓, Validate Deployment Contract ✓, Deploy to ECS (a8 CLI) ✗, Deploy Lambda via Terraform ✗ (failed at ECS service update; Lambda + alarms + cron applied successfully BEFORE the ECS failure halted the run).
- Cache-freshness Track B preconditions cleared: PRE-1 ✓ (PR #28), PRE-2 ✓ (Lambda image=9110e80 carries c00ed989), PRE-3 ✓ (Batch-D Terraform applied), PRE-5 ✓ (deploy SHA matches PR #28 ancestry).
- Track B PRE-4 awaits 1-3d observation window + flip Terraform PR.
- T0 baseline file: `/tmp/batch-d-baseline-anchor-2026-04-28.txt`.
