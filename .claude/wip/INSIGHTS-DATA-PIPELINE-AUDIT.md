# Insights Data Pipeline Audit: Cross-Service Inventory

```yaml
status: SEED DOCUMENT
date: 2026-02-20
purpose: Deep dive seed for autom8y-data session
relates_to: [insights_export, SPIKE-attachment-format-evaluation]
next_action: Open session in ~/Code/autom8y-data for per-table deep dives
```

---

## Executive Summary

The insights_export workflow in autom8y-asana produces a 10-table HTML report for each active Offer task. These 10 tables are served by **3 distinct API endpoints** on autom8y-data, backed by **4 insight definitions** from the analytics engine's InsightRegistry (26 pre-composed queries total). This document maps every table in the consumer report to its producer pipeline, identifies gaps, and provides the triage framework for the upcoming data service deep dive.

### Key Numbers

| Metric | Value |
|--------|-------|
| Tables in report | 10 |
| API calls per offer | 9 (UNUSED ASSETS derived from ASSET TABLE) |
| Distinct autom8y-data endpoints hit | 3 |
| Insight definitions used | 4 (account_level_stats, offer_level_stats, asset_level_stats, + ad_questions) |
| Typical execution time (1 offer) | 45-56s |
| HTML output size | ~1.1MB (326 assets, 100 appts, 100 leads, 97 summary rows) |

---

## Table-to-Pipeline Cross-Reference

### Overview Map

| # | Report Table | API Endpoint | HTTP | Factory/Params | Insight Definition | Frame Type | Period |
|---|-------------|-------------|------|---------------|-------------------|------------|--------|
| 1 | **SUMMARY** | `/api/v1/data-service/insights` | POST | factory=base | `account_level_stats` | unit | lifetime |
| 2 | **APPOINTMENTS** | `/api/v1/data-service/appointments` | GET | days=90, limit=100 | *(dedicated endpoint)* | — | 90 days |
| 3 | **LEADS** | `/api/v1/data-service/leads` | GET | days=30, limit=100 | *(dedicated endpoint)* | — | 30 days |
| 4 | **BY QUARTER** | `/api/v1/data-service/insights` | POST | factory=base | `account_level_stats` | unit | quarter |
| 5 | **BY MONTH** | `/api/v1/data-service/insights` | POST | factory=base | `account_level_stats` | unit | month |
| 6 | **BY WEEK** | `/api/v1/data-service/insights` | POST | factory=base | `account_level_stats` | unit | week |
| 7 | **AD QUESTIONS** | `/api/v1/data-service/insights` | POST | factory=ad_questions | `account_level_stats` | offer | lifetime |
| 8 | **ASSET TABLE** | `/api/v1/data-service/insights` | POST | factory=assets | `asset_level_stats` | asset | t30 |
| 9 | **OFFER TABLE** | `/api/v1/data-service/insights` | POST | factory=business_offers | `offer_level_stats` | offer | t30 |
| 10 | **UNUSED ASSETS** | *(derived)* | — | — | — | — | — |

### Factory-to-Frame-Type Mapping (autom8y-asana side)

```python
FACTORY_TO_FRAME_TYPE = {
    "base":             "unit",
    "ad_questions":     "offer",
    "assets":           "asset",
    "business_offers":  "offer",
}
```

### Frame-Type-to-Insight Mapping (autom8y-data side)

```python
FRAME_TYPE_TO_INSIGHT = {
    "offer":    "offer_level_stats",
    "unit":     "account_level_stats",
    "business": "account_level_stats",
    "asset":    "asset_level_stats",
}
```

---

## Per-Table Deep Dive

### 1. SUMMARY

| Attribute | Value |
|-----------|-------|
| **Consumer call** | `client.get_insights_async(factory="base", period="lifetime")` |
| **API endpoint** | `POST /api/v1/data-service/insights` |
| **Frame type** | `unit` → insight: `account_level_stats` |
| **Period** | `LIFETIME` (all-time aggregation) |
| **Row shape** | Single row per phone: spend, imp, leads, scheds, convs, cps, ecps, cpl, etc. |
| **Observed row count** | 97 rows (E2E test, offer 1205925604226368) |
| **Data source** | DuckDB/MySQL: daily grain ad_insights → aggregated |
| **Computed fields** | `questions_asked` (separate query to prevent Cartesian) |
| **Cache** | L1: 60s memory, L2: 1hr Redis (LIFETIME) |

**Audit questions for deep dive**:
- Why 97 rows for a single phone/vertical? Is this returning multiple entities?
- What columns are included? Are they all relevant for the summary view?
- Is lifetime the right period, or should it show a rolling window?
- Column order and naming: do they match legacy report expectations?

---

### 2. APPOINTMENTS

| Attribute | Value |
|-----------|-------|
| **Consumer call** | `client.get_appointments_async(office_phone, days=90, limit=100)` |
| **API endpoint** | `GET /api/v1/data-service/appointments` |
| **Insight definition** | *(dedicated endpoint, not analytics engine)* |
| **Period** | Last 90 days rolling |
| **Row limit** | 100 (configurable via workflow params) |
| **Row shape** | Individual appointment records: date, name, status, phone, source, etc. |
| **Observed row count** | 100 rows (hit limit) |
| **Data source** | Direct DB query on appointments table |
| **Cache** | Circuit breaker + stale cache fallback |

**Audit questions for deep dive**:
- What columns does the appointment endpoint return? Full schema?
- Is 90 days the right window? Too much? Too little?
- Sorting: most recent first? Or by status?
- Is the 100-row limit causing data loss? What's the typical appointment volume?
- Status values: what are the valid statuses? Are they standardized?
- PII handling: names and phone numbers in rows — are these masked?

---

### 3. LEADS

| Attribute | Value |
|-----------|-------|
| **Consumer call** | `client.get_leads_async(office_phone, days=30, exclude_appointments=True, limit=100)` |
| **API endpoint** | `GET /api/v1/data-service/leads` |
| **Insight definition** | *(dedicated endpoint, not analytics engine)* |
| **Period** | Last 30 days rolling |
| **Row limit** | 100 (configurable) |
| **Exclude filter** | `exclude_appointments=True` (avoid double-counting) |
| **Row shape** | Individual lead records: date, source, status, contact info |
| **Observed row count** | 100 rows (hit limit) |
| **Data source** | Direct DB query on leads table |
| **Cache** | Circuit breaker + stale cache fallback |

**Audit questions for deep dive**:
- What's the `exclude_appointments` logic? Anti-join on phone/date?
- Lead vs appointment boundary: when does a lead become an appointment?
- Is 30 days appropriate? The legacy report may have used different windows.
- Column schema: what fields are returned?
- PII handling: contact info in rows

---

### 4-6. BY QUARTER / BY MONTH / BY WEEK

| Attribute | BY QUARTER | BY MONTH | BY WEEK |
|-----------|-----------|---------|---------|
| **Consumer call** | `get_insights_async(factory="base", period="quarter")` | `...period="month"` | `...period="week"` |
| **Frame type** | unit | unit | unit |
| **Insight** | `account_level_stats` | `account_level_stats` | `account_level_stats` |
| **Period** | QUARTER | MONTH | WEEK |
| **Observed rows** | 9 | 24 | 96 |
| **Data pipeline** | Daily grain → `aggregate_by_period()` post-query | Same | Same |

**Period aggregation pipeline** (autom8y-data side):
1. Fetch daily-grain data from `account_level_stats` (period=None → all-time)
2. Post-query Polars aggregation via `period_aggregator.py`
3. Group by period boundaries (quarter/month/week start)
4. Sum volume metrics (spend, imp, leads), recalculate rate metrics (cps, cpl)
5. Add `period_start`, `period_end`, `period_label` columns

**Audit questions for deep dive**:
- How far back does each period go? Is it bounded or truly all-time?
- Are rate metrics (cps, cpl) recalculated correctly from aggregated volumes?
- 96 weeks = ~1.8 years of weekly data — is this appropriate?
- Column set: same as SUMMARY or different?
- What happens when a period has zero data? Included as zeros or omitted?

---

### 7. AD QUESTIONS

| Attribute | Value |
|-----------|-------|
| **Consumer call** | `client.get_insights_async(factory="ad_questions", period="lifetime")` |
| **API endpoint** | `POST /api/v1/data-service/insights` |
| **Frame type** | `offer` → insight: `offer_level_stats` |
| **Period** | LIFETIME |
| **Row shape** | Per-offer question response data |
| **Observed row count** | 25 |
| **Special handling** | `ad_questions` factory maps to `offer` frame type |

**Audit questions for deep dive**:
- What exactly is an "ad question"? Facebook lead form questions?
- Does `offer_level_stats` insight include question data, or is this a computed field?
- `questions_asked` computed field in `account_level_stats` — is this related?
- Column schema: question text, response count, response values?
- Is this the right insight for this data, or should it have a dedicated query?

---

### 8. ASSET TABLE

| Attribute | Value |
|-----------|-------|
| **Consumer call** | `client.get_insights_async(factory="assets", period="t30")` |
| **API endpoint** | `POST /api/v1/data-service/insights` |
| **Frame type** | `asset` → insight: `asset_level_stats` |
| **Period** | T30 (trailing 30 days) |
| **Row shape** | Per-asset metrics: asset_id, asset_type, spend, imp, leads, cps, etc. |
| **Observed row count** | 326 |
| **Asset enrichment** | Category B assets (zero metrics) appended via anti-join |
| **Derived table** | UNUSED ASSETS filtered from this result |

**Asset enrichment pipeline** (autom8y-data side):
1. Query `asset_level_stats` → returns Category A assets (with ad_insights data)
2. Query full asset inventory from `assets` table
3. Anti-join: find assets NOT in Category A results
4. Append Category B assets with zero metrics
5. Deduplication for multi-vertical/multi-platform fan-out

**Audit questions for deep dive**:
- 326 assets for a single office — is this typical? Seems high.
- Category A vs B: what determines if an asset has ad_insights data?
- Asset types: image, video, carousel? What type distribution?
- `asset_link` field: URL to creative? Does it work in the HTML report?
- `transcript` field: video transcript text? How long can it be?
- `is_raw`, `is_generic`, `disabled` flags: how do these affect display?
- De-duplication logic: can one asset appear in multiple offers?

---

### 9. OFFER TABLE

| Attribute | Value |
|-----------|-------|
| **Consumer call** | `client.get_insights_async(factory="business_offers", period="t30")` |
| **API endpoint** | `POST /api/v1/data-service/insights` |
| **Frame type** | `offer` → insight: `offer_level_stats` |
| **Period** | T30 (trailing 30 days) |
| **Row shape** | Per-offer metrics: offer_id, spend, leads, scheds, convs, cpl, cps, etc. |
| **Observed row count** | 25 |
| **Data source** | Analytics engine: daily grain → T30 aggregation |

**Audit questions for deep dive**:
- 25 offers for a single office — what's the typical range?
- Are inactive/paused offers included?
- What columns are returned? Full `offer_level_stats` schema?
- `ltv` and `roas` metrics: how are these calculated?
- `budget` dimension: is this the offer-level budget or weekly budget?

---

### 10. UNUSED ASSETS (Derived)

| Attribute | Value |
|-----------|-------|
| **Source** | ASSET TABLE (table #8) response |
| **Filter logic** | `row["spend"] == 0 AND row["imp"] == 0` |
| **No API call** | Derived client-side in autom8y-asana |
| **Observed row count** | Variable (subset of 326 assets) |

**Audit questions for deep dive**:
- Is `spend == 0 AND imp == 0` the correct definition of "unused"?
- Should `disabled` assets be excluded?
- Should `is_generic` or `is_raw` assets be excluded?
- Could this be computed server-side to reduce payload?

---

## Data Service Architecture Summary

### Endpoint Architecture

```
autom8y-asana (consumer)          autom8y-data (producer)
─────────────────────────         ──────────────────────────

insights_export workflow          FastAPI Application
  │                                 │
  ├─ get_insights_async() ───────→ POST /api/v1/data-service/insights
  │   factory=base                    │
  │   period=lifetime/quarter/        ├─ InsightsService.execute()
  │          month/week               ├─ L1/L2 cache check
  │                                   ├─ FrameTypeMapper → insight name
  │   factory=ad_questions            ├─ PeriodTranslator → engine preset
  │   factory=assets                  ├─ AnalyticsEngine.execute_insight()
  │   factory=business_offers         ├─ PeriodAggregator (if quarter/month/week)
  │                                   ├─ AssetEnricher (if asset frame_type)
  │                                   └─ Response builder (200/207)
  │
  ├─ get_appointments_async() ───→ GET /api/v1/data-service/appointments
  │   days=90, limit=100              │
  │                                   └─ Direct DB query → appointment rows
  │
  └─ get_leads_async() ──────────→ GET /api/v1/data-service/leads
      days=30, limit=100              │
      exclude_appointments=true       └─ Direct DB query → lead rows
                                         (with anti-join on appointments)
```

### Analytics Engine Pipeline

```
InsightRegistry (26 insights)
    │
    ├── account_level_stats ─── SUMMARY, BY QUARTER, BY MONTH, BY WEEK
    ├── offer_level_stats ───── AD QUESTIONS, OFFER TABLE
    ├── asset_level_stats ───── ASSET TABLE (→ UNUSED ASSETS derived)
    └── (22 other insights not used by insights_export)

    ↓
InsightExecutor
    │
    ├── QueryBuilder → SQL
    ├── ConnectionPool → DuckDB/MySQL
    ├── Polars DataFrame processing
    └── Computed field evaluation
```

### Caching Tiers

| Tier | Store | TTL | Used By |
|------|-------|-----|---------|
| L1 | In-memory OrderedDict | 60s | All insight queries |
| L2 | Redis | 5min (T7/T14/T30) / 1hr (LIFETIME) | All insight queries |
| Client | autom8y-asana circuit breaker | Stale fallback on error | All tables |

---

## Gap Analysis Framework

For each table in the deep dive session, evaluate:

### Data Quality
- [ ] Column completeness: are all expected columns present?
- [ ] Data freshness: how stale can the data be?
- [ ] Null handling: are nulls meaningful or data gaps?
- [ ] Numeric precision: decimal places for currency, percentages

### Display Quality
- [ ] Column naming: snake_case → human-readable mapping
- [ ] Column ordering: most important columns first
- [ ] Value formatting: dates, currency, percentages, phone numbers
- [ ] Empty state: what shows when no data exists?

### Performance
- [ ] Query execution time per table
- [ ] Cache hit rates in production
- [ ] Payload size vs. useful data ratio
- [ ] Row limit appropriateness

### Parity with Legacy
- [ ] Compare legacy .txt columns with current API response columns
- [ ] Identify missing columns from legacy format
- [ ] Identify new columns not in legacy format
- [ ] Identify columns with different names/formats

### Production Readiness
- [ ] Error handling: graceful degradation per table
- [ ] PII: phone numbers, names, addresses in row data
- [ ] Rate limiting: impact of batch queries at scale (3,769 offers)
- [ ] Monitoring: per-table success/failure metrics

---

## Recommended Deep Dive Order

Priority based on complexity and impact:

1. **SUMMARY** — Most visible table, highest column count, sets the tone
2. **APPOINTMENTS** / **LEADS** — Direct DB queries, PII concerns, limit tuning
3. **ASSET TABLE** / **UNUSED ASSETS** — 326 rows, enrichment pipeline, derived table logic
4. **BY QUARTER / MONTH / WEEK** — Period aggregation correctness, rate recalculation
5. **AD QUESTIONS** — Unclear data model, may need dedicated insight
6. **OFFER TABLE** — Straightforward but needs column audit

---

## Files Reference

### autom8y-asana (consumer)
| File | Role |
|------|------|
| `src/autom8_asana/automation/workflows/insights_export.py` | Workflow orchestrator, `_fetch_all_tables()` |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | HTML renderer, `compose_report()` |
| `src/autom8_asana/clients/data/client.py` | DataServiceClient, API call methods |
| `src/autom8_asana/clients/data/_endpoints/insights.py` | `execute_insights_request()` HTTP impl |
| `src/autom8_asana/clients/data/_endpoints/simple.py` | `get_appointments()`, `get_leads()` HTTP impl |
| `src/autom8_asana/clients/data/models.py` | InsightsResponse, InsightsRequest models |
| `src/autom8_asana/clients/data/config.py` | DataServiceConfig, timeouts, retry |

### autom8y-data (producer)
| File | Role |
|------|------|
| `src/autom8_data/api/routes/data_service.py` | `/api/v1/data-service/*` endpoint handlers |
| `src/autom8_data/api/routes/insights.py` | `/api/v1/insights/*` endpoint handlers |
| `src/autom8_data/api/services/insights_service.py` | InsightsService, batch execution, asset enrichment |
| `src/autom8_data/api/services/frame_type_mapper.py` | Frame type → insight name mapping |
| `src/autom8_data/api/services/period_translator.py` | Period literal → engine preset |
| `src/autom8_data/api/services/period_aggregator.py` | Post-query period aggregation |
| `src/autom8_data/api/services/cache.py` | L1/L2 tiered cache |
| `src/autom8_data/analytics/engine.py` | AnalyticsEngine core |
| `src/autom8_data/analytics/insights/library.py` | 26 insight definitions |
| `src/autom8_data/analytics/insights/registry.py` | InsightRegistry |
| `src/autom8_data/analytics/insights/computed_fields.py` | Computed field specs |
