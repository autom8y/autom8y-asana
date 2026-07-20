"""Caller-constant projection registry coherence (TDD SS6.3).

Parametrized over EVERY registered in-repo ``get_async`` caller projection
constant, asserting each is SERVED COVERED after first hydration: a write at
that projection is HIT by a read at that projection with zero extra fetches,
and any cross-pair read sequence converges in at most ONE widening fetch
(the union-monotone property).

RULE (enforced by this registry): new ``tasks.get_async`` caller projections
MUST be module constants and MUST be registered in ``REGISTERED_PROJECTIONS``
below -- projection growth stays visible and deliberate, and every new
projection inherits the coverage guarantee test-first. An inline literal
projection is invisible to this registry and to the starvation analysis that
produced DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any

import pytest
from tests.unit.clients.conftest import MockCacheProvider
from tests.unit.clients.test_taskcache_projection_coverage import EchoOptFieldsTransport

from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import (
    _PREFLIGHT_OPT_FIELDS,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.office_resolution import (
    _WALK_OPT_FIELDS,
)
from autom8_asana.cache.integration.hierarchy_warmer import _HIERARCHY_OPT_FIELDS
from autom8_asana.clients.tasks import _MINIMUM_OPT_FIELDS, TasksClient
from autom8_asana.dataframes.builders.fields import BASE_OPT_FIELDS
from autom8_asana.models.business.fields import (
    DETECTION_OPT_FIELDS,
    STANDARD_TASK_OPT_FIELDS,
)
from autom8_asana.services.field_write_service import _TASK_OPT_FIELDS

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig

TASK_GID = "1234567890123"

# The registry: every in-repo caller projection constant (TDD SS6.3).
REGISTERED_PROJECTIONS: dict[str, list[str]] = {
    "STANDARD_TASK_OPT_FIELDS": list(STANDARD_TASK_OPT_FIELDS),
    "DETECTION_OPT_FIELDS": list(DETECTION_OPT_FIELDS),
    "_MINIMUM_OPT_FIELDS": sorted(_MINIMUM_OPT_FIELDS),
    "BASE_OPT_FIELDS": list(BASE_OPT_FIELDS),
    "_HIERARCHY_OPT_FIELDS": list(_HIERARCHY_OPT_FIELDS),
    "field_write_service._TASK_OPT_FIELDS": list(_TASK_OPT_FIELDS),
    "office_resolution._WALK_OPT_FIELDS": list(_WALK_OPT_FIELDS),
    "link_on_play._PREFLIGHT_OPT_FIELDS": list(_PREFLIGHT_OPT_FIELDS),
}


def _fresh_client(
    config: AsanaConfig, auth_provider: Any
) -> tuple[TasksClient, EchoOptFieldsTransport]:
    transport = EchoOptFieldsTransport()
    client = TasksClient(
        http=transport,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=MockCacheProvider(),
        client=None,
    )
    return client, transport


class TestRegisteredProjectionsServedCovered:
    @pytest.mark.parametrize(
        "name",
        sorted(REGISTERED_PROJECTIONS),
    )
    async def test_projection_hits_after_first_hydration(
        self,
        name: str,
        config: AsanaConfig,
        auth_provider: Any,
    ) -> None:
        """Write at projection P => read at projection P HITs, zero extra HTTP."""
        projection = REGISTERED_PROJECTIONS[name]
        client, transport = _fresh_client(config, auth_provider)

        await client.get_async(TASK_GID, raw=True, opt_fields=list(projection))
        assert len(transport.calls) == 1

        await client.get_async(TASK_GID, raw=True, opt_fields=list(projection))
        assert len(transport.calls) == 1, (
            f"{name}: read at its own projection must be served covered "
            "(zero extra fetches after first hydration)"
        )

    async def test_cross_pair_reads_converge_in_at_most_one_widening(
        self,
        config: AsanaConfig,
        auth_provider: Any,
    ) -> None:
        """For every ordered pair (P, Q): read P, read Q, read Q again =>
        at most 2 fetches total (initial + <=1 widening), and the third read
        is always a covered HIT."""
        for (name_p, proj_p), (name_q, proj_q) in itertools.permutations(
            REGISTERED_PROJECTIONS.items(), 2
        ):
            client, transport = _fresh_client(config, auth_provider)

            await client.get_async(TASK_GID, raw=True, opt_fields=list(proj_p))
            await client.get_async(TASK_GID, raw=True, opt_fields=list(proj_q))
            calls_after_pair = len(transport.calls)
            assert calls_after_pair <= 2, (
                f"({name_p} -> {name_q}): cross-pair must converge in <=1 widening"
            )

            await client.get_async(TASK_GID, raw=True, opt_fields=list(proj_q))
            assert len(transport.calls) == calls_after_pair, (
                f"({name_p} -> {name_q}): repeat read must be a covered HIT"
            )
