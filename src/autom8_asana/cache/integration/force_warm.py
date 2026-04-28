"""Coalescer-routed force-warm surface for the cache_warmer Lambda.

Per HANDOFF §3 LD-P3-2 (FORBIDDEN: direct Lambda invoke from CLI/elsewhere)
and ADR-003 (HYBRID L1 invalidation policy):

- Force-warm requests MUST route through ``DataFrameCacheCoalescer`` to
  prevent in-process thundering herd. The coalescer dedup key is
  ``forcewarm:{project_gid}:{entity_type|*}``. The ECS-process-local
  ``DataFrameCacheCoalescer`` covers the in-process axis; the Lambda
  idempotency-key window covers the cross-process axis (P3 §5.2).
- The coalescer dedup key is namespaced under ``forcewarm:`` so it does NOT
  collide with the existing build-lock key ``{entity_type}:{project_gid}``
  used by the SWR rebuild path (DataFrameCache._build_key). A force-warm
  request and a concurrent SWR rebuild for the same key are ALLOWED to
  proceed in parallel.
- Sync mode (``--wait`` flag, ``InvocationType="RequestResponse"``):
  invalidates L1 MemoryTier on Lambda success (ADR-003 HYBRID branch).
- Async mode (default, ``InvocationType="Event"``): does NOT invalidate L1;
  next SWR rebuild trigger picks up freshly-warmed L2 within the SWR window.

The Lambda function name resolves from environment variable
``CACHE_WARMER_LAMBDA_ARN`` (existing fleet convention; see
``src/autom8_asana/api/routes/admin.py:211`` and
``src/autom8_asana/api/preload/progressive.py:548``). Documenting in
``--help`` output is the responsibility of the CLI surface (Batch-A).

This module is the only sanctioned channel between the CLI surface and the
cache_warmer Lambda; AP-3 (parquet not invalidated on task mutation) is NOT
closed by this module — task-mutation invalidation remains the unresolved
named risk per P2 §7.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.cache.integration.dataframe_cache import DataFrameCache

logger = get_logger(__name__)


#: Environment variable carrying the cache_warmer Lambda ARN or function name.
#: Pre-existing fleet convention used by api/routes/admin.py and
#: api/preload/progressive.py.
LAMBDA_ARN_ENV_VAR: str = "CACHE_WARMER_LAMBDA_ARN"

#: Coalescer dedup-key prefix for force-warm requests. Distinct from the
#: SWR build-lock key ({entity_type}:{project_gid}) so the two surfaces
#: do not steal locks from each other.
COALESCER_KEY_PREFIX: str = "forcewarm:"

#: Default wait timeout for the in-process coalescer wait when a force-warm
#: is already in flight. Bounded by the coalescer's max_wait_seconds (60s)
#: but kept lower here for CLI responsiveness.
DEFAULT_COALESCER_WAIT_SECONDS: float = 30.0


class ForceWarmError(RuntimeError):
    """Raised when a force-warm operation fails non-recoverably.

    The ``kind`` attribute is one of: 'config', 'invoke', 'lambda', 'timeout'.
    """

    KIND_CONFIG = "config"
    KIND_INVOKE = "invoke"
    KIND_LAMBDA = "lambda"
    KIND_TIMEOUT = "timeout"

    def __init__(self, kind: str, message: str) -> None:
        self.kind = kind
        super().__init__(f"[{kind}] {message}")


@dataclass(frozen=True)
class ForceWarmResult:
    """Outcome metadata for a force-warm invocation.

    Attributes:
        invoked: Whether a Lambda invoke was actually issued (False when the
            request was deduped by the coalescer to an in-flight request).
        invocation_type: One of {"Event", "RequestResponse"}.
        deduped: Whether this request was coalesced onto an existing
            in-flight force-warm.
        lambda_status_code: HTTP-style status from the Lambda response
            (None for async / Event mode; 200..299 = success in sync mode).
        lambda_response_payload: Decoded payload (sync mode only).
        l1_invalidated: Whether the L1 MemoryTier was invalidated post-warm.
        latency_seconds: End-to-end latency observed by the caller (CLI
            parse time → return). Per FLAG-1, this includes coalescer wait;
            it does NOT include the freshness-recheck round-trip (the CLI
            caller is responsible for that final probe).
        function_arn: Resolved Lambda function ARN or name.
        project_gid: Project GID the warm targeted.
        entity_types: Entity types passed in the Lambda payload.
        coalescer_key: The coalescer dedup key used.
        error: Populated if the warm failed (mode-specific shape).
    """

    invoked: bool
    invocation_type: str
    deduped: bool
    latency_seconds: float
    function_arn: str
    project_gid: str
    entity_types: tuple[str, ...]
    coalescer_key: str
    lambda_status_code: int | None = None
    lambda_response_payload: dict[str, Any] | None = None
    l1_invalidated: bool = False
    error: str | None = None


def resolve_lambda_arn(env: dict[str, str] | None = None) -> str:
    """Resolve the cache_warmer Lambda ARN/name from the environment.

    Args:
        env: Optional environment mapping (defaults to ``os.environ``).
            Injection point for tests.

    Returns:
        The Lambda ARN or function name string.

    Raises:
        ForceWarmError: kind="config" if CACHE_WARMER_LAMBDA_ARN is unset
            or empty.
    """
    source = env if env is not None else dict(os.environ)
    arn = source.get(LAMBDA_ARN_ENV_VAR, "").strip()
    if not arn:
        raise ForceWarmError(
            ForceWarmError.KIND_CONFIG,
            f"environment variable {LAMBDA_ARN_ENV_VAR!r} is unset; "
            "cannot resolve cache_warmer Lambda function. Document in CLI "
            "--help that this env var is required for --force-warm.",
        )
    return arn


def build_coalescer_key(project_gid: str, entity_types: tuple[str, ...]) -> str:
    """Build the coalescer dedup key for a force-warm request.

    The key namespacing prevents collision with SWR rebuild build-lock keys
    (which use ``{entity_type}:{project_gid}``).

    Two force-warm requests with the same (project_gid, entity_types) tuple
    coalesce; differing entity_types tuples produce distinct keys.
    """
    et_part = ",".join(sorted(entity_types)) if entity_types else "*"
    return f"{COALESCER_KEY_PREFIX}{project_gid}:{et_part}"


async def force_warm(
    *,
    cache: DataFrameCache,
    project_gid: str,
    entity_types: tuple[str, ...] = (),
    wait: bool = False,
    invocation_type: str | None = None,
    lambda_client: Any = None,
    env: dict[str, str] | None = None,
    coalescer_wait_seconds: float = DEFAULT_COALESCER_WAIT_SECONDS,
) -> ForceWarmResult:
    """Coalescer-routed force-warm of the cache_warmer Lambda.

    Per HANDOFF §3 LD-P3-2: this is the SOLE sanctioned channel between
    callers (CLI surface, internal admin paths) and direct Lambda invoke.
    Direct ``boto3.client('lambda').invoke(...)`` adjacent to caller code
    is FORBIDDEN.

    Args:
        cache: The shared ``DataFrameCache`` instance — its coalescer is
            consulted for in-process dedup; on sync success its ``invalidate``
            method is called for L1 HYBRID invalidation (ADR-003).
        project_gid: Asana project GID the warm targets.
        entity_types: Optional tuple of entity types (e.g. ("unit", "offer"));
            empty tuple means "all entity types" — the Lambda payload omits
            ``entity_types`` to let the warmer enumerate them.
        wait: If True, invokes Lambda synchronously
            (``InvocationType="RequestResponse"``) and invalidates L1 on
            success per ADR-003 HYBRID. If False (default), invokes
            asynchronously and skips L1 invalidation (operator accepts SWR
            rebuild lag).
        invocation_type: Optional explicit override for invocation type.
            When None, derived from ``wait`` (False → "Event"; True →
            "RequestResponse"). Useful for tests that want to drive both
            paths without flipping ``wait``.
        lambda_client: Optional boto3 Lambda client (for tests / DI). When
            None, a default client is constructed via ``boto3.client('lambda')``.
        env: Optional environment override (for tests).
        coalescer_wait_seconds: Maximum time to wait for an existing
            in-flight force-warm to complete when this request is deduped.

    Returns:
        ForceWarmResult capturing the outcome metadata.

    Raises:
        ForceWarmError: kind="config" if Lambda ARN is unresolved;
            kind="invoke" / "lambda" / "timeout" on Lambda errors.
    """
    start_time = time.perf_counter()

    if invocation_type is None:
        invocation_type = "RequestResponse" if wait else "Event"

    function_arn = resolve_lambda_arn(env)
    coalescer_key = build_coalescer_key(project_gid, entity_types)

    logger.info(
        "force_warm_request",
        extra={
            "project_gid": project_gid,
            "entity_types": list(entity_types),
            "wait": wait,
            "invocation_type": invocation_type,
            "function_arn": function_arn,
            "coalescer_key": coalescer_key,
        },
    )

    # Stamp 1: try to acquire coalescer dedup lock. The cache.coalescer is
    # the SAME instance backing SWR builds; we use a namespaced key so we
    # do not steal the build-lock for this entity_type.
    coalescer = cache.coalescer
    acquired = await coalescer.try_acquire_async(coalescer_key)

    if not acquired:
        # Another force-warm is in flight for the same target — coalesce.
        logger.info(
            "force_warm_coalesced",
            extra={
                "project_gid": project_gid,
                "coalescer_key": coalescer_key,
            },
        )
        success = await coalescer.wait_async(coalescer_key, coalescer_wait_seconds)
        latency = time.perf_counter() - start_time

        if not success:
            return ForceWarmResult(
                invoked=False,
                invocation_type=invocation_type,
                deduped=True,
                latency_seconds=latency,
                function_arn=function_arn,
                project_gid=project_gid,
                entity_types=entity_types,
                coalescer_key=coalescer_key,
                error="coalesced wait failed (timeout or upstream failure)",
            )
        return ForceWarmResult(
            invoked=False,
            invocation_type=invocation_type,
            deduped=True,
            latency_seconds=latency,
            function_arn=function_arn,
            project_gid=project_gid,
            entity_types=entity_types,
            coalescer_key=coalescer_key,
        )

    # We hold the lock — perform the actual Lambda invoke.
    success = False
    status_code: int | None = None
    payload: dict[str, Any] | None = None
    error_str: str | None = None
    invalidated = False
    invoked = False

    try:
        client = lambda_client if lambda_client is not None else _make_lambda_client()
        body: dict[str, Any] = {
            "project_gid": project_gid,
            "strict": False,
            "resume_from_checkpoint": False,
        }
        if entity_types:
            body["entity_types"] = list(entity_types)
        invoke_kwargs: dict[str, Any] = {
            "FunctionName": function_arn,
            "InvocationType": invocation_type,
            "Payload": json.dumps(body).encode("utf-8"),
        }

        try:
            response = client.invoke(**invoke_kwargs)
        except Exception as exc:  # BROAD-CATCH: degrade -- boto3 surface variability
            logger.exception(
                "force_warm_invoke_failed",
                extra={
                    "project_gid": project_gid,
                    "function_arn": function_arn,
                    "invocation_type": invocation_type,
                    "error_type": type(exc).__name__,
                },
            )
            raise ForceWarmError(
                ForceWarmError.KIND_INVOKE,
                f"Lambda invoke failed: {type(exc).__name__}: {exc}",
            ) from exc

        invoked = True
        status_code = response.get("StatusCode")

        # Async (Event) success: 202 Accepted; no payload to inspect.
        if invocation_type == "Event":
            success = status_code is not None and 200 <= status_code < 300
            if not success:
                error_str = f"async invoke returned StatusCode={status_code}"
                logger.warning(
                    "force_warm_async_invoke_unexpected_status",
                    extra={
                        "project_gid": project_gid,
                        "status_code": status_code,
                    },
                )
        else:
            # Sync (RequestResponse) — inspect payload for FunctionError.
            success, status_code, payload, error_str = _interpret_sync_response(response)

            # ADR-003 HYBRID: on sync success invalidate L1 MemoryTier.
            if success:
                _invalidate_l1(cache, project_gid, entity_types)
                invalidated = True

    finally:
        # Always release the coalescer lock — never leave it dangling.
        try:
            await coalescer.release_async(coalescer_key, success=success)
        except (
            Exception
        ) as exc:  # BROAD-CATCH: isolation -- coalescer release errors must not crash caller
            logger.exception(
                "force_warm_coalescer_release_failed",
                extra={
                    "project_gid": project_gid,
                    "coalescer_key": coalescer_key,
                    "error_type": type(exc).__name__,
                },
            )

    latency = time.perf_counter() - start_time

    logger.info(
        "force_warm_complete",
        extra={
            "project_gid": project_gid,
            "invocation_type": invocation_type,
            "success": success,
            "invoked": invoked,
            "status_code": status_code,
            "latency_seconds": round(latency, 4),
            "l1_invalidated": invalidated,
        },
    )

    if not success and invocation_type == "RequestResponse":
        # Sync mode: surface lambda failures to caller as exception so the
        # CLI can map to non-zero exit code. Async mode is fire-and-forget
        # by design — non-2xx status is logged but not raised.
        raise ForceWarmError(
            ForceWarmError.KIND_LAMBDA,
            error_str or "Lambda RequestResponse invocation failed",
        )

    return ForceWarmResult(
        invoked=invoked,
        invocation_type=invocation_type,
        deduped=False,
        latency_seconds=latency,
        function_arn=function_arn,
        project_gid=project_gid,
        entity_types=entity_types,
        coalescer_key=coalescer_key,
        lambda_status_code=status_code,
        lambda_response_payload=payload,
        l1_invalidated=invalidated,
        error=error_str,
    )


def _make_lambda_client() -> Any:
    """Construct a default boto3 Lambda client.

    Isolated as a tiny seam so tests can monkeypatch the import surface
    without instantiating real boto3.
    """
    import boto3

    return boto3.client("lambda")


def _interpret_sync_response(
    response: Any,
) -> tuple[bool, int | None, dict[str, Any] | None, str | None]:
    """Interpret a sync-mode Lambda response.

    Returns:
        Tuple of (success, status_code, payload, error_str).
    """
    status_code = response.get("StatusCode")
    function_error = response.get("FunctionError")
    payload: dict[str, Any] | None = None

    body_handle = response.get("Payload")
    if body_handle is not None:
        try:
            raw = body_handle.read() if hasattr(body_handle, "read") else body_handle
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    payload = {"_raw": payload}
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as exc:
            logger.warning(
                "force_warm_payload_parse_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )

    if function_error:
        return (
            False,
            status_code,
            payload,
            f"Lambda FunctionError={function_error}; payload={payload!r}",
        )
    if status_code is None or not (200 <= status_code < 300):
        return (
            False,
            status_code,
            payload,
            f"sync invoke returned StatusCode={status_code}",
        )
    # Inspect payload for application-level success flag if present.
    if isinstance(payload, dict):
        body = payload.get("body")
        if isinstance(body, str):
            try:
                body_obj = json.loads(body)
            except json.JSONDecodeError:
                body_obj = None
            if isinstance(body_obj, dict) and "success" in body_obj and not body_obj["success"]:
                return (
                    False,
                    status_code,
                    payload,
                    f"Lambda body.success=False: {body_obj!r}",
                )
        elif isinstance(body, dict) and "success" in body and not body["success"]:
            return (
                False,
                status_code,
                payload,
                f"Lambda body.success=False: {body!r}",
            )
    return True, status_code, payload, None


def _invalidate_l1(
    cache: DataFrameCache,
    project_gid: str,
    entity_types: tuple[str, ...],
) -> None:
    """Invalidate L1 MemoryTier per ADR-003 HYBRID branch.

    When ``entity_types`` is empty, invalidates all known entity types for
    the project (matches the Lambda warmer's "warm everything" semantic).
    """
    try:
        if entity_types:
            for et in entity_types:
                cache.invalidate(project_gid=project_gid, entity_type=et)
        else:
            cache.invalidate_project(project_gid=project_gid)
    except (
        Exception
    ) as exc:  # BROAD-CATCH: isolation -- L1 invalidation must not undo successful warm
        logger.exception(
            "force_warm_l1_invalidation_failed",
            extra={
                "project_gid": project_gid,
                "entity_types": list(entity_types),
                "error_type": type(exc).__name__,
            },
        )
        raise
