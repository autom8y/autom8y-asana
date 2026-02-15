"""Unit tests for MetricRegistry."""

from __future__ import annotations

import pytest

from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.registry import MetricRegistry


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    """Reset MetricRegistry singleton before each test."""
    MetricRegistry.reset()
    yield  # type: ignore[misc]
    MetricRegistry.reset()


def _make_metric(name: str, column: str = "val") -> Metric:
    """Create a minimal Metric for testing."""
    return Metric(
        name=name,
        description=f"Test metric: {name}",
        expr=MetricExpr(name=f"sum_{column}", column=column, agg="sum"),
        scope=Scope(entity_type="test"),
    )


class TestSingleton:
    """Test singleton behavior."""

    def test_same_instance(self) -> None:
        r1 = MetricRegistry()
        r2 = MetricRegistry()
        assert r1 is r2

    def test_reset_creates_new_instance(self) -> None:
        r1 = MetricRegistry()
        MetricRegistry.reset()
        r2 = MetricRegistry()
        assert r1 is not r2


class TestRegistration:
    """Test register/get/list operations."""

    def test_register_and_get(self) -> None:
        registry = MetricRegistry()
        metric = _make_metric("test_m")
        registry.register(metric)
        # Mark as initialized to skip definitions import
        registry._initialized = True
        assert registry.get_metric("test_m") is metric

    def test_get_unknown_raises_key_error(self) -> None:
        registry = MetricRegistry()
        registry._initialized = True
        with pytest.raises(KeyError, match="Unknown metric 'nonexistent'"):
            registry.get_metric("nonexistent")

    def test_key_error_includes_available(self) -> None:
        registry = MetricRegistry()
        registry.register(_make_metric("alpha"))
        registry.register(_make_metric("beta"))
        registry._initialized = True
        with pytest.raises(KeyError, match="alpha, beta"):
            registry.get_metric("nonexistent")

    def test_duplicate_same_object_is_idempotent(self) -> None:
        registry = MetricRegistry()
        metric = _make_metric("m")
        registry.register(metric)
        registry.register(metric)  # No error
        registry._initialized = True
        assert registry.get_metric("m") is metric

    def test_duplicate_different_object_raises(self) -> None:
        registry = MetricRegistry()
        registry.register(_make_metric("m"))
        different = _make_metric("m")
        with pytest.raises(ValueError, match="already registered"):
            registry.register(different)

    def test_list_metrics_sorted(self) -> None:
        registry = MetricRegistry()
        registry.register(_make_metric("zebra"))
        registry.register(_make_metric("alpha"))
        registry._initialized = True
        assert registry.list_metrics() == ["alpha", "zebra"]


class TestLazyInitialization:
    """Test lazy loading of definitions."""

    def test_not_initialized_before_access(self) -> None:
        registry = MetricRegistry()
        assert registry._initialized is False

    def test_initialized_after_get_metric(self) -> None:
        registry = MetricRegistry()
        # This triggers _ensure_initialized which imports definitions
        try:
            registry.get_metric("active_mrr")
        except KeyError:
            pass
        assert registry._initialized is True

    def test_definitions_loaded_on_first_access(self) -> None:
        """After initialization, built-in definitions should be available."""
        registry = MetricRegistry()
        names = registry.list_metrics()
        assert "active_mrr" in names
        assert "active_ad_spend" in names
