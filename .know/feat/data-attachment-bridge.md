---
domain: feat/data-attachment-bridge
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/automation/workflows/insights/**/*.py"
  - "./src/autom8_asana/automation/workflows/conversation_audit/**/*.py"
  - "./src/autom8_asana/automation/workflows/mixins.py"
  - "./src/autom8_asana/automation/workflows/bridge_base.py"
  - "./src/autom8_asana/lambda_handlers/insights_export.py"
  - "./src/autom8_asana/lambda_handlers/conversation_audit.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.83
format_version: "1.0"
---

# Data Attachment Bridge (Backend-to-Asana Reporting Pipeline)

## Purpose and Design Rationale

The bridge pushes data from `autom8_data` into Asana as file attachments. Two concrete workflows:

- **InsightsExportWorkflow**: Daily at 6:00 AM ET. For every active Offer, fetches 12 tables from autom8_data, composes HTML report, uploads as attachment.
- **ConversationAuditWorkflow**: Weekly. For every active ContactHolder, fetches 30-day conversation CSV, replaces previous attachment.

Both are feature-flag-gated (`AUTOM8_EXPORT_ENABLED` / `AUTOM8_AUDIT_ENABLED`) and use **upload-first attachment replacement** (new file uploaded before old deleted).

## Conceptual Model

### Class Hierarchy

`WorkflowAction` -> `BridgeWorkflowAction` (shared: validate, enumerate, semaphore fan-out) -> `InsightsExportWorkflow` / `ConversationAuditWorkflow`. `AttachmentReplacementMixin` provides `_delete_old_attachments()`.

### 12-Table Dispatch (InsightsExport)

`TABLE_SPECS` declares 12 tables with `DispatchType` (INSIGHTS, APPOINTMENTS, LEADS, RECONCILIATION). All 12 fetched concurrently via `asyncio.gather()`. Individual table failures isolated; full failure (all 12) fails the offer.

### Resolution Chain

InsightsExport: Offer -> OfferHolder -> Unit -> UnitHolder -> Business (cached per batch run).
ConversationAudit: ContactHolder -> Business (direct parent), with bulk activity pre-resolution.

## Implementation Map

10 key files: base.py, bridge_base.py, mixins.py, insights/workflow.py, insights/tables.py, insights/formatter.py, conversation_audit/workflow.py, lambda_handlers/insights_export.py, conversation_audit.py, workflow_handler.py.

### CloudWatch Metrics

WorkflowExecutionCount, WorkflowDuration, WorkflowSuccessRate, BridgeFleetHealth (fleet-level health signal), DMS timestamp (dead-man's-switch), BridgeExecutionComplete domain event.

## Boundaries and Failure Modes

- Kill-switch env vars + DataServiceClient circuit breaker check in `validate_async()`
- Semaphore(5) default concurrency per workflow run
- Per-entity BROAD-CATCH isolation
- SCAR-016 (date_range_days not forwarded), SCAR-017 (csv_row_count missing), SCAR-026 (non-existent method masked by MagicMock)

## Knowledge Gaps

1. `formatter.py` HTML composition logic not read.
2. `ResolutionContext` multi-hop traversal internals not traced.
3. `EntityScope.from_event()` event schema not documented.
