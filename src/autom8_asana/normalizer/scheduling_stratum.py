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
branch condition.  The legacy active/inactive status gate is ABSENT from the
cascade walk (defeats B4): provider identity is resolved from the raw values
only.  In the monolith each source-field getter was gated by an inactive-status
check that nulled the value; that active/inactive decision is NOT conflated into
this resolver's cascade.

ENROLLMENT (FORK-1, wire contract v2).  The pure projection re-sources enrollment
from the office-global Asana enrollment-status enum (the monolith ``CustomCalStatus``
binary field) -- read at the EXTRACTOR
(:mod:`~autom8_asana.normalizer.scheduling_extractor`), never here.  The retired 019
operator-override plane no longer participates.  Enrollment is ORTHOGONAL to the
cascade: the resolver CARRIES the producer-derived ``enrolled`` bit (and the
``ghl_ownership`` axis) through onto :class:`StratumResult` without gating the
cascade walk on it, so the two axes stay independent (a de-enrolled office keeps
its resolved provider category).  No follow-up booking classification (defeats B6).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

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
#: ``inactive``.  Whether an inactive office is served the GHL fallback is the
#: data-side thin gate's decision, not the resolver's.
INACTIVE_STRATUM = "inactive"

# ---------------------------------------------------------------------------
# GHL-ownership vocabulary (wire contract v2 / ESC-1).  A CLOSED trichotomy that
# records WHICH GHL slot supplied the effective calendar id, so the downstream
# consumer knows which Webflow embed to push (client-owned vs internal-duration).
# ---------------------------------------------------------------------------

#: The office's explicit ``custom_ghl_id`` won ``derive_effective_ghl_id``.
GHL_OWNERSHIP_CLIENT_OWNED = "client_owned"
#: The appointment-duration-keyed ``{duration}_min_ghl_id`` fallback won.
GHL_OWNERSHIP_INTERNAL_DURATION = "internal_duration"
#: Neither GHL slot supplied an id.
GHL_OWNERSHIP_NONE = "none"

#: The closed ownership value-set (drift guard target for the wire contract).
GHL_OWNERSHIP_VALUES: frozenset[str] = frozenset(
    {
        GHL_OWNERSHIP_CLIENT_OWNED,
        GHL_OWNERSHIP_INTERNAL_DURATION,
        GHL_OWNERSHIP_NONE,
    }
)


class StratumResult(NamedTuple):
    """The resolved posture: stratum + GHL coordinates + the wire-contract-v2 axes.

    v1 surface (unchanged): ``stratum`` + ``custom_ghl_id`` + ``ghl_calendar_id``
    (the GHL coordinates are carried independent of the winning stratum so the
    autom8y-data read route's beyond-TTL GHL fail-closed fallback is always
    populated).

    v2 additions (FORK-1 Option 2, thick-wire / projection-complete):

      * ``enrolled`` -- the producer-derived enrollment bit (from the Asana
        enrollment-status enum, resolved at the extractor).  A de-enrolled office
        STAYS PRESENT with ``enrolled=False`` -- never omitted from the snapshot.
        Defaults ``True`` (the legacy ACTIVE default) so a cascade-only caller
        that does not pass it fails to the legacy-faithful posture, not a crash.
      * ``canonical_destination_url`` -- the cascade winner's booking URL, built
        via the RESIDENT formatters (:func:`_build_canonical_url`); ``None`` when
        no provider resolves.
      * ``ghl_ownership`` -- the closed :data:`GHL_OWNERSHIP_VALUES` trichotomy
        (from :func:`derive_ghl_ownership`); defaults :data:`GHL_OWNERSHIP_NONE`.

    The two v2 axes ``enrolled`` / ``ghl_ownership`` are ORTHOGONAL to the cascade
    and are supplied by the extractor (the only site with the Asana enrollment
    status and the PRE-fold GHL provenance); the resolver carries them through.
    """

    stratum: str
    custom_ghl_id: str | None
    ghl_calendar_id: str | None
    enrolled: bool = True
    canonical_destination_url: str | None = None
    ghl_ownership: str = GHL_OWNERSHIP_NONE


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


def derive_ghl_ownership(
    custom_ghl_id: str | None,
    duration_fallback_id: str | None = None,
) -> str:
    """Classify GHL calendar ownership (wire contract v2 / ESC-1).

    Mirrors :func:`derive_effective_ghl_id`'s explicit-wins-over-duration
    precedence, reporting WHICH slot supplied the effective id:

      * explicit ``custom_ghl_id`` non-empty -> :data:`GHL_OWNERSHIP_CLIENT_OWNED`;
      * else duration fallback non-empty      -> :data:`GHL_OWNERSHIP_INTERNAL_DURATION`;
      * neither                               -> :data:`GHL_OWNERSHIP_NONE`.

    MUST be called with the RAW (pre-fold) signals -- the extractor invokes this
    BEFORE folding the effective id into the ``custom_ghl_id`` slot, because the
    fold erases the provenance the trichotomy needs.
    """
    if not _is_empty(custom_ghl_id):
        return GHL_OWNERSHIP_CLIENT_OWNED
    if not _is_empty(duration_fallback_id):
        return GHL_OWNERSHIP_INTERNAL_DURATION
    return GHL_OWNERSHIP_NONE


#: Source fields whose winning value is FORMATTED into a canonical URL by a
#: RESIDENT formatter (the raw stored value is an id, not a URL).  Every other
#: non-GHL winner (reviewwave / acuity / calendly / janeapp / ehr) already carries
#: an external destination URL and is forwarded raw -- byte-faithful to the monolith
#: ``CustomCalUrl`` cascade model (``_resolve_from_cascade`` lines 203-216, where
#: JaneApp/EHR are the DIRECT categories that forward the external destination).
_URL_FORMATTERS: dict[str, Callable[[str], str]] = {
    "trackstat_id": format_trackstat_url,
    "sked_id": format_sked_url,
}


def _build_canonical_url(
    winning_field: str | None,
    winning_value: str | None,
    effective_ghl_id: str | None,
) -> str | None:
    """Build the cascade winner's canonical destination URL (wire contract v2).

    Mirrors the monolith ``CustomCalUrl`` cascade's per-category destination
    (``_resolve_from_cascade``):

      * no winner (inactive)             -> ``None``;
      * ``custom_ghl_id`` (GHL winner)   -> :func:`build_ghl_url` of the effective id;
      * ``trackstat_id`` / ``sked_id``   -> the RESIDENT formatter of the raw id;
      * every other provider             -> the raw external destination forwarded
        (reviewwave / acuity / calendly and the DIRECT janeapp / ehr categories).

    Formatters are REUSED, never duplicated.
    """
    if winning_field is None or winning_value is None:
        return None
    if winning_field == "custom_ghl_id":
        return build_ghl_url(effective_ghl_id) if effective_ghl_id else None
    formatter = _URL_FORMATTERS.get(winning_field)
    if formatter is not None:
        return formatter(winning_value)
    return winning_value


def resolve_stratum(
    normalized_inputs: Mapping[str, str | None],
    cascade: Sequence[str],
    *,
    enrolled: bool = True,
    ghl_ownership: str = GHL_OWNERSHIP_NONE,
) -> StratumResult:
    """Resolve an office's scheduling posture from its source values (PURE).

    First-non-empty-in-``cascade`` wins and selects the stratum via
    :data:`SOURCE_TO_STRATUM`; all-empty yields :data:`INACTIVE_STRATUM`.  The
    winner's ``canonical_destination_url`` is built via :func:`_build_canonical_url`
    (RESIDENT formatters; ``None`` on the inactive terminal).  The GHL fail-closed
    coordinates are derived from the ``custom_ghl_id`` slot and carried on EVERY
    result (independent of the winning stratum) so the autom8y-data read route can
    serve the beyond-TTL GHL fallback for any office.

    The ``custom_ghl_id`` slot is expected to already hold the *effective* GHL id
    (the extractor applies :func:`derive_effective_ghl_id` with the duration
    fallback before calling); this function does not re-derive it.

    ``enrolled`` / ``ghl_ownership`` are the wire-contract-v2 axes.  They are
    ORTHOGONAL to the cascade and supplied by the extractor (the only site with
    the Asana enrollment status and the pre-fold GHL provenance); the resolver
    carries them through unchanged.  Their defaults (``True`` /
    :data:`GHL_OWNERSHIP_NONE`) are the legacy-faithful posture for a cascade-only
    caller that omits them.

    Args:
        normalized_inputs: ``source_field_name -> value`` (value may be ``None`` or
            whitespace).  Keys are the :data:`CASCADE_PRIORITY` field names.
        cascade: The priority-ordered source-field list to walk (normally
            :data:`CASCADE_PRIORITY`).  Each member MUST be a key of
            :data:`SOURCE_TO_STRATUM`.
        enrolled: Producer-derived enrollment bit (default ``True`` = legacy ACTIVE).
        ghl_ownership: Producer-derived ownership (default :data:`GHL_OWNERSHIP_NONE`).

    Returns:
        A :class:`StratumResult`.
    """
    stratum = INACTIVE_STRATUM
    winning_field: str | None = None
    winning_value: str | None = None
    for source_field in cascade:
        candidate = normalized_inputs.get(source_field)
        if not _is_empty(candidate):
            assert candidate is not None  # narrowed by _is_empty
            stratum = SOURCE_TO_STRATUM[source_field]
            winning_field = source_field
            winning_value = candidate.strip()
            break

    # GHL fail-closed coordinates -- always carried when an effective GHL id exists,
    # regardless of which stratum won (the read route serves these beyond TTL).
    effective_ghl = normalized_inputs.get("custom_ghl_id")
    if _is_empty(effective_ghl):
        custom_ghl_id = None
    else:
        assert effective_ghl is not None  # narrowed by _is_empty
        custom_ghl_id = effective_ghl.strip()
    ghl_calendar_id = build_ghl_url(custom_ghl_id) if custom_ghl_id else None

    return StratumResult(
        stratum=stratum,
        custom_ghl_id=custom_ghl_id,
        ghl_calendar_id=ghl_calendar_id,
        enrolled=enrolled,
        canonical_destination_url=_build_canonical_url(winning_field, winning_value, custom_ghl_id),
        ghl_ownership=ghl_ownership,
    )
