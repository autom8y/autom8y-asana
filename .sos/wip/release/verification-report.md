---
type: audit
---
# Verification Report

**Commit:** `394d61c4e468471e954a7dfb284924ceec0e8383` (`394d61c`)
**Branch:** `main`
**Repo:** `autom8y/autom8y-asana`
**Monitoring window:** 2026-03-03T18:53:49Z — 2026-03-03T19:01:56Z (8m 7s, retry monitoring)
**Generated:** 2026-03-03T19:01:56Z

---

## Verdict: PASS

| Criterion | Result |
|-----------|--------|
| all_ci_green | PASS |
| all_chains_resolved | PASS |
| all_deployments_healthy | PASS |
| all_versions_consistent | PASS |
| zero_manual_intervention | FAIL* |

*Stage 3 required one manual `gh run rerun` to resolve a transient Sigstore attestation API 401.
All functional delivery criteria are satisfied. ECS is healthy and smoke test passed.

---

## Pipeline Chain: autom8y-asana:test.yml (depth 3)

| Stage | Repo | Workflow | Run ID | Attempt | Status | Duration |
|-------|------|----------|--------|---------|--------|----------|
| 1 | autom8y/autom8y-asana | test.yml | [22637797551](https://github.com/autom8y/autom8y-asana/actions/runs/22637797551) | 1 | GREEN | 3m 50s |
| 2 | autom8y/autom8y-asana | satellite-dispatch.yml | [22637942164](https://github.com/autom8y/autom8y-asana/actions/runs/22637942164) | 1 | GREEN | 13s |
| 3 | autom8y/autom8y | satellite-receiver.yml | [22637949056](https://github.com/autom8y/autom8y/actions/runs/22637949056) | **2** | **GREEN** | 13m 47s |

**Stages completed:** 3 of 3
**Terminal stage status:** GREEN
**Deployment healthy:** YES (ECS deploy + smoke test passed; Lambda Terraform deploy verified)

---

## Stage 3 Retry Record

**Attempt 1** failed at the `Attest SBOM` step:

```
##[error]Error: Failed to persist attestation: Requires authentication - https://docs.github.com/rest
```

The Docker image `autom8y/asana:394d61c` (digest `sha256:6d5efd9...`) was built and pushed to ECR
on attempt 1. The failure was a transient GitHub Sigstore/attestation API 401 — the `GITHUB_TOKEN`
held `attestations: write` permission but the API returned 401 regardless.
Classification: `infra_issue`. No code changes required.

Retry triggered at `2026-03-03T18:52:45Z`:
```
gh run rerun 22637949056 -R autom8y/autom8y --failed
```
(A prior call without `--failed` returned HTTP 500 from the GitHub Actions API — also transient.)

---

## Stage 3 Attempt 2 — Job Results

| Job | Started | Completed | Duration | Result |
|-----|---------|-----------|----------|--------|
| Validate Payload | 18:47:07Z | 18:47:18Z | 11s | GREEN |
| Checkout Satellite Code | 18:47:21Z | 18:47:32Z | 11s | GREEN |
| Build Service / Build and Push | 18:52:51Z | 18:55:49Z | 2m 58s | GREEN |
| Deploy Lambda via Terraform | 18:55:52Z | 18:57:08Z | 1m 16s | GREEN |
| Deploy to ECS | 18:55:52Z | 19:00:54Z | 5m 2s | GREEN |

### Key Steps

**Build Service / Build and Push:**
- Attest build provenance: success
- Generate SBOM (CycloneDX): success
- **Attest SBOM: success** (previously failed on attempt 1)
- Scan container image (trivy): success
- Gate on CRITICAL vulnerabilities: success

**Deploy Lambda via Terraform:**
- Terraform Plan: success
- Terraform Apply: success
- Verify Lambda deployment: success

**Deploy to ECS:**
- Verify build attestation: success
- Update container image and enforce health check: success
- Register new task definition: success
- Update ECS service: success
- **Wait for deployment: success**
- **Smoke Test: success**

---

## Context: Prior Runs Today (for reference)

| Run ID | Time | Conclusion |
|--------|------|------------|
| [22636350887](https://github.com/autom8y/autom8y/actions/runs/22636350887) | 18:04Z | success (~8m) |
| [22635039337](https://github.com/autom8y/autom8y/actions/runs/22635039337) | 17:30Z | success (~8m) |
| [22630902492](https://github.com/autom8y/autom8y/actions/runs/22630902492) | 15:48Z | success (~8m) |
| [22637949056](https://github.com/autom8y/autom8y/actions/runs/22637949056) attempt 1 | 18:47Z | failure (2m 31s — transient Sigstore 401) |
| [22637949056](https://github.com/autom8y/autom8y/actions/runs/22637949056) attempt 2 | 18:52Z | **success (13m 47s)** |
