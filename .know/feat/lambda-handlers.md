---
domain: feat/lambda-handlers
generated_at: "2026-04-01T17:20:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/lambda_handlers/**/*.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# AWS Lambda Function Handlers

## Purpose and Design Rationale

Fleet of 13 Lambda entry points for scheduled and event-driven workloads that cannot run inside the ECS API server. Complements the REST API by handling long-running, batch, and infrastructure-maintenance operations.

**Dual-mode container**: Same Docker image for ECS (uvicorn) and Lambda (awslambdaric). Detection: `AWS_LAMBDA_RUNTIME_API` env var.

## Conceptual Model

### Handler Taxonomy (13 files, 4 roles)

| Role | Files |
|------|-------|
| Infrastructure maintenance | cache_warmer, cache_invalidate |
| Workflow execution | insights_export, conversation_audit, payment_reconciliation |
| Post-warm side-effects | push_orchestrator, story_warmer, pipeline_stage_aggregator, reconciliation_runner |
| Handler infrastructure | workflow_handler, checkpoint, timeout, cloudwatch |

### Two Patterns

**Pattern A (Manual)**: `cache_warmer`, `cache_invalidate` -- hand-written, `asyncio.run()`, `@instrument_lambda`.

**Pattern B (Factory)**: Workflow handlers call `create_workflow_handler(WorkflowHandlerConfig(...))` which returns a decorated handler. Factory handles: client init, EntityScope, validation, enumeration, execution, metric emission, DMS, fleet health, domain events.

### Cache Warmer Orchestration Pipeline

1. DataFrame warming (per entity, cascade order, with checkpoint-resume and timeout detection)
2. GID mapping push
3. Account status push
4. Story cache warming
5. Vertical backfill (feature-flagged)
6. Pipeline aggregation
7. Reconciliation shadow

Steps 2-7 are **non-blocking**: failures never affect `WarmResponse.success`.

### Checkpoint-Resume

S3-backed checkpoint at `s3://{bucket}/cache-warmer/checkpoints/latest.json`. Save after each entity. On timeout: checkpoint, self-invoke continuation via `Lambda.invoke(InvocationType="Event")`, return partial result. Staleness window: 1 hour.

## Implementation Map

5 public handlers exported from `__init__.py`: cache_warmer, cache_invalidate, insights_export, conversation_audit, payment_reconciliation. 8 internal helpers: cloudwatch (shared metric emit), checkpoint (S3 persistence), timeout (early exit + self-invoke), workflow_handler (factory), push_orchestrator (GID + status push), story_warmer (incremental story cache), pipeline_stage_aggregator (process DataFrame summary), reconciliation_runner (shadow reconciliation).

### Architecture Doc Discrepancy

`.know/architecture.md` lists only 5 handlers (stale). Actual count: 13 files. 8 additional infrastructure modules undocumented.

### Test Coverage

All 13 files now have test coverage. `cloudwatch.py`, `push_orchestrator.py`, `timeout.py` tests added in commit `065471f` -- `.know/test-coverage.md` still lists them as gaps (stale).

## Boundaries and Failure Modes

### Isolation Contract

Every module uses broad-catch + log + degrade for non-critical operations. Annotated with `# BROAD-CATCH: {type}`. Post-warm side-effects never affect `WarmResponse.success`.

### Known Risks

- **`cache_invalidate` with `clear_tasks=True`**: Destroys story incremental cursors (ADR-0020). Recovery: 5-30 min via cache_warmer.
- **Checkpoint single-writer assumption**: Requires `reserved_concurrent_executions=1`.
- **Self-invocation requires `invoked_function_arn`**: Silently no-ops in local testing.
- **Bootstrap discrepancy**: Workflow handlers bootstrap eagerly at import; cache_warmer defers lazily.

## Knowledge Gaps

1. `cascade_warm_order()` exact entity list not read.
2. `EntityScope.from_event()` schema not read.
3. GID push data contract (`gid_lookup.py`, `gid_push.py`) not read.
4. Lambda timeout/concurrency config not in source (infrastructure as code).
5. `autom8y_telemetry.aws.instrument_lambda` decorator internals not read.
