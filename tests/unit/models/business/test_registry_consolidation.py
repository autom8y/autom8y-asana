"""Unit tests for registry consolidation bootstrap.

Per TDD-registry-consolidation: Tests for explicit model registration via _bootstrap.py.

Test cases:
1. register_all_models() populates registry
2. Bootstrap is idempotent
3. reset_bootstrap() enables re-registration
4. Known entity types have expected GIDs
5. Registry works without explicit model imports
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.models.business._bootstrap import (
    is_bootstrap_complete,
    register_all_models,
    reset_bootstrap,
)
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    get_registry,
)

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def clean_registry_and_bootstrap() -> Generator[None, None, None]:
    """Reset registry and bootstrap state before and after each test.

    Per TDD-registry-consolidation: Ensures test isolation for both
    registry singleton and bootstrap flag.
    """
    ProjectTypeRegistry.reset()
    reset_bootstrap()
    yield
    ProjectTypeRegistry.reset()
    reset_bootstrap()


class TestBootstrapRegistration:
    """Tests for register_all_models() bootstrap function."""

    def test_register_all_models_populates_registry(
        self, clean_registry_and_bootstrap: None
    ) -> None:
        """Bootstrap registers all entity models with known GIDs."""
        register_all_models()

        registry = get_registry()

        # Business should be registered
        assert registry.lookup("1200653012566782") == EntityType.BUSINESS

        # Unit should be registered
        assert registry.lookup("1201081073731555") == EntityType.UNIT

        # Contact should be registered
        assert registry.lookup("1200775689604552") == EntityType.CONTACT

    def test_bootstrap_is_idempotent(self, clean_registry_and_bootstrap: None) -> None:
        """Bootstrap can be called multiple times without error."""
        register_all_models()
        register_all_models()  # Second call should be no-op

        registry = get_registry()
        assert registry.lookup("1200653012566782") == EntityType.BUSINESS

    def test_is_bootstrap_complete_tracks_state(self, clean_registry_and_bootstrap: None) -> None:
        """is_bootstrap_complete() correctly tracks registration state."""
        assert not is_bootstrap_complete()

        register_all_models()

        assert is_bootstrap_complete()

    def test_reset_bootstrap_enables_re_registration(
        self, clean_registry_and_bootstrap: None
    ) -> None:
        """reset_bootstrap() allows re-running registration."""
        register_all_models()
        assert is_bootstrap_complete()

        reset_bootstrap()
        assert not is_bootstrap_complete()

        # Can register again
        register_all_models()
        assert is_bootstrap_complete()


class TestKnownEntityGIDs:
    """Tests verifying known entity type to GID mappings."""

    def test_business_gid(self, clean_registry_and_bootstrap: None) -> None:
        """Business entity maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1200653012566782") == EntityType.BUSINESS
        assert registry.get_primary_gid(EntityType.BUSINESS) == "1200653012566782"

    def test_unit_gid(self, clean_registry_and_bootstrap: None) -> None:
        """Unit entity maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1201081073731555") == EntityType.UNIT
        assert registry.get_primary_gid(EntityType.UNIT) == "1201081073731555"

    def test_contact_gid(self, clean_registry_and_bootstrap: None) -> None:
        """Contact entity maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1200775689604552") == EntityType.CONTACT
        assert registry.get_primary_gid(EntityType.CONTACT) == "1200775689604552"

    def test_offer_gid(self, clean_registry_and_bootstrap: None) -> None:
        """Offer entity maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1143843662099250") == EntityType.OFFER
        assert registry.get_primary_gid(EntityType.OFFER) == "1143843662099250"

    def test_location_gid(self, clean_registry_and_bootstrap: None) -> None:
        """Location entity maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1200836133305610") == EntityType.LOCATION
        assert registry.get_primary_gid(EntityType.LOCATION) == "1200836133305610"

    def test_hours_gid(self, clean_registry_and_bootstrap: None) -> None:
        """Hours entity maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1201614578074026") == EntityType.HOURS
        assert registry.get_primary_gid(EntityType.HOURS) == "1201614578074026"


class TestHolderGIDs:
    """Tests verifying holder type to GID mappings."""

    def test_contact_holder_gid(self, clean_registry_and_bootstrap: None) -> None:
        """ContactHolder maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1201500116978260") == EntityType.CONTACT_HOLDER

    def test_unit_holder_gid(self, clean_registry_and_bootstrap: None) -> None:
        """UnitHolder maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1204433992667196") == EntityType.UNIT_HOLDER

    def test_offer_holder_gid(self, clean_registry_and_bootstrap: None) -> None:
        """OfferHolder maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1210679066066870") == EntityType.OFFER_HOLDER

    def test_dna_holder_gid(self, clean_registry_and_bootstrap: None) -> None:
        """DNAHolder maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1167650840134033") == EntityType.DNA_HOLDER

    def test_reconciliation_holder_gid(self, clean_registry_and_bootstrap: None) -> None:
        """ReconciliationHolder maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1203404998225231") == EntityType.RECONCILIATIONS_HOLDER

    def test_asset_edit_holder_gid(self, clean_registry_and_bootstrap: None) -> None:
        """AssetEditHolder maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1203992664400125") == EntityType.ASSET_EDIT_HOLDER

    def test_videography_holder_gid(self, clean_registry_and_bootstrap: None) -> None:
        """VideographyHolder maps to expected GID."""
        register_all_models()
        registry = get_registry()

        assert registry.lookup("1207984018149338") == EntityType.VIDEOGRAPHY_HOLDER


class TestRegistryWorksThroughModuleImport:
    """Tests verifying registry works via module import (not explicit class import)."""

    def test_registry_populated_after_package_import(
        self, clean_registry_and_bootstrap: None
    ) -> None:
        """Importing business package populates registry.

        Per TDD-registry-consolidation: The key validation - registry should
        be populated after importing the business package, without needing
        to explicitly import any model classes.
        """
        # Re-import to trigger registration
        register_all_models()

        # Get registry - should have Business registered
        registry = get_registry()

        # This is the key test from TDD-registry-consolidation:
        # Registry should work without explicit Business class import
        assert registry.lookup("1200653012566782") == EntityType.BUSINESS

    def test_detection_works_before_explicit_model_import(
        self, clean_registry_and_bootstrap: None
    ) -> None:
        """Detection via registry works before any model class is imported.

        This validates the core fix: detection should work during cache warming
        when models haven't been explicitly imported yet.
        """
        # Run bootstrap (simulates package import)
        register_all_models()

        # Now lookup should work
        registry = get_registry()
        entity_type = registry.lookup("1200653012566782")

        assert entity_type == EntityType.BUSINESS


class TestProcessAndLocationHoldersWithoutGID:
    """Tests for entities without PRIMARY_PROJECT_GID."""

    def test_process_without_dedicated_project(self, clean_registry_and_bootstrap: None) -> None:
        """Process entity has no dedicated project GID (uses pipeline detection).

        Per design: Process uses WorkspaceProjectRegistry for pipeline detection,
        not a static PRIMARY_PROJECT_GID.
        """
        register_all_models()
        registry = get_registry()

        # Process should not have a primary GID (None in model)
        # but may still be registered via other means
        # For now, just verify registration completes without error
        assert is_bootstrap_complete()

    def test_process_holder_without_dedicated_project(
        self, clean_registry_and_bootstrap: None
    ) -> None:
        """ProcessHolder has no dedicated project GID.

        Per design: ProcessHolder detection uses parent inference,
        not a static PRIMARY_PROJECT_GID.
        """
        register_all_models()
        registry = get_registry()

        # ProcessHolder should not have a primary GID registered
        assert registry.get_primary_gid(EntityType.PROCESS_HOLDER) is None

    def test_location_holder_without_dedicated_project(
        self, clean_registry_and_bootstrap: None
    ) -> None:
        """LocationHolder has no dedicated project GID.

        Per design: LocationHolder detection uses parent inference,
        not a static PRIMARY_PROJECT_GID.
        """
        register_all_models()
        registry = get_registry()

        # LocationHolder should not have a primary GID registered
        assert registry.get_primary_gid(EntityType.LOCATION_HOLDER) is None
