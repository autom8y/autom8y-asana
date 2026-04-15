"""Unit tests for CascadeNotReadyError enforcement (Sprint 1).

Per TDD sprint-1-cascade-not-ready-tdd.md test scenarios 1-11:
- CascadeNotReadyError attributes and serialization
- SERVICE_ERROR_MAP registration
- check_cascade_health() pure function behavior
- _check_cascade_health() gate integration in UniversalResolutionStrategy
- Index cache hit bypass behavior
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.builders.cascade_validator import (
    CASCADE_NULL_ERROR_THRESHOLD,
    CascadeHealthResult,
    check_cascade_health,
)
from autom8_asana.services.dynamic_index import DynamicIndexCache
from autom8_asana.services.errors import (
    CascadeNotReadyError,
    ServiceError,
    get_status_for_error,
)
from autom8_asana.services.universal_strategy import UniversalResolutionStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_schema(cascade_columns: list[tuple[str, str]]) -> MagicMock:
    """Create a mock DataFrameSchema with given cascade columns."""
    schema = MagicMock()
    schema.get_cascade_columns.return_value = cascade_columns
    return schema


def _make_descriptor(key_columns: tuple[str, ...] = ()) -> MagicMock:
    """Create a mock EntityDescriptor."""
    desc = MagicMock()
    desc.key_columns = key_columns
    return desc


# ---------------------------------------------------------------------------
# Test Scenario 1: CascadeNotReadyError attributes
# ---------------------------------------------------------------------------


class TestCascadeNotReadyErrorAttributes:
    """Verify error_code, status_hint, to_dict(), message formatting."""

    def test_inherits_from_service_error(self) -> None:
        err = CascadeNotReadyError(
            entity_type="unit",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.25},
            max_null_rate=0.25,
        )
        assert isinstance(err, ServiceError)

    def test_error_code(self) -> None:
        err = CascadeNotReadyError(
            entity_type="unit",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.25},
            max_null_rate=0.25,
        )
        assert err.error_code == "CASCADE_NOT_READY"

    def test_status_hint(self) -> None:
        err = CascadeNotReadyError(
            entity_type="unit",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.25},
            max_null_rate=0.25,
        )
        assert err.status_hint == 503

    def test_message_formatting(self) -> None:
        err = CascadeNotReadyError(
            entity_type="unit",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.253},
            max_null_rate=0.253,
        )
        assert "unit" in err.message
        assert "office_phone" in err.message
        assert "25.3%" in err.message
        assert "20% null threshold" in err.message

    def test_to_dict(self) -> None:
        err = CascadeNotReadyError(
            entity_type="unit",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.253},
            max_null_rate=0.253,
        )
        d = err.to_dict()
        assert d["error"] == "CASCADE_NOT_READY"
        assert d["entity_type"] == "unit"
        assert d["degraded_columns"] == {"office_phone": 0.253}
        assert "message" in d

    def test_to_dict_multiple_columns(self) -> None:
        err = CascadeNotReadyError(
            entity_type="offer",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.30, "vertical": 0.45},
            max_null_rate=0.45,
        )
        d = err.to_dict()
        assert d["degraded_columns"] == {"office_phone": 0.30, "vertical": 0.45}

    def test_attributes_stored(self) -> None:
        err = CascadeNotReadyError(
            entity_type="unit",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.25},
            max_null_rate=0.25,
        )
        assert err.entity_type == "unit"
        assert err.project_gid == "proj-1"
        assert err.degraded_columns == {"office_phone": 0.25}
        assert err.max_null_rate == 0.25


# ---------------------------------------------------------------------------
# Test Scenario 2: SERVICE_ERROR_MAP registration
# ---------------------------------------------------------------------------


class TestServiceErrorMapRegistration:
    """get_status_for_error(CascadeNotReadyError(...)) returns 503."""

    def test_get_status_returns_503(self) -> None:
        err = CascadeNotReadyError(
            entity_type="unit",
            project_gid="proj-1",
            degraded_columns={"office_phone": 0.25},
            max_null_rate=0.25,
        )
        assert get_status_for_error(err) == 503


# ---------------------------------------------------------------------------
# Test Scenario 3: check_cascade_health -- healthy DataFrame
# ---------------------------------------------------------------------------


class TestCheckCascadeHealthHealthy:
    """All cascade key columns below threshold returns healthy."""

    def test_all_below_threshold(self) -> None:
        df = pl.DataFrame(
            {
                "gid": [f"g{i}" for i in range(100)],
                "office_phone": ["+1555000" + str(i).zfill(4) for i in range(100)],
                "vertical": ["dental"] * 100,
            }
        )
        schema = _make_schema([("office_phone", "Office Phone")])
        result = check_cascade_health(
            df=df,
            entity_type="unit",
            schema=schema,
            key_columns=("office_phone", "vertical"),
        )
        assert result.healthy is True
        assert result.degraded_columns == {}

    def test_null_rate_at_threshold_boundary_passes(self) -> None:
        """Exactly 20% null rate should pass (threshold is > not >=)."""
        total = 100
        null_count = 20  # exactly 20%
        phones = [None] * null_count + [
            "+1555" + str(i).zfill(7) for i in range(total - null_count)
        ]
        df = pl.DataFrame(
            {
                "gid": [f"g{i}" for i in range(total)],
                "office_phone": phones,
                "vertical": ["dental"] * total,
            }
        )
        schema = _make_schema([("office_phone", "Office Phone")])
        result = check_cascade_health(
            df=df,
            entity_type="unit",
            schema=schema,
            key_columns=("office_phone", "vertical"),
        )
        assert result.healthy is True
        assert result.degraded_columns == {}


# ---------------------------------------------------------------------------
# Test Scenario 4: check_cascade_health -- single degraded column
# ---------------------------------------------------------------------------


class TestCheckCascadeHealthSingleDegraded:
    """One cascade key column above 20% null rate returns unhealthy."""

    def test_single_column_above_threshold(self) -> None:
        total = 100
        null_count = 25  # 25% > 20%
        phones = [None] * null_count + [
            "+1555" + str(i).zfill(7) for i in range(total - null_count)
        ]
        df = pl.DataFrame(
            {
                "gid": [f"g{i}" for i in range(total)],
                "office_phone": phones,
                "vertical": ["dental"] * total,
            }
        )
        schema = _make_schema([("office_phone", "Office Phone")])
        result = check_cascade_health(
            df=df,
            entity_type="unit",
            schema=schema,
            key_columns=("office_phone", "vertical"),
        )
        assert result.healthy is False
        assert "office_phone" in result.degraded_columns
        assert result.degraded_columns["office_phone"] == pytest.approx(0.25)
        assert result.max_null_rate == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# Test Scenario 5: check_cascade_health -- multiple degraded columns
# ---------------------------------------------------------------------------


class TestCheckCascadeHealthMultipleDegraded:
    """Multiple columns above threshold, max_null_rate reflects worst."""

    def test_two_degraded_columns(self) -> None:
        total = 100
        # office_phone: 25% null, vertical: 40% null
        phones = [None] * 25 + ["+1555" + str(i).zfill(7) for i in range(75)]
        verticals = [None] * 40 + ["dental"] * 60
        df = pl.DataFrame(
            {
                "gid": [f"g{i}" for i in range(total)],
                "office_phone": phones,
                "vertical": verticals,
            }
        )
        schema = _make_schema(
            [
                ("office_phone", "Office Phone"),
                ("vertical", "Vertical"),
            ]
        )
        result = check_cascade_health(
            df=df,
            entity_type="offer",
            schema=schema,
            key_columns=("office_phone", "vertical", "offer_id"),
        )
        assert result.healthy is False
        assert len(result.degraded_columns) == 2
        assert result.max_null_rate == pytest.approx(0.40)


# ---------------------------------------------------------------------------
# Test Scenario 6: check_cascade_health -- non-cascade key columns ignored
# ---------------------------------------------------------------------------


class TestCheckCascadeHealthNonCascadeIgnored:
    """Key columns that are not cascade-sourced do not participate."""

    def test_non_cascade_key_column_ignored(self) -> None:
        total = 100
        # offer_id has 50% nulls -- but it is NOT cascade-sourced
        # office_phone is cascade-sourced and healthy
        df = pl.DataFrame(
            {
                "gid": [f"g{i}" for i in range(total)],
                "office_phone": ["+1555" + str(i).zfill(7) for i in range(total)],
                "vertical": ["dental"] * total,
                "offer_id": [None] * 50 + ["OID" + str(i) for i in range(50)],
            }
        )
        # Only office_phone is cascade-sourced
        schema = _make_schema([("office_phone", "Office Phone")])
        result = check_cascade_health(
            df=df,
            entity_type="offer",
            schema=schema,
            key_columns=("office_phone", "vertical", "offer_id"),
        )
        assert result.healthy is True


# ---------------------------------------------------------------------------
# Test Scenario 7: check_cascade_health -- empty DataFrame
# ---------------------------------------------------------------------------


class TestCheckCascadeHealthEmptyDataFrame:
    """Empty DataFrame returns healthy (safe degradation)."""

    def test_empty_df_returns_healthy(self) -> None:
        df = pl.DataFrame(
            {
                "gid": [],
                "office_phone": [],
                "vertical": [],
            },
            schema={
                "gid": pl.Utf8,
                "office_phone": pl.Utf8,
                "vertical": pl.Utf8,
            },
        )
        schema = _make_schema([("office_phone", "Office Phone")])
        result = check_cascade_health(
            df=df,
            entity_type="unit",
            schema=schema,
            key_columns=("office_phone", "vertical"),
        )
        assert result.healthy is True
        assert result.max_null_rate == 0.0


# ---------------------------------------------------------------------------
# Test Scenario 8: check_cascade_health -- no cascade columns in schema
# ---------------------------------------------------------------------------


class TestCheckCascadeHealthNoCascadeColumns:
    """Entity with no cascade dependencies returns healthy."""

    def test_no_cascade_columns(self) -> None:
        df = pl.DataFrame(
            {
                "gid": ["g1", "g2"],
                "office_phone": ["+15551234567", None],
            }
        )
        # Schema returns no cascade columns (e.g., business entity)
        schema = _make_schema([])
        result = check_cascade_health(
            df=df,
            entity_type="business",
            schema=schema,
            key_columns=("office_phone",),
        )
        assert result.healthy is True
        assert result.degraded_columns == {}


# ---------------------------------------------------------------------------
# Test Scenario 9: _check_cascade_health skip path
# ---------------------------------------------------------------------------


class TestCheckCascadeHealthGateSkipPath:
    """Entity without key_columns or without schema silently passes."""

    def test_no_descriptor_silently_passes(self) -> None:
        strategy = UniversalResolutionStrategy(
            entity_type="nonexistent_entity",
            index_cache=DynamicIndexCache(),
        )
        df = pl.DataFrame({"gid": ["g1"]})
        # Should not raise -- registry returns None for unknown entity
        with patch("autom8_asana.services.universal_strategy._get_entity_registry") as mock_reg:
            mock_reg.return_value.get.return_value = None
            strategy._check_cascade_health(df, "proj-1")

    def test_empty_key_columns_silently_passes(self) -> None:
        strategy = UniversalResolutionStrategy(
            entity_type="some_entity",
            index_cache=DynamicIndexCache(),
        )
        df = pl.DataFrame({"gid": ["g1"]})
        desc = _make_descriptor(key_columns=())
        with patch("autom8_asana.services.universal_strategy._get_entity_registry") as mock_reg:
            mock_reg.return_value.get.return_value = desc
            strategy._check_cascade_health(df, "proj-1")

    def test_no_schema_silently_passes(self) -> None:
        strategy = UniversalResolutionStrategy(
            entity_type="some_entity",
            index_cache=DynamicIndexCache(),
        )
        df = pl.DataFrame({"gid": ["g1"]})
        desc = _make_descriptor(key_columns=("office_phone",))
        with (
            patch("autom8_asana.services.universal_strategy._get_entity_registry") as mock_reg,
            patch.object(strategy, "_get_entity_schema", return_value=None),
        ):
            mock_reg.return_value.get.return_value = desc
            strategy._check_cascade_health(df, "proj-1")


# ---------------------------------------------------------------------------
# Test Scenario 10: _resolve_group raises on degraded cascade
# ---------------------------------------------------------------------------


class TestResolveGroupCascadeNotReady:
    """CascadeNotReadyError propagates from _get_or_build_index through _resolve_group."""

    async def test_cascade_not_ready_propagates(self) -> None:
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        total = 100
        null_count = 30  # 30% > 20%
        phones = [None] * null_count + [
            "+1555" + str(i).zfill(7) for i in range(total - null_count)
        ]
        degraded_df = pl.DataFrame(
            {
                "gid": [f"g{i}" for i in range(total)],
                "office_phone": phones,
                "vertical": ["dental"] * total,
                "name": [f"Unit {i}" for i in range(total)],
            }
        )

        # Mock _get_dataframe to return degraded DataFrame
        strategy._get_dataframe = AsyncMock(return_value=degraded_df)

        desc = _make_descriptor(key_columns=("office_phone", "vertical"))
        schema = _make_schema([("office_phone", "Office Phone")])

        with (
            patch("autom8_asana.services.universal_strategy._get_entity_registry") as mock_reg,
            patch.object(strategy, "_get_entity_schema", return_value=schema),
        ):
            mock_reg.return_value.get.return_value = desc

            with pytest.raises(CascadeNotReadyError) as exc_info:
                await strategy._get_or_build_index(
                    project_gid="proj-1",
                    key_columns=["office_phone", "vertical"],
                    client=MagicMock(),
                )

            err = exc_info.value
            assert err.entity_type == "unit"
            assert err.project_gid == "proj-1"
            assert "office_phone" in err.degraded_columns
            assert err.max_null_rate == pytest.approx(0.30)


# ---------------------------------------------------------------------------
# Test Scenario 11: Index cache hit bypasses health check
# ---------------------------------------------------------------------------


class TestIndexCacheHitBypassesHealthCheck:
    """Health check not called when index is served from cache."""

    async def test_cache_hit_skips_health_check(self) -> None:
        cache = DynamicIndexCache(max_per_entity=5, ttl_seconds=3600)
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=cache,
        )

        # Pre-populate cache with a dummy index
        mock_index = MagicMock()
        cache.put(
            entity_type="unit",
            key_columns=["office_phone", "vertical"],
            index=mock_index,
        )

        # _get_dataframe should NOT be called on cache hit
        strategy._get_dataframe = AsyncMock()

        result = await strategy._get_or_build_index(
            project_gid="proj-1",
            key_columns=["office_phone", "vertical"],
            client=MagicMock(),
        )

        assert result is mock_index
        strategy._get_dataframe.assert_not_called()


# ---------------------------------------------------------------------------
# Threshold constant sanity check
# ---------------------------------------------------------------------------


class TestThresholdConstant:
    """Verify the threshold constant is correctly reused."""

    def test_cascade_null_error_threshold_value(self) -> None:
        assert CASCADE_NULL_ERROR_THRESHOLD == 0.20


# ---------------------------------------------------------------------------
# CascadeHealthResult dataclass
# ---------------------------------------------------------------------------


class TestCascadeHealthResult:
    """Verify the frozen dataclass behaves correctly."""

    def test_frozen(self) -> None:
        result = CascadeHealthResult(healthy=True, degraded_columns={}, max_null_rate=0.0)
        with pytest.raises(AttributeError):
            result.healthy = False  # type: ignore[misc]

    def test_attributes(self) -> None:
        result = CascadeHealthResult(
            healthy=False,
            degraded_columns={"office_phone": 0.25},
            max_null_rate=0.25,
        )
        assert result.healthy is False
        assert result.degraded_columns == {"office_phone": 0.25}
        assert result.max_null_rate == 0.25
