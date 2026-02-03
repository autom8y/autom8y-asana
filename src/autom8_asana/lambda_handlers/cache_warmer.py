"""Lambda handler for cache warming.

Per TDD-DATAFRAME-CACHE-001 Section 5.7 and TDD-lambda-cache-warmer Section 3.6:
Lambda warm-up handler for pre-deployment cache hydration with timeout detection,
checkpoint-based resume capability, and CloudWatch metric emission.

This module provides:
- handler: AWS Lambda entry point for cache warming
- handler_async: Async Lambda entry point for direct async invocation
- WarmResponse: Response dataclass for Lambda returns
- Timeout detection via _should_exit_early()
- Checkpoint integration for resume-on-retry
- CloudWatch metric emission for observability

Environment Variables Required:
    ASANA_PAT: Asana Personal Access Token
    ASANA_CACHE_S3_BUCKET: S3 bucket for cache storage
    ASANA_CACHE_S3_PREFIX: S3 key prefix (optional, default: "cache/")
    ENVIRONMENT: Deployment environment (staging/production)
    CLOUDWATCH_NAMESPACE: CloudWatch namespace (default: "autom8/cache-warmer")

Usage:
    Deploy as AWS Lambda function with handler:
    autom8_asana.lambda_handlers.cache_warmer.handler

    Invoke with optional event parameters:
    {
        "entity_types": ["unit", "offer"],  // Optional, defaults to all
        "strict": true,                      // Optional, default true
        "resume_from_checkpoint": true       // Optional, default true
    }
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import inflection
from autom8y_log import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Flag to track if bootstrap has run (for lazy initialization)
_bootstrap_initialized = False


def _ensure_bootstrap() -> None:
    """Lazy bootstrap initialization for Lambda cold starts.

    HOTFIX: Moved from module-level import to avoid import chain failures
    when autom8y_cache has missing modules. The bootstrap populates
    ProjectTypeRegistry for Tier 1 detection.
    """
    global _bootstrap_initialized
    if not _bootstrap_initialized:
        try:
            import autom8_asana.models.business  # noqa: F401 - side effect import

            _bootstrap_initialized = True
            logger.info("bootstrap_complete", detail="ProjectTypeRegistry populated")
        except ImportError as e:
            logger.warning(
                "bootstrap_failed",
                error=str(e),
                impact="Detection may fall through to Tier 5 (unknown)",
            )


# ============================================================================
# Constants (per TDD-lambda-cache-warmer Section 3.2)
# ============================================================================

# Timeout buffer: exit 2 minutes before Lambda timeout (per PRD FR-001)
TIMEOUT_BUFFER_MS = 120_000

# CloudWatch namespace for cache warmer metrics
CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_NAMESPACE", "autom8/cache-warmer")

# Environment for metric dimensions
ENVIRONMENT = os.environ.get("ENVIRONMENT", "staging")

# Lazy-initialized CloudWatch client
_cloudwatch_client: Any = None


@dataclass
class WarmResponse:
    """Response from cache warming Lambda.

    Per TDD-DATAFRAME-CACHE-001 and TDD-lambda-cache-warmer: Structured response
    for Lambda invocation with detailed status per entity type, checkpoint status,
    and invocation correlation.

    Attributes:
        success: Overall success status (all entity types warmed).
        message: Human-readable summary.
        entity_results: Per-entity-type warming results.
        total_rows: Total rows warmed across all entity types.
        duration_ms: Total execution time in milliseconds.
        timestamp: ISO timestamp of completion.
        checkpoint_cleared: Whether checkpoint was cleared after successful completion.
        invocation_id: Lambda request ID for correlation (if available).
    """

    success: bool
    message: str
    entity_results: list[dict[str, Any]] = field(default_factory=list)
    total_rows: int = 0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    checkpoint_cleared: bool = False
    invocation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Lambda response.

        Returns:
            Dictionary suitable for JSON serialization.
        """
        return {
            "success": self.success,
            "message": self.message,
            "entity_results": self.entity_results,
            "total_rows": self.total_rows,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "checkpoint_cleared": self.checkpoint_cleared,
            "invocation_id": self.invocation_id,
        }


# ============================================================================
# Timeout Detection (per TDD-lambda-cache-warmer Section 3.2)
# ============================================================================


def _should_exit_early(context: Any) -> bool:
    """Check if we should exit to avoid Lambda timeout.

    Per TDD-lambda-cache-warmer: Monitors context.get_remaining_time_in_millis()
    and signals exit when remaining time falls below TIMEOUT_BUFFER_MS (2 minutes).

    Args:
        context: Lambda context with get_remaining_time_in_millis() method.
            May be None in test or non-Lambda environments.

    Returns:
        True if remaining time < TIMEOUT_BUFFER_MS, False otherwise.
        Returns False if context is None (no timeout enforcement).
    """
    if context is None:
        return False

    try:
        remaining_ms: int = context.get_remaining_time_in_millis()
        return bool(remaining_ms < TIMEOUT_BUFFER_MS)
    except AttributeError:
        # Context doesn't have the method (e.g., mock without it)
        return False


# ============================================================================
# CloudWatch Metric Emission (per TDD-lambda-cache-warmer Section 5.2)
# ============================================================================


def _get_cloudwatch_client() -> Any:
    """Lazily initialize CloudWatch client.

    Uses module-level caching to avoid repeated client creation.

    Returns:
        boto3 CloudWatch client.
    """
    global _cloudwatch_client
    if _cloudwatch_client is None:
        import boto3

        _cloudwatch_client = boto3.client("cloudwatch")
    return _cloudwatch_client


def _emit_metric(
    metric_name: str,
    value: float,
    unit: str = "Count",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit CloudWatch metric with graceful degradation.

    Per TDD-lambda-cache-warmer Section 5.2: Emits metrics to the
    CLOUDWATCH_NAMESPACE with environment dimension always included.

    Args:
        metric_name: Name of the metric (e.g., "WarmSuccess", "WarmDuration").
        value: Metric value.
        unit: CloudWatch unit (Count, Milliseconds, etc.).
        dimensions: Optional additional dimensions (e.g., {"entity_type": "unit"}).

    Note:
        Failures are logged as warnings but do not raise exceptions.
        Per ADR-0064: CloudWatch errors should not block warming.
    """
    client = _get_cloudwatch_client()

    # Build dimensions list with environment always first
    metric_dimensions = [
        {"Name": "environment", "Value": ENVIRONMENT},
    ]

    if dimensions:
        for dim_name, dim_value in dimensions.items():
            metric_dimensions.append({"Name": dim_name, "Value": dim_value})

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
        # Graceful degradation: log warning but don't fail the warm
        logger.warning(
            "metric_emit_error",
            extra={
                "metric": metric_name,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


def _self_invoke_continuation(
    context: Any,
    pending_entities: list[str],
    parent_invocation_id: str,
) -> None:
    """Self-invoke Lambda with remaining entities for continuation.

    Uses context.invoked_function_arn to get own ARN.
    Fires asynchronously (InvocationType=Event) so current invocation
    can return cleanly.
    """
    if not pending_entities:
        return

    function_arn = getattr(context, "invoked_function_arn", None)
    if not function_arn:
        logger.warning(
            "self_invoke_no_arn",
            extra={"parent_invocation_id": parent_invocation_id},
        )
        return

    import json

    import boto3

    payload = {
        "entity_types": pending_entities,
        "strict": False,
        "resume_from_checkpoint": True,
    }
    try:
        client = boto3.client("lambda")
        client.invoke(
            FunctionName=function_arn,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        logger.info(
            "self_invoke_continuation",
            extra={
                "function_arn": function_arn,
                "pending_entities": pending_entities,
                "parent_invocation_id": parent_invocation_id,
            },
        )
        _emit_metric("SelfContinuationInvoked", 1)
    except Exception as e:
        logger.error(
            "self_invoke_failed",
            extra={
                "error": str(e),
                "parent_invocation_id": parent_invocation_id,
            },
        )


async def _discover_entity_projects_for_lambda() -> None:
    """Discover and register entity type project mappings for Lambda.

    Standalone discovery function for Lambda environment that replicates
    the discovery logic from api/main.py without FastAPI dependencies.

    Raises:
        RuntimeError: If discovery fails critically.
    """
    import os

    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat

    # Per TDD-registry-consolidation: Import from package to ensure bootstrap runs
    from autom8_asana.models.business import get_workspace_registry
    from autom8_asana.services.resolver import EntityProjectRegistry

    # Get bot PAT for S2S Asana access
    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.warning(
            "lambda_discovery_no_bot_pat",
            extra={"error": str(e)},
        )
        raise RuntimeError(f"Bot PAT not available: {e}") from e

    # Get workspace GID from environment
    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")

    if not workspace_gid:
        logger.warning("lambda_discovery_no_workspace")
        raise RuntimeError("ASANA_WORKSPACE_GID not set")

    async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
        # Use existing WorkspaceProjectRegistry discovery
        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(client)

        # Map discovered projects to entity resolver registry
        entity_registry = EntityProjectRegistry.get_instance()

        # Known entity types to discover
        entity_types_to_discover: list[str] = [
            "unit",
            "business",
            "offer",
            "contact",
            "asset_edit",
            "asset_edit_holder",
        ]

        # Match projects to entity types via normalized name matching
        for project_name, project_gid in workspace_registry.get_all_projects().items():
            entity_type = _match_entity_type(project_name, entity_types_to_discover)
            if entity_type:
                entity_registry.register(
                    entity_type=entity_type,
                    project_gid=project_gid,
                    project_name=project_name,
                )
                logger.info(
                    "lambda_entity_project_registered",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "project_name": project_name,
                    },
                )

        # Fallback: use PRIMARY_PROJECT_GID from model classes for unmatched entities
        from autom8_asana.services.discovery import ENTITY_MODEL_MAP

        for et in entity_types_to_discover:
            if entity_registry.get_project_gid(et) is None:
                model_cls = ENTITY_MODEL_MAP.get(et)
                gid = getattr(model_cls, "PRIMARY_PROJECT_GID", None) if model_cls else None
                if gid:
                    entity_registry.register(
                        entity_type=et,
                        project_gid=gid,
                        project_name=f"{et} (model fallback)",
                    )
                    logger.info(
                        "lambda_entity_project_registered_fallback",
                        extra={
                            "entity_type": et,
                            "project_gid": gid,
                            "source": "PRIMARY_PROJECT_GID",
                        },
                    )

        logger.info(
            "lambda_entity_discovery_complete",
            extra={
                "registered_types": entity_registry.get_all_entity_types(),
            },
        )


# Override map for non-standard project names (exact match, case-insensitive)
# Maps project names that don't follow convention to their entity types
ENTITY_OVERRIDES: dict[str, str] = {
    "business offers": "offer",
    "business units": "unit",
    "paid content": "asset_edit",
    "units": "unit_holder",  # Maps correctly, but unit_holder not in WARMABLE_ENTITIES
}

# Valid entity types in priority order for cache warming
# Only these entity types will be returned by _normalize_project_name
WARMABLE_ENTITIES: list[str] = ["offer", "business", "contact", "unit", "asset_edit", "asset_edit_holder"]


def _normalize_project_name(name: str) -> str | None:
    """Map project name to entity type using convention + overrides.

    Uses a two-step algorithm:
    1. Check explicit overrides first (exact match, case-insensitive)
    2. Singularize project name using inflection (Rails port)

    Only returns entity types that are in WARMABLE_ENTITIES. This ensures
    workflow projects like "pause a business unit" are NOT mapped to any
    entity type (they don't match overrides and singularization won't produce
    a valid warmable entity).

    Args:
        name: Project name to normalize.

    Returns:
        Entity type string if valid and warmable, None if no match.
    """
    normalized = name.lower().strip()

    # 1. Check overrides first (exact match)
    if normalized in ENTITY_OVERRIDES:
        entity_type = ENTITY_OVERRIDES[normalized]
        # Only return if it's warmable
        if entity_type in WARMABLE_ENTITIES:
            return entity_type
        return None

    # 2. Singularize using inflection (Rails port - handles edge cases correctly)
    singular = inflection.singularize(normalized)

    # 3. Return only if it's a valid warmable entity
    if singular in WARMABLE_ENTITIES:
        return singular

    return None


def _match_entity_type(project_name: str, entity_types: list[str]) -> str | None:
    """Match a project name to an entity type.

    Args:
        project_name: Project name to match.
        entity_types: List of valid entity type identifiers.

    Returns:
        Matched entity type or None if no match.
    """
    normalized = _normalize_project_name(project_name)
    if normalized is not None and normalized in entity_types:
        return normalized
    return None


async def _warm_cache_async(
    entity_types: list[str] | None = None,
    strict: bool = True,
    resume_from_checkpoint: bool = True,
    context: Any = None,
) -> WarmResponse:
    """Async implementation of cache warming with checkpoint support.

    Per TDD-lambda-cache-warmer Section 3.6: Enhanced cache warming with
    timeout detection, checkpoint-based resume capability, and CloudWatch
    metric emission.

    Args:
        entity_types: Optional list of entity types to warm.
            Defaults to all types: ["unit", "business", "offer", "contact",
            "asset_edit", "asset_edit_holder"]
        strict: If True, fail on any entity type warm failure.
        resume_from_checkpoint: If True, resume from last checkpoint if available.
        context: Lambda context for timeout detection and correlation ID.
            Should have get_remaining_time_in_millis() and aws_request_id.

    Returns:
        WarmResponse with detailed results, checkpoint status, and invocation ID.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.cache.dataframe.factory import (
        get_dataframe_cache,
        initialize_dataframe_cache,
    )
    from autom8_asana.cache.dataframe.warmer import (
        CacheWarmer,
        WarmResult,
    )
    from autom8_asana.lambda_handlers.checkpoint import CheckpointManager
    from autom8_asana.services.resolver import EntityProjectRegistry

    start_time = time.monotonic()

    # Extract invocation ID from context or generate UUID
    invocation_id = getattr(context, "aws_request_id", None) or str(uuid.uuid4())

    # Initialize checkpoint manager
    checkpoint_mgr = CheckpointManager(
        bucket=os.environ.get("ASANA_CACHE_S3_BUCKET", "autom8-s3"),
    )

    # Initialize DataFrameCache if not already done
    cache = get_dataframe_cache()
    if cache is None:
        cache = initialize_dataframe_cache()

    if cache is None:
        return WarmResponse(
            success=False,
            message="Failed to initialize DataFrameCache. Check S3 configuration.",
            duration_ms=(time.monotonic() - start_time) * 1000,
            invocation_id=invocation_id,
        )

    # Get EntityProjectRegistry
    registry = EntityProjectRegistry.get_instance()
    if not registry.is_ready():
        # Try to discover projects
        try:
            await _discover_entity_projects_for_lambda()
        except Exception as e:
            logger.warning(
                "cache_warmer_discovery_failed",
                extra={"error": str(e), "invocation_id": invocation_id},
            )

    if not registry.is_ready():
        return WarmResponse(
            success=False,
            message="EntityProjectRegistry not initialized. No projects discovered.",
            duration_ms=(time.monotonic() - start_time) * 1000,
            invocation_id=invocation_id,
        )

    # Determine entity types to warm - note: per TDD priority order is unit first
    default_priority = [
        "unit",
        "business",
        "offer",
        "contact",
        "asset_edit",
        "asset_edit_holder",
    ]
    if entity_types:
        # Validate entity types
        valid_types = set(default_priority)
        invalid = set(entity_types) - valid_types
        if invalid:
            return WarmResponse(
                success=False,
                message=f"Invalid entity types: {invalid}. Valid types: {valid_types}",
                duration_ms=(time.monotonic() - start_time) * 1000,
                invocation_id=invocation_id,
            )
        processing_list = entity_types
    else:
        processing_list = default_priority

    # Track completed entities and results (may be populated from checkpoint)
    completed_entities: list[str] = []
    entity_results: list[dict[str, Any]] = []

    # Check for existing checkpoint if resume is enabled
    if resume_from_checkpoint:
        checkpoint = await checkpoint_mgr.load_async()
        if checkpoint:
            completed_entities = checkpoint.completed_entities
            entity_results = checkpoint.entity_results
            # Only process pending entities
            processing_list = checkpoint.pending_entities

            logger.info(
                "resuming_from_checkpoint",
                extra={
                    "prior_invocation": checkpoint.invocation_id,
                    "completed": completed_entities,
                    "pending": processing_list,
                    "invocation_id": invocation_id,
                },
            )

            # Emit checkpoint resumed metric
            _emit_metric("CheckpointResumed", 1)

    # Get Asana client credentials
    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        return WarmResponse(
            success=False,
            message=f"Failed to get bot PAT: {e}",
            duration_ms=(time.monotonic() - start_time) * 1000,
            invocation_id=invocation_id,
        )

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
    if not workspace_gid:
        return WarmResponse(
            success=False,
            message="ASANA_WORKSPACE_GID environment variable not set",
            duration_ms=(time.monotonic() - start_time) * 1000,
            invocation_id=invocation_id,
        )

    # Define project GID provider using EntityProjectRegistry
    def get_project_gid(entity_type: str) -> str | None:
        return registry.get_project_gid(entity_type)

    # Create warmer - use strict=False for checkpoint granularity, handle failures individually
    warmer = CacheWarmer(
        cache=cache,
        priority=processing_list,
        strict=False,  # Handle failures individually for checkpointing
    )

    # Execute warming with async context manager for client
    try:
        async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
            # Process entity types sequentially for checkpoint granularity
            for entity_type in processing_list:
                # Check timeout before processing
                if _should_exit_early(context):
                    remaining_ms = (
                        context.get_remaining_time_in_millis() if context else 0
                    )
                    logger.warning(
                        "exiting_early_timeout",
                        extra={
                            "remaining_ms": remaining_ms,
                            "completed": completed_entities,
                            "pending": [
                                et
                                for et in processing_list
                                if et not in completed_entities
                            ],
                            "invocation_id": invocation_id,
                        },
                    )

                    # Save checkpoint before exit
                    pending = [
                        et for et in processing_list if et not in completed_entities
                    ]
                    await checkpoint_mgr.save_async(
                        invocation_id=invocation_id,
                        completed_entities=completed_entities,
                        pending_entities=pending,
                        entity_results=entity_results,
                    )
                    _emit_metric("CheckpointSaved", 1)

                    # Self-invoke with remaining entities
                    _self_invoke_continuation(context, pending, invocation_id)

                    return WarmResponse(
                        success=False,
                        message=f"Partial completion, self-continuing. Completed: {completed_entities}, Pending: {pending}",
                        entity_results=entity_results,
                        total_rows=sum(r.get("row_count", 0) for r in entity_results),
                        duration_ms=(time.monotonic() - start_time) * 1000,
                        invocation_id=invocation_id,
                    )

                # Warm this entity type
                entity_start = time.monotonic()
                try:
                    status = await warmer.warm_entity_async(
                        entity_type=entity_type,
                        client=client,
                        project_gid_provider=get_project_gid,
                    )

                    entity_results.append(status.to_dict())
                    entity_duration_ms = (time.monotonic() - entity_start) * 1000

                    if status.result == WarmResult.SUCCESS:
                        completed_entities.append(entity_type)

                        # NOTE: Previously (TDD-cache-freshness-remediation
                        # Fix 2) we deleted the manifest here so ECS would
                        # do a "fresh build" on restart.  This caused a
                        # fundamental flaw: ECS preload found no manifest,
                        # could not resume from sections, and either OOM'd
                        # doing a full API fetch or delegated to Lambda —
                        # leaving the container with an empty in-memory
                        # cache (503).  Staleness is now handled by the
                        # watermark freshness check in the preload path
                        # (Fix 3), so we preserve manifests for resumption.
                        project_gid = get_project_gid(entity_type)
                        if project_gid:
                            logger.info(
                                "manifest_preserved_after_warm",
                                extra={
                                    "entity_type": entity_type,
                                    "project_gid": project_gid,
                                    "invocation_id": invocation_id,
                                },
                            )

                        # Emit success metrics
                        _emit_metric(
                            "WarmSuccess",
                            1,
                            dimensions={"entity_type": entity_type},
                        )
                        _emit_metric(
                            "WarmDuration",
                            entity_duration_ms,
                            unit="Milliseconds",
                            dimensions={"entity_type": entity_type},
                        )
                        _emit_metric(
                            "RowsWarmed",
                            status.row_count,
                            dimensions={"entity_type": entity_type},
                        )

                        logger.info(
                            "entity_warm_success",
                            extra={
                                "entity_type": entity_type,
                                "row_count": status.row_count,
                                "duration_ms": entity_duration_ms,
                                "invocation_id": invocation_id,
                            },
                        )
                    else:
                        # Failure for this entity
                        _emit_metric(
                            "WarmFailure",
                            1,
                            dimensions={"entity_type": entity_type},
                        )

                        logger.warning(
                            "entity_warm_failure",
                            extra={
                                "entity_type": entity_type,
                                "error": status.error,
                                "invocation_id": invocation_id,
                            },
                        )

                        if strict:
                            # Save checkpoint and exit
                            pending = [
                                et
                                for et in processing_list
                                if et not in completed_entities
                            ]
                            await checkpoint_mgr.save_async(
                                invocation_id=invocation_id,
                                completed_entities=completed_entities,
                                pending_entities=pending,
                                entity_results=entity_results,
                            )
                            _emit_metric("CheckpointSaved", 1)

                            return WarmResponse(
                                success=False,
                                message=f"Failed on {entity_type}: {status.error}",
                                entity_results=entity_results,
                                total_rows=sum(
                                    r.get("row_count", 0) for r in entity_results
                                ),
                                duration_ms=(time.monotonic() - start_time) * 1000,
                                invocation_id=invocation_id,
                            )

                    # Save checkpoint after each entity (if more pending)
                    pending = [
                        et for et in processing_list if et not in completed_entities
                    ]
                    if pending:
                        await checkpoint_mgr.save_async(
                            invocation_id=invocation_id,
                            completed_entities=completed_entities,
                            pending_entities=pending,
                            entity_results=entity_results,
                        )
                        _emit_metric("CheckpointSaved", 1)

                except Exception as e:
                    logger.error(
                        "entity_warm_exception",
                        extra={
                            "entity_type": entity_type,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "invocation_id": invocation_id,
                        },
                    )

                    entity_results.append(
                        {
                            "entity_type": entity_type,
                            "result": "failure",
                            "error": str(e),
                        }
                    )

                    _emit_metric(
                        "WarmFailure",
                        1,
                        dimensions={"entity_type": entity_type},
                    )

                    if strict:
                        pending = [
                            et for et in processing_list if et not in completed_entities
                        ]
                        await checkpoint_mgr.save_async(
                            invocation_id=invocation_id,
                            completed_entities=completed_entities,
                            pending_entities=pending,
                            entity_results=entity_results,
                        )
                        _emit_metric("CheckpointSaved", 1)
                        raise

        # All entities completed - clear checkpoint
        checkpoint_cleared = await checkpoint_mgr.clear_async()

        total_rows = sum(r.get("row_count", 0) for r in entity_results)
        duration_ms = (time.monotonic() - start_time) * 1000

        # Emit total duration metric
        _emit_metric("TotalDuration", duration_ms, unit="Milliseconds")

        # Count successes/failures for message
        success_count = sum(1 for r in entity_results if r.get("result") == "success")
        failure_count = sum(1 for r in entity_results if r.get("result") == "failure")
        skipped_count = sum(1 for r in entity_results if r.get("result") == "skipped")

        all_success = failure_count == 0 and skipped_count == 0

        if all_success:
            message = f"Cache warm complete: {success_count} entity types warmed, {total_rows} total rows"
        else:
            message = (
                f"Cache warm finished: {success_count} success, "
                f"{failure_count} failed, {skipped_count} skipped"
            )

        return WarmResponse(
            success=all_success,
            message=message,
            entity_results=entity_results,
            total_rows=total_rows,
            duration_ms=duration_ms,
            checkpoint_cleared=checkpoint_cleared,
            invocation_id=invocation_id,
        )

    except Exception as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.error(
            "cache_warmer_handler_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": duration_ms,
                "invocation_id": invocation_id,
            },
        )

        return WarmResponse(
            success=False,
            message=f"Cache warm failed: {e}",
            duration_ms=duration_ms,
            invocation_id=invocation_id,
        )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for cache warming.

    Per TDD-DATAFRAME-CACHE-001 and TDD-lambda-cache-warmer: Entry point for AWS
    Lambda invocation. Warms all configured entity types in priority order with
    timeout detection and checkpoint-based resume capability.

    Args:
        event: Lambda event with optional configuration:
            - entity_types (list[str]): Optional list of entity types to warm.
                Defaults to ["unit", "business", "offer", "contact"].
            - strict (bool): If True, fail on any entity type failure.
                Defaults to True.
            - resume_from_checkpoint (bool): If True, resume from last checkpoint
                if available. Defaults to True.
        context: Lambda context with get_remaining_time_in_millis() and aws_request_id.

    Returns:
        Dictionary with warming results:
            - statusCode (int): HTTP status code (200 for success, 500 for failure)
            - body (dict): WarmResponse as dictionary

    Example Event:
        {
            "entity_types": ["unit", "offer"],
            "strict": false,
            "resume_from_checkpoint": true
        }

    Example Response:
        {
            "statusCode": 200,
            "body": {
                "success": true,
                "message": "Cache warm complete: 2 entity types warmed, 15000 total rows",
                "entity_results": [
                    {"entity_type": "unit", "result": "success", "row_count": 10000, ...},
                    {"entity_type": "offer", "result": "success", "row_count": 5000, ...}
                ],
                "total_rows": 15000,
                "duration_ms": 4500.5,
                "timestamp": "2026-01-06T12:00:00+00:00",
                "checkpoint_cleared": true,
                "invocation_id": "abc-123-def-456"
            }
        }

    Environment Variables:
        ASANA_PAT: Asana Personal Access Token (required)
        ASANA_CACHE_S3_BUCKET: S3 bucket for cache storage (required)
        ASANA_CACHE_S3_PREFIX: S3 key prefix (optional)
        ENVIRONMENT: Deployment environment for metrics (optional)
        CLOUDWATCH_NAMESPACE: CloudWatch namespace (optional)
    """
    # HOTFIX: Lazy bootstrap to avoid import chain failures
    _ensure_bootstrap()

    # Extract invocation ID for logging correlation
    invocation_id = getattr(context, "aws_request_id", None)

    logger.info(
        "cache_warmer_handler_invoked",
        extra={
            "event": event,
            "has_context": context is not None,
            "invocation_id": invocation_id,
        },
    )

    # Parse event parameters
    entity_types = event.get("entity_types")
    strict = event.get("strict", True)
    resume_from_checkpoint = event.get("resume_from_checkpoint", True)

    # Run async warming with context for timeout detection
    try:
        response = asyncio.run(
            _warm_cache_async(
                entity_types=entity_types,
                strict=strict,
                resume_from_checkpoint=resume_from_checkpoint,
                context=context,
            )
        )
    except Exception as e:
        logger.error(
            "cache_warmer_handler_exception",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "invocation_id": invocation_id,
            },
        )
        response = WarmResponse(
            success=False,
            message=f"Handler exception: {e}",
            invocation_id=invocation_id,
        )

    # Return Lambda response format
    status_code = 200 if response.success else 500

    return {
        "statusCode": status_code,
        "body": response.to_dict(),
    }


async def handler_async(
    event: dict[str, Any],
    context: Any = None,
) -> dict[str, Any]:
    """Async Lambda handler for direct async invocation.

    Alternative entry point for environments that support async handlers
    or for testing purposes. Supports the same parameters as handler().

    Args:
        event: Lambda event with optional configuration:
            - entity_types (list[str]): Optional list of entity types to warm.
            - strict (bool): If True, fail on any entity type failure.
            - resume_from_checkpoint (bool): If True, resume from checkpoint.
        context: Lambda context with get_remaining_time_in_millis() and aws_request_id.

    Returns:
        Same format as handler().
    """
    # HOTFIX: Lazy bootstrap to avoid import chain failures
    _ensure_bootstrap()

    invocation_id = getattr(context, "aws_request_id", None)

    logger.info(
        "cache_warmer_handler_async_invoked",
        extra={
            "event": event,
            "invocation_id": invocation_id,
        },
    )

    entity_types = event.get("entity_types")
    strict = event.get("strict", True)
    resume_from_checkpoint = event.get("resume_from_checkpoint", True)

    response = await _warm_cache_async(
        entity_types=entity_types,
        strict=strict,
        resume_from_checkpoint=resume_from_checkpoint,
        context=context,
    )

    status_code = 200 if response.success else 500

    return {
        "statusCode": status_code,
        "body": response.to_dict(),
    }
