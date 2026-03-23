---
name: satellite_receiver_deployment_failures
description: Known failure modes in autom8y/autom8y Satellite Receiver Stage 3 deployment — all regressions resolved as of Round 4. Rounds 5 and 7 confirmed clean. Round 6 failed at Stage 1 (ruff formatting). Round 7 PASS with 1 ECS waiter retry.
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
`aws: [ERROR]: Waiter ServicesStable failed: Max attempts exceeded`. Occurred on Rounds 2-4, NOT in Round 5, and again in Round 7 (retry 1 resolved it). The asana service can stabilize within the waiter window when ECS infrastructure load is lower. Round 5 completed Stage 3 in 13m 42s with no waiter timeout on a platform tooling push (no Docker image rebuild). When the timeout does occur, it resolves on retry within 2 attempts. Always allow up to 2 retries before treating as a persistent failure. The failure appears mid-run at the Deploy to ECS / "Wait for deployment" step.

**OpenSSF Scorecard — pre-existing ancillary failure (non-blocking)**
Scorecard `workflow-permissions` check scores top-level permissions as high-risk. This is a static security posture score (Severity: High) — not a gate triggered by application code changes. Pre-existing across all rounds. Fix requires hardening top-level permissions to `read-all` or `contents: read` in affected workflows. Separate security work item, not a release blocker.

**Round history:**
- Round 1: Stage 1 (Test) — 13 test failures + ruff violation from env var rename. Fixed in autom8y-asana.
- Round 2: Stage 3 — Attestation fix + aws_region fix. Retries exhausted on ECS waiter.
- Round 3: Stage 3 — metrics_path + scrape_interval exposed. Fixed in autom8y/autom8y.
- Round 4: Stage 3 — All null vars resolved. ECS waiter resolved on retry 2. Verdict: PASS.
- Round 5: Platform tooling push (no app code). Chain resolved on first attempt, zero retries, no ECS waiter timeout. Verdict: PASS.
- Round 6: Stage 1 (Test) — Ruff formatting violation in 2 files introduced by tooling sync push. Stage 2 skipped, Stage 3 not reached. Verdict: FAIL. Fix: ruff format on entry.py and field_resolver.py.
- Round 7: Formatting-only fix. Stage 1 green (3m 46s). Stage 2 green (9s). Stage 3 — ECS waiter timeout on attempt 1; resolved on retry 1 of 2. All 5 Satellite Receiver jobs green. Deployment healthy. Verdict: PASS.

**Why:** Latent issues in autom8y/autom8y infrastructure. The ecs-otel-sidecar module requires a complete set of observability config variables; the asana service was added to the module without populating all required fields. Terraform exits on first error so each round reveals one more null variable. The ECS waiter timeout is a runtime infrastructure behavior, not a code issue.

**How to apply:** When adding any service to the ecs-otel-sidecar module, always supply all required and optional templatefile() variables explicitly in the service's observability_config block. When the ECS ServicesStable waiter times out, always retry (up to 2 retries) before investigating as a persistent failure. Platform tooling pushes (no Docker rebuild) may avoid the ECS waiter timeout entirely. Ruff formatting violations are deterministic — a retry without a code fix will fail identically; always apply the format fix first.
