"""Unit tests for Scope and Metric dataclasses."""

from __future__ import annotations

import pytest
import polars as pl

from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope


class TestScope:
    """Test Scope dataclass."""

    def test_basic_creation(self) -> None:
        scope = Scope(entity_type="offer")
        assert scope.entity_type == "offer"
        assert scope.section is None
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
