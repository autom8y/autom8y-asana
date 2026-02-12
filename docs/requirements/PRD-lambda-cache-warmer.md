---
artifact_id: PRD-lambda-cache-warmer
title: "Lambda-Based DataFrame Cache Warmer"
created_at: "2026-01-06T12:00:00Z"
author: requirements-analyst
status: draft
complexity: SERVICE
success_criteria:
  - id: SC-001
    description: "Lambda completes all entity warming within 15 minutes without timeout"
    testable: true
    priority: must-have
  - id: SC-002
    description: "S3 artifacts updated with fresh watermarks after each warming run"
    testable: true
    priority: must-have
  - id: SC-003
    description: "CloudWatch alarms fire on warming failures within 5 minutes"
    testable: true
    priority: must-have
  - id: SC-004
    description: "Manual trigger via just cache-warm-lambda completes successfully"
    testable: true
    priority: must-have
  - id: SC-005
    description: "EventBridge triggers daily warming at 2 AM UTC"
    testable: true
    priority: must-have
  - id: SC-006
    description: "Chunked processing persists progress after each entity type"
    testable: true
    priority: must-have
  - id: SC-007
    description: "Failed invocations route to DLQ for retry and alerting"
    testable: true
    priority: should-have
  - id: SC-008
    description: "Cold start latency under 5 seconds for entity discovery"
    testable: true
    priority: should-have
stakeholders:
  - platform-operator
  - service-developer
  - sre
impact: high
impact_categories: [cross_service, data_model]
schema_version: "1.0"
---

# PRD: Lambda-Based DataFrame Cache Warmer

**PRD ID**: PRD-lambda-cache-warmer
**Version**: 1.0
**Date**: 2026-01-06
**Estimated Effort**: 2-3 weeks

---

## Overview

This PRD defines requirements for implementing a production-ready Lambda-based cache warming system for the autom8_asana DataFrame cache. The system will proactively warm all entity type caches on a scheduled basis, eliminating cold-start latency for API consumers and ensuring consistent performance regardless of service restarts.

---

## Problem Statement

### Current State

The autom8_asana DataFrame cache relies on two warming mechanisms:

1. **Lazy Loading**: Cache is populated on first API request (cold path)
2. **ECS Task Restart**: Service restart triggers cache rebuild

Both approaches have significant drawbacks:

| Mechanism | Problem |
|-----------|---------|
| Lazy Loading | First request experiences 30-60 second latency while DataFrames build |
| ECS Restart | Requires service disruption; `cache-rebuild` command causes downtime |
| ECS Warm Task | Consumes Fargate resources at full container cost (~$0.05/invocation) |

### User Pain Points

1. **Unpredictable First-Request Latency**: SDK consumers experience 30-60 second latency on first request after cache expiration. This breaks SLA commitments and causes timeout errors in downstream systems.

2. **Expensive Cache Warming**: Current ECS-based `cache-warm` command requires spinning up a full Fargate task, costing approximately $0.05 per invocation and taking 2-3 minutes to start.

3. **No Scheduled Refresh**: Cache TTL of 12 hours means caches expire unpredictably throughout the day. No mechanism exists to proactively refresh before expiration.

4. **Cold Start After Deployment**: New deployments start with cold cache, causing degraded performance for initial users.

### Technical Root Cause

The existing Lambda handler at `src/autom8_asana/lambda_handlers/cache_warmer.py` provides the core warming logic but lacks:

- **Timeout Resilience**: No chunked processing to survive Lambda's 15-minute limit with 50K+ tasks
- **Infrastructure**: No Terraform module for deployment
- **Scheduling**: No EventBridge integration for automated runs
- **Observability**: Limited CloudWatch metrics and alerting

---

## User Personas

### Platform Operator

**Role**: Engineer responsible for autom8y platform infrastructure and Lambda deployments.

**Needs**:
- Terraform module for consistent Lambda deployment across environments
- CloudWatch dashboards for monitoring cache health
- Just commands for manual invocation and debugging

**Pain Points**:
- Managing ECS tasks for cache operations is operationally complex
- No visibility into cache freshness across entity types
- Manual intervention required after deployments

### Service Developer

**Role**: Developer building features that depend on DataFrame cache.

**Needs**:
- Predictable cache availability for development and testing
- Ability to trigger cache warm manually during development
- Clear documentation on cache behavior and timing

**Pain Points**:
- First request latency makes local development frustrating
- Unclear when cache was last refreshed
- No way to force refresh for specific entity types

### SRE (Site Reliability Engineer)

**Role**: Engineer responsible for production reliability and incident response.

**Needs**:
- Alerts on cache warming failures
- Runbooks for cache-related incidents
- Visibility into warming duration and success rates

**Pain Points**:
- No alerting when cache warming fails
- Difficult to diagnose whether latency issues are cache-related
- No historical data on cache warming performance

---

## User Stories

### US-001: Scheduled Cache Warming

**As a** Platform Operator
**I want** the DataFrame cache to be warmed automatically on a daily schedule
**So that** API consumers never experience cold-cache latency

**Acceptance Criteria**:
- [ ] EventBridge rule triggers Lambda at 2 AM UTC daily
- [ ] All four entity types (unit, business, offer, contact) are warmed
- [ ] Warming completes before business hours (before 6 AM UTC)
- [ ] Failed runs retry automatically with backoff

### US-002: Timeout-Resilient Processing

**As a** Platform Operator
**I want** cache warming to survive Lambda's 15-minute timeout
**So that** large entity sets (50K+ tasks) complete successfully

**Acceptance Criteria**:
- [ ] Each entity type is processed and persisted independently
- [ ] Progress is checkpointed to S3 after each entity type
- [ ] Partial failures do not prevent subsequent entity types from warming
- [ ] Retry resumes from last successful checkpoint (not from scratch)

### US-003: Manual Cache Warming

**As a** Service Developer
**I want** to trigger cache warming manually via CLI
**So that** I can refresh the cache during development or after deployments

**Acceptance Criteria**:
- [ ] `just cache-warm-lambda` invokes Lambda directly
- [ ] Optional entity type filter: `just cache-warm-lambda entity=unit`
- [ ] Command returns warming status and duration
- [ ] Supports both staging and production environments

### US-004: Infrastructure as Code

**As a** Platform Operator
**I want** a reusable Terraform module for Lambda cache infrastructure
**So that** I can deploy consistently across environments

**Acceptance Criteria**:
- [ ] Module at `terraform/modules/autom8-cache-lambda/`
- [ ] Configurable memory, timeout, schedule
- [ ] Includes IAM roles, S3 permissions, Secrets Manager access
- [ ] EventBridge rule with configurable cron expression
- [ ] DLQ for failed invocations

### US-005: Observability and Alerting

**As an** SRE
**I want** comprehensive metrics and alerts for cache warming
**So that** I can detect and respond to failures quickly

**Acceptance Criteria**:
- [ ] CloudWatch metrics: duration, success/failure count, rows warmed
- [ ] CloudWatch alarm on consecutive failures (threshold: 2)
- [ ] Structured logging with correlation IDs
- [ ] Dashboard showing warming history and trends

### US-006: Cost-Effective Operation

**As a** Platform Operator
**I want** cache warming to be cost-effective
**So that** scheduled runs do not significantly impact AWS costs

**Acceptance Criteria**:
- [ ] Lambda invocation cost < $0.01 per run (vs. $0.05 for ECS)
- [ ] Memory configured for optimal cost/performance (512MB-1GB)
- [ ] No unnecessary invocations (skip if cache is fresh)
- [ ] Monthly cost projection < $5 for daily runs

---

## Functional Requirements

### Must Have

#### FR-001: Chunked/Micro-Commit Processing Pattern

The system SHALL process entity types sequentially with checkpointing to handle Lambda's 15-minute timeout constraint.

**Behavior**:
1. Process entity types in priority order: `["unit", "business", "offer", "contact"]`
2. After each entity type completes:
   - Persist DataFrame to S3 with watermark
   - Record checkpoint in S3 metadata or DynamoDB
   - Log completion with duration and row count
3. If timeout approaches (remaining time < 2 minutes):
   - Complete current entity type
   - Exit gracefully with partial success
   - Record last completed entity for resume

**Rationale**: Lambda's 15-minute maximum timeout is insufficient for warming 50K+ tasks across four entity types with current sequential processing. Chunked processing ensures progress is preserved.

#### FR-002: EventBridge Scheduling

The system SHALL trigger cache warming automatically via EventBridge.

**Configuration**:
- Schedule: Daily at 2 AM UTC (`cron(0 2 * * ? *)`)
- Retry policy: 2 retries with exponential backoff
- DLQ routing after all retries exhausted

**Rationale**: 2 AM UTC ensures cache is fresh before business hours in US timezones (6 PM PT / 9 PM ET previous day) and European timezones (3 AM CET).

#### FR-003: Terraform Module for Lambda Infrastructure

The system SHALL provide a reusable Terraform module at `terraform/modules/autom8-cache-lambda/`.

**Module Interface**:
```hcl
module "cache_warmer" {
  source = "./modules/autom8-cache-lambda"

  # Required
  environment        = "production"
  s3_bucket          = "autom8-s3"

  # Optional with defaults
  memory_size        = 1024       # MB
  timeout            = 900        # seconds (15 min max)
  schedule_expression = "cron(0 2 * * ? *)"

  # Secrets
  asana_pat_secret_arn     = aws_secretsmanager_secret.asana_pat.arn
  workspace_gid_secret_arn = aws_secretsmanager_secret.workspace_gid.arn
}
```

**Resources Created**:
- Lambda function with container image from ECR
- IAM role with S3, Secrets Manager, CloudWatch permissions
- EventBridge rule and target
- CloudWatch log group with 30-day retention
- DLQ (SQS) for failed invocations

#### FR-004: Just Commands for Manual Invocation

The system SHALL provide just commands for manual cache operations.

**Commands**:

| Command | Description |
|---------|-------------|
| `just cache-warm-lambda` | Invoke Lambda to warm all entity types |
| `just cache-warm-lambda entity=unit` | Warm specific entity type |
| `just cache-warm-lambda-status` | Check most recent invocation status |
| `just cache-warm-lambda-logs` | Tail CloudWatch logs for Lambda |

#### FR-005: CloudWatch Metrics and Alerting

The system SHALL emit structured metrics to CloudWatch.

**Metrics** (namespace: `autom8/cache-warmer`):

| Metric | Unit | Description |
|--------|------|-------------|
| `WarmDuration` | Milliseconds | Total warming time per entity type |
| `WarmSuccess` | Count | Successful entity type warms |
| `WarmFailure` | Count | Failed entity type warms |
| `RowsWarmed` | Count | Total rows across all entity types |
| `ColdStartDuration` | Milliseconds | Time to initialize Lambda |
| `EntityDiscoveryDuration` | Milliseconds | Time to discover project GIDs |

**Alarms**:

| Alarm | Condition | Action |
|-------|-----------|--------|
| `CacheWarmConsecutiveFailures` | Failures >= 2 in 24h | SNS notification |
| `CacheWarmTimeout` | Duration > 14 minutes | SNS warning |
| `CacheWarmHighLatency` | Duration > 10 minutes | CloudWatch insight |

#### FR-006: Dead-Letter Queue for Failed Invocations

The system SHALL route failed invocations to an SQS DLQ.

**Configuration**:
- Queue name: `autom8-cache-warmer-dlq-{env}`
- Retention: 14 days
- CloudWatch alarm on messages > 0

**DLQ Message Content**:
```json
{
  "requestId": "abc-123",
  "functionName": "autom8-cache-warmer",
  "errorType": "TimeoutError",
  "errorMessage": "Task timed out after 900 seconds",
  "timestamp": "2026-01-06T02:15:00Z",
  "entityTypesCompleted": ["unit", "business"],
  "entityTypesFailed": ["offer"]
}
```

### Should Have

#### FR-007: Checkpoint Resume on Retry

The system SHOULD resume from the last successful checkpoint on retry.

**Behavior**:
1. On invocation, check for existing checkpoint in S3 metadata
2. If checkpoint exists and is recent (< 1 hour), skip completed entity types
3. Process remaining entity types
4. Clear checkpoint on full completion

**Rationale**: Prevents redundant work when retry occurs after partial success.

#### FR-008: Concurrent Entity Warming (Optional)

The system SHOULD support concurrent warming of independent entity types.

**Behavior**:
- Use `asyncio.gather()` with `return_exceptions=True`
- Limit concurrency to 2-3 parallel entity types
- Each entity type has independent circuit breaker

**Rationale**: Reduces total warming time from ~12 minutes (sequential) to ~4-5 minutes (concurrent).

#### FR-009: Skip Fresh Cache

The system SHOULD skip warming for entity types with fresh cache.

**Behavior**:
1. Check S3 watermark for each entity type before warming
2. If watermark is within TTL (12 hours), skip warming
3. Log skip reason with watermark age

**Rationale**: Prevents unnecessary API calls and S3 writes when cache is already fresh.

### Could Have

#### FR-010: Step Functions Orchestration

The system MAY use AWS Step Functions for complex orchestration.

**Rationale**: Step Functions provide native retry, branching, and state management. Recommended if concurrent warming or complex error handling is required.

**Deferred**: Initial implementation uses simple Lambda with checkpointing. Step Functions can be added in a future phase if complexity warrants.

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target | Rationale |
|--------|--------|-----------|
| Cold start latency | < 5 seconds | Entity discovery requires Asana API calls |
| Per-entity warm time | < 3 minutes | 50K tasks at 300 tasks/second |
| Total warm time (4 entities) | < 12 minutes | Sequential processing within 15-min limit |
| Total warm time (concurrent) | < 5 minutes | Future optimization with parallelism |

### NFR-002: Reliability

| Metric | Target | Rationale |
|--------|--------|-----------|
| Daily success rate | > 99% | 363/365 successful runs per year |
| Retry success rate | > 95% | Most failures recoverable via retry |
| MTTR (mean time to recovery) | < 1 hour | DLQ alerting enables fast response |

### NFR-003: Cost

| Item | Estimate | Calculation |
|------|----------|-------------|
| Lambda invocation | $0.006/run | 15 min * 1GB = 900,000 GB-ms |
| S3 writes | $0.0001/run | 4 PUT requests per run |
| CloudWatch logs | $0.50/month | ~100MB/month retention |
| **Monthly total** | < $5 | Daily runs + monitoring |

### NFR-004: Observability

| Requirement | Implementation |
|-------------|----------------|
| Structured logging | JSON logs with `autom8y_log` |
| Request tracing | Lambda request ID as correlation ID |
| Metric dimensions | entity_type, environment, result |
| Log retention | 30 days (CloudWatch) |

### NFR-005: Security

| Requirement | Implementation |
|-------------|----------------|
| Secrets management | ASANA_PAT via Secrets Manager |
| IAM least privilege | S3 bucket/prefix scoped, no admin |
| Network isolation | VPC not required (S3 + Asana APIs public) |
| Encryption | S3 SSE-S3 for cached DataFrames |

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Lambda timeout during entity processing | Current entity completes if possible; checkpoint saved; retry picks up remaining |
| Asana API rate limit | Exponential backoff with jitter; fail after 5 retries |
| S3 write failure | Retry 3 times; fail entity type; continue to next |
| Invalid ASANA_PAT | Fail fast with clear error; route to DLQ |
| No projects discovered | Fail with `EntityProjectRegistry not initialized`; alert |
| Concurrent Lambda invocations | Idempotent; later invocation overwrites with fresh data |
| Entity type not configured | Skip with `WarmResult.SKIPPED`; log warning |
| Zero tasks in project | Succeed with empty DataFrame; watermark updated |
| Schema version mismatch | Log warning; rebuild DataFrame with current schema |

---

## Success Criteria (Detailed)

### SC-001: Lambda Completes Within Timeout

**Verification**:
- Integration test with production-like data volume (10K+ tasks)
- Monitor `WarmDuration` metric for 99th percentile < 14 minutes
- No timeout errors in CloudWatch logs over 7-day period

### SC-002: S3 Artifacts Updated

**Verification**:
- After each run, verify S3 objects exist for all entity types
- Watermark timestamps are within expected range (< 15 minutes old)
- Parquet files are valid and readable

### SC-003: CloudWatch Alarms Fire

**Verification**:
- Simulate failure by invoking with invalid credentials
- Verify alarm transitions to ALARM state within 5 minutes
- Verify SNS notification is delivered

### SC-004: Manual Trigger Works

**Verification**:
- Execute `just cache-warm-lambda` from development machine
- Verify Lambda invocation succeeds
- Verify command returns status and duration

### SC-005: EventBridge Scheduling

**Verification**:
- Verify EventBridge rule exists with correct schedule
- Check CloudWatch Events metrics for scheduled invocations
- Verify invocations occur at expected time (2 AM UTC)

### SC-006: Chunked Processing Persists Progress

**Verification**:
- Inject 10-second delay per entity type
- Verify each entity type's DataFrame is persisted independently
- Simulate timeout after 2 entity types; verify partial results in S3

### SC-007: DLQ Integration

**Verification**:
- Simulate failure (invalid event payload)
- Verify message appears in DLQ
- Verify DLQ alarm fires

### SC-008: Cold Start Latency

**Verification**:
- Measure cold start via `INIT_START` CloudWatch log entry
- Verify entity discovery completes within 5 seconds
- Monitor `ColdStartDuration` custom metric

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Real-time cache invalidation | Polling-based freshness sufficient; webhooks add complexity |
| Multi-region deployment | Single-region (us-east-1) sufficient for current scale |
| Custom warm schedules per entity | Uniform schedule simpler; can add per-entity schedules later |
| Step Functions orchestration | Simple Lambda sufficient initially; add if complexity grows |
| Cache pre-warming on deploy | EventBridge schedule ensures freshness; deploy-triggered warm is optional |
| Local development warm | ECS-based `cache-warm-local` remains for local development |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `cache_warmer.py` Lambda handler | Implemented | Existing handler at `src/autom8_asana/lambda_handlers/cache_warmer.py` |
| DataFrameCache S3 tier | Implemented | S3 storage at `s3://autom8-s3/asana-cache/project-frames/` |
| CacheWarmer class | Implemented | Priority-based warming at `src/autom8_asana/cache/dataframe/warmer.py` |
| EntityProjectRegistry | Implemented | Project GID discovery for entity types |
| ASANA_PAT secret | Required | Secrets Manager secret with Asana PAT |
| ASANA_WORKSPACE_GID secret | Required | Secrets Manager secret with workspace GID |
| ECR repository | Required | Container image repository for Lambda deployment |
| S3 bucket permissions | Required | Lambda IAM role needs S3 read/write |
| autom8y Terraform | Exists | Terraform patterns in `terraform/services/` |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Lambda timeout with large datasets | Medium | High | Chunked processing (FR-001); monitoring timeout warnings |
| Asana API rate limiting | Low | Medium | Exponential backoff; morning schedule avoids business hour traffic |
| Cost overrun from frequent invocations | Low | Low | Daily schedule; skip-fresh-cache logic (FR-009) |
| Cold start latency > 5s | Medium | Low | Optimize imports; provisioned concurrency if needed |
| DLQ queue growth unnoticed | Low | Medium | CloudWatch alarm on queue depth > 0 |
| Concurrent invocations causing conflicts | Low | Low | Idempotent writes; last-write-wins |

---

## Phased Rollout

### Phase 1: Basic Lambda Deployment (Week 1)

**Scope**:
- Terraform module with Lambda function
- IAM roles and S3 permissions
- Basic just commands (`cache-warm-lambda`)
- CloudWatch log group

**Exit Criteria**:
- Lambda can be invoked manually
- Warming completes for all entity types
- Logs visible in CloudWatch

### Phase 2: Chunked Processing (Week 1-2)

**Scope**:
- Implement checkpoint after each entity type
- Add timeout detection and graceful exit
- Emit custom CloudWatch metrics

**Exit Criteria**:
- Partial progress survives timeout
- Retry resumes from checkpoint
- Metrics visible in CloudWatch

### Phase 3: EventBridge and DLQ (Week 2)

**Scope**:
- EventBridge rule with daily schedule
- DLQ for failed invocations
- CloudWatch alarms for failures

**Exit Criteria**:
- Scheduled runs execute at 2 AM UTC
- Failed invocations route to DLQ
- Alarms fire on consecutive failures

### Phase 4: Production Hardening (Week 2-3)

**Scope**:
- Production deployment with monitoring
- Runbook documentation
- Performance tuning (memory, concurrency)
- Optional: concurrent entity warming

**Exit Criteria**:
- 7 consecutive days of successful scheduled runs
- SRE sign-off on monitoring and alerting
- Documentation complete

---

## Appendix A: Existing Code References

### Lambda Handler

```python
# src/autom8_asana/lambda_handlers/cache_warmer.py
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for cache warming.

    Args:
        event: Lambda event with optional configuration:
            - entity_types (list[str]): Optional list of entity types
            - strict (bool): If True, fail on any entity type failure
        context: Lambda context

    Returns:
        {"statusCode": 200|500, "body": WarmResponse.to_dict()}
    """
```

### CacheWarmer Class

```python
# src/autom8_asana/cache/dataframe/warmer.py
@dataclass
class CacheWarmer:
    cache: "DataFrameCache"
    priority: list[str] = ["offer", "unit", "business", "contact"]
    strict: bool = True

    async def warm_all_async(
        self,
        client: "AsanaClient",
        project_gid_provider: Callable[[str], str | None],
    ) -> list[WarmStatus]:
        """Warm all entity types in priority order."""
```

### S3 Cache Structure

```
s3://autom8-s3/
  asana-cache/
    project-frames/
      unit/
        {project_gid}.parquet
        {project_gid}.metadata.json
      business/
        ...
      offer/
        ...
      contact/
        ...
```

---

## Appendix B: Terraform Module Structure

```
terraform/modules/autom8-cache-lambda/
  main.tf           # Lambda function, log group
  iam.tf            # IAM role and policies
  eventbridge.tf    # Scheduled rule and target
  dlq.tf            # SQS dead-letter queue
  cloudwatch.tf     # Alarms and dashboard
  variables.tf      # Module inputs
  outputs.tf        # Module outputs
  README.md         # Usage documentation
```

---

## Appendix C: Just Command Reference

```just
# cache-lambda.just (new file)

# Invoke Lambda to warm cache
cache-warm-lambda entity="" env="staging":
    #!/usr/bin/env bash
    set -euo pipefail
    FUNCTION="autom8-cache-warmer-{{env}}"

    if [ -n "{{entity}}" ]; then
        PAYLOAD='{"entity_types": ["{{entity}}"]}'
    else
        PAYLOAD='{}'
    fi

    aws lambda invoke \
        --function-name "$FUNCTION" \
        --payload "$PAYLOAD" \
        --cli-binary-format raw-in-base64-out \
        /tmp/lambda-response.json

    cat /tmp/lambda-response.json | jq .

# Check Lambda invocation status
cache-warm-lambda-status env="staging":
    aws lambda get-function \
        --function-name "autom8-cache-warmer-{{env}}" \
        --query 'Configuration.{State:State,LastModified:LastModified}' \
        --output table

# Tail Lambda logs
cache-warm-lambda-logs env="staging":
    aws logs tail "/aws/lambda/autom8-cache-warmer-{{env}}" --follow
```

---

## Appendix D: Cost Breakdown

| Component | Unit Cost | Monthly Usage | Monthly Cost |
|-----------|-----------|---------------|--------------|
| Lambda compute | $0.0000166667/GB-s | 30 runs * 900s * 1GB = 27,000 GB-s | $0.45 |
| Lambda requests | $0.20/1M requests | 30 requests | $0.00 |
| S3 PUT requests | $0.005/1K requests | 120 requests (4 entities * 30 days) | $0.00 |
| S3 storage | $0.023/GB | ~1GB | $0.02 |
| CloudWatch Logs | $0.50/GB ingested | ~0.1GB | $0.05 |
| CloudWatch Metrics | $0.30/metric/month | 6 custom metrics | $1.80 |
| CloudWatch Alarms | $0.10/alarm/month | 3 alarms | $0.30 |
| SQS (DLQ) | $0.40/1M requests | ~0 (failures only) | $0.00 |
| **Total** | | | **$2.62** |

---

**End of PRD**
