---
type: handoff
handoff_type: execution
status: proposed
source_rite: 10x-dev
target_rite: releaser
title: FPC Phase-2 cure cache-tier fix — LAND (re-PR → merge → deploy → re-warm → re-measure coherent≥100)
date: 2026-06-10
branch: cr3/fpc-phase2-cache-tier-fix
head: 2faaec5c   # pushed to origin; off origin/main 8affc80f
rung: tested      # NOT verified-live; NOT merged. coherent≥100 is the live receipt gated on this land.
evidence_grade: MODERATE   # self-ref ceiling; STRONG = eunomia rite-disjoint + the LIVE coherent≥100 receipt
---

# HANDOFF — 10x-dev → releaser — FPC Phase-2 cache-tier fix LAND

## What is ready (build complete, banked at `tested`)
- Branch **`cr3/fpc-phase2-cache-tier-fix`** @ **`2faaec5c`** (PUSHED to origin), cut from
  origin/main `8affc80f`. Scope: exactly 2 files (+542/-20) — `null_number_recovery.py`
  (the cure) + its test. Single commit, conventional subject, no Co-Authored-By.
- **The fix:** the cure now reads the **durable S3 per-task tier** (`asana-cache/tasks/<gid>/task.json`
  via `S3CacheProvider.get_versioned`, `EntryType.TASK`) for hot-store-miss gids — bounded-concurrency
  (`asyncio.Semaphore` cap=24, env `ASANA_CURE_COLD_CONCURRENCY`, clamped [1,64]). Zero new Asana GETs
  (S3 = durable cache). Resolves the root cause: the prod `unified_store` is **Redis-only** (no S3 cold
  tier; `cache/integration/factory.py:217-219`) + the resume warm leaves the hot store cold
  (`fetched_rows:0`), so the old `get_batch_async(IMMEDIATE)` missed all 3021.
- **Validation (tested rung):** broken-fixture RED→GREEN (cold hot-store + populated S3 → heals to exact
  cached value; reverting the hunk → RED — G-THEATER load-bearing); 174 builders-dir tests green; ruff
  clean; qa-adversary full matrix GREEN (never-fabricate/overwrite, not-N+1 = 1 read/distinct-gid,
  additive/never-raises, idempotent, envelope-handling) with the sole NO-GO (latency) now CURED:
  cold-read term ~375s → ~15.6s (N=3021, cap=24); total warm ≈541s/900s.

## LAND sequence (releaser execution — operator owns the gated levers)
1. **Open PR** base `main` ← `cr3/fpc-phase2-cache-tier-fix`. Verify `/files` = the 2 cure files only.
2. **CI-green** on the head sha (REST check-runs; GraphQL may 429). Rebase onto fresh main + re-CI if behind.
3. **[OPERATOR LEVER] squash-merge** — title: `fix(dataframes): heal null numeric cf cells from durable S3 per-task tier (cold-store cure)`.
4. **[OPERATOR LEVER] deploy** — autom8y `satellite-receiver.yml` (cross-repo). NOTE the known traps from
   the #119 land: ~30-min `satellite-deploy-asana` concurrency lock (a hung prior run blocks the new one;
   its 30-min timeout frees the lock); the `metrics-smoke-gate` reds the GHA job COSMETICALLY even on a
   healthy service — **judge deploy success by ECS task-def image tag advancing + rollout COMPLETED +
   1/1 healthy, NOT the GHA job color** (`a8 deploy` rolls ECS before the gate).
5. **[OPERATOR LEVER] re-warm** (force fresh): `aws lambda invoke --function-name autom8-asana-cache-warmer
   --region us-east-1 --invocation-type Event --cli-binary-format raw-in-base64-out
   --payload '{"resume_from_checkpoint":false,"strict":false}' /tmp/warm.json`.
6. **Re-measure** (the throughline DEPLOY node) — canonical coherence query (TDD §97-104) over fresh
   `dataframes/1201081073731555/unit/dataframe.parquet` + `…/1143843662099250/offer/dataframe.parquet`.

## Acceptance — verified-live (the receipts that fire the node)
- Warmer log `null_number_recovery_*` shows **`cold_present_gids > 0` AND `healed_cells > 0`** for unit
  (was `healed_cells:0, cache_miss_gids:3021`).
- `unit.mrr` populated ≈ **25–30% (~764 active)**, was 1/3021.
- Canonical query: **`coherent ≥ 100`**, `gun` collapses off 588 toward 0.
- `population_receipt_below_floor` WARN clears for the active unit subset (Phase-1 floor — do not regress).
- Template/inactive units STAY null (G-DENOM).

## Rungs (never round up)
`authored < tested(HERE) < CI-green < merged < deployed < verified-live(coherent≥100) < protecting-prod`.
This hands off at **tested**. MODERATE, self-ref ceiling. STRONG = eunomia rite-disjoint critic + the LIVE
`coherent≥100` receipt (both gated on this land).

## DEFER / watch-register
- **Residual integration risk (retired ONLY by the live receipt):** the tests use stand-ins
  (`_S3Backend`/`_ColdHotStore`), not the real `S3CacheProvider` against real S3. The cure resolves the
  cold backend from `S3Settings` defaults (bucket `autom8-s3`, prefix `asana-cache` — matches prod env).
  Real-backend resolution + payload shape are asserted by code-reading, PROVEN only by the deploy+re-warm
  `coherent≥100`. This is the design-altitude→deploy-empirical gap the node exists to close.
- **Option-2 (architect/operator):** prod `unified_store` is Redis-only; making S3 a first-class store
  READ tier (env `ASANA_CACHE_S3_ENABLED` + factory wiring) is a fleet-wide cache-topology change
  (every read path, write-through, promotion, single-worker SlowAPI budget) — NOT taken here; cure-side
  Option-1 is surgically scoped. Flag if the team wants the broader topology.
- `ASANA_CURE_COLD_CONCURRENCY` (default 24) — a warm-SLO knob; watch at deploy.
- UK-2 (#114 dtype-parity) · `metrics-smoke-gate` deploy-hang reliability (sre) · AC-6 · SEAM-2 monolith
  rebind · D-1 template-null integrity rests on the durable-WRITE path (in-code SCAR note; a future
  `/know` pass persists it to `.know/scar-tissue.md`).

## Reserved (operator only — surface, do NOT fire)
merge-to-main · autom8y deploy trigger · re-warm invoke · UK-2 · CR-3 Stage-B→Secret-2 · AC-6 cutover.
