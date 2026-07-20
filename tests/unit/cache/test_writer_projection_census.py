"""Writer-census tests for PHE projection metadata (TDD SS6.4, ADR fork c).

Every TASK-entry writer must either stamp the fetcher's projection
(``opt_fields_used`` metadata) or write an explicitly coverage-UNKNOWN entry
(fail-safe: miss-once-and-heal). The two-sided warmer-honesty arm proves the
warm write SERVES with the ITEM-C threading and coverage-misses without it --
without the fix the warmer is neutered to prefetch-without-serve (pure cost).

Census scope (per HANDOFF ITEM-C + CH-02): autom8_adapter.py's TWO bare
CacheEntry(TASK) sites, loader.load_task_entry AND the batch writer
load_batch_entries, plus a source-level grep-assertion that no TASK-writer
CacheEntry construction lacks a metadata= stamp.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

import autom8_asana.cache.integration.autom8_adapter as autom8_adapter_module
import autom8_asana.cache.integration.loader as loader_module
from autom8_asana.cache.integration.autom8_adapter import (
    migrate_task_collection_loading,
    warm_project_tasks,
)
from autom8_asana.cache.integration.loader import load_batch_entries, load_task_entry
from autom8_asana.cache.models.entry import EntryType
from autom8_asana.clients.tasks import TasksClient
from tests.unit.clients.conftest import MockCacheProvider
from tests.unit.clients.test_taskcache_projection_coverage import EchoOptFieldsTransport

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig

TASK_GID = "1234567890123"

# A warm projection that covers its own read-back: includes the tasks-client
# _MINIMUM_OPT_FIELDS so resolved reads at the fetcher's projection are subsets.
WARM_OPT_FIELDS = [
    "gid",
    "name",
    "modified_at",
    "parent.gid",
    "memberships.project.gid",
    "memberships.project.name",
]


def _warm_task(gid: str = TASK_GID) -> dict[str, Any]:
    return {
        "gid": gid,
        "resource_type": "task",
        "name": "Warmed Task",
        "modified_at": "2026-07-08T12:00:00.000Z",
        "parent": None,
        "memberships": [{"project": {"gid": "9990001112223", "name": "Units"}}],
    }


@pytest.fixture
def cache_provider() -> MockCacheProvider:
    return MockCacheProvider()


@pytest.fixture
def tasks_client(
    config: AsanaConfig,
    auth_provider: Any,
    cache_provider: MockCacheProvider,
) -> tuple[TasksClient, EchoOptFieldsTransport]:
    transport = EchoOptFieldsTransport()
    client = TasksClient(
        http=transport,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
        client=None,
    )
    return client, transport


class TestWarmerHonesty:
    """Two-sided warmer honesty: serve WITH the projection stamp, miss without."""

    async def test_warm_with_opt_fields_first_read_hits_zero_http(
        self,
        cache_provider: MockCacheProvider,
        tasks_client: tuple[TasksClient, EchoOptFieldsTransport],
    ) -> None:
        """A warm write threaded with the fetcher's projection SERVES: the first
        get_async read at (a subset of) that projection HITs with zero fetches."""
        client, transport = tasks_client

        async def fetcher(project_gid: str) -> list[dict[str, Any]]:
            return [_warm_task()]

        warmed = await warm_project_tasks(
            cache=cache_provider,  # type: ignore[arg-type]
            project_gid="9990001112223",
            task_fetcher=fetcher,
            opt_fields=list(WARM_OPT_FIELDS),
        )
        assert warmed == 1

        served = await client.get_async(TASK_GID, raw=True, opt_fields=["gid", "name"])

        assert transport.calls == [], (
            "warm-written entry with projection metadata must serve the covered "
            "read with ZERO HTTP calls (warmer honesty)"
        )
        assert served["name"] == "Warmed Task"

    async def test_warm_without_opt_fields_is_unknown_and_misses_once(
        self,
        cache_provider: MockCacheProvider,
        tasks_client: tuple[TasksClient, EchoOptFieldsTransport],
    ) -> None:
        """The bare warm write (no projection threading) is coverage-UNKNOWN:
        the first projected read coverage-misses and re-fetches -- the
        prefetch-without-serve degradation ITEM-C exists to prevent."""
        client, transport = tasks_client

        async def fetcher(project_gid: str) -> list[dict[str, Any]]:
            return [_warm_task()]

        await warm_project_tasks(
            cache=cache_provider,  # type: ignore[arg-type]
            project_gid="9990001112223",
            task_fetcher=fetcher,
        )

        await client.get_async(TASK_GID, raw=True, opt_fields=["gid", "name"])
        assert len(transport.calls) == 1, (
            "UNKNOWN warm entry must coverage-miss once (fail-safe heal)"
        )
        # ...and the re-fetched entry is projection-honest thereafter.
        await client.get_async(TASK_GID, raw=True, opt_fields=["gid", "name"])
        assert len(transport.calls) == 1


class TestAdapterMigrationStamp:
    """migrate_task_collection_loading stamps the fetcher's projection."""

    async def test_stale_fetch_writes_projection_metadata(
        self,
        cache_provider: MockCacheProvider,
    ) -> None:
        async def batch_api(gids: list[str]) -> dict[str, str]:
            return {gid: "2026-07-08T12:00:00.000Z" for gid in gids}

        async def task_fetcher(gids: list[str]) -> list[dict[str, Any]]:
            return [_warm_task(gid) for gid in gids]

        await migrate_task_collection_loading(
            task_dicts=[{"gid": TASK_GID}],
            cache=cache_provider,  # type: ignore[arg-type]
            batch_api=batch_api,
            task_fetcher=task_fetcher,
            opt_fields=list(WARM_OPT_FIELDS),
        )

        entry = cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"]
        assert entry.metadata["opt_fields_used"] == sorted(set(WARM_OPT_FIELDS))

    async def test_stale_fetch_without_opt_fields_writes_unknown(
        self,
        cache_provider: MockCacheProvider,
    ) -> None:
        async def batch_api(gids: list[str]) -> dict[str, str]:
            return {gid: "2026-07-08T12:00:00.000Z" for gid in gids}

        async def task_fetcher(gids: list[str]) -> list[dict[str, Any]]:
            return [_warm_task(gid) for gid in gids]

        await migrate_task_collection_loading(
            task_dicts=[{"gid": TASK_GID}],
            cache=cache_provider,  # type: ignore[arg-type]
            batch_api=batch_api,
            task_fetcher=task_fetcher,
        )

        entry = cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"]
        assert "opt_fields_used" not in entry.metadata


class TestLoaderProjectionThreading:
    """loader.load_task_entry AND load_batch_entries (CH-02) thread opt_fields."""

    async def test_load_task_entry_with_opt_fields_stamps_metadata(
        self,
        cache_provider: MockCacheProvider,
    ) -> None:
        async def fetcher(gid: str) -> dict[str, Any]:
            return _warm_task(gid)

        entry, hit = await load_task_entry(
            TASK_GID,
            EntryType.TASK,
            cache_provider,
            fetcher,
            opt_fields=list(WARM_OPT_FIELDS),
        )

        assert not hit
        assert entry is not None
        assert entry.metadata["opt_fields_used"] == sorted(set(WARM_OPT_FIELDS))

    async def test_load_task_entry_without_opt_fields_is_unknown(
        self,
        cache_provider: MockCacheProvider,
    ) -> None:
        async def fetcher(gid: str) -> dict[str, Any]:
            return _warm_task(gid)

        entry, _ = await load_task_entry(TASK_GID, EntryType.TASK, cache_provider, fetcher)

        assert entry is not None
        assert "opt_fields_used" not in entry.metadata

    async def test_load_batch_entries_with_opt_fields_stamps_metadata(
        self,
        cache_provider: MockCacheProvider,
    ) -> None:
        """CH-02: the batch writer site (loader.py CacheEntry construct) is
        threaded identically to the single-task writer."""

        async def batch_fetcher(gids: list[str]) -> dict[str, dict[str, Any]]:
            return {gid: _warm_task(gid) for gid in gids}

        results = await load_batch_entries(
            [TASK_GID],
            EntryType.TASK,
            cache_provider,
            batch_fetcher,
            opt_fields=list(WARM_OPT_FIELDS),
        )

        entry, hit = results[TASK_GID]
        assert not hit
        assert entry is not None
        assert entry.metadata["opt_fields_used"] == sorted(set(WARM_OPT_FIELDS))


class TestWriterCensusGrep:
    """Source-level census: no TASK-writer CacheEntry construction without a
    metadata stamp in the two writer modules (HANDOFF ITEM-C TL-C + CH-02)."""

    @pytest.mark.parametrize(
        "module",
        [autom8_adapter_module, loader_module],
        ids=["autom8_adapter", "loader"],
    )
    def test_every_cache_entry_construct_carries_metadata(self, module: Any) -> None:
        source = Path(module.__file__).read_text()
        # Find every CacheEntry( construction and require a metadata= kwarg
        # within its argument span (naive brace-window: next 12 lines).
        lines = source.splitlines()
        construct_lines = [
            i for i, line in enumerate(lines) if re.search(r"= CacheEntry\($", line.strip())
        ]
        assert construct_lines, "census expects CacheEntry constructions in writer modules"
        for i in construct_lines:
            window = "\n".join(lines[i : i + 12])
            assert "metadata=" in window, (
                f"{module.__name__} line {i + 1}: CacheEntry construction without "
                "a projection metadata stamp (PHE writer census violation)"
            )
