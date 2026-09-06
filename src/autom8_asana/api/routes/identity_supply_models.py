"""Wire models for the id-walk identity-evidence exposure route.

This module is an ADAPTER, not a second contract. Every closed set on the wire
(``Supplier``, ``AbsentReason``, ``Grain``, ``Population``, ``SystemOfRecord``)
is the SUPPLY's own enum, imported and used as the pydantic field type -- so the
OpenAPI spec publishes the ratified members from ONE definition. Re-declaring
them here would make this module a second writer for a closed set that already
has one, which is the failure the supply's own ``RATIFIED_ABSENT_REASONS``
equality pin exists to prevent.

WHAT CROSSES, AND WHY
---------------------
The whole ``IdentitySupply`` crosses: the three evidence objects AND the
candidate SET. The set is not decoration -- ADR rule 2 is *SET, never PICK*, and
the consumer (seat A, the ``[data]`` appender) needs the candidates in order to
append N observations and let the fold grade them ``disputed`` (ADR §14.3 case
B). A response that carried only the three families would silently convert a
two-candidate walk into an unexplained ``undecidable``.

WHAT DOES NOT CROSS
-------------------
Nothing is added. ``confidence`` is not on ``Evidence`` (the supply refuses to
guard on it and the fold derives the fold-side confidence), ``shared`` /
``shared_count`` / ``corroborated_by`` / ``lineage`` / ``fold_version`` /
``fold_at`` have their own writers elsewhere, and this module mints no field of
its own. The one derived value on the envelope, ``basis_version``, is READ OFF
the evidence objects and refuses when they disagree -- see
:func:`derive_basis_version`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from autom8_asana.models.business.identity_supply import (
    AbsentReason,
    BusinessCandidate,
    Evidence,
    Grain,
    IdentitySupply,
    Population,
    Supplier,
    SystemOfRecord,
)

__all__ = [
    "BasisVersionConflict",
    "BusinessCandidateModel",
    "EvidenceModel",
    "IdentitySupplyResponse",
    "build_identity_supply_response",
    "derive_basis_version",
]


class BasisVersionConflict(ValueError):
    """Raised when the supplied evidence objects disagree on ``basis_version``.

    Unrepresentable by construction at this head (``_absent`` and ``_present``
    both stamp the module constant), which is exactly why it is raised rather
    than papered over: if the supply ever grows a second basis, a consumer that
    re-grades observations against "the" basis version would be re-grading
    against a number that was true of only some of the rows it received.
    """


#: Example payloads used ONLY for the published spec. Every gid is synthetic and
#: every name is a fixture string -- this is a wire contract, not a data sample.
_EVIDENCE_EXAMPLE: dict[str, object] = {
    "family": "asana_business",
    "value": "3000000000000003",
    "absent_reason": None,
    "supplier": "id_walk",
    "supplier_path": "entry->parent*->business",
    "detection_tier": 1,
    "needs_healing": False,
    "grain": "G-1",
    "population": "fleet",
    "system_of_record": "asana",
    "match_count": 1,
    "total_match_count": 1,
    "set_disclosed": True,
    "refuted": False,
    "observed_at": "2026-09-06T12:00:00Z",
    "basis_version": 2,
}

_CANDIDATE_EXAMPLE: dict[str, object] = {
    "gid": "3000000000000003",
    "name": "Fixture Business A",
    "detection_tier": 1,
    "needs_healing": False,
}


class EvidenceModel(BaseModel):
    """One evidence object, one family, as SUPPLIED.

    Field-for-field the supply's :class:`Evidence` dataclass. ``value`` and
    ``absent_reason`` are XOR (E-0) -- that invariant is enforced in the
    dataclass's ``__post_init__``, upstream of this model, so it is stated here
    rather than re-implemented.
    """

    family: str = Field(
        ...,
        examples=["asana_business"],
        description="The evidence family: asana_business, business_display_name, or offer.",
    )
    value: str | None = Field(
        None,
        examples=["3000000000000003"],
        description=(
            "The supplied value, or null when the fact is a TYPED ABSENCE. "
            "Exactly one of value / absent_reason is non-null (E-0)."
        ),
    )
    absent_reason: AbsentReason | None = Field(
        None,
        examples=["undecidable"],
        description=(
            "The ratified typed-absence token, or null when a value was "
            "published. The enum members are the supply's ratified set."
        ),
    )
    supplier: Supplier = Field(
        ...,
        examples=["id_walk"],
        description=(
            "Which supplier produced the fact. Required even when value is "
            "null. `cascade` is a declared member of the closed set and is "
            "FORBIDDEN -- the supply raises rather than emit it."
        ),
    )
    supplier_path: str | None = Field(
        None,
        examples=["entry->parent*->business"],
        description="The hop SHAPE. A shape, never a value and never a name.",
    )
    detection_tier: int | None = Field(
        None,
        examples=[1],
        description=(
            "WHICH detector tier concluded the identification. CARRIED onto "
            "the refusal arm too: a refused tier-4 row lands here as 4, not as "
            "null. Never a confidence number."
        ),
    )
    needs_healing: bool | None = Field(
        None,
        examples=[False],
        description=(
            "What the detector thought of its OWN conclusion. True means the "
            "detector self-flagged; the supply publishes such an "
            "identification as a typed absence, never as a value."
        ),
    )
    grain: Grain = Field(..., examples=["G-1"], description="The grain the fact is stated at.")
    population: Population = Field(
        ...,
        examples=["fleet"],
        description="The denominator the fact was computed over.",
    )
    system_of_record: SystemOfRecord = Field(
        ...,
        examples=["asana"],
        description="The system of record for the fact.",
    )
    match_count: int | None = Field(
        None,
        examples=[1],
        description="Candidate Business ancestors confirmed by the walk.",
    )
    total_match_count: int | None = Field(
        None,
        examples=[1],
        description=(
            "The PRE-filter total. Equal to match_count here BY CONSTRUCTION: "
            "the id walk does not filter, so there is no erased population."
        ),
    )
    set_disclosed: bool = Field(
        ...,
        examples=[True],
        description="Whether the candidate set is disclosed alongside this fact.",
    )
    refuted: bool = Field(
        ...,
        examples=[False],
        description=(
            "Always False from this seat. Refutation is published by the fold; "
            "an observation is never self-refuted."
        ),
    )
    observed_at: datetime | None = Field(
        None,
        examples=["2026-09-06T12:00:00Z"],
        description=(
            "The WALK's own observation instant, offset-aware UTC. Never a landing instant."
        ),
    )
    basis_version: int = Field(
        ...,
        ge=1,
        examples=[2],
        description=(
            "The version of the supplier's disposition rules that produced "
            "this fact, so an appended observation can be re-graded against "
            "the rule that made it."
        ),
    )

    @classmethod
    def from_evidence(cls, evidence: Evidence) -> EvidenceModel:
        """Project a supply :class:`Evidence` onto the wire, field for field."""
        return cls(
            family=evidence.family,
            value=evidence.value,
            absent_reason=evidence.absent_reason,
            supplier=evidence.supplier,
            supplier_path=evidence.supplier_path,
            detection_tier=evidence.detection_tier,
            needs_healing=evidence.needs_healing,
            grain=evidence.grain,
            population=evidence.population,
            system_of_record=evidence.system_of_record,
            match_count=evidence.match_count,
            total_match_count=evidence.total_match_count,
            set_disclosed=evidence.set_disclosed,
            refuted=evidence.refuted,
            observed_at=evidence.observed_at,
            basis_version=evidence.basis_version,
        )


class BusinessCandidateModel(BaseModel):
    """One candidate Business ancestor, WITH the detection that produced it.

    ``name`` is carried byte-verbatim off the Asana card. It is a display
    string: it decides STATE, never IDENTITY (W-7 STRICT), and it is never a
    key member and never used to reach ``gid``.
    """

    gid: str = Field(
        ...,
        examples=["3000000000000003"],
        description="The candidate Business card gid.",
    )
    name: str | None = Field(
        None,
        examples=["Fixture Business A"],
        description="The candidate's display name, byte-verbatim.",
    )
    detection_tier: int | None = Field(
        None,
        examples=[1],
        description="The tier that identified this candidate as a Business.",
    )
    needs_healing: bool | None = Field(
        None,
        examples=[False],
        description="The detector's self-flag for this candidate.",
    )

    @classmethod
    def from_candidate(cls, candidate: BusinessCandidate) -> BusinessCandidateModel:
        """Project a supply :class:`BusinessCandidate` onto the wire."""
        return cls(
            gid=candidate.gid,
            name=candidate.name,
            detection_tier=candidate.detection_tier,
            needs_healing=candidate.needs_healing,
        )


class IdentitySupplyResponse(BaseModel):
    """What the supply hands seat A, on the wire.

    The three evidence objects keep the supply's own attribute names, so a
    reader comparing this response to ``IdentitySupply`` is comparing like with
    like rather than decoding a rename.
    """

    offer_gid: str = Field(
        ...,
        examples=["3000000000000001"],
        description="The offer gid the walk started from (echoed, digits-only).",
    )
    basis_version: int = Field(
        ...,
        ge=1,
        examples=[2],
        description=(
            "The supplier basis version. READ OFF the evidence objects, not "
            "minted here; the route refuses when they disagree."
        ),
    )
    asana_business: EvidenceModel = Field(
        ...,
        examples=[_EVIDENCE_EXAMPLE],
        description="The Business card gid family (G-1).",
    )
    business_display_name: EvidenceModel = Field(
        ...,
        examples=[_EVIDENCE_EXAMPLE],
        description="The Business card name family (G-1). A display string.",
    )
    offer: EvidenceModel = Field(
        ...,
        examples=[_EVIDENCE_EXAMPLE],
        description="The entry offer gid family (G-3).",
    )
    candidates: list[BusinessCandidateModel] = Field(
        default_factory=list,
        examples=[[_CANDIDATE_EXAMPLE]],
        description=(
            "Every Business ancestor the walk confirmed. Present so a consumer "
            "can append N observations under SET-never-PICK; a two-candidate "
            "walk publishes no identity but discloses both candidates here."
        ),
    )


def derive_basis_version(supply: IdentitySupply) -> int:
    """Return the one basis version the supplied evidence agrees on.

    Read off the evidence objects rather than re-imported from the supply
    module: a route that stamped ``BASIS_VERSION`` onto the envelope would be
    asserting a version the rows it is carrying might not share.

    Raises:
        BasisVersionConflict: if the three families disagree.
    """
    versions = {ev.basis_version for ev in supply.families().values()}
    if len(versions) != 1:
        raise BasisVersionConflict(
            f"supplied evidence carries {len(versions)} basis versions "
            f"({sorted(versions)}); a single envelope version would be a lie"
        )
    return versions.pop()


def build_identity_supply_response(
    supply: IdentitySupply,
    *,
    offer_gid: str,
) -> IdentitySupplyResponse:
    """Project an :class:`IdentitySupply` onto its wire model. PURE -- no I/O.

    Raises:
        BasisVersionConflict: propagated from :func:`derive_basis_version`.
    """
    return IdentitySupplyResponse(
        offer_gid=offer_gid,
        basis_version=derive_basis_version(supply),
        asana_business=EvidenceModel.from_evidence(supply.asana_business),
        business_display_name=EvidenceModel.from_evidence(supply.business_display_name),
        offer=EvidenceModel.from_evidence(supply.offer),
        candidates=[BusinessCandidateModel.from_candidate(c) for c in supply.candidates],
    )
