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
    async def test_happy_path(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_empty_results(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_pagination_metadata(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_passes_offset(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_uses_task_opt_fields(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_happy_path(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_missing_project_raises(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_no_project_key_raises(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_pagination_metadata(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_passes_offset(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
    async def test_fetches_section_first(
        self, service: DataFrameService, mock_client: MagicMock
    ):
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
