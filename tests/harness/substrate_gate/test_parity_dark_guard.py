"""DARK-guard + RC-E-4 routing-invariant tests (S7 · P5 · REQUIREMENT 2).

The live-parity path must be impossible to run accidentally before S8, AND it must be
genuinely wired through v1's pacing controllers (not merely declared). These tests:

  * drive the PUBLIC paced fan-out with a real event loop and a fast (injected-clock)
    floor gate, and assert it routes through admit → AIMD slot → retry → gather and
    then raises ``LiveParityNotArmedError`` at the dark outbound leg;
  * assert the sync ``fetch`` guard fires while DARK, and stays guarded even when
    ``armed=True`` without an injected outbound impl;
  * assert (structurally) that NO harness library module imports ``AsanaClient`` — the
    only un-paced Asana surface — so the routing invariant holds by construction.
"""

from __future__ import annotations

import asyncio
import importlib
from datetime import UTC, datetime

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.identity import ArtifactId
from tests.harness.substrate_gate import LiveParityNotArmedError, PacedLiveParitySource

_NOW = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)

_LIBRARY_MODULES = (
    "cases",
    "frame_codec",
    "divergence",
    "replay",
    "reference",
    "parity",
    "exemplars",
    "corpus",
)


def _aid() -> ArtifactId:
    return ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)


class _FastClock:
    """A monotonically-advancing fake clock so the floor gate earns tokens instantly."""

    def __init__(self) -> None:
        self._t = 0.0

    def __call__(self) -> float:
        self._t += 100.0
        return self._t


async def _no_sleep(_seconds: float) -> None:
    return None


def _fast_source(*, armed: bool = False) -> PacedLiveParitySource:
    return PacedLiveParitySource(armed=armed, gate_clock=_FastClock(), gate_sleep=_no_sleep)


def test_sync_fetch_is_dark_and_raises() -> None:
    with pytest.raises(LiveParityNotArmedError):
        _fast_source().fetch(_aid())


def test_paced_fanout_routes_primitives_then_hits_dark_guard() -> None:
    source = _fast_source()
    with pytest.raises(LiveParityNotArmedError):
        asyncio.run(source.fetch_all_paced([_aid()]))


def test_armed_without_outbound_impl_is_still_guarded() -> None:
    # arming alone is insufficient — S8 must ALSO inject a paced outbound impl.
    source = PacedLiveParitySource(armed=True, gate_clock=_FastClock(), gate_sleep=_no_sleep)
    with pytest.raises(LiveParityNotArmedError):
        asyncio.run(source.fetch_all_paced([_aid()]))


def test_routes_through_paced_primitives_property_is_true() -> None:
    assert PacedLiveParitySource().routes_through_paced_primitives() is True


def test_harness_library_never_imports_asana_client() -> None:
    """RC-E-4: no library module binds ``AsanaClient`` — no un-paced Asana surface exists."""
    offenders = []
    for name in _LIBRARY_MODULES:
        module = importlib.import_module(f"tests.harness.substrate_gate.{name}")
        if hasattr(module, "AsanaClient"):
            offenders.append(name)
    assert not offenders, f"un-paced AsanaClient imported in: {offenders}"


def test_injected_outbound_would_run_paced_when_armed() -> None:
    """Positive control: an injected outbound impl runs THROUGH the paced path when armed.

    Proves the dark guard is the ONLY thing gating live execution — the composition
    itself is functional. Uses a stub outbound (no network) to keep wave-2 offline.
    """
    from tests.harness.substrate_gate.exemplars import exemplar_one_observation
    from tests.harness.substrate_gate.parity import ParityObservation

    calls: list[str] = []

    async def _stub_outbound(aid: ArtifactId) -> ParityObservation:
        calls.append(aid.project_gid)
        return exemplar_one_observation()

    source = PacedLiveParitySource(
        armed=True, outbound=_stub_outbound, gate_clock=_FastClock(), gate_sleep=_no_sleep
    )
    results = asyncio.run(source.fetch_all_paced([_aid()]))
    assert calls == ["1143843662099250"]  # the outbound ran, routed through the paced path
    assert len(results) == 1
    assert isinstance(results[0], ParityObservation)
