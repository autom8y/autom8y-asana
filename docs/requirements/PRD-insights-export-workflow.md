# PRD: InsightsExportWorkflow

```yaml
id: PRD-EXPORT-001
status: stakeholder-approved
author: requirements-analyst
date: 2026-02-12
impact: high
impact_categories: [cross_service, api_contract]
complexity: MODULE
sprints: TBD (Pythia orchestration)
stakeholder_interview: 15 decisions confirmed
```

## 1. Problem Statement

Account managers rely on daily insights reports attached to offer tasks in Asana to monitor ad performance, lead flow, and appointment activity. The current export is produced by a legacy `run_export` job that predates the modern autom8_data insights API and the WorkflowAction batch framework. This legacy job:

1. **Cannot leverage modern data**: It queries legacy database views rather than the autom8_data insights service, which now provides reconciliation-validated, period-aware, multi-frame-type analytics.
2. **Is the only remaining scheduled job outside the WorkflowAction pattern**: The conversation audit workflow (ConversationAuditWorkflow) established the canonical pattern for batch Asana attachment workflows -- enumerate targets, resolve per-target context, fetch data from autom8_data, upload attachment, clean up old attachments. The export job duplicates this lifecycle with ad-hoc code.
3. **Uses legacy column names**: Column naming follows the old database schema (e.g., `ad_spend`, `last_7_days`). Account managers and any tooling downstream must mentally translate between legacy and modern naming conventions.

The InsightsExportWorkflow replaces `run_export` with a WorkflowAction that uses the existing DataServiceClient to produce markdown insights reports attached to offer tasks. This is a v0 scope: export only. No other legacy job migrations (algo_optimizations, customer_health, pull_insights) are in this release.

### Current State

| Component | Status |
|-----------|--------|
| ConversationAuditWorkflow | Production. Established WorkflowAction + Lambda handler + EventBridge pattern. |
| DataServiceClient | Production. `get_insights_async()` supports all frame_types; `get_export_csv_async()` supports conversation CSV. No appointment/lead detail endpoints yet. |
| `_normalize_period()` | Supports LIFETIME, T7, T14, T30. Does NOT support QUARTER, MONTH, WEEK. |
| Legacy `run_export` | Production. EventBridge-scheduled. Produces CSV attachments on offer tasks. |
| Reconciliation fields | Validated in autom8_data code, deploying to production. |

### Why Now

- The ConversationAuditWorkflow proved the pattern. InsightsExportWorkflow is the second instance, validating the WorkflowAction framework as a general-purpose batch primitive.
- The modern insights API provides richer, validated data. Every day the legacy job runs is another day of stale-schema reports.
- Account managers are the sole consumers. A clean break to modern naming is low-risk with high clarity gain.

---

## 2. Stakeholders & Consumers

| Stakeholder | Role | Interest |
|-------------|------|----------|
| Account Managers (AMs) | Primary consumer | Read daily markdown reports in Asana. Only human readers. No programmatic consumers. |
| Operations | System owner | Scheduling, monitoring, rollout. Needs observability and kill switch. |
| autom8_data team | Upstream dependency | Provides insights API, reconciliation fields, and (future) asset_score. |
| Platform | Infrastructure | Lambda timeout, EventBridge rules, feature flag conventions. |

---

## 3. Scope

### 3.1 In-Scope Tables (10)

| # | Table Name | Description |
|---|-----------|-------------|
| 1 | SUMMARY | Lifetime aggregated metrics for the offer (single row) |
| 2 | APPOINTMENTS | Recent appointment detail rows (90 days, max 100) |
| 3 | LEADS | Recent lead detail rows (30 days, excluding appointments, max 100) |
| 4 | BY QUARTER | Unit metrics broken down by quarter |
| 5 | BY MONTH | Unit metrics broken down by month |
| 6 | BY WEEK | Unit metrics broken down by week |
| 7 | AD QUESTIONS | Offer-level metrics with question dimension (lifetime) |
| 8 | ASSET TABLE | Per-asset metrics (T30), asset_score deferred to autom8_data |
| 9 | OFFER TABLE | Per-offer metrics (T30) |
| 10 | UNUSED ASSETS | Assets with zero spend AND zero impressions (client-side filter on asset insights) |

### 3.2 Deferred Tables (5)

| Table | Rationale | Phase |
|-------|-----------|-------|
| LIFETIME RECONCILIATIONS | Requires payment data integration not yet in modern pipeline | Phase 2 |
| T14 RECONCILIATIONS | Same as above | Phase 2 |
| DEMO TABLE | Requires 7 demographic sub-queries not in modern pipeline | Phase 2 |
| T7 BY AD | `ad` frame_type does not exist in autom8_data yet | Phase 2 |
| T7 BY ADSET | `adset` frame_type does not exist in autom8_data yet | Phase 2 |

### 3.3 Out of Scope

| Item | Rationale |
|------|-----------|
| Other legacy job migrations (algo_optimizations, customer_health, pull_insights) | v0 scope is InsightsExportWorkflow only |
| Programmatic consumers / API endpoint for export | AMs are the only consumers; Asana attachment is the delivery mechanism |
| Format fidelity to legacy CSV | Clean break. Markdown with modern column names. |
| template_id support | Not required for MVP |
| Reconciliation tables | Payment data integration is future autom8_data work |
| Asset score computation in autom8_asana | Must be computed by autom8_data HealthScoreService |
| Phase 2: unused assets that have no insights row at all | MVP filter only catches assets with a row where spend=0 AND imp=0 |

---

## 4. Requirements

### W01: Core Workflow (WorkflowAction Protocol)

The InsightsExportWorkflow SHALL implement the WorkflowAction protocol (workflow_id, execute_async, validate_async) following the ConversationAuditWorkflow pattern.

**FR-W01.1: Workflow Identity**
- `workflow_id` = `"insights-export"`
- Registered in WorkflowRegistry at application startup

**FR-W01.2: Pre-flight Validation (validate_async)**
- Check feature flag `AUTOM8_EXPORT_ENABLED` (environment variable)
- Check DataServiceClient circuit breaker state
- Return list of validation error strings (empty = ready)

**FR-W01.3: Offer Enumeration**
- Enumerate active (non-completed) offer tasks from the BusinessOffers project
- Use paginated task listing with `completed_since="now"` filter
- Fetch opt_fields: `["name", "completed", "parent", "parent.name"]`

**FR-W01.4: Per-Offer Resolution**
- Resolve each offer to `office_phone` and `vertical` via ResolutionContext
- Resolution path: Offer task -> parent Business -> `office_phone` descriptor + `vertical` descriptor
- Skip offers where office_phone or vertical cannot be resolved (status = "skipped", reason = "no_resolution")

**FR-W01.5: Per-Offer Data Fetch**
- Fetch all 10 in-scope tables via DataServiceClient
- Use `asyncio.gather()` for parallel table fetches within a single offer (all 10 calls dispatched concurrently per offer)
- Each table maps to a specific API call (see Appendix: Table-to-API-Call Mapping)

**FR-W01.6: Markdown Report Composition**
- Compose a single markdown (.md) document per offer from the 10 table responses
- Section order: Header -> SUMMARY -> APPOINTMENTS -> LEADS -> BY QUARTER -> BY MONTH -> BY WEEK -> AD QUESTIONS -> ASSET TABLE -> OFFER TABLE -> UNUSED ASSETS -> Footer
- Format specification defined in W03

**FR-W01.7: Attachment Upload (Upload-First Pattern)**
- Upload new .md attachment to the offer task BEFORE deleting old attachments
- File naming: `insights_export_{BusinessName}_{YYYYMMDD}.md`
- BusinessName sanitized: spaces replaced with underscores, non-alphanumeric characters stripped
- Content-Type: `text/markdown`

**FR-W01.8: Old Attachment Cleanup**
- After successful upload, delete old attachments matching `insights_export_*.md` glob pattern
- Exclude the just-uploaded file from deletion
- Delete failure is non-fatal (next run cleans up duplicates)

**FR-W01.9: Concurrency Control**
- `asyncio.Semaphore` with configurable max_concurrency (default = 5)
- Controls how many offers are processed in parallel
- Configurable via params dict: `max_concurrency`

**FR-W01.10: WorkflowResult Reporting**
- Return WorkflowResult with total/succeeded/failed/skipped counts
- `metadata` dict includes:
  - `per_offer_table_counts`: dict mapping offer GID to `{"tables_succeeded": int, "tables_failed": int}`
  - `total_tables_succeeded`: int
  - `total_tables_failed`: int

**Priority**: MUST

**Acceptance Criteria**:
- AC-W01.1: InsightsExportWorkflow implements WorkflowAction ABC (workflow_id, execute_async, validate_async)
- AC-W01.2: validate_async returns error when AUTOM8_EXPORT_ENABLED=false
- AC-W01.3: validate_async returns error when DataServiceClient circuit breaker is open
- AC-W01.4: execute_async enumerates only non-completed offers from BusinessOffers project
- AC-W01.5: Each offer is resolved to office_phone and vertical via ResolutionContext
- AC-W01.6: Offers with no office_phone or vertical are skipped with reason logged
- AC-W01.7: All 10 table API calls are dispatched concurrently per offer
- AC-W01.8: A single markdown file is uploaded per offer with correct naming convention
- AC-W01.9: Old insights_export_*.md attachments are deleted after successful upload
- AC-W01.10: Upload-first: new attachment exists before old ones are removed
- AC-W01.11: Concurrency is bounded by Semaphore (default 5 concurrent offers)
- AC-W01.12: WorkflowResult includes total/succeeded/failed/skipped and per-offer table counts in metadata

---

### W02: Partial Export with Error Markers

The workflow SHALL produce a partial report when some but not all tables fail for an offer.

**FR-W02.1: Per-Table Error Isolation**
- Each of the 10 table fetches is individually wrapped in error handling
- A failed table does not prevent other tables from rendering
- Failed tables produce an error marker section in the markdown output

**FR-W02.2: Error Marker Format**
- Failed table sections render as:
  ```markdown
  ## TABLE_NAME
  > [ERROR] {error_type}: {message}
  ```
- `error_type`: Classification (e.g., `InsightsServiceError`, `InsightsNotFoundError`, `timeout`, `circuit_breaker`)
- `message`: Human-readable description

**FR-W02.3: Total Failure Handling**
- If ALL 10 tables fail for a single offer, mark the offer as failed
- Do NOT upload an empty report (no attachment created)
- Log the offer as failed with all 10 error details

**FR-W02.4: Per-Offer Table Tracking**
- WorkflowResult.metadata tracks per-offer table success/failure counts
- Format: `{offer_gid: {"tables_succeeded": N, "tables_failed": M}}`

**Priority**: MUST

**Acceptance Criteria**:
- AC-W02.1: When 1 of 10 tables fails, the report still contains the other 9 tables plus an error marker for the failed table
- AC-W02.2: Error marker sections include table name, error type, and human-readable message
- AC-W02.3: When all 10 tables fail for an offer, no attachment is uploaded and the offer is marked failed
- AC-W02.4: WorkflowResult.metadata contains per-offer table success and failure counts
- AC-W02.5: Error markers are valid markdown (blockquote syntax)

---

### W03: Markdown Report Format

The workflow SHALL produce valid markdown documents with pipe tables.

**FR-W03.1: File Format**
- Markdown (.md) with pipe tables
- Asana renders markdown in attachment previews (confirmed)
- File extension: `.md`

**FR-W03.2: Header Section**
- Business name
- Office phone (masked: `+1770***3103` format via `mask_phone_number()`)
- Vertical
- Report generation timestamp (UTC ISO 8601)
- Report date range description

**FR-W03.3: Table Sections**
- Each table is a level-2 heading (`## TABLE_NAME`)
- Data rendered as markdown pipe tables with header row and alignment row
- Empty tables (zero rows from API) render as `> No data available` instead of empty pipe table

**FR-W03.4: Column Naming**
- Use modern autom8_data column names throughout (offer_cost, period_label, etc.)
- Clean break from legacy naming (no backward-compatible aliases)
- Column names formatted as Title Case for display (e.g., `offer_cost` -> `Offer Cost`)

**FR-W03.5: Null Field Handling**
- Columns with always-null values are included (not omitted):
  - APPOINTMENTS: out_calls, in_calls, time_on_call
  - LEADS: follow_up, convo, lead_call_time
- Null values rendered as dash marker: `---`

**FR-W03.6: Row Limits**
- Row limits are configurable per table type via params dict
- Defaults:
  - APPOINTMENTS: 100 rows
  - LEADS: 100 rows
  - BY QUARTER / BY MONTH / BY WEEK: no limit (all rows from API)
  - All other tables: no limit
- If row limit is reached, a note is appended below the table: `> Showing first {N} of {total} rows`

**FR-W03.7: Footer Section**
- Generation duration (seconds, 2 decimal places)
- Table count: `{succeeded}/{total}` (e.g., `9/10`)
- Error count (if any)
- Workflow version identifier

**FR-W03.8: Unused Assets Filter**
- UNUSED ASSETS table is derived from the same ASSET TABLE API response
- Client-side filter: include rows where `spend == 0 AND imp == 0`
- If no rows match the filter, render `> No unused assets found`
- Known limitation (documented, not a bug): assets with no insights row at all are not captured

**Priority**: MUST

**Acceptance Criteria**:
- AC-W03.1: Generated file is valid markdown parseable by standard markdown processors
- AC-W03.2: Header includes masked phone number, business name, vertical, and UTC timestamp
- AC-W03.3: Each table section uses level-2 headings and pipe table syntax
- AC-W03.4: All column names use modern autom8_data naming convention in Title Case
- AC-W03.5: Always-null columns (out_calls, in_calls, time_on_call, follow_up, convo, lead_call_time) are present with `---` markers
- AC-W03.6: Pipe tables include header row, alignment row, and data rows
- AC-W03.7: Empty tables show "No data available" note instead of empty table
- AC-W03.8: Footer includes generation duration, table count, and error count
- AC-W03.9: UNUSED ASSETS table correctly filters on spend==0 AND imp==0 from asset response
- AC-W03.10: Row limit truncation note appears when limit is reached
- AC-W03.11: File naming follows `insights_export_{BusinessName}_{YYYYMMDD}.md` convention

---

### W04: DataServiceClient Extensions

The DataServiceClient SHALL be extended with new methods and period normalization to support the 10-table scope.

**FR-W04.1: get_appointments_async()**
- Signature: `get_appointments_async(office_phone: str, *, days: int = 90, limit: int = 100) -> InsightsResponse`
- Maps to: `GET /appointments` on autom8_data (new endpoint)
- Query parameters: `office_phone`, `days`, `limit`
- Uses same circuit breaker, retry handler, auth infrastructure as `get_insights_async()`
- PII masking in all log output

**FR-W04.2: get_leads_async()**
- Signature: `get_leads_async(office_phone: str, *, days: int = 30, exclude_appointments: bool = True, limit: int = 100) -> InsightsResponse`
- Maps to: `GET /leads` on autom8_data (new endpoint)
- Query parameters: `office_phone`, `days`, `exclude_appointments`, `limit`
- Uses same circuit breaker, retry handler, auth infrastructure as `get_insights_async()`
- PII masking in all log output

**FR-W04.3: Extend _normalize_period()**
- Add support for QUARTER, MONTH, WEEK period values
- Mapping:
  - `"quarter"` -> `"QUARTER"`
  - `"month"` -> `"MONTH"`
  - `"week"` -> `"WEEK"`
- Existing mappings unchanged (LIFETIME, T7, T14, T30)

**FR-W04.4: InsightsRequest Period Validation**
- Extend `InsightsRequest.validate_period()` to accept `quarter`, `month`, `week` as valid period formats

**Priority**: MUST

**Acceptance Criteria**:
- AC-W04.1: `get_appointments_async()` returns appointment detail rows with PII masking
- AC-W04.2: `get_appointments_async()` respects circuit breaker and retry configuration
- AC-W04.3: `get_leads_async()` returns lead detail rows excluding appointments by default
- AC-W04.4: `get_leads_async()` respects circuit breaker and retry configuration
- AC-W04.5: `_normalize_period("quarter")` returns `"QUARTER"`
- AC-W04.6: `_normalize_period("month")` returns `"MONTH"`
- AC-W04.7: `_normalize_period("week")` returns `"WEEK"`
- AC-W04.8: Existing period normalization (LIFETIME, T7, T14, T30) is unchanged
- AC-W04.9: `InsightsRequest(insights_period="quarter")` passes validation
- AC-W04.10: Both new methods log with masked phone numbers

---

### W05: Scheduling and Deployment

The workflow SHALL be deployed as a Lambda handler triggered by EventBridge.

**FR-W05.1: Lambda Handler**
- New module: `lambda_handlers/insights_export.py`
- Follow the ConversationAuditWorkflow Lambda handler pattern exactly:
  - `handler(event, context)` entry point calling `asyncio.run(_handler_async(...))`
  - Client initialization within `_execute()` function
  - Pre-flight validation before execution
  - Structured JSON response with status, counts, and duration
- Register in `lambda_handlers/__init__.py`

**FR-W05.2: EventBridge Schedule**
- Schedule: Once daily, 6:00 AM Eastern Time
- Cron expression: `cron(0 11 * * ? *)` (11:00 UTC = 6:00 AM ET, accounting for EST; 10:00 UTC during EDT)
- Rule name convention consistent with existing EventBridge rules

**FR-W05.3: Feature Flag (Kill Switch)**
- Environment variable: `AUTOM8_EXPORT_ENABLED`
- Default behavior: enabled (missing or empty env var = enabled)
- Disable values: `"false"`, `"0"`, `"no"` (case-insensitive)
- Checked in `validate_async()` before any data fetching

**FR-W05.4: WorkflowRegistry Registration**
- Register InsightsExportWorkflow in WorkflowRegistry
- Registration follows existing pattern from ConversationAuditWorkflow

**FR-W05.5: Lambda Timeout**
- Default: 15 minutes (900 seconds)
- Configurable via Lambda configuration (not code)
- Workflow should complete well under timeout for typical offer counts

**FR-W05.6: Rollout Strategy**
- Hard cutover: disable legacy `run_export` EventBridge rule, enable new InsightsExportWorkflow rule
- No parallel running period
- No rollback plan. Fix forward if issues arise. Confidence is high.
- Feature flag `AUTOM8_EXPORT_ENABLED` serves as kill switch if emergency disable is needed

**Priority**: MUST

**Acceptance Criteria**:
- AC-W05.1: Lambda handler module exists at `lambda_handlers/insights_export.py`
- AC-W05.2: Lambda handler follows conversation_audit.py handler pattern (asyncio.run, _handler_async, _execute)
- AC-W05.3: Lambda handler is registered in `lambda_handlers/__init__.py`
- AC-W05.4: EventBridge rule triggers at 6:00 AM ET daily
- AC-W05.5: Setting AUTOM8_EXPORT_ENABLED=false prevents workflow execution
- AC-W05.6: Missing AUTOM8_EXPORT_ENABLED env var defaults to enabled
- AC-W05.7: InsightsExportWorkflow is registered in WorkflowRegistry
- AC-W05.8: Lambda timeout is configured at 15 minutes
- AC-W05.9: Handler returns structured JSON with status, total, succeeded, failed, skipped, duration_seconds

---

## 5. Non-Functional Requirements

### NFR-EXPORT-001: Performance

- Single offer processing (10 table fetches + compose + upload): P95 under 10 seconds
- Full workflow for 100 offers at concurrency=5: P95 under 5 minutes
- Markdown composition is CPU-bound and should add negligible latency (< 100ms per offer)

### NFR-EXPORT-002: Reliability

- Per-offer error isolation: a single offer failure does not affect other offers
- Per-table error isolation: a single table failure does not prevent other tables from rendering
- Circuit breaker integration: if autom8_data is degraded, workflow degrades gracefully (partial reports or skipped offers) rather than failing entirely
- Retry behavior: inherited from DataServiceClient (exponential backoff with jitter)
- Upload-first pattern: ensures a report is always available on the offer task (old attachment is only deleted after new one is confirmed uploaded)

### NFR-EXPORT-003: Observability

Structured logging for every workflow execution:

| Log Event | When | Fields |
|-----------|------|--------|
| `insights_export_started` | Workflow begins | total_offers, max_concurrency |
| `insights_export_offer_started` | Per-offer processing begins | offer_gid, office_phone (masked), vertical |
| `insights_export_table_fetched` | Per-table fetch completes | offer_gid, table_name, row_count, duration_ms |
| `insights_export_table_failed` | Per-table fetch fails | offer_gid, table_name, error_type, error_message |
| `insights_export_offer_succeeded` | Per-offer processing completes | offer_gid, tables_succeeded, tables_failed, duration_ms |
| `insights_export_offer_failed` | All tables failed for offer | offer_gid, error_count |
| `insights_export_offer_skipped` | Offer skipped (no phone/vertical) | offer_gid, reason |
| `insights_export_upload_succeeded` | Attachment uploaded | offer_gid, filename, size_bytes |
| `insights_export_old_attachment_deleted` | Old attachment cleaned up | offer_gid, attachment_gid, attachment_name |
| `insights_export_completed` | Workflow finishes | total, succeeded, failed, skipped, duration_seconds |

### NFR-EXPORT-004: Security

- PII masking: office_phone is masked in all log output via `mask_phone_number()`
- Phone number is NOT masked in the insights API calls (required for lookup) but IS masked in the markdown report header
- No secrets in Lambda event payloads
- Auth: DataServiceClient uses existing S2S JWT / API key authentication

### NFR-EXPORT-005: Idempotency

- Re-running the workflow produces the same end state: latest report attached, old reports cleaned up
- Upload-first + delete-old pattern ensures exactly one current report exists after each run
- Safe to manually re-trigger via Lambda console if needed

---

## 6. Dependencies

### 6.1 autom8_data Reconciliation Fields (GREEN)

| Field | Status |
|-------|--------|
| num_invoices | Validated in code, deploying |
| collected | Validated in code, deploying |
| variance | Validated in code, deploying |
| variance_pct | Validated in code, deploying |
| first_payment | Validated in code, deploying |
| latest_payment | Validated in code, deploying |
| days_with_activity | Validated in code, deploying |
| expected_collection | Validated in code, deploying |
| expected_variance | Validated in code, deploying |

These fields are in the insights response already. They appear in the SUMMARY and periodic tables. Reconciliation-specific tables (LIFETIME RECONCILIATIONS, T14 RECONCILIATIONS) are deferred to Phase 2, but the underlying fields are available for any table that includes them.

Status: GREEN for planning. QA will verify live data availability during implementation.

### 6.2 autom8_data asset_score Inline (YELLOW -- Needs New Work)

The ASSET TABLE should display an `asset_score` column computed by autom8_data's HealthScoreService, returned inline in the insights response for frame_type=asset.

**Current state**: HealthScoreService exists but does not inject asset_score into the insights response. This requires new work in autom8_data.

**Mitigation**: If `asset_score` is not available at implementation time, the ASSET TABLE section renders without it (raw metrics only: spend, imp, clicks, etc.). The column is added when the autom8_data work is complete. No schema break required -- just an additional column appearing.

### 6.3 autom8_data Appointment and Lead Endpoints (YELLOW -- Verify Availability)

- `GET /appointments` and `GET /leads` endpoints must be available on autom8_data
- These are assumed to exist based on the modern API surface; verify during implementation
- If unavailable: APPOINTMENTS and LEADS tables render with error markers; other 8 tables proceed normally

### 6.4 Existing Infrastructure (GREEN)

| Component | Status | Used For |
|-----------|--------|----------|
| WorkflowAction ABC | Production | Base class |
| WorkflowRegistry | Production | Registration |
| DataServiceClient | Production | Insights fetch |
| AttachmentsClient | Production | Upload/delete |
| ResolutionContext | Production | Phone/vertical resolution |
| ConversationAuditWorkflow Lambda pattern | Production | Handler template |
| mask_phone_number() | Production | PII masking |

---

## 7. Rollout Plan

### Phase 1: Implementation and Testing
1. Implement DataServiceClient extensions (W04)
2. Implement InsightsExportWorkflow (W01, W02)
3. Implement markdown report formatter (W03)
4. Implement Lambda handler (W05)
5. Unit tests for all components
6. Integration tests with mocked autom8_data responses

### Phase 2: Deployment
1. Deploy Lambda function with `AUTOM8_EXPORT_ENABLED=true`
2. Manual Lambda invocation to verify against live Asana data
3. Verify markdown rendering in Asana attachment preview
4. Disable legacy `run_export` EventBridge rule
5. Enable InsightsExportWorkflow EventBridge rule (6 AM ET daily)
6. Monitor first 3 daily runs via CloudWatch logs

### Rollback Procedure
- Not planned. Fix forward.
- Emergency: Set `AUTOM8_EXPORT_ENABLED=false` to disable the new workflow, re-enable legacy `run_export` EventBridge rule
- Confidence level: High. The pattern is proven by ConversationAuditWorkflow. The risk surface is the data mapping (10 tables), not the infrastructure.

---

## 8. MoSCoW Prioritization

### Must Have
- W01: Core workflow (WorkflowAction protocol, offer enumeration, resolution, fetch, compose, upload, cleanup)
- W02: Partial export with error markers (per-table isolation, total failure handling)
- W03: Markdown report format (pipe tables, modern column names, null handling, header/footer)
- W04: DataServiceClient extensions (get_appointments_async, get_leads_async, period normalization)
- W05: Scheduling and deployment (Lambda handler, EventBridge, feature flag, WorkflowRegistry)
- NFR-EXPORT-001 through NFR-EXPORT-005 (performance, reliability, observability, security, idempotency)

### Should Have
- Row limit truncation notes in markdown
- Per-offer table success/failure counts in WorkflowResult.metadata
- Configurable row limits per table type

### Could Have
- Markdown table alignment (right-align numeric columns)
- Summary statistics in footer (total spend across all offers, etc.)
- Configurable section order

### Won't Have (This Release)
- Reconciliation tables (LIFETIME RECONCILIATIONS, T14 RECONCILIATIONS)
- Demographics table (DEMO TABLE)
- Ad/Adset breakdown tables (T7 BY AD, T7 BY ADSET)
- Asset score column (depends on autom8_data HealthScoreService work)
- template_id support
- Other legacy job migrations
- CSV output format (markdown only)
- Programmatic API for export data

---

## 9. Success Criteria

### SC-EXPORT-001: Core Workflow

| Test | Pass Criteria |
|------|---------------|
| Workflow implements WorkflowAction protocol | `workflow_id == "insights-export"`, `execute_async()` and `validate_async()` are callable |
| Feature flag disabled | `validate_async()` returns `["Workflow disabled via AUTOM8_EXPORT_ENABLED=false"]` |
| Offer enumeration | Only non-completed offers from BusinessOffers project are enumerated |
| Resolution success | offer -> Business -> office_phone + vertical resolved via ResolutionContext |
| Resolution failure | Offer skipped with reason `"no_resolution"`, other offers unaffected |
| Attachment upload | .md file uploaded to offer task with correct naming convention |
| Old attachment cleanup | Previous `insights_export_*.md` files deleted; new file preserved |
| Concurrency | At most `max_concurrency` offers processed simultaneously |

### SC-EXPORT-002: Partial Export

| Test | Pass Criteria |
|------|---------------|
| 1 table fails, 9 succeed | Report contains 9 rendered tables + 1 error marker section |
| All 10 tables fail | No attachment uploaded; offer marked as failed |
| Error marker format | `## TABLE_NAME\n> [ERROR] {type}: {message}` is valid markdown |
| Per-offer table counts | WorkflowResult.metadata includes `{offer_gid: {tables_succeeded: 9, tables_failed: 1}}` |

### SC-EXPORT-003: Markdown Format

| Test | Pass Criteria |
|------|---------------|
| Valid markdown | Output parses without errors in a standard markdown processor |
| Pipe table syntax | Header row + alignment row + data rows for each table |
| Modern column names | No legacy names (ad_spend -> offer_cost, etc.) |
| Null rendering | Always-null columns present with `---` markers |
| Masked phone | Header shows `+1770***3103` format, not raw phone |
| Empty table | Shows `> No data available` note |
| Unused assets filter | Only rows with spend==0 AND imp==0 appear in UNUSED ASSETS |

### SC-EXPORT-004: DataServiceClient

| Test | Pass Criteria |
|------|---------------|
| get_appointments_async() | Returns appointment rows, respects days and limit params |
| get_leads_async() | Returns lead rows, excludes appointments by default |
| _normalize_period("quarter") | Returns "QUARTER" |
| _normalize_period("month") | Returns "MONTH" |
| _normalize_period("week") | Returns "WEEK" |
| Existing periods unchanged | LIFETIME, T7, T14, T30 still work |

### SC-EXPORT-005: Deployment

| Test | Pass Criteria |
|------|---------------|
| Lambda handler invocation | Returns `{statusCode: 200, body: {status: "completed", ...}}` |
| Manual trigger | Lambda can be invoked from console with override params |
| EventBridge fires | Rule triggers at 6 AM ET daily |
| Kill switch | Setting AUTOM8_EXPORT_ENABLED=false prevents execution |

### SC-EXPORT-006: Observability

| Test | Pass Criteria |
|------|---------------|
| Successful run | `insights_export_started` and `insights_export_completed` logs present with counts and duration |
| Failed offer | `insights_export_offer_failed` log present with offer_gid and error details |
| PII masking | No raw phone numbers in any log output |

---

## 10. Open Questions

None. All 15 stakeholder decisions confirmed. No blocking questions remain.

---

## 11. Appendix: Table-to-API-Call Mapping

| # | Table | API Call | frame_type | period | Notes |
|---|-------|----------|------------|--------|-------|
| 1 | SUMMARY | `POST /insights` | `unit` | `LIFETIME` | Single aggregated row |
| 2 | APPOINTMENTS | `GET /appointments` | N/A (detail) | days=90 | New client method; limit=100 |
| 3 | LEADS | `GET /leads` | N/A (detail) | days=30 | New client method; exclude_appointments=true, limit=100 |
| 4 | BY QUARTER | `POST /insights` | `unit` | `QUARTER` | Multiple rows per quarter; requires W04 period extension |
| 5 | BY MONTH | `POST /insights` | `unit` | `MONTH` | Multiple rows per month; requires W04 period extension |
| 6 | BY WEEK | `POST /insights` | `unit` | `WEEK` | Multiple rows per week; requires W04 period extension |
| 7 | AD QUESTIONS | `POST /insights` | `offer` | `LIFETIME` | Question dimension on offer |
| 8 | ASSET TABLE | `POST /insights` | `asset` | `T30` | Per-asset metrics; asset_score deferred |
| 9 | OFFER TABLE | `POST /insights` | `offer` | `T30` | Per-offer metrics |
| 10 | UNUSED ASSETS | `POST /insights` | `asset` | `T30` | Same API call as ASSET TABLE; client-side filter: `spend == 0 AND imp == 0` |

**Note on UNUSED ASSETS**: Table 10 reuses the API response from Table 8 (ASSET TABLE). The workflow should make a single `POST /insights` call for frame_type=asset, period=T30, and derive both the ASSET TABLE (all rows) and UNUSED ASSETS (filtered rows) from that single response. This avoids a redundant API call.

---

## 12. Appendix: Reconciliation Semantic Differences

This appendix documents the semantic mapping between legacy and modern reconciliation fields. It is included as reference for Phase 2 when reconciliation tables are added.

### Balance Direction

| Concept | Legacy (Budget-Centric) | Modern (Payment-Centric) |
|---------|------------------------|--------------------------|
| Core metric | Budget remaining | Variance from expected |
| Direction | Positive = under budget | Positive = over-collected |
| Field | Computed from budget - spend | `variance` (direct from API) |

### Derived Metrics

| Metric | Legacy Formula | Modern Derivation |
|--------|---------------|-------------------|
| Spend Percentage | `spend / budget * 100` | `spend / expected_collection * 100` |
| Balance Percentage | `(budget - spend) / budget * 100` | `expected_variance / expected_collection * 100` |
| Balance Amount | `budget - spend` | Use `variance` directly (no computation needed) |

### Key Differences

1. **No "budget" field in modern API**: Legacy used a budget field from Asana custom fields. Modern uses `expected_collection` from payment data, which is more accurate.
2. **variance is signed**: Positive variance means collected more than expected. Legacy balance was always positive (remaining budget).
3. **variance_pct is pre-computed**: No need to derive percentage client-side. Use `variance_pct` directly from API response.
4. **Payment dates available**: `first_payment` and `latest_payment` provide payment timeline context not available in legacy.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-insights-export-workflow.md` | Yes (Written 2026-02-12) |
| Stakeholder Interview | 15 confirmed decisions | Completed 2026-02-12 |
| Reference: ConversationAuditWorkflow | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/conversation_audit.py` | Read-verified |
| Reference: WorkflowAction ABC | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/workflows/base.py` | Read-verified |
| Reference: Lambda handler pattern | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/conversation_audit.py` | Read-verified |
| Reference: DataServiceClient | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/data/client.py` | Read-verified |
| Reference: PRD-entity-write-api (format reference) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-entity-write-api.md` | Read-verified |
