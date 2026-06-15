---
type: decision
subtype: incident-surface
status: accepted   # RESOLVED 2026-06-15: all 3 rulings landed — (1) re-anchored :526 (IC-SOAK-REANCHOR-on-526), (2) band CLEARED via coordinated re-warm (coherent 248→594, warm-partial artifact), (3) CLOCK-DOCTRINE-src-identity-carry adopted. Caveat: durable sentinel cron requested but runtime reported session-only — see brief.
title: "INCIDENT — soak sentinel blackout (06-12→06-15) + #136 freeze-breach deploy reset the clock + a live band-coherence sub-floor anomaly; THREE operator rulings pending"
date: 2026-06-15
detected_by: hygiene-rite /consult PV re-derivation across a multi-day session interruption (the sentinel cron was session-bound and died — the exact caveat flagged at arming)
evidence_grade: STRONG (live receipts, this hour) for the findings; the rulings are operator-reserved
---

# INCIDENT — three findings, three operator rulings

## Finding 1 — the clock was RESET on 06-12, ~4h after it was anchored (and nobody caught it)
- The co-signed anchor: 2026-06-12T09:02:05Z on `:516`/`fa265ce`.
- **#136** `ci(test): bump reusable pin to c824da59` merged to asana main during the freeze →
  Satellite Dispatch → ECS **`:526`/image `6517f0b`** registered 2026-06-12T13:10:52Z, steady ~13:20Z.
  Live now: main = **`6517f0b3`** (≠ the expected `fa265ce1`); ECS sole `:526`/`6517f0b` COMPLETED;
  warmer `6517f0b`; floor 2048/8192 held.
- Per the reset law (new task-def mid-window = new soak), **the 09:02:05Z anchor is VOID** — and it
  lived only ~4 hours. The task-def chain `:516→:525` were all `fa265ce` rerolls; `:526` is the
  `6517f0b` deploy; stable since (ECS steady-states every 6h on `:526` through 06-15T13:25Z — no
  further motion).

### The rung CARRIES (src-identity, the established carry rule — 5th application)
`git diff fa265ce1..6517f0b3` = **exactly 1 file: `.github/workflows/test.yml`** (a reusable-pin
bump); `src/ Dockerfile pyproject.toml tests/` = 0, uv.lock = 0. `6517f0b` is byte-identical
application source to `fa265ce1`. `self-heal-game-day-proven` + day-1-CORROBORATED + serve-path-proven
all carry. No fresh game-day is owed for a re-anchor.

## Finding 2 — the sentinel went DARK 06-12→06-15 (the session-bound cron died)
Only `SOAK-DAY-1-ATTESTATION-telos-soak-2026-06-11.md` exists (and it is the PRE-reset day-1). The
re-based window's days 1–3 (06-12/13/14) were **never attested** — the cron (82be5eef) was
session-bound and died across the interruption, exactly as flagged at arming. **Consequence:** the
#136 reset slipped through unattested; the window-integrity discipline had no daily check for ~3 days.

### Plane health across the blackout — reconstructed CLEAN (residual evidence, not contemporaneous)
- **Zero 5xx over 72h**: `sum(increase(autom8y_asana_receiver_query_outcome_total{outcome="server_error"}[72h]))` → no series.
- **AC-6 flowed**: ~1969 outcomes over 72h, 15/25 3h-buckets with traffic, no dark stretch; up{job=asana}=1.
- **Alarms**: FastBurn/SlowBurn/HeartbeatAbsent all `inactive` (armed-not-firing) now.
- Caveat: this is RESIDUAL reconstruction (AMP range + ECS events + current band) — NOT the
  contemporaneous daily parquet-count attestation the protocol specifies. Days 1–3 cannot be made
  contemporaneous after the fact.

## Finding 3 — a LIVE band-coherence sub-floor anomaly (the ratio floor masks it)
Band NOW (06-15, both parquets fresh: unit lastMod 12:36Z, offer 13:07Z — 31 min apart, freshness-skew RULED OUT):
- unit.mrr **725/3027 ratio 0.2395** (ratio floor ≥0.20 PASS) · offer.mrr **1332/4079** (PASS) — both match the arc at row level.
- **coherent = 248 (floor ≥561) — FAIL · gun = 2.** Unprecedented in the arc (every prior reading 561–593).
- Overlap diagnostic: unit nonnull-phones=721, offer=2083, shared-any=688 (high — NOT a key skew);
  binding cause = **unit mrr concentrated in 256 distinct office_phones** (vs the ~581 the arc always showed).
  Same ~725 mrr rows, same ratio, **different distribution** → the row-ratio floor would have rubber-stamped
  GREEN; the coherence floor caught a real distributional shift it masks (content-not-log at the band layer).
- **NOT RULED**: cannot distinguish {underlying-Asana-data-shift over 3 days | warm-partial-mid-cadence |
  a genuine unit-mrr-breadth regression} without a coordinated unit+offer re-warm + re-measure. The cure
  (unit mrr population) IS the soak subject, so this gates a clean re-anchor until disambiguated.

## THREE RULINGS PENDING (operator-reserved — surfaced, not ruled)
1. **Reset / re-anchor**: the clock is VOID (Finding 1). Re-anchor target + whether to bank the ~3 days
   of de-facto `:526` stability (reconstructed) or restart contemporaneous from now.
2. **Band anomaly disposition** (Finding 3): disambiguate before re-anchor (coordinated re-warm + re-measure)
   vs accept-as-data-shift vs treat-as-degrade → route to 10x-dev.
3. **Freeze enforcement** (Finding 2 mechanism): #136 breached a CONVENTION freeze. Enforce hard
   (branch protection / disable auto-propagation to asana during soak) vs adopt the src-identity-carry
   rule as a STANDING clock doctrine (behavior-neutral deploys re-anchor-but-carry, never reset to zero;
   only src-material deploys reset) — the latter ends the brittle "every CI churn resets" cycle (5 resets so far).
   Plus: the sentinel must move off session-bound to durable.
