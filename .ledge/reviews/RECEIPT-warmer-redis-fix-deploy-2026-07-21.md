---
type: review
subtype: deploy-watch-receipt
status: accepted
artifact_id: RECEIPT-warmer-redis-fix-deploy-2026-07-21
initiative: F1a warmer-floor cure — warmer redis packaging fix (PR #257)
watch_ref: .ledge/reviews/WATCH-f1a-warmers-first-activation-2026-07-21.md §13
deploy_commit: b3da9d8c7d44e3f748d2788e336ca3f3994b2c44
region: us-east-1
account: "696318035277"
date: 2026-07-21
operator: sre platform-engineer (DEPLOY-WATCH, act-and-report PW-4/PW-7)
verdict: "DEPLOYED + IMPORT-CURE REALIZED + FLIP RESTORED DURABLY-IN-IaC 2026-07-21 20:15Z (STOP-condition RESOLVED via autom8y #1189 flip + #1188 pin-refresh; probes b/c pending next -bulk cycle — see WATCH §14)"
---

# RECEIPT — warmer redis packaging fix deploy-watch (PR #257 / b3da9d8c)

> **HEADLINE (STOP condition):** the deploy **SUCCEEDED** (redis packaging fix
> live on all 3 warmers, digest-verified) and its **import-level cure REALIZED**
> (probe (a) PASS — `cache_degraded_mode`/`redis_package_not_installed` absent
> across 35,158 post-deploy events). BUT the deploy **CLOBBERED the F1a flip
> env** on both active warmers (`ASANA_BUDGET_ALLOCATOR_ENABLED` true→absent;
> allocator_boot active→**inert**). The end-to-end cache-fill goal (probes
> (b)/(c)) did **NOT** realize in-window — CurrItems still 0, no Redis writes —
> confounded by the clobbered flip AND a newly-unmasked transient "Too many
> connections" runtime degrade. Reported per the watch's HONESTY clause: partial
> realization is reported as partial.

> **RESOLUTION UPDATE 2026-07-21 ~20:15Z (STOP-condition cleared):** the flip is
> now **durable in IaC and clobber-proof**. autom8y **PR #1189** adds
> `ASANA_BUDGET_ALLOCATOR_ENABLED = "true"` to both active warmer env blocks in
> `terraform/services/asana/main.tf`; **PR #1188** refreshed the stale
> scheduled-lambda image pin `2ee3391 → b3da9d8` (else the dispatch apply would
> have rolled the 6 lambdas OFF the redis fix). Applied via the sanctioned
> service-terraform dispatch (run 29864540858, prod-gate approved) — plan
> corroborated `0 add / 3 change / 0 destroy` = 2 warmers env-only + 1 benign ALB
> default, **zero image roll**. Live: both warmers carry `=true`, keys 24→25 /
> 20→21, CodeSha unchanged 3533b7a8. The end-to-end cache-fill probes (b)/(c)
> await the first post-flip -bulk warm cycle; see WATCH §14.

## Field 1 — PRE-CONTROL (own-hands, pre-deploy 2026-07-21 ~19:08–19:20Z)

| Item | Pre-deploy state |
|---|---|
| Warmer image (all 3) | `autom8y/asana:d11ae57`, CodeSha256 `dcd96528…e106a048` (redis-**less** build) |
| Redis `autom8y-asana-redis-001` CurrItems | **0.0** sustained (last 30m + the §12 24h baseline) — no-op cache |
| Degraded announcement (old image) | `redis_package_not_installed` (WARNING) firing every cold start: ≥11 (cache-warmer) / ≥20 (-bulk) in 4h. `cache_degraded_mode` = 0 (new event absent on old image) |
| F1a flip (pre-deploy, own-hands) | `ASANA_BUDGET_ALLOCATOR_ENABLED=true` PRESENT on cache-warmer (25 keys) + -bulk (21 keys); allocator_boot `state=active/enabled=true` per watch §11.2 |
| Convergence baseline (probe c target) | project **1203404998225231** `uncached_count` **FLAT at 2466** across 4 ticks (17:08 / 17:22 / 17:37 / 17:53Z, entity_type=section) — perfect non-convergence (cache writes nothing) |
| Watched GID 1143843662099250 | `uncached_count` near-full 3191–3293 (matches §8 baseline) |

## Field 2 — COMMAND (the deploy + the F-1 listener apply)

**The auto-deploy (sanctioned merge-to-main path, no --admin, no manual trigger):**
```
merge PR#257 → b3da9d8c on main @ 2026-07-21T19:07:22Z
  → Test [b3da9d8c] SUCCESS @ 19:14Z  (autom8y-asana run 29860169224)
  → Satellite Dispatch @ 19:13:48Z SUCCESS  (workflow_run→repository_dispatch satellite-deploy to autom8y/autom8y)
  → autom8y/autom8y "Satellite Receiver — asana" build 29860632298 (repository_dispatch @ 19:13:57Z)
      job "Build Service / Build and Push" SUCCESS → ECR tag b3da9d8 pushed @ 19:16:03Z
      job "Deploy Lambda via Terraform" SUCCESS → warmer Lambdas updated @ 19:20:15Z   ← env-clobber vector
      job "Deploy to ECS (a8 CLI)" (fair-share lane; separate; still in_progress at watch time)
```
End-to-end merge→warmer-update ≈ **13 min** (faster than the ~35 min prior-deploy memory).

**F-1 listener (applied live via interactive-admin CLI — asana tf apply path is the known snowflake; see Field 6):**
```
aws logs put-metric-filter --log-group-name <each of 3 warmer LGs> \
  --filter-name asana-warmer-cache-degraded-mode \
  --filter-pattern '{ $.event = "cache_degraded_mode" }' \
  --metric-transformations metricName=CacheDegradedMode,metricNamespace=Autom8y/AsanaWarmerCache,metricValue=1
aws cloudwatch put-metric-alarm --alarm-name asana-F1-warmer-cache-degraded-mode \
  --namespace Autom8y/AsanaWarmerCache --metric-name CacheDegradedMode --statistic Sum \
  --comparison-operator GreaterThanThreshold --threshold 0 --period 300 \
  --evaluation-periods 1 --datapoints-to-alarm 1 --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:696318035277:autom8y-platform-alerts
```

## Field 3 — POST-PROOF (own-hands, post-deploy 2026-07-21 19:20–19:35Z)

### 3a. Provenance — the image deployed cleanly (all 3 warmers)
| Function | CodeSha256 (after) | ImageUri | LastModified | UpdateStatus |
|---|---|---|---|---|
| autom8-asana-cache-warmer | `3533b7a8…8657b3f6` | `…/autom8y/asana:b3da9d8` | 2026-07-21T19:20:15Z | Successful |
| autom8-asana-cache-warmer-bulk | `3533b7a8…8657b3f6` | `…/autom8y/asana:b3da9d8` | 2026-07-21T19:20:15Z | Successful |
| autom8-asana-cache-warmer-section | `3533b7a8…8657b3f6` | `…/autom8y/asana:b3da9d8` | 2026-07-21T19:20:09Z | Successful |

- ECR digest for tag `b3da9d8` = `sha256:3533b7a88970bbd13cc328a2decdeecdd6a7eea09fcc0f3987ace8228657b3f6`
  = **EXACT match** to all 3 Lambdas' CodeSha256 (container-Lambda provenance: CodeSha256 == image manifest digest → the warmers run exactly the b3da9d8 image). Changed FROM the redis-less `dcd96528…`.

### 3b. ⚠ SURPRISE-1 (STOP condition) — the deploy CLOBBERED the F1a flip env
| Function | keys before→after | `ASANA_BUDGET_ALLOCATOR_ENABLED` before→after | allocator_boot after |
|---|---|---|---|
| autom8-asana-cache-warmer | 25 → **24** | `true` → **ABSENT** | (shares image) |
| autom8-asana-cache-warmer-bulk | 21 → **20** | `true` → **ABSENT** | `state=inert, enabled=false` @ 19:25:56Z |

- Corroborated three ways: (i) env key NAMES list — `ASANA_BUDGET_ALLOCATOR_ENABLED` absent post-deploy; (ii) key count dropped by exactly 1 (the flip key) on each; (iii) the app's own telemetry `allocator_boot` reverted `active/enabled=true` → **`inert/enabled=false`**.
- **Root cause (structural, GUARANTEED to recur):** the `Deploy Lambda via Terraform` build step runs `terraform apply` on the warmer modules (`terraform/services/asana/main.tf` `module.cache_warmer` env @ **:336-344**, and the mirror `module.cache_warmer_bulk`). That env block does **not** contain `ASANA_BUDGET_ALLOCATOR_ENABLED` — it is **nowhere in the autom8y monorepo IaC** (grep = 0 hits). The F1a flip was a manual `aws lambda update-function-configuration` (env drift); terraform-apply reverts drift on **every** deploy. This is the classic "manual env mutation clobbered by IaC deploy" (config-drift anti-pattern).

### 3c. Probe (a) — PASS: the import-level redis fix REALIZED
- `cache_degraded_mode` = **0** and `redis_package_not_installed` = **0** across **35,158** post-deploy `-bulk` events (2 cold starts, 19:25:56Z + warm-reuse). Live positive corroboration: `Production environment with Redis configured, using RedisCacheProvider`, `dataframe_cache_put`/`progressive_tier_put_success`/`cache_warm_success`. → `import redis` now resolves in prod; the packaging fix (PR #257 core) is realized.

### 3d. Probe (b) — NOT realized in-window
- Redis `autom8y-asana-redis-001`: **CurrItems = 0.0** (60s granularity, sustained through 19:35Z); **SetTypeCmds = empty** (no writes reaching the cluster); CurrConnections = **5.0** flat (warmer IS connected).
- ⚠ SURPRISE-2 — the redis fix UNMASKED a downstream degrade: `backend_entering_degraded_mode` reason **"Too many connections"** (x2, 19:26:11–14Z, WARNING, cold-start only, self-healed). At only 5 cluster connections on a `cache.t4g.micro` (server maxclients ~65k), this is a **client-side pool limit**, not the server ceiling.
- **Attribution is confounded** and reported as such: (i) the clobbered flip means the F1a per-chunk banking is OFF (allocator inert), and (ii) the transient connection degrade. CurrItems=0 persisted AFTER the transient cleared, so the cache-fill likely depends on the flip being ON and/or a further write-path detail. Whether (b) realizes with the flip restored is **UNPROVEN** — the clobber destroyed the clean test.

### 3e. Probe (c) — no post-deploy datapoint in-window
- Project 1203404998225231 was **not swept** by `-bulk` post-deploy within the window (the queue had not rotated to it). Absent a cache fill (3d), it would not shrink regardless. The durable read is the 2026-07-22 peak — which will observe an **INERT** allocator unless the flip is restored first.

### 3f. F-1 listener — applied LIVE + verified
- 3 metric filters (`asana-warmer-cache-degraded-mode`, pattern `{ $.event = "cache_degraded_mode" }` → `Autom8y/AsanaWarmerCache/CacheDegradedMode`) on all 3 warmer log groups + alarm `asana-F1-warmer-cache-degraded-mode` (Sum>0, period 300, notBreaching, → `autom8y-platform-alerts`). State: INSUFFICIENT_DATA → settles OK (quiet-when-healthy). Topic delivers (Slack lambda + email subs confirmed).
- ⚠ COVERAGE NOTE: F-1 matches `cache_degraded_mode` (boot/import degrade, ERROR — exactly the PR#257 companion + the task spec). It does **NOT** match `backend_entering_degraded_mode` (the runtime connection-degrade, WARNING, inherited from the cache base class). Recommend a SEPARATE, sustained-threshold listener for runtime degrade (naive threshold-0 would be noisy — the "Too many connections" blips self-heal). Not built here (deliberate; avoids a noisy alarm).

## Field 4 — ROLLBACK
- **Image rollback (NOT recommended):** revert b3da9d8c + redeploy returns the warmers to `d11ae57` (the redis-**less** build) = re-breaks the import. The redis fix itself is GOOD (probe (a) realized); do not roll it back.
- **Flip restore (the actual remediation for the clobber):** re-apply the F1a flip per watch §11.1 (`get-function-configuration` → `jq '. + {ASANA_BUDGET_ALLOCATOR_ENABLED:"true"}'` → `update-function-configuration`) on cache-warmer + -bulk. **Durable fix (required or it re-clobbers next deploy):** add `ASANA_BUDGET_ALLOCATOR_ENABLED = "true"` to `terraform/services/asana/main.tf` `module.cache_warmer` env (:336-344) + `module.cache_warmer_bulk` env, in the **autom8y monorepo** (cross-repo). Then terraform-apply preserves the flip.
- **"Too many connections":** investigate the RedisCacheProvider client connection-pool sizing vs Lambda concurrency (t4g.micro server ceiling is not the limit).
- **F-1 listener rollback (if ever unwanted):** `aws logs delete-metric-filter --log-group-name <LG> --filter-name asana-warmer-cache-degraded-mode` (x3) + `aws cloudwatch delete-alarms --alarm-names asana-F1-warmer-cache-degraded-mode`.

## Field 5 — FILED
- This receipt: `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/RECEIPT-warmer-redis-fix-deploy-2026-07-21.md`
- Watch update: `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/WATCH-f1a-warmers-first-activation-2026-07-21.md` §13 (dated deploy-watch block)
- F-1 code-of-record (authored, un-committed): `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/terraform/services/asana/warmer_cache_degraded_alarm.tf`

## Field 6 — NOTIFIED
- F-1 listener applied directly (CLI) per the task's snowflake-path guidance: the asana tf tree has **no wired apply pipeline and no backend/state** (the sibling `observability_alarms.tf` AL-1..AL-4 suite has sat authored-un-applied since 2026-07-01). A PR into it would produce an authored-but-never-live alarm. The live listener + this receipt + the byte-matched code-of-record tf are the durable record.
- **STOP-condition escalation (this report):** the flip clobber is surfaced to the operator/dispatcher as the headline. Not auto-re-flipped — the task mandates STOP+report on clobber, and a bare re-flip just re-creates the drift; the durable fix is IaC + a connection-pool investigation. Operator levers: (1) restore flip + durable-IaC it; (2) investigate "Too many connections"; (3) the 2026-07-22 peak reads against an inert allocator until (1).
