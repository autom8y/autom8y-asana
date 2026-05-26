"""G2-RECV tests — body-parameterized entities resolvable on the UNREGISTERED path.

Implements TDD-G2RECV-001 §7 test plan (T1-T5). These tests deliberately exercise
the PRODUCTION path where project/section have NO EntityProjectRegistry GID — the
exact condition that fires in prod (ECS rev 420: project/section absent from
registered_types). They MUST NOT inherit the `register_project_gids_sprint2`
autouse fixture from test_routes_query_project_section_rows_sprint2.py; a fix that
only passes with that fixture re-ships the G2-RECV gap.

Isolation discipline:
- This is a SEPARATE module, so the sibling module's autouse fixture does not apply.
- The API conftest `reset_singletons` autouse fixture registers only
  offer/unit/contact/business — project/section stay UNREGISTERED here, which is
  precisely the prod condition under test.

Acceptance criteria locked:
- AC-G2R-3: project/section in the resolvable set (T2).
- AC-G2R-5: POST /v1/query/project/rows with body project_gid → 200 (T1).
- risk-1 guard: missing-body-GID fails fast 4xx, never None into the engine (T5).
- Non-regression: offer-domain still gated on registry/descriptor GID (T3).
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.services.entity_context import EntityContext
from autom8_asana.services.entity_service import EntityService
from autom8_asana.services.errors import ServiceNotConfiguredError, UnknownEntityError
from autom8_asana.services.resolver import EntityProjectRegistry, get_resolvable_entities

# Synthetic 16-digit GID (S-06 pattern) supplied via the request body.
_BODY_PROJECT_GID = "1234567890123456"

JWT_TOKEN = "header.payload.signature"

# xdist group guard (SCAR-W1E-LOADGROUP-001): shares FastAPI app state via the
# module-scoped client; must run in the same group as the sibling route tests.
pytestmark = [pytest.mark.xdist_group("query_routes")]


def _assert_no_sprint2_fixture() -> None:
    """Belt-and-suspenders: project/section must NOT be registered here.

    If a future refactor accidentally pulls in the sprint2 autouse fixture (or a
    sibling registers project/section), this guard makes the fidelity violation
    loud instead of silently masking the prod path.
    """
    registry = EntityProjectRegistry.get_instance()
    assert registry.get_project_gid("project") is None, (
        "project must be UNREGISTERED for the G2-RECV prod-path tests; "
        "the register_project_gids_sprint2 fixture must NOT apply here"
    )
    assert registry.get_project_gid("section") is None, (
        "section must be UNREGISTERED for the G2-RECV prod-path tests"
    )


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _make_project_dataframe() -> pl.DataFrame:
    """Minimal DataFrame satisfying the project schema (no row model — by design)."""
    return pl.DataFrame(
        {
            "gid": ["1111111111111111", "2222222222222222"],
            "name": ["Test Project Alpha", "Test Project Beta"],
            "section": ["ACTIVE", "PAUSED"],
            "vertical": ["dental", "medical"],
            "office_phone": ["+15551234567", "+15559876543"],
        }
    )


class TestT1UnregisteredProjectRows200WithBodyGid:
    """T1: POST /v1/query/project/rows with body project_gid on the UNREGISTERED path → 200."""

    def test_unregistered_project_rows_200_with_body_gid(self, client) -> None:
        """AC-G2R-5: unregistered project + body project_gid → 200 + RowsResponse; meta matches body GID."""
        _assert_no_sprint2_fixture()
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
            f"Expected 200 on the UNREGISTERED path, got {response.status_code}: {response.text}"
        )
        body = response.json()["data"]
        # Double-envelope per B1: data.data holds rows, data.meta holds metadata.
        assert len(body["data"]) > 0, "Expected non-empty rows when body project_gid set"
        assert body["meta"]["project_gid"] == _BODY_PROJECT_GID, (
            f"meta.project_gid should be the body GID {_BODY_PROJECT_GID!r}, "
            f"got {body['meta']['project_gid']!r}"
        )


class TestT2UnregisteredInResolvableSet:
    """T2 / AC-G2R-3: project + section join the resolvable set with NO registry GID."""

    def test_unregistered_project_section_in_resolvable_set(self) -> None:
        """project and section resolvable purely via body_parameterized=True."""
        EntityProjectRegistry.reset()
        registry = EntityProjectRegistry.get_instance()
        # Sanity: no registry GID for either body-param type.
        assert registry.get_project_gid("project") is None
        assert registry.get_project_gid("section") is None

        resolvable = get_resolvable_entities()

        assert "project" in resolvable, "project must be resolvable on schema + body_parameterized"
        assert "section" in resolvable, "section must be resolvable on schema + body_parameterized"


class TestT3OfferDomainStillRequiresGid:
    """T3 (NON-REGRESSION): the resolvability/configured gate is NOT globally loosened.

    Locks the ADR REJECT condition: offer-domain (body_parameterized=False) entities
    must STILL require a GID. Proven two ways:
      (a) the resolvability predicate excludes a non-body-param entity that has
          neither a registry GID nor a descriptor GID;
      (b) validate_entity_type still raises ServiceNotConfiguredError (GATE 2) for a
          non-body-param entity whose GID is None.
    """

    def test_offer_domain_predicate_excludes_gidless_non_body_param(self) -> None:
        """A synthetic non-body-param entity with no GID is NOT resolvable.

        Drives get_resolvable_entities with controlled registries so the assertion
        does not depend on which production entities happen to carry a hardcoded
        primary_project_gid. A real-world offer-domain type (e.g. process) carries
        body_parameterized=False; the relaxation must not admit it.
        """
        # Schema registry advertises one task type; entity registry maps it to a
        # non-body-param descriptor; project registry has NO GID for it.
        schema = MagicMock()
        schema.name = "process"
        schema_registry = MagicMock()
        schema_registry.list_task_types.return_value = ["process"]
        schema_registry.get_schema.return_value = schema

        project_registry = MagicMock()
        project_registry.get_project_gid.return_value = None  # no registry GID

        non_body_param_desc = replace(
            get_registry().get("unit"),  # real offer-domain descriptor shape
            name="process",
            primary_project_gid=None,
            body_parameterized=False,
        )

        with patch("autom8_asana.core.entity_registry.get_registry") as mock_get_reg:
            mock_get_reg.return_value.get.return_value = non_body_param_desc
            resolvable = get_resolvable_entities(
                schema_registry=schema_registry,
                project_registry=project_registry,
            )

        assert "process" not in resolvable, (
            "REJECT condition: a non-body-param entity with no GID must stay "
            "non-resolvable — the gate must not be globally loosened"
        )

    def test_validate_entity_type_gate2_still_raises_for_non_body_param(self) -> None:
        """GATE 2 still raises ServiceNotConfiguredError for a non-body-param gidless entity."""
        non_body_param_desc = replace(
            get_registry().get("unit"),
            name="process",
            primary_project_gid=None,
            body_parameterized=False,
        )

        entity_registry = MagicMock()
        entity_registry.require.return_value = non_body_param_desc

        project_registry = MagicMock()
        project_registry.get_project_gid.return_value = None

        service = EntityService(entity_registry=entity_registry, project_registry=project_registry)
        # GATE 1 is bypassed by overriding get_queryable_entities so we isolate GATE 2.
        service.get_queryable_entities = MagicMock(return_value={"process"})  # type: ignore[method-assign]

        with pytest.raises(ServiceNotConfiguredError):
            service.validate_entity_type("process")


class TestT4BodyParamEntityContextProjectGidNone:
    """T4: validate_entity_type for an unregistered body-param entity → ctx.project_gid is None, no raise."""

    def test_body_param_entity_context_project_gid_none(self) -> None:
        """project (body_parameterized=True, no registry GID) → EntityContext(project_gid=None)."""
        project_desc = get_registry().get("project")
        assert project_desc.body_parameterized is True

        entity_registry = MagicMock()
        entity_registry.require.return_value = project_desc

        project_registry = MagicMock()
        project_registry.get_project_gid.return_value = None  # unregistered

        service = EntityService(entity_registry=entity_registry, project_registry=project_registry)
        service.get_queryable_entities = MagicMock(return_value={"project"})  # type: ignore[method-assign]

        with patch(
            "autom8_asana.auth.bot_pat.get_bot_pat",
            return_value="test_bot_pat",
        ):
            ctx = service.validate_entity_type("project")

        assert isinstance(ctx, EntityContext)
        assert ctx.project_gid is None, (
            "body-parameterized entity must produce EntityContext.project_gid=None "
            "(GATE 2 skipped); the route's A1 branch supplies the real GID"
        )
        assert ctx.entity_type == "project"


class TestT5BodyParamMissingBodyGidFailsFast:
    """T5 (risk-1 guard): missing body project_gid for a body-param entity → fail-fast 4xx, NOT 500."""

    def test_body_param_missing_body_gid_fails_fast(self, client) -> None:
        """POST /v1/query/project/rows with EMPTY body → 4xx fail-fast (no None into the engine)."""
        _assert_no_sprint2_fixture()

        # _get_dataframe is patched to BLOW UP if reached — the guard must short-circuit
        # before any engine call. If the guard is missing, this surfaces as a 500.
        engine_called = MagicMock(side_effect=AssertionError("engine reached with None GID"))

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
                side_effect=engine_called,
            ),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            response = client.post(
                "/v1/query/project/rows",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                json={},  # no project_gid in body
            )

        assert 400 <= response.status_code < 500, (
            f"risk-1 guard: missing body project_gid must fail-fast 4xx, "
            f"got {response.status_code}: {response.text}"
        )
        assert response.status_code != 500, "must NOT 500 (None into the engine)"
        # The guard raises InvalidParameterError → 400 INVALID_PARAMETER.
        assert response.status_code == 400, (
            f"expected 400 INVALID_PARAMETER from the risk-1 guard, got {response.status_code}"
        )


class TestT5bAggregateRejectsBodyParam:
    """risk-1 audit: aggregate endpoint (no body project_gid) rejects body-param entities."""

    def test_aggregate_rejects_body_parameterized_entity(self, client) -> None:
        """POST /v1/query/project/aggregate for unregistered project → 4xx, never None downstream."""
        _assert_no_sprint2_fixture()

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch(
                "autom8_asana.auth.bot_pat.get_bot_pat",
                return_value="test_bot_pat",
            ),
        ):
            response = client.post(
                "/v1/query/project/aggregate",
                headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                # Schema-valid body so the request passes Pydantic validation and
                # reaches the route's risk-1 guard (not a 422 from the body model).
                json={
                    "group_by": ["section"],
                    "aggregations": [{"column": "gid", "agg": "count"}],
                },
            )

        assert response.status_code == 400, (
            f"aggregate must reject body-parameterized entity with 400, "
            f"got {response.status_code}: {response.text}"
        )


def test_t3_unknown_entity_unaffected() -> None:
    """Sanity: a genuinely unknown entity still raises UnknownEntityError (GATE 1)."""
    entity_registry = MagicMock()
    project_registry = MagicMock()
    service = EntityService(entity_registry=entity_registry, project_registry=project_registry)
    service.get_queryable_entities = MagicMock(return_value={"project", "unit"})  # type: ignore[method-assign]

    with pytest.raises(UnknownEntityError):
        service.validate_entity_type("definitely_not_an_entity")
