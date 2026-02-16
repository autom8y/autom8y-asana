"""Bounded-concurrency async gather utility."""

import asyncio
import time
from collections.abc import Coroutine, Iterable
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


async def gather_with_semaphore(
    coros: Iterable[Coroutine],
    *,
    concurrency: int = 10,
    return_exceptions: bool = True,
    label: str = "gather",
) -> list[Any]:
    """Execute coroutines with bounded concurrency.

    Combines a local asyncio.Semaphore with transport-layer AIMD for
    two-level throttling. The semaphore bounds are callsite-local --
    they do NOT bound global thread pool usage.

    Args:
        coros: Unawaited coroutine objects (not tasks, not futures).
              Generators are eagerly consumed.
        concurrency: Maximum concurrent coroutines. Sized per-callsite:
                    cache warming (20), watermarks (10), deltas (5),
                    init actions (4), project enumeration (5).
        return_exceptions: If True, exceptions are returned as results
                          instead of propagating. Default True.
        label: Identifier for structured log output.

    Returns:
        List of results (or exceptions if return_exceptions=True),
        in the same order as the input coroutines.
    """
    tasks = [coro for coro in coros]  # eagerly consume generators
    if not tasks:
        return []

    sem = asyncio.Semaphore(concurrency)

    async def _bounded(coro: Coroutine) -> Any:
        async with sem:
            return await coro

    start = time.perf_counter()
    results = await asyncio.gather(
        *[_bounded(c) for c in tasks],
        return_exceptions=return_exceptions,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000

    succeeded = sum(1 for r in results if not isinstance(r, BaseException))
    failed = len(results) - succeeded

    logger.info(
        f"{label}_completed",
        succeeded=succeeded,
        failed=failed,
        total=len(results),
        elapsed_ms=round(elapsed_ms, 1),
    )

    return list(results)
