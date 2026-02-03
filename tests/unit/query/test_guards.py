"""Tests for query/guards.py: depth limits and row count clamping.

Test Cases (per TDD Section 11.3):
- TC-G001: Depth 1 (leaf comparison) -- no error
- TC-G002: Depth 2 (one group) -- no error
- TC-G003: Depth 5 (at limit) -- no error
- TC-G004: Depth 6 (exceeds) -- QueryTooComplexError
- TC-G005: Flat array depth treated as group (depth 2)
- TC-G006: None predicate -- depth 0, no error
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter

from autom8_asana.query.errors import QueryTooComplexError
from autom8_asana.query.guards import QueryLimits, predicate_depth
from autom8_asana.query.models import (
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
    PredicateNode,
    RowsRequest,
)

_predicate_adapter = TypeAdapter(PredicateNode)
_leaf = {"field": "name", "op": "eq", "value": "x"}


class TestPredicateDepth:
    """Test predicate_depth() calculation."""

    def test_tc_g001_leaf_depth_1(self) -> None:
        """TC-G001: Single comparison = depth 1."""
        node = _predicate_adapter.validate_python(_leaf)
        assert predicate_depth(node) == 1

    def test_tc_g002_one_group_depth_2(self) -> None:
        """TC-G002: AND group with leaf = depth 2."""
        node = _predicate_adapter.validate_python({"and": [_leaf]})
        assert predicate_depth(node) == 2

    def test_tc_g003_depth_5_at_limit(self) -> None:
        """TC-G003: 5-deep nesting is at the limit, no error."""
        # depth 5: and -> or -> and -> not -> leaf
        nested = {
            "and": [
                {
                    "or": [
                        {
                            "and": [
                                {
                                    "not": _leaf,
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        node = _predicate_adapter.validate_python(nested)
        assert predicate_depth(node) == 5

    def test_tc_g004_depth_6_exceeds(self) -> None:
        """TC-G004: Depth 6 exceeds max of 5, raises QueryTooComplexError."""
        # depth 6: and -> or -> and -> not -> and -> leaf
        nested = {
            "and": [
                {
                    "or": [
                        {
                            "and": [
                                {
                                    "not": {
                                        "and": [_leaf],
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        node = _predicate_adapter.validate_python(nested)
        depth = predicate_depth(node)
        assert depth == 6

        limits = QueryLimits()
        with pytest.raises(QueryTooComplexError) as exc_info:
            limits.check_depth(depth)

        err = exc_info.value
        assert err.depth == 6
        assert err.max_depth == 5
        err_dict = err.to_dict()
        assert err_dict["error"] == "QUERY_TOO_COMPLEX"
        assert "6" in err_dict["message"]
        assert "5" in err_dict["message"]

    def test_tc_g005_flat_array_depth(self) -> None:
        """TC-G005: Flat array sugar wraps in AND -> depth 2."""
        req = RowsRequest.model_validate({"where": [_leaf, _leaf]})
        assert isinstance(req.where, AndGroup)
        assert predicate_depth(req.where) == 2

    def test_empty_and_group_depth_1(self) -> None:
        """Empty AND group = depth 1."""
        node = _predicate_adapter.validate_python({"and": []})
        assert predicate_depth(node) == 1

    def test_not_group_depth(self) -> None:
        """NOT group adds 1 to child depth."""
        node = _predicate_adapter.validate_python({"not": _leaf})
        assert predicate_depth(node) == 2

    def test_or_group_depth(self) -> None:
        """OR group adds 1 to max child depth."""
        node = _predicate_adapter.validate_python({"or": [_leaf, {"and": [_leaf]}]})
        # or(leaf, and(leaf)) -> max(1, 2) + 1 = 3
        assert predicate_depth(node) == 3


class TestQueryLimits:
    """Test QueryLimits class."""

    def test_default_limits(self) -> None:
        limits = QueryLimits()
        assert limits.max_predicate_depth == 5
        assert limits.max_result_rows == 10_000

    def test_check_depth_passes_at_limit(self) -> None:
        """Depth == max_predicate_depth does not raise."""
        limits = QueryLimits()
        limits.check_depth(5)  # Should not raise

    def test_check_depth_passes_below_limit(self) -> None:
        limits = QueryLimits()
        limits.check_depth(1)  # Should not raise

    def test_check_depth_fails_above_limit(self) -> None:
        limits = QueryLimits()
        with pytest.raises(QueryTooComplexError):
            limits.check_depth(6)

    def test_clamp_limit_below_max(self) -> None:
        limits = QueryLimits()
        assert limits.clamp_limit(100) == 100

    def test_clamp_limit_at_max(self) -> None:
        limits = QueryLimits()
        assert limits.clamp_limit(10_000) == 10_000

    def test_clamp_limit_above_max(self) -> None:
        limits = QueryLimits()
        assert limits.clamp_limit(50_000) == 10_000

    def test_custom_limits(self) -> None:
        limits = QueryLimits(max_predicate_depth=3, max_result_rows=500)
        assert limits.max_predicate_depth == 3
        assert limits.max_result_rows == 500
        limits.check_depth(3)  # at limit, ok
        with pytest.raises(QueryTooComplexError):
            limits.check_depth(4)
        assert limits.clamp_limit(1000) == 500
