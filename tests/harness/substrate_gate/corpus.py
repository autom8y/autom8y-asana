"""Corpus (S7 · PT-01 fixture catalogue) — the 22 RC-A..F predicates, FILLED.

The PE scaffold enumerated all 22 predicate ids with 9 worked cases spanning SERVE
+ every CLOSED refuse reason; the qa-adversary has now AUTHORED the corpus into
this surface (role split per the S7 shape: PE built the harness, QA brings the
teeth). Every predicate is TWO-SIDED per the discriminating-canary posture:

  * a BROKEN case is a deliberately-corrupted INPUT the harness must catch — never
    an injected defect in working code — and every replay-expressible broken case
    trips ``SilentServeSubstrate``'s silent serve (asserted in the saboteur suite);
  * a GOOD case is the real/healthy twin that must SERVE — and every one trips
    ``OverRefuseSubstrate``'s noise. No vacuous cases: a case that a correct AND a
    defective substrate would both pass is rejected by that suite.

The QA broken variants deliberately SMELL LIKE THE WOUND
(``DEFECT-seam1-entity-blind-prober-plane-split-2026-07-27``): project
1143843662099250, the 2026-07-13 v2/offer freeze, the 13:00:30.232451 bulk stamp,
the 13:01 fresh-mtime re-consolidation, the entity-blind legacy-plane shadow
writes, and the ``$79,585``-vs-``$84,385`` composition shift.

FIVE predicates (RC-C-1, RC-C-3, RC-E-2, RC-E-3, RC-E-4) have falsifying inputs
that are UNCONSTRUCTABLE as ``SeededState`` fixtures — that IS their acceptance
mode (BY-CONSTRUCTION / process altitude). They carry construction slots here
(``build=None``) and are realized two-sidedly at construction altitude in
``test_corpus_scaffold.py`` (§ construction-refusal suite).

Sunset cases follow the TDD §11 C13 architect ruling (2026-07-29): expected
REJECT ``reason=STALE`` per the frozen CLOSED ``RefuseReason`` grammar PLUS a
populated ``sunset_breach`` payload-marker assertion (machine-distinguishable,
not comment-only). No new enum member is invented — the enum is closed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

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
    SunsetBreach,
)
from tests.harness.substrate_gate.exemplars import exemplar_one_replay_case

if TYPE_CHECKING:
    from collections.abc import Mapping

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
    """RC-D-1 BROKEN — a bridge past its machine-enforced sunset fails loud.

    sunset→STALE per the frozen CLOSED RefuseReason grammar (TDD §11 C13,
    architect ruling 2026-07-29): the enum stays closed; the breach is asserted
    machine-distinguishable via the ``sunset_breach`` payload marker below —
    a marker-blind STALE (indistinguishable from age-STALE) FAILS this case.
    """
    sunset = _NOW - timedelta(days=1)
    return ReplayCase(
        case_id="rc-d-1-broken-sunset-breach",
        predicate_id="RC-D-1",
        variant=CaseVariant.BROKEN,
        state=SeededState(
            aid=_aid(),
            materializations=(_mat("legacy-bridge", 80_000.0, _NOW),),
            now=_NOW,
            sunset_after=sunset,
        ),
        expected=ExpectRefuse(
            reason=RefuseReason.STALE,
            sunset_breach=SunsetBreach(
                surface="legacy-bridge", sunset_after=sunset, observed_at=_NOW
            ),
        ),
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


# ═══════════════════════════════════════════════════════════════════════════════
# QA-ADVERSARY CORPUS (authored 2026-07-29) — the two-sided fill of all 22 slots.
# Broken variants smell like the wound; boundary cases pin inclusive/exclusive
# semantics from both sides. Prefix ``qa-`` on every authored case_id.
# ═══════════════════════════════════════════════════════════════════════════════

# ── The wound's timeline (DEFECT :16-:23, :64-:76) ─────────────────────────────
_QNOW = datetime(2026, 7, 27, 15, 27, tzinfo=UTC)  # the live re-warm instant
_FROZEN_AT = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)  # v2/offer plane freeze (14d)
_BULK_STAMP_AT = datetime(2026, 7, 27, 13, 0, 30, 232451, tzinfo=UTC)  # DEFECT :22a
_RECONSOLIDATED_AT = datetime(2026, 7, 27, 13, 1, tzinfo=UTC)  # fresh mtime (:22c)

_V2_PLANE = "v2/offer"
_LEGACY_PLANE = "legacy/sections"  # the entity-blind prober's default-None plane

# ── The wound's compositions (DEFECT :64-:71 addendum table) ───────────────────
_STALE_79585: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=51, value=65_585.0),
    "OPTIMIZE – Human Review": SectionCell(rows=2, value=3_100.0),
    "STAGED": SectionCell(rows=5, value=6_000.0),
    "OTHER (unchanged)": SectionCell(rows=6, value=4_900.0),
}
_FRESH_84385: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=48, value=61_585.0),
    "OPTIMIZE – Human Review": SectionCell(rows=5, value=7_900.0),
    "STAGED": SectionCell(rows=7, value=10_000.0),
    "OTHER (unchanged)": SectionCell(rows=6, value=4_900.0),
}
# Zero-net shift: offers moved ACTIVE → STAGED with NO net change (±$4,000, net $0).
_SHIFTED_79585: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=48, value=61_585.0),
    "OPTIMIZE – Human Review": SectionCell(rows=2, value=3_100.0),
    "STAGED": SectionCell(rows=8, value=10_000.0),
    "OTHER (unchanged)": SectionCell(rows=6, value=4_900.0),
}
# The fragmentary legacy plane the shadow writer produced (DEFECT :21: ACTIVE 48r/$60,585).
_LEGACY_74585: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=48, value=60_585.0),
    "OPTIMIZE – Human Review": SectionCell(rows=2, value=3_100.0),
    "STAGED": SectionCell(rows=5, value=6_000.0),
    "OTHER (unchanged)": SectionCell(rows=6, value=4_900.0),
}
# The GID-set-preserving value edit (same 51 GIDs in ACTIVE, one MRR $1,000 → $1,200).
_EDITED_79785: dict[str, SectionCell] = {
    "ACTIVE": SectionCell(rows=51, value=65_785.0),
    "OPTIMIZE – Human Review": SectionCell(rows=2, value=3_100.0),
    "STAGED": SectionCell(rows=5, value=6_000.0),
    "OTHER (unchanged)": SectionCell(rows=6, value=4_900.0),
}
_BULK_SECTIONS: dict[str, SectionCell] = {
    f"SECTION-{index:02d}": SectionCell(rows=1, value=100.0) for index in range(34)
}


def _qmat(
    plane: str,
    value: float,
    built_at: datetime,
    *,
    composition: Mapping[str, SectionCell] | None = None,
    digest: str = "sha256:content",
    frame_digest: str | None = None,
    sla: int = _SLA,
) -> Materialization:
    return Materialization(
        plane=plane,
        proof=FreshnessProof(built_from_live_at=built_at, content_digest=digest, sla_seconds=sla),
        served_value=value,
        composition=(
            composition if composition is not None else {"ALL": SectionCell(rows=1, value=value)}
        ),
        frame_digest=frame_digest if frame_digest is not None else digest,
    )


def _qstate(
    *mats: Materialization, now: datetime = _QNOW, sunset_after: datetime | None = None
) -> SeededState:
    return SeededState(aid=_aid(), materializations=mats, now=now, sunset_after=sunset_after)


# ═══ RC-A-1 — single source of truth ══════════════════════════════════════════


def _qa_a1_good_empty_but_valid() -> ReplayCase:
    """BOUNDARY — an empty-but-valid frame SERVES $0 (empty ≠ MISSING).

    A project with zero offers is a provable zero: artifact present, digest
    consistent, fresh. A substrate mapping empty → MISSING over-refuses; a
    substrate serving 0 WITHOUT an artifact (SilentServe on the absent state) is
    the silent-zero wound. This case pins the distinction.
    """
    return ReplayCase(
        case_id="qa-rc-a-1-good-empty-but-valid",
        predicate_id="RC-A-1",
        variant=CaseVariant.GOOD,
        state=_qstate(_qmat(_V2_PLANE, 0.0, _QNOW, composition={}, digest="sha256:empty-frame")),
        expected=ExpectServe(value=0.0, plane=_V2_PLANE, composition={}),
    )


def _qa_a1_broken_two_readable_copies() -> ReplayCase:
    """RC-A-1 falsifying input: per-section AND consolidated layouts both readable.

    The DEFECT :74 second split: the consolidated ``offer/dataframe.parquet``
    (frozen re-sum, $79,585) and the per-section ``offer/sections/*`` layout
    (rebuilt live, $84,385) are BOTH live read targets claiming to answer
    active_mrr. Two disagreeing read targets must be refused DIVERGENT, never
    resolved silently to either.
    """
    return ReplayCase(
        case_id="qa-rc-a-1-broken-two-readable-copies",
        predicate_id="RC-A-1",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                "v2/offer/dataframe.parquet",
                79_585.0,
                _FROZEN_AT,
                composition=_STALE_79585,
                digest="sha256:consolidated-frozen-0713",
            ),
            _qmat(
                "v2/offer/sections",
                84_385.0,
                _QNOW,
                composition=_FRESH_84385,
                digest="sha256:per-section-rebuilt-1527",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.DIVERGENT),
    )


# ═══ RC-A-2 — disagreeing copies detected, refused, EXPLAINED ═════════════════


def _qa_a2_good_coherent_post_warm() -> ReplayCase:
    """The coherent post-warm state SERVES $84,385 — with the composition asserted.

    The two-sided complement of the Parity Exemplar: after the full re-warm the
    single canonical copy serves, and the PER-SECTION content is asserted too (a
    substrate serving the right total over wrong per-section content must fail).
    """
    return ReplayCase(
        case_id="qa-rc-a-2-good-coherent-post-warm",
        predicate_id="RC-A-2",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(
                _V2_PLANE, 84_385.0, _QNOW, composition=_FRESH_84385, digest="sha256:fresh-84385"
            ),
        ),
        expected=ExpectServe(value=84_385.0, plane=_V2_PLANE, composition=_FRESH_84385),
    )


def _qa_a2_broken_zero_net_composition_shift() -> ReplayCase:
    """BOUNDARY — zero-magnitude divergence with a composition shift → DIVERGENT.

    The nastiest twin pair: two copies whose TOTALS agree to the cent ($79,585
    both) while offers moved ACTIVE → STAGED (±$4,000, net $0). A magnitude-only
    detector serves the stale copy silently — section-level consumers then read
    14-day-stale content under a green serve. The scaffold's original scalar-only
    ``diverges`` had exactly this hole (found and fixed during corpus authoring);
    this case locks the fix.
    """
    return ReplayCase(
        case_id="qa-rc-a-2-broken-zero-net-composition-shift",
        predicate_id="RC-A-2",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                79_585.0,
                _FROZEN_AT,
                composition=_STALE_79585,
                digest="sha256:stale-composition",
            ),
            _qmat(
                "fresh-rewarm",
                79_585.0,
                _QNOW,
                composition=_SHIFTED_79585,
                digest="sha256:shifted-composition",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.DIVERGENT),
    )


# ═══ RC-A-3 — writer target IS reader target ══════════════════════════════════


def _qa_a3_good_rebuild_refreshes_read() -> ReplayCase:
    """A successful full rebuild refreshes exactly what the consumer reads.

    The DEFECT :74 inverse: the 15:27 warm's output IS the artifact the reader
    resolves — the read reflects the warm ($84,385), no cross-wired layout where
    the warm rewrote ``dataframe.parquet`` while the reader kept per-section
    ``sections/*`` frozen.
    """
    return ReplayCase(
        case_id="qa-rc-a-3-good-rebuild-refreshes-read",
        predicate_id="RC-A-3",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                84_385.0,
                _QNOW,
                composition=_FRESH_84385,
                digest="sha256:warm-output-1527",
            ),
        ),
        expected=ExpectServe(value=84_385.0, plane=_V2_PLANE),
    )


# ═══ RC-A-4 — bounded, asserted writer set ════════════════════════════════════


def _qa_a4_good_single_writer_discipline() -> ReplayCase:
    """Single-writer discipline: exactly one canonical copy exists → SERVE."""
    return ReplayCase(
        case_id="qa-rc-a-4-good-single-writer-discipline",
        predicate_id="RC-A-4",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(
                _V2_PLANE, 79_585.0, _QNOW, composition=_STALE_79585, digest="sha256:sole-writer"
            ),
        ),
        expected=ExpectServe(value=79_585.0, plane=_V2_PLANE),
    )


def _qa_a4_broken_entity_blind_shadow_writer() -> ReplayCase:
    """THE WOUND'S ROOT CAUSE as an input: a second unasserted writer's shadow copy.

    Writer A (full builder) froze the v2/offer plane at 07-13; Writer B (the
    entity-blind ``SectionFreshnessProber``, zero ``entity_type``) kept writing
    fresh deltas to the legacy plane at 13:00 — producing a divergent shadow
    copy nothing asserted against the canonical. The two copies' disagreement
    must be DETECTED and refused, never a silent serve of either.
    """
    return ReplayCase(
        case_id="qa-rc-a-4-broken-entity-blind-shadow-writer",
        predicate_id="RC-A-4",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                79_585.0,
                _FROZEN_AT,
                composition=_STALE_79585,
                digest="sha256:writer-a-frozen-0713",
            ),
            _qmat(
                _LEGACY_PLANE,
                74_585.0,
                _BULK_STAMP_AT,
                composition=_LEGACY_74585,
                digest="sha256:writer-b-shadow-1300",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.DIVERGENT),
    )


# ═══ RC-B-1 — GID-set-preserving content edit is detected (D8) ════════════════


def _qa_b1_broken_gid_preserving_value_edit() -> ReplayCase:
    """THE D8 NULL-WATERMARK CLASS: a value edit invisible to a GID-set check.

    Same 51 task GIDs in ACTIVE (membership unchanged), one offer's MRR edited
    ``$1,000 → $1,200``. v1's hash-only path read CLEAN and stamped ``verified``
    (DEFECT :22b/:43). Here the proof still carries the pre-edit GID-set-era
    baseline digest while the frame carries the edited content — the
    content-derived check the GID-set check cannot perform must refuse CORRUPT
    (the served bytes are not what was proven), never stamp-and-serve.
    """
    return ReplayCase(
        case_id="qa-rc-b-1-broken-gid-preserving-value-edit",
        predicate_id="RC-B-1",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                79_785.0,
                _BULK_STAMP_AT,
                composition=_EDITED_79785,
                digest="sha256:gid-set-baseline-pre-edit",  # the false-CLEAN stamp's claim
                frame_digest="sha256:content-after-value-edit",  # the actual edited bytes
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.CORRUPT),
    )


def _qa_b1_good_value_edit_reproved() -> ReplayCase:
    """The same value edit with an HONESTLY re-derived proof → SERVE $79,785.

    The good twin of the D8 case: after a genuine content-verify the digest is
    re-derived from the edited content and the new number serves. The pair proves
    the harness discriminates on proof-honesty, not on the edit itself.
    """
    return ReplayCase(
        case_id="qa-rc-b-1-good-value-edit-reproved",
        predicate_id="RC-B-1",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                79_785.0,
                _QNOW,
                composition=_EDITED_79785,
                digest="sha256:content-after-value-edit",
            ),
        ),
        expected=ExpectServe(value=79_785.0, plane=_V2_PLANE),
    )


# ═══ RC-B-2 — write-time metadata is never proof of freshness ═════════════════


def _qa_b2_broken_false_fresh_reconsolidation() -> ReplayCase:
    """THE WOUND-REPLAY: fresh-mtime-stale-content → the false-fresh class.

    DEFECT :22c: the 13:01 re-consolidation touched ``dataframe.parquet``'s mtime
    (fresh, today) over a re-sum of the FROZEN 07-13 per-section parquets. Encoded
    at proof altitude: the proof CLAIMS a live fetch at 13:01 with a digest it
    asserts was derived then — but the frame bytes are the frozen 07-13 content.
    A lying proof is unprovable: REFUSE CORRUPT. (The 'verified 1m ago' beside
    14-day-old content was exactly this class served green.)
    """
    return ReplayCase(
        case_id="qa-rc-b-2-broken-false-fresh-reconsolidation",
        predicate_id="RC-B-2",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                79_585.0,
                _RECONSOLIDATED_AT,  # the fresh write-time the trap trusts
                composition=_STALE_79585,
                digest="sha256:claimed-live-fetch-1301",  # what the stamp claims it proved
                frame_digest="sha256:frozen-content-0713",  # what the bytes actually are
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.CORRUPT),
    )


def _qa_b2_good_age_exactly_sla() -> ReplayCase:
    """BOUNDARY — age exactly == SLA serves (inclusive per the frozen contract).

    ``is_provable``: PROVABLE iff ``(now - built_from_live_at) <= sla_seconds``.
    The boundary is inclusive; a substrate refusing at exactly-SLA over-refuses.
    """
    return ReplayCase(
        case_id="qa-rc-b-2-good-age-exactly-sla",
        predicate_id="RC-B-2",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(_V2_PLANE, 80_000.0, _QNOW - timedelta(seconds=_SLA), digest="sha256:at-sla"),
        ),
        expected=ExpectServe(value=80_000.0, plane=_V2_PLANE),
    )


def _qa_b2_broken_age_one_second_past_sla() -> ReplayCase:
    """BOUNDARY — age == SLA + 1s refuses STALE (the boundary's broken twin).

    Together with the exactly-SLA good twin this pins the inclusive boundary from
    both sides: serve at SLA, refuse at SLA+1. A substrate with an off-by-one or
    a sloppy ``<`` / ``>=`` comparison fails one of the pair.
    """
    return ReplayCase(
        case_id="qa-rc-b-2-broken-age-one-second-past-sla",
        predicate_id="RC-B-2",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE, 80_000.0, _QNOW - timedelta(seconds=_SLA + 1), digest="sha256:past-sla"
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.STALE),
    )


# ═══ RC-B-3 — N sections cannot share ONE freshness proof ═════════════════════


def _qa_b3_broken_bulk_stamp_34_sections() -> ReplayCase:
    """THE BULK STAMP (DEFECT :22a): one write claims 34 verification events.

    All 34 sections carry the single ``13:00:30.232451`` stamp written by one
    per-warm bulk operation — 20 of them null-watermark, never content-verified.
    The bulk stamp's claimed digest was not derived from the actual per-section
    content (no genuine per-section verification happened), so the frame cannot
    match the proof: REFUSE CORRUPT. A shared stamp accepted as N verification
    events = FALSIFIED.
    """
    return ReplayCase(
        case_id="qa-rc-b-3-broken-bulk-stamp-34-sections",
        predicate_id="RC-B-3",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                3_400.0,
                _BULK_STAMP_AT,
                composition=_BULK_SECTIONS,
                digest="sha256:bulk-stamp-claim",  # one stamp claiming all 34 proven
                frame_digest="sha256:actual-mixed-vintage-sections",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.CORRUPT),
    )


def _qa_b3_good_min_over_section_instants() -> ReplayCase:
    """Genuine per-section verification: the proof instant is the MIN over sections.

    C1 semantics: ``built_from_live_at`` = MIN over constituent sections' last
    REAL content-fetch instants — the OLDEST section bounds the proof (here 30
    minutes ago, within SLA), and the digest was derived from the actual content.
    N sections, N genuine events, one honest aggregate proof → SERVE.
    """
    return ReplayCase(
        case_id="qa-rc-b-3-good-min-over-section-instants",
        predicate_id="RC-B-3",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                3_400.0,
                _QNOW - timedelta(seconds=1_800),  # the oldest section's fetch instant
                composition=_BULK_SECTIONS,
                digest="sha256:derived-from-actual-sections",
            ),
        ),
        expected=ExpectServe(value=3_400.0, plane=_V2_PLANE),
    )


# ═══ RC-B-4 — unestablishable currency is refused, never stamped ══════════════


def _qa_b4_good_establishable_currency() -> ReplayCase:
    """The good twin of the CORRUPT worked case: establishable currency SERVES.

    The frame bytes are exactly what the proof proved (digest match) and the
    proof is within SLA — currency established, number serves.
    """
    return ReplayCase(
        case_id="qa-rc-b-4-good-establishable-currency",
        predicate_id="RC-B-4",
        variant=CaseVariant.GOOD,
        state=_qstate(_qmat(_V2_PLANE, 80_000.0, _QNOW, digest="sha256:established")),
        expected=ExpectServe(value=80_000.0, plane=_V2_PLANE),
    )


# ═══ RC-C-2 — every consumer path resolves plane-correct ══════════════════════


def _qa_c2_good_entity_typed_plane_serves() -> ReplayCase:
    """A consumer path resolving through the entity-typed plane SERVES.

    Serve-altitude half of RC-C-2 (the type-level floor — ``SeededState`` is
    unconstructable without a typed ``ArtifactId`` — is asserted at construction
    altitude in the construction-refusal suite; the full CP-1..6 per-path serve
    matrix is S8's, against the real consumer paths).
    """
    return ReplayCase(
        case_id="qa-rc-c-2-good-entity-typed-plane-serves",
        predicate_id="RC-C-2",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(_V2_PLANE, 84_385.0, _QNOW, composition=_FRESH_84385, digest="sha256:typed"),
        ),
        expected=ExpectServe(value=84_385.0, plane=_V2_PLANE),
    )


def _qa_c2_broken_legacy_plane_shadow_readable() -> ReplayCase:
    """A plane-blind serve attempt: the entity-agnostic legacy plane is readable.

    The default-``None``-emits-legacy trap (RC spec §V-1) as an input state: the
    legacy entity-agnostic plane — where every entity-blind read/write lands —
    is live beside v2/offer and disagrees. Serving EITHER silently is the wound;
    the state must refuse DIVERGENT. (SilentServe serves the first copy — the
    exact plane-blind serve — and the saboteur suite proves the harness catches
    it.)
    """
    return ReplayCase(
        case_id="qa-rc-c-2-broken-legacy-plane-shadow-readable",
        predicate_id="RC-C-2",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _LEGACY_PLANE,
                74_585.0,
                _BULK_STAMP_AT,
                composition=_LEGACY_74585,
                digest="sha256:legacy-fragmentary",
            ),
            _qmat(
                _V2_PLANE,
                79_585.0,
                _FROZEN_AT,
                composition=_STALE_79585,
                digest="sha256:v2-frozen",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.DIVERGENT),
    )


# ═══ RC-D-1 — bridges carry a declared, enforced sunset ═══════════════════════


def _qa_d1_good_bridge_inside_sunset() -> ReplayCase:
    """A bridge WITH a declared, unexpired sunset serves — the only legal bridge.

    The good twin of the worked sunset-breach case: the transitional surface
    exists, its sunset is declared and machine-read, and the window is open.
    """
    return ReplayCase(
        case_id="qa-rc-d-1-good-bridge-inside-sunset",
        predicate_id="RC-D-1",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat("legacy-bridge", 80_000.0, _QNOW, digest="sha256:bridge"),
            sunset_after=_QNOW + timedelta(days=30),
        ),
        expected=ExpectServe(value=80_000.0, plane="legacy-bridge"),
    )


# ═══ RC-D-2 — the sunset is machine-enforced (teeth, not prose) ═══════════════


def _qa_d2_broken_one_second_past_sunset() -> ReplayCase:
    """BOUNDARY — ONE SECOND past the sunset goes red: the date is machine-read.

    If the sunset lived only in prose/ADR, a 1-second breach would change
    nothing. sunset→STALE per the frozen CLOSED RefuseReason grammar (TDD §11
    C13); the breach is machine-distinguishable via the asserted
    ``sunset_breach`` payload marker — no EXPIRED member is invented (the enum
    is closed; the rot-trigger for minting one is recorded in C13).
    """
    sunset = _QNOW - timedelta(seconds=1)
    return ReplayCase(
        case_id="qa-rc-d-2-broken-one-second-past-sunset",
        predicate_id="RC-D-2",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat("legacy-bridge", 80_000.0, _QNOW, digest="sha256:bridge"),
            sunset_after=sunset,
        ),
        expected=ExpectRefuse(
            reason=RefuseReason.STALE,
            sunset_breach=SunsetBreach(
                surface="legacy-bridge", sunset_after=sunset, observed_at=_QNOW
            ),
        ),
    )


def _qa_d2_good_sunset_boundary_at_now() -> ReplayCase:
    """BOUNDARY — sunset exactly AT now still serves (breach is strictly-after).

    The machine-enforcement boundary from the other side: the window closes the
    instant AFTER the declared sunset, not before. Paired with the 1-second-past
    broken twin, this pins the comparison the CI teeth must implement.
    """
    return ReplayCase(
        case_id="qa-rc-d-2-good-sunset-boundary-at-now",
        predicate_id="RC-D-2",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat("legacy-bridge", 80_000.0, _QNOW, digest="sha256:bridge"),
            sunset_after=_QNOW,
        ),
        expected=ExpectServe(value=80_000.0, plane="legacy-bridge"),
    )


# ═══ RC-D-3 — the dual-plane state cannot outlive its window ══════════════════


def _qa_d3_broken_legacy_plane_survives_cutover() -> ReplayCase:
    """Disabled-but-present legacy plane past cutover — must be detected, refused.

    The sharpest RC-D-3 form: the surviving legacy plane AGREES with v2 (looks
    harmless — 'disabled', mirror content) but the cutover window closed a day
    ago. The 2026-06-09 → 2026-07-27 immortality is exactly this state left
    unrefused for 7 weeks. sunset→STALE per the frozen grammar (TDD §11 C13),
    machine-distinguishable via the asserted ``sunset_breach`` marker.
    """
    sunset = _QNOW - timedelta(days=1)
    return ReplayCase(
        case_id="qa-rc-d-3-broken-legacy-plane-survives-cutover",
        predicate_id="RC-D-3",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            # the survivor resolves first — a reader would still touch legacy
            _qmat(
                _LEGACY_PLANE,
                84_385.0,
                _QNOW,
                composition=_FRESH_84385,
                digest="sha256:legacy-mirror",
            ),
            _qmat(
                _V2_PLANE,
                84_385.0,
                _QNOW,
                composition=_FRESH_84385,
                digest="sha256:v2-canonical",
            ),
            sunset_after=sunset,
        ),
        expected=ExpectRefuse(
            reason=RefuseReason.STALE,
            sunset_breach=SunsetBreach(
                surface=_LEGACY_PLANE, sunset_after=sunset, observed_at=_QNOW
            ),
        ),
    )


def _qa_d3_good_legacy_plane_deleted() -> ReplayCase:
    """Post-cutover the legacy plane is DELETED, not disabled → single copy serves.

    Charter P12: deletion, not disabling. No bridge, no sunset, no second plane —
    the terminal state RC-D-3 demands. The pair (deleted serves / present past
    sunset refuses) makes survival DETECTABLE, per the predicate's note that the
    deletion ACT is operator-gated but detectability is the acceptance surface.
    """
    return ReplayCase(
        case_id="qa-rc-d-3-good-legacy-plane-deleted",
        predicate_id="RC-D-3",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(_V2_PLANE, 84_385.0, _QNOW, composition=_FRESH_84385, digest="sha256:sole-plane"),
        ),
        expected=ExpectServe(value=84_385.0, plane=_V2_PLANE),
    )


# ═══ RC-E-1 — partial/failed build cannot corrupt prod ════════════════════════


def _qa_e1_broken_torn_mid_rebuild_frame() -> ReplayCase:
    """MID-REBUILD PARTIAL STATE VISIBLE: a torn artifact must never serve.

    The rebuild was killed after section 15 of 34; the visible frame is
    mixed-vintage. A torn frame cannot match ANY single proven digest — the
    proof proves last-good, the bytes are the tear: REFUSE CORRUPT. (RC-E-1's
    construction guarantee is stage-then-swap; this is the serve-altitude
    observable that a tear, if ever visible, is refused loudly.)
    """
    return ReplayCase(
        case_id="qa-rc-e-1-broken-torn-mid-rebuild-frame",
        predicate_id="RC-E-1",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                41_000.0,
                _QNOW,
                composition={"PARTIAL (15 of 34)": SectionCell(rows=15, value=41_000.0)},
                digest="sha256:last-good-proof",
                frame_digest="sha256:torn-mixed-vintage-15-of-34",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.CORRUPT),
    )


def _qa_e1_good_last_good_survives_kill() -> ReplayCase:
    """After a mid-build kill, prod is UNCHANGED: last-good serves atomically.

    The staged build died; the swap never happened; the canonical artifact is
    still the intact last-good (digest-consistent, within SLA) → SERVE. The
    atomic transition observable: last-good → next-good, never a mixture.
    """
    return ReplayCase(
        case_id="qa-rc-e-1-good-last-good-survives-kill",
        predicate_id="RC-E-1",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                79_585.0,
                _QNOW - timedelta(seconds=1_800),
                composition=_STALE_79585,
                digest="sha256:last-good-intact",
            ),
        ),
        expected=ExpectServe(value=79_585.0, plane=_V2_PLANE),
    )


# ═══ RC-F-1 / RC-F-2 — two-sided alarm (serve-altitude proxy) ═════════════════


def _qa_f1_good_silent_on_provable() -> ReplayCase:
    """The alarm's SILENT side on a provable state — pairs with RC-F-2.

    RC-F-1 fires on unprovability; its two-sided complement is that the coherent
    post-warm state does NOT fire (serves cleanly). The true alarm surface is
    the S6 observability seam; the harness proxies provability at serve altitude.
    """
    return ReplayCase(
        case_id="qa-rc-f-1-good-silent-on-provable",
        predicate_id="RC-F-1",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(_V2_PLANE, 84_385.0, _QNOW, composition=_FRESH_84385, digest="sha256:provable"),
        ),
        expected=ExpectServe(value=84_385.0, plane=_V2_PLANE),
    )


def _qa_f1_broken_fires_on_corrupt() -> ReplayCase:
    """The alarm fires on EVERY unprovability class, not only age-staleness.

    A digest-unprovable state (frame ≠ proof) is as unprovable as a 14-day-stale
    one; the worked RC-F-1 case covers the age class, this covers the integrity
    class → REFUSE CORRUPT (the fire, at serve altitude).
    """
    return ReplayCase(
        case_id="qa-rc-f-1-broken-fires-on-corrupt",
        predicate_id="RC-F-1",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                80_000.0,
                _QNOW,
                digest="sha256:proven",
                frame_digest="sha256:not-what-was-proven",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.CORRUPT),
    )


# ═══ RC-F-3 — provability signal independent of query traffic ═════════════════


def _qa_f3_broken_stale_under_query_silence() -> ReplayCase:
    """AL-5's query-gating wound: 14 days of silence must not mask staleness.

    Nobody queried the (project, entity) for 14 days (DEFECT :57 — the alarm's
    input metric only existed on query, so absence-of-query looked like health).
    The FIRST query after the silence hits a plane frozen since 07-13: the
    verdict is a pure function of (proof, now) — query history is not an input —
    so the staleness fires immediately: REFUSE STALE. (Heartbeat-emission
    independent of traffic is the S6 half; the structural
    no-query-history-input floor is asserted in the construction-refusal suite.)
    """
    return ReplayCase(
        case_id="qa-rc-f-3-broken-stale-under-query-silence",
        predicate_id="RC-F-3",
        variant=CaseVariant.BROKEN,
        state=_qstate(
            _qmat(
                _V2_PLANE,
                79_585.0,
                _FROZEN_AT,
                composition=_STALE_79585,
                digest="sha256:frozen-unqueried",
            ),
        ),
        expected=ExpectRefuse(reason=RefuseReason.STALE),
    )


def _qa_f3_good_rarely_queried_but_fresh() -> ReplayCase:
    """The complement: rarely queried but genuinely fresh serves — no false fire.

    The warmer kept the content fresh (10 minutes old) even though no consumer
    queried for days; the first query serves cleanly. Absence of traffic is not
    staleness — the two axes are independent, and the harness must not conflate
    them in either direction.
    """
    return ReplayCase(
        case_id="qa-rc-f-3-good-rarely-queried-but-fresh",
        predicate_id="RC-F-3",
        variant=CaseVariant.GOOD,
        state=_qstate(
            _qmat(_V2_PLANE, 84_385.0, _QNOW - timedelta(seconds=600), digest="sha256:warm-kept"),
        ),
        expected=ExpectServe(value=84_385.0, plane=_V2_PLANE),
    )


# ═══ RC-F-4 — the dead-man watches a proven-live signal ═══════════════════════


def _qa_f4_broken_watched_signal_absent() -> ReplayCase:
    """The dead-man's trigger condition: the watched signal went ABSENT → fire.

    The orphaned ``DMS-24h`` wound (DEFECT :57): a dead-man keyed on a retired
    metric is permanently inert — absence reads as fine. At serve altitude the
    watched artifact being absent must FIRE loudly (MISSING), never read as a
    silent zero. SilentServe's silent-zero on this exact state IS the orphaned
    dead-man behavior, and the saboteur suite proves the harness catches it.
    """
    return ReplayCase(
        case_id="qa-rc-f-4-broken-watched-signal-absent",
        predicate_id="RC-F-4",
        variant=CaseVariant.BROKEN,
        state=_qstate(),
        expected=ExpectRefuse(reason=RefuseReason.MISSING),
    )


def _qa_f4_good_watched_signal_live() -> ReplayCase:
    """The dead-man's healthy side: the watched signal is present and live.

    The artifact exists, is provable, and serves — the dead-man watching THIS
    signal is watching something that genuinely emits (not an orphan), and it
    stays silent. Paired with the absent twin: fires on absence, silent on
    presence — two-sided.
    """
    return ReplayCase(
        case_id="qa-rc-f-4-good-watched-signal-live",
        predicate_id="RC-F-4",
        variant=CaseVariant.GOOD,
        state=_qstate(_qmat(_V2_PLANE, 84_385.0, _QNOW, digest="sha256:live-signal")),
        expected=ExpectServe(value=84_385.0, plane=_V2_PLANE),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Registries + slot machinery
# ═══════════════════════════════════════════════════════════════════════════════

# PE worked builders span SERVE + every CLOSED refuse reason: DIVERGENT (exemplar),
# STALE, CORRUPT, MISSING.
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

# The QA-authored corpus: (predicate_id, variant, title, builder).
_QA_AUTHORED: tuple[tuple[str, CaseVariant, str, CaseBuilder], ...] = (
    (
        "RC-A-1",
        CaseVariant.GOOD,
        "empty-but-valid frame serves $0 (empty ≠ MISSING)",
        _qa_a1_good_empty_but_valid,
    ),
    (
        "RC-A-1",
        CaseVariant.BROKEN,
        "per-section + consolidated both readable → DIVERGENT",
        _qa_a1_broken_two_readable_copies,
    ),
    (
        "RC-A-2",
        CaseVariant.GOOD,
        "coherent post-warm serves $84,385 (composition asserted)",
        _qa_a2_good_coherent_post_warm,
    ),
    (
        "RC-A-2",
        CaseVariant.BROKEN,
        "zero-net composition-shift twins → DIVERGENT",
        _qa_a2_broken_zero_net_composition_shift,
    ),
    (
        "RC-A-3",
        CaseVariant.GOOD,
        "full rebuild refreshes exactly what the reader reads",
        _qa_a3_good_rebuild_refreshes_read,
    ),
    (
        "RC-A-4",
        CaseVariant.GOOD,
        "single-writer discipline: one canonical copy serves",
        _qa_a4_good_single_writer_discipline,
    ),
    (
        "RC-A-4",
        CaseVariant.BROKEN,
        "entity-blind shadow writer's legacy copy → DIVERGENT",
        _qa_a4_broken_entity_blind_shadow_writer,
    ),
    (
        "RC-B-1",
        CaseVariant.GOOD,
        "value edit with honestly re-derived proof serves",
        _qa_b1_good_value_edit_reproved,
    ),
    (
        "RC-B-1",
        CaseVariant.BROKEN,
        "D8: GID-set-preserving value edit → CORRUPT",
        _qa_b1_broken_gid_preserving_value_edit,
    ),
    (
        "RC-B-2",
        CaseVariant.GOOD,
        "age exactly == SLA serves (inclusive boundary)",
        _qa_b2_good_age_exactly_sla,
    ),
    (
        "RC-B-2",
        CaseVariant.BROKEN,
        "wound-replay: fresh-mtime-stale-content → CORRUPT",
        _qa_b2_broken_false_fresh_reconsolidation,
    ),
    (
        "RC-B-2",
        CaseVariant.BROKEN,
        "age == SLA + 1s → STALE (boundary's broken twin)",
        _qa_b2_broken_age_one_second_past_sla,
    ),
    (
        "RC-B-3",
        CaseVariant.GOOD,
        "MIN-over-sections honest aggregate proof serves",
        _qa_b3_good_min_over_section_instants,
    ),
    (
        "RC-B-3",
        CaseVariant.BROKEN,
        "one bulk stamp claiming 34 verification events → CORRUPT",
        _qa_b3_broken_bulk_stamp_34_sections,
    ),
    (
        "RC-B-4",
        CaseVariant.GOOD,
        "establishable currency serves (digest match)",
        _qa_b4_good_establishable_currency,
    ),
    (
        "RC-C-2",
        CaseVariant.GOOD,
        "entity-typed plane consumer path serves",
        _qa_c2_good_entity_typed_plane_serves,
    ),
    (
        "RC-C-2",
        CaseVariant.BROKEN,
        "entity-agnostic legacy shadow readable → DIVERGENT",
        _qa_c2_broken_legacy_plane_shadow_readable,
    ),
    (
        "RC-D-1",
        CaseVariant.GOOD,
        "bridge inside its declared sunset serves",
        _qa_d1_good_bridge_inside_sunset,
    ),
    (
        "RC-D-2",
        CaseVariant.GOOD,
        "sunset boundary at now serves (strictly-after breach)",
        _qa_d2_good_sunset_boundary_at_now,
    ),
    (
        "RC-D-2",
        CaseVariant.BROKEN,
        "one second past sunset → STALE + C13 marker",
        _qa_d2_broken_one_second_past_sunset,
    ),
    (
        "RC-D-3",
        CaseVariant.GOOD,
        "legacy plane DELETED post-cutover: single copy serves",
        _qa_d3_good_legacy_plane_deleted,
    ),
    (
        "RC-D-3",
        CaseVariant.BROKEN,
        "disabled-but-present legacy past cutover → STALE + C13 marker",
        _qa_d3_broken_legacy_plane_survives_cutover,
    ),
    (
        "RC-E-1",
        CaseVariant.GOOD,
        "last-good survives a mid-build kill (atomic swap)",
        _qa_e1_good_last_good_survives_kill,
    ),
    (
        "RC-E-1",
        CaseVariant.BROKEN,
        "torn mid-rebuild frame visible → CORRUPT",
        _qa_e1_broken_torn_mid_rebuild_frame,
    ),
    (
        "RC-F-1",
        CaseVariant.GOOD,
        "alarm silent on provable state (pairs with RC-F-2)",
        _qa_f1_good_silent_on_provable,
    ),
    (
        "RC-F-1",
        CaseVariant.BROKEN,
        "alarm fires on integrity-unprovability → CORRUPT",
        _qa_f1_broken_fires_on_corrupt,
    ),
    (
        "RC-F-3",
        CaseVariant.GOOD,
        "rarely queried but fresh serves (no false fire)",
        _qa_f3_good_rarely_queried_but_fresh,
    ),
    (
        "RC-F-3",
        CaseVariant.BROKEN,
        "14d query-silence never masks staleness → STALE",
        _qa_f3_broken_stale_under_query_silence,
    ),
    (
        "RC-F-4",
        CaseVariant.GOOD,
        "watched signal live: dead-man silent, value serves",
        _qa_f4_good_watched_signal_live,
    ),
    (
        "RC-F-4",
        CaseVariant.BROKEN,
        "watched signal absent → MISSING fires loudly",
        _qa_f4_broken_watched_signal_absent,
    ),
)

# Predicates whose falsifying input is UNCONSTRUCTABLE as a SeededState fixture —
# their acceptance mode is BY-CONSTRUCTION / process altitude. Realized two-sidedly
# in the construction-refusal suite (test_corpus_scaffold.py); slot build=None here.
CONSTRUCTION_ALTITUDE_IDS: frozenset[str] = frozenset(
    {"RC-C-1", "RC-C-3", "RC-E-2", "RC-E-3", "RC-E-4"}
)

# RC-F-2's REJECT side is a SUBSTRATE defect (over-refusal / alarm noise), not a
# corruptible input: per the discriminating-canary doctrine its broken side is the
# OverRefuse saboteur tripping on the GOOD case (asserted in the saboteur suite).
SABOTEUR_SIDE_ONLY_IDS: frozenset[str] = frozenset({"RC-F-2"})


def _build_slots() -> tuple[CaseSlot, ...]:
    by_predicate: dict[str, list[CaseSlot]] = {pid: [] for pid in ALL_PREDICATE_IDS}
    for predicate_id in ALL_PREDICATE_IDS:
        builder = _WORKED.get(predicate_id)
        if builder is not None:
            variant = CaseVariant.GOOD if predicate_id in _WORKED_GOOD else CaseVariant.BROKEN
            by_predicate[predicate_id].append(
                CaseSlot(
                    predicate_id=predicate_id,
                    variant=variant,
                    title=f"worked example ({variant.value})",
                    build=builder,
                )
            )
    for predicate_id, variant, title, builder in _QA_AUTHORED:
        by_predicate[predicate_id].append(
            CaseSlot(predicate_id=predicate_id, variant=variant, title=title, build=builder)
        )
    for predicate_id in sorted(CONSTRUCTION_ALTITUDE_IDS):
        by_predicate[predicate_id].append(
            CaseSlot(
                predicate_id=predicate_id,
                variant=CaseVariant.BROKEN,
                title=(
                    "construction-refusal (falsifying input unconstructable by design) — "
                    "realized two-sidedly in test_corpus_scaffold.py § construction-refusal"
                ),
                build=None,
            )
        )
    return tuple(slot for pid in ALL_PREDICATE_IDS for slot in by_predicate[pid])


CORPUS_SLOTS: tuple[CaseSlot, ...] = _build_slots()


def covered_predicate_ids() -> set[str]:
    """The set of predicate ids that have at least one slot."""
    return {slot.predicate_id for slot in CORPUS_SLOTS}


def filled_slots() -> list[CaseSlot]:
    """Slots with an executable replay builder."""
    return [slot for slot in CORPUS_SLOTS if slot.build is not None]


def construction_slots() -> list[CaseSlot]:
    """Slots realized at construction altitude (``build is None`` BY DESIGN).

    These are NOT pending: their falsifying inputs are unconstructable as
    ``SeededState`` fixtures — that is the predicate's acceptance mode — and
    their two-sided teeth live in the construction-refusal suite.
    """
    return [slot for slot in CORPUS_SLOTS if slot.build is None]


def filled_cases() -> list[ReplayCase]:
    """Build every executable replay case (construction slots excluded)."""
    return [slot.build() for slot in CORPUS_SLOTS if slot.build is not None]
