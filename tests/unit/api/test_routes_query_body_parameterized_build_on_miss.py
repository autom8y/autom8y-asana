"""G2-RECV build-on-demand tests — request-time build for body-parameterized entities.

Implements TDD-G2RECV §12 test plan (T-BOD-1..8) and ADR-G2RECV-002. These tests
exercise the synchronous build-on-miss path inside
``UniversalResolutionStrategy._get_dataframe`` / ``_build_on_miss``. The cold-cache
first request for a body-parameterized entity (project/section) MUST build inline and
return 200 (AC-G2R-5), not 503.

Critical fidelity discipline:
- These tests MUST NOT patch ``_get_dataframe`` (that is the method under test). The
  T1 resolvability test patched ``_get_dataframe`` to bypass the cache; here we let
  ``_get_dataframe`` run for real and patch only ``_build_dataframe`` (the Asana fetch
  + ProgressiveProjectBuilder leaf) and the cache provider. Unit tests must not hit
  the network.
- T-BOD-3 locks the hard non-regression: offer-domain (``body_parameterized=False``)
  entities still return None on a cache miss and NEVER enter ``_build_on_miss``.

Outcome → status contract (TDD §10.6):
    build OK rows>0      → 200 (rows)
    build OK zero rows   → 200 (data: [], total_count: 0)   [legit empty project]
    build returns None   → 503 DATAFRAME_BUILD_FAILED
    build raises         → 503 DATAFRAME_BUILD_ERROR
    inline build timeout → 503 DATAFRAME_BUILD_TIMEOUT
    waiter timeout       → 503 CACHE_BUILD_IN_PROGRESS
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.api.exception_types import ApiDataFrameBuildError
from autom8_asana.services.resolver import EntityProjectRegistry
from autom8_asana.services.universal_strategy import (
    UniversalResolutionStrategy,
    get_universal_strategy,
)

# Synthetic 16-digit GID (S-06 pattern) supplied via the request body.
_BODY_PROJECT_GID = "1234567890123456"
_OTHER_PROJECT_GID = "6543210987654321"

JWT_TOKEN = "header.payload.signature"

# xdist group guard (SCAR-W1E-LOADGROUP-001): shares FastAPI app state via the
# module-scoped client; must run in the same group as the sibling route tests.
pytestmark = [pytest.mark.xdist_group("query_routes")]


def _assert_no_sprint2_fixture() -> None:
    """project/section must NOT be registered — exercise the cold prod path."""
    registry = EntityProjectRegistry.get_instance()
    assert registry.get_project_gid("project") is None, (
        "project must be UNREGISTERED for the G2-RECV build-on-miss tests"
    )
    assert registry.get_project_gid("section") is None, (
        "section must be UNREGISTERED for the G2-RECV build-on-miss tests"
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


def _empty_project_dataframe() -> pl.DataFrame:
    """Schema-shaped but ZERO rows — a legitimately empty project (200, not 503)."""
    return pl.DataFrame(
        schema={
            "gid": pl.Utf8,
            "name": pl.Utf8,
            "section": pl.Utf8,
            "vertical": pl.Utf8,
            "office_phone": pl.Utf8,
        }
    )


class _FakeCacheEntry:
    """Minimal stand-in for DataFrameCacheEntry (only .dataframe is read)."""

    def __init__(self, dataframe: pl.DataFrame) -> None:
        self.dataframe = dataframe


class FakeDataFrameCache:
    """Stateful in-memory fake of the cache provider's build-coalescer surface.

    Models exactly the methods _get_dataframe / _build_on_miss touch:
    get_async, acquire_build_lock_async, wait_for_build_async,
    release_build_lock_async, put_async, get_freshness_info. Lock semantics:
    first acquire for a key wins; a second concurrent acquire returns False and
    the caller waits on an asyncio.Event that put_async/release set.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], pl.DataFrame] = {}
        self._locks: dict[tuple[str, str], bool] = {}
        self._events: dict[tuple[str, str], asyncio.Event] = {}
        self._wait_should_timeout = False

    def _key(self, project_gid: str, entity_type: str) -> tuple[str, str]:
        return (project_gid, entity_type)

    async def get_async(self, project_gid: str, entity_type: str) -> _FakeCacheEntry | None:
        df = self._store.get(self._key(project_gid, entity_type))
        return _FakeCacheEntry(df) if df is not None else None

    def get_freshness_info(self, project_gid: str, entity_type: str) -> Any:
        return None

    async def acquire_build_lock_async(self, project_gid: str, entity_type: str) -> bool:
        key = self._key(project_gid, entity_type)
        if self._locks.get(key):
            return False  # someone else holds it
        self._locks[key] = True
        self._events[key] = asyncio.Event()
        return True

    async def release_build_lock_async(
        self, project_gid: str, entity_type: str, success: bool
    ) -> None:
        key = self._key(project_gid, entity_type)
        self._locks[key] = False
        if key in self._events:
            self._events[key].set()

    async def wait_for_build_async(
        self, project_gid: str, entity_type: str, timeout_seconds: float = 30.0
    ) -> _FakeCacheEntry | None:
        if self._wait_should_timeout:
            return None
        key = self._key(project_gid, entity_type)
        event = self._events.get(key)
        if event is not None:
            try:
                await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
            except TimeoutError:
                return None
        return await self.get_async(project_gid, entity_type)

    async def put_async(
        self,
        project_gid: str,
        entity_type: str,
        dataframe: pl.DataFrame,
        watermark: datetime,
        build_result: Any = None,
    ) -> None:
        self._store[self._key(project_gid, entity_type)] = dataframe


def _route_patches(
    *,
    build_side_effect: Any = None,
    build_return: Any = None,
    cache: FakeDataFrameCache | None = None,
):
    """Common patch stack for a route-level build-on-miss test.

    Patches JWT, bot PAT, AsanaClient (no network), the cache provider factory,
    and ``_build_dataframe`` (the leaf the build path invokes). Does NOT patch
    ``_get_dataframe`` — the method under test runs for real.
    """
    cache = cache if cache is not None else FakeDataFrameCache()

    build_kwargs: dict[str, Any] = {"new_callable": AsyncMock}
    if build_side_effect is not None:
        build_kwargs["side_effect"] = build_side_effect
    else:
        build_kwargs["return_value"] = build_return

    mock_asana = MagicMock()
    mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
    mock_asana.__aexit__ = AsyncMock(return_value=None)

    client_patch = patch("autom8_asana.client.AsanaClient")

    return cache, mock_asana, client_patch, build_kwargs


def _post_project_rows(client, body: dict[str, Any] | None = None):
    return client.post(
        "/v1/query/project/rows",
        headers={"Authorization": f"Bearer {JWT_TOKEN}"},
        json=body if body is not None else {"project_gid": _BODY_PROJECT_GID},
    )


class TestTBOD1ColdBuild200:
    """T-BOD-1 / AC-G2R-5: cold cache → first request builds inline → 200 with rows."""

    def test_cold_request_builds_and_returns_200(self, client) -> None:
        _assert_no_sprint2_fixture()
        cache = FakeDataFrameCache()
        df = _make_project_dataframe()
        watermark = datetime.now(UTC)

        cache, mock_asana, client_patch, build_kwargs = _route_patches(
            build_return=(df, watermark), cache=cache
        )

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
            client_patch as mock_client_class,
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy, "_build_dataframe", **build_kwargs
            ) as mock_build,
        ):
            mock_client_class.return_value = mock_asana
            response = _post_project_rows(client)

        assert response.status_code == 200, (
            f"cold build must yield 200, got {response.status_code}: {response.text}"
        )
        body = response.json()["data"]
        assert len(body["data"]) > 0, "expected non-empty rows from the built frame"
        assert body["meta"]["project_gid"] == _BODY_PROJECT_GID
        mock_build.assert_awaited_once()
        # Built frame was written to cache for warm reuse.
        assert cache._store.get((_BODY_PROJECT_GID, "project")) is not None


class TestTBOD2WarmSecondHit:
    """T-BOD-2: second hit on the same GID serves from cache, does NOT rebuild."""

    def test_warm_second_hit_no_rebuild(self, client) -> None:
        _assert_no_sprint2_fixture()
        # Pre-warm the cache for the GID so _get_dataframe's get_async branch hits.
        cache = FakeDataFrameCache()
        cache._store[(_BODY_PROJECT_GID, "project")] = _make_project_dataframe()

        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new_callable=AsyncMock,
            ) as mock_build,
        ):
            mock_client_class.return_value = mock_asana
            response = _post_project_rows(client)

        assert response.status_code == 200, response.text
        mock_build.assert_not_awaited()  # served warm — no rebuild


class TestTBOD3OfferDomainNonRegression:
    """T-BOD-3 (HARD NON-REGRESSION): offer-domain miss → None, NEVER builds.

    ADR-G2RECV-002 REJECT condition: build-on-miss is strictly gated on
    descriptor.body_parameterized. Offer-domain entities (False) must fall through
    to the unchanged cache-only `return None` and never enter _build_on_miss.
    """

    async def test_offer_domain_miss_returns_none_no_build(self) -> None:
        cache = FakeDataFrameCache()  # empty → miss for everything
        strategy = get_universal_strategy("unit")  # offer-domain, body_parameterized=False
        client = MagicMock()

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy, "_build_on_miss", new_callable=AsyncMock
            ) as mock_build_on_miss,
            patch.object(
                UniversalResolutionStrategy, "_build_dataframe", new_callable=AsyncMock
            ) as mock_build,
        ):
            result = await strategy._get_dataframe(_BODY_PROJECT_GID, client)

        assert result is None, "offer-domain cache miss must return None (cache-only)"
        mock_build_on_miss.assert_not_awaited()
        mock_build.assert_not_awaited()

    async def test_body_param_miss_enters_build_on_miss(self) -> None:
        """Mirror assertion: project (body_parameterized=True) DOES enter the build path."""
        cache = FakeDataFrameCache()
        strategy = get_universal_strategy("project")
        client = MagicMock()

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_on_miss",
                new_callable=AsyncMock,
                return_value=_make_project_dataframe(),
            ) as mock_build_on_miss,
        ):
            result = await strategy._get_dataframe(_BODY_PROJECT_GID, client)

        assert result is not None
        mock_build_on_miss.assert_awaited_once()


class TestTBOD4Concurrency:
    """T-BOD-4 / 4b: same-GID coalesces to a single build; distinct GIDs build in parallel."""

    async def test_same_gid_single_build(self) -> None:
        """Two concurrent same-GID _build_on_miss calls → _build_dataframe runs ONCE."""
        cache = FakeDataFrameCache()
        df = _make_project_dataframe()
        watermark = datetime.now(UTC)
        build_calls = 0
        build_started = asyncio.Event()

        async def slow_build(project_gid: str, client: Any) -> tuple[pl.DataFrame, datetime]:
            nonlocal build_calls
            build_calls += 1
            build_started.set()
            await asyncio.sleep(0.05)  # hold the lock so the sibling must wait
            return df, watermark

        strategy = get_universal_strategy("project")
        client = MagicMock()

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(side_effect=slow_build),
            ),
        ):
            # First call acquires the lock and begins the slow build; second call
            # arrives while the lock is held → coalesces (waits, reads cache).
            task1 = asyncio.create_task(strategy._build_on_miss(_BODY_PROJECT_GID, client))
            await build_started.wait()
            task2 = asyncio.create_task(strategy._build_on_miss(_BODY_PROJECT_GID, client))
            r1, r2 = await asyncio.gather(task1, task2)

        assert build_calls == 1, "same-GID requests must coalesce to a single build"
        assert r1 is not None and r2 is not None
        assert r1.equals(r2), "both requests get identical rows"

    async def test_distinct_gids_build_in_parallel(self) -> None:
        """Two concurrent distinct-GID builds → both build (no false contention)."""
        cache = FakeDataFrameCache()
        watermark = datetime.now(UTC)
        build_gids: list[str] = []

        async def build(project_gid: str, client: Any) -> tuple[pl.DataFrame, datetime]:
            build_gids.append(project_gid)
            await asyncio.sleep(0.02)
            return _make_project_dataframe(), watermark

        strategy = get_universal_strategy("project")
        client = MagicMock()

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(side_effect=build),
            ),
        ):
            r1, r2 = await asyncio.gather(
                strategy._build_on_miss(_BODY_PROJECT_GID, client),
                strategy._build_on_miss(_OTHER_PROJECT_GID, client),
            )

        assert sorted(build_gids) == sorted([_BODY_PROJECT_GID, _OTHER_PROJECT_GID]), (
            "distinct GIDs must both build (no false contention)"
        )
        assert r1 is not None and r2 is not None


class TestTBOD5BuildFailure:
    """T-BOD-5 / 5b: build returns None → 503 FAILED; build raises → 503 ERROR."""

    async def test_build_returns_none_raises_failed(self) -> None:
        cache = FakeDataFrameCache()
        strategy = get_universal_strategy("project")
        client = MagicMock()

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(return_value=(None, datetime.now(UTC))),
            ),
        ):
            with pytest.raises(ApiDataFrameBuildError) as exc:
                await strategy._build_on_miss(_BODY_PROJECT_GID, client)

        assert exc.value.code == "DATAFRAME_BUILD_FAILED"
        assert exc.value.status_code == 503
        # Lock released success=False (circuit-breaker failure path).
        assert cache._locks.get((_BODY_PROJECT_GID, "project")) is False

    async def test_build_raises_maps_to_error(self) -> None:
        cache = FakeDataFrameCache()
        strategy = get_universal_strategy("project")
        client = MagicMock()

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(side_effect=RuntimeError("asana boom")),
            ),
        ):
            with pytest.raises(ApiDataFrameBuildError) as exc:
                await strategy._build_on_miss(_BODY_PROJECT_GID, client)

        assert exc.value.code == "DATAFRAME_BUILD_ERROR"
        assert exc.value.status_code == 503
        assert cache._locks.get((_BODY_PROJECT_GID, "project")) is False

    def test_build_failure_route_returns_503(self, client) -> None:
        """End-to-end: build returns None → route returns 503 (not 500, not empty 200)."""
        _assert_no_sprint2_fixture()
        cache = FakeDataFrameCache()
        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(return_value=(None, datetime.now(UTC))),
            ),
        ):
            mock_client_class.return_value = mock_asana
            response = _post_project_rows(client)

        assert response.status_code == 503, (
            f"build failure must be 503, got {response.status_code}: {response.text}"
        )
        assert response.status_code != 500
        assert response.json()["error"]["code"] == "DATAFRAME_BUILD_FAILED"


class TestTBOD6BuildTimeout:
    """T-BOD-6: inline build exceeds the timeout → 503 DATAFRAME_BUILD_TIMEOUT, no hang."""

    async def test_build_timeout_raises_timeout(self) -> None:
        cache = FakeDataFrameCache()
        strategy = get_universal_strategy("project")
        client = MagicMock()

        async def hang(project_gid: str, client: Any) -> tuple[pl.DataFrame, datetime]:
            await asyncio.sleep(10)  # far exceeds the patched timeout
            return _make_project_dataframe(), datetime.now(UTC)

        # Patch settings so the timeout budget is tiny and the test is fast.
        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(side_effect=hang),
            ),
            patch("autom8_asana.services.universal_strategy.get_settings") as mock_settings,
        ):
            mock_settings.return_value.cache.dataframe_build_timeout_seconds = 0.05
            mock_settings.return_value.cache.dataframe_build_wait_seconds = 0.05
            with pytest.raises(ApiDataFrameBuildError) as exc:
                await strategy._build_on_miss(_BODY_PROJECT_GID, client)

        assert exc.value.code == "DATAFRAME_BUILD_TIMEOUT"
        assert exc.value.status_code == 503
        # Lock released success=False so the circuit breaker records the timeout.
        assert cache._locks.get((_BODY_PROJECT_GID, "project")) is False


class TestTBOD7LegitEmptyProject:
    """T-BOD-7: build succeeds with ZERO rows → 200 data:[] (distinguished from failure)."""

    async def test_empty_build_returns_frame_not_none(self) -> None:
        cache = FakeDataFrameCache()
        strategy = get_universal_strategy("project")
        client = MagicMock()
        empty = _empty_project_dataframe()

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(return_value=(empty, datetime.now(UTC))),
            ),
        ):
            result = await strategy._build_on_miss(_BODY_PROJECT_GID, client)

        assert result is not None, "an empty-but-built frame must be returned, not None"
        assert len(result) == 0
        # Empty frame was cached (warm on retry).
        assert cache._store.get((_BODY_PROJECT_GID, "project")) is not None

    def test_empty_project_route_returns_200_empty(self, client) -> None:
        """End-to-end: legit empty project → 200 with data: [] and total_count 0."""
        _assert_no_sprint2_fixture()
        cache = FakeDataFrameCache()
        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "autom8_asana.api.routes.internal.validate_service_token",
                _mock_jwt_validation(),
            ),
            patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
            patch("autom8_asana.client.AsanaClient") as mock_client_class,
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch.object(
                UniversalResolutionStrategy,
                "_build_dataframe",
                new=AsyncMock(return_value=(_empty_project_dataframe(), datetime.now(UTC))),
            ),
        ):
            mock_client_class.return_value = mock_asana
            response = _post_project_rows(client)

        assert response.status_code == 200, (
            f"legit empty project must be 200, got {response.status_code}: {response.text}"
        )
        body = response.json()["data"]
        assert body["data"] == [], "empty project → data: []"
        assert body["meta"]["total_count"] == 0


class TestTBOD8WaiterTimeout:
    """T-BOD-8: a coalesced waiter whose builder exceeds the wait budget → 503 IN_PROGRESS."""

    async def test_waiter_timeout_raises_in_progress(self) -> None:
        cache = FakeDataFrameCache()
        # Simulate: lock already held by another worker, and the wait times out.
        cache._locks[(_BODY_PROJECT_GID, "project")] = True
        cache._wait_should_timeout = True

        strategy = get_universal_strategy("project")
        client = MagicMock()

        with patch(
            "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
            return_value=cache,
        ):
            with pytest.raises(ApiDataFrameBuildError) as exc:
                await strategy._build_on_miss(_BODY_PROJECT_GID, client)

        assert exc.value.code == "CACHE_BUILD_IN_PROGRESS"
        assert exc.value.status_code == 503
        assert exc.value.details == {"retry_after_seconds": 5}
