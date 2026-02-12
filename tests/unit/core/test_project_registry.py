"""Tests for central project registry.

Per STAKEHOLDER-CONTEXT Section 10: Verify the registry is the single source
of truth for all Asana project GIDs and that values match entity classes.
"""

from __future__ import annotations

import pytest

from autom8_asana.core.project_registry import (
    ACCOUNT_ERROR_PIPELINE_PROJECT,
    ASSET_EDIT_HOLDER_PROJECT,
    ASSET_EDIT_PROJECT,
    BUSINESS_PROJECT,
    CONTACT_HOLDER_PROJECT,
    CONTACT_PROJECT,
    DNA_HOLDER_PROJECT,
    EXPANSION_PIPELINE_PROJECT,
    HOURS_PROJECT,
    IMPLEMENTATION_PIPELINE_PROJECT,
    LOCATION_PROJECT,
    OFFER_HOLDER_PROJECT,
    OFFER_PROJECT,
    ONBOARDING_PIPELINE_PROJECT,
    OUTREACH_PIPELINE_PROJECT,
    REACTIVATION_PIPELINE_PROJECT,
    RECONCILIATION_HOLDER_PROJECT,
    RETENTION_PIPELINE_PROJECT,
    SALES_PIPELINE_PROJECT,
    UNIT_HOLDER_PROJECT,
    UNIT_PROJECT,
    VIDEOGRAPHY_HOLDER_PROJECT,
    all_entity_project_gids,
    all_pipeline_project_gids,
    all_project_gids,
    get_project_gid,
    get_project_name,
)

# =============================================================================
# Module-Level Constants
# =============================================================================

ALL_ENTITY_CONSTANTS = {
    "BUSINESS_PROJECT": BUSINESS_PROJECT,
    "UNIT_PROJECT": UNIT_PROJECT,
    "UNIT_HOLDER_PROJECT": UNIT_HOLDER_PROJECT,
    "OFFER_PROJECT": OFFER_PROJECT,
    "OFFER_HOLDER_PROJECT": OFFER_HOLDER_PROJECT,
    "CONTACT_PROJECT": CONTACT_PROJECT,
    "CONTACT_HOLDER_PROJECT": CONTACT_HOLDER_PROJECT,
    "ASSET_EDIT_PROJECT": ASSET_EDIT_PROJECT,
    "ASSET_EDIT_HOLDER_PROJECT": ASSET_EDIT_HOLDER_PROJECT,
    "LOCATION_PROJECT": LOCATION_PROJECT,
    "HOURS_PROJECT": HOURS_PROJECT,
    "DNA_HOLDER_PROJECT": DNA_HOLDER_PROJECT,
    "RECONCILIATION_HOLDER_PROJECT": RECONCILIATION_HOLDER_PROJECT,
    "VIDEOGRAPHY_HOLDER_PROJECT": VIDEOGRAPHY_HOLDER_PROJECT,
}

ALL_PIPELINE_CONSTANTS = {
    "SALES_PIPELINE_PROJECT": SALES_PIPELINE_PROJECT,
    "OUTREACH_PIPELINE_PROJECT": OUTREACH_PIPELINE_PROJECT,
    "ONBOARDING_PIPELINE_PROJECT": ONBOARDING_PIPELINE_PROJECT,
    "IMPLEMENTATION_PIPELINE_PROJECT": IMPLEMENTATION_PIPELINE_PROJECT,
    "RETENTION_PIPELINE_PROJECT": RETENTION_PIPELINE_PROJECT,
    "REACTIVATION_PIPELINE_PROJECT": REACTIVATION_PIPELINE_PROJECT,
    "ACCOUNT_ERROR_PIPELINE_PROJECT": ACCOUNT_ERROR_PIPELINE_PROJECT,
    "EXPANSION_PIPELINE_PROJECT": EXPANSION_PIPELINE_PROJECT,
}

ALL_CONSTANTS = {**ALL_ENTITY_CONSTANTS, **ALL_PIPELINE_CONSTANTS}


# =============================================================================
# GID Value Tests
# =============================================================================


class TestGidValues:
    """Verify all GID constants are valid non-empty strings."""

    @pytest.mark.parametrize("name,gid", sorted(ALL_CONSTANTS.items()))
    def test_gid_is_nonempty_string(self, name: str, gid: str) -> None:
        """Each GID must be a non-empty string."""
        assert isinstance(gid, str), f"{name} should be a string, got {type(gid)}"
        assert len(gid) > 0, f"{name} should not be empty"

    @pytest.mark.parametrize("name,gid", sorted(ALL_CONSTANTS.items()))
    def test_gid_is_numeric(self, name: str, gid: str) -> None:
        """Asana GIDs are purely numeric strings."""
        assert gid.isdigit(), f"{name} GID {gid!r} should be all digits"

    def test_no_duplicate_gids(self) -> None:
        """All GIDs should be unique (no two names map to the same GID)."""
        gids = list(ALL_CONSTANTS.values())
        assert len(gids) == len(set(gids)), (
            f"Duplicate GIDs found: "
            f"{[g for g in gids if gids.count(g) > 1]}"
        )

    def test_total_registered_count(self) -> None:
        """Registry should contain exactly 22 projects (14 entity + 8 pipeline)."""
        assert len(ALL_CONSTANTS) == 22


# =============================================================================
# Forward Lookup Tests
# =============================================================================


class TestGetProjectGid:
    """Tests for get_project_gid() forward lookup."""

    @pytest.mark.parametrize("name,expected_gid", sorted(ALL_CONSTANTS.items()))
    def test_returns_correct_gid(self, name: str, expected_gid: str) -> None:
        """get_project_gid returns the matching GID for each logical name."""
        assert get_project_gid(name) == expected_gid

    def test_unknown_name_raises_key_error(self) -> None:
        """Unknown logical names raise KeyError with helpful message."""
        with pytest.raises(KeyError, match="Unknown project logical name"):
            get_project_gid("NONEXISTENT_PROJECT")

    def test_error_message_lists_available_names(self) -> None:
        """Error message includes list of valid names."""
        with pytest.raises(KeyError, match="Available names"):
            get_project_gid("BOGUS")

    def test_case_sensitive(self) -> None:
        """Lookup is case-sensitive (lowercase should fail)."""
        with pytest.raises(KeyError):
            get_project_gid("business_project")


# =============================================================================
# Reverse Lookup Tests
# =============================================================================


class TestGetProjectName:
    """Tests for get_project_name() reverse lookup."""

    @pytest.mark.parametrize("name,gid", sorted(ALL_CONSTANTS.items()))
    def test_returns_correct_name(self, name: str, gid: str) -> None:
        """get_project_name returns the matching logical name for each GID."""
        assert get_project_name(gid) == name

    def test_unknown_gid_raises_key_error(self) -> None:
        """Unknown GIDs raise KeyError with helpful message."""
        with pytest.raises(KeyError, match="Unknown project GID"):
            get_project_name("9999999999999999")

    def test_roundtrip_forward_then_reverse(self) -> None:
        """Forward then reverse lookup produces the original name."""
        for name in ALL_CONSTANTS:
            gid = get_project_gid(name)
            assert get_project_name(gid) == name

    def test_roundtrip_reverse_then_forward(self) -> None:
        """Reverse then forward lookup produces the original GID."""
        for gid in ALL_CONSTANTS.values():
            name = get_project_name(gid)
            assert get_project_gid(name) == gid


# =============================================================================
# Collection Helper Tests
# =============================================================================


class TestCollectionHelpers:
    """Tests for all_project_gids, all_pipeline_project_gids, all_entity_project_gids."""

    def test_all_project_gids_returns_frozenset(self) -> None:
        """all_project_gids returns a frozenset."""
        result = all_project_gids()
        assert isinstance(result, frozenset)

    def test_all_project_gids_count(self) -> None:
        """all_project_gids contains all 22 unique GIDs."""
        assert len(all_project_gids()) == 22

    def test_all_pipeline_project_gids_count(self) -> None:
        """all_pipeline_project_gids returns 8 pipeline GIDs."""
        result = all_pipeline_project_gids()
        assert len(result) == 8

    def test_all_pipeline_project_gids_order(self) -> None:
        """Pipeline GIDs are in declaration order (sales first)."""
        result = all_pipeline_project_gids()
        assert result[0] == SALES_PIPELINE_PROJECT
        assert result[-1] == EXPANSION_PIPELINE_PROJECT

    def test_all_pipeline_project_gids_content(self) -> None:
        """Pipeline list matches the pipeline constants."""
        result = set(all_pipeline_project_gids())
        expected = set(ALL_PIPELINE_CONSTANTS.values())
        assert result == expected

    def test_all_entity_project_gids_count(self) -> None:
        """all_entity_project_gids returns 14 entity GIDs."""
        result = all_entity_project_gids()
        assert len(result) == 14

    def test_entity_and_pipeline_gids_are_disjoint(self) -> None:
        """Entity and pipeline GID sets do not overlap."""
        entity_set = set(all_entity_project_gids())
        pipeline_set = set(all_pipeline_project_gids())
        assert entity_set.isdisjoint(pipeline_set)

    def test_entity_plus_pipeline_equals_all(self) -> None:
        """Entity + pipeline GIDs = all project GIDs."""
        entity_set = set(all_entity_project_gids())
        pipeline_set = set(all_pipeline_project_gids())
        assert entity_set | pipeline_set == all_project_gids()


# =============================================================================
# Parity Tests: Registry vs Entity Classes
# =============================================================================


class TestParityWithEntityClasses:
    """Verify registry GIDs match PRIMARY_PROJECT_GID on entity classes.

    These tests import each entity class and compare its PRIMARY_PROJECT_GID
    attribute to the corresponding registry constant. This ensures the registry
    stays in sync until entity classes are migrated to reference it directly.
    """

    def test_business_parity(self) -> None:
        from autom8_asana.models.business.business import Business

        assert Business.PRIMARY_PROJECT_GID == BUSINESS_PROJECT

    def test_unit_parity(self) -> None:
        from autom8_asana.models.business.unit import Unit

        assert Unit.PRIMARY_PROJECT_GID == UNIT_PROJECT

    def test_unit_holder_parity(self) -> None:
        from autom8_asana.models.business.unit import UnitHolder

        assert UnitHolder.PRIMARY_PROJECT_GID == UNIT_HOLDER_PROJECT

    def test_offer_parity(self) -> None:
        from autom8_asana.models.business.offer import Offer

        assert Offer.PRIMARY_PROJECT_GID == OFFER_PROJECT

    def test_offer_holder_parity(self) -> None:
        from autom8_asana.models.business.offer import OfferHolder

        assert OfferHolder.PRIMARY_PROJECT_GID == OFFER_HOLDER_PROJECT

    def test_contact_parity(self) -> None:
        from autom8_asana.models.business.contact import Contact

        assert Contact.PRIMARY_PROJECT_GID == CONTACT_PROJECT

    def test_contact_holder_parity(self) -> None:
        from autom8_asana.models.business.contact import ContactHolder

        assert ContactHolder.PRIMARY_PROJECT_GID == CONTACT_HOLDER_PROJECT

    def test_asset_edit_parity(self) -> None:
        from autom8_asana.models.business.asset_edit import AssetEdit

        assert AssetEdit.PRIMARY_PROJECT_GID == ASSET_EDIT_PROJECT

    def test_asset_edit_holder_parity(self) -> None:
        from autom8_asana.models.business.business import AssetEditHolder

        assert AssetEditHolder.PRIMARY_PROJECT_GID == ASSET_EDIT_HOLDER_PROJECT

    def test_location_parity(self) -> None:
        from autom8_asana.models.business.location import Location

        assert Location.PRIMARY_PROJECT_GID == LOCATION_PROJECT

    def test_hours_parity(self) -> None:
        from autom8_asana.models.business.hours import Hours

        assert Hours.PRIMARY_PROJECT_GID == HOURS_PROJECT

    def test_dna_holder_parity(self) -> None:
        from autom8_asana.models.business.business import DNAHolder

        assert DNAHolder.PRIMARY_PROJECT_GID == DNA_HOLDER_PROJECT

    def test_reconciliation_holder_parity(self) -> None:
        from autom8_asana.models.business.business import ReconciliationHolder

        assert ReconciliationHolder.PRIMARY_PROJECT_GID == RECONCILIATION_HOLDER_PROJECT

    def test_videography_holder_parity(self) -> None:
        from autom8_asana.models.business.business import VideographyHolder

        assert VideographyHolder.PRIMARY_PROJECT_GID == VIDEOGRAPHY_HOLDER_PROJECT


# =============================================================================
# Parity Tests: Registry vs Lifecycle YAML
# =============================================================================


class TestParityWithLifecycleYaml:
    """Verify pipeline registry GIDs match lifecycle_stages.yaml project_gid values.

    These are hardcoded parity checks. If the YAML changes, these tests will
    catch the drift.
    """

    def test_sales_yaml_parity(self) -> None:
        assert SALES_PIPELINE_PROJECT == "1200944186565610"

    def test_outreach_yaml_parity(self) -> None:
        assert OUTREACH_PIPELINE_PROJECT == "1201753128450029"

    def test_onboarding_yaml_parity(self) -> None:
        assert ONBOARDING_PIPELINE_PROJECT == "1201319387632570"

    def test_implementation_yaml_parity(self) -> None:
        assert IMPLEMENTATION_PIPELINE_PROJECT == "1201476141989746"

    def test_retention_yaml_parity(self) -> None:
        assert RETENTION_PIPELINE_PROJECT == "1201346565918814"

    def test_reactivation_yaml_parity(self) -> None:
        assert REACTIVATION_PIPELINE_PROJECT == "1201265144487549"

    def test_account_error_yaml_parity(self) -> None:
        assert ACCOUNT_ERROR_PIPELINE_PROJECT == "1201684018234520"

    def test_expansion_yaml_parity(self) -> None:
        assert EXPANSION_PIPELINE_PROJECT == "1201265144487557"


# =============================================================================
# Parity Tests: Registry vs Workflow Hardcoded GIDs
# =============================================================================


class TestParityWithWorkflows:
    """Verify registry GIDs match hardcoded values in workflow modules."""

    def test_conversation_audit_contact_holder_parity(self) -> None:
        """conversation_audit.py CONTACT_HOLDER_PROJECT_GID matches registry."""
        from autom8_asana.automation.workflows.conversation_audit import (
            CONTACT_HOLDER_PROJECT_GID,
        )

        assert CONTACT_HOLDER_PROJECT_GID == CONTACT_HOLDER_PROJECT

    def test_pipeline_transition_default_projects_parity(self) -> None:
        """pipeline_transition.py DEFAULT_PIPELINE_PROJECTS matches registry."""
        from autom8_asana.automation.workflows.pipeline_transition import (
            DEFAULT_PIPELINE_PROJECTS,
        )

        assert set(DEFAULT_PIPELINE_PROJECTS) == set(all_pipeline_project_gids())
