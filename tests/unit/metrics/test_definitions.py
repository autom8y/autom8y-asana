"""Unit tests for metric definitions (offer.py)."""

from __future__ import annotations

import pytest
import polars as pl

from autom8_asana.metrics.registry import MetricRegistry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset MetricRegistry singleton before each test."""
    MetricRegistry.reset()
    yield  # type: ignore[misc]
    MetricRegistry.reset()


class TestOfferDefinitions:
    """Test that offer metric definitions are correct and registered."""

    def test_active_mrr_definition(self) -> None:
        registry = MetricRegistry()
        metric = registry.get_metric("active_mrr")
        assert metric.name == "active_mrr"
        assert metric.expr.column == "mrr"
        assert metric.expr.cast_dtype == pl.Float64
        assert metric.expr.agg == "sum"
        assert metric.scope.entity_type == "offer"
        assert metric.scope.section == "1143843662099256"
        assert metric.scope.section_name == "Active"
        assert metric.scope.dedup_keys == ["office_phone", "vertical"]

    def test_active_ad_spend_definition(self) -> None:
        registry = MetricRegistry()
        metric = registry.get_metric("active_ad_spend")
        assert metric.name == "active_ad_spend"
        assert metric.expr.column == "weekly_ad_spend"
        assert metric.expr.cast_dtype == pl.Float64
        assert metric.expr.agg == "sum"
        assert metric.scope.entity_type == "offer"
        assert metric.scope.section == "1143843662099256"
        assert metric.scope.dedup_keys == ["office_phone", "vertical"]

    def test_definitions_registered(self) -> None:
        registry = MetricRegistry()
        names = registry.list_metrics()
        assert "active_mrr" in names
        assert "active_ad_spend" in names

    def test_shared_scope(self) -> None:
        """Both offer metrics share the same Scope instance."""
        registry = MetricRegistry()
        mrr = registry.get_metric("active_mrr")
        ad_spend = registry.get_metric("active_ad_spend")
        assert mrr.scope is ad_spend.scope
