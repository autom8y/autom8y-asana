"""G2-RECV build-on-demand tests — request-time build for body-parameterized entities.

Implements TDD-G2RECV §12 test plan (T-BOD-1..8) and ADR-G2RECV-002.

Option B (G2-RECV frame-quality convergence fix): ``_build_on_miss`` no longer
builds inline and returns a DataFrame.  Instead it launches a background build
(via ``_swr_build_callback``) and ALWAYS raises a retryable 503
``CACHE_BUILD_IN_PROGRESS``.  The warm-hit path (T-BOD-2) and the offer-domain
non-regression (T-BOD-3) are unchanged.

Critical fidelity discipline:
- The route-level tests MUST NOT patch ``_get_dataframe`` (that is the method under
  test). We let ``_get_dataframe`` / ``_build_on_miss`` run for real and patch only
  the cache provider and ``_swr_build_callback`` (the background leaf). Unit tests
  must not hit the network.
- Patching ``_build_dataframe`` is now PROHIBITED for cold-miss tests — that mock
  is exactly why the frame-quality gap slipped past CI (the old inline path was
  being tested, not the background-build path).
- T-BOD-3 locks the hard non-regression: offer-domain (``body_parameterized=False``)
  entities still return None on a cache miss and NEVER enter ``_build_on_miss``.

CI-fragility discipline (SCAR-W1E-LOADGROUP-001 follow-on):
    Background-build tests use ``asyncio.create_task`` internally but the test
    itself only ``await``s ``_build_on_miss`` once and then awaits a short
    ``asyncio.sleep`` for teardown.  This is the same pattern used in
    ``test_g2_recv_frame_quality.py`` and does NOT trigger the CI worker crash.

Outcome → status contract (new, Option B):
    cache warm (any entity)          → 200 (rows served from cache)
    cold miss body_parameterized     → 503 CACHE_BUILD_IN_PROGRESS (retryable)
    cold miss offer-domain           → resolver returns None → query-layer 404/empty
    warm retry after background build→ 200 (served from cache)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from datetime import datetime

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
        # Non-blocking: a coalesced waiter either reads the already-built frame or
        # (when _wait_should_timeout is set) reports a timeout. We deliberately do
        # NOT await an asyncio.Event under wait_for here — that raw-asyncio pattern
        # is the CI worker-crash trigger this file was reformed to eliminate.
        if self._wait_should_timeout:
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


class TestTBOD1ColdBuild503:
    """T-BOD-1 / Option B: cold cache → background build launched → 503 retryable.

    Option B changes the cold-miss contract: instead of building inline and
    returning 200, the first cold request for a body-parameterized entity now
    launches a background build and returns 503 CACHE_BUILD_IN_PROGRESS.
    A subsequent request after the background build completes will serve 200
    from the warm cache.
    """

    def test_cold_request_launches_background_build_and_returns_503(self, client) -> None:
        _assert_no_sprint2_fixture()
        cache = FakeDataFrameCache()
        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        async def _noop_swr(cache_arg: Any, project_gid: str, entity_type: str) -> None:
            """No-op background build stub so no real Asana network I/O occurs."""

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
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_noop_swr,
            ),
        ):
            mock_client_class.return_value = mock_asana
            response = _post_project_rows(client)

        assert response.status_code == 503, (
            f"cold miss must yield 503 CACHE_BUILD_IN_PROGRESS (Option B), "
            f"got {response.status_code}: {response.text}"
        )
        assert response.json()["error"]["code"] == "CACHE_BUILD_IN_PROGRESS"


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

    Each test is a single plain ``await`` against ``_get_dataframe`` — no
    ``asyncio.create_task`` / ``asyncio.gather``, no pending tasks left behind.
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


class TestTBOD5ColdMissAlways503:
    """T-BOD-5 / Option B: cold miss for body-parameterized entity → always 503.

    Option B removes all the inline build failure modes (DATAFRAME_BUILD_FAILED,
    DATAFRAME_BUILD_ERROR) from the request path.  Every cold miss now returns
    CACHE_BUILD_IN_PROGRESS regardless of what happens during the background build.

    The background build failure is captured by the done-callback logger (not
    surfaced to the caller synchronously).  A subsequent cold request after a
    failed build will trigger a new background build attempt (the in-flight key
    is cleared on failure).

    Tests for dedup and background task lifecycle live in
    ``tests/unit/services/test_g2_recv_frame_quality.py`` (AC-G2R6-BG1..3).
    """

    async def test_build_on_miss_always_raises_cache_build_in_progress(self) -> None:
        """_build_on_miss raises CACHE_BUILD_IN_PROGRESS on cold miss (no exception
        from the background build is surfaced synchronously)."""
        from autom8_asana.services import universal_strategy as _us_mod

        cache = FakeDataFrameCache()
        strategy = get_universal_strategy("project")
        client = MagicMock()

        # Clear in-flight set so the test always starts from cold state.
        _us_mod._background_builds.discard((_BODY_PROJECT_GID, "project"))

        async def _noop_swr(cache_arg: Any, project_gid: str, entity_type: str) -> None:
            pass

        with (
            patch(
                "autom8_asana.cache.dataframe.factory.get_dataframe_cache_provider",
                return_value=cache,
            ),
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_noop_swr,
            ),
        ):
            with pytest.raises(ApiDataFrameBuildError) as exc:
                await strategy._build_on_miss(_BODY_PROJECT_GID, client)

        assert exc.value.code == "CACHE_BUILD_IN_PROGRESS"
        assert exc.value.status_code == 503

    def test_cold_miss_route_returns_503_cache_build_in_progress(self, client) -> None:
        """End-to-end: cold body-parameterized miss → route returns 503
        CACHE_BUILD_IN_PROGRESS (not 500, not empty 200, not DATAFRAME_BUILD_FAILED)."""
        _assert_no_sprint2_fixture()
        cache = FakeDataFrameCache()
        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        async def _noop_swr(cache_arg: Any, project_gid: str, entity_type: str) -> None:
            pass

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
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_noop_swr,
            ),
        ):
            mock_client_class.return_value = mock_asana
            response = _post_project_rows(client)

        assert response.status_code == 503, (
            f"cold miss must be 503, got {response.status_code}: {response.text}"
        )
        assert response.status_code != 500
        assert response.json()["error"]["code"] == "CACHE_BUILD_IN_PROGRESS"


class TestTBOD6WarmRetryAfterBackgroundBuild:
    """T-BOD-6 (Option B): after background build completes, warm retry returns 200.

    The inline timeout (DATAFRAME_BUILD_TIMEOUT) no longer exists — Option B
    removes the request-bound ``asyncio.wait_for`` guard.  T-BOD-6 is repurposed
    to verify the two-phase flow: cold miss → 503 → warm cache → 200.

    The warm-hit path after background completion is already covered by
    ``TestTBOD2WarmSecondHit`` (pre-warmed cache).  This test makes the
    causality explicit: first request triggers background build, second request
    (after cache is warm) returns 200.
    """

    def test_warm_retry_after_background_build_returns_200(self, client) -> None:
        _assert_no_sprint2_fixture()
        # Start with an empty cache → first request will get 503.
        cache = FakeDataFrameCache()
        mock_asana = MagicMock()
        mock_asana.__aenter__ = AsyncMock(return_value=mock_asana)
        mock_asana.__aexit__ = AsyncMock(return_value=None)

        async def _noop_swr(cache_arg: Any, project_gid: str, entity_type: str) -> None:
            pass

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
            patch(
                "autom8_asana.cache.dataframe.factory._swr_build_callback",
                side_effect=_noop_swr,
            ),
        ):
            mock_client_class.return_value = mock_asana
            # First request — cold miss → 503.
            first_response = _post_project_rows(client)

        assert first_response.status_code == 503
        assert first_response.json()["error"]["code"] == "CACHE_BUILD_IN_PROGRESS"

        # Simulate background build completing by pre-warming the cache.
        cache._store[(_BODY_PROJECT_GID, "project")] = _make_project_dataframe()

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
        ):
            mock_client_class.return_value = mock_asana
            # Second request — warm hit → 200.
            second_response = _post_project_rows(client)

        assert second_response.status_code == 200, (
            f"warm retry after background build must yield 200, "
            f"got {second_response.status_code}: {second_response.text}"
        )
        body = second_response.json()["data"]
        assert len(body["data"]) > 0, "expected non-empty rows from warm cache"


class TestTBOD7LegitEmptyProject:
    """T-BOD-7 (Option B): legit empty project is served 200 from warm cache.

    Option B: the background build eventually puts the frame (even if empty)
    into the cache.  A warm-hit request with the empty frame returns 200
    data:[] (distinguishing a legit empty project from an uncached one).

    The cold-miss path (before the background build completes) returns 503
    CACHE_BUILD_IN_PROGRESS — this is indistinguishable from a non-empty
    cold-miss project by the caller until the build completes.
    """

    def test_warm_empty_project_returns_200_empty(self, client) -> None:
        """Warm cache with empty project frame → 200 data: [] (not a 503 or error)."""
        _assert_no_sprint2_fixture()
        # Pre-warm cache with an empty frame (simulates background build completing
        # for a legitimately empty project).
        cache = FakeDataFrameCache()
        cache._store[(_BODY_PROJECT_GID, "project")] = _empty_project_dataframe()

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
        ):
            mock_client_class.return_value = mock_asana
            response = _post_project_rows(client)

        assert response.status_code == 200, (
            f"warm empty project must be 200, got {response.status_code}: {response.text}"
        )
        body = response.json()["data"]
        assert body["data"] == [], "warm empty project → data: []"
        assert body["meta"]["total_count"] == 0
