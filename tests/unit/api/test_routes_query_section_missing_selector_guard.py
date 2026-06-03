"""PQ-5 fail-closed guard — section-entity request missing its required selector.

Locks the fail-closed branch added at query.py (immediately after the risk-1
project_gid guard): a section-entity request that supplies project_gid but omits
the live `section` selector must be REJECTED with 400, not silently degenerated
into an unfiltered project-wide 200.

Root vulnerability (reconciled at source 2026-06-03):
- The engine applies the section predicate ONLY `if section_name_filter is not None`
  (engine.py "7.5 Apply section filter"). `_resolve_section` returns None when
  `request.section is None`. So a section query with no `section` selector skips
  section narrowing and returns the unfiltered project frame as a 200 — a
  liveness-masquerade (S7-GATE-FIDELITY false-negative class).
- `request.section_gid` is INERT on this path: it is declared on RowsRequest but
  never consumed by the engine / resolve_section_index post the S3-MAP fix. So the
  live, required selector is `section` (the name), NOT `section_gid`.
- The pre-existing project_gid guard (risk-1) does NOT cover this: a section
  request can carry project_gid (passing risk-1) yet omit `section`.

Deliberate shortcuts (prototype):
- All GIDs are synthetic (16-digit patterns, not real Asana data).
- DataFrame is a hardcoded mock via _get_dataframe patch.
- Live Asana API / real SectionPersistence backend not exercised.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.services.resolver import EntityProjectRegistry

# Synthetic 16-digit GIDs (S-06 pattern).
_BODY_PROJECT_GID = "1234567890123456"
_BODY_SECTION_GID = "9876543210987654"  # inert on the /rows path — used to prove it does NOT scope

JWT_TOKEN = "header.payload.signature"

# xdist group guard (SCAR-W1E-LOADGROUP-001): shares FastAPI app state via the
# module-scoped client; must run in the same group as the sibling route tests.
pytestmark = [pytest.mark.xdist_group("query_routes")]


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _make_section_dataframe() -> pl.DataFrame:
    """Minimal DataFrame satisfying the project/section frame shape.

    Two rows in two distinct sections — so a correctly-scoped section query would
    return a strict subset, and a degenerate unfiltered query would return both.
    """
    return pl.DataFrame(
        {
            "gid": ["1111111111111111", "2222222222222222"],
            "name": ["Task Alpha", "Task Beta"],
            "section": ["ACTIVE", "PAUSED"],
            "vertical": ["dental", "medical"],
            "office_phone": ["+15551234567", "+15559876543"],
        }
    )


@pytest.fixture(autouse=True)
def register_section_gid():
    """Register a synthetic GID for the section entity so routing resolves.

    The guard fires BEFORE the engine regardless of registration; registration
    here keeps the non-regression (section-supplied) test on the happy path.
    """
    registry = EntityProjectRegistry.get_instance()
    registry.register(
        entity_type="section",
        project_gid=_BODY_PROJECT_GID,
        project_name="PQ-5 Guard Sections",
    )
    registry.register(
        entity_type="project",
        project_gid=_BODY_PROJECT_GID,
        project_name="PQ-5 Guard Projects",
    )
    yield


def _patched(mock_df: pl.DataFrame):
    """Context-manager list mirroring the sibling route tests' patch stack.

    Returns (jwt, bot_pat, asana_client_patch, get_df_patch). The caller enters
    all four and binds the AsanaClient patch's mock to drive __aenter__/__aexit__.
    """
    return [
        patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ),
        patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            return_value="test_bot_pat",
        ),
        patch("autom8_asana.client.AsanaClient"),
        patch(
            "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
            new_callable=AsyncMock,
            return_value=mock_df,
        ),
    ]


class TestPq5GuardFires:
    """The guard converts the silent degenerate-200 into an explicit 400."""

    def test_section_request_without_selector_is_rejected_400(self, client) -> None:
        """section entity + project_gid + NO section selector → 400 (was: unfiltered 200)."""
        mock_df = _make_section_dataframe()
        jwt_p, pat_p, client_p, df_p = _patched(mock_df)
        with jwt_p, pat_p, client_p as mock_client_class, df_p:
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/section/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"project_gid": _BODY_PROJECT_GID},  # no `section` selector
            )

        assert response.status_code == 400, (
            "section-entity request without a `section` selector must fail-closed 400, "
            f"not silently return an unfiltered project-wide frame; got {response.status_code}: "
            f"{response.text}"
        )
        assert "MISSING_SECTION_SELECTOR" in response.text, (
            f"expected MISSING_SECTION_SELECTOR-class error, got: {response.text}"
        )

    def test_section_gid_alone_does_not_satisfy_the_guard(self, client) -> None:
        """section_gid is INERT — supplying ONLY section_gid still fails-closed 400.

        This is the load-bearing reconciliation receipt: section_gid is declared on
        RowsRequest but never consumed on the /rows path, so it does NOT scope the
        query. A caller who supplies only section_gid (expecting it to narrow) would
        otherwise get the degenerate unfiltered 200. The guard requires `section`.
        """
        mock_df = _make_section_dataframe()
        jwt_p, pat_p, client_p, df_p = _patched(mock_df)
        with jwt_p, pat_p, client_p as mock_client_class, df_p:
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/section/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"project_gid": _BODY_PROJECT_GID, "section_gid": _BODY_SECTION_GID},
            )

        assert response.status_code == 400, (
            "section_gid is inert on the /rows path; supplying only section_gid must "
            f"still fail-closed 400 (the live selector is `section`); got {response.status_code}: "
            f"{response.text}"
        )


class TestPq5GuardNonRegression:
    """The guard must NOT block legitimate traffic."""

    def test_section_request_with_section_selector_passes_guard(self, client) -> None:
        """section entity + project_gid + `section` selector → NOT blocked by the guard.

        Reaches the engine (200) with the section narrowing applied. The point is
        that the guard does not fire; `resolve_section_index` is stubbed so the
        section name resolves without a live S3/manifest round-trip.
        """
        mock_df = _make_section_dataframe()
        # Stub the section index so "ACTIVE" resolves to a (truthy) gid; the engine's
        # _resolve_section returns the section name and applies the section predicate.
        mock_index = MagicMock()
        mock_index.resolve.return_value = "ACTIVE"
        jwt_p, pat_p, client_p, df_p = _patched(mock_df)
        with (
            jwt_p,
            pat_p,
            client_p as mock_client_class,
            df_p,
            patch(
                "autom8_asana.api.routes.query.resolve_section_index",
                new_callable=AsyncMock,
                return_value=mock_index,
            ),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/section/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"project_gid": _BODY_PROJECT_GID, "section": "ACTIVE"},
            )

        # The guard must NOT fire: a MISSING_SECTION_SELECTOR rejection is the failure
        # we are guarding against over-blocking. A 200 (section narrowed to ACTIVE) is
        # the expected pass.
        assert "MISSING_SECTION_SELECTOR" not in response.text, (
            "the guard over-fired on a section request that DID supply a `section` "
            f"selector: {response.text}"
        )
        assert response.status_code == 200, (
            "section request WITH a `section` selector must pass the guard and reach "
            f"the engine; got {response.status_code}: {response.text}"
        )
        # The section predicate narrowed the frame to the ACTIVE row only.
        rows = response.json()["data"]["data"]
        assert all(r["section"] == "ACTIVE" for r in rows), (
            f"section narrowing should have filtered to ACTIVE rows only; got {rows}"
        )

    def test_project_request_without_section_is_unaffected(self, client) -> None:
        """project entity (not section) → guard must NOT fire even with no section.

        A project-wide read is a legitimate request; the guard is section-only.
        """
        mock_df = _make_section_dataframe()
        jwt_p, pat_p, client_p, df_p = _patched(mock_df)
        with jwt_p, pat_p, client_p as mock_client_class, df_p:
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/project/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={"project_gid": _BODY_PROJECT_GID},  # no section — legitimate for project
            )

        assert response.status_code == 200, (
            "project-entity request must be unaffected by the section-only guard; "
            f"got {response.status_code}: {response.text}"
        )
