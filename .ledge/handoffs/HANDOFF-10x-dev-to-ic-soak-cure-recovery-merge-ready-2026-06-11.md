---
type: handoff
handoff_type: validation
status: proposed
source_rite: 10x-dev
target_rite: ic-soak (the soak re-anchor + the deploy-gated acceptance) · operator (the merge + deploy levers)
title: Cure Recovery-Path Hardening MERGE-READY (PR #127) — deploy HELD/soak-clear-gated · soak anchor CORRECTED
date: 2026-06-11
pr: autom8y-asana#127 (10x/cure-recovery-path-hardening, off bafd2508)
ceiling_rung: broken-fixture-RED-proven + CI-green + qa-MODERATE → MERGE-READY (merge=operator)
evidence_grade: MODERATE  # 10x-dev self; eunomia STRONG-cert RESERVED rite-disjoint at a later seam
---

# HANDOFF — 10x-dev → ic-soak / operator — cure-recovery hardening is MERGE-READY (deploy HELD)

## TL;DR
The EXP-1 chaos findings are remediated in **PR #127** (fail-closed write + quality-aware rebuild gate),
**CI fully green**, qa-adversary **MERGE-READY (MODERATE)** with no defect. **Merge is your lever**
(the optional Meta-Grant to delegate it was not pasted; and its `eunomia-corroborated` precondition is
unmet — eunomia STRONG is a later rite-disjoint seam). **The merge IS a deploy** (Satellite Dispatch
auto-deploys on src merge to main) → it **resets the soak** → HELD/soak-clear-gated. Separately, the
PV gate caught that the **08:41:12Z soak anchor was already void** (raced by the #126 deploy) — corrected.

## What landed MERGE-READY (PR #127, receipts)
| Item | Rung | Receipt |
|---|---|---|
| Fork-1 fail-closed write (`fail_closed_write.py` pure + `progressive.py` gate wiring) | RED-proven | PRESERVE_PRIOR_GOOD / WRITE_COALESCED / WRITE_AS_IS; never-fabricate; per-entity (offer untouched) |
| Fork-2 quality-aware rebuild (`rebuild_gate.py` pure) | RED-proven | `stale_by_age OR (population_degraded AND NOT grant_unhealthy_recently)`; floor-SSOT-derived, G-DENOM-honest, storm-suppressed |
| `population_degraded`/`population_min_rate` persisted to `watermark.json` via `save_dataframe` | wired-real | round-trip exercised by `test_fork2_below_floor_clears_on_healthy_rewarm` |
| Broken-grant fixture (boto3-boundary, real shapes, exact-key) | RED→GREEN ×2 | builder 9/9; qa independently re-derived RED via 3 distinct mutations |
| Regression fixed (delegation test signature drift) | GREEN | `test_section_persistence_storage` updated to the extended `save_dataframe` contract; 1367 pass |
| CI | GREEN | all shards + full-graph Lint&Type + coverage + fuzz + CodeQL + gitleaks pass (Integration/Convention conditional-skip) |
| FROZEN + FROZEN-4 | GREEN | 7/7; no new `to_thread`; allowlist untouched |
| qa-adversary verdict | MERGE-READY (MODERATE) | no silent fabrication under wholesale/partial/transient/prior-read-error/cold-start faults |

## Soak-anchor CORRECTION (PV inversion, rung-honest)
The IC-SOAK-IGNITION 08:41:12Z anchor is **VOID** — the #126 (`bafd250`/`:508`, γ-0 annotation) deploy
reached steady-state **08:42:52Z**, ~100s after it, resetting the soak. `:508` is behavior-neutral and
the band holds (**coherent=564, gun=14, unit 723/3021, offer 1347/4079**), so the convergence is
continuous. **Re-anchor to 2026-06-11T08:42:52Z** pending operator/IC GO-criteria re-confirm on `:508`.
Detail: `.ledge/decisions/CORRECTION-soak-anchor-raced-by-126-deploy-2026-06-11.md`. **Process lesson:**
during a soak, even a behavior-neutral src merge auto-deploys + resets — so **PR #127's merge must be
timed by you** (it will reset whatever soak is then running).

## Your levers (surfaced, exact — NOT fired)
1. **Merge PR #127** → `env -u GITHUB_TOKEN gh pr merge 127 --repo autom8y/autom8y-asana --squash` (this triggers a deploy → soak reset; time it deliberately).
2. **Deploy** = the merge's Satellite Dispatch (no separate action); HELD/soak-clear-gated.
3. **Re-anchor the soak** on `:508` (or on the cure-bearing substrate if you bundle #127's deploy into the re-anchor — one reset instead of two; recommended since a re-anchor is needed anyway).
4. **Game-day EXP-1 re-run** (the live acceptance, deploy-gated): post-deploy, revoke `S3DurableTaskCacheRead` → warm → assert the unit frame is PRESERVED at 723/3021 (NOT nulled) + auto-re-heals on restore. This is the `self-heal-game-day-proven` rung — RESERVED.
5. **eunomia STRONG-cert** (rite-disjoint, later seam) — `/frame → eunomia/framing` if you want the STRONG before the soak clears.

## qa observations (non-blocking, watch-registered)
- **`grant_unhealthy_recently` hardcoded False at the sole prod call site** (`progressive.py:153-156`) — the storm-suppressor is latent in prod (the preload implies a live grant by construction; it protects a future warmer-side caller). Verified at unit altitude, not end-to-end. One-line note if a warmer-side caller is added.
- **`recovery_receipt=None` treated as wholesale-outage** (`fail_closed_write.py:189-191`) — conservative; safe today (wiring always threads the real receipt).

## Rungs (never round up)
**broken-fixture-RED-proven + CI-green + qa-MODERATE = MERGE-READY.** NOT merged, NOT deployed, NOT
live, NOT self-heal-game-day-proven. eunomia STRONG RESERVED. The telos five-signal remains
NOT verified-realized.

## DEFER watch-register (not scope-crept)
unit-floor calibration (UK-2) · EXP-2 full heartbeat-kill + EXP-3/4/5 game-days · SEAM-2 rebind ·
β-3 IaC-codify · autom8y vendored gen.json re-vendor · CHANGE-001 `asana-cache/tasks/*` OIDC grant ·
**Node20 non-deploy sweep — deadline 2026-06-16 (5 days)** · the 2 qa observations above.

Next `/frame` → **ic-soak/framing** (the soak re-anchor + the deploy-gated game-day acceptance), or
**eunomia/framing** if you want the rite-disjoint STRONG-cert of PR #127 first.
