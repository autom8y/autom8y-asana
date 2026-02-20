"""Tests for classification virtual filter on RowsRequest and QueryEngine.

Covers S-2 implementation:
- RowsRequest model validation (classification field, mutual exclusion)
- QueryEngine._resolve_classification() expansion logic
- QueryEngine.execute_rows() integration with classification filter
- Error cases: unknown entity type, invalid classification value
- Backward compatibility: classification=None has no effect
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.models.business.activity import (
    CLASSIFIERS,
    OFFER_CLASSIFIER,
    AccountActivity,
)
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import ClassificationError
from autom8_asana.query.models import RowsRequest
from autom8_asana.services.query_service import EntityQueryService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_schema() -> DataFrameSchema:
    """Schema matching the sample DataFrame columns."""
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
            ColumnDef("vertical", "Utf8", nullable=True),
        ],
    )


@pytest.fixture
def sample_df() -> pl.DataFrame:
    """DataFrame with sections spanning multiple classification groups.

    Uses actual section names from the OFFER_CLASSIFIER definition
    to ensure realistic filtering behavior.
    """
    return pl.DataFrame(
        {
            "gid": ["1", "2", "3", "4", "5", "6", "7"],
            "name": [
                "Offer A",
                "Offer B",
                "Offer C",
                "Offer D",
                "Offer E",
                "Offer F",
                "Offer G",
            ],
            "section": [
                "ACTIVE",       # active classification
                "STAGING",      # active classification
                "ACTIVATING",   # activating classification
                "INACTIVE",     # inactive classification
                "Complete",     # ignored classification
                "STAGED",       # active classification
                "Onboarding",   # activating classification (unit classifier)
            ],
            "vertical": [
                "dental",
                "medical",
                "dental",
                "medical",
                "dental",
                "medical",
                "dental",
            ],
        }
    )


@pytest.fixture
def mock_query_service(sample_df: pl.DataFrame) -> EntityQueryService:
    """EntityQueryService with mocked get_dataframe."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=sample_df)  # type: ignore[method-assign]
    return service


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def engine(mock_query_service: EntityQueryService) -> QueryEngine:
    return QueryEngine(query_service=mock_query_service)


def _patch_schema(schema: DataFrameSchema):
    """Context manager to patch SchemaRegistry for tests."""
    return patch(
        "autom8_asana.query.engine.SchemaRegistry",
        **{
            "return_value.get_schema.return_value": schema,
            "get_instance.return_value.get_schema.return_value": schema,
        },
    )


# ---------------------------------------------------------------------------
# RowsRequest Model Validation
# ---------------------------------------------------------------------------


class TestRowsRequestClassification:
    """Model-level validation for the classification field."""

    def test_classification_field_accepted(self) -> None:
        """RowsRequest with classification='active' is valid."""
        request = RowsRequest.model_validate({"classification": "active"})
        assert request.classification == "active"
        assert request.section is None

    def test_classification_none_by_default(self) -> None:
        """RowsRequest without classification defaults to None."""
        request = RowsRequest.model_validate({})
        assert request.classification is None

    def test_section_and_classification_mutually_exclusive(self) -> None:
        """RowsRequest with both section and classification raises ValidationError."""
        with pytest.raises(ValueError, match="mutually exclusive"):
            RowsRequest.model_validate(
                {"section": "ACTIVE", "classification": "active"}
            )

    def test_section_alone_still_works(self) -> None:
        """RowsRequest with section alone is unaffected by new field."""
        request = RowsRequest.model_validate({"section": "ACTIVE"})
        assert request.section == "ACTIVE"
        assert request.classification is None

    def test_classification_with_other_fields(self) -> None:
        """classification coexists with where, select, limit, etc."""
        request = RowsRequest.model_validate(
            {
                "classification": "active",
                "where": {"field": "vertical", "op": "eq", "value": "dental"},
                "select": ["gid", "name"],
                "limit": 50,
            }
        )
        assert request.classification == "active"
        assert request.where is not None
        assert request.limit == 50


# ---------------------------------------------------------------------------
# QueryEngine._resolve_classification Unit Tests
# ---------------------------------------------------------------------------


class TestResolveClassification:
    """Direct tests for _resolve_classification method."""

    def test_none_returns_none(self, engine: QueryEngine) -> None:
        """classification=None returns None (no-op)."""
        result = engine._resolve_classification(None, "offer")
        assert result is None

    def test_active_returns_active_sections(self, engine: QueryEngine) -> None:
        """classification='active' returns the ACTIVE section set from classifier."""
        result = engine._resolve_classification("active", "offer")
        assert result is not None
        expected = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)
        assert result == expected
        # Verify known active sections are present (lowercase)
        assert "active" in result
        assert "staging" in result
        assert "staged" in result

    def test_activating_returns_activating_sections(
        self, engine: QueryEngine
    ) -> None:
        """classification='activating' returns ACTIVATING section set."""
        result = engine._resolve_classification("activating", "offer")
        assert result is not None
        expected = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVATING)
        assert result == expected
        assert "activating" in result

    def test_inactive_returns_inactive_sections(self, engine: QueryEngine) -> None:
        """classification='inactive' returns INACTIVE section set."""
        result = engine._resolve_classification("inactive", "offer")
        assert result is not None
        expected = OFFER_CLASSIFIER.sections_for(AccountActivity.INACTIVE)
        assert result == expected
        assert "inactive" in result

    def test_ignored_returns_ignored_sections(self, engine: QueryEngine) -> None:
        """classification='ignored' returns IGNORED section set."""
        result = engine._resolve_classification("ignored", "offer")
        assert result is not None
        expected = OFFER_CLASSIFIER.sections_for(AccountActivity.IGNORED)
        assert result == expected
        assert "complete" in result

    def test_case_insensitive_input(self, engine: QueryEngine) -> None:
        """classification='ACTIVE' is accepted (case-insensitive)."""
        result = engine._resolve_classification("ACTIVE", "offer")
        assert result is not None
        expected = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)
        assert result == expected

    def test_unit_entity_type(self, engine: QueryEngine) -> None:
        """classification works for 'unit' entity type."""
        result = engine._resolve_classification("active", "unit")
        assert result is not None
        assert "active" in result
        assert "month 1" in result

    def test_unknown_entity_type_raises(self, engine: QueryEngine) -> None:
        """Entity type with no classifier raises ClassificationError."""
        with pytest.raises(ClassificationError, match="No classifier registered"):
            engine._resolve_classification("active", "business")

    def test_unknown_entity_type_lists_available(
        self, engine: QueryEngine
    ) -> None:
        """Error message includes available entity types."""
        with pytest.raises(ClassificationError) as exc_info:
            engine._resolve_classification("active", "contact")
        assert "offer" in str(exc_info.value.message)
        assert "unit" in str(exc_info.value.message)

    def test_invalid_classification_value_raises(
        self, engine: QueryEngine
    ) -> None:
        """Invalid classification value raises ClassificationError."""
        with pytest.raises(ClassificationError, match="Invalid classification value"):
            engine._resolve_classification("bogus", "offer")

    def test_invalid_classification_lists_valid_values(
        self, engine: QueryEngine
    ) -> None:
        """Error message includes valid classification values."""
        with pytest.raises(ClassificationError) as exc_info:
            engine._resolve_classification("bogus", "offer")
        for activity in AccountActivity:
            assert activity.value in str(exc_info.value.message)


# ---------------------------------------------------------------------------
# QueryEngine.execute_rows() Integration with Classification
# ---------------------------------------------------------------------------


class TestClassificationQueryExecution:
    """Integration tests for classification filtering through execute_rows."""

    @pytest.mark.asyncio
    async def test_active_classification_filters_correctly(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """classification='active' returns only rows in ACTIVE-classified sections."""
        request = RowsRequest.model_validate({"classification": "active"})
        with _patch_schema(test_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        # From sample_df: ACTIVE, STAGING, STAGED are active-classified
        assert result.meta.total_count == 3
        section_names = {row["section"] for row in result.data}
        # All returned sections should be in the active classification
        for section_name in section_names:
            classification = OFFER_CLASSIFIER.classify(section_name)
            assert classification == AccountActivity.ACTIVE

    @pytest.mark.asyncio
    async def test_activating_classification_filters_correctly(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """classification='activating' returns only ACTIVATING-classified rows."""
        request = RowsRequest.model_validate({"classification": "activating"})
        with _patch_schema(test_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        # ACTIVATING is the only activating section in the sample
        assert result.meta.total_count == 1
        assert result.data[0]["section"] == "ACTIVATING"

    @pytest.mark.asyncio
    async def test_classification_with_where_predicate(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """classification combined with where predicate ANDs both filters."""
        request = RowsRequest.model_validate(
            {
                "classification": "active",
                "where": {"field": "vertical", "op": "eq", "value": "dental"},
                "select": ["gid", "name", "vertical"],
            }
        )
        with _patch_schema(test_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        # Active dental: only "Offer A" (ACTIVE, dental)
        assert result.meta.total_count == 1
        assert result.data[0]["name"] == "Offer A"
        assert result.data[0]["vertical"] == "dental"

    @pytest.mark.asyncio
    async def test_classification_none_no_effect(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """classification=None returns all rows (backward compatible)."""
        request = RowsRequest.model_validate({})
        with _patch_schema(test_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 7  # All rows

    @pytest.mark.asyncio
    async def test_unknown_entity_type_raises_classification_error(
        self,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """classification on entity_type with no classifier raises ClassificationError."""
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(  # type: ignore[method-assign]
            return_value=pl.DataFrame(
                {"gid": ["1"], "name": ["A"], "section": ["X"], "vertical": ["v"]}
            )
        )
        engine = QueryEngine(query_service=service)

        request = RowsRequest.model_validate({"classification": "active"})
        with _patch_schema(test_schema):
            with pytest.raises(ClassificationError, match="No classifier registered"):
                await engine.execute_rows(
                    entity_type="business",
                    project_gid="proj-123",
                    client=mock_client,
                    request=request,
                )

    @pytest.mark.asyncio
    async def test_invalid_classification_value_raises(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """Invalid classification value raises ClassificationError."""
        request = RowsRequest.model_validate({"classification": "bogus"})
        with _patch_schema(test_schema):
            with pytest.raises(ClassificationError, match="Invalid classification"):
                await engine.execute_rows(
                    entity_type="offer",
                    project_gid="proj-123",
                    client=mock_client,
                    request=request,
                )

    @pytest.mark.asyncio
    async def test_classification_case_insensitive_section_match(
        self,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """Classification filter matches sections case-insensitively.

        The classifier stores lowercase keys, but DataFrame sections
        use original case (e.g., 'ACTIVE', 'Staging'). The filter
        must match regardless of case.
        """
        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "section": ["ACTIVE", "active", "Active"],
                "vertical": ["d", "d", "d"],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        request = RowsRequest.model_validate({"classification": "active"})
        with _patch_schema(test_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        # All three rows should match regardless of case
        assert result.meta.total_count == 3

    @pytest.mark.asyncio
    async def test_classification_with_select(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """classification works with select fields."""
        request = RowsRequest.model_validate(
            {
                "classification": "active",
                "select": ["name", "section"],
            }
        )
        with _patch_schema(test_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 3
        for row in result.data:
            assert "gid" in row
            assert "name" in row
            assert "section" in row

    @pytest.mark.asyncio
    async def test_classification_with_pagination(
        self,
        engine: QueryEngine,
        mock_client: AsyncMock,
        test_schema: DataFrameSchema,
    ) -> None:
        """classification works with limit/offset pagination."""
        request = RowsRequest.model_validate(
            {
                "classification": "active",
                "limit": 2,
                "offset": 1,
            }
        )
        with _patch_schema(test_schema):
            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-123",
                client=mock_client,
                request=request,
            )

        assert result.meta.total_count == 3  # Total active
        assert result.meta.returned_count == 2  # Limited to 2
        assert result.meta.offset == 1


# ---------------------------------------------------------------------------
# ClassificationError Serialization
# ---------------------------------------------------------------------------


class TestClassificationErrorSerialization:
    """Test that ClassificationError serializes correctly for HTTP responses."""

    def test_to_dict(self) -> None:
        """ClassificationError.to_dict() produces expected structure."""
        err = ClassificationError(
            message="No classifier registered for entity type 'business'"
        )
        d = err.to_dict()
        assert d["error"] == "INVALID_CLASSIFICATION"
        assert "business" in d["message"]

    def test_error_status_mapping(self) -> None:
        """ClassificationError maps to HTTP 400 in query route."""
        from autom8_asana.api.routes.query import _ERROR_STATUS

        assert _ERROR_STATUS.get(ClassificationError) == 400
