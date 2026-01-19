"""Tests for SearchService.

Per TDD-search-interface: Comprehensive tests for SearchService methods
including find_async, find_one_async, and convenience methods.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from autom8_asana._defaults.cache import NullCacheProvider
from autom8_asana.search.models import (
    FieldCondition,
    SearchCriteria,
    SearchResult,
)
from autom8_asana.search.service import SearchService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def null_cache() -> NullCacheProvider:
    """Null cache provider."""
    return NullCacheProvider()


@pytest.fixture
def search_service(null_cache: NullCacheProvider) -> SearchService:
    """SearchService with null cache."""
    return SearchService(cache=null_cache, dataframe_integration=None)


@pytest.fixture
def sample_dataframe() -> pl.DataFrame:
    """Sample DataFrame for testing."""
    return pl.DataFrame(
        {
            "gid": ["task1", "task2", "task3", "task4", "task5"],
            "name": [
                "Medical Clinic Offer",
                "Dental Practice Unit",
                "Healthcare Business",
                "Tech Startup Offer",
                "Medical Lab Unit",
            ],
            "type": ["Offer", "Unit", "Business", "Offer", "Unit"],
            "Vertical": ["Medical", "Medical", "Medical", "Technology", "Medical"],
            "Status": ["Active", "Active", "Pending", "Active", "Inactive"],
            "Office Phone": [
                "555-1234",
                "555-5678",
                "555-9999",
                "555-0000",
                "555-1234",
            ],
        }
    )


@pytest.fixture
def service_with_df(
    null_cache: NullCacheProvider,
    sample_dataframe: pl.DataFrame,
) -> SearchService:
    """SearchService with pre-cached DataFrame."""
    service = SearchService(cache=null_cache, dataframe_integration=None)
    service.set_project_dataframe("proj123", sample_dataframe)
    return service


# =============================================================================
# Test SearchService Initialization
# =============================================================================


class TestSearchServiceInit:
    """Tests for SearchService initialization."""

    def test_init_with_null_cache(self, null_cache: NullCacheProvider) -> None:
        """Should initialize with null cache."""
        service = SearchService(cache=null_cache)
        assert service._cache is not None
        assert service._df_integration is None

    def test_init_with_dataframe_integration(
        self, null_cache: NullCacheProvider
    ) -> None:
        """Should initialize with DataFrame integration."""
        mock_integration = MagicMock()
        service = SearchService(
            cache=null_cache,
            dataframe_integration=mock_integration,
        )
        assert service._df_integration is mock_integration


# =============================================================================
# Test find_async
# =============================================================================


class TestFindAsync:
    """Tests for find_async method."""

    @pytest.mark.asyncio
    async def test_find_no_dataframe_returns_empty(
        self,
        search_service: SearchService,
    ) -> None:
        """Should return empty result when no DataFrame cached."""
        result = await search_service.find_async(
            "proj123",
            {"Vertical": "Medical"},
        )
        assert isinstance(result, SearchResult)
        assert result.hits == []
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_find_single_field_match(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should find entities matching single field."""
        result = await service_with_df.find_async(
            "proj123",
            {"Vertical": "Medical"},
        )
        assert result.total_count == 4
        assert all(
            hit.matched_fields.get("Vertical") == "Medical" for hit in result.hits
        )

    @pytest.mark.asyncio
    async def test_find_compound_and(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should find entities matching multiple fields with AND."""
        result = await service_with_df.find_async(
            "proj123",
            {"Vertical": "Medical", "Status": "Active"},
        )
        # task1 and task2 match both conditions
        assert result.total_count == 2

    @pytest.mark.asyncio
    async def test_find_no_match_returns_empty(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should return empty result when no matches."""
        result = await service_with_df.find_async(
            "proj123",
            {"Vertical": "Finance"},
        )
        assert result.total_count == 0
        assert result.hits == []

    @pytest.mark.asyncio
    async def test_find_with_entity_type_filter(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should filter by entity type."""
        result = await service_with_df.find_async(
            "proj123",
            {"Vertical": "Medical"},
            entity_type="Offer",
        )
        # Only task1 is an Offer with Medical vertical
        assert result.total_count == 1
        assert result.hits[0].gid == "task1"

    @pytest.mark.asyncio
    async def test_find_with_limit(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should respect result limit."""
        result = await service_with_df.find_async(
            "proj123",
            {"Vertical": "Medical"},
            limit=2,
        )
        assert result.total_count == 2

    @pytest.mark.asyncio
    async def test_find_with_search_criteria(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should work with SearchCriteria object."""
        criteria = SearchCriteria(
            project_gid="proj123",
            conditions=[
                FieldCondition(field="Vertical", value="Medical"),
            ],
            limit=3,
        )
        result = await service_with_df.find_async("proj123", criteria)
        assert result.total_count == 3

    @pytest.mark.asyncio
    async def test_find_returns_from_cache_true(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should indicate results came from cache."""
        result = await service_with_df.find_async(
            "proj123",
            {"Vertical": "Medical"},
        )
        assert result.from_cache is True

    @pytest.mark.asyncio
    async def test_find_records_query_time(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should record query time."""
        result = await service_with_df.find_async(
            "proj123",
            {"Vertical": "Medical"},
        )
        assert result.query_time_ms >= 0

    @pytest.mark.asyncio
    async def test_find_extracts_matched_fields(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should include matched fields in hits."""
        result = await service_with_df.find_async(
            "proj123",
            {"Office Phone": "555-1234"},
        )
        assert result.total_count >= 1
        for hit in result.hits:
            assert "Office Phone" in hit.matched_fields
            assert hit.matched_fields["Office Phone"] == "555-1234"


# =============================================================================
# Test find_one_async
# =============================================================================


class TestFindOneAsync:
    """Tests for find_one_async method."""

    @pytest.mark.asyncio
    async def test_find_one_single_match(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should return single hit when exactly one match."""
        result = await service_with_df.find_one_async(
            "proj123",
            {"Vertical": "Technology"},
        )
        assert result is not None
        assert result.gid == "task4"

    @pytest.mark.asyncio
    async def test_find_one_no_match_returns_none(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should return None when no match."""
        result = await service_with_df.find_one_async(
            "proj123",
            {"Vertical": "Finance"},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_find_one_multiple_matches_raises(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should raise ValueError when multiple matches."""
        with pytest.raises(ValueError, match="Multiple matches found"):
            await service_with_df.find_one_async(
                "proj123",
                {"Vertical": "Medical"},
            )


# =============================================================================
# Test Convenience Methods
# =============================================================================


class TestConvenienceMethods:
    """Tests for convenience methods."""

    @pytest.mark.asyncio
    async def test_find_offers_async(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should find Offer GIDs."""
        gids = await service_with_df.find_offers_async(
            "proj123",
            vertical="Medical",
        )
        assert "task1" in gids
        assert "task2" not in gids  # Unit, not Offer

    @pytest.mark.asyncio
    async def test_find_units_async(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should find Unit GIDs."""
        gids = await service_with_df.find_units_async(
            "proj123",
            vertical="Medical",
        )
        assert "task2" in gids
        assert "task5" in gids
        assert "task1" not in gids  # Offer, not Unit

    @pytest.mark.asyncio
    async def test_find_businesses_async(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should find Business GIDs."""
        gids = await service_with_df.find_businesses_async(
            "proj123",
            vertical="Medical",
        )
        assert "task3" in gids

    @pytest.mark.asyncio
    async def test_convenience_method_normalizes_field_names(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should normalize snake_case to Title Case."""
        # office_phone should match "Office Phone" column
        gids = await service_with_df.find_offers_async(
            "proj123",
            office_phone="555-1234",
        )
        assert "task1" in gids


# =============================================================================
# Test Sync Wrappers
# =============================================================================


class TestSyncWrappers:
    """Tests for sync wrapper methods."""

    def test_find_sync(self, service_with_df: SearchService) -> None:
        """Should work synchronously."""
        result = service_with_df.find(
            "proj123",
            {"Vertical": "Medical"},
        )
        assert result.total_count == 4

    def test_find_one_sync(self, service_with_df: SearchService) -> None:
        """Should work synchronously."""
        result = service_with_df.find_one(
            "proj123",
            {"Vertical": "Technology"},
        )
        assert result is not None
        assert result.gid == "task4"

    def test_find_offers_sync(self, service_with_df: SearchService) -> None:
        """Should work synchronously."""
        gids = service_with_df.find_offers(
            "proj123",
            vertical="Medical",
        )
        assert "task1" in gids

    def test_find_units_sync(self, service_with_df: SearchService) -> None:
        """Should work synchronously."""
        gids = service_with_df.find_units(
            "proj123",
            vertical="Medical",
        )
        assert "task2" in gids

    def test_find_businesses_sync(self, service_with_df: SearchService) -> None:
        """Should work synchronously."""
        gids = service_with_df.find_businesses(
            "proj123",
            vertical="Medical",
        )
        assert "task3" in gids


# =============================================================================
# Test DataFrame Cache Management
# =============================================================================


class TestDataFrameCacheManagement:
    """Tests for DataFrame cache management."""

    def test_set_project_dataframe(
        self,
        search_service: SearchService,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Should cache DataFrame for project."""
        search_service.set_project_dataframe("proj123", sample_dataframe)
        assert "proj123" in search_service._project_df_cache

    def test_clear_project_cache_specific(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should clear specific project cache."""
        service_with_df.clear_project_cache("proj123")
        assert "proj123" not in service_with_df._project_df_cache

    def test_clear_project_cache_all(
        self,
        service_with_df: SearchService,
        sample_dataframe: pl.DataFrame,
    ) -> None:
        """Should clear all project caches."""
        service_with_df.set_project_dataframe("proj456", sample_dataframe)
        service_with_df.clear_project_cache()
        assert len(service_with_df._project_df_cache) == 0


# =============================================================================
# Test Field Name Normalization
# =============================================================================


class TestFieldNameNormalization:
    """Tests for field name normalization in search."""

    @pytest.mark.asyncio
    async def test_case_insensitive_field_match(
        self,
        null_cache: NullCacheProvider,
    ) -> None:
        """Should match fields case-insensitively."""
        df = pl.DataFrame(
            {
                "gid": ["task1"],
                "name": ["Test Task"],
                "Vertical": ["Medical"],
            }
        )
        service = SearchService(cache=null_cache)
        service.set_project_dataframe("proj123", df)

        # Match with different case
        result = await service.find_async(
            "proj123",
            {"vertical": "Medical"},  # lowercase field name
        )
        assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_snake_case_to_title_case(
        self,
        null_cache: NullCacheProvider,
    ) -> None:
        """Should match snake_case to Title Case columns."""
        df = pl.DataFrame(
            {
                "gid": ["task1"],
                "name": ["Test Task"],
                "Office Phone": ["555-1234"],
            }
        )
        service = SearchService(cache=null_cache)
        service.set_project_dataframe("proj123", df)

        # Match with snake_case
        result = await service.find_async(
            "proj123",
            {"office_phone": "555-1234"},
        )
        assert result.total_count == 1


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_invalid_field_returns_empty(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should return empty when field doesn't exist."""
        result = await service_with_df.find_async(
            "proj123",
            {"NonExistentField": "value"},
        )
        # No valid conditions -> empty result
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_empty_criteria_returns_empty(
        self,
        service_with_df: SearchService,
    ) -> None:
        """Should return empty with empty criteria."""
        result = await service_with_df.find_async(
            "proj123",
            {},
        )
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_uncached_project_returns_empty(
        self,
        search_service: SearchService,
    ) -> None:
        """Should return empty for uncached project."""
        result = await search_service.find_async(
            "nonexistent_project",
            {"Vertical": "Medical"},
        )
        assert result.total_count == 0
        assert result.from_cache is False
