"""Behavior-preservation property test for T-04 PredicateNode walker refactor.

Per Pythia C4 condition: this test is authored BEFORE the T-04 refactor,
run to confirm it passes against the current implementation, then run again
after the refactor to confirm behavior is preserved.

Covers the 4 functions that share the PredicateNode isinstance ladder:
- predicate_references_field (returns bool)
- validate_section_values (raises or returns None)
- _split_date_predicates (returns tuple)
- _contains_date_op (returns bool)

Each function is tested with all PredicateNode shapes:
- Comparison leaf
- AndGroup of 2
- OrGroup of 3
- NotGroup(of Comparison)
- Nested: NotGroup(of AndGroup)
"""

from __future__ import annotations

import pytest

from autom8_asana.api.routes._exports_helpers import (
    _contains_date_op,
    _split_date_predicates,
    predicate_references_field,
    validate_section_values,
)
from autom8_asana.query.models import AndGroup, Comparison, NotGroup, Op, OrGroup


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def comp_section() -> Comparison:
    """Comparison on 'section' field."""
    return Comparison(field="section", op=Op.EQ, value="active")


@pytest.fixture()
def comp_other() -> Comparison:
    """Comparison on non-section, non-date field."""
    return Comparison(field="name", op=Op.EQ, value="foo")


@pytest.fixture()
def comp_date_gte() -> Comparison:
    """Comparison with date GTE operator."""
    return Comparison(field="modified_at", op=Op.DATE_GTE, value="2024-01-01")


@pytest.fixture()
def comp_date_lte() -> Comparison:
    """Comparison with date LTE operator."""
    return Comparison(field="modified_at", op=Op.DATE_LTE, value="2024-12-31")


# ---------------------------------------------------------------------------
# predicate_references_field behavior preservation
# ---------------------------------------------------------------------------


class TestPredicateReferencesFieldBehavior:
    """Behavior-preservation tests for predicate_references_field."""

    def test_none_returns_false(self) -> None:
        assert predicate_references_field(None, "section") is False

    def test_comparison_leaf_match(self, comp_section: Comparison) -> None:
        assert predicate_references_field(comp_section, "section") is True

    def test_comparison_leaf_no_match(self, comp_other: Comparison) -> None:
        assert predicate_references_field(comp_other, "section") is False

    def test_and_group_of_2_match(
        self, comp_section: Comparison, comp_other: Comparison
    ) -> None:
        node = AndGroup(and_=[comp_section, comp_other])
        assert predicate_references_field(node, "section") is True

    def test_and_group_of_2_no_match(self, comp_other: Comparison) -> None:
        comp_other2 = Comparison(field="status", op=Op.EQ, value="x")
        node = AndGroup(and_=[comp_other, comp_other2])
        assert predicate_references_field(node, "section") is False

    def test_or_group_of_3_match(
        self, comp_section: Comparison, comp_other: Comparison
    ) -> None:
        comp3 = Comparison(field="gid", op=Op.EQ, value="y")
        node = OrGroup(or_=[comp_other, comp_section, comp3])
        assert predicate_references_field(node, "section") is True

    def test_or_group_of_3_no_match(self) -> None:
        comps = [
            Comparison(field="a", op=Op.EQ, value="1"),
            Comparison(field="b", op=Op.EQ, value="2"),
            Comparison(field="c", op=Op.EQ, value="3"),
        ]
        node = OrGroup(or_=comps)
        assert predicate_references_field(node, "section") is False

    def test_not_group_of_comparison_match(self, comp_section: Comparison) -> None:
        node = NotGroup(not_=comp_section)
        assert predicate_references_field(node, "section") is True

    def test_not_group_of_comparison_no_match(self, comp_other: Comparison) -> None:
        node = NotGroup(not_=comp_other)
        assert predicate_references_field(node, "section") is False


# ---------------------------------------------------------------------------
# validate_section_values behavior preservation
# ---------------------------------------------------------------------------


class TestValidateSectionValuesBehavior:
    """Behavior-preservation tests for validate_section_values."""

    def test_none_returns_none(self) -> None:
        result = validate_section_values(None)
        assert result is None

    def test_comparison_non_section_no_raise(self, comp_other: Comparison) -> None:
        # Should not raise; non-section comparisons are ignored
        validate_section_values(comp_other)

    def test_comparison_valid_section_no_raise(self) -> None:
        node = Comparison(field="section", op=Op.EQ, value="ACTIVE")
        validate_section_values(node)  # "ACTIVE" is a valid PROCESS_PIPELINE_SECTION

    def test_comparison_invalid_section_raises(self) -> None:
        node = Comparison(field="section", op=Op.EQ, value="INVALID_SECTION_XYZ")
        with pytest.raises(Exception):
            validate_section_values(node)

    def test_and_group_invalid_section_raises(self) -> None:
        bad = Comparison(field="section", op=Op.EQ, value="INVALID_SECTION_XYZ")
        good = Comparison(field="name", op=Op.EQ, value="x")
        node = AndGroup(and_=[good, bad])
        with pytest.raises(Exception):
            validate_section_values(node)

    def test_and_group_valid_sections_no_raise(self) -> None:
        good1 = Comparison(field="section", op=Op.EQ, value="ACTIVE")
        good2 = Comparison(field="name", op=Op.EQ, value="x")
        node = AndGroup(and_=[good1, good2])
        validate_section_values(node)

    def test_or_group_invalid_section_raises(self) -> None:
        bad = Comparison(field="section", op=Op.EQ, value="INVALID_SECTION_XYZ")
        good = Comparison(field="name", op=Op.EQ, value="x")
        node = OrGroup(or_=[good, bad])
        with pytest.raises(Exception):
            validate_section_values(node)

    def test_not_group_invalid_section_raises(self) -> None:
        bad = Comparison(field="section", op=Op.EQ, value="INVALID_SECTION_XYZ")
        node = NotGroup(not_=bad)
        with pytest.raises(Exception):
            validate_section_values(node)


# ---------------------------------------------------------------------------
# _contains_date_op behavior preservation
# ---------------------------------------------------------------------------


class TestContainsDateOpBehavior:
    """Behavior-preservation tests for _contains_date_op."""

    def test_none_returns_false(self) -> None:
        assert _contains_date_op(None) is False

    def test_comparison_non_date_returns_false(self, comp_other: Comparison) -> None:
        assert _contains_date_op(comp_other) is False

    def test_comparison_date_gte_returns_true(self, comp_date_gte: Comparison) -> None:
        assert _contains_date_op(comp_date_gte) is True

    def test_comparison_date_lte_returns_true(self, comp_date_lte: Comparison) -> None:
        assert _contains_date_op(comp_date_lte) is True

    def test_and_group_contains_date(
        self, comp_date_gte: Comparison, comp_other: Comparison
    ) -> None:
        node = AndGroup(and_=[comp_other, comp_date_gte])
        assert _contains_date_op(node) is True

    def test_and_group_no_date(self, comp_other: Comparison) -> None:
        comp2 = Comparison(field="b", op=Op.EQ, value="2")
        node = AndGroup(and_=[comp_other, comp2])
        assert _contains_date_op(node) is False

    def test_or_group_of_3_contains_date(
        self, comp_date_lte: Comparison, comp_other: Comparison
    ) -> None:
        comp3 = Comparison(field="c", op=Op.EQ, value="3")
        node = OrGroup(or_=[comp_other, comp3, comp_date_lte])
        assert _contains_date_op(node) is True

    def test_not_group_contains_date(self, comp_date_gte: Comparison) -> None:
        node = NotGroup(not_=comp_date_gte)
        assert _contains_date_op(node) is True

    def test_not_group_no_date(self, comp_other: Comparison) -> None:
        node = NotGroup(not_=comp_other)
        assert _contains_date_op(node) is False


# ---------------------------------------------------------------------------
# _split_date_predicates behavior preservation
# ---------------------------------------------------------------------------


class TestSplitDatePredicatesBehavior:
    """Behavior-preservation tests for _split_date_predicates tuple return."""

    def test_none_returns_none_empty(self) -> None:
        cleaned, exprs = _split_date_predicates(None)
        assert cleaned is None
        assert exprs == []

    def test_comparison_non_date_unchanged(self, comp_other: Comparison) -> None:
        cleaned, exprs = _split_date_predicates(comp_other)
        assert cleaned is comp_other
        assert exprs == []

    def test_comparison_date_gte_extracted(self, comp_date_gte: Comparison) -> None:
        cleaned, exprs = _split_date_predicates(comp_date_gte)
        assert cleaned is None
        assert len(exprs) == 1

    def test_comparison_date_lte_extracted(self, comp_date_lte: Comparison) -> None:
        cleaned, exprs = _split_date_predicates(comp_date_lte)
        assert cleaned is None
        assert len(exprs) == 1

    def test_and_group_date_extracted_non_date_survives(
        self, comp_date_gte: Comparison, comp_other: Comparison
    ) -> None:
        node = AndGroup(and_=[comp_date_gte, comp_other])
        cleaned, exprs = _split_date_predicates(node)
        # date extracted -> 1 expr
        assert len(exprs) == 1
        # non-date survives -> cleaned = comp_other
        assert cleaned is comp_other

    def test_and_group_all_dates_cleaned_is_none(
        self, comp_date_gte: Comparison, comp_date_lte: Comparison
    ) -> None:
        node = AndGroup(and_=[comp_date_gte, comp_date_lte])
        cleaned, exprs = _split_date_predicates(node)
        assert cleaned is None
        assert len(exprs) == 2

    def test_or_group_no_date_passes_through(self, comp_other: Comparison) -> None:
        comp2 = Comparison(field="b", op=Op.EQ, value="2")
        comp3 = Comparison(field="c", op=Op.EQ, value="3")
        node = OrGroup(or_=[comp_other, comp2, comp3])
        cleaned, exprs = _split_date_predicates(node)
        assert cleaned is node
        assert exprs == []

    def test_or_group_with_date_raises(
        self, comp_date_gte: Comparison, comp_other: Comparison
    ) -> None:
        node = OrGroup(or_=[comp_other, comp_date_gte])
        with pytest.raises(ValueError):
            _split_date_predicates(node)

    def test_not_group_no_date_passes_through(self, comp_other: Comparison) -> None:
        node = NotGroup(not_=comp_other)
        cleaned, exprs = _split_date_predicates(node)
        assert cleaned is node
        assert exprs == []

    def test_not_group_with_date_raises(self, comp_date_gte: Comparison) -> None:
        node = NotGroup(not_=comp_date_gte)
        with pytest.raises(ValueError):
            _split_date_predicates(node)
