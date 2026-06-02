"""Shared CPU-bound offload concurrency control for DataFrame builds.

Per TD-001 (thermia cache-architecture ADR-001) and the capacity specification
PDR-002 §4.3: CPU-bound Polars merge work (``pl.concat``) must be moved OFF the
asyncio event-loop thread via ``asyncio.to_thread`` so that ALB health-check
probes and async Asana I/O are not starved during bulk fan-out. Starving the
event loop is what causes ECS task replacement and the ELB-502 cascade (CF-2).

The offload alone is NOT sufficient. ``asyncio.to_thread`` submits to the shared
default ``ThreadPoolExecutor`` (``min(32, cpu_count + 4)``), which is the SAME
executor used by S3 persistence I/O (``dataframes/storage.py:457,525``). At Path 3
peak there are up to 32 concurrent submissions (4 builds x 8 sections;
``build_coordinator.py:131``), which exceeds the default pool on every plausible
Fargate host and can starve the executor — blocking S3 writes for completed
builds. PDR-002 §4.3 therefore requires a dedicated application-level semaphore
capping concurrent CPU-bound submissions at ``max_concurrent_builds`` (= 4).

This module is the single sizing authority. ``run_cpu_bound`` couples the
semaphore acquisition and the ``to_thread`` offload into one indivisible
operation, so a call site cannot offload CPU work without passing through the
gate. The semaphore is load-bearing by construction: removing it (or calling
``asyncio.to_thread`` directly at a merge site) re-introduces the thread-pool /
S3-persistence starvation that PDR-002 was written to prevent.

The semaphore acquire is async and yields to the event loop while waiting, so
gating never blocks the loop — health-check probes remain serviceable even when
all CPU slots are in use.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

from autom8_asana.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

# Module-level singletons, lazily initialized so the Semaphore binds to the
# running event loop on first use (Python 3.12: Semaphore does not capture the
# loop at construction). A single shared instance is the sizing authority for
# ALL CPU-bound offload across the dataframes package.
_cpu_thread_semaphore: asyncio.Semaphore | None = None
_configured_concurrency: int | None = None


def _resolve_concurrency() -> int:
    """Resolve the configured CPU-thread concurrency (PDR-002 §4.3 sizing)."""
    return get_settings().cache.cpu_thread_concurrency


def get_cpu_thread_semaphore() -> asyncio.Semaphore:
    """Return the process-wide CPU-bound offload semaphore.

    Lazily constructs the semaphore on first call using the configured
    ``cpu_thread_concurrency`` (default 4 = ``max_concurrent_builds``). The same
    instance is returned thereafter so every CPU-bound offload across the package
    shares one gate. Exposed for introspection and adversarial tests that assert
    the gate is load-bearing.
    """
    global _cpu_thread_semaphore, _configured_concurrency
    if _cpu_thread_semaphore is None:
        _configured_concurrency = _resolve_concurrency()
        _cpu_thread_semaphore = asyncio.Semaphore(_configured_concurrency)
    return _cpu_thread_semaphore


def reset_cpu_thread_semaphore() -> None:
    """Reset the cached semaphore (test-only seam).

    Forces re-resolution of ``cpu_thread_concurrency`` on the next
    ``get_cpu_thread_semaphore`` call. Used by tests that exercise different
    concurrency limits; never call from production code paths.
    """
    global _cpu_thread_semaphore, _configured_concurrency
    _cpu_thread_semaphore = None
    _configured_concurrency = None


async def run_cpu_bound(
    func: Callable[..., T],
    /,
    *args: object,
    **kwargs: object,
) -> T:
    """Run a CPU-bound callable off the event loop, gated by the shared semaphore.

    This is the ONLY sanctioned path for offloading CPU-bound Polars work
    (``pl.concat``) per TD-001. It performs two operations as one indivisible
    unit:

    1. Acquire the shared CPU-thread semaphore (async; yields to the loop while
       waiting, so health-check probes stay serviceable).
    2. Submit ``func`` to the default thread pool via ``asyncio.to_thread``,
       freeing the event-loop thread for the duration of the CPU work.

    Coupling acquisition and offload here guarantees that no merge/checkpoint
    site can offload without the cap — the semaphore is load-bearing by
    construction (PDR-002 §4.3).

    Args:
        func: A synchronous, CPU-bound callable (e.g. ``polars.concat``).
        *args: Positional arguments forwarded to ``func``.
        **kwargs: Keyword arguments forwarded to ``func``.

    Returns:
        The return value of ``func``.
    """
    semaphore = get_cpu_thread_semaphore()
    async with semaphore:
        return await asyncio.to_thread(func, *args, **kwargs)
