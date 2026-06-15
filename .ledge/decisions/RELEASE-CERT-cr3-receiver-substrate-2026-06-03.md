---
type: decision
status: accepted
date: 2026-06-03
rite: releaser
role: qa-adversary (adjudicator + attestor)
initiative: cr3-receiver-bulk-fanout-readiness
artifact_kind: release-certification
self_ref_axis_note: >
  This is a RITE-DISJOINT releaser certification of an SRE-authored substrate. For the
  deploy-state / merge-state / IaC-drift axes the releaser independently re-derived every
  receipt (gh REST, aws CLI, terraform plan JSON audit) — so on those axes it LIFTS the two
  SRE handoffs' "deployed" claims from self-ref MODERATE → STRONG (external corroboration by
  a disjoint rite). For the full-load ≥99% capacity re-gate and the live HTTP behavior probes
  it relies on the SRE smoke agents' execution and grades those sub-claims accordingly
  (STRONG-live where re-verifiable, MODERATE where single-source).
aws_context: { account: "696318035277", region: us-east-1, identity: "user/tom.tenuta" }
verdict: CERTIFIED
clears: [cr3-producer-receiver-99pct-re-gate, cr3-consumer-monolith-cutover-prep]
stage_b: human/IC-gated (unchanged by this cert)
handoff_back: sre
---

# RELEASE-CERT — CR-3 Receiver-Substrate (2026-06-03)

Adversarial adjudication (default-to-REFUTED) of the 5 acceptance criteria in
`HANDOFF-sre-to-releaser-cr3-receiver-substrate-certification-2026-06-03.md`. Every load-bearing
claim was independently re-derived from live receipts (not accepted on the evidence agents' prose).
No production secret VALUES printed (OTLP credential redacted to length + sha256[:8]).

## OVERALL VERDICT: **CERTIFIED** (5/5 PASS, with 2 tracked non-blocking caveats)

The CR-3 receiver substrate — #96 disjoint-checkpoint image, the `cache_warmer_bulk` module (30-min
schedule, mem=2048, reserved=1), the IAM trio, cpu=1024 durable, and the serve-stale/503/honest-empty
read-path behaviors — is **proven `prod == main`, zero-drift on the CR-3 surface, IAM-trio-intact,
SHA-pinned, and functionally smoked**. The handoffs' "deployed in prod" claims LIFT MODERATE → STRONG
on the deploy/merge/IaC axes. The two-pronged producer/consumer work is **CLEARED to proceed**;
Stage-B (fallback removal) remains human/IC-gated independently.

## Per-criterion adjudication

| # | Criterion | Verdict | Grade | Receipt (independently re-derived) |
|---|---|---|---|---|
| **1** | 3 substrate PRs merged at SHAs; #97/#338 NOT merged | **PASS** | STRONG (live) | `gh api .../pulls/{96,331,335}` → merged=true at `3c1dca5`/`f09ecda`/`e2fab87` (base main). #97 open `mergeable_state:clean` merged=false; #338 open merged=false. asana main tip = `3c1dca5` (IS the #96 merge). `f09ecda`+`e2fab87` confirmed ANCESTORS of autom8y main (`compare` status=behind, ahead_by=0). |
| **2** | Clean `terraform plan` = 0-drift, IAM trio present, SHA tag consistent | **PASS** (CR-3 surface ZERO-drift; sole delta orthogonal) | STRONG (live, plan-JSON audited) | `/tmp/cr3-asana-plan.json` (135 resource_changes): **0 add / 5 change / 0 destroy**. All 5 changes = `aws_lambda_function.main` and the ONLY changed key is `OTEL_EXPORTER_OTLP_HEADERS` (added=[], removed=[]; sha8 `2c843518`→`4ed6204e`, len 252 both sides — single fleet-wide SSM cred rotation, NON-CR-3). ECR `3c1dca5`=`@sha256:00ebebb5…` (tags `[3c1dca5,latest]` → cosmetic drift = SAME digest, no real divergence). asana TF byte-identical between plan SHA `f947358` and current `origin/main` `11bc828f` (`git diff --stat` empty). |
| | — **Trap-4 guard** (REFUTE a clean plan that didn't load the IAM trio) | **PASS** | STRONG | Plan JSON shows `aws_iam_role_policy.cache_warmer_bulk_{s3,self_invoke,cloudwatch_metrics}` ALL present as **no-op** (in scope, not absent/destroyed) + `dlq`/`secrets`/role attachments no-op. **Stack-wide destroy actions = NONE.** Live corroboration: `iam list-role-policies autom8-asana-cache-warmer-bulk-lambda-role` → 5 inline (trio + dlq + secrets). The trio was loaded into scope — not a false-clean. |
| | — **Trap-5 guard** (REFUTE a plan run without the SHA image_tag) | **PASS** | STRONG | Bulk warmer `image_uri` before==after == `…/asana:3c1dca5` (SHA tag, NOT `latest`); ECS `aws_ecs_task_definition.service` + `aws_ecs_service.service` both no-op; `CACHE_WARMER_CHECKPOINT_PREFIX` no-op. `variables.tf:image_tag default="latest"`, `image_ref default=@sha256:21a70179…` (stale) — defaults WOULD have produced phantom service churn; the plan correctly passed `image_tag=3c1dca5`. ECS no-op is legitimate via `ecs-fargate-service/main.tf:277-284 lifecycle{ignore_changes=[desired_count,task_definition]}` ("Prevent TF from reverting task definitions deployed by CI/CD") — and the LIVE task IS on `:462`/cpu=1024/`00ebebb5`, so NOT a refresh-skip false-clean. |
| **3** | Deploy durable: cpu=1024, bulk Active/mem=2048/30-min/IAM, #96 image fleet-wide | **PASS** | STRONG (live) | ECS svc ACTIVE 1/1, taskdef `:462` **cpu=1024 mem=2048** image `:3c1dca5`. Bulk lambda Active, mem=2048, reserved=1, schedule `cron(0,30 * * * ? *)` ENABLED, ResolvedImageUri `00ebebb5`, LastMod `09:06:11Z`. Offer lambda Active, `00ebebb5`. Fast lambda `ResourceNotFoundException` (#97/#338 not live). No asana-scoped APPLY pending: the only non-terminal apply-path run (Service-Terraform push@`11bc828f`, run 26884223507) is **plan-only, environment-gated `waiting`** (cannot mutate state) and `11bc828f`(#341) touches only `terraform/shared/`, not `services/asana/`. |
| **4** | QA smoke green on all 5 content-bound checks | **PASS** | STRONG-live for (a/503)(b/serve-stale)(c/honest-empty)(warm-persist)(cpu); MODERATE for canary (smoke-scale only) | (a) serve-stale: warm-set GID `1201081073731555` 200-from-cache, `meta.freshness=approaching_stale`, sub-ms query_ms (SWR path, not build) — SRE live probe. (b) 503: cold GID → 503 `CACHE_BUILD_IN_PROGRESS` + `Retry-After:30` header — SRE live probe. (c) honest-empty: `CustomerHealth` 200 `meta.honest_empty=true` total_count=0; controls (162/1480 rows) → honest_empty=false (discriminator holds). warm-persist: **independently re-verified** S3 `dataframes/1201081073731555/watermark.json` LastMod `12:06:43Z` row_count=3012; `checkpoints/bulk/latest.json` LastMod `12:17:21Z` (active sweep); AccessDenied on data-path since 09:20Z = 0. cpu durable = criterion 3. **Canary RAN at SMOKE scale (1min/30rpm, exit 0 PASS) — NOT the full 10min/100rpm ≥99% re-gate** (that is the producer prong's, not this cert's). |
| **5** | Certification artifact lifting MODERATE → STRONG | **PASS** | STRONG (this file) | This artifact. Rite-disjoint releaser independently re-derived merge/deploy/IaC receipts → lifts those axes to STRONG. |

## Adversarial findings (surfaced honestly; none blocking)

1. **Plan is NOT a literal 0/0/0** — it is `0 add / 5 change / 0 destroy`. The CR-3 substrate is zero-drift;
   the 5 changes are a SINGLE orthogonal delta: `OTEL_EXPORTER_OTLP_HEADERS` rotated in SSM
   (`/autom8y/production/observability/grafana-tempo-otlp-headers`) after the lambdas' last deploy, not yet
   propagated. Fleet-wide (all 5 asana lambdas, identical sha8 transition), NON-destructive, NON-IAM,
   NON-image. **Disposition: route to platform-engineer / SRE-obs to converge** (re-run satellite deploy /
   `a8 deploy` so lambdas pick up SSM v10 → re-plan should yield literal 0/0/0). A fix PR
   (`sre/observability-tempo-cred-single-source`) is already in flight. This does NOT block CR-3 on its merits.
2. **Smoke source-equivalence claim was imprecise** — the SRE smoke agent asserted all 5 probed source files
   "SAME-AS-MAIN@3c1dca5"; independent `git diff origin/main` shows 4/5 identical but
   `src/autom8_asana/core/project_registry.py` DIFFERS by **+60 purely-ADDITIVE lines** (the held #97
   fast-lane block: `FAST_LANE_HEAVY_GIDS`, `fast_lane_prematerialization_keys()`). The cited warm-set range
   (`:229-298`) and `bulk_prematerialization_keys` (the exercised path) are byte-identical to main; the
   appended fast-lane code is dead/undeployed (not in `00ebebb5`). Net: a MODERATE-downgrade nuance on one
   structural sub-claim, NOT a refutation — behavior (a/b/c) is attested by LIVE HTTP probes against the
   deployed image regardless of working-tree source equivalence.
3. **Cosmetic-only deltas vs handoff text** (non-issues): autom8y main advanced `f947358`→`11bc828f` (asana TF
   untouched); ECS taskdef is `:462` not the handoff's `:459` (advanced 3 revs, cpu=1024 held); #338
   `mergeable_state` now `unknown` (was `behind`) — immaterial, both not-merged.

## Tracked non-blocking caveats (file as follow-ups; do NOT gate CR-3)
- **C1 — OTLP cred propagation lag** (finding 1): fleet-wide lambda OTLP header behind SSM by 1 rotation.
  Owner: platform-engineer / SRE-obs. Watch: re-plan after convergence = literal 0/0/0.
- **C2 — CloudWatch metric-namespace IAM mismatch**: bulk warmer emits `LastSuccessTimestamp` under namespace
  `Autom8y/AsanaCacheWarmer` but the `cloudwatch-metrics` policy grants PutMetricData only for
  `cloudwatch:namespace = autom8y/cache-warmer-bulk` → 3 dropped datapoints since 09:20Z (per SRE smoke logs,
  MODERATE single-source). Observability side-channel only; data path (frames + checkpoints) clean. Owner:
  platform-engineer.

## Gating logic
- **CLEARS — producer prong:** receiver ≥99% re-gate per
  `HANDOFF-autom8-to-asana-sre-cr3-producer-work-queue-ingest-2026-06-03.md`. NOTE: this cert proves the
  substrate is LANDED/DURABLE; it does **not** discharge the ≥99% capacity verdict (canary ran smoke-scale
  only). The re-gate must run the full 10min/100rpm dual-arm load and disaggregate the 3 `GetDfFallback`
  causes (S7 false-green guard) before any Stage-B.
- **CLEARS — consumer prong:** monolith cutover prep per `HANDOFF-asana-sre-to-autom8-cr3-return-2026-06-03.md`.
- **Stage-B (fallback removal):** remains human/IC-gated; unchanged by this cert.
- Had any of Trap-4 (trio absent/destroyed) or Trap-5 (no SHA image_tag) or a CR-3-surface drift or a smoke
  content-fail occurred → verdict would be NOT-CERTIFIED, both prongs HALTED, TF/deploy fix routed to
  platform-engineer. None occurred.

## handoff_back → sre
CERTIFIED. Clear the two-pronged work. Carry C1 (OTLP cred converge) + C2 (metric-namespace IAM) as
non-blocking follow-ups to platform-engineer. Re-run a fleet-wide satellite/`a8` deploy to converge C1, then
a confirmatory re-plan (expect literal 0/0/0). Stage-B stays IC-gated.

## Receipts index (SVR)
- PRs: `gh api repos/autom8y/{autom8y-asana,autom8y}/pulls/{96,97,331,335,338}` (merged/merged_at/merge_commit_sha/state/base); `branches/main`; `compare/main...{f09ecda,e2fab87}`.
- Image: `aws ecr describe-images autom8y/asana imageTag=3c1dca5` (digest 00ebebb5, tags [3c1dca5,latest]).
- ECS: `aws ecs describe-services autom8y-cluster/autom8y-asana-service` (:462); `describe-task-definition :462` (cpu 1024, image :3c1dca5, ADOT sidecar).
- Lambdas: `aws lambda get-function autom8-asana-cache-warmer-{bulk,,fast}` (bulk/offer Active 00ebebb5; fast ResourceNotFound); `aws events describe-rule autom8-asana-cache-warmer-bulk-schedule` (cron(0,30…) ENABLED); bulk env `CACHE_WARMER_CHECKPOINT_PREFIX`.
- IAM: `aws iam list-role-policies autom8-asana-cache-warmer-bulk-lambda-role` (5 inline incl trio).
- Plan: `/tmp/cr3-asana-plan.json` (0/5/0; per-resource changed-key audit; Trap-4 trio no-op; Trap-5 image :3c1dca5; stack destroys NONE). `terraform v1.14.6`. Source `autom8y/terraform/services/asana/` @ `origin/main` (asana TF == plan SHA f947358). `variables.tf:image_tag default=latest / image_ref default=@sha256:21a70179`; `ecs-fargate-service/main.tf:277-284 ignore_changes`.
- S3: `s3api head-object` watermark.json (12:06:43Z, 442B) + checkpoints/bulk/latest.json (12:17:21Z, 7886B); watermark contents row_count=3012 entity_type=unit.
- CI: `gh run view 26884223507` (Service-Terraform push@11bc828f — all production Plan jobs `waiting`/env-gated, asana plan-only). `git show --stat 11bc828f` (#341 touches terraform/shared only).
- Source equivalence: `git diff --quiet origin/main -- <5 files>` (4 SAME; project_registry.py +60 additive held-#97 lines).
- No secret VALUES printed (OTLP cred → length 252 + sha256[:8] only).
