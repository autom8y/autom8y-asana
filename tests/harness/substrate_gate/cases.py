"""Substrate cutover-gate harness — case schema (S7 · P5 · WAVE-2 dark build).

The replay corpus vocabulary. A ``ReplayCase`` seeds a substrate's INPUT state
(artifacts + FreshnessProofs) and declares the EXPECTED verdict — a served-value
match (``ExpectServe``) or a loud refusal with a CLOSED reason (``ExpectRefuse``).

DISCIPLINE (architect S7 ruling, obeyed here):
  * The harness runs against a HARNESS-INTERNAL serve surface (``HarnessSubstrate``
    below), NOT the frozen async ``substrate.serve.SubstrateReader`` Protocol and
    NOT the empty ``substrate.rebuild.AcceptancePredicates`` Protocol (which stays
    EMPTY until S4 draws it). This lets the corpus drive ANY candidate: a fixture
    stub in wave-2, the real v2 serve (adapted) at S8.
  * The OBSERVABLE vocabulary is the FROZEN seam surface — ``ServedNumber`` /
    ``Provable`` / ``Refused`` / ``RefuseReason`` (SEAM-0, ``substrate.serve``).
    The harness verifies against what S8 will actually serve; it invents no
    parallel refusal grammar.

The expected verdict is deliberately kept BLIND to the substrate: ``serve`` is
handed only the ``SeededState`` INPUT, never the ``ReplayCase`` (which carries the
answer). A substrate cannot cheat by reading the expectation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

from autom8_asana.substrate.serve import RefusePayload

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from autom8_asana.substrate.freshness import FreshnessProof
    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.serve import RefuseReason, ServedNumber

# Tolerance for the composition-consistency guard (dollar aggregates; sub-cent).
_COMPOSITION_ABS_TOL = 0.005


@dataclass(frozen=True, slots=True)
class SectionCell:
    """One section's contribution to a served aggregate: a row count and a value.

    The unit the RC-A-2 ``per_section_delta`` observable is composed from (e.g. the
    ``ACTIVE`` section carrying ``48 rows · $61,585``).
    """

    rows: int
    value: float


@dataclass(frozen=True, slots=True)
class Materialization:
    """One physical copy of a (project, entity) answer — a single plane's view.

    RC-A turns on there being MORE THAN ONE of these for the same ``ArtifactId``:
    two disagreeing copies must be detected and refused, never silently served.

    SCHEMA RESISTANCE (qa-adversary): ``__post_init__`` REFUSES a fixture whose
    composition does not sum to its ``served_value``. Without this guard a sloppy
    case author could seed an internally-inconsistent copy, and the divergence
    ledger's Σ-invariant (Σ per_section_delta == magnitude) would silently
    mis-explain. The invariant is enforced at construction, not by vigilance.
    """

    plane: str  # which copy/plane this is, e.g. "v2/offer" or "fresh-rewarm"
    proof: FreshnessProof  # its freshness proof (built_from_live_at, content_digest, sla_seconds)
    served_value: float  # the aggregate number this copy would serve (e.g. active_mrr)
    composition: Mapping[str, SectionCell]  # per-section breakdown (feeds per_section_delta)
    frame_digest: str  # digest of the parsed frame; CORRUPT iff != proof.content_digest

    def __post_init__(self) -> None:
        total = sum(cell.value for cell in self.composition.values())
        if abs(total - self.served_value) > _COMPOSITION_ABS_TOL:
            raise ValueError(
                f"inconsistent Materialization on plane {self.plane!r}: "
                f"composition sums to {total} but served_value is {self.served_value}; "
                "the ledger Σ-invariant would silently mis-explain — fix the fixture"
            )


@dataclass(frozen=True, slots=True)
class SunsetBreach:
    """Field-level sunset marker (TDD §11 C13 — architect ruling 2026-07-29).

    The CLOSED ``RefuseReason`` enum STANDS (sunset-breach → ``STALE``); the breach
    is made machine-distinguishable by THIS named marker riding the refusal payload,
    never by a new enum member (the rot-trigger for minting EXPIRED is recorded in
    C13 — do not invent one here).
    """

    surface: str  # which bridge/transitional surface breached (the serving plane)
    sunset_after: datetime  # the declared sunset instant
    observed_at: datetime  # the serving instant at which the breach was observed


@dataclass(frozen=True, slots=True)
class HarnessRefusePayload(RefusePayload):
    """C13 additive payload extension — HARNESS-INTERNAL, seam un-narrowed.

    The frozen seam ``RefusePayload`` carries the OQ-1 four fields; C13 rules the
    payload MUST additionally carry a named ``sunset_breach`` marker. This subclass
    realizes the ruling additively inside the harness (the frozen four fields stay
    exactly as landed; a 5th optional field is ADDED, nothing narrowed). The
    seam-side additive field is the S4 owner's to land per C13; until then the
    harness carries it here so sunset cases are machine-distinguishable NOW.
    """

    sunset_breach: SunsetBreach | None = None


@dataclass(frozen=True, slots=True)
class SeededState:
    """The INPUT half of a case — the artifacts + proofs a substrate serves from.

    Carries NO expected verdict: a substrate must never see the answer. ``now`` is
    the serving instant (drives absolute age deterministically — no wall clock).
    """

    aid: ArtifactId
    materializations: tuple[Materialization, ...]  # >=1; RC-A needs >1
    now: datetime  # tz-aware UTC serving instant
    sunset_after: datetime | None = None  # RC-D bridge sunset input; None = no bridge


class CaseVariant(Enum):
    """Whether the seeded input is a healthy case or a deliberately-broken one."""

    GOOD = "good"  # a provable, single-source, plane-correct input — expect SERVE
    BROKEN = "broken"  # a falsifying input (stale/divergent/corrupt/...) — expect REJECT


class Verdict(Enum):
    """The correct classification of an input: serve a provable value, or refuse."""

    SERVE = "serve"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class ExpectServe:
    """Expect a ``Provable`` whose decoded served value + plane match (SERVE side).

    ``composition``, when given, is ALSO asserted per-section (qa-adversary
    strengthening: a substrate serving the right TOTAL over the wrong per-section
    content must not pass — the DEFECT's zero-net composition shift is the wound).
    ``None`` = total+plane only (back-compatible with the worked cases).
    """

    value: float
    plane: str
    composition: Mapping[str, SectionCell] | None = None


@dataclass(frozen=True, slots=True)
class ExpectRefuse:
    """Expect a ``Refused`` carrying this CLOSED ``RefuseReason`` (REJECT side).

    ``sunset_breach``, when given, is ALSO asserted against the payload's C13
    marker (see ``SunsetBreach``): a sunset-breach refusal must be
    machine-distinguishable from an age-STALE refusal, not comment-only.
    """

    reason: RefuseReason
    sunset_breach: SunsetBreach | None = None


type Expected = ExpectServe | ExpectRefuse


def verdict_of(expected: Expected) -> Verdict:
    """Reduce an ``Expected`` to its coarse ``Verdict`` (the harness's classification)."""
    if isinstance(expected, ExpectServe):
        return Verdict.SERVE
    return Verdict.REJECT


@dataclass(frozen=True, slots=True)
class ReplayCase:
    """A single corpus case: a seeded input, its variant, and its expected verdict.

    ``predicate_id`` binds the case to one of the 22 RC-A..F acceptance predicates
    (see ``corpus.ALL_PREDICATE_IDS``). Broken-variant cases carry ``ExpectRefuse``.
    """

    case_id: str
    predicate_id: str  # e.g. "RC-A-2"
    variant: CaseVariant
    state: SeededState
    expected: Expected


class HarnessSubstrate(Protocol):
    """Harness-internal serve surface — the corpus's injection seam.

    NOT the frozen async ``substrate.serve.SubstrateReader`` (S4-owned): this is a
    synchronous, deterministic surface the replay runner drives with fixtures in
    wave-2. At S8 a thin adapter satisfies it over the real v2 serve. The return
    type IS the frozen ``ServedNumber`` observable.
    """

    def serve(self, state: SeededState) -> ServedNumber:
        """Serve the (project, entity) named by ``state.aid`` → Provable | Refused.

        Handed only the INPUT ``SeededState`` — never the ``ReplayCase``.
        """
        ...
