"""Corpus skeleton (S7 · P5) — the 22 RC-A..F predicate slots.

REQUIREMENT (case-authoring surface): the case schema must be expressive enough for
all 22 acceptance predicates in ``RC-acceptance-predicates-substrate-v2.md`` — each
predicate id maps to >=1 case slot, and broken-variant slots carry ``ExpectRefuse``
(REJECT). This module is the clean authoring surface the qa-adversary fills next: it
enumerates all 22 ids, ships WORKED builders for a subset spanning SERVE + every
CLOSED refuse reason {STALE, CORRUPT, MISSING, DIVERGENT}, and leaves the rest as
declared-but-pending slots (``build=None``) for the corpus author.

The harness makes NO claim that these worked cases are the full acceptance corpus —
they are the two-sided teeth proof + the authoring template. QA owns the corpus.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.serve import RefuseReason
from tests.harness.substrate_gate.cases import (
    CaseVariant,
    ExpectRefuse,
    ExpectServe,
    Materialization,
    ReplayCase,
    SectionCell,
    SeededState,
)
from tests.harness.substrate_gate.exemplars import exemplar_one_replay_case

type CaseBuilder = Callable[[], ReplayCase]

# The 22 charter-derived predicates (RC spec §Coverage self-check: A:4 B:4 C:3 D:3 E:4 F:4).
ALL_PREDICATE_IDS: tuple[str, ...] = (
    "RC-A-1",
    "RC-A-2",
    "RC-A-3",
    "RC-A-4",
    "RC-B-1",
    "RC-B-2",
    "RC-B-3",
    "RC-B-4",
    "RC-C-1",
    "RC-C-2",
    "RC-C-3",
    "RC-D-1",
    "RC-D-2",
    "RC-D-3",
    "RC-E-1",
    "RC-E-2",
    "RC-E-3",
    "RC-E-4",
    "RC-F-1",
    "RC-F-2",
    "RC-F-3",
    "RC-F-4",
)

_NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
_PROJECT = "1143843662099250"
_SLA = 3_600


@dataclass(frozen=True, slots=True)
class CaseSlot:
    """One corpus slot: a predicate id, a variant, and an optional worked builder.

    ``build is None`` = declared-but-pending (the qa-adversary authors it). A filled
    ``build`` returns an executable ``ReplayCase`` the reference substrate discriminates.
    """

    predicate_id: str
    variant: CaseVariant
    title: str
    build: CaseBuilder | None


def _aid() -> ArtifactId:
    return ArtifactId(project_gid=_PROJECT, entity_type=EntityType.OFFER)


def _proof(built_at: datetime, digest: str, *, sla: int = _SLA) -> FreshnessProof:
    return FreshnessProof(built_from_live_at=built_at, content_digest=digest, sla_seconds=sla)


def _mat(
    plane: str,
    value: float,
    built_at: datetime,
    *,
    digest: str = "sha256:content",
    frame_digest: str | None = None,
    sla: int = _SLA,
) -> Materialization:
    return Materialization(
        plane=plane,
        proof=_proof(built_at, digest, sla=sla),
        served_value=value,
        composition={"ALL": SectionCell(rows=1, value=value)},
        frame_digest=frame_digest if frame_digest is not None else digest,
    )


def _good_single() -> ReplayCase:
    """RC-A-1 GOOD — a single fresh source resolves and serves (SERVE side)."""
    return ReplayCase(
        case_id="rc-a-1-good-single-source",
        predicate_id="RC-A-1",
        variant=CaseVariant.GOOD,
        state=SeededState(
            aid=_aid(), materializations=(_mat("v2/offer", 80_000.0, _NOW),), now=_NOW
        ),
        expected=ExpectServe(value=80_000.0, plane="v2/offer"),
    )


def _missing() -> ReplayCase:
    """RC-A-3 BROKEN — reader resolves nothing → loud MISSING (never a silent zero)."""
    return ReplayCase(
        case_id="rc-a-3-broken-missing",
        predicate_id="RC-A-3",
        variant=CaseVariant.BROKEN,
        state=SeededState(aid=_aid(), materializations=(), now=_NOW),
        expected=ExpectRefuse(reason=RefuseReason.MISSING),
    )


def _stale_single() -> ReplayCase:
    """RC-B-1 BROKEN — a single copy older than its SLA → REJECT STALE."""
    return ReplayCase(
        case_id="rc-b-1-broken-stale",
        predicate_id="RC-B-1",
        variant=CaseVariant.BROKEN,
        state=SeededState(
            aid=_aid(),
            materializations=(_mat("v2/offer", 80_000.0, _NOW - timedelta(seconds=_SLA * 4)),),
            now=_NOW,
        ),
        expected=ExpectRefuse(reason=RefuseReason.STALE),
    )


def _content_stale() -> ReplayCase:
    """RC-B-2 BROKEN — content age (built_from_live_at), not mtime, drives freshness.

    A copy whose content instant is 14d old reads STALE regardless of any fresh write
    time — the write-time-metadata trap becomes unconstructable at the harness gate.
    """
    return ReplayCase(
        case_id="rc-b-2-broken-content-stale",
        predicate_id="RC-B-2",
        variant=CaseVariant.BROKEN,
        state=SeededState(
            aid=_aid(),
            materializations=(_mat("v2/offer", 80_000.0, _NOW - timedelta(days=14)),),
            now=_NOW,
        ),
        expected=ExpectRefuse(reason=RefuseReason.STALE),
    )


def _corrupt() -> ReplayCase:
    """RC-B-4 BROKEN — served frame digest != proven content digest → REJECT CORRUPT.

    A currency that cannot be established (the served bytes are not what was proven)
    is refused, never stamped verified.
    """
    return ReplayCase(
        case_id="rc-b-4-broken-corrupt",
        predicate_id="RC-B-4",
        variant=CaseVariant.BROKEN,
        state=SeededState(
            aid=_aid(),
            materializations=(
                _mat(
                    "v2/offer", 80_000.0, _NOW, digest="sha256:proven", frame_digest="sha256:other"
                ),
            ),
            now=_NOW,
        ),
        expected=ExpectRefuse(reason=RefuseReason.CORRUPT),
    )


def _sunset_breach() -> ReplayCase:
    """RC-D-1 BROKEN — a bridge past its machine-enforced sunset fails loud."""
    return ReplayCase(
        case_id="rc-d-1-broken-sunset-breach",
        predicate_id="RC-D-1",
        variant=CaseVariant.BROKEN,
        state=SeededState(
            aid=_aid(),
            materializations=(_mat("legacy-bridge", 80_000.0, _NOW),),
            now=_NOW,
            sunset_after=_NOW - timedelta(days=1),
        ),
        expected=ExpectRefuse(reason=RefuseReason.STALE),
    )


def _unprovable_proxy() -> ReplayCase:
    """RC-F-1 BROKEN — an unprovable (stale) state refuses (fires) — serve-altitude proxy.

    The true RC-F alarm is the S6 observability seam; the harness proxies the
    provability signal at serve altitude (unprovable → REJECT).
    """
    return ReplayCase(
        case_id="rc-f-1-broken-unprovable",
        predicate_id="RC-F-1",
        variant=CaseVariant.BROKEN,
        state=SeededState(
            aid=_aid(),
            materializations=(_mat("v2/offer", 80_000.0, _NOW - timedelta(days=14)),),
            now=_NOW,
        ),
        expected=ExpectRefuse(reason=RefuseReason.STALE),
    )


def _provable_proxy() -> ReplayCase:
    """RC-F-2 GOOD — a healthy provable state serves (alarm silent) — serve-altitude proxy."""
    return ReplayCase(
        case_id="rc-f-2-good-provable",
        predicate_id="RC-F-2",
        variant=CaseVariant.GOOD,
        state=SeededState(
            aid=_aid(), materializations=(_mat("v2/offer", 84_385.0, _NOW),), now=_NOW
        ),
        expected=ExpectServe(value=84_385.0, plane="v2/offer"),
    )


# Worked builders span SERVE + every CLOSED refuse reason: DIVERGENT (exemplar), STALE,
# CORRUPT, MISSING. The remaining ids are declared pending for the qa-adversary.
_WORKED: dict[str, CaseBuilder] = {
    "RC-A-1": _good_single,
    "RC-A-2": exemplar_one_replay_case,
    "RC-A-3": _missing,
    "RC-B-1": _stale_single,
    "RC-B-2": _content_stale,
    "RC-B-4": _corrupt,
    "RC-D-1": _sunset_breach,
    "RC-F-1": _unprovable_proxy,
    "RC-F-2": _provable_proxy,
}

# The predicate ids whose worked builder is a GOOD (SERVE) case; the rest are BROKEN.
_WORKED_GOOD: frozenset[str] = frozenset({"RC-A-1", "RC-F-2"})

_PENDING_TITLES: dict[str, str] = {
    "RC-A-4": "second unasserted writer produces a shadow copy → REJECT",
    "RC-B-3": "N sections share one bulk freshness stamp → REJECT",
    "RC-C-1": "read/write/key-build without a plane discriminator → REJECT",
    "RC-C-2": "any one consumer path serves plane-blind → REJECT",
    "RC-C-3": "a brand-new consumer bypasses the guard list → REJECT",
    "RC-D-2": "a past-due sunset leaves CI green → REJECT",
    "RC-D-3": "a superseded legacy plane survives past cutover → REJECT",
    "RC-E-1": "a mid-build kill leaves prod mixed-vintage → REJECT",
    "RC-E-2": "a read-typed path writes prod (DEFECT :76) → REJECT",
    "RC-E-3": "a read/compute-typed path silently persists → REJECT",
    "RC-E-4": "a rebuild issues an unpaced 429-storm → REJECT",
    "RC-F-3": "a provability signal exists only when queried → REJECT",
    "RC-F-4": "a dead-man watches an orphaned metric → REJECT",
}


def _build_slots() -> tuple[CaseSlot, ...]:
    slots: list[CaseSlot] = []
    for predicate_id in ALL_PREDICATE_IDS:
        builder = _WORKED.get(predicate_id)
        if builder is not None:
            variant = CaseVariant.GOOD if predicate_id in _WORKED_GOOD else CaseVariant.BROKEN
            slots.append(
                CaseSlot(
                    predicate_id=predicate_id,
                    variant=variant,
                    title=f"worked example ({variant.value})",
                    build=builder,
                )
            )
        else:
            slots.append(
                CaseSlot(
                    predicate_id=predicate_id,
                    variant=CaseVariant.BROKEN,
                    title=_PENDING_TITLES.get(predicate_id, "pending — qa-adversary authors"),
                    build=None,
                )
            )
    return tuple(slots)


CORPUS_SLOTS: tuple[CaseSlot, ...] = _build_slots()


def covered_predicate_ids() -> set[str]:
    """The set of predicate ids that have at least one slot."""
    return {slot.predicate_id for slot in CORPUS_SLOTS}


def filled_slots() -> list[CaseSlot]:
    """Slots with a worked builder (executable now)."""
    return [slot for slot in CORPUS_SLOTS if slot.build is not None]


def pending_slots() -> list[CaseSlot]:
    """Slots awaiting the qa-adversary's authorship (``build is None``)."""
    return [slot for slot in CORPUS_SLOTS if slot.build is None]


def filled_cases() -> list[ReplayCase]:
    """Build every worked case (skips pending slots)."""
    return [slot.build() for slot in CORPUS_SLOTS if slot.build is not None]
