"""Two-sided contract tests for the L2 gate vs frame-less cascade providers.

Regression suite for the #192 wedge: PR #192 flagged the frame-less
``unit_holder`` HOLDER entity as a cascade provider (OFFER_SCHEMA 1.6.0,
scheduling-posture columns). The warm-phase planner
(``cascade_warm_phases``) schedules only frame-warmable entities, so
``unit_holder`` appears in NO phase — but the L2 pre-phase gate demanded
the UNFILTERED provider set, making ``offer``'s preload a structurally
unsatisfiable demand (``WarmupOrderingError`` on every service start,
observed live 2026-07-02T14:48:10Z).

The cure re-unifies planner and gate on one predicate
(``get_frame_warm_providers`` — the planner's own
``warmable_entities()`` membership), enforced by
``assert_l2_pre_phase_gate``. These tests are two-sided:

| Side  | What it proves |
|-------|----------------|
| RED   | Gate still fires for a genuinely missing FRAME-WARMABLE provider |
| GREEN | A frame-LESS provider does not wedge its consumer's phase |
| PROP  | Planner/gate coherence is a structural property, not an instance |

WS-B TRANSITION (DIAG-ws-b-offer-frame-collapse-2026-08-05)
-----------------------------------------------------------
``unit_holder`` was this suite's LIVE frame-less provider. WS-B gives it a
DataFrame schema of its own (nine ``cf:`` scheduling-posture columns) and marks
it ``warmable=True``, because the ancestor walk that was supposed to deliver
those values to the offer frame terminates at depth 1 and never reaches it.

The original ``TestLiveRegistryDefectShape`` docstring anticipated exactly this:

    "If these preconditions drift (e.g., unit_holder gains a frame or stops
     providing), the two-sided tests below lose their meaning and must be
     revisited."

This is that revisit. Two consequences, both handled deliberately:

1. The preconditions below now pin the NEW registry state (unit_holder IS
   frame-warmable) rather than the old one.
2. **There is no longer ANY frame-less cascade provider in the live registry**
   (providers are business, unit, unit_holder — all warmable). The GREEN side
   would therefore go VACUOUS if it kept asserting against live state. It is
   converted to a SYNTHETIC fixture that reconstructs the frame-less condition
   by patching ``warmable_entities``, so the #192 wedge class stays guarded
   after its live instance disappeared. A guard that silently stops guarding is
   worse than no guard.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from autom8_asana.dataframes.cascade_utils import (
    WarmupOrderingError,
    assert_l2_pre_phase_gate,
    cascade_warm_phases,
    get_cascade_providers,
    get_frame_warm_providers,
)

# ---------------------------------------------------------------------------
# Live-registry preconditions (pin the defect shape this suite guards)
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestLiveRegistryDefectShape:
    """Pin the POST-WS-B registry state.

    unit_holder remains offer's cascade provider, but it is now frame-warmable
    (it owns UNIT_HOLDER_SCHEMA). If these preconditions drift again, the
    two-sided tests below must be revisited a second time.
    """

    def test_unit_holder_is_a_cascade_provider_for_offer(self) -> None:
        """offer's unfiltered provider set still includes unit_holder.

        WS-B did NOT remove offer's cascade declaration — the offer schema
        keeps its nine cascade: posture columns (they remain the correct
        declaration and the target of the CARD WS-B/1 ancestor-walk cure).
        """
        assert "unit_holder" in get_cascade_providers("offer")

    def test_unit_holder_is_now_frame_warmable(self) -> None:
        """WS-B: unit_holder owns a DataFrame schema and is warmed.

        Inverts the pre-WS-B precondition (``warmable is False`` /
        ``schema_module_path is None``). The nine scheduling-posture columns
        are read cf: off UnitHolder's own manifest, so this frame is immune to
        the depth-1 ancestor-walk defect that darkened them on the offer frame.
        """
        from autom8_asana.core.entity_registry import get_registry

        desc = get_registry().get("unit_holder")
        assert desc is not None
        assert desc.warmable is True
        assert desc.schema_module_path == (
            "autom8_asana.dataframes.schemas.unit_holder.UNIT_HOLDER_SCHEMA"
        )

    def test_unit_holder_now_appears_in_a_warm_phase(self) -> None:
        """The planner schedules unit_holder now that it has a frame."""
        scheduled = {e for phase in cascade_warm_phases() for e in phase}
        assert "unit_holder" in scheduled

    def test_unit_holder_warms_before_offer(self) -> None:
        """L1 ordering: a frame-warm provider must precede its consumer.

        Load-bearing regression guard for the WS-B priority correction. Marking
        unit_holder warmable moves it INTO offer's frame-warm provider set, so
        validate_cascade_ordering() (fail-fast at api/lifespan.py:326) requires
        unit_holder earlier in the flat warm order. At warm_priority=7 this
        raised "offer (priority_idx=2) warms BEFORE its cascade provider
        unit_holder (priority_idx=6)" — an ECS start refusal.
        """
        from autom8_asana.core.entity_registry import get_registry

        order = [d.name for d in get_registry().warmable_entities()]
        assert order.index("unit_holder") < order.index("offer")

    def test_no_frameless_cascade_providers_remain(self) -> None:
        """Pin the fact that forces the GREEN side to be synthetic.

        Every cascade provider in the live registry is now frame-warmable, so
        the #192 wedge condition has NO live instance. If a frame-less provider
        is ever reintroduced, this test fails and the GREEN fixture below
        should be re-grounded on the real entity instead.
        """
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()
        scheduled = {e for phase in cascade_warm_phases() for e in phase}
        providers: set[str] = set()
        for entity_type in scheduled:
            providers |= get_cascade_providers(entity_type)

        frameless = {p for p in providers if (d := registry.get(p)) is not None and not d.warmable}
        assert not frameless, (
            "A frame-less cascade provider reappeared: "
            f"{sorted(frameless)}. The GREEN side of this suite is a synthetic "
            "fixture precisely because none existed at WS-B; re-ground it."
        )


# ---------------------------------------------------------------------------
# RED tooth: gate keeps its teeth for frame-WARMABLE providers
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestRedToothFrameWarmableProviderMissing:
    """The gate must still fail closed when a frame-warmable provider
    is genuinely missing (SCAR-005/006 — null cascade at extraction)."""

    def test_gate_raises_when_business_not_completed(self) -> None:
        """unit requires frame-warmable business; empty completed set -> RED."""
        # Precondition: business is a frame-warm provider of unit
        assert "business" in get_frame_warm_providers("unit")

        with pytest.raises(WarmupOrderingError, match="business"):
            assert_l2_pre_phase_gate(
                phase_idx=1,
                phase_entity_types=["unit"],
                completed_entities=set(),
            )

    def test_gate_raises_for_offer_when_frame_warm_providers_missing(self) -> None:
        """offer still demands its frame-warmable providers (gate NOT weakened)."""
        frame_warm = get_frame_warm_providers("offer")
        # Precondition: the fix must not have emptied offer's demand set
        assert "business" in frame_warm
        assert "unit" in frame_warm

        with pytest.raises(WarmupOrderingError, match="L2 pre-phase gate"):
            assert_l2_pre_phase_gate(
                phase_idx=2,
                phase_entity_types=["offer"],
                completed_entities={"business"},  # unit still missing
            )

    def test_gate_error_message_carries_diagnostics(self) -> None:
        """Error names the entity, phase, missing providers, completed set."""
        with pytest.raises(WarmupOrderingError) as exc_info:
            assert_l2_pre_phase_gate(
                phase_idx=7,
                phase_entity_types=["unit"],
                completed_entities={"asset_edit_holder"},
            )
        msg = str(exc_info.value)
        assert "'unit'" in msg
        assert "phase 7" in msg
        assert "business" in msg
        assert "asset_edit_holder" in msg


# ---------------------------------------------------------------------------
# GREEN side: frame-less providers no longer wedge the preload
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestGreenFramelessProviderSatisfied:
    """A frame-LESS provider must not wedge its consumer's phase.

    SYNTHETIC fixture (WS-B). unit_holder was the live instance of this
    condition until WS-B gave it a frame; no frame-less provider remains
    (pinned by ``test_no_frameless_cascade_providers_remain``). Rather than
    delete the guard and let the #192 class go unwatched, the historical live
    state is RECONSTRUCTED by patching ``warmable_entities`` to omit
    unit_holder — which is exactly what ``warmable=False`` did to the two
    predicates under test (``get_frame_warm_providers`` and the planner).
    """

    @staticmethod
    def _registry_without_unit_holder() -> tuple[object, list[object]]:
        """Live registry + its warmable list with unit_holder removed.

        Reconstructs the pre-WS-B frame-less condition for unit_holder.
        """
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()
        warmable_sans_uh = [d for d in registry.warmable_entities() if d.name != "unit_holder"]
        return registry, warmable_sans_uh

    def test_frame_warm_providers_excludes_a_frameless_provider(self) -> None:
        """The gate's demand set omits a frame-less provider, while the
        unfiltered set (L3's view) still carries it."""
        registry, warmable_sans_uh = self._registry_without_unit_holder()

        with patch.object(registry, "warmable_entities", return_value=warmable_sans_uh):
            frame_warm = get_frame_warm_providers("offer")
            assert "unit_holder" not in frame_warm
            # The gate NARROWED the set; it did not empty it (teeth preserved)
            assert "business" in frame_warm
            assert "unit" in frame_warm
        # ... while the unfiltered set (L3's view) still carries it
        assert "unit_holder" in get_cascade_providers("offer")

    def test_offer_phase_passes_without_frameless_provider_completion(self) -> None:
        """#192 replay: offer's gate passes once the phases BEFORE offer's
        phase have completed — the frame-less provider never completes."""
        registry, warmable_sans_uh = self._registry_without_unit_holder()

        with patch.object(registry, "warmable_entities", return_value=warmable_sans_uh):
            phases = cascade_warm_phases()
            offer_phase_idx = next(i for i, p in enumerate(phases) if "offer" in p)

            completed: set[str] = set()
            for phase in phases[:offer_phase_idx]:
                completed.update(phase)
            assert "unit_holder" not in completed  # never frame-warms

            # Must NOT raise (was a guaranteed WarmupOrderingError pre-#192-fix)
            assert_l2_pre_phase_gate(
                phase_idx=offer_phase_idx,
                phase_entity_types=["offer"],
                completed_entities=completed,
            )

    def test_frameless_fixture_would_wedge_under_the_unfiltered_set(self) -> None:
        """TEETH: prove the fixture reconstructs a condition that ACTUALLY
        wedges if the gate used the unfiltered provider set (the #192 bug).

        Without this, the two tests above could pass vacuously against a
        fixture that never reproduced the defect.
        """
        registry, warmable_sans_uh = self._registry_without_unit_holder()

        with patch.object(registry, "warmable_entities", return_value=warmable_sans_uh):
            phases = cascade_warm_phases()
            offer_phase_idx = next(i for i, p in enumerate(phases) if "offer" in p)
            completed: set[str] = set()
            for phase in phases[:offer_phase_idx]:
                completed.update(phase)

            # The #192 bug used get_cascade_providers (UNFILTERED) as the demand
            # set. Under the fixture that demand is unsatisfiable by construction.
            unfiltered_demand = get_cascade_providers("offer") - completed
            assert unfiltered_demand == {"unit_holder"}, (
                "Fixture failed to reconstruct the #192 wedge condition; the "
                "GREEN assertions above would be vacuous."
            )

    def test_full_planner_replay_satisfies_gate_at_every_phase(self) -> None:
        """Running the planner's phases in order satisfies the gate at
        EVERY phase for EVERY scheduled entity (no entity is wedged)."""
        completed: set[str] = set()
        for phase_idx, phase_types in enumerate(cascade_warm_phases()):
            assert_l2_pre_phase_gate(
                phase_idx=phase_idx,
                phase_entity_types=list(phase_types),
                completed_entities=completed,
            )
            completed.update(phase_types)


# ---------------------------------------------------------------------------
# Coherence property: the planner/gate invariant itself
# ---------------------------------------------------------------------------


@pytest.mark.scar
class TestPlannerGateCoherenceProperty:
    """Structural guard so this defect class cannot recur silently:
    every provider the gate could ever demand is schedulable by the
    planner; every other provider is EXPLICITLY classified frame-less."""

    def test_every_cascade_provider_is_schedulable_or_explicitly_frameless(
        self,
    ) -> None:
        """For every scheduled entity, each provider in its UNFILTERED
        provider set is either (i) schedulable by cascade_warm_phases()
        or (ii) a registered descriptor with warmable=False (frame-less,
        satisfied via ancestor hydration). Anything else is an
        unclassified provider — the #192 failure class."""
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()
        schedulable = {e for phase in cascade_warm_phases() for e in phase}

        unclassified: list[str] = []
        for entity_type in schedulable:
            for provider in get_cascade_providers(entity_type):
                if provider in schedulable:
                    continue  # (i) frame-warmable and scheduled
                desc = registry.get(provider)
                if desc is not None and desc.warmable is False:
                    continue  # (ii) explicitly frame-less
                unclassified.append(
                    f"{entity_type} <- {provider} "
                    f"(registered={desc is not None}, "
                    f"warmable={getattr(desc, 'warmable', None)})"
                )

        assert not unclassified, (
            "PLANNER/GATE INCOHERENCE: cascade providers that are neither "
            "schedulable by cascade_warm_phases() nor explicitly frame-less "
            "(warmable=False). The L2 gate would demand these forever "
            "(#192 wedge class):\n" + "\n".join(f"  - {u}" for u in unclassified)
        )

    def test_gate_demand_set_is_satisfiable_by_earlier_phases(self) -> None:
        """STRONGEST form: for every entity in phase i, the gate's demand
        set (get_frame_warm_providers) is a subset of the union of phases
        0..i-1. This directly implies the L2 gate can always be satisfied
        by executing the planner's phases in order."""
        phases = cascade_warm_phases()
        earlier: set[str] = set()
        violations: list[str] = []
        for phase_idx, phase_types in enumerate(phases):
            for entity_type in phase_types:
                unsatisfiable = get_frame_warm_providers(entity_type) - earlier
                if unsatisfiable:
                    violations.append(
                        f"phase {phase_idx} entity {entity_type}: "
                        f"demands {sorted(unsatisfiable)} not in any earlier phase"
                    )
            earlier.update(phase_types)

        assert not violations, (
            "L2 gate demand not satisfiable by planner phase order:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_frame_warm_providers_is_subset_of_cascade_providers(self) -> None:
        """The gate predicate only ever NARROWS the provider set — it can
        never demand a provider the dependency graph doesn't declare."""
        from autom8_asana.core.entity_registry import get_registry

        for desc in get_registry().warmable_entities():
            assert get_frame_warm_providers(desc.name) <= get_cascade_providers(desc.name)
