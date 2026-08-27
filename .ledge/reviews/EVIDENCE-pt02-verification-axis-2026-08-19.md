---
type: review
status: accepted
title: EVIDENCE — PT-02 bundle, verification-axis landing (producer live + SDK registry resolution)
initiative: asr-verification-axis-landing
gate: PT-02
rite: 10x-dev
author: principal-engineer
created: 2026-08-19
verdict: LEG-1 PASS / LEG-2 PASS
evidence_grade: MODERATE
grade_ceiling_reason: >-
  Single attester, same rite as the builder and the QA. Every receipt below was
  re-derived first-hand (own AWS probes, own token mint, own clean venv, own
  CloudWatch scans with a live positive control), but same-rite convergence
  caps at MODERATE. No STRONG is claimed.
production_change: NONE — read-only against production throughout
pins:
  merge_commit: 412376f4a60fc6a0a8e67a9a1e18fd4fd3e93781
  merged_at_utc: "2026-08-19T17:32:14Z"
  ecs_task_definition: autom8y-asana-service:791
  ecs_image: 696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/asana:412376f
  ecs_image_digest: sha256:6e280c21b760d56cb14ec2180cd9e9f7789a3fc210a355edd6c375ca283cdf80
  sdk_version: autom8y-core 4.16.0
  probed_at_utc: "2026-08-19T18:06Z – 18:27Z"
---

# EVIDENCE — PT-02, verification-axis landing

> **LEG 1 (producer live, the after-trace): PASS.**
> **LEG 2 (SDK registry resolution, RISK-1 closure): PASS.**
>
> Both legs stand on receipts I produced myself. Nothing below is inherited
> from the PR body, the QA file, or the dispatch — those are cited only as the
> **before** side of the diff and as method sources.

**Scars honoured throughout:** every `aws` call carried
`--cli-connect-timeout 5 --cli-read-timeout 20`; every instant in this file is
UTC (the AWS CLI returned `-07:00` offsets, converted explicitly and shown as
both where it matters).

---

## §0 The one thing that had to be established first

The dispatch's premise — *"the satellite rolled the nine lambdas to `:412376f`
at 18:04:48Z"* — does **not** by itself put the axis on the serve path. ASR's
`fetch_offers` talks to `https://asana.api.autom8y.io`, which is **ECS**, not a
Lambda. At my first probe (18:06:17Z) the ECS service was mid-rollout, and it
took **another 18 minutes** before production traffic actually reached
`412376f`. Issuing the after-trace at 18:06 would have produced a false FAIL.

The rollout is a **CANARY** deployment (`strategy: CANARY`, `canaryPercent 10`,
`canaryBakeTimeInMinutes 5`) across two ALB target groups. Verbatim:

```json
{
    "deploymentConfiguration": {
        "maximumPercent": 200,
        "minimumHealthyPercent": 100,
        "strategy": "CANARY",
        "bakeTimeInMinutes": 0,
        "canaryConfiguration": { "canaryPercent": 10.0, "canaryBakeTimeInMinutes": 5 }
    },
    "healthCheckGracePeriodSeconds": 2400
}
```

**Naming trap, recorded because it inverts the obvious reading:** the target
group literally named `a8-asana-green` held the **OLD** revision (`:790`, image
`8098d30`, IP `10.0.151.66`), and the target group named
`targetgroup/autom8y-asana-service` held the **NEW** revision (`:791`, image
`412376f`, IP `10.0.139.125`). Anyone reading "green = new" would have drawn the
opposite conclusion about which revision was serving. Task→IP→TG mapping,
verbatim:

```json
{ "td": ".../autom8y-asana-service:791", "ip": "10.0.139.125", "last": "RUNNING", "health": "HEALTHY", "started": "2026-08-19T11:05:03.864000-07:00" }
{ "td": ".../autom8y-asana-service:790", "ip": "10.0.151.66",  "last": "RUNNING", "health": "HEALTHY", "started": "2026-08-19T10:43:37.983000-07:00" }
```

`healthStatus: HEALTHY` on the ECS task is the **container** health check and is
NOT the serve-path signal: at that same instant the ALB reported the `:791`
target `unhealthy / Target.ResponseCodeMismatch`, because `/ready` was returning
`503` while the frame preload ran. The serve-path anchor is the **ALB production
listener rule's forward weights**, not the task health.

---

## §1 LEG 1 — PRODUCER LIVE (the after-trace) — **PASS**

### §1.1 ECS anchor (the taskdef the serve path actually runs)

```json
{
    "rev": 791,
    "registeredAt": "2026-08-19T11:04:02.608000-07:00",
    "images": [
        { "name": "autom8y-asana-service",
          "image": "696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/asana:412376f" },
        { "name": "adot-collector",
          "image": "public.ecr.aws/aws-observability/aws-otel-collector@sha256:40a7eb9b..." }
    ]
}
```

Terminal service state (after the rollout settled) — a **single** deployment,
`COMPLETED`, on `:791`:

```json
{
    "taskDefinition": "arn:aws:ecs:us-east-1:696318035277:task-definition/autom8y-asana-service:791",
    "deployments": [
        { "status": "PRIMARY",
          "taskDef": ".../autom8y-asana-service:791",
          "rolloutState": "COMPLETED",
          "running": 1,
          "updatedAt": "2026-08-19T11:25:33.636000-07:00" }
    ]
}
```

Cluster discovered by enumeration: `aws ecs list-clusters` returned seven
clusters; `autom8y-asana-service` lives on
`arn:aws:ecs:us-east-1:696318035277:cluster/autom8y-cluster`.

QA baseline reconciliation (QA-v1 §3 NOTE-1): QA observed taskdef `:788` at
image `8098d30` at 17:12Z. I additionally observed `:790` — **also** at image
`8098d30` (registered 17:42:36Z, a re-registration with no image change). So the
20-key baseline QA re-verified at 17:18Z on `8098d30` is the same code that
served until 18:24Z. The before/after diff below is therefore anchored
`8098d30 → 412376f` with no intervening image.

### §1.2 UV-P-1 — the deploy-latency measurement

Every row is a first-hand observation with its source named. Merge is t=0.

| t | UTC | Event | Source |
|---|-----|-------|--------|
| 00:00:00 | **17:32:14Z** | PR #384 merged to `main` as `412376f` | `gh pr view 384 --json mergedAt,mergeCommit` |
| 00:27:51 | **18:00:05Z** | ECR image `autom8y/asana:412376f` pushed (digest `sha256:6e280c21…`) | `aws ecr describe-images` |
| 00:31:49 | **18:04:02.608Z** | task-definition `:791` registered with that image | `aws ecs describe-task-definition` |
| 00:31:55 | **18:04:09.176Z** | ECS service deployment `bkrMo5q4e4zwOJuIPKTG0` created + started | `aws ecs describe-service-deployments` |
| 00:32:34 | **18:04:48Z** | container entrypoint `"Starting in ECS mode"` on task `084d0c03…` | CloudWatch `/ecs/autom8y-asana-service` |
| 00:32:50 | **18:05:03.864Z** | ECS task `startedAt` | `aws ecs describe-tasks` |
| 00:43:22 | **18:15:36.230Z** | last `preload_heartbeat` (`projects_completed 6, remaining 1, elapsed_ms 633980`) | CloudWatch |
| 00:43:46 | **18:16:00.415Z** | `/ready` flips **503 → 200** | CloudWatch (`GET /ready HTTP/1.1" 200 OK`) |
| 00:44:19 | **18:16:33Z** | ALB target `10.0.139.125` (`:791`) first observed `healthy` | `aws elbv2 describe-target-health`, own poll |
| 00:45:49 | **18:18:03Z** | lifecycleStage → `TEST_TRAFFIC_SHIFT` | own poll |
| 00:46:11 | **18:18:25Z** | **first production traffic to `412376f`** — prod rule weights `blue(:791)=100, green(:790)=900` (10% canary); stage `PRODUCTION_TRAFFIC_SHIFT` | own poll |
| **00:51:47** | **≤18:24:01Z** | **serve path 100% on `412376f`** — `blue(:791)=100, green(:790)=0` (flip occurred in the 18-second window 18:23:43Z–18:24:01Z; 18:24:01Z is the first observation) | own poll |
| 00:52:05 | **18:24:19.7Z** | axis first observed on the consumer's own request shape | §1.4 below |
| 00:53:19 | **18:25:33.636Z** | ECS deployment `rolloutState: COMPLETED`, old task drained | `aws ecs describe-services` |

**UV-P-1 headline:** merge → serve-path-live (100% of production traffic on
`412376f`) = **51 min 47 s** (bounded 51:29–51:47). Decomposed:
build+publish **27:51**, publish→taskdef **3:58**, task start→`/ready` green
**11:12** (the frame preload dominates), health→canary **1:52**, canary bake
**5:36**.

[UV-P: the 18:23:43Z–18:24:01Z flip instant is bounded by my 15-second poll
cadence, not read from an ECS/ELB event record | METHOD: deferred-to-CloudTrail
`ModifyRule` lookup | REASON: CloudTrail was not queried in this window; the
18-second bound is sufficient for the PT-02 measurement and the conservative
(later) end is the one reported]

### §1.3 Method for the two POSTs — reused verbatim from the consumer

Not reconstructed from the PR body. Read out of the consumer's own source and
the consumer's own deployed configuration:

- **Request shape** — `services/account-status-recon/src/account_status_recon/fetcher.py:217-251`:
  `POST /v1/query/offer/rows`, `classification="active"` then `"activating"`,
  `limit=1000`, `offset=0`, and the nine-field select list verbatim
  (`gid, name, section, office, office_phone, vertical, offer_id,
  weekly_ad_spend, platforms`).
- **Body construction** — `autom8y_core/clients/asana_query.py:142-151`
  (`limit`/`offset` always; `classification`/`select` only when non-None).
- **Identity** — the consumer's own service account, read from the deployed
  Lambda: `aws lambda get-function-configuration --function-name
  autom8y-account-status-recon` → `SERVICE_CLIENT_ID=sa_3397d6e1…`,
  `SERVICE_CLIENT_SECRET_ARN=arn:aws:secretsmanager:us-east-1:696318035277:secret:autom8y/auth/service-api-keys/account-status-recon-service-L7neWb`.
  Secret read read-only via `aws secretsmanager get-secret-value` (value **not**
  reproduced here).
- **Token mint** — `sa_*` credential class routes to
  `POST {auth_url}/tokens/exchange-business` with an `Authorization: Basic
  base64(client_id:client_secret)` header and an **empty** JSON body
  (multi-tenant), per `autom8y_core/token_manager.py:544-546`
  (`_resolve_token_endpoint`) and `:579-616` (`_build_teb_kwargs`) — empty body
  because ASR's `Config` sets no `business_id`. Mint returned a 1327-char RS256
  JWT.
- **Read discipline** — raw JSON parsed by hand (`json.loads`), **not** through
  `QueryRowsResponse`. A typed model drops undeclared keys and could not witness
  absence; this is the same discipline the PR body's before-trace used, so the
  two rosters are comparable.

Probe source: `after_trace.py` in the session scratchpad (not committed).

### §1.4 The AFTER trace — verbatim

Both POSTs, one token, back to back, at 18:24:19Z — **18 seconds after** the
100%-shift observation.

```json
{
  "active": {
    "captured_at_utc": "2026-08-19T18:24:19.149207+00:00",
    "http_status": 200,
    "response_headers": { "date": "Wed, 19 Aug 2026 18:24:19 GMT", "server": "uvicorn", "x-request-id": "52920065b0434b85" },
    "row_count": 62,
    "meta_key_count": 24,
    "meta_keys_sorted": [
      "axes_present", "column_manifest", "contract_complete", "data_age_seconds",
      "entity_type", "freshness", "honest_contract_complete", "honest_empty",
      "join_entity", "join_key", "join_matched", "join_unmatched", "limit",
      "offset", "project_gid", "query_ms", "returned_count", "stale_served",
      "staleness_ratio", "total_count", "unservable_required_columns",
      "verification_age_seconds", "verification_backfill_used", "verified_at"
    ],
    "meta_verbatim": {
      "total_count": 62, "returned_count": 62, "limit": 1000, "offset": 0,
      "entity_type": "offer", "project_gid": "1143843662099250", "query_ms": 2.95,
      "join_entity": null, "join_key": null, "join_matched": null, "join_unmatched": null,
      "freshness": "stale", "data_age_seconds": 642.6, "staleness_ratio": 3.57,
      "stale_served": true, "honest_contract_complete": true, "honest_empty": false,
      "contract_complete": true, "unservable_required_columns": [], "column_manifest": null,
      "verified_at": "2026-08-19T18:13:36.243295+00:00",
      "verification_age_seconds": 643.477208,
      "verification_backfill_used": false,
      "axes_present": ["verified_at", "verification_age_seconds", "verification_backfill_used"]
    },
    "axis_fields_present": { "verified_at": true, "verification_age_seconds": true, "verification_backfill_used": true },
    "axes_present_key_present": true
  },
  "activating": {
    "captured_at_utc": "2026-08-19T18:24:19.830009+00:00",
    "http_status": 200,
    "response_headers": { "date": "Wed, 19 Aug 2026 18:24:20 GMT", "server": "uvicorn", "x-request-id": "966c02b62db54a5d" },
    "row_count": 50,
    "meta_key_count": 24,
    "meta_keys_sorted": [ "…identical 24-key roster to `active`…" ],
    "meta_verbatim": {
      "total_count": 50, "returned_count": 50, "limit": 1000, "offset": 0,
      "entity_type": "offer", "project_gid": "1143843662099250", "query_ms": 3.39,
      "join_entity": null, "join_key": null, "join_matched": null, "join_unmatched": null,
      "freshness": "stale", "data_age_seconds": 643.1, "staleness_ratio": 3.57,
      "stale_served": true, "honest_contract_complete": true, "honest_empty": false,
      "contract_complete": true, "unservable_required_columns": [], "column_manifest": null,
      "verified_at": "2026-08-19T18:13:36.243295+00:00",
      "verification_age_seconds": 644.029342,
      "verification_backfill_used": false,
      "axes_present": ["verified_at", "verification_age_seconds", "verification_backfill_used"]
    },
    "axis_fields_present": { "verified_at": true, "verification_age_seconds": true, "verification_backfill_used": true },
    "axes_present_key_present": true
  }
}
```

### §1.5 BEFORE / AFTER roster diff, side by side

BEFORE is the PR-body X-8 capture at 16:19:19Z on image `e3aab8d` (task-def
`:787`), re-verified first-hand by QA at 17:18:32Z on image `8098d30`
(task-def `:788`) with **the same 20-key roster**. AFTER is mine, 18:24:19Z on
image `412376f` (task-def `:791`).

| # | meta key (sorted) | BEFORE (`e3aab8d` / `8098d30`, 20 keys) | AFTER (`412376f`, 24 keys) |
|---|---|---|---|
| 1 | `axes_present` | — **absent** | **PRESENT** |
| 2 | `column_manifest` | present | present |
| 3 | `contract_complete` | present | present |
| 4 | `data_age_seconds` | present | present |
| 5 | `entity_type` | present | present |
| 6 | `freshness` | present | present |
| 7 | `honest_contract_complete` | present | present |
| 8 | `honest_empty` | present | present |
| 9 | `join_entity` | present | present |
| 10 | `join_key` | present | present |
| 11 | `join_matched` | present | present |
| 12 | `join_unmatched` | present | present |
| 13 | `limit` | present | present |
| 14 | `offset` | present | present |
| 15 | `project_gid` | present | present |
| 16 | `query_ms` | present | present |
| 17 | `returned_count` | present | present |
| 18 | `stale_served` | present | present |
| 19 | `staleness_ratio` | present | present |
| 20 | `total_count` | present | present |
| 21 | `unservable_required_columns` | present | present |
| 22 | `verification_age_seconds` | — **absent** | **PRESENT** |
| 23 | `verification_backfill_used` | — **absent** | **PRESENT** |
| 24 | `verified_at` | — **absent** | **PRESENT** |

**Delta: +4, −0.** Every one of the 20 baseline keys survives, with the same
types and the same null-carrying behaviour (`join_*` still `null`,
`column_manifest` still `null`, `unservable_required_columns` still `[]`). The
addition is exactly the three axis fields plus the `axes_present` capability
signal. This is the AXIS-ABSENT → AXIS-PRESENT transition, measured on both
request shapes, on the consumer's own request shape and identity.

### §1.6 Are the three values sane?

| Check | Observation | Verdict |
|---|---|---|
| `verified_at` is offset-bearing UTC | `"2026-08-19T18:13:36.243295+00:00"` — explicit `+00:00`, not a naive string, not a `Z`-less instant, not space-separated | **PASS** (pins TDD §5.4 / the QA DEF-1 naive-stamp arm never fired) |
| `verification_backfill_used` is literal `false` | `false` on **both** legs — a boolean, not `null`, not a string, and it survived serialization (no `exclude_none`/`exclude_unset` betrayal) | **PASS** — a `null` here would be AXIS-INCOHERENT and would refuse every response |
| `verification_age_seconds` is arithmetically consistent | `18:24:19.149` (my client stamp, taken *before* the POST) − `18:13:36.243` = **642.906 s**. Producer emitted **643.477 s** — 0.57 s later, exactly the client→server flight time. `activating`: 644.029 s, 0.55 s after `active`, matching the 0.68 s gap between my two `captured_at` stamps. | **PASS** |
| The axis is not aliasing the content axis | `data_age_seconds 642.6` vs `verification_age_seconds 643.477208` on the same response — different values (Δ≈0.88 s) **and** different precision. If the verification axis were riding `ResponseFreshness` these would be the same number. | **PASS** — live corroboration of the non-aliasing property the module's docstring claims |
| `axes_present` is the exact three-field roster | `["verified_at", "verification_age_seconds", "verification_backfill_used"]` — no near-miss token (`verification`, `verif_age`, `last_verified_at`), no partial declaration | **PASS** |
| The watermark actually moves (not a frozen constant) | second capture at **18:26:29Z** returned `verified_at = "2026-08-19T18:24:44.822575+00:00"` — the stamp advanced 11 min 8 s between my two captures | **PASS** |
| Age is inside the consumer's bar | ASR `OFFER_STALENESS_THRESHOLD_SECONDS=3600` (read from the deployed Lambda env). Observed 643 s ≪ 3600 s | GATE, not ABORT |
| Stamp provenance is plausible | `verified_at 18:13:36` falls **inside** the `:791` task's own preload window (container start 18:04:48Z, `/ready` green 18:16:00Z) — i.e. the stamp was written by this task's own warm, not carried forward | **PASS** |

[UV-P: direct cross-read of the serve manifest's `last_verified_at` stamps to
confirm `verified_at == min(stamps)` over the in-scope sections | METHOD:
deferred-to-S3-manifest-read | REASON: the SEAM-1 manifest key
`{prefix}{project_gid}/{entity_type}/manifest.json` did not resolve under the
`ASANA_CACHE_S3_PREFIX` value (`asana-cache/project-frames/`) — that prefix is
laid out by project *name* and holds legacy parquet frames; `SectionPersistence`
carries its own `_prefix`, which I did not resolve within this dispatch. The
substitute evidence is the two-capture watermark advance plus the arithmetic
consistency above, both of which are first-hand]

### §1.7 The serve-window log line (§1c)

**Correlation — proof the requests were served by `412376f`, not by the draining
`8098d30` task.** `query_rows_complete` (INFO,
`api/routes/query.py:548`) in the **`:791` task's own stream**
(`ecs/autom8y-asana-service/084d0c03c2af44d9ac75355587833c89`), window
18:24:00Z–18:25:00Z, verbatim:

```json
{"extra": {"entity_type": "offer", "total_count": 62, "returned_count": 62, "query_ms": 2.95,
  "caller_service": "8156aa10-9731-464c-bfb2-c85a884d3d11", "predicate_depth": 0,
  "section": null, "classification": "active"},
 "event": "query_rows_complete", "level": "info",
 "trace_id": "0296612d16dc45ecf94d06360045cd18", "span_id": "86593ddede055e7f",
 "timestamp": "2026-08-19T18:24:19.721037Z"}

{"extra": {"entity_type": "offer", "total_count": 50, "returned_count": 50, "query_ms": 3.39,
  "caller_service": "8156aa10-9731-464c-bfb2-c85a884d3d11", "predicate_depth": 0,
  "section": null, "classification": "activating"},
 "event": "query_rows_complete", "level": "info",
 "trace_id": "eb06b732a841983d7f25ee5156bc9826", "span_id": "abf43aa17274436e",
 "timestamp": "2026-08-19T18:24:20.273182Z"}
```

`query_ms` **2.95** and **3.39** and counts **62**/**50** and classifications
`active`/`activating` match my captured `meta_verbatim` byte for byte. These two
requests were served by the task running image `412376f`. (The two identifier
namespaces are disjoint by design: the ALB/app returns `x-request-id`
`52920065b0434b85` / `966c02b62db54a5d` on the wire, while the log line carries
the OTel `trace_id`. The `query_ms`+counts+classification tuple is the join.)

**Absence of the refusal events**, same stream, window 18:04:00Z–18:26:00Z
(the whole life of the `:791` task to date):

```
serve_verification_axis_derivation_failed : 0 events
serve_verification_axis_null              : 0 events
serve_verification_axis_derived           : 0 events
```

…and group-wide over `/ecs/autom8y-asana-service` in the same window:

```
serve_verification_axis_derivation_failed : 0 events
serve_verification_axis_null              : 0 events
```

**Anti-blind positive control** (the zero is a real zero, not a broken query):
the *same* log group, *same* window, *same* `filter-pattern` grammar for a
known-present event returned

```
query_rows_complete : 90 events
```

so the scan mechanism is live. The **`derived` event's zero is expected, not
anomalous**: `engine.py:711` emits it at `logger.debug`, and the deployed
container carries `LOG_LEVEL=INFO` (read from task-def `:791`'s environment). The
derivation is therefore observable positively only through the wire values in
§1.4 and negatively through the absence of the two `warning`-level refusal
events — which is exactly what the wire shows.

### §1.8 LEG 1 verdict — **PASS**

Every clause of the leg is discharged: the ECS service reached `412376f`; the
two consumer POSTs returned 200 with a 24-key roster; the three axis fields plus
`axes_present` are present with sane, arithmetically consistent, non-aliased,
moving values; and the serve window carries zero derivation-failure and zero
axis-null events against a live positive control. PR-body exit criterion **7
(PRODUCTION-OBSERVABLE)** and **8 (UV-P-1 deploy latency)** — both marked
`PENDING MERGE` in the PR body and correctly unclaimed by QA (NOTE-2) — are now
**MET**.

---

## §2 LEG 2 — SDK REGISTRY RESOLUTION (RISK-1 false-green closure) — **PASS**

### §2.1 Why this leg exists and what it adds over the build-time receipt

The standing false-green: dev and CI resolve `autom8y-core = { workspace = true }`
**editable**, so they carry a new symbol regardless of any floor pin, while a
deployed consumer image resolves the published floor from **CodeArtifact**. The
wheel-level receipt closed at build. This one could only close after publish —
it proves the artifact **as the registry actually serves it**.

### §2.2 Publication anchor

```json
{ "version": "4.16.0", "status": "Published",
  "publishedTime": "2026-08-19T10:26:02.174000-07:00",   // 17:26:02Z
  "revision": "4c1ThwwHEN7GmcdT/56xdMF5nZGspUPyVkW+F2ScbEA=" }
```

Registry endpoint (`aws codeartifact get-repository-endpoint --domain autom8y
--repository autom8y-python --format pypi`):
`https://autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com/pypi/autom8y-python/`

### §2.3 Clean-env install — CodeArtifact as the ONLY index

Venv created **outside any repo** — `git rev-parse --show-toplevel` at the venv
parent returns `fatal: not a git repository (or any of the parent directories)`.

`PIP_CONFIG_FILE=/dev/null` is load-bearing: the ambient environment carries a
pip config that *already* points at CodeArtifact (a bare `pip install --upgrade
pip` emitted two `401 Error, Credentials not correct` warnings against
`.../pypi/autom8y-python/simple/pip/`). Neutralising it makes the index an
explicit argument rather than an inherited one. The 401-on-redirect trap was
cured with a `NETRC` file rather than inline basic-auth in the URL.

```
$ printf 'machine %s\nlogin aws\npassword %s\n' "$HOST" "$TOKEN" > netrc   # chmod 600
$ PIP_CONFIG_FILE=/dev/null NETRC=./netrc venv/bin/pip install autom8y-core==4.16.0 \
    --index-url https://autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com/pypi/autom8y-python/simple/ \
    --no-cache-dir
```

No `--extra-index-url`, **no PyPI**: every wheel in the resolution came off
CodeArtifact. Asset-URL receipt for the package under test (isolated re-resolve
with `--force-reinstall --no-deps`):

```
Looking in indexes: https://autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com/pypi/autom8y-python/simple/
Collecting autom8y-core==4.16.0
  Downloading https://autom8y-696318035277.d.codeartifact.us-east-1.amazonaws.com/pypi/autom8y-python/simple/autom8y-core/4.16.0/autom8y_core-4.16.0-py3-none-any.whl (129 kB)
Successfully installed autom8y-core-4.16.0
```

Full first resolution:
`autom8y-core-4.16.0 autom8y-api-schemas-1.12.0 pydantic-2.13.4 pydantic-core-2.46.4
httpx-0.28.1 httpcore-1.0.9 h11-0.16.0 anyio-4.14.2 certifi-2026.7.22 idna-3.19
pyyaml-6.0.3 typing-extensions-4.16.0 typing-inspection-0.4.4 annotated-types-0.8.0`.

### §2.4 The `python -P` / `cwd=/` probe — every check ASSERTS

Run as `env -i PATH=/usr/bin:/bin HOME=/tmp <venv>/bin/python -P probe.py`, with
`os.chdir("/")` executed before any `autom8y_core` import. `-P` keeps the script
directory and cwd off `sys.path`; `cwd=/` kills the "you were standing in the
repo" objection. Receipt tail, verbatim:

```json
{
  "cwd": "/",
  "sys_path": [
    "/Users/tomtenuta/.local/share/mise/installs/python/3.12.12/lib/python312.zip",
    "/Users/tomtenuta/.local/share/mise/installs/python/3.12.12/lib/python3.12",
    "/Users/tomtenuta/.local/share/mise/installs/python/3.12.12/lib/python3.12/lib-dynload",
    "/private/tmp/.../scratchpad/leg2/venv/lib/python3.12/site-packages"
  ],
  "pythonpath_env": "<unset>",
  "virtualenv_env": "<unset>",
  "autom8y_core_version": "4.16.0",
  "autom8y_core__file__":        ".../leg2/venv/lib/python3.12/site-packages/autom8y_core/__init__.py",
  "asana_verification__file__":  ".../leg2/venv/lib/python3.12/site-packages/autom8y_core/helpers/asana_verification.py",
  "QueryMeta__module__file":     ".../leg2/venv/lib/python3.12/site-packages/autom8y_core/models/asana_service.py",
  "QueryMeta_field_count": 23,
  "axis_fields_on_QueryMeta": {
    "verified_at": "str | None",
    "verification_age_seconds": "float | None",
    "verification_backfill_used": "bool | None"
  },
  "VERIFICATION_AXIS_FIELDS": ["verified_at", "verification_age_seconds", "verification_backfill_used"],
  "asana_verification_public": [
    "MISDECLARED_AXIS_TOKENS", "ResponseVerification", "VERIFICATION_AXIS_FIELDS",
    "VerificationAxisVerdict", "VerificationDisposition", "derive_response_verification"
  ],
  "roundtrip_from_live_meta": {
    "verified_at": "2026-08-19T18:13:36.243295+00:00",
    "verification_age_seconds": 643.477208,
    "verification_backfill_used": false,
    "axes_present": ["verified_at", "verification_age_seconds", "verification_backfill_used"],
    "declares_verification_age_seconds": true
  }
}

LEG-2 PROBE: ALL ASSERTIONS PASSED
```

The assertions that could have failed (a probe that only prints is not a
receipt): no `sys.path` entry contains a workspace root; `""` not on `sys.path`;
`PYTHONPATH` unset; `importlib.metadata.version == "4.16.0"`; every
`__file__` contains `site-packages` and no workspace root; each of the three
names in `QueryMeta.model_fields`; `axes_present` in `model_fields`;
`VERIFICATION_AXIS_FIELDS` spelled exactly; and on the live-meta round-trip,
`verified_at is not None`, `verification_backfill_used is False`,
`declares_axis("verification_age_seconds") is True`.

`sys_path` is four entries — the three stdlib entries plus **only** the scratch
venv's `site-packages`. No workspace path is reachable.

### §2.5 Two-sided teeth (the probe bites)

The receipt is discriminating, not a one-sided green. The **same** probe against
the **previous published version**, installed from the **same** registry into a
sibling clean venv:

```
=== 4.15.0 (prev) ===
version: 4.15.0
asana_verification IMPORT FAILS: ImportError cannot import name 'asana_verification'
  from 'autom8y_core.helpers' (.../venv_prev/.../autom8y_core/helpers/__init__.py)
QueryMeta field count: 20
  verified_at: ABSENT
  verification_age_seconds: ABSENT
  verification_backfill_used: ABSENT
  axes_present: PRESENT

=== 4.16.0 (under test) ===
version: 4.16.0
asana_verification IMPORTS: .../venv/.../autom8y_core/helpers/asana_verification.py
QueryMeta field count: 23
  verified_at: PRESENT
  verification_age_seconds: PRESENT
  verification_backfill_used: PRESENT
  axes_present: PRESENT
```

Note the symmetry with LEG 1: **20 → 23** model fields mirrors the wire's
**20 → 24** meta keys (the wire's extra key is `axes_present`, which the model
already carried at 4.15.0 — the SDK leg landed the capability signal ahead of
the producer, which is exactly what makes a version-skewed fleet safe). Running
the *full* probe against 4.15.0 fails at the first assert:

```
AssertionError: resolved version is 4.15.0, expected 4.16.0
```

### §2.6 End-to-end closure — registry SDK against the live production response

The strongest available form of this leg: feed the **live production response**
(full envelope, captured 18:26:29Z, `x-request-id af9c7d854c874660`, 62 rows)
into the **registry-resolved** SDK's own verdict function.

```
rows parsed: 62
  disposition = <VerificationDisposition.GATE: 'GATE'>
  axis_verdict = <VerificationAxisVerdict.OK: 'OK'>
  verified_at = '2026-08-19T18:24:44.822575+00:00'
  verification_age_seconds = 121.492955
  backfill_used = False
  future_dated = False
  disclosure = "verification age derived from verified_at='2026-08-19T18:24:44.822575+00:00'
                (121.493s at the reference instant); producer emitted
                verification_age_seconds=104.167368, carried as disclosure only"

ASSERT OK: registry-resolved SDK 4.16.0 GATEs on the live production response
```

The whole chain is closed on live bytes: **producer emits → registry-served SDK
parses, declares, re-derives its own age from `verified_at`, treats the
producer's emitted age as disclosure only, and returns `GATE`/`OK`.** No
workspace, no editable install, no fixture.

### §2.7 LEG 2 verdict — **PASS**

`autom8y_core.helpers.asana_verification` imports from a CodeArtifact-resolved
4.16.0 wheel; `QueryMeta` carries all three axis fields; module origin is
`site-packages` with no workspace path anywhere on `sys.path`; the probe bites
on 4.15.0; and the registry SDK gates correctly on live production bytes.
**RISK-1 (the CodeArtifact-resolved SDK divergence class the QA named as its
residual surprise) is closed at registry level.**

---

## §3 Verdicts

| Leg | Verdict | Basis |
|---|---|---|
| **LEG 1 — producer live (after-trace)** | **PASS** | 24-key roster on both consumer request shapes at 18:24:19Z on image `412376f`, ECS anchor task-def `:791`, three axis fields + `axes_present` with sane/consistent/moving values, zero refusal events against a live positive control, log-line correlation proving the new task served the requests |
| **LEG 2 — SDK registry resolution** | **PASS** | CodeArtifact-only clean-env install of `autom8y-core==4.16.0` outside any repo, `python -P` + `cwd=/` probe with falsifiable asserts, two-sided teeth vs 4.15.0, and the registry SDK returning `GATE`/`OK` on the live production response |

**Neither leg is BLOCKED-ON anything.** Two UV-P labels are carried forward and
are *not* blockers:

1. the 18-second bound on the traffic-flip instant (poll cadence, conservative
   end reported);
2. the direct S3 manifest `last_verified_at` cross-read (substituted by the
   arithmetic consistency and the two-capture watermark advance).

---

## §4 Notes worth carrying

- **`healthStatus: HEALTHY` on an ECS task is not a serve-path signal.** With a
  CANARY deployment the serve path is the ALB production listener rule's forward
  weights. At 18:16 the task was HEALTHY and serving **zero** production
  traffic. Anyone measuring "deploy latency" off ECS task health would have
  under-reported this deploy by **8 minutes**.
- **The target-group names invert the convention here.** `a8-asana-green` held
  the OLD revision; `targetgroup/autom8y-asana-service` held the NEW one. Verify
  by task IP, never by name.
- **The dominant term in this service's deploy latency is the frame preload**
  (11 min 12 s from task start to `/ready` green, against a
  `healthCheckGracePeriodSeconds` of 2400). Build+publish was 27 min 51 s. The
  ECS mechanics (canary + bake) contributed only 7 min 28 s.
- **`serve_verification_axis_derived` is DEBUG and the fleet runs INFO**, so the
  happy path is log-invisible by construction. The observability contract on
  this axis rests entirely on the two `warning`-level refusal events. Any future
  metric-filter binding (the sre lane's) should be built against
  `serve_verification_axis_null` and
  `serve_verification_axis_derivation_failed`, and should carry its own positive
  control — a filter that finds nothing looks identical to a system that refuses
  nothing.
- **`data_age_seconds` and `verification_age_seconds` are visibly different
  numbers on the same live response** (642.6 vs 643.477208). That is the
  non-aliasing property observable in production, not just in tests.

*Self-grade: **MODERATE**. Single attester, same rite as the builder and QA.
Every load-bearing claim above carries a first-hand receipt produced in this
session; nothing is inherited except the BEFORE side of the roster diff, which
is cited as such and was independently re-verified by QA at 17:18Z on the image
that served until 18:24Z. No STRONG is claimed; a rite-disjoint attester
(SPR-VC) remains owed.*
