---
type: spike
initiative: north-star-per-offer-economics
generator: "data-analyst+DRE rite charge via general agent"
status: accepted
live_legs: measured
self_assessment_cap: MODERATE
date: 2026-07-08
---

# SPIKE: Asset-Linkage Coverage Measurement (creative→asset via junction path)

**Operator charge:** "creative→asset should be *much* higher [than 18.7%] — spike this better on modern ads which all should be linked via assets_ad_creatives and the ad_creatives table through ads→adsets→etc hierarchy defined."

**Repo under measurement:** `/Users/tomtenuta/Code/a8/a8/repos/autom8y-data` (MySQL RDS `nhc-db`, schema `dtenuta`).

---

## Leg 1 — CODE-TOPOLOGY (MEASURED from source; always completable)

### 1.1 The linkage chain, with exact join columns

```
ads_insights.ad_id ──────────────► ads.ad_id                    (fact → dimension)
ads.creative_id ─────────────────► ad_creatives.creative_id      (ad → creative)
                                       │
                     ┌─────────────────┴──────────────────┐
        DIRECT path (sparse)                  JUNCTION path (the operator's path)
        ad_creatives.asset_id ──► assets.id   ad_creatives.creative_id ──► assets_ad_creatives.ad_creative_id
                                              assets_ad_creatives.asset_id ──► assets.id
                                                                                  │
                                              assets.offer_id ──► offers.offer_id (NULLABLE — shared-by-design)
```

File:line anchors (all under `src/autom8_data/` in autom8y-data):

| Edge | Anchor |
|---|---|
| `ads_insights.ad_id → ads.ad_id` | `core/models/_advertising.py:113` (`AdInsight.ad_id` FK) |
| `ads_insights.platform → ad_platforms.id` (col name `platform`) | `core/models/_advertising.py:121` |
| `ads.creative_id → ad_creatives.creative_id` | `core/models/_advertising.py:35` |
| `ads.adset_id → adsets.adset_id` | `core/models/_advertising.py:34` |
| `adsets.offer_id → offers.offer_id` (nullable) | `core/models/_advertising.py:53` |
| DIRECT: `ad_creatives.asset_id → assets.id` (sparse) | `core/models/_advertising.py:249`; in-code figure at `:235-241` |
| JUNCTION: `assets_ad_creatives (ad_creative_id, asset_id, platform_id)` composite PK | `core/models/_advertising.py:296-303` |
| `assets_ad_creatives.asset_id → assets.id` | `core/models/_advertising.py:302` |
| `assets.offer_id → offers.offer_id` (nullable) | `core/models/_advertising.py:165` |
| `asset_verticals (asset_id, vertical_id)` composite PK | `core/models/_advertising.py:306-326` |
| `campaigns.vertical_id → verticals.id` | `core/models/_advertising.py:80` |

### 1.2 The canonical query-planner path (production join semantics)

`ADS_INSIGHTS_ASSETS_PATH` at `analytics/core/joins/canonical_paths.py:337-378` is the LIVE
planner path for asset-dimension spend queries:

```
ads_insights → ads → adsets → campaigns          (hierarchy context)
ads.creative_id → ad_creatives.creative_id
ad_creatives.creative_id → assets_ad_creatives.ad_creative_id
    WITH ancestor_condition: ads_insights.platform = assets_ad_creatives.platform_id   ← platform_id semantics
assets_ad_creatives.asset_id → assets.id
assets.id → platform_assets.asset_id (platform + chiropractor scoped)
```

**platform_id semantics:** junction rows are PER-PLATFORM. The canonical path constrains the
junction join to the insight row's platform (`canonical_paths.py:358-360`,
`ancestor_conditions=(("ads_insights", "platform", "platform_id"),)`). So "creative linked to an
asset" has two flavors: linked-on-ANY-platform vs linked-on-the-SPENDING-platform. Leg 2
measures both.

Corroborating sites:
- `analytics/core/metrics/library.py:391-398` — explicit `JoinDefinition("ad_creatives_to_assets_ad_creatives", LEFT)` planner hint.
- `analytics/core/metrics/library.py:407` — metric `n_distinct_assets` counts `assets_ad_creatives.asset_id` ("carousel junction table for broadest asset coverage").
- `services/assets_ad_creatives.py:65-67` — tenant chain `assets_ad_creatives.asset_id = assets.id → assets.chiropractor_id = chiropractors.guid`.
- `analytics/core/infra/enrichment_views.py:518-528` — ARM-004: `ads_insights.vertical` is enrichment-resolved (Priority 1 campaign chain, Priority 2 lead rescue); raw `ads_insights` has no vertical column.

### 1.3 Where `AssetVertical` fits

`asset_verticals` maps `assets.id → verticals.id` many:many (`_advertising.py:306-326`). It is
NOT on the spend-attribution chain — it is the asset-side vertical equivalence-class label. For
the operator's pending shared-asset-grain ruling, it is the candidate key for the
"same-vertical" equivalence class of shared assets (a shared asset with NULL `offer_id` can
still carry vertical membership via this table). `campaigns.vertical_id` is the spend-side
vertical; `asset_verticals` is the creative-side vertical. Both exist; neither is derived from
the other.

### 1.4 What "modern ads" means operationally

There is **no "modern" flag or platform-generation column** in the schema (grep across
`src/autom8_data` finds no such concept). Available recency axes:

| Column | Type | Anchor | Usable as recency axis? |
|---|---|---|---|
| `ads_insights.date` | VARCHAR `YYYY-MM-DD` | `_advertising.py:104,114` | YES — primary (spend recency; what matters for spend-weighted coverage) |
| `ad_creatives.created_at` | VARCHAR, NOT NULL | `_advertising.py:257` | YES — secondary (creative cohort) |
| `assets.created_at` | VARCHAR, NOT NULL | `_advertising.py:162` | YES — asset cohort |
| `ads.*` | — | `_advertising.py:21-41` | NO date column on `ads` at all |

**Operationalization chosen:** "modern" = segmented by quarter of `ads_insights.date`
(spend-weighted, the operator's stated metric of interest), cross-checked by
`ad_creatives.created_at` year cohort. If modern ads are near-fully junction-linked, the
junction coverage share should approach 100% in recent quarters.

### 1.5 The 18.7% figure is the WRONG path — and internally inconsistent in-code

`_advertising.py:235-241` claims "asset linkage - direct FK, 18.7% populated" but the numbers
given in the SAME docstring are 2,589 of 44,523 = **5.8%**, not 18.7% (2,589/18.7% implies a
~13.8K-row denominator from an older snapshot). Either way it measures the DIRECT sparse
column only. The junction table had 85,405 rows against 44,523 creatives at that snapshot —
the junction path was always the broader path, exactly as the operator asserts.

---

## Leg 2-4 — MEASUREMENT SQL (MySQL dialect, pushed down server-side)

All queries are read-only SELECTs. Live execution route: `QueryConnection.from_settings()`
(ATTACHes RDS as `{attach_as}_raw`; `attach_as` default `"dtenuta"` per `core/config.py:302`)
then push each statement server-side via DuckDB's
`SELECT * FROM mysql_query('dtenuta_raw', '<sql>')` so aggregation runs on RDS, not through
the no-pushdown scanner (SCAR-027 avoidance).

### Leg 2 — spend coverage by quarter (junction vs direct vs neither; row- and spend-weighted)

```sql
SELECT
  CONCAT(SUBSTRING(ai.`date`,1,4), '-Q', QUARTER(ai.`date`)) AS qtr,
  COUNT(*)                                               AS n_rows,
  ROUND(SUM(COALESCE(ai.spend,0)),2)                     AS spend_total,
  ROUND(SUM(CASE WHEN a.ad_id IS NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_no_ad_row,
  ROUND(SUM(CASE WHEN a.ad_id IS NOT NULL AND ac.creative_id IS NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_no_creative,
  ROUND(SUM(CASE WHEN j.ad_creative_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_junction_any,
  ROUND(SUM(CASE WHEN jp.ad_creative_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_junction_platform_matched,
  ROUND(SUM(CASE WHEN ac.asset_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_direct_column,
  ROUND(SUM(CASE WHEN j.ad_creative_id IS NOT NULL OR ac.asset_id IS NOT NULL
        THEN COALESCE(ai.spend,0) ELSE 0 END),2)         AS spend_either,
  SUM(j.ad_creative_id IS NOT NULL)                      AS rows_junction_any,
  SUM(ac.asset_id IS NOT NULL)                           AS rows_direct_column,
  SUM(j.ad_creative_id IS NOT NULL OR ac.asset_id IS NOT NULL) AS rows_either
FROM ads_insights ai
LEFT JOIN ads a  ON a.ad_id = ai.ad_id
LEFT JOIN ad_creatives ac ON ac.creative_id = a.creative_id
LEFT JOIN (SELECT DISTINCT ad_creative_id FROM assets_ad_creatives) j
       ON j.ad_creative_id = a.creative_id
LEFT JOIN (SELECT DISTINCT ad_creative_id, platform_id FROM assets_ad_creatives) jp
       ON jp.ad_creative_id = a.creative_id AND jp.platform_id = ai.platform
GROUP BY qtr
ORDER BY qtr;
```

Notes: DISTINCT sub-joins prevent junction many:many fan-out from multiplying spend;
`jp` applies the canonical platform-match condition; `QUARTER()` coerces the VARCHAR date.

Secondary "modern" axis — creative-grain coverage by `ad_creatives.created_at` year:

```sql
SELECT
  SUBSTRING(ac.created_at,1,4) AS creative_year,
  COUNT(*) AS n_creatives,
  SUM(ac.asset_id IS NOT NULL) AS with_direct_column,
  SUM(j.ad_creative_id IS NOT NULL) AS with_junction,
  SUM(j.ad_creative_id IS NOT NULL OR ac.asset_id IS NOT NULL) AS with_either
FROM ad_creatives ac
LEFT JOIN (SELECT DISTINCT ad_creative_id FROM assets_ad_creatives) j
       ON j.ad_creative_id = ac.creative_id
GROUP BY creative_year ORDER BY creative_year;
```

### Leg 3 — shared vs dedicated magnitude

Spend split by asset-class of the creative (link = junction UNION direct column):

```sql
WITH link AS (
  SELECT aac.ad_creative_id AS creative_id, aac.asset_id
  FROM assets_ad_creatives aac
  UNION
  SELECT ac.creative_id, ac.asset_id
  FROM ad_creatives ac WHERE ac.asset_id IS NOT NULL
),
prof AS (
  SELECT l.creative_id,
         COUNT(DISTINCT l.asset_id)      AS n_assets,
         SUM(ast.offer_id IS NOT NULL)   AS n_dedicated,
         SUM(ast.offer_id IS NULL)       AS n_shared,
         COUNT(DISTINCT ast.offer_id)    AS n_offers
  FROM link l
  JOIN assets ast ON ast.id = l.asset_id
  GROUP BY l.creative_id
)
SELECT
  CASE
    WHEN p.creative_id IS NULL THEN 'unlinked'
    WHEN p.n_shared = 0 AND p.n_offers = 1 THEN 'dedicated_single_offer'
    WHEN p.n_shared = 0 AND p.n_offers > 1 THEN 'dedicated_multi_offer'
    WHEN p.n_dedicated = 0 THEN 'shared_only_offer_id_null'
    ELSE 'mixed_shared_and_dedicated'
  END AS asset_class,
  COUNT(*) AS n_insight_rows,
  COUNT(DISTINCT a.creative_id) AS n_creatives,
  ROUND(SUM(COALESCE(ai.spend,0)),2) AS spend
FROM ads_insights ai
LEFT JOIN ads a ON a.ad_id = ai.ad_id
LEFT JOIN prof p ON p.creative_id = a.creative_id
GROUP BY asset_class ORDER BY spend DESC;
```

Fan-out stats (assets serving >1 creative; creatives with >1 asset):

```sql
SELECT
  (SELECT COUNT(DISTINCT asset_id) FROM assets_ad_creatives) AS assets_linked,
  (SELECT COUNT(*) FROM (SELECT asset_id FROM assets_ad_creatives
     GROUP BY asset_id HAVING COUNT(DISTINCT ad_creative_id) > 1) t1) AS assets_serving_multi_creative,
  (SELECT COUNT(DISTINCT ad_creative_id) FROM assets_ad_creatives) AS creatives_linked,
  (SELECT COUNT(*) FROM (SELECT ad_creative_id FROM assets_ad_creatives
     GROUP BY ad_creative_id HAVING COUNT(DISTINCT asset_id) > 1) t2) AS creatives_with_multi_asset;
```

Assets spanning >1 OPERATIONAL offer (via `adsets.offer_id` of the ads that used them —
the many:many cross-offer signal even where `assets.offer_id` is NULL):

```sql
SELECT COUNT(*) AS assets_spanning_multi_offer FROM (
  SELECT aac.asset_id
  FROM assets_ad_creatives aac
  JOIN ads a    ON a.creative_id = aac.ad_creative_id
  JOIN adsets s ON s.adset_id = a.adset_id
  WHERE s.offer_id IS NOT NULL
  GROUP BY aac.asset_id
  HAVING COUNT(DISTINCT s.offer_id) > 1
) t;
```

### Leg 4 — carried C-0 live legs

```sql
-- (a) assets.offer_id population
SELECT COUNT(*) AS total_assets, SUM(offer_id IS NOT NULL) AS with_offer_id FROM assets;
-- (b) junction row count
SELECT COUNT(*) AS junction_rows, COUNT(DISTINCT ad_creative_id) AS distinct_creatives,
       COUNT(DISTINCT asset_id) AS distinct_assets FROM assets_ad_creatives;
-- (c) account_status (SD-02 registry) population + freshness
SELECT COUNT(*) AS n_rows, MAX(synced_at) AS max_synced_at,
       MAX(stage_entered_at) AS max_stage_entered_at FROM account_status;
-- supplementary: adsets.offer_id propagation
SELECT COUNT(*) AS n_adsets, SUM(offer_id IS NOT NULL) AS with_offer_id FROM adsets;
```

`account_status.synced_at` anchor: `core/models/_platform.py:548-551` (cache-warmer Lambda
pushes snapshots every 4h; SD-05 snapshot-replace).

---

## MEASURED RESULTS (LIVE, 2026-07-08)

**Execution receipt:** all legs ran LIVE against RDS via `QueryConnection.from_settings()`
(env loaded by `direnv exec .` in the autom8y-data repo; `mysql_query()` pushdown AVAILABLE;
probe exit 0). Probe script preserved at
`/private/tmp/claude-501/-Users-tomtenuta-Code-a8-a8-repos-autom8y-asana/e84d5621-522b-4506-8690-d95417cf2fe4/scratchpad/asset_linkage_probe.py`.
No stale parquet was touched. Read-only SELECTs only. **Every leg: MEASURED. Zero blocked.**

### Leg 4 — carried C-0 live legs (headline first)

| Probe | Result |
|---|---|
| **(c) `account_status` (SD-02 registry)** | **0 rows. `MAX(synced_at)` = NULL. The registry is EMPTY — the 4h cache-warmer snapshot push is NOT populating it.** (0 rows cannot mean "no active accounts"; SD-02 active-only semantics would still have rows for the live book.) |
| (a) `assets.offer_id` population | 2,444 / 42,511 = **5.7% non-null** — consistent with shared-by-design; unusable as a primary attribution key |
| (b) `assets_ad_creatives` rows | **93,768** rows; 46,025 distinct creatives; 6,103 distinct assets |
| (supp) `adsets.offer_id` population | **66,350 / 66,354 = 99.99%** — spend-side offer attribution is essentially total at adset grain |
| (supp) `ads.creative_id` population | 59,153 / 59,607 = 99.2% |
| (supp) `ad_creatives.asset_id` (direct col) | 16,241 / 46,935 = **34.6% today** (the in-code "18.7%" is stale AND the wrong path) |
| (supp) junction creative coverage | 46,025 / 46,935 = **98.1% of all creatives have ≥1 junction row** |
| (supp) `ads_insights` shape | 687,574 rows, 2017-11-08 → 2026-07-08, total spend **$7,071,479.08** |
| (supp) junction by platform | 1=facebook 48,624; 6=meta 22,258; 7=instagram 22,785; 8=audience_network 55; 10=tiktok 46 |
| (supp) `ad_platforms` enum | 1 facebook, 2 google, 3 youtube, 4 sendgrid, 5 twilio, 6 meta, 7 instagram, 8 audience_network, 9 messenger, 10 tiktok, 11 unknown, 12 linkedin, 13 twitter, 14 email |

### Leg 2 — spend-weighted coverage by quarter (OPERATOR CONFIRMED)

Full 37-quarter series measured (2017-Q4 → 2026-Q3). Lifetime and per-year rollups:

| Year | Spend total | Junction-any % of total | **Junction % among spend WITH ads row** | No-ads-row % | Direct-col % |
|---|---|---|---|---|---|
| 2021 | $505,762 | 89.3% | 89.3% | 0.0% | 0.0% |
| 2022 | $793,096 | 77.9% | 78.1% | 0.2% | 0.0% |
| 2023 | $1,144,739 | 87.7% | 93.1% | 5.9% | 1.0% |
| 2024 | $1,520,665 | 87.4% | **99.6%** | 12.3% | 31.5% |
| 2025 | $1,916,216 | 84.8% | **98.8%** | 14.1% | 84.6% |
| 2026 | $848,591 | 88.4% | **100.0%** | 11.6% | 88.0% |
| **Lifetime** | **$7,071,479** | **86.3%** | **94.6%** | 8.8% | 40.4% |

Modern-quarter precision (unlinked spend among rows that HAVE an ads row):
2025-Q4 = 0.04%, 2026-Q1 = **0.00%**, 2026-Q2 = **0.00%**, 2026-Q3 = **0.00%**.

**Findings:**
1. **The operator is confirmed exactly.** On modern ads, creative→asset via the junction is
   effectively total: 100.00% of 2026 spend that reaches the ads hierarchy is asset-linked.
   The 18.7% in-code figure measured the wrong path (direct column) at a stale snapshot.
2. **The REAL modern coverage hole is upstream of creatives:** 11.6–14.1% of 2024–2026 spend
   sits on `ads_insights.ad_id` values with **no `ads` row at all** (orphan ads — the same
   class ARM-004's Priority-2 lead-rescue addresses for vertical). Asset linkage is not the
   problem; hierarchy completeness is.
3. **Platform-mismatch window (2021-Q2 → 2025-Q1):** junction-any far exceeds
   platform-matched (e.g. 2024-Q3: $393K vs $157K) — junction rows written under platform 1
   (facebook) while spend was recorded under 6/7 (meta/instagram), the facebook→meta enum-drift
   era. From 2025-Q2 the two converge to identical (2025-Q3: $403,972.65 vs $403,972.56).
   **Historical analyses must use ANY-platform junction linkage; the canonical
   platform-matched join (`canonical_paths.py:358-360`) undercounts pre-2025 spend by up to
   60%.**
4. `ad_creatives.created_at` spans ONLY 2025–2026 (44,666 + 2,269 rows) — it is a row-insertion
   /backfill timestamp, not platform creation time; unusable as historical cohort axis.
   (2026 cohort: 100% junction-linked; 2025 cohort: 81%.)
5. ~7,598 junction `ad_creative_id`s (46,025 − 38,427) have no `ad_creatives` row — junction
   orphans; the junction can rescue creative-linkage even where `ad_creatives` is missing.

### Leg 3 — shared vs dedicated magnitude

Spend by asset-class of the linked creative (junction ∪ direct; asset-linked total $6,092,386):

| Class | Spend | Share of linked | Insight rows | Creatives |
|---|---|---|---|---|
| **shared_only (`assets.offer_id` NULL)** | **$3,528,223** | **57.9%** | 269,568 | 11,690 |
| dedicated_single_offer | $2,510,187 | 41.2% | 356,988 | 7,804 |
| mixed_shared_and_dedicated | $53,111 | 0.87% | 3,944 | 78 |
| dedicated_multi_offer | $865 | 0.014% | 71 | 4 |
| (unlinked, incl. no-ads-row) | $979,093 | — (13.8% of grand total) | 57,003 | 737 |

Fan-out / reuse structure:
- **4,369 / 6,103 linked assets (71.6%) serve >1 creative** — reuse is the norm, not the exception.
- 2,631 / 46,025 linked creatives (5.7%) carry >1 asset (carousel).
- **792 assets span >1 distinct operational offer** (via `adsets.offer_id` of the ads that used them) — cross-offer sharing is real and measurable even where `assets.offer_id` is NULL.
- `assets.offer_id` population by asset cohort: 2024 = 4.0%, 2025 = 7.1%, **2026 = 62.4%** (528/846) — dedication tagging is rising sharply in the newest cohort.

---

## Verdict — one page, addressed to the shared-asset-grain ruling

**What the numbers say:**

1. **The junction path is the canonical creative→asset edge, full stop.** 98.1% of creatives
   have junction rows; on modern (2025-Q4+) spend, junction coverage among hierarchy-intact
   rows is 99.96–100.00%. Any per-offer-economics denominator built on the direct
   `ad_creatives.asset_id` column (the 18.7% figure) undercounts by design. Retire that figure;
   fix the `_advertising.py:235-241` docstring (its own numbers say 5.8%, and today's truth is
   34.6% direct / 98.1% junction).

2. **Shared assets are the MAIN BODY of spend, not a residual.** 57.9% of asset-linked lifetime
   spend flows to NULL-`offer_id` assets, and 71.6% of linked assets serve multiple creatives.
   Any ruling that treats shared assets as an edge case to be dropped or force-assigned will
   misstate the majority of creative economics. NULL `offer_id` is confirmed behaving as
   SHARED-BY-DESIGN (operator domain truth), not as missing data — but note the 2026 cohort is
   62.4% dedicated-tagged, so the shared pool is shrinking at the margin.

3. **Class-rollup vs split vs vertical-pool:** the data supports a TWO-LAYER answer.
   - **Spend-side (per-offer P&L):** `adsets.offer_id` is 99.99% populated. Per-offer spend
     attribution should ride `ads_insights → ads → adsets.offer_id` and does NOT need asset
     dedication at all. This is the SPLIT layer, and it is already fully determined.
   - **Asset-side (creative economics / reuse ROI):** assets are a shared pool. For the
     57.9% shared-spend mass, allocate to offers THROUGH the spend-side key (each insight row
     already knows its adset's offer), i.e. usage-weighted allocation — not through
     `assets.offer_id`. The `asset_verticals` junction (many:many) is the ready-made
     equivalence-class key for the operator's "same-vertical" class definition
     (vertical-pool rollup); only 792 assets genuinely span multiple operational offers and
     would need explicit multi-offer handling under any split scheme.
   - Net: **split spend by `adsets.offer_id`; roll assets up as a vertical-pooled shared
     layer; do not promote `assets.offer_id` (5.7%) to an attribution key.**

4. **Two defects surfaced that gate C-1 denominator quality:**
   - **Orphan ad_ids:** ~12–14% of modern spend has no `ads` row → invisible to ANY
     hierarchy-based offer attribution. This, not creative→asset linkage, is the coverage
     gap worth engineering effort.
   - **`account_status` is EMPTY (0 rows)** — the SD-02 registry is not populating; the 4h
     cache-warmer push is not landing. Anything consuming it (active-book denominators)
     currently reads an empty registry.

5. **Historical-analysis rule:** use ANY-platform junction linkage for pre-2025 data; the
   canonical platform-matched ancestor condition undercounts the 2021–2024 facebook/meta
   enum-drift window by up to ~60% of quarterly spend. Post-2025-Q2 the two are identical, so
   the canonical path is safe for modern data.

**Evidence grade:** MODERATE (self-assessed, per cap). All figures above are live RDS
measurements taken 2026-07-08 by this spike's own probe; none are inherited from code comments
or stale parquet.

---

## Operator runbook (re-run in one paste)

```bash
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-data
direnv exec . uv run python /private/tmp/claude-501/-Users-tomtenuta-Code-a8-a8-repos-autom8y-asana/e84d5621-522b-4506-8690-d95417cf2fe4/scratchpad/asset_linkage_probe.py
```

(direnv exports the `DB_*` tuple; the probe uses `QueryConnection.from_settings()` and pushes
every statement server-side via `mysql_query('dtenuta_raw', ...)`. Read-only. If the scratchpad
copy has been reaped, every SQL body is reproduced verbatim in the Leg 2–4 sections above and
can be pasted into any MySQL client against `dtenuta`.)
