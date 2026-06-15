---
type: handoff
handoff_type: execution
status: proposed
source_rite: 10x-dev
target_rite: releaser/framing (deploy → re-game-day → re-anchor) · ic-soak (the clock) · operator (the levers)
title: Warmer-path PRESERVE enforcement MERGED (#128 → 3a59c72c) — deploy + re-game-day + re-anchor at the releaser seam
date: 2026-06-11
pr: autom8y-asana#128 (merged squash → main 3a59c72c)
ceiling_rung: merged (deploy/re-game-day/re-anchor = releaser seam; STRONG = eunomia, later)
evidence_grade: MODERATE  # 10x-dev self; STRONG is eunomia rite-disjoint at soak-clear
heads:
  asana_main: 3a59c72c   # was 7973c10a (#127); #128 squash-merged
---

# HANDOFF — 10x-dev → releaser — the warmer+serve PRESERVE gap is CLOSED (merged), ready to deploy + re-game-day + re-anchor

## TL;DR
The game-day RED (PRESERVE decided-but-not-enforced) is fixed and **MERGED** (#128 → main `3a59c72c`).
It took **three defect-rounds in one class** — each caught by adversarial qa, each closed structurally,
not patched. The fix converges BOTH the write side AND the serve side onto single gated primitives, so
no current or future writer/server can bypass the fail-closed decision. Ceiling reached: **merged**.
The **deploy → re-run game-day → re-anchor the 7-day soak** is the releaser/ic-soak seam (the soak is
void, so the deploy is free when it fires). eunomia STRONG-cert is reserved (rite-disjoint, soak-clear).

## What landed (#128, cumulative — receipts)
| Layer | Fix | Proof |
|---|---|---|
| **Write (D2)** | converge all dataframe writers onto the gated `write_final_artifacts_async`; carry `WriteDecision` on `BuildResult` → warmer/admin/decorator | warmer-path broken-grant fixture RED→GREEN; W3/W6/W7 GATED, W4/W5 guard-covered |
| **Memory-put (D2b)** | on a degrade decision, skip+evict the hot-tier promote | serve-altitude probe RED→GREEN; #127 builder 9-green preserved |
| **Serve (D2c)** | converge BOTH memory-serve readers (`_check_freshness_and_serve` + `_get_circuit_lkg`) onto ONE gated accessor `_memory_get_serviceable` | circuit-open probe RED→GREEN; convergence-completeness grep: the sole `memory_tier.get` in src/ is inside the accessor |
| **qa final (D3c)** | convergence-completeness audit — 11-path serve enumeration, 2 mutation REDs, no fabrication | **MERGE-READY (MODERATE)**: "no un-gated memory-serve path remains" |

## The lesson (for the record + scar-tissue)
This is **integration-boundary-fidelity recursing three times**: a fix that gates ONE of N writers/servers
goes green in unit tests while a sibling path still surfaces the degrade. #127 gated the receiver/progressive
builder; D2 the warmer disk-write; D2b the memory-put; D2c the circuit-LKG serve. The durable cure each
time was **convergence onto one gated primitive** (the G-PROPAGATE "one propagation point"), and the catch
each time was a **live/integration test asserting frame CONTENT** (`count(mrr)`), never the PRESERVE log —
the log fired while the write degraded, twice. Stub-green ≠ production-real, at the serve altitude.

## The releaser seam (what's next — the soak is void, deploy is free)
1. **Deploy** main `3a59c72c` (Satellite Dispatch → receiver + warmer). Judge by image tag + rolloutState COMPLETED + floor 2048/8192, never job color (metrics-smoke red is cosmetic; Validate-Payload Docker-Hub timeouts are transient — `gh run rerun --failed`).
2. **Re-run game-day EXP-1** on the deployed substrate — THE acceptance this procession earns: revoke `S3DurableTaskCacheRead` one lane → force a warm → assert the unit frame is PRESERVED at **723/3021 by CONTENT at BOTH layers** (the S3 `dataframe.parquet` AND `cache.get_async` serve — the serve layer is the NEW acceptance dimension D2b/D2c added) → restore → assert Fork-2 auto-re-heal. A FAIL routes back to 10x-dev; PRESERVE-proven earns `self-heal-game-day-proven`.
3. **Re-anchor** the 7-day telos-soak to the clean-plane moment on the hardened substrate (supersede the CORRECTION + IC-SOAK-IGNITION records). Then the clock runs.
Rollback staged-pattern: restore grant + (if needed) the captured prior-good frame; re-capture prior-good BEFORE the revoke.

## Rungs (never round up)
**merged ✓** (`3a59c72c`). NOT deployed, NOT re-game-day-proven, NOT soak-running. The deploy/re-game-day/
re-anchor are the releaser/ic-soak seam's; the STRONG attest is eunomia's, rite-disjoint, at soak-clear.
The telos five-signal remains NOT verified-realized.

## DEFER watch-register (carried)
FM-5 column-fidelity frame (operator-ratified, post-soak — `OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md`) ·
UK-2 floor calibration · #127's 2 qa observations (grant_unhealthy_recently latent-in-prod; recovery_receipt=None→wholesale) ·
β-2 IaC drift-lock (self-healed by the #127 deploy, but un-drift-locked) · CHANGE-001 nightly RED-until-OIDC-grant ·
**Node20 non-deploy sweep — deadline 2026-06-16 (5 days)**.

Next `/frame` → **releaser/framing** (deploy → re-game-day → re-anchor). Do not dispatch the next rite's specialists directly.
