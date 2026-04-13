"""Tests for query/offline_provider.py: OfflineDataFrameProvider, NullClient, OfflineProjectRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from autom8_asana.query.offline_provider import (
    NullClient,
    OfflineDataFrameProvider,
    OfflineProjectRegistry,
)


class TestOfflineDataFrameProviderProtocol:
    """Verify OfflineDataFrameProvider implements DataFrameProvider protocol."""

    def test_implements_protocol(self) -> None:
        """OfflineDataFrameProvider must pass isinstance check against DataFrameProvider."""
        from autom8_asana.protocols.dataframe_provider import DataFrameProvider

        provider = OfflineDataFrameProvider(bucket="test-bucket")
        assert isinstance(provider, DataFrameProvider)

    def test_has_last_freshness_info_property(self) -> None:
        """Provider must expose last_freshness_info property."""
        provider = OfflineDataFrameProvider(bucket="test-bucket")
        assert provider.last_freshness_info is None

    def test_has_get_dataframe_method(self) -> None:
        """Provider must expose async get_dataframe method."""
        import inspect

        provider = OfflineDataFrameProvider(bucket="test-bucket")
        assert hasattr(provider, "get_dataframe")
        assert inspect.iscoroutinefunction(provider.get_dataframe)


class TestOfflineDataFrameProviderCaching:
    """Verify in-process cache behavior."""

    @pytest.mark.asyncio
    async def test_get_dataframe_returns_cached(self) -> None:
        """Second call returns same DataFrame object (no S3 re-read)."""
        sample_df = pl.DataFrame({"gid": ["1", "2"], "name": ["A", "B"]})

        provider = OfflineDataFrameProvider(bucket="test-bucket")

        with patch(
            "autom8_asana.dataframes.offline.load_project_dataframe_with_meta",
            return_value=(sample_df, None),
        ) as mock_load:
            client = NullClient()
            first = await provider.get_dataframe("offer", "123", client)  # type: ignore[arg-type]
            second = await provider.get_dataframe("offer", "123", client)  # type: ignore[arg-type]

            # Same object (cached)
            assert first is second
            # load_project_dataframe_with_meta called only once
            mock_load.assert_called_once_with("123", bucket="test-bucket", region="us-east-1")

    @pytest.mark.asyncio
    async def test_different_project_gids_not_cached(self) -> None:
        """Different project GIDs trigger separate S3 loads."""
        df1 = pl.DataFrame({"gid": ["1"]})
        df2 = pl.DataFrame({"gid": ["2"]})

        provider = OfflineDataFrameProvider(bucket="test-bucket")

        with patch(
            "autom8_asana.dataframes.offline.load_project_dataframe_with_meta",
            side_effect=[(df1, None), (df2, None)],
        ) as mock_load:
            client = NullClient()
            first = await provider.get_dataframe("offer", "111", client)  # type: ignore[arg-type]
            second = await provider.get_dataframe("unit", "222", client)  # type: ignore[arg-type]

            assert first is not second
            assert mock_load.call_count == 2

    @pytest.mark.asyncio
    async def test_freshness_info_after_load(self) -> None:
        """After loading, freshness_info reflects s3_offline status."""
        sample_df = pl.DataFrame({"gid": ["1"]})

        provider = OfflineDataFrameProvider(bucket="test-bucket")

        with patch(
            "autom8_asana.dataframes.offline.load_project_dataframe_with_meta",
            return_value=(sample_df, None),
        ):
            client = NullClient()
            await provider.get_dataframe("offer", "123", client)  # type: ignore[arg-type]

            info = provider.last_freshness_info
            assert info is not None
            assert info.freshness == "s3_offline"
            assert info.staleness_ratio == 0.0
            assert info.data_age_seconds >= 0

    @pytest.mark.asyncio
    async def test_last_freshness_info_none_before_load(self) -> None:
        """Before any load, last_freshness_info is None."""
        provider = OfflineDataFrameProvider(bucket="test-bucket")
        assert provider.last_freshness_info is None

    @pytest.mark.asyncio
    async def test_freshness_info_with_last_modified(self) -> None:
        """Freshness should include real data_age_seconds from S3 LastModified."""
        from datetime import UTC, datetime, timedelta

        sample_df = pl.DataFrame({"gid": ["1"]})
        # Simulate S3 object modified 2 hours ago
        two_hours_ago = datetime.now(UTC) - timedelta(hours=2)

        provider = OfflineDataFrameProvider(bucket="test-bucket")

        with patch(
            "autom8_asana.dataframes.offline.load_project_dataframe_with_meta",
            return_value=(sample_df, two_hours_ago),
        ):
            client = NullClient()
            await provider.get_dataframe("offer", "123", client)  # type: ignore[arg-type]

            info = provider.last_freshness_info
            assert info is not None
            assert info.freshness == "s3_offline"
            # data_age_seconds should be approximately 7200 (2 hours)
            assert 7100 < info.data_age_seconds < 7500
            assert info.staleness_ratio == 0.0


class TestNullClient:
    """Verify NullClient sentinel behavior."""

    def test_raises_on_attribute_access(self) -> None:
        """Any attribute access on NullClient raises RuntimeError."""
        client = NullClient()
        with pytest.raises(RuntimeError, match="NullClient"):
            client.some_method()

    def test_raises_on_different_attributes(self) -> None:
        """Different attribute names all raise with the attribute name in the message."""
        client = NullClient()
        with pytest.raises(RuntimeError, match="get_tasks"):
            client.get_tasks()

        with pytest.raises(RuntimeError, match="search"):
            client.search()

    def test_error_message_includes_offline_guidance(self) -> None:
        """Error message explains offline mode context."""
        client = NullClient()
        with pytest.raises(RuntimeError, match="offline mode"):
            client.any_call()


class TestOfflineProjectRegistry:
    """Verify OfflineProjectRegistry wraps EntityRegistry correctly."""

    def test_returns_project_gid_for_known_entity(self) -> None:
        """Known entity types return their primary_project_gid."""
        registry = OfflineProjectRegistry()
        # 'offer' is always registered with project GID 1143843662099250
        gid = registry.get_project_gid("offer")
        assert gid == "1143843662099250"

    def test_returns_project_gid_for_business(self) -> None:
        """Business entity returns its project GID."""
        registry = OfflineProjectRegistry()
        gid = registry.get_project_gid("business")
        assert gid == "1200653012566782"

    def test_returns_none_for_unknown_entity(self) -> None:
        """Unknown entity types return None."""
        registry = OfflineProjectRegistry()
        gid = registry.get_project_gid("nonexistent_entity_type_xyz")
        assert gid is None

    def test_returns_none_for_entity_without_project(self) -> None:
        """Entity types without primary_project_gid return None."""
        registry = OfflineProjectRegistry()
        # 'process' has no static primary_project_gid
        gid = registry.get_project_gid("process")
        assert gid is None
