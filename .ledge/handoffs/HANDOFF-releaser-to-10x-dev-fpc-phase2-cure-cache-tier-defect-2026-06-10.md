---
type: handoff
handoff_type: implementation
status: accepted
source_rite: releaser
target_rite: 10x-dev
title: FPC Phase-2 Cure — cache-tier read defect (cure deployed but inert)
date: 2026-06-10
origin_head: 8affc80f16ccdbe0bd8c0b4a393a4728e7a8a151   # #119 cure, MERGED + DEPLOYED (:501)
evidence_grade: MODERATE   # self-ref ceiling; STRONG = eunomia rite-disjoint (HELD)
---

# HANDOFF — releaser → 10x-dev — FPC Phase-2 Cure cache-tier defect

## What landed (banked, receipts)
- #119 FPC Phase-2 cure **MERGED** (`8affc80f`) + **DEPLOYED**: ECS task-def `:501`,
  image `8affc80`, rollout COMPLETED 09:03:07Z, 1/1 healthy. Warmer Lambda
  `autom8-asana-cache-warmer` on cure image (LastModified 08:54:38Z).
- Re-warm fired (`resume_from_checkpoint:false`); business+unit+… warmed.

## The defect (deploy-empirical FALSIFICATION of the cure)
The throughline DEPLOY node did **NOT** fire. Live canonical coherence query over
post-deploy frames (`dataframes/1201081073731555/unit/` + `…/1143843662099250/offer/`):
- `unit.mrr 1/3021` (should be ~25–30% / ~764 active), `offer.mrr 1356/4080` (correct).
- `gun=588`, **`coherent=1`** (baseline `gun=571, coherent=0` — essentially unmoved).

Cure telemetry (warmer log, invocation `86f7dd84`):
```
null_number_recovery_no_op: unit  null_cells_before:9063  healed_cells:0  cache_miss_gids:3021
build_result_classified: unit  fetched_rows:0   (pure resume from persisted sections)
population_receipt_below_floor: active_rows 764, mrr nonnull 0.0   (Phase-1 floor WARNED — vindicated)
```

## Root cause (code, not data; live-verified)
The cure reads `store.get_batch_async(freshness=IMMEDIATE, required_level=STANDARD)`
(`null_number_recovery.py:242-246`) = hot-tier-only. On the steady-state warm the
build is `resume=True` and re-fetches **0 tasks**, so `unified_store`'s hot memory is
**cold** → all 3021 gids miss. The cure's premise ("the just-warmed copy IS the
post-warm") assumes a full fetch populated the hot store; the resume path never does.

The data the cure needs **exists in a reachable durable tier**:
`s3://autom8-s3/asana-cache/tasks/<gid>/task.json` carries `MRR` `number_value`
(sampled 4/4 active = 1500). BUT the store's S3 **cold tier is DISABLED**:
`ASANA_CACHE_S3_ENABLED` is **unset** on both the warmer Lambda and ECS `:501`
(`TieredConfig.s3_enabled` defaults False; `tiered.get()` "checks hot tier only").
So the cure can never reach the populated S3 copies.

## Load-bearing premises (default-to-REFUTED; re-verify LIVE before mutation)
| id | premise |
|---|---|
| PV-DEFECT | cure `get_batch_async(IMMEDIATE,STANDARD)` is hot-only; cold on resume warm → `cache_miss_gids:3021` → heals 0 |
| PV-DATA-CACHED | `asana-cache/tasks/<gid>/task.json` carries MRR `number_value` for active units (4/4=1500). Cure reads the WRONG tier |
| PV-S3-DISABLED | `ASANA_CACHE_S3_ENABLED` unset on warmer + ECS `:501` → tiered S3 cold tier OFF |
| PV-NOT-PAT-GATED | `coherent≥100` needs NO live Asana fetch (data cached) — downgrades the prior ASANA-PAT magnitude gate |
| PV-FLOOR-WORKS | `population_receipt_below_floor` WARNED (active 764, mrr 0.0) — Phase-1 (#115) vindicated; do NOT regress |
| PV-DEPLOY-PATH | deploy = autom8y `satellite-receiver.yml` (cross-repo, ~30-min concurrency lock; `metrics-smoke-gate` reds cosmetically; `a8 deploy` rolls ECS first) |

## The fix (design — to be ratified/implemented by 10x-dev)
Make the cure read the **durable S3 per-task tier** for hot-miss gids, independent of
warm-mode and the global flag. CR-3-safe: **zero new Asana GETs** (S3 reads only; NFR-1
counts *Asana* calls). Preserve never-fabricate (cache-miss → honest null),
never-overwrite (coalesce), not-N+1 (one batch). Field-agnostic (every numeric `cf:`).

- **Option-1 (cure-side, preferred):** the cure reads `asana-cache/tasks/<gid>/task.json`
  via the S3 cache backend for the null gids (or a cold-tier read), extracting
  `number_value` as the probe does. Self-contained; no global store-behavior change.
- **Option-2 (warm-hydrate):** pre-cure step hydrates the store from S3 task copies.

## Acceptance (G-THEATER — broken-fixture, not green-alone)
- **Broken-fixture RED→GREEN:** COLD hot-store + POPULATED S3 per-task cache → the cure
  MUST heal (fires RED on the current `IMMEDIATE`-only read, GREEN after the fix). The
  7 existing isolation tests (pre-populated mock store) stay green but are NOT sufficient.
- **Live:** post-deploy + re-warm, the canonical coherence query shows `coherent≥100`,
  `gun→0` band, `unit.mrr` ~25–30%; warmer log `cache_miss_gids → ~0` for active units.
- Template/inactive units STAY null (G-DENOM; never blanket-fabricate).

## Production-mutating levers (operator's — surface, do not fire)
merge-to-main · autom8y `satellite-receiver.yml` deploy trigger + `aws lambda invoke
autom8-asana-cache-warmer` re-warm · UK-2 (#114) · CR-3 Stage-B→Secret-2 · AC-6 cutover.

## Watch-register (DEFER)
UK-2 (#114 dtype-parity) · `metrics-smoke-gate` deploy-hang reliability (sre) · AC-6 ·
SEAM-2 monolith rebind · `ASANA_CACHE_S3_ENABLED`-globally vs cure-local (note the broader
store-read implications if the flag is flipped fleet-wide).
