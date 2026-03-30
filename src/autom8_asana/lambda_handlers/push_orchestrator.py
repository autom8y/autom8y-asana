"""Push orchestration for the cache warmer Lambda.

Extracted from cache_warmer.py (RF-003). Provides thin orchestration
wrappers that sequence side-effects (GID push, account status push)
after DataFrame warming completes.

Per architectural decision FLAG-1: these functions remain in
lambda_handlers/ (not services/) to avoid a circular dependency — the
service modules already own the implementation being called here.
"""

from __future__ import annotations

from typing import Any

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric

logger = get_logger(__name__)

__all__ = [
    "_push_gid_mappings_for_completed_entities",
    "_push_account_status_for_completed_entities",
]


async def _push_gid_mappings_for_completed_entities(
    completed_entities: list[str],
    get_project_gid: Any,
    cache: Any,
    invocation_id: str,
) -> None:
    """Push GID mappings to autom8_data for each successfully warmed entity.

    After cache warming, iterate over
    completed entities, build a transient GidLookupIndex from each cached
    DataFrame, and push mappings to autom8_data's sync endpoint.

    Only entity types whose DataFrames contain the required columns
    (office_phone, vertical, gid) will produce GID mappings. Others are
    silently skipped.

    This function is non-blocking: all errors are caught and logged so
    that push failures never affect the cache warmer result.

    Args:
        completed_entities: Entity types that were successfully warmed.
        get_project_gid: Callable(entity_type) -> project_gid or None.
        cache: DataFrameCache instance for retrieving warmed DataFrames.
        invocation_id: Lambda invocation ID for log correlation.
    """
    from autom8_asana.services.gid_lookup import GidLookupIndex
    from autom8_asana.services.gid_push import push_gid_mappings_to_data_service
    from autom8_asana.services.universal_strategy import DEFAULT_KEY_COLUMNS

    push_count = 0

    for entity_type in completed_entities:
        project_gid = get_project_gid(entity_type)
        if not project_gid:
            continue

        try:
            # Retrieve the cached DataFrame
            entry = await cache.get_async(project_gid, entity_type)
            if entry is None or entry.dataframe is None:
                continue

            df = entry.dataframe

            # Attempt to build a GidLookupIndex; skip if columns are missing
            try:
                key_cols = DEFAULT_KEY_COLUMNS.get(entity_type, ["gid"])
                index = GidLookupIndex.from_dataframe(df, key_columns=key_cols)
            except KeyError:
                # DataFrame lacks required key columns -- not
                # a GID-bearing entity type (e.g., offer, contact). Skip.
                continue

            if len(index) == 0:
                continue

            # Push mappings (non-blocking -- failures logged internally)
            success = await push_gid_mappings_to_data_service(
                project_gid=project_gid,
                index=index,
            )

            if success:
                push_count += 1
                emit_metric(
                    "GidPushSuccess",
                    1,
                    dimensions={"entity_type": entity_type},
                )
            else:
                emit_metric(
                    "GidPushFailure",
                    1,
                    dimensions={"entity_type": entity_type},
                )

        except (
            Exception
        ) as e:  # BROAD-CATCH: isolation -- push failure must never fail cache warmer
            logger.warning(
                "gid_push_entity_error",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "invocation_id": invocation_id,
                },
            )

    if push_count > 0:
        logger.info(
            "gid_push_complete",
            extra={
                "push_count": push_count,
                "total_entities": len(completed_entities),
                "invocation_id": invocation_id,
            },
        )


async def _push_account_status_for_completed_entities(
    completed_entities: list[str],
    get_project_gid: Any,
    cache: Any,
    invocation_id: str,
) -> None:
    """Push account status to autom8_data for each warmed entity type.

    Extracts section classifications from warmed DataFrames and
    aggregates all entries into a single snapshot push.

    Non-blocking: all errors are caught and logged.

    Args:
        completed_entities: Entity types that were successfully warmed.
        get_project_gid: Callable(entity_type) -> project_gid or None.
        cache: DataFrameCache instance for retrieving warmed DataFrames.
        invocation_id: Lambda invocation ID for log correlation.
    """
    from autom8_asana.services.gid_push import (
        extract_status_from_dataframe,
        push_status_to_data_service,
    )

    all_entries: list[dict[str, Any]] = []

    for entity_type in completed_entities:
        project_gid = get_project_gid(entity_type)
        if not project_gid:
            continue

        try:
            entry = await cache.get_async(project_gid, entity_type)
            if entry is None or entry.dataframe is None:
                continue

            entries = extract_status_from_dataframe(
                df=entry.dataframe,
                project_gid=project_gid,
                entity_type=entity_type,
            )
            all_entries.extend(entries)

        except Exception as e:  # BROAD-CATCH: isolation
            logger.warning(
                "status_extract_entity_error",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                    "error": str(e),
                    "invocation_id": invocation_id,
                },
            )

    if all_entries:
        from datetime import UTC, datetime

        success = await push_status_to_data_service(
            entries=all_entries,
            source_timestamp=datetime.now(UTC).isoformat(),
        )

        if success:
            emit_metric(
                "StatusPushSuccess",
                1,
                dimensions={"entry_count": str(len(all_entries))},
            )
        else:
            emit_metric("StatusPushFailure", 1)

        logger.info(
            "status_push_complete",
            extra={
                "entry_count": len(all_entries),
                "success": success,
                "invocation_id": invocation_id,
            },
        )
