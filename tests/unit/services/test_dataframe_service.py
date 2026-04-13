"""Tests for DataFrameService -- DataFrame build operations with mock dependencies.

Verifies:
- Schema resolution: valid schema, invalid schema, wildcard rejection, empty input
- Build project: happy path, empty results, pagination
- Build section: happy path, missing project GID, pagination
- TASK_OPT_FIELDS: single source of truth (not duplicated)
- InvalidSchemaError: error code, to_dict, MRO status resolution
- DataFrameResult: frozen dataclass properties
- _SectionProxy: adapter interface

Per TDD-SERVICE-LAYER-001 v2.0 Phase 4.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.services.dataframe_service import (
    DataFrameResult,
    DataFrameService,
    InvalidSchemaError,
    _SectionProxy,
    reset_schema_cache,
)
from autom8_asana.services.errors import (
    EntityNotFoundError,
    InvalidParameterError,
    get_status_for_error,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset module-level schema cache before and after each test."""
    reset_schema_cache()
    yield
    reset_schema_cache()


@pytest.fixture()
def service() -> DataFrameService:
    return DataFrameService()


@pytest.fixture()
def mock_client() -> MagicMock:
    """Create a mock AsanaClient with _http sub-mock."""
    client = MagicMock()
    client._http = MagicMock()
    client._http.get = AsyncMock()
    client._http.get_paginated = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# InvalidSchemaError
# ---------------------------------------------------------------------------


class TestInvalidSchemaError:
    """Tests for InvalidSchemaError exception class."""

    def test_is_invalid_parameter_error(self):
        """InvalidSchemaError is a subclass of InvalidParameterError."""
        err = InvalidSchemaError("bad", ["base", "unit"])
        assert isinstance(err, InvalidParameterError)

    def test_error_code(self):
        """Error code is INVALID_SCHEMA."""
        err = InvalidSchemaError("bad", ["base", "unit"])
        assert err.error_code == "INVALID_SCHEMA"

    def test_to_dict(self):
        """to_dict includes error, message, and valid_schemas."""
        err = InvalidSchemaError("bad", ["base", "unit"])
        d = err.to_dict()
        assert d["error"] == "INVALID_SCHEMA"
        assert "bad" in d["message"]
        assert d["valid_schemas"] == ["base", "unit"]

    def test_mro_status_resolution(self):
        """get_status_for_error resolves to 400 via MRO walk."""
        err = InvalidSchemaError("bad", ["base"])
        assert get_status_for_error(err) == 400

    def test_message_includes_valid_schemas(self):
        """Error message lists valid schemas."""
        err = InvalidSchemaError("bad", ["base", "unit", "offer"])
        assert "base" in err.message
        assert "unit" in err.message
        assert "offer" in err.message


# ---------------------------------------------------------------------------
# DataFrameResult
# ---------------------------------------------------------------------------


class TestDataFrameResult:
    """Tests for DataFrameResult frozen dataclass."""

    def test_attributes(self):
        """DataFrameResult stores dataframe, has_more, and next_offset."""
        df = pl.DataFrame({"a": [1]})
        result = DataFrameResult(dataframe=df, has_more=True, next_offset="abc")
        assert result.dataframe.shape == (1, 1)
        assert result.has_more is True
        assert result.next_offset == "abc"

    def test_frozen(self):
        """DataFrameResult is frozen (immutable)."""
        df = pl.DataFrame({"a": [1]})
        result = DataFrameResult(dataframe=df, has_more=False, next_offset=None)
        with pytest.raises(AttributeError):
            result.has_more = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _SectionProxy
# ---------------------------------------------------------------------------


class TestSectionProxy:
    """Tests for _SectionProxy adapter class."""

    def test_interface(self):
        """_SectionProxy provides gid, project, and tasks attributes."""
        proxy = _SectionProxy("sec123", "proj456", ["task1", "task2"])
        assert proxy.gid == "sec123"
        assert proxy.project == {"gid": "proj456"}
        assert proxy.tasks == ["task1", "task2"]

    def test_slots(self):
        """_SectionProxy uses __slots__ for memory efficiency."""
        proxy = _SectionProxy("sec123", "proj456", [])
        assert hasattr(proxy, "__slots__")
        with pytest.raises(AttributeError):
            proxy.extra = "not allowed"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TASK_OPT_FIELDS
# ---------------------------------------------------------------------------


class TestTaskOptFields:
    """Tests for TASK_OPT_FIELDS class constant."""

    def test_is_list_of_strings(self):
        """TASK_OPT_FIELDS is a list of strings."""
        assert isinstance(DataFrameService.TASK_OPT_FIELDS, list)
        assert all(isinstance(f, str) for f in DataFrameService.TASK_OPT_FIELDS)

    def test_contains_required_fields(self):
        """TASK_OPT_FIELDS includes essential Asana task fields."""
        fields = DataFrameService.TASK_OPT_FIELDS
        assert "gid" in fields
        assert "name" in fields
        assert "completed" in fields
        assert "custom_fields" in fields
        assert "memberships.section.name" in fields
        assert "memberships.project.gid" in fields

    def test_no_duplicates(self):
        """TASK_OPT_FIELDS has no duplicates."""
        fields = DataFrameService.TASK_OPT_FIELDS
        assert len(fields) == len(set(fields))


# ---------------------------------------------------------------------------
# Schema Resolution
# ---------------------------------------------------------------------------


class TestGetSchema:
    """Tests for DataFrameService.get_schema()."""

    def test_valid_schema_base(self, service: DataFrameService):
        """Resolves 'base' to the base schema."""
        schema = service.get_schema("base")
        assert isinstance(schema, object)  # DataFrameSchema
        assert schema is not None

    def test_valid_schema_unit(self, service: DataFrameService):
        """Resolves 'unit' to the unit schema."""
        schema = service.get_schema("unit")
        assert schema is not None

    def test_valid_schema_case_insensitive(self, service: DataFrameService):
        """Schema names are case-insensitive."""
        schema_lower = service.get_schema("unit")
        schema_upper = service.get_schema("UNIT")
        schema_mixed = service.get_schema("Unit")
        # All should resolve to the same schema
        assert schema_lower.name == schema_upper.name == schema_mixed.name

    def test_invalid_schema_raises(self, service: DataFrameService):
        """Invalid schema name raises InvalidSchemaError."""
        with pytest.raises(InvalidSchemaError) as exc_info:
            service.get_schema("nonexistent")
        assert "nonexistent" in str(exc_info.value)
        assert exc_info.value.valid_schemas  # non-empty list

    def test_wildcard_rejected(self, service: DataFrameService):
        """Wildcard '*' is rejected as direct input."""
        with pytest.raises(InvalidSchemaError) as exc_info:
            service.get_schema("*")
        assert exc_info.value.schema_name == "*"

    def test_empty_string_returns_base(self, service: DataFrameService):
        """Empty string falls back to base schema."""
        schema = service.get_schema("")
        assert schema is not None

    def test_whitespace_returns_base(self, service: DataFrameService):
        """Whitespace-only string falls back to base schema."""
        schema = service.get_schema("   ")
        assert schema is not None

    def test_valid_schemas_list_populated(self, service: DataFrameService):
        """InvalidSchemaError contains valid_schemas list with expected entries."""
        with pytest.raises(InvalidSchemaError) as exc_info:
            service.get_schema("bogus")
        valid = exc_info.value.valid_schemas
        assert "base" in valid
        assert "unit" in valid
        assert len(valid) >= 4  # At minimum: base + core types


# ---------------------------------------------------------------------------
# Build Project DataFrame
# ---------------------------------------------------------------------------


class TestBuildProjectDataframe:
    """Tests for DataFrameService.build_project_dataframe()."""

    @pytest.mark.asyncio
    async def test_happy_path(self, service: DataFrameService, mock_client: MagicMock):
        """Builds DataFrame from paginated task data."""
        schema = service.get_schema("base")

        # Mock paginated response with task data
        task_data = {
            "gid": "123",
            "name": "Test Task",
            "resource_type": "task",
            "completed": False,
            "completed_at": None,
            "created_at": "2024-01-01T00:00:00.000Z",
            "modified_at": "2024-01-02T00:00:00.000Z",
            "notes": "Notes",
            "assignee": {"gid": "u1", "name": "User"},
            "due_on": "2024-03-01",
            "due_at": None,
            "start_on": None,
            "memberships": [
                {
                    "section": {"name": "Backlog"},
                    "project": {"gid": "proj1"},
                }
            ],
            "custom_fields": [],
        }
        mock_client._http.get_paginated.return_value = ([task_data], None)

        result = await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset=None,
        )

        assert isinstance(result, DataFrameResult)
        assert isinstance(result.dataframe, pl.DataFrame)
        assert result.dataframe.height == 1
        assert result.has_more is False
        assert result.next_offset is None

    @pytest.mark.asyncio
    async def test_empty_results(self, service: DataFrameService, mock_client: MagicMock):
        """Returns empty DataFrame when no tasks found."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        result = await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset=None,
        )

        assert result.dataframe.height == 0
        assert result.has_more is False
        assert result.next_offset is None

    @pytest.mark.asyncio
    async def test_pagination_metadata(self, service: DataFrameService, mock_client: MagicMock):
        """Propagates pagination info from HTTP response."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], "next_cursor")

        result = await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=50,
            offset=None,
        )

        assert result.has_more is True
        assert result.next_offset == "next_cursor"

    @pytest.mark.asyncio
    async def test_passes_offset(self, service: DataFrameService, mock_client: MagicMock):
        """Passes offset parameter to HTTP client when provided."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset="cursor123",
        )

        call_args = mock_client._http.get_paginated.call_args
        assert call_args[1]["params"]["offset"] == "cursor123"

    @pytest.mark.asyncio
    async def test_uses_task_opt_fields(self, service: DataFrameService, mock_client: MagicMock):
        """Uses TASK_OPT_FIELDS for the opt_fields parameter."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset=None,
        )

        call_args = mock_client._http.get_paginated.call_args
        opt_fields = call_args[1]["params"]["opt_fields"]
        assert "gid" in opt_fields
        assert "custom_fields" in opt_fields


# ---------------------------------------------------------------------------
# Build Section DataFrame
# ---------------------------------------------------------------------------


class TestBuildSectionDataframe:
    """Tests for DataFrameService.build_section_dataframe()."""

    @pytest.mark.asyncio
    async def test_happy_path(self, service: DataFrameService, mock_client: MagicMock):
        """Builds DataFrame from section tasks."""
        schema = service.get_schema("base")

        # Mock section lookup
        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": "proj1"},
        }

        # Mock task fetch
        task_data = {
            "gid": "123",
            "name": "Test Task",
            "resource_type": "task",
            "completed": False,
            "completed_at": None,
            "created_at": "2024-01-01T00:00:00.000Z",
            "modified_at": "2024-01-02T00:00:00.000Z",
            "notes": "Notes",
            "assignee": {"gid": "u1", "name": "User"},
            "due_on": "2024-03-01",
            "due_at": None,
            "start_on": None,
            "memberships": [
                {
                    "section": {"name": "Backlog"},
                    "project": {"gid": "proj1"},
                }
            ],
            "custom_fields": [],
        }
        mock_client._http.get_paginated.return_value = ([task_data], None)

        result, project_gid = await service.build_section_dataframe(
            client=mock_client,
            section_gid="sec1",
            schema=schema,
            limit=100,
            offset=None,
        )

        assert isinstance(result, DataFrameResult)
        assert isinstance(result.dataframe, pl.DataFrame)
        assert result.has_more is False
        assert project_gid == "proj1"

    @pytest.mark.asyncio
    async def test_missing_project_raises(self, service: DataFrameService, mock_client: MagicMock):
        """Raises EntityNotFoundError when section has no parent project."""
        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {},  # No gid
        }

        with pytest.raises(EntityNotFoundError) as exc_info:
            schema = service.get_schema("base")
            await service.build_section_dataframe(
                client=mock_client,
                section_gid="sec1",
                schema=schema,
                limit=100,
                offset=None,
            )

        assert "Section not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_project_key_raises(self, service: DataFrameService, mock_client: MagicMock):
        """Raises EntityNotFoundError when section response has no project key."""
        mock_client._http.get.return_value = {
            "gid": "sec1",
            # No 'project' key at all
        }

        with pytest.raises(EntityNotFoundError):
            schema = service.get_schema("base")
            await service.build_section_dataframe(
                client=mock_client,
                section_gid="sec1",
                schema=schema,
                limit=100,
                offset=None,
            )

    @pytest.mark.asyncio
    async def test_pagination_metadata(self, service: DataFrameService, mock_client: MagicMock):
        """Propagates pagination info from HTTP response."""
        schema = service.get_schema("base")

        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": "proj1"},
        }
        mock_client._http.get_paginated.return_value = ([], "next_xyz")

        result, _ = await service.build_section_dataframe(
            client=mock_client,
            section_gid="sec1",
            schema=schema,
            limit=50,
            offset=None,
        )

        assert result.has_more is True
        assert result.next_offset == "next_xyz"

    @pytest.mark.asyncio
    async def test_passes_offset(self, service: DataFrameService, mock_client: MagicMock):
        """Passes offset parameter to HTTP client when provided."""
        schema = service.get_schema("base")

        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": "proj1"},
        }
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_section_dataframe(
            client=mock_client,
            section_gid="sec1",
            schema=schema,
            limit=100,
            offset="cursor456",
        )

        call_args = mock_client._http.get_paginated.call_args
        assert call_args[1]["params"]["offset"] == "cursor456"

    @pytest.mark.asyncio
    async def test_fetches_section_first(self, service: DataFrameService, mock_client: MagicMock):
        """Fetches section metadata before tasks."""
        schema = service.get_schema("base")

        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": "proj1"},
        }
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_section_dataframe(
            client=mock_client,
            section_gid="sec1",
            schema=schema,
            limit=100,
            offset=None,
        )

        # Verify section was fetched
        mock_client._http.get.assert_called_once()
        get_call = mock_client._http.get.call_args
        assert "/sections/sec1" in get_call[0][0]


# ---------------------------------------------------------------------------
# Schema Cache
# ---------------------------------------------------------------------------


class TestSchemaCache:
    """Tests for module-level schema mapping cache."""

    def test_cache_is_populated(self, service: DataFrameService):
        """Schema mapping is built on first access."""
        mapping, valid = service._get_schema_mapping()
        assert isinstance(mapping, dict)
        assert "base" in mapping
        assert len(valid) >= 4

    def test_reset_clears_cache(self, service: DataFrameService):
        """reset_schema_cache() clears the module cache."""
        # Populate cache
        service._get_schema_mapping()

        # Reset
        reset_schema_cache()

        # Verify re-populated on next access
        mapping, valid = service._get_schema_mapping()
        assert "base" in mapping


# ===========================================================================
# ADVERSARIAL TESTS -- QA Adversary (I2 Phase 4)
#
# Targets:
# 1. InvalidSchemaError MRO status resolution (TDD deviation)
# 2. Content negotiation preservation
# 3. Section 404 handling edge cases
# 4. Schema cache isolation / pollution
# 5. Pagination offset passthrough fidelity
# 6. DataFrameResult edge cases
# 7. _SectionProxy correctness boundaries
# 8. get_schema() boundary inputs
# 9. TASK_OPT_FIELDS deduplication
# 10. build_section_dataframe edge cases (project key variants)
# ===========================================================================


class TestAdversarialInvalidSchemaErrorMRO:
    """Adversarial: MRO status resolution for InvalidSchemaError.

    InvalidSchemaError is NOT in SERVICE_ERROR_MAP. It relies on
    MRO walk to find InvalidParameterError -> 400. This is the
    TDD deviation that must be validated.
    """

    def test_mro_walk_finds_400_not_500(self):
        """get_status_for_error walks MRO to InvalidParameterError -> 400.

        If this returned 500, the TDD deviation is broken and
        InvalidSchemaError would map to the wrong HTTP status.
        """
        from autom8_asana.services.errors import SERVICE_ERROR_MAP

        err = InvalidSchemaError("test", ["base"])

        # Confirm InvalidSchemaError is NOT directly in the map
        assert type(err) not in SERVICE_ERROR_MAP

        # Confirm MRO walk resolves to 400
        status = get_status_for_error(err)
        assert status == 400, (
            f"Expected 400 via MRO walk, got {status}. "
            f"InvalidSchemaError relies on InvalidParameterError mapping."
        )

    def test_mro_chain_is_correct(self):
        """InvalidSchemaError MRO includes InvalidParameterError before ServiceError."""
        mro = InvalidSchemaError.__mro__
        mro_names = [cls.__name__ for cls in mro]
        assert "InvalidParameterError" in mro_names
        assert "EntityValidationError" in mro_names
        assert "ServiceError" in mro_names
        # InvalidParameterError must come before ServiceError
        assert mro_names.index("InvalidParameterError") < mro_names.index("ServiceError")

    def test_status_hint_fallback_is_also_400(self):
        """Even if MRO walk failed, status_hint on InvalidParameterError is 400."""
        err = InvalidSchemaError("test", [])
        # InvalidParameterError inherits from EntityValidationError (400)
        assert err.status_hint == 400


class TestAdversarialDataFrameResultEdgeCases:
    """Adversarial: DataFrameResult construction with tricky inputs."""

    def test_empty_dataframe(self):
        """DataFrameResult with a zero-row DataFrame."""
        df = pl.DataFrame({"col": pl.Series([], dtype=pl.Utf8)})
        result = DataFrameResult(dataframe=df, has_more=False, next_offset=None)
        assert result.dataframe.height == 0
        assert result.dataframe.width == 1
        assert result.has_more is False

    def test_none_offset(self):
        """DataFrameResult with None offset (no more pages)."""
        df = pl.DataFrame({"a": [1]})
        result = DataFrameResult(dataframe=df, has_more=False, next_offset=None)
        assert result.next_offset is None

    def test_empty_string_offset(self):
        """DataFrameResult with empty string offset (falsy but not None)."""
        df = pl.DataFrame({"a": [1]})
        result = DataFrameResult(dataframe=df, has_more=True, next_offset="")
        # Empty string is a valid value for the dataclass
        assert result.next_offset == ""

    def test_has_more_false_with_offset_present(self):
        """DataFrameResult allows has_more=False with non-None offset (no enforcement)."""
        df = pl.DataFrame({"a": [1]})
        result = DataFrameResult(dataframe=df, has_more=False, next_offset="leftover_cursor")
        # This is a data inconsistency but DataFrameResult is a dumb container
        assert result.has_more is False
        assert result.next_offset == "leftover_cursor"

    def test_equality(self):
        """Two DataFrameResults with same data are equal (frozen dataclass)."""
        df = pl.DataFrame({"a": [1]})
        r1 = DataFrameResult(dataframe=df, has_more=True, next_offset="x")
        r2 = DataFrameResult(dataframe=df, has_more=True, next_offset="x")
        assert r1 == r2


class TestAdversarialSchemaCacheIsolation:
    """Adversarial: Schema cache pollution across tests."""

    def test_cache_does_not_leak_between_services(self):
        """Two DataFrameService instances share the same module-level cache."""
        svc1 = DataFrameService()
        svc2 = DataFrameService()

        # First call populates cache
        mapping1, valid1 = svc1._get_schema_mapping()

        # Second instance should see the same cached data
        mapping2, valid2 = svc2._get_schema_mapping()

        assert mapping1 is mapping2, "Cache should be shared (same dict object)"
        assert valid1 is valid2, "Cache should be shared (same list object)"

    def test_reset_between_tests(self):
        """After reset, cache is re-built from scratch."""
        svc = DataFrameService()

        # Populate cache
        mapping_before, _ = svc._get_schema_mapping()
        id_before = id(mapping_before)

        # Reset
        reset_schema_cache()

        # Re-populate
        mapping_after, _ = svc._get_schema_mapping()
        id_after = id(mapping_after)

        # Different objects (cache was rebuilt)
        assert id_before != id_after

    def test_cache_content_matches_registry(self):
        """Cache mapping keys match SchemaRegistry schemas."""
        from autom8_asana.dataframes.models.registry import SchemaRegistry

        svc = DataFrameService()
        mapping, valid = svc._get_schema_mapping()

        registry = SchemaRegistry.get_instance()
        task_types = registry.list_task_types()

        # "base" maps to "*" which isn't in task_types but is in mapping
        assert "base" in mapping
        assert mapping["base"] == "*"

        # Every task type in registry should be represented
        for tt in task_types:
            schema = registry.get_schema(tt)
            assert schema.name in mapping, f"Schema {schema.name} for {tt} missing"

    def test_valid_schemas_is_sorted(self):
        """Valid schemas list is always sorted alphabetically."""
        svc = DataFrameService()
        _, valid = svc._get_schema_mapping()
        assert valid == sorted(valid), "valid_schemas must be sorted"


class TestAdversarialSectionProxyBoundary:
    """Adversarial: _SectionProxy correctness in boundary cases."""

    def test_empty_tasks_list(self):
        """Proxy with empty tasks list is valid."""
        proxy = _SectionProxy("sec", "proj", [])
        assert proxy.tasks == []

    def test_project_dict_format(self):
        """SectionDataFrameBuilder._get_project_gid() reads proxy.project['gid']."""
        proxy = _SectionProxy("sec", "proj_gid_123", [])
        assert proxy.project["gid"] == "proj_gid_123"
        assert isinstance(proxy.project, dict)

    def test_no_extra_attributes(self):
        """__slots__ prevents any extra attributes beyond gid/project/tasks."""
        proxy = _SectionProxy("s", "p", [])
        assert set(proxy.__slots__) == {"gid", "project", "tasks"}

    def test_tasks_is_mutable(self):
        """Tasks list on proxy is the same list object passed in (no copy)."""
        tasks = ["t1", "t2"]
        proxy = _SectionProxy("s", "p", tasks)
        assert proxy.tasks is tasks

    def test_proxy_with_none_tasks_value(self):
        """Proxy stores None tasks if passed -- builder handles this."""
        # _SectionProxy doesn't validate; SectionDataFrameBuilder.get_tasks() does
        proxy = _SectionProxy("s", "p", None)  # type: ignore[arg-type]
        assert proxy.tasks is None


class TestAdversarialGetSchemaBoundary:
    """Adversarial: get_schema() with unusual inputs."""

    def test_numeric_string_raises(self, service: DataFrameService):
        """Numeric string is not a valid schema name."""
        with pytest.raises(InvalidSchemaError):
            service.get_schema("42")

    def test_special_chars_raise(self, service: DataFrameService):
        """Schema name with special characters raises."""
        with pytest.raises(InvalidSchemaError):
            service.get_schema("base; DROP TABLE schemas")

    def test_very_long_name_raises(self, service: DataFrameService):
        """Very long schema name raises (not a valid schema)."""
        with pytest.raises(InvalidSchemaError):
            service.get_schema("a" * 1000)

    def test_tab_whitespace_returns_base(self, service: DataFrameService):
        """Tab character triggers empty/whitespace fallback to base."""
        schema = service.get_schema("\t")
        assert schema is not None

    def test_newline_whitespace_returns_base(self, service: DataFrameService):
        """Newline character triggers empty/whitespace fallback to base."""
        schema = service.get_schema("\n")
        assert schema is not None

    def test_wildcard_with_spaces_rejected(self, service: DataFrameService):
        """' * ' (wildcard with spaces) is normalized and rejected."""
        with pytest.raises(InvalidSchemaError) as exc_info:
            service.get_schema(" * ")
        assert exc_info.value.schema_name == "*"

    def test_case_preserved_in_error(self, service: DataFrameService):
        """Error message preserves original case of the invalid name."""
        with pytest.raises(InvalidSchemaError) as exc_info:
            service.get_schema("UnItZ")
        assert exc_info.value.schema_name == "UnItZ"

    def test_base_resolves_to_wildcard_schema(self, service: DataFrameService):
        """'base' maps to '*' (wildcard) task type in SchemaRegistry."""
        schema = service.get_schema("base")
        assert schema.task_type == "*"

    def test_all_7_schemas_resolve(self, service: DataFrameService):
        """All 7 registered schema names resolve successfully."""
        expected_schemas = [
            "base",
            "unit",
            "contact",
            "business",
            "offer",
            "asset_edit",
            "asset_edit_holder",
        ]
        for name in expected_schemas:
            schema = service.get_schema(name)
            assert schema is not None, f"Schema '{name}' should resolve"
            assert schema.name == name


class TestAdversarialBuildSectionProjectKeyVariants:
    """Adversarial: build_section_dataframe when section API returns
    unusual 'project' key values.
    """

    @pytest.mark.asyncio
    async def test_project_none_raises_entity_not_found(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """D1 FIX: project=None now correctly raises EntityNotFoundError.

        When the Asana API returns {"project": null} for an orphaned section,
        the null-safe pattern `section_data.get("project") or {}` coerces
        None to {}, so project_gid resolves to None and raises
        EntityNotFoundError (HTTP 404) instead of AttributeError (HTTP 500).
        """
        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": None,
        }

        with pytest.raises(EntityNotFoundError):
            schema = service.get_schema("base")
            await service.build_section_dataframe(
                client=mock_client,
                section_gid="sec1",
                schema=schema,
                limit=100,
                offset=None,
            )

    @pytest.mark.asyncio
    async def test_project_gid_empty_string_raises(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """project.gid='' (empty string) triggers EntityNotFoundError."""
        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": ""},
        }

        with pytest.raises(EntityNotFoundError):
            schema = service.get_schema("base")
            await service.build_section_dataframe(
                client=mock_client,
                section_gid="sec1",
                schema=schema,
                limit=100,
                offset=None,
            )

    @pytest.mark.asyncio
    async def test_project_gid_none_raises(self, service: DataFrameService, mock_client: MagicMock):
        """project.gid=None triggers EntityNotFoundError."""
        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": None},
        }

        with pytest.raises(EntityNotFoundError):
            schema = service.get_schema("base")
            await service.build_section_dataframe(
                client=mock_client,
                section_gid="sec1",
                schema=schema,
                limit=100,
                offset=None,
            )

    @pytest.mark.asyncio
    async def test_completely_empty_response_raises(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """Empty dict response from section API triggers EntityNotFoundError."""
        mock_client._http.get.return_value = {}

        with pytest.raises(EntityNotFoundError):
            schema = service.get_schema("base")
            await service.build_section_dataframe(
                client=mock_client,
                section_gid="sec1",
                schema=schema,
                limit=100,
                offset=None,
            )


class TestAdversarialPaginationPassthrough:
    """Adversarial: Offset passthrough fidelity for both endpoints."""

    @pytest.mark.asyncio
    async def test_project_offset_none_not_in_params(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """When offset=None, 'offset' key should NOT be in params."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset=None,
        )

        call_args = mock_client._http.get_paginated.call_args
        assert "offset" not in call_args[1]["params"]

    @pytest.mark.asyncio
    async def test_project_offset_empty_string_not_in_params(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """When offset='' (empty string), 'offset' key should NOT be in params.

        Empty string is falsy, so `if offset:` evaluates to False.
        """
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset="",
        )

        call_args = mock_client._http.get_paginated.call_args
        assert "offset" not in call_args[1]["params"]

    @pytest.mark.asyncio
    async def test_section_offset_none_not_in_params(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """Section endpoint: offset=None should NOT include 'offset' in params."""
        schema = service.get_schema("base")
        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": "proj1"},
        }
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_section_dataframe(
            client=mock_client,
            section_gid="sec1",
            schema=schema,
            limit=100,
            offset=None,
        )

        call_args = mock_client._http.get_paginated.call_args
        assert "offset" not in call_args[1]["params"]

    @pytest.mark.asyncio
    async def test_section_offset_passthrough_exact(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """Section endpoint: offset value is passed through exactly."""
        schema = service.get_schema("base")
        mock_client._http.get.return_value = {
            "gid": "sec1",
            "project": {"gid": "proj1"},
        }
        mock_client._http.get_paginated.return_value = ([], None)

        cursor = "eyJvZmZzZXQiOjEwMH0"
        await service.build_section_dataframe(
            client=mock_client,
            section_gid="sec1",
            schema=schema,
            limit=100,
            offset=cursor,
        )

        call_args = mock_client._http.get_paginated.call_args
        assert call_args[1]["params"]["offset"] == cursor

    @pytest.mark.asyncio
    async def test_project_limit_passthrough_exact(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """Project endpoint: limit value is passed through exactly to HTTP params."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=42,
            offset=None,
        )

        call_args = mock_client._http.get_paginated.call_args
        assert call_args[1]["params"]["limit"] == 42


class TestAdversarialTaskOptFieldsDeduplication:
    """Adversarial: TASK_OPT_FIELDS deduplication and structure."""

    def test_no_whitespace_in_fields(self):
        """No field name contains leading/trailing whitespace."""
        for f in DataFrameService.TASK_OPT_FIELDS:
            assert f == f.strip(), f"Field '{f}' has whitespace"

    def test_no_empty_strings(self):
        """No empty strings in TASK_OPT_FIELDS."""
        for f in DataFrameService.TASK_OPT_FIELDS:
            assert f, "Empty string found in TASK_OPT_FIELDS"

    def test_all_fields_dot_delimited_or_plain(self):
        """Every field is either plain or uses dot notation (no other separators)."""
        import re

        for f in DataFrameService.TASK_OPT_FIELDS:
            assert re.match(r"^[a-z_]+(\.[a-z_]+)*$", f), f"Field '{f}' uses unexpected format"

    def test_opt_fields_join_produces_valid_csv(self):
        """Joining TASK_OPT_FIELDS produces a valid comma-separated string."""
        csv = ",".join(DataFrameService.TASK_OPT_FIELDS)
        assert ",," not in csv, "Double comma means empty field"
        assert not csv.startswith(","), "Leading comma"
        assert not csv.endswith(","), "Trailing comma"

    def test_field_count_is_stable(self):
        """TASK_OPT_FIELDS has a known count (catches accidental additions/removals)."""
        # 28 fields: 26 from Phase 4 + parent, parent.gid for cascade warming
        assert len(DataFrameService.TASK_OPT_FIELDS) == 28


class TestAdversarialContentNegotiation:
    """Adversarial: _should_use_polars_format from route layer."""

    def test_polars_in_accept_returns_true(self):
        """MIME_POLARS in accept header triggers Polars format."""
        from autom8_asana.api.routes.dataframes import _should_use_polars_format

        assert _should_use_polars_format("application/x-polars-json") is True

    def test_json_in_accept_returns_false(self):
        """application/json in accept header does NOT trigger Polars."""
        from autom8_asana.api.routes.dataframes import _should_use_polars_format

        assert _should_use_polars_format("application/json") is False

    def test_none_accept_returns_false(self):
        """None accept header defaults to JSON (not Polars)."""
        from autom8_asana.api.routes.dataframes import _should_use_polars_format

        assert _should_use_polars_format(None) is False

    def test_mixed_accept_with_polars_returns_true(self):
        """Accept with multiple MIME types including polars returns True."""
        from autom8_asana.api.routes.dataframes import _should_use_polars_format

        assert (
            _should_use_polars_format("text/html, application/x-polars-json, application/json")
            is True
        )

    def test_empty_accept_returns_false(self):
        """Empty string accept header returns False."""
        from autom8_asana.api.routes.dataframes import _should_use_polars_format

        assert _should_use_polars_format("") is False

    def test_polars_substring_attack(self):
        """Accept header containing 'polars' but NOT the exact MIME type."""
        from autom8_asana.api.routes.dataframes import _should_use_polars_format

        # This should be False because "polars" alone is not the MIME type
        assert _should_use_polars_format("application/polars") is False


class TestAdversarialBuildProjectEmptyDataFrame:
    """Adversarial: Empty DataFrame schema conformance."""

    @pytest.mark.asyncio
    async def test_empty_df_has_correct_columns(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """Empty DataFrame from build_project_dataframe has correct schema columns."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        result = await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset=None,
        )

        # Empty DataFrame should still have the schema's column names
        expected_columns = schema.column_names()
        assert result.dataframe.columns == expected_columns

    @pytest.mark.asyncio
    async def test_empty_df_has_correct_dtypes(
        self, service: DataFrameService, mock_client: MagicMock
    ):
        """Empty DataFrame from build_project_dataframe has correct dtypes."""
        schema = service.get_schema("base")
        mock_client._http.get_paginated.return_value = ([], None)

        result = await service.build_project_dataframe(
            client=mock_client,
            project_gid="proj1",
            schema=schema,
            limit=100,
            offset=None,
        )

        polars_schema = schema.to_polars_schema()
        for col_name, expected_dtype in polars_schema.items():
            actual_dtype = result.dataframe.schema[col_name]
            assert actual_dtype == expected_dtype, (
                f"Column '{col_name}' dtype mismatch: {actual_dtype} vs {expected_dtype}"
            )
