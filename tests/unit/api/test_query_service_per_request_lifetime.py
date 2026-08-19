"""The per-request lifetime invariant the verification axis's 0s horizon rests on.

The axis is always-current because the manifest is read fresh from S3 inside
each request. That holds only while ``EntityQueryService`` — and therefore the
``SectionPersistence`` that owns ``_manifest_cache`` — is constructed per
request. That memo has NO TTL and NO read-path invalidation: its only eviction
sits inside ``delete_manifest_async``. Per request it is a harmless memo; hoisted
to a module singleton it becomes an unbounded staleness cache, and the design
silently degrades into the cache-carry option that was refused precisely because
its horizon is unbounded.

Nothing about that degradation is visible in a response. This test is the
tripwire: it goes RED the moment the construction leaves the handler.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.services.query_service import EntityQueryService
from autom8_asana.services.resolver import EntityProjectRegistry

_PROJECT_GID = "9990000000000011"
JWT_TOKEN = "header.payload.signature"


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    claims = MagicMock()
    claims.sub = f"service:{service_name}"
    claims.service_name = service_name
    claims.scope = "multi-tenant"
    return AsyncMock(return_value=claims)


def _project_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "gid": ["1111111111111111", "2222222222222222"],
            "name": ["Alpha", "Beta"],
            "section": ["ACTIVE", "PAUSED"],
            "vertical": ["dental", "medical"],
            "office_phone": ["+15551234567", "+15559876543"],
        }
    )


@pytest.fixture(autouse=True)
def register_project_gid():
    EntityProjectRegistry.get_instance().register(
        entity_type="project",
        project_gid=_PROJECT_GID,
        project_name="Lifetime Guard Projects",
    )
    yield


class TestEntityQueryServiceIsPerRequest:
    def test_two_requests_construct_two_services_each_with_an_empty_memo(self, client) -> None:
        constructed: list[EntityQueryService] = []
        memo_at_construction: list[object] = []

        def _record() -> EntityQueryService:
            service = EntityQueryService()
            constructed.append(service)
            # Captured at CONSTRUCTION, before the handler touches it: a
            # per-request service starts with no persistence and therefore no
            # inherited manifest memo.
            memo_at_construction.append(service._section_persistence)
            return service

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
                new_callable=AsyncMock,
                return_value=_project_df(),
            ),
            patch("autom8_asana.api.routes.query.EntityQueryService", side_effect=_record),
        ):
            mock_asana = MagicMock()
            mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
            mock_asana.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_asana

            for _ in range(2):
                response = client.post(
                    "/v1/query/project/rows",
                    headers={"Authorization": f"Bearer {JWT_TOKEN}"},
                    json={},
                )
                assert response.status_code == 200

        assert len(constructed) == 2, (
            "each /rows request must construct its own EntityQueryService; a hoisted "
            "singleton turns the per-request manifest memo into an unbounded cache"
        )
        assert constructed[0] is not constructed[1]
        assert memo_at_construction == [None, None], (
            "a service arriving with persistence already attached is carrying state across requests"
        )

    def test_a_fresh_service_has_no_manifest_memo(self) -> None:
        """The memo is empty at birth, and the accessor that creates it is lazy."""
        service = EntityQueryService()

        assert service._section_persistence is None
