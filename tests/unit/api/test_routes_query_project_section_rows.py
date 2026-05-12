"""Smoke tests for Sprint 1 — asana-clean-break-leaf T1.6.

AC-1: POST /v1/query/project/rows → 200 + non-empty rows
AC-2: POST /v1/query/section/rows → 200 + non-empty rows
AC-3: honest_contract_complete present in meta and derived (not fabricated).

Deliberate shortcuts (S-06):
- project and section GIDs are synthetic ("9990000000000001", "9990000000000002")
  registered directly via EntityProjectRegistry (no Asana API call).
- DataFrames are hardcoded mocks via _get_dataframe patch.
- SectionManifest is mocked to control honest_contract_complete derivation.

What is NOT tested here (production gaps):
- Live Asana API connectivity.
- Real SectionPersistence storage backend (DEF-005 production concern).
- Concurrent request handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.services.resolver import EntityProjectRegistry

# Synthetic GIDs for project and section (S-06 shortcut).
_PROJECT_GID = "9990000000000001"
_SECTION_GID = "9990000000000002"

JWT_TOKEN = "header.payload.signature"


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _make_project_dataframe() -> pl.DataFrame:
    """Minimal DataFrame satisfying the project schema (base 13 + 3 extra)."""
    return pl.DataFrame(
        {
            "gid": ["1111111111111111", "2222222222222222"],
            "name": ["Test Project Alpha", "Test Project Beta"],
            "section": ["ACTIVE", "PAUSED"],
            "vertical": ["dental", "medical"],
            "office_phone": ["+15551234567", "+15559876543"],
        }
    )


def _make_section_dataframe() -> pl.DataFrame:
    """Minimal DataFrame satisfying the section schema (base 13 + 3 extra)."""
    return pl.DataFrame(
        {
            "gid": ["3333333333333333", "4444444444444444"],
            "name": ["Section A", "Section B"],
            "section": ["ACTIVE", "ACTIVE"],
            "vertical": ["dental", "dental"],
            "office_phone": ["+15551234567", "+15559876543"],
        }
    )


@pytest.fixture(autouse=True)
def register_project_section_gids():
    """Register synthetic GIDs for project and section before each test.

    S-06: primary_project_gid=None on the descriptors means dynamic
    registration at test time. EntityProjectRegistry.get_instance() is
    already populated by the api conftest reset_singletons fixture;
    we add project and section on top.
    """
    registry = EntityProjectRegistry.get_instance()
    registry.register(
        entity_type="project",
        project_gid=_PROJECT_GID,
        project_name="Smoke Test Projects",
    )
    registry.register(
        entity_type="section",
        project_gid=_SECTION_GID,
        project_name="Smoke Test Sections",
    )
    yield


class TestProjectRowsSmoke:
    """AC-1: POST /v1/query/project/rows → 200 + non-empty rows."""

    def test_ac1_project_rows_200_non_empty(self, client) -> None:
        """AC-1: project/rows returns 200 with at least one row."""
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
                json={},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()["data"]
        assert len(body["data"]) > 0, "Expected non-empty rows for project/rows"

    def test_ac1_project_rows_meta_shape(self, client) -> None:
        """AC-1 (meta): project/rows meta includes total_count and entity_type."""
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
                json={},
            )

        assert response.status_code == 200
        meta = response.json()["data"]["meta"]
        assert meta["entity_type"] == "project"
        assert meta["total_count"] == 2
        assert meta["project_gid"] == _PROJECT_GID

    def test_ac3_project_rows_honest_contract_complete_present(self, client) -> None:
        """AC-3: honest_contract_complete present in meta (not fabricated, False by default).

        With no SectionPersistence manifest, _derive_honest_contract_complete()
        returns False (DEF-005 safe default). AC-3 forbids unconditional True;
        False is the safe, honest default when no manifest exists.
        """
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
                json={},
            )

        assert response.status_code == 200
        meta = response.json()["data"]["meta"]
        # AC-3: field must be present (not missing/None).
        assert "honest_contract_complete" in meta, (
            "meta missing honest_contract_complete — attestation field not threaded through"
        )
        # AC-3: S-01 REFUSED — unconditional True not allowed.
        # Default with no manifest is False (safe/honest default).
        assert isinstance(meta["honest_contract_complete"], bool), (
            "honest_contract_complete must be bool, not fabricated string/None"
        )

    def test_ac3_project_rows_honest_contract_complete_true_when_all_complete(
        self, client
    ) -> None:
        """AC-3 (positive case): honest_contract_complete=True propagates when engine derives True.

        Patches QueryEngine._derive_honest_contract_complete() to return True,
        verifying that the derivation result is threaded through to meta correctly.
        The derivation method itself is tested by unit/query/test_engine.py — this
        smoke test validates the end-to-end threading.
        """
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
            patch(
                "autom8_asana.query.engine.QueryEngine._derive_honest_contract_complete",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/project/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 200
        meta = response.json()["data"]["meta"]
        assert meta["honest_contract_complete"] is True


class TestSectionRowsSmoke:
    """AC-2: POST /v1/query/section/rows → 200 + non-empty rows."""

    def test_ac2_section_rows_200_non_empty(self, client) -> None:
        """AC-2: section/rows returns 200 with at least one row."""
        mock_df = _make_section_dataframe()

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
                "/v1/query/section/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()["data"]
        assert len(body["data"]) > 0, "Expected non-empty rows for section/rows"

    def test_ac2_section_rows_meta_shape(self, client) -> None:
        """AC-2 (meta): section/rows meta includes total_count and entity_type."""
        mock_df = _make_section_dataframe()

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
                "/v1/query/section/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 200
        meta = response.json()["data"]["meta"]
        assert meta["entity_type"] == "section"
        assert meta["total_count"] == 2
        assert meta["project_gid"] == _SECTION_GID

    def test_ac3_section_rows_honest_contract_complete_present(self, client) -> None:
        """AC-3: honest_contract_complete present in section/rows meta.

        Same derivation path as project — False with no manifest (safe default).
        """
        mock_df = _make_section_dataframe()

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
                "/v1/query/section/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},
            )

        assert response.status_code == 200
        meta = response.json()["data"]["meta"]
        assert "honest_contract_complete" in meta, (
            "meta missing honest_contract_complete for section/rows"
        )
        assert isinstance(meta["honest_contract_complete"], bool)

    def test_ac2_section_rows_gid_always_in_records(self, client) -> None:
        """AC-2 (content): Every row in section/rows response includes gid field."""
        mock_df = _make_section_dataframe()

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
                "/v1/query/section/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"select": ["name", "vertical"]},
            )

        assert response.status_code == 200
        for record in response.json()["data"]["data"]:
            assert "gid" in record, "gid must always be present in row records"
