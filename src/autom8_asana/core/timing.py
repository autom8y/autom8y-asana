"""Timing utilities for performance measurement."""

import time


def elapsed_ms(start_time: float) -> float:
    """Calculate elapsed time in milliseconds from a perf_counter start.

    Args:
        start_time: Start time from time.perf_counter().

    Returns:
        Elapsed time in milliseconds.
    """
    return (time.perf_counter() - start_time) * 1000
