# SPIKE: InsightsExport Migration Gap Analysis

**Date**: 2026-02-12
**Author**: Architect (Claude)
**Status**: RESEARCH COMPLETE
**Scope**: Map each legacy InsightsExport table to modern autom8_data API capabilities

---

## 1. Executive Summary

| Status | Count | Tables |
|--------|-------|--------|
| **GREEN** | 5 | BY QUARTER, BY MONTH, BY WEEK, OFFER TABLE, AD QUESTIONS TABLE |
| **YELLOW** | 5 | SUMMARY, BY AD SET / T7 BY ADSET / T7 BY AD, ASSET TABLE, APPOINTMENTS, LEADS |
| **RED** | 4 | LIFETIME RECONCILIATIONS, T14 DAY RECONCILIATIONS, DEMO TABLE, UNUSED ASSET TABLE |

**Overall Readiness: YELLOW** -- 5 of 14 tables are directly servable from the modern API today. Another 5 require format translation or minor data enrichment on the autom8_asana side. 4 tables require capabilities that do not yet exist in autom8_data and would need new endpoint development.

### Key Findings

1. **Core aggregated insights** (quarterly/monthly/weekly/offer/ad-question) are fully supported via `POST /api/v1/data-service/insights` with the period aggregation path (QUARTER, MONTH, WEEK) and frame_type mapping (offer, unit, asset).

2. **Budget reconciliation** has no equivalent in autom8_data. The SpendInsights factory (primary_dim="reconcile") with its payment tracking columns (num_pmts, weekly_budget, pmts_start, pmts_end, balance, diff, diff_units) is entirely legacy MySQL+S3 backed. This is the largest RED gap.

3. **Detail row endpoints** (appointments, leads) exist in autom8_data but have format differences from the legacy tabulated output. The modern endpoints return JSON with different column sets; translation is needed.

4. **Unused asset detection** is pure business logic in the legacy AssetsInsightsManager -- it cross-references all available assets against those with ad-level spend. autom8_data has no equivalent computation.

5. **Demographics (DEMO TABLE)** aggregates 7+ sub-queries (max_age, min_age, radius, zips, income, education, objective) into a pivoted frame. autom8_data has no demographics insight or targeting dimension support.

---

## 2. Per-Table Analysis

### 2.1 SUMMARY

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.summary_table` -> `AdInsights.get_summary_frame()` |
| **Factory** | Composite: `AdsInsights` (enabled ads frame), `SpendInsights` (lifetime reconciliation), metric summarization logic |
| **Key Columns** | Total Ad Spend, Total LTV, Total Leads, Total Scheduled, Avg CPS, Median CPS, Min CPS, Current CPS, Min CPS Ad ID |
| **Business Logic** | Computes summary statistics (avg, median, min, max, current) for CPL, CPS, ROAS across all enabled ads. Filters by `offer_cost`, `offer_id`, `asset_id notna`, `spend > 40`. Pulls total spend from lifetime reconciliations. |
| **Modern API** | `POST /insights` with `frame_type=unit, period=LIFETIME` returns aggregated metrics (spend, leads, scheds, ltv, cps, cpl, roas, avg_conv). Missing: per-ad min/max/median CPS computation and reconciliation-sourced total spend. |
| **Status** | **YELLOW** |
| **Gap Details** | The summary table's min/max/median CPS across individual ads requires the ad-level breakdown (frame_type does not support ad-level grouping). Total Ad Spend comes from reconciliation (RED). The modern unit-level data provides totals but not the distributional statistics. |
| **Migration Notes** | MVP could use unit-level aggregates from modern API for totals (spend, ltv, leads, scheds) and compute CPS stats client-side from an ad-level query. Reconciliation spend would need a separate source or the legacy reconciliation column dropped in favor of Parquet-sourced spend. |

### 2.2 LIFETIME RECONCILIATIONS

| Field | Value |
|-------|-------|
| **Legacy Source** | `budget_manager.lifetime_reconciliations_table` -> `ReconcileBudget.lifetime_reconciliations_frame` |
| **Factory** | `SpendInsights` (primary_dim="reconcile") with `InsightsPeriod.LIFETIME` |
| **Key Columns** | num_pmts, weekly_budget, pmts_start, pmts_end, first_pmt_date, latest_pmt_date, balance, spend, spent, diff, balance_units, spend_units, diff_units |
| **Business Logic** | Computes budget vs. actual spend reconciliation over the full lifetime. Joins payment records with ad spend data. Calculates balance (collected - spent), diff, and unit-normalized variants. Column renaming: `this_balance` -> `balance`, `this_spend` -> `spend`, `this_diff` -> `diff`, etc. |
| **Modern API** | **NOT AVAILABLE**. No reconciliation endpoint or computation exists in autom8_data. The `InsightsService` returns ad performance metrics only. No payment data integration. |
| **Status** | **RED** |
| **Gap Details** | Payment data (num_pmts, pmts_start, pmts_end, weekly_budget) comes from MySQL tables not replicated in autom8_data's Parquet/DuckDB pipeline. The entire reconciliation computation is absent. |
| **Migration Notes** | Three remediation paths: (a) Build a new `/api/v1/data-service/reconciliations` endpoint in autom8_data that joins payment tables with spend data, (b) Keep reconciliation as a legacy MySQL query called from autom8_asana directly, (c) Expose a minimal reconciliation computation in the export service that combines modern spend data with a payment lookup. Option (b) is lowest cost for MVP. |

### 2.3 T14 DAY RECONCILIATIONS

| Field | Value |
|-------|-------|
| **Legacy Source** | `budget_manager.t14_reconciliations_table` -> `ReconcileBudget.t14_reconciliations_frame` |
| **Factory** | `SpendInsights` (primary_dim="reconcile") with `InsightsPeriod.T14` |
| **Key Columns** | Same as LIFETIME RECONCILIATIONS but scoped to trailing 14 days |
| **Business Logic** | Same reconciliation logic as lifetime, but for the T14 window. Uses `_filter_period_frame_cols()` to rename `this_*` columns. |
| **Modern API** | **NOT AVAILABLE**. Same gap as LIFETIME RECONCILIATIONS. |
| **Status** | **RED** |
| **Gap Details** | Identical to LIFETIME RECONCILIATIONS -- payment data and reconciliation computation are absent from autom8_data. |
| **Migration Notes** | Same remediation paths as 2.2. Both reconciliation tables share the same factory and logic; solving one solves both. |

### 2.4 APPOINTMENTS

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.appts_table` -> `AdInsights.appts_frame` |
| **Factory** | `ApptInsights` (primary_dim="appts", extends LeadInsights) |
| **Key Columns** | id, name, status, ad_id, platform, follow_up, office_phone, vertical, appt_source, notes, appt_created, appt_dt, appt_status, out_calls, in_calls, appt_call_time, time_on_call, ltv |
| **Business Logic** | Filters to last 90 days (`X_DAYS_FOR_APPT_INSIGHTS`). Removes rows where `appt_created` is null. Sorts by `appt_created` descending. Truncated to `SMALL_TABLE_LEN` rows in tabulate output. |
| **Modern API** | `GET /api/v1/data-service/appointments?office_phone=...&days=90&limit=100` returns individual appointment records with campaign hierarchy JOINs. |
| **Status** | **YELLOW** |
| **Gap Details** | The modern endpoint exists and returns detail rows from MySQL. Column set differences: modern uses `AppointmentDetailRecord` Pydantic model which may not include all legacy columns (e.g., `follow_up`, `convo`, `notes`, `appt_source`). Also: legacy output is tabulated text, modern returns JSON. |
| **Migration Notes** | Need to verify column parity between `AppointmentDetailRecord` and legacy `ApptInsights.DIMS + METRICS`. Format translation from JSON to tabulated text is trivial. May need to add missing columns to the modern query's JOIN if they are required. |

### 2.5 LEADS

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.leads_table` -> `AdInsights.leads_frame` |
| **Factory** | `LeadInsights` (primary_dim="leads") |
| **Key Columns** | created, id, name, status, ad_id, adset_id, platform, follow_up, in_calls, out_calls, lead_call_time, time_on_call, ltv, vertical, notes, convo |
| **Business Logic** | Filters to last 30 days (`X_DAYS_FOR_LEAD_INSIGHTS`). Excludes leads that appear in the appointments frame (by `id`). Selects only `LEAD_INSIGHTS_COLS`. |
| **Modern API** | `GET /api/v1/data-service/leads?office_phone=...&days=30&exclude_appointments=true&limit=100` returns individual lead records with appointment exclusion. |
| **Status** | **YELLOW** |
| **Gap Details** | The modern endpoint exists with `exclude_appointments` support, matching the legacy behavior. Column set differences similar to appointments -- need to verify `LeadDetailRecord` includes `follow_up`, `notes`, `convo`, `adset_id`. Legacy filters by `LEAD_INSIGHTS_COLS` specifically. |
| **Migration Notes** | Same as appointments: verify column parity, translate JSON to tabulated text. The `exclude_appointments` flag maps directly to the legacy exclusion logic. |

### 2.6 BY QUARTER

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.quarterly_insights_table` -> `AdInsights.quarterly_frame` |
| **Factory** | `AccountInsights` with `InsightsPeriod.QUARTER` |
| **Key Columns** | PERIOD_COLS (date, year, quarter, month, week, day, period, period_len, start_date, end_date) + METRIC_COLS (first_ran, last_ran, budget, spend, cpl, cps, ecps, esp20m, lctr, leads, contacts, scheds, fut_pen, ns_nc, convs, ltv, avg_conv, ns_rate, nsr_ncr, conv_rate, roas) |
| **Business Logic** | Account-level metrics aggregated by calendar quarter. Filtered to `PERIOD_COLS + METRIC_COLS`. Truncated to `SMALL_TABLE_LEN` (3) rows. |
| **Modern API** | `POST /insights` with `frame_type=unit, period=QUARTER` triggers Polars post-query aggregation via `aggregate_by_period(df, "by_quarter")`. Returns `period_start`, `period_end`, `period_label` plus all unit metrics and recomputed rates. |
| **Status** | **GREEN** |
| **Gap Details** | Full coverage. The modern `period_aggregator.py` handles QUARTER aggregation with proper rate recomputation from summed volumes. Column names differ slightly (`period_start`/`period_end`/`period_label` vs `start_date`/`end_date`/`quarter`). |
| **Migration Notes** | Column name mapping needed: `period_label` -> `quarter` (or keep modern names). The `budget` column may not be present in modern output (it is a reconciliation-adjacent field). `fut_pen` is present as a SUM_METRIC. Rate metrics (cpl, cps, ecps, etc.) are recomputed correctly. |

### 2.7 BY MONTH

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.monthly_insights_table` -> `AdInsights.monthly_frame` |
| **Factory** | `AccountInsights` with `InsightsPeriod.MONTH` |
| **Key Columns** | Same as BY QUARTER |
| **Business Logic** | Account-level metrics aggregated by calendar month. Truncated to `SMALL_TABLE_LEN` (3) rows. |
| **Modern API** | `POST /insights` with `frame_type=unit, period=MONTH` triggers `aggregate_by_period(df, "by_month")`. |
| **Status** | **GREEN** |
| **Gap Details** | Full coverage, same column mapping considerations as BY QUARTER. |
| **Migration Notes** | Same as BY QUARTER. |

### 2.8 BY WEEK

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.weekly_insights_table` -> `AdInsights.weekly_frame` |
| **Factory** | `AccountInsights` with `InsightsPeriod.WEEK` |
| **Key Columns** | Same as BY QUARTER |
| **Business Logic** | Account-level metrics aggregated by ISO week. Truncated to `MED_TABLE_LEN` rows. |
| **Modern API** | `POST /insights` with `frame_type=unit, period=WEEK` triggers `aggregate_by_period(df, "by_week")`. |
| **Status** | **GREEN** |
| **Gap Details** | Full coverage. |
| **Migration Notes** | Same as BY QUARTER. |

### 2.9 BY AD SET (algo v1) / T7 BY ADSET + T7 BY AD (algo v2)

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.insights_table` (v1) / `insights_manager.t7_adsets_table` + `insights_manager.t7_ads_table` (v2) |
| **Factory** | `AdsInsights` (primary_dim=None, break_down by ad_id) for ads, `AdsetsInsights` (break_down by adset_id) for adsets |
| **Key Columns** | PERIOD_COLS + ADS_INSIGHTS_COLS (ad_id, asset_id, offer_id, offer_cost, form_questions) + METRIC_COLS for ads; PERIOD_COLS + ADSETS_INSIGHTS_COLS (adset_id, adset_name) + METRIC_COLS for adsets |
| **Business Logic** | For v1: full lifetime insights frame filtered by `spend > SPEND_CUTOFF` or `last_ran >= DATE_CUTOFF`, with disabled asset exclusion. For v2: T7 period-specific ad and adset breakdowns. Truncated to `LARGE_TABLE_LEN` / `MED_TABLE_LEN`. |
| **Modern API** | No direct ad-level or adset-level frame_type exists. Modern API supports `frame_type` of offer/unit/business/asset only. The ad and adset breakdowns would require either a new frame_type or custom grouping parameters. |
| **Status** | **YELLOW** |
| **Gap Details** | The modern `FrameTypeMapper` does not include `ad` or `adset` frame types. The AnalyticsEngine likely has the underlying data (ad-level and adset-level insights exist in the legacy SQL factories and presumably in the Parquet files), but the API does not expose ad/adset grouping. The `asset` frame_type partially overlaps with ad-level data (since ads reference assets) but is not a direct substitute. |
| **Migration Notes** | Two paths: (a) Add `ad` and `adset` frame_types to the FrameTypeMapper and create corresponding AnalyticsEngine insights, or (b) Use the legacy AdsInsights/AdsetsInsights factories directly from autom8_asana (keeping the legacy SQL path for these specific tables). Path (b) is lower risk for MVP; path (a) is the clean migration. |

### 2.10 AD QUESTIONS TABLE

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.ad_question_insights_table` -> `AdInsights.ad_question_insights` |
| **Factory** | `AdQuestionInsights` (primary_dim="questions") |
| **Key Columns** | PERIOD_COLS + AD_QUESTION_COLS (key, priority) + METRIC_COLS |
| **Business Logic** | Lifetime ad question performance grouped by question key. No special filtering beyond the factory defaults. |
| **Modern API** | The HealthScoreService supports `ad_question` entity_level for health scoring, and the AnalyticsEngine has an `account_level_stats` fallback. However, the insights API does not have a direct `ad_question` frame_type. The legacy factory uses `primary_dim="questions"` with `key` and `priority` dimensions. |
| **Status** | **GREEN** (with caveat) |
| **Gap Details** | While no explicit `ad_question` frame_type exists in the InsightsService, the underlying data pipeline in autom8_data includes question-level metrics (the `ad_question_index` health scoring definition references these metrics). A frame_type addition would be straightforward. The metrics themselves (lp20m, sp20m, esp20m, etc.) are all available. |
| **Migration Notes** | Add `ad_question` frame_type to `FrameTypeMapper` pointing to a `question_level_stats` insight. The dimensions are `key` and `priority` (simple additions). Alternatively, this could be fetched via the existing ad-level data and aggregated client-side by question key. |

### 2.11 ASSET TABLE

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.assets_table` -> `AdInsights.assets_frame` -> `creative_manager.asset_insights_frame` -> `AssetsInsightsManager.asset_insights_frame` |
| **Factory** | `AssetInsights` (primary_dim="assets") with computed scores from `AssetsInsightsManager` |
| **Key Columns** | ASSET_INSIGHT_COLS (asset_id, disabled, asset_type, asset_link, offer_id, template_id) + performance metrics (spend, imp, leads, scheds, cps, esp20m, etc.) + computed `asset_score` |
| **Business Logic** | Lifetime asset performance with health scoring. The `AssetsInsightsManager` adds computed scores using the asset health index weights. Filters out TEXT assets. |
| **Modern API** | `POST /insights` with `frame_type=asset, period=LIFETIME` returns per-asset metrics with the correct dimensions (asset_id, asset_type, asset_link, etc.) and metrics (spend, imp, leads, scheds, cps, esp20m, etc.). |
| **Status** | **YELLOW** |
| **Gap Details** | The core asset metrics are fully available. Missing: (a) `template_id` column (not in modern asset dimensions), (b) computed `asset_score` from the health scoring engine (available via HealthScoreService but not inline in the insights response), (c) `disabled` filtering logic. |
| **Migration Notes** | MVP can use `frame_type=asset` for raw metrics. Asset scoring can be obtained from HealthScoreService separately or computed client-side. The `template_id` dimension would need to be added to the AnalyticsEngine asset insight if required. |

### 2.12 OFFER TABLE

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.offer_insights_table` -> `AdInsights.offer_insights` |
| **Factory** | `BusinessOfferInsights` (primary_dim="business_offers") |
| **Key Columns** | PERIOD_COLS + OFFER_COLS (offer_id, offer_name, cost) + METRIC_COLS |
| **Business Logic** | Lifetime offer performance grouped by offer_id. No special filtering. |
| **Modern API** | `POST /insights` with `frame_type=offer, period=LIFETIME` returns per-offer metrics with dimensions (offer_id, offer_name, offer_cost, office_phone, vertical). |
| **Status** | **GREEN** |
| **Gap Details** | Full coverage. The modern `FrameTypeMapper` has an explicit `offer` frame_type with `offer_level_stats` insight. Column name difference: legacy `cost` vs modern `offer_cost`. |
| **Migration Notes** | Column rename: `offer_cost` -> `cost` if needed. Otherwise direct mapping. |

### 2.13 DEMO TABLE

| Field | Value |
|-------|-------|
| **Legacy Source** | `insights_manager.demos_table` -> `AdInsights.demos_frame` -> `demo_manager.demo_insights_frame` -> `DemographicInsights.demo_insights_frame` |
| **Factory** | Custom SQL queries via `demographics/sql_utils.py` -- NOT a standard factory |
| **Key Columns** | val, cat (max_age, min_age, radius, zips, $, ed, obj) + METRIC_COLS for each demographic dimension |
| **Business Logic** | Aggregates 7 separate demographic dimension queries (max_age, min_age, radius, zips, income, education, campaign objective) into a single pivoted frame. Each sub-query returns performance metrics broken down by a specific targeting parameter. Uses population estimation for radius insights. |
| **Modern API** | **NOT AVAILABLE**. autom8_data has no demographic/targeting dimension insights. The AnalyticsEngine does not have insights that break down by radius, zip code, age range, income bracket, or education level. |
| **Status** | **RED** |
| **Gap Details** | The demographic insights are sourced from ad-platform targeting parameters (Meta/TikTok API targeting specs joined with performance data). This data is in the legacy MySQL tables and the legacy S3 cache but is not replicated to the Parquet/DuckDB pipeline. None of the 7 demographic dimensions are available as modern API parameters. |
| **Migration Notes** | Three options: (a) Build demographic dimension support in autom8_data's AnalyticsEngine (significant scope), (b) Keep demographics as a direct MySQL query from autom8_asana, (c) Drop the DEMO TABLE from MVP export (it has the lowest business criticality of the export tables). Recommend option (c) for MVP, with (a) as a Phase 2 goal. |

### 2.14 UNUSED ASSET TABLE

| Field | Value |
|-------|-------|
| **Legacy Source** | `creative_manager.unused_assets_table` -> `CreativeInsights.unused_assets_frame` -> `AssetsInsightsManager.unused_assets_report` |
| **Factory** | No factory -- pure application logic in `AssetsInsightsManager` |
| **Key Columns** | ASSET_COLS (asset_created, asset_id, asset_type, asset_link, offer_id, template_id, is_generic, sanitized_text, is_raw, disabled, transcript) |
| **Business Logic** | Cross-references all available assets (from the offer holder's all_assets_frame) against assets that appear in performance reports (lifetime and recent). Assets without any ad spend are flagged as "unused." Adds `spend=0.0` and `asset_score=0.0` columns. |
| **Modern API** | **NOT AVAILABLE**. No unused asset detection in autom8_data. The insights API returns metrics for assets WITH spend data; it has no concept of "all available assets" vs "used assets." |
| **Status** | **RED** |
| **Gap Details** | The unused asset computation requires two data sources: (a) the complete asset inventory for an offer (from the Asana asset management system), and (b) the set of assets with any ad spend (from the insights pipeline). autom8_data only has (b). The asset inventory (a) lives in the autom8 legacy system's asset tracking. |
| **Migration Notes** | This is inherently a cross-system computation. Options: (a) autom8_asana already knows the asset inventory; it could call `frame_type=asset` to get assets-with-spend and compute the diff locally, (b) Build an unused-asset endpoint in autom8_data that accepts an asset ID list and returns the complement. Option (a) is the natural architecture since autom8_asana owns the asset inventory. |

---

## 3. Modern API Inventory

### 3.1 Endpoints Available in autom8_data

| Endpoint | Method | Description | Frame Types / Params |
|----------|--------|-------------|---------------------|
| `/api/v1/data-service/insights` | POST | Batch insights with frame-type abstraction | offer, unit, business, asset x T7/T14/T30/LIFETIME/QUARTER/MONTH/WEEK |
| `/api/v1/data-service/appointments` | GET | Detail appointment rows (MySQL) | office_phone, days, start_date, end_date, limit |
| `/api/v1/data-service/leads` | GET | Detail lead rows (MySQL) | office_phone, days, exclude_appointments, start_date, end_date, limit |
| `/api/v1/data-service/gid-map` | POST | Phone/vertical to Asana GID lookup | phone_vertical_pairs |

### 3.2 AnalyticsEngine Insights

| Insight Name | Entity Level | Source |
|-------------|-------------|--------|
| `account_level_stats` | unit/business | DuckDB/Parquet |
| `offer_level_stats` | offer | DuckDB/Parquet |
| `asset_level_stats` | asset | DuckDB/Parquet |

### 3.3 Period Support

| Period | Translation | Implementation |
|--------|------------|----------------|
| T7 | `trailing_7_days` | Engine preset (date filter) |
| T14 | `trailing_14_days` | Engine preset (date filter) |
| T30 | `trailing_30_days` | Engine preset (date filter) |
| LIFETIME | `None` (no filter) | Engine preset (all data) |
| QUARTER | `by_quarter` | Polars post-query aggregation |
| MONTH | `by_month` | Polars post-query aggregation |
| WEEK | `by_week` | Polars post-query aggregation |

### 3.4 Metrics Available in Modern API

The `EntityMetrics` response model supports 60+ fields including:
- **Volume**: spend, imp, lclicks, leads, contacts, scheds, effective_scheds, convs, ltv
- **Appointment Status**: fut, pen, ns, nc, fut_pen, ns_nc
- **Rate Metrics**: cps, ecps, cpl, cpc, ctr, lctr, conversion_rate, booking_rate, ns_rate, nc_rate, conv_rate, nsr_ncr, roas, avg_conv, sched_rate
- **Per-20k**: lp20m, sp20m, esp20m, ltv20m
- **Period Context**: first_ran, last_ran, period_len, days_with_activity, period_start, period_end, period_label
- **Reconciliation**: num_invoices, collected, first_payment, latest_payment, variance, variance_pct, expected_collection, expected_variance
- **Pacing**: expected_spend, pacing_ratio, projected_spend, budget_variance, pacing_status
- **Asset-Specific**: asset_id, platform_id, asset_type, asset_link, transcript, is_raw, is_generic, disabled
- **Offer-Specific**: offer_id, offer_cost, budget

**Note**: The reconciliation and pacing fields are defined in the response model but are not populated by any current insight. They are placeholders for future capability.

---

## 4. Critical Gaps (RED Items)

### 4.1 Budget Reconciliation (LIFETIME + T14)

**Impact**: HIGH -- reconciliation is core to the budget management workflow. The export is consumed by account managers to verify spend vs. collection alignment.

**What is Missing**:
- Payment data (num_pmts, weekly_budget, pmts_start, pmts_end, first_pmt_date, latest_pmt_date)
- Balance computation (collected - spent)
- Unit normalization (balance_units, spend_units, diff_units)
- The `SpendInsights` factory with `primary_dim="reconcile"` SQL query

**Remediation Paths**:
1. **New autom8_data endpoint** (`/api/v1/data-service/reconciliations`): Medium effort. Requires MySQL access to payment tables + Parquet spend data join. Most architecturally clean.
2. **Legacy SQL pass-through from autom8_asana**: Low effort. autom8_asana calls the legacy `SpendInsights` factory directly (requires legacy DB access from autom8_asana runtime).
3. **Hybrid approach**: autom8_asana fetches spend from modern API + payment data from a lightweight new endpoint, computes reconciliation client-side.

**Recommendation**: Path 3 for MVP. Keep reconciliation logic in autom8_asana (it already has the business rules in `ReconcileBudget`), source spend from modern API, add a minimal payment-data endpoint to autom8_data.

### 4.2 Demographics (DEMO TABLE)

**Impact**: MEDIUM -- demographics inform targeting decisions but are not as operationally critical as reconciliation or performance tables.

**What is Missing**:
- 7 demographic dimension queries (max_age, min_age, radius, zips, income, education, objective)
- Population estimation for radius insights
- Pivoted cat/val format combining all dimensions

**Remediation Paths**:
1. **Full demographic support in autom8_data**: High effort. Requires targeting-parameter enrichment of the Parquet pipeline.
2. **Legacy SQL pass-through**: Medium effort. Demographics queries are custom SQL, not standard factory patterns.
3. **Drop from MVP export**: Zero effort. Re-add in Phase 2.

**Recommendation**: Path 3 for MVP. Demographics are the least critical export table and the most complex to migrate.

### 4.3 Unused Asset Table

**Impact**: LOW-MEDIUM -- informs creative refresh decisions. The information is useful but not operationally blocking.

**What is Missing**:
- Complete asset inventory (all available assets, not just those with spend)
- Cross-reference computation (inventory minus active)

**Remediation Paths**:
1. **Client-side computation in autom8_asana**: Low effort. autom8_asana already has the asset inventory. Fetch `frame_type=asset` from modern API to get assets-with-spend, compute the diff locally.
2. **New autom8_data endpoint**: Medium effort. Requires autom8_data to accept an asset ID list and return the complement.

**Recommendation**: Path 1. This is naturally computed in autom8_asana which owns the asset inventory.

---

## 5. CHI Weight Parity

### 5.1 Legacy CHI Weights

Source: `~/code/autom8/config/thresholds/health_scoring.py`

```python
CHI_WEIGHTS = {
    "lp20m": 1,
    "sp20m": 2.5,
    "esp20m": 3,
    "nsr_ncr": 2,
    "conv_rate": 2,
    "ltv20m": 3,
}
```

### 5.2 Modern CHI Weights

Source: `/Users/tomtenuta/code/autom8_data/src/autom8_data/analytics/primitives/config/health_scoring.py`

```python
chi_index = IndexDefinition(
    display_name="Customer Health Index",
    entity_level="account",
    components=[
        ComponentDefinition(name="lead_volume", source_metric="lp20m", weight=1.0, direction="higher_is_better"),
        ComponentDefinition(name="schedule_volume", source_metric="sp20m", weight=2.5, direction="higher_is_better"),
        ComponentDefinition(name="effective_schedule_volume", source_metric="esp20m", weight=3.0, direction="higher_is_better"),
        ComponentDefinition(name="no_show_no_close_rate", source_metric="nsr_ncr", weight=2.0, direction="lower_is_better"),
        ComponentDefinition(name="conversion_rate", source_metric="conv_rate", weight=2.0, direction="higher_is_better"),
        ComponentDefinition(name="ltv_efficiency", source_metric="ltv20m", weight=3.0, direction="higher_is_better"),
    ],
)
```

### 5.3 Parity Assessment: **FULL PARITY**

| Metric | Legacy Weight | Modern Weight | Direction | Status |
|--------|-------------|---------------|-----------|--------|
| lp20m | 1 | 1.0 | higher_is_better | MATCH |
| sp20m | 2.5 | 2.5 | higher_is_better | MATCH |
| esp20m | 3 | 3.0 | higher_is_better | MATCH |
| nsr_ncr | 2 | 2.0 | lower_is_better | MATCH |
| conv_rate | 2 | 2.0 | higher_is_better | MATCH |
| ltv20m | 3 | 3.0 | higher_is_better | MATCH |

The modern system adds explicit `direction` metadata (particularly `lower_is_better` for `nsr_ncr`) which was implicit in the legacy system. All weights are numerically identical.

### 5.4 Other Health Index Parity

| Index | Legacy Source | Modern Source | Parity |
|-------|-------------|--------------|--------|
| ASSET_WEIGHTS | `health_scoring.py` | `health_scoring.py` (primitives/config) | MATCH (lctr:3, lp20m:2, sp20m:4, esp20m:2, ltv20m:2) |
| OFFER_WEIGHTS | `health_scoring.py` | `health_scoring.py` (primitives/config) | MATCH (lctr:1, lp20m:1, sp20m:4, esp20m:3, ltv20m:2) |
| AD_QUESTION_WEIGHTS | `health_scoring.py` | `health_scoring.py` (primitives/config) | PARTIAL -- modern has only 3 components (lctr:1, lp20m:1, sp20m:1) vs legacy 4 (lctr:1, lp20m:1, sp20m:2, esp20m:4, ltv20m:3). Modern is labeled as "placeholder per PRD D-8". |

---

## 6. Recommendations for Phase 2 Scoping

### 6.1 MVP Table Selection (Minimum Viable Export)

**Recommended MVP set (8 tables)**:

| Table | Source | Effort |
|-------|--------|--------|
| BY QUARTER | Modern API (QUARTER) | Low |
| BY MONTH | Modern API (MONTH) | Low |
| BY WEEK | Modern API (WEEK) | Low |
| OFFER TABLE | Modern API (offer) | Low |
| AD QUESTIONS TABLE | Modern API (needs frame_type addition) | Low-Medium |
| APPOINTMENTS | Modern API (detail endpoint) | Medium (format translation) |
| LEADS | Modern API (detail endpoint) | Medium (format translation) |
| ASSET TABLE | Modern API (asset) | Medium (missing score, template_id) |

**Deferred to Phase 2**:

| Table | Reason | Effort to Add |
|-------|--------|---------------|
| SUMMARY | Requires ad-level distributional stats + reconciliation spend | Medium |
| BY AD SET / T7 tables | Requires ad/adset frame_type | Medium |
| LIFETIME RECONCILIATIONS | Requires payment data integration | High |
| T14 RECONCILIATIONS | Same as LIFETIME | High |
| DEMO TABLE | Requires demographic dimension pipeline | High |
| UNUSED ASSET TABLE | Client-side computation | Low (add to Phase 2 early) |

### 6.2 Format Decisions

The legacy export produces a single `.txt` file with tabulated text (`tabulate` library, `psql` format). The modern API returns JSON. Key decisions:

1. **Keep text export format?** If the export is consumed by humans reading a text file attachment in Asana, the tabulated format should be preserved. The migration layer in autom8_asana would call the modern API and format responses using `tabulate`.

2. **Switch to JSON/CSV?** If downstream consumers can be updated, JSON or CSV exports would be more machine-parseable. This is a business decision.

3. **Hybrid**: Keep the text attachment for backward compatibility but also make the data available via a new API endpoint in autom8_asana for programmatic access.

### 6.3 Architecture Decision Needed

The InsightsExport currently lives in the legacy `autom8` codebase. Its migration to autom8_asana requires a decision:

- **Option A: Thin orchestrator in autom8_asana** -- autom8_asana's export service calls `DataServiceClient` for each table, formats results, produces the text file, attaches to Asana. All data sourcing is via the modern API.

- **Option B: Gradual migration** -- Start with the GREEN tables via modern API. Keep YELLOW/RED tables calling legacy paths. Migrate table-by-table as autom8_data capabilities grow.

- **Option C: Full rewrite** -- Build the entire export pipeline in autom8_asana from scratch, using only modern APIs. Accept that some tables will be unavailable until autom8_data gaps are filled.

**Recommendation**: Option B. It is the most pragmatic path. The 5 GREEN tables can be migrated immediately. The 5 YELLOW tables can follow within the same sprint with format translation work. The 4 RED tables remain on legacy until autom8_data capabilities are extended.

### 6.4 Immediate Next Steps

1. **ADR needed**: Document the export migration strategy (Option B above)
2. **TDD needed**: Technical design for the autom8_asana export service that orchestrates calls to `DataServiceClient`
3. **autom8_data ticket**: Add `ad_question` frame_type to `FrameTypeMapper` (enables AD QUESTIONS TABLE migration)
4. **Column parity audit**: Verify `AppointmentDetailRecord` and `LeadDetailRecord` against legacy column lists
5. **Reconciliation spike**: Deep-dive on payment data access patterns to inform the reconciliation endpoint design
