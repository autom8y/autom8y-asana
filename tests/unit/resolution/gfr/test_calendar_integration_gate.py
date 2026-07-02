"""FAULT-7 two-sided gate tests — Calendar-Integrations entry classification.

Per ADR-fault7-gfr-anchor-onboarding-walkthrough-2026-07-02 (+ AMENDMENTS A1-A5)
and ADVERSARY-REPORT-fault7-gfr-anchor-2026-07-02 condition C2.

Gate-1 (RED-1/GREEN-1, one two-sided test): a task whose SOLE membership is the
Calendar Integrations project (``1209442849265632``) must classify via the REAL
detection path (Tier-1 project membership -> ``ProjectTypeRegistry.lookup`` ->
``EntityRegistry.get_by_gid``). The QA-fixture shortcut (injecting ``entry_type``
into a mocked ``HydrationResult``) is deliberately NOT used here — pre-fix, that
shortcut would mask the defect this suite exists to catch. Pre-fix the entry gate
refuses with ``UnresolvedError(reason="entity-type-undetectable")`` (the RED side,
proven by running this file against stashed pre-fix src); post-fix the gate passes
and the anchor carries ``EntityType.CALENDAR_INTEGRATION`` (the GREEN side).

Gate-2 (C2 / RED-2b): with the DataFrameCache CONSTRUCTED (S3 tier active — the
AMENDMENT A1 corrected premise; ``S3Settings.bucket`` defaults to ``autom8-s3``)
and the S3 storage layer raising ``ClientError(AccessDenied)`` (the Lambda
execution role's actual cold-cause), the read must degrade to a tier miss
(``errors.py`` S3_TRANSPORT_ERRORS -> ``tiers/progressive.py`` miss) ->
``CacheNotWarmError`` (``services/query_service.py`` raise) — with the PT-03
invariant intact: ZERO Asana-API calls after the entry phase (INVARIANT I3).

Blast radius (G-PROPAGATE): the new descriptor must not alter any OTHER project
gid's classification — the Business tier-1 project still resolves BUSINESS, an
unregistered gid still resolves to None/UNKNOWN, and the calendar gid is the ONLY
gid mapping to the new type.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# Pre-existing single-source gid constant (origin/main): importable on BOTH sides
# of the two-sided run (the core-layer constant lands WITH the fix, so the test
# reuses the workflow-local named constant instead — never a raw literal here).
from autom8_asana.automation.workflows.onboarding_walkthrough.constants import (
    CALENDAR_INTEGRATIONS_PROJECT_GID,
)
from autom8_asana.core.types import EntityType
from autom8_asana.models.business.registry import (
    ProjectTypeRegistry,
    WorkspaceProjectRegistry,
)
from autom8_asana.models.business.registry import get_registry as get_ptr
from autom8_asana.models.common import NameGid
from autom8_asana.models.task import Task
from autom8_asana.resolution.gfr.entry import _fetch_and_anchor_async
from autom8_asana.resolution.gfr.errors import UnresolvedError
from tests.unit.resolution.gfr.conftest import BUSINESS_PROJECT_GID

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]

_CAL_TASK_GID = "CAL_PLAY_TASK"
_BUSINESS_ROOT_GID = "B_ROOT"
_FACTORY_PROVIDER = "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider"


@pytest.fixture(autouse=True)
def _fresh_registries() -> Any:
    """Isolate the process-global detection registries around each test.

    The RED side of the two-sided run triggers lazy workspace discovery (the
    calendar gid is unregistered pre-fix); reset both singletons before AND
    after so no discovery/bootstrap state leaks across tests or suites.
    """
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()
    yield
    ProjectTypeRegistry.reset()
    WorkspaceProjectRegistry.reset()


def _make_task_map() -> dict[str, Task]:
    """The FAULT-7 topology: a play task whose SOLE membership is the Calendar
    Integrations project, parent-chained directly to a Business root (path_len 1
    in walkthrough terms; the traversal path EXCLUDES the Business itself)."""
    calendar_task = Task(
        gid=_CAL_TASK_GID,
        name="GHL Pilot Setup",  # deliberately matches NO Tier-2 name pattern
        memberships=[
            {
                "project": {
                    "gid": CALENDAR_INTEGRATIONS_PROJECT_GID,
                    "name": "Calendar Integrations",
                }
            }
        ],
        parent=NameGid(gid=_BUSINESS_ROOT_GID, name="Neu Life"),
    )
    business_task = Task(
        gid=_BUSINESS_ROOT_GID,
        name="Neu Life",
        memberships=[{"project": {"gid": BUSINESS_PROJECT_GID, "name": "Businesses"}}],
        parent=None,
    )
    return {_CAL_TASK_GID: calendar_task, _BUSINESS_ROOT_GID: business_task}


def _make_real_path_client(task_map: dict[str, Task]) -> MagicMock:
    """AsanaClient mock serving REAL Task models to the REAL detection path.

    No entry_type injection anywhere: hydration, Tier 1-4 detection, and the
    upward traversal all run for real against these payloads. Discovery
    (pre-fix path) and Tier-4 structure inspection are answered honestly-empty
    so the pre-fix classification lands on UNKNOWN via the real tiers.
    """
    client = MagicMock()
    # Tier-4 cache seam reads this attr; MagicMock's auto-attr would be truthy.
    client._cache_provider = None
    client.default_workspace_gid = "WS_TEST"
    client.tasks.get_async = AsyncMock(side_effect=lambda gid, **_kw: task_map[gid])
    # Lazy workspace discovery (fires ONLY pre-fix, on the unregistered gid).
    _lister = MagicMock()
    _lister.collect = AsyncMock(return_value=[])
    client.projects.list_async = MagicMock(return_value=_lister)
    # Tier-4 structure inspection: no subtasks -> no structural match.
    _subtasks = MagicMock()
    _subtasks.collect = AsyncMock(return_value=[])
    client.tasks.subtasks_async = MagicMock(return_value=_subtasks)
    return client


class TestGate1RealDetectionPath:
    """RED-1/GREEN-1 — one two-sided test, flipped by the fix itself.

    Pre-fix (stashed src): Tier-1 lookup misses, discovery finds nothing, Tiers
    2-4 find nothing -> UNKNOWN -> the entry gate raises
    ``UnresolvedError(reason="entity-type-undetectable")`` and THIS TEST FAILS —
    that failure is the pasted RED receipt. Post-fix: Tier-1 classifies
    CALENDAR_INTEGRATION and the gate passes.
    """

    @pytest.mark.asyncio
    async def test_calendar_sole_membership_classifies_and_passes_entry_gate(self) -> None:
        client = _make_real_path_client(_make_task_map())

        anchor = await _fetch_and_anchor_async(_CAL_TASK_GID, client)

        assert anchor.entity_type is EntityType.CALENDAR_INTEGRATION
        assert anchor.business_gid == _BUSINESS_ROOT_GID
        # Traversal path excludes the Business root: direct child => 0 entries.
        assert anchor.path_len == 0
        # Tier-1 static hit: NO workspace discovery, NO structure inspection —
        # the classification came from the registry, not an API fallback.
        client.projects.list_async.assert_not_called()
        client.tasks.subtasks_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_pre_fix_refusal_shape_is_the_entry_gate(self) -> None:
        """The refusal the RED side exhibits is the entry gate's, not incidental.

        Force the real detection path to UNKNOWN (unregistered project gid — the
        pre-fix condition for the calendar gid, permanently true for this synthetic
        gid) and assert the gate refuses with the exact closed-vocabulary reason
        the walkthrough logged in production. This pins the refusal SHAPE on both
        sides of the fix without injecting entry_type.
        """
        task_map = _make_task_map()
        unknown_task = Task(
            gid="UNREGISTERED_TASK",
            name="GHL Pilot Setup",
            memberships=[{"project": {"gid": "999999999999999", "name": "Nowhere"}}],
            parent=NameGid(gid=_BUSINESS_ROOT_GID, name="Neu Life"),
        )
        task_map["UNREGISTERED_TASK"] = unknown_task
        client = _make_real_path_client(task_map)

        with pytest.raises(UnresolvedError) as exc:
            await _fetch_and_anchor_async("UNREGISTERED_TASK", client)
        assert exc.value.reason == "entity-type-undetectable"


class TestGate2S3AccessDeniedDegradation:
    """C2 / RED-2b — the adversary's condition (corrected cold-cause chain).

    DataFrameCache IS constructed (S3 tier active per AMENDMENT A1); the S3
    storage layer raises ``ClientError(AccessDenied)`` — the walkthrough Lambda
    execution role's ACTUAL production cold-cause. Asserted chain:
    AccessDenied -> S3_TRANSPORT_ERRORS catch -> ProgressiveTier miss (tier
    ``read_errors`` receipt) -> ``CacheNotWarmError`` raised by
    ``EntityQueryService.get_dataframe`` — and PT-03: post-entry Asana
    call-count delta == 0 (INVARIANT I3: the degradation NEVER falls back to
    the Asana API).

    NOTE (contract-vs-reality, reported in the PR body): the pre-amendment ADR
    narrative appended "-> UnresolvedError" to this chain. No such conversion
    exists in code: ``CacheNotWarmError`` (a ``ServiceError``) propagates out of
    ``gfr.resolve_async`` unwrapped — it is NOT a ``GfrError``. AMENDMENT A1's
    corrected chain ends at ``CacheNotWarmError`` (query_service raise), which
    is what this test encodes. Fail-closed is preserved either way: no frame,
    no identity read, no attach.
    """

    @pytest.mark.asyncio
    async def test_access_denied_degrades_to_tier_miss_cachenotwarm_pt03(self) -> None:
        import polars as pl  # noqa: F401 — ensures the frames substrate is importable

        from autom8_asana.cache.dataframe.circuit_breaker import CircuitBreaker
        from autom8_asana.cache.dataframe.coalescer import DataFrameCacheCoalescer
        from autom8_asana.cache.dataframe.tiers.memory import MemoryTier
        from autom8_asana.cache.dataframe.tiers.progressive import ProgressiveTier
        from autom8_asana.cache.integration.dataframe_cache import DataFrameCache
        from autom8_asana.query.engine import QueryEngine
        from autom8_asana.resolution.gfr.engine import resolve_async
        from autom8_asana.services.errors import CacheNotWarmError
        from autom8_asana.services.query_service import EntityQueryService

        # --- The S3 storage layer: every read is AccessDenied (the IAM gap). ---
        access_denied = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            operation_name="GetObject",
        )
        storage = MagicMock()
        storage.load_dataframe_with_metadata = AsyncMock(side_effect=access_denied)
        storage.load_dataframe = AsyncMock(side_effect=access_denied)
        persistence = MagicMock()
        persistence.storage = storage

        progressive_tier = ProgressiveTier(persistence=persistence)
        cache = DataFrameCache(
            memory_tier=MemoryTier(),
            progressive_tier=progressive_tier,
            coalescer=DataFrameCacheCoalescer(),
            circuit_breaker=CircuitBreaker(),
        )

        # --- PT-03 baseline: the entry phase's own bounded read budget. ---
        entry_client = _make_real_path_client(_make_task_map())
        await _fetch_and_anchor_async(_CAL_TASK_GID, entry_client)
        entry_budget = entry_client.tasks.get_async.await_count

        # --- Full resolve against the REAL substrate (EntityQueryService). ---
        client = _make_real_path_client(_make_task_map())
        engine = QueryEngine(provider=EntityQueryService())
        with patch(_FACTORY_PROVIDER, return_value=cache):
            with pytest.raises(CacheNotWarmError):
                await resolve_async(
                    _CAL_TASK_GID,
                    ["company_id"],
                    client=client,
                    query_engine=engine,
                )

        # The S3 read WAS attempted and degraded to a tier miss (never a crash).
        storage.load_dataframe_with_metadata.assert_awaited()
        assert progressive_tier._stats["read_errors"] == 1
        assert progressive_tier._stats["reads"] == 1

        # PT-03 (INVARIANT I3): zero Asana-API calls after the entry phase —
        # the identity-read degradation never touches the Asana API.
        assert client.tasks.get_async.await_count == entry_budget
        client.projects.list_async.assert_not_called()
        client.tasks.subtasks_async.assert_not_called()


class TestBlastRadius:
    """G-PROPAGATE — the descriptor entry alters NO other gid's classification."""

    def test_business_tier1_project_still_business(self) -> None:
        assert get_ptr().lookup(BUSINESS_PROJECT_GID) is EntityType.BUSINESS

    def test_unregistered_gid_still_unresolved_then_unknown(self) -> None:
        # Registry level: still no mapping.
        assert get_ptr().lookup("999999999999999") is None
        # Detection level: the sync path still lands on UNKNOWN (Tier 5).
        from autom8_asana.models.business.detection.facade import detect_entity_type

        task = Task(
            gid="T_UNREG",
            name="GHL Pilot Setup",
            memberships=[{"project": {"gid": "999999999999999", "name": "Nowhere"}}],
        )
        result = detect_entity_type(task)
        assert result.entity_type is EntityType.UNKNOWN

    def test_calendar_gid_is_the_only_mapping_to_the_new_type(self) -> None:
        from autom8_asana.core.entity_registry import get_registry

        matching = [
            d.primary_project_gid
            for d in get_registry().all_descriptors()
            if d.entity_type is EntityType.CALENDAR_INTEGRATION
        ]
        assert matching == [CALENDAR_INTEGRATIONS_PROJECT_GID]

    def test_every_preexisting_static_gid_mapping_unchanged(self) -> None:
        """Pin the full pre-fix static gid->type mapping (frozen expected set).

        Derived from origin/main's ENTITY_DESCRIPTORS + _bind_entity_types():
        every gid-bearing, type-bound descriptor that existed BEFORE this fix
        must still resolve to exactly its pre-fix type via the canonical front
        door (ProjectTypeRegistry.lookup -> EntityRegistry.get_by_gid).
        """
        preexisting = {
            "1200653012566782": EntityType.BUSINESS,
            "1201081073731555": EntityType.UNIT,
            "1200775689604552": EntityType.CONTACT,
            "1143843662099250": EntityType.OFFER,
            "1202204184560785": EntityType.ASSET_EDIT,
            "1200836133305610": EntityType.LOCATION,
            "1201614578074026": EntityType.HOURS,
            "1201500116978260": EntityType.CONTACT_HOLDER,
            "1204433992667196": EntityType.UNIT_HOLDER,
            "1167650840134033": EntityType.DNA_HOLDER,
            "1203404998225231": EntityType.RECONCILIATIONS_HOLDER,
            "1203992664400125": EntityType.ASSET_EDIT_HOLDER,
            "1207984018149338": EntityType.VIDEOGRAPHY_HOLDER,
            "1210679066066870": EntityType.OFFER_HOLDER,
        }
        ptr = get_ptr()
        for gid, expected_type in preexisting.items():
            assert ptr.lookup(gid) is expected_type, (
                f"classification drifted for {gid}: expected {expected_type}"
            )
