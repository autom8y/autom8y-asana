---
type: decision
status: proposed
title: "ADR — Cure-Recovery-Path Hardening: Fail-Closed Write + Quality-Aware Freshness"
slug: cure-recovery-path-hardening
date: 2026-06-11
rite: 10x-dev
author: architect
evidence_grade: MODERATE  # self-rite authorship ceiling per self-ref-evidence-grade-rule
substrate_head: b48452d
related_tdd: .ledge/specs/TDD-cure-recovery-path-hardening-2026-06-11.md
chaos_receipt: .ledge/reviews/SRE-IGNITION-MATRIX-realization-tail-2026-06-11.md
supersedes: none
---

# ADR — Cure-Recovery-Path Hardening

## Status

PROPOSED — DESIGN-ONLY. Implementation HELD: the deploy that makes this live RESETS the
running telos-soak (anchored 2026-06-11T08:41Z, clear ~2026-06-18). Ship soak-clear-gated.

## Context

The FPC Phase-2 `null_number_recovery` cure (at deployed head `b48452d`,
`src/autom8_asana/dataframes/builders/null_number_recovery.py:251`) backfills null numeric
custom-field cells from the durable per-task S3 cache during a warm. A chaos drill (EXP-1,
2026-06-11, `.ledge/reviews/SRE-IGNITION-MATRIX-realization-tail-2026-06-11.md` §4) revoked the
warmer's `S3DurableTaskCacheRead` IAM grant and surfaced two latent resilience gaps in the
cure-failure / recovery path:

1. **Write-not-fail-closed.** Under the revoked grant the warm rebuilt the unit frame from source
   and PERSISTED it null-degraded (`dataframe.parquet` mrr_nonnull 0/3021, down from 723/3021)
   instead of fail-closing to preserve the prior-good frame. The population floor WARNed (LOUD —
   honest), but a consumer reading in the gap gets nulls.
2. **Freshness-skip blocks auto-recovery.** After grant restore, the next warm refreshed
   `manifest.json` but freshness-skipped the dataframe rebuild (parquet watermark < the age
   ceiling), so the degraded frame did NOT self-heal until forced. Freshness keys on AGE, not data
   QUALITY.

Re-derived code anchors (all `@ b48452d`, default-to-REFUTED, code-is-truth):

- Write gate UNCONDITIONAL after recovery: `dataframes/builders/progressive.py:863-871` — gate is
  `if total_rows > 0 or honest_complete_empty:` with NO quality term; recovery receipt discarded as
  `_recovery_receipt` (`:812`); population receipt return value discarded (`:834`).
- Freshness predicate AGE-keyed: `metrics/freshness.py:173-179` `FreshnessReport.stale =
  max_age_seconds > threshold_seconds`; ceiling `config.py:219` project=86400/section=3000.
- Quality SSOT: `post_build_population_receipt.py:54` `POPULATION_WARN_THRESHOLD=0.80`; `:69`
  `"unit": ("mrr",)`; `:219` `below_floor`; active-subset filter `:101-126` (G-DENOM-clean).
- Carrier: `build_result.py:265 class BuildQuality` — carries section-outcome status only, NO
  null-population field today (INVERTS the prompt's `build_quality`-as-ready-carrier hypothesis).
- boto3 boundary: `cache/durable_task_cache.py:221` `client.get_object`; AccessDenied → raises
  (`:240`) → `_one` maps to None + WARN (`:296`). SOLE `to_thread` site (FROZEN-4 allowlist).

PV inversion of note: the cure does NOT exist on the active branch HEAD `3bbb9bc8`
(`cr3/gate2-receiver-probe-and-durability`); it lives at the certified/deployed head `b48452d`.
This ADR designs against `b48452d`.

## Decision

Adopt a **coherent pair** of fixes sharing one seam — a new
`BuildQuality.population_degraded` flag derived from the population-floor SSOT (the existing,
discarded `PopulationReceipt.below_floor`).

**FORK-1 (fail-closed write): preserve-prior-good (1a) + merge-prior-good cold-start fallback (1c).**
When the floor breaches AND the cure healed nothing from cache, do NOT overwrite a strictly-better
prior-good frame; when only partial prior-good exists, coalesce its higher-population value cells in
before writing; when no prior-good exists (cold start), write the honest-null frame (preserving the
honest-empty-200 invariant). The DEGRADED stamp (1b) is retained as a secondary observability signal
and as Fork-2's trigger, NOT as the primary gap fix. Hard-failing the build (1d) is REJECTED.

**FORK-2 (quality-aware freshness): floor-breach → not-fresh → rebuild (2a), persisted via the
`population_degraded` stamp (2b).** The rebuild decision becomes
`needs_rebuild = stale_by_age OR (population_degraded AND grant_now_healthy)`. `FreshnessReport.stale`
stays a pure age signal; the quality term lives in the warmer/consumer rebuild gate. A shorter
degraded-age ceiling (2c) and always-rebuild (2d) are REJECTED.

**Composition:** Fork-1 SETS `population_degraded` at write-time; Fork-2 READS it at next-warm-time.
Fork-1(a) preserve-prior-good moots Fork-2 for the common unit case (the prior-good frame is not
below-floor, so it is not stamped → no re-warm storm); Fork-2 does load-bearing work only in the
`WRITE_COALESCED` / cold-start paths where a degraded-or-partial frame persisted. The
`grant_now_healthy` conjunct suppresses a rebuild storm while the grant is still revoked.

**Coherent-pair invariant:** after any durable-read outage, the persisted frame is never strictly
worse in active-subset population than the prior-good frame (Fork-1), AND any below-floor frame
rebuilds on the next healthy warm (Fork-2). Degrade SAFELY; self-heal DETERMINISTICALLY.

## Alternatives Considered

See TDD §3 for the full option tables. Summary of rejected paths:

- **1(b) write-but-mark-DEGRADED as the sole fix** — REJECTED: serves nulls in the gap and requires
  a reader-side change that risks the live offer read path (PV-OFFER-INTACT). Adopted as a secondary
  signal only.
- **1(d) hard-fail the build** — REJECTED: violates the floor's load-bearing WARN-first contract
  (`post_build_population_receipt.py:17` "NEVER changes build status") and regresses
  "degraded-but-present beats empty"; 503-trap risk.
- **2(c) shorter max-DEGRADED-age** — REJECTED: still age-keyed; does not guarantee ≤1-cycle re-heal
  (NFR-2), only shrinks the blind-spot window.
- **2(d) always rebuild** — REJECTED: removes the load-bearing build-pressure relief valve; storms
  the single-worker warmer.

## Consequences

**Positive:**
- A durable-read outage degrades to the LAST-GOOD frame; consumers in the gap see prior-good, not nulls.
- A below-floor frame deterministically self-heals on the next healthy warm (no manual force, no
  staleness-window wait).
- The fix derives entirely from the existing population-floor SSOT — no new threshold, no orphan
  per-builder flag (G-PROPAGATE).
- Fires only on a real active-subset floor-breach (G-DENOM); zero false re-warm for legitimately-sparse
  / inactive-null / cold-start frames.

**Negative / cost:**
- One additional best-effort S3 read (prior-good frame) on the warm path; failure degrades to
  WRITE_AS_IS (never blocks a write).
- One new field on `BuildQuality` and one new pure helper module (`fail_closed_write.py`); the
  persisted `population_degraded` must survive into the next warm's freshness consult.

**Reversibility — TWO-WAY DOOR.** `population_degraded` defaults False; the rebuild term is additive
(`OR`); the write decision degrades to `WRITE_AS_IS` on any uncertainty. Revert = drop the field and
the two added terms. No schema migration, no public API change, no infrastructure commitment.

**Deploy reversibility caveat — SOAK INTERACTION.** The deploy that makes this live resets the
running telos-soak. This is operational sequencing (ship after soak clear ~2026-06-18), not a
code-reversibility concern. Stakeholder acknowledgment required before implementation begins
(G-RUNG: ceiling = authored).

## Hard-Gate Attestation

- **G-PROVE:** every anchor re-derived with pasted file:line @ b48452d (TDD §0); two PV inversions named.
- **G-PROPAGATE:** both forks derive from `PopulationReceipt.below_floor` (the SSOT at
  `post_build_population_receipt.py:219`); no orphan flag.
- **G-DENOM:** fail-closed and rebuild fire on the ACTIVE-subset breach the floor already computes
  (`:101-126`); never blanket "any null → rebuild".
- **G-RUNG:** ceiling = authored (TDD + ADR); deploy soak-clear-gated; no src/tests written, no commits.
- **@option-enumeration-discipline:** four options per fork enumerated exhaustively before recommend
  (TDD §3).

Evidence grade: MODERATE (self-rite authorship ceiling).
