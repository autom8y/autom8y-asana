---
type: review
status: draft
station: P7.B-PRE
procession_id: cache-freshness-procession-2026-04-27
author_agent: thermia.thermal-monitor
parent_telos: verify-active-mrr-provenance
verification_deadline: 2026-05-27
authored_on: 2026-04-28
disposition: TRACK-B-READINESS-CHECKLIST — operator-runnable; gates Track B execution
---

# P7.B Track B Readiness Checklist

This artifact spells out the **exact operator-runnable predicates and commands**
required to clear PRE-1 through PRE-5, plus the Track B execution sequence
(Probes 1, 2, 3, 5; Probe-4 already discharged at QA Phase D commit `e4b5222d`).

When PRE-1..PRE-5 ALL pass and `actions_enabled=true` is flipped, thermia
re-engages for `thermal-monitor` to execute Probes 1, 2, 3, 5 and author the
final `## Verification Attestation` verdict in
`.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md`.

## §1 Precondition status (2026-04-28 refresh)

| PRE | Predicate | Current state | What clears it |
|---|---|---|---|
| **PRE-1** | `gh pr view 28 --json state --jq '.state' == "MERGED"` | ✓ **CLEARED** (`c00ed989`) | done |
| **PRE-2** | deploy lag from PR #28 merge ≤7d | ⏳ **deploy-pipeline-cycle pending** | autom8y-asana production deploy automation runs against `c00ed989` |
| **PRE-3** | `gh pr view 163 --repo autom8y/autom8y --json state --jq '.state' == "MERGED"` | ⏳ **OPEN/MERGEABLE** at `974c94a2`; CI 5/5 SUCCESS so far | reviewer approval + merge of autom8y#163 |
| **PRE-4** | `aws cloudwatch describe-alarms --alarm-names autom8-asana-cache-freshness-warning autom8-asana-cache-freshness-sustained-p1 autom8-asana-cache-warmer-failure-offer autom8-asana-cache-warmer-DMS-24h --query 'MetricAlarms[*].ActionsEnabled' --output text` returns `True True True True` | ⏳ **0/4 alarms exist today**; PT-1 XC-2 staging requires `actions_enabled=false` initial apply, then 1-3d observation, then flip to `true` | (a) `terraform apply` after #163 merge, (b) 1-3d observation window, (c) `actions_enabled=true` Terraform PR + apply |
| **PRE-5** | deploy SHA = PR #28 merge SHA `c00ed989` | ⏳ **deploy-pipeline-cycle pending** | clears with PRE-2 |

**Mid-attestation refreshed predicate baseline** (2026-04-28 live AWS scan):

| Namespace | Metric inventory | Notes |
|---|---|---|
| `Autom8y/FreshnessProbe` | 5 metrics: `MaxParquetAgeSeconds`, `ForceWarmLatencySeconds`, `SectionCount`, `SectionAgeP95Seconds`, `SectionCoverageDelta` | All 5 emitting from PR #28 in production CW (canary-in-prod model) |
| `Autom8y/AsanaCacheWarmer` | `LastSuccessTimestamp` | DMS heartbeat — emit path at `cache_warmer.py:843-845` (Pascal namespace, hardcoded `DMS_NAMESPACE` constant at `cache_warmer.py:70`) |
| `autom8y/cache-warmer` | `CoalescerDedupCount` | per ADR-006 (coalescer dedup); `WarmSuccess`/`WarmFailure`/`WarmDuration` will land on first warmer Lambda success/failure (per ADR-007 runtime-config) |
| `autom8/lambda` | `StoryWarmSuccess`, `StoryWarmFailure`, `StoryWarmDuration`, `StoriesWarmed` | UNRELATED to cache-warmer (asana-stories warmer; per `P7A-alert-predicates-2026-04-27.md` §10 CORRECTION) |

Existing cache-related alarms (pre-Batch-D apply): `autom8-asana-cache-warmer-dlq-not-empty`, `autom8-asana-cache-warmer-lambda-errors`. Both `OK`, `ActionsEnabled=true`. No Batch-D alarm names yet exist.

## §2 Operator unblock sequence

Discrete steps with verifiable per-step exit criteria:

### Step 1 — Merge `autom8y/autom8y-asana#30` (thermia-close)

- **PR**: https://github.com/autom8y/autom8y-asana/pull/30
- **Scope**: design-substrate documentation (ADR-007, P2/P3/P4 specs, P7.A reviews, dossiers, runbook). NO source-code changes (impl already shipped via PR #28).
- **Verify post-merge**: `git fetch origin main && git log origin/main --oneline -1` shows the new merge commit.
- **Exit criterion**: PR state `MERGED`; main commit SHA recorded.

### Step 2 — Production deploy of `c00ed989` (autom8y-asana)

- **Trigger**: existing CI/CD automation (deploy-pipeline reacts to merges to main).
- **Verify post-deploy**:
  ```
  # Production deploy timestamp + SHA via deploy-pipeline status check
  # (operator inspects deploy-pipeline dashboard or status endpoint)
  ```
- **Exit criterion**: deploy-SHA matches `c00ed989`; PRE-2 + PRE-5 cleared.

### Step 3 — Merge `autom8y/autom8y#163` (Batch-D Terraform)

- **PR**: https://github.com/autom8y/autom8y/pull/163
- **Scope**: 4 alarms (ALERT-1/2/3/4) `actions_enabled=false` + cron `cron(0 2 * * ? *)` → `cron(0 */4 * * ? *)`.
- **Verify post-merge**: `gh pr view 163 --repo autom8y/autom8y --json mergeCommit | jq .mergeCommit.oid` returns SHA.
- **Exit criterion**: PR state `MERGED`; PRE-3 cleared.

### Step 4 — `terraform apply` against autom8y main (autom8y repo)

- **Trigger**: operator runs `terraform apply` against the merged Batch-D state.
- **Verify post-apply**:
  ```
  aws cloudwatch describe-alarms \
    --alarm-name-prefix "autom8-asana-cache-" \
    --query 'MetricAlarms[*].[AlarmName,StateValue,ActionsEnabled]' \
    --output table
  # Expected: 6 alarms total (2 pre-existing + 4 new); the 4 new with ActionsEnabled=False
  ```
- **Exit criterion**: 4 Batch-D alarms exist with `ActionsEnabled=False`. EventBridge schedule for cache_warmer Lambda updated to `cron(0 */4 * * ? *)`.

### Step 5 — 1-3 day baseline observation window

- **Verify state-stability** during this window:
  ```
  # Daily check: alarm states should be steady-state ALARM/OK/INSUFFICIENT, not flapping
  aws cloudwatch describe-alarms \
    --alarm-name-prefix "autom8-asana-cache-" \
    --query 'MetricAlarms[*].[AlarmName,StateValue,StateUpdatedTimestamp]' \
    --output table

  # Also verify cache_warmer Lambda is invoking on the new 4h schedule
  aws cloudwatch get-metric-statistics \
    --namespace Autom8y/AsanaCacheWarmer \
    --metric-name LastSuccessTimestamp \
    --start-time $(date -u -d "26 hours ago" +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 3600 \
    --statistics SampleCount
  # Expected: SampleCount >= 6 over 24h (4h cadence × 24/4 = 6 invocations)
  ```
- **Acceptable anomalies during window** (do not block flip):
  - ALERT-1 / ALERT-2 in `ALARM` state during the first 6h after apply if SLO-1 was already in deficit pre-apply (per `cache-freshness-observability.md` §SLO-1 starts in deficit). Should clear within 6h after first warmer cycle.
  - DMS alarm `INSUFFICIENT_DATA` during first hour — expected (alarm needs at least 1 datapoint to evaluate).
- **Blockers** (delay flip if observed):
  - ALERT-3 (`WarmFailure`) firing in steady state — indicates warmer is genuinely failing on `entity_type=offer`; investigate Warmer-1 runbook BEFORE flipping any alarm to live.
  - DMS alarm in `ALARM` state past the first 24h — indicates warmer has not run successfully; investigate DMS-1 runbook.
- **Exit criterion**: 1-3 days elapsed; no blocking anomaly; alarm states are steady-state.

### Step 6 — Flip `actions_enabled=true` (operator-paced second Terraform apply)

- **Authoring**: another small Terraform PR or local edit removing `actions_enabled = false` lines from the 4 alarms (or setting to `true`).
- **Verify post-apply**: `aws cloudwatch describe-alarms --alarm-names ... --query 'MetricAlarms[*].ActionsEnabled' --output text` returns `True True True True`.
- **Exit criterion**: PRE-4 cleared.

### Step 7 — `/cross-rite-handoff --to=thermia` (resume thermia P7.B)

- All PRE-1..PRE-5 cleared. Thermia rite re-engages for Track B execution.

## §3 Track B Probe Execution Sequence (post-PRE-clearance)

`thermal-monitor` executes 4 probes against the deployed system. Probe-4 already discharged at QA Phase D commit `e4b5222d` (re-run optional as design-review evidence).

### Probe-1 — Force-warm reduces oldest-parquet age below SLA

```
# Capture pre-state
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --json | jq '.freshness.max_age_seconds'
PRE_AGE=$(...)  # capture above

# Run force-warm with --wait
python -m autom8_asana.metrics --force-warm --wait

# Capture post-state (allow up to 5 min for ADR-003 SWR rebuild)
sleep 60
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --json | jq '.freshness.max_age_seconds'
POST_AGE=$(...)

# Receipt: POST_AGE < PRE_AGE; POST_AGE < 21600 (6h)
```

**PASS predicate**: `POST_AGE < 21600` AND `POST_AGE < PRE_AGE`. Records receipt with both values + duration.

### Probe-2 — Alarm fires when max_mtime > SLA threshold

This requires a controlled-staleness setup (or waiting for natural staleness). Cleanest pattern:

```
# Verify each alarm's configured threshold matches spec
aws cloudwatch describe-alarms \
  --alarm-names \
    autom8-asana-cache-freshness-warning \
    autom8-asana-cache-freshness-sustained-p1 \
    autom8-asana-cache-warmer-failure-offer \
    autom8-asana-cache-warmer-DMS-24h \
  --query 'MetricAlarms[*].[AlarmName,Threshold,ComparisonOperator,EvaluationPeriods,Period]' \
  --output table
```

**PASS predicate**: thresholds match spec (`MaxParquetAgeSeconds > 21600`, eval 1 for ALERT-1; eval 6 for ALERT-2; `WarmFailure >= 1` 1h for ALERT-3; `LastSuccessTimestamp < 1` SampleCount 24h `treat_missing_data=breaching` for ALERT-4). Records receipt with verbatim alarm config.

For active firing-validation (more invasive — typically not part of P7.B), would require staleness-injection (e.g., temporarily disabling cron). Default P7.B verdict accepts the threshold-match-evidence as sufficient.

### Probe-3 — Force-warm + freshness CLI compose; ADR-003 acceptance

```
# Sync path: --wait causes L1 invalidation (per ADR-003 HYBRID)
python -m autom8_asana.metrics --force-warm --wait
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --strict
# Expect: exit 0 (fresh data)

# Async path: default (no --wait); accepts SWR rebuild lag
python -m autom8_asana.metrics --force-warm
sleep 60
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --strict
# Expect: exit 0 (eventually fresh) OR exit 1 (still in SWR rebuild window)
```

**PASS predicate**: sync path exits 0 within reasonable time. Async path may have transient deficit acceptable per ADR-003 §Decision.

### Probe-5 — Section-coverage telemetry emits expected metrics in deployed CW

```
aws cloudwatch list-metrics --namespace Autom8y/FreshnessProbe \
  --query 'Metrics[*].MetricName' --output text | tr '\t' '\n' | sort -u
# Expected: 5 metrics — MaxParquetAgeSeconds, ForceWarmLatencySeconds, SectionCount, SectionAgeP95Seconds, SectionCoverageDelta
```

**PASS predicate**: ALL 5 metrics enumerated. **PARTIAL DISCHARGE today** — 2026-04-28 baseline already shows all 5 emitting in production CW (PR #28 pre-deploy emissions from local CLI runs); post-deploy validation just re-confirms with timestamps post-deploy-SHA-`c00ed989`.

## §4 Final Verdict Authoring

After all 4 probes execute, `thermal-monitor` authors the `## Verification Attestation` final verdict in `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md` per schema §4.4. Verdict per dossier §V.5:

- **`ATTESTED`**: PRE-1..PRE-5 PASS AND Probes 1/2/3/5 PASS clean AND no Track B observation-window firings on freshness-bound (lens 1) or failure-mode (lens 4) alarms AND DRIFT-1/2/3 patched in main (i.e., PR #30 merged).
- **`ATTESTED-WITH-FLAGS`**: PRE-1..PRE-5 PASS AND Probes 1/2/3/5 PASS AND ≤2 telos-adjacent DEFERs/DRIFTs remain open with named owner+date AND no Track B alarm firings on critical lenses.
- **`REJECTED-REOPEN`**: any Probe FAIL OR Track B firing on freshness-bound or failure-mode OR ≥1 telos-adjacent DRIFT unresolved without owner OR deadline 2026-05-27 passed without Track B execution.

## §5 Pythia PT-A5 sprint_close (post-attestation)

After final verdict authored, `thermal-monitor` (or main agent) invokes Pythia for `sprint_close` (PT-A5) to validate procession-level through-line consciousness one last time. Captures: did the discharged D8 verified_realized actually verify the inception telos? Are there any unaddressed FLAGs from the procession that should propagate forward to a successor procession?

Then `/sos wrap` thermia session.

## §6 Receipts

- 2026-04-28 live AWS predicate baseline:
  - `Autom8y/FreshnessProbe`: 5 metrics confirmed.
  - `Autom8y/AsanaCacheWarmer`: 1 metric `LastSuccessTimestamp`.
  - `autom8y/cache-warmer`: 1 metric `CoalescerDedupCount`.
  - cache-related alarms: 2 pre-existing (`*-dlq-not-empty`, `*-lambda-errors`), 0 Batch-D alarms.
- PR autom8y-asana#30: OPEN, MERGEABLE.
- PR autom8y#163: OPEN, MERGEABLE; CI 5/5 SUCCESS at first scan.
- main HEAD: `c00ed989` (PR #28 merge); `8fd0aefb` (PR #29 merge); `786eb096` (PR #26 merge).
