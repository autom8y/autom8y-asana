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
            Exception  # noqa: BLE001
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


async def _unit_frame_with_activity(
    unit_df: Any,
    *,
    get_project_gid: Any,
    cache: Any,
    invocation_id: str,
) -> Any | None:
    """Return the Unit frame with its ``unit_activity`` column, or None.

    Unit activity is computed ONCE per snapshot, here, where both the ECS and
    the Lambda pushes read their Unit frame, from the Unit and Offer frames the
    same cache holds (``unit_activity.with_unit_activity``, the single
    definition). A marketing Unit's activity needs the Offer frame, so without a
    usable one this returns None and the caller withholds the whole snapshot:
    the receiver keeps its last good one rather than a snapshot without Units.
    """
    from autom8_asana.models.business.unit_activity import (
        UnitActivityInputError,
        with_unit_activity,
    )

    offer_project_gid = get_project_gid("offer")
    offer_entry = await cache.get_async(offer_project_gid, "offer") if offer_project_gid else None
    if offer_entry is None or offer_entry.dataframe is None:
        logger.warning(
            "status_push_unit_activity_skipped",
            extra={"reason": "offer_frame_unavailable", "invocation_id": invocation_id},
        )
        return None

    try:
        return with_unit_activity(unit_df, offer_entry.dataframe)
    except UnitActivityInputError as e:
        logger.warning(
            "status_push_unit_activity_skipped",
            extra={"reason": str(e), "invocation_id": invocation_id},
        )
        return None


async def _push_account_status_for_completed_entities(
    completed_entities: list[str],
    get_project_gid: Any,
    cache: Any,
    invocation_id: str,
) -> None:
    """Push account status to autom8_data for each warmed entity type.

    Extracts section classifications from warmed DataFrames and
    aggregates all entries into a single snapshot push. The Unit frame first
    gets its ``unit_activity`` column (``_unit_frame_with_activity``), which the
    extraction reads instead of the Unit's own section. When the Unit rows are
    lost (see ``unit_activity_withheld``), the whole snapshot is withheld and
    ``StatusPushSkipped{skip_reason=unit_activity_unavailable}`` is emitted once.

    Non-blocking: all errors are caught and logged.

    Args:
        completed_entities: Entity types that were successfully warmed.
        get_project_gid: Callable(entity_type) -> project_gid or None.
        cache: DataFrameCache instance for retrieving warmed DataFrames.
        invocation_id: Lambda invocation ID for log correlation.
    """
    from autom8_asana.services.gid_push import (
        PIPELINE_TYPE_BY_PROJECT_GID,
        SKIP_REASON_UNIT_ACTIVITY_UNAVAILABLE,
        extract_status_from_dataframe,
        push_status_to_data_service,
    )

    # SD-02 warm-set vs pipeline-map reconciliation (sprint-C6): of the warmed
    # entity set, only entities whose project GID appears in
    # PIPELINE_TYPE_BY_PROJECT_GID can EVER contribute registry rows -- the
    # rest are a silent narrowing of what "the account's status" covers.
    # Surface it (WARNING + metric), do not silently accept it. With today's
    # map and the default warm set this fires every run with mapped=["unit"]
    # -- that is the honest signal, by design. Expanding the map is a product
    # decision routed to a DEFER (watch-trigger: StatusPushUnmappedEntities > 0
    # sustained after C-2 lands), NOT this sprint. Living in the shared
    # orchestrator means the Lambda lane inherits this if ever re-armed.
    mapped: list[str] = []
    unmapped: list[str] = []
    for _entity_type in completed_entities:
        _project_gid = get_project_gid(_entity_type)
        if not _project_gid:
            continue
        if PIPELINE_TYPE_BY_PROJECT_GID.get(_project_gid):
            mapped.append(_entity_type)
        else:
            unmapped.append(_entity_type)
    if unmapped:
        logger.warning(
            "status_push_registry_coverage",
            extra={
                "mapped": mapped,
                "unmapped": unmapped,
                "narrowing": ("registry narrows to pipeline_types of mapped projects only"),
                "invocation_id": invocation_id,
            },
        )
    emit_metric(
        "StatusPushUnmappedEntities",
        len(unmapped),
        namespace="Autom8y/AsanaBridgeFleet",
    )

    all_entries: list[dict[str, Any]] = []
    # Set when the Unit rows are lost to this snapshot: a Unit cache miss, Unit
    # activity that could not be computed, or a Unit extraction that raised.
    # The receiver REPLACES the whole snapshot, so a snapshot without its Unit
    # rows would delete them there: such a snapshot is withheld, never pushed.
    unit_activity_withheld = False

    for entity_type in completed_entities:
        project_gid = get_project_gid(entity_type)
        if not project_gid:
            continue

        try:
            entry = await cache.get_async(project_gid, entity_type)
            if entry is None or entry.dataframe is None:
                if entity_type == "unit":
                    # A Unit cache miss loses the Unit rows like any other Unit
                    # failure: withhold, never push the other entities alone.
                    logger.warning(
                        "status_push_unit_activity_skipped",
                        extra={"reason": "unit_frame_unavailable", "invocation_id": invocation_id},
                    )
                    unit_activity_withheld = True
                continue

            df = entry.dataframe
            if entity_type == "unit":
                df = await _unit_frame_with_activity(
                    df,
                    get_project_gid=get_project_gid,
                    cache=cache,
                    invocation_id=invocation_id,
                )
                if df is None:
                    unit_activity_withheld = True
                    continue

            entries = extract_status_from_dataframe(
                df=df,
                project_gid=project_gid,
                entity_type=entity_type,
            )
            all_entries.extend(entries)

        except Exception as e:  # BROAD-CATCH: isolation  # noqa: BLE001
            if entity_type == "unit":
                # The Unit rows are lost to this snapshot; never push it without them.
                unit_activity_withheld = True
            logger.warning(
                "status_extract_entity_error",
                extra={
                    "entity_type": entity_type,
                    "project_gid": project_gid,
                    "error": str(e),
                    "invocation_id": invocation_id,
                },
            )

    if unit_activity_withheld:
        # A withheld snapshot is a skipped push: count it ONCE per snapshot, under
        # its own reason, so a lasting withhold is visible as a metric (the
        # receiver serves its last good snapshot meanwhile), not only as a log.
        emit_metric(
            "StatusPushSkipped",
            1,
            dimensions={"skip_reason": SKIP_REASON_UNIT_ACTIVITY_UNAVAILABLE},
            namespace="Autom8y/AsanaBridgeFleet",
        )
        logger.warning(
            "status_push_snapshot_withheld",
            extra={
                "reason": SKIP_REASON_UNIT_ACTIVITY_UNAVAILABLE,
                "entry_count": len(all_entries),
                "invocation_id": invocation_id,
            },
        )
        return

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
    else:
        # Empty denominator: every warmed entity contributed zero status
        # entries (the three-way reconciler denominator is null on this run).
        # Previously this branch was metric-silent, making a benign idle run
        # indistinguishable from a misconfigured one. Per SRE observability-
        # design N1 §B-1 (AI-4): emit StatusPushSkipped{three_way_denominator_null}.
        # Additive observability only -- no push behavior change.
        emit_metric(
            "StatusPushSkipped",
            1,
            dimensions={"skip_reason": "three_way_denominator_null"},
            namespace="Autom8y/AsanaBridgeFleet",
        )
        logger.info(
            "status_push_skipped",
            extra={
                "reason": "three_way_denominator_null",
                "entry_count": 0,
                "invocation_id": invocation_id,
            },
        )
