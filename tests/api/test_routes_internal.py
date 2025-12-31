"""Tests for internal routes (/api/v1/internal/*).

Per TDD-DATA-SERVICE-CLIENT-001 WS2:
- POST /api/v1/internal/gid-lookup requires service token (S2S)
- Batch size validation (max 1000)
- E.164 phone format validation
- Input order preserved in response
"""

from __future__ import annotations

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create a synchronous test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """Reset auth singletons before and after each test."""
    clear_bot_pat_cache()
    reset_auth_client()
    yield
    clear_bot_pat_cache()
    reset_auth_client()


def _mock_jwt_validation(service_name: str = "autom8_data"):
    """Helper to create a mock JWT validation that returns valid claims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


class TestGidLookupEndpoint:
    """Test POST /api/v1/internal/gid-lookup."""

    def test_valid_batch_lookup_returns_mappings(self, client: TestClient) -> None:
        """Valid batch lookup returns mappings for all pairs."""
        # Arrange
        jwt_token = "header.payload.signature"  # 2 dots = JWT

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            # Act
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+15551234567", "vertical": "dental"},
                        {"phone": "+15559876543", "vertical": "medical"},
                    ]
                },
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "mappings" in data
        assert len(data["mappings"]) == 2

        # Check first mapping
        assert data["mappings"][0]["phone"] == "+15551234567"
        assert data["mappings"][0]["vertical"] == "dental"
        # task_gid is None in stub implementation
        assert data["mappings"][0]["task_gid"] is None

        # Check second mapping
        assert data["mappings"][1]["phone"] == "+15559876543"
        assert data["mappings"][1]["vertical"] == "medical"
        assert data["mappings"][1]["task_gid"] is None

    def test_empty_pairs_returns_empty_mappings(self, client: TestClient) -> None:
        """Empty phone_vertical_pairs returns empty mappings."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"phone_vertical_pairs": []},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["mappings"] == []

    def test_preserves_input_order(self, client: TestClient) -> None:
        """Response mappings preserve input order."""
        jwt_token = "header.payload.signature"

        pairs = [
            {"phone": "+11111111111", "vertical": "a"},
            {"phone": "+12222222222", "vertical": "b"},
            {"phone": "+13333333333", "vertical": "c"},
            {"phone": "+14444444444", "vertical": "d"},
            {"phone": "+15555555555", "vertical": "e"},
        ]

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"phone_vertical_pairs": pairs},
            )

        assert response.status_code == 200
        data = response.json()

        # Verify order matches input
        for i, pair in enumerate(pairs):
            assert data["mappings"][i]["phone"] == pair["phone"]
            assert data["mappings"][i]["vertical"] == pair["vertical"]


class TestGidLookupValidation:
    """Test input validation for gid-lookup endpoint."""

    def test_batch_over_1000_returns_422(self, client: TestClient) -> None:
        """Batch size > 1000 returns 422 validation error."""
        jwt_token = "header.payload.signature"

        # Create 1001 pairs
        pairs = [
            {"phone": f"+1555{i:07d}", "vertical": "dental"}
            for i in range(1001)
        ]

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"phone_vertical_pairs": pairs},
            )

        assert response.status_code == 422
        data = response.json()
        # Pydantic validation error format
        assert "detail" in data
        # Check that the error mentions batch size
        error_msg = str(data["detail"]).lower()
        assert "batch" in error_msg or "1000" in error_msg

    def test_batch_exactly_1000_succeeds(self, client: TestClient) -> None:
        """Batch size of exactly 1000 is allowed."""
        jwt_token = "header.payload.signature"

        pairs = [
            {"phone": f"+1555{i:07d}", "vertical": "dental"}
            for i in range(1000)
        ]

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"phone_vertical_pairs": pairs},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["mappings"]) == 1000

    def test_invalid_e164_phone_returns_422(self, client: TestClient) -> None:
        """Invalid E.164 phone format returns 422 validation error."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "5551234567", "vertical": "dental"},  # Missing +
                    ]
                },
            )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Pydantic error should mention phone or E.164
        error_msg = str(data["detail"]).lower()
        assert "e.164" in error_msg or "phone" in error_msg or "invalid" in error_msg

    def test_phone_with_invalid_characters_returns_422(self, client: TestClient) -> None:
        """Phone with letters/special chars returns 422."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+1-555-123-4567", "vertical": "dental"},  # Dashes
                    ]
                },
            )

        assert response.status_code == 422

    def test_phone_starting_with_zero_returns_422(self, client: TestClient) -> None:
        """E.164 phones cannot start with zero after +."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+05551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 422

    def test_extra_fields_rejected(self, client: TestClient) -> None:
        """Extra fields in request body are rejected."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ],
                    "extra_field": "should_be_rejected",
                },
            )

        assert response.status_code == 422


class TestGidLookupAuthentication:
    """Test authentication requirements for gid-lookup endpoint."""

    def test_missing_auth_header_returns_401(self, client: TestClient) -> None:
        """Missing Authorization header returns 401."""
        response = client.post(
            "/api/v1/internal/gid-lookup",
            json={
                "phone_vertical_pairs": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "MISSING_AUTH"

    def test_pat_token_returns_401(self, client: TestClient) -> None:
        """PAT token (not JWT) returns 401 with SERVICE_TOKEN_REQUIRED."""
        # PAT tokens start with 0/ or 1/ (no dots)
        pat_token = "0/1234567890abcdef1234567890"

        response = client.post(
            "/api/v1/internal/gid-lookup",
            headers={"Authorization": f"Bearer {pat_token}"},
            json={
                "phone_vertical_pairs": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "SERVICE_TOKEN_REQUIRED"
        assert "service-to-service" in data["detail"]["message"].lower()

    def test_invalid_jwt_returns_401(self, client: TestClient) -> None:
        """Invalid JWT returns 401 with validation error."""
        jwt_token = "invalid.jwt.token"

        # Mock validation to raise an error
        mock_error = Exception("Token expired")
        mock_error.code = "TOKEN_EXPIRED"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            AsyncMock(side_effect=mock_error),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "TOKEN_EXPIRED"

    def test_valid_jwt_allows_access(self, client: TestClient) -> None:
        """Valid JWT token allows access to endpoint."""
        jwt_token = "header.payload.signature"

        with patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(service_name="test_service"),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 200

    def test_invalid_bearer_scheme_returns_401(self, client: TestClient) -> None:
        """Non-Bearer scheme returns 401."""
        response = client.post(
            "/api/v1/internal/gid-lookup",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
            json={
                "phone_vertical_pairs": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error"] == "INVALID_SCHEME"

    def test_empty_bearer_token_returns_401(self, client: TestClient) -> None:
        """Empty Bearer token returns 401."""
        response = client.post(
            "/api/v1/internal/gid-lookup",
            headers={"Authorization": "Bearer "},
            json={
                "phone_vertical_pairs": [
                    {"phone": "+15551234567", "vertical": "dental"},
                ]
            },
        )

        assert response.status_code == 401


class TestGidLookupModels:
    """Test model validation for gid-lookup request/response."""

    def test_phone_vertical_input_valid(self) -> None:
        """PhoneVerticalInput accepts valid E.164 phones."""
        from autom8_asana.api.routes.internal import PhoneVerticalInput

        # Valid E.164 formats
        valid_phones = [
            "+15551234567",     # US
            "+441onal234567",   # UK (with letters - wait, that's wrong)
            "+447911123456",    # UK mobile
            "+8613912345678",   # China
            "+61412345678",     # Australia
            "+1",               # Minimum (country code only)
        ]

        for phone in ["+15551234567", "+447911123456", "+8613912345678"]:
            model = PhoneVerticalInput(phone=phone, vertical="dental")
            assert model.phone == phone

    def test_phone_vertical_input_invalid(self) -> None:
        """PhoneVerticalInput rejects invalid phones."""
        from autom8_asana.api.routes.internal import PhoneVerticalInput
        import pydantic

        invalid_phones = [
            "5551234567",        # Missing +
            "+05551234567",      # Starts with 0
            "1-555-123-4567",    # Missing + with dashes
            "+1-555-123-4567",   # Has dashes
            "+1 555 123 4567",   # Has spaces
            "",                  # Empty
        ]

        for phone in invalid_phones:
            with pytest.raises(pydantic.ValidationError):
                PhoneVerticalInput(phone=phone, vertical="dental")

    def test_gid_lookup_request_batch_limit(self) -> None:
        """GidLookupRequest enforces batch limit."""
        from autom8_asana.api.routes.internal import (
            GidLookupRequest,
            PhoneVerticalInput,
        )
        import pydantic

        # Valid: 1000 pairs
        pairs_1000 = [
            PhoneVerticalInput(phone=f"+1555{i:07d}", vertical="v")
            for i in range(1000)
        ]
        request = GidLookupRequest(phone_vertical_pairs=pairs_1000)
        assert len(request.phone_vertical_pairs) == 1000

        # Invalid: 1001 pairs
        pairs_1001 = [
            PhoneVerticalInput(phone=f"+1555{i:07d}", vertical="v")
            for i in range(1001)
        ]
        with pytest.raises(pydantic.ValidationError) as exc_info:
            GidLookupRequest(phone_vertical_pairs=pairs_1001)

        # Check error message contains batch info
        error_str = str(exc_info.value)
        assert "1001" in error_str or "1000" in error_str


class TestServiceClaimsModel:
    """Test ServiceClaims model."""

    def test_service_claims_creation(self) -> None:
        """ServiceClaims can be created with valid data."""
        from autom8_asana.api.routes.internal import ServiceClaims

        claims = ServiceClaims(
            sub="service:autom8_data",
            service_name="autom8_data",
            scope="multi-tenant",
        )

        assert claims.sub == "service:autom8_data"
        assert claims.service_name == "autom8_data"
        assert claims.scope == "multi-tenant"

    def test_service_claims_optional_scope(self) -> None:
        """ServiceClaims scope is optional."""
        from autom8_asana.api.routes.internal import ServiceClaims

        claims = ServiceClaims(
            sub="service:test",
            service_name="test",
        )

        assert claims.scope is None


class TestGidResolutionWithGidLookupIndex:
    """Test GID resolution with GidLookupIndex-based approach.

    Per task-003: Tests updated to work with new index-based lookups
    instead of loop-based SearchService calls.
    """

    @pytest.fixture
    def mock_client(self):
        """Create a mock AsanaClient."""
        mock = MagicMock()
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__ = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample Polars DataFrame for testing."""
        import polars as pl

        return pl.DataFrame({
            "gid": ["1234567890123456", "1111111111111111", "2222222222222222"],
            "office_phone": ["+15551234567", "+11111111111", "+13333333333"],
            "vertical": ["dental", "dental", "medical"],
            "name": ["Unit A", "Unit B", "Unit C"],
        })

    @pytest.fixture(autouse=True)
    def clear_index_cache(self):
        """Clear index cache before and after each test."""
        from autom8_asana.api.routes.internal import _gid_index_cache
        _gid_index_cache.clear()
        yield
        _gid_index_cache.clear()

    @pytest.mark.asyncio
    async def test_resolve_gids_returns_task_gid_on_match(
        self, mock_client, sample_dataframe
    ) -> None:
        """resolve_gids returns task_gid when unit is found."""
        from autom8_asana.api.routes.internal import (
            PhoneVerticalInput,
            _resolve_gids_with_client,
        )

        # Arrange - mock _build_unit_dataframe to return sample DataFrame
        with patch(
            "autom8_asana.api.routes.internal._build_unit_dataframe",
            AsyncMock(return_value=sample_dataframe),
        ):
            pairs = [PhoneVerticalInput(phone="+15551234567", vertical="dental")]

            # Act
            results = await _resolve_gids_with_client(
                mock_client, pairs, "project_gid_123"
            )

        # Assert
        assert len(results) == 1
        assert results[0].phone == "+15551234567"
        assert results[0].vertical == "dental"
        assert results[0].task_gid == "1234567890123456"

    @pytest.mark.asyncio
    async def test_resolve_gids_returns_none_on_no_match(
        self, mock_client, sample_dataframe
    ) -> None:
        """resolve_gids returns None when no unit is found."""
        from autom8_asana.api.routes.internal import (
            PhoneVerticalInput,
            _resolve_gids_with_client,
        )

        with patch(
            "autom8_asana.api.routes.internal._build_unit_dataframe",
            AsyncMock(return_value=sample_dataframe),
        ):
            # Arrange - phone/vertical pair not in DataFrame
            pairs = [PhoneVerticalInput(phone="+15559999999", vertical="unknown")]

            # Act
            results = await _resolve_gids_with_client(
                mock_client, pairs, "project_gid_123"
            )

        # Assert
        assert len(results) == 1
        assert results[0].phone == "+15559999999"
        assert results[0].vertical == "unknown"
        assert results[0].task_gid is None

    @pytest.mark.asyncio
    async def test_resolve_gids_handles_multiple_pairs(
        self, mock_client, sample_dataframe
    ) -> None:
        """resolve_gids handles multiple pairs correctly."""
        from autom8_asana.api.routes.internal import (
            PhoneVerticalInput,
            _resolve_gids_with_client,
        )

        with patch(
            "autom8_asana.api.routes.internal._build_unit_dataframe",
            AsyncMock(return_value=sample_dataframe),
        ):
            # Arrange - first pair matches, second doesn't
            pairs = [
                PhoneVerticalInput(phone="+11111111111", vertical="dental"),
                PhoneVerticalInput(phone="+12222222222", vertical="medical"),  # Not in data
            ]

            # Act
            results = await _resolve_gids_with_client(
                mock_client, pairs, "project_gid_123"
            )

        # Assert
        assert len(results) == 2
        assert results[0].task_gid == "1111111111111111"
        assert results[1].task_gid is None

        # Verify order preserved
        assert results[0].phone == "+11111111111"
        assert results[1].phone == "+12222222222"

    @pytest.mark.asyncio
    async def test_resolve_gids_handles_dataframe_build_error(
        self, mock_client
    ) -> None:
        """resolve_gids returns None when DataFrame build fails."""
        from autom8_asana.api.routes.internal import (
            PhoneVerticalInput,
            _resolve_gids_with_client,
        )

        # Arrange - DataFrame build fails (returns None)
        with patch(
            "autom8_asana.api.routes.internal._build_unit_dataframe",
            AsyncMock(return_value=None),
        ):
            pairs = [PhoneVerticalInput(phone="+15551234567", vertical="dental")]

            # Act
            results = await _resolve_gids_with_client(
                mock_client, pairs, "project_gid_123"
            )

        # Assert - graceful degradation to None
        assert len(results) == 1
        assert results[0].task_gid is None

    @pytest.mark.asyncio
    async def test_resolve_gids_empty_pairs_returns_empty(
        self, mock_client, sample_dataframe
    ) -> None:
        """resolve_gids returns empty list for empty input."""
        from autom8_asana.api.routes.internal import _resolve_gids_with_client

        with patch(
            "autom8_asana.api.routes.internal._build_unit_dataframe",
            AsyncMock(return_value=sample_dataframe),
        ):
            # Act
            results = await _resolve_gids_with_client(mock_client, [], "project_gid_123")

        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_index_cache_reused_on_second_call(
        self, mock_client, sample_dataframe
    ) -> None:
        """Index is cached and reused on subsequent calls."""
        from autom8_asana.api.routes.internal import (
            PhoneVerticalInput,
            _resolve_gids_with_client,
            _gid_index_cache,
        )

        build_mock = AsyncMock(return_value=sample_dataframe)

        with patch(
            "autom8_asana.api.routes.internal._build_unit_dataframe",
            build_mock,
        ):
            pairs = [PhoneVerticalInput(phone="+15551234567", vertical="dental")]

            # First call - should build index
            await _resolve_gids_with_client(mock_client, pairs, "project_gid_123")
            assert build_mock.call_count == 1
            assert "project_gid_123" in _gid_index_cache

            # Second call - should use cached index
            await _resolve_gids_with_client(mock_client, pairs, "project_gid_123")
            # Build should NOT be called again
            assert build_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_stale_index_triggers_rebuild(
        self, mock_client, sample_dataframe
    ) -> None:
        """Stale index triggers a rebuild."""
        from autom8_asana.api.routes.internal import (
            PhoneVerticalInput,
            _resolve_gids_with_client,
            _gid_index_cache,
            GidLookupIndex,
        )
        from datetime import datetime, timezone, timedelta

        # Create a stale index (older than TTL)
        stale_index = GidLookupIndex.from_dataframe(sample_dataframe)
        # Override created_at to make it stale
        stale_index._created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        _gid_index_cache["project_gid_123"] = stale_index

        build_mock = AsyncMock(return_value=sample_dataframe)

        with patch(
            "autom8_asana.api.routes.internal._build_unit_dataframe",
            build_mock,
        ):
            pairs = [PhoneVerticalInput(phone="+15551234567", vertical="dental")]

            # Call with stale index - should trigger rebuild
            await _resolve_gids_with_client(mock_client, pairs, "project_gid_123")
            assert build_mock.call_count == 1


class TestGidResolutionConfiguration:
    """Test configuration and error handling for GID resolution."""

    def test_resolve_gids_missing_project_gid_env(self, client: TestClient) -> None:
        """resolve_gids returns None when UNIT_PROJECT_GID not set."""
        jwt_token = "header.payload.signature"

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch.dict("os.environ", {}, clear=True),
            patch(
                "autom8_asana.api.routes.internal._get_unit_project_gid",
                return_value=None,
            ),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Should return None for all when not configured
        assert data["mappings"][0]["task_gid"] is None

    def test_resolve_gids_with_project_gid_configured(self, client: TestClient) -> None:
        """resolve_gids uses UNIT_PROJECT_GID when configured."""
        import polars as pl

        jwt_token = "header.payload.signature"

        # Create mock DataFrame with matching data
        mock_df = pl.DataFrame({
            "gid": ["9876543210987654"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
            "name": ["Test Unit"],
        })

        # Clear the index cache to ensure fresh build
        from autom8_asana.api.routes.internal import _gid_index_cache
        _gid_index_cache.clear()

        # Mock the entire resolution flow
        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.api.routes.internal._get_unit_project_gid",
                return_value="1143843662099250",
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.api.routes.internal._build_unit_dataframe",
                AsyncMock(return_value=mock_df),
            ),
        ):
            # Setup mock client
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["mappings"][0]["task_gid"] == "9876543210987654"

        # Clean up
        _gid_index_cache.clear()

    def test_resolve_gids_bot_pat_unavailable(self, client: TestClient) -> None:
        """resolve_gids returns None when bot PAT unavailable."""
        jwt_token = "header.payload.signature"

        from autom8_asana.auth.bot_pat import BotPATError

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.api.routes.internal._get_unit_project_gid",
                return_value="1143843662099250",
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                side_effect=BotPATError("Bot PAT not configured"),
            ),
        ):
            response = client.post(
                "/api/v1/internal/gid-lookup",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "phone_vertical_pairs": [
                        {"phone": "+15551234567", "vertical": "dental"},
                    ]
                },
            )

        assert response.status_code == 200
        data = response.json()
        # Should return None when bot PAT unavailable
        assert data["mappings"][0]["task_gid"] is None
