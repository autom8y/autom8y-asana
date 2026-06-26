---
type: decision
subtype: ic-soak-ignition
status: accepted
title: "TELOS-SOAK RE-ANCHORED — 7-day clock RUNNING on :511 (hardened substrate; game-day content-proven at BOTH altitudes; serve-path + AC-6-pipe live-HTTP-proven)"
date: 2026-06-11
clock_state: RUNNING
anchor_utc: 2026-06-11T15:24:21Z   # :511 deploy steady-state — the last GO-criterion to become true; all criteria receipted at/after this moment with nothing resetting since
target_clear_utc: 2026-06-18T15:24:21Z   # +7 clean days
substrate: ECS :511 / image 49099b1 (BOTH faces) — src-IDENTICAL to the game-day-proven 3a59c72 (#129 was .github/-only: 6 files +6/−6; src/, Dockerfile, pyproject, uv.lock, tests/ zero-diff)
soak_subject: telos dataframe-resolution-coherence — five-signal verified_realized of the CONVERGED + RECOVERY-HARDENED plane
evidence_grade: MODERATE   # releaser self-attest ceiling (delegated IC co-sign per the operator Meta-Grant, "Keystone Release" procession); soak-CLEARED STRONG is eunomia's (rite-disjoint, simultaneous five-signal) at the next seam
authorized_by: operator Meta-Grant 2026-06-11 (cross-rite-handoff --to=releaser — soak re-anchor co-sign explicitly delegated)
supersedes:
  - .ledge/decisions/IC-SOAK-IGNITION-telos-soak-RUNNING-2026-06-11.md   # 08:41:12Z anchor (VOID — raced by #126)
  - .ledge/decisions/CORRECTION-soak-anchor-raced-by-126-deploy-2026-06-11.md   # 08:42:52Z proposal (mooted by #127/#128)
---

# IC SOAK RE-ANCHOR — the telos-soak clock is RUNNING on :511

> Anchored to **2026-06-11T15:24:21Z** — the `:511` deploy steady-state moment, on a substrate
> src-identical to the one that passed the game-day EXP-1 **by CONTENT at BOTH altitudes** with
> zero restore interventions, with the serve path and AC-6 metric pipe additionally proven by a
> live-HTTP smoke. The 7-day window targets **2026-06-18T15:24:21Z**. This procession's ceiling is
> **soak-RUNNING**; soak-CLEARED and the telos five-signal verified-realized belong to the next
> seam, attested rite-disjoint by eunomia.

## Anchor lineage (never rounded up — every void named)
1. **08:41:12Z** (IC-SOAK-IGNITION) — VOID: raced ~100s later by the #126 `:508` deploy.
2. **08:42:52Z** (CORRECTION, proposed) — never confirmed; mooted by #127 `:509` (whose game-day went
   RED: PRESERVE decided-not-enforced on the warmer path) and #128 `:510` (the cure).
3. **14:59:07Z on `:510`** (this procession's first re-anchor) — lived ~16 minutes: RACED by the
   `:511` deploy that this procession's OWN clock-debt station fired (asana#129 → Satellite Dispatch;
   "DAG-independent ≠ deploy-independent" — any merge to the satellite's main IS the deploy trigger).
   Caught at the G-PREMISE re-check before any soak-RUNNING claim was published. The game-day rung
   CARRIES to `:511` by src-identity proof (below); only the anchor moved.
4. **15:24:21Z on `:511`** — THIS anchor.

## Src-identity carry (why the game-day rung holds on :511 without a re-run)
`git diff 3a59c72c..49099b12` = exactly 6 files, all `.github/workflows/*` (+6/−6, action-pin bumps);
`src/ Dockerfile pyproject.toml uv.lock tests/` diff-count = **0**. The `:511` image is built from
byte-identical application source → `self-heal-game-day-proven` carries by src-diff proof (the
γ-0/#126 behavior-neutral-deploy precedent).

## GO criteria — ALL GREEN at anchor (falsifiable, receipted live this hour)
| # | Criterion | Receipt | State |
|---|---|---|---|
| 1 | Deploy steady-state, hardened substrate, both faces | ECS `:511` rolloutState=COMPLETED 15:24:21Z (1/1, failed=0); image `49099b1` BOTH faces (ECS task-def :511 + warmer ImageUri, LastUpdateStatus=Successful); floor cpu=2048/mem=8192; deploy run 27356864645 (Metrics-Smoke tail cosmetic per the deploy-judgment law) | **GREEN** |
| 2 | #486 must-arm pair + dead-man armed | AMP `/rules`: `slo_asana_receiver_alerts` → AsanaReceiverAvailabilityFastBurn / SlowBurn / HeartbeatAbsent present, state `inactive` (armed, not firing) | **GREEN** |
| 3 | SLI affirmative | `up{job="asana"}==1` on the `:511` task (ip-10-0-138-103) | **GREEN** |
| 4 | AC-6 counter pipe PROVEN live (the iris disambiguation) | live-HTTP smoke 15:40–15:56Z: `autom8y_asana_receiver_query_outcome_total` EMPTY→**1284**, +468/5m, monotonic ~+100/min tracking the project arm 1:1; **zero `outcome=server_error` series**. The missed organic bursts (14:30Z/15:30Z) are a **monolith-side cadence gap** → DEFER-watch, not a receiver defect | **GREEN** (pipe) / **WATCH** (organic cadence) |
| 5 | Self-heal game-day PROVEN (carried by src-identity) | EXP-1 on `:510` (receipts below) + src-identity proof | **GREEN** |
| 6 | Serve path proven at the REAL HTTP altitude | iris smoke: project arm **993/993** 2xx over the full 10-min GATE-2 window @100rpm, content contract 100%, zero 5xx, zero 429, p99 703ms; section 400s = honest `MISSING_SECTION_SELECTOR` refusals (canary PQ-5 degenerate case by design) | **GREEN** |
| 7 | Plane clean + band in-band at anchor | band on `:511` frames @15:26Z: unit.mrr **724/3027** (23.9% sold band) · offer **1332/4079** · gun **9** · coherent **581** (inside the certified 579–592); fresh frame 15:22:35Z = the `:511` task's startup preload, clean build (zero `fail_closed` events) | **GREEN** |
| — | S5 eunomia attester (simultaneous five-signal) | coordination precondition — next-seam STRONG instrument (releaser caps at MODERATE) | reserved |

## The game-day receipts (EXP-1 on :510 — the acceptance this anchor stands on)
- **Prior-good captured FIRST**: unit parquet etag `e4317556e0b479abd41163e658ed7f30` (168,087 B, 14:05:41Z), content 723/3021; live 4-Sid warmer policy captured pre-revoke.
- **Inject 14:37:05Z**: `S3DurableTaskCacheRead` stripped from `autom8-asana-cache-warmer-lambda-role` inline policy `autom8-asana-cache-warmer-s3-cache` (ONE lane; revoke doc derived from the LIVE capture).
- **Fault warm** (`c33d9b8d`, 14:37:27→14:50:55): **3,021/3,021** `durable_task_cache_read_gid_failed` AccessDenied (wholesale outage, LOUD, per-gid).
- **Decision AND enforcement** (the #127 RED inverted): `fail_closed_write_preserve_prior_good` @14:45:25.241Z + `fail_closed_write_preserve_prior_good_enforced` @14:45:25.242Z (`converged_gate_skipped_save_dataframe_at_write_site`); `final_artifacts_written` in the fault window: **ZERO** (the morning RED wrote the degraded parquet 243ms after deciding PRESERVE).
- **CONTENT under fault — disk**: unit parquet **byte-identical** (etag unchanged), 723/3021; offer untouched.
- **CONTENT under fault — serve**: `get_async` through the converged `_memory_get_serviceable` (deployed code, live S3) → **723/3021**. The PRESERVE log was corroborating color only.
- **Restore 14:49:33Z** (finally-discipline): exact captured 4-Sid doc; verified.
- **Fork-2 re-heal**: post-restore warm (`9a3ea3d1`) wrote a fresh healthy frame 14:59:07Z (etag `d377283d`): disk 723/3021, serve 723/3021, band bit-exact.
- **Zero interventions**: no prior-good restore needed — the plane was never dirtied.

## The five-signal observation plan (unchanged)
S1 active_mrr denominator stable (62/$79,485) · S2 ad_reporting offer-entity (SEAM-2-gated, DEFERRED-NOT-OBSERVED)
· S3 payments/mrr congruent (SEAM-2-gated) · S4 population WARN absent — the unit-mrr floor WARNs perpetually
at the sold band (~0.239 vs 0.8), a NAMED calibration exception (UK-2/FPC-Phase-3), NOT a reset trigger ·
S5 eunomia simultaneous re-derivation (next seam).

## What RESETS vs LOGS (carried, with the new watch)
RESET: active_mrr collapse (62→~7) · `autom8y_asana_receiver_query_outcome_total` goes absent mid-window
**with the pipe proven dark under traffic** (the iris disambiguation method: smoke it — pipe-dark = RESET-grade;
monolith-cadence-gap = LOG/WATCH) · burn-rate SLO ALARM under real traffic · SLI dark mid-window · **a deploy
mid-window (new task-def = new soak; bit THREE times today)** · a degraded frame PERSISTS unhealed past one
staleness window.
LOG (investigate, not reset): the named unit-floor calibration WARN · UK-2 drift-cells · β-3 canary signals ·
S2/S3 SEAM-2 deferred-not-observed · **the monolith organic-burst cadence gap (last burst 13:30Z=104.9; pipe
proven healthy; if no organic burst resumes within 24h → cross-repo investigation of the monolith satellite arm)**.

## Dead-man watch + rollback runbook (registered)
- **Heartbeat dead-man**: `AsanaReceiverHeartbeatAbsent` (AMP `absent()`) → SNS → Slack (drill-proven 07:51Z).
- **Burn-rate**: FastBurn / SlowBurn → same route.
- **Rollbacks staged**: prior task-defs `:510`/`3a59c72` and `:509`/`7973c10`; β-3 policy rollback sha `730841e1`;
  warmer 4-Sid policy capture `/tmp/key-r2/policy_live_pre.json`; prior-good frame `/tmp/key-r2/unit_priorgood.parquet`.

## Rung — never round up
**soak = RUNNING (MODERATE, releaser-attested under delegated IC co-sign).** Substrate rung:
`self-heal-game-day-proven` (carried to `:511` by src-identity) **+ serve-path live-HTTP-proven (iris)**.
NOT soak-CLEARED. The telos five-signal (SEAM-2 consumers, AC-6-sustained-7d, valid-soak-clear,
fallback-flip) is **NOT verified-realized** — the next seam's, attested by eunomia.
