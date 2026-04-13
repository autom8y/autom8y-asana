"""Tests for query/hierarchy.py: EntityRelationship registry.

Test cases TC-H001 through TC-H009 per TDD-hierarchy-index Section 10.1.
Test cases TC-H010 through TC-H017 per WS1-S3 auto-wire verification.
"""

from __future__ import annotations

from autom8_asana.query.hierarchy import (
    ENTITY_RELATIONSHIPS,
    EntityRelationship,
    _build_relationships_from_registry,
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


# ============================================================================
# WS1-S3: Auto-Wire Verification Tests
# ============================================================================


class TestAutoWiredRelationships:
    """Tests verifying descriptor-driven relationship derivation.

    Per ARCH-descriptor-driven-auto-wiring section 3.4: The derived list is a
    superset of the original 4 hardcoded entries. These tests verify that the
    auto-wired ENTITY_RELATIONSHIPS contains all expected entries and that
    existing helper functions continue to work correctly.
    """

    # The original 4 hardcoded relationships that must still be present.
    ORIGINAL_FOUR = [
        ("business", "unit", "office_phone"),
        ("business", "contact", "office_phone"),
        ("business", "offer", "office_phone"),
        ("unit", "offer", "office_phone"),
    ]

    def test_tc_h010_derived_is_superset_of_original_four(self) -> None:
        """TC-H010: Derived relationships contain all original 4 entries."""
        derived_tuples = {
            (r.parent_type, r.child_type, r.default_join_key) for r in ENTITY_RELATIONSHIPS
        }
        for parent, child, key in self.ORIGINAL_FOUR:
            assert (parent, child, key) in derived_tuples, (
                f"Missing original relationship: {parent} -> {child} via {key}"
            )

    def test_tc_h011_derived_has_more_than_four(self) -> None:
        """TC-H011: Derived list is a proper superset (more than 4 entries)."""
        assert len(ENTITY_RELATIONSHIPS) > 4, (
            f"Expected >4 relationships from bidirectional join_keys, "
            f"got {len(ENTITY_RELATIONSHIPS)}"
        )

    def test_tc_h012_all_relationships_have_valid_structure(self) -> None:
        """TC-H012: Every derived relationship is a proper EntityRelationship."""
        for rel in ENTITY_RELATIONSHIPS:
            assert isinstance(rel, EntityRelationship)
            assert isinstance(rel.parent_type, str) and rel.parent_type
            assert isinstance(rel.child_type, str) and rel.child_type
            assert isinstance(rel.default_join_key, str) and rel.default_join_key
            assert isinstance(rel.description, str) and rel.description

    def test_tc_h013_descriptions_indicate_auto_derived(self) -> None:
        """TC-H013: All derived relationship descriptions start with 'Auto-derived:'."""
        for rel in ENTITY_RELATIONSHIPS:
            assert rel.description.startswith("Auto-derived:"), (
                f"Relationship {rel.parent_type}->{rel.child_type} "
                f"has non-auto description: {rel.description!r}"
            )

    def test_tc_h014_build_function_is_deterministic(self) -> None:
        """TC-H014: _build_relationships_from_registry() returns same result each call."""
        result1 = _build_relationships_from_registry()
        result2 = _build_relationships_from_registry()
        assert len(result1) == len(result2)
        for r1, r2 in zip(result1, result2):
            assert r1.parent_type == r2.parent_type
            assert r1.child_type == r2.child_type
            assert r1.default_join_key == r2.default_join_key


class TestAutoWiredFindRelationship:
    """Verify find_relationship works for all known entity pairs after auto-wire."""

    def test_tc_h015_find_all_original_pairs(self) -> None:
        """TC-H015: find_relationship returns non-None for all original pairs."""
        pairs = [
            ("business", "unit"),
            ("business", "contact"),
            ("business", "offer"),
            ("unit", "offer"),
        ]
        for source, target in pairs:
            rel = find_relationship(source, target)
            assert rel is not None, f"find_relationship({source!r}, {target!r}) is None"
            assert rel.default_join_key == "office_phone"

    def test_tc_h016_find_bidirectional_for_new_entries(self) -> None:
        """TC-H016: Bidirectional find works for newly derived entries."""
        # unit -> business is a new entry (unit declares join_key to business)
        rel = find_relationship("unit", "business")
        assert rel is not None
        assert rel.default_join_key == "office_phone"

        # contact -> business (contact declares join_key to business)
        rel = find_relationship("contact", "business")
        assert rel is not None
        assert rel.default_join_key == "office_phone"

    def test_tc_h017_no_false_positives(self) -> None:
        """TC-H017: Entities without join_keys still return None."""
        # asset_edit has no join_keys, process has no join_keys
        assert find_relationship("asset_edit", "business") is None
        assert find_relationship("process", "business") is None
        assert find_relationship("hours", "unit") is None
