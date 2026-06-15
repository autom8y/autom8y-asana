---
type: handoff
handoff_type: implementation
status: proposed
source_rite: releaser
target_rite: 10x-dev
title: FPC Phase-2 cache-tier cure STILL inert post-deploy — durable-S3 read prefix+reader mismatch (2nd falsification)
date: 2026-06-10
origin_head: 44d9ff7342f790cc184977e063ed4fa24970a71a   # #120 cache-tier-fix MERGED + DEPLOYED (:502)
evidence_grade: MODERATE
---

# HANDOFF — releaser → 10x-dev — cache-tier cure STILL inert (the read path is wrong)

## Rung (G-HALT)
The cache-tier fix (#120) is **MERGED + DEPLOYED** (ECS `:502`/`44d9ff7` COMPLETED, 1/1, 0 failed;
warmer Lambda on `44d9ff7`). But the throughline DEPLOY node **did NOT fire** — this is the **second
deploy-empirical falsification** of the cure. Land HALTED at `deployed`. Do NOT round to fired.

## The live receipt (warmer log, post force-rewarm 11:00Z; unit warmed 11:05:38Z)
```
null_number_recovery_no_op: unit  healed_cells:0  cold_present_gids:0  cache_miss_gids:3021  null_cells_before:9063
```
`cold_present_gids:0` = the cure's NEW durable-S3 read found ZERO present objects across all 3021 gids.
No `cold_read_failed` logged → the backend resolved without error; it simply read the wrong place.
unit.mrr stays ~0 → coherent stays ~1 (heal=0 makes any coherence change impossible; canonical query
re-run unnecessary to conclude the node is unfired).

## Dual root cause (live-verified at origin/main 44d9ff7)
**(1) Prefix pollution.** `S3Settings` (`settings.py:404`, `env_prefix="ASANA_CACHE_S3_"`,
`prefix` default `"asana-cache"`, line 430) → its `prefix` reads env **`ASANA_CACHE_S3_PREFIX`**, which the
warmer/receiver sets to **`asana-cache/project-frames/`** (the *dataframe-storage* prefix, sharing one env
var). The cure's `_resolve_cold_backend` (`null_number_recovery.py:461-466`) builds
`S3CacheProvider(prefix=get_settings().s3.prefix)` = `asana-cache/project-frames/` → key
`asana-cache/project-frames/tasks/<gid>/task.json` → that namespace is **EMPTY** (verified `aws s3 ls`).
The actual copies live at **`asana-cache/tasks/<gid>/task.json`** (default prefix `asana-cache`).

**(2) Reader/format mismatch.** `asana-cache/tasks/<gid>/task.json` is a **RAW Asana task dict** (top-level
`gid`/`custom_fields`, `MRR number_value=1500`; NO `data` envelope, NO version/completeness metadata —
verified by download+inspect). It is written by a different subsystem, NOT the `S3CacheProvider`. The cure
reads via `S3CacheProvider.get_versioned` → `_deserialize_entry`, which expects the versioned CacheEntry
envelope — so even at the correct prefix it would not deserialize these raw objects.

**Why the tests missed it:** build+qa used stand-ins (`_S3Backend` returning `CacheEntry`s directly),
never exercising `get_settings().s3.prefix` NOR real-object deserialization. Stub-green ≠ integration-real.
This is the SAME failure class as the first cure (green-isolation, inert-production) — TWICE now.

## The proven-correct read (already empirically validated against real S3)
`scripts/probe_unit_mrr_provenance.py` ALREADY reads these objects correctly and is PROVEN live:
raw S3 GET of `asana-cache/tasks/<gid>/task.json` (default prefix `asana-cache`) + `raw.get("data", raw)`
→ `custom_fields` → `MRR number_value` (4/4 active = 1500, re-confirmed this pass). The cure must MIRROR
the probe's proven mechanism, not the typed `S3CacheProvider` abstraction.

## Fix direction (10x-dev)
Rebuild the cure's durable read to mirror the probe:
- Read **raw** `asana-cache/tasks/<gid>/task.json` at the **canonical task-cache prefix `asana-cache`** —
  decoupled from the env-polluted `get_settings().s3.prefix` (which carries the dataframe-storage path).
  (Do NOT route through `S3CacheProvider.get_versioned`; these objects are raw, not enveloped.)
- Keep: bounded concurrency (cap=24), 0 Asana GETs (S3 only), never-fabricate/never-overwrite/not-N+1,
  additive/never-raises, the sanctioned `_SANCTIONED_IO_TO_THREAD` entry, the `cold_present_gids` receipt.
- Parse via `raw.get("data", raw)` then the existing `get_custom_field_value(task_data, cf_name)`.

## MANDATORY acceptance (break the stub-theater — TWO falsifications demand it)
- A test/validation that exercises the read against the **REAL object key+format** — either a live
  smoke read of `asana-cache/tasks/<a-known-active-gid>/task.json` (e.g. `1207519540893045` → MRR 1500),
  or a fixture using the REAL raw-dict shape at the REAL default prefix (NOT a `CacheEntry` stub).
- The broken-fixture must fail RED against the current (project-frames-prefix + get_versioned) code and
  GREEN after — proving the prefix AND reader are both corrected.
- Live gate (releaser, post-redeploy+rewarm): warmer log `cold_present_gids>0 / healed_cells>0`, then the
  canonical coherence query `coherent≥100`, `unit.mrr ~25–30%`.

## Deeper smell (watch / surface)
`ASANA_CACHE_S3_PREFIX` is OVERLOADED: it drives BOTH the task-cache `S3Settings.prefix` AND the
dataframe-storage `S3LocationConfig` (warm_cache.py), set to `asana-cache/project-frames/` for the latter
while the task cache actually lives at `asana-cache/`. The task-cache WRITER ignores the env (writes to the
default `asana-cache/tasks/`); the cure's READER trusted it. A config-hygiene fix (separate env vars) is an
sre/architect item — but the CURE fix must not depend on that env regardless.

## Reserved (operator only)
merge-to-main · deploy trigger · re-warm · UK-2 · CR-3 Stage-B/Secret-2 · AC-6.
