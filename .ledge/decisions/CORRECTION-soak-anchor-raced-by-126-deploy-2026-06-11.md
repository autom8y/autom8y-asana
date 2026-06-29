---
type: decision
subtype: correction
status: accepted
title: "CORRECTION — the 08:41:12Z soak anchor was raced by the #126 (:508) deploy; re-anchor to 08:42:52Z"
date: 2026-06-11
corrects: .ledge/decisions/IC-SOAK-IGNITION-telos-soak-RUNNING-2026-06-11.md
rite: 10x-dev (PV-gate discovery; the authoritative re-anchor is operator/IC)
evidence_grade: MODERATE
---

# CORRECTION — soak anchor raced by the #126 deploy

> 🔄 **RESOLVED + SUPERSEDED 2026-06-11** by
> `IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md` — the hold below cleared: #128
> (`3a59c72c`) deployed to `:510` (COMPLETED 14:12:12Z), the re-game-day passed **by CONTENT at
> BOTH altitudes** (disk byte-identical under fault + serve 723/3021; PRESERVE decided AND
> enforced), an iris live-HTTP smoke proved the serve path + AC-6 pipe, and the clock is
> re-anchored to **2026-06-11T15:24:21Z on `:511`** (src-identical carry; clear 06-18T15:24:21Z).
> The 08:42:52Z proposal below was mooted by the #127/#128 deploys. Retained for lineage only.

> **UPDATE 2026-06-11 (releaser, post-#127):** the re-anchor is now further GATED. #127 deployed
> (`:509`/`7973c10`) but the game-day EXP-1 (R4) went **RED** — the warmer write path persists a
> degraded frame despite a logged PRESERVE decision (`section_persistence.py:842` ungated; see
> `HANDOFF-releaser-to-10x-dev-gameday-RED-warmer-preserve-gap-2026-06-11.md`). The soak re-anchor is
> **HELD** until the warmer-path enforcement fix lands + a re-run game-day proves PRESERVE live.
> Re-anchor to the THEN-clean moment, not 08:42:52Z.

> Surfaced at the 10x-dev Cure-Recovery-Path-Hardening PV gate (default-to-REFUTED).
> **PV-SOAK-RUNNING was REFUTED.** The 08:41:12Z anchor in the IC-SOAK-IGNITION record is VOID.
> This is a rung-honesty correction (G-RUNG: never let a false "RUNNING" claim stand). The
> convergence is intact; only the anchor timestamp + substrate-version were wrong.

## What happened (ECS event receipts, CEST→UTC)
- The sre procession merged **#126 (γ-0 attribution, `bafd2508`)** to autom8y-asana main during its run.
  That src change triggered a Satellite Dispatch → receiver redeploy.
- ECS task-def **`:508` = image `bafd250` = #126** registered **08:33:28Z**; new task healthy 08:34:22Z;
  old task drained 08:41:50Z; **deployment steady-state 08:42:52Z** (`describe-services events`).
- The soak was anchored **08:41:12Z** reading `:507` — but `:508` was MID-ROLLOUT at that instant and
  reached steady state **~100s later**. The anchor read a transient pre-cutover deployment slot.

## Verdict
- **The 08:41:12Z anchor is VOID** — per the soak's own RESET rule ("a deploy mid-window = new
  substrate = new soak"), a deploy completed ~100s after it. The soak did not validly run on `:507`.
- **`:508` is a CLEAN, behavior-neutral substrate.** `:508`/`bafd250`/#126 changes only the SNC
  registry `external_name` literal + `namespaces.gen.json` (γ-0 annotation; no prefix/ARN/verb/behavior
  change — confirmed by the merging agent's STOP-gate). Band on `:508` re-derived live:
  **unit 723/3021, offer 1347/4079, coherent=564, gun=14** — converged (same plane, +15 offer cells
  from a normal warm). The convergence observation is CONTINUOUS across `:507`→`:508`.

## Recommended re-anchor (operator/IC lever — NOT fired here)
Re-anchor the 7-day clock to **2026-06-11T08:42:52Z** (the `:508` steady-state), target clear
**2026-06-18T08:42:52Z**, IF the GO criteria re-confirm on `:508` (they should — behavior-neutral;
dead-man/SLI/#486 unaffected by a γ-0 annotation deploy). The ~100s shift is immaterial to a 7-day
window; the substrate-version bump `:507`→`:508` is recorded for honesty, not because it broke anything.

## Process finding (routed, not papered)
Merging a **deploy-triggering src change (#126) during a running-soak window** raced the anchor. The
γ-0 attribution was behavior-neutral so the blast was benign — but the GENERAL lesson: any src merge to
autom8y-asana main auto-deploys the receiver and resets the soak. **During a soak, even "behavior-neutral"
src merges must be treated as soak-resetting** (the Satellite Dispatch does not distinguish annotation
from behavior). This reinforces THIS procession's deploy-hold: the cure-hardening PR must NOT be merged
during a window the operator intends to keep running — its merge IS a deploy.
