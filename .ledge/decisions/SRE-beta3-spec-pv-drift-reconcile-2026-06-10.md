---
type: spec
status: proposed
---

# SRE β-3 Spec — PV-DRIFT Reconcile + ECS Write-Surface Enumeration

> Station R3 (READ-ONLY). PV-DRIFT reconcile of the LIVE ECS-task-role full-bucket
> S3 policy vs the checked-in (SCOPED-warmer) Terraform, plus full enumeration of
> the ECS receiver S3 write surface, producing the operator-gated β-3 spec to
> narrow `autom8y-asana-service-task-s3` from full-bucket to the declared
> namespace set. **β-3 is NOT executed here.** No mutations performed.

- **Authored**: 2026-06-10
- **Author**: sre / incident-commander (station R3)
- **Evidence grade**: `[STRUCTURAL | MODERATE]` — self-ref ceiling per
  `self-ref-evidence-grade-rule`; every load-bearing claim carries an SVR receipt
  or is marked UV-P. AWS live-state probes are `bash-probe` receipts re-runnable
  by any operator with the same credentials.
- **AWS context**: account `696318035277`, region `us-east-1`, identity
  `arn:aws:iam::696318035277:user/tom.tenuta` (SVR: `aws sts get-caller-identity`
  → `Account: 696318035277`; exit 0).

---

## 0. Grandeur Anchor

β-3 (narrowing the ECS task role from full-bucket to the declared namespace set)
was BLIND until we answered: (a) why the LIVE policy is full-bucket while the
checked-in TF is scoped, and (b) every prefix the receiver actually WRITES. This
spec resolves both with receipts and hands the operator a canary-gated narrowing
plan with an exact-JSON rollback.

---

## 1. DRIFT VERDICT — `TF-NEVER-OWNED-IT (out-of-band creation)`

### 1.1 The live policy (full bucket)

```
aws iam get-role-policy --role-name autom8y-asana-service-ecs-task \
  --policy-name autom8y-asana-service-task-s3 --region us-east-1
```
→ `Sid: S3CacheAccess`, Actions `[GetObject, PutObject, DeleteObject, ListBucket,
HeadObject]`, Resource `["arn:aws:s3:::autom8-s3", "arn:aws:s3:::autom8-s3/*"]`
(FULL BUCKET). exit 0. **[SVR bash-probe]**

Role metadata: `CreateDate 2025-12-22T19:45:41Z`, `RoleLastUsed 2026-06-10T17:18:43Z`
region us-east-1 (the role is ACTIVE — used today). **[SVR bash-probe]**

All inline policies on the role: `["autom8y-asana-service-task-s3",
"autom8y-asana-service-task-ssm", "cache-warmer-invoke"]`. Attached managed:
`autom8y-asana-production-amp-write`, `autom8y-asana-production-xray-write`.
**[SVR bash-probe]**

### 1.2 What the dispatch-cited TF lines ACTUALLY scope (premise CORRECTED)

The dispatch premise — "autom8y main.tf ~:955-959/:1046-1050/:1137-1140 show
SCOPED resources [for the ECS task role]" — is **FALSE**. Reading those exact
lines (`git show origin/main:terraform/services/asana/main.tf | sed -n '940,1150p'`):

- Lines 940-1150 are **CloudWatch log-metric-filters and alarms** (SRE-N6 D2/D3/D4
  observability): `aws_cloudwatch_log_metric_filter.population_receipt_below_floor`
  (~998), `aws_cloudwatch_metric_alarm.active_offer_rows_collapse` (~1080),
  `aws_cloudwatch_log_metric_filter.resolver_cascade_loop` (~1134). **NONE is an
  IAM resource.** **[SVR file-read; marker: `resource "aws_cloudwatch_log_metric_filter" "population_receipt_below_floor"`]**

The genuinely-scoped S3 `aws_iam_role_policy` resources in `asana/main.tf` are the
**WARMER-LANE** policies (`cache_warmer_s3` :1180, `cache_warmer_bulk_s3` :1283,
`cache_warmer_section_s3` :1385, `unit_reconciliation_s3` :1549), each scoped to
`asana-cache/project-frames/*`, `dataframes/*`, `cache-warmer/checkpoints/*`,
`asana-cache/tasks/*`, `reconciliation/reports/*`. These attach to the **warmer
Lambda roles, NOT the ECS task role.** **[SVR file-read; marker: `"arn:aws:s3:::autom8-s3/asana-cache/project-frames/*",`]**

### 1.3 Resolving which TF resource (if any) owns `autom8y-asana-service-task-s3`

**Decisive question answered: NO TF resource owns it.**

1. **Not in autom8y-asana repo TF.** `git grep -n 'autom8y-asana-service-task-s3\|task_s3\|service-task-s3'` over `origin/main:terraform/services/asana/` returns ZERO matches for the task-role S3 policy. **[SVR git-ls-files / grep; result: does-not-exist]**

2. **Not in the autom8y repo TF.** `git -C autom8y grep -ln 'autom8y-asana-service-task-s3\|service-task-s3' origin/main -- terraform/` returns EMPTY. **[SVR bash-probe; empty stdout]**

3. **Not in the external `service-stateless` stack.** `module "service"`
   (`asana/main.tf:88`) sources
   `git::https://github.com/autom8y/a8.git//terraform/modules/stacks/service-stateless?ref=a72c43f4`
   and passes **NO S3 IAM argument** (no `s3_bucket`, `additional_iam_policies`
   carrying S3, `s3_prefixes`, or `task_role_policy`). **[SVR file-read; marker: `source = "git::https://github.com/autom8y/a8.git//terraform/modules/stacks/service-stateless?ref=a72c43f4"`]**
   Cloned the a8 repo at the pinned ref `a72c43f4` and inspected the stack +
   its `iam-service-role` primitive (`../../primitives/iam-service-role`).

4. **The IAM primitive creates `task_ssm` and `task_efs` — but NO `task_s3`.**
   `terraform/modules/primitives/iam-service-role/main.tf:145`:
   `resource "aws_iam_role_policy" "task_ssm" { name = "${local.name_prefix}-task-ssm" ... Sid = "ECSExec" }`
   This is the EXACT generator of the live `autom8y-asana-service-task-ssm` policy
   (ECSExec, ssmmessages:*, verified live). `task_efs` at :176. **There is no
   `task_s3` resource anywhere in the primitive, the stack, or either repo.**
   **[SVR file-read; marker: `resource "aws_iam_role_policy" "task_ssm" {`]**

### 1.4 The naming-convention tell

The module's auto-naming convention is `${local.name_prefix}-task-{suffix}` →
`autom8y-asana-service-task-{suffix}`. The live `autom8y-asana-service-task-s3`
**follows this exact convention** (the `-task-s3` suffix), which is why it *looks*
module-generated — but no `task_s3` resource exists to generate it. By contrast,
the repo-owned `cache-warmer-invoke` inline policy (verified live as
`InvokeCacheWarmerLambda` / `lambda:InvokeFunction`) maps EXACTLY to
`asana/main.tf:268 aws_iam_role_policy.cache_warmer_invoke` (which uses
`role = module.service.task_role_name`) and does NOT carry the `-task-` prefix —
proving the repo author names repo-owned policies differently.

**Conclusion**: `autom8y-asana-service-task-s3` was created **out-of-band**
(console or CLI `put-role-policy`), deliberately mimicking the module's
`-task-s3` naming so it reads as module-generated. A `terraform apply` of the
asana service would NOT touch it (Terraform has no resource for it; it is not in
any state file this spec could reach), which is precisely why the full-bucket
grant has survived as silent drift.

### 1.5 Forensic limits (stated loudly)

- **CloudTrail returned ZERO events** for `ResourceName=autom8y-asana-service-ecs-task`
  (`aws cloudtrail lookup-events`, exit 0, `"Events": []`). The role was created
  2025-12-22 (~6 months ago); the `PutRolePolicy` mutation that created the
  full-bucket policy is **older than CloudTrail's 90-day lookup-events window**,
  so the literal who/when of the out-of-band creation cannot be recovered from
  CloudTrail today. **The verdict in §1.3 rests on TF-source absence (three
  independent sources), not on a CloudTrail mutation record.** **[SVR bash-probe; empty Events]**
- **gh API was rate-limited** (5,000/hr exceeded) during the session, so the a8
  module was inspected via a direct `git clone` at the pinned ref rather than via
  the GitHub API. The clone + checkout succeeded (exit 0).

### 1.6 Registry corroboration

The StorageNamespaceContract registry already names this exact drift as the β-3
target. `src/autom8_asana/storage_namespace.py` TASK_CACHE.lifecycle_note: "The
ECS task role holds full-bucket autom8-s3/* today; narrowing is the Phase-beta
beta-3 operator-gated target." **[SVR file-read; marker: `narrowing is the Phase-beta beta-3 operator-gated target.`]**
The registry's `iam_grants` matrix carries ONLY the warmer-role ARN
(`autom8-asana-cache-warmer-lambda-role`) and the monolith user
(`user/autom8`) — **it does NOT yet declare an ECS-task-role principal**, and
no TF resource consumes `namespaces.gen.json` for the ECS principal
(`git -C autom8y grep namespaces.gen.json -- terraform/` → empty). So the β-3
scoped policy must be DERIVED from the write/read surface below, not lifted from
the registry grant matrix.

---

## 2. ECS RECEIVER WRITE-SURFACE ENUMERATION

### 2.1 Runtime discrimination (which code runs on ECS vs warmer)

- **ECS receiver = the FastAPI app** (`module.service`, ECS Fargate, the
  preload/request path).
- **Warmer = the `cache_warmer*` Lambdas** (cron-scheduled, separate roles).

The cache-provider factory selects the backend by environment
(`cache/integration/factory.py:155`): in **production** with `REDIS_HOST` set it
returns `RedisCacheProvider` (NOT S3). **[SVR file-read; marker: `Production environment with Redis configured, using RedisCacheProvider`]**
There is **NO production `S3CacheProvider(` construction site** in `src/` (grep
finds only docstring examples at `cache/backends/__init__.py:13` and `s3.py:85`,
the class def at `s3.py:63`, and a "would NOT use it" comment at
`durable_task_cache.py:17`). **[SVR bash-probe; grep shows only docstring/classdef hits]**

### 2.2 The write-surface table

| Prefix (S3 key) | Writer code path (file:line) | Runtime | Verb(s) | Receipt |
|---|---|---|---|---|
| `dataframes/{project_gid}[/{entity_type}]/...` (dataframe.parquet, watermark.json, gid_lookup_index.json, manifest.json, sections/*.parquet) | `dataframes/storage.py:342` (S3DataFrameStorage default `prefix="dataframes/"`) via `dataframes/section_persistence.py:806 write_final_artifacts_async` | **ECS** (constructed at `api/preload/progressive.py:298` and `api/preload/legacy.py:130`; written via `put_async` at `api/preload/progressive.py:545,604`, `api/preload/legacy.py:294,349`, `api/routes/admin.py:330`) **AND** warmer | PutObject, DeleteObject (HeadObject/GetObject on read) | SVR file-read: `prefix: str = "dataframes/",` (storage.py); `await dataframe_cache.put_async(` (progressive.py:545) |
| `dataframes/...` (cold-start build, non-prod only) | `api/preload/progressive.py` builder fall-through (`builder.build_progressive_async`) then `put_async` | **ECS** (non-prod / local; prod delegates to warmer Lambda when no manifest — `progressive_preload_no_manifest_no_lambda` skip path) | PutObject | SVR file-read: `if app_settings.is_production:` ... `skipping` (progressive.py) |

**Live S3 corroboration**: `dataframes/1143843662099250/dataframe.parquet`
LastModified `2026-06-09T08:37:26Z` — recent, consistent with an active ECS+warmer
write path. **[SVR bash-probe: s3api list-objects-v2 dataframes/]**

### 2.3 Read-only S3 surfaces touched by the ECS receiver (GET/HEAD/LIST, NOT write)

The ECS receiver READS but does not WRITE these; they still require GET/HEAD/LIST
in the scoped policy because the receiver reads them on the request path:

| Prefix | Reader (file:line) | Runtime | Verb(s) |
|---|---|---|---|
| `dataframes/...` (read-then-fallback) | `api/preload/legacy.py:125`, `api/preload/progressive.py:291`, `dataframes/section_persistence.py:1045`, `dataframes/offline.py:49` | ECS | GetObject, HeadObject, ListBucket |
| `asana-cache/tasks/{gid}/task.json` (+ `.gz`) | `cache/durable_task_cache.py:DurableTaskCacheReader.read_batch` (raw boto3 `get_object`); consumed by `dataframes/builders/null_number_recovery.py:_cold_read_durable` | ECS (cold-tier null fill) | GetObject, HeadObject |

### 2.4 The γ-0 writer question — PINNED

**Q: Could the ECS receiver be the writer of `asana-cache/tasks/` (the durable
per-task cache)?**

**A: NO — the ECS receiver does NOT write `asana-cache/tasks/`. The writer is
EXTERNAL to this repo (the autom8 monolith IAM super-user `user/autom8`).**

Evidence chain:
1. The only ECS task-cache write path is `cache.set_versioned(...)` (e.g.
   `autom8_adapter.py:300`), but `cache` in production is `RedisCacheProvider`
   (factory.py:155), so that write lands in **Redis, not S3**. The registry's A1
   attribution of `autom8_adapter.py:300` to an S3 write is therefore **REFUTED**
   (the path is provider-agnostic and prod=Redis). **[SVR file-read: factory + adapter]**
2. **No S3 write key-construction for `asana-cache/tasks/{gid}/task.json` exists
   anywhere in `src/`** (`git grep` of `task.json|modified_at.json|stories.json|/tasks/`
   filtered to write paths returns only HTTP API routes/middleware, no S3 write).
   **[SVR bash-probe; grep shows only api/routes + middleware path strings]**
3. The warmer Lambdas write `dataframes/` and `cache-warmer/checkpoints/`
   (`lambda_handlers/checkpoint.py:313 put_object`) and DELETE under `{prefix}/tasks/`
   on invalidation (`lambda_handlers/cache_invalidate.py:136`), but **no warmer
   path WRITES `asana-cache/tasks/{gid}/task.json`** in this repo. **[SVR bash-probe; grep lambda_handlers]**
4. **Live LastModified** on `asana-cache/tasks/.../modified_at.json` =
   `2026-05-29T21:40:00Z`, `stories.json` = `2026-05-29T19:28:51Z` — recently
   written, but by an actor outside this repo. The monolith holds `user/autom8`
   full-bucket and is the registry-declared external owner of the sibling
   `asana-cache/task-cache/` and `task-data-cache-v3/` fossils. **[SVR bash-probe: s3api list-objects-v2 asana-cache/tasks/]**

**γ-0 disposition for β-3**: `asana-cache/tasks/` is a **READ-only** namespace for
the ECS receiver (DurableTaskCacheReader does GET only). The scoped ECS policy
grants GET/HEAD on `asana-cache/tasks/*` and **withholds PUT/DELETE** there. The
external write owner (monolith) operates under its own `user/autom8` full-bucket
identity and is **out of β-3's blast radius** (β-3 narrows ONLY the
`autom8y-asana-service-ecs-task` role, not the monolith user).

### 2.5 Exclusions (stated loudly)

- **EXCL-1**: The exact who/when of the out-of-band `PutRolePolicy` is
  unrecoverable (CloudTrail window aged out — §1.5). The verdict rests on
  TF-source absence, not a mutation record.
- **EXCL-2**: The monolith/external writer of `asana-cache/tasks/`,
  `task-cache/`, `task-data-cache-v3/`, `insights-frames/`, `name-gid-mappings/`,
  `asana-cache/dataframes/` is NOT located by code anchor (it is not in this repo).
  The registry marks these as EXTERNAL/FOSSIL. β-3 does NOT touch the monolith;
  it scopes only the ECS receiver role.
- **EXCL-3**: `reconciliation/reports/*` appears in the warmer-lane
  `unit_reconciliation_s3` TF policy but is a **warmer/unit-reconciliation
  surface, not an ECS receiver surface** — excluded from the ECS scoped policy
  unless a future receiver read-path is enumerated.
- **EXCL-4**: Redis (the real hot store) carries no S3 prefix and is out of the
  S3-namespace matrix by construction (registry note).
- **EXCL-5**: The a8 module was inspected at pinned ref `a72c43f4`; if the live
  ECS role were ever re-created by a NEWER service-stateless ref that DOES emit a
  `task_s3` resource, the verdict would change. As of the pinned ref the repo
  references, no such resource exists. Operator should re-confirm the live
  `module.service` ref before apply.

---

## 3. THE β-3 SPEC (NOT EXECUTED)

### 3.1 Target scoped policy (derived from §2 write+read surface)

Replace the full-bucket `Resource` with the minimal namespace set the ECS receiver
actually touches. PutObject/DeleteObject are granted ONLY where the receiver
writes (`dataframes/*`); GET/HEAD/LIST where it reads.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ListScopedPrefixes",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::autom8-s3",
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "dataframes/*",
            "asana-cache/tasks/*"
          ]
        }
      }
    },
    {
      "Sid": "S3DataframesReadWrite",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:HeadObject"
      ],
      "Resource": "arn:aws:s3:::autom8-s3/dataframes/*"
    },
    {
      "Sid": "S3DurableTaskCacheReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:HeadObject"
      ],
      "Resource": "arn:aws:s3:::autom8-s3/asana-cache/tasks/*"
    }
  ]
}
```

Notes on the target:
- `ListBucket` is bucket-level (cannot be prefix-ARN-scoped) so it is constrained
  via a `s3:prefix` Condition to the two prefixes the receiver lists.
- PUT/DELETE deliberately **excluded** from `asana-cache/tasks/*` per the γ-0
  finding (§2.4): the receiver only READS the durable task cache.
- If a live AccessDenied surfaces during the canary on a prefix not listed here,
  that is itself a **discovery** of an un-enumerated receiver path — do NOT widen
  blindly; enumerate the new path first, then add the minimal Sid.

### 3.2 GO criteria (ALL must hold before apply)

- [ ] **Write-surface enumerated** — §2.2 table complete with code anchors (DONE here).
- [ ] **γ-0 writer pinned** — `asana-cache/tasks/` writer confirmed EXTERNAL; ECS
      receiver is read-only on it (DONE here, §2.4).
- [ ] **Drift explained** — TF-NEVER-OWNED-IT verdict with 3-source absence proof
      (DONE here, §1.3).
- [ ] **Live `module.service` ref re-confirmed** at apply time to still be a ref
      that emits NO `task_s3` resource (so the apply does not collide with a
      future module-generated policy). Operator runs:
      `git -C autom8y show origin/main:terraform/services/asana/main.tf | sed -n '88,98p'`.
- [ ] **Canary plan armed** (§3.3) with instant rollback (§3.4) staged.
- [ ] **Saved full-bucket JSON present** (§3.4) and byte-verified against live.

### 3.3 Canary plan (apply scoped → watch → confirm)

1. **Stage** the saved rollback JSON (§3.4) and the target JSON (§3.1) on the
   operator host. Byte-verify the saved JSON equals live:
   `aws iam get-role-policy --role-name autom8y-asana-service-ecs-task --policy-name autom8y-asana-service-task-s3 --query PolicyDocument` matches the saved file.
2. **Apply scoped** (the ONE mutation β-3 authorizes, operator-gated):
   `aws iam put-role-policy --role-name autom8y-asana-service-ecs-task --policy-name autom8y-asana-service-task-s3 --policy-document file://beta3-target-task-s3-scoped.json`
3. **Watch for AccessDenied** in the ECS receiver logs for **N = 2 hours minimum**
   (long enough to cover at least one full preload/warm read+write cycle and a
   cold-start path). Watch:
   - CloudWatch Logs `/ecs/autom8y-asana-service` (or the service's log group) for
     `AccessDenied`, `s3_storage`, `progressive_tier_put_error`,
     `progressive_tier_put_exception`, `s3_expired_entry_delete_failed`.
   - The existing SRE-N6 alarms (population_receipt_below_floor, active_offer_rows_collapse)
     must NOT trip — a scoped-policy AccessDenied on the write path would manifest
     as a degraded/empty active set.
   - CloudWatch metric `4xxErrors`/`5xxErrors` on the ALB target group for the
     receiver, and any rise in `WarmerKeysCovered` shortfall.
4. **Confirm GREEN**: zero AccessDenied over N hours AND a real write occurred
   (a fresh `dataframes/.../dataframe.parquet` LastModified inside the window
   AND a `progressive_tier_put_success` log line). A canary with no writes in the
   window is INCONCLUSIVE — extend until a write is observed or seed one via the
   admin force-rebuild route (`api/routes/admin.py:330`).
5. If GREEN → β-3 closes; codify the scoped policy into IaC (β-3 follow-on:
   declare a `task_s3` resource derived from `namespaces.gen.json` for the ECS
   principal so the drift cannot silently recur — this is the durable fix; the
   put-role-policy is the interim narrowing).

### 3.4 Rollback (instant; exact saved JSON)

If ANY AccessDenied or receiver degradation appears, restore full-bucket
immediately:

```
aws iam put-role-policy \
  --role-name autom8y-asana-service-ecs-task \
  --policy-name autom8y-asana-service-task-s3 \
  --region us-east-1 \
  --policy-document file://beta3-rollback-task-s3-fullbucket.json
```

**Exact saved full-bucket JSON** (`beta3-rollback-task-s3-fullbucket.json` — this
is the live policy captured this session, byte-for-byte; also saved at
`/tmp/beta3-rollback-task-s3-fullbucket.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3CacheAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:HeadObject"
      ],
      "Resource": [
        "arn:aws:s3:::autom8-s3",
        "arn:aws:s3:::autom8-s3/*"
      ]
    }
  ]
}
```

Rollback is a single `put-role-policy` overwriting the inline policy in place —
effective in seconds (IAM eventual-consistency is sub-minute for inline role
policies). No ECS task restart is required (the task assumes the role; policy
changes take effect on the next S3 call).

### 3.5 Operator decision points

1. **Apply window**: NOT during the active soak's heaviest warm cadence; pick a
   window where a cold-start write can be observed but blast radius is bounded.
2. **N-hour watch length**: default 2h; EXTEND if no write observed in window.
3. **Codify-vs-leave-imperative**: after a GREEN canary, decide whether to
   immediately land the IaC `task_s3` resource (durable, prevents recurrence) or
   leave the imperative put-role-policy as interim and schedule the IaC follow-on.
   **Recommendation**: codify — an out-of-band imperative narrowing is itself the
   same drift class that created this finding.
4. **If AccessDenied on an un-listed prefix**: STOP, rollback, enumerate the new
   receiver path, add the minimal Sid, re-canary. Do NOT widen to full-bucket.

---

## 4. SVR Receipt Ledger (platform-behavior claims)

All live-state claims are `bash-probe` receipts (re-runnable). All TF/code claims
are `file-read`/`git-ls-files` receipts. UV-P items below are deferred.

- **Live full-bucket policy** — bash-probe `aws iam get-role-policy ... task-s3` → Resource `autom8-s3` + `autom8-s3/*`; exit 0.
- **Role active** — bash-probe `aws iam get-role ... RoleLastUsed` → `2026-06-10T17:18:43Z`.
- **TF absence (autom8y-asana)** — git grep `service-task-s3` → does-not-exist.
- **TF absence (autom8y)** — bash-probe git grep → empty stdout.
- **Stack passes no S3 arg** — file-read `asana/main.tf:88-265` module.service block.
- **Primitive has task_ssm/task_efs but no task_s3** — file-read `iam-service-role/main.tf:145,176`.
- **Prod backend is Redis not S3** — file-read `factory.py:155`.
- **No prod S3CacheProvider construction** — bash-probe grep (docstring/classdef only).
- **ECS writes dataframes/** — file-read `storage.py:342`, `section_persistence.py:806`, `progressive.py:298,545`.
- **γ-0 tasks/ writer external** — bash-probe grep (no S3 write key) + s3api LastModified.
- **CloudTrail aged out** — bash-probe `cloudtrail lookup-events` → `"Events": []`.

[UV-P: a `terraform apply` of the asana service today does not touch `autom8y-asana-service-task-s3` | METHOD: deferred-to-apply-observation | REASON: requires running `terraform plan` against live state with the role's TF state file, which is a mutation-adjacent operation out of this READ-ONLY station's scope; the verdict instead rests on the 3-source TF-resource-absence proof in §1.3]

[UV-P: the scoped target policy in §3.1 is sufficient (no AccessDenied) for the live ECS receiver | METHOD: deferred-to-canary (§3.3) | REASON: only the N-hour live canary with an observed write can confirm sufficiency; this spec asserts the target is DERIVED-COMPLETE from the enumerated surface, not that it is canary-proven]

---

## 5. Handoff

- **Owner**: platform-engineer executes β-3 (the put-role-policy + IaC codify) per
  this spec; chaos-engineer optionally validates the rollback procedure under a
  forced-AccessDenied fault before the real apply.
- **Blocking question (scoped-blocking-authority)**: β-3 MUST NOT apply until the
  §3.2 GO checklist is fully checked, including the live `module.service` ref
  re-confirmation (§3.2 item 4) — the one premise that could invert the verdict.
