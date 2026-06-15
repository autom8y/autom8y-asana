---
type: handoff
handoff_type: validation
status: proposed
source_rite: sre
target_rite: ic-soak (primary) · eunomia (N=2 + Phase-α STRONG request rides) · operator (the bundle)
title: β staged (PRs #490/#491 plan-validated) · PV-DRIFT resolved (TF-NEVER-OWNED) · proving deploy CAPTURED · the ordered operator bundle
date: 2026-06-10
---

# HANDOFF — sre → ic-soak / eunomia / operator

## R-matrix (GREEN/RED, receipts)

| Station | Result | Receipt |
|---|---|---|
| R1 proving deploy (P5) | **GREEN — proven in anger** | Run 27292936411: `Deploy to ECS` **success in 10.5 min** (17:17:42→17:28:10, lock released on completion vs the 30-min burn); `Metrics-Smoke Gate` split job, **bounded 2 min**, reds cosmetically, `continue-on-error` → run success; node24 + CodeArtifact-retry chain green. The queued #123 ride dequeued ON lock-release (the fix observable twice in one hour). |
| R2 β-1 | **PR-OPEN, plan-validated, MERGE HELD at the prod gate** | autom8y **#490**: gen.json vendored byte-identical (sha256 `03a6201c…`), `locals_namespaces.tf` jsondecode derivation, 4+2 env literals + 3 warmer policies derived; **plan: `No changes`** (warmer IAM ×3 + lambdas w/ image pin). 23 checks green; the only pending check is the operator-gated `Plan (asana, production)` environment approval — merging past it is apply-adjacent, so the PR is left MERGEABLE for you. |
| R2 β-2 | **PR-OPEN, plan-validated, MERGE HELD** | autom8y **#491** (disjoint diff on #490): plan `0 add / 3 change / 0 destroy` — exactly the 3 warmer policies: project-frames loses PUT/DELETE/Head, gains GET-only `S3FossilFramesRead`. |
| R3 PV-DRIFT | **RESOLVED — TF-NEVER-OWNED-IT** | The live full-bucket `autom8y-asana-service-task-s3` policy exists in NO repo's TF (3-source proof; the `iam-service-role` module emits task_ssm/task_efs but NO task_s3); console/CLI-created, mimics the module naming; CloudTrail aged out (role 2025-12-22). An apply would never touch it — the premise "TF is scoped" was FALSE (those lines were warmer policies). |
| R3 write-surface | **ENUMERATED** | ECS writes ONLY `dataframes/*` (storage.py:342 → section_persistence.py:806; put_async at preload/legacy/admin); `asana-cache/tasks/` is **READ-ONLY from ECS** — **γ-0 PINNED-NEGATIVE: the receiver is NOT the tasks/ writer; it is the external monolith (`user/autom8` full-bucket)**, out of β-3 blast radius. β-3 spec + GO criteria + rollback JSON: `.ledge/decisions/SRE-beta3-spec-pv-drift-reconcile-2026-06-10.md`. |
| AC-6 | **RED (re-verified)** | `receiver_query_outcome_total` absent in AMP. The soak gate unchanged (#36/R2). |
| Band | holding | 16:00Z cron: coherent=592/gun=11/723/3021; the #123 (behavior-neutral) post-deploy check rides monitor b8t4oczt2. |

## THE OPERATOR BUNDLE (ordered; everything below is YOURS — exact commands)
1. **Approve + merge β-1 (#490), then β-2 (#491)** — approve the `Plan (asana, production)` environment check on each, review the pasted plan (β-1 `No changes`; β-2 `3 to change`), merge.
2. **Apply #486** (the soak observability bundle) then **arm the must-arm pair**:
   `cd autom8y/terraform/services/observability && terraform apply` → then `terraform apply -var=asana_receiver_slo_alerts_armed=true` (probe dead-man + burn-rate; the 3 CW alarms may stay dark).
3. **Apply β-1 then β-2** (after #486; same pipeline): β-2's apply retires the fossil PUT/DELETE live.
4. **β-3 decision** (the spec's GO criteria are now 3/5 satisfied — write-surface ✓ drift ✓ γ-0 ✓): canary the scoped ECS policy per `.ledge/decisions/SRE-beta3-spec-…` §3 (rollback JSON saved); after GREEN, codify `task_s3` in TF (leaving it imperative reproduces the drift class).
5. **Chaos EXP-1+EXP-2** (post-#486-apply) per `.ledge/specs/CHAOS-DESIGN-receiver-post-cure-blast-2026-06-10.md`.
6. **AC-6 (#36/R2)** — the soak's single blocking dependency; then co-sign the 7d clock per `IC-SOAK-READINESS` P1–P8.
Standing: UK-2 (#114) · CHANGE-001 ack · CR-3 Stage-B HELD · γ-0's REMAINING half (pin the monolith writer's code anchor in the autom8 repo when accessible).

## eunomia requests (ride the seam)
1. Phase-α STRONG-cert (#123: registry+t1–t5+phantom-RETIRE; receipts in the 10x-dev handoff).
2. `integration-boundary-fidelity` **N=2 promotion ruling** (config-altitude application; layer mapping in the arch HANDOFF).

## Rungs (never round up)
P5 = **proven-in-anger** · β-1/β-2 = **PR-open/plan-validated, NOT merged** (held at the prod gate by design) · β-3 = **specced** · #486 = merged-NOT-applied · soak = NOT started · telos = NOT verified-realized (SEAM-2 · AC-6 · valid soak · fallback flip).

## DEFER watch-register
metrics-smoke cosmetic red (bounded, non-blocking — diagnose the cold-start race at leisure) · the 128k legacy task-cache · CHANGE-002..005 · t3 blind spots · Node20 non-deploy sweep (06-16) · #97 · SEAM-2/CR-3 clocks.

Next `/frame` → `ic-soak/framing` (the clock, the day AC-6 lands) — or eunomia first at your discretion.
