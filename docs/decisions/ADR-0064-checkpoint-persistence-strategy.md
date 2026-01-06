---
artifact_id: ADR-0064
title: "S3 Metadata for Lambda Cache Warmer Checkpoint Persistence"
created_at: "2026-01-06T15:30:00Z"
author: architect
status: accepted
context: "The Lambda cache warmer must handle Lambda's 15-minute timeout with 50K+ tasks across four entity types. Checkpointing progress after each entity type enables resume-on-retry, but we need to decide where to persist checkpoint state."
decision: "Use S3 object storage for checkpoint persistence, storing a JSON checkpoint record at a well-known key (cache-warmer/checkpoints/latest.json) with a 1-hour staleness window."
consequences:
  - type: positive
    description: "No additional AWS services required - leverages existing S3 bucket and IAM permissions"
  - type: positive
    description: "Atomic with cache writes - checkpoint and cache data use same S3 client and error handling patterns"
  - type: positive
    description: "Simple debugging - checkpoint is a readable JSON file that can be inspected with aws s3 cp"
  - type: positive
    description: "Natural expiration via staleness check - no TTL configuration needed"
  - type: negative
    description: "Limited to ~2KB for S3 object metadata approach; requires separate object for larger state"
    mitigation: "Using full S3 object (not metadata) allows unlimited size; current checkpoint is well under 2KB"
  - type: negative
    description: "No ACID transactions for checkpoint updates"
    mitigation: "Single writer (Lambda concurrency=1) eliminates race conditions; idempotent operations"
  - type: neutral
    description: "Requires S3 GET on every invocation to check for checkpoint"
related_artifacts:
  - PRD-lambda-cache-warmer
  - TDD-lambda-cache-warmer
tags:
  - lambda
  - caching
  - persistence
  - s3
schema_version: "1.0"
---

## Context

The Lambda-based DataFrame cache warmer (PRD-lambda-cache-warmer) must warm 50K+ tasks across four entity types within Lambda's 15-minute hard timeout. Per FR-001 and FR-007, the system needs:

1. **Chunked processing**: Save progress after each entity type completes
2. **Resume capability**: On retry, resume from the last checkpoint rather than starting over
3. **Staleness window**: Ignore checkpoints older than 1 hour (stale data)

We evaluated three options for checkpoint persistence:

| Option | Description |
|--------|-------------|
| **S3 object** | Store JSON checkpoint at well-known S3 key |
| **DynamoDB** | Store checkpoint in DynamoDB table with TTL |
| **Lambda context** | Use Lambda's built-in context for cross-invocation state |

## Decision

We will use **S3 object storage** for checkpoint persistence, storing a single JSON file at:

```
s3://autom8-s3/cache-warmer/checkpoints/latest.json
```

The checkpoint record contains:
- `invocation_id`: Lambda request ID for correlation
- `completed_entities`: List of successfully warmed entity types
- `pending_entities`: List of entity types not yet processed
- `entity_results`: WarmStatus results for completed entities
- `created_at`: Checkpoint creation timestamp
- `expires_at`: Staleness expiration (created_at + 1 hour)

## Rationale

### Why S3 over DynamoDB?

1. **No additional infrastructure**: The cache warmer already uses S3 for DataFrame storage. Adding DynamoDB would introduce a new service dependency, IAM permissions, and operational burden.

2. **Consistent patterns**: S3Tier already handles JSON serialization, error handling, and client management. CheckpointManager can follow the same patterns.

3. **Simple debugging**: Operators can inspect checkpoints with:
   ```bash
   aws s3 cp s3://autom8-s3/cache-warmer/checkpoints/latest.json - | jq .
   ```

4. **Cost**: S3 PUT/GET is cheaper than DynamoDB for our low-frequency access pattern (1-2 times per day).

### Why not Lambda context?

Lambda context does not persist across invocations. When Lambda times out and EventBridge retries, the new invocation has no access to the previous invocation's state.

### Why a single "latest.json" file?

1. **Single writer**: Lambda has `reserved_concurrent_executions = 1`, so only one invocation runs at a time.
2. **Simplicity**: No need to manage multiple checkpoint files or version cleanup.
3. **Clear semantics**: Load checkpoint -> process -> clear checkpoint on success.

## Consequences

### Positive

- **Zero infrastructure changes**: Uses existing S3 bucket
- **Atomic with cache updates**: Same S3 client and error handling
- **Human-readable**: JSON format for easy debugging
- **Natural staleness**: Code-based TTL check, no external configuration

### Negative

- **No ACID guarantees**: S3 is eventually consistent for some operations
  - **Mitigation**: Single writer eliminates race conditions; checkpoint operations are idempotent
- **Extra S3 GET per invocation**: Adds ~50-100ms latency to check for checkpoint
  - **Mitigation**: Acceptable for daily scheduled job; negligible compared to total warm time

### Neutral

- Checkpoint must fit in S3 object (not limited to 2KB metadata)
- Requires explicit staleness check in code

## Implementation Notes

```python
class CheckpointManager:
    """S3-based checkpoint persistence."""

    def _checkpoint_key(self) -> str:
        return f"{self.prefix}latest.json"

    async def load_async(self) -> CheckpointRecord | None:
        """Load checkpoint if exists and fresh."""
        # GET s3://bucket/cache-warmer/checkpoints/latest.json
        # Return None if not found or stale

    async def save_async(self, ...) -> bool:
        """Save checkpoint to S3."""
        # PUT s3://bucket/cache-warmer/checkpoints/latest.json

    async def clear_async(self) -> bool:
        """Delete checkpoint after successful completion."""
        # DELETE s3://bucket/cache-warmer/checkpoints/latest.json
```

## Alternatives Considered

### DynamoDB Table

```
Table: autom8-cache-warmer-checkpoints
PK: "checkpoint"
SK: "latest"
TTL: expires_at (1 hour from creation)
```

**Rejected because**:
- Adds DynamoDB dependency and IAM permissions
- Requires table creation in Terraform
- More complex error handling (conditional writes, throttling)
- Overkill for single-record storage

### SSM Parameter Store

```
/autom8/cache-warmer/checkpoint = { JSON }
```

**Rejected because**:
- 4KB parameter limit could be constraining
- Parameter Store is designed for configuration, not ephemeral state
- No natural TTL support

## References

- PRD-lambda-cache-warmer FR-001 (chunked processing)
- PRD-lambda-cache-warmer FR-007 (checkpoint resume)
- TDD-lambda-cache-warmer Section 3 (checkpoint architecture)
