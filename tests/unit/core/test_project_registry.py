"""Tests for central project registry.

Per STAKEHOLDER-CONTEXT Section 10: Verify the registry is the single source
of truth for all Asana project GIDs and that values match entity classes.
"""

from __future__ import annotations

import pytest

from autom8_asana.core.project_registry import (
    ACCOUNT_ERROR_PIPELINE_PROJECT,
    ACTIVATION_CONSULTATION_PROJECT,
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
    "ACTIVATION_CONSULTATION_PROJECT": ACTIVATION_CONSULTATION_PROJECT,
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
            f"Duplicate GIDs found: {[g for g in gids if gids.count(g) > 1]}"
        )

    def test_total_registered_count(self) -> None:
        """Registry should contain exactly 23 projects (14 entity + 9 pipeline)."""
        assert len(ALL_CONSTANTS) == 23


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
        """all_project_gids contains all 23 unique GIDs."""
        assert len(all_project_gids()) == 23

    def test_all_pipeline_project_gids_count(self) -> None:
        """all_pipeline_project_gids returns 9 pipeline GIDs."""
        result = all_pipeline_project_gids()
        assert len(result) == 9

    def test_all_pipeline_project_gids_order(self) -> None:
        """Pipeline GIDs are in declaration order (sales first)."""
        result = all_pipeline_project_gids()
        assert result[0] == SALES_PIPELINE_PROJECT
        assert result[-1] == ACTIVATION_CONSULTATION_PROJECT

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


# =============================================================================
# TD-005: Bulk Pre-Materialization Key Enumeration
# =============================================================================


# =============================================================================
# ADR-3 WS-2: Consumer Warm Set (34 GIDs) -- set-diff regression
# =============================================================================

# The authoritative consumer-derived warm set: the GID of every ``Project``
# subclass that the consumer ``refresh_project_frames._gather_project_classes()``
# enumerates (autom8/apis/asana_api/objects/project/models/__init__.py, minus
# the two abstract GID-less bases ProcessProject/IsolatedPlayProject). This is
# the SOURCE-OF-TRUTH the receiver warm set MUST equal (set-diff == 0). Drift in
# either direction (consumer adds a Project subclass, or the receiver warm set
# desyncs) is caught by ``test_warm_set_setdiff_consumer_is_empty`` below.
#
# If the consumer adds/removes a Project subclass, this fixture is updated in
# the SAME commit and the regression test re-confirms set-diff == 0. The live
# re-gate (VG-004) verifies the static set is a superset of the live enumeration.
CONSUMER_REFRESH_FRAMES_GIDS: frozenset[str] = frozenset(
    {
        "1205526136594283",  # QuestionOnPerformance
        "1143843662099250",  # BusinessOffers
        "1201627461398630",  # Commission
        "1200775689604552",  # Contacts
        "1202204184560785",  # PaidContent
        "1201684018234520",  # AccountError
        "1167650840134033",  # BackendClientSuccessDna
        "1207507299545000",  # BackendOnboardABusiness
        "1201081073731555",  # BusinessUnits
        "1200653012566782",  # Businesses
        "1201532776033312",  # Consultation
        "1201476141989746",  # Implementation
        "1210679066066870",  # OfferHolders
        "1206330409791366",  # PauseABusinessUnit
        "1201346565918814",  # Retention
        "1201500116978260",  # ContactHolder
        "1203992664400125",  # AssetEditHolder
        "1207984018149338",  # VideographyServices
        "1206176773330155",  # VideographerSourcing
        "1208231632857419",  # OptimizationNotifications
        "1200944186565610",  # Sales
        "1201319387632570",  # Onboarding
        "1201753128450029",  # Outreach
        "1201265144487557",  # Expansion
        "1201614578074026",  # Hours
        "1200836133305610",  # Locations
        "1204433992667196",  # Units
        "1203404998225231",  # Reconciliations
        "1208848470341588",  # CustomerHealth
        "1209247943184017",  # PracticeOfTheWeek
        "1209247943184021",  # ActivationConsultation
        "1209442849265632",  # CalendarIntegrations
        "1209442727608287",  # AccessProcessing
        "1201265144487549",  # Reactivation
    }
)


class TestConsumerWarmSet:
    """ADR-3 §3.1: the warm set MUST equal the consumer's 34-GID subclass set."""

    def test_consumer_fixture_has_34_distinct_gids(self) -> None:
        """The consumer enumerates exactly 34 distinct GID-bearing subclasses."""
        assert len(CONSUMER_REFRESH_FRAMES_GIDS) == 34

    def test_warm_set_has_34_distinct_gids(self) -> None:
        """The receiver warm set is exactly 34 distinct GIDs (no dupes)."""
        from autom8_asana.core.project_registry import consumer_warm_set_gids

        gids = consumer_warm_set_gids()
        assert len(gids) == 34
        assert len(set(gids)) == 34, "warm set has duplicate GIDs"

    def test_warm_set_setdiff_consumer_is_empty(self) -> None:
        """ADR-3 acceptance: set-diff(warm-set, consumer) == 0 in BOTH directions.

        This is the load-bearing reconciliation assertion (CF-3). A non-empty
        diff means either the receiver omits a consumer-queried GID (cold-503
        under bulk fan-out) or warms a GID the consumer never queries (waste +
        false denominator).
        """
        from autom8_asana.core.project_registry import consumer_warm_set_gids

        warm = set(consumer_warm_set_gids())
        consumer = set(CONSUMER_REFRESH_FRAMES_GIDS)
        missing_from_warm = consumer - warm
        extra_in_warm = warm - consumer
        assert not missing_from_warm, f"consumer GIDs not warmed: {sorted(missing_from_warm)}"
        assert not extra_in_warm, f"warm GIDs the consumer never queries: {sorted(extra_in_warm)}"

    def test_domain_registry_is_strict_subset_of_warm_set(self) -> None:
        """The 23 domain-registry GIDs are a strict subset of the 34 warm GIDs.

        Confirms the reconcile is PURE-ADDITIVE: every existing domain GID is
        still warmed, and exactly 11 consumer-only GIDs are added (ADR-3 §3.1
        one-way-door note: no receiver-only GID, no resolution-behavior change).
        """
        from autom8_asana.core.project_registry import (
            all_project_gids,
            consumer_warm_set_gids,
        )

        domain = all_project_gids()
        warm = set(consumer_warm_set_gids())
        assert domain <= warm, f"domain GIDs dropped from warm set: {sorted(domain - warm)}"
        assert len(warm - domain) == 11, "expected exactly 11 consumer-only warm GIDs"

    def test_warm_set_gids_are_numeric_strings(self) -> None:
        """Every warm GID is a non-empty all-digit Asana GID string."""
        from autom8_asana.core.project_registry import consumer_warm_set_gids

        for gid in consumer_warm_set_gids():
            assert isinstance(gid, str) and gid.isdigit(), f"bad GID {gid!r}"


class TestBulkPrematerializationKeys:
    """Verify the TD-005 (project_gid, entity_type) bulk warm enumeration."""

    def test_default_arms_are_project_and_section(self) -> None:
        """The default arms are exactly the body-parameterized consumer arms."""
        from autom8_asana.core.project_registry import BULK_PREMATERIALIZATION_ARMS

        assert BULK_PREMATERIALIZATION_ARMS == ("project", "section")

    def test_enumerates_gids_times_arms(self) -> None:
        """Key count is len(warm GIDs) x len(arms) -- the 68-key reconciled scope."""
        from autom8_asana.core.project_registry import (
            bulk_prematerialization_keys,
            consumer_warm_set_gids,
        )

        keys = bulk_prematerialization_keys()
        gid_count = len(consumer_warm_set_gids())
        # 34 consumer GIDs x 2 arms = 68 (reconciled, ADR-3 §3.1).
        assert len(keys) == gid_count * 2
        assert len(keys) == 68

    def test_each_gid_paired_with_each_arm(self) -> None:
        """Every warm-set GID appears once per arm."""
        from autom8_asana.core.project_registry import (
            bulk_prematerialization_keys,
            consumer_warm_set_gids,
        )

        keys = bulk_prematerialization_keys()
        for gid in consumer_warm_set_gids():
            assert (gid, "project") in keys
            assert (gid, "section") in keys

    def test_heaviest_first_ordering(self) -> None:
        """CF-2 fix: the DNA holder (heaviest GID) is warmed FIRST, not last."""
        from autom8_asana.core.project_registry import bulk_prematerialization_keys

        keys = bulk_prematerialization_keys()
        first_gid = keys[0][0]
        # BackendClientSuccessDna ~30k rows -- the OOM driver, must lead.
        assert first_gid == "1167650840134033"

    def test_deterministic_order(self) -> None:
        """Enumeration order is stable across calls (checkpoint resume needs it)."""
        from autom8_asana.core.project_registry import bulk_prematerialization_keys

        assert bulk_prematerialization_keys() == bulk_prematerialization_keys()

    def test_custom_arms_subset(self) -> None:
        """A single-arm enumeration yields one key per warm GID."""
        from autom8_asana.core.project_registry import (
            bulk_prematerialization_keys,
            consumer_warm_set_gids,
        )

        keys = bulk_prematerialization_keys(arms=("project",))
        assert len(keys) == len(consumer_warm_set_gids())
        assert all(et == "project" for _gid, et in keys)


class TestFastLanePrematerializationKeys:
    """Verify the SRE fast-lane heavy-subset (project_gid, entity_type) enumeration."""

    def test_fast_lane_gids_are_the_two_heaviest(self) -> None:
        """FAST_LANE_HEAVY_GIDS references the existing constants, not literals."""
        from autom8_asana.core.project_registry import (
            DNA_HOLDER_PROJECT,
            FAST_LANE_HEAVY_GIDS,
            UNIT_PROJECT,
        )

        # Identity (is), not just equality: the constants are the source of truth.
        assert FAST_LANE_HEAVY_GIDS == (DNA_HOLDER_PROJECT, UNIT_PROJECT)
        assert FAST_LANE_HEAVY_GIDS[0] is DNA_HOLDER_PROJECT
        assert FAST_LANE_HEAVY_GIDS[1] is UNIT_PROJECT

    def test_enumerates_four_keys(self) -> None:
        """2 heavy GIDs x 2 arms = 4 keys -- the fast lane's own denominator."""
        from autom8_asana.core.project_registry import (
            FAST_LANE_HEAVY_GIDS,
            fast_lane_prematerialization_keys,
        )

        keys = fast_lane_prematerialization_keys()
        assert len(keys) == len(FAST_LANE_HEAVY_GIDS) * 2
        assert len(keys) == 4

    def test_each_heavy_gid_paired_with_each_arm(self) -> None:
        """Every fast-lane GID appears once per body-parameterized arm."""
        from autom8_asana.core.project_registry import (
            FAST_LANE_HEAVY_GIDS,
            fast_lane_prematerialization_keys,
        )

        keys = fast_lane_prematerialization_keys()
        for gid in FAST_LANE_HEAVY_GIDS:
            assert (gid, "project") in keys
            assert (gid, "section") in keys

    def test_exact_four_key_membership(self) -> None:
        """The 4 keys are exactly the DNA-holder and BusinessUnits x both arms."""
        from autom8_asana.core.project_registry import (
            fast_lane_prematerialization_keys,
        )

        keys = set(fast_lane_prematerialization_keys())
        assert keys == {
            ("1167650840134033", "project"),  # DNA holder (heaviest)
            ("1167650840134033", "section"),
            ("1201081073731555", "project"),  # BusinessUnits
            ("1201081073731555", "section"),
        }

    def test_heaviest_first_ordering(self) -> None:
        """DNA holder (heaviest GID) leads, matching the bulk-sweep contract."""
        from autom8_asana.core.project_registry import (
            fast_lane_prematerialization_keys,
        )

        keys = fast_lane_prematerialization_keys()
        assert keys[0][0] == "1167650840134033"

    def test_deterministic_order(self) -> None:
        """Enumeration order is stable across calls (checkpoint resume needs it)."""
        from autom8_asana.core.project_registry import (
            fast_lane_prematerialization_keys,
        )

        assert fast_lane_prematerialization_keys() == fast_lane_prematerialization_keys()

    def test_custom_arms_subset(self) -> None:
        """A single-arm enumeration yields one key per fast-lane GID."""
        from autom8_asana.core.project_registry import (
            FAST_LANE_HEAVY_GIDS,
            fast_lane_prematerialization_keys,
        )

        keys = fast_lane_prematerialization_keys(arms=("project",))
        assert len(keys) == len(FAST_LANE_HEAVY_GIDS)
        assert all(et == "project" for _gid, et in keys)

    def test_fast_lane_is_subset_of_bulk_sweep(self) -> None:
        """BACKSTOP invariant: every fast key is also a bulk-sweep key.

        This is the runtime mirror of the module-load parity assertion: the
        30-min bulk sweep must remain the backstop for every fast-lane GID, so
        the fast key set is a strict subset of the full sweep key set.
        """
        from autom8_asana.core.project_registry import (
            bulk_prematerialization_keys,
            fast_lane_prematerialization_keys,
        )

        fast = set(fast_lane_prematerialization_keys())
        bulk = set(bulk_prematerialization_keys())
        assert fast <= bulk
        assert fast  # non-empty

    def test_parity_assertion_holds_fast_gids_in_tier1_heavy(self) -> None:
        """The module-load parity invariant: fast GIDs subset TIER_1_HEAVY sweep."""
        from autom8_asana.core.project_registry import (
            _CONSUMER_WARM_SET_TIER_1_HEAVY,
            FAST_LANE_HEAVY_GIDS,
        )

        assert set(FAST_LANE_HEAVY_GIDS) <= set(_CONSUMER_WARM_SET_TIER_1_HEAVY)
