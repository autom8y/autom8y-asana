"""Lambda handler for cache warming.

Per TDD-DATAFRAME-CACHE-001 Section 5.7:
Lambda warm-up handler for pre-deployment cache hydration.

This module provides:
- handler: AWS Lambda entry point for cache warming
- WarmResponse: Response dataclass for Lambda returns

Environment Variables Required:
    ASANA_PAT: Asana Personal Access Token
    ASANA_CACHE_S3_BUCKET: S3 bucket for cache storage
    ASANA_CACHE_S3_PREFIX: S3 key prefix (optional, default: "cache/")

Usage:
    Deploy as AWS Lambda function with handler:
    autom8_asana.lambda_handlers.cache_warmer.handler

    Invoke with optional event parameters:
    {
        "entity_types": ["unit", "offer"],  // Optional, defaults to all
        "strict": true                       // Optional, default true
    }
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@dataclass
class WarmResponse:
    """Response from cache warming Lambda.

    Per TDD-DATAFRAME-CACHE-001: Structured response for Lambda
    invocation with detailed status per entity type.

    Attributes:
        success: Overall success status (all entity types warmed).
        message: Human-readable summary.
        entity_results: Per-entity-type warming results.
        total_rows: Total rows warmed across all entity types.
        duration_ms: Total execution time in milliseconds.
        timestamp: ISO timestamp of completion.
    """

    success: bool
    message: str
    entity_results: list[dict[str, Any]] = field(default_factory=list)
    total_rows: int = 0
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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
        }


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
    from autom8_asana.models.business.registry import get_workspace_registry
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
        entity_types_to_discover: list[str] = ["unit", "business", "offer", "contact"]

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

        logger.info(
            "lambda_entity_discovery_complete",
            extra={
                "registered_types": entity_registry.get_all_entity_types(),
            },
        )


def _normalize_project_name(name: str) -> str:
    """Normalize project name for entity type matching.

    Converts names like "Business Units" to "unit", "Offers" to "offer", etc.

    Args:
        name: Project name to normalize.

    Returns:
        Normalized name suitable for entity type matching.
    """
    # Remove common suffixes and prefixes
    normalized = name.lower().strip()

    # Handle "Business Units" -> "unit"
    if "unit" in normalized:
        return "unit"

    # Handle "Businesses" or "Business" -> "business"
    if normalized.startswith("business") and "unit" not in normalized:
        return "business"

    # Handle "Offers" or "Offer" -> "offer"
    if normalized.startswith("offer"):
        return "offer"

    # Handle "Contacts" or "Contact" -> "contact"
    if normalized.startswith("contact"):
        return "contact"

    return normalized


def _match_entity_type(project_name: str, entity_types: list[str]) -> str | None:
    """Match a project name to an entity type.

    Args:
        project_name: Project name to match.
        entity_types: List of valid entity type identifiers.

    Returns:
        Matched entity type or None if no match.
    """
    normalized = _normalize_project_name(project_name)
    if normalized in entity_types:
        return normalized
    return None


async def _warm_cache_async(
    entity_types: list[str] | None = None,
    strict: bool = True,
) -> WarmResponse:
    """Async implementation of cache warming.

    Args:
        entity_types: Optional list of entity types to warm.
            Defaults to all types: ["offer", "unit", "business", "contact"]
        strict: If True, fail on any entity type warm failure.

    Returns:
        WarmResponse with detailed results.
    """
    import os

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
    from autom8_asana.services.resolver import EntityProjectRegistry

    start_time = time.monotonic()

    # Initialize DataFrameCache if not already done
    cache = get_dataframe_cache()
    if cache is None:
        cache = initialize_dataframe_cache()

    if cache is None:
        return WarmResponse(
            success=False,
            message="Failed to initialize DataFrameCache. Check S3 configuration.",
            duration_ms=(time.monotonic() - start_time) * 1000,
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
                extra={"error": str(e)},
            )

    if not registry.is_ready():
        return WarmResponse(
            success=False,
            message="EntityProjectRegistry not initialized. No projects discovered.",
            duration_ms=(time.monotonic() - start_time) * 1000,
        )

    # Determine entity types to warm
    default_priority = ["offer", "unit", "business", "contact"]
    if entity_types:
        # Validate entity types
        valid_types = set(default_priority)
        invalid = set(entity_types) - valid_types
        if invalid:
            return WarmResponse(
                success=False,
                message=f"Invalid entity types: {invalid}. Valid types: {valid_types}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        priority = entity_types
    else:
        priority = default_priority

    # Create warmer with specified priority
    warmer = CacheWarmer(
        cache=cache,
        priority=priority,
        strict=strict,
    )

    # Get Asana client credentials
    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        return WarmResponse(
            success=False,
            message=f"Failed to get bot PAT: {e}",
            duration_ms=(time.monotonic() - start_time) * 1000,
        )

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
    if not workspace_gid:
        return WarmResponse(
            success=False,
            message="ASANA_WORKSPACE_GID environment variable not set",
            duration_ms=(time.monotonic() - start_time) * 1000,
        )

    # Define project GID provider using EntityProjectRegistry
    def get_project_gid(entity_type: str) -> str | None:
        return registry.get_project_gid(entity_type)

    # Execute warming with async context manager for client
    try:
        async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
            results = await warmer.warm_all_async(
                client=client,
                project_gid_provider=get_project_gid,
            )

        # Build response
        entity_results = [status.to_dict() for status in results]
        success_count = sum(1 for r in results if r.result == WarmResult.SUCCESS)
        failure_count = sum(1 for r in results if r.result == WarmResult.FAILURE)
        skipped_count = sum(1 for r in results if r.result == WarmResult.SKIPPED)
        total_rows = sum(r.row_count for r in results)

        all_success = failure_count == 0 and skipped_count == 0
        duration_ms = (time.monotonic() - start_time) * 1000

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
        )

    except Exception as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.error(
            "cache_warmer_handler_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": duration_ms,
            },
        )

        return WarmResponse(
            success=False,
            message=f"Cache warm failed: {e}",
            duration_ms=duration_ms,
        )


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for cache warming.

    Per TDD-DATAFRAME-CACHE-001: Entry point for AWS Lambda invocation.
    Warms all configured entity types in priority order.

    Args:
        event: Lambda event with optional configuration:
            - entity_types (list[str]): Optional list of entity types to warm.
                Defaults to ["offer", "unit", "business", "contact"].
            - strict (bool): If True, fail on any entity type failure.
                Defaults to True.
        context: Lambda context (unused but required by AWS Lambda signature).

    Returns:
        Dictionary with warming results:
            - statusCode (int): HTTP status code (200 for success, 500 for failure)
            - body (dict): WarmResponse as dictionary

    Example Event:
        {
            "entity_types": ["unit", "offer"],
            "strict": false
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
                "timestamp": "2026-01-06T12:00:00+00:00"
            }
        }

    Environment Variables:
        ASANA_PAT: Asana Personal Access Token (required)
        ASANA_CACHE_S3_BUCKET: S3 bucket for cache storage (required)
        ASANA_CACHE_S3_PREFIX: S3 key prefix (optional)
    """
    logger.info(
        "cache_warmer_handler_invoked",
        extra={
            "event": event,
            "has_context": context is not None,
        },
    )

    # Parse event parameters
    entity_types = event.get("entity_types")
    strict = event.get("strict", True)

    # Run async warming
    try:
        response = asyncio.run(_warm_cache_async(
            entity_types=entity_types,
            strict=strict,
        ))
    except Exception as e:
        logger.error(
            "cache_warmer_handler_exception",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        response = WarmResponse(
            success=False,
            message=f"Handler exception: {e}",
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
    or for testing purposes.

    Args:
        event: Lambda event (same format as handler).
        context: Lambda context (optional).

    Returns:
        Same format as handler().
    """
    logger.info(
        "cache_warmer_handler_async_invoked",
        extra={
            "event": event,
        },
    )

    entity_types = event.get("entity_types")
    strict = event.get("strict", True)

    response = await _warm_cache_async(
        entity_types=entity_types,
        strict=strict,
    )

    status_code = 200 if response.success else 500

    return {
        "statusCode": status_code,
        "body": response.to_dict(),
    }
