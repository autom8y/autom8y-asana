"""Unit tests for cached resolution strategies (Offer and Contact).

Per TDD-DATAFRAME-CACHE-001 Phase 2 (task-003, task-004):
Tests that @dataframe_cache decorator is properly applied to
OfferResolutionStrategy and ContactResolutionStrategy.
"""

import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.cache.dataframe_cache import (
    CacheEntry,
    DataFrameCache,
    reset_dataframe_cache,
)


def make_offer_dataframe() -> pl.DataFrame:
    """Create a test Offer DataFrame."""
    return pl.DataFrame({
        "gid": ["offer-1", "offer-2", "offer-3"],
        "offer_id": ["OID001", "OID002", "OID003"],
        "office_phone": ["1234567890", "1234567890", "9876543210"],
        "vertical": ["Dental", "Dental", "Medical"],
        "name": ["Offer A", "Offer B", "Offer C"],
    })


def make_contact_dataframe() -> pl.DataFrame:
    """Create a test Contact DataFrame."""
    return pl.DataFrame({
        "gid": ["contact-1", "contact-2", "contact-3", "contact-4"],
        "contact_email": ["a@test.com", "b@test.com", "a@test.com", "c@test.com"],
        "contact_phone": ["111-111-1111", "222-222-2222", "333-333-3333", "111-111-1111"],
    })


def make_cache_entry(
    project_gid: str,
    entity_type: str,
    dataframe: pl.DataFrame,
) -> CacheEntry:
    """Create a test CacheEntry."""
    return CacheEntry(
        project_gid=project_gid,
        entity_type=entity_type,
        dataframe=dataframe,
        watermark=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        schema_version="1.0.0",
    )


def make_mock_cache() -> MagicMock:
    """Create a mock DataFrameCache."""
    cache = MagicMock(spec=DataFrameCache)
    cache.get_async = AsyncMock(return_value=None)
    cache.put_async = AsyncMock()
    cache.acquire_build_lock_async = AsyncMock(return_value=True)
    cache.release_build_lock_async = AsyncMock()
    cache.wait_for_build_async = AsyncMock(return_value=None)
    return cache


class MockCriterion:
    """Mock resolution criterion for testing."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestOfferResolutionStrategyWithCache:
    """Tests for OfferResolutionStrategy with @dataframe_cache."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clean up after each test."""
        yield
        if "DATAFRAME_CACHE_BYPASS" in os.environ:
            del os.environ["DATAFRAME_CACHE_BYPASS"]
        reset_dataframe_cache()

    @pytest.mark.asyncio
    async def test_cache_hit_uses_cached_dataframe(self) -> None:
        """On cache hit, uses injected _cached_dataframe for lookups."""
        from autom8_asana.services.resolver import OfferResolutionStrategy

        mock_cache = make_mock_cache()
        offer_df = make_offer_dataframe()
        entry = make_cache_entry("proj-offer", "offer", offer_df)
        mock_cache.get_async.return_value = entry

        with patch(
            "autom8_asana.services.resolver.get_dataframe_cache_provider",
            return_value=mock_cache,
        ):
            strategy = OfferResolutionStrategy()
            strategy._cached_dataframe = offer_df  # Simulate decorator injection

            criteria = [MockCriterion(offer_id="OID001")]

            # Mock client
            mock_client = MagicMock()

            result = await strategy.resolve(criteria, "proj-offer", mock_client)

        assert len(result) == 1
        assert result[0].gid == "offer-1"
        assert result[0].error is None

    @pytest.mark.asyncio
    async def test_lookup_by_offer_id(self) -> None:
        """Offer lookup by offer_id field."""
        from autom8_asana.services.resolver import OfferResolutionStrategy

        strategy = OfferResolutionStrategy()
        offer_df = make_offer_dataframe()
        strategy._cached_dataframe = offer_df

        criteria = [MockCriterion(offer_id="OID002")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-offer", mock_client)

        assert len(result) == 1
        assert result[0].gid == "offer-2"

    @pytest.mark.asyncio
    async def test_lookup_by_composite(self) -> None:
        """Offer lookup by phone/vertical/offer_name composite."""
        from autom8_asana.services.resolver import OfferResolutionStrategy

        strategy = OfferResolutionStrategy()
        offer_df = make_offer_dataframe()
        strategy._cached_dataframe = offer_df

        criteria = [
            MockCriterion(
                phone="1234567890",
                vertical="Dental",
                offer_name="Offer B",
            )
        ]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-offer", mock_client)

        assert len(result) == 1
        assert result[0].gid == "offer-2"

    @pytest.mark.asyncio
    async def test_lookup_not_found(self) -> None:
        """Offer lookup returns NOT_FOUND when not matched."""
        from autom8_asana.services.resolver import OfferResolutionStrategy

        strategy = OfferResolutionStrategy()
        offer_df = make_offer_dataframe()
        strategy._cached_dataframe = offer_df

        criteria = [MockCriterion(offer_id="NONEXISTENT")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-offer", mock_client)

        assert len(result) == 1
        assert result[0].gid is None
        assert result[0].error == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_build_dataframe_returns_tuple(self) -> None:
        """_build_dataframe returns (DataFrame, watermark) tuple."""
        from autom8_asana.services.resolver import OfferResolutionStrategy

        strategy = OfferResolutionStrategy()

        # Mock the internal build method
        mock_df = make_offer_dataframe()
        with patch.object(
            strategy,
            "_build_offer_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ):
            result = await strategy._build_dataframe("proj-offer", MagicMock())

        assert isinstance(result, tuple)
        assert len(result) == 2
        df, watermark = result
        assert isinstance(df, pl.DataFrame)
        assert isinstance(watermark, datetime)

    @pytest.mark.asyncio
    async def test_bypass_uses_build_directly(self) -> None:
        """With cache bypass, builds DataFrame directly."""
        from autom8_asana.services.resolver import OfferResolutionStrategy

        os.environ["DATAFRAME_CACHE_BYPASS"] = "true"

        strategy = OfferResolutionStrategy()
        strategy._cached_dataframe = None  # No cached data

        mock_df = make_offer_dataframe()
        mock_client = MagicMock()

        with patch.object(
            strategy,
            "_build_offer_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ):
            criteria = [MockCriterion(offer_id="OID001")]
            result = await strategy.resolve(criteria, "proj-offer", mock_client)

        assert len(result) == 1
        assert result[0].gid == "offer-1"


class TestContactResolutionStrategyWithCache:
    """Tests for ContactResolutionStrategy with @dataframe_cache."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clean up after each test."""
        yield
        if "DATAFRAME_CACHE_BYPASS" in os.environ:
            del os.environ["DATAFRAME_CACHE_BYPASS"]
        reset_dataframe_cache()

    @pytest.mark.asyncio
    async def test_cache_hit_uses_cached_dataframe(self) -> None:
        """On cache hit, uses injected _cached_dataframe for lookups."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        strategy = ContactResolutionStrategy()
        contact_df = make_contact_dataframe()
        strategy._cached_dataframe = contact_df

        criteria = [MockCriterion(contact_email="b@test.com")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-contact", mock_client)

        assert len(result) == 1
        assert result[0].gid == "contact-2"

    @pytest.mark.asyncio
    async def test_lookup_by_email(self) -> None:
        """Contact lookup by email field."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        strategy = ContactResolutionStrategy()
        contact_df = make_contact_dataframe()
        strategy._cached_dataframe = contact_df

        criteria = [MockCriterion(contact_email="c@test.com")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-contact", mock_client)

        assert len(result) == 1
        assert result[0].gid == "contact-4"
        assert result[0].multiple is None  # Single match

    @pytest.mark.asyncio
    async def test_lookup_by_phone(self) -> None:
        """Contact lookup by phone field."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        strategy = ContactResolutionStrategy()
        contact_df = make_contact_dataframe()
        strategy._cached_dataframe = contact_df

        criteria = [MockCriterion(contact_phone="222-222-2222")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-contact", mock_client)

        assert len(result) == 1
        assert result[0].gid == "contact-2"

    @pytest.mark.asyncio
    async def test_multiple_matches_returns_flag(self) -> None:
        """Multiple matches return first GID with multiple=True."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        strategy = ContactResolutionStrategy()
        contact_df = make_contact_dataframe()
        strategy._cached_dataframe = contact_df

        # Email a@test.com has two matches (contact-1 and contact-3)
        criteria = [MockCriterion(contact_email="a@test.com")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-contact", mock_client)

        assert len(result) == 1
        assert result[0].gid == "contact-1"  # First match
        assert result[0].multiple is True  # Multiple flag set

    @pytest.mark.asyncio
    async def test_multiple_matches_by_phone(self) -> None:
        """Multiple phone matches return first GID with multiple=True."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        strategy = ContactResolutionStrategy()
        contact_df = make_contact_dataframe()
        strategy._cached_dataframe = contact_df

        # Phone 111-111-1111 has two matches (contact-1 and contact-4)
        criteria = [MockCriterion(contact_phone="111-111-1111")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-contact", mock_client)

        assert len(result) == 1
        assert result[0].gid == "contact-1"  # First match
        assert result[0].multiple is True

    @pytest.mark.asyncio
    async def test_lookup_not_found(self) -> None:
        """Contact lookup returns NOT_FOUND when not matched."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        strategy = ContactResolutionStrategy()
        contact_df = make_contact_dataframe()
        strategy._cached_dataframe = contact_df

        criteria = [MockCriterion(contact_email="nonexistent@test.com")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-contact", mock_client)

        assert len(result) == 1
        assert result[0].gid is None
        assert result[0].error == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_build_dataframe_returns_tuple(self) -> None:
        """_build_dataframe returns (DataFrame, watermark) tuple."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        strategy = ContactResolutionStrategy()

        mock_df = make_contact_dataframe()
        with patch.object(
            strategy,
            "_build_contact_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ):
            result = await strategy._build_dataframe("proj-contact", MagicMock())

        assert isinstance(result, tuple)
        assert len(result) == 2
        df, watermark = result
        assert isinstance(df, pl.DataFrame)
        assert isinstance(watermark, datetime)

    @pytest.mark.asyncio
    async def test_bypass_uses_build_directly(self) -> None:
        """With cache bypass, builds DataFrame directly."""
        from autom8_asana.services.resolver import ContactResolutionStrategy

        os.environ["DATAFRAME_CACHE_BYPASS"] = "true"

        strategy = ContactResolutionStrategy()
        strategy._cached_dataframe = None  # No cached data

        mock_df = make_contact_dataframe()
        mock_client = MagicMock()

        with patch.object(
            strategy,
            "_build_contact_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ):
            criteria = [MockCriterion(contact_email="b@test.com")]
            result = await strategy.resolve(criteria, "proj-contact", mock_client)

        assert len(result) == 1
        assert result[0].gid == "contact-2"


class TestCacheFactoryIntegration:
    """Tests for cache factory integration."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clean up after each test."""
        yield
        reset_dataframe_cache()

    def test_get_dataframe_cache_provider_returns_none_initially(self) -> None:
        """Cache provider returns None when not initialized."""
        from autom8_asana.cache.dataframe.factory import get_dataframe_cache_provider

        reset_dataframe_cache()
        cache = get_dataframe_cache_provider()
        assert cache is None

    def test_initialize_sets_singleton(self) -> None:
        """Initialize creates and sets singleton cache."""
        from autom8_asana.cache.dataframe.factory import (
            initialize_dataframe_cache,
            reset_dataframe_cache,
        )
        from autom8_asana.settings import reset_settings

        reset_dataframe_cache()
        reset_settings()

        # Without S3 configured, returns None
        cache = initialize_dataframe_cache()

        # With S3 not configured, should return None
        assert cache is None

    @patch.dict(os.environ, {"ASANA_CACHE_S3_BUCKET": "test-bucket"})
    def test_initialize_with_s3_creates_cache(self) -> None:
        """Initialize with S3 configured creates cache."""
        from autom8_asana.cache.dataframe.factory import (
            get_dataframe_cache_provider,
            initialize_dataframe_cache,
            reset_dataframe_cache,
        )
        from autom8_asana.settings import reset_settings

        reset_dataframe_cache()
        reset_settings()

        cache = initialize_dataframe_cache()

        assert cache is not None
        assert get_dataframe_cache_provider() is cache

    @patch.dict(os.environ, {"ASANA_CACHE_S3_BUCKET": "test-bucket"})
    def test_initialize_idempotent(self) -> None:
        """Multiple initialize calls return same instance."""
        from autom8_asana.cache.dataframe.factory import (
            initialize_dataframe_cache,
            reset_dataframe_cache,
        )
        from autom8_asana.settings import reset_settings

        reset_dataframe_cache()
        reset_settings()

        cache1 = initialize_dataframe_cache()
        cache2 = initialize_dataframe_cache()

        assert cache1 is cache2


def make_unit_dataframe() -> pl.DataFrame:
    """Create a test Unit DataFrame with phone/vertical columns.

    Phone numbers must be in E.164 format per PhoneVerticalPair validation.
    Verticals must be lowercase to match GidLookupIndex normalization.
    """
    return pl.DataFrame({
        "gid": ["unit-1", "unit-2", "unit-3"],
        "office_phone": ["+11234567890", "+19876543210", "+15555555555"],
        "vertical": ["dental", "medical", "dental"],
        "name": ["Unit A", "Unit B", "Unit C"],
    })


class TestUnitResolutionStrategyWithCache:
    """Tests for UnitResolutionStrategy with @dataframe_cache.

    Per TDD-DATAFRAME-CACHE-001 Phase 3 (task-001):
    Tests that @dataframe_cache decorator is properly applied to
    UnitResolutionStrategy.
    """

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clean up after each test."""
        yield
        if "DATAFRAME_CACHE_BYPASS" in os.environ:
            del os.environ["DATAFRAME_CACHE_BYPASS"]
        reset_dataframe_cache()

    @pytest.mark.asyncio
    async def test_cache_hit_uses_cached_dataframe(self) -> None:
        """On cache hit, uses injected _cached_dataframe for lookups."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()
        unit_df = make_unit_dataframe()
        strategy._cached_dataframe = unit_df  # Simulate decorator injection

        criteria = [MockCriterion(phone="+11234567890", vertical="dental")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-unit", mock_client)

        assert len(result) == 1
        assert result[0].gid == "unit-1"
        assert result[0].error is None

    @pytest.mark.asyncio
    async def test_lookup_by_phone_vertical(self) -> None:
        """Unit lookup by phone/vertical pair."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()
        unit_df = make_unit_dataframe()
        strategy._cached_dataframe = unit_df

        criteria = [MockCriterion(phone="+19876543210", vertical="medical")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-unit", mock_client)

        assert len(result) == 1
        assert result[0].gid == "unit-2"

    @pytest.mark.asyncio
    async def test_lookup_not_found(self) -> None:
        """Unit lookup returns NOT_FOUND when not matched."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()
        unit_df = make_unit_dataframe()
        strategy._cached_dataframe = unit_df

        # Valid E.164 format but not in DataFrame
        criteria = [MockCriterion(phone="+10000000000", vertical="unknown")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-unit", mock_client)

        assert len(result) == 1
        assert result[0].gid is None
        assert result[0].error == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_multiple_criteria(self) -> None:
        """Unit lookup handles multiple criteria in batch."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()
        unit_df = make_unit_dataframe()
        strategy._cached_dataframe = unit_df

        criteria = [
            MockCriterion(phone="+11234567890", vertical="dental"),  # unit-1
            MockCriterion(phone="+19876543210", vertical="medical"),  # unit-2
            MockCriterion(phone="+10000000000", vertical="unknown"),  # not found
        ]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-unit", mock_client)

        assert len(result) == 3
        assert result[0].gid == "unit-1"
        assert result[1].gid == "unit-2"
        assert result[2].gid is None
        assert result[2].error == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_build_dataframe_returns_tuple(self) -> None:
        """_build_dataframe returns (DataFrame, watermark) tuple."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()

        mock_df = make_unit_dataframe()
        with patch.object(
            strategy,
            "_build_unit_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ):
            result = await strategy._build_dataframe("proj-unit", MagicMock())

        assert isinstance(result, tuple)
        assert len(result) == 2
        df, watermark = result
        assert isinstance(df, pl.DataFrame)
        assert isinstance(watermark, datetime)

    @pytest.mark.asyncio
    async def test_bypass_builds_directly(self) -> None:
        """With cache bypass, builds DataFrame directly without caching."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        os.environ["DATAFRAME_CACHE_BYPASS"] = "true"

        strategy = UnitResolutionStrategy()
        strategy._cached_dataframe = None  # No cached data from decorator

        mock_df = make_unit_dataframe()
        mock_client = MagicMock()

        with patch.object(
            strategy,
            "_build_unit_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ):
            criteria = [MockCriterion(phone="+11234567890", vertical="dental")]
            result = await strategy.resolve(criteria, "proj-unit", mock_client)

        assert len(result) == 1
        assert result[0].gid == "unit-1"

    @pytest.mark.asyncio
    async def test_cached_dataframe_used_for_lookup(self) -> None:
        """Cached DataFrame is used directly for lookups."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()

        # Create a DataFrame with test data
        # Phone numbers must be E.164 format, verticals lowercase
        cached_df = pl.DataFrame({
            "gid": ["cached-unit-1"],
            "office_phone": ["+11111111111"],
            "vertical": ["cached"],
            "name": ["Cached Unit"],
        })
        strategy._cached_dataframe = cached_df

        criteria = [MockCriterion(phone="+11111111111", vertical="cached")]
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-unit", mock_client)

        # Should use cached DataFrame
        assert len(result) == 1
        assert result[0].gid == "cached-unit-1"

    @pytest.mark.asyncio
    async def test_invalid_criteria_returns_error(self) -> None:
        """Invalid criteria without phone/vertical returns INVALID_CRITERIA."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()
        unit_df = make_unit_dataframe()
        strategy._cached_dataframe = unit_df

        criteria = [MockCriterion(phone=None, vertical=None)]  # Invalid
        mock_client = MagicMock()

        result = await strategy.resolve(criteria, "proj-unit", mock_client)

        assert len(result) == 1
        assert result[0].gid is None
        assert result[0].error == "INVALID_CRITERIA"

    @pytest.mark.asyncio
    async def test_empty_criteria_returns_empty(self) -> None:
        """Empty criteria list returns empty results."""
        from autom8_asana.services.resolver import UnitResolutionStrategy

        strategy = UnitResolutionStrategy()
        strategy._cached_dataframe = make_unit_dataframe()

        result = await strategy.resolve([], "proj-unit", MagicMock())

        assert result == []


class TestLegacyCacheRemoval:
    """Tests verifying legacy _gid_index_cache has been removed."""

    def test_gid_index_cache_not_importable(self) -> None:
        """_gid_index_cache has been removed from resolver module."""
        with pytest.raises(ImportError):
            from autom8_asana.services.resolver import _gid_index_cache  # noqa: F401

    def test_index_ttl_seconds_not_importable(self) -> None:
        """_INDEX_TTL_SECONDS has been removed from resolver module."""
        with pytest.raises(ImportError):
            from autom8_asana.services.resolver import _INDEX_TTL_SECONDS  # noqa: F401

    def test_gid_index_cache_not_in_all(self) -> None:
        """_gid_index_cache is not in __all__ exports."""
        from autom8_asana.services import resolver

        assert "_gid_index_cache" not in resolver.__all__
        assert "_INDEX_TTL_SECONDS" not in resolver.__all__
