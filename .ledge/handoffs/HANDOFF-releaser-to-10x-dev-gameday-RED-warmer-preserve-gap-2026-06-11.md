---
type: handoff
handoff_type: assessment
status: proposed
source_rite: releaser
target_rite: 10x-dev (the fix) · ic-soak (the re-anchor — HELD on the fix)
title: GAME-DAY RED — #127 PRESERVE is decided-but-not-enforced on the WARMER write path (section_persistence:842); soak re-anchor HELD
date: 2026-06-11
initiative: cure-recovery-path-hardening (FPC Phase-2 follow-up)
evidence_grade: STRONG (deploy-empirical: live revoke→warm→degraded-parquet despite a logged PRESERVE decision; root-locus grep-confirmed on origin/main)
heads:
  asana_main: 7973c10a (#127 merged + DEPLOYED — ECS :509/7973c10 + warmer 7973c10, floor 2048/8192, both faces COMPLETED)
---

# HANDOFF — releaser → 10x-dev — the game-day caught a production gap the unit tests could not

## TL;DR
The releaser procession LANDED #127 (merge `7973c10a` → deployed `:509`/`7973c10` both faces, floor held — **R2/R3 BANKED**). The **game-day EXP-1 self-heal acceptance (R4) is RED**: under a revoked durable-read grant, the warmer's `decide_write` **correctly returned PRESERVE_PRIOR_GOOD and logged it** — but the degraded parquet was **still persisted (0/3021)**. The fail-closed decision is computed and logged but **NOT enforced** at the warmer's actual write site. Per G-HALT, the **soak re-anchor (R5) is HELD** — we do not anchor a 7-day clock on a substrate whose self-heal is unproven. Plane restored to 723/3021; grant restored. Routed to 10x-dev for a localized follow-up to #127.

## The RED — deploy-empirical receipts (live, this session)
Game-day on the DEPLOYED `:509`/`7973c10` substrate (the #127-hardened code):
1. **Captured prior-good** (healthy `:509`): unit 3021/**723**/719/335, offer 4079/1332.
2. **Revoked** `S3DurableTaskCacheRead` on the main warmer lane (11:32:56Z; rollback sha `5b119126`); forced a warm.
3. **The decision was CORRECT and logged**: `fail_closed_write_preserve_prior_good` — `{entity_type: unit, project_gid: 1201081073731555, min_nonnull_rate: 0.0, reason: "below_floor_wholesale_durable_read_outage"}` @ **11:34:47.383Z** (span `109c668f`). decide_write reached the warmer path and chose PRESERVE on the wholesale outage — exactly as designed.
4. **But the parquet was written anyway**: `final_artifacts_written {row_count: 3021, index_written: false, entity_type: unit}` @ **11:34:47.626Z** (span `438951b3`, 243ms later). The fetched frame = **0/3021** (identical to the un-hardened EXP-1). `index_written:false` is the tell — PRESERVE was honored for the INDEX branch but **NOT for the dataframe.parquet**.
5. **Restored**: grant @ 11:36:11Z (4 Sids), prior-good frame @ 11:36:13Z → re-verified **723/3021**. Offer frame untouched throughout.

## Root locus (grep-confirmed on origin/main `7973c10a`)
`src/autom8_asana/dataframes/section_persistence.py:806 write_final_artifacts_async` — the WARMER's write path — calls `save_dataframe` **unconditionally at :842**; the function contains **ZERO** `WriteDecision`/`decide_write`/PRESERVE references (grep). #127 wired the fail-closed gate into `progressive.py`'s `_finalize_artifacts_write_async` (the receiver/preload builder — qa-adversary tested THAT path, GREEN). The PRESERVE decision is computed upstream and logged, but **not threaded into** the downstream `write_final_artifacts_async` that the warmer actually uses to persist the parquet. Two finalize paths; the gate guards one.

## The fix (10x-dev — localized follow-up to #127)
Thread the `WriteDecision` from the decision site into `write_final_artifacts_async` (section_persistence:806) and **gate the `:842 save_dataframe` on it** — skip the parquet save (not just the index) when `PRESERVE_PRIOR_GOOD`; honor `WRITE_COALESCED` likewise. The test contract must add a **warmer-path** broken-grant fixture (the qa fixture covered the progressive path only — this is the integration-boundary-fidelity lesson: cover BOTH finalize paths, or assert they converge on one gated write). Re-run the game-day after the fix deploys to earn the `self-heal-game-day-proven` rung.

## Rungs (never round up)
**merged ✓ · deployed ✓ (both faces, :509/7973c10)** — BANKED. **self-heal-game-day-proven = RED** (warmer enforcement gap). **soak-RUNNING(re-anchored) = HELD** on the follow-up fix. The 08:41Z anchor remains VOID; the re-anchor is now gated on a self-heal-proven warmer path (which needs the fix → a deploy → which resets/re-anchors anyway, so bundle them).

## Banked side-finding (resolved this procession)
DEFER #115 (β-2 live-drift) **self-healed**: the #127 deploy's "Deploy Lambda via Terraform" job re-applied the asana module from autom8y main → the warmer S3 policy now carries `S3FossilFramesRead` + the project-frames PUT/DELETE strip (4 Sids, β-2-correct). The earlier live-drift was reconciled by this deploy.

## DEFER watch-register (carried)
Node20 non-deploy sweep — deadline **2026-06-16 (4 days)** · CHANGE-001 nightly RED-until-`asana-cache/tasks/*` OIDC grant (forcing-function working) · FM-5 column-fidelity (operator-ratified, frame post-soak — `OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md`) · the 2 qa observations on #127 (grant_unhealthy_recently latent-in-prod; recovery_receipt=None→wholesale) · Stage-B→Secret-2 (soak-clear-gated).

Next `/frame` → **10x-dev/framing** (the warmer-path enforcement fix — a tight follow-up to #127), THEN the re-deploy + re-game-day + re-anchor (releaser/ic-soak). The FM-5 frame queues behind the soak per the operator ruling.
