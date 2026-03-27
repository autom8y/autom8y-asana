---
name: satellite_receiver_deployment_failures
description: Known failure modes in autom8y/autom8y Satellite Receiver Stage 3 deployment — all infra regressions resolved as of Round 4. Rounds 5 and 7 confirmed clean. Rounds 6, 8, 9, 10 failed at Stage 1. Round 11: Stage 1 and Stage 2 first-ever GREEN, Stage 3 failed — uv --frozen + --no-sources conflict in Dockerfile. Round 12: Docker build GREEN, two new Stage 3 failures — Lambda Terraform aws_region arg removed + ECS verify container index wrong. Round 13 (2026-03-25): 5-repo PLATFORM scope — autom8y-ads and autom8y-data full chain GREEN; three failures: asana ECS rollout=FAILED (new pattern), sms Docker 401 Unauthorized (infra/credentials), scheduling collection error (new regression). Round 14 (2026-03-25): Force-new-deployment also failed — root cause confirmed as missing canary test listener rule in ALB; infra escalation required. Rounds 15-16 (2026-03-26): Stage 1 ruff format/lint fixed. Round 17 (2026-03-26): Stage 1 and Stage 2 first-ever GREEN for commit ab88d9e; Stage 3 same ECS canary ALB failure (7th consecutive). Round 18 (2026-03-26): Manual dispatch escape hatch — Stage 2 GREEN (run 23573997606), Stage 3 RED (run 23574001411) — ECS canary ALB failure (8th consecutive). Root cause deepened: ECS service advancedConfiguration has no testListenerRule at all. Terraform apply recreated productionListenerRule but CANARY strategy requires BOTH. Round 19 (2026-03-26): Switched to ROLLING deployment (terraform apply + AWS CLI + push e76a71b). Stage 2 GREEN (run 23574386737, 20s). Stage 3 RED (run 23574390485, 23m 25s) — ECS ROLLING ServicesStable waiter timeout. NEW failure mode: rollout=IN_PROGRESS running=1/1 failed=0 for all 60 polls. No ALB errors, no failed tasks, no rollback. CI 15-minute cap exhausted before ECS completed circuit breaker evaluation. Round 20 (2026-03-26): FINAL PASS — Stage 2 GREEN (run 23575710247, 4s), Stage 3 GREEN (run 23575713587, 7m 31s). ECS rolloutState=COMPLETED within CI window. All five Satellite Receiver jobs succeeded including Wait for deployment, Verify deployed image digest, and Smoke Test. Verdict: PASS.
type: project
---

All Satellite Receiver regressions from the autom8y-asana PATCH release (2026-03-15) are resolved as of Round 4. Documented for future pattern recognition.

**Regression 1: Sigstore attestation — FIXED in Round 3**
Root cause: `push-to-registry: true` on `attest-build-provenance` action caused attestation to be stored in ECR registry rather than GitHub Attestation store. Fix: remove `push-to-registry: true`. Confirmed fixed in Rounds 3, 4, 5, and 7 — Build and Push job steps 16 and 19 (Attest build provenance + Attest SBOM) both complete with success. Note: the Deploy to ECS and Deploy Lambda jobs still show "Error: no attestations found" in their verification steps but those steps are non-fatal (`|| VERIFY_STATUS="FAILED"` pattern) and conclude success. This is expected permanent behavior under the current workflow design.

**Regression 2: Terraform ecs-otel-sidecar null variables — FULLY FIXED in Rounds 3-4**
The `ecs-otel-sidecar` primitive at `.terraform/modules/service/terraform/modules/primitives/ecs-otel-sidecar/main.tf` calls `templatefile("adot-config.yaml.tpl", {...})`. The asana service's `observability_config` block required all optional fields to be explicitly set:
- `aws_region` — FIXED in Round 3
- `metrics_path` — FIXED in Round 4
- `scrape_interval` — FIXED in Round 4
- `collector_cpu` / `collector_memory` — FIXED in Round 4

All four fields now supplied. Terraform Plan passes cleanly. Pattern: Terraform exits on first null variable error, so each fix round revealed one more unset field. When adding a new service to the ecs-otel-sidecar module, supply all optional observability_config fields explicitly to avoid this incremental failure pattern.

**Regression 3: ECS ServicesStable waiter timeout — transient infra_issue, NOT always present**
`aws: [ERROR]: Waiter ServicesStable failed: Max attempts exceeded`. Occurred on Rounds 2-4, NOT in Round 5, and again in Round 7 (retry 1 resolved it). The asana service can stabilize within the waiter window when ECS infrastructure load is lower. Round 5 completed Stage 3 in 13m 42s with no waiter timeout on a platform tooling push (no Docker image rebuild). When the timeout does occur, it resolves on retry within 2 attempts. Always allow up to 2 retries before treating as a persistent failure. The failure appears mid-run at the Deploy to ECS / "Wait for deployment" step. Round 12: ECS stabilized at Poll 32/60 (rollout=COMPLETED running=1/1 failed=0) — no waiter timeout. Round 20: ECS stabilized well within CI window (~3m 10s) after ECS service was in clean steady-state before dispatch.

**ROLLING deployment waiter timeout (Round 19, 2026-03-26) — same pattern, resolved in Round 20**
After switching to ROLLING deployment strategy (resolving the CANARY testListenerRule issue), the Round 19 run hit the same ECS ServicesStable waiter timeout. All 60 polls: rollout=IN_PROGRESS running=1/1 failed=0. No task failures, no rollback, no ALB errors. Error: `##[error]Deployment did not stabilize within 15 minutes`. The ECS circuit breaker evaluation window (default minimum healthy percent 100% with task replacement) takes longer than the CI waiter's 15-minute cap when the service is freshly recreated/modified. Round 20 confirmed: once the ECS service reaches steady state (rolloutState=COMPLETED, running=1/1, 1 deployment), a retry dispatch produces a clean waiter completion well within 15 minutes (3m 10s in Round 20).

**OpenSSF Scorecard — pre-existing ancillary failure (non-blocking)**
Scorecard `workflow-permissions` check scores top-level permissions as high-risk. This is a static security posture score (Severity: High) — not a gate triggered by application code changes. Pre-existing across all rounds. Fix requires hardening top-level permissions to `read-all` or `contents: read` in affected workflows. Separate security work item, not a release blocker.

**Round 9 regression: mypy arg-type errors in STANDARD_ERROR_RESPONSES — FIXED in Round 10**
Commit `1a44723` added `STANDARD_ERROR_RESPONSES: dict[int, dict[str, Any]]` in `src/autom8_asana/api/error_responses.py`. FastAPI's APIRouter methods expect `dict[int | str, dict[str, Any]] | None` for the `responses` parameter — mypy strict rejects the narrower `dict[int, ...]` type. 39 errors across 7 route files. Fixed in commit `58896d1` by changing the annotation to `dict[int | str, dict[str, Any]]`. mypy strict passed cleanly in Rounds 10 and 11.

**Round 9 regression: Resolver endpoint returning HTTP 500 — FULLY FIXED in Round 11**
Round 9: 6 tests failing — 3 integration E2E (test_entity_resolver_e2e.py) + 3 unit route (test_routes_resolver.py).
Round 10: Commit `58896d1` fixed the unit mock signature mismatch. The 3 unit tests pass. 3 integration E2E tests still 500.
Round 11: Commit `06183a8` added `active_only` to E2E resolver mock. All 3 integration E2E tests now pass. Stage 1 is GREEN.

Root cause was confirmed: the `active_only` filter (commit `1f83e85`) added a required keyword argument to the resolver mock's dependency. The unit mock was patched in Round 10, but the integration E2E mock also needed the same `active_only=True` argument. Once both mocks matched the real signature, all 6 resolver tests pass.

**Round 11 regression: uv --frozen + --no-sources conflict in Dockerfile — FIXED in Round 12**
Stage 3 Satellite Receiver failed at the Docker build step. The Dockerfile in autom8y-asana contained:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-sources --extra api --extra auth --extra lambda
```

The version of `uv` installed in the runner image (`ubuntu-24.04 Version: 20260309.50.1`) no longer accepts `--frozen` combined with `--no-sources`. Fix in commit `12cf5fb`: Remove `--no-sources`. Docker build passed in Round 12 confirming the fix.

**Round 12 regression: Lambda Terraform aws_region argument removed from module interface — FIXED in Round 13**
Stage 3, job: Deploy Lambda via Terraform. Terraform Plan failed at `main.tf line 102` in the asana service definition in autom8y/autom8y. The Lambda service module in autom8y/autom8y removed `aws_region` from its variable interface, but the asana service caller still passed it. Fixed in autom8y/autom8y by Round 13 (HEAD `fcb2955b`). Deploy Lambda via Terraform succeeded cleanly in Round 13's asana satellite-receiver run.

**Round 12 regression: ECS image digest verification queries wrong container by index — STATUS UNKNOWN (Round 13)**
Stage 3, job: Deploy to ECS / Deploy to ECS, step: Verify deployed image digest. The Round 12 false negative queried `containers[0].image` from `describe-tasks`, returning the OTEL sidecar instead of the app container. In Round 13 the asana ECS deployment failed before reaching the Verify step (rolloutState=FAILED at Poll 2), so this fix could not be confirmed. Presumed fixed in `fcb2955b` given Lambda fix was in the same HEAD. Confirmed working in Rounds 19-20 (digest verify succeeded).

**Round 13 regression: autom8y-asana ECS rollout=FAILED, failedTasks=0 — ROOT CAUSE RESOLVED in Round 19 by switching to ROLLING**
Stage 3, run 23518837465, job: Deploy to ECS / Deploy to ECS, step: Wait for deployment.
```
Poll 1/60: rollout=IN_PROGRESS running=1/1 failed=0
Poll 2/60: rollout=FAILED running=1/1 failed=0
Deployment FAILED (rolloutState=FAILED, failedTasks=0)
```
Root cause confirmed via ECS service events (Round 14 force-deploy investigation) and deepened in Round 18 via direct ECS service inspection:

The ECS service used a CANARY deployment strategy. The service's `advancedConfiguration` contained:
- `alternateTargetGroupArn`: `a8-asana-green/5e180261daf3da79` (present)
- `productionListenerRule`: ARN of the priority-120 production rule (present, recreated by Round 4 terraform apply)
- `testListenerRule`: **ABSENT** (this was the structural gap)

**Fix applied in Round 19**: Switched ECS service to ROLLING deployment strategy via terraform apply + AWS CLI. Pushed commit e76a71b to autom8y/autom8y. This resolved the CANARY structural failure completely. Round 19's Stage 3 run had zero ALB errors, zero failed tasks, no rollback events.

**Round 13 regression: autom8y-sms CodeArtifact 401 Unauthorized in Docker build — OPEN (2026-03-25)**
Stage 3, run 23518729560, job: Build Service / Build and Push, step: Build and push image (with CodeArtifact).
`uv export --no-sources` failed because the CodeArtifact index returned 401 Unauthorized inside the Docker build context. The dependency unsatisfiability message (autom8y-ai[anthropic]>=1.3.0 not available) is a consequence of auth failure, not a real constraint violation. Classification: infra_issue (credential injection). The Dockerfile correctly uses `--no-sources` without `--frozen`. A retry with valid CodeArtifact auth credentials injected into the Docker build context should succeed.

**Round 13 regression: autom8y-scheduling tests/golden_traces collection error — OPEN (2026-03-25)**
Stage 1, run 23518703951: `ModuleNotFoundError: No module named 'tests.golden_traces.serializer'`. pytest collection aborted with exit code 2 — no tests ran. This is NOT the known 7 pre-existing failures (GATE-ESC-003). Exit code 2 (collection error) vs exit code 1 (test failures) are categorically different. The module `tests.golden_traces.serializer` is missing or has a broken import — likely a missing `__init__.py` or renamed/removed file introduced by commit `213422e` (fix(lint): resolve ruff SIM105). satellite-dispatch concluded `skipped` (not fired). Stage 3 not reached. Classification: regression.

**Round 14 (2026-03-25): Force-new-deployment also failed — confirmed infra escalation required**
Commit `26e36a4` (fix(dataframes): resolve asset_edit INTERNAL_ERROR). A `aws ecs update-service --force-new-deployment` was issued after clearing stuck deployment state. The force-new-deployment (ecs-svc/1711504920042385159, task-def :319) immediately failed with the same `PRE_SCALE_UP` ALB rules-not-found error as all prior attempts. This is the 6th consecutive deployment failure since 2026-03-24T17:30Z. The prior deployment (ecs-svc/3260077771747396911, task-def :312) remains ACTIVE serving traffic; health endpoint returns HTTP 200. No code retry will succeed until the canary test listener rule is recreated in the ALB. Verdict: FAIL. Monitoring completed via ECS direct poll (no CI run — the CI pipeline stages all passed independently).

**Rounds 15-16 (2026-03-26): Stage 1 ruff format/lint failures for commit bbba220 PATCH**
Round 15 (session-internal Round 1): ruff format --check failed on `src/autom8_asana/dataframes/builders/cascade_validator.py`. Fix: ruff format applied.
Round 16 (session-internal Round 2): ruff check found 3 violations (I001 unsorted import block at line 114, F401 unused `re` at line 414, F841 unused `total_rows` at line 416) in same file. Fix commit `ab88d9e` removed dead code and reordered imports.

**Round 17 (2026-03-26): Stage 1 and Stage 2 GREEN — Stage 3 same ECS canary ALB failure (7th consecutive)**
Commit `ab88d9e`, run 23573283784. Stage 1: all 4 CI jobs passed (Lint & Type Check, Test, Integration Tests, Convention Check). Duration 4m 32s. Stage 2: Satellite Dispatch run 23573404803, completed in 8s. Stage 3: Satellite Receiver run 23573407846 — same signature: Poll 1 IN_PROGRESS running=1/1 failed=0, Poll 2 FAILED running=1/1 failed=0. Task definition :321 was registered. This is the 7th consecutive ECS deployment failure. No code fix can help. Infra escalation remains the only path forward.

**Round 18 (2026-03-26): Manual dispatch escape hatch — Stage 2 GREEN, Stage 3 RED (8th consecutive ECS failure). testListenerRule confirmed absent.**
Manual dispatch of `satellite-dispatch.yml` (run 23573997606, completed in 10s). Satellite Receiver run 23574001411 triggered immediately (repository_dispatch, created 02:09:05Z). Run progressed through all jobs: Validate Payload (success), Checkout Satellite Code (success), Build Service/Build and Push (success, task-def :324 registered), Deploy Lambda via Terraform (success), Deploy to ECS (FAILED at "Wait for deployment").

Direct ECS service inspection (`aws ecs describe-services`) confirmed `advancedConfiguration` has no `testListenerRule` key. ALB listener rules (`aws elbv2 describe-rules`) show no rule for the `a8-asana-green` target group. The Round 4 terraform apply (this PATCH) recreated the `productionListenerRule` but the `testListenerRule` was never part of the Terraform config.

Lambda deployment succeeded cleanly. ECS is the sole remaining blocker.

**Round 19 (2026-03-26): ROLLING strategy applied — Stage 2 GREEN, Stage 3 RED (ServicesStable waiter timeout). CANARY failure mode fully resolved.**
Terraform change (commit e76a71b) switched autom8y-asana-service from CANARY to ROLLING deployment strategy. Manual dispatch Stage 2 run 23574386737 (completed success, 20s). Stage 3 Satellite Receiver run 23574390485 triggered immediately.

Stage 3 job results: Validate Payload (success), Checkout Satellite Code (success), Build Service/Build and Push (success — Docker build, ECR push, Trivy scan all passed), Deploy Lambda via Terraform (success), Deploy to ECS (FAILED — waiter timeout at Poll 60).

Critical evidence: zero ALB errors, zero failed tasks, no rollback event. `running=1/1 failed=0` throughout all 60 polls. Error: `##[error]Deployment did not stabilize within 15 minutes`. The ECS circuit breaker evaluation window outlasted the CI 15-minute cap. The task was running and health checks passing at Poll 60.

This is the same transient ServicesStable timeout pattern seen in early rounds (Regression 3 above). The CANARY structural failure is resolved. Retry recommended — verify ECS service rolloutState via `aws ecs describe-services` first to determine if Round 19's deployment completed post-CI.

**Round 20 (2026-03-26): FINAL PASS — Stage 2 GREEN, Stage 3 GREEN. ECS ROLLING deployment successful.**
Manual dispatch Stage 2 run 23575710247 (completed success, 4s). Stage 3 Satellite Receiver run 23575713587 triggered immediately (03:15:09Z).

Stage 3 job results: Validate Payload (success, 7s), Checkout Satellite Code (success, 12s), Build Service/Build and Push (success, 3m 30s — Docker, ECR, Trivy, SBOM attestation all passed), Deploy Lambda via Terraform (success, 1m 9s), Deploy to ECS (success, 3m 30s — Wait for deployment completed ~3m 10s, digest verify success, smoke test success).

The ECS service was in clean steady state (rolloutState=COMPLETED, running=1/1, 1 deployment) before this dispatch. This allowed the Round 20 ROLLING deployment to stabilize within the CI window in ~3m 10s rather than exceeding the 15-minute cap. Verdict: PASS.

**Round history:**
- Round 1: Stage 1 (Test) — 13 test failures + ruff violation from env var rename. Fixed in autom8y-asana.
- Round 2: Stage 3 — Attestation fix + aws_region fix. Retries exhausted on ECS waiter.
- Round 3: Stage 3 — metrics_path + scrape_interval exposed. Fixed in autom8y/autom8y.
- Round 4: Stage 3 — All null vars resolved. ECS waiter resolved on retry 2. Verdict: PASS.
- Round 5: Platform tooling push (no app code). Chain resolved on first attempt, zero retries, no ECS waiter timeout. Verdict: PASS.
- Round 6: Stage 1 (Test) — Ruff formatting violation in 2 files introduced by tooling sync push. Stage 2 skipped, Stage 3 not reached. Verdict: FAIL. Fix: ruff format on entry.py and field_resolver.py.
- Round 7: Formatting-only fix. Stage 1 green (3m 46s). Stage 2 green (9s). Stage 3 — ECS waiter timeout on attempt 1; resolved on retry 1 of 2. All 5 Satellite Receiver jobs green. Deployment healthy. Verdict: PASS.
- Round 8: Stage 1 (Test) — Ruff formatting violation in 2 files introduced by 6-commit API enrichment push (run 23494049011, 2026-03-24). Files: src/autom8_asana/api/error_responses.py and tests/unit/api/routes/test_resolver_gid_contract.py. Stage 2 fired (skipped). Stages 3-5 not reached. Verdict: FAIL. Fix: ruff format on both files.
- Round 9: Stage 1 (Test) — Two regressions exposed after Round 8's ruff fix (run 23494393484, 2026-03-24, commit f57c4d7). (1) mypy 39 errors: STANDARD_ERROR_RESPONSES dict[int,...] not assignable to dict[int|str,...] in 7 route files. (2) Resolver 500: all 6 resolver tests return RESOLUTION_ERROR. Stages 2-5 not reached. Verdict: FAIL.
- Round 10: Stage 1 (Test) — mypy fixed. Unit resolver mock mismatch fixed (3 tests now pass). Integration E2E resolver 500 persists (3 tests, run 23494850849, 2026-03-24, commit 58896d1). Stages 2-5 not reached. Verdict: FAIL.
- Round 11: Stage 1 GREEN (run 23495311748, commit 06183a8). Stage 2 GREEN (Satellite Dispatch, run 23495558885). Stage 3 RED — uv --frozen + --no-sources conflict in Dockerfile (run 23495567965). Stages 4-5 not reached. Verdict: FAIL.
- Round 12: Stage 1 GREEN (run 23495832163, commit 12cf5fb). Stage 2 GREEN (run 23496067553). Stage 3 RED (run 23496074229) — Docker build GREEN (uv fix confirmed), but two jobs failed: (1) Deploy Lambda via Terraform: Terraform Plan rejected aws_region arg (module interface change in autom8y/autom8y); (2) Deploy to ECS: Verify deployed image digest false negative (containers[0] returned OTEL sidecar not app container). Stages 4-5 not reached. Verdict: FAIL.
- Round 13 (2026-03-25): 5-repo PLATFORM scope. autom8y-ads chain GREEN (run 23517401116, pre-existing commit 9c64ef7). autom8y-data chain GREEN (run 23518905597, commit f1170d9, 18m total). autom8y-asana: Stage 1 GREEN (run 23518701992, commit c6bcef6), Stage 2 GREEN (run 23518833869), Stage 3 RED (run 23518837465) — ECS rollout=FAILED at Poll 2, failedTasks=0. autom8y-sms: Stage 1 GREEN (run 23518702738, commit 9934462), Stage 2 GREEN (run 23518725018), Stage 3 RED (run 23518729560) — Docker build 401 Unauthorized on CodeArtifact. autom8y-scheduling: Stage 1 RED (run 23518703951, commit 213422e) — collection error ModuleNotFoundError tests.golden_traces.serializer. Lambda Terraform confirmed fixed. Verdict: FAIL.
- Round 14 (2026-03-25): Force-new-deployment for commit 26e36a4. CI stages (test, build, Lambda Terraform) all passed independently. ECS force-new-deployment (ecs-svc/1711504920042385159, task-def :319) failed immediately — 6th consecutive failure since 2026-03-24T17:30Z. Root cause confirmed: missing canary test listener rule in ALB HTTPS listener. Service live on task-def :312. Verdict: FAIL. Infra escalation required.
- Round 15 (2026-03-26): Stage 1 (Test) — ruff format --check failed for commit bbba220 cascade source/phone normalization changes. Fix: ruff format on cascade_validator.py. Verdict: FAIL.
- Round 16 (2026-03-26): Stage 1 (Test) — ruff check found 3 violations in cascade_validator.py (I001, F401, F841). Fixed in commit ab88d9e. Verdict: FAIL.
- Round 17 (2026-03-26): Stage 1 GREEN (run 23573283784, commit ab88d9e, 4m 32s). Stage 2 GREEN (run 23573404803, 8s). Stage 3 RED (run 23573407846, 4m 57s) — ECS rollout=FAILED at Poll 2 (7th consecutive). Same canary ALB listener rule absence as Rounds 13-16. Task-def :321 registered but deployment blocked. Verdict: FAIL. Infra escalation required.
- Round 18 (2026-03-26): Stage 2 GREEN (manual dispatch, run 23573997606, 10s). Stage 3 RED (run 23574001411, 5m 4s) — ECS rollout=FAILED at Poll 2 (8th consecutive). Root cause deepened: ECS advancedConfiguration confirmed missing testListenerRule (not just an ALB rule gap — the ECS service config itself never had one). Lambda deployment succeeded. Task-def :324 registered. Verdict: FAIL. Infra escalation required — testListenerRule must be added to ECS service Terraform config AND a corresponding ALB rule must be created.
- Round 19 (2026-03-26): ROLLING deployment strategy applied (terraform apply + AWS CLI, commit e76a71b to autom8y/autom8y). Stage 2 GREEN (manual dispatch, run 23574386737, 20s). Stage 3 RED (run 23574390485, 23m 25s) — ECS ROLLING ServicesStable waiter timeout. All 60 polls: rollout=IN_PROGRESS running=1/1 failed=0. No ALB errors, no failed tasks, no rollback. CI 15-minute cap exhausted. CANARY failure mode is resolved — new failure mode is the known transient ServicesStable waiter timeout. Lambda Terraform succeeded. Docker build/ECR push/Trivy scan all succeeded. Verdict: FAIL. Retry recommended after verifying ECS rolloutState via AWS CLI.
- Round 20 (2026-03-26): FINAL PASS. Stage 2 GREEN (manual dispatch, run 23575710247, 4s). Stage 3 GREEN (run 23575713587, 7m 31s). ECS ROLLING deployment completed within CI window (~3m 10s). All 5 Satellite Receiver jobs succeeded. Smoke test passed. Commit ab88d9e deployed and healthy. Verdict: PASS.

**Why:** Latent issues in autom8y/autom8y infrastructure. The ecs-otel-sidecar module requires a complete set of observability config variables; the asana service was added to the module without populating all required fields. Terraform exits on first error so each round reveals one more null variable. The ECS waiter timeout is a runtime infrastructure behavior, not a code issue. Ruff formatting violations recur when new files are added or substantially modified without running the formatter locally first. The Round 9 mypy failure follows the pattern of CI running mypy strict — any new type annotation introduced without strict compatibility will surface here. The resolver 500 pattern (all scenarios failing uniformly) is a reliable signal of a startup/wiring error rather than logic bugs. The unit/integration split in Round 10 confirmed the fix must target the actual mock used by E2E tests, not just the unit mock. The Round 11 Dockerfile failure is a runner image uv version bump — the `--frozen` + `--no-sources` combination became invalid. Round 12 failures are both in autom8y/autom8y: the Lambda module dropped `aws_region` from its interface without updating all callers, and the ECS digest verification script uses array index `[0]` which is fragile when sidecars precede the app container in the task definition. Rounds 13-18: ECS rollout=FAILED with failedTasks=0 is caused by the ECS CANARY deployment controller failing at the PRE_SCALE_UP lifecycle hook — the testListenerRule for the a8-asana-green canary target group was never configured in the ECS service advancedConfiguration AND the corresponding ALB rule does not exist. Round 19: CANARY failure resolved by switching to ROLLING; new transient failure is ECS ServicesStable waiter timeout (same pattern as Regression 3). Round 20: ROLLING deployment completed cleanly once ECS service was in steady state before dispatch. The sms 401 is a credentials gap in the Docker build context for the `uv export --no-sources` step. The scheduling collection error is a missing module (tests.golden_traces.serializer) likely caused by a ruff SIM105 lint fix that may have altered module structure.

**How to apply:** When adding any service to the ecs-otel-sidecar module, always supply all required and optional templatefile() variables explicitly in the service's observability_config block. When the ECS ServicesStable waiter times out on ROLLING deployment with running=1/1 failed=0, always check the ECS rolloutState via `aws ecs describe-services` before retrying — the service may have stabilized after the CI script exited. If ECS rolloutState is already COMPLETED when you re-dispatch, the new run will complete well within the 15-minute CI cap. Allow up to 2 retries of the satellite-dispatch before escalating. Platform tooling pushes (no Docker rebuild) may avoid the ECS waiter timeout entirely. When rollout=FAILED at Poll 2 with failedTasks=0 on a CANARY strategy, check ECS service events for ALB listener rule errors — this is a structural config gap, not a transient issue, and retrying without infra change is futile. Ruff formatting violations are deterministic — always apply `uv run ruff format <file>` before pushing. When using STANDARD_ERROR_RESPONSES with FastAPI routes, always type it as `dict[int | str, dict[str, Any]]` to satisfy mypy strict. For Dockerfile uv sync commands, do not combine `--frozen` with `--no-sources`. When modifying the Lambda Terraform service module interface in autom8y/autom8y, scan all service callers for removed arguments. When writing ECS image digest verification steps, always query by container name (not array index). A pytest collection error (exit code 2) is categorically distinct from test failures (exit code 1) — GATE-ESC-003 exemptions do NOT cover collection errors.
