# Insights Export Pipeline -- Canonical Context

**Date**: 2026-02-20
**Status**: Last 10% -- polish, reconciliation UX, row limits, smoke validation
**Smoke target**: Offer `1211872268838349`

---

## TL;DR

The insights export pipeline generates a daily HTML report for each active Asana Offer task. It fetches 12 tables of analytics data from autom8y-data, renders them into a self-contained HTML document, and uploads the result as an Asana attachment. The pipeline is fully operational: 7 of 12 tables are CORRECT, 2 are data-pending (Stripe REC-8), 3 have UX limitations (row caps, overflow). The remaining work is display-layer polish and a production smoke test.

---

## 1. Business Context

Each Offer in Asana represents a marketing campaign for a business location (identified by `office_phone` + `vertical`). Account managers need a daily snapshot of performance metrics, lead flow, appointment conversions, asset performance, and financial reconciliation. The insights export replaces manual data pulls with an automated HTML attachment on each Offer task.

---

## 2. End-to-End Architecture

```
EventBridge (6AM ET daily)
    |
    v
Lambda handler (insights_export.py)
    |
    v
WorkflowHandlerConfig
    |-- EntityScope.from_event(event) --> targeted GIDs or full enumeration
    |-- DataServiceClient (async context manager)
    |-- InsightsExportWorkflow
            |
            |-- validate_async()   : feature flag + circuit breaker
            |-- enumerate_async()  : section-targeted Offer discovery
            |-- execute_async()    : Semaphore(max_concurrency=5)
                    |
                    |-- _process_offer() per Offer:
                    |       |-- _resolve_business() --> office_phone, vertical, business_name
                    |       |-- _fetch_all_tables() --> 11 API calls + 1 derived
                    |       |-- compose_report()    --> HTML string
                    |       |-- upload attachment (upload-first atomicity)
                    |       |-- delete old attachments (*.html + legacy *.md)
                    |
                    v
              WorkflowResult (per-offer table tracking in metadata)
```

**Key behaviors**:
- Business hierarchy caching (AT3-001): dedup on `offer_gid` prevents redundant Business API traversals
- Upload-first atomicity: new attachment uploaded before old ones deleted
- Stale cache fallback on `InsightsServiceError`
- PII redaction: `mask_phone_number()` in logs and HTML headers
- Circuit breaker: `DataServiceClient` with connect 5.0s, read 30.0s, pool max 10

---

## 3. Twelve-Table Inventory

### 3.1 Table-to-API Mapping

| # | Table | Method | API Call | Factory/Endpoint | Period | Row Behavior |
|---|-------|--------|----------|-----------------|--------|-------------|
| 1 | SUMMARY | insights | POST /insights | `base` (unit frame) | `lifetime` | 1 row |
| 2 | APPOINTMENTS | detail | GET /appointments | days=90 | last 90d | limit param |
| 3 | LEADS | detail | GET /leads | days=30, exclude_appts | last 30d | limit param |
| 4 | LIFETIME RECONCILIATIONS | reconciliation | POST /insights/reconciliation/execute | -- | LIFETIME (period=None) | 1 row |
| 5 | T14 RECONCILIATIONS | reconciliation | POST /insights/reconciliation/execute | -- | window_days=14 | N windows |
| 6 | BY QUARTER | insights | POST /insights | `base` (unit frame) | `quarter` | N periods |
| 7 | BY MONTH | insights | POST /insights | `base` (unit frame) | `month` | N periods |
| 8 | BY WEEK | insights | POST /insights | `base` (unit frame) | `week` | N periods |
| 9 | AD QUESTIONS | insights | POST /insights | `ad_questions` (question frame) | `lifetime` | N questions |
| 10 | ASSET TABLE | insights | POST /insights | `assets` (asset frame) | `t30` | unbounded |
| 11 | OFFER TABLE | insights | POST /insights | `business_offers` (offer frame) | `t30` | N offers |
| 12 | UNUSED ASSETS | derived | -- (filtered from #10) | -- | t30 | subset of #10 |

### 3.2 Correctness Status

| # | Table | Status | Detail |
|---|-------|--------|--------|
| 1 | SUMMARY | CORRECT | Fixed H-03: `_PERIOD_NOT_SET` sentinel prevents 97-row bug |
| 2 | APPOINTMENTS | PARTIAL | H-06: row limit hard-coded at 100; server max is 500 |
| 3 | LEADS | PARTIAL | H-06: row limit hard-coded at 100; server max is 500 |
| 4 | LIFETIME RECONCILIATIONS | DATA PENDING | H-01: Stripe REC-8 not live; payment cols null |
| 5 | T14 RECONCILIATIONS | DATA PENDING | H-01: same as above |
| 6 | BY QUARTER | CORRECT | Period columns ordered left via COLUMN_ORDER |
| 7 | BY MONTH | CORRECT | Period columns ordered left via COLUMN_ORDER |
| 8 | BY WEEK | CORRECT | Period columns ordered left via COLUMN_ORDER |
| 9 | AD QUESTIONS | CORRECT | Fixed H-02: frame_type corrected to `question` |
| 10 | ASSET TABLE | PARTIAL | H-09: unbounded rows (300+); H-07: transcript overflow; H-08: ANY_VALUE non-determinism |
| 11 | OFFER TABLE | CORRECT | |
| 12 | UNUSED ASSETS | CORRECT | Fixed H-05: disabled/is_generic excluded |

**Scorecard**: 7 CORRECT, 2 DATA PENDING (external blocker), 3 PARTIAL (UX issues, actionable now)

---

## 4. Data Producer Inventory (autom8y-data)

### 4.1 Insight Definitions

| Insight | Frame type | Key metrics | Grain |
|---------|-----------|-------------|-------|
| `account_level_stats` | unit/business | 24 (volume, appt status, rates, per-20k) | office_phone x vertical |
| `offer_level_stats` | offer | 10 | offer_id x office_phone x vertical |
| `asset_level_stats` | asset | 23 | asset_id x office_phone x vertical |
| `question_level_stats` | question | 11 + n_distinct_ads | question_key x priority x office_phone x vertical |
| `reconciliation` | runtime frame | 10 financial | office_phone x vertical |

### 4.2 API Endpoints

| Endpoint | Method | Purpose | Caching |
|----------|--------|---------|---------|
| POST /api/v1/data-service/insights | POST | Primary insights query | L1 in-mem 60s + L2 Redis (period-dependent TTL) |
| POST /api/v1/data-service/gid-map | POST | GID lookup (currently mock) | -- |
| GET /api/v1/data-service/appointments | GET | Appointment detail list | Redis TTL by period |
| GET /api/v1/data-service/leads | GET | Lead detail list | Redis TTL by period |

### 4.3 Aggregation Pipeline

`aggregate_by_window()`: fixed-width non-overlapping windows anchored to most recent date. Returns `period_label` (P0=most recent), `period_start`, `period_end`, `period_len`. Rate metrics recomputed from windowed volumes with safe division.

`_PRECISION_RULES`: 32 fields -- currency at 2dp, rate at 4dp, pct at 2dp, per20k at 2dp.

Aggregation constants: `SUM_METRICS` (34), `RATE_METRIC_FORMULAS` (17), `PER_20K_FORMULAS` (4).

---

## 5. Display Layer (autom8y-asana)

### 5.1 Rendering Pipeline

```
InsightsReportData
    |
    v
compose_report()           # insights_formatter.py:363
    |-- Build metadata     # Phone (masked), Vertical, Generated, Period
    |-- Build sections     # TABLE_ORDER loop, row_limits truncation
    |-- Build footer       # Duration, Tables N/12, Errors, Version
    |
    v
HtmlRenderer.render_document()
    |-- _render_doctype_and_head()  # Inline CSS, no external resources
    |-- _render_header()            # Title + metadata
    |-- Per section:
    |     |-- _render_table_section()  # Column discovery, reorder, format cells
    |     |-- _render_empty_section()  # "No data available"
    |     |-- _render_error_section()  # "[ERROR] type: message"
    |-- _render_footer()
    v
Complete self-contained HTML string
```

### 5.2 Column Ordering

`COLUMN_ORDER` (insights_formatter.py:50-75): Preferred leading columns per table.
- Period tables (BY QUARTER/MONTH/WEEK): `period_label`, `period_start`, `period_end`
- LIFETIME RECONCILIATIONS: `office_phone`, `vertical`, `num_invoices`, `collected`, `spend`, `variance`, `variance_pct`
- T14 RECONCILIATIONS: `period`, `period_label`, `period_start`, `period_end`, `period_len`, `num_invoices`, `collected`, `spend`, `variance`, `variance_pct`

### 5.3 Field Formatting (_FIELD_FORMAT)

`_FIELD_FORMAT` (insights_formatter.py:485-506): 32 fields mapped to 5 format categories.

| Category | Count | Example output | Fields |
|----------|-------|---------------|--------|
| currency | 16 | `$12,847.50` | spend, cpl, cps, ecps, cpc, ltv, avg_conv, collected, variance, expected_collection, expected_variance, offer_cost, budget, expected_spend, projected_spend, budget_variance |
| rate | 10 | `3.42%` (decimal x 100) | ctr, lctr, conversion_rate, booking_rate, ns_rate, nc_rate, conv_rate, nsr_ncr, sched_rate, pacing_ratio |
| percentage | 1 | `42.50%` (already in %) | variance_pct |
| ratio | 1 | `3.50x` (ROAS multiplier) | roas |
| per20k | 4 | `12.50` | lp20m, sp20m, esp20m, ltv20m |
| (fallback) | -- | int: `45,000`; float: `123.46` | all unlisted fields |

### 5.4 HTML Features

- Self-contained: all CSS inlined, zero external dependencies
- XSS prevention: `html.escape()` on all dynamic content
- Zebra striping on table rows
- Numeric right-alignment via `_column_align_class()`
- Truncation notes: "Showing N of M rows" when `row_limits` applied
- Print styles for clean printing
- Section IDs via `_slugify()` for anchor links

---

## 6. Build History (Complete)

### Phase 1: Core Pipeline
- WorkflowAction base class + WorkflowHandlerConfig factory
- InsightsExportWorkflow: enumerate, resolve, fetch, compose, upload
- 10-table fetch via asyncio.gather() + error isolation per table
- AttachmentReplacementMixin: upload-first atomicity
- Section-targeted enumeration with project-level fallback

### Phase 2: Data Correctness (H-series fixes)
- **H-02**: AD QUESTIONS frame_type corrected from `offer` to `question` in FACTORY_TO_FRAME_TYPE
- **H-03**: SUMMARY 97-row bug fixed via `_PERIOD_NOT_SET` sentinel in insight_executor
- **H-05**: UNUSED ASSETS filter: exclude `disabled` and `is_generic` assets

### Phase 3: Display Layer
- StructuredDataRenderer protocol + HtmlRenderer implementation
- Markdown-to-HTML migration (compose_report returns HTML, not markdown)
- `_FIELD_FORMAT` with 32 field mappings across 5 format categories
- `_format_cell_html()` with None-as-dash rendering
- COLUMN_ORDER for period and reconciliation tables

### Phase 4: Extended Tables
- LIFETIME RECONCILIATIONS + T14 RECONCILIATIONS added (tables 4-5)
- `get_reconciliation_async()` client method using InsightExecutor endpoint
- `window_days` parameter threading through `_fetch_table()`
- TOTAL_TABLE_COUNT bumped from 10 to 12

### Phase 5: Polish
- Period column reordering (left-anchored in time-series tables)
- Legacy attachment cleanup (*.md pattern for pre-migration)
- Business hierarchy caching (AT3-001)
- PII redaction in logs and headers
- Row limits with truncation display

---

## 7. Open Items -- The Last 10%

### P0 -- Before claiming full parity

| ID | Issue | Scope | Est | Detail |
|----|-------|-------|-----|--------|
| H-01 | Reconciliation null payment data | Display | 0.5d | Tables 4-5 show nulls for collected, num_invoices, variance until Stripe REC-8 ships. Add "Payment data pending" indicator in section header, OR show empty-message placeholder instead of null-filled rows. |

### P1 -- Significant UX

| ID | Issue | Scope | Est | Detail |
|----|-------|-------|-----|--------|
| H-06 | APPOINTMENTS/LEADS row limit too low | Config | 0.25d | Hard-coded at 100 in `default_params`. Server max is 500. Raise to 250. |

### P2 -- Polish

| ID | Issue | Scope | Est | Detail |
|----|-------|-------|-----|--------|
| H-07 | Transcript column overflow | CSS | 0.25d | ASSET TABLE `transcript` field contains full video transcripts. Add `max-height` + overflow clip on long text cells. |
| H-09 | ASSET TABLE unbounded rows | Config | 0.25d | Can have 300+ rows (T30). Add `row_limits["ASSET TABLE"] = 150`, sort by spend desc. |
| H-10 | `n_distinct_ads` display label | Formatter | 0.1d | Renders as "N Distinct Ads" via `_to_title_case()`. Add display label override dict. |
| H-08 | ANY_VALUE non-determinism note | Display | 0.1d | Assets on multiple offers get arbitrary offer_id. Consider section header note. |

### Missing Tests

| Gap | Scope | Detail |
|-----|-------|--------|
| 12-table count assertion | Unit | No test verifies `len(table_results) == 12` in workflow output |
| Reconciliation fetch mock | Unit | No test for `_fetch_table()` with `method="reconciliation"` path |
| `window_days` threading | Unit | No test verifies `window_days=14` reaches `get_reconciliation_async()` |

### Smoke Test

Full pipeline run on offer `1211872268838349` with per-table verification. See `INSIGHTS_EXPORT-SMOKETEST-2026-02-20.md`.

---

## 8. Key File Reference

### autom8y-asana (`/Users/tomtenuta/Code/autom8y-asana/`)

| File | Line(s) | Content |
|------|---------|---------|
| `src/autom8_asana/lambda_handlers/insights_export.py` | 36-48 | Lambda entry point, WorkflowHandlerConfig |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | 68-178 | Generic handler factory, EntityScope construction |
| `src/autom8_asana/automation/workflows/insights_export.py` | 69-84 | TABLE_NAMES, TOTAL_TABLE_COUNT |
| `src/autom8_asana/automation/workflows/insights_export.py` | 63-66 | DEFAULT_ROW_LIMITS |
| `src/autom8_asana/automation/workflows/insights_export.py` | 690-849 | `_fetch_all_tables()`, 11 gather calls + UNUSED ASSETS derivation |
| `src/autom8_asana/automation/workflows/insights_export.py` | 851-950 | `_fetch_table()` dispatch (appointments/leads/reconciliation/insights) |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | 33-46 | TABLE_ORDER |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | 50-75 | COLUMN_ORDER |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | 485-506 | `_FIELD_FORMAT` (32 fields) |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | 509-530 | `_format_cell_html()` |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | 363-456 | `compose_report()` |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | 464-475 | `_to_title_case()` |
| `src/autom8_asana/clients/data/client.py` | 650-665 | FACTORY_TO_FRAME_TYPE |
| `src/autom8_asana/clients/data/client.py` | 1202-1227 | `get_reconciliation_async()` |
| `src/autom8_asana/core/scope.py` | 39-63 | `EntityScope.from_event()` |
| `tests/unit/automation/workflows/test_insights_formatter.py` | -- | 139 tests |
| `tests/unit/automation/workflows/test_insights_export.py` | -- | ~100 tests |
| `tests/unit/lambda_handlers/test_insights_export.py` | -- | Lambda handler tests |

### autom8y-data (`/Users/tomtenuta/Code/autom8y-data/`)

| File | Content |
|------|---------|
| `src/autom8_data/analytics/insights/library.py` | All 5 InsightDefinitions |
| `src/autom8_data/api/services/frame_type_mapper.py` | Frame type to insight mapping |
| `src/autom8_data/api/services/insights_service.py` | Precision rules, FR-7 filter |
| `src/autom8_data/api/services/period_aggregator.py` | `aggregate_by_window()` |
| `src/autom8_data/analytics/insight_executor.py` | `_PERIOD_NOT_SET` sentinel |
| `src/autom8_data/api/routes/data_service.py` | 4 endpoints |
