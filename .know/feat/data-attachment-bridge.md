---
domain: feat/data-attachment-bridge
generated_at: "2026-03-18T12:59:19Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/workflows/**/*.py"
  - "./src/autom8_asana/lambda_handlers/workflow_handler.py"
  - "./src/autom8_asana/lambda_handlers/insights_export.py"
  - "./src/autom8_asana/lambda_handlers/conversation_audit.py"
  - "./src/autom8_asana/clients/data/**/*.py"
  - "./src/autom8_asana/core/scope.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "2c604fa"
confidence: 0.93
format_version: "1.0"
---

# Data Attachment Bridge (Backend-to-Asana Reporting Pipeline)

## Purpose and Design Rationale

### The "Asana as Internal Operations UI" Principle

This pattern exists because the company's sales reps, account managers, and operations staff live in Asana. Rather than building a separate analytics dashboard, the system brings analytics to where users already are: it fetches data from the `autom8_data` satellite service, formats it as a file (HTML report or CSV), and attaches that file directly to the relevant Asana task.

This is not a convenience -- it is a deliberate product decision. Asana IS the internal operations UI. A separate analytics dashboard would require a separate login, a separate context switch, and would not be visible inline when a rep opens a task. By attaching reports to Offer tasks and ContactHolder tasks, the analytics are surfaced at the exact point of decision.

### The Business Context for Each Instance

**InsightsExportWorkflow**: Operations staff and account managers review ad performance data when managing active advertising campaigns. An Offer task in the Business Offers project represents one client's advertising contract. The attached HTML report gives the account manager 12 tables of performance data (spend, leads, appointments, reconciliation, period breakdowns, asset performance) without leaving the Offer task.

**ConversationAuditWorkflow**: Operations staff reviewing SMS conversation quality open a ContactHolder task in Asana. The attached CSV gives them a 30-day export of all conversations associated with that business's phone number without leaving the task.

### ADR-DRY-WORKFLOW-001: The DRY Refactoring

The Lambda handler modules `lambda_handlers/insights_export.py` and `lambda_handlers/conversation_audit.py` were originally 95% identical boilerplate (client initialization, validation, serialization, error handling, metric emission). ADR-DRY-WORKFLOW-001 extracted this shared scaffolding into the `WorkflowHandlerConfig` + `create_workflow_handler()` factory in `lambda_handlers/workflow_handler.py`. The mixin module `automation/workflows/mixins.py` similarly extracted 39 lines of duplicated upload-first attachment replacement logic that both workflows shared.

### ADR References in Source

The following ADRs are cited directly in docstrings and comments:

| Reference | Location | Decision |
|---|---|---|
| `ADR-DRY-WORKFLOW-001` | `mixins.py:5`, `workflow_handler.py:8` | Extract shared handler boilerplate and attachment logic into shared infrastructure |
| `TDD-CONV-AUDIT-001` | `conversation_audit.py:3`, `base.py:3` | WorkflowAction protocol, ConversationAuditWorkflow specification |
| `TDD-EXPORT-001` | `insights_export.py:3`, `lambda_handlers/insights_export.py:4` | InsightsExportWorkflow specification |
| `TDD-ENTITY-SCOPE-001` | `base.py:5`, `scope.py:4` | EntityScope cross-cutting invocation contract |
| `TDD-SPRINT-C` | `insights_tables.py:8` | TABLE_SPECS centralization |

---

## Conceptual Model

### The Shared Pipeline Archetype

Both workflows instantiate the same archetype:

```
Lambda Event (EventBridge schedule or manual invocation)
    |
    v
EntityScope.from_event(event)          [invocation contract: targeting + dry_run]
    |
    v
workflow.validate_async()              [kill switch + circuit breaker check]
    |
    v
workflow.enumerate_async(scope)        [list entities to process]
    |
    v
workflow.execute_async(entities, params) [async fan-out with Semaphore(5)]
    |
    +-- for each entity:
    |       resolve_entity -> office_phone [resolve the data key]
    |       fetch data from DataServiceClient
    |       format data as file (HTML or CSV)
    |       upload_async(file)             [upload-first]
    |       _delete_old_attachments(...)   [delete old matching files]
    |
    v
WorkflowResult(total, succeeded, failed, skipped, errors, metadata)
    |
    v
emit_metric(WorkflowDuration, WorkflowSuccessRate)
emit_success_timestamp(dms_namespace)   [dead-man's-switch]
```

### The WorkflowAction Contract

Defined in `src/autom8_asana/automation/workflows/base.py`.

```python
class WorkflowAction(ABC):
    @property
    @abstractmethod
    def workflow_id(self) -> str: ...

    @abstractmethod
    async def enumerate_async(self, scope: EntityScope) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def execute_async(
        self,
        entities: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> WorkflowResult: ...

    @abstractmethod
    async def validate_async(self) -> list[str]: ...
```

The contract is:
1. `validate_async()` runs first. Any errors abort execution -- the workflow returns `{"status": "skipped", "reason": "validation_failed"}`.
2. `enumerate_async(scope)` returns the entity list. When `scope.has_entity_ids` is True, workflows must return synthetic dicts for the specified GIDs only. When False, they do full enumeration.
3. `execute_async(entities, params)` processes all entities and returns a `WorkflowResult`. Errors are per-item -- the batch continues even when individual entities fail.

Implementations must be idempotent: re-running the same workflow produces the same end state (upload-first + delete-old ensures this).

### AttachmentReplacementMixin

Defined in `src/autom8_asana/automation/workflows/mixins.py`.

The shared "upload-first, delete-old" pattern is implemented in `AttachmentReplacementMixin._delete_old_attachments()`. The convention is:

1. Upload the new file first (so there is always a current attachment visible).
2. Delete all existing attachments matching the glob pattern, excluding the one just uploaded.

Usage contract: the concrete class must set `_attachments_client` (an `AttachmentsClient`) and expose `workflow_id` (provided by `WorkflowAction`).

Individual delete failures are non-fatal: logged as warnings, swallowed, and the batch continues. The next execution will clean up stragglers.

### EntityScope: The Invocation Contract

Defined in `src/autom8_asana/core/scope.py`.

`EntityScope` is a frozen dataclass constructed once at the Lambda event boundary. It flows from the handler into `enumerate_async()`. It controls:

- `entity_ids`: When non-empty, target only these GIDs (skip full enumeration). Allows single-entity manual re-runs.
- `section_filter`: Restrict enumeration to specific section names (not used by the reporting bridge workflows currently, but available in the contract).
- `limit`: Maximum entity count. `None` means no limit.
- `dry_run`: When True, skip all write operations (upload, delete). For ConversationAudit, this also emits CSV row counts in the result metadata for validation.

`EntityScope.from_event(event)` is the canonical construction path. Unknown keys are silently ignored for forward compatibility.

### The Two Instances as Specializations

| Dimension | InsightsExportWorkflow | ConversationAuditWorkflow |
|---|---|---|
| `workflow_id` | `"insights-export"` | `"conversation-audit"` |
| Entity type | Offer (Asana task in Business Offers project) | ContactHolder (Asana task in ContactHolder project) |
| Data source | 12 concurrent DataServiceClient calls (5 dispatch types) | 1 DataServiceClient call (CSV export endpoint) |
| Output format | Self-contained HTML with inline CSS/JS | Raw CSV bytes |
| File pattern | `insights_export_{name}_{date}.html` | `conversations_*.csv` (from ExportResult.filename) |
| Attachment content-type | `text/html` | `text/csv` |
| Skip condition | No office_phone/vertical resolution OR all tables failed | No office_phone OR zero CSV rows OR business not ACTIVE |
| Pre-execution activity check | None (enumerates only ACTIVE section Offers) | Bulk pre-resolve Business activities, filter non-ACTIVE |
| Entity resolution path | Offer -> OfferHolder -> Unit -> UnitHolder -> Business (via `ResolutionContext`) | ContactHolder -> Business (via `ResolutionContext`, single hop) |
| In-run cache | `_business_cache: dict[business_gid -> (phone, vertical, name)]` | `_activity_map: dict[business_gid -> AccountActivity\|None]` |
| Feature flag env var | `AUTOM8_EXPORT_ENABLED` | `AUTOM8_AUDIT_ENABLED` |
| DMS namespace | `"Autom8y/AsanaInsights"` | `"Autom8y/AsanaAudit"` |
| Default max concurrency | 5 | 5 |
| Default date range | N/A | 30 days |

### How to Add a Third Reporting Bridge Workflow

A third bridge workflow (e.g., "payment-reconciliation-report") requires these artifacts:

1. **Workflow class** at `src/autom8_asana/automation/workflows/{name}.py`:
   - Inherit from `AttachmentReplacementMixin, WorkflowAction` (in that MRO order).
   - Set `_attachments_client` in `__init__`.
   - Implement `workflow_id` property (convention: `"kebab-case-name"`).
   - Implement `validate_async()`: check feature flag env var, check `DataServiceClient` circuit breaker.
   - Implement `enumerate_async(scope)`: handle `scope.has_entity_ids` targeting path; handle full enumeration path with optional `scope.limit` truncation.
   - Implement `execute_async(entities, params)`: fan-out with `asyncio.Semaphore(max_concurrency)`; return `WorkflowResult`.
   - Entity resolution must follow the ResolutionContext pattern (see existing workflows for reference).
   - File upload: call `self._attachments_client.upload_async(parent=entity_gid, file=..., name=filename, content_type=...)`.
   - File cleanup: call `self._delete_old_attachments(entity_gid, attachment_pattern, exclude_name=filename)`.

2. **Lambda handler** at `src/autom8_asana/lambda_handlers/{name}.py`:
   - Call `bootstrap()` at module import time.
   - Define `_create_workflow(asana_client, data_client) -> WorkflowAction` with deferred import.
   - Instantiate `WorkflowHandlerConfig` with `workflow_factory`, `workflow_id`, `log_prefix`, `default_params`, `response_metadata_keys`, and `dms_namespace`.
   - Call `handler = create_workflow_handler(_config)`.
   - Entry point: `autom8_asana.lambda_handlers.{name}.handler`.

3. **Feature flag env var**: Add `{NAME}_ENABLED` env var, check in `validate_async()`, document in the handler module's docstring under "Environment Variables Required".

4. **Register in `WorkflowRegistry`** if the workflow will also be dispatched by `PollingScheduler` (not required for Lambda-only workflows, but needed for CLI/scheduler invocation).

---

## Implementation Map

### Shared Infrastructure Files

| File | Role | Key Types |
|---|---|---|
| `src/autom8_asana/automation/workflows/base.py` | WorkflowAction ABC, result types | `WorkflowAction`, `WorkflowResult`, `WorkflowItemError` |
| `src/autom8_asana/automation/workflows/mixins.py` | Shared attachment logic | `AttachmentReplacementMixin._delete_old_attachments()` |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | Lambda factory, shared handler scaffolding | `WorkflowHandlerConfig`, `create_workflow_handler()` |
| `src/autom8_asana/core/scope.py` | Invocation contract | `EntityScope`, `EntityScope.from_event()`, `EntityScope.to_params()` |
| `src/autom8_asana/lambda_handlers/cloudwatch.py` | CloudWatch metric emission | `emit_metric()` |
| `src/autom8_asana/clients/data/client.py` | Shared data source | `DataServiceClient` |

### Per-Instance Files: InsightsExportWorkflow

| File | Role |
|---|---|
| `src/autom8_asana/automation/workflows/insights_export.py` | Workflow implementation |
| `src/autom8_asana/automation/workflows/insights_formatter.py` | HTML report composition (`compose_report()`, `HtmlRenderer`, `StructuredDataRenderer`) |
| `src/autom8_asana/automation/workflows/insights_tables.py` | 12 table definitions (`TABLE_SPECS`, `TableSpec`, `DispatchType`) |
| `src/autom8_asana/automation/workflows/static/insights_report.css` | Inlined CSS for HTML report |
| `src/autom8_asana/automation/workflows/static/insights_report.js` | Inlined JS for HTML report |
| `src/autom8_asana/automation/workflows/section_resolution.py` | `resolve_section_gids()` utility for section-targeted enumeration |
| `src/autom8_asana/lambda_handlers/insights_export.py` | Lambda entry point (`handler`) |

### Per-Instance Files: ConversationAuditWorkflow

| File | Role |
|---|---|
| `src/autom8_asana/automation/workflows/conversation_audit.py` | Workflow implementation |
| `src/autom8_asana/lambda_handlers/conversation_audit.py` | Lambda entry point (`handler`) |

### Key Type Signatures

```python
# WorkflowResult (base.py)
@dataclass
class WorkflowResult:
    workflow_id: str
    started_at: datetime
    completed_at: datetime
    total: int
    succeeded: int
    failed: int
    skipped: int
    errors: list[WorkflowItemError]
    metadata: dict[str, Any]

    @property
    def duration_seconds(self) -> float: ...
    @property
    def failure_rate(self) -> float: ...
    def to_response_dict(self, extra_metadata_keys: list[str] | None = None) -> dict[str, Any]: ...

# WorkflowItemError (base.py)
@dataclass
class WorkflowItemError:
    item_id: str          # entity GID
    error_type: str       # e.g., "export_failed", "circuit_breaker_open"
    message: str
    recoverable: bool = True

# WorkflowHandlerConfig (workflow_handler.py)
@dataclass(frozen=True)
class WorkflowHandlerConfig:
    workflow_factory: Callable[..., WorkflowAction]   # (asana_client, data_client) -> WorkflowAction
    workflow_id: str
    log_prefix: str
    default_params: dict[str, Any]
    response_metadata_keys: tuple[str, ...] = ()
    requires_data_client: bool = True
    dms_namespace: str | None = None

# EntityScope (core/scope.py)
@dataclass(frozen=True)
class EntityScope:
    entity_ids: tuple[str, ...] = ()
    section_filter: frozenset[str] = frozenset()
    limit: int | None = None
    dry_run: bool = False
    @classmethod def from_event(cls, event: dict[str, Any]) -> EntityScope: ...
    @property def has_entity_ids(self) -> bool: ...
    def to_params(self) -> dict[str, Any]: ...  # returns {"dry_run": bool}
```

### Data Flow: InsightsExportWorkflow

```
Lambda event (EventBridge daily, 6:00 AM ET)
    -> EntityScope.from_event(event)
    -> InsightsExportWorkflow.validate_async()
         -> check AUTOM8_EXPORT_ENABLED env var
         -> check DataServiceClient._circuit_breaker.check()
    -> InsightsExportWorkflow.enumerate_async(scope)
         -> if scope.has_entity_ids: return [{gid, name=None}, ...]
         -> else: resolve ACTIVE section GIDs via resolve_section_gids()
              -> parallel section fetch (Semaphore(5))
              -> fallback: project-level fetch + OFFER_CLASSIFIER.classify()
    -> InsightsExportWorkflow.execute_async(entities, params)
         -> asyncio.Semaphore(5) fan-out
         -> for each Offer:
              _resolve_offer(offer_gid)
                  -> Offer -> OfferHolder -> Unit -> UnitHolder -> Business (ResolutionContext)
                  -> cache result in _business_cache[business_gid]
              _fetch_all_tables(office_phone, vertical, ...)
                  -> asyncio.gather(12 _fetch_table calls)
                  -> each _fetch_table dispatches via match spec.dispatch_type:
                       INSIGHTS -> data_client.get_insights_async(factory, office_phone, vertical, period)
                       APPOINTMENTS -> data_client.get_appointments_async(office_phone, days, limit)
                       LEADS -> data_client.get_leads_async(office_phone, days, exclude_appointments, limit)
                       RECONCILIATION -> data_client.get_reconciliation_async(office_phone, vertical, period, window_days)
                           -> phone filter (D-02): strip rows where office_phone != target
              compose_report(InsightsReportData)
                  -> HtmlRenderer.render_document() with inline CSS+JS
              attachments_client.upload_async(offer_gid, file=html_bytes, name=filename, content_type="text/html")
              _delete_old_attachments(offer_gid, "insights_export_*.html", exclude=filename)
    -> WorkflowResult
         metadata: {per_offer_table_counts, total_tables_succeeded, total_tables_failed}
    -> emit_metric(WorkflowDuration), emit_metric(WorkflowSuccessRate)
    -> emit_success_timestamp("Autom8y/AsanaInsights")
```

### Data Flow: ConversationAuditWorkflow

```
Lambda event (EventBridge weekly schedule)
    -> EntityScope.from_event(event)
    -> ConversationAuditWorkflow.validate_async()
         -> check AUTOM8_AUDIT_ENABLED env var
         -> check DataServiceClient._circuit_breaker.check()
    -> ConversationAuditWorkflow.enumerate_async(scope)
         -> if scope.has_entity_ids: return [{gid, name=None, parent_gid=None, parent=None}, ...]
         -> else:
              _enumerate_contact_holders()  [project-level fetch, non-completed only]
              _pre_resolve_business_activities(holders)  [bulk parallel, Semaphore(8)]
              filter to holders where business activity == ACTIVE
    -> ConversationAuditWorkflow.execute_async(entities, params)
         -> compute start_date / end_date from date_range_days (default 30)
         -> asyncio.Semaphore(5) fan-out
         -> for each ContactHolder:
              _resolve_business_activity(parent_gid)  [cache hit after pre-resolve]
              skip if activity != ACTIVE
              _resolve_office_phone(holder_gid, parent_gid)
                  -> ContactHolder -> Business (ResolutionContext, direct business_gid= path)
              data_client.get_export_csv_async(office_phone, start_date, end_date)
                  -> returns ExportResult(csv_content, row_count, truncated, filename)
              skip if export.row_count == 0
              attachments_client.upload_async(holder_gid, file=io.BytesIO(csv_content), name=export.filename, content_type="text/csv")
              _delete_old_attachments(holder_gid, "conversations_*.csv", exclude=export.filename)
    -> WorkflowResult
         metadata: {truncated_count, activity_skipped_count}
    -> emit_metric(WorkflowDuration), emit_metric(WorkflowSuccessRate)
    -> emit_success_timestamp("Autom8y/AsanaAudit")
```

### Lambda Handler Factory: What `create_workflow_handler()` Provides

`create_workflow_handler(config)` returns a `handler(event, context)` function that:

1. Logs `{log_prefix}_started`.
2. Emits `WorkflowExecutionCount` metric.
3. Constructs `EntityScope.from_event(event)`.
4. Merges `default_params` with event overrides (whitelisted: only keys present in `default_params` are overridable).
5. Injects `dry_run` from scope via `scope.to_params()`.
6. Instantiates `AsanaClient` and (if `requires_data_client`) `DataServiceClient` (via `async with`).
7. Calls `workflow_factory(asana_client, data_client)` with deferred import.
8. Calls `_validate_enumerate_and_run(workflow, scope, params)`.
9. On validation failure: returns `{"statusCode": 200, "body": {"status": "skipped", ...}}` and emits `WorkflowValidationSkipped`.
10. On success: serializes `WorkflowResult.to_response_dict()`, emits `WorkflowDuration` + `WorkflowSuccessRate`, optionally calls `emit_success_timestamp(dms_namespace)`.
11. On any uncaught exception: returns `{"statusCode": 500, ...}` and emits `WorkflowExecutionError`.

### Test Locations

| Test file | Covers |
|---|---|
| `tests/unit/automation/workflows/test_conversation_audit.py` | `ConversationAuditWorkflow` unit tests |
| `tests/unit/automation/workflows/test_insights_export.py` | `InsightsExportWorkflow` unit tests |
| `tests/unit/automation/workflows/test_attachment_mixin.py` | `AttachmentReplacementMixin` unit tests |
| `tests/unit/automation/workflows/test_base.py` | `WorkflowAction`, `WorkflowResult`, `WorkflowItemError` |
| `tests/unit/automation/workflows/test_insights_formatter.py` | `compose_report()`, `HtmlRenderer` |
| `tests/unit/lambda_handlers/test_insights_export.py` | Insights export Lambda handler |
| `tests/unit/lambda_handlers/test_workflow_handler.py` | `create_workflow_handler()` factory |
| `tests/integration/automation/workflows/test_conversation_audit_e2e.py` | ConversationAuditWorkflow end-to-end (265 lines) |

Note: No dedicated `tests/unit/lambda_handlers/test_conversation_audit.py` exists. Coverage relies on the shared `test_workflow_handler.py`.

---

## Boundaries and Failure Modes

### Shared Failure Patterns

**Kill switch**: Both workflows check an env var in `validate_async()`. Values `"false"`, `"0"`, `"no"` (case-insensitive) abort the workflow before execution. The Lambda returns `{"status": "skipped", "reason": "validation_failed"}`.

| Workflow | Env Var | Default |
|---|---|---|
| InsightsExportWorkflow | `AUTOM8_EXPORT_ENABLED` | enabled (any value other than false/0/no) |
| ConversationAuditWorkflow | `AUTOM8_AUDIT_ENABLED` | enabled |

**Circuit breaker check**: Both workflows call `await self._data_client._circuit_breaker.check()` in `validate_async()`. If the circuit breaker is open (5 failures within 60s), the workflow is skipped for that scheduler cycle. A sustained open circuit breaker silently skips all affected workflows until recovery (30s timeout, then HALF-OPEN with 1-success reset). This is the intended behavior.

**Per-entity isolation**: All entity processing failures are caught by broad-catch exception handlers at the per-entity level. A failing entity produces a `WorkflowItemError(recoverable=True)` and increments `failed`, but the batch continues. This is the canonical failure contract.

**Upload-first atomicity**: The attachment replacement is deliberately non-atomic. The upload completes first, then old files are deleted. During a brief window, both old and new attachments are visible in Asana. Old attachment deletion failures are non-fatal: logged as warnings, swallowed. The next execution run will clean up.

**Dry-run mode**: When `scope.dry_run=True`, both workflows skip all write operations. InsightsExport writes preview HTML files to `.wip/` directory locally instead of uploading. ConversationAudit logs the skip. Both include dry-run metadata in the `WorkflowResult`.

### Per-Instance Failure Patterns

**InsightsExportWorkflow-specific**:

- **Partial table success**: If some (but not all) tables fail, the HTML report is still composed and uploaded with error sections for the failed tables. Only if ALL 12 tables fail does the offer get `status="failed"`.
- **Reconciliation cross-phone contamination**: The reconciliation endpoint may return rows from multiple businesses. `_fetch_table()` applies phone-number filtering when it detects multiple `office_phone` values in the response (D-02 decision). This is a defensive guard.
- **Reconciliation pending state**: When all payment indicator columns are null across all rows, the formatter renders a "payment data pending" message instead of an empty table.
- **Business resolution cache**: `_business_cache` and `_offer_to_business` are per-run, in-memory only. Multiple sibling Offers sharing the same parent Business hit the cache after the first resolution.
- **Section-targeted enumeration with fallback**: Primary path uses section GIDs to enumerate only ACTIVE offers. If section resolution fails, it falls back to project-level fetch with `OFFER_CLASSIFIER` filtering.

**ConversationAuditWorkflow-specific**:

- **Activity pre-filtering**: During `enumerate_async`, the workflow bulk-resolves all parent Business activities (Semaphore(8)) and removes non-ACTIVE holders before they enter `execute_async`.
- **`ExportError` handling**: Only `reason="client_error"` is non-recoverable. All other reasons are marked `recoverable=True`.
- **Export truncation**: Server-side 10K row cap. `ExportResult.truncated=True` increments `truncated_count` in metadata (informational).
- **Zero-row skip**: Holders with no conversation data produce `row_count=0` and are counted as `skipped` (not `failed`).

### What Can Break Silently

1. **Circuit breaker sustained open**: Both workflows silently skip every execution cycle. Only the dead-man's-switch DMS metric going stale surfaces this.
2. **Activity pre-resolution failures in ConversationAudit**: `_resolve_business_activity` broad-catches all exceptions and records `None`. Holders with `activity=None` are silently skipped.
3. **Section resolution failure in InsightsExport**: Falls through to project-level fallback silently.
4. **Old attachment delete failures**: Non-fatal, swallowed. Stale attachments accumulate until next successful run.

### What a Third Workflow Must Handle

When implementing a third bridge workflow, these are the non-obvious obligations:

1. **Idempotency**: Upload-first + delete-old must be the attachment update strategy.
2. **Office_phone as data key**: The data service is always keyed by `(office_phone, vertical)` or just `office_phone`. Entity resolution to Business is always required.
3. **`scope.has_entity_ids` fast-path**: Must be supported for targeted manual re-runs.
4. **Feature flag + circuit breaker in `validate_async()`**: Both checks are required.
5. **In-run caching**: For cross-entity shared resolution, build a per-run dict cache. Do NOT persist across runs.
6. **`requires_data_client=True`** in `WorkflowHandlerConfig` (default): Set to `False` if the workflow does not use `DataServiceClient`.
7. **PII contract**: Phone numbers must be masked before logging via `mask_phone_number` from `src/autom8_asana/clients/data/_pii.py`.

---

## Knowledge Gaps

1. **`insights_export.py` double bootstrap**: The Lambda handler calls `bootstrap()` twice at module import. Harmless but a code smell.

2. **Static assets size**: `insights_report.css` and `insights_report.js` are loaded at import time and inlined into every HTML report. Their size and browser compatibility are not documented.

3. **EventBridge trigger schedules**: Not in this repository. Actual cron expressions and retry policies are externally configured.

4. **`conversation_audit` Lambda test gap**: No `tests/unit/lambda_handlers/test_conversation_audit.py`. Coverage relies on the generic `test_workflow_handler.py`.

5. **WorkflowRegistry registration**: Whether both bridge workflows are registered in `automation/workflows/registry.py` was not verified. The Lambda path does not use the registry.

6. **`section_resolution.py` failure contract**: Used by InsightsExport for section-targeted enumeration. The broad-catch fallback means failures are silent except for a warning log.
