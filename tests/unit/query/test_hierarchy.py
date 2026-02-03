"""Tests for query/hierarchy.py: EntityRelationship registry.

Test cases TC-H001 through TC-H009 per TDD-hierarchy-index Section 10.1.
"""

from __future__ import annotations

from autom8_asana.query.hierarchy import (
    find_relationship,
    get_join_key,
    get_joinable_types,
)


class TestFindRelationship:
    """Tests for find_relationship()."""

    def test_tc_h001_offer_business(self) -> None:
        """TC-H001: find_relationship('offer', 'business') returns the relationship."""
        rel = find_relationship("offer", "business")
        assert rel is not None
        assert rel.parent_type == "business"
        assert rel.child_type == "offer"
        assert rel.default_join_key == "office_phone"

    def test_tc_h002_business_offer_bidirectional(self) -> None:
        """TC-H002: find_relationship('business', 'offer') returns same relationship."""
        rel = find_relationship("business", "offer")
        assert rel is not None
        assert rel.parent_type == "business"
        assert rel.child_type == "offer"

    def test_tc_h003_offer_contact_no_relationship(self) -> None:
        """TC-H003: find_relationship('offer', 'contact') returns None."""
        rel = find_relationship("offer", "contact")
        assert rel is None


class TestGetJoinKey:
    """Tests for get_join_key()."""

    def test_tc_h004_default_key(self) -> None:
        """TC-H004: get_join_key('offer', 'business') returns 'office_phone'."""
        key = get_join_key("offer", "business")
        assert key == "office_phone"

    def test_tc_h005_explicit_override(self) -> None:
        """TC-H005: get_join_key with explicit key returns the override."""
        key = get_join_key("offer", "business", "name")
        assert key == "name"

    def test_tc_h006_no_relationship(self) -> None:
        """TC-H006: get_join_key('offer', 'contact') returns None."""
        key = get_join_key("offer", "contact")
        assert key is None


class TestGetJoinableTypes:
    """Tests for get_joinable_types()."""

    def test_tc_h007_offer(self) -> None:
        """TC-H007: get_joinable_types('offer') returns ['business', 'unit']."""
        types = get_joinable_types("offer")
        assert types == ["business", "unit"]

    def test_tc_h008_business(self) -> None:
        """TC-H008: get_joinable_types('business') returns ['contact', 'offer', 'unit']."""
        types = get_joinable_types("business")
        assert types == ["contact", "offer", "unit"]

    def test_tc_h009_asset_edit_empty(self) -> None:
        """TC-H009: get_joinable_types('asset_edit') returns []."""
        types = get_joinable_types("asset_edit")
        assert types == []
