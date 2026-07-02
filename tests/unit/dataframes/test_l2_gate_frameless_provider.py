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
| GREEN | Offer's phase passes with the frame-less unit_holder provider |
| PROP  | Planner/gate coherence is a structural property, not an instance |
"""

from __future__ import annotations

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
    """Pin the registry state that produced the #192 wedge.

    If these preconditions drift (e.g., unit_holder gains a frame or
    stops providing), the two-sided tests below lose their meaning and
    must be revisited.
    """

    def test_unit_holder_is_a_cascade_provider_for_offer(self) -> None:
        """offer's unfiltered provider set includes frame-less unit_holder."""
        assert "unit_holder" in get_cascade_providers("offer")

    def test_unit_holder_is_not_frame_warmable(self) -> None:
        """unit_holder is a HOLDER: no warmable flag, no DataFrame schema."""
        from autom8_asana.core.entity_registry import get_registry

        desc = get_registry().get("unit_holder")
        assert desc is not None
        assert desc.warmable is False
        assert desc.schema_module_path is None

    def test_unit_holder_never_appears_in_any_warm_phase(self) -> None:
        """The planner cannot schedule unit_holder — it is frame-less."""
        scheduled = {e for phase in cascade_warm_phases() for e in phase}
        assert "unit_holder" not in scheduled


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
    """Offer's phase passes with unit_holder present-but-frame-less —
    the live registry state that wedged every service start."""

    def test_frame_warm_providers_excludes_unit_holder(self) -> None:
        """The gate's demand set for offer omits the frame-less provider."""
        frame_warm = get_frame_warm_providers("offer")
        assert "unit_holder" not in frame_warm
        # ... while the unfiltered set (L3's view) still carries it
        assert "unit_holder" in get_cascade_providers("offer")

    def test_offer_phase_passes_without_unit_holder_completion(self) -> None:
        """Live-registry replay: offer's gate passes once the phases
        BEFORE offer's phase have completed — unit_holder never does."""
        phases = cascade_warm_phases()
        offer_phase_idx = next(i for i, p in enumerate(phases) if "offer" in p)

        completed: set[str] = set()
        for phase in phases[:offer_phase_idx]:
            completed.update(phase)
        assert "unit_holder" not in completed  # never frame-warms

        # Must NOT raise (was a guaranteed WarmupOrderingError pre-fix)
        assert_l2_pre_phase_gate(
            phase_idx=offer_phase_idx,
            phase_entity_types=["offer"],
            completed_entities=completed,
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
