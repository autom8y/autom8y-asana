---
type: review
status: proposed
---

# DEFECT — SEAM-1 entity-blind prober plane-split (active_mrr served 14-day-stale)

- Date: 2026-07-27
- Severity: HIGH for decision-integrity (a financial metric served ~14-day-stale data under a false-fresh "verified 1m ago" signal); client_impact: NONE (read-path only; no write to Asana)
- Discovered by: operator `/qa` on `python -m autom8_asana.metrics active_mrr` — disbelief that "no section changed in 38 days" on a live revenue project
- Blast radius: FLEET-WIDE — every entity-typed metric on every project warmed via the resume path, not just `active_mrr` on project 1143843662099250
- Status: root-caused (single load-bearing defect + 3 compounding); P1–P5 code fix built and green; P0 (prod re-baseline) + P6/P7 (cross-repo / migration) are operator-gated

## Symptom

`active_mrr` reported **$79,585**. The CLI's own freshness output showed `newest parquet = 2026-07-13` (14 days old) yet `verification age: 1m (22 in-scope sections)` — a WARNING quoting a 14-day mutation age while `--strict` still exited 0. The operator did not believe the project had been static for two weeks.

## Evidence (verified directly against S3, project 1143843662099250)

1. **Two divergent write-planes.** `dataframes/{gid}/offer/sections/*.parquet` (v2 SEAM-1 plane — what the metric reads) frozen at **2026-07-13**; `dataframes/{gid}/sections/*.parquet` (legacy plane) receiving fresh writes **2026-07-27 13:00** — including the `ACTIVE` section.
2. **The data genuinely changed.** Direct parquet comparison of the `ACTIVE` section: v2/offer plane (07-13) = **51 rows, $65,585**; legacy plane (07-27) = **48 rows, $60,585**. Three offers churned out; −$5,000 on that section alone.
3. **False-fresh, three layers deep.** (a) All 34 sections share one identical `last_verified_at` (2026-07-27T13:00:30.232451Z) — a per-warm bulk stamp, not 34 verification events. (b) 20/34 sections are `watermark=NULL` → the prober's content check is skipped → hash-only CLEAN → stamped "verified" anyway (ADR-006 D8). (c) The consolidated `offer/dataframe.parquet` carries a **fresh mtime (today 13:01) but stale content** — a re-consolidation of the frozen 07-13 per-section parquets; it sums identically to $79,585.
4. **A trustworthy corrected total is NOT cleanly recoverable from cache.** The fresh legacy plane is fragmentary (7 of 22 active sections present as files); mixing vintages breaks the `(office_phone, vertical)` cross-section dedup (a naive mix yields $83,385 with 63 combos vs 62 — unreliable). The real number is lower than $79,585 on `ACTIVE` but requires a full warm against live Asana (P0) or a live recompute.

## Root cause (single load-bearing defect)

`SectionFreshnessProber` (`src/autom8_asana/dataframes/builders/freshness.py`) was omitted from the SEAM-1 threading (commit **7fa56d19**, #111, 2026-06-09). It had **zero `entity_type`** — `grep -c entity_type builders/freshness.py` → 0 — so every S3 read/write defaulted to `entity_type=None` → the **legacy entity-agnostic plane**, while the full builder (`ProgressiveProjectBuilder`) and the offline reader both moved to the v2 `offer/` plane.

Mechanism of the split-brain, per daily warm:
1. `build_progressive_async(resume=True)` reads the **v2** manifest, finds all sections COMPLETE → `sections_to_fetch=[]` → the full builder (Writer A) writes nothing.
2. `_probe_freshness` runs `SectionFreshnessProber` (Writer B, entity-blind) → the only fresh per-section writes → land on **legacy** `sections/*`.
3. `_merge_section_dataframes` re-reads the frozen **v2** `offer/sections/*` → rewrites `offer/dataframe.parquet` (fresh mtime, stale content) + re-stamps the v2 manifest's `last_verified_at`.
4. The metric reads the frozen v2 plane. `--strict` gates on the (fresh) verification stamp → exits 0.

The last full-fetch that refreshed `offer/sections/*` was 07-13; since then only the entity-blind prober wrote (to legacy), so the v2 plane has been frozen ever since.

### Why the SEAM-1 NFR-2 call-site guard missed it
`tests/unit/dataframes/test_seam1_callsite_inventory.py` enumerated only the **storage-layer** methods (`load_section`/`save_section`/…). The prober calls the **persistence-layer wrappers** (`write_section_async`, `read_section_async`, `update_manifest_section_async`), which were **not in the inventory** — so its entity-blind calls were invisible and the guard passed.

## Compounding defects

- **C1 — silent stale-plane fallback.** `offline._resolve_section_keys` (and `metrics/freshness.py from_s3_resolved`) fall back to legacy only on a v2 **miss (empty)**, never on **v2-stale-but-present**. `max_last_modified` is computed but never used to prefer/guard the fresher plane. Violates SCAR-FRESH-001 (staleness must fail loud).
- **C2 — null-watermark false-CLEAN self-perpetuation.** A null-watermark section can only be probed hash-only; a content edit preserving the GID set is invisible → CLEAN → never rewritten → watermark stays null forever. Each false-CLEAN still stamped `last_verified_at=now` (ADR-006 §Decision-5b / D8 residual).
- **C3 — operator-surface mismatch.** The stderr WARNING keyed on `mutation_age` while `--strict` keyed on `verification_age`; the two could point in opposite directions.

## Remediation (this branch — P1–P5 built, green)

- **P1 (root cause):** thread `entity_type` through `SectionFreshnessProber` (init + all four persistence calls) and its construction in `progressive._probe_freshness`. The prober now reads its baseline from and writes deltas to the SAME v2 plane as the reader.
- **P2 (C1):** `offline._guard_plane_divergence` + `PlaneDivergenceError` — when v2 is present but the legacy plane is >6h fresher, REFUSE (fail loud) rather than serve stale; the metrics CLI maps it to a loud `DATA-INTEGRITY` exit. (Prefer-fresher is unsafe: the legacy plane is fragmentary.)
- **P3 (C2):** a null-watermark CLEAN section is no longer stamped (its `verification_age` climbs off `written_at`, surfacing it as unverified); its watermark is HEALED from the cached parquet's `last_modified` so the next warm can content-verify and stamp legitimately (`progressive._heal_null_watermark`).
- **P4 (C3):** the WARNING now keys on the same axis as `--strict` (verification_age) and prints both axes (`format_verification_warning`).
- **P5 (guard + regression):** extended the SEAM-1 call-site inventory to the persistence-wrapper surface (would now catch this class); added behavioral tests — stale-v2/fresh-legacy refusal, null-watermark not-stamped-but-healed, and an entity-blind-`write_section_async` regression lock.

## Operator-gated follow-ups (NOT in this branch)

- **P0 — re-baseline now:** force a full v2 rebuild (delete/rename `offer/manifest.json` → warm re-fetches all 34 sections from live Asana) to obtain the real current MRR. Requires `CACHE_WARMER_LAMBDA_ARN` (parent-repo `module.cache_warmer.function_arn`). Mind the 429-storm history — off-peak, one project.
- **P6 — observability + deploy:** plane-divergence alarm (v2-vs-legacy mtime skew, absolute v2 age independent of query — AL-5 only emits on query); confirm the parent-repo warmer image picks up P1; retire the orphaned `autom8-asana-cache-warmer-DMS-24h` dead-man.
- **P7 — complete SEAM-1 migration:** copy/rebuild v2 fleet-wide, delete legacy `sections/*`, flip `legacy_fallback_enabled=False`. With legacy gone, the split-brain is structurally impossible.

## ADDENDUM 2026-07-27 — P0 re-baseline result + a second write-path split

The P0 re-baseline was executed against project 1143843662099250 (offer): the v2 `offer/manifest.json` was backed up and deleted, and the prod `autom8-asana-cache-warmer` Lambda was invoked scoped to `{"entity_types":["offer"]}`. Two results:

**1. Validated current number.** The warm rebuilt `offer/dataframe.parquet` live at 15:27 UTC: **`active_mrr = $84,385`** (64 dedup combos, 4,179 rows) vs the stale `$79,585` the CLI was serving — **+$4,800 / +6%**. The per-section diff proves it is a coherent composition shift, not noise:

| Active section | Stale (07-13) | Fresh (15:27) | Δ |
|---|---|---|---|
| ACTIVE | 51r · $65,585 | 48r · $61,585 | −$4,000 |
| OPTIMIZE – Human Review | 2r · $3,100 | 5r · $7,900 | +$4,800 |
| STAGED | 5r · $6,000 | 7r · $10,000 | +$4,000 |

Three offers left ACTIVE but did NOT churn — they moved into OPTIMIZE/STAGED (still active-classified), plus net growth. The independently-derived ACTIVE figure ($61,585/48) matches the fresh legacy-plane read ($60,585/48). The 2-week freeze hid both the workflow movement and the revenue growth.

**2. NEW FINDING — the consolidated-warm and the per-section read-layout are DIFFERENT write paths.** The offer-domain warm (`DataFrameCacheWarmer._warm_entity_type_async` → `strategy._build_dataframe` → `cache.put_async` → `write_final_artifacts_async`) rewrote the consolidated `offer/dataframe.parquet` (+ `watermark.json` + `gid_lookup_index.json`) but did **NOT** rewrite the per-section `offer/sections/*.parquet` files or recreate the manifest (observed: `sections_fresh=0/33`, `manifest_present=0` at finalize). The offline metrics reader (`offline.load_project_dataframe`) reads the **per-section** layout, NOT `dataframe.parquet` — so even a successful full offer warm does not refresh the number the CLI reports. This is a SECOND consumer/producer split on top of the entity-blind-prober split: (a) the incremental prober writes the wrong ENTITY plane (legacy vs v2); (b) the offer-domain warm writes the wrong LAYOUT (consolidated `dataframe.parquet` vs per-section `sections/*`). P7 must reconcile BOTH — the per-section SEAM-1 layout needs its own full rebuild path, and the reader/writer layout choice must be unified (either the CLI reads `dataframe.parquet`, or the offer warm writes the per-section layout, but not the current cross-wired state).

**Operational note:** during the ad-hoc validation, a local `strategy._build_dataframe` run (intended as read-only) partially rewrote prod `offer/sections/*` — the progressive builder persists sections mid-fetch, so that path is NOT side-effect-free. Prod was restored to a coherent state (manifest re-copied from the `.bak-2026-07-27` backup); the fresh `dataframe.parquet` is retained. For the CLI to REPORT $84,385, P1 must deploy AND the per-section layout must be rebuilt.

## Lineage

Subsumes the "Metrics CLI Under-count" scar's 4 open questions (bucket mapping, freshness SLA, section-coverage gap, staleness-surface). Related: SCAR-DFR-001 (entity-agnostic key collision), SCAR-FRESH-001 (staleness must fail loud), ADR-seam1-entity-identity-key, ADR-006-freshness-equals-verification-recency.
