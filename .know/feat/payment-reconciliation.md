---
domain: feat/payment-reconciliation
generated_at: "2026-04-01T16:20:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/reconciliation/**/*.py"
  - "./src/autom8_asana/lambda_handlers/payment_reconciliation.py"
  - "./src/autom8_asana/lambda_handlers/reconciliation_runner.py"
  - "./src/autom8_asana/automation/workflows/payment_reconciliation/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Payment Reconciliation Processing (Excel Output)

## Purpose and Design Rationale

Payment Reconciliation runs across two execution surfaces:

**Surface A -- Excel Report Delivery** (`payment_reconciliation` Lambda): Weekly. For each active Unit, resolves to parent Business (2-hop), fetches payment data from `autom8_data`, formats as multi-sheet `.xlsx` via `openpyxl`, uploads as attachment. Upload-first pattern.

**Surface B -- Section Move Reconciliation** (`reconciliation_runner`, shadow-mode): Post-cache-warm. Retrieves Unit and Offer DataFrames, identifies mismatches between section placement and activity state, plans (but does not execute) section moves. Always `dry_run=True`.

Feature flags: `AUTOM8_RECONCILIATION_ENABLED` (Excel), `ASANA_RECONCILIATION_SHADOW_ENABLED` (shadow). Both default disabled.

## Conceptual Model

### Two-Signal Priority Model

**PRIMARY**: `pipeline_summary` (latest process type + section) -> `DERIVATION_TABLE` from lifecycle_stages.yaml.
**SECONDARY**: `offer_df` (offer section -> AccountActivity classification).

Pipeline signal takes precedence when process activity is ACTIVE/ACTIVATING.

### Offer Lookup: Composite Key with Phone-Only Fallback

Composite index `(office_phone, vertical)` for exact match. Phone-only fallback logs `reconciliation_vertical_mismatch` warning.

### Section Exclusion: GID-First, Name Fallback

4 excluded sections (Templates, Next Steps, Account Review, Account Error). GID-based check first, name fallback when GID absent.

### SCAR-REG-001: Unverified Section GIDs

**Production blocker**: All GIDs in `section_registry.py` are sequential placeholders not verified against live Asana API. `_validate_gid_set()` emits WARNING at import. `VERIFY-BEFORE-PROD` comments mark both GID sets.

## Implementation Map

### reconciliation/ package (6 files)

engine.py (orchestrator: `run_reconciliation`), processor.py (`ReconciliationBatchProcessor` -- builds 3 indexes, iterates units, emits `ReconciliationAction` list), executor.py (async execution with `dry_run` guard), report.py (metrics + anomaly detection: >50% exclusion rate triggers warning), section_registry.py (GID/name constants with startup validation).

### payment_reconciliation/ workflow (2 files)

workflow.py (`PaymentReconciliationWorkflow` extends `BridgeWorkflowAction` -- enumerate non-completed Units, 2-hop resolution with per-run `_business_cache`, fetch + format + upload + cleanup), formatter.py (`ExcelFormatEngine.render()` -- Summary sheet + Reconciliation detail + per-period sheets via openpyxl).

### Lambda handlers (2 files)

payment_reconciliation.py (Excel report via `create_workflow_handler`), reconciliation_runner.py (shadow-mode post-cache-warm, always dry_run=True, BROAD-CATCH isolated from cache warmer).

### Domain model

`models/business/reconciliation.py`: `Reconciliation(BusinessEntity)` stub -- separate from processing package, represents Asana reconciliation records under ReconciliationHolder.

## Boundaries and Failure Modes

- **executor live path never exercised**: `dry_run=False` is tested but never called in production
- **Excel report depends on**: `DataServiceClient.get_reconciliation_async()`, `openpyxl`, `ResolutionContext` for 2-hop traversal
- **Shadow runner depends on**: pre-warmed DataFrame cache, `lifecycle_stages.yaml` DERIVATION_TABLE
- **PII contract**: `office_phone` always masked via `mask_phone_number()` before logging

### Test Coverage

processor.py and executor.py covered (executor newly created per git status). engine.py and report.py have no direct tests (gap in test-coverage.md). formatter.py untested.

## Knowledge Gaps

1. **SCAR-REG-001**: Section GIDs are placeholders -- blocks live execution.
2. **`pipeline_summary` construction origin** (pipeline_stage_aggregator) not traced.
3. **formatter.py test gap**: No dedicated test file visible.
4. **report.py and engine.py** no direct test coverage.
