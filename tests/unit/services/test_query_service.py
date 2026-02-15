"""Unit tests for QueryService functions.

Tests for validate_fields(), resolve_section(), resolve_section_index(),
and strip_section_conflicts() functions in the query service layer.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.services.errors import InvalidFieldError, UnknownSectionError
from autom8_asana.services.query_service import (
    resolve_section,
    resolve_section_index,
    strip_section_conflicts,
    validate_fields,
)


class TestValidateFields:
    """Tests for validate_fields() function."""

    def _mock_schema(self, column_names: list[str]) -> MagicMock:
        """Create a mock schema with given column names."""
        schema = MagicMock()
        schema.column_names.return_value = column_names
        return schema

    def _patch_registry(self, mock_registry: MagicMock):
        """Patch SchemaRegistry.get_instance at source."""
        return patch(
            "autom8_asana.dataframes.models.registry.SchemaRegistry.get_instance",
            return_value=mock_registry,
        )

    def test_valid_fields_pass_silently(self) -> None:
        """Valid fields should not raise."""
        schema = self._mock_schema(["gid", "name", "section", "vertical"])
        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = schema

        with self._patch_registry(mock_registry):
            validate_fields(["gid", "name"], "offer")

    def test_invalid_fields_raise_invalid_field_error(self) -> None:
        """Invalid fields should raise InvalidFieldError."""
        schema = self._mock_schema(["gid", "name", "section"])
        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = schema

        with self._patch_registry(mock_registry):
            with pytest.raises(InvalidFieldError) as exc_info:
                validate_fields(["gid", "nonexistent"], "offer")

            err = exc_info.value
            assert "nonexistent" in err.invalid_fields
            assert "gid" in err.available_fields
            assert "name" in err.available_fields

    def test_falls_back_to_wildcard_schema(self) -> None:
        """Falls back to '*' schema when entity-specific schema not found."""
        from autom8_asana.dataframes.exceptions import SchemaNotFoundError

        wildcard_schema = self._mock_schema(["gid", "name"])
        mock_registry = MagicMock()
        mock_registry.get_schema.side_effect = [
            SchemaNotFoundError("Offer"),
            wildcard_schema,
        ]

        with self._patch_registry(mock_registry):
            validate_fields(["gid"], "offer")

            calls = mock_registry.get_schema.call_args_list
            assert calls[0].args[0] == "Offer"
            assert calls[1].args[0] == "*"

    def test_empty_fields_list_passes(self) -> None:
        """Empty fields list should not raise."""
        schema = self._mock_schema(["gid", "name"])
        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = schema

        with self._patch_registry(mock_registry):
            validate_fields([], "offer")

    def test_error_contains_sorted_fields(self) -> None:
        """InvalidFieldError should contain sorted invalid and available fields."""
        schema = self._mock_schema(["gid", "name", "section"])
        mock_registry = MagicMock()
        mock_registry.get_schema.return_value = schema

        with self._patch_registry(mock_registry):
            with pytest.raises(InvalidFieldError) as exc_info:
                validate_fields(["zzz", "aaa"], "offer")

            err = exc_info.value
            assert err.invalid_fields == ["aaa", "zzz"]
            assert err.available_fields == ["gid", "name", "section"]


class TestResolveSection:
    """Tests for resolve_section() function."""

    @pytest.mark.asyncio
    async def test_resolves_via_manifest(self) -> None:
        """Section resolved via manifest returns the section name."""
        mock_index = MagicMock()
        mock_index.resolve.return_value = "gid-123"

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_manifest_async",
                new_callable=AsyncMock,
                return_value=mock_index,
            ),
        ):
            result = await resolve_section("ACTIVE", "offer", "proj-123")

        assert result == "ACTIVE"

    @pytest.mark.asyncio
    async def test_falls_back_to_enum(self) -> None:
        """Falls back to enum when manifest resolution returns None."""
        # Manifest index returns None for the section
        mock_manifest_index = MagicMock()
        mock_manifest_index.resolve.return_value = None

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(return_value=None)

        # Enum index resolves it
        mock_enum_index = MagicMock()
        mock_enum_index.resolve.return_value = "gid-456"

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_manifest_async",
                new_callable=AsyncMock,
                return_value=mock_manifest_index,
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_enum_fallback",
                return_value=mock_enum_index,
            ),
        ):
            result = await resolve_section("ACTIVE", "offer", "proj-123")

        assert result == "ACTIVE"

    @pytest.mark.asyncio
    async def test_falls_back_to_enum_on_s3_error(self) -> None:
        """Falls back to enum when S3 transport error occurs."""
        mock_enum_index = MagicMock()
        mock_enum_index.resolve.return_value = "gid-789"

        mock_persistence = MagicMock()
        mock_persistence.is_available = True
        mock_persistence.__aenter__ = AsyncMock(return_value=mock_persistence)
        mock_persistence.__aexit__ = AsyncMock(
            side_effect=ConnectionError("S3 unavailable")
        )

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_enum_fallback",
                return_value=mock_enum_index,
            ),
        ):
            result = await resolve_section("ACTIVE", "offer", "proj-123")

        assert result == "ACTIVE"

    @pytest.mark.asyncio
    async def test_raises_unknown_section_error(self) -> None:
        """Raises UnknownSectionError when section cannot be resolved."""
        mock_enum_index = MagicMock()
        mock_enum_index.resolve.return_value = None

        mock_persistence = MagicMock()
        mock_persistence.is_available = False

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_enum_fallback",
                return_value=mock_enum_index,
            ),
        ):
            with pytest.raises(UnknownSectionError) as exc_info:
                await resolve_section("NONEXISTENT", "offer", "proj-123")

            assert exc_info.value.section_name == "NONEXISTENT"

    @pytest.mark.asyncio
    async def test_persistence_not_available_uses_enum(self) -> None:
        """When persistence is not available, falls through to enum."""
        mock_enum_index = MagicMock()
        mock_enum_index.resolve.return_value = "gid-000"

        mock_persistence = MagicMock()
        mock_persistence.is_available = False

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.SectionPersistence",
                return_value=mock_persistence,
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_enum_fallback",
                return_value=mock_enum_index,
            ),
        ):
            result = await resolve_section("ACTIVE", "offer", "proj-123")

        assert result == "ACTIVE"


class TestResolveSectionIndex:
    """Tests for resolve_section_index() function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_section_name_is_none(self) -> None:
        """Returns None when section_name is None (no section filtering)."""
        result = await resolve_section_index(None, "offer", "proj-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_manifest_first_strategy(self) -> None:
        """Returns manifest-based section index when manifest resolves."""
        mock_manifest_index = MagicMock()
        mock_manifest_index.resolve.return_value = "gid-123"

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
            ) as mock_create,
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_manifest_async",
                new_callable=AsyncMock,
                return_value=mock_manifest_index,
            ),
        ):
            mock_create.return_value = MagicMock()

            result = await resolve_section_index("ACTIVE", "offer", "proj-123")

        assert result is mock_manifest_index

    @pytest.mark.asyncio
    async def test_enum_fallback_when_manifest_fails(self) -> None:
        """Falls back to enum when manifest resolution returns None."""
        mock_manifest_index = MagicMock()
        mock_manifest_index.resolve.return_value = None

        mock_enum_index = MagicMock()

        with (
            patch(
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
            ) as mock_create,
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_manifest_async",
                new_callable=AsyncMock,
                return_value=mock_manifest_index,
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_enum_fallback",
                return_value=mock_enum_index,
            ),
        ):
            mock_create.return_value = MagicMock()

            result = await resolve_section_index("ACTIVE", "offer", "proj-123")

        assert result is mock_enum_index


class TestStripSectionConflicts:
    """Tests for strip_section_conflicts() function."""

    def _make_rows_request(
        self, where=None, section: str | None = None
    ) -> MagicMock:
        """Create a mock RowsRequest-like object for testing.

        Uses the real RowsRequest model to ensure compatibility.
        """
        from autom8_asana.query.models import RowsRequest

        kwargs: dict = {}
        if section is not None:
            kwargs["section"] = section
        if where is not None:
            kwargs["where"] = where
        return RowsRequest(**kwargs)

    def test_no_conflict_when_section_is_none(self) -> None:
        """Returns request unmodified when section_name is None."""
        request = self._make_rows_request(
            where={"field": "section", "op": "eq", "value": "ACTIVE"}
        )
        result = strip_section_conflicts(request, None)
        assert result is request

    def test_no_conflict_when_where_is_none(self) -> None:
        """Returns request unmodified when where clause is None."""
        request = self._make_rows_request(section="ACTIVE")
        result = strip_section_conflicts(request, "ACTIVE")
        assert result is request

    def test_no_conflict_when_no_section_in_predicate(self) -> None:
        """Returns request unmodified when predicate has no section fields."""
        request = self._make_rows_request(
            where={"field": "vertical", "op": "eq", "value": "dental"},
            section="ACTIVE",
        )
        result = strip_section_conflicts(request, "ACTIVE")
        assert result is request

    def test_strips_section_predicate_on_conflict(self) -> None:
        """Strips section predicates when section param and predicate both present."""
        request = self._make_rows_request(
            where={
                "and": [
                    {"field": "section", "op": "eq", "value": "ACTIVE"},
                    {"field": "vertical", "op": "eq", "value": "dental"},
                ]
            },
            section="PAUSED",
        )
        result = strip_section_conflicts(request, "PAUSED")

        # Should return a new request with section predicates stripped
        assert result is not request
        # The vertical predicate should survive
        assert result.where is not None

    def test_returns_none_where_when_only_section_predicate(self) -> None:
        """When the only predicate is a section comparison, where becomes None."""
        request = self._make_rows_request(
            where={"field": "section", "op": "eq", "value": "ACTIVE"},
            section="PAUSED",
        )
        result = strip_section_conflicts(request, "PAUSED")

        # The section predicate should be stripped, leaving None
        assert result.where is None


class TestEntityServiceProjectRegistry:
    """Tests for EntityService.project_registry property."""

    def test_project_registry_property_returns_registry(self) -> None:
        """project_registry property exposes _project_registry."""
        from autom8_asana.services.entity_service import EntityService

        mock_entity_registry = MagicMock()
        mock_project_registry = MagicMock()

        service = EntityService(
            entity_registry=mock_entity_registry,
            project_registry=mock_project_registry,
        )

        assert service.project_registry is mock_project_registry

    def test_project_registry_is_read_only(self) -> None:
        """project_registry property is read-only (no setter)."""
        from autom8_asana.services.entity_service import EntityService

        mock_entity_registry = MagicMock()
        mock_project_registry = MagicMock()

        service = EntityService(
            entity_registry=mock_entity_registry,
            project_registry=mock_project_registry,
        )

        with pytest.raises(AttributeError):
            service.project_registry = MagicMock()  # type: ignore[misc]
