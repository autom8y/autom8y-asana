"""Tests for the section activity classifier module.

Covers AccountActivity enum, SectionClassifier, extract_section_name(),
module-level classifier instances (OFFER_CLASSIFIER, UNIT_CLASSIFIER),
CLASSIFIERS registry, and get_classifier().
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any
from unittest.mock import MagicMock

import pytest

from autom8_asana.models.business.activity import (
    ACTIVITY_PRIORITY,
    CLASSIFIERS,
    OFFER_CLASSIFIER,
    UNIT_CLASSIFIER,
    AccountActivity,
    SectionClassifier,
    extract_section_name,
    get_classifier,
)


# ---------------------------------------------------------------------------
# AccountActivity Enum
# ---------------------------------------------------------------------------


class TestAccountActivity:
    """Tests for the AccountActivity enum."""

    def test_values(self) -> None:
        assert AccountActivity.ACTIVE == "active"
        assert AccountActivity.ACTIVATING == "activating"
        assert AccountActivity.INACTIVE == "inactive"
        assert AccountActivity.IGNORED == "ignored"

    def test_is_str_enum(self) -> None:
        assert isinstance(AccountActivity.ACTIVE, str)

    def test_from_string(self) -> None:
        assert AccountActivity("active") is AccountActivity.ACTIVE
        assert AccountActivity("activating") is AccountActivity.ACTIVATING
        assert AccountActivity("inactive") is AccountActivity.INACTIVE
        assert AccountActivity("ignored") is AccountActivity.IGNORED

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError):
            AccountActivity("nonexistent")

    def test_all_members(self) -> None:
        members = set(AccountActivity)
        assert members == {
            AccountActivity.ACTIVE,
            AccountActivity.ACTIVATING,
            AccountActivity.INACTIVE,
            AccountActivity.IGNORED,
        }


# ---------------------------------------------------------------------------
# ACTIVITY_PRIORITY
# ---------------------------------------------------------------------------


class TestActivityPriority:
    """Tests for the ACTIVITY_PRIORITY tuple."""

    def test_ordering(self) -> None:
        assert ACTIVITY_PRIORITY == (
            AccountActivity.ACTIVE,
            AccountActivity.ACTIVATING,
            AccountActivity.INACTIVE,
            AccountActivity.IGNORED,
        )

    def test_all_members_present(self) -> None:
        assert set(ACTIVITY_PRIORITY) == set(AccountActivity)

    def test_active_is_highest_priority(self) -> None:
        assert ACTIVITY_PRIORITY[0] is AccountActivity.ACTIVE

    def test_ignored_is_lowest_priority(self) -> None:
        assert ACTIVITY_PRIORITY[-1] is AccountActivity.IGNORED

    def test_is_tuple(self) -> None:
        assert isinstance(ACTIVITY_PRIORITY, tuple)


# ---------------------------------------------------------------------------
# SectionClassifier
# ---------------------------------------------------------------------------


class TestSectionClassifier:
    """Tests for the SectionClassifier frozen dataclass."""

    @pytest.fixture
    def simple_classifier(self) -> SectionClassifier:
        return SectionClassifier.from_groups(
            entity_type="test",
            project_gid="123",
            groups={
                "active": {"ACTIVE", "RUNNING"},
                "activating": {"STARTING"},
                "inactive": {"PAUSED", "STOPPED"},
                "ignored": {"TEMPLATE"},
            },
        )

    # --- classify ---

    def test_classify_exact_match(self, simple_classifier: SectionClassifier) -> None:
        assert simple_classifier.classify("ACTIVE") == AccountActivity.ACTIVE
        assert simple_classifier.classify("STARTING") == AccountActivity.ACTIVATING
        assert simple_classifier.classify("PAUSED") == AccountActivity.INACTIVE
        assert simple_classifier.classify("TEMPLATE") == AccountActivity.IGNORED

    def test_classify_case_insensitive(self, simple_classifier: SectionClassifier) -> None:
        assert simple_classifier.classify("active") == AccountActivity.ACTIVE
        assert simple_classifier.classify("Active") == AccountActivity.ACTIVE
        assert simple_classifier.classify("ACTIVE") == AccountActivity.ACTIVE
        assert simple_classifier.classify("AcTiVe") == AccountActivity.ACTIVE

    def test_classify_unknown_returns_none(self, simple_classifier: SectionClassifier) -> None:
        assert simple_classifier.classify("UNKNOWN") is None
        assert simple_classifier.classify("") is None
        assert simple_classifier.classify("nonexistent section") is None

    def test_classify_all_categories(self, simple_classifier: SectionClassifier) -> None:
        assert simple_classifier.classify("RUNNING") == AccountActivity.ACTIVE
        assert simple_classifier.classify("STOPPED") == AccountActivity.INACTIVE

    # --- sections_for ---

    def test_sections_for_single_category(self, simple_classifier: SectionClassifier) -> None:
        result = simple_classifier.sections_for(AccountActivity.ACTIVE)
        assert result == frozenset({"active", "running"})

    def test_sections_for_multiple_categories(self, simple_classifier: SectionClassifier) -> None:
        result = simple_classifier.sections_for(AccountActivity.ACTIVE, AccountActivity.ACTIVATING)
        assert result == frozenset({"active", "running", "starting"})

    def test_sections_for_returns_frozenset(self, simple_classifier: SectionClassifier) -> None:
        result = simple_classifier.sections_for(AccountActivity.ACTIVE)
        assert isinstance(result, frozenset)

    def test_sections_for_no_match(self) -> None:
        classifier = SectionClassifier.from_groups(
            entity_type="test",
            project_gid="123",
            groups={"active": {"RUNNING"}},
        )
        result = classifier.sections_for(AccountActivity.INACTIVE)
        assert result == frozenset()

    # --- active_sections ---

    def test_active_sections(self, simple_classifier: SectionClassifier) -> None:
        result = simple_classifier.active_sections()
        assert result == frozenset({"active", "running"})

    # --- billable_sections ---

    def test_billable_sections(self, simple_classifier: SectionClassifier) -> None:
        result = simple_classifier.billable_sections()
        assert result == frozenset({"active", "running", "starting"})

    # --- from_groups factory ---

    def test_from_groups_creates_classifier(self) -> None:
        classifier = SectionClassifier.from_groups(
            entity_type="offer",
            project_gid="999",
            groups={"active": {"A"}, "inactive": {"B"}},
        )
        assert classifier.entity_type == "offer"
        assert classifier.project_gid == "999"
        assert classifier.classify("A") == AccountActivity.ACTIVE
        assert classifier.classify("B") == AccountActivity.INACTIVE

    def test_from_groups_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError):
            SectionClassifier.from_groups(
                entity_type="test",
                project_gid="123",
                groups={"invalid_category": {"A"}},
            )

    def test_from_groups_lowercases_keys(self) -> None:
        classifier = SectionClassifier.from_groups(
            entity_type="test",
            project_gid="123",
            groups={"active": {"UPPER CASE"}},
        )
        assert classifier.classify("upper case") == AccountActivity.ACTIVE
        assert classifier.classify("UPPER CASE") == AccountActivity.ACTIVE

    # --- Frozen guarantee ---

    def test_frozen_cannot_mutate_entity_type(self, simple_classifier: SectionClassifier) -> None:
        with pytest.raises(FrozenInstanceError):
            simple_classifier.entity_type = "other"  # type: ignore[misc]

    def test_frozen_cannot_mutate_project_gid(self, simple_classifier: SectionClassifier) -> None:
        with pytest.raises(FrozenInstanceError):
            simple_classifier.project_gid = "999"  # type: ignore[misc]

    # --- Attributes ---

    def test_entity_type(self, simple_classifier: SectionClassifier) -> None:
        assert simple_classifier.entity_type == "test"

    def test_project_gid(self, simple_classifier: SectionClassifier) -> None:
        assert simple_classifier.project_gid == "123"


# ---------------------------------------------------------------------------
# extract_section_name
# ---------------------------------------------------------------------------


def _make_task_with_memberships(
    memberships: list[dict[str, Any]] | None = None,
) -> MagicMock:
    """Create a mock task with memberships."""
    task = MagicMock()
    task.memberships = memberships
    return task


class TestExtractSectionName:
    """Tests for extract_section_name()."""

    def test_no_memberships_returns_none(self) -> None:
        task = _make_task_with_memberships(None)
        assert extract_section_name(task) is None

    def test_empty_memberships_returns_none(self) -> None:
        task = _make_task_with_memberships([])
        assert extract_section_name(task) is None

    def test_extracts_section_name(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
                "section": {"gid": "sec1", "name": "ACTIVE"},
            }
        ])
        assert extract_section_name(task) == "ACTIVE"

    def test_filters_by_project_gid(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
                "section": {"gid": "sec1", "name": "WRONG"},
            },
            {
                "project": {"gid": "proj2", "name": "Project 2"},
                "section": {"gid": "sec2", "name": "CORRECT"},
            },
        ])
        assert extract_section_name(task, project_gid="proj2") == "CORRECT"

    def test_without_project_gid_returns_first(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
                "section": {"gid": "sec1", "name": "FIRST"},
            },
            {
                "project": {"gid": "proj2", "name": "Project 2"},
                "section": {"gid": "sec2", "name": "SECOND"},
            },
        ])
        assert extract_section_name(task) == "FIRST"

    def test_no_matching_project_gid_returns_none(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
                "section": {"gid": "sec1", "name": "ACTIVE"},
            },
        ])
        assert extract_section_name(task, project_gid="nonexistent") is None

    def test_missing_section_returns_none(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
            },
        ])
        assert extract_section_name(task) is None

    def test_section_with_no_name_returns_none(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
                "section": {"gid": "sec1"},
            },
        ])
        assert extract_section_name(task) is None

    def test_section_none_returns_none(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
                "section": None,
            },
        ])
        assert extract_section_name(task) is None

    def test_preserves_original_case(self) -> None:
        task = _make_task_with_memberships([
            {
                "project": {"gid": "proj1", "name": "Project 1"},
                "section": {"gid": "sec1", "name": "Month 1"},
            },
        ])
        assert extract_section_name(task) == "Month 1"


# ---------------------------------------------------------------------------
# OFFER_CLASSIFIER
# ---------------------------------------------------------------------------


class TestOfferClassifier:
    """Tests for the OFFER_CLASSIFIER module-level instance."""

    def test_entity_type(self) -> None:
        assert OFFER_CLASSIFIER.entity_type == "offer"

    def test_project_gid(self) -> None:
        assert OFFER_CLASSIFIER.project_gid == "1143843662099250"

    def test_active_sections(self) -> None:
        active = OFFER_CLASSIFIER.active_sections()
        assert "active" in active
        assert "pending approval" in active
        assert "staging" in active
        assert "staged" in active
        assert "manual" in active
        assert "system error" in active

    def test_active_section_count(self) -> None:
        assert len(OFFER_CLASSIFIER.active_sections()) == 21

    def test_activating_sections(self) -> None:
        activating = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVATING)
        assert "activating" in activating
        assert "launch error" in activating
        assert "implementing" in activating
        assert "new launch review" in activating
        assert "awaiting access" in activating
        assert len(activating) == 5

    def test_inactive_sections(self) -> None:
        inactive = OFFER_CLASSIFIER.sections_for(AccountActivity.INACTIVE)
        assert "account error" in inactive
        assert "awaiting rep update" in inactive
        assert "inactive" in inactive
        assert len(inactive) == 3

    def test_ignored_sections(self) -> None:
        ignored = OFFER_CLASSIFIER.sections_for(AccountActivity.IGNORED)
        assert "sales process" in ignored
        assert "complete" in ignored
        assert "plays" in ignored
        assert "performance concerns" in ignored
        assert len(ignored) == 4

    def test_total_section_count(self) -> None:
        total = (
            len(OFFER_CLASSIFIER.active_sections())
            + len(OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVATING))
            + len(OFFER_CLASSIFIER.sections_for(AccountActivity.INACTIVE))
            + len(OFFER_CLASSIFIER.sections_for(AccountActivity.IGNORED))
        )
        assert total == 33

    def test_classify_optimize_sections(self) -> None:
        assert OFFER_CLASSIFIER.classify("OPTIMIZE - Human Review") == AccountActivity.ACTIVE
        assert OFFER_CLASSIFIER.classify("OPTIMIZE QUANTITY - Request Asset Edit") == AccountActivity.ACTIVE
        assert OFFER_CLASSIFIER.classify("OPTIMIZE QUALITY - Update Targeting") == AccountActivity.ACTIVE
        assert OFFER_CLASSIFIER.classify("OPTIMIZE QUALITY - Poor Show Rates") == AccountActivity.ACTIVE

    def test_classify_restart_sections(self) -> None:
        assert OFFER_CLASSIFIER.classify("RESTART - Request Testimonial") == AccountActivity.ACTIVE
        assert OFFER_CLASSIFIER.classify("RESTART - Pending Leads") == AccountActivity.ACTIVE

    def test_classify_case_insensitive(self) -> None:
        assert OFFER_CLASSIFIER.classify("active") == AccountActivity.ACTIVE
        assert OFFER_CLASSIFIER.classify("ACTIVE") == AccountActivity.ACTIVE
        assert OFFER_CLASSIFIER.classify("Active") == AccountActivity.ACTIVE

    def test_billable_sections(self) -> None:
        billable = OFFER_CLASSIFIER.billable_sections()
        assert "active" in billable
        assert "activating" in billable
        assert len(billable) == 26  # 21 active + 5 activating


# ---------------------------------------------------------------------------
# UNIT_CLASSIFIER
# ---------------------------------------------------------------------------


class TestUnitClassifier:
    """Tests for the UNIT_CLASSIFIER module-level instance."""

    def test_entity_type(self) -> None:
        assert UNIT_CLASSIFIER.entity_type == "unit"

    def test_project_gid(self) -> None:
        assert UNIT_CLASSIFIER.project_gid == "1201081073731555"

    def test_active_sections(self) -> None:
        active = UNIT_CLASSIFIER.active_sections()
        assert "month 1" in active
        assert "consulting" in active
        assert "active" in active
        assert len(active) == 3

    def test_activating_sections(self) -> None:
        activating = UNIT_CLASSIFIER.sections_for(AccountActivity.ACTIVATING)
        assert "onboarding" in activating
        assert "implementing" in activating
        assert "delayed" in activating
        assert "preview" in activating
        assert len(activating) == 4

    def test_inactive_sections(self) -> None:
        inactive = UNIT_CLASSIFIER.sections_for(AccountActivity.INACTIVE)
        assert "unengaged" in inactive
        assert "engaged" in inactive
        assert "scheduled" in inactive
        assert "paused" in inactive
        assert "cancelled" in inactive
        assert "no start" in inactive
        assert len(inactive) == 6

    def test_ignored_sections(self) -> None:
        ignored = UNIT_CLASSIFIER.sections_for(AccountActivity.IGNORED)
        assert "templates" in ignored
        assert len(ignored) == 1

    def test_total_section_count(self) -> None:
        total = (
            len(UNIT_CLASSIFIER.active_sections())
            + len(UNIT_CLASSIFIER.sections_for(AccountActivity.ACTIVATING))
            + len(UNIT_CLASSIFIER.sections_for(AccountActivity.INACTIVE))
            + len(UNIT_CLASSIFIER.sections_for(AccountActivity.IGNORED))
        )
        assert total == 14

    def test_classify_case_insensitive(self) -> None:
        assert UNIT_CLASSIFIER.classify("Month 1") == AccountActivity.ACTIVE
        assert UNIT_CLASSIFIER.classify("month 1") == AccountActivity.ACTIVE
        assert UNIT_CLASSIFIER.classify("MONTH 1") == AccountActivity.ACTIVE

    def test_billable_sections(self) -> None:
        billable = UNIT_CLASSIFIER.billable_sections()
        assert len(billable) == 7  # 3 active + 4 activating


# ---------------------------------------------------------------------------
# CLASSIFIERS Registry & get_classifier
# ---------------------------------------------------------------------------


class TestClassifiersRegistry:
    """Tests for CLASSIFIERS dict and get_classifier()."""

    def test_registry_contains_offer(self) -> None:
        assert "offer" in CLASSIFIERS
        assert CLASSIFIERS["offer"] is OFFER_CLASSIFIER

    def test_registry_contains_unit(self) -> None:
        assert "unit" in CLASSIFIERS
        assert CLASSIFIERS["unit"] is UNIT_CLASSIFIER

    def test_registry_size(self) -> None:
        assert len(CLASSIFIERS) == 2

    def test_get_classifier_offer(self) -> None:
        assert get_classifier("offer") is OFFER_CLASSIFIER

    def test_get_classifier_unit(self) -> None:
        assert get_classifier("unit") is UNIT_CLASSIFIER

    def test_get_classifier_unknown_returns_none(self) -> None:
        assert get_classifier("business") is None
        assert get_classifier("process") is None
        assert get_classifier("") is None
