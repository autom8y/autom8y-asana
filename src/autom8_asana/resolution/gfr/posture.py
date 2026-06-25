"""GFR runtime posture + provenance assembly (INVARIANT I4, I7; TDD §6.2).

The posture layer turns raw rows + a ``RowsMeta`` freshness side-channel into a
typed ``ResolvedFields`` result, applying the runtime posture rules:

* **Stale = resolved** (INVARIANT I4): a present value satisfies the contract
  even when served past TTL; it is stamped ``status='stale'`` (async refresh is
  the cache layer's concern, not GFR's) rather than treated as a miss.
* **All-or-nothing on the field SET** (INVARIANT I4): if the owning frame is
  genuinely empty (no rows) for a requested field, the WHOLE call raises
  ``UnresolvedError(reason="empty-frame")`` — never a partial result.
* **Provenance from the side-channel** (INVARIANT I7): per-field
  ``{value, status, source, as_of}`` is derived from ``RowsMeta``
  (``query/models.py:368-417`` — ``freshness`` / ``stale_served`` /
  ``data_age_seconds``), NEVER fabricated. ``as_of`` is the frame watermark
  (tier-1) or the data-service timestamp (tier-2), passed in by the engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import (
    FieldStatus,
    FieldWithProvenance,
    ResolvedFields,
    TruthTier,
)

if TYPE_CHECKING:
    from datetime import datetime

    from autom8_asana.query.models import RowsMeta

logger = get_logger(__name__)


def derive_status(meta: RowsMeta) -> FieldStatus:
    """Map the ``RowsMeta`` freshness side-channel to a ``FieldStatus``.

    ``stale_served`` is the single unambiguous "was this read served stale?"
    signal (``query/models.py`` ADR-serve-stale-within-bound). A stale-within-
    bound serve is STILL resolved (INVARIANT I4) — it maps to ``STALE``, not a
    miss. The textual ``freshness`` enum is consulted as a fallback when
    ``stale_served`` is its default.
    """
    if meta.stale_served:
        return FieldStatus.STALE
    freshness = (meta.freshness or "").lower()
    if freshness in {"stale", "lkg", "approaching_stale"}:
        return FieldStatus.STALE
    return FieldStatus.FRESH


def assemble_rows(
    *,
    gid: str,
    fields: list[str],
    data: list[dict[str, object]],
    meta: RowsMeta,
    source: TruthTier,
    as_of: datetime | None,
) -> ResolvedFields:
    """Assemble a ``ResolvedFields`` result from rows + freshness metadata.

    Args:
        gid: The entry gid being resolved.
        fields: The requested field names (the SET subject to all-or-nothing).
        data: Result rows (one dict per entity) from ``execute_rows``.
        meta: ``RowsMeta`` freshness side-channel for the read.
        source: Provenance tier (CACHE or VERIFIED) to stamp on each field.
        as_of: Serving timestamp (frame watermark or data-service response time).

    Returns:
        A row-set native ``ResolvedFields`` (1..N rows, INVARIANT I5).

    Raises:
        UnresolvedError(reason="empty-frame"): if the owning frame is genuinely
            empty (no rows) — all-or-nothing on the field SET (INVARIANT I4).
    """
    if not data:
        # A genuinely empty frame for a requested field fails the whole SET.
        logger.info(
            "GFR posture: empty frame",
            extra={"gid": gid, "fields": fields, "entity_type": meta.entity_type},
        )
        raise UnresolvedError(fields=list(fields), reason="empty-frame")

    status = derive_status(meta)
    rows: list[dict[str, FieldWithProvenance]] = []
    for row in data:
        resolved_row: dict[str, FieldWithProvenance] = {}
        for field in fields:
            resolved_row[field] = FieldWithProvenance(
                value=row.get(field),
                status=status,
                source=source,
                as_of=as_of,
            )
        rows.append(resolved_row)

    logger.debug(
        "GFR posture: assembled rows",
        extra={
            "gid": gid,
            "row_count": len(rows),
            "status": status.value,
            "source": source.value,
        },
    )
    return ResolvedFields(gid=gid, rows=rows, row_count=len(rows))
