"""The id-walk SUPPLY for the identity-activity substrate.

Per ADR-identity-activity-substrate (2026-09-04) §1.13: the id walk into the Asana
hierarchy is the SUPPLY for the substrate's id-walk-supplied families -- **never the
store**. This module is the ``[asana]``-side half of that supply: it walks upward
from an offer gid and RETURNS evidence objects. It writes nothing, mutates nothing,
and holds no state. Seat A (the appender, custody ``[data]``) consumes what this
returns and appends it; seat A never writes to ``[asana]`` (§14.1).

WHAT THIS MODULE SUPPLIES (ADR §12.1, §14.2)
--------------------------------------------
``asana_business``        -- the Business card gid           (§14.2 row 1, grain G-1)
``business_display_name`` -- the Business card name          (§14.2 row 2, grain G-1)
``offer``                 -- the entry offer gid             (§14.2 row 6, grain G-3)

THE FOUR RULES THIS MODULE IS BUILT AROUND
-------------------------------------------
1. **CW-S09-3 is EXERCISED, not inherited.** The walk delegates Business
   identification to a five-tier detector and the traversal path turns Tier 4
   (subtask-name structure inspection) ON by explicit choice. Tier 4 concludes
   BUSINESS from three lowercased subtask names and SELF-FLAGS the conclusion
   ``needs_healing=True`` -- at ``CONFIDENCE_TIER_4 = 0.9``, the SECOND-HIGHEST
   confidence in the set. **A confidence guard would wave a self-flagged row
   through.** This module therefore guards on the FLAG, never on the number:
   :func:`classify_identification` does not read ``confidence`` at all, and a
   self-flagged identification is published as a TYPED ABSENCE, never as a value.

2. **SET, never PICK.** If the walk yields more than one candidate Business
   ancestor the supply returns the SET with ``match_count`` and publishes NO value.
   It does not choose. The candidates stay reachable on
   :class:`IdentitySupply.candidates` so the appender can append N observations and
   let the fold grade them ``disputed`` (§14.3 case B).

3. **W-7 STRICT -- a display string may decide STATE, never IDENTITY.**
   ``asana_business`` (the identity) is the walked GID. ``business_display_name``
   is a separate family whose value is carried BYTE-VERBATIM and is never consulted
   to derive, key, filter or disambiguate any identity. K-A applies wherever a
   string decides state: exact match, no strip, no case-fold, refuse on unknown.

4. **The cascade is never consulted.** ``dataframes/views/cascade_view.py`` root
   substitution is FORBIDDEN as a supplier for every key member at every grain
   (grain ruling §3.2; ADR §3.3 -- ``cascade`` is a declared member of the closed
   supplier set precisely so its emission is a visible violation). This module
   neither imports it nor reaches it.

FIELDS THIS SEAT DOES NOT MINT
-------------------------------
``confidence`` / ``refuted_basis`` / ``refuted_by`` are DERIVED by seat F, the fold
(§14.2 rows 11-12: "DERIVED, not minted"). ``shared`` / ``shared_count`` are
fleet-denominator facts only a fleet holder can compute (§14.2 row 14).
``corroborated_by`` / ``lineage`` are assembled where the cross-check legs live.
``fold_version`` / ``fold_at`` belong to the fold. An appender that minted any of
them would be a second writer for a fact that already has one, so :class:`Evidence`
deliberately has no such attribute -- the seat boundary is enforced by the type,
not by a comment.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.errors import HydrationError

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

__all__ = [
    "AbsentReason",
    "BusinessCandidate",
    "Evidence",
    "Grain",
    "IdentitySupply",
    "Population",
    "RATIFIED_ABSENT_REASONS",
    "SystemOfRecord",
    "Supplier",
    "TIER4_ABSENT_REASON",
    "TIER_STRUCTURE_INSPECTION",
    "WalkOutcome",
    "build_identity_supply",
    "classify_identification",
    "supply_identity_evidence_async",
    "walk_business_candidates_async",
]

logger = get_logger(__name__)

#: The detection tier whose conclusion the detector itself flags as needing
#: healing (subtask-name structure inspection). Named as a constant so the guard
#: reads as a TIER test and can never be mistaken for a confidence threshold.
TIER_STRUCTURE_INSPECTION = 4

#: Basis version of this supplier's rules. Bump when the disposition rules below
#: change, so an appended observation can be re-graded against the rule that made it.
BASIS_VERSION = 1

#: Hop-shape label -- a SHAPE, never a value and never a name (ADR §12.1a
#: ``supplier_path``).
SUPPLIER_PATH_UPWARD_WALK = "entry->parent*->business"


class Supplier(enum.StrEnum):
    """ADR §3.3 -- the CLOSED set of SIX. Required even when ``value`` is null.

    ``CASCADE`` is a declared member and is FORBIDDEN as a supplier: it is present
    so that an emission of it is a visible conflict rather than an unrepresentable
    one. This module never emits it.
    """

    PRODUCER_HELD = "producer_held"
    ID_WALK = "id_walk"
    RESOLUTION_CONTEXT = "resolution_context"
    RESOLVE_ON_PHONE = "resolve_on_phone"
    PARENT_REF = "parent_ref"
    CASCADE = "cascade"


class AbsentReason(enum.StrEnum):
    """ADR §3.5 -- the typed-absence set, BASE + ID-WALK, plus one PROPOSED member.

    A closed set that may drift from its emitter is not a contract, it is a comment
    (E-2), so :data:`RATIFIED_ABSENT_REASONS` pins the ratified members and the
    module's tests assert this enum against it.
    """

    # --- BASE (every family, every supplier) ---
    NOT_THIS_SURFACE = "not_this_surface"
    PRODUCER_INPUT_ABSENT = "producer_input_absent"
    RESOLVER_UNAVAILABLE = "resolver_unavailable"
    SYSTEM_OF_RECORD_RETIRED = "system_of_record_retired"
    UNDECIDABLE = "undecidable"

    # --- ID-WALK ---
    PARENT_ABSENT = "parent_absent"
    ANCESTOR_FIELD_ABSENT = "ancestor_field_absent"
    WALK_ROOT_WITHOUT_BUSINESS = "walk_root_without_business"
    WALK_CYCLE = "walk_cycle"
    WALK_DEPTH_EXCEEDED = "walk_depth_exceeded"

    # --- PROPOSED, NOT YET RATIFIED ---
    # `tier4_needs_healing` is NOT one of the five ID-WALK members ratified at ADR
    # rev 2 §3.5. It is proposed here because the ratified set has no member that
    # says "the walk reached a node, the detector typed it BUSINESS, and the
    # detector flagged its own conclusion as needing healing" -- which is a
    # different fact from every ratified member. The in-set fallback if the
    # landing seat declines the extension is `UNDECIDABLE`: flip
    # :data:`TIER4_ABSENT_REASON` and nothing else changes.
    TIER4_NEEDS_HEALING = "tier4_needs_healing"


#: The ADR rev-2 §3.5 ratified members (BASE + ID-WALK), pinned so that any drift
#: between this emitter and the ADR is a test failure rather than a silent widening.
RATIFIED_ABSENT_REASONS: frozenset[str] = frozenset(
    {
        "not_this_surface",
        "producer_input_absent",
        "resolver_unavailable",
        "system_of_record_retired",
        "undecidable",
        "parent_absent",
        "ancestor_field_absent",
        "walk_root_without_business",
        "walk_cycle",
        "walk_depth_exceeded",
    }
)

#: The reason emitted for a self-flagged Tier-4 identification. ONE line to flip to
#: :attr:`AbsentReason.UNDECIDABLE` if the wave-2 landing seat declines the
#: proposed sixth ID-WALK member.
TIER4_ABSENT_REASON = AbsentReason.TIER4_NEEDS_HEALING


class Grain(enum.StrEnum):
    """ADR §12.1a / grain ruling §1.2."""

    G_0 = "G-0"
    G_1 = "G-1"
    G_2 = "G-2"
    G_2A = "G-2a"
    G_3 = "G-3"


class Population(enum.StrEnum):
    """The DENOMINATOR a fact was computed over (ADR §12.1a)."""

    FLEET = "fleet"
    ROSTER = "roster"


class SystemOfRecord(enum.StrEnum):
    """ADR §12.1a."""

    STRIPE = "stripe"
    META = "meta"
    ASANA = "asana"
    DATA = "data"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Evidence:
    """One evidence object, one family, as SUPPLIED (ADR §3.1 / §12.1a).

    ``value`` and ``absent_reason`` are XOR: exactly one is non-null (E-0 -- an
    omitted key and a fabricated value are the two failure modes the shape exists
    to make impossible).

    ``refuted`` is ALWAYS emitted and is ALWAYS ``False`` from this seat: an
    observation is never self-refuted, and refutation is published by the fold
    (§14.2 row 11). See the module docstring for the fields this seat does not mint.

    ``total_match_count`` (the PRE-filter total) always equals ``match_count`` here,
    BY CONSTRUCTION rather than by coincidence: the id walk does not filter. It
    returns every Business ancestor it confirmed, so there is no pre-filter
    population that differs from the post-filter one, and no total to erase. The
    field is emitted rather than nulled so a reader never has to guess which of
    those two facts a null meant.
    """

    family: str
    value: str | None
    absent_reason: AbsentReason | None
    supplier: Supplier
    supplier_path: str | None
    detection_tier: int | None
    needs_healing: bool | None
    grain: Grain
    population: Population
    system_of_record: SystemOfRecord
    match_count: int | None
    total_match_count: int | None
    set_disclosed: bool
    refuted: bool
    observed_at: datetime | None
    basis_version: int

    def __post_init__(self) -> None:
        if (self.value is None) == (self.absent_reason is None):
            raise ValueError(
                f"E-0 violated for family {self.family!r}: exactly one of `value` "
                f"/ `absent_reason` must be non-null "
                f"(value={self.value!r}, absent_reason={self.absent_reason!r})"
            )
        if self.supplier is Supplier.CASCADE:
            raise ValueError(
                "`cascade` is FORBIDDEN as a supplier (ADR §3.3); it fails "
                "silently-WRONG and substitutes a well-formed value no caller "
                "can detect"
            )
        if self.observed_at is not None and self.observed_at.tzinfo is None:
            raise ValueError(
                f"`observed_at` must be offset-aware UTC, got naive {self.observed_at!r} (NB-6)"
            )


@dataclass(frozen=True, slots=True)
class BusinessCandidate:
    """One candidate Business ancestor, WITH the detection that produced it.

    ``name`` is carried byte-verbatim off the Asana card. It is a display string
    and decides STATE only (W-7 STRICT); it is never a key member, never folded,
    and never used to reach ``gid``.
    """

    gid: str
    name: str | None
    detection_tier: int | None
    needs_healing: bool | None


@dataclass(frozen=True, slots=True)
class WalkOutcome:
    """What the walk saw. No dispositions applied yet -- that is the assembler's job.

    ``failure`` is the TYPED walk failure (one of the four ID-WALK failure modes),
    or ``None`` when the walk terminated normally. The walk's three raise sites
    used to collapse into one untyped exception; ``HydrationError.walk_failure``
    keeps them apart.
    """

    offer_gid: str | None
    candidates: tuple[BusinessCandidate, ...]
    failure: AbsentReason | None


@dataclass(frozen=True, slots=True)
class IdentitySupply:
    """What the supply hands seat A. Evidence objects plus the candidate SET."""

    asana_business: Evidence
    business_display_name: Evidence
    offer: Evidence
    candidates: tuple[BusinessCandidate, ...]

    def families(self) -> dict[str, Evidence]:
        """The supplied families, keyed by family name."""
        return {
            "asana_business": self.asana_business,
            "business_display_name": self.business_display_name,
            "offer": self.offer,
        }


def classify_identification(
    detection_tier: int | None,
    needs_healing: bool | None,
) -> AbsentReason | None:
    """Return a typed absence when an identification must NOT be published as a value.

    **THE GUARD IS ON THE FLAG AND THE TIER, NEVER ON THE CONFIDENCE NUMBER.**
    ``confidence`` is not a parameter of this function and cannot be one. Tier 4
    carries ``CONFIDENCE_TIER_4 = 0.9`` -- the second-highest value in the set, above
    Tier 3's ``0.8`` and far above Tier 2's ``0.6`` -- so a consumer screening on
    confidence would read a self-flagged structure-inspection identification as
    near-certain and let it through. The number says the opposite of what the flag
    says. Because this function never reads the number, moving ``CONFIDENCE_TIER_4``
    to any value cannot change any disposition here.

    Returns:
        ``None`` when the identification may be published as a value, or the typed
        absence that must be published instead.
    """
    if detection_tier is None:
        # The supplier could not say how it identified the node. An undisclosed
        # basis is not a clean identification.
        return AbsentReason.UNDECIDABLE
    if needs_healing or detection_tier == TIER_STRUCTURE_INSPECTION:
        return TIER4_ABSENT_REASON
    return None


def _absent(
    family: str,
    reason: AbsentReason,
    *,
    grain: Grain,
    observed_at: datetime,
    detection_tier: int | None = None,
    needs_healing: bool | None = None,
    match_count: int | None = None,
    set_disclosed: bool = True,
    system_of_record: SystemOfRecord = SystemOfRecord.ASANA,
    supplier: Supplier = Supplier.ID_WALK,
) -> Evidence:
    return Evidence(
        family=family,
        value=None,
        absent_reason=reason,
        supplier=supplier,
        supplier_path=SUPPLIER_PATH_UPWARD_WALK,
        detection_tier=detection_tier,
        needs_healing=needs_healing,
        grain=grain,
        population=Population.FLEET,
        system_of_record=system_of_record,
        match_count=match_count,
        total_match_count=match_count,
        set_disclosed=set_disclosed,
        refuted=False,
        observed_at=observed_at,
        basis_version=BASIS_VERSION,
    )


def _present(
    family: str,
    value: str,
    *,
    grain: Grain,
    observed_at: datetime,
    detection_tier: int | None,
    needs_healing: bool | None,
    match_count: int,
    supplier: Supplier = Supplier.ID_WALK,
) -> Evidence:
    return Evidence(
        family=family,
        value=value,
        absent_reason=None,
        supplier=supplier,
        supplier_path=SUPPLIER_PATH_UPWARD_WALK,
        detection_tier=detection_tier,
        needs_healing=needs_healing,
        grain=grain,
        population=Population.FLEET,
        system_of_record=SystemOfRecord.ASANA,
        match_count=match_count,
        total_match_count=match_count,
        set_disclosed=True,
        refuted=False,
        observed_at=observed_at,
        basis_version=BASIS_VERSION,
    )


def build_identity_supply(
    outcome: WalkOutcome,
    *,
    observed_at: datetime,
) -> IdentitySupply:
    """Assemble the evidence objects from a walk outcome. PURE -- no I/O, no clock.

    ``observed_at`` is the WALK's own observation instant, passed in rather than
    read here so that it can never be silently replaced by a landing instant
    (NB-1/NB-2) and so this function is fully deterministic under test.

    Dispositions, in order:

    1. no offer gid                -> every family absent, ``producer_input_absent``
    2. typed walk failure          -> the id-walk families carry THAT reason
    3. zero candidates             -> ``undecidable``
    4. more than one candidate     -> **SET, never PICK**: no value, ``match_count=N``
    5. exactly one, self-flagged   -> the typed Tier-4 absence (CW-S09-3)
    6. exactly one, clean          -> the gid is published; the name is published if
       the card carries one, else ``ancestor_field_absent`` -- which must never
       collapse into ``parent_absent`` (ADR §3.7 Ground 1)
    """
    if observed_at.tzinfo is None:
        raise ValueError("`observed_at` must be offset-aware UTC (NB-6)")

    match_count = len(outcome.candidates)

    if outcome.offer_gid is None:
        offer_ev = _absent(
            "offer",
            AbsentReason.PRODUCER_INPUT_ABSENT,
            grain=Grain.G_3,
            observed_at=observed_at,
            supplier=Supplier.PRODUCER_HELD,
            system_of_record=SystemOfRecord.NONE,
            match_count=0,
        )
    else:
        offer_ev = _present(
            "offer",
            outcome.offer_gid,
            grain=Grain.G_3,
            observed_at=observed_at,
            detection_tier=None,
            needs_healing=None,
            match_count=1,
            supplier=Supplier.PRODUCER_HELD,
        )

    def _both_absent(
        reason: AbsentReason,
        *,
        detection_tier: int | None = None,
        needs_healing: bool | None = None,
    ) -> IdentitySupply:
        return IdentitySupply(
            asana_business=_absent(
                "asana_business",
                reason,
                grain=Grain.G_1,
                observed_at=observed_at,
                detection_tier=detection_tier,
                needs_healing=needs_healing,
                match_count=match_count,
            ),
            business_display_name=_absent(
                "business_display_name",
                reason,
                grain=Grain.G_1,
                observed_at=observed_at,
                detection_tier=detection_tier,
                needs_healing=needs_healing,
                match_count=match_count,
            ),
            offer=offer_ev,
            candidates=outcome.candidates,
        )

    if outcome.offer_gid is None:
        return _both_absent(AbsentReason.PRODUCER_INPUT_ABSENT)

    if outcome.failure is not None:
        return _both_absent(outcome.failure)

    if match_count == 0:
        return _both_absent(AbsentReason.UNDECIDABLE)

    if match_count > 1:
        # SET, never PICK. The candidates ride on `IdentitySupply.candidates`; the
        # fold grades them `disputed` and suppresses the link (§14.3 case B).
        logger.info(
            "id_walk_multiple_business_candidates",
            extra={"offer_gid": outcome.offer_gid, "match_count": match_count},
        )
        return _both_absent(AbsentReason.UNDECIDABLE)

    candidate = outcome.candidates[0]
    typed = classify_identification(candidate.detection_tier, candidate.needs_healing)
    if typed is not None:
        logger.info(
            "id_walk_identification_refused",
            extra={
                "offer_gid": outcome.offer_gid,
                "detection_tier": candidate.detection_tier,
                "needs_healing": candidate.needs_healing,
                "absent_reason": str(typed),
            },
        )
        return _both_absent(
            typed,
            detection_tier=candidate.detection_tier,
            needs_healing=candidate.needs_healing,
        )

    # The name is carried BYTE-VERBATIM. No strip, no case-fold, no normalisation:
    # a display string decides STATE, never IDENTITY (W-7 STRICT / K-A).
    name_ev: Evidence
    if candidate.name is None or candidate.name == "":
        # The ancestor WAS reached and its name field is empty. This must never
        # collapse into `parent_absent`, which says the walk was never attempted.
        name_ev = _absent(
            "business_display_name",
            AbsentReason.ANCESTOR_FIELD_ABSENT,
            grain=Grain.G_1,
            observed_at=observed_at,
            detection_tier=candidate.detection_tier,
            needs_healing=candidate.needs_healing,
            match_count=match_count,
        )
    else:
        name_ev = _present(
            "business_display_name",
            candidate.name,
            grain=Grain.G_1,
            observed_at=observed_at,
            detection_tier=candidate.detection_tier,
            needs_healing=candidate.needs_healing,
            match_count=match_count,
        )

    return IdentitySupply(
        asana_business=_present(
            "asana_business",
            candidate.gid,
            grain=Grain.G_1,
            observed_at=observed_at,
            detection_tier=candidate.detection_tier,
            needs_healing=candidate.needs_healing,
            match_count=match_count,
        ),
        business_display_name=name_ev,
        offer=offer_ev,
        candidates=outcome.candidates,
    )


async def walk_business_candidates_async(
    client: AsanaClient,
    offer_gid: str,
    *,
    max_depth: int = 10,
) -> WalkOutcome:
    """Walk upward from ``offer_gid`` and report what was seen. READ-ONLY.

    No write of any kind is issued: the only calls made are ``tasks.get_async``
    and, where the detector reaches Tier 4, ``tasks.subtasks_async``.
    """
    from autom8_asana.models.business.hydration import (
        _traverse_upward_with_detection_async,
    )

    try:
        entry_task = await client.tasks.get_async(offer_gid)
    except Exception:  # noqa: BLE001 -- boundary: the entry fetch spans a
        # heterogeneous API/model exception surface, and every one of them means
        # the same supply-side fact: the resolver could not be reached. Typing it
        # as `resolver_unavailable` is the honest absence; letting it escape would
        # make one unreachable offer fail a whole batch.
        logger.warning("id_walk_entry_fetch_failed", extra={"offer_gid": offer_gid})
        return WalkOutcome(
            offer_gid=offer_gid,
            candidates=(),
            failure=AbsentReason.RESOLVER_UNAVAILABLE,
        )

    try:
        business, _path, detection = await _traverse_upward_with_detection_async(
            entry_task, client, max_depth
        )
    except HydrationError as exc:
        failure = _failure_reason(exc)
        logger.info(
            "id_walk_failed",
            extra={"offer_gid": offer_gid, "absent_reason": str(failure)},
        )
        return WalkOutcome(offer_gid=offer_gid, candidates=(), failure=failure)

    return WalkOutcome(
        offer_gid=offer_gid,
        candidates=(
            BusinessCandidate(
                gid=business.gid,
                name=business.name,
                detection_tier=detection.tier_used,
                needs_healing=detection.needs_healing,
            ),
        ),
        failure=None,
    )


def _failure_reason(exc: HydrationError) -> AbsentReason:
    """Map a typed walk failure to its ID-WALK absence.

    The three upward raise sites are kept APART here. An untagged
    ``HydrationError`` (any future raise site that forgets the discriminator)
    degrades to ``UNDECIDABLE`` rather than being attributed to a mode it may not
    be -- an honest absence beats a confident wrong one.
    """
    tag = getattr(exc, "walk_failure", None)
    if tag is None:
        return AbsentReason.UNDECIDABLE
    return AbsentReason(tag)


async def supply_identity_evidence_async(
    client: AsanaClient,
    offer_gid: str,
    *,
    max_depth: int = 10,
    observed_at: datetime | None = None,
) -> IdentitySupply:
    """Walk from ``offer_gid`` and return the id-walk-supplied evidence objects.

    This is the whole public surface of the supply. It SUPPLIES; it does not store,
    fold, publish, or mutate anything.

    Args:
        client: AsanaClient. Read-only use.
        offer_gid: The ``contract.offer_gid`` carried on today's producer rows.
        max_depth: Traversal depth cut-off, forwarded to the walk.
        observed_at: The walk's OWN observation instant. Defaults to now(UTC),
            captured BEFORE the walk so it is the observation instant and never a
            landing instant (NB-1/NB-2).
    """
    instant = observed_at if observed_at is not None else datetime.now(UTC)
    outcome = await walk_business_candidates_async(client, offer_gid, max_depth=max_depth)
    return build_identity_supply(outcome, observed_at=instant)
