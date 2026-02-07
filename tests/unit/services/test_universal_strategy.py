"""Unit tests for UniversalResolutionStrategy.

Per TDD-DYNAMIC-RESOLVER-001 / FR-005:
Tests for the universal schema-driven resolution strategy that replaces
per-entity strategies with a single flexible approach.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.services.dynamic_index import DynamicIndexCache
from autom8_asana.services.universal_strategy import (
    UniversalResolutionStrategy,
    get_shared_index_cache,
    get_universal_strategy,
    reset_shared_index_cache,
)

# --- Test Fixtures ---


def make_unit_dataframe() -> pl.DataFrame:
    """Create a test Unit DataFrame with phone/vertical columns."""
    return pl.DataFrame(
        {
            "gid": ["unit-1", "unit-2", "unit-3"],
            "office_phone": ["+11234567890", "+19876543210", "+15555555555"],
            "vertical": ["dental", "medical", "dental"],
            "name": ["Unit A", "Unit B", "Unit C"],
        }
    )


def make_contact_dataframe() -> pl.DataFrame:
    """Create a test Contact DataFrame with email/phone columns.

    Note: Uses "contact_email" and "contact_phone" to match the actual
    Contact schema column names used in the resolver.
    """
    return pl.DataFrame(
        {
            "gid": ["contact-1", "contact-2", "contact-3", "contact-4"],
            "contact_email": [
                "a@test.com",
                "b@test.com",
                "a@test.com",
                "c@test.com",
            ],
            "contact_phone": [
                "111-111-1111",
                "222-222-2222",
                "333-333-3333",
                "111-111-1111",
            ],
            "name": ["Contact A", "Contact B", "Contact C", "Contact D"],
        }
    )


def make_offer_dataframe() -> pl.DataFrame:
    """Create a test Offer DataFrame."""
    return pl.DataFrame(
        {
            "gid": ["offer-1", "offer-2", "offer-3"],
            "offer_id": ["OID001", "OID002", "OID003"],
            "office_phone": ["+11234567890", "+11234567890", "+19876543210"],
            "vertical": ["dental", "dental", "medical"],
            "name": ["Offer A", "Offer B", "Offer C"],
        }
    )


@pytest.fixture
def unit_dataframe() -> pl.DataFrame:
    """Fixture for Unit test DataFrame."""
    return make_unit_dataframe()


@pytest.fixture
def contact_dataframe() -> pl.DataFrame:
    """Fixture for Contact test DataFrame."""
    return make_contact_dataframe()


@pytest.fixture
def index_cache() -> DynamicIndexCache:
    """Fixture for fresh DynamicIndexCache."""
    return DynamicIndexCache(max_per_entity=5, ttl_seconds=3600)


@pytest.fixture
def mock_client() -> MagicMock:
    """Fixture for mock AsanaClient."""
    client = MagicMock()
    client.unified_store = MagicMock()
    return client


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up shared state after each test."""
    yield
    reset_shared_index_cache()


# --- UniversalResolutionStrategy Tests ---


class TestUniversalResolutionStrategy:
    """Tests for UniversalResolutionStrategy class."""

    @pytest.mark.asyncio
    async def test_resolve_single_criterion(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test resolution with a single criterion."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert len(results) == 1
        assert results[0].gid == "unit-1"
        assert results[0].error is None
        assert results[0].is_unique

    @pytest.mark.asyncio
    async def test_resolve_multiple_criteria(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test resolution with multiple criteria."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[
                {"office_phone": "+11234567890", "vertical": "dental"},
                {"office_phone": "+19876543210", "vertical": "medical"},
                {"office_phone": "+10000000000", "vertical": "unknown"},
            ],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert len(results) == 3
        assert results[0].gid == "unit-1"
        assert results[1].gid == "unit-2"
        assert results[2].gid is None
        assert results[2].error == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_resolve_multi_match(
        self, contact_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test resolution returning multiple matches."""
        strategy = UniversalResolutionStrategy(
            entity_type="contact",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = contact_dataframe

        # Mock validation to pass (schema may not have contact_email in test env)
        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                errors=[],
                normalized_criterion={"contact_email": "a@test.com"},
            )

            # Email "a@test.com" matches contact-1 and contact-3
            results = await strategy.resolve(
                criteria=[{"contact_email": "a@test.com"}],
                project_gid="test-project",
                client=MagicMock(),
            )

        assert len(results) == 1
        result = results[0]
        assert result.gid == "contact-1"  # First match (backwards compat)
        assert len(result.gids) == 2
        assert "contact-1" in result.gids
        assert "contact-3" in result.gids
        assert result.is_ambiguous  # Multiple matches
        assert result.match_count == 2

    @pytest.mark.asyncio
    async def test_resolve_not_found(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test resolution when criterion doesn't match."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+10000000000", "vertical": "unknown"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert len(results) == 1
        assert results[0].gid is None
        assert results[0].error == "NOT_FOUND"
        assert results[0].match_count == 0

    @pytest.mark.asyncio
    async def test_resolve_empty_criteria(self, index_cache: DynamicIndexCache) -> None:
        """Test resolution with empty criteria list."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        results = await strategy.resolve(
            criteria=[],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_legacy_field_mapping(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test that legacy 'phone' field maps to 'office_phone'."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        # Use legacy "phone" field instead of "office_phone"
        results = await strategy.resolve(
            criteria=[{"phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert len(results) == 1
        assert results[0].gid == "unit-1"
        assert results[0].error is None

    @pytest.mark.asyncio
    async def test_index_caching(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test that indexes are cached for reuse."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        # First resolution - builds index
        await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        # Check index is cached
        cached_index = index_cache.get(
            entity_type="unit",
            key_columns=["office_phone", "vertical"],
        )
        assert cached_index is not None

        # Second resolution should use cached index
        await strategy.resolve(
            criteria=[{"office_phone": "+19876543210", "vertical": "medical"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        # Stats should show cache hit
        stats = index_cache.get_stats()
        assert stats["hits"] >= 1

    def test_validate_criterion_valid(self, index_cache: DynamicIndexCache) -> None:
        """Test validation of valid criterion."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        # Mock validate_criterion_for_entity to return valid result
        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                errors=[],
                unknown_fields=[],
                available_fields=["gid", "office_phone", "vertical", "name"],
                normalized_criterion={
                    "office_phone": "+11234567890",
                    "vertical": "dental",
                },
            )

            errors = strategy.validate_criterion(
                {"office_phone": "+11234567890", "vertical": "dental"}
            )

        assert errors == []

    def test_get_default_key_columns(self, index_cache: DynamicIndexCache) -> None:
        """Test getting default key columns for entity types."""
        unit_strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        assert unit_strategy.get_default_key_columns() == ["office_phone", "vertical"]

        contact_strategy = UniversalResolutionStrategy(
            entity_type="contact",
            index_cache=index_cache,
        )
        assert contact_strategy.get_default_key_columns() == [
            "office_phone",
            "contact_phone",
            "contact_email",
        ]

        offer_strategy = UniversalResolutionStrategy(
            entity_type="offer",
            index_cache=index_cache,
        )
        assert offer_strategy.get_default_key_columns() == [
            "office_phone",
            "vertical",
            "offer_id",
        ]


class TestUniversalStrategyBackwardsCompatibility:
    """Tests for backwards compatibility with existing Unit phone/vertical behavior."""

    @pytest.mark.asyncio
    async def test_unit_phone_vertical_lookup(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test Unit resolution matches existing UnitResolutionStrategy behavior."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert len(results) == 1
        assert results[0].gid == "unit-1"
        # Backwards compatible gid property
        assert results[0].gid == results[0].gids[0]

    @pytest.mark.asyncio
    async def test_case_insensitive_vertical(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test that vertical matching is case-insensitive."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        # Use uppercase vertical
        results = await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "DENTAL"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert len(results) == 1
        assert results[0].gid == "unit-1"


class TestCriterionValidationIntegration:
    """Tests for criterion validation integration."""

    @pytest.mark.asyncio
    async def test_invalid_criterion_returns_error(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Test that invalid criterion returns INVALID_CRITERIA error."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        # Use unknown field that won't validate
        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=False,
                errors=["Unknown field: invalid_field"],
                normalized_criterion={},
            )

            results = await strategy.resolve(
                criteria=[{"invalid_field": "value"}],
                project_gid="test-project",
                client=MagicMock(),
            )

        assert len(results) == 1
        assert results[0].error == "INVALID_CRITERIA"
        assert results[0].gid is None


class TestIndexUnavailable:
    """Tests for handling unavailable indexes."""

    @pytest.mark.asyncio
    async def test_no_cached_dataframe_no_cache_returns_error(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Test that missing DataFrame returns INDEX_UNAVAILABLE error."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = None

        # Mock validate to pass
        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                errors=[],
                normalized_criterion={"office_phone": "+1234", "vertical": "test"},
            )

            # Mock the _get_dataframe method to return None (no DataFrame available)
            with patch.object(strategy, "_get_dataframe", return_value=None):
                results = await strategy.resolve(
                    criteria=[{"office_phone": "+1234", "vertical": "test"}],
                    project_gid="test-project",
                    client=MagicMock(),
                )

        assert len(results) == 1
        assert results[0].error == "INDEX_UNAVAILABLE"


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_get_shared_index_cache_singleton(self) -> None:
        """Test that get_shared_index_cache returns singleton."""
        reset_shared_index_cache()

        cache1 = get_shared_index_cache()
        cache2 = get_shared_index_cache()

        assert cache1 is cache2

    def test_reset_shared_index_cache(self) -> None:
        """Test that reset clears the singleton."""
        cache1 = get_shared_index_cache()
        reset_shared_index_cache()
        cache2 = get_shared_index_cache()

        assert cache1 is not cache2

    def test_get_universal_strategy_returns_strategy(self) -> None:
        """Test get_universal_strategy factory function."""
        # Mock is_entity_resolvable to return True
        with patch(
            "autom8_asana.services.resolver.is_entity_resolvable", return_value=True
        ):
            strategy = get_universal_strategy("unit")

        assert strategy is not None
        assert isinstance(strategy, UniversalResolutionStrategy)
        assert strategy.entity_type == "unit"

    def test_get_strategy_returns_none_for_unknown(self) -> None:
        """Test get_strategy returns None for unknown entity."""
        from autom8_asana.services.resolver import get_strategy

        # Mock is_entity_resolvable to return False
        with patch(
            "autom8_asana.services.resolver.is_entity_resolvable", return_value=False
        ):
            strategy = get_strategy("unknown_entity")

        assert strategy is None


class TestResolverIntegration:
    """Tests for resolver.py integration."""

    def test_get_strategy_imported_from_resolver(self) -> None:
        """Test that get_strategy is exported from resolver module."""
        from autom8_asana.services.resolver import get_strategy

        assert callable(get_strategy)

    def test_get_strategy_in_resolver_all(self) -> None:
        """Test that get_strategy is in __all__."""
        from autom8_asana.services import resolver

        assert "get_strategy" in resolver.__all__


class TestResolutionResultIntegration:
    """Tests for ResolutionResult integration."""

    @pytest.mark.asyncio
    async def test_result_to_dict(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test that results can be converted to dict for API response."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        result_dict = results[0].to_dict()

        assert "gid" in result_dict
        assert "gids" in result_dict
        assert "match_count" in result_dict
        assert result_dict["gid"] == "unit-1"
        assert result_dict["gids"] == ["unit-1"]
        assert result_dict["match_count"] == 1

    @pytest.mark.asyncio
    async def test_not_found_result_to_dict(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test NOT_FOUND result to_dict."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+10000000000", "vertical": "unknown"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        result_dict = results[0].to_dict()

        assert result_dict["gid"] is None
        assert result_dict["gids"] == []
        assert result_dict["match_count"] == 0
        assert result_dict["error"] == "NOT_FOUND"


class TestDynamicIndexBuilding:
    """Tests for dynamic index building behavior."""

    @pytest.mark.asyncio
    async def test_builds_index_for_criterion_columns(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test that index is built for the specific columns in criterion."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        # Resolve with specific columns
        await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        # Check index was built for those columns
        cached_index = index_cache.get(
            entity_type="unit",
            key_columns=["office_phone", "vertical"],
        )
        assert cached_index is not None
        assert sorted(cached_index.key_columns) == ["office_phone", "vertical"]

    @pytest.mark.asyncio
    async def test_different_column_combos_different_indexes(
        self, contact_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Test that different column combinations create different indexes."""
        strategy = UniversalResolutionStrategy(
            entity_type="contact",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = contact_dataframe

        # Mock validation to pass for different column combinations
        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            # First call: contact_email lookup
            mock_validate.return_value = MagicMock(
                is_valid=True,
                errors=[],
                normalized_criterion={"contact_email": "a@test.com"},
            )
            await strategy.resolve(
                criteria=[{"contact_email": "a@test.com"}],
                project_gid="test-project",
                client=MagicMock(),
            )

            # Second call: contact_phone lookup
            mock_validate.return_value = MagicMock(
                is_valid=True,
                errors=[],
                normalized_criterion={"contact_phone": "111-111-1111"},
            )
            await strategy.resolve(
                criteria=[{"contact_phone": "111-111-1111"}],
                project_gid="test-project",
                client=MagicMock(),
            )

        # Both indexes should be cached with actual column names
        email_index = index_cache.get("contact", ["contact_email"])
        phone_index = index_cache.get("contact", ["contact_phone"])

        assert email_index is not None
        assert phone_index is not None
        assert email_index is not phone_index


# --- Field Enrichment Tests ---


class TestEnrichFromDataframe:
    """Tests for _enrich_from_dataframe method.

    Per TDD-FIELDS-ENRICHMENT-001: Post-lookup enrichment from DataFrame.
    """

    def test_enrichment_returns_requested_fields(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Enrichment returns only requested fields plus gid."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        df = pl.DataFrame(
            {
                "gid": ["123", "456", "789"],
                "name": ["A", "B", "C"],
                "vertical": ["dental", "medical", "chiro"],
                "mrr": [100.0, 200.0, 300.0],
            }
        )

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123", "456"],
            fields=["name", "vertical"],
        )

        assert len(result) == 2
        assert result[0] == {"gid": "123", "name": "A", "vertical": "dental"}
        assert result[1] == {"gid": "456", "name": "B", "vertical": "medical"}
        # mrr not included (not requested)
        assert "mrr" not in result[0]

    def test_enrichment_always_includes_gid(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """GID is always included even if not in requested fields."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        df = pl.DataFrame(
            {
                "gid": ["123"],
                "name": ["Test"],
            }
        )

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123"],
            fields=["name"],  # gid not in list
        )

        assert "gid" in result[0]
        assert result[0]["gid"] == "123"

    def test_enrichment_preserves_gid_order(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Results returned in same order as input GIDs."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        df = pl.DataFrame(
            {
                "gid": ["123", "456", "789"],
                "name": ["A", "B", "C"],
            }
        )

        # Request in different order than DataFrame
        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["789", "123", "456"],
            fields=["name"],
        )

        assert result[0]["gid"] == "789"
        assert result[1]["gid"] == "123"
        assert result[2]["gid"] == "456"

    def test_enrichment_handles_missing_gid(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Missing GID returns dict with just gid."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        df = pl.DataFrame(
            {
                "gid": ["123"],
                "name": ["A"],
            }
        )

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123", "999"],  # 999 not in DataFrame
            fields=["name"],
        )

        assert len(result) == 2
        assert result[0] == {"gid": "123", "name": "A"}
        assert result[1] == {"gid": "999"}  # Only gid returned

    def test_enrichment_empty_gids(self, index_cache: DynamicIndexCache) -> None:
        """Empty GID list returns empty result."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        df = pl.DataFrame({"gid": ["123"], "name": ["A"]})

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=[],
            fields=["name"],
        )

        assert result == []

    def test_enrichment_none_dataframe(self, index_cache: DynamicIndexCache) -> None:
        """None DataFrame returns empty result."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        result = strategy._enrich_from_dataframe(
            df=None,
            gids=["123"],
            fields=["name"],
        )

        assert result == []

    def test_enrichment_skips_missing_columns(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Missing columns in DataFrame are skipped gracefully."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )

        df = pl.DataFrame(
            {
                "gid": ["123"],
                "name": ["A"],
                # no 'vertical' column
            }
        )

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123"],
            fields=["name", "vertical"],  # vertical doesn't exist
        )

        assert result[0] == {"gid": "123", "name": "A"}
        # vertical not in result (column doesn't exist)


class TestResolveWithFields:
    """Tests for resolve() with requested_fields.

    Per TDD-FIELDS-ENRICHMENT-001: Tests for field enrichment integration.
    """

    @pytest.mark.asyncio
    async def test_resolve_without_fields_no_enrichment(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Resolve without fields returns no data."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
            requested_fields=None,  # No fields
        )

        assert len(results) == 1
        assert results[0].gid == "unit-1"
        assert results[0].match_context is None

    @pytest.mark.asyncio
    async def test_resolve_with_fields_returns_data(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Resolve with fields returns enriched data."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
            requested_fields=["name"],  # Request name field
        )

        assert len(results) == 1
        assert results[0].gid == "unit-1"
        assert results[0].match_context is not None
        assert len(results[0].match_context) == 1
        assert results[0].match_context[0]["gid"] == "unit-1"
        assert results[0].match_context[0]["name"] == "Unit A"

    @pytest.mark.asyncio
    async def test_resolve_not_found_with_fields_no_data(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Resolve with no matches returns no data even when fields requested."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+10000000000", "vertical": "unknown"}],
            project_gid="test-project",
            client=MagicMock(),
            requested_fields=["name"],  # Request name field but no match
        )

        assert len(results) == 1
        assert results[0].gid is None
        assert results[0].error == "NOT_FOUND"
        assert results[0].match_context is None  # No enrichment for no matches

    @pytest.mark.asyncio
    async def test_resolve_multi_match_with_fields(
        self, contact_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Resolve with multiple matches returns data for all matches."""
        strategy = UniversalResolutionStrategy(
            entity_type="contact",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = contact_dataframe

        # Mock validation to pass
        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                errors=[],
                normalized_criterion={"contact_email": "a@test.com"},
            )

            results = await strategy.resolve(
                criteria=[{"contact_email": "a@test.com"}],
                project_gid="test-project",
                client=MagicMock(),
                requested_fields=["name"],
            )

        assert len(results) == 1
        result = results[0]
        assert result.match_count == 2
        assert result.match_context is not None
        assert len(result.match_context) == 2
        # Both matches should have name field
        names = [item["name"] for item in result.match_context]
        assert "Contact A" in names
        assert "Contact C" in names


# --- Batch Parallelization Tests (TDD-B03) ---


class TestBatchParallelization:
    """Tests for group-and-gather parallel batch resolution.

    Per TDD-B03: Verifies that resolve() groups criteria by key_columns,
    builds each index once, executes groups concurrently, and preserves
    result ordering and error isolation.
    """

    @pytest.mark.asyncio
    async def test_multi_group_parallel_execution(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Criteria with different key_columns produce distinct groups.

        Submits criteria mixing phone+vertical lookups with offer_id lookups.
        Asserts _get_or_build_index is called exactly once per distinct key_columns.
        """
        df = pl.DataFrame(
            {
                "gid": ["unit-1", "unit-2", "offer-1"],
                "office_phone": ["+11111111111", "+12222222222", "+13333333333"],
                "vertical": ["dental", "medical", "dental"],
                "offer_id": ["OID001", "OID002", "OID003"],
            }
        )

        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = df

        # Track _get_or_build_index calls with key_columns recorded
        build_calls: list[list[str]] = []
        original_get_or_build = strategy._get_or_build_index

        async def tracking_get_or_build(
            project_gid: str, key_columns: list[str], client: object
        ):
            build_calls.append(key_columns)
            return await original_get_or_build(
                project_gid=project_gid, key_columns=key_columns, client=client
            )

        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            # Return different normalized criteria to produce 2 groups
            mock_validate.side_effect = [
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={
                        "office_phone": "+11111111111",
                        "vertical": "dental",
                    },
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"offer_id": "OID003"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={
                        "office_phone": "+12222222222",
                        "vertical": "medical",
                    },
                ),
            ]

            with patch.object(
                strategy, "_get_or_build_index", side_effect=tracking_get_or_build
            ):
                results = await strategy.resolve(
                    criteria=[
                        {"office_phone": "+11111111111", "vertical": "dental"},
                        {"offer_id": "OID003"},
                        {"office_phone": "+12222222222", "vertical": "medical"},
                    ],
                    project_gid="test-project",
                    client=MagicMock(),
                )

        # Two distinct groups: (office_phone, vertical) and (offer_id,)
        assert len(build_calls) == 2
        sorted_calls = sorted([tuple(sorted(c)) for c in build_calls])
        assert ("offer_id",) in sorted_calls
        assert ("office_phone", "vertical") in sorted_calls

        # All 3 criteria should have results
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_result_ordering_preserved(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Results match input order regardless of group execution order.

        Submits 5 criteria with alternating key_columns patterns and verifies
        results[i] corresponds to criteria[i].
        """
        df = pl.DataFrame(
            {
                "gid": ["g-0", "g-1", "g-2", "g-3", "g-4"],
                "office_phone": ["p0", "p1", "p2", "p3", "p4"],
                "vertical": ["v0", "v1", "v2", "v3", "v4"],
                "offer_id": ["oid-0", "oid-1", "oid-2", "oid-3", "oid-4"],
            }
        )

        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = df

        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            # Alternating: phone+vertical, offer_id, phone+vertical, offer_id, phone+vertical
            mock_validate.side_effect = [
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p0", "vertical": "v0"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"offer_id": "oid-1"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p2", "vertical": "v2"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"offer_id": "oid-3"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p4", "vertical": "v4"},
                ),
            ]

            results = await strategy.resolve(
                criteria=[
                    {"office_phone": "p0", "vertical": "v0"},
                    {"offer_id": "oid-1"},
                    {"office_phone": "p2", "vertical": "v2"},
                    {"offer_id": "oid-3"},
                    {"office_phone": "p4", "vertical": "v4"},
                ],
                project_gid="test-project",
                client=MagicMock(),
            )

        assert len(results) == 5
        assert results[0].gid == "g-0"
        assert results[1].gid == "g-1"
        assert results[2].gid == "g-2"
        assert results[3].gid == "g-3"
        assert results[4].gid == "g-4"

    @pytest.mark.asyncio
    async def test_per_criterion_error_isolation(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """One criterion's lookup error does not affect others in same group.

        Uses a mock index where one lookup raises an exception, verifying
        that sibling criteria in the same group still resolve correctly.
        """
        from autom8_asana.services.dynamic_index import DynamicIndex

        df = pl.DataFrame(
            {
                "gid": ["g-0", "g-1", "g-2"],
                "office_phone": ["p0", "p1", "p2"],
                "vertical": ["v0", "v1", "v2"],
            }
        )

        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = df

        # Create a real index, then patch its lookup to fail on specific input
        real_index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone", "vertical"],
            value_column="gid",
        )

        original_lookup = real_index.lookup

        def failing_lookup(criterion: dict) -> list[str]:
            if criterion.get("office_phone") == "p1":
                raise RuntimeError("Simulated lookup failure")
            return original_lookup(criterion)

        real_index.lookup = failing_lookup  # type: ignore[method-assign]

        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.side_effect = [
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p0", "vertical": "v0"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p1", "vertical": "v1"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p2", "vertical": "v2"},
                ),
            ]

            with patch.object(
                strategy,
                "_get_or_build_index",
                new_callable=AsyncMock,
                return_value=real_index,
            ):
                results = await strategy.resolve(
                    criteria=[
                        {"office_phone": "p0", "vertical": "v0"},
                        {"office_phone": "p1", "vertical": "v1"},
                        {"office_phone": "p2", "vertical": "v2"},
                    ],
                    project_gid="test-project",
                    client=MagicMock(),
                )

        assert len(results) == 3
        # First and third succeed
        assert results[0].gid == "g-0"
        assert results[0].error is None
        assert results[2].gid == "g-2"
        assert results[2].error is None
        # Second has LOOKUP_ERROR
        assert results[1].error == "LOOKUP_ERROR"
        assert results[1].gid is None

    @pytest.mark.asyncio
    async def test_cross_group_error_isolation(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """One group's index build failure does not affect other groups.

        Mocks _get_or_build_index to raise for one key_columns group
        but succeed for another, verifying independent error handling.
        """
        from autom8_asana.services.dynamic_index import DynamicIndex

        df = pl.DataFrame(
            {
                "gid": ["g-0", "g-1"],
                "office_phone": ["p0", "p1"],
                "vertical": ["v0", "v1"],
                "offer_id": ["oid-0", "oid-1"],
            }
        )

        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = df

        # Build a real index for phone+vertical only
        phone_index = DynamicIndex.from_dataframe(
            df=df,
            key_columns=["office_phone", "vertical"],
            value_column="gid",
        )

        async def selective_build(
            project_gid: str, key_columns: list[str], client: object
        ):
            if sorted(key_columns) == ["offer_id"]:
                raise ConnectionError("Simulated index build failure")
            return phone_index

        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.side_effect = [
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p0", "vertical": "v0"},
                ),
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"offer_id": "oid-1"},
                ),
            ]

            with patch.object(
                strategy, "_get_or_build_index", side_effect=selective_build
            ):
                results = await strategy.resolve(
                    criteria=[
                        {"office_phone": "p0", "vertical": "v0"},
                        {"offer_id": "oid-1"},
                    ],
                    project_gid="test-project",
                    client=MagicMock(),
                )

        assert len(results) == 2
        # Phone+vertical group succeeded
        assert results[0].gid == "g-0"
        assert results[0].error is None
        # Offer group failed with INDEX_UNAVAILABLE
        assert results[1].error == "INDEX_UNAVAILABLE"
        assert results[1].gid is None

    @pytest.mark.asyncio
    async def test_single_criterion_no_regression(
        self, unit_dataframe: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Single criterion works identically to before parallelization.

        Verifies the group-and-gather path does not regress single-criterion
        behavior -- the most common production case.
        """
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = unit_dataframe

        results = await strategy.resolve(
            criteria=[{"office_phone": "+11234567890", "vertical": "dental"}],
            project_gid="test-project",
            client=MagicMock(),
        )

        assert len(results) == 1
        assert results[0].gid == "unit-1"
        assert results[0].error is None
        assert results[0].is_unique

    @pytest.mark.asyncio
    async def test_all_same_key_columns_single_group(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Homogeneous batch creates single group with 1 index build.

        Submits 10 criteria all with same key_columns (office_phone+vertical).
        Verifies _get_or_build_index is called exactly once.
        """
        # Build a DataFrame with 10 rows
        df = pl.DataFrame(
            {
                "gid": [f"g-{i}" for i in range(10)],
                "office_phone": [f"p{i}" for i in range(10)],
                "vertical": [f"v{i}" for i in range(10)],
            }
        )

        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = df

        build_call_count = 0
        original_get_or_build = strategy._get_or_build_index

        async def counting_get_or_build(
            project_gid: str, key_columns: list[str], client: object
        ):
            nonlocal build_call_count
            build_call_count += 1
            return await original_get_or_build(
                project_gid=project_gid, key_columns=key_columns, client=client
            )

        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.side_effect = [
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": f"p{i}", "vertical": f"v{i}"},
                )
                for i in range(10)
            ]

            with patch.object(
                strategy, "_get_or_build_index", side_effect=counting_get_or_build
            ):
                results = await strategy.resolve(
                    criteria=[
                        {"office_phone": f"p{i}", "vertical": f"v{i}"}
                        for i in range(10)
                    ],
                    project_gid="test-project",
                    client=MagicMock(),
                )

        # Only 1 index build call (single group)
        assert build_call_count == 1

        # All 10 results present and correct
        assert len(results) == 10
        for i in range(10):
            assert results[i].gid == f"g-{i}"
            assert results[i].error is None

    @pytest.mark.asyncio
    async def test_validation_failures_excluded_from_groups(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Invalid criteria get INVALID_CRITERIA, valid ones resolve normally.

        Mixes valid and invalid criteria to verify Phase 1 validation
        correctly separates invalid results from grouped resolution.
        """
        df = pl.DataFrame(
            {
                "gid": ["g-0", "g-1"],
                "office_phone": ["p0", "p1"],
                "vertical": ["v0", "v1"],
            }
        )

        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=index_cache,
        )
        strategy._cached_dataframe = df

        with patch(
            "autom8_asana.services.resolver.validate_criterion_for_entity"
        ) as mock_validate:
            mock_validate.side_effect = [
                # criteria[0]: valid
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p0", "vertical": "v0"},
                ),
                # criteria[1]: invalid
                MagicMock(
                    is_valid=False,
                    errors=["Unknown field: bad_field"],
                    normalized_criterion={},
                ),
                # criteria[2]: valid
                MagicMock(
                    is_valid=True,
                    errors=[],
                    normalized_criterion={"office_phone": "p1", "vertical": "v1"},
                ),
                # criteria[3]: invalid
                MagicMock(
                    is_valid=False,
                    errors=["Empty criterion"],
                    normalized_criterion={},
                ),
            ]

            results = await strategy.resolve(
                criteria=[
                    {"office_phone": "p0", "vertical": "v0"},
                    {"bad_field": "value"},
                    {"office_phone": "p1", "vertical": "v1"},
                    {},
                ],
                project_gid="test-project",
                client=MagicMock(),
            )

        assert len(results) == 4
        # Valid criteria resolved correctly
        assert results[0].gid == "g-0"
        assert results[0].error is None
        assert results[2].gid == "g-1"
        assert results[2].error is None
        # Invalid criteria have INVALID_CRITERIA errors
        assert results[1].error == "INVALID_CRITERIA"
        assert results[1].gid is None
        assert results[3].error == "INVALID_CRITERIA"
        assert results[3].gid is None
