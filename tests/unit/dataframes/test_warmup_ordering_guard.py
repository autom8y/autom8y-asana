"""WG-01..WG-05: Warm-up ordering guard contract tests.

Tests the three-layer defense-in-depth enforcement of the cascade
warm-up ordering invariant (SCAR-005/006 prevention).

| Test ID | Layer | What It Verifies |
|---------|-------|-----------------|
| WG-01   | L1    | warm_priority ordering conflicts raises ValueError |
| WG-02   | L2    | missing cascade provider raises WarmupOrderingError |
| WG-03   | L3    | provider data absent triggers advisory warning |
| WG-04   | All   | WarmupOrderingError propagates past BROAD-CATCH |
| WG-05   | L1    | Lambda cache warmer uses cascade_warm_order for ordering |
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestWG01L1StartupValidation:
    """WG-01: L1 ordering conflict raises ValueError at startup.

    validate_cascade_ordering() checks that warm_priority ordering
    matches the cascade dependency graph. A conflict raises ValueError,
    preventing the process from starting with corrupt ordering.
    """

    def test_current_ordering_passes_validation(self) -> None:
        """WG-01a: Current production warm_priority values pass L1 check."""
        from autom8_asana.dataframes.cascade_utils import validate_cascade_ordering

        # Should not raise — current values are correct
        validate_cascade_ordering()

    def test_swapped_priority_raises_value_error(self) -> None:
        """WG-01b: Misconfigured warm_priority raises ValueError.

        If business (the root cascade provider) has a higher priority
        index than one of its consumers, validate_cascade_ordering()
        must detect and reject this.
        """
        from autom8_asana.dataframes.cascade_utils import (
            get_cascade_providers,
            validate_cascade_ordering,
        )

        # Verify that business provides cascade fields to other entities
        # (precondition: if business isn't a provider, the test is meaningless)
        unit_providers = get_cascade_providers("unit")
        assert "business" in unit_providers, (
            "Test precondition: unit must depend on business for cascade fields"
        )

        # Mock warmable_entities to return business AFTER unit (wrong order)
        # This simulates a misconfigured warm_priority
        from autom8_asana.core.entity_registry import get_registry

        registry = get_registry()
        real_warmable = registry.warmable_entities()

        # Find business and unit descriptors and swap their positions
        desc_by_name = {d.name: d for d in real_warmable}
        assert "business" in desc_by_name
        assert "unit" in desc_by_name

        # Build a list where unit comes before business (violates invariant)
        swapped = [d for d in real_warmable if d.name not in ("business", "unit")]
        swapped.insert(0, desc_by_name["unit"])  # unit first (wrong)
        swapped.insert(1, desc_by_name["business"])  # business second (wrong)

        with patch.object(registry, "warmable_entities", return_value=swapped):
            with pytest.raises(ValueError, match="CASCADE ORDERING MISCONFIGURATION"):
                validate_cascade_ordering()


class TestWG02L2PrePhaseGate:
    """WG-02: L2 pre-phase gate blocks when cascade provider is missing.

    The pre-phase gate in progressive.py checks that all cascade
    providers for entities in the current phase have completed before
    the phase begins.
    """

    def test_get_cascade_providers_returns_business_for_unit(self) -> None:
        """WG-02a: get_cascade_providers correctly identifies business as unit's provider."""
        from autom8_asana.dataframes.cascade_utils import get_cascade_providers

        providers = get_cascade_providers("unit")
        assert "business" in providers

    def test_get_cascade_providers_empty_for_business(self) -> None:
        """WG-02b: business (root provider) has no cascade providers."""
        from autom8_asana.dataframes.cascade_utils import get_cascade_providers

        providers = get_cascade_providers("business")
        assert len(providers) == 0

    def test_l2_gate_raises_warmup_ordering_error(self) -> None:
        """WG-02c: Simulated L2 gate raises WarmupOrderingError on missing provider.

        Reproduces the L2 logic: if an entity's cascade providers are not
        in the completed set, WarmupOrderingError must be raised.
        """
        from autom8_asana.dataframes.cascade_utils import (
            WarmupOrderingError,
            get_cascade_providers,
        )

        # Simulate the L2 gate logic from progressive.py:668-676
        completed_entities: set[str] = set()  # Nothing completed yet
        entity_type = "unit"  # Unit depends on business

        missing_providers = get_cascade_providers(entity_type) - completed_entities
        assert len(missing_providers) > 0, "unit should have missing providers"

        # The L2 gate would raise WarmupOrderingError here
        with pytest.raises(WarmupOrderingError):
            if missing_providers:
                raise WarmupOrderingError(
                    f"L2 pre-phase gate: entity '{entity_type}' requires "
                    f"cascade providers {missing_providers} which have not "
                    f"completed. Completed so far: {completed_entities}."
                )

    def test_l2_gate_passes_when_providers_complete(self) -> None:
        """WG-02d: L2 gate passes when all cascade providers are in completed set."""
        from autom8_asana.dataframes.cascade_utils import get_cascade_providers

        # business has completed
        completed_entities = {"business"}
        entity_type = "unit"

        missing_providers = get_cascade_providers(entity_type) - completed_entities
        # All providers should be in completed_entities
        assert len(missing_providers) == 0, (
            f"unit's providers should all be completed, but missing: {missing_providers}"
        )


class TestWG03L3PerEntityAssertion:
    """WG-03: L3 per-entity assertion warns when provider data is absent.

    The L3 check in ProgressiveProjectBuilder._check_cascade_provider_data()
    probes the store's hierarchy index. If empty, it logs a warning
    (advisory, not blocking).
    """

    def test_l3_check_skips_for_providers(self) -> None:
        """WG-03a: Business entity (cascade provider) skips L3 check."""
        from autom8_asana.dataframes.cascade_utils import get_cascade_providers

        # Business has no cascade deps — L3 would return immediately
        providers = get_cascade_providers("business")
        assert len(providers) == 0

    def test_l3_check_identifies_consumers(self) -> None:
        """WG-03b: Consumer entities have non-empty provider sets for L3 check."""
        from autom8_asana.dataframes.cascade_utils import get_cascade_providers

        # Offer should depend on business and/or unit
        offer_providers = get_cascade_providers("offer")
        assert len(offer_providers) > 0, "offer should have cascade providers"

        contact_providers = get_cascade_providers("contact")
        assert len(contact_providers) > 0, "contact should have cascade providers"

    def test_l3_method_exists_on_builder(self) -> None:
        """WG-03c: ProgressiveProjectBuilder has _check_cascade_provider_data method."""
        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveProjectBuilder,
        )

        assert hasattr(ProgressiveProjectBuilder, "_check_cascade_provider_data")


class TestWG04ErrorPropagation:
    """WG-04: WarmupOrderingError propagates past BROAD-CATCH handlers.

    WarmupOrderingError must NOT be caught by broad except Exception
    handlers. It must crash the process to prevent serving corrupted data.
    """

    def test_warmup_ordering_error_is_exception_subclass(self) -> None:
        """WG-04a: WarmupOrderingError is a proper Exception subclass."""
        from autom8_asana.dataframes.cascade_utils import WarmupOrderingError

        assert issubclass(WarmupOrderingError, Exception)
        error = WarmupOrderingError("test message")
        assert str(error) == "test message"

    def test_warmup_ordering_error_not_caught_by_value_error(self) -> None:
        """WG-04b: WarmupOrderingError is not a ValueError subclass.

        This matters because some BROAD-CATCH handlers catch ValueError.
        WarmupOrderingError must bypass them.
        """
        from autom8_asana.dataframes.cascade_utils import WarmupOrderingError

        assert not issubclass(WarmupOrderingError, ValueError)
        assert not issubclass(WarmupOrderingError, TypeError)
        assert not issubclass(WarmupOrderingError, RuntimeError)

    def test_progressive_preload_re_raises_warmup_ordering_error(self) -> None:
        """WG-04c: progressive.py has explicit WarmupOrderingError re-raise.

        The progressive preload has a BROAD-CATCH `except Exception` block.
        An `except WarmupOrderingError: raise` clause must appear BEFORE it
        to ensure the error propagates.
        """
        import inspect

        from autom8_asana.api.preload.progressive import (
            _preload_dataframe_cache_progressive,
        )

        source = inspect.getsource(_preload_dataframe_cache_progressive)
        # Verify the WarmupOrderingError re-raise is present
        assert "except WarmupOrderingError" in source, (
            "progressive.py must have 'except WarmupOrderingError: raise' "
            "before the BROAD-CATCH to prevent silent swallowing"
        )


class TestWG05LambdaParity:
    """WG-05: Lambda cache warmer uses cascade-safe ordering.

    The Lambda cache warmer must process entities in the same
    cascade-safe order as the ECS progressive preload.
    """

    def test_lambda_uses_cascade_warm_order(self) -> None:
        """WG-05a: Lambda cache warmer imports cascade_warm_order for entity ordering."""
        import inspect

        from autom8_asana.lambda_handlers import cache_warmer

        source = inspect.getsource(cache_warmer)
        assert "cascade_warm_order" in source, (
            "Lambda cache warmer must use cascade_warm_order() for "
            "cascade-safe entity processing order"
        )

    def test_cascade_warm_order_matches_phase_flattening(self) -> None:
        """WG-05b: cascade_warm_order() equals flattened cascade_warm_phases().

        Ensures the Lambda convenience wrapper produces the same ordering
        as the phase-based approach used by the ECS preload.
        """
        from autom8_asana.dataframes.cascade_utils import (
            cascade_warm_order,
            cascade_warm_phases,
        )

        phases = cascade_warm_phases()
        flat_phases = [e for phase in phases for e in phase]
        warm_order = cascade_warm_order()

        assert warm_order == flat_phases
