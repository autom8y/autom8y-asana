---
artifact_id: ADR-0065
title: "EventBridge Retry with Checkpoint Resume for Lambda Cache Warmer"
created_at: "2026-01-06T15:30:00Z"
author: architect
status: accepted
context: "The Lambda cache warmer needs a retry strategy that handles both invocation-level failures (transient errors) and timeout-induced partial completions. We need to decide how to combine AWS-native retry mechanisms with application-level checkpointing."
decision: "Use EventBridge retry policy (2 attempts, exponential backoff) for invocation-level failures, combined with S3-based checkpointing for timeout recovery. DLQ captures failures after retry exhaustion."
consequences:
  - type: positive
    description: "Simple architecture - uses native AWS retry without custom orchestration"
  - type: positive
    description: "Clear separation - EventBridge handles invocation retry, checkpointing handles partial progress"
  - type: positive
    description: "Observable - DLQ messages provide clear signal for manual intervention"
  - type: negative
    description: "Limited to 2 retries - complex failure scenarios may require manual intervention"
    mitigation: "DLQ alerting enables fast human response; most failures are transient and resolve within 2 retries"
  - type: negative
    description: "No built-in retry delay customization per error type"
    mitigation: "In-handler backoff for rate limiting; EventBridge retry for invocation failures"
  - type: neutral
    description: "Requires monitoring both Lambda errors and DLQ depth"
related_artifacts:
  - PRD-lambda-cache-warmer
  - TDD-lambda-cache-warmer
  - ADR-0064
tags:
  - lambda
  - retry
  - error-handling
  - eventbridge
schema_version: "1.0"
---

## Context

The Lambda cache warmer must handle several failure modes:

| Failure Mode | Frequency | Recovery |
|--------------|-----------|----------|
| Lambda timeout (15 min) | Expected with large datasets | Resume from checkpoint |
| Asana API rate limit | Occasional | Retry with backoff |
| Asana API 5xx | Rare | Retry |
| S3 write failure | Very rare | Retry |
| Invalid credentials | Permanent until fixed | Fail fast, alert |
| No projects discovered | Permanent until fixed | Fail fast, alert |

We evaluated three retry strategies:

| Strategy | Description |
|----------|-------------|
| **EventBridge + Checkpoint** | Native retry for failures; checkpoint for partial progress |
| **Lambda Destinations** | Async routing based on success/failure |
| **Step Functions** | Full orchestration with explicit retry and error handling |

## Decision

We will use **EventBridge retry with checkpoint resume**:

1. **EventBridge retry policy**: 2 retry attempts with exponential backoff for invocation-level failures
2. **S3 checkpointing**: Resume from last completed entity type on any retry (timeout or failure)
3. **DLQ routing**: After retry exhaustion, failed invocations route to SQS DLQ
4. **In-handler backoff**: Exponential backoff for Asana API rate limits (handled within the handler)

```
EventBridge Schedule
        |
        v
+-------+--------+
| Lambda Handler |<-------- Retry (up to 2x)
+-------+--------+
        |
   +----+----+
   |         |
Success   Failure
   |         |
   v         v
 Clear    Save
Checkpoint Checkpoint
             |
             v
         Route to DLQ
         (after 2 retries)
```

## Rationale

### Why EventBridge retry over Lambda Destinations?

1. **Simpler configuration**: EventBridge retry is declarative in Terraform:
   ```hcl
   retry_policy {
     maximum_event_age_in_seconds = 3600
     maximum_retry_attempts       = 2
   }
   ```

2. **Same behavior for scheduled and manual triggers**: Both use the same EventBridge target configuration.

3. **Lambda Destinations add complexity**: Requires separate Lambda functions or SNS topics for success/failure routing, which is overkill for our use case.

### Why not Step Functions?

Step Functions provide richer orchestration (parallel execution, wait states, explicit error handling) but:

1. **Cost**: Step Functions charge per state transition; Lambda already handles our logic
2. **Complexity**: Our flow is simple (sequential entity warming with checkpointing)
3. **Operational burden**: Another service to monitor and debug
4. **Premature optimization**: Can migrate to Step Functions later if orchestration needs grow

### Why 2 retries?

- Most transient failures (network, rate limits) resolve within 1-2 retries
- 3 retries would add 3+ hours of delay before DLQ alerting
- Checkpoint resume means retries don't restart from scratch

### Why combine with checkpointing?

EventBridge retry handles complete invocation failures. Checkpointing handles:
- **Timeout**: Lambda completed some entities before timeout
- **Partial failure**: One entity failed but others succeeded

Without checkpointing, every retry would re-warm already-completed entities, wasting time and API quota.

## Consequences

### Positive

- **Native AWS integration**: No custom retry logic to maintain
- **Clear failure signal**: DLQ messages indicate when human intervention needed
- **Efficient retries**: Checkpointing prevents redundant work

### Negative

- **Limited retry count**: 2 retries may be insufficient for extended outages
  - **Mitigation**: DLQ alerting enables manual re-trigger; outages > 2 hours are rare
- **No error-specific retry logic**: Can't configure different retry for rate limit vs. auth failure
  - **Mitigation**: In-handler classification; fail fast on permanent errors

### Neutral

- Operators must monitor both Lambda errors and DLQ depth
- Manual re-trigger required after DLQ routing

## Failure Classification

The handler classifies failures to determine retry behavior:

```python
def _classify_error(error: Exception) -> str:
    """Classify error as transient or permanent."""
    if isinstance(error, RateLimitError):
        return "transient"  # Retry with backoff
    if isinstance(error, (AuthenticationError, ConfigurationError)):
        return "permanent"  # Fail fast, route to DLQ
    if isinstance(error, (S3Error, NetworkError)):
        return "transient"  # Retry
    return "transient"  # Default to retry
```

Permanent errors bypass checkpointing and fail immediately to surface configuration issues quickly.

## DLQ Message Schema

```json
{
  "requestId": "abc-123",
  "functionName": "autom8-cache-warmer-production",
  "errorType": "RuntimeError",
  "errorMessage": "Bot PAT not available",
  "timestamp": "2026-01-06T02:15:00Z",
  "entityTypesCompleted": ["unit"],
  "entityTypesFailed": ["business", "offer", "contact"],
  "checkpointKey": "cache-warmer/checkpoints/latest.json",
  "retryAttempt": 2
}
```

## Implementation Notes

### EventBridge Target Configuration

```hcl
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "CacheWarmerLambdaTarget"
  arn       = aws_lambda_function.cache_warmer.arn

  retry_policy {
    maximum_event_age_in_seconds = 3600  # 1 hour
    maximum_retry_attempts       = 2
  }

  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}
```

### In-Handler Rate Limit Backoff

```python
async def _warm_with_backoff(entity_type: str, max_retries: int = 3) -> WarmStatus:
    """Warm entity with exponential backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            return await _warm_entity(entity_type)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            delay = 2 ** attempt + random.uniform(0, 1)  # Exponential + jitter
            await asyncio.sleep(delay)
```

## Alternatives Considered

### Lambda Destinations

```
Lambda
  |
  +---> On Success ---> SNS (optional)
  |
  +---> On Failure ---> SQS DLQ
```

**Rejected because**:
- Async invocation required (complicates manual triggering)
- Success destination is unnecessary for our use case
- EventBridge DLQ provides equivalent failure routing

### Step Functions State Machine

```
StartState
  |
  v
WarmUnit --> WarmBusiness --> WarmOffer --> WarmContact
  |              |              |              |
  +---> Retry ---+---> Retry ---+---> Retry ---+
  |              |              |              |
  +---> Fail ----+---> Fail ----+---> Fail ----+
                                               |
                                               v
                                           Complete
```

**Rejected because**:
- Adds cost (~$0.025 per execution vs. ~$0.006 for Lambda alone)
- Requires Step Functions expertise for debugging
- Our sequential flow doesn't benefit from Step Functions' parallelism
- Can migrate later if orchestration needs grow (FR-010 in PRD)

## References

- PRD-lambda-cache-warmer FR-002 (EventBridge scheduling)
- PRD-lambda-cache-warmer FR-006 (DLQ integration)
- PRD-lambda-cache-warmer FR-010 (Step Functions as future option)
- ADR-0064 (checkpoint persistence strategy)
