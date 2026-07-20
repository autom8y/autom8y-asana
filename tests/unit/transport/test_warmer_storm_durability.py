"""RED-first durability test for the ASR offer-warmer self-inflicted 429 storm.

Per WS-A (TDD-asr-offer-warmer-durability §7). This test fires on the LIVE
failure mode reconstructed from the production bulk-warmer burst ``ff771464``
(>=8 concurrent ``rate_limit_429_received`` in 139ms, then ``Retry-After``-paced
throttle). It is the anti-theater counterpart to
``test_aimd_integration.py::test_429_triggers_aimd_decrease_in_request`` -- that
test proves AIMD *can* halve a window with a single ``MagicMock`` 429 and passes
green today while production storms. This test drives the FULL 34-GID warm-set
denominator (G-DENOM) through the single transport-altitude AIMD semaphore that
every warm request funnels through (``AsanaHttpClient._request`` ->
``semaphore.acquire()``), and asserts the AND of three post-fix conditions:

  (a) completion under storm   -- all 34 GIDs' requests reach SUCCESS, never a
                                  truncated subset that reads "above floor" by
                                  sampling the cheap tail;
  (b) provable hold-near-floor -- across >=2 simulated invocation boundaries the
                                  peak concurrent in-flight at the transport never
                                  exceeds the post-fix governed bound (NOT a single
                                  above-floor read; mirrors PT-02' (b) sustained);
  (c) AIMD provably contracted -- aimd_decrease fired AND was captured by the
                                  client's logger (unobservable until C-1 fixes
                                  the logger gate; the window must hold near floor,
                                  not blast-then-halve from a cold ceiling=50).

RED today because: the AIMD window starts at the ceiling (50) on a cold client
(``adaptive_semaphore.py`` window=ceiling), so the first burst admits far more
than 8 in-flight -> assertion (b) fails; and the deployed ``DefaultLogProvider``
fails ``isinstance(_, LoggerProtocol)`` (missing ``bind``), so ``semaphore_logger``
is ``None`` and ``aimd_decrease`` is never captured -> assertion (c) fails.

GREEN only after C-1 (logger gate), C-2/C-3 (conservative start + governed
window), C-5 (honest hold gate) land.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana._defaults.log import DefaultLogProvider
from autom8_asana.config import AsanaConfig, ConcurrencyConfig
from autom8_asana.core.project_registry import CONSUMER_WARM_SET_GIDS
from autom8_asana.transport.asana_http import AsanaHttpClient

pytestmark = pytest.mark.asyncio

# The live burst shape from invocation ff771464: the server 429s once concurrent
# in-flight exceeds a low tolerance. We model a HOSTILE server (threshold=2) so
# that even a conservatively-started warm trips at least one 429 -- this is the
# realistic production case (the workspace PAT tier may 429 at low concurrency,
# C-4 UV-P) and it is what makes assertion (c) provable: AIMD must demonstrably
# contract AND hold near floor, not merely avoid the storm by luck.
LIVE_BURST_THRESHOLD = 2

# The post-fix governed in-flight bound. With a conservative AIMD start and a
# sharpened multiplicative decrease, a warm under this hostile server must drive
# the window DOWN toward floor and HOLD it there -- never blasting the cold
# ceiling (12) wide, and far below the prior ceiling of 50. This is the
# anti-self-storm invariant.
POST_FIX_INFLIGHT_CEILING = 4


class _StormAuthProvider:
    """Minimal auth provider for the storm harness."""

    def get_secret(self, key: str) -> str:
        return "storm_test_token"


class _StormTransport:
    """An httpx-shaped transport that replays the ff771464 self-storm shape.

    Tracks live concurrent in-flight at the SERVER edge. While more than
    ``burst_threshold`` requests are simultaneously in flight, the server 429s
    (the self-inflicted storm: too many concurrent requests trip the rate
    ceiling). Once the caller backs off and in-flight falls to a sane level,
    requests 200. Records the peak concurrency the caller ever drove so the test
    can assert the warm held near floor instead of blasting wide.
    """

    def __init__(self, burst_threshold: int = LIVE_BURST_THRESHOLD) -> None:
        self._burst_threshold = burst_threshold
        self._in_flight = 0
        self.peak_in_flight = 0
        self.total_429 = 0
        self.total_200 = 0
        self._lock = asyncio.Lock()

    async def request(self, method: str, path: str, **kwargs: Any) -> MagicMock:
        async with self._lock:
            self._in_flight += 1
            self.peak_in_flight = max(self.peak_in_flight, self._in_flight)
            over_threshold = self._in_flight > self._burst_threshold
        try:
            # Yield so concurrent coroutines actually overlap at the edge.
            await asyncio.sleep(0)
            if over_threshold:
                async with self._lock:
                    self.total_429 += 1
                return self._make_429()
            async with self._lock:
                self.total_200 += 1
            return self._make_200()
        finally:
            async with self._lock:
                self._in_flight -= 1

    @staticmethod
    def _make_429(retry_after: int = 1) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 429
        resp.headers = {"Retry-After": str(retry_after), "retry-after": str(retry_after)}
        resp.json.return_value = {"errors": [{"message": "Rate limited"}]}
        resp.text = '{"errors":[{"message":"Rate limited"}]}'
        return resp

    @staticmethod
    def _make_200() -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {}
        resp.json.return_value = {"data": {"gid": "ok"}}
        resp.text = '{"data":{"gid":"ok"}}'
        return resp


class _CapturingLogProvider(DefaultLogProvider):
    """A DefaultLogProvider that ALSO records structured events.

    Subclassing DefaultLogProvider is deliberate: this test must use the SAME
    logger class the deployed bulk-warmer constructs (``client.py:144``), so the
    C-1 isinstance(LoggerProtocol) gate is exercised on the real production type.
    The capture is purely additive observation; behavior is the parent's.
    """

    def __init__(self) -> None:
        super().__init__()
        self.events: list[str] = []

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.events.append(msg)
        super().warning(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.events.append(msg)
        super().info(msg, *args, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.events.append(msg)
        super().debug(msg, *args, **kwargs)


def _build_storm_client(
    transport: _StormTransport, logger: _CapturingLogProvider
) -> AsanaHttpClient:
    """Construct an AsanaHttpClient wired to the storm transport + capturing logger.

    Mirrors the deployed construction path: the bulk-warmer builds AsanaClient,
    which passes its DefaultLogProvider down to AsanaHttpClient. We pass a
    DefaultLogProvider *subclass* so C-1's isinstance gate sees the real type.
    """
    config = AsanaConfig(concurrency=ConcurrencyConfig(read_limit=50, write_limit=15))
    client = AsanaHttpClient(config, _StormAuthProvider(), logger=logger)

    # Inject the storm transport as the platform client's underlying httpx client.
    mock_platform = AsyncMock()
    mock_platform._client = MagicMock()
    mock_platform._client.request = transport.request
    client._platform_client = mock_platform
    return client


async def _warm_one_invocation(client: AsanaHttpClient, gids: tuple[str, ...]) -> list[str]:
    """Fan out one GET per GID concurrently (the warm-cycle fan-out shape).

    Returns the GIDs that reached SUCCESS. Each GID funnels through the shared
    transport AIMD semaphore -- exactly the path the warm takes.
    """
    completed: list[str] = []

    async def _one(gid: str) -> None:
        try:
            await client.get(f"/projects/{gid}/sections")
            completed.append(gid)
        except Exception:
            pass

    await asyncio.gather(*[_one(gid) for gid in gids], return_exceptions=True)
    return completed


async def test_offer_warm_holds_floor_under_live_429_storm() -> None:
    """Drive the FULL 34-GID denominator under the ff771464 storm across >=2 cycles.

    PASS requires the AND of completion (a), held-near-floor across cycles (b),
    and provable+observable AIMD contraction (c). RED on current main.
    """
    assert len(CONSUMER_WARM_SET_GIDS) == 34, (
        "G-DENOM: the warm-set denominator must be the full 34 consumer GIDs, "
        f"got {len(CONSUMER_WARM_SET_GIDS)}"
    )

    transport = _StormTransport(burst_threshold=LIVE_BURST_THRESHOLD)
    logger = _CapturingLogProvider()
    client = _build_storm_client(transport, logger)

    # Two simulated invocation boundaries (checkpoint save->load->resume shape):
    # the limiter state on the shared client persists across the boundary, so a
    # post-fix warm must STAY governed across both -- not recover on read 1 then
    # blast on read 2.
    all_completed: set[str] = set()
    for _ in range(2):
        completed = await _warm_one_invocation(client, CONSUMER_WARM_SET_GIDS)
        all_completed.update(completed)

    # (a) completion under storm: the FULL denominator reached SUCCESS, not a
    #     lucky subset of the cheap tail.
    assert all_completed == set(CONSUMER_WARM_SET_GIDS), (
        "G-DENOM/completion: warm truncated under storm -- "
        f"{len(all_completed)}/34 GIDs reached SUCCESS; missing "
        f"{set(CONSUMER_WARM_SET_GIDS) - all_completed}"
    )

    # (b) provable hold-near-floor across the cycle boundary: the warm never drove
    #     more than the governed in-flight bound at the server edge. On main this
    #     fails: the cold AIMD window starts at ceiling=50, so the first fan-out
    #     blasts the full burst wide before AIMD reacts.
    assert transport.peak_in_flight <= POST_FIX_INFLIGHT_CEILING, (
        "anti-self-storm: peak concurrent in-flight at the API was "
        f"{transport.peak_in_flight}, exceeding the governed ceiling of "
        f"{POST_FIX_INFLIGHT_CEILING}. The warm is self-inflicting the 429 storm "
        "(cold AIMD window starts at ceiling instead of a conservative start)."
    )

    # (c) AIMD provably contracted AND observable: aimd_decrease fired and the
    #     deployed-shape logger captured it. On main this fails twice over: the
    #     DefaultLogProvider-subclass fails isinstance(LoggerProtocol) so
    #     semaphore_logger is None (logger-dark, C-1), and with the storm avoided
    #     by (b) there may be no decrease at all.
    assert "aimd_decrease" in logger.events, (
        "AIMD-dark: no aimd_decrease event captured. Either the logger gate "
        "nulled semaphore_logger for the DefaultLogProvider path (C-1 unfixed), "
        "or the window never contracted under the storm."
    )

    # The window must have actually held near floor during the storm (not merely
    # logged one decrease then climbed back to ceiling).
    assert client._read_semaphore.current_limit <= POST_FIX_INFLIGHT_CEILING, (
        "AIMD window did not hold near floor under sustained storm: "
        f"current_limit={client._read_semaphore.current_limit} > "
        f"{POST_FIX_INFLIGHT_CEILING}"
    )


async def test_logger_gate_admits_default_log_provider_for_aimd() -> None:
    """C-1 focused: the deployed DefaultLogProvider path must be AIMD-observable.

    The production bulk-warmer constructs AsanaClient with DefaultLogProvider
    (client.py:144). On main, AsanaHttpClient nulls semaphore_logger for that
    type because isinstance(DefaultLogProvider(), LoggerProtocol) is False
    (LoggerProtocol requires ``bind``; DefaultLogProvider lacks it). This test
    asserts the AIMD semaphore RECEIVES a usable logger when constructed with the
    real deployed logger type -- RED on main (logger is None), GREEN after C-1.
    """
    logger = DefaultLogProvider()
    config = AsanaConfig(concurrency=ConcurrencyConfig(read_limit=50, write_limit=15))
    client = AsanaHttpClient(config, _StormAuthProvider(), logger=logger)

    # The read AIMD semaphore must have a non-None logger so aimd_decrease can emit.
    assert client._read_semaphore._logger is not None, (
        "C-1: AIMD semaphore_logger is None for the deployed DefaultLogProvider "
        "path -- the AIMD limiter runs observability-dark and no aimd_decrease / "
        "aimd_at_minimum event can ever reach prod logs under a 429 storm."
    )
