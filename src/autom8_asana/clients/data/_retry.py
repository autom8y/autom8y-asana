"""Retry callback factory for DataServiceClient endpoints.

Private module providing a factory function that generates the three
callback functions required by _execute_with_retry. Eliminates ~196 LOC
of near-identical boilerplate across 5 endpoint methods.

These functions are NOT part of the public API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from autom8y_http import CircuitBreaker

    from autom8_asana.protocols.log import LogProvider


@dataclass(frozen=True, slots=True)
class RetryCallbacks:
    """Container for the three retry callback functions."""

    on_retry: Callable[[int, int, int | None], Awaitable[None]] | None
    on_timeout_exhausted: Callable[[httpx.TimeoutException, int], Awaitable[None]]
    on_http_error: Callable[[httpx.HTTPError, int], Awaitable[None]]


def build_retry_callbacks(
    *,
    circuit_breaker: CircuitBreaker,
    error_class: type[Exception],
    timeout_message: str,
    http_error_template: str,
    error_kwargs: dict[str, Any],
    log: LogProvider | None = None,
    log_event_retry: str | None = None,
    log_event_fail: str | None = None,
    max_retries: int = 0,
    emit_metric: Callable[[str, float, dict[str, str]], None] | None = None,
    metric_tags: dict[str, str] | None = None,
    extra_log_context: dict[str, Any] | None = None,
    start_time: float | None = None,
) -> RetryCallbacks:
    """Build retry callbacks for _execute_with_retry.

    This factory parameterizes the 7 variation axes identified in the
    decomposition map:
    1. on_retry presence (via log_event_retry: None to skip)
    2. Error class (InsightsServiceError or ExportError)
    3. Error messages (timeout_message, http_error_template with {e})
    4. Error kwargs (request_id=..., office_phone=..., etc.)
    5. Metrics emission (via emit_metric callback)
    6. Elapsed time calculation (via start_time)
    7. Extra log context fields (via extra_log_context)

    Args:
        circuit_breaker: Circuit breaker for recording failures.
        error_class: Exception class to raise on failure.
        timeout_message: Message for timeout errors.
        http_error_template: Message template for HTTP errors (use {e} placeholder).
        error_kwargs: Extra kwargs passed to error_class constructor.
            Should NOT include 'reason'; the factory injects 'reason' per callback.
            These kwargs are also merged into log extras (e.g., request_id).
        log: Logger instance (None to skip logging).
        log_event_retry: Log event name for retries (None to skip on_retry entirely).
        log_event_fail: Log event name for failures (None to skip failure logging).
        max_retries: Max retries value for log extras.
        emit_metric: Metric emission callback (None to skip metrics).
            Signature: (name: str, value: float, tags: dict[str, str]) -> None.
        metric_tags: Tags for metric emission.
        extra_log_context: Extra fields merged into log extras (beyond error_kwargs).
        start_time: Monotonic timestamp for elapsed_ms calculation.
            If None, elapsed_ms is not computed or logged.

    Returns:
        RetryCallbacks dataclass with on_retry, on_timeout_exhausted, on_http_error.
    """
    _extra_log_context = extra_log_context or {}
    _metric_tags = metric_tags or {}

    # Base log fields shared across all callbacks: error_kwargs (e.g. request_id)
    # merged with caller-supplied extra_log_context (e.g. batch_size).
    _base_log_extras: dict[str, Any] = {**error_kwargs, **_extra_log_context}

    # Build on_retry callback (None when log_event_retry is not given)
    on_retry: Callable[[int, int, int | None], Awaitable[None]] | None

    if log_event_retry is not None:

        async def on_retry(  # type: ignore[misc]
            attempt: int, status_code: int, retry_after: int | None
        ) -> None:
            if log:
                extra: dict[str, Any] = {
                    **_base_log_extras,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                }
                if status_code:
                    extra["status_code"] = status_code
                    extra["retry_after"] = retry_after
                else:
                    extra["error_type"] = "TimeoutException"
                    extra["reason"] = "timeout"
                log.warning(log_event_retry, extra=extra)

    else:
        on_retry = None

    async def on_timeout_exhausted(e: httpx.TimeoutException, attempt: int) -> None:
        if start_time is not None:
            elapsed_ms: float | None = (time.monotonic() - start_time) * 1000
        else:
            elapsed_ms = None

        if log and log_event_fail:
            fail_extra: dict[str, Any] = {
                **_base_log_extras,
                "error_type": "TimeoutException",
                "reason": "timeout",
                "attempt": attempt + 1,
            }
            if elapsed_ms is not None:
                fail_extra["duration_ms"] = elapsed_ms
            log.error(log_event_fail, extra=fail_extra)

        if emit_metric is not None and elapsed_ms is not None:
            emit_metric(
                "insights_request_error_total",
                1,
                {**_metric_tags, "error_type": "timeout"},
            )
            emit_metric(
                "insights_request_latency_ms",
                elapsed_ms,
                {**_metric_tags, "status": "error"},
            )

        await circuit_breaker.record_failure(e)
        raise error_class(
            timeout_message,
            **error_kwargs,
            reason="timeout",
        ) from e

    async def on_http_error(e: httpx.HTTPError, attempt: int) -> None:
        if start_time is not None:
            elapsed_ms = (time.monotonic() - start_time) * 1000
        else:
            elapsed_ms = None

        if log and log_event_fail:
            fail_extra = {
                **_base_log_extras,
                "error_type": e.__class__.__name__,
                "reason": "http_error",
                "attempt": attempt + 1,
            }
            if elapsed_ms is not None:
                fail_extra["duration_ms"] = elapsed_ms
            log.error(log_event_fail, extra=fail_extra)

        if emit_metric is not None and elapsed_ms is not None:
            emit_metric(
                "insights_request_error_total",
                1,
                {**_metric_tags, "error_type": "http_error"},
            )
            emit_metric(
                "insights_request_latency_ms",
                elapsed_ms,
                {**_metric_tags, "status": "error"},
            )

        await circuit_breaker.record_failure(e)
        raise error_class(
            http_error_template.format(e=e),
            **error_kwargs,
            reason="http_error",
        ) from e

    return RetryCallbacks(
        on_retry=on_retry,
        on_timeout_exhausted=on_timeout_exhausted,
        on_http_error=on_http_error,
    )
