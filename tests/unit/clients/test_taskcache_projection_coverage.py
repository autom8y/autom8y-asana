"""PHE (Projection-Honest Entry) TASK-cache coverage suite.

Per TDD-taskcache-projection-coverage-2026-07-08 SS6.1: the 2-sided STARVATION
CANARY plus teeth / ping-pong / interaction arms. The TASK cache key is
opt_fields-blind (FR-CLIENT-002); before PHE the hit path served a cached entry
with NO check that the stored entry covers the requested projection, so a first
reader whose hydration union lacked a field family STARVED every later reader
that needed it (DEFECT-taskcache-cross-reader-section-starvation-2026-07-08:
the C-1-guard-first read poisoned the ACTIVE-section preflight with
``section=None`` and false-HALTed the floodgates batch).

The fake transport here echoes EXACTLY the requested opt_fields params --
memberships elements carry ``section`` iff ``memberships.section.*`` was
requested -- reproducing the proven live probe shape. The fakes that HID this
class returned complete dicts regardless of projection.

RED-before receipt (discriminating-canary mode 2 -- a genuine production gap,
NOT an injected defect): on main @ 5b5c249a the canary FAILS -- one total HTTP
call, the second reader is served section-less memberships from cache.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from autom8_asana.cache.models.entry import EntryType
from autom8_asana.clients.tasks import TasksClient
from autom8_asana.models.business import STANDARD_TASK_OPT_FIELDS

if TYPE_CHECKING:
    from tests.unit.clients.conftest import MockCacheProvider

    from autom8_asana.config import AsanaConfig


TASK_GID = "1234567890123"

# The proven starvation pair (DEFECT-taskcache-cross-reader-section-starvation):
# reader-1 = the C-1-guard projection; reader-2 = the ACTIVE-section preflight.
READER_1_OPT_FIELDS = ["gid", "name"]
READER_2_OPT_FIELDS = ["memberships.section.gid", "memberships.section.name"]


class EchoOptFieldsTransport:
    """Fake HTTP transport that echoes exactly the requested ``opt_fields``.

    Models real Asana projection semantics: every field family is present in
    the response iff it was requested. Membership elements carry ``section``
    iff ``memberships.section.*`` was requested (the proven probe shape --
    a section-less membership is what poisoned the preflight).
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, set[str]]] = []

    @staticmethod
    def _requested(params: dict[str, Any] | None) -> set[str]:
        params = params or {}
        raw = params.get("opt_fields", "")
        return set(raw.split(",")) if raw else set()

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        requested = self._requested(params)
        self.calls.append((path, requested))
        gid = path.rsplit("/", 1)[-1]

        data: dict[str, Any] = {"gid": gid, "resource_type": "task"}
        if "name" in requested:
            data["name"] = "PLAY: Custom Calendar Integration"
        if "modified_at" in requested:
            data["modified_at"] = "2026-07-08T12:00:00.000Z"
        if "parent" in requested or "parent.gid" in requested:
            data["parent"] = None
        if any(f.startswith("memberships") for f in requested):
            membership: dict[str, Any] = {}
            if {"memberships.project.gid", "memberships.project.name"} & requested:
                membership["project"] = {"gid": "9990001112223", "name": "Calendar-Integrations"}
            if {"memberships.section.gid", "memberships.section.name"} & requested:
                membership["section"] = {"gid": "8880001112223", "name": "ACTIVE"}
            data["memberships"] = [membership]
        if any(f.startswith("custom_fields") for f in requested):
            data["custom_fields"] = [
                {"gid": "cf1", "name": "Office Phone", "display_value": "+15551234567"},
            ]
        if any(f.startswith("tags") for f in requested):
            data["tags"] = []
        return data


@pytest.fixture
def echo_transport() -> EchoOptFieldsTransport:
    """Opt_fields-echoing fake transport with call recording."""
    return EchoOptFieldsTransport()


@pytest.fixture
def tasks_client(
    echo_transport: EchoOptFieldsTransport,
    config: AsanaConfig,
    auth_provider: Any,
    cache_provider: MockCacheProvider,
) -> TasksClient:
    """TasksClient with a REAL in-process cache and the echoing transport."""
    return TasksClient(
        http=echo_transport,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        cache_provider=cache_provider,
        client=None,
    )


def _section_of(served: dict[str, Any]) -> Any:
    """Extract memberships[0].section from a served raw task dict (None-safe)."""
    memberships = served.get("memberships") or []
    if not memberships:
        return None
    return memberships[0].get("section")


class TestStarvationCanary:
    """SS6.1: the 2-sided starvation canary (the sprint gate)."""

    async def test_second_reader_gets_section_family_via_second_fetch(
        self,
        tasks_client: TasksClient,
        echo_transport: EchoOptFieldsTransport,
    ) -> None:
        """THE CANARY. Reader-1 (C-1-guard projection) then reader-2 (ACTIVE-section
        preflight projection) on ONE gid: reader-2 MUST get its section family,
        via a SECOND fetch whose params carry ``memberships.section.*``.

        RED on main @ 5b5c249a: the second read HITs the opt_fields-blind cache
        (ONE total HTTP call) and serves section-less memberships -- the exact
        false-HALT poisoning from
        DEFECT-taskcache-cross-reader-section-starvation-2026-07-08.
        GREEN after PHE: coverage-miss => second HTTP call carrying the union.
        """
        await tasks_client.get_async(TASK_GID, raw=True, opt_fields=list(READER_1_OPT_FIELDS))
        assert len(echo_transport.calls) == 1
        first_requested = echo_transport.calls[0][1]

        served = await tasks_client.get_async(
            TASK_GID, raw=True, opt_fields=list(READER_2_OPT_FIELDS)
        )

        # The second reader's demand was starved from the first hydration union
        # (STANDARD deliberately excludes memberships.section.*), so a SECOND
        # fetch must occur...
        assert len(echo_transport.calls) == 2, (
            "reader-2's projection is NOT covered by the stored entry; the hit "
            "path must coverage-miss and re-fetch -- got a starved cache serve "
            f"instead ({len(echo_transport.calls)} HTTP call(s) total)"
        )
        second_requested = echo_transport.calls[1][1]
        # ...carrying the section family...
        assert {"memberships.section.gid", "memberships.section.name"} <= second_requested
        # ...AND the previously-stored projection (the anti-thrash union term).
        assert first_requested <= second_requested, (
            "re-hydration must fetch union(requested, STANDARD, stored projection); "
            f"missing stored fields: {sorted(first_requested - second_requested)}"
        )

        # And the served data actually carries the section family.
        section = _section_of(served)
        assert section is not None, (
            "reader-2 was served section-less memberships (section=None) -- the "
            "exact preflight poisoning shape"
        )
        assert section["name"] == "ACTIVE"
        assert section["gid"] == "8880001112223"

    async def test_teeth_covered_reader_serves_with_zero_extra_http(
        self,
        tasks_client: TasksClient,
        echo_transport: EchoOptFieldsTransport,
    ) -> None:
        """TEETH / no-defect arm: a reader whose requested projection IS covered
        by the stored union gets a cache HIT with ZERO extra HTTP calls --
        the predicate bites ONLY on the defect; the cache still serves."""
        await tasks_client.get_async(TASK_GID, raw=True, opt_fields=list(READER_1_OPT_FIELDS))
        assert len(echo_transport.calls) == 1

        # requested subset of stored union (reader-1's union includes STANDARD).
        covered = await tasks_client.get_async(
            TASK_GID,
            raw=True,
            opt_fields=["name", "custom_fields.display_value"],
        )

        assert len(echo_transport.calls) == 1, (
            "covered reader must be served from cache with ZERO extra HTTP calls"
        )
        assert covered["name"] == "PLAY: Custom Calendar Integration"

    async def test_ping_pong_bound_two_disjoint_readers_alternating(
        self,
        tasks_client: TasksClient,
        echo_transport: EchoOptFieldsTransport,
    ) -> None:
        """Ping-pong regression: alternating the two disjoint readers x10 on one
        gid produces exactly TWO total HTTP calls (initial + ONE widening) --
        pins the union-monotone anti-thrash property of the stored-projection
        term in the re-hydration union."""
        for _ in range(10):
            await tasks_client.get_async(TASK_GID, raw=True, opt_fields=list(READER_1_OPT_FIELDS))
            await tasks_client.get_async(TASK_GID, raw=True, opt_fields=list(READER_2_OPT_FIELDS))

        assert len(echo_transport.calls) == 2, (
            "entry projections must be monotonically non-decreasing within a "
            "cache lifetime: disjoint readers converge after ONE widening fetch, "
            f"got {len(echo_transport.calls)} HTTP calls"
        )

    async def test_unknown_legacy_entry_misses_once_and_heals(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        echo_transport: EchoOptFieldsTransport,
    ) -> None:
        """A pre-PHE entry (no projection metadata) is coverage-UNKNOWN: it
        misses ONCE, is re-fetched at the union, rewritten projection-honest,
        and serves thereafter (self-healing migration, no version bump)."""
        from datetime import UTC, datetime

        from autom8_asana.cache.models.entry import CacheEntry

        legacy = CacheEntry(
            key=TASK_GID,
            data={"gid": TASK_GID, "name": "Legacy"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 1, 1, tzinfo=UTC),
            ttl=300,
        )
        cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"] = legacy

        await tasks_client.get_async(TASK_GID, raw=True, opt_fields=list(READER_1_OPT_FIELDS))
        assert len(echo_transport.calls) == 1, "UNKNOWN entry must miss once"

        await tasks_client.get_async(TASK_GID, raw=True, opt_fields=list(READER_1_OPT_FIELDS))
        assert len(echo_transport.calls) == 1, "healed entry must serve (no second fetch)"

    async def test_raw_and_model_paths_gate_identically(
        self,
        client_factory: Any,
        echo_transport: EchoOptFieldsTransport,
    ) -> None:
        """raw/model parity: the predicate runs on metadata BEFORE the raw/model
        branch, so both paths coverage-miss (and hit) identically."""
        from tests.unit.clients.conftest import MockCacheProvider

        for raw in (True, False):
            transport = EchoOptFieldsTransport()
            client = client_factory(
                TasksClient,
                http=transport,
                cache_provider=MockCacheProvider(),
                client=None,
            )
            await client.get_async(TASK_GID, raw=raw, opt_fields=list(READER_1_OPT_FIELDS))
            await client.get_async(TASK_GID, raw=raw, opt_fields=list(READER_2_OPT_FIELDS))
            assert len(transport.calls) == 2, f"raw={raw}: expected miss-then-widen"
            await client.get_async(TASK_GID, raw=raw, opt_fields=list(READER_2_OPT_FIELDS))
            assert len(transport.calls) == 2, f"raw={raw}: expected covered hit"


class TestCoverageMissStalenessInteraction:
    """SS6.5: coverage-miss x soft-stale = ONE fetch (the open-fork test)."""

    async def test_coverage_miss_on_soft_stale_entry_fetches_exactly_once(
        self,
        tasks_client: TasksClient,
        cache_provider: MockCacheProvider,
        echo_transport: EchoOptFieldsTransport,
    ) -> None:
        """An entry that is BOTH coverage-insufficient AND soft-invalidated
        (staleness hint on its freshness stamp) satisfies both conditions with
        ONE union fetch -- no double-fetch."""
        from datetime import UTC, datetime

        from autom8_asana.cache.models.entry import CacheEntry
        from autom8_asana.cache.models.freshness_stamp import (
            FreshnessStamp,
            VerificationSource,
        )

        stamp = FreshnessStamp(
            last_verified_at=datetime(2026, 1, 1, tzinfo=UTC),
            source=VerificationSource.API_FETCH,
        ).with_staleness_hint("mutation:task:update:999")
        narrow_stale = CacheEntry(
            key=TASK_GID,
            data={"gid": TASK_GID, "name": "Stale narrow"},
            entry_type=EntryType.TASK,
            version=datetime(2026, 1, 1, tzinfo=UTC),
            ttl=300,
            metadata={"opt_fields_used": ["gid", "name"], "completeness_level": "minimal"},
            freshness_stamp=stamp,
        )
        cache_provider._cache[f"{TASK_GID}:{EntryType.TASK.value}"] = narrow_stale

        served = await tasks_client.get_async(
            TASK_GID, raw=True, opt_fields=list(READER_2_OPT_FIELDS)
        )

        assert len(echo_transport.calls) == 1, (
            "coverage-miss on a soft-stale entry must resolve with exactly ONE "
            f"fetch; got {len(echo_transport.calls)}"
        )
        assert _section_of(served) is not None
        # The replacement entry is projection-honest and fresh (TTL reset,
        # stored projection = the union actually fetched).
        _, rewritten = cache_provider.set_versioned_calls[-1]
        stored = set(rewritten.metadata["opt_fields_used"])
        assert set(READER_2_OPT_FIELDS) <= stored
        assert set(STANDARD_TASK_OPT_FIELDS) <= stored
        assert {"gid", "name"} <= stored, "stored projection term must be carried"
