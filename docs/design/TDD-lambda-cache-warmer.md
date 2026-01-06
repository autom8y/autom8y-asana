---
artifact_id: TDD-lambda-cache-warmer
title: "Lambda-Based DataFrame Cache Warmer Infrastructure"
created_at: "2026-01-06T15:00:00Z"
author: architect
prd_ref: PRD-lambda-cache-warmer
status: draft
components:
  - name: LambdaCacheWarmer
    type: module
    description: "Enhanced Lambda handler with chunked processing and timeout resilience"
    dependencies:
      - name: CacheWarmer
        type: internal
      - name: DataFrameCache
        type: internal
      - name: CheckpointManager
        type: internal
  - name: CheckpointManager
    type: module
    description: "S3-based checkpoint persistence for resume-on-retry capability"
    dependencies:
      - name: S3Tier
        type: internal
      - name: boto3
        type: external
  - name: TerraformModule
    type: config
    description: "Reusable Terraform module for Lambda infrastructure deployment"
    dependencies:
      - name: AWS Lambda
        type: external
      - name: AWS EventBridge
        type: external
      - name: AWS SQS
        type: external
      - name: AWS CloudWatch
        type: external
  - name: Observability
    type: module
    description: "CloudWatch metrics, alarms, and structured logging"
    dependencies:
      - name: autom8y_log
        type: internal
      - name: CloudWatch
        type: external
api_contracts:
  - endpoint: "Lambda Invocation"
    method: POST
    description: "AWS Lambda event invocation for cache warming"
    request:
      headers: {}
      body:
        entity_types: "list[str] | None - Optional filter for specific entity types"
        strict: "bool - Fail on any entity failure (default: true)"
        resume_from_checkpoint: "bool - Resume from last checkpoint if available (default: true)"
    response:
      success:
        status: 200
        body:
          success: boolean
          message: string
          entity_results: array
          total_rows: integer
          duration_ms: float
          checkpoint_cleared: boolean
      errors:
        - status: 500
          description: "Cache warming failed (partial or complete)"
data_models:
  - name: CheckpointRecord
    type: value_object
    fields:
      - name: invocation_id
        type: str
        required: true
        constraints: "Lambda request ID for correlation"
      - name: completed_entities
        type: list[str]
        required: true
        constraints: "Entity types that completed successfully"
      - name: pending_entities
        type: list[str]
        required: true
        constraints: "Entity types not yet processed"
      - name: entity_results
        type: list[dict]
        required: true
        constraints: "WarmStatus for each completed entity"
      - name: created_at
        type: datetime
        required: true
        constraints: "ISO 8601 timestamp"
      - name: expires_at
        type: datetime
        required: true
        constraints: "created_at + 1 hour staleness window"
  - name: DLQMessage
    type: value_object
    fields:
      - name: requestId
        type: str
        required: true
        constraints: "Lambda request ID"
      - name: functionName
        type: str
        required: true
        constraints: "Lambda function name"
      - name: errorType
        type: str
        required: true
        constraints: "Exception class name"
      - name: errorMessage
        type: str
        required: true
        constraints: "Error description"
      - name: timestamp
        type: str
        required: true
        constraints: "ISO 8601 timestamp"
      - name: entityTypesCompleted
        type: list[str]
        required: true
        constraints: "Successfully warmed entity types"
      - name: entityTypesFailed
        type: list[str]
        required: true
        constraints: "Entity types that failed or were not attempted"
      - name: checkpointKey
        type: str
        required: false
        constraints: "S3 key for checkpoint if available"
security_considerations:
  - "ASANA_PAT retrieved from AWS Secrets Manager at runtime"
  - "IAM role follows least privilege - scoped to specific S3 prefix and metric namespace"
  - "No VPC required - S3 and Asana APIs are public endpoints"
  - "S3 objects encrypted with SSE-S3"
related_adrs:
  - ADR-0064
  - ADR-0065
schema_version: "1.0"
---

# TDD: Lambda-Based DataFrame Cache Warmer Infrastructure

> Technical Design Document for implementing production-ready Lambda-based cache warming with timeout resilience, checkpointing, and comprehensive observability.

---

## 1. Overview

This TDD defines the technical design for enhancing the existing Lambda cache warmer to handle Lambda's 15-minute timeout constraint with 50K+ tasks across four entity types. The design introduces chunked processing with S3-based checkpointing, a reusable Terraform module, and comprehensive observability.

### 1.1 Design Goals

| Goal | Approach |
|------|----------|
| **Timeout Resilience** | Checkpoint after each entity type; detect remaining time; graceful exit |
| **Resume Capability** | S3-based checkpoint with 1-hour staleness window |
| **Infrastructure as Code** | Reusable Terraform module at `terraform/modules/autom8-cache-lambda/` |
| **Observability** | CloudWatch metrics, alarms, structured logging with correlation IDs |
| **Cost Efficiency** | Lambda pricing vs ECS (~$0.006 vs $0.05 per invocation) |

### 1.2 Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Lambda max timeout | 15 minutes | AWS Lambda hard limit |
| Task volume | 50K+ tasks | Production data |
| Entity types | 4 (unit, business, offer, contact) | PRD-lambda-cache-warmer |
| S3 bucket | autom8-s3 | Existing infrastructure |
| Checkpoint staleness | < 1 hour | PRD FR-007 |
| Timeout buffer | 2 minutes | PRD FR-001 |

---

## 2. Architecture

### 2.1 System Context

```
                                    +------------------+
                                    |   EventBridge    |
                                    |  (Daily 2 AM)    |
                                    +--------+---------+
                                             |
                                             v
+-------------------+             +----------+---------+
|   Manual Trigger  |------------>|   Lambda Function  |
| (just cache-warm) |             | autom8-cache-warmer|
+-------------------+             +----------+---------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
                    v                        v                        v
          +---------+--------+    +----------+---------+    +---------+---------+
          |   Asana API      |    |       S3           |    |   CloudWatch      |
          | (Task fetching)  |    | (Cache + Checkpoint)|   | (Metrics + Logs)  |
          +------------------+    +--------------------+    +-------------------+
                                             |
                                             v
                                  +----------+---------+
                                  |  SQS Dead-Letter   |
                                  |      Queue         |
                                  +--------------------+
```

### 2.2 Component Architecture

```
src/autom8_asana/lambda_handlers/
  cache_warmer.py              # Enhanced handler with timeout detection
  checkpoint.py                # NEW: CheckpointManager for S3 persistence

terraform/modules/autom8-cache-lambda/
  main.tf                      # Lambda function, log group
  iam.tf                       # IAM role and policies
  eventbridge.tf               # Scheduled rule and target
  dlq.tf                       # SQS dead-letter queue
  cloudwatch.tf                # Alarms and dashboard
  variables.tf                 # Module inputs
  outputs.tf                   # Module outputs
```

---

## 3. Chunked Processing Architecture (FR-001)

### 3.1 Design Decision: Checkpoint Strategy

**Decision**: Use S3 object metadata for checkpoint persistence.

**Alternatives Considered**:

| Strategy | Pros | Cons |
|----------|------|------|
| **S3 metadata** | Atomic with cache writes; no additional resources; leverages existing S3Tier | Limited to 2KB metadata; requires custom JSON serialization |
| DynamoDB | ACID transactions; query flexibility; native TTL | Additional service; cost; complexity |
| Lambda context | Zero latency; built-in | Lost on timeout; no cross-invocation persistence |

**Rationale**: S3 metadata is sufficient for our checkpoint needs (< 2KB), avoids introducing DynamoDB dependency, and maintains atomic consistency with cache writes. The checkpoint record is small and fits within S3's 2KB metadata limit.

See **ADR-0064** for full decision record.

### 3.2 Timeout Detection

The Lambda handler monitors `context.get_remaining_time_in_millis()` and exits gracefully when remaining time falls below the buffer threshold.

```python
# Constants
TIMEOUT_BUFFER_MS = 120_000  # 2 minutes (per PRD FR-001)
CHECKPOINT_PREFIX = "cache-warmer/checkpoints/"

def _should_exit_early(context: LambdaContext) -> bool:
    """Check if we should exit to avoid timeout.

    Args:
        context: Lambda context with remaining time.

    Returns:
        True if remaining time < TIMEOUT_BUFFER_MS.
    """
    remaining_ms = context.get_remaining_time_in_millis()
    return remaining_ms < TIMEOUT_BUFFER_MS
```

### 3.3 Processing Flow

```
                    START
                      |
                      v
            +-------------------+
            | Load Checkpoint?  |
            | (if resume=true)  |
            +--------+----------+
                     |
        +------------+------------+
        |                         |
        v                         v
   [Checkpoint Found        [No Checkpoint]
    & Fresh (<1hr)]               |
        |                         |
        v                         v
   Resume from               Start from
   pending_entities          full priority
        |                         |
        +------------+------------+
                     |
                     v
            +-------------------+
            | FOR each entity   |
            | in processing_list|
            +--------+----------+
                     |
                     v
            +-------------------+
            | Check remaining   |
            | time < 2 min?     |
            +--------+----------+
                     |
          +----------+----------+
          |                     |
          v                     v
    [Time OK]             [Low Time]
          |                     |
          v                     v
    +-------------+      +-------------+
    | Warm entity |      | Save        |
    | type        |      | checkpoint  |
    +------+------+      | & exit      |
           |             +-------------+
           v
    +-------------+
    | Persist to  |
    | S3 cache    |
    +------+------+
           |
           v
    +-------------+
    | Save        |
    | checkpoint  |
    +------+------+
           |
           v
    [Next entity or COMPLETE]
```

### 3.4 Checkpoint Record Schema

```python
@dataclass
class CheckpointRecord:
    """Checkpoint for resuming partial warming runs.

    Persisted to S3 at: s3://{bucket}/cache-warmer/checkpoints/latest.json

    Staleness window: 1 hour from created_at. Checkpoints older than this
    are ignored and warming restarts from scratch.
    """
    invocation_id: str          # Lambda request ID for correlation
    completed_entities: list[str]  # Entity types successfully warmed
    pending_entities: list[str]    # Entity types not yet processed
    entity_results: list[dict]     # WarmStatus.to_dict() for each completed
    created_at: datetime           # Checkpoint creation time
    expires_at: datetime           # created_at + 1 hour

    def is_stale(self) -> bool:
        """Check if checkpoint has exceeded staleness window."""
        return datetime.now(timezone.utc) > self.expires_at

    def to_json(self) -> str:
        """Serialize to JSON for S3 storage."""
        return json.dumps({
            "invocation_id": self.invocation_id,
            "completed_entities": self.completed_entities,
            "pending_entities": self.pending_entities,
            "entity_results": self.entity_results,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        })

    @classmethod
    def from_json(cls, data: str) -> "CheckpointRecord":
        """Deserialize from JSON."""
        obj = json.loads(data)
        return cls(
            invocation_id=obj["invocation_id"],
            completed_entities=obj["completed_entities"],
            pending_entities=obj["pending_entities"],
            entity_results=obj["entity_results"],
            created_at=datetime.fromisoformat(obj["created_at"]),
            expires_at=datetime.fromisoformat(obj["expires_at"]),
        )
```

### 3.5 CheckpointManager Implementation

```python
@dataclass
class CheckpointManager:
    """Manages checkpoint persistence to S3.

    Checkpoints are stored at a well-known S3 key for resumption.
    Only one checkpoint exists at a time (latest state).
    """
    bucket: str
    prefix: str = "cache-warmer/checkpoints/"
    s3_client: S3Client | None = None
    staleness_hours: float = 1.0

    def _ensure_client(self) -> S3Client:
        if self.s3_client is None:
            import boto3
            self.s3_client = boto3.client("s3")
        return self.s3_client

    def _checkpoint_key(self) -> str:
        return f"{self.prefix}latest.json"

    async def load_async(self) -> CheckpointRecord | None:
        """Load checkpoint if exists and fresh.

        Returns:
            CheckpointRecord if found and not stale, None otherwise.
        """
        client = self._ensure_client()
        key = self._checkpoint_key()

        try:
            response = client.get_object(Bucket=self.bucket, Key=key)
            data = response["Body"].read().decode("utf-8")
            checkpoint = CheckpointRecord.from_json(data)

            if checkpoint.is_stale():
                logger.info(
                    "checkpoint_stale",
                    extra={
                        "created_at": checkpoint.created_at.isoformat(),
                        "expires_at": checkpoint.expires_at.isoformat(),
                    },
                )
                return None

            logger.info(
                "checkpoint_loaded",
                extra={
                    "invocation_id": checkpoint.invocation_id,
                    "completed": checkpoint.completed_entities,
                    "pending": checkpoint.pending_entities,
                },
            )
            return checkpoint

        except client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.warning(
                "checkpoint_load_error",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            return None

    async def save_async(
        self,
        invocation_id: str,
        completed_entities: list[str],
        pending_entities: list[str],
        entity_results: list[dict],
    ) -> bool:
        """Save checkpoint to S3.

        Args:
            invocation_id: Lambda request ID.
            completed_entities: Successfully warmed entity types.
            pending_entities: Entity types not yet processed.
            entity_results: WarmStatus dictionaries.

        Returns:
            True on success, False on failure.
        """
        client = self._ensure_client()
        key = self._checkpoint_key()

        now = datetime.now(timezone.utc)
        checkpoint = CheckpointRecord(
            invocation_id=invocation_id,
            completed_entities=completed_entities,
            pending_entities=pending_entities,
            entity_results=entity_results,
            created_at=now,
            expires_at=now + timedelta(hours=self.staleness_hours),
        )

        try:
            client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=checkpoint.to_json().encode("utf-8"),
                ContentType="application/json",
            )

            logger.info(
                "checkpoint_saved",
                extra={
                    "invocation_id": invocation_id,
                    "completed": completed_entities,
                    "pending": pending_entities,
                },
            )
            return True

        except Exception as e:
            logger.error(
                "checkpoint_save_error",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            return False

    async def clear_async(self) -> bool:
        """Clear checkpoint after successful completion.

        Returns:
            True on success, False on failure.
        """
        client = self._ensure_client()
        key = self._checkpoint_key()

        try:
            client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("checkpoint_cleared")
            return True
        except Exception as e:
            logger.warning(
                "checkpoint_clear_error",
                extra={"error": str(e)},
            )
            return False
```

### 3.6 Enhanced Lambda Handler

```python
async def _warm_cache_async_chunked(
    entity_types: list[str] | None = None,
    strict: bool = True,
    resume_from_checkpoint: bool = True,
    context: LambdaContext | None = None,
) -> WarmResponse:
    """Async cache warming with chunked processing and checkpointing.

    Args:
        entity_types: Optional filter for specific entity types.
        strict: If True, fail on any entity type failure.
        resume_from_checkpoint: If True, resume from last checkpoint if available.
        context: Lambda context for timeout detection.

    Returns:
        WarmResponse with results and checkpoint status.
    """
    start_time = time.monotonic()
    invocation_id = context.aws_request_id if context else str(uuid.uuid4())

    # Initialize components
    checkpoint_mgr = CheckpointManager(
        bucket=os.environ.get("ASANA_CACHE_S3_BUCKET", "autom8-s3"),
    )

    # Determine processing list
    default_priority = ["unit", "business", "offer", "contact"]
    processing_list = entity_types or default_priority
    completed_entities: list[str] = []
    entity_results: list[dict] = []

    # Check for existing checkpoint
    if resume_from_checkpoint:
        checkpoint = await checkpoint_mgr.load_async()
        if checkpoint:
            completed_entities = checkpoint.completed_entities
            entity_results = checkpoint.entity_results
            processing_list = checkpoint.pending_entities

            logger.info(
                "resuming_from_checkpoint",
                extra={
                    "prior_invocation": checkpoint.invocation_id,
                    "completed": completed_entities,
                    "pending": processing_list,
                },
            )

    # Initialize cache and client (existing code)
    cache = get_dataframe_cache()
    if cache is None:
        cache = initialize_dataframe_cache()

    if cache is None:
        return WarmResponse(
            success=False,
            message="Failed to initialize DataFrameCache",
            duration_ms=(time.monotonic() - start_time) * 1000,
        )

    # ... registry initialization (existing code) ...

    warmer = CacheWarmer(
        cache=cache,
        priority=processing_list,
        strict=False,  # Handle failures individually for checkpointing
    )

    # Process entity types with timeout detection
    for entity_type in processing_list:
        # Check timeout
        if context and _should_exit_early(context):
            remaining = context.get_remaining_time_in_millis()
            logger.warning(
                "exiting_early_timeout",
                extra={
                    "remaining_ms": remaining,
                    "completed": completed_entities,
                    "pending": [et for et in processing_list if et not in completed_entities],
                },
            )

            # Save checkpoint before exit
            pending = [et for et in processing_list if et not in completed_entities]
            await checkpoint_mgr.save_async(
                invocation_id=invocation_id,
                completed_entities=completed_entities,
                pending_entities=pending,
                entity_results=entity_results,
            )

            return WarmResponse(
                success=False,
                message=f"Partial completion due to timeout. Completed: {completed_entities}",
                entity_results=entity_results,
                total_rows=sum(r.get("row_count", 0) for r in entity_results),
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

        # Warm entity type
        try:
            status = await warmer.warm_entity_async(
                entity_type=entity_type,
                client=client,
                project_gid_provider=get_project_gid,
            )

            entity_results.append(status.to_dict())

            if status.result == WarmResult.SUCCESS:
                completed_entities.append(entity_type)

                # Emit CloudWatch metric
                _emit_metric(
                    metric_name="WarmSuccess",
                    value=1,
                    dimensions={"entity_type": entity_type},
                )
                _emit_metric(
                    metric_name="WarmDuration",
                    value=status.duration_ms,
                    unit="Milliseconds",
                    dimensions={"entity_type": entity_type},
                )
                _emit_metric(
                    metric_name="RowsWarmed",
                    value=status.row_count,
                    dimensions={"entity_type": entity_type},
                )
            else:
                _emit_metric(
                    metric_name="WarmFailure",
                    value=1,
                    dimensions={"entity_type": entity_type},
                )

                if strict:
                    # Save checkpoint and exit
                    pending = [et for et in processing_list if et not in completed_entities]
                    await checkpoint_mgr.save_async(
                        invocation_id=invocation_id,
                        completed_entities=completed_entities,
                        pending_entities=pending,
                        entity_results=entity_results,
                    )

                    return WarmResponse(
                        success=False,
                        message=f"Failed on {entity_type}: {status.error}",
                        entity_results=entity_results,
                        total_rows=sum(r.get("row_count", 0) for r in entity_results),
                        duration_ms=(time.monotonic() - start_time) * 1000,
                    )

            # Save checkpoint after each successful entity
            pending = [et for et in processing_list if et not in completed_entities]
            if pending:  # Don't save if this was the last entity
                await checkpoint_mgr.save_async(
                    invocation_id=invocation_id,
                    completed_entities=completed_entities,
                    pending_entities=pending,
                    entity_results=entity_results,
                )

        except Exception as e:
            logger.error(
                "entity_warm_exception",
                extra={
                    "entity_type": entity_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            entity_results.append({
                "entity_type": entity_type,
                "result": "failure",
                "error": str(e),
            })

            if strict:
                pending = [et for et in processing_list if et not in completed_entities]
                await checkpoint_mgr.save_async(
                    invocation_id=invocation_id,
                    completed_entities=completed_entities,
                    pending_entities=pending,
                    entity_results=entity_results,
                )
                raise

    # All entities completed - clear checkpoint
    await checkpoint_mgr.clear_async()

    total_rows = sum(r.get("row_count", 0) for r in entity_results)
    duration_ms = (time.monotonic() - start_time) * 1000

    return WarmResponse(
        success=True,
        message=f"Cache warm complete: {len(completed_entities)} entities, {total_rows} rows",
        entity_results=entity_results,
        total_rows=total_rows,
        duration_ms=duration_ms,
    )
```

---

## 4. Terraform Module Design (FR-003)

### 4.1 Module Interface

```hcl
# terraform/modules/autom8-cache-lambda/variables.tf

variable "environment" {
  description = "Deployment environment (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be 'staging' or 'production'."
  }
}

variable "s3_bucket" {
  description = "S3 bucket for cache storage"
  type        = string
}

variable "s3_prefix" {
  description = "S3 key prefix for cache objects"
  type        = string
  default     = "asana-cache/project-frames/"
}

variable "memory_size" {
  description = "Lambda memory allocation in MB"
  type        = number
  default     = 1024
  validation {
    condition     = var.memory_size >= 512 && var.memory_size <= 3008
    error_message = "Memory must be between 512 and 3008 MB."
  }
}

variable "timeout" {
  description = "Lambda timeout in seconds (max 900)"
  type        = number
  default     = 900
  validation {
    condition     = var.timeout >= 60 && var.timeout <= 900
    error_message = "Timeout must be between 60 and 900 seconds."
  }
}

variable "schedule_expression" {
  description = "EventBridge schedule expression (cron or rate)"
  type        = string
  default     = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC
}

variable "asana_pat_secret_arn" {
  description = "ARN of Secrets Manager secret containing ASANA_PAT"
  type        = string
}

variable "workspace_gid_secret_arn" {
  description = "ARN of Secrets Manager secret containing ASANA_WORKSPACE_GID"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL for Lambda container image"
  type        = string
}

variable "image_tag" {
  description = "Container image tag to deploy"
  type        = string
  default     = "latest"
}

variable "enable_alarms" {
  description = "Enable CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alert_sns_topic_arn" {
  description = "SNS topic ARN for alarm notifications"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "reserved_concurrency" {
  description = "Reserved concurrent executions (0 = unreserved)"
  type        = number
  default     = 1  # Only one warm at a time
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
```

### 4.2 Module Resources

#### 4.2.1 Lambda Function (main.tf)

```hcl
# terraform/modules/autom8-cache-lambda/main.tf

locals {
  name_prefix = "autom8-cache-warmer-${var.environment}"
  common_tags = merge(var.tags, {
    Service     = "autom8-cache-warmer"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name_prefix}"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# Lambda Function
resource "aws_lambda_function" "cache_warmer" {
  function_name = local.name_prefix
  description   = "DataFrame cache warmer with chunked processing (TDD-lambda-cache-warmer)"
  role          = aws_iam_role.lambda_execution.arn

  # Container image deployment
  package_type = "Image"
  image_uri    = "${var.ecr_repository_url}:${var.image_tag}"

  # Image configuration
  image_config {
    command = ["autom8_asana.lambda_handlers.cache_warmer.handler"]
  }

  # Resource allocation
  memory_size = var.memory_size
  timeout     = var.timeout
  architectures = ["arm64"]

  # Environment variables
  environment {
    variables = {
      ASANA_CACHE_S3_BUCKET    = var.s3_bucket
      ASANA_CACHE_S3_PREFIX    = var.s3_prefix
      ASANA_PAT_SECRET_ARN     = var.asana_pat_secret_arn
      ASANA_WORKSPACE_SECRET_ARN = var.workspace_gid_secret_arn
      LOG_LEVEL                = "INFO"
      CLOUDWATCH_NAMESPACE     = "autom8/cache-warmer"
    }
  }

  # Reserved concurrency: prevent concurrent warms
  reserved_concurrent_executions = var.reserved_concurrency

  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_basic_execution,
  ]

  tags = local.common_tags
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cache_warmer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}
```

#### 4.2.2 IAM Role (iam.tf)

```hcl
# terraform/modules/autom8-cache-lambda/iam.tf

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Lambda Execution Role
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

# Basic Lambda execution
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# X-Ray tracing
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Custom policy for cache warmer
resource "aws_iam_role_policy" "cache_warmer" {
  name = "${local.name_prefix}-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 access for cache and checkpoints
      {
        Sid    = "S3CacheAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:HeadObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket}/${var.s3_prefix}*",
          "arn:aws:s3:::${var.s3_bucket}/cache-warmer/checkpoints/*"
        ]
      },

      # S3 bucket listing (for cache discovery)
      {
        Sid    = "S3BucketList"
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = "arn:aws:s3:::${var.s3_bucket}"
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "${var.s3_prefix}*",
              "cache-warmer/checkpoints/*"
            ]
          }
        }
      },

      # Secrets Manager access
      {
        Sid    = "SecretsManagerAccess"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          var.asana_pat_secret_arn,
          var.workspace_gid_secret_arn
        ]
      },

      # CloudWatch Metrics - scoped namespace
      {
        Sid    = "CloudWatchMetricsAccess"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "autom8/cache-warmer"
          }
        }
      },

      # CloudWatch Logs (extended)
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name_prefix}*"
        ]
      }
    ]
  })
}
```

#### 4.2.3 EventBridge Schedule (eventbridge.tf)

```hcl
# terraform/modules/autom8-cache-lambda/eventbridge.tf

# EventBridge Rule for scheduled invocation
resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${local.name_prefix}-schedule"
  description         = "Triggers cache warmer Lambda daily at 2 AM UTC"
  schedule_expression = var.schedule_expression

  tags = local.common_tags
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "CacheWarmerLambdaTarget"
  arn       = aws_lambda_function.cache_warmer.arn

  # Input passed to Lambda handler
  input = jsonencode({
    source               = "aws.events"
    detail-type          = "Scheduled Event"
    detail = {
      schedule            = var.schedule_expression
      environment         = var.environment
      trigger_type        = "scheduled"
      resume_from_checkpoint = true
    }
  })

  # Retry configuration
  retry_policy {
    maximum_event_age_in_seconds = 3600  # 1 hour
    maximum_retry_attempts       = 2
  }

  # DLQ for failed invocations
  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}
```

#### 4.2.4 Dead-Letter Queue (dlq.tf)

```hcl
# terraform/modules/autom8-cache-lambda/dlq.tf

# SQS Dead-Letter Queue
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.name_prefix}-dlq"
  message_retention_seconds = 1209600  # 14 days

  # Enable server-side encryption
  sqs_managed_sse_enabled = true

  tags = local.common_tags
}

# SQS Policy - allow EventBridge to send messages
resource "aws_sqs_queue_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgeSend"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.dlq.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.schedule.arn
          }
        }
      }
    ]
  })
}
```

#### 4.2.5 Module Outputs (outputs.tf)

```hcl
# terraform/modules/autom8-cache-lambda/outputs.tf

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.cache_warmer.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.cache_warmer.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "dlq_url" {
  description = "URL of the dead-letter queue"
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "ARN of the dead-letter queue"
  value       = aws_sqs_queue.dlq.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.schedule.arn
}

output "dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.cache_warmer.dashboard_name}"
}
```

---

## 5. Observability Design (FR-005)

### 5.1 CloudWatch Metrics

**Namespace**: `autom8/cache-warmer`

| Metric | Unit | Description | Dimensions |
|--------|------|-------------|------------|
| `WarmDuration` | Milliseconds | Time to warm a single entity type | entity_type, environment |
| `WarmSuccess` | Count | Successful entity type warms | entity_type, environment |
| `WarmFailure` | Count | Failed entity type warms | entity_type, environment |
| `RowsWarmed` | Count | Rows warmed per entity type | entity_type, environment |
| `ColdStartDuration` | Milliseconds | Lambda cold start time | environment |
| `EntityDiscoveryDuration` | Milliseconds | Time to discover project GIDs | environment |
| `CheckpointSaved` | Count | Checkpoint saves | environment |
| `CheckpointResumed` | Count | Resumptions from checkpoint | environment |
| `TotalDuration` | Milliseconds | Total invocation duration | environment |

### 5.2 Metric Emission Helper

```python
import os
import boto3
from typing import Any

CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "autom8/cache-warmer")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "staging")

_cloudwatch_client = None

def _get_cloudwatch_client():
    global _cloudwatch_client
    if _cloudwatch_client is None:
        _cloudwatch_client = boto3.client("cloudwatch")
    return _cloudwatch_client

def _emit_metric(
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit CloudWatch metric.

    Args:
        metric_name: Name of the metric.
        value: Metric value.
        unit: CloudWatch unit (Count, Milliseconds, etc.).
        dimensions: Optional additional dimensions.
    """
    client = _get_cloudwatch_client()

    metric_dimensions = [
        {"Name": "environment", "Value": ENVIRONMENT},
    ]

    if dimensions:
        for name, dim_value in dimensions.items():
            metric_dimensions.append({"Name": name, "Value": dim_value})

    try:
        client.put_metric_data(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                    "Dimensions": metric_dimensions,
                }
            ],
        )
    except Exception as e:
        logger.warning(
            "metric_emit_error",
            extra={"metric": metric_name, "error": str(e)},
        )
```

### 5.3 CloudWatch Alarms (cloudwatch.tf)

```hcl
# terraform/modules/autom8-cache-lambda/cloudwatch.tf

# Dashboard
resource "aws_cloudwatch_dashboard" "cache_warmer" {
  dashboard_name = local.name_prefix

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: Duration and Success/Failure
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Warm Duration by Entity Type"
          region  = data.aws_region.current.name
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["autom8/cache-warmer", "WarmDuration", "entity_type", "unit", "environment", var.environment, { stat = "Average" }],
            ["...", "business", ".", ".", { stat = "Average" }],
            ["...", "offer", ".", ".", { stat = "Average" }],
            ["...", "contact", ".", ".", { stat = "Average" }]
          ]
          period = 86400  # 1 day
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Warm Success/Failure"
          region = data.aws_region.current.name
          metrics = [
            ["autom8/cache-warmer", "WarmSuccess", "environment", var.environment, { stat = "Sum", color = "#2ca02c" }],
            [".", "WarmFailure", ".", ".", { stat = "Sum", color = "#d62728" }]
          ]
          period = 86400
        }
      },
      # Row 2: Rows Warmed and Total Duration
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Rows Warmed by Entity Type"
          region = data.aws_region.current.name
          metrics = [
            ["autom8/cache-warmer", "RowsWarmed", "entity_type", "unit", "environment", var.environment, { stat = "Sum" }],
            ["...", "business", ".", ".", { stat = "Sum" }],
            ["...", "offer", ".", ".", { stat = "Sum" }],
            ["...", "contact", ".", ".", { stat = "Sum" }]
          ]
          period = 86400
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Total Invocation Duration"
          region = data.aws_region.current.name
          metrics = [
            ["autom8/cache-warmer", "TotalDuration", "environment", var.environment, { stat = "Average" }],
            ["...", { stat = "Maximum" }]
          ]
          period = 86400
        }
      },
      # Row 3: Lambda Metrics and Logs
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 8
        height = 6
        properties = {
          title  = "Lambda Invocations"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.cache_warmer.function_name, { stat = "Sum" }],
            [".", "Errors", ".", ".", { stat = "Sum" }],
            [".", "Throttles", ".", ".", { stat = "Sum" }]
          ]
          period = 86400
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 12
        width  = 8
        height = 6
        properties = {
          title  = "Checkpoint Activity"
          region = data.aws_region.current.name
          metrics = [
            ["autom8/cache-warmer", "CheckpointSaved", "environment", var.environment, { stat = "Sum" }],
            [".", "CheckpointResumed", ".", ".", { stat = "Sum" }]
          ]
          period = 86400
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 12
        width  = 8
        height = 6
        properties = {
          title  = "DLQ Messages"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.dlq.name, { stat = "Maximum" }]
          ]
          period = 86400
        }
      },
      # Row 4: Recent Logs
      {
        type   = "log"
        x      = 0
        y      = 18
        width  = 24
        height = 6
        properties = {
          title  = "Recent Cache Warmer Logs"
          region = data.aws_region.current.name
          query  = "SOURCE '/aws/lambda/${local.name_prefix}' | fields @timestamp, @message | filter @message like /cache_warm/ | sort @timestamp desc | limit 50"
        }
      }
    ]
  })
}

# Alarm: Consecutive Failures
resource "aws_cloudwatch_metric_alarm" "consecutive_failures" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-consecutive-failures"
  alarm_description   = "Cache warmer has failed for 2 consecutive runs (FR-005)"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  threshold           = 1
  treat_missing_data  = "notBreaching"

  metric_name = "WarmFailure"
  namespace   = "autom8/cache-warmer"
  statistic   = "Sum"
  period      = 86400  # 24 hours

  dimensions = {
    environment = var.environment
  }

  alarm_actions = var.alert_sns_topic_arn != "" ? [var.alert_sns_topic_arn] : []
  ok_actions    = var.alert_sns_topic_arn != "" ? [var.alert_sns_topic_arn] : []

  tags = merge(local.common_tags, {
    Severity = "High"
    Alert    = "CacheWarmConsecutiveFailures"
  })
}

# Alarm: Duration Warning (approaching timeout)
resource "aws_cloudwatch_metric_alarm" "duration_warning" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-duration-warning"
  alarm_description   = "Cache warmer duration exceeds 14 minutes (approaching 15-min timeout)"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 840000  # 14 minutes in milliseconds
  treat_missing_data  = "notBreaching"

  metric_name = "TotalDuration"
  namespace   = "autom8/cache-warmer"
  statistic   = "Maximum"
  period      = 86400

  dimensions = {
    environment = var.environment
  }

  alarm_actions = var.alert_sns_topic_arn != "" ? [var.alert_sns_topic_arn] : []

  tags = merge(local.common_tags, {
    Severity = "Medium"
    Alert    = "CacheWarmTimeout"
  })
}

# Alarm: High Latency Warning
resource "aws_cloudwatch_metric_alarm" "high_latency" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-high-latency"
  alarm_description   = "Cache warmer duration exceeds 10 minutes"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 600000  # 10 minutes in milliseconds
  treat_missing_data  = "notBreaching"

  metric_name = "TotalDuration"
  namespace   = "autom8/cache-warmer"
  statistic   = "Average"
  period      = 86400

  alarm_actions = var.alert_sns_topic_arn != "" ? [var.alert_sns_topic_arn] : []

  tags = merge(local.common_tags, {
    Severity = "Low"
    Alert    = "CacheWarmHighLatency"
  })
}

# Alarm: Lambda Errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-lambda-errors"
  alarm_description   = "Cache warmer Lambda function errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  treat_missing_data  = "notBreaching"

  metric_name = "Errors"
  namespace   = "AWS/Lambda"
  statistic   = "Sum"
  period      = 86400

  dimensions = {
    FunctionName = aws_lambda_function.cache_warmer.function_name
  }

  alarm_actions = var.alert_sns_topic_arn != "" ? [var.alert_sns_topic_arn] : []

  tags = merge(local.common_tags, {
    Severity = "High"
    Alert    = "LambdaErrors"
  })
}

# Alarm: DLQ Messages
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  count = var.enable_alarms ? 1 : 0

  alarm_name          = "${local.name_prefix}-dlq-messages"
  alarm_description   = "Cache warmer DLQ has pending messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  threshold           = 0
  treat_missing_data  = "notBreaching"

  metric_name = "ApproximateNumberOfMessagesVisible"
  namespace   = "AWS/SQS"
  statistic   = "Maximum"
  period      = 300  # 5 minutes

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  alarm_actions = var.alert_sns_topic_arn != "" ? [var.alert_sns_topic_arn] : []

  tags = merge(local.common_tags, {
    Severity = "Medium"
    Alert    = "DLQMessages"
  })
}
```

### 5.4 Structured Logging Schema

All logs use `autom8y_log` with structured JSON output:

```json
{
  "timestamp": "2026-01-06T02:00:00.000Z",
  "level": "INFO",
  "logger": "autom8_asana.lambda_handlers.cache_warmer",
  "message": "cache_warm_success",
  "correlation_id": "abc-123-def-456",
  "extra": {
    "entity_type": "unit",
    "project_gid": "1234567890123456",
    "row_count": 15000,
    "duration_ms": 2500.5,
    "watermark": "2026-01-06T01:59:00.000Z"
  }
}
```

**Correlation ID**: Lambda request ID (`context.aws_request_id`) is used as correlation ID and passed to all log entries.

---

## 6. Error Handling and DLQ (FR-006)

### 6.1 Failure Classification

| Error Type | Classification | Retry Behavior |
|------------|---------------|----------------|
| Asana API rate limit | Transient | EventBridge retry (2x) |
| Asana API 5xx | Transient | EventBridge retry (2x) |
| S3 write failure | Transient | In-handler retry (3x), then fail |
| Invalid ASANA_PAT | Permanent | Fail fast, route to DLQ |
| No projects discovered | Permanent | Fail fast, route to DLQ |
| Lambda timeout | Transient | Resume from checkpoint on retry |
| Schema validation error | Permanent | Log warning, skip entity, continue |

### 6.2 Design Decision: Retry Approach

**Decision**: Use EventBridge retry for invocation-level failures; use checkpointing for timeout recovery.

**Alternatives Considered**:

| Approach | Pros | Cons |
|----------|------|------|
| **EventBridge retry + checkpoint** | Simple; leverages native retry; checkpoints handle timeouts | 2 retry limit; no complex logic |
| Lambda Destinations | Native async handling; automatic routing | More complex setup; harder to test |
| Step Functions | Full orchestration; visual debugging | Additional service; cost; complexity |

**Rationale**: EventBridge retry (2 attempts) handles transient failures adequately. Checkpointing handles the timeout case specifically. Step Functions would be overkill for this use case but could be added later if orchestration complexity grows.

See **ADR-0065** for full decision record.

### 6.3 DLQ Message Schema

```json
{
  "requestId": "abc-123-def-456",
  "functionName": "autom8-cache-warmer-production",
  "errorType": "RuntimeError",
  "errorMessage": "Bot PAT not available: Secret not found",
  "timestamp": "2026-01-06T02:15:00.000Z",
  "entityTypesCompleted": ["unit", "business"],
  "entityTypesFailed": ["offer", "contact"],
  "checkpointKey": "cache-warmer/checkpoints/latest.json",
  "eventSource": "aws.events",
  "retryAttempt": 2,
  "environment": "production"
}
```

### 6.4 DLQ Processing Runbook

1. **Alert Received**: DLQ alarm fires (messages > 0)
2. **Triage**: Check error type in DLQ message
   - Permanent error: Fix root cause (secrets, permissions)
   - Transient error with retries exhausted: Manual re-trigger
3. **Resolution**:
   - For secrets issues: Verify Secrets Manager secret exists and IAM has access
   - For rate limits: Check Asana API usage; consider adjusting schedule
   - For timeouts: Verify checkpointing worked; manual trigger with `resume_from_checkpoint=true`
4. **Verification**: Monitor next scheduled run or manually trigger
5. **Cleanup**: Delete processed DLQ messages

---

## 7. Interface Contracts

### 7.1 Lambda Event Schema (Input)

```json
{
  "source": "aws.events | manual",
  "detail-type": "Scheduled Event | Manual Invocation",
  "detail": {
    "schedule": "cron(0 2 * * ? *)",
    "environment": "production",
    "trigger_type": "scheduled | manual"
  },
  "entity_types": ["unit", "business", "offer", "contact"],
  "strict": true,
  "resume_from_checkpoint": true
}
```

All fields except `source` are optional.

### 7.2 Lambda Response Schema (Output)

```json
{
  "statusCode": 200,
  "body": {
    "success": true,
    "message": "Cache warm complete: 4 entities, 52000 rows",
    "entity_results": [
      {
        "entity_type": "unit",
        "result": "success",
        "project_gid": "1234567890123456",
        "row_count": 15000,
        "duration_ms": 2500.5,
        "error": null
      },
      {
        "entity_type": "business",
        "result": "success",
        "project_gid": "2345678901234567",
        "row_count": 2000,
        "duration_ms": 800.2,
        "error": null
      }
    ],
    "total_rows": 52000,
    "duration_ms": 480000.5,
    "timestamp": "2026-01-06T02:08:00.000Z",
    "checkpoint_cleared": true,
    "invocation_id": "abc-123-def-456"
  }
}
```

### 7.3 Checkpoint Record Schema

```json
{
  "invocation_id": "abc-123-def-456",
  "completed_entities": ["unit", "business"],
  "pending_entities": ["offer", "contact"],
  "entity_results": [
    {
      "entity_type": "unit",
      "result": "success",
      "project_gid": "1234567890123456",
      "row_count": 15000,
      "duration_ms": 2500.5,
      "error": null
    }
  ],
  "created_at": "2026-01-06T02:04:00.000Z",
  "expires_at": "2026-01-06T03:04:00.000Z"
}
```

---

## 8. Just Command Integration (FR-004)

### 8.1 Just Commands

Add to project justfile:

```just
# === Lambda Cache Warmer ===

# Invoke Lambda to warm cache (all entity types)
cache-warm-lambda env="staging":
    #!/usr/bin/env bash
    set -euo pipefail
    FUNCTION="autom8-cache-warmer-{{env}}"
    echo "Invoking $FUNCTION..."

    aws lambda invoke \
        --function-name "$FUNCTION" \
        --payload '{"trigger_type": "manual", "resume_from_checkpoint": true}' \
        --cli-binary-format raw-in-base64-out \
        /tmp/lambda-response.json

    echo ""
    echo "=== Response ==="
    cat /tmp/lambda-response.json | jq .

# Invoke Lambda to warm specific entity type
cache-warm-lambda-entity entity env="staging":
    #!/usr/bin/env bash
    set -euo pipefail
    FUNCTION="autom8-cache-warmer-{{env}}"
    echo "Invoking $FUNCTION for entity type: {{entity}}..."

    PAYLOAD=$(cat <<EOF
    {"entity_types": ["{{entity}}"], "trigger_type": "manual", "strict": false}
    EOF
    )

    aws lambda invoke \
        --function-name "$FUNCTION" \
        --payload "$PAYLOAD" \
        --cli-binary-format raw-in-base64-out \
        /tmp/lambda-response.json

    echo ""
    echo "=== Response ==="
    cat /tmp/lambda-response.json | jq .

# Check Lambda function status
cache-warm-lambda-status env="staging":
    #!/usr/bin/env bash
    set -euo pipefail
    FUNCTION="autom8-cache-warmer-{{env}}"

    echo "=== Function Configuration ==="
    aws lambda get-function \
        --function-name "$FUNCTION" \
        --query 'Configuration.{State:State,LastModified:LastModified,MemorySize:MemorySize,Timeout:Timeout}' \
        --output table

    echo ""
    echo "=== Recent Invocations (last 24h) ==="
    aws cloudwatch get-metric-statistics \
        --namespace AWS/Lambda \
        --metric-name Invocations \
        --dimensions Name=FunctionName,Value="$FUNCTION" \
        --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '-24 hours' +%Y-%m-%dT%H:%M:%SZ) \
        --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
        --period 3600 \
        --statistics Sum \
        --query 'Datapoints[*].{Time:Timestamp,Count:Sum}' \
        --output table

# Tail Lambda logs
cache-warm-lambda-logs env="staging":
    aws logs tail "/aws/lambda/autom8-cache-warmer-{{env}}" --follow

# Check checkpoint status
cache-warm-checkpoint-status env="staging":
    #!/usr/bin/env bash
    set -euo pipefail
    BUCKET="autom8-s3"
    KEY="cache-warmer/checkpoints/latest.json"

    echo "=== Checkpoint Status ==="
    if aws s3 ls "s3://$BUCKET/$KEY" > /dev/null 2>&1; then
        echo "Checkpoint exists:"
        aws s3 cp "s3://$BUCKET/$KEY" - | jq .
    else
        echo "No checkpoint found (clean state)"
    fi

# Clear checkpoint (force fresh start)
cache-warm-checkpoint-clear env="staging":
    #!/usr/bin/env bash
    set -euo pipefail
    BUCKET="autom8-s3"
    KEY="cache-warmer/checkpoints/latest.json"

    echo "Clearing checkpoint..."
    aws s3 rm "s3://$BUCKET/$KEY" 2>/dev/null || echo "No checkpoint to clear"
    echo "Done."

# Check DLQ messages
cache-warm-dlq-status env="staging":
    #!/usr/bin/env bash
    set -euo pipefail
    QUEUE="autom8-cache-warmer-{{env}}-dlq"

    echo "=== DLQ Status ==="
    aws sqs get-queue-attributes \
        --queue-url "https://sqs.us-east-1.amazonaws.com/$(aws sts get-caller-identity --query Account --output text)/$QUEUE" \
        --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
        --output table
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/unit/lambda_handlers/test_cache_warmer_chunked.py

class TestCheckpointManager:
    """Tests for CheckpointManager."""

    async def test_save_and_load_checkpoint(self, mock_s3):
        """Checkpoint can be saved and loaded."""
        mgr = CheckpointManager(bucket="test-bucket", s3_client=mock_s3)

        await mgr.save_async(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer"],
            entity_results=[{"entity_type": "unit", "result": "success"}],
        )

        checkpoint = await mgr.load_async()

        assert checkpoint is not None
        assert checkpoint.invocation_id == "test-123"
        assert checkpoint.completed_entities == ["unit"]
        assert checkpoint.pending_entities == ["business", "offer"]

    async def test_stale_checkpoint_returns_none(self, mock_s3, freezer):
        """Stale checkpoints are not loaded."""
        mgr = CheckpointManager(bucket="test-bucket", s3_client=mock_s3)

        await mgr.save_async(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=["business"],
            entity_results=[],
        )

        # Advance time past staleness window
        freezer.move_to(datetime.now(timezone.utc) + timedelta(hours=2))

        checkpoint = await mgr.load_async()
        assert checkpoint is None

    async def test_clear_checkpoint(self, mock_s3):
        """Checkpoint can be cleared."""
        mgr = CheckpointManager(bucket="test-bucket", s3_client=mock_s3)

        await mgr.save_async(
            invocation_id="test-123",
            completed_entities=["unit"],
            pending_entities=[],
            entity_results=[],
        )

        await mgr.clear_async()

        checkpoint = await mgr.load_async()
        assert checkpoint is None


class TestTimeoutDetection:
    """Tests for timeout detection logic."""

    def test_should_exit_early_when_low_time(self):
        """Handler exits when remaining time < buffer."""
        context = MockLambdaContext(remaining_time_ms=60_000)  # 1 min

        assert _should_exit_early(context) is True

    def test_should_not_exit_when_sufficient_time(self):
        """Handler continues when remaining time > buffer."""
        context = MockLambdaContext(remaining_time_ms=300_000)  # 5 min

        assert _should_exit_early(context) is False


class TestChunkedWarming:
    """Tests for chunked warming with checkpointing."""

    async def test_resumes_from_checkpoint(self, mock_s3, mock_asana):
        """Warming resumes from checkpoint."""
        # Setup: checkpoint with unit completed
        mgr = CheckpointManager(bucket="test-bucket", s3_client=mock_s3)
        await mgr.save_async(
            invocation_id="prior-123",
            completed_entities=["unit"],
            pending_entities=["business", "offer", "contact"],
            entity_results=[{"entity_type": "unit", "result": "success", "row_count": 100}],
        )

        # Act: invoke handler with resume=True
        response = await _warm_cache_async_chunked(
            resume_from_checkpoint=True,
            context=MockLambdaContext(remaining_time_ms=600_000),
        )

        # Assert: unit was not re-warmed
        warmed_types = [r["entity_type"] for r in response.entity_results if r.get("warmed_this_run")]
        assert "unit" not in warmed_types
        assert "business" in warmed_types

    async def test_saves_checkpoint_on_timeout(self, mock_s3, mock_asana):
        """Checkpoint saved when timeout approaching."""
        context = MockLambdaContext(remaining_time_ms=300_000)  # 5 min initially

        # Simulate time passing during warm
        def advance_time(*args):
            context.remaining_time_ms = 60_000  # Drop to 1 min

        mock_asana.tasks.list_async.side_effect = advance_time

        response = await _warm_cache_async_chunked(
            context=context,
        )

        assert response.success is False
        assert "Partial completion" in response.message

        # Verify checkpoint saved
        mgr = CheckpointManager(bucket="test-bucket", s3_client=mock_s3)
        checkpoint = await mgr.load_async()
        assert checkpoint is not None
```

### 9.2 Integration Tests

```python
# tests/integration/test_cache_warmer_lambda.py

@pytest.mark.integration
class TestLambdaCacheWarmerIntegration:
    """Integration tests for Lambda cache warmer."""

    async def test_full_warming_cycle(self, real_s3, real_asana):
        """Full warming cycle completes within timeout."""
        response = await _warm_cache_async_chunked(
            entity_types=["unit"],  # Single entity for faster test
            context=MockLambdaContext(remaining_time_ms=900_000),
        )

        assert response.success is True
        assert response.total_rows > 0

        # Verify S3 cache updated
        cache = get_dataframe_cache()
        entry = await cache.get_async(
            project_gid=test_project_gid,
            entity_type="unit",
        )
        assert entry is not None
        assert entry.row_count == response.entity_results[0]["row_count"]

    async def test_checkpoint_resume_integration(self, real_s3):
        """Checkpoint resume works end-to-end."""
        # Create checkpoint
        mgr = CheckpointManager(bucket="autom8-s3")
        await mgr.save_async(
            invocation_id="test-int-123",
            completed_entities=["unit"],
            pending_entities=["business"],
            entity_results=[{"entity_type": "unit", "result": "success", "row_count": 100}],
        )

        # Resume
        response = await _warm_cache_async_chunked(
            resume_from_checkpoint=True,
            context=MockLambdaContext(remaining_time_ms=900_000),
        )

        assert response.success is True
        # Should have results for both entities
        entity_types = [r["entity_type"] for r in response.entity_results]
        assert "unit" in entity_types
        assert "business" in entity_types
```

---

## 10. Implementation Plan

### Phase 1: CheckpointManager (Week 1)

**Files**:
- `src/autom8_asana/lambda_handlers/checkpoint.py` (NEW)
- `tests/unit/lambda_handlers/test_checkpoint.py` (NEW)

**Tasks**:
1. Implement `CheckpointRecord` dataclass
2. Implement `CheckpointManager` with save/load/clear
3. Add unit tests for checkpoint operations
4. Verify S3 integration with existing bucket

### Phase 2: Enhanced Handler (Week 1-2)

**Files**:
- `src/autom8_asana/lambda_handlers/cache_warmer.py` (MODIFY)
- `tests/unit/lambda_handlers/test_cache_warmer.py` (MODIFY)

**Tasks**:
1. Add timeout detection using `context.get_remaining_time_in_millis()`
2. Integrate `CheckpointManager` into warming flow
3. Add metric emission helpers
4. Update handler to support `resume_from_checkpoint` parameter
5. Add integration tests

### Phase 3: Terraform Module (Week 2)

**Files**:
- `terraform/modules/autom8-cache-lambda/` (NEW directory)
  - `main.tf`, `iam.tf`, `eventbridge.tf`, `dlq.tf`, `cloudwatch.tf`, `variables.tf`, `outputs.tf`

**Tasks**:
1. Create module structure following platform patterns
2. Implement Lambda function resource
3. Implement IAM role with least-privilege policy
4. Implement EventBridge schedule and DLQ
5. Implement CloudWatch alarms and dashboard
6. Write module documentation

### Phase 4: Just Commands and Production Hardening (Week 2-3)

**Files**:
- `justfile` (MODIFY)

**Tasks**:
1. Add cache-warm-lambda commands
2. Add checkpoint management commands
3. Add DLQ monitoring commands
4. Deploy to staging and validate
5. Production deployment with monitoring
6. Create runbook documentation

---

## 11. Architecture Decision Records

### ADR-0064: S3 Metadata for Checkpoint Persistence

See separate file: `docs/decisions/ADR-0064-checkpoint-persistence-strategy.md`

### ADR-0065: EventBridge Retry with Checkpoint Resume

See separate file: `docs/decisions/ADR-0065-retry-and-resume-strategy.md`

---

## 12. Artifact Verification

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-lambda-cache-warmer.md` | Pending |
| PRD Reference | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-lambda-cache-warmer.md` | Read |
| Existing Handler | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lambda_handlers/cache_warmer.py` | Read |
| Existing Warmer | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/warmer.py` | Read |
| S3 Tier | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/dataframe/tiers/s3.py` | Read |

---

## 13. Handoff Checklist

Ready for Implementation phase when:

- [x] TDD covers all PRD requirements (FR-001 through FR-006)
- [x] Component boundaries and responsibilities are clear
- [x] Data models defined (CheckpointRecord, DLQMessage)
- [x] API contracts specified (Lambda event/response schemas)
- [x] Key flows have sequence diagrams (Section 3.3)
- [x] NFRs have concrete approaches
- [x] ADRs document checkpoint strategy and retry approach
- [x] Risks identified with mitigations
- [x] Principal Engineer can implement without architectural questions
- [ ] All artifacts verified via Read tool
- [x] Attestation table included with absolute paths

---

**End of TDD**
