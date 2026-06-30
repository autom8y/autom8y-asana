"""Scheduling-stratum snapshot push to autom8y-data (Phase-2 normalizer-seam).

Resolves each active office's scheduling stratum (via the pure
:func:`~autom8_asana.normalizer.scheduling_stratum.resolve_stratum` fed by the
GFR by-name extractor) and pushes a whole-snapshot batch to the Phase-1 sync
contract ``POST /api/v1/scheduling-stratum/sync`` (autom8y-data, PR #218).  Mirrors
the account-status snapshot push (``services/gid_push.py``) and REUSES its
data-service HTTP seam (S2S JWT bearer, broad-catch isolation, PII masking).

OPERATOR-ACTIVATABLE / DEFAULT-DARK.  The live prod POST is gated behind
``SCHEDULING_STRATUM_PUSH_ENABLED`` (DEFAULT-OFF -- opposite polarity from the
legacy default-on gid/status push).  The Phase-2 build runs DRY-RUN only: it
resolves, builds, and validates the batch payload but performs NO live POST.
Flipping the gate on is a deploy-time operator decision (a post-deploy step), and
the live "GET /{guid} returns a valid stratum" check requires Phase-1 DEPLOYED --
both are POST-DEPLOY, not build-time, gates.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, NamedTuple

from autom8y_log import get_logger
from pydantic import BaseModel, ConfigDict

from autom8_asana.normalizer.scheduling_extractor import extract_scheduling_inputs
from autom8_asana.normalizer.scheduling_stratum import CASCADE_PRIORITY, resolve_stratum

# Reuse the established data-service push seam (the shared HTTP helper that already
# owns the S2S JWT bearer header, timeout, broad-catch isolation, and PII masking).
from autom8_asana.services.gid_push import (
    _get_auth_token,
    _get_data_service_url,
    _push_to_data_service,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from autom8_asana.client import AsanaClient
    from autom8_asana.normalizer.scheduling_extractor import ExtractedScheduling
    from autom8_asana.normalizer.scheduling_stratum import StratumResult
    from autom8_asana.query.engine import QueryEngine

logger = get_logger(__name__)

#: Emergency / activation gate.  DEFAULT-OFF: the build ships dark; a live POST
#: requires an explicit truthy value (deploy-time operator decision).
SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR = "SCHEDULING_STRATUM_PUSH_ENABLED"

#: The Phase-1 sync route (PR #218, bounded prefix -- NOT fused into /businesses/).
_SYNC_ENDPOINT_PATH = "/api/v1/scheduling-stratum/sync"

#: Snapshot source identifier -- matches the Phase-1 ``snapshot_source`` default.
SNAPSHOT_SOURCE = "asana"


class SchedulingStratumSyncResponse(BaseModel):
    """``POST /api/v1/scheduling-stratum/sync`` response envelope (``synced`` count)."""

    model_config = ConfigDict(extra="ignore")

    synced: int | None = None


class StratumPushResult(NamedTuple):
    """Outcome of a push attempt -- carries the built payload for dry-run inspection."""

    pushed: bool
    dry_run: bool
    entry_count: int
    payload: dict[str, Any]


def _is_stratum_push_enabled() -> bool:
    """Whether the LIVE push is enabled (DEFAULT-OFF, operator-activatable).

    Returns ``True`` only when ``SCHEDULING_STRATUM_PUSH_ENABLED`` is an explicit
    truthy value.  Absent / any other value -> dry-run (no live POST).
    """
    return os.environ.get(SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR, "").lower() in {
        "true",
        "1",
        "yes",
    }


def build_stratum_entry(
    guid: str,
    result: StratumResult,
    resolved_at: datetime | None,
) -> dict[str, Any]:
    """Build ONE contract-shaped ``SchedulingStratumEntry`` (Phase-1 PR #218).

    The field set is EXACTLY ``{guid, stratum, custom_ghl_id, ghl_calendar_id,
    resolved_at}``.  The Phase-1 entry model is ``extra="forbid"``, so the
    envelope-only fields (``snapshot_source`` / ``source_timestamp`` / the
    server-assigned ``synced_at``) MUST NOT appear on an entry or the sync 422s.
    """
    return {
        "guid": guid,
        "stratum": result.stratum,
        "custom_ghl_id": result.custom_ghl_id,
        "ghl_calendar_id": result.ghl_calendar_id,
        "resolved_at": resolved_at.isoformat() if resolved_at is not None else None,
    }


def build_sync_payload(
    entries: list[dict[str, Any]],
    source_timestamp: str,
) -> dict[str, Any]:
    """Build the ``SchedulingStratumSyncRequest`` envelope (Phase-1 PR #218).

    Field set is EXACTLY ``{snapshot_source, entries, source_timestamp,
    entry_count}``.  Note the stratum contract uses ``snapshot_source`` (NOT the
    account-status ``source``) and requires ``source_timestamp`` + the
    ``entry_count`` integrity witness (the data side 400s on a count mismatch).
    """
    return {
        "snapshot_source": SNAPSHOT_SOURCE,
        "entries": entries,
        "source_timestamp": source_timestamp,
        "entry_count": len(entries),
    }


async def push_stratum_snapshot(
    entries: list[dict[str, Any]],
    source_timestamp: str,
    *,
    dry_run: bool | None = None,
    data_service_url: str | None = None,
    auth_token: str | None = None,
) -> StratumPushResult:
    """Push (or dry-run) a built stratum snapshot batch to autom8y-data.

    ``dry_run`` resolution: an explicit argument wins; otherwise it is derived from
    the gate (dry-run unless ``SCHEDULING_STRATUM_PUSH_ENABLED`` is truthy).  In
    dry-run the contract payload is built and returned for inspection with NO live
    POST.  Non-blocking on the live path (the shared helper swallows all errors).

    Returns:
        A :class:`StratumPushResult` (``payload`` always carries the built batch).
    """
    payload = build_sync_payload(entries, source_timestamp)
    enabled = _is_stratum_push_enabled()
    effective_dry_run = (not enabled) if dry_run is None else dry_run

    if effective_dry_run:
        logger.info(
            "scheduling_stratum_push_dry_run",
            extra={
                "entry_count": len(entries),
                "endpoint": _SYNC_ENDPOINT_PATH,
                "enabled_flag": enabled,
                "reason": "dry_run" if dry_run else "gate_default_off",
            },
        )
        return StratumPushResult(
            pushed=False, dry_run=True, entry_count=len(entries), payload=payload
        )

    base_url = data_service_url or _get_data_service_url()
    token = auth_token or _get_auth_token()
    if not base_url or not token:
        logger.warning(
            "scheduling_stratum_push_skipped",
            extra={
                "reason": "AUTOM8Y_DATA_URL or AUTOM8Y_DATA_API_KEY missing",
                "entry_count": len(entries),
            },
        )
        return StratumPushResult(
            pushed=False, dry_run=False, entry_count=len(entries), payload=payload
        )

    ok = await _push_to_data_service(
        endpoint_path=_SYNC_ENDPOINT_PATH,
        payload=payload,
        response_model=SchedulingStratumSyncResponse,
        metric_dimensions={"entry_count": str(len(entries))},
        log_prefix="scheduling_stratum_push",
        base_url=base_url,
        token=token,
    )
    return StratumPushResult(pushed=ok, dry_run=False, entry_count=len(entries), payload=payload)


def resolve_office_entries(
    extracted_offices: Sequence[ExtractedScheduling],
    *,
    resolved_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Resolve a batch of already-extracted offices into contract-shaped entries (PURE).

    Splits the resolve/build step out of the I/O loop so the snapshot pipeline is
    demonstrable as a dry-run WITHOUT any live Asana call: feed sample
    :class:`ExtractedScheduling` rows and get the exact entries that would be pushed.
    """
    stamp = resolved_at if resolved_at is not None else datetime.now(UTC)
    entries: list[dict[str, Any]] = []
    for office in extracted_offices:
        result = resolve_stratum(office.normalized_inputs, CASCADE_PRIORITY)
        entries.append(build_stratum_entry(office.guid, result, stamp))
    return entries


async def resolve_and_push_snapshot(
    gids: Sequence[str],
    *,
    client: AsanaClient,
    query_engine: QueryEngine,
    dry_run: bool | None = None,
    extract_fn: Callable[..., Awaitable[ExtractedScheduling]] = extract_scheduling_inputs,
    data_service_url: str | None = None,
    auth_token: str | None = None,
) -> StratumPushResult:
    """Iterate offices, resolve each stratum, and push the snapshot (or dry-run).

    Per-office isolation: an extraction/resolution failure for one office is logged
    and skipped, never aborting the whole snapshot.  ``extract_fn`` is injectable so
    the pipeline is exercisable end-to-end without a live Asana call.

    Args:
        gids: The active-office task gids (reuse the cache_warmer office iteration).
        client: ``AsanaClient`` threaded to the per-office extractor.
        query_engine: Substrate ``QueryEngine`` GFR reads through.
        dry_run: Force dry-run; ``None`` defers to the gate (default-off => dry-run).
        extract_fn: The per-office extractor (default the live GFR by-name extractor).
        data_service_url / auth_token: Optional overrides for the data-service POST.
    """
    now = datetime.now(UTC)
    extracted: list[ExtractedScheduling] = []
    for gid in gids:
        try:
            extracted.append(await extract_fn(gid, client=client, query_engine=query_engine))
        except Exception as exc:  # noqa: BLE001 -- per-office isolation
            logger.warning(
                "scheduling_stratum_extract_error",
                extra={"gid": gid, "error": str(exc), "error_type": type(exc).__name__},
            )

    entries = resolve_office_entries(extracted, resolved_at=now)
    return await push_stratum_snapshot(
        entries,
        now.isoformat(),
        dry_run=dry_run,
        data_service_url=data_service_url,
        auth_token=auth_token,
    )


__all__ = [
    "SCHEDULING_STRATUM_PUSH_ENABLED_ENV_VAR",
    "SNAPSHOT_SOURCE",
    "SchedulingStratumSyncResponse",
    "StratumPushResult",
    "build_stratum_entry",
    "build_sync_payload",
    "push_stratum_snapshot",
    "resolve_and_push_snapshot",
    "resolve_office_entries",
]
