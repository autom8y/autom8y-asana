"""Tests for the id-walk SUPPLY (identity-activity substrate, S-B5).

The keystone here is the TWO-SIDED proof that ``CONFIDENCE_TIER_4 = 0.9`` cannot
wave a self-flagged identification through. Both arms drive the REAL five-tier
detector through the REAL upward walk -- neither side is a stubbed disposition.

Every gid and every name in this file is synthetic (W-3): no real client name, no
real Asana gid other than the Businesses PROJECT gid, which is a registry constant
already present in the source tree and is not a client identifier.
"""

from __future__ import annotations

import ast
import inspect
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.errors import HydrationError
from autom8_asana.models.business.detection.tier4 import (
    detect_by_structure_inspection,
)
from autom8_asana.models.business.detection.types import (
    CONFIDENCE_TIER_1,
    CONFIDENCE_TIER_2,
    CONFIDENCE_TIER_3,
    CONFIDENCE_TIER_4,
    CONFIDENCE_TIER_5,
)
from autom8_asana.models.business.hydration import (
    _traverse_upward_async,
    _traverse_upward_with_detection_async,
)
from autom8_asana.models.business.identity_supply import (
    RATIFIED_ABSENT_REASONS,
    TIER4_ABSENT_REASON,
    TIER_STRUCTURE_INSPECTION,
    AbsentReason,
    BusinessCandidate,
    Evidence,
    Grain,
    IdentitySupply,
    Population,
    Supplier,
    SystemOfRecord,
    WalkOutcome,
    build_identity_supply,
    classify_identification,
    supply_identity_evidence_async,
    walk_business_candidates_async,
)
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task

# The Businesses PROJECT gid -- a registry constant, not a client identifier.
BUSINESSES_PROJECT_GID = "1200653012566782"

OBSERVED_AT = datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC)


# =============================================================================
# Fixture builders -- synthetic hierarchy, real detector
# =============================================================================


def _client(
    *,
    business_task: Task,
    business_subtasks: list[Task] | None = None,
) -> MagicMock:
    """A read-only client over: offer o1 -> holder oh1 -> business b1."""
    client = MagicMock()
    client._cache_provider = None

    async def get_async(gid: str, **_kwargs: object) -> Task:
        if gid == "o1":
            return Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="oh1", name="Offers"))
        if gid == "oh1":
            return Task(
                gid="oh1",
                name="Offers",
                parent=NameGid(gid="b1", name="Fixture Business A"),
            )
        if gid == "b1":
            return business_task
        raise ValueError(f"Unexpected gid: {gid}")

    client.tasks.get_async = AsyncMock(side_effect=get_async)

    def subtasks(gid: str, **_kwargs: object) -> AsyncMock:
        mock = AsyncMock()
        if gid == "b1" and business_subtasks is not None:
            mock.collect = AsyncMock(return_value=business_subtasks)
        else:
            mock.collect = AsyncMock(return_value=[])
        return mock

    client.tasks.subtasks_async.side_effect = subtasks
    return client


def _clean_tier1_client() -> MagicMock:
    """Business identified DETERMINISTICALLY by project membership (Tier 1)."""
    return _client(
        business_task=Task(
            gid="b1",
            name="Fixture Business A",
            memberships=[{"project": {"gid": BUSINESSES_PROJECT_GID, "name": "Businesses"}}],
        )
    )


def _selfflagged_tier4_client() -> MagicMock:
    """Business identified by SUBTASK-NAME STRUCTURE INSPECTION (Tier 4).

    No project membership, so Tiers 1-3 all miss; the traversal path turns Tier 4
    on and the detector concludes BUSINESS from the lowercased subtask names,
    self-flagging ``needs_healing=True`` at confidence 0.9.
    """
    return _client(
        business_task=Task(gid="b1", name="Fixture Business A"),
        business_subtasks=[
            Task(gid="ch1", name="Contacts"),
            Task(gid="uh1", name="Units"),
        ],
    )


def _candidate(
    *,
    gid: str = "b1",
    name: str | None = "Fixture Business A",
    detection_tier: int | None = 1,
    needs_healing: bool | None = False,
) -> BusinessCandidate:
    return BusinessCandidate(
        gid=gid, name=name, detection_tier=detection_tier, needs_healing=needs_healing
    )


# =============================================================================
# E3 -- THE TWO-SIDED CONFIDENCE_TIER_4 PROOF (the keystone)
# =============================================================================


class TestTierFourIsNotWavedThrough:
    """CONFIDENCE_TIER_4 = 0.9 must not wave a self-flagged row through."""

    def test_the_trap_is_real_tier4_outranks_tier3_on_confidence(self) -> None:
        """Pin the premise: the flagged tier carries the SECOND-HIGHEST confidence.

        If this ever stops being true the trap changes shape and the receipt that
        rests on it must be re-read.
        """
        assert pytest.approx(0.9) == CONFIDENCE_TIER_4
        assert CONFIDENCE_TIER_4 > CONFIDENCE_TIER_3 == pytest.approx(0.8)
        assert CONFIDENCE_TIER_4 > CONFIDENCE_TIER_2 == pytest.approx(0.6)
        assert CONFIDENCE_TIER_4 < CONFIDENCE_TIER_1 == pytest.approx(1.0)
        # A guard of the shape `if confidence >= 0.8: accept` would accept it.
        assert CONFIDENCE_TIER_4 >= 0.8

    async def test_side_i_selfflagged_tier4_is_refused_not_published(self) -> None:
        """SIDE (i): a self-flagged Tier-4 node is TYPED, never emitted as a value."""
        client = _selfflagged_tier4_client()

        # The walk really does land on it, at really 0.9, really self-flagged.
        _business, _path, detection = await _traverse_upward_with_detection_async(
            Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="oh1", name="Offers")),
            client,
        )
        assert detection.tier_used == TIER_STRUCTURE_INSPECTION
        assert detection.confidence == pytest.approx(CONFIDENCE_TIER_4)
        assert detection.needs_healing is True

        supply = await supply_identity_evidence_async(client, "o1", observed_at=OBSERVED_AT)

        for family in ("asana_business", "business_display_name"):
            ev = supply.families()[family]
            assert ev.value is None, f"{family} published a self-flagged value"
            assert ev.absent_reason is TIER4_ABSENT_REASON
            # The discarded discriminators are CARRIED, not dropped (E1/CW-S09-3).
            assert ev.detection_tier == 4
            assert ev.needs_healing is True
            assert ev.supplier is Supplier.ID_WALK

    async def test_side_ii_clean_tier1_passes(self) -> None:
        """SIDE (ii): a clean Tier-1 node at confidence 1.0 IS published."""
        client = _clean_tier1_client()

        _business, _path, detection = await _traverse_upward_with_detection_async(
            Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="oh1", name="Offers")),
            client,
        )
        assert detection.tier_used == 1
        assert detection.confidence == pytest.approx(CONFIDENCE_TIER_1)
        assert detection.needs_healing is False

        supply = await supply_identity_evidence_async(client, "o1", observed_at=OBSERVED_AT)

        assert supply.asana_business.value == "b1"
        assert supply.asana_business.absent_reason is None
        assert supply.asana_business.detection_tier == 1
        assert supply.asana_business.needs_healing is False
        assert supply.business_display_name.value == "Fixture Business A"
        assert supply.business_display_name.absent_reason is None

    def test_side_ii_b_a_clean_node_without_the_flag_passes(self) -> None:
        """SIDE (ii-b): unflagged identifications pass at every tier the walk can reach.

        The detector cannot currently emit a clean node AT confidence 0.9 (see
        :meth:`TestDetectorSelfFlagging.test_tier4_always_self_flags`), so the
        nearest reachable arm is an unflagged non-Tier-4 identification. It passes.
        """
        for tier in (1, 2, 3):
            supply = build_identity_supply(
                WalkOutcome(
                    offer_gid="o1",
                    candidates=(_candidate(detection_tier=tier, needs_healing=False),),
                    failure=None,
                ),
                observed_at=OBSERVED_AT,
            )
            assert supply.asana_business.value == "b1", f"tier {tier} was refused"

    def test_the_disposition_is_CONFIDENCE_INVARIANT(self) -> None:
        """Moving CONFIDENCE_TIER_4 cannot change any disposition.

        The guard has no confidence parameter, so this is provable by signature as
        well as by behaviour. Both are asserted.
        """
        assert "confidence" not in inspect.signature(classify_identification).parameters

        for confidence in (
            CONFIDENCE_TIER_1,
            CONFIDENCE_TIER_2,
            CONFIDENCE_TIER_3,
            CONFIDENCE_TIER_4,
            CONFIDENCE_TIER_5,
            0.0,
            0.5,
            1.0,
        ):
            # The number is deliberately unused: it cannot reach the guard.
            assert confidence is not None
            assert classify_identification(1, False) is None
            assert classify_identification(4, True) is TIER4_ABSENT_REASON

    def test_the_flag_alone_refuses_even_at_a_non_four_tier(self) -> None:
        """``needs_healing`` refuses on its own -- the tier number is not the only teeth."""
        assert classify_identification(1, True) is TIER4_ABSENT_REASON
        assert classify_identification(3, True) is TIER4_ABSENT_REASON

    def test_tier_four_refuses_even_when_the_flag_is_absent(self) -> None:
        """Tier 4 refuses on its own -- so a future detector that drops the flag
        cannot silently re-open the hole."""
        assert classify_identification(4, False) is TIER4_ABSENT_REASON
        assert classify_identification(4, None) is TIER4_ABSENT_REASON

    def test_an_undisclosed_tier_is_undecidable_not_accepted(self) -> None:
        assert classify_identification(None, False) is AbsentReason.UNDECIDABLE
        assert classify_identification(None, None) is AbsentReason.UNDECIDABLE


class TestGuardHasTeeth:
    """The assertion battery must bite ONLY on the defect.

    A no-op guard and a conflating guard are each run through the same battery the
    real guard passes. If either survived, the battery would be matching on shape
    rather than substance.
    """

    @staticmethod
    def _battery(guard) -> list[str]:  # noqa: ANN001 - local test helper
        """Return the names of the assertions this guard FAILS."""
        failures: list[str] = []
        if guard(4, True) is None:
            failures.append("admits_selfflagged_tier4")
        if guard(1, False) is not None:
            failures.append("refuses_clean_tier1")
        if guard(1, True) is None:
            failures.append("admits_flagged_tier1")
        if guard(None, None) is None:
            failures.append("admits_undisclosed_tier")
        return failures

    def test_the_real_guard_passes_the_battery(self) -> None:
        assert self._battery(classify_identification) == []

    def test_a_noop_guard_is_rejected(self) -> None:
        """A guard that admits everything fails 3 of 4 -- the battery is not vacuous."""
        failures = self._battery(lambda _tier, _flag: None)
        assert set(failures) == {
            "admits_selfflagged_tier4",
            "admits_flagged_tier1",
            "admits_undisclosed_tier",
        }

    def test_a_conflating_guard_is_rejected(self) -> None:
        """A guard that refuses everything fails the clean arm -- so the battery is
        two-sided and cannot be satisfied by blanket refusal."""
        failures = self._battery(lambda _tier, _flag: AbsentReason.UNDECIDABLE)
        assert failures == ["refuses_clean_tier1"]


class TestDetectorSelfFlagging:
    """Pin the emitter: Tier 4 ALWAYS self-flags, on both of its branches."""

    async def test_tier4_always_self_flags(self) -> None:
        client = MagicMock()

        def subtasks(_gid: str, **_kwargs: object) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(
                return_value=[Task(gid="s1", name="Contacts"), Task(gid="s2", name="Units")]
            )
            return mock

        client.tasks.subtasks_async.side_effect = subtasks
        result = await detect_by_structure_inspection(Task(gid="x1", name="X"), client)
        assert result is not None
        assert result.tier_used == 4
        assert result.needs_healing is True
        assert result.confidence == pytest.approx(CONFIDENCE_TIER_4)

    async def test_tier4_unit_branch_also_self_flags(self) -> None:
        client = MagicMock()

        def subtasks(_gid: str, **_kwargs: object) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[Task(gid="s1", name="Offers")])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks
        result = await detect_by_structure_inspection(Task(gid="x1", name="X"), client)
        assert result is not None
        assert result.needs_healing is True


# =============================================================================
# E2 -- the hydration DISCARD is cured
# =============================================================================


class TestDiscardIsCured:
    async def test_detection_crosses_the_return_boundary(self) -> None:
        client = _clean_tier1_client()
        _business, _path, detection = await _traverse_upward_with_detection_async(
            Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="oh1", name="Offers")),
            client,
        )
        # All three discriminators, previously dead at `:711`, are now reachable.
        assert detection.tier_used == 1
        assert detection.needs_healing is False
        assert detection.confidence == pytest.approx(1.0)

    async def test_the_two_tuple_wrapper_is_behaviour_preserving(self) -> None:
        entry = Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="oh1", name="Offers"))
        wrapped = await _traverse_upward_async(entry, _clean_tier1_client())
        full = await _traverse_upward_with_detection_async(entry, _clean_tier1_client())

        assert len(wrapped) == 2
        assert wrapped[0].gid == full[0].gid
        assert wrapped[0].name == full[0].name
        assert [e.gid for e in wrapped[1]] == [e.gid for e in full[1]]

    @pytest.mark.parametrize(
        ("scenario", "expected"),
        [
            ("no_parent", "parent_absent"),
            ("root_without_business", "walk_root_without_business"),
            ("cycle", "walk_cycle"),
            ("depth", "walk_depth_exceeded"),
        ],
    )
    async def test_the_three_raise_sites_no_longer_collapse(
        self, scenario: str, expected: str
    ) -> None:
        """Four distinct causes, four distinct tags. They used to be one exception."""
        client = MagicMock()
        client._cache_provider = None

        def subtasks(_gid: str, **_kwargs: object) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks

        if scenario == "no_parent":
            entry = Task(gid="o1", name="Fixture Offer A")
            client.tasks.get_async = AsyncMock(side_effect=AssertionError("no fetch"))
        elif scenario == "root_without_business":
            entry = Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="p1", name="P"))
            client.tasks.get_async = AsyncMock(
                side_effect=lambda gid, **_k: Task(gid="p1", name="P")
            )
        elif scenario == "cycle":
            entry = Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="p1", name="P"))

            async def cyclic(gid: str, **_kwargs: object) -> Task:
                return Task(gid="p1", name="P", parent=NameGid(gid="p1", name="P"))

            client.tasks.get_async = AsyncMock(side_effect=cyclic)
        else:  # depth
            entry = Task(gid="o1", name="Fixture Offer A", parent=NameGid(gid="p0", name="P"))
            counter = {"n": 0}

            async def deep(_gid: str, **_kwargs: object) -> Task:
                counter["n"] += 1
                return Task(
                    gid=f"p{counter['n']}",
                    name="P",
                    parent=NameGid(gid=f"p{counter['n'] + 1}", name="P"),
                )

            client.tasks.get_async = AsyncMock(side_effect=deep)

        with pytest.raises(HydrationError) as excinfo:
            await _traverse_upward_with_detection_async(entry, client, max_depth=3)
        assert excinfo.value.walk_failure == expected

    async def test_typed_walk_failures_reach_the_supply(self) -> None:
        """And the supply publishes the SPECIFIC reason, not a collapsed one."""
        client = MagicMock()
        client._cache_provider = None
        client.tasks.get_async = AsyncMock(
            side_effect=lambda gid, **_k: Task(gid="o1", name="Fixture Offer A")
        )

        def subtasks(_gid: str, **_kwargs: object) -> AsyncMock:
            mock = AsyncMock()
            mock.collect = AsyncMock(return_value=[])
            return mock

        client.tasks.subtasks_async.side_effect = subtasks

        outcome = await walk_business_candidates_async(client, "o1")
        assert outcome.failure is AbsentReason.PARENT_ABSENT
        assert outcome.candidates == ()

        supply = build_identity_supply(outcome, observed_at=OBSERVED_AT)
        assert supply.asana_business.absent_reason is AbsentReason.PARENT_ABSENT
        assert supply.asana_business.value is None

    def test_an_untagged_hydration_error_degrades_to_undecidable(self) -> None:
        """A future raise site that forgets the tag must not be mis-attributed."""
        from autom8_asana.models.business.identity_supply import _failure_reason

        exc = HydrationError("boom", entity_gid="x", phase="upward")
        assert exc.walk_failure is None
        assert _failure_reason(exc) is AbsentReason.UNDECIDABLE

    def test_walk_failure_defaults_to_none_for_every_existing_caller(self) -> None:
        """The new kwarg is purely additive."""
        exc = HydrationError("boom", entity_gid="x", phase="downward")
        assert exc.walk_failure is None


# =============================================================================
# SET, never PICK
# =============================================================================


class TestSetNeverPick:
    def test_two_candidates_publish_no_value_and_disclose_the_set(self) -> None:
        outcome = WalkOutcome(
            offer_gid="o1",
            candidates=(
                _candidate(gid="b1", name="Fixture Business A"),
                _candidate(gid="b2", name="Fixture Business B"),
            ),
            failure=None,
        )
        supply = build_identity_supply(outcome, observed_at=OBSERVED_AT)

        assert supply.asana_business.value is None
        assert supply.business_display_name.value is None
        assert supply.asana_business.match_count == 2
        assert supply.asana_business.set_disclosed is True
        # The SET stays reachable: the fold grades it, the supply does not pick.
        assert [c.gid for c in supply.candidates] == ["b1", "b2"]

    def test_the_supply_does_not_pick_the_first_candidate(self) -> None:
        """The exact failure mode this rule exists to forbid."""
        outcome = WalkOutcome(
            offer_gid="o1",
            candidates=(_candidate(gid="b1"), _candidate(gid="b2")),
            failure=None,
        )
        supply = build_identity_supply(outcome, observed_at=OBSERVED_AT)
        assert supply.asana_business.value != "b1"
        assert supply.asana_business.value != "b2"

    def test_zero_candidates_is_undecidable(self) -> None:
        supply = build_identity_supply(
            WalkOutcome(offer_gid="o1", candidates=(), failure=None),
            observed_at=OBSERVED_AT,
        )
        assert supply.asana_business.absent_reason is AbsentReason.UNDECIDABLE
        assert supply.asana_business.match_count == 0


# =============================================================================
# W-7 STRICT / K-A -- a display string decides STATE, never IDENTITY
# =============================================================================


class TestDisplayNameDiscipline:
    @pytest.mark.parametrize(
        "raw_name",
        [
            "  Fixture Business A  ",
            "FIXTURE BUSINESS A",
            "fixture business a",
            # U+00A0 written as an escape so the next reader can SEE it: a
            # display string that NFKC would fold to plain spaces must not be
            # folded here.
            "Fixture\u00a0Business\u00a0A",
            "Fixture  Business   A",
            "Fixture Business A — Offers",
        ],
    )
    def test_the_name_is_carried_byte_verbatim(self, raw_name: str) -> None:
        """No strip, no case-fold, no NFKC, no whitespace collapse (K-A)."""
        supply = build_identity_supply(
            WalkOutcome(offer_gid="o1", candidates=(_candidate(name=raw_name),), failure=None),
            observed_at=OBSERVED_AT,
        )
        assert supply.business_display_name.value == raw_name

    def test_the_name_never_becomes_the_identity(self) -> None:
        supply = build_identity_supply(
            WalkOutcome(
                offer_gid="o1",
                candidates=(_candidate(gid="b1", name="Fixture Business A"),),
                failure=None,
            ),
            observed_at=OBSERVED_AT,
        )
        assert supply.asana_business.value == "b1"
        assert supply.asana_business.value != supply.business_display_name.value

    def test_an_empty_name_is_ancestor_field_absent_never_parent_absent(self) -> None:
        """These two must not collapse (ADR §3.7 Ground 1)."""
        for empty in (None, ""):
            supply = build_identity_supply(
                WalkOutcome(offer_gid="o1", candidates=(_candidate(name=empty),), failure=None),
                observed_at=OBSERVED_AT,
            )
            assert supply.business_display_name.absent_reason is AbsentReason.ANCESTOR_FIELD_ABSENT
            # The ancestor WAS reached, so the identity is still published.
            assert supply.asana_business.value == "b1"


# =============================================================================
# Schema pins -- the emitter, asserted against the ADR
# =============================================================================


class TestSchemaPins:
    def test_supplier_is_the_closed_set_of_six(self) -> None:
        assert {s.value for s in Supplier} == {
            "producer_held",
            "id_walk",
            "resolution_context",
            "resolve_on_phone",
            "parent_ref",
            "cascade",
        }

    def test_no_supplier_member_is_name_keyed(self) -> None:
        assert not any("name" in s.value for s in Supplier)

    def test_absent_reasons_pin_the_ratified_set_plus_exactly_one_proposal(self) -> None:
        emitted = {r.value for r in AbsentReason}
        assert emitted >= RATIFIED_ABSENT_REASONS, "a ratified member went missing"
        proposed = emitted - RATIFIED_ABSENT_REASONS
        assert proposed == {"tier4_needs_healing"}, (
            "the ID-WALK absence set widened beyond the single declared proposal"
        )

    def test_the_tier4_reason_has_an_in_set_fallback(self) -> None:
        """One line flips it back inside the ratified set if wave 2 declines it."""
        assert AbsentReason.UNDECIDABLE.value in RATIFIED_ABSENT_REASONS

    def test_cascade_is_forbidden_as_a_supplier(self) -> None:
        with pytest.raises(ValueError, match="FORBIDDEN as a supplier"):
            Evidence(
                family="asana_business",
                value="b1",
                absent_reason=None,
                supplier=Supplier.CASCADE,
                supplier_path=None,
                detection_tier=1,
                needs_healing=False,
                grain=Grain.G_1,
                population=Population.FLEET,
                system_of_record=SystemOfRecord.ASANA,
                match_count=1,
                total_match_count=1,
                set_disclosed=True,
                refuted=False,
                observed_at=OBSERVED_AT,
                basis_version=1,
            )

    @pytest.mark.parametrize(
        ("value", "reason"),
        [("b1", AbsentReason.UNDECIDABLE), (None, None)],
    )
    def test_value_and_absent_reason_are_XOR(
        self, value: str | None, reason: AbsentReason | None
    ) -> None:
        with pytest.raises(ValueError, match="E-0 violated"):
            Evidence(
                family="asana_business",
                value=value,
                absent_reason=reason,
                supplier=Supplier.ID_WALK,
                supplier_path=None,
                detection_tier=1,
                needs_healing=False,
                grain=Grain.G_1,
                population=Population.FLEET,
                system_of_record=SystemOfRecord.ASANA,
                match_count=1,
                total_match_count=1,
                set_disclosed=True,
                refuted=False,
                observed_at=OBSERVED_AT,
                basis_version=1,
            )

    def test_observed_at_must_be_offset_aware(self) -> None:
        with pytest.raises(ValueError, match="offset-aware UTC"):
            build_identity_supply(
                WalkOutcome(offer_gid="o1", candidates=(_candidate(),), failure=None),
                observed_at=datetime(2026, 9, 5, 12, 0, 0),  # noqa: DTZ001
            )

    def test_this_seat_does_not_mint_fold_owned_fields(self) -> None:
        """One writer per fact: the appender must not carry the fold's columns."""
        fold_owned = {
            "confidence",
            "refuted_basis",
            "refuted_by",
            "shared",
            "shared_count",
            "corroborated_by",
            "lineage",
            "fold_version",
            "fold_at",
        }
        assert fold_owned.isdisjoint(set(Evidence.__dataclass_fields__))

    def test_the_walk_does_not_filter_so_pre_equals_post(self) -> None:
        """`total_match_count` is never erased: the id walk filters nothing."""
        for outcome in (
            WalkOutcome(offer_gid="o1", candidates=(_candidate(),), failure=None),
            WalkOutcome(
                offer_gid="o1",
                candidates=(_candidate(gid="b1"), _candidate(gid="b2")),
                failure=None,
            ),
            WalkOutcome(offer_gid="o1", candidates=(), failure=AbsentReason.WALK_DEPTH_EXCEEDED),
        ):
            supply = build_identity_supply(outcome, observed_at=OBSERVED_AT)
            for ev in supply.families().values():
                assert ev.total_match_count == ev.match_count

    def test_refuted_is_always_explicitly_false(self) -> None:
        supply = build_identity_supply(
            WalkOutcome(offer_gid="o1", candidates=(_candidate(),), failure=None),
            observed_at=OBSERVED_AT,
        )
        for ev in supply.families().values():
            assert ev.refuted is False

    def test_supplier_is_present_even_when_the_value_is_null(self) -> None:
        supply = build_identity_supply(
            WalkOutcome(offer_gid="o1", candidates=(), failure=AbsentReason.WALK_CYCLE),
            observed_at=OBSERVED_AT,
        )
        for family in ("asana_business", "business_display_name"):
            ev = supply.families()[family]
            assert ev.value is None
            assert ev.supplier is Supplier.ID_WALK

    def test_the_id_walk_families_declare_grain_G1(self) -> None:
        supply = build_identity_supply(
            WalkOutcome(offer_gid="o1", candidates=(_candidate(),), failure=None),
            observed_at=OBSERVED_AT,
        )
        assert supply.asana_business.grain is Grain.G_1
        assert supply.business_display_name.grain is Grain.G_1
        assert supply.offer.grain is Grain.G_3

    def test_a_missing_offer_gid_is_typed_never_silent(self) -> None:
        supply = build_identity_supply(
            WalkOutcome(offer_gid=None, candidates=(), failure=None),
            observed_at=OBSERVED_AT,
        )
        for ev in supply.families().values():
            assert ev.value is None
            assert ev.absent_reason is AbsentReason.PRODUCER_INPUT_ABSENT

    def test_the_observation_clock_is_the_walks_own_and_is_never_substituted(
        self,
    ) -> None:
        instant = datetime.now(UTC) - timedelta(days=3)
        supply = build_identity_supply(
            WalkOutcome(offer_gid="o1", candidates=(_candidate(),), failure=None),
            observed_at=instant,
        )
        for ev in supply.families().values():
            assert ev.observed_at == instant


# =============================================================================
# E4 -- the cascade is never consulted
# =============================================================================


class TestCascadeIsNeverConsulted:
    def test_the_supply_module_does_not_reference_the_cascade_view(self) -> None:
        """AST, not grep: docstrings and comments MAY name the cascade (they explain
        why it is refused); no executable statement may reach it."""
        from autom8_asana.models.business import identity_supply

        tree = ast.parse(inspect.getsource(identity_supply))
        referenced: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                referenced.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                referenced.add(node.module or "")
                referenced.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Attribute):
                referenced.add(node.attr)
            elif isinstance(node, ast.Name):
                referenced.add(node.id)

        # `Supplier.CASCADE` is EXCLUDED by name: the module references that enum
        # member only to REFUSE it in `Evidence.__post_init__`. Naming the forbidden
        # supplier in order to reject it is the opposite of consulting it.
        offenders = {name for name in referenced if "cascade" in name.lower() and name != "CASCADE"}
        assert offenders == set(), f"the supply reaches the cascade via {offenders}"

    def test_no_disposition_ever_emits_the_cascade_supplier(self) -> None:
        """Across every disposition the assembler can take, `cascade` is never the
        supplier of anything."""
        outcomes = [
            WalkOutcome(offer_gid=None, candidates=(), failure=None),
            WalkOutcome(offer_gid="o1", candidates=(), failure=None),
            WalkOutcome(offer_gid="o1", candidates=(), failure=AbsentReason.WALK_CYCLE),
            WalkOutcome(offer_gid="o1", candidates=(_candidate(),), failure=None),
            WalkOutcome(
                offer_gid="o1",
                candidates=(_candidate(detection_tier=4, needs_healing=True),),
                failure=None,
            ),
            WalkOutcome(
                offer_gid="o1",
                candidates=(_candidate(gid="b1"), _candidate(gid="b2")),
                failure=None,
            ),
        ]
        for outcome in outcomes:
            supply = build_identity_supply(outcome, observed_at=OBSERVED_AT)
            for ev in supply.families().values():
                assert ev.supplier is not Supplier.CASCADE

    def test_the_teeth_of_the_ast_probe(self) -> None:
        """The AST probe must actually bite: a module that DOES import the cascade
        view is caught by the same predicate."""
        tree = ast.parse("from autom8_asana.dataframes.views.cascade_view import CascadeView\n")
        referenced: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                referenced.add(node.module or "")
                referenced.update(alias.name for alias in node.names)
        assert {name for name in referenced if "cascade" in name.lower()}

    async def test_the_walk_path_makes_no_cascade_call(self) -> None:
        """A live negative control: the read-set is `get_async` + `subtasks_async` only."""
        client = _clean_tier1_client()
        await supply_identity_evidence_async(client, "o1", observed_at=OBSERVED_AT)

        called = {
            name.split(".")[0]
            for name, _args, _kwargs in client.mock_calls
            if name and not name.startswith("_")
        }
        assert called <= {"tasks"}, f"unexpected client surface touched: {called}"


# =============================================================================
# NO PRODUCTION WRITE
# =============================================================================


class TestSupplyIsReadOnly:
    async def test_no_write_method_is_ever_called(self) -> None:
        client = _clean_tier1_client()
        await supply_identity_evidence_async(client, "o1", observed_at=OBSERVED_AT)

        write_tokens = ("create", "update", "delete", "post", "put", "patch", "set_")
        offenders = [
            name
            for name, _args, _kwargs in client.mock_calls
            if any(token in name.lower() for token in write_tokens)
        ]
        assert offenders == []

    async def test_the_supply_returns_a_frozen_result(self) -> None:
        supply = await supply_identity_evidence_async(
            _clean_tier1_client(), "o1", observed_at=OBSERVED_AT
        )
        assert isinstance(supply, IdentitySupply)
        with pytest.raises((AttributeError, TypeError)):
            supply.asana_business.value = "tampered"  # type: ignore[misc]
