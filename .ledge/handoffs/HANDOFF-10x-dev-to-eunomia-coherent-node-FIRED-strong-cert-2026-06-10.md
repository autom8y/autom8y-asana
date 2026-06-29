---
type: handoff
handoff_type: validation
status: proposed
source_rite: 10x-dev
target_rite: eunomia
title: THROUGHLINE DEPLOY NODE FIRED — coherent 0→561 — rite-disjoint STRONG-cert requested
date: 2026-06-10
rung: verified-live (MODERATE self-ref ceiling — STRONG is YOURS to grant)
origin_heads:
  autom8y-asana: b114530e   # #121 durable-read fix (3rd cure) MERGED+DEPLOYED (:503)
  autom8y: 55334d8f         # #481 warmer IAM grant codified, MERGED
---

# HANDOFF — 10x-dev → eunomia — STRONG-cert of the FIRED `coherent≥100` node

## The node receipt (live, 2026-06-10 ~13:08Z — re-derive, do not inherit)
Canonical coherence query (TDD-FPC §97-104) over FRESH production frames
(`dataframes/1201081073731555/unit/dataframe.parquet` @13:07:45Z +
`…/1143843662099250/offer/dataframe.parquet` @13:05:10Z, bucket `autom8-s3`):

| metric | baseline 06-09 | pre-fix 06-10 10:56 | **NOW (post-heal)** |
|---|---|---|---|
| `unit.mrr` populated | 0/3021 | 1/3021 | **723/3021 (23.9%)** |
| `gun` | 571 | 588 | **10** |
| `coherent` | 0 | 1 | **561** (5.6× the ≥100 bar) |
| total_joined | 2001 | 2066 | 2001 |

Warmer-log heal receipt (invocation post-12:57:26Z force re-warm):
`13:07:43Z null_number_recovery_healed healed_cells:1777 cold_present_gids:3015 cache_miss_gids:6
by_column {mrr:723, weekly_ad_spend:719, discount:335}` — vs the two falsifications
(`healed:0 cold_present:0 cache_miss:3021`). Operator's predicted sold-band ~25-30% → measured 23.9%.

## What fired it — the TRIPLE-defect saga (each found ONLY by the deploy-empirical node)
1. **v1 (#119, 8affc80):** cure read the hot store only — cold on the `resume=True` warm (`fetched_rows:0`) → inert.
2. **v2 (#120, 44d9ff73):** cure read durable S3 via `S3CacheProvider(prefix=get_settings().s3.prefix)` — but env
   `ASANA_CACHE_S3_PREFIX` is OVERLOADED (prod = the dataframe prefix `asana-cache/project-frames/`, TF
   `autom8y/terraform/services/asana/main.tf:213`) AND the objects are RAW task dicts, not provider envelopes → inert.
3. **v3 (#121, b114530e):** raw boto3 GET at the PINNED prefix (`asana-cache/tasks/<gid>/task.json`) — read the RIGHT
   key but the warmer role lacked `s3:GetObject` on it → `AccessDenied` ×3021 (12:36Z) → honest no-op.
4. **IAM grant (α-pattern):** read-only `S3DurableTaskCacheRead` applied live to all 3 warmer lanes ~12:55-13:00Z +
   codified autom8y#481 (`55334d8f`, MERGED — apply is now a no-op reconcile). Next warm → **the node fired.**

v1+v2 passed CI and qa on stub-validated tests (G-THEATER lesson, twice). v3 was REAL-validated pre-land:
live smoke read of 3 production gids through the cure's own path + env-pollution-immunity proof with the
prod-poisoned prefix active + behavioral RED witness of the v2 code (#121 PR body carries receipts).

## What we ask of eunomia (rite-disjoint — promotes MODERATE → STRONG)
1. **Re-fire the canonical query yourself** from fresh-pulled frames (do NOT trust our numbers).
2. Re-pull the warmer-log heal line; verify `denied_errors` ≈ 0 on the NEXT scheduled warm (the 6 residual
   at 13:07 were the 6 cache-miss gids / propagation stragglers — verify, don't assume).
3. Verify heal STABILITY across ≥2 subsequent scheduled warms (no re-clobber; idempotent re-heal).
4. Verify G-DENOM honesty: Templates/inactive stay null (no blanket fill — 723/3021 ≈ the sold band, NOT 3021/3021).
5. Verify the IAM codification is a live no-op (TF plan on autom8y main shows no change on the 3 warmer policies).
6. Audit the residual `gun=10` (cache_miss 6 + present-but-null durable copies) — classify, don't round to 0.

## Banked vs gated (never round up)
- **BANKED:** #115 floor · #118 guard · #119+#120+#121 merged · ECS `:503`/warmer on `b114530` · IAM grant live+codified (#481) ·
  **the node receipt above** (MODERATE). SEAM-1 62/$79,485 intact.
- **GATED:** STRONG = yours · full-magnitude (residual gun=10) audit · telos five-signal verified-realized (needs SEAM-2 + AC-6, cross-repo).

## Carry to sre (do not lose)
- **AMBER-2 SLI still dark** (EcsServiceDenominatorAbsent) — a dark SLI cannot certify the soak; the `:503` deploy was another re-test window.
- **`ASANA_CACHE_S3_PREFIX` overload** (task-cache settings vs dataframe storage share one env var) — config-hygiene split; the cure no longer depends on it, but the next consumer will.
- **`metrics-smoke-gate` deploy-hang** (~30-min satellite lock burn per deploy) — reliability defect.
- **discount healed 335 cells** — discount is the UK-2 drift cell (schema Decimal vs model Enum); the cure faithfully healed number_values present in durable copies. Flag into the UK-2 ruling context.
- CR-3 soak / Stage-B · AC-6 cutover (#36/R2) — operator/IC clocks, unchanged.

## DEFER watch-register
UK-2 (#114) · UK-3 · #97 warmer fast-lane · Option-2 (S3 as store read-tier, architect) · D-1 probe-script citation nit in the cure docstring · `ASANA_CURE_COLD_CONCURRENCY` knob at scale.
