"""Unit tests for QueryService functions.

Tests for validate_fields() and resolve_section() functions
extracted from query.py during I2-S2 wiring.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.services.errors import InvalidFieldError, UnknownSectionError
from autom8_asana.services.query_service import resolve_section, validate_fields


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
