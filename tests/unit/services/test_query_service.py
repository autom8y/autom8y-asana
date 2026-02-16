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


# ============================================================================
# Adversarial Tests -- QA Phase 3 validation
# ============================================================================


class TestResolveSectionIndexAdversarial:
    """Adversarial tests for resolve_section_index() edge cases."""

    @pytest.mark.asyncio
    async def test_empty_string_section_name_not_treated_as_none(self) -> None:
        """Empty string section_name should NOT return None -- it enters the
        manifest path (unlike None which short-circuits).

        An empty string is a confused-user input. The function should attempt
        resolution and either return a SectionIndex or let the caller handle it.
        """
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

            result = await resolve_section_index("", "offer", "proj-123")

        # Empty string is NOT None -- should attempt resolution, hit enum fallback
        assert result is mock_enum_index

    @pytest.mark.asyncio
    async def test_s3_transport_error_propagates_unhandled(self) -> None:
        """resolve_section_index does NOT catch S3 transport errors.

        Unlike resolve_section() which wraps S3 calls in try/except
        S3_TRANSPORT_ERRORS, resolve_section_index() lets errors propagate.
        This documents the pre-existing behavior faithfully extracted from
        the old inline code in query_v2.py.
        """
        with (
            patch(
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
            ) as mock_create,
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_manifest_async",
                new_callable=AsyncMock,
                side_effect=ConnectionError("S3 network failure"),
            ),
        ):
            mock_create.return_value = MagicMock()

            with pytest.raises(ConnectionError, match="S3 network failure"):
                await resolve_section_index("ACTIVE", "offer", "proj-123")

    @pytest.mark.asyncio
    async def test_create_persistence_failure_propagates(self) -> None:
        """If create_section_persistence() itself throws, error propagates."""
        with patch(
            "autom8_asana.dataframes.section_persistence.create_section_persistence",
            side_effect=RuntimeError("S3 config missing"),
        ):
            with pytest.raises(RuntimeError, match="S3 config missing"):
                await resolve_section_index("ACTIVE", "offer", "proj-123")

    @pytest.mark.asyncio
    async def test_manifest_returns_empty_index_falls_back_to_enum(self) -> None:
        """When manifest returns an empty SectionIndex (no sections in manifest),
        should fall back to enum because resolve() returns None for any name.
        """
        mock_manifest_index = MagicMock()
        mock_manifest_index.resolve.return_value = None  # Empty manifest

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

    @pytest.mark.asyncio
    async def test_unknown_entity_type_enum_returns_empty_index(self) -> None:
        """For unknown entity types, enum fallback returns empty SectionIndex.

        SectionIndex.from_enum_fallback() returns empty dict for unknown types.
        resolve_section_index() should still return this empty index.
        """
        mock_manifest_index = MagicMock()
        mock_manifest_index.resolve.return_value = None

        # Real-ish empty enum index
        mock_enum_index = MagicMock()
        mock_enum_index.resolve.return_value = None

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

            result = await resolve_section_index(
                "ACTIVE", "unknown_entity", "proj-123"
            )

        # Returns the (empty) enum index, not None
        assert result is mock_enum_index


class TestHasSectionPredAdversarial:
    """Adversarial tests for _has_section_pred() predicate tree walker."""

    @staticmethod
    def _build_predicate(raw: dict):
        """Build a PredicateNode from a raw dict using Pydantic validation."""
        from pydantic import TypeAdapter

        from autom8_asana.query.models import PredicateNode

        adapter = TypeAdapter(PredicateNode)
        return adapter.validate_python(raw)

    def test_deeply_nested_section_pred_detected(self) -> None:
        """Section predicate buried inside AND->OR->NOT->AND is detected."""
        from autom8_asana.services.query_service import _has_section_pred

        tree = self._build_predicate(
            {
                "and": [
                    {
                        "or": [
                            {
                                "not": {
                                    "and": [
                                        {
                                            "field": "section",
                                            "op": "eq",
                                            "value": "ACTIVE",
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        )
        assert _has_section_pred(tree) is True

    def test_no_section_in_deep_tree(self) -> None:
        """Non-section predicates in deep tree return False."""
        from autom8_asana.services.query_service import _has_section_pred

        tree = self._build_predicate(
            {
                "and": [
                    {
                        "or": [
                            {
                                "not": {
                                    "and": [
                                        {
                                            "field": "vertical",
                                            "op": "eq",
                                            "value": "dental",
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        )
        assert _has_section_pred(tree) is False

    def test_not_group_wrapping_section_detected(self) -> None:
        """NOT(section == 'X') is still detected as containing section pred."""
        from autom8_asana.services.query_service import _has_section_pred

        tree = self._build_predicate(
            {"not": {"field": "section", "op": "eq", "value": "PAUSED"}}
        )
        assert _has_section_pred(tree) is True

    def test_or_group_with_mixed_section_and_non_section(self) -> None:
        """OR with one section and one non-section comparison returns True."""
        from autom8_asana.services.query_service import _has_section_pred

        tree = self._build_predicate(
            {
                "or": [
                    {"field": "section", "op": "eq", "value": "ACTIVE"},
                    {"field": "vertical", "op": "eq", "value": "dental"},
                ]
            }
        )
        assert _has_section_pred(tree) is True

    def test_arbitrary_object_returns_false(self) -> None:
        """Unknown node type returns False (defensive)."""
        from autom8_asana.services.query_service import _has_section_pred

        assert _has_section_pred("not_a_node") is False
        assert _has_section_pred(42) is False
        assert _has_section_pred(None) is False


class TestStripSectionConflictsAdversarial:
    """Adversarial tests for strip_section_conflicts() edge cases."""

    def _make_rows_request(self, **kwargs):
        from autom8_asana.query.models import RowsRequest

        return RowsRequest(**kwargs)

    def test_model_copy_preserves_all_fields(self) -> None:
        """When stripping section predicates, all non-where fields survive."""
        request = self._make_rows_request(
            where={"field": "section", "op": "eq", "value": "ACTIVE"},
            section="PAUSED",
            select=["gid", "name", "vertical"],
            limit=50,
            offset=10,
            order_by="name",
            order_dir="desc",
        )
        result = strip_section_conflicts(request, "PAUSED")

        # where should be stripped (only section predicate)
        assert result.where is None
        # All other fields must be preserved
        assert result.section == "PAUSED"
        assert result.select == ["gid", "name", "vertical"]
        assert result.limit == 50
        assert result.offset == 10
        assert result.order_by == "name"
        assert result.order_dir == "desc"

    def test_section_in_or_group_stripped_correctly(self) -> None:
        """Section predicate in OR group with non-section sibling."""
        request = self._make_rows_request(
            where={
                "or": [
                    {"field": "section", "op": "eq", "value": "ACTIVE"},
                    {"field": "vertical", "op": "eq", "value": "dental"},
                ]
            },
            section="PAUSED",
        )
        result = strip_section_conflicts(request, "PAUSED")

        # Should have been stripped (result differs from original)
        assert result is not request

    def test_no_mutation_of_original_request(self) -> None:
        """strip_section_conflicts must not mutate the original request."""
        request = self._make_rows_request(
            where={
                "and": [
                    {"field": "section", "op": "eq", "value": "ACTIVE"},
                    {"field": "vertical", "op": "eq", "value": "dental"},
                ]
            },
            section="PAUSED",
        )
        # Save original where for comparison
        original_where = request.where

        result = strip_section_conflicts(request, "PAUSED")

        # Original should be untouched
        assert request.where is original_where
        assert result is not request


class TestEntityServiceValidateAdversarial:
    """Adversarial tests for EntityService.validate_entity_type() error paths."""

    def test_unknown_entity_returns_correct_error_code(self) -> None:
        """UnknownEntityError has error_code UNKNOWN_ENTITY_TYPE."""
        from autom8_asana.services.entity_service import EntityService
        from autom8_asana.services.errors import UnknownEntityError

        mock_entity_registry = MagicMock()
        mock_project_registry = MagicMock()

        service = EntityService(
            entity_registry=mock_entity_registry,
            project_registry=mock_project_registry,
        )

        # Mock get_resolvable_entities to return a known set
        with patch(
            "autom8_asana.services.resolver.get_resolvable_entities",
            return_value={"offer", "unit"},
        ):
            with pytest.raises(UnknownEntityError) as exc_info:
                service.validate_entity_type("nonexistent")

            err = exc_info.value
            assert err.error_code == "UNKNOWN_ENTITY_TYPE"
            assert err.entity_type == "nonexistent"
            assert "offer" in err.available
            assert "unit" in err.available

    def test_unknown_entity_http_status_is_404(self) -> None:
        """UnknownEntityError maps to HTTP 404 via get_status_for_error."""
        from autom8_asana.services.errors import (
            UnknownEntityError,
            get_status_for_error,
        )

        err = UnknownEntityError("foo", ["bar", "baz"])
        assert get_status_for_error(err) == 404

    def test_service_not_configured_error_code_and_status(self) -> None:
        """ServiceNotConfiguredError has correct error_code and 503 status.

        The old inline code returned PROJECT_NOT_CONFIGURED (503).
        The new code returns SERVICE_NOT_CONFIGURED (503).
        The HTTP status is the same (503), but the error code changed.
        This was an intentional design decision.
        """
        from autom8_asana.services.errors import (
            ServiceNotConfiguredError,
            get_status_for_error,
        )

        err = ServiceNotConfiguredError(
            "No project configured for entity type: offer"
        )
        assert err.error_code == "SERVICE_NOT_CONFIGURED"
        assert get_status_for_error(err) == 503

    def test_project_gid_none_raises_service_not_configured(self) -> None:
        """When project_gid is None, raises ServiceNotConfiguredError (not 404)."""
        from autom8_asana.services.entity_service import EntityService
        from autom8_asana.services.errors import ServiceNotConfiguredError

        mock_entity_registry = MagicMock()
        mock_entity_registry.require.return_value = MagicMock()

        mock_project_registry = MagicMock()
        mock_project_registry.get_project_gid.return_value = None

        service = EntityService(
            entity_registry=mock_entity_registry,
            project_registry=mock_project_registry,
        )

        with patch(
            "autom8_asana.services.resolver.get_resolvable_entities",
            return_value={"offer"},
        ):
            with pytest.raises(ServiceNotConfiguredError):
                service.validate_entity_type("offer")

    def test_bot_pat_missing_raises_service_not_configured(self) -> None:
        """When bot PAT is missing, raises ServiceNotConfiguredError."""
        from autom8_asana.auth.bot_pat import BotPATError
        from autom8_asana.services.entity_service import EntityService
        from autom8_asana.services.errors import ServiceNotConfiguredError

        mock_entity_registry = MagicMock()
        mock_entity_registry.require.return_value = MagicMock()

        mock_project_registry = MagicMock()
        mock_project_registry.get_project_gid.return_value = "proj-123"

        service = EntityService(
            entity_registry=mock_entity_registry,
            project_registry=mock_project_registry,
        )

        with (
            patch(
                "autom8_asana.services.resolver.get_resolvable_entities",
                return_value={"offer"},
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                side_effect=BotPATError("no PAT"),
            ),
        ):
            with pytest.raises(ServiceNotConfiguredError, match="Bot PAT"):
                service.validate_entity_type("offer")

    def test_to_dict_format_for_unknown_entity(self) -> None:
        """UnknownEntityError.to_dict() has the expected wire format."""
        from autom8_asana.services.errors import UnknownEntityError

        err = UnknownEntityError("bogus", ["offer", "unit"])
        d = err.to_dict()
        assert d == {
            "error": "UNKNOWN_ENTITY_TYPE",
            "message": "Unknown entity type: bogus",
            "available_types": ["offer", "unit"],
        }

    def test_to_dict_format_for_service_not_configured(self) -> None:
        """ServiceNotConfiguredError.to_dict() has the expected wire format."""
        from autom8_asana.services.errors import ServiceNotConfiguredError

        err = ServiceNotConfiguredError("No project for offer")
        d = err.to_dict()
        assert d == {
            "error": "SERVICE_NOT_CONFIGURED",
            "message": "No project for offer",
        }


class TestResolveSectionContractParity:
    """Contract tests ensuring resolve_section and resolve_section_index
    behave consistently for shared paths (manifest-first, enum-fallback).
    """

    @pytest.mark.asyncio
    async def test_both_return_when_manifest_resolves(self) -> None:
        """Both functions succeed when manifest resolves the section."""
        mock_manifest_index = MagicMock()
        mock_manifest_index.resolve.return_value = "gid-123"

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
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
                return_value=MagicMock(),
            ),
            patch(
                "autom8_asana.metrics.resolve.SectionIndex.from_manifest_async",
                new_callable=AsyncMock,
                return_value=mock_manifest_index,
            ),
        ):
            # resolve_section returns the section name
            result_section = await resolve_section("ACTIVE", "offer", "proj-123")
            assert result_section == "ACTIVE"

            # resolve_section_index returns the index itself
            result_index = await resolve_section_index("ACTIVE", "offer", "proj-123")
            assert result_index is mock_manifest_index

    @pytest.mark.asyncio
    async def test_both_fall_back_to_enum_on_empty_manifest(self) -> None:
        """Both functions fall back to enum when manifest returns empty index."""
        mock_manifest_index = MagicMock()
        mock_manifest_index.resolve.return_value = None

        mock_enum_index = MagicMock()
        mock_enum_index.resolve.return_value = "gid-enum"

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
                "autom8_asana.dataframes.section_persistence.create_section_persistence",
                return_value=MagicMock(),
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
            # resolve_section returns the section name (via enum)
            result_section = await resolve_section("ACTIVE", "offer", "proj-123")
            assert result_section == "ACTIVE"

            # resolve_section_index returns the enum index
            result_index = await resolve_section_index("ACTIVE", "offer", "proj-123")
            assert result_index is mock_enum_index
