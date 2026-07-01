"""PURE scheduling-stratum resolver -- the cascade core of the Phase-2 ACL.

This module reconceives the legacy CustomCalUrl cascade (the monolith
``autom8`` text-field model, cascade at lines 198-219) as a declarative,
side-effect-free function: a first-non-empty-wins walk over the eight provider
source fields, producing the resolved scheduling stratum plus the derived GHL
fail-closed fallback coordinates.

PURITY CONTRACT (TL-A1 / B1 / B2 / B5 -- enforced by the normalizer fitness tests).
This module is import-pure and side-effect-free by construction:

  * it pulls in NO persistence layer (no ORM, no DB query module);
  * it pulls in NO service client, NO HTTP library, and NO AWS SDK;
  * it spawns NO concurrency primitive -- the monolith resolver joined a worker
    pool inside its field getter; the reconception does none of that;
  * it performs NO attribute mutation (no setter / update call, no field write);
  * it performs NO identity re-resolution (no guid-resolve helper, no phone join,
    no monolith MySQL chiropractors query).

The cascade is DATA (:data:`CASCADE_PRIORITY`), not a hard-coded branch chain
(defeats B3): the resolver takes the cascade as an argument and indexes the
declarative :data:`SOURCE_TO_STRATUM` map -- no provider name ever appears in a
branch condition.  The legacy active/inactive status gate is ABSENT (defeats B4):
provider identity is resolved from the raw values only.  In the monolith each
source-field getter was gated by an inactive-status check that nulled the value;
that active/inactive decision is REPLACED by the enrollment plane (the autom8y-data
enrollment record's fail-closed default + operator override) and is NOT this
resolver's concern.  No follow-up booking classification (defeats B6).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# ---------------------------------------------------------------------------
# Ported provider URL prefixes (byte-faithful to the monolith CustomCalUrl model,
# constant block lines 21-24) so the formatters below are a faithful port.
# ---------------------------------------------------------------------------
GHL_PREFIX = "https://api.leadconnectorhq.com/widget/booking"
GHL_PREFIX_ALT = "https://api.leadconnectorhq.com/widget/bookings"
TRACKSTAT_PREFIX = "https://clinic.patienthealthcenters.org"
SKED_PREFIX = "https://portal.sked.life/new-patient"

# ---------------------------------------------------------------------------
# Declarative cascade configuration (defeats B3 -- no hard-coded branch chain).
# ---------------------------------------------------------------------------

#: The scheduling-source cascade in priority order.  The first source field whose
#: value is non-empty wins and selects that office's stratum.  Ordering and
#: membership are faithful to the monolith cascade resolver (lines 198-219), with
#: the GHL terminal expressed as the raw ``custom_ghl_id`` source field (its URL is
#: derived, never declared).  The resolver consumes this as an argument so the
#: cascade is configuration, never control flow.
CASCADE_PRIORITY: list[str] = [
    "reviewwave_id",
    "acuity_cal_url",
    "calendly_url",
    "janeapp_url",
    "ehr_cal_url",
    "trackstat_id",
    "sked_id",
    "custom_ghl_id",
]

#: Source-field -> stratum mapping.  Values are EXACTLY the autom8y-data
#: ``SchedulingStratumEnum`` members (Phase-1 PR #218); drift here would fail the
#: contract-match assertion.  The map IS the cascade-to-stratum translation, so the
#: resolver never names a provider in a branch condition (defeats B3).
SOURCE_TO_STRATUM: dict[str, str] = {
    "reviewwave_id": "reviewwave",
    "acuity_cal_url": "acuity",
    "calendly_url": "calendly",
    "janeapp_url": "janeapp",
    "ehr_cal_url": "ehr",
    "trackstat_id": "trackstat",
    "sked_id": "sked",
    "custom_ghl_id": "ghl",
}

#: All-eight-empty terminal.  No provider signal is present; the resolver reports
#: ``inactive``.  Whether an inactive office is served the GHL fallback or held for
#: re-enrollment is the enrollment plane's decision, not the resolver's.
INACTIVE_STRATUM = "inactive"


class StratumResult(NamedTuple):
    """The resolved stratum plus the derived GHL fail-closed coordinates.

    Field set is fixed to the Phase-1 snapshot-entry contract surface:
    ``stratum`` + ``custom_ghl_id`` + ``ghl_calendar_id`` (the GHL coordinates are
    carried independent of the winning stratum so the autom8y-data read route's
    beyond-TTL GHL fail-closed fallback is always populated).
    """

    stratum: str
    custom_ghl_id: str | None
    ghl_calendar_id: str | None


def _is_empty(value: str | None) -> bool:
    """First-non-empty predicate: ``None`` or whitespace-only counts as empty.

    Mirrors the monolith cascade's truthiness test while also treating a
    whitespace-only Asana text value as absent.
    """
    return value is None or value.strip() == ""


def format_trackstat_url(raw_id: str) -> str:
    """Port of the monolith TrackStat formatter (CustomCalUrl model, lines 184-189).

    Pure: ``raw id -> embed URL``.  An already-prefixed value passes through; a
    value already carrying a query string is appended with ``&clinic=``; otherwise
    the canonical ``/embedded/book?clinic=`` path is built.
    """
    if raw_id.startswith(TRACKSTAT_PREFIX):
        return raw_id
    if "?" in raw_id:
        return f"{TRACKSTAT_PREFIX}&clinic={raw_id}"
    return f"{TRACKSTAT_PREFIX}/embedded/book?clinic={raw_id}"


def format_sked_url(raw_id: str) -> str:
    """Port of the monolith Sked formatter (CustomCalUrl model, lines 191-196).

    Pure: ``raw id -> portal URL``.  Prefix-passthrough / query-append / canonical
    ``?key=`` build, byte-faithful to the monolith.
    """
    if raw_id.startswith(SKED_PREFIX):
        return raw_id
    if "?" in raw_id:
        return f"{SKED_PREFIX}&key={raw_id}"
    return f"{SKED_PREFIX}?key={raw_id}"


def build_ghl_url(calendar_id: str, *, prefer_plural: bool = False) -> str:
    """Port of the monolith ``_build_ghl_url`` (CustomCalUrl model, lines 36-39).

    Pure: ``calendar id -> GHL widget booking URL``.  ``prefer_plural`` selects the
    ``/bookings`` variant (the monolith's plural-widget support).
    """
    prefix = GHL_PREFIX_ALT if prefer_plural else GHL_PREFIX
    return f"{prefix}/{calendar_id}"


def derive_effective_ghl_id(
    custom_ghl_id: str | None,
    duration_fallback_id: str | None = None,
) -> str | None:
    """Resolve the effective GHL calendar id with the monolith's empty-fallback.

    Faithful port of the monolith offer GHL-calendar resolver (lines 1090-1110): the
    explicit ``custom_ghl_id`` wins; when it is empty, the duration-specific
    ``{duration}_min_ghl_id`` value is the fallback.

    BOUNDARY (carried, not dropped -- per Phase-2 spec): the ``{duration}_min_ghl_id``
    field READ needs offer-duration context (the duration ints + the duration-keyed
    source fields), which lives at the I/O boundary.  The extractor resolves
    ``duration_fallback_id`` and passes it here; this function is PURE and only
    applies the precedence.  Passing ``None`` reduces to "explicit id only".
    """
    if not _is_empty(custom_ghl_id):
        assert custom_ghl_id is not None  # narrowed by _is_empty
        return custom_ghl_id.strip()
    if not _is_empty(duration_fallback_id):
        assert duration_fallback_id is not None  # narrowed by _is_empty
        return duration_fallback_id.strip()
    return None


def resolve_stratum(
    normalized_inputs: Mapping[str, str | None],
    cascade: Sequence[str],
) -> StratumResult:
    """Resolve an office's scheduling stratum from its eight source values (PURE).

    First-non-empty-in-``cascade`` wins and selects the stratum via
    :data:`SOURCE_TO_STRATUM`; all-empty yields :data:`INACTIVE_STRATUM`.  The GHL
    fail-closed coordinates are derived from the ``custom_ghl_id`` slot and carried
    on EVERY result (independent of the winning stratum) so the autom8y-data read
    route can serve the beyond-TTL GHL fallback for any office.

    The ``custom_ghl_id`` slot is expected to already hold the *effective* GHL id
    (the extractor applies :func:`derive_effective_ghl_id` with the duration
    fallback before calling); this function does not re-derive it.

    Args:
        normalized_inputs: ``source_field_name -> value`` (value may be ``None`` or
            whitespace).  Keys are the :data:`CASCADE_PRIORITY` field names.
        cascade: The priority-ordered source-field list to walk (normally
            :data:`CASCADE_PRIORITY`).  Each member MUST be a key of
            :data:`SOURCE_TO_STRATUM`.

    Returns:
        A :class:`StratumResult` ``(stratum, custom_ghl_id, ghl_calendar_id)``.
    """
    stratum = INACTIVE_STRATUM
    for source_field in cascade:
        if not _is_empty(normalized_inputs.get(source_field)):
            stratum = SOURCE_TO_STRATUM[source_field]
            break

    # GHL fail-closed coordinates -- always carried when an effective GHL id exists,
    # regardless of which stratum won (the read route serves these beyond TTL).
    effective_ghl = normalized_inputs.get("custom_ghl_id")
    if _is_empty(effective_ghl):
        return StratumResult(stratum=stratum, custom_ghl_id=None, ghl_calendar_id=None)

    assert effective_ghl is not None  # narrowed by _is_empty
    custom_ghl_id = effective_ghl.strip()
    return StratumResult(
        stratum=stratum,
        custom_ghl_id=custom_ghl_id,
        ghl_calendar_id=build_ghl_url(custom_ghl_id),
    )
