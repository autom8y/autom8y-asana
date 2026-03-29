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
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from autom8y_config.lambda_extension import resolve_secret_from_env
from autom8y_log import get_logger
from autom8y_telemetry.aws import emit_success_timestamp, instrument_lambda

from autom8_asana.lambda_handlers.cloudwatch import emit_metric
from autom8_asana.lambda_handlers.push_orchestrator import (
    _push_account_status_for_completed_entities,
    _push_gid_mappings_for_completed_entities,
)
from autom8_asana.lambda_handlers.story_warmer import (
    _warm_story_caches_for_completed_entities,
)
from autom8_asana.lambda_handlers.timeout import (
    _self_invoke_continuation,
    _should_exit_early,
)
from autom8_asana.settings import get_settings

logger = get_logger(__name__)

# Dead-man's-switch namespace for Grafana alerting (24h threshold)
DMS_NAMESPACE = "Autom8y/AsanaCacheWarmer"

# Flag to track if bootstrap has run (for lazy initialization)
_bootstrap_initialized = False


def _ensure_bootstrap() -> None:
    """Lazy bootstrap initialization for Lambda cold starts."""
    global _bootstrap_initialized
    if not _bootstrap_initialized:
        try:
            from autom8_asana.models.business._bootstrap import bootstrap

            bootstrap()
            _bootstrap_initialized = True

            # Cross-registry validation (QW-4)
            from autom8_asana.core.registry_validation import (
                validate_cross_registry_consistency,
            )

            validation = validate_cross_registry_consistency(
                check_project_type_registry=True,
                check_entity_project_registry=False,
            )
            if not validation.ok:
                logger.error(
                    "cross_registry_validation_failed",
                    extra={"errors": validation.errors},
                )
        except ImportError as e:
            logger.warning(
                "bootstrap_failed",
                error=str(e),
                impact="Detection may fall through to Tier 5 (unknown)",
            )


async def _run_vertical_backfill(
    *,
    completed_entities: list[str],
    get_project_gid: Any,
    cache: Any,
    client: Any,
    invocation_id: str | None,
) -> None:
    """Run vertical backfill for unit tasks if feature flag is enabled.

    Per remediation-vertical-investigation-spike Option A: backfill
    cf:Vertical for unit tasks with empty vertical values. Guarded by
    ASANA_VERTICAL_BACKFILL_ENABLED environment variable (default: disabled).

    Non-blocking: all exceptions are caught and logged so that backfill
    failures never affect the cache warmer's success status.

    Args:
        completed_entities: Entity types that were successfully warmed.
        get_project_gid: Callable(entity_type) -> project_gid or None.
        cache: DataFrameCache instance for retrieving warmed DataFrames.
        client: Asana client for API calls.
        invocation_id: Lambda invocation ID for log correlation.
    """
    import os

    enabled = os.environ.get("ASANA_VERTICAL_BACKFILL_ENABLED", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not enabled:
        return

    if "unit" not in completed_entities:
        return

    project_gid = get_project_gid("unit")
    if not project_gid:
        return

    try:
        entry = await cache.get_async(project_gid, "unit")
        if entry is None or entry.dataframe is None:
            return

        from autom8_asana.services.vertical_backfill import VerticalBackfillService

        service = VerticalBackfillService(client=client)
        result = await service.backfill_from_dataframe(entry.dataframe)

        logger.info(
            "vertical_backfill_result",
            extra={
                "attempted": result.attempted,
                "succeeded": result.succeeded,
                "skipped": result.skipped,
                "failed": result.failed,
                "invocation_id": invocation_id,
            },
        )

    except Exception as e:  # BROAD-CATCH: isolation -- backfill must never fail cache warmer
        logger.warning(
            "vertical_backfill_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "invocation_id": invocation_id,
            },
        )


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
        bucket=get_settings().s3.bucket or "autom8-s3",
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
        # Try to discover projects using the shared 3-phase discovery service
        try:
            from autom8_asana.services.discovery import discover_entity_projects_async

            await discover_entity_projects_async()
        except (
            Exception
        ) as e:  # BROAD-CATCH: isolation -- discovery failure should not block warming
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

    # Determine entity types to warm.
    # Order derived from cascade dependency graph: providers (business, unit)
    # must warm before consumers (offer, contact, asset_edit, etc.).
    from autom8_asana.dataframes.cascade_utils import cascade_warm_order

    default_priority = cascade_warm_order()
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
            emit_metric("CheckpointResumed", 1)

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

    try:
        workspace_gid = resolve_secret_from_env("ASANA_WORKSPACE_GID")
    except ValueError:
        workspace_gid = None
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
                    emit_metric("CheckpointSaved", 1)

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
                        emit_metric(
                            "WarmSuccess",
                            1,
                            dimensions={"entity_type": entity_type},
                        )
                        emit_metric(
                            "WarmDuration",
                            entity_duration_ms,
                            unit="Milliseconds",
                            dimensions={"entity_type": entity_type},
                        )
                        emit_metric(
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
                        emit_metric(
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
                            emit_metric("CheckpointSaved", 1)

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
                        emit_metric("CheckpointSaved", 1)

                except Exception as e:  # BROAD-CATCH: isolation -- per-entity-type loop, single failure must not abort batch
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

                    emit_metric(
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
                        emit_metric("CheckpointSaved", 1)
                        raise

        # All entities completed - clear checkpoint
        checkpoint_cleared = await checkpoint_mgr.clear_async()

        # ----------------------------------------------------------------
        # GID mapping push
        # After warming completes, push GID mappings to autom8_data for
        # each successfully warmed entity type. Non-blocking: failures are
        # logged but do not affect the cache warmer's success status.
        # ----------------------------------------------------------------
        await _push_gid_mappings_for_completed_entities(
            completed_entities=completed_entities,
            get_project_gid=get_project_gid,
            cache=cache,
            invocation_id=invocation_id,
        )

        # ----------------------------------------------------------------
        # Account status push
        # After GID push, extract account status classifications from
        # warmed DataFrames and push to autom8_data. Non-blocking:
        # failures are logged but do not affect the cache warmer result.
        # ----------------------------------------------------------------
        try:
            await _push_account_status_for_completed_entities(
                completed_entities=completed_entities,
                get_project_gid=get_project_gid,
                cache=cache,
                invocation_id=invocation_id,
            )
        except Exception as e:  # BROAD-CATCH: isolation -- status push must never fail cache warmer
            logger.error(
                "status_push_fatal_error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "invocation_id": invocation_id,
                },
            )

        # ----------------------------------------------------------------
        # Story cache warming (Strategy E: piggyback on DataFrame warmer)
        # After DataFrame warming and GID push, populate story caches for
        # each task GID found in warmed DataFrames. Non-blocking: failures
        # are logged but do not affect the cache warmer's success status.
        # ----------------------------------------------------------------
        await _warm_story_caches_for_completed_entities(
            completed_entities=completed_entities,
            get_project_gid=get_project_gid,
            dataframe_cache=cache,
            client=client,
            invocation_id=invocation_id,
            context=context,
        )

        # ----------------------------------------------------------------
        # Vertical custom field backfill (Option A from P1-E spike)
        # After warming completes, backfill cf:Vertical for unit tasks
        # that have empty vertical values. Feature-flagged via
        # ASANA_VERTICAL_BACKFILL_ENABLED env var (default: disabled).
        # Non-blocking: failures are logged but do not affect the cache
        # warmer's success status.
        # ----------------------------------------------------------------
        await _run_vertical_backfill(
            completed_entities=completed_entities,
            get_project_gid=get_project_gid,
            cache=cache,
            client=client,
            invocation_id=invocation_id,
        )

        total_rows = sum(r.get("row_count", 0) for r in entity_results)
        duration_ms = (time.monotonic() - start_time) * 1000

        # Emit total duration metric
        emit_metric("TotalDuration", duration_ms, unit="Milliseconds")

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

    except Exception as e:  # BROAD-CATCH: boundary -- async function top-level catch, returns error response
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


@instrument_lambda
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
    # Lazy bootstrap to avoid import chain failures
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
    except Exception as e:  # BROAD-CATCH: boundary -- Lambda handler top-level catch
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

    # Dead-man's-switch: record successful completion timestamp.
    # A Grafana alert fires when this metric is absent or stale >24h.
    if response.success:
        emit_success_timestamp(DMS_NAMESPACE)

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
    # Lazy bootstrap to avoid import chain failures
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
