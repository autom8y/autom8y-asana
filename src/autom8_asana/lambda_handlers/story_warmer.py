"""Story cache warming for the cache warmer Lambda.

Extracted from cache_warmer.py (RF-002). Provides story warming after
DataFrame warming completes, piggybacking on the existing warmer run
(Strategy E per TDD-lambda-cache-warmer).
"""

from __future__ import annotations

import time
from typing import Any

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric
from autom8_asana.lambda_handlers.timeout import _should_exit_early

logger = get_logger(__name__)

__all__ = ["_warm_story_caches_for_completed_entities"]


async def _warm_story_caches_for_completed_entities(
    completed_entities: list[str],
    get_project_gid: Any,
    dataframe_cache: Any,
    client: Any,
    invocation_id: str,
    context: Any = None,
) -> dict[str, Any]:
    """Warm story caches for tasks in completed DataFrame entities.

    After DataFrame warming completes, iterate task GIDs from each warmed
    DataFrame and populate the entity (story) cache via the client's
    list_for_task_cached_async method with bounded concurrency.

    This function is non-blocking: all errors are caught and logged so
    that story warming failures never affect the cache warmer result.

    Strategy E: piggyback story warming on the existing DataFrame warmer.

    Args:
        completed_entities: Entity types that were successfully warmed.
        get_project_gid: Callable(entity_type) -> project_gid or None.
        dataframe_cache: DataFrameCache instance for retrieving warmed DataFrames.
        client: AsanaClient with entity cache for story warming.
        invocation_id: Lambda invocation ID for log correlation.
        context: Lambda context for timeout detection.

    Returns:
        Dict with story warming stats: {success: int, failure: int, skipped: int, total_tasks: int}.
    """
    import asyncio

    stats: dict[str, Any] = {
        "success": 0,
        "failure": 0,
        "skipped": 0,
        "total_tasks": 0,
    }
    warm_start = time.monotonic()

    try:
        sem = asyncio.Semaphore(3)
        tasks_processed = 0

        for entity_type in completed_entities:
            project_gid = get_project_gid(entity_type)
            if not project_gid:
                continue

            try:
                # Retrieve the cached DataFrame to get task GIDs
                entry = await dataframe_cache.get_async(project_gid, entity_type)
                if entry is None or entry.dataframe is None:
                    continue

                df = entry.dataframe

                # Extract task GIDs from the DataFrame's 'gid' column
                if "gid" not in df.columns:
                    continue

                task_gids = df["gid"].to_list()
                stats["total_tasks"] += len(task_gids)

                async def _warm_story(task_gid: str, _et: str = entity_type) -> bool:
                    """Warm story cache for a single task. Returns True on success."""
                    try:
                        async with sem:
                            await client.stories.list_for_task_cached_async(
                                task_gid,
                                max_cache_age_seconds=7200,
                            )
                        return True
                    except (
                        Exception
                    ) as e:  # BROAD-CATCH: isolation -- single task failure must not abort batch
                        logger.debug(
                            "story_warm_task_failed",
                            extra={
                                "task_gid": task_gid,
                                "entity_type": _et,
                                "error": str(e),
                                "invocation_id": invocation_id,
                            },
                        )
                        return False

                # Process tasks in chunks, checking timeout periodically
                chunk_size = 100
                for i in range(0, len(task_gids), chunk_size):
                    # Check timeout before each chunk
                    if _should_exit_early(context):
                        logger.warning(
                            "story_warm_timeout_exit",
                            extra={
                                "tasks_processed": tasks_processed,
                                "total_tasks": stats["total_tasks"],
                                "invocation_id": invocation_id,
                            },
                        )
                        break

                    chunk = task_gids[i : i + chunk_size]
                    results = await asyncio.gather(
                        *[_warm_story(gid) for gid in chunk],
                        return_exceptions=True,
                    )

                    for result in results:
                        tasks_processed += 1
                        if isinstance(result, BaseException):
                            stats["failure"] += 1
                        elif result is True:
                            stats["success"] += 1
                        else:
                            stats["failure"] += 1

            except (
                Exception
            ) as e:  # BROAD-CATCH: isolation -- per-entity failure must not abort story warming
                logger.warning(
                    "story_warm_entity_error",
                    extra={
                        "entity_type": entity_type,
                        "project_gid": project_gid,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "invocation_id": invocation_id,
                    },
                )

        warm_duration_ms = (time.monotonic() - warm_start) * 1000

        # Emit CloudWatch metrics
        emit_metric("StoryWarmSuccess", stats["success"])
        emit_metric("StoryWarmFailure", stats["failure"])
        emit_metric("StoriesWarmed", stats["success"] + stats["failure"])
        emit_metric("StoryWarmDuration", warm_duration_ms, unit="Milliseconds")

        if stats["success"] > 0 or stats["failure"] > 0:
            logger.info(
                "story_warm_complete",
                extra={
                    "success": stats["success"],
                    "failure": stats["failure"],
                    "total_tasks": stats["total_tasks"],
                    "duration_ms": round(warm_duration_ms, 1),
                    "invocation_id": invocation_id,
                },
            )

    except (
        Exception
    ) as e:  # BROAD-CATCH: isolation -- story warming must never fail the overall warmer
        warm_duration_ms = (time.monotonic() - warm_start) * 1000
        logger.error(
            "story_warm_fatal_error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(warm_duration_ms, 1),
                "invocation_id": invocation_id,
            },
        )
        emit_metric("StoryWarmFailure", 1)

    return stats
