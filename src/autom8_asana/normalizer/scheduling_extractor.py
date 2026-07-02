"""Scheduling-source extractor -- the I/O boundary of the Phase-2 normalizer-seam.

Given an office task gid, this module reads the eight provider source values, the
office-global enrollment status, and the office guid off the office via the GFR
dynvocab BY-NAME path (:func:`autom8_asana.resolution.gfr.resolve_async`),
producing the ``normalized_inputs`` dict the PURE
:func:`autom8_asana.normalizer.scheduling_stratum.resolve_stratum` consumes plus the
producer-derived wire-contract-v2 axes (``enrolled`` / ``ghl_ownership``).

ENROLLMENT (R-NEW-1 / FORK-1).  This is the SOLE site that reads the office-global
enrollment status (:data:`CUSTOM_CAL_STATUS_FIELD`) and projects it to the
``enrolled`` bit (:func:`derive_enrolled`) -- the pure projection's re-sourced
enrollment axis (the retired 019 override plane no longer participates).  The
resolver stays orthogonal to it.

This is the ONLY module in the seam that may touch the Asana client / GFR engine.
The pure resolver imports nothing from here -- the dependency points one way
(extractor -> resolver).  By-name resolution is NameNormalizer-robust (case /
space / underscore insensitive), so the eight logical field names below are NOT
hard-coded Asana display strings -- they normalize-match whatever the live custom
field is named (defeats the legacy literal-string brittleness).

GHL ``{duration}_min_ghl_id`` boundary (carried, not dropped): the pure
:func:`derive_effective_ghl_id` already supports the duration fallback.  Wiring the
LIVE read of the duration-keyed ``{word}_min_ghl_id`` field family (which is NOT
one of the eight FORK-UVP source fields and needs ``calendar_duration`` /
``appt_duration`` context) is an explicit, additively-activatable deferral: pass a
resolved ``duration_fallback_id`` to fold it in -- no resolver change required.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from autom8y_log import get_logger

from autom8_asana.normalizer.scheduling_stratum import (
    CASCADE_PRIORITY,
    GHL_OWNERSHIP_NONE,
    derive_effective_ghl_id,
    derive_ghl_ownership,
)
from autom8_asana.resolution.gfr import UnresolvedError, resolve_async

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from typing import Any

    from autom8_asana.client import AsanaClient
    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.resolution.gfr import ResolvedFields

logger = get_logger(__name__)

#: The GFR identity field that carries the office guid (== chiropractors.guid;
#: see ``resolution/gfr/truth_source.py``).  Resolved ONCE here at the guarded
#: write-site; downstream consumers are LB-NO-RERESOLVE.
GUID_FIELD = "company_id"

#: The office-global enrollment-status field (wire contract v2 / R-NEW-1).  Read
#: BY NAME via the same GFR dynvocab path as the eight cascade fields (the monolith
#: ``CustomCalStatus`` binary enum lives on the UnitHolder; autom8y-asana reads it
#: off the field-bearing office task).  Resolved as the enum option NAME string
#: (e.g. "Inactive") or ``None`` when unset/absent -- fed to :func:`derive_enrolled`.
CUSTOM_CAL_STATUS_FIELD = "custom_cal_status"

#: Enrollment-status values (normalized) that gate the office OFF (``enrolled=False``).
#: Faithful to the monolith ``BinaryStatus.get_status`` INACTIVE alias set (contente
#: ``BinaryStatus``).  Everything else -- the ACTIVE aliases, an unknown option, and
#: absent/unset -- follows the legacy ACTIVE default (``enrolled=True``).
_INACTIVE_STATUS_ALIASES: frozenset[str] = frozenset(
    {"inactive", "false", "disabled", "disable", "paused", "pause", "off", "0"}
)

#: The projected posture columns a 1.5.0 offer frame MUST carry for the frame-first
#: extraction to read the posture WITHOUT any live Asana call: the office guid, the
#: office-global enrollment status, and the eight CASCADE_PRIORITY provider sources.
#: A pre-1.5.0 frame (the SWR cache may serve one stale-while-revalidate on the first
#: post-deploy read) LACKS these columns -- detected by :func:`missing_frame_columns`
#: and REFUSED honestly (never fabricated / default-filled). Cf. the offer schema
#: ``dataframes/schemas/offer.py`` (schema_version 1.5.0).
REQUIRED_FRAME_COLUMNS: tuple[str, ...] = (GUID_FIELD, CUSTOM_CAL_STATUS_FIELD, *CASCADE_PRIORITY)


class FrameSchemaLagError(Exception):
    """The offer frame lacks the 1.5.0 posture-projection columns (schema lag).

    Raised by :func:`map_frame_row_to_inputs` (and mirrored by the handler's
    frame-level guard) when a stale-while-revalidate cache serves a PRE-1.5.0 frame
    on the first post-deploy read. The honest posture is to REFUSE -- never fabricate
    posture fields from a frame that does not carry them. The read the refusal
    triggers converges the frame; a subsequent run succeeds.
    """


def _normalize_status(value: str) -> str:
    """Normalize an enrollment-status option name for the INACTIVE-alias match.

    Mirrors the monolith ``FMTS.snake_lower`` shape closely enough for the closed
    binary vocabulary: lower-cased, trimmed, spaces/hyphens folded to underscores.
    """
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def derive_enrolled(custom_cal_status: str | None) -> bool:
    """Project the enrollment bit from the office-global status (R-NEW-1).

    ``enrolled := (status != INACTIVE)``:

      * ``None`` (absent / unset / present-but-null) -> ``True`` (legacy ACTIVE
        default, faithful to the monolith ``CustomCalStatus`` default);
      * a value normalizing to an INACTIVE alias -> ``False`` (de-enrolled);
      * any other value (ACTIVE aliases, an unknown option) -> ``True``.

    De-enrolled offices are still EMITTED (with ``enrolled=False``) -- never omitted
    from the snapshot -- so the data-side thin gate fails them safe to GHL.
    """
    if custom_cal_status is None:
        return True
    return _normalize_status(custom_cal_status) not in _INACTIVE_STATUS_ALIASES


class ExtractedScheduling(NamedTuple):
    """The extractor output fed straight into ``resolve_stratum``.

    ``guid`` is the office identity (resolved once); ``normalized_inputs`` maps each
    of the eight :data:`CASCADE_PRIORITY` source-field names to its value (``None``
    when absent / present-but-null), with the ``custom_ghl_id`` slot already folded
    with any duration fallback via :func:`derive_effective_ghl_id`.

    Wire-contract-v2 producer axes (resolved HERE because this is the only site with
    the office-global enrollment status and the PRE-fold GHL provenance):

      * ``enrolled`` -- from :func:`derive_enrolled` (default ``True`` = legacy ACTIVE);
      * ``ghl_ownership`` -- from :func:`~...scheduling_stratum.derive_ghl_ownership`,
        derived from the RAW (pre-fold) explicit-vs-duration signals.
    """

    guid: str
    normalized_inputs: dict[str, str | None]
    enrolled: bool = True
    ghl_ownership: str = GHL_OWNERSHIP_NONE


def _coerce_text(value: object) -> str | None:
    """Coerce a resolved field value to ``str | None`` (the source fields are text).

    PRESENT_BUT_NULL surfaces as ``None``; a genuine text value passes through; any
    non-string typed value (defensive -- the eight are text custom fields) is
    treated as absent rather than silently stringified into the cascade.
    """
    return value if isinstance(value, str) else None


def map_resolved_to_inputs(
    resolved: ResolvedFields,
    *,
    duration_fallback_id: str | None = None,
) -> ExtractedScheduling:
    """Project a GFR ``ResolvedFields`` row onto the cascade input dict (PURE).

    Reads the eight source fields BY NAME from the single resolved row and the
    ``company_id`` identity; folds the duration fallback into the ``custom_ghl_id``
    slot.  Pure and synchronous so the "maps the eight by-name correctly" gate is
    testable without any live Asana call (construct a ``ResolvedFields`` and assert).

    Args:
        resolved: A single-row ``ResolvedFields`` carrying ``company_id`` plus the
            eight :data:`CASCADE_PRIORITY` fields.
        duration_fallback_id: Optional ``{duration}_min_ghl_id`` value resolved at
            the I/O boundary (see module docstring); folded into ``custom_ghl_id``.

    Returns:
        An :class:`ExtractedScheduling`.

    Raises:
        ValueError: if the row lacks a usable ``company_id`` (no office identity).
    """
    row = resolved.scalar()  # single office -> single row (raises if N != 1)

    guid_field = row.get(GUID_FIELD)
    guid = _coerce_text(guid_field.value) if guid_field is not None else None
    if guid is None:
        raise ValueError(f"scheduling extractor: no resolvable {GUID_FIELD} for gid {resolved.gid}")

    # Enrollment axis (R-NEW-1): re-sourced from the office-global status.  A field
    # genuinely absent from the manifest (dropped by the governed-strict re-resolve)
    # surfaces as ``None`` here -> the legacy ACTIVE default -> enrolled.
    status_prov = row.get(CUSTOM_CAL_STATUS_FIELD)
    custom_cal_status = _coerce_text(status_prov.value) if status_prov is not None else None
    enrolled = derive_enrolled(custom_cal_status)

    normalized_inputs: dict[str, str | None] = {}
    for field in CASCADE_PRIORITY:
        prov = row.get(field)
        normalized_inputs[field] = _coerce_text(prov.value) if prov is not None else None

    # Ownership (ESC-1): derive BEFORE the fold, while the RAW explicit vs duration
    # provenance is still distinguishable (the fold erases which slot won).
    ghl_ownership = derive_ghl_ownership(
        normalized_inputs.get("custom_ghl_id"),
        duration_fallback_id,
    )

    # Fold the duration fallback into the effective GHL id (pure precedence).
    normalized_inputs["custom_ghl_id"] = derive_effective_ghl_id(
        normalized_inputs.get("custom_ghl_id"),
        duration_fallback_id,
    )

    return ExtractedScheduling(
        guid=guid,
        normalized_inputs=normalized_inputs,
        enrolled=enrolled,
        ghl_ownership=ghl_ownership,
    )


def missing_frame_columns(available: Iterable[str]) -> list[str]:
    """Return the :data:`REQUIRED_FRAME_COLUMNS` absent from ``available`` (order-preserved).

    The SCHEMA-LAG guard input: pass the warmed offer frame's column set. A non-empty
    result means the frame is PRE-1.5.0 (the projected posture columns are absent) and
    the snapshot MUST refuse rather than fabricate posture from a frame that cannot
    carry it.
    """
    present = set(available)
    return [c for c in REQUIRED_FRAME_COLUMNS if c not in present]


def map_frame_row_to_inputs(
    row: Mapping[str, Any],
    *,
    duration_fallback_id: str | None = None,
) -> ExtractedScheduling:
    """Project a WARMED offer-frame row dict onto the cascade inputs (PURE, frame-first).

    The frame-first twin of :func:`map_resolved_to_inputs`: instead of a GFR
    ``ResolvedFields`` row, it consumes one offer-frame row (e.g. a ``df.to_dicts()``
    entry) whose keys are the 1.5.0 projected posture columns. Pure and synchronous --
    NO Asana call -- so the whole snapshot is a sub-second Polars pass. REUSES the
    established pure primitives (:func:`derive_enrolled`,
    :func:`~...scheduling_stratum.derive_ghl_ownership`,
    :func:`~...scheduling_stratum.derive_effective_ghl_id`, :data:`CASCADE_PRIORITY`)
    UNCHANGED, so it is provably equivalent to the GFR-path reference for the same
    office data (the wire-v2 axes {enrolled, canonical_destination_url, ghl_ownership}
    are byte-identical).

    SCHEMA-LAG guard (never fabricate): if the row lacks any
    :data:`REQUIRED_FRAME_COLUMNS` key (a pre-1.5.0 frame served by the SWR cache),
    raise :class:`FrameSchemaLagError` -- do NOT ``.get(col, None)`` a missing column
    into a fabricated ACTIVE default. A column PRESENT with a null value is legitimate
    absence (the office genuinely lacks that field) and maps to ``None``.

    Args:
        row: One offer-frame row mapping (all 1.5.0 posture columns present as keys).
        duration_fallback_id: Optional ``{duration}_min_ghl_id`` fallback (additive
            deferral -- the frame path does not yet project the duration family, so
            callers pass ``None``; folded into ``custom_ghl_id`` when supplied).

    Returns:
        An :class:`ExtractedScheduling`.

    Raises:
        FrameSchemaLagError: if the row lacks a projected posture column (schema lag).
        ValueError: if the row carries no usable ``company_id`` (no office identity).
    """
    missing = [c for c in REQUIRED_FRAME_COLUMNS if c not in row]
    if missing:
        raise FrameSchemaLagError(
            f"offer frame row lacks projected posture columns (frame schema pre-1.5.0): {missing}"
        )

    guid = _coerce_text(row.get(GUID_FIELD))
    if guid is None:
        raise ValueError(f"scheduling frame adapter: no resolvable {GUID_FIELD} in frame row")

    # Enrollment axis (R-NEW-1): a null column value -> None -> legacy ACTIVE default.
    enrolled = derive_enrolled(_coerce_text(row.get(CUSTOM_CAL_STATUS_FIELD)))

    normalized_inputs: dict[str, str | None] = {
        field: _coerce_text(row.get(field)) for field in CASCADE_PRIORITY
    }

    # Ownership (ESC-1): derive from the RAW (pre-fold) provenance, then fold.
    ghl_ownership = derive_ghl_ownership(
        normalized_inputs.get("custom_ghl_id"),
        duration_fallback_id,
    )
    normalized_inputs["custom_ghl_id"] = derive_effective_ghl_id(
        normalized_inputs.get("custom_ghl_id"),
        duration_fallback_id,
    )

    return ExtractedScheduling(
        guid=guid,
        normalized_inputs=normalized_inputs,
        enrolled=enrolled,
        ghl_ownership=ghl_ownership,
    )


async def extract_scheduling_inputs(
    gid: str,
    *,
    client: AsanaClient,
    query_engine: QueryEngine,
    duration_fallback_id: str | None = None,
) -> ExtractedScheduling:
    """Resolve the office guid + eight source values for ``gid`` (the I/O boundary).

    Issues a single GFR ``resolve_async`` for ``company_id`` + the eight source
    fields (the entry fetch is the one accounted Asana read; the dynamic tail is
    cache-only).  Defensive degrade: if some source fields are genuinely ABSENT from
    the office manifest (governed-strict ``unknown-field``), they are treated as
    empty and the present subset is re-resolved -- a drifted office never aborts the
    whole snapshot.

    Args:
        gid: The office task gid (the scheduling-field-bearing entity -- Offer per
            the autom8y-asana precedent; see the placement decision in the Phase-2
            ADR).
        client: The ``AsanaClient`` for the entry fetch.
        query_engine: The substrate ``QueryEngine`` GFR reads through.
        duration_fallback_id: Optional duration-keyed GHL fallback (see module docstring).

    Returns:
        An :class:`ExtractedScheduling`.
    """
    requested = [GUID_FIELD, CUSTOM_CAL_STATUS_FIELD, *CASCADE_PRIORITY]
    try:
        resolved = await resolve_async(
            gid, requested, client=client, query_engine=query_engine, scalar=True
        )
    except UnresolvedError as exc:
        absent = set(exc.fields)
        # Identity must resolve; if company_id itself is unresolvable this office has
        # no usable guid -> re-raise (the snapshot loop isolates per-office failures).
        if GUID_FIELD in absent:
            raise
        present = [f for f in requested if f not in absent]
        logger.info(
            "scheduling_extractor_partial_manifest",
            extra={"gid": gid, "absent_fields": sorted(absent)},
        )
        resolved = await resolve_async(
            gid, present, client=client, query_engine=query_engine, scalar=True
        )

    return map_resolved_to_inputs(resolved, duration_fallback_id=duration_fallback_id)


__all__ = [
    "CUSTOM_CAL_STATUS_FIELD",
    "GUID_FIELD",
    "REQUIRED_FRAME_COLUMNS",
    "ExtractedScheduling",
    "FrameSchemaLagError",
    "derive_enrolled",
    "extract_scheduling_inputs",
    "map_frame_row_to_inputs",
    "map_resolved_to_inputs",
    "missing_frame_columns",
]
