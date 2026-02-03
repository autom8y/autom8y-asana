"""Unit tests for section name resolution."""

from __future__ import annotations

from dataclasses import replace

import pytest

from autom8_asana.metrics.expr import MetricExpr
from autom8_asana.metrics.metric import Metric, Scope
from autom8_asana.metrics.resolve import SectionIndex, resolve_metric_scope


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_metric(
    *,
    section: str | None = None,
    section_name: str | None = None,
) -> Metric:
    return Metric(
        name="test",
        description="test metric",
        expr=MetricExpr(name="sum_val", column="val", agg="sum"),
        scope=Scope(
            entity_type="offer",
            section=section,
            section_name=section_name,
        ),
    )


# ---------------------------------------------------------------------------
# SectionIndex
# ---------------------------------------------------------------------------


class TestSectionIndex:
    def test_case_insensitive(self) -> None:
        index = SectionIndex(_name_to_gid={"active": "123"})
        assert index.resolve("active") == "123"
        assert index.resolve("ACTIVE") == "123"
        assert index.resolve("Active") == "123"

    def test_not_found(self) -> None:
        index = SectionIndex(_name_to_gid={"active": "123"})
        assert index.resolve("paused") is None

    def test_from_enum_fallback_offer(self) -> None:
        index = SectionIndex.from_enum_fallback("offer")
        assert index.resolve("active") == "1143843662099256"

    def test_from_enum_fallback_unknown(self) -> None:
        index = SectionIndex.from_enum_fallback("unknown_type")
        assert index.resolve("active") is None


# ---------------------------------------------------------------------------
# resolve_metric_scope
# ---------------------------------------------------------------------------


class TestResolveMetricScope:
    def test_already_resolved(self) -> None:
        metric = _make_metric(section="999", section_name="Active")
        index = SectionIndex(_name_to_gid={"active": "123"})
        resolved = resolve_metric_scope(metric, index)
        assert resolved.scope.section == "999"  # GID wins

    def test_name_only(self) -> None:
        metric = _make_metric(section_name="Active")
        index = SectionIndex(_name_to_gid={"active": "123"})
        resolved = resolve_metric_scope(metric, index)
        assert resolved.scope.section == "123"

    def test_both_set_gid_wins(self) -> None:
        metric = _make_metric(section="original", section_name="Active")
        index = SectionIndex(_name_to_gid={"active": "different"})
        resolved = resolve_metric_scope(metric, index)
        assert resolved.scope.section == "original"

    def test_unknown_raises(self) -> None:
        metric = _make_metric(section_name="Nonexistent")
        index = SectionIndex(_name_to_gid={"active": "123"})
        with pytest.raises(ValueError, match="Cannot resolve section name"):
            resolve_metric_scope(metric, index)

    def test_no_section_no_name_passthrough(self) -> None:
        metric = _make_metric()
        index = SectionIndex(_name_to_gid={"active": "123"})
        resolved = resolve_metric_scope(metric, index)
        assert resolved.scope.section is None
