"""Unit tests for Scope and Metric dataclasses."""

from __future__ import annotations

import polars as pl
import pytest

from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope


class TestScope:
    """Test Scope dataclass."""

    def test_basic_creation(self) -> None:
        scope = Scope(entity_type="offer")
        assert scope.entity_type == "offer"
        assert scope.section is None
        assert scope.section_name is None
        assert scope.dedup_keys is None
        assert scope.pre_filters is None

    def test_full_creation(self) -> None:
        scope = Scope(
            entity_type="offer",
            section="123",
            dedup_keys=["phone", "vertical"],
            pre_filters=[pl.col("status") == "active"],
        )
        assert scope.section == "123"
        assert scope.dedup_keys == ["phone", "vertical"]
        assert len(scope.pre_filters) == 1

    def test_section_name_field(self) -> None:
        scope = Scope(entity_type="offer", section_name="Active")
        assert scope.section_name == "Active"
        assert scope.section is None

    def test_with_resolved_section(self) -> None:
        scope = Scope(entity_type="offer", section_name="Active")
        resolved = scope.with_resolved_section("123")
        assert resolved.section == "123"
        assert resolved.section_name == "Active"
        # Original unchanged (frozen)
        assert scope.section is None

    def test_classification_field_default_none(self) -> None:
        scope = Scope(entity_type="offer")
        assert scope.classification is None

    def test_classification_field_set(self) -> None:
        scope = Scope(entity_type="offer", classification="active")
        assert scope.classification == "active"

    def test_frozen(self) -> None:
        scope = Scope(entity_type="offer")
        with pytest.raises(AttributeError):
            scope.entity_type = "changed"  # type: ignore[misc]


class TestMetric:
    """Test Metric dataclass."""

    def test_basic_creation(self) -> None:
        expr = MetricExpr(name="sum_val", column="val", agg="sum")
        scope = Scope(entity_type="offer", section="123")
        metric = Metric(
            name="test_metric",
            description="A test metric",
            expr=expr,
            scope=scope,
        )
        assert metric.name == "test_metric"
        assert metric.description == "A test metric"
        assert metric.expr is expr
        assert metric.scope is scope

    def test_frozen(self) -> None:
        expr = MetricExpr(name="sum_val", column="val", agg="sum")
        scope = Scope(entity_type="offer")
        metric = Metric(name="m", description="d", expr=expr, scope=scope)
        with pytest.raises(AttributeError):
            metric.name = "changed"  # type: ignore[misc]
