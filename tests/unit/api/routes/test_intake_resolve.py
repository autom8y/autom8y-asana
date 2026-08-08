"""Tests for intake resolve endpoints.

POST /v1/resolve/business - Business resolution by phone/vertical
POST /v1/resolve/contact  - Contact resolution by email/phone within business scope

Per ADR-INT-001: Never return 404 for not-found business; use found=False.
Per ADR-INT-002: Email-then-phone priority, NO name matching.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.core.entity_registry import get_registry
from autom8_asana.services.intake_resolve_service import BusinessIndexUnavailableError
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Test data constants
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

BUSINESS_GID = "1234567890123456"
CONTACT_GID = "9876543210123456"
CONTACT_HOLDER_GID = "5555555555555555"

# Per ADR-resolve-cure-design-2026-08-08 D-1b, a resolved GID is only claimed as
# found=True after it is positively asserted to be a member of the registry's
# business project. Sourced from the descriptor, never a literal.
BUSINESS_PROJECT_GID = get_registry().require("business").primary_project_gid
BUSINESS_MEMBERSHIPS = [{"project": {"gid": BUSINESS_PROJECT_GID, "name": "Business"}}]


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


def _make_collect_mock(items):
    """Create a mock that supports the .collect() async pattern.

    Matches the PageIterator pattern: service calls method(...).collect().
    The method returns an object synchronously, and .collect() is awaited.
    """
    mock = MagicMock()
    mock.collect = AsyncMock(return_value=items)
    return mock


def _make_mock_asana_client(
    *,
    task_data: dict | None = None,
    subtasks: list[dict] | None = None,
    contact_holder_subtasks: list[dict] | None = None,
    raise_on_get: Exception | None = None,
    raise_on_subtasks: Exception | None = None,
) -> MagicMock:
    """Create mock AsanaClient with configurable task/subtask responses.

    subtasks_async returns a PageIterator-like object with .collect().
    The source code calls: await client.tasks.subtasks_async(...).collect()
    So subtasks_async is a sync call returning an object, and .collect() is awaited.
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    # Mock tasks.get_async
    if raise_on_get:
        mock_client.tasks.get_async = AsyncMock(side_effect=raise_on_get)
    else:
        mock_client.tasks.get_async = AsyncMock(return_value=task_data or {})

    # Mock tasks.subtasks_async with context-sensitive responses
    # subtasks_async(...) returns a PageIterator synchronously;
    # .collect() on that iterator is awaited.
    if raise_on_subtasks:
        # Make .collect() raise the exception when awaited
        error_mock = MagicMock()
        error_mock.collect = AsyncMock(side_effect=raise_on_subtasks)
        mock_client.tasks.subtasks_async = MagicMock(return_value=error_mock)
    elif contact_holder_subtasks is not None:
        # First call returns business subtasks (with contact_holder),
        # second call returns contacts under contact_holder
        call_count = {"n": 0}

        def subtasks_side_effect(gid, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _make_collect_mock(subtasks or [])
            return _make_collect_mock(contact_holder_subtasks)

        mock_client.tasks.subtasks_async = MagicMock(side_effect=subtasks_side_effect)
    else:
        mock_client.tasks.subtasks_async = MagicMock(
            return_value=_make_collect_mock(subtasks or []),
        )

    return mock_client


def _resolve_patches(
    mock_client: MagicMock | None = None,
    index_gid: str | None = None,
    build_on_miss: AsyncMock | None = None,
):
    """Create context manager patches for JWT, bot PAT, AsanaClient, and index.

    ``build_on_miss`` stubs the authoritative post-fast-path resolve. Its default
    -- return ``None`` -- is the ABSENT outcome (index consulted successfully,
    key genuinely missing). Pass an ``AsyncMock(side_effect=...)`` to exercise
    the UNAVAILABLE outcome. The mechanism itself is covered by the real-index
    fixtures in tests/unit/services/test_intake_resolve_business_index.py.
    """
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
        "autom8_asana.api.routes.intake_resolve.AsanaClient",
        return_value=mock_client_instance,
    )

    # Mock the module-level resolve_gid_from_index function
    index_patch = patch(
        "autom8_asana.services.intake_resolve_service.resolve_gid_from_index",
        return_value=index_gid,
    )

    build_patch = patch(
        "autom8_asana.services.intake_resolve_service."
        "IntakeResolveService._resolve_gid_build_on_miss",
        build_on_miss or AsyncMock(return_value=None),
    )

    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        index_patch,
        build_patch,
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
    """Create a test application with mocked lifespan discovery."""
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
# POST /v1/resolve/business
# ---------------------------------------------------------------------------


class TestResolveBusinessEndpoint:
    """POST /v1/resolve/business"""

    def test_found_existing_business(self, client: TestClient) -> None:
        """Known phone returns found=True with GID and metadata."""
        mock_asana = _make_mock_asana_client(
            task_data={
                "gid": BUSINESS_GID,
                "name": "Test Dental",
                "custom_fields": [
                    {"name": "company_id", "text_value": "guid-123", "gid": "cf_1"},
                ],
                "memberships": BUSINESS_MEMBERSHIPS,
            },
            subtasks=[
                {"gid": "sub_1", "name": "unit_holder"},
                {"gid": CONTACT_HOLDER_GID, "name": "contact_holder"},
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana, index_gid=BUSINESS_GID)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+15551234567"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        data = body["data"]
        assert data["found"] is True
        assert data["task_gid"] == BUSINESS_GID
        assert data["name"] == "Test Dental"
        assert data["office_phone"] == "+15551234567"
        assert data["company_id"] == "guid-123"
        assert data["has_unit"] is True
        assert data["has_contact_holder"] is True

    def test_not_found_returns_found_false(self, client: TestClient) -> None:
        """ABSENT: index consulted OK, key genuinely missing -> 200 found=False,
        NOT a 404 (ADR-INT-001)."""
        patches = _resolve_patches(index_gid=None)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+19999999999"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is False
        assert data["task_gid"] is None
        assert data["office_phone"] == "+19999999999"

    def test_index_unavailable_is_503_not_found_false(self, client: TestClient) -> None:
        """UNAVAILABLE: the index could not be consulted or built -> 503
        INDEX_NOT_READY.

        This is the OTHER half of the A-2 discriminator, and the wire difference
        is the whole point: the request above is byte-identical apart from the
        world-state. Pre-cure BOTH produced 200 found=false, and the calendly
        pipeline answers found=false with CREATE -- so fail-open guaranteed a
        duplicate production business on every index gap.
        """
        patches = _resolve_patches(
            index_gid=None,
            build_on_miss=AsyncMock(
                side_effect=BusinessIndexUnavailableError(
                    "resolution strategy reported INDEX_UNAVAILABLE"
                )
            ),
        )

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+19999999999"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 503
        body = resp.json()
        assert "INDEX_NOT_READY" in str(body)
        assert "found" not in str(body.get("data", ""))

    def test_unverified_business_is_503_not_found_true(self, client: TestClient) -> None:
        """A resolved GID that is not a member of the business project is refused.

        Pre-cure the fetch-failure branch answered found=True with an unverified
        bare GID; the unit fallback could put a UNIT gid there. Both are now
        fail-closed.
        """
        wrong_project_task = {
            "gid": BUSINESS_GID,
            "name": "A Unit, Not A Business",
            "custom_fields": [],
            "memberships": [{"project": {"gid": "1201081073731555", "name": "Business Units"}}],
        }
        mock_asana = _make_mock_asana_client(task_data=wrong_project_task, subtasks=[])
        patches = _resolve_patches(mock_client=mock_asana, index_gid=BUSINESS_GID)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+15551234567"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 503
        assert "BUSINESS_VERIFY_FAILED" in str(resp.json())

    def test_meta_request_id_is_a_real_correlation_id(self, client: TestClient) -> None:
        """D-2c / O-1: RequestIDMiddleware is now MOUNTED on the production app.

        It was previously mounted only by its own unit test's private FastAPI
        instance, so get_request_id resolved its "unknown" fallback on every
        response and X-Request-ID was never emitted.
        """
        patches = _resolve_patches(index_gid=None)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+19999999999"},
                headers=AUTH_HEADER,
            )

        request_id = resp.json()["meta"]["request_id"]
        assert request_id != "unknown"
        assert len(request_id) == 16
        # The response header and the envelope join on the same value.
        assert resp.headers["X-Request-ID"] == request_id

    def test_inbound_request_id_header_is_honoured(self, client: TestClient) -> None:
        """Cross-service correlation: a caller-supplied X-Request-ID propagates."""
        patches = _resolve_patches(index_gid=None)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+19999999999"},
                headers={**AUTH_HEADER, "X-Request-ID": "abcdef0123456789"},
            )

        assert resp.json()["meta"]["request_id"] == "abcdef0123456789"

    def test_with_vertical_filter(self, client: TestClient) -> None:
        """Vertical is passed through to the response."""
        mock_asana = _make_mock_asana_client(
            task_data={
                "gid": BUSINESS_GID,
                "name": "Multi Vertical Biz",
                "custom_fields": [],
                "memberships": BUSINESS_MEMBERSHIPS,
            },
            subtasks=[],
        )
        patches = _resolve_patches(mock_client=mock_asana, index_gid=BUSINESS_GID)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+15551234567", "vertical": "dental"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is True
        assert data["vertical"] == "dental"

    def test_invalid_phone_format_422(self, client: TestClient) -> None:
        """Non-E.164 phone returns 422 (rejected at Pydantic deserialization).

        Post-R03 migration: office_phone is OfficePhoneField (E.164 pattern
        enforced by Pydantic), so invalid values are rejected before the route
        handler runs. The custom 400/INVALID_PHONE_FORMAT path is superseded.
        """
        patches = _resolve_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "555-1234567"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 422

    def test_requires_s2s_jwt(self, client: TestClient) -> None:
        """Missing auth header returns 401."""
        resp = client.post(
            "/v1/resolve/business",
            json={"office_phone": "+15551234567"},
        )
        assert resp.status_code == 401

    def test_pat_token_rejected(self, client: TestClient) -> None:
        """PAT token rejected with SERVICE_TOKEN_REQUIRED."""
        # Patch JWT validation to detect PAT and reject
        with patch(
            "autom8_asana.auth.dual_mode.detect_token_type",
        ) as mock_detect:
            from autom8_asana.auth.dual_mode import AuthMode

            mock_detect.return_value = AuthMode.PAT
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+15551234567"},
                headers={"Authorization": "Bearer 1/pat_token_here_123456789"},
            )

        assert resp.status_code == 401

    def test_has_unit_flag(self, client: TestClient) -> None:
        """has_unit=True when business has a unit_holder subtask."""
        mock_asana = _make_mock_asana_client(
            task_data={
                "gid": BUSINESS_GID,
                "name": "Biz",
                "custom_fields": [],
                "memberships": BUSINESS_MEMBERSHIPS,
            },
            subtasks=[
                {"gid": "sub_unit", "name": "unit_holder"},
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana, index_gid=BUSINESS_GID)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+15551234567"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        assert resp.json()["data"]["has_unit"] is True
        assert resp.json()["data"]["has_contact_holder"] is False

    def test_has_contact_holder_flag(self, client: TestClient) -> None:
        """has_contact_holder=True when contact_holder subtask exists."""
        mock_asana = _make_mock_asana_client(
            task_data={
                "gid": BUSINESS_GID,
                "name": "Biz",
                "custom_fields": [],
                "memberships": BUSINESS_MEMBERSHIPS,
            },
            subtasks=[
                {"gid": CONTACT_HOLDER_GID, "name": "contact_holder"},
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana, index_gid=BUSINESS_GID)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/business",
                json={"office_phone": "+15551234567"},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        assert resp.json()["data"]["has_contact_holder"] is True
        assert resp.json()["data"]["has_unit"] is False


# ---------------------------------------------------------------------------
# POST /v1/resolve/contact
# ---------------------------------------------------------------------------


class TestResolveContactEndpoint:
    """POST /v1/resolve/contact"""

    def test_found_by_email(self, client: TestClient) -> None:
        """Email match returns found=True, match_field='email'."""
        mock_asana = _make_mock_asana_client(
            subtasks=[
                {"gid": CONTACT_HOLDER_GID, "name": "contact_holder"},
            ],
            contact_holder_subtasks=[
                {
                    "gid": CONTACT_GID,
                    "name": "Jane Doe",
                    "custom_fields": [
                        {
                            "name": "contact_email",
                            "text_value": "jane@example.com",
                            "gid": "cf_email",
                        },
                        {
                            "name": "contact_phone",
                            "text_value": "+15559876543",
                            "gid": "cf_phone",
                        },
                    ],
                },
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/contact",
                json={
                    "business_gid": BUSINESS_GID,
                    "email": "jane@example.com",
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body
        data = body["data"]
        assert data["found"] is True
        assert data["contact_gid"] == CONTACT_GID
        assert data["name"] == "Jane Doe"
        assert data["email"] == "jane@example.com"
        assert data["match_field"] == "email"

    def test_found_by_phone(self, client: TestClient) -> None:
        """Phone match returns found=True, match_field='phone'."""
        mock_asana = _make_mock_asana_client(
            subtasks=[
                {"gid": CONTACT_HOLDER_GID, "name": "contact_holder"},
            ],
            contact_holder_subtasks=[
                {
                    "gid": CONTACT_GID,
                    "name": "John Smith",
                    "custom_fields": [
                        {
                            "name": "contact_email",
                            "text_value": "john@other.com",
                            "gid": "cf_email",
                        },
                        {
                            "name": "contact_phone",
                            "text_value": "+15559876543",
                            "gid": "cf_phone",
                        },
                    ],
                },
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/contact",
                json={
                    "business_gid": BUSINESS_GID,
                    "phone": "+15559876543",
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is True
        assert data["match_field"] == "phone"

    def test_email_takes_priority(self, client: TestClient) -> None:
        """When both email and phone could match, email wins (ADR-INT-002)."""
        mock_asana = _make_mock_asana_client(
            subtasks=[
                {"gid": CONTACT_HOLDER_GID, "name": "contact_holder"},
            ],
            contact_holder_subtasks=[
                {
                    "gid": "contact_a",
                    "name": "Contact A",
                    "custom_fields": [
                        {
                            "name": "contact_email",
                            "text_value": "target@example.com",
                            "gid": "cf_email",
                        },
                        {
                            "name": "contact_phone",
                            "text_value": "+10000000000",
                            "gid": "cf_phone",
                        },
                    ],
                },
                {
                    "gid": "contact_b",
                    "name": "Contact B",
                    "custom_fields": [
                        {
                            "name": "contact_email",
                            "text_value": "other@example.com",
                            "gid": "cf_email",
                        },
                        {
                            "name": "contact_phone",
                            "text_value": "+15559876543",
                            "gid": "cf_phone",
                        },
                    ],
                },
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/contact",
                json={
                    "business_gid": BUSINESS_GID,
                    "email": "target@example.com",
                    "phone": "+15559876543",
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is True
        assert data["contact_gid"] == "contact_a"
        assert data["match_field"] == "email"

    def test_not_found(self, client: TestClient) -> None:
        """No match returns found=False, NOT a 404."""
        mock_asana = _make_mock_asana_client(
            subtasks=[
                {"gid": CONTACT_HOLDER_GID, "name": "contact_holder"},
            ],
            contact_holder_subtasks=[
                {
                    "gid": CONTACT_GID,
                    "name": "Existing Contact",
                    "custom_fields": [
                        {
                            "name": "contact_email",
                            "text_value": "other@example.com",
                            "gid": "cf_email",
                        },
                        {
                            "name": "contact_phone",
                            "text_value": "+10000000000",
                            "gid": "cf_phone",
                        },
                    ],
                },
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/contact",
                json={
                    "business_gid": BUSINESS_GID,
                    "email": "nonexistent@example.com",
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is False
        assert data["contact_gid"] is None
        assert data["match_field"] is None

    def test_no_criteria_422(self, client: TestClient) -> None:
        """Neither email nor phone returns 422 MISSING_CRITERIA."""
        patches = _resolve_patches()

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/contact",
                json={"business_gid": BUSINESS_GID},
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "MISSING_CRITERIA"

    def test_no_contact_holder_returns_found_false(self, client: TestClient) -> None:
        """Business without contact_holder returns found=False."""
        mock_asana = _make_mock_asana_client(
            subtasks=[
                {"gid": "sub_unit", "name": "unit_holder"},
                # No contact_holder
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/contact",
                json={
                    "business_gid": BUSINESS_GID,
                    "email": "jane@example.com",
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["found"] is False

    def test_requires_s2s_jwt(self, client: TestClient) -> None:
        """Missing auth header returns 401."""
        resp = client.post(
            "/v1/resolve/contact",
            json={
                "business_gid": BUSINESS_GID,
                "email": "jane@example.com",
            },
        )
        assert resp.status_code == 401

    def test_email_case_insensitive(self, client: TestClient) -> None:
        """Email matching is case-insensitive."""
        mock_asana = _make_mock_asana_client(
            subtasks=[
                {"gid": CONTACT_HOLDER_GID, "name": "contact_holder"},
            ],
            contact_holder_subtasks=[
                {
                    "gid": CONTACT_GID,
                    "name": "Jane Doe",
                    "custom_fields": [
                        {
                            "name": "contact_email",
                            "text_value": "Jane@Example.com",
                            "gid": "cf_email",
                        },
                    ],
                },
            ],
        )
        patches = _resolve_patches(mock_client=mock_asana)

        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            resp = client.post(
                "/v1/resolve/contact",
                json={
                    "business_gid": BUSINESS_GID,
                    "email": "jane@example.com",
                },
                headers=AUTH_HEADER,
            )

        assert resp.status_code == 200
        assert resp.json()["data"]["found"] is True
        assert resp.json()["data"]["match_field"] == "email"
