---
domain: feat/payment-reconciliation
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/reconciliation/"
  - "./src/autom8_asana/lambda_handlers/payment_reconciliation.py"
  - "./src/autom8_asana/lambda_handlers/reconciliation_runner.py"
  - "./src/autom8_asana/models/business/reconciliation.py"
  - "./src/autom8_asana/automation/workflows/payment_reconciliation/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.93
format_version: "1.0"
---

# Payment Reconciliation Processing (Excel Output + Shadow Section-Move Engine)

## Purpose and Design Rationale

Payment reconciliation runs across two distinct execution surfaces that share domain vocabulary
but have no runtime coupling:

**Surface A — Excel Report Delivery** (`payment_reconciliation` Lambda):
Triggered weekly (EventBridge, Monday 08:00 ET). For each active (non-completed) Unit task in
the Business Units project, resolves the Unit → UnitHolder → Business chain (2-hop), fetches
payment data from `autom8y-data`, formats as a multi-sheet `.xlsx` workbook via `openpyxl`, and
uploads as an attachment to the Unit task (upload-first, then deletes older matching attachments).
Gate: `AUTOM8_RECONCILIATION_ENABLED` env var (default: enabled per lambda handler comment).

**Surface B — Section Move Reconciliation** (`reconciliation_runner` shadow function):
Post-cache-warm execution. Retrieves Unit and Offer DataFrames from the warmed cache, identifies
mismatches between a unit's current section and the section indicated by either (a) pipeline
activity (PRIMARY — from `pipeline_stage_aggregator`) or (b) offer activity (SECONDARY fallback).
Always `dry_run=True` in production; gate: `ASANA_RECONCILIATION_SHADOW_ENABLED`.

Design decisions documented in source comments:
- **ADR-pipeline-stage-aggregation Phase 3**: `pipeline_summary` is the PRIMARY derivation
  signal; offer comparison is SECONDARY. `DERIVATION_TABLE` is built dynamically from
  `lifecycle_stages.yaml` via `load_config().build_derivation_table()`.
- **ADR-reconciliation-executor-materialization**: Live executor path is materialized
  (wired to `task_service.move_to_section`) but never invoked in production (`dry_run=True`
  throughout the shadow path).
- **ADR-bridge-intermediate-base-class**: `PaymentReconciliationWorkflow` is the third bridge
  built on the `BridgeWorkflowAction` platform (Sprint-5, Workstream C validation).
- **REVIEW-reconciliation-deep-audit**: Corrected P0-A (column name `section` not `section_name`)
  and P0-B (exclusion uses `EXCLUDED_SECTION_NAMES` with 4 entries, not `UNIT_CLASSIFIER.ignored`
  with 1 entry) — both were production-silent failures.
- **FLAG-1 (architectural)**: Reconciliation orchestration functions live in `lambda_handlers/`
  rather than `services/` to avoid circular dependencies with service modules.

Tradeoffs accepted:
- Executor live path is wired but never triggered. Section-move reconciliation remains observability-only until SCAR-REG-001 (placeholder GIDs) is resolved.
- `pipeline_summary` is computed ephemerally per warm cycle (not cached) per ADR-pipeline-stage-aggregation Option C.

## Conceptual Model

### Two-Signal Priority Model (Surface B)

PRIMARY — `pipeline_summary` (produced by `pipeline_stage_aggregator`):
- Scans warmed pipeline DataFrames (entities named `process_*`)
- Produces per-(office_phone, vertical): `latest_process_type`, `latest_process_section`,
  `latest_created`
- Processor builds `_pipeline_index: dict[tuple[str, str], tuple[str, str]]` from this
- When a pipeline entry is ACTIVE or ACTIVATING → consult `DERIVATION_TABLE` for target section
- When INACTIVE, IGNORED, or unknown → fall through to SECONDARY

SECONDARY — `offer_df` comparison (existing logic):
- Composite key `(office_phone, vertical)` → section for exact match
- Phone-only fallback: `phone → (section, vertical)`, first-occurrence wins; logs
  `reconciliation_vertical_mismatch` warning
- `OFFER_CLASSIFIER.classify(offer_section)` → `AccountActivity`; maps to valid unit sections
  via `OFFER_ACTIVITY_VALID_UNIT_SECTIONS` and default via `OFFER_ACTIVITY_DEFAULT_UNIT_SECTION`

### Section Exclusion: GID-First, Name Fallback (LBC-004)

Four excluded sections (Templates, Next Steps, Account Review, Account Error):
- GID-based check fires first (`section_gid in EXCLUDED_SECTION_GIDS`)
- Name fallback fires only when GID is absent (`EXCLUDED_SECTION_NAMES` — 4 entries)
- **DO NOT** substitute `UNIT_CLASSIFIER.ignored` (contains only `{"Templates"}` — misses 3 of 4)
- This is a load-bearing constraint: `LBC-004` in `.know/design-constraints.md`

### SCAR-REG-001: Unverified Section GIDs (Production Blocker)

All GIDs in `section_registry.py` are sequential placeholders (1201081073731600–1201081073731603
for excluded; 1201081073731610–1201081073731624 for unit sections). `_validate_gid_set()` fires at
module import time, emitting WARNING via `section_registry_gids_appear_fabricated` when sequential
pattern is detected. Four `VERIFY-BEFORE-PROD` annotations at lines 57, 79, 94, 128. See also
`EC-007` and `RISK-001` in design-constraints.md.

### Excel Workbook Structure (Surface A)

Sheet layout from `ExcelFormatEngine.render()`:
- Tab 0: "Summary" — header block (Business Name, Vertical, Phone, Generated timestamp) +
  aggregate totals (Total Rows, Total Spend, Total Payments)
- Tab 1: "Reconciliation" — full detail rows with auto-width columns
- Tabs 2+: Per-period sheets (only when data contains a `period` field AND multiple periods exist)

PII contract: `office_phone` is always masked via `mask_phone_number()` before logging and before
being passed to `ExcelFormatEngine`. The raw phone is used only for `DataServiceClient` API call
and `ResolutionContext` traversal.

### Reconciliation Lifecycle States

`AccountActivity` enum (from `models.business.activity`):
- `ACTIVE` → valid unit sections: `{Active, Month 1, Consulting}`; default target: `Active`
- `ACTIVATING` → valid: `{Onboarding, Implementing, Preview, Engaged, Scheduled}`; default: `Onboarding`
- `INACTIVE` → valid: `{Paused, Unengaged, Cancelled, No Start}`; default: `Paused`
- `IGNORED` → no action (terminal offer states)

## Implementation Map

### `reconciliation/` package (5 source files + `__init__.py`)

| File | Purpose | Key Types / Functions |
|------|---------|----------------------|
| `engine.py` | Orchestrator | `run_reconciliation(unit_df, offer_df, *, config, pipeline_summary)` → `ReconciliationResult`; `ReconciliationConfig(dry_run, max_actions)` |
| `processor.py` | Batch matching engine | `ReconciliationBatchProcessor.__init__` + `.process()` → `ProcessorResult`; `ReconciliationAction(unit_gid, phone, vertical, current_section, target_section, reason)`; `DERIVATION_TABLE` (loaded from YAML at import); `OFFER_ACTIVITY_VALID_UNIT_SECTIONS`, `OFFER_ACTIVITY_DEFAULT_UNIT_SECTION` |
| `executor.py` | Async section-move executor | `execute_actions(actions, *, dry_run, task_service, client, project_gid, section_name_to_gid)` → `ExecutionResult(succeeded, failed, skipped, errors)` |
| `report.py` | Metric emission + anomaly detection | `build_report(result)` → `ReconciliationReport`; `emit_report_metrics(report)` — emits `ReconciliationExcludedCount`, `ReconciliationExclusionRate`; threshold 50% exclusion rate triggers `reconciliation_exclusion_rate_anomaly` WARNING |
| `section_registry.py` | GID/name constants with startup validation | `EXCLUDED_SECTION_GIDS` (4), `EXCLUDED_SECTION_NAMES` (4), `UNIT_SECTION_GIDS` (15), `EXCLUDED_GID_TO_NAME`; `_validate_gid_set()` runs at import |

`__init__.py` re-exports: `EXCLUDED_SECTION_NAMES`, `ReconciliationAction`, `ReconciliationBatchProcessor`, `ReconciliationConfig`, `ReconciliationResult`, `run_reconciliation`.

### `automation/workflows/payment_reconciliation/` (2 source files + `__init__.py`)

| File | Purpose | Key Types / Functions |
|------|---------|----------------------|
| `workflow.py` | Excel delivery bridge workflow | `PaymentReconciliationWorkflow(BridgeWorkflowAction)` — `.enumerate_entities()` (non-completed Units from `UNIT_PROJECT_GID`), `@trace_reconciliation .process_entity()` (resolve → fetch → format → upload → cleanup); `_resolve_unit()` (2-hop with `_business_cache`); `_build_result_metadata()` (total_excel_rows) |
| `formatter.py` | openpyxl Excel render engine | `ExcelFormatEngine.render(data)` → bytes; `compose_excel(response_data, *, office_phone, vertical, business_name)` → `(bytes, row_count)` |

Constants exported from `__init__.py`: `DEFAULT_MAX_CONCURRENCY=5`, `DEFAULT_ATTACHMENT_PATTERN="reconciliation_*.xlsx"`, `DEFAULT_LOOKBACK_DAYS=30`.

### Lambda Handlers (2 files)

| File | Trigger | Purpose |
|------|---------|---------|
| `lambda_handlers/payment_reconciliation.py` | EventBridge weekly | Creates `WorkflowHandlerConfig(workflow_id="payment-reconciliation", dms_namespace="Autom8y/AsanaReconciliation")` and `handler = create_workflow_handler(_config)` |
| `lambda_handlers/reconciliation_runner.py` | Called from `cache_warmer.py` post-warm | `_run_reconciliation_shadow(completed_entities, get_project_gid, cache, invocation_id, pipeline_summary)` — entity guard (both unit+offer must be warmed), retrieves DataFrames, calls `run_reconciliation(dry_run=True)`, calls `execute_actions(dry_run=True)`, emits report; BROAD-CATCH never crashes cache warmer |

**pipeline_stage_aggregator wiring** (documented for completeness):
`cache_warmer.py:48` imports `_aggregate_pipeline_stages` from `lambda_handlers/pipeline_stage_aggregator.py`. After cache warm completes, `cache_warmer.py:662` calls `_aggregate_pipeline_stages(completed_entities, cache, invocation_id)` → `pl.DataFrame | None`, then passes `pipeline_summary` to `_run_reconciliation_shadow` at line 682. The aggregator produces per-(phone, vertical) summary by scanning all `process_*` DataFrames, filtering to `is_completed=False`, and selecting the most-recent `created` row per group.

### Domain Model

`models/business/reconciliation.py`: `Reconciliation(BusinessEntity)` — minimal typed model for children under `ReconciliationHolder`. Uses descriptor-based navigation (TDD-HARDENING-C, ADR-0075, ADR-0076). Navigation: `reconciliation_holder` (HolderRef), `business` (ParentRef). Does NOT participate in Surface A or Surface B logic; represents Asana reconciliation record objects in the entity graph.

### Data Flow

**Surface A (Excel delivery):**
```
EventBridge trigger
  → payment_reconciliation.handler (create_workflow_handler)
  → PaymentReconciliationWorkflow.enumerate_entities()
      → tasks.list_async(project=UNIT_PROJECT_GID, completed_since="now")
  → For each Unit (concurrency=5):
      @trace_reconciliation process_entity()
        → _resolve_unit() [ResolutionContext 2-hop → (office_phone, vertical, business_name)]
        → DataServiceClient.get_reconciliation_async(phone, vertical, period="monthly", window_days=30)
        → compose_excel(response.data, office_phone=masked_phone, ...)  [ExcelFormatEngine.render()]
        → attachments.upload_async(parent=unit_gid, file=BytesIO(excel_bytes), ...)
        → _delete_old_attachments(unit_gid, pattern, exclude=new_filename)
  → WorkflowResult with total_excel_rows metadata
```

**Surface B (Shadow section-move):**
```
cache_warmer Lambda post-warm
  → _aggregate_pipeline_stages(completed_entities, cache, invocation_id)
      → Scan process_* DataFrames → group by (phone, vertical) → latest active
      → pl.DataFrame | None (pipeline_summary)
  → _run_reconciliation_shadow(completed_entities, get_project_gid, cache, invocation_id, pipeline_summary)
      [entity guard: both "unit" + "offer" must be warmed]
      → cache.get_async(unit_project_gid, "unit") / ("offer")
      → run_reconciliation(unit_df, offer_df, config=ReconciliationConfig(dry_run=True), pipeline_summary=pipeline_summary)
          → ReconciliationBatchProcessor(unit_df, offer_df, pipeline_summary=pipeline_summary)
              → _build_pipeline_index(pipeline_summary) [PRIMARY]
              → _build_offer_activity_index(offer_df)   [GID-based]
              → _build_offer_phone_indexes(offer_df)    [SECONDARY composite + phone-only]
              → .process() → ProcessorResult (actions, counts)
      → execute_actions(actions, dry_run=True)  [logs, no API calls]
      → build_report(processor_result) → emit_report_metrics(report)
```

### Test Coverage

| Test File | Covers | Size |
|-----------|--------|------|
| `tests/unit/reconciliation/test_processor.py` | `ReconciliationBatchProcessor` — P0-A column contract, P0-B exclusion logic, pipeline primary signal, offer secondary, vertical mismatch fallback, adversarial edge cases | 1640 lines |
| `tests/unit/reconciliation/test_executor.py` | `execute_actions` dry_run and live paths, dependency injection validation | 320 lines |
| `tests/unit/reconciliation/test_section_registry.py` | `_validate_gid_set`, `_looks_sequential`, startup warning behavior (SCAR-REG-001) | 301 lines |
| `tests/unit/reconciliation/test_contract.py` | Cross-module contract checks | 78 lines |
| `tests/unit/reconciliation/test_adversarial.py` | Adversarial / edge inputs to processor | 245 lines |
| `tests/unit/automation/workflows/payment_reconciliation/test_formatter.py` | `ExcelFormatEngine.render()`, `compose_excel()`, `_safe_sum`, `_sanitize_sheet_name` | 329 lines |
| `tests/unit/automation/workflows/test_payment_reconciliation.py` | `PaymentReconciliationWorkflow` (integration-style) | present |
| `tests/unit/lambda_handlers/test_payment_reconciliation_handler.py` | Lambda handler wiring | present |
| `tests/unit/lambda_handlers/test_reconciliation_runner.py` | Shadow runner behavior, entity guard, broad-catch isolation | present |

**Remaining gap**: `engine.py` and `report.py` lack dedicated test files (no `test_engine.py`, no `test_report.py`). Engine is exercised indirectly through processor tests. Report logic is simple enough that the gap is low risk, but remains undocumented.

## Boundaries and Failure Modes

### Scope Boundaries ("this feature does NOT")

- **Does NOT execute section moves in production**: `dry_run=True` is hardcoded in `ReconciliationConfig` on every production call path. Live executor requires manual injection of `task_service`, `client`, `project_gid`, `section_name_to_gid`.
- **Does NOT manage Asana section GIDs directly**: GIDs in `section_registry.py` are sequential placeholders (SCAR-REG-001). No production reconciliation against real GIDs is possible until they are replaced with verified values.
- **Does NOT persist `pipeline_summary`**: The aggregation result is ephemeral, computed per-warm-cycle and never written to cache.
- **Does NOT handle cross-project section name collisions**: `OFFER_ACTIVITY_VALID_UNIT_SECTIONS` maps to unit-project section names; offer sections come from a different Asana project — names are compared only after classification through `AccountActivity`, not by string equality.
- **Does NOT have a REST API surface**: Both surfaces are Lambda-triggered; no route handlers.

### Error Paths and Recovery

| Path | Error Handling |
|------|---------------|
| Surface B as a whole | BROAD-CATCH in `_run_reconciliation_shadow` — any exception is caught, logged as `reconciliation_shadow_error` WARNING, and swallowed. Cache warmer is never affected. |
| `_resolve_unit()` (Surface A) | Returns `None` → `process_entity()` returns `_UnitOutcome(status="skipped", reason="no_resolution")` |
| No reconciliation data from DataServiceClient | Returns `_UnitOutcome(status="skipped", reason="no_data")` |
| Live executor dependency missing | `RuntimeError` raised with specific list of missing params |
| Live executor API failure | Per-action `except Exception` (BLE001 noqa) — logs `reconciliation_executor_error`, increments `failed`, continues next action |
| Exclusion rate >50% | `ReconciliationReport.is_anomalous=True` → `reconciliation_exclusion_rate_anomaly` WARNING logged |
| DataFrame lacks `section` column | `P1-B` schema entry guard logs WARNING `reconciliation_schema_entry_guard` at import; `P0-A` check logs `reconciliation_unit_no_section_column` in `process()` |
| `pipeline_summary` missing required columns | `_build_pipeline_index` logs WARNING and returns empty dict; processor falls through to offer-based comparison |

### Known Limitations and Constraints

- **SCAR-REG-001** (RISK-001, EC-007): Sequential placeholder GIDs block live deployment. `VERIFY-BEFORE-PROD` at `section_registry.py:57,79,94,128`. Project GID for verification: `1201081073731555`. API: `GET /projects/1201081073731555/sections`.
- **RISK-002**: Phantom exclusion rate. Root cause: pre-P0-A, processor used `section_name` (non-existent column) → all units fell to no-section path → 100% exclusion rate. Fixed. Anomaly detection at 50% threshold guards against regression.
- **LBC-004**: `EXCLUDED_SECTION_NAMES` in `section_registry.py:109-120` is the authoritative 4-entry list. Do NOT substitute `UNIT_CLASSIFIER.ignored` (1 entry). This is a load-bearing constant (`LBC-004` in design-constraints).
- **`_business_cache` scope**: Per-run dict on `PaymentReconciliationWorkflow` instance, keyed by `business_gid`. Not persisted across invocations. Used to avoid redundant `ResolutionContext` traversals within one Lambda execution.
- **`pipeline_summary` construction origin**: `pipeline_stage_aggregator.py` — produces the DataFrame consumed as PRIMARY signal. Located at `lambda_handlers/pipeline_stage_aggregator.py`. Scans all `process_*` entities from warmed cache; `_derive_pipeline_type` strips `process_` prefix.
- **SCAR-020** (historical): `PhoneNormalizer` was wired only into matching engine, not reconciliation read path — caused reconciliation blindness. Fix in commit `09163c06`. Phone normalization now happens upstream of reconciliation processor.

### Interaction Points

| Boundary | Direction | Consumer |
|----------|-----------|---------|
| `DataServiceClient.get_reconciliation_async()` | Surface A calls | `clients/data/_endpoints/reconciliation.py` |
| `ResolutionContext` (2-hop) | Surface A calls | `resolution/context.py` |
| `TaskService.move_to_section()` | Executor calls (live, never in prod) | `services/task_service.py` |
| `DataFrameCache.get_async()` | Surface B reads | `cache/` subsystem |
| `pipeline_stage_aggregator._aggregate_pipeline_stages()` | `cache_warmer` calls | `lambda_handlers/pipeline_stage_aggregator.py` |
| `lifecycle_stages.yaml` | `processor.py` reads at import | `lifecycle/config.py:load_config()` |
| `BridgeWorkflowAction` | Surface A inherits | `automation/workflows/bridge_base.py` |
| `autom8y_telemetry.trace_reconciliation` | Surface A decorates | external SDK `autom8y-telemetry` |

### Configuration Boundaries

| Env Var | Surface | Default | Effect |
|---------|---------|---------|--------|
| `AUTOM8_RECONCILIATION_ENABLED` | A | enabled (handler comment) | Feature flag — disables Excel delivery |
| `ASANA_RECONCILIATION_SHADOW_ENABLED` | B | disabled | Feature flag — `"1"`, `"true"`, `"yes"` enables shadow run |
| `ASANA_PAT` | A | required | Asana authentication |
| `AUTOM8Y_DATA_URL` | A | required | `autom8y-data` base URL |
| `AUTOM8Y_DATA_API_KEY` | A | required | `autom8y-data` API key |

```metadata
{
  "slug": "payment-reconciliation",
  "category": "Business Domain",
  "complexity": "HIGH",
  "surfaces": ["excel-delivery", "section-move-shadow"],
  "source_files": 11,
  "test_files": 9,
  "production_blocker": "SCAR-REG-001",
  "load_bearing_constants": ["LBC-004"],
  "design_constraints": ["RISK-001", "RISK-002", "EC-007"],
  "feature_flags": ["AUTOM8_RECONCILIATION_ENABLED", "ASANA_RECONCILIATION_SHADOW_ENABLED"],
  "key_adrs": [
    "ADR-pipeline-stage-aggregation",
    "ADR-reconciliation-executor-materialization",
    "ADR-bridge-intermediate-base-class",
    "REVIEW-reconciliation-deep-audit"
  ]
}
```
