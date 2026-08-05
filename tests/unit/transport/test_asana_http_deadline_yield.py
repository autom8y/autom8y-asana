"""F1a pacing teeth: the warm-deadline yield fires INSIDE the transport retry loop.

Root-cause forensics (acct 696318035277, /aws/lambda/autom8-asana-cache-warmer-bulk,
7 d to 2026-08-05): 229/932 invocations (24.6 %) SIGKILLed at the 900 s wall mid-429-storm
because the ``while True`` retry loops in ``asana_http.py`` had NO deadline awareness -- a
sampled kill (req 557f3498..., 07:51:38Z) died 11.6 min after ``retry_waiting attempt=5
max_retries=5`` with no graceful yield.

RED-AGAINST-MAIN: on origin/main ``_wait_for_retry`` is 3 lines with no deadline check, so
``test_wait_for_retry_yields_when_deadline_reached`` and
``test_retry_loop_yields_on_first_retry_past_deadline`` FAIL (the loop exhausts all retries
and raises RateLimitError regardless of the deadline). The guard is the diff that makes them
pass. Two-sided: with the deadline NOT reached the loop retries normally (the guard never
false-fires).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from autom8_asana.config import AsanaConfig
from autom8_asana.core.warm_deadline import (
    WarmDeadlineExceeded,
    arm_warm_deadline,
    disarm_warm_deadline,
)
from autom8_asana.errors import RateLimitError
from autom8_asana.transport.asana_http import AsanaHttpClient


class _MockAuthProvider:
    def get_secret(self, key: str) -> str:
        return "test_token"


class _FakeContext:
    def __init__(self, remaining_ms: int) -> None:
        self._remaining_ms = remaining_ms

    def get_remaining_time_in_millis(self) -> int:
        return self._remaining_ms


def _make_client() -> AsanaHttpClient:
    return AsanaHttpClient(AsanaConfig(), _MockAuthProvider())


def _make_429_response() -> httpx.Response:
    request = httpx.Request("GET", "https://app.asana.com/api/1.0/tasks")
    return httpx.Response(
        429,
        headers={"Retry-After": "1"},
        json={"errors": [{"message": "Rate limit exceeded"}]},
        request=request,
    )


@pytest.fixture(autouse=True)
def _disarm():
    disarm_warm_deadline()
    yield
    disarm_warm_deadline()


# --------------------------------------------------------------------------
# Funnel-level: _wait_for_retry is the single choke-point all 3 loops route through.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_retry_yields_when_deadline_reached():
    """RED on main: with the deadline reached, _wait_for_retry raises instead of sleeping."""
    client = _make_client()
    client._retry_policy.wait = AsyncMock()  # guard must fire BEFORE any sleep
    arm_warm_deadline(_FakeContext(remaining_ms=0))  # reached

    with pytest.raises(WarmDeadlineExceeded):
        await client._wait_for_retry(1)

    client._retry_policy.wait.assert_not_awaited()


@pytest.mark.asyncio
async def test_wait_for_retry_proceeds_when_deadline_not_reached():
    """Two-sided: with ample time the guard does NOT fire; the retry sleep proceeds."""
    client = _make_client()
    client._retry_policy.wait = AsyncMock()
    arm_warm_deadline(_FakeContext(remaining_ms=600_000))  # not reached

    await client._wait_for_retry(1)

    client._retry_policy.wait.assert_awaited_once()


@pytest.mark.asyncio
async def test_wait_for_retry_proceeds_when_disarmed():
    """INERT: disarmed (ECS/API/every non-warmer) => byte-identical to origin/main."""
    client = _make_client()
    client._retry_policy.wait = AsyncMock()
    # no arm

    await client._wait_for_retry(1)

    client._retry_policy.wait.assert_awaited_once()


# --------------------------------------------------------------------------
# Loop-level: a real retry loop against a fake 429 transport yields inside the loop.
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_loop_yields_on_first_retry_past_deadline():
    """RED on main: the retry loop yields (WarmDeadlineExceeded) after ONE request when the
    deadline is reached, instead of storming through all max_attempts retries."""
    client = _make_client()
    client._retry_policy.wait = AsyncMock()  # no real sleeps if the guard failed to fire

    fake_platform = AsyncMock()
    fake_platform._client.request = AsyncMock(return_value=_make_429_response())
    client._get_client = AsyncMock(return_value=fake_platform)

    arm_warm_deadline(_FakeContext(remaining_ms=0))  # reached

    with pytest.raises(WarmDeadlineExceeded):
        await client._request_paginated("GET", "/tasks")

    # One request (attempt 0), then the guard yields at the first retry decision --
    # NOT the full max_attempts storm.
    assert fake_platform._client.request.await_count == 1
    client._retry_policy.wait.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_loop_storms_all_attempts_when_deadline_not_reached():
    """Two-sided: with ample time the loop retries max_attempts times then raises
    RateLimitError (normal behaviour -- the guard never false-fires)."""
    client = _make_client()
    client._retry_policy.wait = AsyncMock()  # skip real backoff sleeps

    fake_platform = AsyncMock()
    fake_platform._client.request = AsyncMock(return_value=_make_429_response())
    client._get_client = AsyncMock(return_value=fake_platform)

    arm_warm_deadline(_FakeContext(remaining_ms=600_000))  # not reached

    max_attempts = client._retry_policy.max_attempts  # 6 (5 retries + 1 initial)
    with pytest.raises(RateLimitError):
        await client._request_paginated("GET", "/tasks")

    assert fake_platform._client.request.await_count == max_attempts
    assert client._retry_policy.wait.await_count == max_attempts - 1
