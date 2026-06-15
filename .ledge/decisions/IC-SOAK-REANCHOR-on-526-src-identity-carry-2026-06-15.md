---
type: decision
subtype: ic-soak-ignition
status: accepted
title: "TELOS-SOAK RE-ANCHORED on :526/6517f0b — operator-ruled 2026-06-15; src-identity-carry doctrine; band-gate CLEARED; ~3 days banked"
date: 2026-06-15
clock_state: RUNNING
anchor_utc: 2026-06-12T12:20:25Z   # :526 steady-state (the #136/6517f0b deploy); ~3.1 days already banked at re-anchor time (reconstructed-clean)
target_clear_utc: 2026-06-19T12:20:25Z   # +7d from the :526 steady moment
substrate: ECS :526 / image 6517f0b (BOTH faces) — src-IDENTICAL to fa265ce1 (#136 = .github/workflows/test.yml only); the :512→:526 chain is ONE logical substrate under CLOCK-DOCTRINE-src-identity-carry
evidence_grade: MODERATE   # hygiene-rite re-anchor under operator ruling; soak-CLEARED STRONG is eunomia's at clear
authority: operator stakeholder-interview ruling 2026-06-15 ("Bank the 3 days — anchor :526 steady, gated on Finding-3 clearing")
supersedes:
  - .ledge/decisions/RESET-RECOMMENDATION-131-deploy-reanchor-proposal-2026-06-11.md   # the co-signed :516 anchor — VOID (raced by #136 ~4h later)
  - .ledge/decisions/IC-SOAK-REANCHOR-telos-soak-2026-06-11.md                          # the :511 anchor lineage
governing_doctrine: .ledge/decisions/CLOCK-DOCTRINE-src-identity-carry-2026-06-15.md
incident: .ledge/decisions/INCIDENT-soak-blackout-and-136-reset-2026-06-15.md
---

# IC SOAK RE-ANCHOR on :526 — the clock runs again, honestly

> Anchored to **2026-06-12T12:20:25Z** (the :526/`6517f0b` steady-state), clear **2026-06-19T12:20:25Z**.
> ~3.1 days were already banked at re-anchor (the substrate has been stable since 06-12T12:20Z); under
> CLOCK-DOCTRINE-src-identity-carry the soak CONTINUED across the behavior-neutral :512→:526 chain
> rather than restarting. Days 1–3 are RECONSTRUCTED-clean (residual evidence, not contemporaneous);
> day-4 (06-15) is the first contemporaneous attestation. Ceiling: soak-RUNNING.

## How we got here (the incident, resolved)
The 06-12T09:02:05Z co-signed anchor (:516) was VOID within ~4h — #136 (a `test.yml` reusable-pin bump)
merged during the freeze → deployed `6517f0b` (:526) at 12:20Z. The session-bound sentinel cron then
died across a multi-day interruption, so the reset slipped through unattested until the 06-15 PV
re-derivation caught it. Three operator rulings (2026-06-15 stakeholder interview) closed it:

1. **Re-anchor**: bank the ~3 days on :526 (this record). Anchor = :526 steady 06-12T12:20:25Z.
2. **Band anomaly (Finding-3)**: a coordinated re-warm RESOLVED it — coherent 248→**594**, gun 10,
   unit-distinct-mrr-phones 256→**598**; the 248 was a warm-partial snapshot artifact, NOT a degrade.
   Receipts: post-rewarm unit lastMod 15:24:39Z / offer 15:30:58Z; band 725/3027 · 1355/4079 · gun 10 · coherent 594.
3. **Freeze fix**: `CLOCK-DOCTRINE-src-identity-carry` adopted — behavior-neutral deploys CONTINUE the
   soak (no restart, no re-game-day); only src-material deploys reset. Ends the 5-reset cycle.

## GO criteria at re-anchor (live, 2026-06-15)
| # | Criterion | Receipt | State |
|---|---|---|---|
| 1 | Substrate steady, both faces, floor | ECS :526/`6517f0b` PRIMARY COMPLETED, stable since 06-12T12:20Z (6h steady-states through 06-15T13:25Z); warmer `6517f0b`; floor 2048/8192 | **GREEN** |
| 2 | Src-identity carry | `git diff fa265ce1..6517f0b3` = test.yml only; src/Docker/deps/tests = 0 → rung carries, soak continues | **GREEN** |
| 3 | Band (post-coordinated-rewarm) | unit 725/3027 r=0.2395 · offer 1355/4079 · gun 10 · coherent **594** (≥561) | **GREEN** |
| 4 | Alarms armed | FastBurn/SlowBurn/HeartbeatAbsent all inactive | **GREEN** |
| 5 | SLI + AC-6 | up{job=asana}=1; AC-6 flowed ~1969/72h, zero 5xx over the blackout | **GREEN** |
| 6 | Rung (carried) | self-heal-game-day-proven + day-1-CORROBORATED + serve-proven — all carry by src-identity | **GREEN (carried)** |
| — | Days 1–3 contemporaneous attestation | **RECONSTRUCTED-only** (residual AMP/ECS/band; cron was dark) — eunomia accepts-or-scopes at clear | **AMBER (named)** |

## What the at-clear eunomia STRONG must weigh (carried into the ratified spec)
The days 1–3 reconstruction is residual, not contemporaneous — the RATIFIED-STRONG-DISPATCH-SPEC's
window-integrity clause must rule whether 4 contemporaneous days (06-15→06-19) + 3 reconstructed-clean
days satisfy the 7-day window, or whether the window scopes to the contemporaneous tail. This is the
honest cost of the blackout; it is named, not rounded over.

## Rung — never round up
**soak = RUNNING (MODERATE, hygiene-attested under operator ruling).** Substrate rung carries
(`self-heal-game-day-proven` + day-1-CORROBORATED + serve-proven). NOT soak-CLEARED (eunomia's, 06-19).
NOT telos-verified-realized.
