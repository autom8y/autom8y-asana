---
type: decision
subtype: ic-soak-ignition
status: accepted
title: "TELOS-SOAK IGNITED — 7-day clock RUNNING (dataframe-resolution-coherence five-signal)"
date: 2026-06-11
clock_state: RUNNING
anchor_utc: 2026-06-11T08:41:12Z   # clean-plane-confirmed moment (all GO criteria simultaneously GREEN, EXP-1 side-effect rolled back)
target_clear_utc: 2026-06-18T08:41:12Z   # +7 clean days
soak_subject: telos dataframe-resolution-coherence — five-signal verified_realized of the CONVERGED plane
evidence_grade: MODERATE   # sre self-attest ceiling; soak-CLEARED STRONG is eunomia's (rite-disjoint, simultaneous five-signal) at the next seam
supersedes: .ledge/decisions/IC-SOAK-READINESS-telos-soak-2026-06-10.md   # the readiness checklist (clock NOT-STARTED) → now IGNITED
---

# IC SOAK IGNITION — the telos-soak clock is RUNNING

> 🔄 **SUPERSEDED 2026-06-11** by
> `IC-SOAK-REANCHOR-telos-soak-RUNNING-2026-06-11.md` — the clock is RE-ANCHORED to
> **2026-06-11T15:24:21Z** on `:511`/`49099b1` (src-identical to the game-day-proven `3a59c72`)
> after the re-game-day passed by CONTENT at both altitudes and an iris live-HTTP smoke proved
> the serve path + AC-6 pipe (clear target 2026-06-18T15:24:21Z). Retained for lineage only.

> ⚠️ **CORRECTION 2026-06-11 (10x-dev PV gate):** the **08:41:12Z anchor below is VOID** — the
> #126 (`:508`/`bafd250`) deploy reached steady-state 08:42:52Z, ~100s after it, resetting the soak.
> `:508` is behavior-neutral (γ-0 annotation) and the band holds (coherent=564/gun=14), so the
> convergence is continuous; **re-anchor to 2026-06-11T08:42:52Z** pending operator/IC GO-criteria
> re-confirm on `:508`. See `CORRECTION-soak-anchor-raced-by-126-deploy-2026-06-11.md`.

> Anchored to the **clean-plane-confirmed moment 2026-06-11T08:41:12Z** — the instant every GO
> criterion held simultaneously AND the EXP-1 chaos side-effect was rolled back. The 7-day window
> targets **2026-06-18T08:41:12Z**. This procession's ceiling is **soak-RUNNING**; soak-CLEARED and
> the telos five-signal verified-realized are the next seam's, attested rite-disjoint by eunomia.

## GO criteria — ALL GREEN at anchor (falsifiable, receipted)
| # | Criterion | Receipt | State |
|---|---|---|---|
| 1 | AC-6 lit (counter flowing, ≥6h) | `receiver_query_outcome_total` 6h=409 / 1h=107; 5-signal bilateral PASS (monolith satellite arm + SM-fetch + SA-pairing + 1947×200/24h + zero fallback) | **GREEN** |
| 2 | #486 applied + must-arm armed | `slo_asana_receiver_alerts` ACTIVE in AMP; FastBurn+SlowBurn+HeartbeatAbsent materialized | **GREEN** |
| 3 | dead-man breaching-on-absence + drill-proven | `AsanaReceiverHeartbeatAbsent`=`absent()`; drill 07:51:25Z → SNS publish +1 → `autom8-slack-alert` invoked → cleared | **GREEN** |
| 4 | deploy proven-in-anger | runs 27293754687 + 27312946195 success ≤20min, no 30-min lock hang | **GREEN** |
| 5 | SLI affirmative | `up{job=asana}=1`; business denominator 107/1h (not OK-on-absence) | **GREEN** |
| 6 | stability holding | 3-warm series + today's band bit-identical (unit 723/3021, offer 1332/4079) | **GREEN** |
| 7 | plane clean (EXP-1 side-effect rolled back) | unit frame restored 3021/723/719/335 @ 08:41:12Z; coherence 578≥100, gun=19 bounded | **GREEN** |
| — | S5 eunomia attester (simultaneous five-signal) | **coordination precondition — the next-seam STRONG instrument** (sre caps at MODERATE) | reserved |

## The five-signal observation plan (per the readiness checklist §2 — unchanged)
S1 active_mrr denominator stable (62/$79,485, no collapse) · S2 ad_reporting offer-entity (SEAM-2-gated,
DEFERRED-NOT-OBSERVED) · S3 payments/mrr denominator congruent (SEAM-2-gated, DEFERRED) · S4 population
WARN absent in steady-state — **NOTE: the unit-mrr floor WARNs perpetually at the sold band (~0.237 vs
0.8), a NAMED calibration exception (UK-2/FPC-Phase-3), NOT a reset trigger** · S5 eunomia simultaneous
re-derivation (the attester — next seam).

## What RESETS the clock vs LOGS (per readiness §3, with the EXP-1-informed addition)
RESET: active_mrr collapse (62→~7) · `receiver_query_outcome_total` goes absent mid-window · burn-rate
SLO ALARM under real traffic · SLI dark mid-window · a deploy mid-window (new task-def = new soak) ·
**a degraded frame PERSISTS unhealed past one staleness window (the EXP-1 finding — auto-recovery is
NOT guaranteed; watch for it)**.
LOG (investigate, not reset): the named unit-floor calibration WARN · UK-2 drift-cell surfacing ·
β-3 canary signals · S2/S3 SEAM-2 deferred-not-observed.

## Dead-man watch + halt/rollback runbook (registered)
- **Heartbeat dead-man**: `AsanaReceiverHeartbeatAbsent` (AMP, 10m `absent()`) → SNS → Slack (route drill-proven).
- **Burn-rate**: FastBurn (1h&5m >14.4) / SlowBurn (6h&30m >6) → same route.
- **Rollbacks staged**: β-3 ECS policy (`/tmp/ign-receipts/beta3-rollback-task-s3-fullbucket.json`, sha `730841e1`); β-1/β-2 warmer policies (`/tmp/ign-receipts/pre-*.json`); EXP-1 grant already restored.

## Rung — never round up
**soak = RUNNING (MODERATE, sre-attested).** NOT soak-CLEARED. The telos five-signal
(SEAM-2 consumers, AC-6-sustained-7d, valid-soak-clear, fallback-flip) is **NOT verified-realized** —
the next seam's, attested by eunomia observing the live five-signal simultaneously.
