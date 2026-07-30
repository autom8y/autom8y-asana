"""AIMD signal-blindness fix (S8-0 pre-gate · REQUIREMENT 1 · the 429-scar class).

Before S8-0 the paced parity source only ever called ``slot.succeed()``: a 429 on the
outbound leg was INVISIBLE to AIMD, so the concurrency window grew and never shrank —
the self-inflicted-429-storm scar reproduced inside the cutover gate. The fix mirrors
the TRUE v1 path (``transport.asana_http`` :485/:633/:723): a 429 (or rate-limit
equivalent) calls ``slot.reject()`` BEFORE retry-handling.

Two-sided teeth: a synthetic 429 MUST propagate a reject (``decrease_count`` 0 → 1 —
this assertion FAILS on the pre-fix code, where it stayed 0); a 200 MUST NOT reject.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.errors import AsanaError, RateLimitError
from autom8_asana.substrate.identity import ArtifactId
from tests.harness.substrate_gate.exemplars import exemplar_one_observation
from tests.harness.substrate_gate.parity import (
    PacedLiveParitySource,
    ParityObservation,
    ParityOutboundError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


def _aid() -> ArtifactId:
    return ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)


class _FastClock:
    """Monotonically-advancing fake clock so the floor gate earns tokens instantly."""

    def __init__(self) -> None:
        self._t = 0.0

    def __call__(self) -> float:
        self._t += 100.0
        return self._t


async def _no_sleep(_seconds: float) -> None:
    return None


def _armed_source(
    outbound: Callable[[ArtifactId], Awaitable[ParityObservation]],
) -> PacedLiveParitySource:
    return PacedLiveParitySource(
        armed=True, outbound=outbound, gate_clock=_FastClock(), gate_sleep=_no_sleep
    )


def test_synthetic_429_propagates_reject_to_aimd() -> None:
    """A 429 on the outbound leg shrinks the AIMD window (decrease_count 0 → 1)."""

    async def _rate_limited(_aid_: ArtifactId) -> ParityObservation:
        raise RateLimitError(
            "synthetic 429 from the parity outbound leg", status_code=429, retry_after=1
        )

    source = _armed_source(_rate_limited)
    assert source.aimd_stats()["decrease_count"] == 0  # baseline: no signal yet

    with pytest.raises(ParityOutboundError) as caught:
        asyncio.run(source.fetch_all_paced([_aid()]))

    # THE discriminating assertion — 0 on pre-fix code (reject was never called).
    assert source.aimd_stats()["decrease_count"] == 1
    assert source.aimd_stats()["consecutive_rejects"] == 1
    # The 429 propagates cleanly (not masked as an AttributeError from core.retry).
    assert caught.value.rate_limited is True
    assert caught.value.status_code == 429
    assert isinstance(caught.value.__cause__, RateLimitError)


def test_rate_limit_equivalent_429_status_also_rejects() -> None:
    """A non-``RateLimitError`` error carrying HTTP 429 is a rate-limit EQUIVALENT."""

    async def _equiv_429(_aid_: ArtifactId) -> ParityObservation:
        raise AsanaError("429 mapped to a bare AsanaError (equivalent)", status_code=429)

    source = _armed_source(_equiv_429)
    with pytest.raises(ParityOutboundError) as caught:
        asyncio.run(source.fetch_all_paced([_aid()]))
    assert source.aimd_stats()["decrease_count"] == 1
    assert caught.value.rate_limited is True
    assert isinstance(caught.value.__cause__, AsanaError)


def test_success_200_does_not_reject() -> None:
    """The other side of the teeth: a 200 succeeds and NEVER shrinks the window."""

    async def _ok(_aid_: ArtifactId) -> ParityObservation:
        return exemplar_one_observation()

    source = _armed_source(_ok)
    results = asyncio.run(source.fetch_all_paced([_aid()]))

    assert len(results) == 1
    assert isinstance(results[0], ParityObservation)
    assert source.aimd_stats()["decrease_count"] == 0  # no reject on a healthy fetch


def test_non_rate_limit_error_does_not_reject() -> None:
    """A non-429 failure (e.g. a 500) must NOT be misread as backpressure."""

    async def _server_error(_aid_: ArtifactId) -> ParityObservation:
        raise AsanaError("500 upstream — not a rate limit", status_code=500)

    source = _armed_source(_server_error)
    with pytest.raises(ParityOutboundError) as caught:
        asyncio.run(source.fetch_all_paced([_aid()]))
    assert source.aimd_stats()["decrease_count"] == 0  # only 429s shrink the window
    assert caught.value.rate_limited is False
    assert caught.value.status_code == 500
    assert isinstance(caught.value.__cause__, AsanaError)
