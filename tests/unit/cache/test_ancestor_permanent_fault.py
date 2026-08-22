"""Permanent per-GID fault tolerance in the ANCESTOR warm (DIC-S04c).

``UnifiedTaskStore._fetch_immediate_parents`` is the second hop of the contact
cascade: gap-warmed ContactHolders are handed to ``put_batch_async`` so their
own ``parent`` edge (the Business that owns ``Office Phone``) gets discovered
and cached. It runs a bare ``asyncio.gather`` with no ``return_exceptions``,
and its only ``except`` clause is ``CACHE_TRANSIENT_ERRORS`` -- boto/redis/OS
only. An Asana ``NotFoundError`` is in neither, so ONE deleted grandparent
propagated out of the gather, out of ``put_batch_async``, past
``HierarchyWarmer._bank_gap_chunk`` (which tolerated only ``RateLimitError``)
and into the gap-warm outer BROAD-CATCH -> ``return 0``.

This is the DIC-S04b wound one level up the chain. S04b hardened the gap GET
(contact -> holder). The ancestor GET (holder -> business) was never hardened,
so the sweep kept dying -- and, because S04b banks the cached-but-unlinked
parents through ``_bank_gap_chunk`` FIRST, it now died BEFORE the first gap GET.

LIVE RECEIPT (cache-warmer, contact frame ``1200775689604552``, 2026-08-20,
running the S04b image ``55e69d78``)::

    hierarchy_gap_fetch_starting  total_parent_gids=2679  uncached_count=795
                                  cached_unlinked_count=1882
    hierarchy_gap_warming_failed  parent_gids_count=795
                                  error="task: Not a recognized ID:
                                         1215624688510678 (HTTP 404)"
                                  error_type="NotFoundError"
    hierarchy_gaps_warmed         reconstructed=23484  gaps_warmed=0
    cascade_key_null_audit        office_phone null_rate=0.897547  severity=error

3.1s separated ``hierarchy_gap_fetch_starting`` from
``hierarchy_gap_warming_failed``, with NO ``hierarchy_gap_parent_unresolvable``
and NO ``hierarchy_gap_chunk_aborted`` in between -- the fault fired inside the
first ``_bank_gap_chunk``, i.e. at ancestor depth, exactly as reproduced here.

Both sides are pinned: the cure must cache every RESOLVABLE ancestor while
skipping the unresolvable one, and must NOT swallow the transient class that
retry exists to serve.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import BotoCoreError

from autom8_asana.cache.models.freshness_unified import FreshnessIntent
from autom8_asana.cache.providers.unified import UnifiedTaskStore
from autom8_asana.errors import ForbiddenError, GoneError, NotFoundError
from tests._shared.factories import make_task_dict as _make_task

if TYPE_CHECKING:
    from autom8_asana.cache.models.entry import EntryType

# The live GID whose deletion zeroed the contact hierarchy warm on the S04b image.
_DELETED_ANCESTOR_GID = "1215624688510678"


def _parent_response(gid: str) -> MagicMock:
    mock = MagicMock()
    mock.model_dump.return_value = {
        "gid": gid,
        "name": f"Parent {gid}",
        "parent": None,
        "custom_fields": [],
    }
    return mock


@pytest.fixture
def cache_provider() -> MagicMock:
    """A CacheProvider that actually remembers what was stored."""
    provider = MagicMock()
    stored: dict[str, object] = {}

    def _get_versioned(gid: str, entry_type: EntryType) -> object | None:
        return stored.get(gid)

    def _set_versioned(gid: str, entry: object, **kwargs: object) -> None:
        stored[gid] = entry

    def _set_batch(entries: dict, **kwargs: object) -> None:
        stored.update(entries)

    provider.get_versioned = MagicMock(side_effect=_get_versioned)
    provider.set_versioned = MagicMock(side_effect=_set_versioned)
    provider.get_batch = MagicMock(return_value={})
    provider.set_batch = MagicMock(side_effect=_set_batch)
    provider.invalidate = MagicMock()
    provider._stored = stored  # noqa: SLF001 -- test introspection handle
    return provider


@pytest.fixture
def store(cache_provider: MagicMock) -> UnifiedTaskStore:
    return UnifiedTaskStore(
        cache=cache_provider,
        batch_client=MagicMock(),
        freshness_mode=FreshnessIntent.EVENTUAL,
    )


def _attempted(client: MagicMock) -> set[str]:
    """The distinct GIDs handed to ``tasks_client.get_async``."""
    return {call.args[0] for call in client.get_async.await_args_list}


def _tasks_client(deleted: set[str], exc: type[Exception] = NotFoundError) -> MagicMock:
    client = MagicMock()

    async def _get_async(gid: str, **_kwargs: object) -> MagicMock:
        if gid in deleted:
            raise exc(f"task: Not a recognized ID: {gid} (HTTP 404)")
        return _parent_response(gid)

    client.get_async = AsyncMock(side_effect=_get_async)
    return client


# ---------------------------------------------------------------------------
# RED against 55e69d78 -- one deleted ancestor must not zero the ancestor warm
# ---------------------------------------------------------------------------


async def test_one_deleted_ancestor_does_not_abort_the_ancestor_warm(
    store: UnifiedTaskStore,
    cache_provider: MagicMock,
) -> None:
    """The live shape: 1 deleted Business among many healthy ones.

    Pre-cure ``put_batch_async`` RAISES ``NotFoundError`` here, which is what
    unwound the whole gap sweep to ``gaps_warmed=0`` on every cycle.
    """
    holders = [_make_task(f"holder-{i}", parent_gid=f"biz-{i}") for i in range(10)]
    holders.append(_make_task("holder-dead", parent_gid=_DELETED_ANCESTOR_GID))
    client = _tasks_client({_DELETED_ANCESTOR_GID})

    await store.put_batch_async(holders, warm_hierarchy=True, tasks_client=client)

    # Every resolvable Business was fetched and cached; the deleted one was not
    # invented as a stub -- absence is reported, never papered over.
    cached = cache_provider._stored  # noqa: SLF001
    assert all(f"biz-{i}" in cached for i in range(10))
    assert _DELETED_ANCESTOR_GID not in cached
    # All 11 ancestors were ATTEMPTED -- the sweep was never short-circuited.
    # (Asserted as a SET: put_batch_async has two ancestor phases, so the
    # unresolvable GID is legitimately re-attempted once by the phase-2 walk.)
    assert _attempted(client) == {f"biz-{i}" for i in range(10)} | {_DELETED_ANCESTOR_GID}


async def test_deleted_ancestor_is_reported_not_silently_dropped(
    store: UnifiedTaskStore,
) -> None:
    """A permanently unresolvable ancestor emits a discriminating event.

    Tolerating the fault must not make it invisible: an operator reading the
    logs has to be able to tell "this ancestor is gone forever" apart from
    "this ancestor is temporarily unreachable".
    """
    holders = [_make_task("holder-1", parent_gid=_DELETED_ANCESTOR_GID)]
    client = _tasks_client({_DELETED_ANCESTOR_GID})

    with patch("autom8_asana.cache.providers.unified.logger") as mock_logger:
        await store.put_batch_async(holders, warm_hierarchy=True, tasks_client=client)

    events = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert "warm_immediate_parent_unresolvable" in events
    # NOT re-labelled as the transient exhaustion event -- different diagnosis.
    assert "warm_immediate_parent_failed_final" not in events


@pytest.mark.parametrize("exc", [NotFoundError, GoneError, ForbiddenError])
async def test_410_and_403_are_the_same_permanent_class(
    store: UnifiedTaskStore,
    cache_provider: MagicMock,
    exc: type[Exception],
) -> None:
    """404 / 410 / 403 are all per-GID and permanent: retrying buys nothing."""
    holders = [
        _make_task("holder-a", parent_gid="biz-a"),
        _make_task("holder-b", parent_gid="biz-gone"),
    ]
    client = _tasks_client({"biz-gone"}, exc=exc)

    await store.put_batch_async(holders, warm_hierarchy=True, tasks_client=client)

    cached = cache_provider._stored  # noqa: SLF001
    assert "biz-a" in cached
    assert "biz-gone" not in cached
    # Permanent means it never enters the 3-attempt transient retry ladder.
    assert _attempted(client) == {"biz-a", "biz-gone"}


async def test_permanent_fault_does_not_consume_the_transient_retry_budget(
    store: UnifiedTaskStore,
) -> None:
    """A 404 must not sleep-and-retry: it never heals, so retrying is pure latency."""
    holders = [_make_task("holder-1", parent_gid=_DELETED_ANCESTOR_GID)]
    client = _tasks_client({_DELETED_ANCESTOR_GID})

    with patch(
        "autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        await store.put_batch_async(holders, warm_hierarchy=True, tasks_client=client)

    mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Negative controls -- MUST pass on BOTH sides of the cure
# ---------------------------------------------------------------------------


async def test_healthy_ancestor_warm_still_caches_every_business(
    store: UnifiedTaskStore,
    cache_provider: MagicMock,
) -> None:
    """No-defect control: with no faults, nothing about the warm changes."""
    holders = [_make_task(f"holder-{i}", parent_gid=f"biz-{i}") for i in range(5)]
    client = _tasks_client(set())

    await store.put_batch_async(holders, warm_hierarchy=True, tasks_client=client)

    cached = cache_provider._stored  # noqa: SLF001
    assert _attempted(client) == {f"biz-{i}" for i in range(5)}


async def test_transient_error_still_retries_then_gives_up(
    store: UnifiedTaskStore,
) -> None:
    """The transient class keeps its 3-attempt ladder -- the cure must not widen.

    Over-tolerance is its own defect: a boto/network blip is exactly the case
    retry exists for, and collapsing it into the permanent branch would turn a
    recoverable gap into a permanent one.
    """
    holders = [_make_task("holder-1", parent_gid="biz-flaky")]
    client = MagicMock()

    async def _get_async(gid: str, **_kwargs: object) -> MagicMock:
        raise BotoCoreError()

    client.get_async = AsyncMock(side_effect=_get_async)

    with (
        patch("autom8_asana.cache.providers.unified.asyncio.sleep", new_callable=AsyncMock),
        patch("autom8_asana.cache.providers.unified.logger") as mock_logger,
    ):
        await store.put_batch_async(holders, warm_hierarchy=True, tasks_client=client)

    events = [c.args[0] for c in mock_logger.warning.call_args_list]
    # 3 attempts = 2 retries then a final give-up. The permanent branch must
    # not have short-circuited the ladder.
    assert events.count("warm_immediate_parent_retry") == 2
    assert "warm_immediate_parent_failed_final" in events
    assert "warm_immediate_parent_unresolvable" not in events


async def test_cached_ancestor_is_not_refetched(
    store: UnifiedTaskStore,
    cache_provider: MagicMock,
) -> None:
    """Control on the gap partition: an already-cached Business costs no GET."""
    holders = [_make_task("holder-1", parent_gid="biz-warm")]
    cache_provider._stored["biz-warm"] = MagicMock()  # noqa: SLF001
    client = _tasks_client(set())

    await store.put_batch_async(holders, warm_hierarchy=True, tasks_client=client)

    client.get_async.assert_not_awaited()
