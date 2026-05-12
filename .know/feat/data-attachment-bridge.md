---
domain: feat/data-attachment-bridge
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/workflows/insights/"
  - "./src/autom8_asana/automation/workflows/conversation_audit/"
  - "./src/autom8_asana/automation/workflows/mixins.py"
  - "./src/autom8_asana/automation/workflows/bridge_base.py"
  - "./src/autom8_asana/lambda_handlers/insights_export.py"
  - "./src/autom8_asana/lambda_handlers/conversation_audit.py"
  - "./src/autom8_asana/lambda_handlers/workflow_handler.py"
  - "./src/autom8_asana/core/scope.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.95
format_version: "1.0"
---

# Data Attachment Bridge (Backend-to-Asana Reporting Pipeline)

## Purpose and Design Rationale

The Data Attachment Bridge is the subsystem that pushes data from the `autom8_data` satellite into Asana as file attachments. It answers the question: "how does derived reporting data get surfaced to Asana task owners without requiring them to leave the Asana UI?"

### Problem Solved

Asana task owners (account managers, strategists) need visibility into per-account metrics and conversation records. The raw data lives in `autom8_data` (a separate service). Rather than building a separate report surface, the bridge uploads formatted files directly as Asana task attachments — surfacing data where users already work.

### Design Decisions and Tradeoffs

**Upload-first attachment replacement** (per ADR-DRY-WORKFLOW-001): New file is uploaded before old matching attachments are deleted. This ensures that if the delete step fails, the new file is still present. The tradeoff is a brief window where two versions coexist. Per `mixins.py` line 71: delete failures are logged as warnings and swallowed (`Non-fatal: individual delete failures ... swallowed so the batch can continue`).

**Intermediate base class `BridgeWorkflowAction`** (per ADR-bridge-intermediate-base-class): `InsightsExportWorkflow` and `ConversationAuditWorkflow` shared nearly identical constructor wiring, validate_async, enumerate_async scope handling, and semaphore fan-out. An intermediate base class (`bridge_base.py`) was introduced in sprint-3/sprint-4 respectively to eliminate this duplication. Rejected alternative: plain composition (too much forwarding boilerplate for async protocol compliance).

**Feature-flag kill-switch** via environment variables (`AUTOM8_EXPORT_ENABLED`, `AUTOM8_AUDIT_ENABLED`): disabling either flag causes `validate_async()` to short-circuit and return a skipped response. No code changes required to disable in production.

**Per-entity broad-catch isolation**: Each entity (Offer/ContactHolder) is processed inside a try/except that returns a failed outcome rather than propagating. This prevents one bad entity from stopping the batch. The pattern is annotated with `# BROAD-CATCH: boundary` comments throughout.

**Concurrent entity processing** via `asyncio.Semaphore(5)` (default): Bounded parallelism avoids thundering-herd against the Asana API and `autom8_data`. Configurable via `max_concurrency` param.

**Generic Lambda handler factory** (per ADR-DRY-WORKFLOW-001, `workflow_handler.py`): The two Lambda handlers were 95% identical; extracted to `create_workflow_handler(WorkflowHandlerConfig)`. Each concrete handler provides only a `workflow_factory` callable plus workflow-specific metadata (DMS namespace, response_metadata_keys, default_params).

### Related Decision Records

- ADR-DRY-WORKFLOW-001 (referenced in `mixins.py`, `workflow_handler.py` docstrings)
- ADR-bridge-intermediate-base-class (referenced in `bridge_base.py`, both workflow docstrings)
- ADR-bridge-invocation-model (referenced in `workflow_handler.py:172`)
- ADR-bridge-dispatch-model (referenced in `workflow_handler.py:183`)
- ADR-bridge-observability-fleet (referenced in `workflow_handler.py:253`)
- TDD-EXPORT-001 (referenced in `insights/workflow.py`)
- TDD-CONV-AUDIT-001 (referenced in `conversation_audit/workflow.py`)
- TDD-ENTITY-SCOPE-001 (referenced in both workflow files and `core/scope.py`)
- PRD-EXPORT-001 / PRD REQ-F18 (referenced in workflow docstrings)

---

## Conceptual Model

### Key Abstractions

**Fetch-Format-Attach cycle**: The core operation every bridge workflow performs:
1. **Fetch** data from `autom8_data` via `DataServiceClient`
2. **Format** the data (HTML report or CSV bytes)
3. **Attach** to an Asana task (upload new, delete old)

**WorkflowAction** (`base.py`): Abstract base. Defines `validate_async()`, `enumerate_async()`, `execute_async()`.

**BridgeWorkflowAction** (`bridge_base.py`): Intermediate base that absorbs all boilerplate common to data-fetching bridges. Provides concrete implementations of validate/enumerate/execute. Subclasses implement only `enumerate_entities()`, `process_entity()`, and optionally `_build_result_metadata()`.

**AttachmentReplacementMixin** (`mixins.py`): Provides `_delete_old_attachments(task_gid, pattern, exclude_name)` — the upload-first deletion step shared by both workflows. Uses glob pattern matching (`fnmatch`) against existing attachment names.

**BridgeOutcome** (`bridge_base.py`): Base dataclass returned by `process_entity()`. Fields: `gid`, `status` (succeeded/failed/skipped), `reason`, `error`. Subclassed by `_OfferOutcome` (adds table counts, preview path) and `_HolderOutcome` (adds truncated flag, csv_row_count).

**EntityScope** (`core/scope.py`): Frozen dataclass constructed once at the invocation boundary. Controls: `entity_ids` (GIDs to target, empty = full enumeration), `section_filter`, `limit`, `dry_run`. Constructed via `EntityScope.from_event(lambda_event_dict)`. The `has_entity_ids` property drives the fast-path vs full-path branch in `enumerate_async()`.

**WorkflowHandlerConfig** (`workflow_handler.py`): Configuration object for `create_workflow_handler()`. Key fields: `workflow_factory`, `workflow_id`, `log_prefix`, `default_params`, `response_metadata_keys`, `dms_namespace`, `fleet_namespace`.

### Class Hierarchy

```
WorkflowAction (base.py)
  └── BridgeWorkflowAction (bridge_base.py)
        [AttachmentReplacementMixin via MRO]
        ├── InsightsExportWorkflow (insights/workflow.py)
        └── ConversationAuditWorkflow (conversation_audit/workflow.py)
```

MRO for concrete classes: `ConcreteWorkflow -> BridgeWorkflowAction -> AttachmentReplacementMixin -> WorkflowAction`.

### Two Concrete Workflows

**InsightsExportWorkflow** (`insights/workflow.py`):
- Schedule: daily 6:00 AM ET (EventBridge)
- Entity type: Offer tasks in `Offer.PRIMARY_PROJECT_GID`
- Data: 12 tables from `autom8_data` fetched concurrently via `asyncio.gather()` over `TABLE_SPECS`
- Format: HTML report composed by `compose_report()` in `insights/formatter.py`
- Output filename: `insights_export_{sanitized_business_name}_{YYYYMMDD}.html`
- Attachment cleanup pattern: `insights_export_*.html`
- Resolution chain: Offer → OfferHolder → Unit → UnitHolder → Business (via `ResolutionContext` with `trigger_entity`)
- Business cache: deduplicates Business API calls across sibling Offers; `_business_cache[business_gid]` + `_offer_to_business[offer_gid]` (per AT3-001)
- Enumeration strategy: section-targeted (resolve ACTIVE section GIDs, parallel Semaphore(5) fetch) with fallback to project-level full enumeration
- Kill-switch: `AUTOM8_EXPORT_ENABLED`

**ConversationAuditWorkflow** (`conversation_audit/workflow.py`):
- Schedule: weekly (EventBridge)
- Entity type: ContactHolder tasks in `ContactHolder.PRIMARY_PROJECT_GID`
- Data: 30-day conversation CSV from `DataServiceClient.get_export_csv_async()`
- Format: raw CSV bytes (no composition step)
- Output filename: provided by `ExportResult.filename` from the data client
- Attachment cleanup pattern: `conversations_*.csv`
- Resolution chain: ContactHolder → parent Business (direct, ContactHolder.parent IS Business)
- Bulk pre-resolution: `_pre_resolve_business_activities()` hydrates all parent Businesses in parallel (Semaphore(8)) at enumeration time to pre-filter inactive Businesses before `execute_async`
- Activity gate: per-holder check against `AccountActivity.ACTIVE` skips ContactHolders whose parent Business is not active
- Kill-switch: `AUTOM8_AUDIT_ENABLED`

### 12-Table Dispatch (InsightsExport)

`TABLE_SPECS` (in `insights/tables.py`) declares 12 table specifications with `DispatchType` enum routing:
- `INSIGHTS` → `DataServiceClient.get_insights_async(factory, period, ...)`
- `APPOINTMENTS` → `DataServiceClient.get_appointments_async(office_phone, days, limit)`
- `LEADS` → `DataServiceClient.get_leads_async(office_phone, days, exclude_appointments, limit)`
- `RECONCILIATION` → `DataServiceClient.get_reconciliation_async(office_phone, vertical, period, window_days)` + defensive phone filtering in dispatcher

Tables by name: SUMMARY, APPOINTMENTS, LEADS, LIFETIME RECONCILIATIONS, T14 RECONCILIATIONS, BY QUARTER, BY MONTH, BY WEEK, AD QUESTIONS, ASSET TABLE (top 150 by spend), OFFER TABLE, UNUSED ASSETS.

Each `TableSpec` is a frozen dataclass coupling fetch config with display config (sort_key, sort_desc, exclude_columns, display_columns, empty_message). `_fetch_table()` uses a `match spec.dispatch_type` statement (eliminating if/elif chain per D-04).

### Lifecycle (unified across both workflows)

```
Lambda event received
  └── EntityScope.from_event(event)
  └── validate_async()                  # kill-switch + data source health
        [ABORT if disabled or CB open]
  └── enumerate_async(scope)            # entity list
        [fast-path: scope.has_entity_ids → synthetic dicts]
        [full-path: enumerate_entities() + limit truncation]
  └── execute_async(entities, params)   # semaphore fan-out
        for each entity (Semaphore(max_concurrency)):
          process_entity(entity, params)
            → resolve identity (phone/vertical/business)
            → fetch data
            → format data
            → upload attachment (unless dry_run)
            → delete old attachments (unless dry_run)
            → return BridgeOutcome
  └── _build_result_metadata(outcomes)
  └── emit CloudWatch metrics + DMS timestamp + fleet health
  └── publish BridgeExecutionComplete domain event (fire-and-forget)
  └── return HTTP 200 with WorkflowResult
```

### Inter-Feature Relationships

- **Consumes from**: `workflow-invoke-api` feature (the HTTP dispatch surface used for manual/API-triggered invocations via `EntityScope.from_event`); `autom8_data` satellite (external dependency via `DataServiceClient`); `ResolutionContext` / `hydrate_from_gid_async` (entity resolution subsystem)
- **Provides to**: Asana tasks (file attachments visible to task owners); CloudWatch metrics namespace `Autom8y/AsanaInsights` and `Autom8y/AsanaAudit` (DMS timestamps); EventBridge `BridgeExecutionComplete` domain events

---

## Implementation Map

### Package/Module Inventory

| File | Purpose | Key Types/Entry Points |
|------|---------|------------------------|
| `src/autom8_asana/automation/workflows/bridge_base.py` | Intermediate base class for all bridge workflows | `BridgeWorkflowAction`, `BridgeOutcome`, `create_workflow_handler` |
| `src/autom8_asana/automation/workflows/mixins.py` | Upload-first attachment replacement shared logic | `AttachmentReplacementMixin._delete_old_attachments()` |
| `src/autom8_asana/automation/workflows/insights/workflow.py` | InsightsExport: daily HTML report for Offer tasks | `InsightsExportWorkflow`, `_OfferOutcome` |
| `src/autom8_asana/automation/workflows/insights/tables.py` | Declarative 12-table config for InsightsExport | `TABLE_SPECS`, `DispatchType`, `TableSpec` |
| `src/autom8_asana/automation/workflows/insights/formatter.py` | HTML report composition from table data | `compose_report(InsightsReportData) -> str`, `HtmlRenderer`, `DataSection` |
| `src/autom8_asana/automation/workflows/conversation_audit/workflow.py` | ConversationAudit: weekly CSV refresh for ContactHolder tasks | `ConversationAuditWorkflow`, `_HolderOutcome` |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Lambda entry point for InsightsExport | `handler` (via `create_workflow_handler`) |
| `src/autom8_asana/lambda_handlers/conversation_audit.py` | Lambda entry point for ConversationAudit | `handler` (via `create_workflow_handler`) |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | Generic Lambda handler factory (eliminates 95% duplication) | `WorkflowHandlerConfig`, `create_workflow_handler()` |
| `src/autom8_asana/core/scope.py` | Cross-cutting invocation control | `EntityScope`, `EntityScope.from_event()` |

### Data Flow

**InsightsExport path:**
```
Lambda event dict
  → EntityScope.from_event()
  → InsightsExportWorkflow.enumerate_async()
      → resolve_section_gids() [ACTIVE sections in Offer project]
      → parallel section task fetch (Semaphore(5))
      [fallback: full project task fetch with client-side ACTIVE filter]
  → InsightsExportWorkflow.execute_async(offers, params)
      for each Offer (Semaphore(5)):
        → _resolve_offer(offer_gid)
            → ResolutionContext(trigger_entity=offer_entity).business_async()
                [Offer → OfferHolder → Unit → UnitHolder → Business]
            → returns (office_phone, vertical, business_name)
        → _fetch_all_tables(office_phone, vertical, row_limits)
            → asyncio.gather(12 × _fetch_table(spec))
                → DataServiceClient.get_{insights|appointments|leads|reconciliation}_async()
        → compose_report(InsightsReportData)
            → HtmlRenderer.render_document() [self-contained HTML with inline CSS]
        → AttachmentsClient.upload_async(offer_gid, html_bytes, filename)
        → _delete_old_attachments(offer_gid, "insights_export_*.html", exclude=filename)
  → _build_result_metadata(outcomes)  [table counts, preview paths]
  → emit_metric(WorkflowDuration, WorkflowSuccessRate, BridgeFleetHealth)
  → emit_success_timestamp(dms_namespace)
  → _publish_bridge_event(result)  [BridgeExecutionComplete]
```

**ConversationAudit path:**
```
Lambda event dict
  → EntityScope.from_event()
  → ConversationAuditWorkflow.enumerate_async()
      → _enumerate_contact_holders()  [full project task list]
      → _pre_resolve_business_activities(holders)  [Semaphore(8) parallel hydration]
      → pre-filter to ACTIVE Business holders
  → ConversationAuditWorkflow.execute_async(holders, params)
      for each ContactHolder (Semaphore(5)):
        → _resolve_business_activity(parent_gid)  [from _activity_map cache]
        → _resolve_office_phone(holder_gid, parent_gid)
            → ResolutionContext(business_gid=business_gid).business_async()
        → DataServiceClient.get_export_csv_async(office_phone, start_date, end_date)
        → AttachmentsClient.upload_async(holder_gid, csv_bytes, filename)
        → _delete_old_attachments(holder_gid, "conversations_*.csv", exclude=filename)
  → _build_result_metadata(outcomes)  [truncated_count, activity_skipped_count]
```

### Lambda Handler Wiring

Both handlers use `create_workflow_handler(WorkflowHandlerConfig)` from `workflow_handler.py`. The factory:
1. Decorates with `@instrument_lambda` (autom8y-telemetry)
2. Calls `asyncio.run(_handler_async(event, context))`
3. Initializes `AsanaClient` + optional `DataServiceClient` (context manager)
4. Calls `workflow_factory(asana_client, data_client)` with deferred import (cold-start optimization)
5. Runs `validate_async()` → `enumerate_async(scope)` → `execute_async(entities, params)`
6. Emits CloudWatch metrics via `emit_metric()` (local `lambda_handlers/cloudwatch.py`) and `emit_business_metric()` (autom8y-telemetry)
7. Emits DMS via `emit_success_timestamp(dms_namespace)` when execution completes
8. Emits fleet health `BridgeFleetHealth` metric to `Autom8y/AsanaBridgeFleet` namespace
9. Fire-and-forget publishes `BridgeExecutionComplete` domain event via `autom8y_events`

**DMS namespaces**: InsightsExport → `Autom8y/AsanaInsights`; ConversationAudit → `Autom8y/AsanaAudit`; fleet → `Autom8y/AsanaBridgeFleet`.

### Key CloudWatch Metrics

Emitted per workflow execution:
- `WorkflowExecutionCount` (count=1, per run)
- `WorkflowDuration` (seconds)
- `WorkflowSuccessRate` (percent)
- `WorkflowValidationSkipped` (count=1, if kill-switch active)
- `WorkflowExecutionError` (count=1, on uncaught exception)
- `BridgeFleetHealth` (1.0=healthy, 0.0=degraded, namespace=`Autom8y/AsanaBridgeFleet`)
- `EntitiesProcessed`, `WorkflowDuration` via `emit_business_metric` (autom8y-telemetry)

### Test Locations and Coverage

| Test File | Covers |
|-----------|--------|
| `tests/unit/automation/workflows/test_bridge_base.py` | `BridgeWorkflowAction`: validate_async, enumerate_async fast-path/full-path, execute_async semaphore fan-out, BridgeOutcome aggregation |
| `tests/unit/automation/workflows/test_attachment_mixin.py` | `AttachmentReplacementMixin._delete_old_attachments`: glob matching, delete soft-fail, exclude_name logic |
| `tests/unit/automation/workflows/test_insights_export.py` | `InsightsExportWorkflow`: offer resolution, table dispatch, HTML composition, upload-first, dry_run preview, business cache |
| `tests/unit/automation/workflows/test_conversation_audit.py` | `ConversationAuditWorkflow`: activity gate, phone resolution, CSV fetch, upload-first, zero-rows skip, truncation |
| `tests/unit/lambda_handlers/test_insights_export.py` | Lambda handler integration: event parsing, metric emission, DMS, BridgeExecutionComplete |
| `tests/unit/lambda_handlers/test_conversation_audit_handler.py` | Lambda handler integration: event parsing, metric emission |
| `tests/integration/automation/workflows/test_conversation_audit_e2e.py` | End-to-end ConversationAudit against mock Asana + data client |

Note: `test_workflow_handler.py` is marked `xdist_group("workflow_handler")` due to SCAR-W1E-LOADGROUP-001 (AsyncMock teardown isolation under `--dist=loadgroup`).

---

## Boundaries and Failure Modes

### Explicit Scope Boundaries

This feature does NOT:
- Produce the HTTP dispatch surface for manual/API-triggered runs — that is `workflow-invoke-api` (the API layer routes and `WorkflowRegistration` mechanism)
- Own the `autom8_data` satellite or its API contract — `DataServiceClient` is an injected dependency
- Own `ResolutionContext` or the entity hierarchy traversal logic — those live in `src/autom8_asana/resolution/`
- Handle Asana webhooks or real-time triggers — these workflows are schedule-driven only (EventBridge)
- Write to Asana tasks (notes, custom fields) — only file attachments are managed

### Configuration Boundaries

| Parameter | Default | Invalid Values |
|-----------|---------|----------------|
| `AUTOM8_EXPORT_ENABLED` | enabled (anything != false/0/no) | `"false"`, `"0"`, `"no"` → kills workflow |
| `AUTOM8_AUDIT_ENABLED` | enabled | `"false"`, `"0"`, `"no"` → kills workflow |
| `max_concurrency` | 5 | 0 would deadlock; very high values risk Asana rate limits |
| `date_range_days` | 30 | Affects `get_export_csv_async` date window |
| `row_limits` (InsightsExport) | APPOINTMENTS=100, LEADS=100, ASSET TABLE=150 | Increasing APPOINTMENTS/LEADS beyond 500 may exceed upstream API caps |

### Failure Modes

**Kill-switch / circuit breaker (pre-flight)**:
- Feature flag env var set to disabled → `validate_async()` returns error string; handler returns HTTP 200 with `status: skipped`; `WorkflowValidationSkipped` metric emitted; `BridgeFleetHealth=0.0` emitted
- `DataServiceClient` circuit breaker open → same path as above
- Non-CB connection errors (ConnectionError, TimeoutError, OSError) in health check are NOT pre-flight failures

**Entity resolution failures**:
- InsightsExport: `_resolve_offer()` returns `None` → offer logged as skipped with `reason="no_resolution"`. This happens when: Offer has no parent task, or traversed Business has no `office_phone` or `vertical`.
- ConversationAudit: Business not ACTIVE → holder skipped with `reason="business_not_active"` or `"activity_unknown"`. Phone resolution returns `None` → skipped with `reason="no_office_phone"`.
- `ResolutionContext` for Offer traversal uses `trigger_entity` (NOT `business_gid` fast-path) — Offer.parent is OfferHolder, not Business. Using the wrong fast-path would return wrong parent.

**Data fetch failures**:
- InsightsExport: Individual table failures isolated — `_fetch_table()` catches all exceptions, returns `TableResult(success=False)`. Total failure (0/12 tables succeed) → offer marked failed with `error_type="all_tables_failed"`. Partial failure continues.
- ConversationAudit: `ExportError` from `get_export_csv_async()` → holder marked failed; `recoverable = (e.reason != "client_error")`. Zero CSV rows → skipped with `reason="zero_rows"`.

**Attachment write failures**:
- Upload failure propagates to per-entity broad-catch → entity marked failed with `error_type="unexpected"`
- Delete failure (in `_delete_old_attachments`) is non-fatal — logged as warning, swallowed. Next execution will clean up stragglers.

**Lambda-level errors**:
- Any unhandled exception in `_handler_async` caught by top-level broad-catch → HTTP 500, `WorkflowExecutionError` metric emitted
- `BridgeExecutionComplete` event publication failures are fire-and-forget — ImportError (autom8y_events not installed) silently skips; other exceptions logged as warning and swallowed

**SCAR references relevant to this feature**:
- SCAR-016: date_range_days not forwarded (historical workflow logic gap)
- SCAR-017: csv_row_count missing (historical workflow logic gap)
- SCAR-026: Non-spec mock drift risk — test mocks for DataServiceClient/AttachmentsClient should use `spec=`; HYG-002 partial adoption in progress
- SCAR-W1E-LOADGROUP-001: `test_workflow_handler.py` must have `xdist_group("workflow_handler")` marker; `--dist=loadgroup` active in `pyproject.toml:105`

### Interaction Points / Boundary Blur Zones

- **`ResolutionContext`** (`resolution/context.py`): Used by both workflows for Business resolution. InsightsExport uses `trigger_entity=` to force multi-hop traversal; ConversationAudit uses `business_gid=` fast-path (ContactHolder.parent IS Business). These are different call signatures — confusing them would silently skip the traversal.
- **`hydrate_from_gid_async`** (`models/business/hydration.py`): Used by ConversationAudit's `_resolve_business_activity()` to hydrate Business + Unit children. `hydrate_full=True` is required to reach Units for max_unit_activity.
- **`workflow_handler.py`** shared factory: Both Lambda handlers delegate entirely to `create_workflow_handler`. The `workflow_factory` callable uses a deferred import pattern for cold-start optimization — the workflow class is NOT imported at module load time.
- **H-006 gap**: `trace_computation` decorator from `autom8y-telemetry 0.6.1` is NOT yet available. `bridge_base.py:193-197` has a TODO comment for future application to `execute_async()`.

```metadata
domain: feat/data-attachment-bridge
source_hash: "8980bcd7"
generated_at: "2026-05-08T00:00Z"
confidence: 0.95
criteria_grades:
  purpose_and_design_rationale:
    grade: A
    pct: 95
    weight: 0.30
  conceptual_model:
    grade: A
    pct: 93
    weight: 0.25
  implementation_map:
    grade: A
    pct: 95
    weight: 0.25
  boundaries_and_failure_modes:
    grade: A
    pct: 93
    weight: 0.20
overall_grade: A
overall_pct: 94
notes: >
  Full refresh from source hash 8980bcd7. Prior file was at source_hash c213958 (confidence 0.83)
  with 3 documented knowledge gaps. This refresh closes all 3 prior gaps:
  (1) formatter.py HTML composition logic now documented (HtmlRenderer, DataSection, compose_report,
  StructuredDataRenderer protocol, self-contained HTML with inline CSS);
  (2) ResolutionContext traversal internals documented (InsightsExport uses trigger_entity= for
  multi-hop, ConversationAudit uses business_gid= fast-path — different call signatures);
  (3) EntityScope.from_event() event schema fully documented (entity_ids, section_filter, limit,
  dry_run fields with normalization semantics).
  New since prior refresh: bridge_base.py intermediate base class, BridgeWorkflowAction,
  WorkflowHandlerConfig/create_workflow_handler factory, section-targeted enumeration with fallback,
  bulk activity pre-resolution in ConversationAudit, H-006 trace_computation TODO, fleet-level
  observability (BridgeFleetHealth, fleet DMS), BridgeExecutionComplete domain event,
  SCAR-W1E-LOADGROUP-001 xdist constraint on test_workflow_handler.py.
```
