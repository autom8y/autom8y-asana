"""Tests for the GET /api/v1/tags satellite read surface (WS-B1 / TAG-1).

Covers the two-sided name-resolution primitive at the route altitude (route +
TagService + envelope, only the SDK client mocked), plus the governed-vocabulary
idempotency annotation and the workspace-not-configured failure path.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from tests.unit.api.conftest import TEST_WORKSPACE_GID

_AUTH = {"Authorization": "Bearer test_pat_token_12345"}

_PLAY_TAG = {"gid": "1209319457948185", "name": "play_custom_calendar_integration"}
_OTHER_TAG = {"gid": "1201265144487000", "name": "Urgent"}


class TestListTags:
    """Unfiltered listing: paginated passthrough of workspace tags."""

    def test_list_tags_success(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_sdk = authed_client
        mock_sdk.default_workspace_gid = TEST_WORKSPACE_GID
        mock_sdk._http.get_paginated.return_value = ([_PLAY_TAG, _OTHER_TAG], None)

        response = client.get("/api/v1/tags", headers=_AUTH)

        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body
        assert len(body["data"]) == 2
        assert body["meta"]["pagination"]["has_more"] is False

    def test_list_tags_pagination(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_sdk = authed_client
        mock_sdk.default_workspace_gid = TEST_WORKSPACE_GID
        mock_sdk._http.get_paginated.return_value = ([_PLAY_TAG], "next_cursor")

        response = client.get("/api/v1/tags?limit=1", headers=_AUTH)

        assert response.status_code == 200
        pagination = response.json()["meta"]["pagination"]
        assert pagination["has_more"] is True
        assert pagination["next_offset"] == "next_cursor"
        assert pagination["limit"] == 1

    def test_list_tags_passes_offset(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_sdk = authed_client
        mock_sdk.default_workspace_gid = TEST_WORKSPACE_GID
        mock_sdk._http.get_paginated.return_value = ([], None)

        response = client.get("/api/v1/tags?offset=cursor123", headers=_AUTH)

        assert response.status_code == 200
        params = mock_sdk._http.get_paginated.call_args.kwargs["params"]
        assert params["offset"] == "cursor123"


class TestResolveTagByName:
    """?name=X: the exact-match name->GID resolution primitive (two-sided)."""

    def test_name_filter_hit_returns_tag(self, authed_client: tuple[TestClient, MagicMock]) -> None:
        client, mock_sdk = authed_client
        mock_sdk.default_workspace_gid = TEST_WORKSPACE_GID
        mock_sdk._http.get_paginated.return_value = ([_PLAY_TAG, _OTHER_TAG], None)

        response = client.get("/api/v1/tags?name=play_custom_calendar_integration", headers=_AUTH)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["gid"] == _PLAY_TAG["gid"]
        assert data[0]["name"] == _PLAY_TAG["name"]

    def test_name_filter_miss_returns_empty_200(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        # Documented design choice: a filtered-collection miss is HTTP 200 with
        # an empty data list (not 404) -- an empty collection, not a missing
        # resource. The caller detects the miss via len(data) == 0.
        client, mock_sdk = authed_client
        mock_sdk.default_workspace_gid = TEST_WORKSPACE_GID
        mock_sdk._http.get_paginated.return_value = ([_OTHER_TAG], None)

        response = client.get("/api/v1/tags?name=nonexistent_tag", headers=_AUTH)

        assert response.status_code == 200
        assert response.json()["data"] == []


class TestTagsIdempotencyAnnotation:
    """The read surface declares itself idempotent with no side effects."""

    def test_get_tags_is_annotated_idempotent_no_side_effects(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        client, _ = authed_client

        spec = client.get("/openapi.json").json()
        get_op = spec["paths"]["/api/v1/tags"]["get"]

        assert get_op["x-fleet-idempotency"]["idempotent"] is True
        assert get_op["x-fleet-side-effects"] == []


class TestTagsWorkspaceConfiguration:
    """Fails closed (503) when the default workspace is not configured."""

    def test_missing_workspace_returns_503(
        self, authed_client: tuple[TestClient, MagicMock]
    ) -> None:
        client, mock_sdk = authed_client
        mock_sdk.default_workspace_gid = None

        response = client.get("/api/v1/tags", headers=_AUTH)

        assert response.status_code == 503
