"""Tests for intake custom field write endpoint.

POST /v1/tasks/{task_gid}/custom-fields

Validates field resolution, partial failure handling, and auth requirements.
"""

from __future__ import annotations

import copy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.errors import NotFoundError, RateLimitError
from autom8_asana.services.resolver import EntityProjectRegistry
from tests._shared.cf_write_readback import (
    apply_write_body,
    captured_put_body,
    read_custom_field,
    real_tasks_client,
)

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

TASK_GID = "9999999999999999"

MOCK_CUSTOM_FIELDS = [
    {
        "gid": "cf_company_id",
        "name": "company_id",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_utm_source",
        "name": "UTM Source",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_utm_medium",
        "name": "UTM Medium",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_status",
        "name": "Status",
        "resource_subtype": "enum",
        "text_value": None,
        "enum_value": None,
        "enum_options": [
            {"gid": "opt_active", "name": "Active", "enabled": True},
            {"gid": "opt_paused", "name": "Paused", "enabled": True},
        ],
    },
    {
        "gid": "cf_ad_spend",
        "name": "Weekly Ad Spend",
        "resource_subtype": "number",
        "number_value": None,
        "enum_options": [],
    },
    {
        "gid": "cf_facebook",
        "name": "Facebook URL",
        "resource_subtype": "text",
        "text_value": None,
        "enum_options": [],
    },
]

MOCK_TASK_DATA = {
    "gid": TASK_GID,
    "custom_fields": MOCK_CUSTOM_FIELDS,
    "memberships": [{"project": {"gid": "proj_123"}}],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    """Create a mock JWT validation returning valid ServiceClaims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _make_mock_asana_client(
    *,
    task_data: dict | None = None,
    raise_on_get: Exception | None = None,
    raise_on_update: Exception | None = None,
) -> MagicMock:
    """Create mock AsanaClient for custom field tests."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    if raise_on_get:
        mock_client.tasks.get_async = AsyncMock(side_effect=raise_on_get)
    else:
        mock_client.tasks.get_async = AsyncMock(return_value=task_data or MOCK_TASK_DATA)

    if raise_on_update:
        mock_client.tasks.update_async = AsyncMock(side_effect=raise_on_update)
    else:
        mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

    return mock_client


def _custom_field_patches(mock_client: MagicMock | None = None):
    """Create context manager patches for JWT, bot PAT, and AsanaClient."""
    jwt_patch = patch(
        "autom8_asana.api.routes.internal.validate_service_token",
        _mock_jwt_validation(),
    )
    jwt_patch_canonical = patch(
        "autom8_asana.auth.jwt_validator.validate_service_token",
        _mock_jwt_validation(),
    )
    pat_patch = patch(
        "autom8_asana.auth.bot_pat.get_bot_pat",
        return_value="test_bot_pat",
    )
    pat_patch_deps = patch(
        "autom8_asana.api.dependencies.get_bot_pat",
        return_value="test_bot_pat",
    )

    mock_client_instance = mock_client or _make_mock_asana_client()

    client_patch = patch(
        "autom8_asana.api.routes.intake_custom_fields.AsanaClient",
        return_value=mock_client_instance,
    )

    # Patch SchemaRegistry to avoid startup dependency
    schema_patch = patch(
        "autom8_asana.services.intake_custom_field_service.IntakeCustomFieldService._enrich_from_schema_registry",
    )

    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        schema_patch,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before and after each test."""
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    """Create a test application with mocked lifespan."""
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="business",
                project_gid="1234567890123456",
                project_name="Business",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    """Synchronous test client with lifespan events."""
    with TestClient(app) as tc:
        yield tc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWriteCustomFieldsEndpoint:
    """POST /v1/tasks/{task_gid}/custom-fields"""

    def test_write_single_field(self, client: TestClient) -> None:
        """Single field written successfully."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"company_id": "guid-456"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_gid"] == TASK_GID
        assert data["fields_written"] == 1
        assert data["errors"] == []

    def test_write_multiple_fields(self, client: TestClient) -> None:
        """Multiple fields written in one call."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={
                    "fields": {
                        "company_id": "guid-789",
                        "UTM Source": "google",
                        "UTM Medium": "cpc",
                    }
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 3
        assert data["errors"] == []

    def test_company_id_writeback(self, client: TestClient) -> None:
        """company_id field write (primary use case)."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"company_id": "company-guid-abc"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_gid"] == TASK_GID
        assert data["fields_written"] == 1

        # Verify the Asana update was called with the right field GID, passed as
        # a ``custom_fields=`` KWARG. Reading ``kwargs["data"]`` here is banned:
        # that was the mock-lie that let CLASS-DEFECT-CF-WRITE ship green.
        mock_asana.tasks.update_async.assert_called_once()
        call_data = mock_asana.tasks.update_async.call_args
        assert "data" not in call_data.kwargs, "data= kwarg double-nests -- silent no-op"
        custom_fields = call_data.kwargs["custom_fields"]
        assert "cf_company_id" in custom_fields
        assert custom_fields["cf_company_id"] == "company-guid-abc"

    def test_partial_failure(self, client: TestClient) -> None:
        """Some fields succeed, some fail (unresolvable). Returns errors list."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={
                    "fields": {
                        "company_id": "guid-000",
                        "nonexistent_field": "value",
                    }
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1
        assert "nonexistent_field" in data["errors"]

    def test_task_not_found_404(self, client: TestClient) -> None:
        """Invalid task_gid returns 404 TASK_NOT_FOUND."""
        mock_asana = _make_mock_asana_client(raise_on_get=NotFoundError("Not found"))
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                "/v1/tasks/0000000000000000/custom-fields",
                json={"fields": {"company_id": "test"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "TASK_NOT_FOUND"

    def test_empty_fields_422(self, client: TestClient) -> None:
        """Empty fields dict returns 422 EMPTY_FIELDS."""
        patches = _custom_field_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "EMPTY_FIELDS"

    def test_requires_s2s_jwt(self, client: TestClient) -> None:
        """Missing auth header returns 401."""
        resp = client.post(
            f"/v1/tasks/{TASK_GID}/custom-fields",
            json={"fields": {"company_id": "test"}},
        )
        assert resp.status_code == 401

    def test_null_value_clears_field(self, client: TestClient) -> None:
        """None value clears the custom field."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"company_id": None}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1

        # Verify null was passed through to Asana
        mock_asana.tasks.update_async.assert_called_once()
        call_data = mock_asana.tasks.update_async.call_args
        assert "data" not in call_data.kwargs, "data= kwarg double-nests -- silent no-op"
        custom_fields = call_data.kwargs["custom_fields"]
        assert custom_fields["cf_company_id"] is None

    def test_social_profile_field_write(self, client: TestClient) -> None:
        """Social profile URL written as custom field."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={"fields": {"Facebook URL": "https://facebook.com/testbiz"}},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 1
        assert data["errors"] == []

    def test_all_fields_unresolvable(self, client: TestClient) -> None:
        """All fields fail resolution. Returns 200 with fields_written=0."""
        mock_asana = _make_mock_asana_client()
        patches = _custom_field_patches(mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            resp = client.post(
                f"/v1/tasks/{TASK_GID}/custom-fields",
                json={
                    "fields": {
                        "nonexistent_a": "val1",
                        "nonexistent_b": "val2",
                    }
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["fields_written"] == 0
        assert len(data["errors"]) == 2


# ---------------------------------------------------------------------------
# Anti-mock-lie transport seam + READBACK receipt (DIC/SUB-2, CLASS-DEFECT-CF-WRITE)
# ---------------------------------------------------------------------------
#
# The tests above stub ``tasks.update_async`` wholesale -- an AsyncMock accepts
# ANY signature, so they can only prove "the code passes what the code passes".
# That is exactly how ``data={"custom_fields": ...}`` shipped green while the
# real client marshaled ``json={"data": {"data": {...}}}`` and Asana answered
# 200 having written NOTHING.
#
# The tests below mock ONE LAYER LOWER (``self._http.put``), run the REAL
# ``TasksClient.update_async`` body-build, and then READ THE FIELD BACK through
# the production extractor. HTTP status is never the receipt.


def _direct_service(tasks):
    """Drive ``IntakeCustomFieldService`` over a real TasksClient shim."""
    from types import SimpleNamespace

    from autom8_asana.services.intake_custom_field_service import IntakeCustomFieldService

    return IntakeCustomFieldService(SimpleNamespace(tasks=tasks))


def _task_read_doc() -> dict:
    """A fresh, wholly-unwritten task-read document."""
    return {"gid": TASK_GID, "custom_fields": copy.deepcopy(MOCK_CUSTOM_FIELDS)}


class TestCustomFieldWriteTransportSeamAntiMockLie:
    """Verbatim outbound-body assertions at the httpx transport seam."""

    async def test_text_field_marshals_single_nested_body(self) -> None:
        """Text CF write reaches the wire as ``{"data": {"custom_fields": {...}}}``."""
        tasks, mock_http = real_tasks_client()
        tasks.get_async = AsyncMock(return_value=_task_read_doc())
        service = _direct_service(tasks)

        with patch(
            "autom8_asana.services.intake_custom_field_service"
            ".IntakeCustomFieldService._enrich_from_schema_registry"
        ):
            await service.write_fields(TASK_GID, {"company_id": "company-guid-abc"})

        mock_http.put.assert_awaited_once_with(
            f"/tasks/{TASK_GID}",
            json={"data": {"custom_fields": {"cf_company_id": "company-guid-abc"}}},
        )
        sent = captured_put_body(mock_http)
        # GATE-1 guard: the inner payload is the task-field map, never another
        # {"data": ...} wrapper. Reverting production to data={...} turns this RED.
        assert "data" not in sent["data"], "double-nested body -- CF write is a silent no-op"

    async def test_enum_field_marshals_plain_option_gid(self) -> None:
        """DIC/F-1: an enum CF WRITE value is the bare option gid string."""
        tasks, mock_http = real_tasks_client()
        tasks.get_async = AsyncMock(return_value=_task_read_doc())
        service = _direct_service(tasks)

        with patch(
            "autom8_asana.services.intake_custom_field_service"
            ".IntakeCustomFieldService._enrich_from_schema_registry"
        ):
            await service.write_fields(TASK_GID, {"Status": "Active"})

        mock_http.put.assert_awaited_once_with(
            f"/tasks/{TASK_GID}",
            json={"data": {"custom_fields": {"cf_status": "opt_active"}}},
        )
        sent = captured_put_body(mock_http)
        written = sent["data"]["custom_fields"]["cf_status"]
        assert written == "opt_active"
        assert not isinstance(written, dict), "enum READ shape on the WRITE path (DIC/F-1)"
        assert "data" not in sent["data"], "double-nested body -- CF write is a silent no-op"

    async def test_multi_field_write_marshals_one_flat_map(self) -> None:
        """All resolved fields ride a single flat ``custom_fields`` map."""
        tasks, mock_http = real_tasks_client()
        tasks.get_async = AsyncMock(return_value=_task_read_doc())
        service = _direct_service(tasks)

        with patch(
            "autom8_asana.services.intake_custom_field_service"
            ".IntakeCustomFieldService._enrich_from_schema_registry"
        ):
            await service.write_fields(
                TASK_GID,
                {"UTM Source": "google", "UTM Medium": "cpc"},
            )

        mock_http.put.assert_awaited_once_with(
            f"/tasks/{TASK_GID}",
            json={
                "data": {
                    "custom_fields": {
                        "cf_utm_source": "google",
                        "cf_utm_medium": "cpc",
                    }
                }
            },
        )


class TestCustomFieldWriteReadback:
    """READBACK receipt: the written field is read back out, not the HTTP status.

    Asana answers 200 for the broken body AND the correct one -- status proves
    nothing. Each test applies the VERBATIM captured body to a task-read
    document via the strict-subset oracle and reads the field back through the
    PRODUCTION extractor (``intake_resolve_service._extract_custom_field``).

    The two arms are non-vacuous only as a pair: the cured arm proves the oracle
    applies a correct body at all; the broken arm proves the pre-cure body is
    not applied. The live-Asana half of this receipt is owed to SUB-3 GATE-2.
    """

    async def test_text_field_reads_back_after_write(self) -> None:
        """CURED arm: the production write lands and the value reads back."""
        task_doc = _task_read_doc()
        tasks, mock_http = real_tasks_client()
        tasks.get_async = AsyncMock(return_value=copy.deepcopy(task_doc))
        service = _direct_service(tasks)

        with patch(
            "autom8_asana.services.intake_custom_field_service"
            ".IntakeCustomFieldService._enrich_from_schema_registry"
        ):
            await service.write_fields(TASK_GID, {"company_id": "company-guid-abc"})

        assert read_custom_field(task_doc, "company_id") is None  # unwritten to start

        after = apply_write_body(task_doc, captured_put_body(mock_http))
        assert read_custom_field(after, "company_id") == "company-guid-abc"

    async def test_enum_field_reads_back_after_write(self) -> None:
        """CURED arm, enum: the option NAME reads back after a plain-gid write."""
        task_doc = _task_read_doc()
        tasks, mock_http = real_tasks_client()
        tasks.get_async = AsyncMock(return_value=copy.deepcopy(task_doc))
        service = _direct_service(tasks)

        with patch(
            "autom8_asana.services.intake_custom_field_service"
            ".IntakeCustomFieldService._enrich_from_schema_registry"
        ):
            await service.write_fields(TASK_GID, {"Status": "Active"})

        after = apply_write_body(task_doc, captured_put_body(mock_http))
        assert read_custom_field(after, "Status") == "Active"

    async def test_pre_cure_double_nested_body_reads_back_none(self) -> None:
        """BROKEN arm: the pre-cure body is a 200 that writes nothing."""
        task_doc = _task_read_doc()
        pre_cure_body = {"data": {"data": {"custom_fields": {"cf_company_id": "company-guid-abc"}}}}

        after = apply_write_body(task_doc, pre_cure_body)

        assert read_custom_field(after, "company_id") is None

    async def test_enum_read_shape_on_write_path_reads_back_none(self) -> None:
        """BROKEN arm, DIC/F-1: the nested ``{"gid": opt}`` shape writes nothing."""
        task_doc = _task_read_doc()
        read_shape_body = {"data": {"custom_fields": {"cf_status": {"gid": "opt_active"}}}}

        after = apply_write_body(task_doc, read_shape_body)

        assert read_custom_field(after, "Status") is None
