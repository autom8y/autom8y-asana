# SPIKE: Workflow Automation Progress Evaluation

**Date**: 2026-02-11
**Timebox**: Exploration spike (research only)
**Question**: What is the current state of workflow automation in autom8_asana, specifically the CSV attachment pipeline for ContactHolder entities, and how cleanly is it integrated with autom8_data?

---

## Executive Summary

**Verdict: PRODUCTION READY. All core workflow automation is complete, tested, and documented.**

The ConversationAuditWorkflow — the first batch workflow service that fetches CSV from the data service for active ContactHolder entities and attaches it to Asana tasks — is **fully implemented and operational**. The cross-service integration with autom8_data follows clean distributed systems patterns with no significant anti-patterns detected.

---

## 1. Architecture Overview

### Two-Dispatch Automation Model

```
PollingScheduler / EventBridge
  |
  +-- action.type == "add_tag" / "add_comment" / etc
  |     -> ActionExecutor -> Per-task dispatch (existing)
  |
  +-- action.type == "workflow"
        -> WorkflowRegistry -> Self-enumerated batch (NEW)
              -> ConversationAuditWorkflow (first implementation)
```

### ConversationAuditWorkflow Data Flow

```
1. Lambda handler (EventBridge trigger)
   |
2. Enumerate ContactHolders from PRIMARY_PROJECT_GID (1201500116978260)
   |
3. For each ContactHolder (concurrency=5):
   |-- Resolve parent Business -> office_phone (2 API calls)
   |-- Fetch 30-day CSV from autom8_data (GET /api/v1/messages/export)
   |-- Upload new CSV attachment (multipart, upload-first pattern)
   |-- Delete old "conversations_*.csv" attachments (glob match)
   |
4. Return WorkflowResult with per-item tracking
```

---

## 2. Component Inventory

### Automation Core (COMPLETE)

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| AutomationEngine | `automation/engine.py` | - | PROD |
| AutomationRule Protocol | `automation/base.py` | - | PROD |
| PipelineConversionRule | `automation/pipeline.py` | 1,083 | PROD |
| FieldSeeder | `automation/seeding.py` | - | PROD |
| TemplateDiscovery | `automation/templates.py` | - | PROD |
| SubtaskWaiter | `automation/waiter.py` | - | PROD |
| ValidationResult | `automation/validation.py` | - | PROD |

### Batch Workflow Framework (COMPLETE)

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| WorkflowAction ABC | `automation/workflows/base.py` | - | PROD |
| WorkflowResult / WorkflowItemError | `automation/workflows/base.py` | - | PROD |
| WorkflowRegistry | `automation/workflows/registry.py` | - | PROD |
| ConversationAuditWorkflow | `automation/workflows/conversation_audit.py` | 444 | PROD |

### Cross-Service Integration (COMPLETE)

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| DataServiceClient | `clients/data/client.py` | 1,596 | PROD |
| get_export_csv_async() | `clients/data/client.py:1434-1583` | 150 | PROD |
| ExportResult model | `clients/data/models.py` | - | PROD |
| Response parsing | `clients/data/_response.py` | 270 | PROD |
| Stale cache fallback | `clients/data/_cache.py` | 195 | PROD |
| Metrics | `clients/data/_metrics.py` | 54 | PROD |
| PhoneVerticalPair | `models/contracts/phone_vertical.py` | 160 | PROD |
| Contract tests | `tests/unit/clients/data/test_contract_alignment.py` | - | PASSING |

### Attachment Lifecycle (COMPLETE)

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Attachment model | `models/attachment.py` | 58 | PROD |
| AttachmentsClient | `clients/attachments.py` | 485 | PROD |
| Multipart transport | `transport/asana_http.py` (post_multipart) | - | PROD |

### Entity Models (COMPLETE)

| Entity | File | Custom Fields | Status |
|--------|------|---------------|--------|
| ContactHolder | `models/business/contact.py:206-237` | - | PROD |
| Contact | `models/business/contact.py:33-204` | 19 | PROD |
| Business (root) | `models/business/business.py` | 19 | PROD |

### Lambda Handler (COMPLETE)

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| conversation_audit_handler | `lambda_handlers/conversation_audit.py` | 130 | PROD |
| Registered in __init__.py | `lambda_handlers/__init__.py` | - | PROD |

---

## 3. Cross-Service Integration Assessment

### Integration Pattern: READ-ONLY Unidirectional

```
autom8_asana (consumer) --GET /api/v1/messages/export--> autom8_data (provider)
```

**autom8_data requires ZERO changes.** The integration is read-only — autom8_asana fetches CSV exports via HTTP, autom8_data serves them.

### Contract Surface

| Aspect | autom8_asana (Consumer) | autom8_data (Provider) |
|--------|------------------------|----------------------|
| Endpoint | `GET /api/v1/messages/export` | `messages.py:595-732` |
| Auth | JWT via S2S API key (`AUTOM8_DATA_API_KEY`) | JWKS validation |
| Query params | `office_phone` (E.164), `start_date`, `end_date` | Same params + `direction`, `status`, `intent` |
| Response body | CSV bytes (RFC 4180 + UTF-8 BOM) | `_build_export_csv()` with BOM |
| Custom headers | Parses `X-Export-Row-Count`, `X-Export-Truncated`, `Content-Disposition` | Sets all three |
| Row limit | Handles truncation flag | EXPORT_MAX_ROWS = 10,000 |
| PII | `mask_phone_number()` in logs | `_mask_phone()` in logs |

### autom8_data also provides a typed client FOR autom8_asana

```python
# In autom8_data/src/autom8_data/clients/asana_client.py
class AsanaServiceClient(BaseClient):
    DEFAULT_BASE_URL = "https://asana.api.autom8y.io"
    ENV_BASE_URL = "ASANA_SERVICE_URL"
    # Methods: health(), get_project_dataframe(), query_entities()
    # Optional resilience wrapper via ResilienceConfig
```

This is the **reverse direction** — autom8_data consuming autom8_asana's API for dataframes and queries. Clean separation of concerns.

### Anti-Pattern Audit

| Anti-Pattern | Status | Notes |
|--------------|--------|-------|
| Hardcoded URLs | CLEAN | Env vars: `AUTOM8_DATA_URL`, `ASANA_SERVICE_URL` |
| Missing error handling | CLEAN | Circuit breaker + retry + stale cache fallback |
| Tight coupling | CLEAN | Unidirectional reads, ExportResult as boundary type |
| Missing retries | CLEAN | ExponentialBackoffRetry with timeout/http callbacks |
| Missing circuit breaker | CLEAN | Records failures on 5xx, checks before request |
| Shared database | CLEAN | No shared DB — HTTP API boundary only |
| Distributed transactions | CLEAN | Upload-first pattern (no 2PC needed) |
| Chatty API | CLEAN | Single GET per holder (CSV in one call) |
| Missing PII protection | CLEAN | Phone masking in both repos |
| Missing feature flags | CLEAN | `AUTOM8_AUDIT_ENABLED` env var |

---

## 4. Entity Hierarchy (ContactHolder Context)

```
Business (root, GID: 1200653012566782)
  +-- ContactHolder (GID: 1201500116978260)
  |     +-- Contact (is_owner=True/False)
  |     +-- Contact
  |     +-- Contact
  +-- UnitHolder
  |     +-- Unit (composite)
  |           +-- OfferHolder -> Offer
  |           +-- ProcessHolder -> Process
  +-- LocationHolder -> Location + Hours
  +-- DNAHolder, ReconciliationHolder, AssetEditHolder, VideographyHolder
```

ContactHolder uses the HolderFactory pattern with declarative configuration:
- `PRIMARY_PROJECT_GID = "1201500116978260"` (enumeration source)
- `child_type = "Contact"`, `children_attr = "_contacts"`
- `owner` property returns first Contact with `is_owner=True`
- Parent Business provides `office_phone` for CSV export

---

## 5. Test Coverage

### Automation Test Matrix

| Test File | Scope | Count | Status |
|-----------|-------|-------|--------|
| `unit/automation/workflows/test_base.py` | WorkflowAction, Registry, Result | ~15 | PASSING |
| `unit/automation/workflows/test_conversation_audit.py` | Full workflow (21KB) | ~30 | PASSING |
| `unit/automation/test_pipeline.py` | Pipeline conversion rule | ~40 | PASSING |
| `unit/automation/test_pipeline_hierarchy.py` | Hierarchy placement | ~10 | PASSING |
| `unit/automation/test_seeding.py` | Field seeding | ~15 | PASSING |
| `unit/automation/test_templates.py` | Template discovery | ~10 | PASSING |
| `unit/automation/test_engine.py` | Automation engine | ~20 | PASSING |
| `unit/automation/test_validation.py` | Precondition validation | ~10 | PASSING |
| `unit/automation/test_waiter.py` | Subtask waiter | ~10 | PASSING |
| `unit/clients/data/test_contract_alignment.py` | Cross-service contracts | 24 | PASSING |
| `integration/automation/workflows/test_conversation_audit_e2e.py` | Full lifecycle E2E | ~5 | PASSING |

**ConversationAuditWorkflow test scenarios covered:**
- Happy path (2 holders succeed, 1 skip, 1 fail)
- Skip: no office_phone (REQ-F03)
- Skip: zero-row export (REQ-F06)
- Error isolation: one failure doesn't abort batch (REQ-F07)
- Upload-first ordering: new CSV uploaded before old deleted (REQ-F04)
- Feature flag disabled: validation returns skip
- Concurrency control: semaphore limits parallel processing
- Truncation handling: X-Export-Truncated header detection

### Overall Project Test Count

- **8,588 tests** (as of 2026-02-07)
- **200+ automation-specific** tests
- Pre-existing failures: 3 (unrelated to workflow automation)

---

## 6. Documentation Inventory

| Document | Location | Status |
|----------|----------|--------|
| PRD | `docs/requirements/PRD-conversation-audit-workflow.md` | FINAL |
| TDD | `docs/design/TDD-conversation-audit-workflow.md` | FINAL |
| QA Plan | `docs/qa/QA-conversation-audit-workflow.md` | FINAL |
| ADR-0017 | `docs/decisions/ADR-0017-automation-architecture.md` | ACCEPTED |
| ADR-0015 | `docs/decisions/ADR-0015-process-pipeline-architecture.md` | ACCEPTED |
| Setup Guide | `docs/guides/pipeline-automation-setup.md` | AVAILABLE |
| Runbook | `docs/runbooks/RUNBOOK-pipeline-automation.md` | AVAILABLE |
| Workflows Guide | `docs/guides/workflows.md` | AVAILABLE |

---

## 7. Key Design Decisions

### Upload-First Attachment Strategy (REQ-F04)
Upload new CSV before deleting old ones. Ensures no gap where a holder has zero attachments. Deletion failures are non-fatal.

### Error Isolation with Per-Item Tracking (REQ-F07)
Each ContactHolder processed independently. One failure doesn't abort the batch. `WorkflowItemError` captures per-item failures with recoverability flags.

### Feature Flag Deactivation via Validation (REQ-F02)
`AUTOM8_AUDIT_ENABLED=false` causes `validate_async()` to return errors. Lambda returns 200 with `status: "skipped"` (not 500 error). Clean operational shutdown.

### PhoneVerticalPair as Cross-Service Identifier
Version-prefixed canonical key (`pv1:{phone}:{vertical}`) for cache routing. E.164 validation. Backward-compatible tuple unpacking. Owned by autom8_asana (not shared package per ADR-INS-001).

---

## 8. Findings: What's NOT Built (and Shouldn't Be)

| Item | Why It's Not Needed |
|------|-------------------|
| Web UI for workflow config | Configured via YAML + env vars (ops-friendly) |
| Workflow scheduler (in-process) | EventBridge handles scheduling externally |
| Monitoring dashboard | Structured logging + CloudWatch (existing infra) |
| Multi-tenant isolation | Single-tenant SaaS model |
| Workflow versioning | Workflows are code artifacts (git-versioned) |
| Generic CSV-to-attachment utility | ConversationAudit is the concrete use case; premature abstraction avoided |

---

## 9. Recommendations

### No Action Required

The workflow automation system is **production-grade and complete** for the ConversationAuditWorkflow use case. The cross-service integration with autom8_data is clean, well-abstracted, and follows distributed systems best practices:

- Unidirectional read-only dependency
- HTTP API boundary (no shared DB)
- Circuit breaker + retry + stale cache fallback
- Upload-first atomicity pattern
- Per-item error isolation
- Feature flag for operational control
- PII protection in both repos
- Comprehensive test coverage (unit + integration + E2E)
- Full documentation (PRD, TDD, ADR, QA plan, guides, runbooks)

### Future Extensibility (When Needed)

If additional batch workflows are needed beyond ConversationAudit:

1. **Implement new WorkflowAction subclass** — the framework is already generalized
2. **Register in WorkflowRegistry** — single-line registration
3. **Add Lambda handler** — copy pattern from `conversation_audit.py`
4. **Add EventBridge rule** — schedule trigger

The `WorkflowAction` ABC + `WorkflowRegistry` pattern was intentionally designed for this extension without modifying existing code.

---

## 10. Scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Feature Completeness** | 10/10 | All PRD requirements implemented |
| **Test Coverage** | 9/10 | 200+ tests, E2E included; minor: no load/stress tests |
| **Documentation** | 10/10 | PRD, TDD, ADR, QA plan, guides, runbooks |
| **Integration Cleanliness** | 9/10 | Clean unidirectional pattern; minor: PhoneVerticalPair key format mismatch with autom8_data's tuple |
| **Error Handling** | 10/10 | Circuit breaker, retry, stale cache, per-item isolation |
| **Operational Readiness** | 9/10 | Feature flag, structured logging, Lambda handler; minor: no runbook for key rotation |
| **Anti-Pattern Freedom** | 10/10 | No shared state, no tight coupling, no chatty APIs |

**Overall: 67/70 (96%) — Production Ready**

---

## PART 2: Infrastructure, Distribution & Extensibility

---

## 11. Deployment Topology (1000ft View)

### Hybrid Architecture: ECS Fargate + Lambda

```
                    ┌──────────────────────────────────────────────┐
                    │           Public Internet (Cloudflare)        │
                    │  *.api.autom8y.io → CNAME → ALB DNS          │
                    └──────────────┬───────────────────────────────┘
                                   │ HTTPS :443
                                   ▼
                    ┌──────────────────────────────┐
                    │   ALB (autom8-prod-alb)      │
                    │   TLS termination            │
                    │   Host-header routing         │
                    └──┬──────────┬──────────┬─────┘
                       │          │          │
             Priority 120   Priority 110  Priority 10
                       │          │          │
                       ▼          ▼          ▼
              ┌────────────┐ ┌─────────┐ ┌──────────┐
              │ asana ECS  │ │data ECS │ │ auth ECS │
              │ 256CPU/1GB │ │1CPU/4GB │ │          │
              │ :8000      │ │:8000 x2 │ │ :8000    │
              └──────┬─────┘ └────┬────┘ └──────────┘
                     │            │
        ┌────────────┘            ├─→ Redis (ElastiCache)
        │                         ├─→ EFS (Parquet storage)
        ▼                         └─→ MySQL (RDS, Zero-ETL)
  ┌──────────────┐
  │ S3: autom8-s3│
  │ /asana-cache/│
  └──────────────┘

        EventBridge (Scheduled)
            │
     ┌──────┴───────────────────┐
     │                          │
     ▼                          ▼
┌──────────────────┐  ┌──────────────────────┐
│ cache-warmer     │  │ conversation-audit    │
│ Lambda (1GB)     │  │ Lambda (512MB)        │
│ Daily 2AM UTC    │  │ Weekly Sun 7AM UTC    │
│ Timeout: 15min   │  │ Timeout: 5min         │
│ Concurrency: -   │  │ Concurrency: 1        │
└──────────────────┘  └──────────────────────┘
     │                          │
     ▼                          ├─→ Asana API (ASANA_PAT)
  S3 cache read/write           └─→ data.api.autom8y.io
                                    (GET /api/v1/messages/export)
```

### Key Infrastructure Facts

| Aspect | Detail |
|--------|--------|
| **VPC** | `autom8-vpc` (us-east-1), private subnets only for ECS |
| **DNS** | `*.api.autom8y.io` via Cloudflare (DNS-only, no proxy) |
| **TLS** | ACM wildcard cert `*.api.autom8y.io` on ALB |
| **ECR** | `autom8y/asana-service` (shared image for ECS + Lambda) |
| **Secrets** | AWS Secrets Manager: `autom8y/asana/{asana-pat, asana-workspace-gid, autom8-data-api-key}` |
| **Logging** | CloudWatch: `/ecs/autom8y-asana-service`, `/aws/lambda/autom8-conversation-audit` |
| **Metrics** | ADOT sidecar → Amazon Managed Prometheus |
| **Alarms** | SNS → `autom8-platform-alerts` topic |

### Terraform Structure (`autom8y`)

```
terraform/services/asana/main.tf
  ├── module "service" (service-stateless stack)
  │     └── ECS Fargate + ALB target group + CloudWatch
  ├── module "cache_warmer" (autom8-cache-lambda)
  │     └── Lambda + EventBridge daily schedule + DLQ
  └── module "conversation_audit" (scheduled-lambda)
        └── Lambda + EventBridge weekly schedule + DLQ
```

---

## 12. Full Pipeline: ConversationAuditWorkflow End-to-End

```
EventBridge Rule: cron(0 7 ? * SUN *)    ← Every Sunday 7AM UTC
  │
  ▼
Lambda: conversation-audit (512MB, 5min timeout, concurrency=1)
  │
  ├─ Read secrets: ASANA_PAT, ASANA_WORKSPACE_GID, AUTOM8_DATA_API_KEY
  │
  ├─ Initialize:
  │   ├─ AsanaClient (Asana REST API via PAT)
  │   └─ DataServiceClient (https://data.api.autom8y.io via API key)
  │
  ├─ Validate:
  │   ├─ Check AUTOM8_AUDIT_ENABLED env var (feature flag)
  │   └─ Check circuit breaker state
  │
  ├─ Execute:
  │   ├─ Enumerate ContactHolders from project GID 1201500116978260
  │   │   └─ Asana API: GET /api/v1/tasks?project={gid}
  │   │
  │   └─ For each holder (semaphore=5):
  │       │
  │       ├─ Resolve parent Business → extract office_phone custom field
  │       │   └─ Asana API: GET /api/v1/tasks/{holder_gid} → parent.gid
  │       │   └─ Asana API: GET /api/v1/tasks/{parent_gid} → custom_fields
  │       │
  │       ├─ Skip if no office_phone (REQ-F03)
  │       │
  │       ├─ Fetch 30-day CSV
  │       │   └─ data.api.autom8y.io: GET /api/v1/messages/export?office_phone=+1...
  │       │   └─ Response: CSV bytes + X-Export-Row-Count + X-Export-Truncated
  │       │
  │       ├─ Skip if zero rows (REQ-F06)
  │       │
  │       ├─ Upload new CSV (upload-first, REQ-F04)
  │       │   └─ Asana API: POST /api/v1/attachments (multipart)
  │       │
  │       └─ Delete old conversations_*.csv attachments
  │           └─ Asana API: GET /api/v1/tasks/{gid}/attachments
  │           └─ Asana API: DELETE /api/v1/attachments/{old_gid} (for each match)
  │
  └─ Return WorkflowResult:
      {
        "status": "completed",
        "workflow_id": "conversation-audit",
        "total": N, "succeeded": X, "failed": Y, "skipped": Z,
        "duration_seconds": T, "failure_rate": Y/N
      }
```

### Cross-Service Request Path (asana → data)

```
Lambda (private subnet)
  → DNS: data.api.autom8y.io
  → Cloudflare CNAME → ALB DNS
  → ALB HTTPS :443 (TLS termination)
  → Host header match: data.api.autom8y.io → Priority 110
  → Target group → data-service ECS task :8000
  → FastAPI: GET /api/v1/messages/export
  → DuckDB query → CSV generation (UTF-8 BOM, 10K row limit)
  → Response: CSV bytes + custom headers
  → Back through ALB → Lambda
```

---

## 13. Trigger Paths (3 Active, 0 via HTTP API)

| Path | Entry Point | Use Case |
|------|-------------|----------|
| **EventBridge → Lambda** | `lambda_handlers/conversation_audit.handler` | Production (weekly schedule) |
| **PollingScheduler** | YAML rule with `action.type: "workflow"` | Secondary production path |
| **Direct Python script** | Instantiate workflow + call `execute_async()` | Dev/testing one-offs |

**There is NO HTTP API endpoint** to trigger the workflow on-demand. The workflow is exclusively scheduled or script-invoked.

---

## 14. One-Off Smoke Test: How To

### Can you run a one-off for a specific ContactHolder?

**YES, but only via Python script** (no API endpoint exists). The workflow exposes `_process_holder()` for single-holder testing:

```python
import asyncio
import os
from autom8_asana import AsanaClient
from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.automation.workflows.conversation_audit import ConversationAuditWorkflow

async def smoke_test_single_holder(holder_gid: str, holder_name: str):
    """One-off smoke test for a specific ContactHolder."""
    os.environ.setdefault("AUTOM8_DATA_URL", "https://data.api.autom8y.io")
    # Requires: ASANA_PAT, AUTOM8_DATA_API_KEY in env

    asana_client = AsanaClient()
    async with DataServiceClient() as data_client:
        workflow = ConversationAuditWorkflow(
            asana_client=asana_client,
            data_client=data_client,
            attachments_client=asana_client.attachments,
        )

        # Single holder processing (bypasses enumeration)
        outcome = await workflow._process_holder(
            holder_gid=holder_gid,
            holder_name=holder_name,
            attachment_pattern="conversations_*.csv",
        )
        print(f"Status: {outcome.status}, Error: {outcome.error}")

# Usage:
# asyncio.run(smoke_test_single_holder("1234567890123456", "John Doe"))
```

### Full batch (all holders) via script:

```python
async def smoke_test_full_batch():
    asana_client = AsanaClient()
    async with DataServiceClient() as data_client:
        workflow = ConversationAuditWorkflow(
            asana_client=asana_client,
            data_client=data_client,
            attachments_client=asana_client.attachments,
        )
        errors = await workflow.validate_async()
        if errors:
            print(f"Validation failed: {errors}")
            return
        result = await workflow.execute_async({
            "max_concurrency": 1,  # Conservative for testing
            "date_range_days": 30,
        })
        print(f"Total: {result.total}, OK: {result.succeeded}, Failed: {result.failed}")
```

---

## 15. Extensibility Analysis

### What's Generic (Reusable for Workflow #2+)

| Component | Generic? | Notes |
|-----------|----------|-------|
| WorkflowAction ABC | YES | Clean contract: `workflow_id`, `validate_async()`, `execute_async()` |
| WorkflowRegistry | YES | Dict-based lookup by `workflow_id` string |
| PollingScheduler dispatch | YES | Zero knowledge of specific workflow implementations |
| WorkflowResult reporting | YES | Standard total/succeeded/failed/skipped/duration |
| YAML config schema | YES | `action.type: "workflow"` + arbitrary `params` dict |
| Lambda handler pattern | PARTIAL | Hardcoded per-workflow; copy-paste required |
| Terraform Lambda module | YES | `scheduled-lambda` module is generic |

### Adding Workflow #2: Concrete Steps

1. **Implement** `NewWorkflow(WorkflowAction)` — ~200 lines
2. **Create** `lambda_handlers/new_workflow.py` — ~40 lines (copy pattern)
3. **Add** YAML rule — ~15 lines
4. **Update** `lambda_handlers/__init__.py` exports — ~2 lines
5. **Add** Terraform `scheduled-lambda` module block — ~30 lines
6. **Add** EventBridge cron rule — included in Terraform module

**Estimated effort**: 2-3 hours for a similar enumerate-process-update pattern.

### Extensibility Gaps

| Gap | Impact | Severity |
|-----|--------|----------|
| **No generic Lambda dispatcher** | Each workflow needs its own Lambda handler (copy-paste) | Low |
| **Monthly scheduling not supported** | Config schema only validates `daily`/`weekly` frequencies | Medium |
| **CLI cannot run workflows** | PollingScheduler created without `workflow_registry` in CLI | Medium |
| **No DI container/factory** | Manual client construction in each Lambda handler | Low |
| **No workflow dependency ordering** | Cross-workflow coordination requires external orchestration | Low |
| **No HTTP trigger endpoint** | Cannot invoke workflows on-demand via API call | Medium |

---

## 16. CI/CD Pipeline

### Build & Deploy Flow

```
1. Push to feature branch
   └─ GitHub Actions: CI tests

2. PR merged to main
   └─ service-build.yml:
      ├─ Build Docker image (autom8_asana)
      ├─ Push to ECR: autom8y/asana-service:{SHA}
      └─ Output: image_tag, image_uri

   └─ service-deploy.yml:
      ├─ Fetch current ECS task definition
      ├─ Update container image to new tag
      ├─ Register new task definition revision
      ├─ Update ECS service → rolling deployment
      ├─ Wait for stabilization
      └─ Smoke test: curl https://asana.api.autom8y.io/health

3. Infrastructure changes
   └─ service-terraform.yml:
      ├─ Detect changed services
      ├─ terraform plan → PR comment
      └─ terraform apply (on main merge)
```

### Same Image, Multiple Runtimes

The `autom8y/asana-service` Docker image serves both ECS and Lambda:
- **ECS mode**: `entrypoint.sh` starts uvicorn (API server on :8000)
- **Lambda mode**: AWS Lambda Runtime Interface Client (`awslambdaric`) routes to handler function

---

## 17. Updated Scorecard (Including Infrastructure)

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Feature Completeness** | 10/10 | All PRD requirements implemented |
| **Test Coverage** | 9/10 | 200+ tests, E2E included; no load/stress tests |
| **Documentation** | 10/10 | PRD, TDD, ADR, QA plan, guides, runbooks |
| **Integration Cleanliness** | 9/10 | Clean unidirectional pattern; minor PVP key mismatch |
| **Error Handling** | 10/10 | Circuit breaker, retry, stale cache, per-item isolation |
| **Operational Readiness** | 9/10 | Feature flag, structured logging, Lambda handler |
| **Anti-Pattern Freedom** | 10/10 | No shared state, no tight coupling, no chatty APIs |
| **Infrastructure** | 9/10 | Full Terraform, CI/CD, secrets management; no HTTP trigger |
| **Extensibility** | 8/10 | Generic ABC+registry; gaps in monthly schedule, CLI, DI |
| **Deployment** | 9/10 | Automated CI/CD, shared image, health checks, alarms |

**Overall: 93/100 — Production Ready with Strong Extensibility Foundation**
