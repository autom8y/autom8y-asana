"""Tests for dataframes endpoints.

Tests cover:
- GET /api/v1/dataframes/project/{gid} - Get project tasks as dataframe
- GET /api/v1/dataframes/section/{gid} - Get section tasks as dataframe

Content negotiation:
- application/json (default): JSON records array
- application/x-polars-json: Polars-serialized format

Schema selection:
- base (default)
- unit
- contact

Per TDD-ASANA-SATELLITE (FR-API-DF-001 through FR-API-DF-005).
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.api.conftest import TEST_PROJECT_GID, TEST_SECTION_GID


# Sample task data matching Asana API response structure
SAMPLE_TASK_DATA = {
    "gid": "1234567890",
    "name": "Sample Task",
    "resource_type": "task",
    "completed": False,
    "completed_at": None,
    "created_at": "2024-01-01T00:00:00.000Z",
    "modified_at": "2024-01-02T00:00:00.000Z",
    "notes": "Task notes",
    "assignee": {"gid": "user123", "name": "Test User"},
    "due_on": "2024-03-01",
    "due_at": None,
    "start_on": None,
    "memberships": [
        {
            "section": {"name": "Backlog"},
            "project": {"gid": TEST_PROJECT_GID},
        }
    ],
    "custom_fields": [
        {
            "gid": "cf_001",
            "name": "Priority",
            "resource_subtype": "enum",
            "display_value": "High",
            "enum_value": {"gid": "ev_001", "name": "High"},
        },
        {
            "gid": "cf_002",
            "name": "Points",
            "resource_subtype": "number",
            "display_value": "5",
            "number_value": 5,
        },
    ],
}

SAMPLE_TASK_DATA_2 = {
    "gid": "9876543210",
    "name": "Another Task",
    "resource_type": "task",
    "completed": True,
    "completed_at": "2024-02-15T12:00:00.000Z",
    "created_at": "2024-01-05T00:00:00.000Z",
    "modified_at": "2024-02-15T12:00:00.000Z",
    "notes": "Completed task",
    "assignee": None,
    "due_on": None,
    "due_at": None,
    "start_on": None,
    "memberships": [
        {
            "section": {"name": "Done"},
            "project": {"gid": TEST_PROJECT_GID},
        }
    ],
    "custom_fields": [],
}


class TestGetProjectDataframe:
    """Tests for GET /api/v1/dataframes/project/{gid} endpoint."""

    def test_get_project_dataframe_success_empty(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns empty dataframe for project with no tasks."""
        client, mock_sdk = authed_client

        # Configure mock to return empty task list
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data
        assert data["data"] == []
        assert "request_id" in data["meta"]
        assert data["meta"]["pagination"]["has_more"] is False
        assert data["meta"]["pagination"]["next_offset"] is None

    def test_get_project_dataframe_success_with_tasks(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns dataframe with task data."""
        client, mock_sdk = authed_client

        # Configure mock to return task list
        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_TASK_DATA, SAMPLE_TASK_DATA_2],
            None,
        )

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert len(data["data"]) == 2
        assert data["meta"]["pagination"]["has_more"] is False

        # Verify dataframe row structure (base schema)
        row = data["data"][0]
        assert "gid" in row
        assert "name" in row

    def test_get_project_dataframe_with_pagination(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns dataframe with pagination metadata."""
        client, mock_sdk = authed_client

        # Configure mock to return paginated response
        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_TASK_DATA],
            "next_cursor_abc",
        )

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?limit=1",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["pagination"]["has_more"] is True
        assert data["meta"]["pagination"]["next_offset"] == "next_cursor_abc"
        assert data["meta"]["pagination"]["limit"] == 1

    def test_get_project_dataframe_with_offset(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses offset parameter for pagination."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA_2], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?offset=cursor123",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify offset was passed to HTTP client
        call_args = mock_sdk._http.get_paginated.call_args
        assert call_args[1]["params"]["offset"] == "cursor123"

    def test_get_project_dataframe_schema_base(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses base schema (default)."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=base",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_get_project_dataframe_schema_unit(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses unit schema with empty response (no tasks)."""
        client, mock_sdk = authed_client

        # Use empty task list to avoid extractor validation issues
        # (Unit schema requires specific custom fields that are
        # domain-specific to Asana workspace configuration)
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=unit",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_get_project_dataframe_schema_contact(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses contact schema with empty response (no tasks)."""
        client, mock_sdk = authed_client

        # Use empty task list to avoid extractor validation issues
        # (Contact schema requires specific custom fields that are
        # domain-specific to Asana workspace configuration)
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=contact",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_get_project_dataframe_invalid_schema_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Invalid schema value returns 422 validation error."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=invalid",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_get_project_dataframe_limit_validation_min(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Limit less than 1 returns 422 validation error."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?limit=0",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_get_project_dataframe_limit_validation_max(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Limit greater than 100 returns 422 validation error."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?limit=101",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_get_project_dataframe_json_format_default(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Default Accept header returns JSON records format."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        # Verify it's a list of records
        data = response.json()
        assert isinstance(data["data"], list)

    def test_get_project_dataframe_json_format_explicit(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Explicit application/json Accept header returns JSON records format."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={
                "Authorization": "Bearer test_pat_token_12345",
                "Accept": "application/json",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_get_project_dataframe_polars_format(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """application/x-polars-json Accept header returns Polars format."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={
                "Authorization": "Bearer test_pat_token_12345",
                "Accept": "application/x-polars-json",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-polars-json"

        # Polars format wraps data as string in response envelope
        data = response.json()
        assert "data" in data
        assert "meta" in data
        # The data field is a JSON string (Polars serialized)
        assert isinstance(data["data"], str)


class TestGetSectionDataframe:
    """Tests for GET /api/v1/dataframes/section/{gid} endpoint."""

    def test_get_section_dataframe_success_empty(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns empty dataframe for section with no tasks."""
        client, mock_sdk = authed_client

        # Mock section lookup to return parent project
        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        # Mock empty task list
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data
        assert data["data"] == []
        assert data["meta"]["pagination"]["has_more"] is False

    def test_get_section_dataframe_success_with_tasks(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns dataframe with task data."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_TASK_DATA, SAMPLE_TASK_DATA_2],
            None,
        )

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 2

    def test_get_section_dataframe_with_pagination(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully returns dataframe with pagination metadata."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = (
            [SAMPLE_TASK_DATA],
            "next_cursor_xyz",
        )

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?limit=1",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["pagination"]["has_more"] is True
        assert data["meta"]["pagination"]["next_offset"] == "next_cursor_xyz"

    def test_get_section_dataframe_with_offset(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses offset parameter for pagination."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA_2], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?offset=cursor456",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify offset was passed to HTTP client
        call_args = mock_sdk._http.get_paginated.call_args
        assert call_args[1]["params"]["offset"] == "cursor456"

    def test_get_section_dataframe_schema_base(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses base schema (default)."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?schema=base",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

    def test_get_section_dataframe_schema_unit(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses unit schema with empty response (no tasks)."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        # Use empty task list to avoid extractor validation issues
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?schema=unit",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_get_section_dataframe_schema_contact(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Successfully uses contact schema with empty response (no tasks)."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        # Use empty task list to avoid extractor validation issues
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?schema=contact",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_get_section_dataframe_invalid_schema_returns_422(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Invalid schema value returns 422 validation error."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?schema=invalid",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_get_section_dataframe_limit_validation_min(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Limit less than 1 returns 422 validation error."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?limit=0",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_get_section_dataframe_limit_validation_max(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Limit greater than 100 returns 422 validation error."""
        client, _ = authed_client

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}?limit=101",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 422

    def test_get_section_dataframe_not_found_returns_404(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Section without parent project returns 404."""
        client, mock_sdk = authed_client

        # Mock section lookup to return no parent project
        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {},  # No gid in project dict
        }

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 404
        assert "Section not found" in response.json()["detail"]

    def test_get_section_dataframe_no_project_returns_404(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Section without project key returns 404."""
        client, mock_sdk = authed_client

        # Mock section lookup to return no project key
        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            # No 'project' key at all
        }

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 404

    def test_get_section_dataframe_json_format_default(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Default Accept header returns JSON records format."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_get_section_dataframe_polars_format(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """application/x-polars-json Accept header returns Polars format."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}",
            headers={
                "Authorization": "Bearer test_pat_token_12345",
                "Accept": "application/x-polars-json",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-polars-json"

        # Polars format wraps data as string
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], str)


class TestContentNegotiation:
    """Tests for content negotiation behavior per ADR-ASANA-005."""

    def test_accept_header_with_multiple_types(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Accept header with multiple types including polars returns polars."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={
                "Authorization": "Bearer test_pat_token_12345",
                "Accept": "text/html, application/x-polars-json, application/json",
            },
        )

        assert response.status_code == 200
        # Should pick polars since it's in the Accept list
        assert response.headers["content-type"] == "application/x-polars-json"

    def test_accept_header_unknown_type_defaults_to_json(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Unknown Accept header type defaults to JSON format."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={
                "Authorization": "Bearer test_pat_token_12345",
                "Accept": "text/xml",
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_no_accept_header_defaults_to_json(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Missing Accept header defaults to JSON format."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([SAMPLE_TASK_DATA], None)

        # Don't include Accept header (TestClient may add default)
        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


class TestSchemaTypeEnum:
    """Tests for SchemaType enum values and behavior."""

    def test_all_valid_schema_types(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """All valid schema types are accepted."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        for schema_type in ["base", "unit", "contact"]:
            response = client.get(
                f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema={schema_type}",
                headers={"Authorization": "Bearer test_pat_token_12345"},
            )
            assert response.status_code == 200, f"Schema {schema_type} should be valid"

    def test_case_sensitive_schema_validation(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Schema type validation is case-sensitive."""
        client, _ = authed_client

        # Uppercase should fail
        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?schema=BASE",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )
        assert response.status_code == 422


class TestApiCallParameters:
    """Tests verifying correct API call parameters are passed."""

    def test_project_endpoint_builds_correct_params(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Project endpoint passes correct parameters to HTTP client."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?limit=50",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify the HTTP call
        call_args = mock_sdk._http.get_paginated.call_args
        assert call_args[0][0] == "/tasks"
        params = call_args[1]["params"]
        assert params["project"] == TEST_PROJECT_GID
        assert params["limit"] == 50
        assert "opt_fields" in params

    def test_section_endpoint_fetches_section_first(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Section endpoint fetches section metadata before tasks."""
        client, mock_sdk = authed_client

        mock_sdk._http.get.return_value = {
            "gid": TEST_SECTION_GID,
            "project": {"gid": TEST_PROJECT_GID},
        }
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get(
            f"/api/v1/dataframes/section/{TEST_SECTION_GID}",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        # Verify section was fetched first
        mock_sdk._http.get.assert_called_once()
        get_call = mock_sdk._http.get.call_args
        assert f"/sections/{TEST_SECTION_GID}" in get_call[0][0]

        # Verify tasks were fetched with section param
        call_args = mock_sdk._http.get_paginated.call_args
        params = call_args[1]["params"]
        assert params["section"] == TEST_SECTION_GID

    def test_limit_is_capped_at_max(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        """Limit is capped at MAX_LIMIT (100) even if valid range allows it."""
        client, mock_sdk = authed_client

        mock_sdk._http.get_paginated.return_value = ([], None)

        # Request with limit=100 (max valid)
        response = client.get(
            f"/api/v1/dataframes/project/{TEST_PROJECT_GID}?limit=100",
            headers={"Authorization": "Bearer test_pat_token_12345"},
        )

        assert response.status_code == 200

        call_args = mock_sdk._http.get_paginated.call_args
        params = call_args[1]["params"]
        assert params["limit"] == 100
