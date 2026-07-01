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
    "ExtractedScheduling",
    "derive_enrolled",
    "extract_scheduling_inputs",
    "map_resolved_to_inputs",
]
