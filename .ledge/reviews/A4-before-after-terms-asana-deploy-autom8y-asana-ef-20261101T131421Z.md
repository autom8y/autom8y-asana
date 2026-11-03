---
type: review
status: proposed
task: A4
clerk_row: 18047
scope: BEFORE record + AFTER terms for the asana deploy of the phone-field annotation change
repo: autom8y/autom8y-asana
main_at_read: d912fa0d3e59
read_window_utc: 2026-11-01T13:05Z to 2026-11-01T13:14Z
stamped_utc: 2026-11-01T13:14:21Z
author_role: observability-engineer (sre, borrowed seat)
mode: READ-ONLY (describe/get/list, metric reads, alarm reads, gh run list/view; zero writes, invokes or dispatches)
---

# A4: BEFORE record and AFTER terms, asana deploy (annotation-only change)

Stamp: `date -u` = 2026-11-01T13:14:21Z. Region us-east-1. All times are UTC.
Shas and digests are 12-hex prefixes. Resources are named by service or function name only.

## 0. Premise corrections (read these first)

The brief makes three assumptions about the deploy path. The reads contradict all three.

| # | Brief premise | What the read shows | Consequence for the AFTER |
|---|---|---|---|
| P-1 | The hybrid stack publishes "the enrollment-intent-bridge Lambda". | **No such function exists.** `list-functions` returns no name containing `enrollment-intent`, and `get-function autom8-asana-enrollment-intent-bridge` returns ResourceNotFound. At autom8y origin/main 971412f3fa12, `terraform/services/asana/enrollment_intent_bridge_lambda.tf` gates the module on `count = local.enrollment_bridge_provisioned ? 1 : 0`, where provisioned is `var.enrollment_bridge_service_client_id != ""`. The default is `""`, and no tfvars or other file at origin/main sets it. The namespace `Autom8y/AsanaEnrollmentBridge` holds 0 metrics. | This deploy cannot create or publish the bridge. The bridge term becomes an **absence** term (T-5). |
| P-2 | "Satellite Dispatch" success means the deploy ran. | Satellite Dispatch is a 10-second hand-off (run 40207901143: 15:38:33Z to 15:38:43Z, success). The real deploy is **autom8y/autom8y "Satellite Receiver"**. Its last asana run, 40207911746 (2026-10-25T15:38:42Z to 16:58:38Z), concluded **failure**. | The AFTER must read the Receiver run and its jobs, not the dispatcher's conclusion. |
| P-3 | A merge rolls the ECS service. | On 10-25, Receiver job "Deploy to ECS (a8 CLI)" exited 4 with `deployment HELD ... [InsufficientTraffic]: the canary served 0 requests between 15:54:15Z and 15:58:45Z (floor 50; the baseline served 0)`. a8 neither promoted nor rolled back. The 10-25 image (2dcb88fa23e5) reached the served task only on 10-29 (task def 856, deployment created 22:11:34Z), by a path this read did not identify (§6, U-2). | Current traffic is 24 requests/h (last 1 h) and 1643/24 h. That is far below 50 requests per 4.5-minute window. **A HELD outcome on InsufficientTraffic is the expected result**, so the terms define it explicitly (T-2b). |

Additional note: the merge touches `src/`, which is not in test.yml `paths-ignore`, so a push to main must start Test. If Test does not start, that is a FAIL of T-1.

## 1. BEFORE: ECS (cluster `autom8y-cluster`, service `autom8y-asana-service`)

Read at 2026-11-01T13:05Z.

| Field | Value |
|---|---|
| Service status | ACTIVE |
| Task definition | `autom8y-asana-service:856` (registered 2026-10-29T22:10:15Z) |
| desired / running / pending | 1 / 1 / 0 |
| Deployments | 1 (PRIMARY, rolloutState COMPLETED, created 2026-10-29T22:11:34Z, completed 22:27:27Z; 15m53s) |
| Deployment controller / strategy | ECS / CANARY, bakeTimeInMinutes 0, circuit breaker **disabled** (enable=false, rollback=false), min 100% / max 200% |
| asana container image digest (task def = running task) | `2dcb88fa23e5` |
| adot-collector sidecar digest | `40a7eb9bfa58` |
| Running task | started 2026-10-29T22:12:23Z, RUNNING, HEALTHY |
| Target group health | `autom8y-asana-service` target group: 1 target, `healthy` |
| Last steady-state event | 2026-11-01T10:32:26Z ("has reached a steady state"; 6-hour cadence) |
| Task-def config fingerprint (asana image + TF_RENDER_SHA removed) | `e939c98ca9d4` (control: rev 855 has the same image `2dcb88fa23e5` but hash `e57a1aff817c`, so the hash discriminates config) |
| Service config fingerprint | `d865771b1629` |

Implication [TACTICAL | MODERATE]: the circuit breaker is off and a8 HOLDs without rolling back. Nothing automatic reverts a bad canary. The AFTER read is the only detector in the window.

## 2. BEFORE: Lambdas

### 2a. enrollment-intent-bridge

**NOT PRESENT** (P-1). No function, no aliases, no versions, 0 invocations, 0 custom metrics.
BEFORE identity: `absent`.

### 2b. asana hybrid-stack Lambdas (what the Receiver's "Deploy Lambda via Terraform" job publishes)

None has an alias, and each publishes only `$LATEST`. Their EventBridge targets are **unqualified** (checked on cache-warmer and insights-export), so `$LATEST` is what gets served. The alias trap does not apply because there is no alias to diverge from `$LATEST`.

| Function | Package | `$LATEST` identity | LastModified | State |
|---|---|---|---|---|
| autom8-asana-traffic-offer-divergence | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-cache-warmer-section | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-insights-export | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-onboarding-walkthrough | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-conversation-audit | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-cache-warmer | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-prov-sweep | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-unit-reconciliation | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-cache-warmer-bulk | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-scheduling-stratum-snapshot | Image | `2dcb88fa23e5` | 2026-10-25T16:58:05Z | Active |
| autom8-asana-soak-sentinel | Zip | `g9E4cAlZt55o` (CodeSha256 b64 prefix) | 2026-06-18T22:22:36Z | Active |

- Lambda config fingerprint, 11 functions, identity fields removed: `c9c0566e35a7`
- Schedule rules `autom8-asana-*`: 10 rules, **10 DISABLED, 0 ENABLED**; fingerprint `9bf35f6f606d`
- The Lambda image matches the ECS image (`2dcb88fa23e5`). Today Lambda and ECS image identity agree.

## 3. BEFORE: CloudWatch alarms

- Name contains `asana`/`Asana`: **72 alarms, 56 OK, 16 ALARM**. Composite alarms matching asana: 0. No alarm without asana in its name targets asana dimensions.
- Alarm-set fingerprint, AL5 excluded (71 rows): **`cdf84aea87af`** (method in §7).
- **Flapping alarm excluded from transition terms**: `asana-AL5-offer-frame-stale-*` (name carries a GID). It made 47 OK-to-ALARM transitions since 2026-10-25, about 0.28 per hour, so roughly a 25% chance of a transition in any 60-minute window with no deploy. It was OK at read, last changed 2026-11-01T12:31:50Z.
- **Fast Burn / High Error Rate**: no CloudWatch alarm with these names targets asana. `Asana Availability Fast Burn` / `Slow Burn` and `High Error Rate` are **Grafana alert rules** (autom8y `docs/reliability/SLO-REGISTRY.md:217`, `terraform/modules/platform/stacks/grafana-service-alerts/locals_ecs.tf:87`). Their state was **NOT TAKEN** (§6, N-1). The CloudWatch burn alarms currently in ALARM (`autom8-auth-mysql-sync-latency-fast-burn` 2026-11-01T12:13:26Z, `-slow-burn` 2026-10-31T20:14:15Z) belong to auth and are out of scope.
- Asana HTTP and error alarms, all OK: `autom8y-asana-service-canary-5xx` (Target_5XX Sum > 10 per 60 s for 3 periods; OK since 2026-06-07), `autom8y-asana-no-healthy-targets` (OK since 2026-07-01), `autom8y-asana-service-canary-healthy-host-serving` (OK since 2026-08-10), `autom8y-asana-service-canary-response-time` (OK since 2026-09-22), and all ten `*-lambda-errors` alarms.
- **Standing ALARM set (16)**, all transitioned on or before 2026-09-08. These are pre-existing and not deploy-caused:

| Alarm | In ALARM since |
|---|---|
| autom8-asana-cache-warmer-DMS-24h | 2026-06-04T18:40:30Z |
| autom8-asana-exports-request-presence-DMS | 2026-06-12T11:28:36Z |
| asana-PROV-9-offer-artifact-uncovered | 2026-08-19T15:24:06Z |
| asana-PROV-2-heartbeat-absence | 2026-09-05T09:22:56Z |
| autom8-asana-cache-warmer-bulk-lambda-liveness | 2026-09-05T11:28:45Z |
| autom8-asana-cache-warmer-bulk-cadence-DMS | 2026-09-05T11:28:48Z |
| autom8y-auth-token-exchange-dark-asana-insights-export | 2026-09-05T12:01:45Z |
| asana-stratum-universe-collapse | 2026-09-05T14:01:34Z |
| asana-stratum-producer-dead | 2026-09-05T14:01:38Z |
| autom8y-asana-story-warm-dead | 2026-09-05T14:30:45Z |
| asana-stratum-substrate-stale | 2026-09-05T15:01:40Z |
| asana-r7-active-offer-roster-floor | 2026-09-06T00:01:42Z |
| autom8-asana-unit-reconciliation-lambda-liveness | 2026-09-06T02:55:10Z |
| asana-r7-evaluator-dead | 2026-09-06T06:01:51Z |
| autom8-asana-cache-warmer-lambda-liveness | 2026-09-06T06:17:36Z |
| autom8-asana-insights-export-lambda-liveness | 2026-09-08T12:07:32Z |

The liveness and DMS alarms in this set are consistent with §2b: every asana schedule is DISABLED. They are reported, not resolved, here.

## 4. BEFORE: error and traffic baselines

ALB `app/autom8-prod-alb/b49b62354ff9d00f`, TargetGroup `targetgroup/autom8y-asana-service/75206e89d0fd529e`. Windows end at 2026-11-01T13:07Z.

| Metric | Last 24 h | Last 1 h | Max hourly in 24 h |
|---|---|---|---|
| HTTPCode_Target_5XX_Count | **0** | **0** | none (0 datapoints) |
| HTTPCode_ELB_5XX_Count | **0** | **0** | none |
| HTTPCode_Target_4XX_Count | 0 | 0 | none |
| RequestCount | 1643 | 24 | 236 (24 hourly datapoints) |
| TargetResponseTime p50 / p99 | 0.789 s / 3.790 s | 0.218 s / 0.623 s | max hourly p99 6.638 s |
| HealthyHostCount (min) | 1 | | |

Positive control: RequestCount returns 24 hourly datapoints on the identical dimension set, so the 5xx zeros are real zeros and not a dimension mismatch.

Lambda (FunctionName dimension; there are no aliases, so no Resource or alias dimension exists):

| Function set | Invocations 24 h | Errors 24 h | Throttles 24 h | Invocations 1 h | Errors 1 h |
|---|---|---|---|---|---|
| each of the 10 image functions | 0 | 0 | 0 | 0 | 0 |
| autom8-asana-enrollment-intent-bridge | 0 (absent) | 0 | 0 | 0 | 0 |

Additional checks: 14-day Invocations = 0 for cache-warmer, insights-export, scheduling-stratum-snapshot and traffic-offer-divergence. Positive control on the same query shape: `autom8-auth-mysql-sync` returns 6 invocations in 24 h, so the zeros are real.

## 5. BEFORE: last deploys for reference

`gh run list -R autom8y/autom8y-asana --workflow "Satellite Dispatch" -L 3`:

| Run id | Conclusion | Created | Head |
|---|---|---|---|
| 40207901143 | success | 2026-10-25T15:38:33Z | cf32e033f2a7 |
| 40083596029 | skipped | 2026-10-24T09:51:13Z | eebac9da192c |
| 40079035438 | skipped | 2026-10-24T08:41:39Z | eebac9da192c |

Downstream autom8y "Satellite Receiver — asana" run 40207911746 (10-25), job timeline:

| Job | Result | Window |
|---|---|---|
| Build Service / Build and Push | success | 15:39:22Z to 15:45:10Z |
| Deploy to ECS (a8 CLI) | **failure** (HELD, InsufficientTraffic, exit 4) | 15:45:24Z to 16:01:28Z |
| Metrics-Smoke Gate | success | 16:01:30Z to 16:02:26Z |
| Deploy Lambda via Terraform | success | **16:56:59Z** to 16:58:38Z |

The Lambda publish landed about 80 minutes after the dispatch. Every Satellite Receiver run in autom8y since 10-25 (data, ads, api-schemas; 9 runs through 2026-11-01T13:11Z) has concluded failure. That is fleet context and is not caused by asana.

## 6. NOT TAKEN and unresolved

- **N-1 Grafana alert state** (`Asana Availability Fast Burn`, `Asana Availability Slow Burn`, `High Error Rate`): NOT TAKEN. Reading Grafana alert state needs a Grafana API credential, and fetching credentials is outside this seat (Tom's floor). The AFTER substitutes the CloudWatch ALB 5xx terms (T-3), which read the same target-group signal.
- **N-2 bridge alias/version read**: NOT TAKEN because the function does not exist (P-1). Absence is recorded instead.
- **U-1** Why the Receiver's Lambda job waited about 55 minutes after the ECS job failed (a hold token or environment approval is suspected; not established).
- **U-2** Which path rolled ECS to task def 856 on 2026-10-29 at 22:10Z with the 10-25 image. It is not a Satellite Dispatch run (none after 10-25). The 10-29 autom8y run list showed no run in 21:40Z to 22:15Z.
- No AWS call failed on auth. Every read in §1 to §5 was taken.

## 7. AFTER terms (declared before the merge)

**Definitions**
- `M` = createdAt of the Test run with `event=push` on the merge sha on main.
- **Window W1** = [M, M+60 min], for CI, ECS and alarms.
- **Window W2** = [M, M+120 min], for the Lambda publish leg only. Evidence: the 10-25 publish landed at dispatch+80 min.
- "New image" `N` = the asana container digest in the newest task def registered in W1. Expect `N` != `2dcb88fa23e5`.
- **Reread commands** must use bash (not zsh) and array-quoted `--dimensions`. The zsh no-word-split scar silently zeroed one BEFORE pass and was caught and rerun.

**T-1 CI chain fires** (W1)
- PASS: a Test run (`event=push`, head = merge sha) concludes success, and a Satellite Dispatch run (`event=workflow_run`, head = merge sha) concludes success, and an autom8y "Satellite Receiver — asana" run starts in W1.
- FAIL: Test is absent or skipped for the merge sha (the path filter cannot suppress a `src/` change), or Test fails, or no Receiver run starts in W1.

**T-2 ECS outcome**: exactly one of T-2a or T-2b holds. Anything else is FAIL.
- **T-2a ROLLED (PASS)**, all within W1:
  - a new task def revision > 856 is PRIMARY, with rolloutState COMPLETED and deployments count back to 1
  - runningCount == desiredCount == 1
  - a "has reached a steady state" event dated after the new deployment's createdAt and inside W1
  - rollout completes within 30 min of the deployment createdAt (BEFORE reference: 15m53s) [PLATFORM-HEURISTIC: about 2x the observed baseline]
  - running asana container digest == `N` != `2dcb88fa23e5`
  - adot-collector digest still `40a7eb9bfa58`
  - target health `healthy`
  - task-def config fingerprint (§7 method) still `e939c98ca9d4`
  - service config fingerprint still `d865771b1629`
- **T-2b HELD-INCONCLUSIVE (not PASS, not FAIL)**: the Receiver's "Deploy to ECS (a8 CLI)" log shows `HELD ... [InsufficientTraffic]`, AND at M+60 all of the following hold:
  - runningCount == desiredCount == 1, target health `healthy`, HealthyHostCount min >= 1 across W1
  - every running asana task's digest is in {`2dcb88fa23e5`, `N`}
  - any new task def revision still matches config fingerprint `e939c98ca9d4`
  - T-3 holds
  - The verdict is "deploy did not complete; nothing regressed". It does **not** prove the change is served. A follow-up read is required once a promotion path runs (U-2).
- **FAIL**, any of:
  - a HELD for any reason other than InsufficientTraffic
  - a rollback
  - runningCount < desired at M+60
  - a task digest outside {old, `N`}
  - a changed config fingerprint (something other than the image or TF_RENDER_SHA changed)
  - more than one deployment still present at M+60 without a HELD log line explaining it

**T-3 errors not above baseline** (W1). The BEFORE baseline is 0 Target 5xx and 0 ELB 5xx over 24 h.
- PASS:
  - Target_5XX + ELB_5XX sum over W1 <= 5, and no single minute > 2 [PLATFORM-HEURISTIC: allows a canary-swap blip. Precedent: the b371deed blue/green swap paged Fast Burn and High Error Rate, test.yml comment]
  - `autom8y-asana-service-canary-5xx` stays OK through W1
  - max 5-minute p99 TargetResponseTime in W1 <= 6.64 s (the BEFORE 24 h max hourly p99)
- FAIL: any of these thresholds is breached. At 24 to 70 requests per hour, 5 errors is a 7% or higher error rate for the hour, which is a real regression and not noise.

**T-4 no new alarm transitions** (W1)
- PASS:
  - no asana alarm except `asana-AL5-offer-frame-stale-*` has a StateUpdate to ALARM with timestamp in W1 (`describe-alarm-history --history-item-type StateUpdate`)
  - the AL5-excluded alarm-set fingerprint equals **`cdf84aea87af`** at M+60 (71 rows, 16 ALARM)
- FAIL: any non-AL5 transition to ALARM in W1, or a changed fingerprint. A standing alarm returning to OK also changes the fingerprint. Record that as a FLAG (improvement, not deploy-caused) and name the alarm, not a FAIL.
- AL5 is reported, not judged. Record its transition count in W1 against the base rate of about 0.28/h.

**T-5 enrollment-intent-bridge stays absent** (W2)
- PASS: `get-function autom8-asana-enrollment-intent-bridge` still returns ResourceNotFound, and `Autom8y/AsanaEnrollmentBridge` still holds 0 metrics.
- FAIL: the function exists. Its creation needs `enrollment_bridge_service_client_id` set, which an annotation merge to asana cannot do. Its appearance would mean an unrelated infra change rode the deploy. If it appears, read `get-alias` and then config with `--qualifier <alias>`, and record what it serves.

**T-6 hybrid Lambdas** (W2). Either outcome passes, as long as the conditions hold.
- **T-6a PUBLISHED (PASS)**: all 10 image functions have `$LATEST` CodeSha256 == `N`, LastModified in W2, State Active, LastUpdateStatus Successful, still 0 aliases, still only `$LATEST` versions.
- **T-6b NOT PUBLISHED (PASS)**: all 10 functions still `2dcb88fa23e5` with LastModified 2026-10-25T16:58:05Z.
- In **both cases** all of these must hold:
  - Lambda config fingerprint `c9c0566e35a7` unchanged
  - soak-sentinel still `g9E4cAlZt55o`
  - schedule fingerprint `9bf35f6f606d` (10 rules, 0 ENABLED)
  - Invocations == 0 and Errors == 0 for all 11 functions in W2
- FAIL: the functions are split across digests; or a digest is neither old nor `N`; or any config, schedule or alias change; or any invocation. An invocation would mean a schedule was enabled or someone invoked a function, and an annotation change does neither.
- FLAG (not FAIL): T-6a with T-2b gives split-brain image identity, with Lambdas on `N` and ECS on the old image. This is the same shape as 10-25 to 10-29. Record it. No served effect follows while all schedules are DISABLED.

**Overall verdict rule**
- PASS = T-1, T-2a, T-3, T-4, T-5 and T-6 all PASS.
- INCONCLUSIVE = T-2b in place of T-2a, with every other term PASS. This is the expected outcome given P-3.
- FAIL = any term FAILs.

### Reread methods (fingerprints print hash prefixes only; they never print config values)

- Alarm set: `describe-alarms` filtered on names containing `asana`/`Asana`, query `[StateValue,AlarmName]`, text output; replace each run of 12 or more digits with `<n>`; drop `asana-AL5-` rows; `LC_ALL=C sort`; take sha256[0:12].
- Task-def config: `describe-task-definition` JSON through `jq -S`. Delete arn, revision, registeredAt, registeredBy, deregisteredAt and status. Sort containers by name. On the asana container, delete `image` and drop the env entry named `TF_RENDER_SHA`. Take sha256[0:12].
- Service config: `jq -S` over {deploymentConfiguration, networkConfiguration, loadBalancers, desiredCount, launchType, platformVersion, capacityProviderStrategy, schedulingStrategy, deploymentController, serviceRegistries, enableExecuteCommand}. Take sha256[0:12].
- Lambda config: for the 11 functions in §2b order, `get-function-configuration` JSON through `jq -S`, deleting CodeSha256, LastModified, RevisionId, Version, LastUpdateStatus*, State*, RuntimeVersionConfig. Concatenate and take sha256[0:12].
- Schedules: `list-rules --name-prefix autom8-asana`, `[Name,State,ScheduleExpression]` text, `LC_ALL=C sort`, sha256[0:12].

Grade: every value above is [TACTICAL | MODERATE]. They are direct reads by this seat at the stamped time. The seat is not rite-disjoint from a future reread, and self-authored terms cap at MODERATE.
