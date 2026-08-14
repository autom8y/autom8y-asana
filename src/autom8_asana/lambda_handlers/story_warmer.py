"""Story cache warming for the cache warmer Lambda.

Extracted from cache_warmer.py (RF-002). Provides story warming after
DataFrame warming completes, piggybacking on the existing warmer run
(Strategy E per TDD-lambda-cache-warmer).

CC-5 (chain-of-custody-closure; Tier-1 offers-only per operator ruling R-1)
adds two things to that Strategy-E piggyback, both inside ``src/``:

1. **Priority-first warm order.** The shared story-warm budget is
   TIME-bound (``_should_exit_early``), not count-bound, and in production
   it is exhausted every run inside the first four cascade entities. Any
   entity below them is enumerated but never warmed -- offer sat at
   cumulative slice 10,617-14,808 against a warmer that never got past
   ~8,527 tasks, i.e. 0 of 4,192 offer tasks warmed across 324+ runs.
   Priority entities (default: ``offer``) are therefore warmed FIRST,
   keyed on their own project GID, independent of their position in -- or
   absence from -- ``completed_entities``.

   This deliberately does NOT raise concurrency, the chunk size, or the
   Lambda budget: the pass is budget-NEUTRAL. The story warmer already ran
   to its timeout wall every run, so the same wall clock and the same
   ``Semaphore(3)`` envelope now buy offer coverage instead of the tail of
   the cascade. Re-warming an already-warm task costs no API call at all
   (``load_stories_incremental`` short-circuits below
   ``max_cache_age_seconds``), so coverage accrues across runs rather than
   restarting from zero.

2. **An always-emitted per-entity receipt.** Before CC-5 the only readout
   was the aggregate ``stats["success"]`` counter, from which a per-entity
   zero could only be INFERRED. ``story_warm_entity_complete`` is now
   logged for every planned entity on every run -- including when every
   counter is zero -- so "warmed none" is a measured datum rather than an
   absent one, and the two negatives are distinguishable:

   * ``enumerated=True,  success=0``  -> budget starvation (reached, warmed none)
   * ``enumerated=False``             -> never reached (``skip_reason`` says why)

Scope fence: Tier 1 only (offers, one project GID, one Lambda invocation).
This module does not attempt the Tier-2 fleet warmer redesign.
"""

from __future__ import annotations

import os
import time
from typing import Any

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric
from autom8_asana.lambda_handlers.timeout import _should_exit_early

logger = get_logger(__name__)

__all__ = [
    "DEFAULT_STORY_WARM_PRIORITY_ENTITIES",
    "STORY_WARM_PRIORITY_ENV_VAR",
    "_build_warm_order",
    "_resolve_priority_entities",
    "_warm_entity_stories",
    "_warm_story_caches_for_completed_entities",
]

# CC-5 / R-1: Tier-1 scope is offers-only. The default names an ENTITY, not
# a project GID -- the GID is resolved through ``get_project_gid`` so a
# registry change cannot silently point the pass at a stale project.
DEFAULT_STORY_WARM_PRIORITY_ENTITIES: tuple[str, ...] = ("offer",)

# Operator lever. Set to a comma-separated entity list to change the
# priority set; set to the EMPTY string to restore the pre-CC-5 pure
# cascade order -- a revert that needs no code change. Unset means
# DEFAULT_STORY_WARM_PRIORITY_ENTITIES.
STORY_WARM_PRIORITY_ENV_VAR = "ASANA_STORY_WARM_PRIORITY_ENTITIES"

# Concurrency envelope. Deliberately unchanged from the pre-CC-5 value:
# raising it re-enters the documented 429-storm surface (option O-G,
# disfavoured) and would confound any post-deploy AL-5 reading.
_STORY_WARM_CONCURRENCY = 3

# Tasks per gather() batch. The timeout check runs once per chunk.
_STORY_WARM_CHUNK_SIZE = 100

# Cache-age threshold handed to the client. A task warmed inside this
# window costs no API call on the next pass.
_STORY_WARM_MAX_CACHE_AGE_SECONDS = 7200


def _resolve_priority_entities(env: dict[str, str] | None = None) -> tuple[str, ...]:
    """Resolve the priority (warm-first) entity list.

    Args:
        env: Environment mapping to read from. Defaults to ``os.environ``.

    Returns:
        Ordered, de-duplicated tuple of entity type names to warm first.
        Empty tuple means "no priority set" (pure cascade order).
    """
    source: Any = os.environ if env is None else env
    raw = source.get(STORY_WARM_PRIORITY_ENV_VAR)
    if raw is None:
        return DEFAULT_STORY_WARM_PRIORITY_ENTITIES

    seen: set[str] = set()
    resolved: list[str] = []
    for part in str(raw).split(","):
        name = part.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        resolved.append(name)
    return tuple(resolved)


def _build_warm_order(
    completed_entities: list[str],
    priority_entities: tuple[str, ...],
) -> list[tuple[str, bool]]:
    """Build the story-warm execution order: priority entities first.

    The priority entities lead REGARDLESS of whether they appear in
    ``completed_entities`` and regardless of where they appear. That is
    what makes the pass immune to CF-18 (``cascade_warm_phases`` breaks
    ``warm_priority`` ties by iterating a ``set``, whose order is not
    stable across processes) and to a checkpoint resume that trimmed the
    priority entity out of ``completed_entities``.

    Args:
        completed_entities: Entity types the DataFrame warmer completed,
            in cascade order.
        priority_entities: Entity types to warm first.

    Returns:
        List of ``(entity_type, is_priority)`` pairs, de-duplicated,
        priority entities first, remaining entities in their original
        relative order.
    """
    seen: set[str] = set()
    order: list[tuple[str, bool]] = []

    for entity_type in priority_entities:
        if entity_type in seen:
            continue
        seen.add(entity_type)
        order.append((entity_type, True))

    for entity_type in completed_entities:
        if entity_type in seen:
            continue
        seen.add(entity_type)
        order.append((entity_type, False))

    return order


def _new_entity_receipt(
    entity_type: str,
    project_gid: str | None,
    is_priority: bool,
    position: int,
    total_tasks_at_entry: int,
) -> dict[str, Any]:
    """Build a zero-valued per-entity receipt.

    Every field is populated up front so a receipt is emitted with
    explicit zeros even on the paths that do no work at all.
    """
    return {
        "entity_type": entity_type,
        "project_gid": project_gid,
        "priority": is_priority,
        "position": position,
        "enumerated": False,
        "skip_reason": None,
        "task_count": 0,
        "processed": 0,
        "success": 0,
        "failure": 0,
        "shared_gids_with_prior": 0,
        "budget_exhausted": False,
        "total_tasks_at_entry": total_tasks_at_entry,
        "duration_ms": 0.0,
    }


def _emit_entity_receipt(receipt: dict[str, Any], invocation_id: str) -> None:
    """Emit the per-entity warm receipt (SLATE section 4 receipt shape).

    ALWAYS emitted, for every planned entity, on every run -- including
    when every counter is zero. An absent ``{entity_type=offer}`` record
    is indistinguishable from ``offer.success = 0``; an explicit zero is
    not. That distinction is the whole point of the receipt.

    The structured log carries EVERY entity (dimension-free, so it adds no
    CloudWatch metric series). CloudWatch metrics are emitted only for
    PRIORITY entities, which bounds the new dimensioned series to the
    Tier-1 scope instead of minting one per fleet entity.
    """
    logger.info(
        "story_warm_entity_complete",
        extra={**receipt, "invocation_id": invocation_id},
    )

    if not receipt.get("priority"):
        return

    dimensions = {"entity_type": str(receipt["entity_type"])}
    # Denominator first: a success count without its task_count cannot be
    # read as coverage.
    emit_metric("StoryWarmEntityTaskCount", receipt["task_count"], dimensions=dimensions)
    emit_metric("StoryWarmEntitySuccess", receipt["success"], dimensions=dimensions)
    emit_metric("StoryWarmEntityFailure", receipt["failure"], dimensions=dimensions)
    emit_metric(
        "StoryWarmEntityReached",
        1 if receipt["enumerated"] else 0,
        dimensions=dimensions,
    )


async def _warm_entity_stories(
    *,
    entity_type: str,
    project_gid: str | None,
    is_priority: bool,
    position: int,
    dataframe_cache: Any,
    client: Any,
    sem: Any,
    context: Any,
    invocation_id: str,
    seen_gids: set[str],
    tasks_processed_before: int,
    total_tasks_before: int,
) -> dict[str, Any]:
    """Warm one entity's story caches; return its receipt.

    Never raises: a per-entity failure is isolated so it cannot abort the
    remaining entities (and so it can never fail the cache warmer).

    Args:
        entity_type: Entity type being warmed.
        project_gid: Project GID for the entity, or None if unresolvable.
        is_priority: Whether this entity is in the warm-first priority set.
        position: Index of this entity in the execution order.
        dataframe_cache: DataFrameCache for retrieving the warmed DataFrame.
        client: AsanaClient with the story cache.
        sem: Shared concurrency semaphore.
        context: Lambda context for timeout detection.
        invocation_id: Lambda invocation ID for log correlation.
        seen_gids: GIDs already enumerated this run. MUTATED: this entity's
            GIDs are added. Used to measure CF-3 population overlap.
        tasks_processed_before: Cumulative tasks processed before this
            entity (preserves the pre-CC-5 ``story_warm_timeout_exit``
            field semantics).
        total_tasks_before: Cumulative tasks enumerated before this entity.

    Returns:
        The per-entity receipt dict.
    """
    import asyncio

    entity_start = time.monotonic()
    receipt = _new_entity_receipt(
        entity_type, project_gid, is_priority, position, total_tasks_before
    )

    if not project_gid:
        receipt["skip_reason"] = "no_project_gid"
        receipt["duration_ms"] = round((time.monotonic() - entity_start) * 1000, 1)
        return receipt

    try:
        # Retrieve the cached DataFrame to get task GIDs
        entry = await dataframe_cache.get_async(project_gid, entity_type)
        if entry is None or entry.dataframe is None:
            receipt["skip_reason"] = "no_cache_entry"
            receipt["duration_ms"] = round((time.monotonic() - entity_start) * 1000, 1)
            return receipt

        df = entry.dataframe

        # Extract task GIDs from the DataFrame's 'gid' column
        if "gid" not in df.columns:
            receipt["skip_reason"] = "no_gid_column"
            receipt["duration_ms"] = round((time.monotonic() - entity_start) * 1000, 1)
            return receipt

        task_gids = df["gid"].to_list()
        receipt["enumerated"] = True
        receipt["task_count"] = len(task_gids)

        # CF-3 instrumentation: an entity's GID set can overlap an
        # earlier-enumerated entity's, in which case a "success" here may
        # be a cache hit rather than a fetch. Measured, not assumed away.
        gid_set = {str(gid) for gid in task_gids}
        receipt["shared_gids_with_prior"] = len(gid_set & seen_gids)
        seen_gids |= gid_set

        async def _warm_story(task_gid: str, _et: str = entity_type) -> bool:
            """Warm story cache for a single task. Returns True on success."""
            try:
                async with sem:
                    await client.stories.list_for_task_cached_async(
                        task_gid,
                        max_cache_age_seconds=_STORY_WARM_MAX_CACHE_AGE_SECONDS,
                    )
                return True
            except (
                Exception  # noqa: BLE001
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
        chunk_size = _STORY_WARM_CHUNK_SIZE
        for i in range(0, len(task_gids), chunk_size):
            # Check timeout before each chunk
            if _should_exit_early(context):
                receipt["budget_exhausted"] = True
                logger.warning(
                    "story_warm_timeout_exit",
                    extra={
                        "tasks_processed": tasks_processed_before + receipt["processed"],
                        "total_tasks": total_tasks_before + receipt["task_count"],
                        "entity_type": entity_type,
                        "entity_processed": receipt["processed"],
                        "entity_task_count": receipt["task_count"],
                        "priority": is_priority,
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
                receipt["processed"] += 1
                if isinstance(result, BaseException):
                    receipt["failure"] += 1
                elif result is True:
                    receipt["success"] += 1
                else:
                    receipt["failure"] += 1

    except (
        Exception  # noqa: BLE001
    ) as e:  # BROAD-CATCH: isolation -- per-entity failure must not abort story warming
        receipt["skip_reason"] = "entity_error"
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

    receipt["duration_ms"] = round((time.monotonic() - entity_start) * 1000, 1)
    return receipt


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

    Priority entities (CC-5, default ``offer``) are warmed FIRST -- see the
    module docstring for why the pre-CC-5 cascade order never reached them.

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
        Dict with story warming stats:
        ``{success, failure, skipped, total_tasks, priority_entities, entities}``
        where ``entities`` holds the per-entity receipts in execution order.
    """
    import asyncio

    priority_entities = _resolve_priority_entities()
    stats: dict[str, Any] = {
        "success": 0,
        "failure": 0,
        "skipped": 0,
        "total_tasks": 0,
        "priority_entities": list(priority_entities),
        "entities": [],
    }
    warm_start = time.monotonic()

    try:
        sem = asyncio.Semaphore(_STORY_WARM_CONCURRENCY)
        tasks_processed = 0
        seen_gids: set[str] = set()
        warm_order = _build_warm_order(completed_entities, priority_entities)

        for position, (entity_type, is_priority) in enumerate(warm_order):
            receipt = await _warm_entity_stories(
                entity_type=entity_type,
                project_gid=get_project_gid(entity_type),
                is_priority=is_priority,
                position=position,
                dataframe_cache=dataframe_cache,
                client=client,
                sem=sem,
                context=context,
                invocation_id=invocation_id,
                seen_gids=seen_gids,
                tasks_processed_before=tasks_processed,
                total_tasks_before=stats["total_tasks"],
            )

            stats["total_tasks"] += receipt["task_count"]
            stats["success"] += receipt["success"]
            stats["failure"] += receipt["failure"]
            tasks_processed += receipt["processed"]
            if not receipt["enumerated"]:
                stats["skipped"] += 1

            _emit_entity_receipt(receipt, invocation_id)
            stats["entities"].append(receipt)

        warm_duration_ms = (time.monotonic() - warm_start) * 1000

        # Emit CloudWatch metrics
        emit_metric("StoryWarmSuccess", stats["success"])
        emit_metric("StoryWarmFailure", stats["failure"])
        emit_metric("StoriesWarmed", stats["success"] + stats["failure"])
        emit_metric("StoryWarmDuration", warm_duration_ms, unit="Milliseconds")

        # Emitted UNCONDITIONALLY. The pre-CC-5 guard
        # (``if success > 0 or failure > 0``) made an all-zero run
        # indistinguishable from a run that never happened -- the same
        # absent-vs-zero defect the per-entity receipt exists to close.
        logger.info(
            "story_warm_complete",
            extra={
                "success": stats["success"],
                "failure": stats["failure"],
                "skipped": stats["skipped"],
                "total_tasks": stats["total_tasks"],
                "entities_planned": len(stats["entities"]),
                "priority_entities": stats["priority_entities"],
                "duration_ms": round(warm_duration_ms, 1),
                "invocation_id": invocation_id,
            },
        )

    except (
        Exception  # noqa: BLE001
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
