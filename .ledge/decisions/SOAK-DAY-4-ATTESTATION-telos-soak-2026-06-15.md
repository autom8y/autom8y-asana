---
type: decision
subtype: soak-attestation
status: accepted
title: "SOAK DAY 4/7 ATTESTATION (2026-06-15) — first CONTEMPORANEOUS record on the :526 re-anchor; band-clear receipt; days 1–3 reconstructed"
date: 2026-06-15
clock_state: RUNNING
anchor_utc: 2026-06-12T12:20:25Z
target_clear_utc: 2026-06-19T12:20:25Z
day_n: 4
evidence_grade: MODERATE
governing_record: .ledge/decisions/IC-SOAK-REANCHOR-on-526-src-identity-carry-2026-06-15.md
---

# SOAK DAY 4/7 — 2026-06-15 (first contemporaneous attestation on the re-anchored clock)

## (a) Deploy-freeze + src-identity classification
- asana main = `6517f0b3` (the anchor source). ECS sole `:526`/`6517f0b` COMPLETED, stable since
  06-12T12:20Z (6h steady-states through 06-15T13:25Z — no task-def motion). Warmer `6517f0b`. Floor 2048/8192.
- Src-identity: main UNMOVED since the anchor; no new deploy this day. **GREEN.**
- (Doctrine now live: a future behavior-neutral deploy CONTINUES the clock; only src-material resets — `CLOCK-DOCTRINE-src-identity-carry`.)

## (b) Band content (parquet counts, post-coordinated-rewarm)
- unit.mrr **725/3027** ratio **0.2395** (≥0.20 ✓) · offer.mrr **1355/4079** (1332-class ✓) · gun **10** (≤15 ✓) · coherent **594** (≥561 ✓). **GREEN.**
- Freshness: unit lastMod 15:24:39Z, offer 15:30:58Z (coordinated re-warm this day).
- **Band-anomaly note (resolved):** an earlier single-snapshot read this day showed coherent=248
  (unit mrr transiently in 256 phones) — a WARM-PARTIAL artifact, NOT a degrade; a coordinated
  re-warm restored coherent to 594 / unit-distinct-mrr-phones to 598. The disambiguation method
  (re-warm + re-measure) is now baked into the sentinel protocol's section (b).

## (c) Alarm states
- `slo_asana_receiver_alerts`: AsanaReceiverAvailabilityFastBurn / SlowBurn / HeartbeatAbsent — all **inactive** (armed-not-firing). **GREEN.**

## (d) AC-6 cadence
- `up{job=asana}` = 1 (ip-10-0-144-178). AC-6 organic traffic flowed over the prior 72h (~1969 outcomes,
  15/25 3h-buckets with traffic, no dark stretch); **zero `outcome=server_error` over 72h** (no 5xx). **GREEN.**

## Days 1–3 (06-12/13/14) — RECONSTRUCTED-clean, NOT contemporaneous (AMBER, named)
The sentinel cron was session-bound and died across a multi-day interruption; days 1–3 have NO
contemporaneous parquet-count attestation. Residual reconstruction (this day's PV re-derivation):
zero 5xx over the window, AC-6 flowed, alarms never fired, substrate stable on `:526`. Clean by
residual evidence — but the at-clear eunomia STRONG must rule whether 4 contemporaneous + 3
reconstructed days satisfy the 7-day window or scope to the contemporaneous tail (carried to the
RATIFIED-STRONG-DISPATCH-SPEC window-integrity clause).

## Verdict
**Day 4/7: GREEN (4 sections) + AMBER (days 1–3 reconstruction, named).** No RESET-candidate live.
Clock RUNNING on `:526`, ~3 days to clear (06-19T12:20:25Z). Rung: soak-RUNNING (carried).
