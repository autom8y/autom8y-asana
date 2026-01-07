"""Lambda handler for cache invalidation.

Per TDD-DETECTION-FIX: Provides mechanism to clear stale cached task data
that may be missing required fields (like memberships for Tier 1 detection).

This module provides:
- handler: AWS Lambda entry point for cache invalidation
- handler_async: Async Lambda entry point for direct async invocation
- InvalidateResponse: Response dataclass for Lambda returns

Usage:
    Deploy as AWS Lambda function with handler:
    autom8_asana.lambda_handlers.cache_invalidate.handler

    Invoke with optional event parameters:
    {
        "clear_tasks": true,      // Clear task cache (default: true)
        "clear_dataframes": false // Clear dataframe cache (default: false)
    }

Environment Variables Required:
    ASANA_CACHE_S3_BUCKET: S3 bucket for cache storage
    ASANA_CACHE_S3_PREFIX: S3 key prefix (optional, default: "asana-cache")
    REDIS_HOST: Redis host for hot tier cache
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class InvalidateResponse:
    """Response from cache invalidation Lambda.

    Attributes:
        success: Overall success status.
        message: Human-readable summary.
        tasks_cleared: Dict with Redis/S3 task counts cleared.
        dataframes_cleared: Count of dataframe entries cleared.
        duration_ms: Total execution time in milliseconds.
        timestamp: ISO timestamp of completion.
        invocation_id: Lambda request ID for correlation.
    """

    success: bool
    message: str
    tasks_cleared: dict[str, int] = field(default_factory=dict)
    dataframes_cleared: int = 0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    invocation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Lambda response."""
        return {
            "success": self.success,
            "message": self.message,
            "tasks_cleared": self.tasks_cleared,
            "dataframes_cleared": self.dataframes_cleared,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
            "invocation_id": self.invocation_id,
        }


async def _invalidate_cache_async(
    clear_tasks: bool = True,
    clear_dataframes: bool = False,
    context: Any = None,
) -> InvalidateResponse:
    """Async implementation of cache invalidation.

    Args:
        clear_tasks: If True, clear all task cache entries.
        clear_dataframes: If True, clear dataframe cache entries.
        context: Lambda context for correlation ID.

    Returns:
        InvalidateResponse with detailed results.
    """
    from autom8_asana.cache.tiered import TieredCacheProvider

    start_time = time.monotonic()
    invocation_id = getattr(context, "aws_request_id", None) or str(uuid.uuid4())

    tasks_cleared: dict[str, int] = {"redis": 0, "s3": 0}
    dataframes_cleared = 0

    try:
        if clear_tasks:
            # Initialize tiered cache provider
            cache = TieredCacheProvider()

            logger.info(
                "cache_invalidate_starting",
                extra={
                    "clear_tasks": clear_tasks,
                    "clear_dataframes": clear_dataframes,
                    "invocation_id": invocation_id,
                },
            )

            # Clear task cache
            tasks_cleared = cache.clear_all_tasks()

        if clear_dataframes:
            # Clear dataframe cache if requested
            from autom8_asana.cache.dataframe.factory import get_dataframe_cache

            df_cache = get_dataframe_cache()
            if df_cache is not None:
                # Dataframe cache doesn't have clear_all, use schema version bump
                df_cache.invalidate_on_schema_change(f"invalidate-{invocation_id}")
                dataframes_cleared = 1  # Approximate - entire memory tier cleared

        duration_ms = (time.monotonic() - start_time) * 1000

        total_cleared = tasks_cleared["redis"] + tasks_cleared["s3"] + dataframes_cleared
        message = f"Cache invalidation complete: {tasks_cleared['redis']} Redis keys, {tasks_cleared['s3']} S3 objects cleared"

        logger.info(
            "cache_invalidate_complete",
            extra={
                "tasks_cleared": tasks_cleared,
                "dataframes_cleared": dataframes_cleared,
                "duration_ms": duration_ms,
                "invocation_id": invocation_id,
            },
        )

        return InvalidateResponse(
            success=True,
            message=message,
            tasks_cleared=tasks_cleared,
            dataframes_cleared=dataframes_cleared,
            duration_ms=duration_ms,
            invocation_id=invocation_id,
        )

    except Exception as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.error(
            "cache_invalidate_failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": duration_ms,
                "invocation_id": invocation_id,
            },
        )

        return InvalidateResponse(
            success=False,
            message=f"Cache invalidation failed: {e}",
            tasks_cleared=tasks_cleared,
            dataframes_cleared=dataframes_cleared,
            duration_ms=duration_ms,
            invocation_id=invocation_id,
        )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for cache invalidation.

    Clears task cache entries from Redis and S3. Use this before
    running cache_warmer when cached data is stale or corrupted.

    Args:
        event: Lambda event with optional configuration:
            - clear_tasks (bool): If True, clear task cache. Default True.
            - clear_dataframes (bool): If True, clear dataframe cache. Default False.
        context: Lambda context with aws_request_id.

    Returns:
        Dictionary with invalidation results:
            - statusCode (int): HTTP status code (200 for success, 500 for failure)
            - body (dict): InvalidateResponse as dictionary

    Example Event:
        {
            "clear_tasks": true,
            "clear_dataframes": false
        }

    Example Response:
        {
            "statusCode": 200,
            "body": {
                "success": true,
                "message": "Cache invalidation complete: 500 Redis keys, 1200 S3 objects cleared",
                "tasks_cleared": {"redis": 500, "s3": 1200},
                "dataframes_cleared": 0,
                "duration_ms": 2500.5,
                "timestamp": "2026-01-07T18:00:00+00:00",
                "invocation_id": "abc-123-def-456"
            }
        }
    """
    invocation_id = getattr(context, "aws_request_id", None)

    logger.info(
        "cache_invalidate_handler_invoked",
        extra={
            "event": event,
            "has_context": context is not None,
            "invocation_id": invocation_id,
        },
    )

    # Parse event parameters
    clear_tasks = event.get("clear_tasks", True)
    clear_dataframes = event.get("clear_dataframes", False)

    # Run async invalidation
    try:
        response = asyncio.run(_invalidate_cache_async(
            clear_tasks=clear_tasks,
            clear_dataframes=clear_dataframes,
            context=context,
        ))
    except Exception as e:
        logger.error(
            "cache_invalidate_handler_exception",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "invocation_id": invocation_id,
            },
        )
        response = InvalidateResponse(
            success=False,
            message=f"Handler exception: {e}",
            invocation_id=invocation_id,
        )

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
    or for testing purposes.

    Args:
        event: Lambda event with optional configuration.
        context: Lambda context with aws_request_id.

    Returns:
        Same format as handler().
    """
    invocation_id = getattr(context, "aws_request_id", None)

    logger.info(
        "cache_invalidate_handler_async_invoked",
        extra={
            "event": event,
            "invocation_id": invocation_id,
        },
    )

    clear_tasks = event.get("clear_tasks", True)
    clear_dataframes = event.get("clear_dataframes", False)

    response = await _invalidate_cache_async(
        clear_tasks=clear_tasks,
        clear_dataframes=clear_dataframes,
        context=context,
    )

    status_code = 200 if response.success else 500

    return {
        "statusCode": status_code,
        "body": response.to_dict(),
    }
