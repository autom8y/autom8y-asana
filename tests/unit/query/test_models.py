"""Tests for query/models.py: PredicateNode parsing, sugar, depth, validation."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from autom8_asana.query.models import (
    AggFunction,
    AggregateMeta,
    AggregateRequest,
    AggSpec,
    AndGroup,
    Comparison,
    NotGroup,
    Op,
    OrGroup,
    PredicateNode,
    RowsMeta,
    RowsRequest,
)

# TypeAdapter for raw dict -> PredicateNode validation
_predicate_adapter = TypeAdapter(PredicateNode)


class TestComparisonParsing:
    """Test Comparison leaf node parsing."""

    def test_eq_comparison(self) -> None:
        node = _predicate_adapter.validate_python(
            {"field": "name", "op": "eq", "value": "Acme"}
        )
        assert isinstance(node, Comparison)
        assert node.field == "name"
        assert node.op == Op.EQ
        assert node.value == "Acme"

    def test_all_operators(self) -> None:
        for op in Op:
            node = _predicate_adapter.validate_python(
                {"field": "x", "op": op.value, "value": "v"}
            )
            assert isinstance(node, Comparison)
            assert node.op == op

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _predicate_adapter.validate_python(
                {"field": "name", "op": "eq", "value": "x", "extra": True}
            )


class TestAndGroupParsing:
    """Test AND group node parsing."""

    def test_and_with_children(self) -> None:
        node = _predicate_adapter.validate_python(
            {
                "and": [
                    {"field": "a", "op": "eq", "value": 1},
                    {"field": "b", "op": "ne", "value": 2},
                ]
            }
        )
        assert isinstance(node, AndGroup)
        assert len(node.and_) == 2
        assert isinstance(node.and_[0], Comparison)
        assert isinstance(node.and_[1], Comparison)

    def test_and_empty_list(self) -> None:
        node = _predicate_adapter.validate_python({"and": []})
        assert isinstance(node, AndGroup)
        assert len(node.and_) == 0

    def test_and_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _predicate_adapter.validate_python({"and": [], "extra": True})


class TestOrGroupParsing:
    """Test OR group node parsing."""

    def test_or_with_children(self) -> None:
        node = _predicate_adapter.validate_python(
            {
                "or": [
                    {"field": "a", "op": "eq", "value": 1},
                    {"field": "b", "op": "eq", "value": 2},
                ]
            }
        )
        assert isinstance(node, OrGroup)
        assert len(node.or_) == 2

    def test_or_empty_list(self) -> None:
        node = _predicate_adapter.validate_python({"or": []})
        assert isinstance(node, OrGroup)


class TestNotGroupParsing:
    """Test NOT group node parsing."""

    def test_not_with_child(self) -> None:
        node = _predicate_adapter.validate_python(
            {"not": {"field": "active", "op": "eq", "value": True}}
        )
        assert isinstance(node, NotGroup)
        assert isinstance(node.not_, Comparison)


class TestNestedParsing:
    """Test deeply nested predicate trees."""

    def test_nested_and_or(self) -> None:
        node = _predicate_adapter.validate_python(
            {
                "and": [
                    {
                        "or": [
                            {"field": "a", "op": "eq", "value": 1},
                            {"field": "b", "op": "eq", "value": 2},
                        ]
                    },
                    {"field": "c", "op": "ne", "value": 3},
                ]
            }
        )
        assert isinstance(node, AndGroup)
        assert isinstance(node.and_[0], OrGroup)
        assert isinstance(node.and_[1], Comparison)

    def test_not_wrapping_and(self) -> None:
        node = _predicate_adapter.validate_python(
            {
                "not": {
                    "and": [
                        {"field": "x", "op": "eq", "value": 1},
                        {"field": "y", "op": "eq", "value": 2},
                    ]
                }
            }
        )
        assert isinstance(node, NotGroup)
        assert isinstance(node.not_, AndGroup)


class TestRowsRequestSugar:
    """Test RowsRequest flat-array sugar and validation."""

    def test_flat_array_wraps_to_and(self) -> None:
        req = RowsRequest.model_validate(
            {
                "where": [
                    {"field": "a", "op": "eq", "value": 1},
                    {"field": "b", "op": "eq", "value": 2},
                ]
            }
        )
        assert isinstance(req.where, AndGroup)
        assert len(req.where.and_) == 2

    def test_empty_array_becomes_none(self) -> None:
        req = RowsRequest.model_validate({"where": []})
        assert req.where is None

    def test_dict_passthrough(self) -> None:
        req = RowsRequest.model_validate(
            {"where": {"field": "a", "op": "eq", "value": 1}}
        )
        assert isinstance(req.where, Comparison)

    def test_none_where(self) -> None:
        req = RowsRequest.model_validate({"where": None})
        assert req.where is None

    def test_no_where(self) -> None:
        req = RowsRequest.model_validate({})
        assert req.where is None

    def test_defaults(self) -> None:
        req = RowsRequest.model_validate({})
        assert req.limit == 100
        assert req.offset == 0
        assert req.section is None
        assert req.select is None
        assert req.order_by is None
        assert req.order_dir == "asc"

    def test_limit_bounds(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": 0})
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"limit": 1001})

    def test_offset_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"offset": -1})

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RowsRequest.model_validate({"bogus": True})


# ---------------------------------------------------------------------------
# AggSpec model validation (TC-AS001 through TC-AS004)
# ---------------------------------------------------------------------------


class TestAggSpec:
    """Test AggSpec model validation."""

    def test_tc_as001_valid_with_alias(self) -> None:
        """TC-AS001: Valid AggSpec with alias parses successfully."""
        spec = AggSpec(column="amount", agg=AggFunction.SUM, alias="total_amount")
        assert spec.column == "amount"
        assert spec.agg == AggFunction.SUM
        assert spec.alias == "total_amount"
        assert spec.resolved_alias == "total_amount"

    def test_tc_as002_default_alias(self) -> None:
        """TC-AS002: Valid AggSpec without alias uses default resolved_alias."""
        spec = AggSpec(column="amount", agg=AggFunction.SUM)
        assert spec.alias is None
        assert spec.resolved_alias == "sum_amount"

    def test_tc_as003_invalid_agg_function(self) -> None:
        """TC-AS003: AggSpec with invalid agg function raises ValidationError."""
        with pytest.raises(ValidationError):
            AggSpec.model_validate({"column": "amount", "agg": "invalid_agg"})

    def test_tc_as004_extra_fields_rejected(self) -> None:
        """TC-AS004: AggSpec with extra fields rejected."""
        with pytest.raises(ValidationError):
            AggSpec.model_validate(
                {"column": "amount", "agg": "sum", "extra_field": True}
            )

    def test_all_agg_functions(self) -> None:
        """All AggFunction enum values can be used in AggSpec."""
        for func in AggFunction:
            spec = AggSpec(column="x", agg=func)
            assert spec.agg == func

    def test_count_distinct_alias(self) -> None:
        """count_distinct default alias uses the value string."""
        spec = AggSpec(column="name", agg=AggFunction.COUNT_DISTINCT)
        assert spec.resolved_alias == "count_distinct_name"


# ---------------------------------------------------------------------------
# AggregateRequest model validation (TC-AS005 through TC-AS010)
# ---------------------------------------------------------------------------


class TestAggregateRequest:
    """Test AggregateRequest model validation."""

    def test_tc_as005_empty_group_by_rejected(self) -> None:
        """TC-AS005: AggregateRequest with empty group_by raises ValidationError."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": [],
                    "aggregations": [{"column": "x", "agg": "count"}],
                }
            )

    def test_tc_as006_too_many_group_by_rejected(self) -> None:
        """TC-AS006: AggregateRequest with >5 group_by raises ValidationError."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": ["a", "b", "c", "d", "e", "f"],
                    "aggregations": [{"column": "x", "agg": "count"}],
                }
            )

    def test_tc_as007_empty_aggregations_rejected(self) -> None:
        """TC-AS007: AggregateRequest with empty aggregations raises ValidationError."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                    "aggregations": [],
                }
            )

    def test_tc_as008_too_many_aggregations_rejected(self) -> None:
        """TC-AS008: AggregateRequest with >10 aggregations raises ValidationError."""
        aggs = [{"column": f"col_{i}", "agg": "count"} for i in range(11)]
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                    "aggregations": aggs,
                }
            )

    def test_tc_as009_where_flat_array_sugar(self) -> None:
        """TC-AS009: AggregateRequest WHERE flat array sugar wraps to AND group."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
                "where": [
                    {"field": "a", "op": "eq", "value": 1},
                    {"field": "b", "op": "eq", "value": 2},
                ],
            }
        )
        assert isinstance(req.where, AndGroup)
        assert len(req.where.and_) == 2

    def test_tc_as010_having_flat_array_sugar(self) -> None:
        """TC-AS010: AggregateRequest HAVING flat array sugar wraps to AND group."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "cnt"}],
                "having": [
                    {"field": "cnt", "op": "gt", "value": 5},
                ],
            }
        )
        assert isinstance(req.having, AndGroup)
        assert len(req.having.and_) == 1

    def test_valid_minimal_request(self) -> None:
        """Minimal valid AggregateRequest parses successfully."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
            }
        )
        assert req.group_by == ["vertical"]
        assert len(req.aggregations) == 1
        assert req.where is None
        assert req.having is None
        assert req.section is None

    def test_extra_fields_rejected(self) -> None:
        """AggregateRequest with extra fields rejected."""
        with pytest.raises(ValidationError):
            AggregateRequest.model_validate(
                {
                    "group_by": ["vertical"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                    "bogus": True,
                }
            )

    def test_where_empty_array_becomes_none(self) -> None:
        """Empty WHERE array becomes None."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
                "where": [],
            }
        )
        assert req.where is None

    def test_having_empty_array_becomes_none(self) -> None:
        """Empty HAVING array becomes None."""
        req = AggregateRequest.model_validate(
            {
                "group_by": ["vertical"],
                "aggregations": [{"column": "gid", "agg": "count"}],
                "having": [],
            }
        )
        assert req.having is None


class TestResponseModelFreshness:
    """Tests for freshness fields on RowsMeta and AggregateMeta."""

    def test_rows_meta_freshness_fields_optional(self) -> None:
        """RowsMeta with no freshness fields is valid (defaults to None)."""
        meta = RowsMeta(
            total_count=10,
            returned_count=5,
            limit=100,
            offset=0,
            entity_type="unit",
            project_gid="proj-1",
            query_ms=1.5,
        )
        assert meta.freshness is None
        assert meta.data_age_seconds is None
        assert meta.staleness_ratio is None

    def test_rows_meta_freshness_fields_populated(self) -> None:
        """RowsMeta with freshness fields round-trips correctly."""
        meta = RowsMeta(
            total_count=10,
            returned_count=5,
            limit=100,
            offset=0,
            entity_type="unit",
            project_gid="proj-1",
            query_ms=1.5,
            freshness="fresh",
            data_age_seconds=60.0,
            staleness_ratio=0.07,
        )
        assert meta.freshness == "fresh"
        assert meta.data_age_seconds == 60.0
        assert meta.staleness_ratio == 0.07

        # Verify serialization round-trip
        data = meta.model_dump()
        restored = RowsMeta.model_validate(data)
        assert restored.freshness == "fresh"
        assert restored.data_age_seconds == 60.0
        assert restored.staleness_ratio == 0.07

    def test_aggregate_meta_freshness_fields_optional(self) -> None:
        """AggregateMeta with no freshness fields is valid (defaults to None)."""
        meta = AggregateMeta(
            group_count=3,
            aggregation_count=1,
            group_by=["vertical"],
            entity_type="unit",
            project_gid="proj-1",
            query_ms=2.0,
        )
        assert meta.freshness is None
        assert meta.data_age_seconds is None
        assert meta.staleness_ratio is None
