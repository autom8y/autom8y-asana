"""Tests for entity model account_activity properties.

Covers Offer.account_activity, Unit.account_activity, and
Business.max_unit_activity properties added in Phase 2.
"""

from __future__ import annotations

from unittest.mock import MagicMock


from autom8_asana.models.business.activity import (
    ACTIVITY_PRIORITY,
    AccountActivity,
)
from autom8_asana.models.business.business import Business
from autom8_asana.models.business.offer import Offer
from autom8_asana.models.business.unit import Unit, UnitHolder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OFFER_PROJECT_GID = "1143843662099250"
UNIT_PROJECT_GID = "1201081073731555"


def _make_offer(section_name: str | None = None, project_gid: str = OFFER_PROJECT_GID) -> Offer:
    """Create an Offer with optional section membership."""
    memberships = []
    if section_name is not None:
        memberships.append({
            "project": {"gid": project_gid, "name": "Offers"},
            "section": {"gid": "sec1", "name": section_name},
        })
    return Offer(
        gid="offer1",
        name="Test Offer",
        resource_type="task",
        custom_fields=[],
        memberships=memberships,
    )


def _make_unit(section_name: str | None = None, project_gid: str = UNIT_PROJECT_GID) -> Unit:
    """Create a Unit with optional section membership."""
    memberships = []
    if section_name is not None:
        memberships.append({
            "project": {"gid": project_gid, "name": "Units"},
            "section": {"gid": "sec1", "name": section_name},
        })
    return Unit(
        gid="unit1",
        name="Test Unit",
        resource_type="task",
        custom_fields=[],
        memberships=memberships,
    )


def _make_business_with_units(unit_activities: list[AccountActivity | None]) -> Business:
    """Create a Business with mock Units having specific activity values."""
    business = Business(
        gid="biz1",
        name="Test Business",
        resource_type="task",
        custom_fields=[],
    )

    # Create mock UnitHolder with mock units
    mock_units = []
    for activity in unit_activities:
        mock_unit = MagicMock(spec=Unit)
        mock_unit.account_activity = activity
        mock_units.append(mock_unit)

    mock_holder = MagicMock(spec=UnitHolder)
    mock_holder.units = mock_units
    business._unit_holder = mock_holder

    return business


# ---------------------------------------------------------------------------
# Offer.account_activity
# ---------------------------------------------------------------------------


class TestOfferAccountActivity:
    """Tests for Offer.account_activity property."""

    def test_active_section(self) -> None:
        offer = _make_offer("ACTIVE")
        assert offer.account_activity == AccountActivity.ACTIVE

    def test_activating_section(self) -> None:
        offer = _make_offer("ACTIVATING")
        assert offer.account_activity == AccountActivity.ACTIVATING

    def test_inactive_section(self) -> None:
        offer = _make_offer("INACTIVE")
        assert offer.account_activity == AccountActivity.INACTIVE

    def test_ignored_section(self) -> None:
        offer = _make_offer("Sales Process")
        assert offer.account_activity == AccountActivity.IGNORED

    def test_no_memberships_returns_none(self) -> None:
        offer = _make_offer(None)
        assert offer.account_activity is None

    def test_unknown_section_returns_none(self) -> None:
        offer = _make_offer("UNKNOWN SECTION NAME")
        assert offer.account_activity is None

    def test_case_insensitive(self) -> None:
        offer = _make_offer("active")
        assert offer.account_activity == AccountActivity.ACTIVE

    def test_optimize_sections(self) -> None:
        offer = _make_offer("OPTIMIZE - Human Review")
        assert offer.account_activity == AccountActivity.ACTIVE

    def test_staging_section(self) -> None:
        offer = _make_offer("STAGING")
        assert offer.account_activity == AccountActivity.ACTIVE

    def test_launch_error_section(self) -> None:
        offer = _make_offer("LAUNCH ERROR")
        assert offer.account_activity == AccountActivity.ACTIVATING

    def test_account_error_section(self) -> None:
        offer = _make_offer("ACCOUNT ERROR")
        assert offer.account_activity == AccountActivity.INACTIVE

    def test_wrong_project_returns_none(self) -> None:
        """Offer in a different project should not match."""
        offer = _make_offer("ACTIVE", project_gid="wrong_project_gid")
        assert offer.account_activity is None

    def test_empty_memberships_returns_none(self) -> None:
        offer = Offer(
            gid="offer1",
            name="Test Offer",
            resource_type="task",
            custom_fields=[],
            memberships=[],
        )
        assert offer.account_activity is None


# ---------------------------------------------------------------------------
# Unit.account_activity
# ---------------------------------------------------------------------------


class TestUnitAccountActivity:
    """Tests for Unit.account_activity property."""

    def test_active_section(self) -> None:
        unit = _make_unit("Active")
        assert unit.account_activity == AccountActivity.ACTIVE

    def test_month_1_section(self) -> None:
        unit = _make_unit("Month 1")
        assert unit.account_activity == AccountActivity.ACTIVE

    def test_consulting_section(self) -> None:
        unit = _make_unit("Consulting")
        assert unit.account_activity == AccountActivity.ACTIVE

    def test_activating_section(self) -> None:
        unit = _make_unit("Onboarding")
        assert unit.account_activity == AccountActivity.ACTIVATING

    def test_implementing_section(self) -> None:
        unit = _make_unit("Implementing")
        assert unit.account_activity == AccountActivity.ACTIVATING

    def test_inactive_section(self) -> None:
        unit = _make_unit("Paused")
        assert unit.account_activity == AccountActivity.INACTIVE

    def test_cancelled_section(self) -> None:
        unit = _make_unit("Cancelled")
        assert unit.account_activity == AccountActivity.INACTIVE

    def test_ignored_section(self) -> None:
        unit = _make_unit("Templates")
        assert unit.account_activity == AccountActivity.IGNORED

    def test_no_memberships_returns_none(self) -> None:
        unit = _make_unit(None)
        assert unit.account_activity is None

    def test_unknown_section_returns_none(self) -> None:
        unit = _make_unit("UNKNOWN SECTION")
        assert unit.account_activity is None

    def test_case_insensitive(self) -> None:
        unit = _make_unit("ACTIVE")
        assert unit.account_activity == AccountActivity.ACTIVE

    def test_wrong_project_returns_none(self) -> None:
        unit = _make_unit("Active", project_gid="wrong_project_gid")
        assert unit.account_activity is None

    def test_delayed_section(self) -> None:
        unit = _make_unit("Delayed")
        assert unit.account_activity == AccountActivity.ACTIVATING

    def test_no_start_section(self) -> None:
        unit = _make_unit("No Start")
        assert unit.account_activity == AccountActivity.INACTIVE


# ---------------------------------------------------------------------------
# Business.max_unit_activity
# ---------------------------------------------------------------------------


class TestBusinessMaxUnitActivity:
    """Tests for Business.max_unit_activity property."""

    def test_no_units_returns_none(self) -> None:
        business = Business(
            gid="biz1",
            name="Test Business",
            resource_type="task",
            custom_fields=[],
        )
        # No unit_holder set -> units returns []
        assert business.max_unit_activity is None

    def test_single_active_unit(self) -> None:
        business = _make_business_with_units([AccountActivity.ACTIVE])
        assert business.max_unit_activity == AccountActivity.ACTIVE

    def test_single_inactive_unit(self) -> None:
        business = _make_business_with_units([AccountActivity.INACTIVE])
        assert business.max_unit_activity == AccountActivity.INACTIVE

    def test_active_beats_inactive(self) -> None:
        business = _make_business_with_units([
            AccountActivity.INACTIVE,
            AccountActivity.ACTIVE,
        ])
        assert business.max_unit_activity == AccountActivity.ACTIVE

    def test_active_beats_activating(self) -> None:
        business = _make_business_with_units([
            AccountActivity.ACTIVATING,
            AccountActivity.ACTIVE,
        ])
        assert business.max_unit_activity == AccountActivity.ACTIVE

    def test_activating_beats_inactive(self) -> None:
        business = _make_business_with_units([
            AccountActivity.INACTIVE,
            AccountActivity.ACTIVATING,
        ])
        assert business.max_unit_activity == AccountActivity.ACTIVATING

    def test_activating_beats_ignored(self) -> None:
        business = _make_business_with_units([
            AccountActivity.IGNORED,
            AccountActivity.ACTIVATING,
        ])
        assert business.max_unit_activity == AccountActivity.ACTIVATING

    def test_inactive_beats_ignored(self) -> None:
        business = _make_business_with_units([
            AccountActivity.IGNORED,
            AccountActivity.INACTIVE,
        ])
        assert business.max_unit_activity == AccountActivity.INACTIVE

    def test_all_activities_returns_active(self) -> None:
        business = _make_business_with_units([
            AccountActivity.IGNORED,
            AccountActivity.INACTIVE,
            AccountActivity.ACTIVATING,
            AccountActivity.ACTIVE,
        ])
        assert business.max_unit_activity == AccountActivity.ACTIVE

    def test_all_none_returns_none(self) -> None:
        business = _make_business_with_units([None, None, None])
        assert business.max_unit_activity is None

    def test_mixed_none_and_values(self) -> None:
        business = _make_business_with_units([
            None,
            AccountActivity.INACTIVE,
            None,
        ])
        assert business.max_unit_activity == AccountActivity.INACTIVE

    def test_single_ignored_unit(self) -> None:
        business = _make_business_with_units([AccountActivity.IGNORED])
        assert business.max_unit_activity == AccountActivity.IGNORED

    def test_multiple_same_activity(self) -> None:
        business = _make_business_with_units([
            AccountActivity.ACTIVATING,
            AccountActivity.ACTIVATING,
            AccountActivity.ACTIVATING,
        ])
        assert business.max_unit_activity == AccountActivity.ACTIVATING

    def test_priority_ordering_is_consistent(self) -> None:
        """Verify max_unit_activity follows ACTIVITY_PRIORITY ordering."""
        for i in range(len(ACTIVITY_PRIORITY)):
            for j in range(i + 1, len(ACTIVITY_PRIORITY)):
                higher = ACTIVITY_PRIORITY[i]
                lower = ACTIVITY_PRIORITY[j]
                business = _make_business_with_units([lower, higher])
                assert business.max_unit_activity == higher, (
                    f"{higher} should beat {lower}"
                )

    def test_empty_unit_holder(self) -> None:
        business = _make_business_with_units([])
        assert business.max_unit_activity is None
