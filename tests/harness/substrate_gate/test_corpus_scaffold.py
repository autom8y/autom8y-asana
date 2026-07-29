"""Corpus coverage + saboteur teeth + construction-refusal (S7 · qa-adversary).

Three suites over the AUTHORED 22-predicate corpus:

§1 COVERAGE — every predicate has >=1 slot; every replay predicate is TWO-SIDED
   (>=1 GOOD and >=1 BROKEN slot); variants and expectations cohere; the corpus
   spans SERVE + every CLOSED refuse reason; case ids are unique.

§2 SABOTEURS (anti-vacuity) — every replay case passes under the REFERENCE
   substrate AND fails under the variant-appropriate saboteur: every BROKEN case
   trips ``SilentServeSubstrate``'s silent serve (the v1 wound), every GOOD case
   trips ``OverRefuseSubstrate``'s noise. A case both a correct and a defective
   substrate would pass is vacuous — this suite makes vacuity unconstructable.
   The C13 sunset-marker cases additionally FAIL a marker-blind refusal even when
   the STALE reason coincides (OverRefuse refuses STALE without the marker).

§3 CONSTRUCTION-REFUSAL — the five BY-CONSTRUCTION predicates (RC-C-1, RC-C-3,
   RC-E-2, RC-E-3, RC-E-4) whose falsifying inputs are UNCONSTRUCTABLE, realized
   two-sidedly: the blind/impure construction is REFUSED (TypeError /
   FrozenInstanceError / structural flag) while the disciplined twin succeeds —
   the refusal bites ONLY on the defect. Plus the RC-C-2 type floor and the
   RC-F-3 no-query-history-input structural floor.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.serve import Provable, RefuseReason
from tests.harness.substrate_gate import (
    ALL_PREDICATE_IDS,
    CONSTRUCTION_ALTITUDE_IDS,
    CORPUS_SLOTS,
    SABOTEUR_SIDE_ONLY_IDS,
    CaseVariant,
    ExpectRefuse,
    ExpectServe,
    HarnessSubstrate,
    Materialization,
    OverRefuseSubstrate,
    ReferenceSubstrate,
    ReplayRunner,
    ResultStatus,
    SectionCell,
    SeededState,
    SilentServeSubstrate,
    construction_slots,
    covered_predicate_ids,
    filled_cases,
    filled_slots,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from autom8_asana.substrate.serve import ServedNumber

# ═══════════════════════════════════════════════════════════════════════════════
# §1 COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════


def test_all_22_predicates_have_at_least_one_slot() -> None:
    assert len(ALL_PREDICATE_IDS) == 22
    assert len(set(ALL_PREDICATE_IDS)) == 22
    assert covered_predicate_ids() == set(ALL_PREDICATE_IDS)


def test_every_replay_predicate_is_two_sided() -> None:
    """Every non-construction predicate carries >=1 GOOD and >=1 BROKEN replay slot.

    RC-F-2's REJECT side is a substrate defect (over-refusal), not a corruptible
    input — its broken side is the OverRefuse saboteur leg (§2), so it is exempt
    from the input-level BROKEN requirement (and only it).
    """
    good_ids = {s.predicate_id for s in filled_slots() if s.variant is CaseVariant.GOOD}
    broken_ids = {s.predicate_id for s in filled_slots() if s.variant is CaseVariant.BROKEN}
    replay_ids = set(ALL_PREDICATE_IDS) - CONSTRUCTION_ALTITUDE_IDS
    assert set(SABOTEUR_SIDE_ONLY_IDS) == {"RC-F-2"}
    missing_good = replay_ids - good_ids
    missing_broken = replay_ids - broken_ids - SABOTEUR_SIDE_ONLY_IDS
    assert not missing_good, f"predicates without a GOOD (serve-side) case: {missing_good}"
    assert not missing_broken, f"predicates without a BROKEN (reject-side) case: {missing_broken}"


def test_every_slot_variant_matches_expected_shape() -> None:
    for slot in filled_slots():
        assert (
            slot.build is not None
        )  # filled_slots() guarantees this; narrows for the type checker
        case = slot.build()
        assert case.predicate_id == slot.predicate_id
        if slot.variant is CaseVariant.BROKEN:
            assert isinstance(case.expected, ExpectRefuse), slot.predicate_id
        else:
            assert isinstance(case.expected, ExpectServe), slot.predicate_id


def test_construction_slots_are_exactly_the_by_construction_predicates() -> None:
    """No pending slots remain: build=None marks construction altitude, by design."""
    assert {slot.predicate_id for slot in construction_slots()} == CONSTRUCTION_ALTITUDE_IDS
    for slot in construction_slots():
        assert slot.build is None
        assert "construction-refusal" in slot.title


def test_corpus_spans_serve_and_every_closed_refuse_reason() -> None:
    reasons: set[RefuseReason] = set()
    served = False
    for case in filled_cases():
        if isinstance(case.expected, ExpectRefuse):
            reasons.add(case.expected.reason)
        else:
            served = True
    assert served, "corpus must include at least one SERVE case"
    assert reasons == {
        RefuseReason.STALE,
        RefuseReason.CORRUPT,
        RefuseReason.MISSING,
        RefuseReason.DIVERGENT,
    }


def test_case_ids_are_unique_across_the_corpus() -> None:
    ids = [case.case_id for case in filled_cases()]
    assert len(ids) == len(set(ids)), "duplicate case_id — a sloppy-author corpus defect"


def test_predicate_id_on_each_case_is_a_known_predicate() -> None:
    known = set(ALL_PREDICATE_IDS)
    for case in filled_cases():
        assert case.predicate_id in known


def test_every_slot_in_corpus_slots_is_accounted() -> None:
    assert len(CORPUS_SLOTS) == len(filled_slots()) + len(construction_slots())


# ═══════════════════════════════════════════════════════════════════════════════
# §2 SABOTEURS — anti-vacuity: reference passes, the wrong substrate is CAUGHT
# ═══════════════════════════════════════════════════════════════════════════════


def test_reference_passes_the_entire_corpus() -> None:
    runner = ReplayRunner(ReferenceSubstrate())
    results = runner.run(filled_cases())
    failures = [(r.case_id, r.detail) for r in results if r.status is not ResultStatus.PASS]
    assert not failures, failures


def test_every_broken_case_trips_silent_serve() -> None:
    """The v1 wound side: a substrate serving regardless MUST fail every BROKEN case."""
    runner = ReplayRunner(SilentServeSubstrate())
    broken = [c for c in filled_cases() if isinstance(c.expected, ExpectRefuse)]
    assert broken
    for case in broken:
        result = runner.run_case(case)
        assert result.status is ResultStatus.FAIL, (case.case_id, result.detail)
        assert "SILENT WRONG-SERVE" in result.detail, (case.case_id, result.detail)


def test_every_good_case_trips_over_refuse() -> None:
    """The noise side: a substrate refusing everything MUST fail every GOOD case."""
    runner = ReplayRunner(OverRefuseSubstrate())
    good = [c for c in filled_cases() if isinstance(c.expected, ExpectServe)]
    assert good
    for case in good:
        result = runner.run_case(case)
        assert result.status is ResultStatus.FAIL, (case.case_id, result.detail)
        assert "OVER-REFUSAL" in result.detail, (case.case_id, result.detail)


def test_sunset_marker_cases_catch_a_marker_blind_refusal() -> None:
    """C13 teeth: a STALE refusal WITHOUT the sunset_breach marker FAILS.

    OverRefuse refuses STALE with a plain (marker-less) payload — on the sunset
    cases the REASON coincides, so only the marker assertion discriminates. This
    proves the marker is machine-checked, not comment-only.
    """
    runner = ReplayRunner(OverRefuseSubstrate())
    marker_cases = [
        c
        for c in filled_cases()
        if isinstance(c.expected, ExpectRefuse) and c.expected.sunset_breach is not None
    ]
    assert len(marker_cases) >= 3, "expected the RC-D-1/D-2/D-3 sunset-marker cases"
    for case in marker_cases:
        assert isinstance(case.expected, ExpectRefuse)  # narrows for the type checker
        assert case.expected.reason is RefuseReason.STALE  # frozen grammar: sunset→STALE
        result = runner.run_case(case)
        assert result.status is ResultStatus.FAIL, (case.case_id, result.detail)
        assert "sunset_breach" in result.detail, (case.case_id, result.detail)


def test_no_case_is_vacuous() -> None:
    """The discriminating-canary property in one matrix: for EVERY case the
    reference PASSES and the variant-appropriate saboteur FAILS. A case that
    cannot separate a correct substrate from a defective one has no teeth."""
    reference = ReplayRunner(ReferenceSubstrate())
    silent = ReplayRunner(SilentServeSubstrate())
    noisy = ReplayRunner(OverRefuseSubstrate())
    for case in filled_cases():
        assert reference.run_case(case).status is ResultStatus.PASS, case.case_id
        saboteur = silent if isinstance(case.expected, ExpectRefuse) else noisy
        assert saboteur.run_case(case).status is ResultStatus.FAIL, case.case_id


# ═══════════════════════════════════════════════════════════════════════════════
# §3 CONSTRUCTION-REFUSAL — the BY-CONSTRUCTION predicates, two-sided
# ═══════════════════════════════════════════════════════════════════════════════

_NOW = datetime(2026, 7, 27, 15, 27, tzinfo=UTC)


def _fresh_materialization(value: float = 84_385.0) -> Materialization:
    return Materialization(
        plane="v2/offer",
        proof=FreshnessProof(built_from_live_at=_NOW, content_digest="sha256:c", sla_seconds=3_600),
        served_value=value,
        composition={"ALL": SectionCell(rows=1, value=value)},
        frame_digest="sha256:c",
    )


# ── RC-C-1: a read/key-build cannot be constructed without a plane discriminator ─


def test_rc_c_1_broken_plane_blind_construction_refused() -> None:
    """The entity-blind construction ATTEMPT (the prober's zero-entity_type shape)
    is refused at the type level: ``ArtifactId`` without ``entity_type`` raises
    TypeError at runtime and is a mypy error statically. This is the harness's
    construction-refusal encoding of RC-C-1 — the falsifying input cannot exist."""
    blind_ctor = cast("Callable[..., ArtifactId]", ArtifactId)
    with pytest.raises(TypeError):
        blind_ctor(project_gid="1143843662099250")


def test_rc_c_1_good_typed_construction_serves() -> None:
    """Two-sided: the SAME construction WITH the discriminator succeeds and serves —
    the refusal bites only on the omission, not on construction per se."""
    aid = ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)
    state = SeededState(aid=aid, materializations=(_fresh_materialization(),), now=_NOW)
    assert isinstance(ReferenceSubstrate().serve(state), Provable)


def test_rc_c_1_discriminator_has_no_default_and_no_none() -> None:
    """The structural floor: the falsifying signature shape is
    ``entity_type: str | None = None`` (RC spec §V-1). Assert the frozen seam
    carries NEITHER a default NOR optionality on the discriminator."""
    parameter = inspect.signature(ArtifactId).parameters["entity_type"]
    assert parameter.default is inspect.Parameter.empty, "discriminator must have NO default"
    (entity_field,) = [f for f in dataclasses.fields(ArtifactId) if f.name == "entity_type"]
    annotation = str(entity_field.type)
    assert "None" not in annotation and "Optional" not in annotation, annotation


# ── RC-C-2: the type floor under every consumer path ───────────────────────────


def test_rc_c_2_seeded_state_requires_a_typed_aid() -> None:
    """A serve cannot even be REQUESTED plane-blind: ``SeededState`` requires an
    ``ArtifactId`` (which requires ``EntityType``). The serve-altitude halves of
    RC-C-2 are the qa-rc-c-2-* replay cases; the per-path matrix is S8's."""
    blind_state = cast("Callable[..., SeededState]", SeededState)
    with pytest.raises(TypeError):
        blind_state(materializations=(), now=_NOW)  # no aid: unconstructable


# ── RC-C-3: a brand-new consumer cannot bypass — there is no guard LIST ────────


def test_rc_c_3_brand_new_consumer_cannot_go_plane_blind() -> None:
    """A BRAND-NEW consumer (defined here, referencing NO inventory/guard list —
    the layer the v1 call-site inventory missed) still cannot construct a
    plane-blind read: the requirement travels with the TYPE, not with a
    maintained list of method names. Two-sided in one function: the blind call
    refuses, the typed call serves."""

    def brand_new_consumer(project_gid: str, entity_type: EntityType | None) -> ServedNumber:
        # a fresh consumer wired straight to the primitives — no guard imports
        if entity_type is None:
            blind_ctor = cast("Callable[..., ArtifactId]", ArtifactId)
            aid = blind_ctor(project_gid=project_gid)  # ← must raise
        else:
            aid = ArtifactId(project_gid=project_gid, entity_type=entity_type)
        state = SeededState(aid=aid, materializations=(_fresh_materialization(),), now=_NOW)
        return ReferenceSubstrate().serve(state)

    with pytest.raises(TypeError):
        brand_new_consumer("1143843662099250", None)
    assert isinstance(brand_new_consumer("1143843662099250", EntityType.OFFER), Provable)


# ── RC-E-2: a read-typed path is provably side-effect-free ─────────────────────


def test_rc_e_2_serve_is_pure_and_input_is_write_refused() -> None:
    """The DEFECT :76 class at harness altitude: the read path (serve) produces
    ZERO writes into the seeded prod-state — and a write ATTEMPT into that state
    is refused at attribute altitude (frozen), two-sidedly proving the purity is
    enforced, not incidental."""
    materialization = _fresh_materialization()
    state = SeededState(aid=_typed_aid(), materializations=(materialization,), now=_NOW)
    first = ReferenceSubstrate().serve(state)
    second = ReferenceSubstrate().serve(state)
    assert isinstance(first, Provable) and isinstance(second, Provable)
    assert first.frame == second.frame  # idempotent read: no state was consumed/mutated
    # the write attempt — the mid-fetch persist DEFECT :76 documents — is REFUSED:
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(materialization, "served_value", 0.0)  # noqa: B010
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(state, "materializations", ())  # noqa: B010


def _typed_aid() -> ArtifactId:
    return ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)


# ── RC-E-3: write capability is explicit — the read surface carries NONE ───────

_WRITE_TOKENS = ("write", "put", "save", "persist", "upload", "delete", "stamp")


def _write_named_members(obj: object) -> list[str]:
    return [
        name
        for name in dir(obj)
        if not name.startswith("_") and any(token in name.lower() for token in _WRITE_TOKENS)
    ]


def test_rc_e_3_read_surface_exposes_no_write_capability() -> None:
    """A path typed as read cannot silently persist: the harness read surface
    (``HarnessSubstrate`` protocol + the reference oracle) exposes ONLY ``serve``
    and no write-named capability; ``serve``'s signature carries no writer/store."""
    assert _write_named_members(ReferenceSubstrate()) == []
    protocol_members = [
        name for name in dir(HarnessSubstrate) if not name.startswith("_") and name != "serve"
    ]
    assert protocol_members == []
    assert list(inspect.signature(ReferenceSubstrate().serve).parameters) == ["state"]


def test_rc_e_3_probe_flags_a_write_capable_surface() -> None:
    """Two-sided teeth for the probe itself: a surface that DOES carry an explicit
    write capability is FLAGGED — the check discriminates, it does not rubber-stamp."""

    class WriteCapableFake:
        def serve(self, state: SeededState) -> None:  # pragma: no cover - never driven
            raise NotImplementedError

        def persist_section(self) -> None:  # pragma: no cover - never driven
            raise NotImplementedError

    assert _write_named_members(WriteCapableFake()) == ["persist_section"]


# ── RC-E-4: a rebuild/parity source is paced — an unpaced one is DISTINGUISHABLE ─


def test_rc_e_4_paced_source_true_unpaced_fake_flagged() -> None:
    """The RC-E-4 routing invariant is a checkable property of the object: the
    real parity source routes through v1's paced primitives (property True); a
    brand-new UNPACED source lacks the property and is flagged False — the
    429-storm shape is distinguishable, not assumed away. (The dark-guard +
    no-AsanaClient-import halves live in test_parity_dark_guard.)"""
    from tests.harness.substrate_gate import PacedLiveParitySource

    class UnpacedFake:
        def fetch(self, aid: ArtifactId) -> None:  # pragma: no cover - never driven
            raise NotImplementedError

    def is_paced(source: object) -> bool:
        probe = getattr(source, "routes_through_paced_primitives", None)
        return bool(probe()) if callable(probe) else False

    assert is_paced(PacedLiveParitySource()) is True
    assert is_paced(UnpacedFake()) is False


# ── RC-F-3 structural floor: query history is not an input to provability ──────


def test_rc_f_3_no_query_history_input_exists() -> None:
    """The verdict is a pure function of (proof, digest, now): ``FreshnessProof``
    carries NO query/traffic field, and serving the same state repeatedly (many
    queries) yields byte-identical verdicts — query count cannot influence
    provability in either direction."""
    field_names = {f.name for f in dataclasses.fields(FreshnessProof)}
    assert field_names == {"built_from_live_at", "content_digest", "sla_seconds"}
    state = SeededState(aid=_typed_aid(), materializations=(_fresh_materialization(),), now=_NOW)
    results = [ReferenceSubstrate().serve(state) for _ in range(3)]
    frames = [r.frame for r in results if isinstance(r, Provable)]
    assert len(frames) == 3 and len(set(frames)) == 1
