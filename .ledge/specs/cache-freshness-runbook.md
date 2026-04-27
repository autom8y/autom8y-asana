---
type: spec
artifact_type: operational-runbook
status: draft
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
session_id: session-20260427-185944-cde32d7b
phase: design
authored_by: thermal-monitor
authored_on: 2026-04-27
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
schema_version: 1
attester_role: de-facto-verification-auditor (per pantheon-role disambiguation)
companion_spec: .ledge/specs/cache-freshness-observability.md
---

# Operational Runbook — Cache Freshness Incidents

> This runbook is for the `active_mrr` freshness system:
> Lambda cache_warmer + S3 parquets at `s3://autom8-s3/dataframes/1143843662099250/sections/`
> + freshness CLI at `python -m autom8_asana.metrics`.
>
> Every scenario below maps to one or more alerts defined in `cache-freshness-observability.md §3`.

---

## Scenario Stale-1 — Stale Data Detected

**Triggering alerts**: ALERT-1 (freshness breach WARNING), ALERT-2 (sustained breach, P1)

**What happened**: The `MaxParquetAgeSeconds` metric has exceeded 21600 seconds (6h). One or more S3 parquet files at `s3://autom8-s3/dataframes/1143843662099250/sections/` have not been refreshed within the SLO-1 window. The `active_mrr` figure may reflect Asana task state from > 6h ago.

### Detection

ALERT-1 fires (P2, Slack `#autom8y-ops`) on any single invocation showing `max_age > 6h`.
ALERT-2 fires (P1, PagerDuty) after 30 minutes of sustained breach.

Manual detection: run the CLI and read the WARNING line on stderr:
```
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h
```
If stderr contains `WARNING: data older than 6h (max_age=...)`, the SLO is breached.

### Impact assessment

1. Is the breach minor (6h–12h) or severe (> 24h)?
   - Run: `python -m autom8_asana.metrics active_mrr --json | python -m json.tool`
   - Read `freshness.max_age_seconds` from the JSON envelope.
   - < 43200 (12h): Low urgency. Warmer may be running late. Monitor.
   - 43200–86400 (12h–24h): Medium urgency. Warmer likely missed a cycle. Trigger force-warm.
   - > 86400 (24h): High urgency. DMS heartbeat alarm should also be firing (see DMS-1). Warmer has not run in over a day.

2. Which sections are stale? (informational — the freshness probe covers the entire prefix, not per-section):
   ```
   aws s3 ls s3://autom8-s3/dataframes/1143843662099250/sections/ \
     --human-readable --summarize
   ```
   Compare `LastModified` timestamps per parquet against the current time.

3. Is the `active_mrr` dollar figure actively being used for a time-sensitive decision? If yes, escalate immediately to Warmer-1 / force-warm. If no (routine monitoring context), apply the 30-minute observation window before escalating.

### Immediate response

**Step 1** (0–5 min): Acknowledge the Slack alert. Check whether ALERT-2 (PagerDuty) has also fired.

**Step 2** (5–10 min): Determine if the warmer is currently running.
```
# Check CloudWatch for recent WarmSuccess metrics
aws cloudwatch get-metric-statistics \
  --namespace autom8/cache-warmer \
  --metric-name WarmSuccess \
  --dimensions Name=entity_type,Value=offer \
  --start-time $(date -u -v-2H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Sum
```
- If `WarmSuccess` sum > 0 in the last 2 hours: the warmer ran recently. The staleness reading is lagging or the warmer completed but the ACTIVE sections were not refreshed. Proceed to Step 3.
- If `WarmSuccess` sum = 0: the warmer has not completed a successful run recently. Proceed to Warmer-1.

**Step 3** (10–15 min): If warmer ran recently but data is still stale, check whether the `offer` entity type completed:
```
aws cloudwatch get-metric-statistics \
  --namespace autom8/cache-warmer \
  --metric-name WarmFailure \
  --dimensions Name=entity_type,Value=offer \
  --start-time $(date -u -v-2H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Sum
```
- `WarmFailure` > 0 for `entity_type=offer`: the warmer ran but the offer entity warm failed. Proceed to Warmer-1.
- `WarmFailure` = 0 and `WarmSuccess` > 0 for offer: the warmer completed successfully. Staleness is unexpectedly persistent. Check S3 directly for parquet `LastModified` values (Step 2 `aws s3 ls` command above). If timestamps are genuinely old despite recent WarmSuccess, this is an anomaly requiring investigation — escalate to engineering.

**Step 4** (if force-warm available, post-P6 impl): Trigger force-warm:
```
python -m autom8_asana.metrics --force-warm
```
Wait for completion confirmation. Then re-run freshness check:
```
python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --strict
```
Exit code 0 = recovery confirmed.

### Recovery verification

Recovery is confirmed when:
1. `python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --strict` exits 0.
2. The `parquet mtime: ... max_age=` line shows a value < 6h.
3. ALERT-1 and ALERT-2 CloudWatch alarms return to OK state (may take up to one evaluation period = 5 minutes).

### Escalation path

- 0–30 min: On-call operator self-resolves via force-warm.
- 30 min: If force-warm has not resolved staleness, escalate to engineering on-call (P1).
- 2h: If still unresolved, escalate to engineering lead. Consider: is the `active_mrr` figure actively blocking a financial decision? If yes, communicate the staleness explicitly to stakeholders.

---

## Scenario Warmer-1 — Lambda Warmer Failure

**Triggering alerts**: ALERT-3 (warmer failure rate, P2), ALERT-4 (DMS heartbeat absent, P1)

**What happened**: The `cache_warmer` Lambda has either failed to complete a successful warm for the `offer` entity type, or has not invoked at all.

### Detection

ALERT-3 fires when `WarmFailure` count for `entity_type=offer` >= 1 in any 1-hour window.

Manual detection — check Lambda execution logs:
```
# Get recent Lambda invocations (replace FUNCTION_NAME with actual Lambda name)
aws logs filter-log-events \
  --log-group-name /aws/lambda/FUNCTION_NAME \
  --start-time $(date -u -v-2H +%s000) \
  --filter-pattern "entity_warm_failure"
```

Check for self-continuation pattern (timeout, not failure):
```
aws logs filter-log-events \
  --log-group-name /aws/lambda/FUNCTION_NAME \
  --start-time $(date -u -v-2H +%s000) \
  --filter-pattern "exiting_early_timeout"
```

### Impact assessment

1. **WarmFailure for entity_type=offer specifically?**
   - Yes: `active_mrr` parquets are directly affected. Freshness SLO-1 breach is imminent if not already present.
   - No (other entity types only): `active_mrr` may be temporarily unaffected. Monitor.

2. **Is this a Lambda execution error or a timeout continuation?**
   - `exiting_early_timeout` in logs: Lambda timed out and self-continued. This is NOT a `WarmFailure` — it is normal checkpoint behavior at `cache_warmer.py:399-425`. Check whether the subsequent self-invocation completed.
   - `entity_warm_failure` in logs with an `error` field: genuine warm failure. Proceed to diagnosis below.

### Diagnosis steps

**Step 1**: Read the error field from CloudWatch Logs:
```
aws logs filter-log-events \
  --log-group-name /aws/lambda/FUNCTION_NAME \
  --start-time $(date -u -v-2H +%s000) \
  --filter-pattern "entity_warm_failure" \
  --query "events[*].message"
```
Common error classes:
- `ASANA_PAT` auth error: Asana API token expired or rotated. Requires secret rotation.
- `AsanaClient` rate limit: 429 from Asana API. The warmer should retry; if not, check for missing retry logic.
- S3 write error (`ClientError`): IAM permissions for S3 write may have drifted. Check Lambda execution role.
- Network timeout: transient; usually self-resolves on next invocation.

**Step 2**: Check whether the Lambda is being invoked at all (schedule verification):
```
aws events list-rules --query "Rules[?contains(Name,'cache') || contains(Name,'warmer')]"
aws events list-targets-by-rule --rule RULE_NAME
```
- If no EventBridge rule found: the schedule is missing or was deleted. This is the AP-1 undocumented-schedule failure mode (heat-mapper assessment L124). Requires IaC restoration or schedule recreation.
- If rule found but Lambda not triggered: check rule state (ENABLED/DISABLED).

**Step 3**: Check checkpoint state — is there a stale checkpoint preventing a clean restart?
```
# Checkpoint location is internal to CheckpointManager
# Check S3 for checkpoint artifacts (prefix may vary by Lambda config)
aws s3 ls s3://autom8-s3/cache/ --recursive | grep checkpoint
```
If a stale checkpoint exists (from a failed invocation > 24h ago), clear it to force a full re-warm:
```
aws s3 rm s3://autom8-s3/cache/CHECKPOINT_PATH
```
(Exact checkpoint path depends on `CheckpointManager` configuration — verify from `cache_warmer.py` `checkpoint_mgr` initialization.)

### Remediation

**Transient failure** (network/rate-limit): Wait for the next scheduled invocation. The warmer will retry automatically. If the schedule cadence is > 6h, manually invoke:
```
aws lambda invoke \
  --function-name CACHE_WARMER_FUNCTION_NAME \
  --payload '{"entity_types": ["offer"], "strict": true, "resume_from_checkpoint": false}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/warm-response.json
cat /tmp/warm-response.json
```
Check `statusCode` in response. 200 = success.

**Auth failure**: Rotate the `ASANA_PAT` secret and update the Lambda environment variable (or Secrets Manager entry). Re-invoke Lambda manually after rotation.

**IAM permissions failure**: Add or restore the S3 write permission for the Lambda execution role. Check CloudTrail for `AccessDenied` events against the `autom8-s3` bucket.

**Schedule missing**: Recreate the EventBridge rule. The rule should target the Lambda function with the `cache_warmer.handler` entry point. Cadence: set per P3 capacity-engineer recommendation (D10 closure). Until P3 delivers, use daily (rate(1 day)) as a conservative default.

### Recovery verification

1. Manually invoke the Lambda with `entity_types=["offer"]` as above.
2. Check response `statusCode == 200` and `body.success == true`.
3. Run freshness check: `python -m autom8_asana.metrics active_mrr --staleness-threshold 6h`
4. Confirm no WARNING on stderr.
5. Verify `WarmSuccess` metric incremented in CloudWatch within 5 minutes.

---

## Scenario DMS-1 — Dead-Man's-Switch Heartbeat Absent

**Triggering alerts**: ALERT-4 (P1 CRITICAL — DMS heartbeat absent > 24h)

**What happened**: The `cache_warmer` Lambda has not emitted a successful `emit_success_timestamp` call to `DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"` (`cache_warmer.py:70`) in over 24 hours. This means the Lambda has not completed a full successful warm cycle in at least one full day. Every ACTIVE section parquet is now at least 24h stale, which is 4x the SLO-1 threshold.

This is the most serious freshness incident. ALERT-1 and ALERT-2 should also be firing.

### Immediate response (first 15 minutes)

This is a P1 incident. Page the engineering on-call if not already paged.

**Step 1** (0–5 min): Confirm the DMS is genuinely absent and not a monitoring gap.
```
aws cloudwatch get-metric-statistics \
  --namespace Autom8y/AsanaCacheWarmer \
  --metric-name LastSuccessTimestamp \
  --start-time $(date -u -v-26H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics SampleCount
```
The metric `LastSuccessTimestamp` is emitted by `autom8y_telemetry.aws.emit_success_timestamp(DMS_NAMESPACE)` at `cache_warmer.py:845`, where `DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"` is the constant at `cache_warmer.py:70`. Verified in production via `aws cloudwatch list-metrics --namespace Autom8y/AsanaCacheWarmer` (2026-04-27 thermia P7.A.3 evidence at `.ledge/reviews/P7A-alert-predicates-2026-04-27.md`).

If the metric shows datapoints: the alarm may have fired erroneously (threshold mismatch). Verify alarm configuration. If genuinely absent: proceed.

**Step 2** (5–10 min): Check Lambda invocation history:
```
aws logs describe-log-streams \
  --log-group-name /aws/lambda/CACHE_WARMER_FUNCTION_NAME \
  --order-by LastEventTime \
  --descending \
  --max-items 5
```
- Last log stream > 24h old: Lambda has not been invoked. Schedule is likely broken (AP-1). Proceed to Warmer-1 Step 2 (schedule verification).
- Log streams present in last 24h but no `handler_success` or DMS metric: Lambda is invoked but consistently failing before reaching the DMS emit at `cache_warmer.py:844`.

**Step 3** (10–15 min): If Lambda is invoking but failing before the DMS emit, check for unhandled exceptions:
```
aws logs filter-log-events \
  --log-group-name /aws/lambda/CACHE_WARMER_FUNCTION_NAME \
  --start-time $(date -u -v-26H +%s000) \
  --filter-pattern "ERROR"
```
The DMS emit at `cache_warmer.py:844-845` is inside the final `if response.success:` block. An exception caught at `cache_warmer.py:833-840` sets `response.success = False`, preventing the DMS emit. Read the `message` field in the error response.

### Force-warm escalation (post-P6)

Once the root cause is identified and mitigated, manually invoke a full warm:
```
aws lambda invoke \
  --function-name CACHE_WARMER_FUNCTION_NAME \
  --payload '{"entity_types": null, "strict": false, "resume_from_checkpoint": false}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/dms-recovery.json
cat /tmp/dms-recovery.json
```
`entity_types: null` invokes all entity types in cascade order. `resume_from_checkpoint: false` forces a clean start (avoids stale checkpoint confounding).

### Recovery verification

1. `cat /tmp/dms-recovery.json` shows `statusCode: 200` and `body.success: true`.
2. CloudWatch `Autom8y/AsanaCacheWarmer` namespace shows a new datapoint within 5 minutes.
3. ALERT-4 CloudWatch alarm transitions to OK state (may take up to 24 evaluation periods = up to 24 hours for the full alarm to clear — the SampleCount-based alarm evaluates over a 24h window).
4. Run: `python -m autom8_asana.metrics active_mrr --staleness-threshold 6h --strict` — expect exit 0 within minutes of successful Lambda completion.
5. Confirm re-warm: `aws s3 ls s3://autom8-s3/dataframes/1143843662099250/sections/` shows updated `LastModified` timestamps.

### Escalation

- 0–30 min: On-call engineers following this runbook.
- 30 min: Engineering lead + any consumer of `active_mrr` who is waiting on a decision — communicate the data is > 24h stale.
- 1h: If Lambda cannot be successfully invoked, escalate to platform engineering (Lambda execution role, VPC, or account-level issues may be blocking).

---

## Scenario ForceWarm-1 — Force-Warm Invocation Failure

**Triggering alerts**: None (force-warm is operator-initiated, not scheduled). Observable via `ForceWarmLatencySeconds` metric exceeding 300s.

**Precondition**: The `--force-warm` CLI affordance is a P6 impl item (PRD NG4). This scenario applies post-P6 deployment.

**What happened**: The operator invoked `python -m autom8_asana.metrics --force-warm` and either (a) the command returned an error, (b) the freshness signal did not improve after the expected completion time, or (c) the force-warm timed out.

### Diagnosis

**Error pattern 1**: Command returns immediately with an error about Lambda invocation:
```
ERROR: force-warm failed: could not invoke Lambda cache_warmer — [reason]
```
- Check IAM permissions: the CLI's execution identity must have `lambda:InvokeFunction` on the `CACHE_WARMER_FUNCTION_NAME` Lambda.
- Check `ASANA_CACHE_S3_BUCKET` and Lambda function name env vars are set.

**Error pattern 2**: Command returns success but freshness does not improve:
- The Lambda may have been invoked but failed internally. Check CloudWatch for `WarmFailure` metrics and Lambda logs (Warmer-1 diagnosis steps apply).
- The `--force-warm` implementation may be fire-and-forget (invoked without waiting for completion). In that case, wait 3–5 minutes and re-run the freshness check.

**Error pattern 3**: MINOR-OBS-2 botocore traceback on bucket misconfiguration:
```
botocore.exceptions.ClientError: ... NoSuchBucket ...
```
This is the uncaught exception gap at `src/autom8_asana/metrics/__main__.py:239`. Cause: `ASANA_CACHE_S3_BUCKET` is set to a non-existent bucket name. Verify the env var: `echo $ASANA_CACHE_S3_BUCKET`. Expected value: `autom8-s3` (stakeholder-affirmed production bucket, `prd.md:261-267`).

### Recovery verification

Same as Stale-1 recovery steps 1–3.

---

## Scenario S3-1 — S3 IO Error

**Triggering alerts**: ALERT-5 (S3 IO error rate, P2 or P1 depending on `kind`)

**What happened**: The `FreshnessReport.from_s3_listing` call at `src/autom8_asana/metrics/freshness.py:141` raised a `FreshnessError`. The CLI emitted an `ERROR: S3 freshness probe failed (kind): ...` line to stderr and exited 1.

### Error kind triage

**kind=auth** (ALERT-5 P2):
- Symptoms: `ERROR: S3 freshness probe failed (auth): could not authenticate against s3://autom8-s3/...`
- Cause: `ASANA_CACHE_S3_REGION` is wrong, AWS credentials have expired, or the execution identity lacks `s3:ListBucket` on `autom8-s3`.
- Check: `aws s3 ls s3://autom8-s3/dataframes/1143843662099250/sections/` (if this works, the issue is in the CLI's credential context, not the bucket).
- Fix: Refresh credentials / `direnv allow` / check secretspec profile. Validate: `secretspec check --config secretspec.toml --provider env --profile cli`.

**kind=not-found** (ALERT-5 P1):
- Symptoms: `ERROR: S3 freshness probe failed (not-found): s3://autom8-s3/... does not exist`
- Cause: The bucket `autom8-s3` or the prefix `dataframes/1143843662099250/sections/` does not exist. This may indicate:
  - `ASANA_CACHE_S3_BUCKET` is misconfigured (bucket-typo / MINOR-OBS-2 scenario)
  - The cache has been accidentally deleted
  - The project GID has changed
- Check: `aws s3 ls s3://autom8-s3/` (verify bucket exists). If bucket exists but prefix is missing, the parquets were deleted or never written. Trigger a full re-warm (Warmer-1 remediation).
- Escalate immediately if the bucket itself is missing — this is a data-loss incident.

**kind=network** (ALERT-5 P2):
- Symptoms: `ERROR: S3 freshness probe failed (network): could not reach s3://autom8-s3/...`
- Cause: Network connectivity issue between the CLI execution environment and the `us-east-1` S3 endpoint (default region at `freshness.py:134`). May be transient.
- Check: `curl -s https://s3.amazonaws.com/` or `aws s3api head-bucket --bucket autom8-s3`.
- Fix: Usually transient. Retry after 30 seconds. If persistent, check VPN / network routing / `ASANA_CACHE_S3_REGION` env var.

**kind=unknown** (ALERT-5 P2):
- Symptoms: `ERROR: S3 freshness probe failed (unknown): ...`
- Cause: An unexpected boto3/botocore exception. Read the `underlying` repr in the error message.
- Escalate to engineering if the error is not recognizable from the underlying repr.

### Recovery verification

1. Resolve the identified root cause.
2. Re-run: `python -m autom8_asana.metrics active_mrr --staleness-threshold 6h`
3. Confirm no `ERROR: S3 freshness probe failed` line on stderr.
4. Confirm exit code 0 (fresh) or 0 with WARNING (stale but readable).

---

## Quick Reference — Alert to Runbook Mapping

| Alert | Severity | Runbook |
|---|---|---|
| ALERT-1: MaxParquetAgeSeconds > 6h (single invocation) | P2 | Stale-1 (initial response) |
| ALERT-2: MaxParquetAgeSeconds > 6h sustained 30min | P1 | Stale-1 (escalated) |
| ALERT-3: WarmFailure >= 1 in 1h (entity_type=offer) | P2 | Warmer-1 |
| ALERT-4: DMS heartbeat absent > 24h | P1 | DMS-1 |
| ALERT-5: FreshnessError count >= 2 in 1h | P2/P1 | S3-1 |
| ALERT-6: SectionCoverageDelta > 0 | NO ALERT — informational | No action needed per PRD C-6 |

## Key File:Line References for On-Call

| Reference | Location |
|---|---|
| DMS namespace constant | `src/autom8_asana/lambda_handlers/cache_warmer.py:70` |
| DMS emit call | `src/autom8_asana/lambda_handlers/cache_warmer.py:844-845` |
| WarmSuccess emit | `src/autom8_asana/lambda_handlers/cache_warmer.py:473` |
| WarmFailure emit | `src/autom8_asana/lambda_handlers/cache_warmer.py:501` |
| Checkpoint save on timeout | `src/autom8_asana/lambda_handlers/cache_warmer.py:416-421` |
| Self-invocation continuation | `src/autom8_asana/lambda_handlers/cache_warmer.py:425` |
| FreshnessReport factory | `src/autom8_asana/metrics/freshness.py:99` |
| FreshnessError kinds | `src/autom8_asana/metrics/freshness.py:39-42` |
| CLI strict-mode exit | `src/autom8_asana/metrics/__main__.py:341` |
| MINOR-OBS-2 gap | `src/autom8_asana/metrics/__main__.py:239` |
| S3 prefix pattern | `src/autom8_asana/metrics/__main__.py:273` |
| Production bucket | `s3://autom8-s3` (stakeholder-affirmed, `prd.md:261-267`) |
