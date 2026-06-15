---
artifact_id: HANDOFF-releaser-to-sre-10xdev-cr3-gate2-release-sequencing-2026-06-08
schema_version: "1.0"
type: handoff
status: draft
handoff_type: execution
source_rite: releaser
target_rite: sre + 10x-dev            # sre = the 7-day soak (proven->live); 10x-dev = coverage gate + G-DENOM backstop
priority: high
blocking: false
initiative: "CR-3 clean-break cutover · R3 GATE-2 receiver LANDING (proven -> merged -> live)"
date: 2026-06-08
decision: "PATH A — soak the certified 29ee052 NOW; eunomia landing runs as a parallel non-blocking track"
rung: "GATE-2 = proven (on 29ee052, the running+certified artifact). Soak (operator clock) converts proven->live. PR #110 = merged-pending. P2-a = emitting."
plan_artifacts:
  - .sos/wip/release/release-plan.md
  - .sos/wip/release/dependency-graph.yaml
  - .sos/wip/release/platform-state-map.yaml
incoming: .ledge/handoffs/HANDOFF-eunomia-to-10xdev-sre-cr3-gate2-external-cert-verdict-2026-06-08.md
---

# CR-3 R3 GATE-2 — Release Sequencing Verdict (releaser → sre/10x-dev)

> **PATH A selected (releaser pantheon, all 3 stations concur): soak the certified `29ee052` NOW.** It is the running AND GATE-2-certified artifact; PR #110's contents (probe SCRIPT, P0-b TEST, P2-a ship-dark/inert) change nothing about the running image, so the 7-day soak drives GATE-2 **proven→live without a new deploy** — sidestepping the PV-3 redeploy+re-prove burden entirely. The eunomia landing (incl. #110) is a parallel track that only triggers a re-prove if/when a NEW image deploys.

## PV Pre-Flight (live receipts)
| # | Premise | Result |
|---|---|---|
| PV-1 | PR #110 open/clean, 10 GATE-2 files | ✓ |
| PV-2 | eunomia→main (PR #108) gating | **BLOCKED** — `ci / Aggregate Coverage Gate=FAILURE` (run 26947346772); all 4 Test shards green |
| PV-3 | deployed = certified artifact | ✓ `29ee052` = origin/main HEAD = task-def :485 (cpu2048/mem8192) |
| Trap-4 | warm lane paused | ✓ section warmer reserved=0 + schedule DISABLED |
| **NEW** | **IaC drift (OPERATOR-STOP)** | **`origin/main` TF declares cpu=1024/mem=2048 (literal); live=2048/8192. The §D substrate is uncodified. An asana `terraform apply` could REVERT the substrate → re-arm RECV-BULK-001.** See the amended P0-a handoff. |

## The DAG (3 parallel tracks; G-HALT is branch-local — no sibling cascade)
- **Track SOAK (the proven→live critical path):** `S1` arm the 7-day soak on `29ee052`. No deploy. **Operator lever.**
- **Track A (land the GATE-2 instrument + guards):** `B1` green the eunomia coverage gate → `A1` merge #110→eunomia → `A2` merge #108 eunomia→main (BEHIND; rebase first; confirm #97 NOT merged — Trap-4) → `A3` auto satellite redeploy (NEW image) → `A4` **mandatory re-prove GATE-2 on the new image** (G-THEATER). Gated by PV-2.
- **Track B (durability IaC):** `TB1` author the P0-a floor + VG-005 alarm **+ the cpu/mem drift-close** (one commit) → `TB2` `terraform plan` (verify cpu 1024→2048, mem 2048→8192, NO unintended replacement) → `TB3` `terraform apply`. Independent of the image.

## Exact operator commands (surfaced — NOT executed; production levers are yours)
```
# S1  — arm the soak on 29ee052 (monitoring posture; no AWS mutation to start). Rollback lever held:
#       aws ecs update-service --cluster <autom8-monolith> --service <monolith> --task-definition <rev with satellite_get_df_enabled=false>
# A1  — gh pr merge 110 --merge --repo autom8y/autom8y-asana          (after B1)
# A2  — git checkout chore/eunomia-ci-rationalization && git merge origin/main && git push   # it is BEHIND
#       gh pr merge 108 --merge --repo autom8y/autom8y-asana          (after A1; confirm #97 unmerged)
# TB1 — (autom8y monorepo) edit terraform/services/asana/main.tf: cpu 1024->2048, memory 2048->8192,
#       + floor validation (cpu>=2048 && mem>=8192), + VG-005 alarm — ONE commit; PR; merge
# TB2 — cd terraform/services/asana && terraform init && terraform plan   # MUST show cpu 1024->2048, mem 2048->8192, NO forced replacement; else HALT
# TB3 — terraform apply
# A4  — (agent, after A3 auto-deploy) re-run the deploy-gate probe on the NEW image + collect receipts
```

## Realization rungs (G-RUNG — no rounding)
- GATE-2: **proven** (29ee052) → **live** on S1 completion (7-day soak).
- PR #110: **merged-pending** → merged on A1+A2.
- P2-a EMF export: **emitting** (ship-dark) → alerting needs the cross-repo durable backend (DEFER).
- Substrate floor: **uncodified-live** → codified-protecting on TB3 (drift-close + guard).

## DEFER (watch-registered, NOT scope-crept)
G-DENOM-backstop (task #44, 10x-dev) · §E-NoSuchKey (fold into VG-005) · P2a-durable-backend · P8-monorepo · **PR #97 cache-warmer fast lane (DIRTY/CONFLICT, Trap-4 surface — do NOT merge without explicit Trap-4 review)** · PR #103 section-guard (independent; eunomia rebases if it lands first).

## Next /frame routing (do NOT dispatch the next rite's specialists from here)
- **sre/framing:** arm + watch the 7-day soak on `29ee052` (S1; proven→live); §E/VG-005 alarm posture.
- **10x-dev/framing:** green the eunomia coverage gate (B1) + the G-DENOM 5th-criterion backstop (#44).
- Operator owns: S1 arm, A1/A2 merges, TB1-TB3 monorepo apply, A4 re-prove authority, all of Stage-B/Secret-2 (irreversible).

*Releaser verdict: PATH A. Evidence MODERATE (releaser self-assessment) — the eunomia cert already supplied rite-disjoint corroboration for the GATE-2 structure; a NEW image's GATE-2 (A4) needs its own rite-disjoint critic. Secrets by name/sha-prefix only. All production levers are the operator's.*
