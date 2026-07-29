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

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from autom8_asana.substrate.freshness import FreshnessProof
    from autom8_asana.substrate.identity import ArtifactId
    from autom8_asana.substrate.serve import RefuseReason, ServedNumber


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
    """

    plane: str  # which copy/plane this is, e.g. "v2/offer" or "fresh-rewarm"
    proof: FreshnessProof  # its freshness proof (built_from_live_at, content_digest, sla_seconds)
    served_value: float  # the aggregate number this copy would serve (e.g. active_mrr)
    composition: Mapping[str, SectionCell]  # per-section breakdown (feeds per_section_delta)
    frame_digest: str  # digest of the parsed frame; CORRUPT iff != proof.content_digest


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
    """Expect a ``Provable`` whose decoded served value + plane match (SERVE side)."""

    value: float
    plane: str


@dataclass(frozen=True, slots=True)
class ExpectRefuse:
    """Expect a ``Refused`` carrying this CLOSED ``RefuseReason`` (REJECT side)."""

    reason: RefuseReason


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
