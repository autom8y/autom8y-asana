"""AC-R1 tests for Sprint 2 receiver-surface — A1 body-precedence + B1 envelope.

Tests the 5 AC-R1 acceptance criteria:
  1. Positive: body project_gid returns 200 + non-empty rows + meta.project_gid matches body GID
  2. Precedence: body project_gid wins over registry-routed GID
  3. Legacy preservation: empty body → registry-routed semantics (Sprint 1 preserved)
  4. section_gid optional: body {project_gid + section_gid} → section-scoped query
  5. Regex validation: body project_gid "not-a-gid" → 422 ValidationError

Deliberate shortcuts (prototype):
- All GIDs are synthetic (16-digit patterns not real Asana data).
- DataFrames are hardcoded mocks via _get_dataframe patch.
- S3 backend not exercised here (DEF-005 — Item D integration test covers that).
- Concurrent request handling not tested.

What is NOT tested here:
- Live Asana API connectivity.
- Real SectionPersistence storage backend.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.services.resolver import EntityProjectRegistry

# Synthetic 16-digit GIDs (S-06 pattern).
_REGISTRY_PROJECT_GID = "9990000000000001"   # what the registry returns
_BODY_PROJECT_GID = "1234567890123456"        # body override — different from registry
_BODY_SECTION_GID = "9876543210987654"        # section_gid companion

JWT_TOKEN = "header.payload.signature"

# xdist group guard (SCAR-W1E-LOADGROUP-001).
# Must run sequentially — uses dependency_overrides (shared FastAPI app state).
pytestmark = [pytest.mark.xdist_group("query_routes")]


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _make_project_dataframe() -> pl.DataFrame:
    """Minimal DataFrame satisfying the project schema."""
    return pl.DataFrame(
        {
            "gid": ["1111111111111111", "2222222222222222"],
            "name": ["Test Project Alpha", "Test Project Beta"],
            "section": ["ACTIVE", "PAUSED"],
            "vertical": ["dental", "medical"],
            "office_phone": ["+15551234567", "+15559876543"],
        }
    )


@pytest.fixture(autouse=True)
def register_project_gids_sprint2():
    """Register synthetic GIDs for project entity (Sprint 2 receiver-surface).

    Registers _REGISTRY_PROJECT_GID as the registry-routed GID for 'project'.
    AC-R1 test 1 also uses _BODY_PROJECT_GID as the body override.
    """
    registry = EntityProjectRegistry.get_instance()
    registry.register(
        entity_type="project",
        project_gid=_REGISTRY_PROJECT_GID,
        project_name="Sprint 2 Smoke Projects",
    )
    registry.register(
        entity_type="section",
        project_gid=_REGISTRY_PROJECT_GID,
        project_name="Sprint 2 Smoke Sections",
    )
    yield


class TestAcR1BodyGidPositive:
    """AC-R1 test 1: body project_gid returns 200 + non-empty rows + meta.project_gid == body GID."""

    def test_body_project_gid_200_nonempty_meta_matches(self, client) -> None:
        """Positive: POST with body project_gid returns rows; meta.project_gid == body GID."""
        mock_df = _make_project_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/project/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"project_gid": _BODY_PROJECT_GID},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()["data"]
        # Non-empty rows
        assert len(body["data"]) > 0, "Expected non-empty rows when body project_gid set"
        # meta.project_gid == body GID (body-precedence rule)
        meta = body["meta"]
        assert meta["project_gid"] == _BODY_PROJECT_GID, (
            f"meta.project_gid should be body GID {_BODY_PROJECT_GID!r}, "
            f"got {meta['project_gid']!r}"
        )


class TestAcR2Precedence:
    """AC-R1 test 2: body project_gid wins over registry-routed GID."""

    def test_body_gid_overrides_registry(self, client) -> None:
        """Precedence: body project_gid != registry GID → response uses body GID."""
        mock_df = _make_project_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/project/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                # Body GID is different from _REGISTRY_PROJECT_GID
                json={"project_gid": _BODY_PROJECT_GID},
            )

        assert response.status_code == 200
        meta = response.json()["data"]["meta"]
        # Body GID must win; registry GID must NOT appear
        assert meta["project_gid"] == _BODY_PROJECT_GID, (
            "Body GID must override registry GID in response meta"
        )
        assert meta["project_gid"] != _REGISTRY_PROJECT_GID, (
            "Registry GID must not appear when body GID is present"
        )


class TestAcR3LegacyPreservation:
    """AC-R1 test 3: empty body → registry-routed legacy (Sprint 1 semantics)."""

    def test_empty_body_uses_registry_gid(self, client) -> None:
        """Legacy preservation: POST with {} (no project_gid) → registry GID in meta."""
        mock_df = _make_project_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/project/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},  # No project_gid — legacy path
            )

        assert response.status_code == 200
        meta = response.json()["data"]["meta"]
        # Legacy path: registry GID must be used
        assert meta["project_gid"] == _REGISTRY_PROJECT_GID, (
            f"Legacy path must use registry GID {_REGISTRY_PROJECT_GID!r}, "
            f"got {meta['project_gid']!r}"
        )


class TestAcR4SectionGidOptional:
    """AC-R1 test 4: body {project_gid + section_gid} → section-scoped query."""

    def test_section_gid_companion_accepted(self, client) -> None:
        """section_gid optional: body with both GIDs → 200, meta reflects project_gid."""
        mock_df = _make_project_dataframe()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=mock_df,
            ),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/project/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={
                    "project_gid": _BODY_PROJECT_GID,
                    "section_gid": _BODY_SECTION_GID,
                },
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        meta = response.json()["data"]["meta"]
        # project_gid body-precedence still applies
        assert meta["project_gid"] == _BODY_PROJECT_GID
        # Rows present
        rows = response.json()["data"]["data"]
        assert len(rows) > 0, "Expected non-empty rows with section_gid companion"


class TestAcR5RegexValidation:
    """AC-R1 test 5: invalid GID format → 422 ValidationError."""

    def test_invalid_project_gid_format_422(self, client) -> None:
        """Regex validation: non-16-digit GID → 422 from Pydantic field_validator."""
        response = client.post(
            "/v1/query/project/rows",
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            json={"project_gid": "not-a-gid"},
        )

        assert response.status_code == 422, (
            f"Expected 422 for invalid GID format, got {response.status_code}: {response.text}"
        )

    def test_invalid_section_gid_format_422(self, client) -> None:
        """Regex validation: non-16-digit section_gid → 422."""
        response = client.post(
            "/v1/query/project/rows",
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            json={
                "project_gid": _BODY_PROJECT_GID,
                "section_gid": "bad-section",
            },
        )

        assert response.status_code == 422, (
            f"Expected 422 for invalid section_gid format, got {response.status_code}: {response.text}"
        )

    def test_too_short_project_gid_422(self, client) -> None:
        """Regex validation: GID with fewer than 16 digits → 422."""
        response = client.post(
            "/v1/query/project/rows",
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
            json={"project_gid": "12345"},
        )

        assert response.status_code == 422, (
            f"Expected 422 for short GID, got {response.status_code}: {response.text}"
        )
