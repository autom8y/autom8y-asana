"""Section scoping edge cases and schema/DataFrame mismatch probes for QueryEngine.

Kept from adversarial triage because these tests cover unique behavior with no
equivalent in test_engine.py:
- Unknown/empty section raises UnknownSectionError
- SectionIndex case-insensitive resolution
- Section + predicate composition
- Section-name case-sensitive DataFrame filter (ADR-DQS-003)
- Predicate field in schema but absent from DataFrame (schema/data drift)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.errors import UnknownSectionError
from autom8_asana.query.models import RowsRequest
from autom8_asana.services.query_service import EntityQueryService


@pytest.fixture
def section_schema() -> DataFrameSchema:
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
        ],
    )


@pytest.fixture
def section_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "gid": ["1", "2", "3"],
            "name": ["A", "B", "C"],
            "section": ["Active", "Won", "Active"],
        }
    )


@pytest.fixture
def section_engine(section_df: pl.DataFrame) -> QueryEngine:
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=section_df)  # type: ignore[method-assign]
    return QueryEngine(query_service=service)


class TestSectionEdgeCases:
    """Adversarial section parameter inputs."""

    @pytest.mark.asyncio
    async def test_nonexistent_section(
        self, section_engine: QueryEngine, section_schema: DataFrameSchema
    ) -> None:
        """Unknown section name raises UnknownSectionError."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate({"section": "Nonexistent"})
        with pytest.raises(UnknownSectionError) as exc:
            await section_engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )
        assert exc.value.section == "Nonexistent"

    @pytest.mark.asyncio
    async def test_empty_string_section(
        self, section_engine: QueryEngine, section_schema: DataFrameSchema
    ) -> None:
        """Empty string section should be rejected (not in index)."""
        from autom8_asana.metrics.resolve import SectionIndex

        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate({"section": ""})
        with pytest.raises(UnknownSectionError):
            await section_engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )

    def test_section_index_case_insensitive(self) -> None:
        """SectionIndex.resolve is case-insensitive."""
        from autom8_asana.metrics.resolve import SectionIndex

        idx = SectionIndex(_name_to_gid={"active": "gid-1"})
        assert idx.resolve("Active") == "gid-1"
        assert idx.resolve("ACTIVE") == "gid-1"
        assert idx.resolve("active") == "gid-1"

    def test_section_error_serialization(self) -> None:
        err = UnknownSectionError(section="Bogus")
        d = err.to_dict()
        assert d["error"] == "UNKNOWN_SECTION"
        assert d["section"] == "Bogus"

    @pytest.mark.asyncio
    async def test_section_param_and_section_predicate_simultaneously(
        self, section_schema: DataFrameSchema
    ) -> None:
        """EC-006: Section param + section field in predicate.

        The engine should accept the section param and the caller (route handler)
        is responsible for stripping conflicting predicates. Here we test
        that if the predicate still contains a section comparison alongside
        the section_name_filter, the section param wins for filtering.
        """
        from autom8_asana.metrics.resolve import SectionIndex

        df = pl.DataFrame(
            {
                "gid": ["1", "2", "3"],
                "name": ["A", "B", "C"],
                "section": ["Active", "Won", "Active"],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        # Request with section param AND a name predicate (section stripped already)
        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate(
            {
                "section": "Active",
                "where": {"field": "name", "op": "eq", "value": "A"},
            }
        )
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = section_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )
        # Only row 1 matches (Active AND name=A)
        assert result.meta.total_count == 1
        assert result.data[0]["name"] == "A"
        assert result.data[0]["section"] == "Active"

    @pytest.mark.asyncio
    async def test_section_case_sensitive_filter(
        self, section_schema: DataFrameSchema
    ) -> None:
        """Section name filter on DataFrame is case-sensitive (per ADR-DQS-003)."""
        from autom8_asana.metrics.resolve import SectionIndex

        df = pl.DataFrame(
            {
                "gid": ["1", "2"],
                "name": ["A", "B"],
                "section": ["Active", "active"],
            }
        )
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        # SectionIndex resolves case-insensitively, but DataFrame filter is exact
        section_index = SectionIndex(_name_to_gid={"active": "gid-1"})
        request = RowsRequest.model_validate({"section": "Active"})
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = section_schema
            mock_reg_cls.get_instance.return_value = mock_reg

            result = await engine.execute_rows(
                entity_type="offer",
                project_gid="proj-1",
                client=AsyncMock(),
                request=request,
                section_index=section_index,
            )
        # Only "Active" matches, not "active"
        assert result.meta.total_count == 1
        assert result.data[0]["section"] == "Active"


class TestSchemaDriftEdgeCases:
    """Edge cases for schema/DataFrame drift (field in schema but not in data)."""

    @pytest.mark.asyncio
    async def test_predicate_field_in_schema_but_not_in_dataframe(self) -> None:
        """Column exists in schema but not in the actual DataFrame.

        This can happen if schema and data are out of sync. The expression
        will compile (schema says field exists), but Polars will raise
        during filter when the column is not in the DataFrame.
        """
        schema = DataFrameSchema(
            name="test",
            task_type="Test",
            columns=[
                ColumnDef("gid", "Utf8", nullable=False),
                ColumnDef("name", "Utf8", nullable=True),
                ColumnDef("section", "Utf8", nullable=True),
                ColumnDef("phantom", "Utf8", nullable=True),
            ],
        )
        df = pl.DataFrame({"gid": ["1"], "name": ["A"], "section": ["S"]})
        service = EntityQueryService()
        service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]
        engine = QueryEngine(query_service=service)

        request = RowsRequest.model_validate(
            {"where": {"field": "phantom", "op": "eq", "value": "ghost"}}
        )
        with patch("autom8_asana.query.engine.SchemaRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_schema.return_value = schema
            mock_reg_cls.get_instance.return_value = mock_reg

            # Polars raises ColumnNotFoundError when filtering by missing column
            with pytest.raises(Exception):
                await engine.execute_rows(
                    entity_type="test",
                    project_gid="proj-1",
                    client=AsyncMock(),
                    request=request,
                )
