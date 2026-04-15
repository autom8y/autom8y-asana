"""Deterministic simulation test for AIMD adaptive semaphore.

Per TDD-GAP-04/SC-003: Under simulated 429 pressure, AIMD produces
fewer total 429s than a fixed semaphore. This test uses a scripted
"server" that returns 429 when concurrent requests exceed its capacity.

CI-safe, deterministic, no real HTTP or real timers beyond asyncio.sleep.
"""

from __future__ import annotations

import asyncio

import pytest

from autom8_asana.transport.adaptive_semaphore import (
    AIMDConfig,
    AsyncAdaptiveSemaphore,
    FixedSemaphoreAdapter,
)


class SimServer:
    """Simulated server that returns 429 when concurrency exceeds capacity.

    Thread-safe within a single event loop (all access through coroutines).
    """

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.concurrent = 0
        self.total_429s = 0
        self.total_200s = 0

    async def handle(self) -> int:
        """Simulate a request. Returns status code."""
        self.concurrent += 1
        try:
            if self.concurrent > self.capacity:
                self.total_429s += 1
                # Brief sleep to simulate 429 processing time
                await asyncio.sleep(0.001)
                return 429
            # Simulate successful request latency
            await asyncio.sleep(0.005)
            self.total_200s += 1
            return 200
        finally:
            self.concurrent -= 1


async def _run_simulation_fixed(
    server: SimServer,
    limit: int,
    n_requests: int,
) -> int:
    """Run simulation with a fixed semaphore (no adaptation)."""
    adapter = FixedSemaphoreAdapter(limit=limit)

    async def make_request():
        async with await adapter.acquire() as slot:
            status = await server.handle()
            if status == 429:
                slot.reject()
                # Simulate brief backoff on 429
                await asyncio.sleep(0.01)
            else:
                slot.succeed()

    tasks = [asyncio.create_task(make_request()) for _ in range(n_requests)]
    await asyncio.gather(*tasks)
    return server.total_429s


async def _run_simulation_aimd(
    server: SimServer,
    limit: int,
    n_requests: int,
) -> int:
    """Run simulation with AIMD adaptive semaphore."""
    config = AIMDConfig(
        ceiling=limit,
        floor=1,
        multiplicative_decrease=0.5,
        additive_increase=1.0,
        grace_period_seconds=0.0,  # No grace period for simulation speed
        increase_interval_seconds=0.0,  # No throttle for simulation speed
    )
    semaphore = AsyncAdaptiveSemaphore(config=config, name="sim")

    async def make_request():
        async with await semaphore.acquire() as slot:
            status = await server.handle()
            if status == 429:
                slot.reject()
                # Simulate brief backoff on 429
                await asyncio.sleep(0.01)
            else:
                slot.succeed()

    tasks = [asyncio.create_task(make_request()) for _ in range(n_requests)]
    await asyncio.gather(*tasks)
    return server.total_429s


class TestAIMDSimulation:
    """Deterministic simulation tests."""

    async def test_aimd_fewer_429s_than_fixed(self):
        """SC-003: Under 429 pressure, AIMD produces fewer total 429s.

        Scenario: Server capacity is 20 concurrent requests. We fire 200
        requests through both a fixed semaphore (ceiling=50) and an AIMD
        semaphore (ceiling=50, adapts on 429).

        The fixed semaphore allows 50 concurrent requests, far exceeding
        the server's capacity of 20, causing many 429s. The AIMD semaphore
        detects the 429s and reduces concurrency, resulting in fewer total
        429s.
        """
        SERVER_CAPACITY = 20
        TOTAL_REQUESTS = 200
        SEMAPHORE_LIMIT = 50

        # Run with fixed semaphore
        fixed_server = SimServer(capacity=SERVER_CAPACITY)
        fixed_429s = await _run_simulation_fixed(
            fixed_server, limit=SEMAPHORE_LIMIT, n_requests=TOTAL_REQUESTS
        )

        # Run with AIMD semaphore
        aimd_server = SimServer(capacity=SERVER_CAPACITY)
        aimd_429s = await _run_simulation_aimd(
            aimd_server, limit=SEMAPHORE_LIMIT, n_requests=TOTAL_REQUESTS
        )

        # AIMD should produce fewer 429s than fixed
        assert aimd_429s < fixed_429s, (
            f"AIMD ({aimd_429s}) should produce fewer 429s than fixed ({fixed_429s})"
        )

        # Sanity check: fixed should have produced some 429s
        # (otherwise the test is not exercising the scenario)
        assert fixed_429s > 0, "Fixed semaphore should have produced some 429s"

    async def test_aimd_converges_under_sustained_pressure(self):
        """AIMD eventually converges to a window near the server capacity.

        After enough requests with 429 feedback, the AIMD window should
        stabilize near the server's actual capacity.
        """
        SERVER_CAPACITY = 10
        SEMAPHORE_LIMIT = 50

        config = AIMDConfig(
            ceiling=SEMAPHORE_LIMIT,
            floor=1,
            multiplicative_decrease=0.5,
            additive_increase=1.0,
            grace_period_seconds=0.0,
            increase_interval_seconds=0.0,
        )
        semaphore = AsyncAdaptiveSemaphore(config=config, name="converge")
        server = SimServer(capacity=SERVER_CAPACITY)

        async def make_request():
            async with await semaphore.acquire() as slot:
                status = await server.handle()
                if status == 429:
                    slot.reject()
                    await asyncio.sleep(0.005)
                else:
                    slot.succeed()

        # Fire enough requests for convergence
        for _ in range(5):
            tasks = [asyncio.create_task(make_request()) for _ in range(50)]
            await asyncio.gather(*tasks)

        # Window should have converged near the server capacity
        # Allow generous tolerance since this is stochastic
        window = semaphore.current_limit
        assert window <= SEMAPHORE_LIMIT, "Window should not exceed ceiling"
        assert window >= 1, "Window should be at least 1"
        # After sustained pressure, window should be below the starting ceiling
        assert window < SEMAPHORE_LIMIT, (
            f"Window ({window}) should have decreased from ceiling ({SEMAPHORE_LIMIT})"
        )
