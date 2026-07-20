"""``asana_mcp.observability`` — sprint-4 observability + guardrails overlay.

REFERENCE-POSTURE PROTOTYPE (charter §5.3 throwaway; NOT production code). Implements
the sprint-4 half of FROZEN mount-seam v1 item 3 and CONSUMES the landed seam
contract ``autom8y-asana/.sos/wip/asana-mcp-v1.s4-seam-contract.md`` (values +
conformance checklist).

FROZEN SEAM (signature unchanged; divergence flagged, never silently patched):

    def instrument(mcp: FastMCP, settings: Settings) -> FastMCP   # idempotent

Per-tool-execution wrap (mount-seam item 3; contract §3/§4):
  1. gen_ai.* span (+ com.autom8y.mcp.* attrs)                 — contract §3.2 / C5
  2. traceparent propagation onto ctx.http calls              — contract §3.3 / C4
  3. outermost timeout guard, values from asana_mcp.timeouts  — contract §1 / R2
  4. honesty-field passthrough assertion (4 native fields)    — contract §4.4 / C6
  5. MCP-side rate cap, refuse MCP_RATE_BUDGET_EXHAUSTED       — contract §2 / R3
     (with retry_after, NEVER unbounded queueing)

Plus the declared failure postures (contract §4): typed cold-frame 503 mapping
(never auth-shaped), satellite /ready fail-closed refusal, inbound-JWKS posture.

TIMEOUT SoT: all timeout constants live in ``asana_mcp.timeouts`` (checklist item 7).
This module reads them; it defines NO timeout constant of its own.

IMPORT-SAFETY (contract §4.2 / checklist item 3): ``from __future__ import
annotations`` + lazy OTel import + call-time-only env reads (``*.from_env``). Both
``asana_mcp.observability`` and ``asana_mcp.timeouts`` import with zero
settings/IO/network. Guards INCIDENT 2026-04-28 (config.py:919-933, SVR-R6).

ZERO domain-SDK coupling (constraint 5 / checklist item 14): NEVER imports
``autom8_asana`` and makes ZERO direct Asana calls. Operates on the duck-typed
``ctx.http`` handed in by the sprint-2 skeleton.

--- DELIBERATE SHORTCUTS / PRODUCTION GAPS (honest ledger) --------------------
S1 (CONTRACT VALUES WIRED): timeout + budget defaults now carry the contract's
   §1.2/§2.2 values (no longer placeholders). The only unresolved seam number is
   the live ALB idle timeout (contract UV-P-1, 60s floor used) — safe under 60 or
   120.
S2 (FASTMCP REGISTRY SEAM): ``_iter_tool_handles`` duck-types FastMCP's tool
   registry because the FastMCP pin is deferred (frame UV-P-1) and s2's skeleton is
   unlanded. The CORE wrapper is fully tested; instrument() wiring is tested against
   the local harness. s2 wires the real middleware/registry API at pin time.
S3 (TRACEPARENT PER-REQUEST): ``propagate_traceparent`` injects into a carrier the
   caller applies. Production must wire HTTPXClientInstrumentor onto ctx.http
   (contract §3.3) so injection is per-request; injecting client default headers
   would leak a stale traceparent. Documented, not solved here.
S4 (RATE CAP BOUNDS THE INDUCER): the MCP makes zero Asana calls; its cap bounds
   the INDUCER (tool executions that can trigger satellite build fan-out), not PAT
   consumption directly. Warmers/API cannot be starved by construction — the cap
   is a ceiling on the new consumer only (contract §2.2 mechanism honesty).
S5 (NO PRODUCTION ERROR PLUMBING): refusals/mapped errors are plain dataclasses,
   not FastMCP/JSON-RPC error envelopes. s2/s6 adapt to the wire shape.
S6 (POSTURES ARE PURE PREDICATES): readiness/JWKS postures are pure decision
   functions the skeleton calls with real probe results; the actual /ready proxy
   call and JWKS validation live in s2's ctx.readiness and the auth dependency.
------------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio
import functools
import os
import re
import threading
import time
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from asana_mcp.timeouts import (
    ALB_IDLE_TIMEOUT_FLOOR_S,
    TimeoutConfig,
    validate_timeout_config,
)

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at runtime
    from fastmcp import FastMCP  # sprint-2 dependency; NOT installed at s4 time

    from asana_mcp.skeleton import Settings  # s2-owned

__all__ = [
    "NATIVE_HONESTY_FIELDS",
    "ObservabilitySettings",
    "BudgetPartition",
    "RateCap",
    "MappedError",
    "BudgetPartitionError",
    "RateCapExceeded",
    "HonestySuppressionError",
    "AuthShapedError",
    "validate_partition",
    "assert_honesty_passthrough",
    "assert_never_auth_shaped",
    "map_upstream_status",
    "readiness_refusal",
    "jwks_posture",
    "propagate_traceparent",
    "tool_span",
    "instrument_tool",
    "instrument",
]

# --- honesty fields (contract §4.4; verified verbatim at query/models.py HEAD) --
#: All FOUR live native honesty fields (contract §4.4 DELTA: slate named three; the
#: live surface carries four — honest_contract_complete (models.py:451) and
#: contract_complete (models.py:489) are distinct siblings, different retry
#: semantics). SVR receipt: stale_served L436, honest_contract_complete L451,
#: honest_empty L470, contract_complete L489.
NATIVE_HONESTY_FIELDS: tuple[str, ...] = (
    "stale_served",
    "honest_empty",
    "contract_complete",
    "honest_contract_complete",
)

# --- span attribute names (contract §3.2) -------------------------------------
GEN_AI_OPERATION = "gen_ai.operation.name"
GEN_AI_TOOL_NAME = "gen_ai.tool.name"
GEN_AI_TOOL_TYPE = "gen_ai.tool.type"
GEN_AI_TOOL_ARGS = "gen_ai.tool.call.arguments"
GEN_AI_TOOL_RESULT = "gen_ai.tool.call.result"
ATTR_SATELLITE = "com.autom8y.mcp.satellite"
ATTR_TOOL_NAME = "com.autom8y.mcp.tool.name"
ATTR_HONESTY_PREFIX = "com.autom8y.mcp.honesty."
ATTR_REFUSAL_CAUSE = "com.autom8y.mcp.refusal.cause"
ATTR_BUDGET_CLASS = "com.autom8y.mcp.budget.class"

_SATELLITE = "asana"
ENV_CAPTURE_CONTENT = "ASANA_MCP_OTEL_CAPTURE_CONTENT"

# --- refusal / error codes (contract §2.3, §4.3, §4.1) ------------------------
CODE_RATE_BUDGET = "MCP_RATE_BUDGET_EXHAUSTED"
CODE_UPSTREAM_TIMEOUT = "MCP_UPSTREAM_TIMEOUT"
CODE_JWKS_UNAVAILABLE = "AUTH_JWKS_UNAVAILABLE"
# Wire error-code constant (contract §4.1), not a credential — S105 false-positive on the name.
CODE_TOKEN_INVALID = "AUTH_TOKEN_INVALID"  # noqa: S105
CODE_NOT_READY = "MCP_SATELLITE_NOT_READY"

#: FORBIDDEN vocabulary on any 5xx/timeout/cold-frame path (contract §4.3).
_AUTH_SHAPED = re.compile(r"auth|unauthoriz|forbidden|credential", re.IGNORECASE)

# --- budget partition defaults + env (contract §2.2) --------------------------
PAT_TOTAL_RPM_DEFAULT = 1500.0
RATE_RPS_DEFAULT = 2.0
RATE_BURST_DEFAULT = 10.0
RATE_MAX_WAIT_DEFAULT_S = 2.0
SHARE_WARMERS_DEFAULT = 0.60
SHARE_API_DEFAULT = 0.32
SHARE_MCP_DEFAULT = 0.08

ENV_RATE_RPS = "ASANA_MCP_RATE_RPS"
ENV_RATE_BURST = "ASANA_MCP_RATE_BURST"
ENV_RATE_MAX_WAIT = "ASANA_MCP_RATE_MAX_WAIT_S"
ENV_SHARE_WARMERS = "ASANA_MCP_PAT_SHARE_WARMERS"
ENV_SHARE_API = "ASANA_MCP_PAT_SHARE_API"
ENV_SHARE_MCP = "ASANA_MCP_PAT_SHARE_MCP"
ENV_PAT_TOTAL_RPM = "ASANA_MCP_PAT_TOTAL_RPM"

_EPS = 1e-9

_INSTRUMENTED_ATTR = "_asana_mcp_instrumented"
_WRAPPED_ATTR = "_asana_mcp_obs_wrapped"


# ---------------------------------------------------------------------------
# Exceptions — all fail-loud; guardrails REFUSE, never silently degrade
# ---------------------------------------------------------------------------


class BudgetPartitionError(ValueError):
    """The static PAT budget partition oversubscribes / is inconsistent (B4)."""


class HonestySuppressionError(AssertionError):
    """A native honesty field was dropped or flipped to a reassuring value (C6)."""


class AuthShapedError(AssertionError):
    """A 5xx/timeout/cold-frame path was rendered auth-shaped (contract §4.3)."""


@dataclass(frozen=True)
class RateCapExceeded(Exception):
    """MCP-side rate cap hit — typed refusal, retry_after, NEVER queue (R3)."""

    retry_after_s: float
    code: str = CODE_RATE_BUDGET
    consumer_class: str = "mcp"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return (
            f"{self.code}: asana-mcp rate cap exceeded for '{self.consumer_class}'; "
            f"retry after {self.retry_after_s:.3f}s (refused, not queued)"
        )


# ---------------------------------------------------------------------------
# Env helpers (call-time only; never at import — C9a)
# ---------------------------------------------------------------------------


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"env {name}={raw!r} is not a float") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Budget partition (contract §2) + MCP-side rate cap (R3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BudgetPartition:
    """Static partition of the shared Asana PAT across warmers/API/MCP (contract §2).

    The share vars are the STATIC PARTITION OF RECORD (accounting + invariant);
    the RPS/BURST cap is the ENFORCEMENT LEVER the sidecar actually owns.
    """

    total_rpm: float = PAT_TOTAL_RPM_DEFAULT
    share_warmers: float = SHARE_WARMERS_DEFAULT
    share_api: float = SHARE_API_DEFAULT
    share_mcp: float = SHARE_MCP_DEFAULT
    rate_rps: float = RATE_RPS_DEFAULT
    rate_burst: float = RATE_BURST_DEFAULT
    max_wait_s: float = RATE_MAX_WAIT_DEFAULT_S

    @classmethod
    def from_env(cls) -> BudgetPartition:
        return cls(
            total_rpm=_env_float(ENV_PAT_TOTAL_RPM, PAT_TOTAL_RPM_DEFAULT),
            share_warmers=_env_float(ENV_SHARE_WARMERS, SHARE_WARMERS_DEFAULT),
            share_api=_env_float(ENV_SHARE_API, SHARE_API_DEFAULT),
            share_mcp=_env_float(ENV_SHARE_MCP, SHARE_MCP_DEFAULT),
            rate_rps=_env_float(ENV_RATE_RPS, RATE_RPS_DEFAULT),
            rate_burst=_env_float(ENV_RATE_BURST, RATE_BURST_DEFAULT),
            max_wait_s=_env_float(ENV_RATE_MAX_WAIT, RATE_MAX_WAIT_DEFAULT_S),
        )

    def sum_shares(self) -> float:
        return self.share_warmers + self.share_api + self.share_mcp


def validate_partition(p: BudgetPartition) -> None:
    """Fail loud on partition inconsistency (contract §2.2 config-time invariants).

    * ``SHARE_WARMERS + SHARE_API + SHARE_MCP <= 1.0``
    * ``RATE_RPS * 60 <= SHARE_MCP * PAT_TOTAL_RPM``  (the RPS cap is consistent
      with the MCP's declared share of the shared bucket)
    """
    if p.total_rpm <= 0:
        raise BudgetPartitionError(f"PAT total_rpm must be > 0, got {p.total_rpm}")
    for name in ("share_warmers", "share_api", "share_mcp", "rate_rps", "rate_burst"):
        val = getattr(p, name)
        if val < 0:
            raise BudgetPartitionError(f"{name} must be >= 0, got {val}")
    if p.sum_shares() > 1.0 + _EPS:
        raise BudgetPartitionError(
            "PAT share partition oversubscribes the shared token (R3): "
            f"warmers({p.share_warmers}) + api({p.share_api}) + mcp({p.share_mcp}) "
            f"= {p.sum_shares()} > 1.0"
        )
    mcp_rpm_ceiling = p.share_mcp * p.total_rpm
    if p.rate_rps * 60.0 > mcp_rpm_ceiling + _EPS:
        raise BudgetPartitionError(
            "rate cap inconsistent with the MCP share (R3): RATE_RPS*60 = "
            f"{p.rate_rps * 60.0} > SHARE_MCP*TOTAL = {mcp_rpm_ceiling}"
        )


class RateCap:
    """A client-side token bucket — REFUSE when empty, never queue (R3).

    ``try_acquire`` is non-blocking: ``(True, 0.0)`` on success else
    ``(False, retry_after_s)``. No waiting/queueing path — over-budget calls are
    refused with a retry_after (contract §2.3 fail-closed-to-refusal).
    """

    def __init__(self, rate: float, window_s: float = 1.0, burst: float | None = None):
        if rate <= 0 or window_s <= 0:
            raise ValueError("RateCap rate and window_s must be > 0")
        self._capacity = burst if burst is not None else rate
        self._tokens = float(self._capacity)
        self._per_second = rate / window_s
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._per_second)
            self._last = now

    def try_acquire(self, cost: float = 1.0) -> tuple[bool, float]:
        with self._lock:
            now = time.monotonic()
            self._refill(now)
            if self._tokens >= cost:
                self._tokens -= cost
                return True, 0.0
            deficit = cost - self._tokens
            return False, deficit / self._per_second


# ---------------------------------------------------------------------------
# Observability settings (composes timeouts + partition; call-time resolution)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObservabilitySettings:
    """Sprint-4-owned settings fragment (s4 contributes to s2's dataclass).

    Built via ``from_env`` (call-time) or constructed in tests. ``instrument`` also
    accepts a duck-typed settings object exposing ``.observability``.
    """

    timeouts: TimeoutConfig
    partition: BudgetPartition
    capture_content: bool = False

    @classmethod
    def from_env(cls) -> ObservabilitySettings:
        return cls(
            timeouts=TimeoutConfig.from_env(),
            partition=BudgetPartition.from_env(),
            capture_content=_env_bool(ENV_CAPTURE_CONTENT, False),
        )

    def validate(self) -> None:
        """Fail-loud config validation — run at instrument() time, never import."""
        validate_timeout_config(self.timeouts)
        validate_partition(self.partition)

    def build_rate_cap(self) -> RateCap:
        return RateCap(
            rate=self.partition.rate_rps,
            window_s=1.0,
            burst=self.partition.rate_burst,
        )


def _coerce_obs_settings(settings: Any) -> ObservabilitySettings:
    if settings is None:
        return ObservabilitySettings.from_env()
    if isinstance(settings, ObservabilitySettings):
        return settings
    frag = getattr(settings, "observability", None)
    if isinstance(frag, ObservabilitySettings):
        return frag
    return ObservabilitySettings.from_env()


# ---------------------------------------------------------------------------
# Honesty passthrough (contract §4.4) — never hide, never fabricate
# ---------------------------------------------------------------------------

_TRUE_IS_HONEST = frozenset({"stale_served", "honest_empty"})
_FALSE_IS_HONEST = frozenset({"contract_complete", "honest_contract_complete"})


def assert_honesty_passthrough(
    upstream_meta: Mapping[str, Any],
    surfaced: Mapping[str, Any],
    fields: tuple[str, ...] = NATIVE_HONESTY_FIELDS,
) -> None:
    """Assert every native honesty field present upstream is surfaced faithfully.

    DROP -> HonestySuppressionError (hiding). FLIP toward reassurance ->
    HonestySuppressionError (fabrication). Movement toward MORE honesty is allowed.
    """
    for field_name in fields:
        if field_name not in upstream_meta:
            continue
        up = upstream_meta[field_name]
        if field_name not in surfaced:
            raise HonestySuppressionError(
                f"honesty field '{field_name}'={up!r} present upstream but DROPPED "
                f"from the surfaced payload (hiding forbidden, contract §4.4)"
            )
        down = surfaced[field_name]
        if down == up:
            continue
        if field_name in _TRUE_IS_HONEST:
            if bool(up) and not bool(down):
                raise HonestySuppressionError(
                    f"honesty field '{field_name}' flipped True->False: fabricates "
                    f"reassurance (upstream {up!r}, surfaced {down!r}; §4.4)"
                )
        elif field_name in _FALSE_IS_HONEST:
            if not bool(up) and bool(down):
                raise HonestySuppressionError(
                    f"honesty field '{field_name}' flipped False->True: fabricates "
                    f"contract-completeness (upstream {up!r}, surfaced {down!r}; §4.4)"
                )
        else:
            raise HonestySuppressionError(
                f"honesty field '{field_name}' altered {up!r}->{down!r}; unknown "
                f"polarity, exact passthrough required (§4.4)"
            )


# ---------------------------------------------------------------------------
# Failure postures (contract §4.1, §4.3) — typed, retryable, never cross-dressed
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MappedError:
    """A tool-layer error mapped from an upstream status / posture (contract §4)."""

    status_code: int
    code: str
    shape: str  # cache_warming | upstream | auth | client | not_ready | jwks
    retryable: bool
    reason: str
    retry_after_s: float | None = None


def assert_never_auth_shaped(mapped: MappedError) -> None:
    """Fail loud if a 5xx/timeout/cold-frame mapping is auth-shaped (contract §4.3).

    Applies to the cache_warming / upstream / not_ready / timeout shapes — NOT to a
    genuine ``auth`` shape (401/403), which is legitimately about credentials.
    """
    if mapped.shape == "auth":
        return
    blob = f"{mapped.code} {mapped.reason}"
    if _AUTH_SHAPED.search(blob):
        raise AuthShapedError(
            f"path {mapped.code!r} (shape={mapped.shape}) rendered auth-shaped: "
            f"{blob!r} matches the forbidden vocabulary (contract §4.3)"
        )


def map_upstream_status(
    status_code: int,
    *,
    cause_code: str | None = None,
    retry_after_s: float | None = None,
    remaining_budget_s: float | None = None,
) -> MappedError | None:
    """Map an upstream satellite HTTP status to a tool-layer error (contract §4.3).

    ``None`` for 2xx. A 503 propagates the TYPED satellite cause (e.g.
    ``CACHE_BUILD_IN_PROGRESS``), retryable, retry_after (satellite Retry-After when
    present, else ``min(remaining_budget, 30)``), and is NEVER auth-shaped. 401/403
    ARE auth so the mapping DISCRIMINATES.
    """
    if 200 <= status_code < 300:
        return None
    if status_code == 503:
        cause = cause_code or "CACHE_BUILD_IN_PROGRESS"
        if retry_after_s is not None:
            ra = retry_after_s
        else:
            ra = min(remaining_budget_s if remaining_budget_s is not None else 30.0, 30.0)
        return MappedError(
            status_code=503,
            code=cause,
            shape="cache_warming",
            retryable=True,
            reason=f"backing satellite frame is cold / building ({cause}); retry shortly",
            retry_after_s=ra,
        )
    if status_code in (401, 403):
        return MappedError(
            status_code=status_code,
            code="UPSTREAM_AUTH_REJECTED",
            shape="auth",
            retryable=False,
            reason="upstream rejected the S2S credential",
        )
    if 500 <= status_code < 600:
        return MappedError(
            status_code=status_code,
            code=cause_code or "MCP_UPSTREAM_ERROR",
            shape="upstream",
            retryable=True,
            reason=f"upstream satellite error {status_code}; retry shortly",
            retry_after_s=retry_after_s,
        )
    return MappedError(
        status_code=status_code,
        code="MCP_CLIENT_ERROR",
        shape="client",
        retryable=False,
        reason=f"client error {status_code}",
    )


def readiness_refusal(ready: bool, *, retry_after_s: float = 2.0) -> MappedError | None:
    """Satellite /ready fail-closed refusal (contract §4.1; checklist item 9).

    ``ready`` -> ``None`` (tools serve). ``not ready`` -> a retryable, warming/not
    -ready refusal (the cacheless sidecar NEVER serves from nothing), never
    auth-shaped.
    """
    if ready:
        return None
    return MappedError(
        status_code=503,
        code=CODE_NOT_READY,
        shape="not_ready",
        retryable=True,
        reason="backing satellite is warming / not ready; retry shortly",
        retry_after_s=retry_after_s,
    )


def jwks_posture(
    *,
    jwks_reachable: bool,
    has_cached_keys: bool,
    token_valid: bool,
) -> MappedError | None:
    """Inbound-JWKS failure posture (contract §4.1; checklist item 10).

    Cold + unreachable JWKS -> retryable ``AUTH_JWKS_UNAVAILABLE`` (503-shaped,
    explicitly NOT a 401): auth-INFRA down is retryable, not a credential failure.
    Reachable (or warm/stale cache) + invalid token -> 401 ``AUTH_TOKEN_INVALID``
    (credential failure, non-retryable). The two families never cross-dress.
    """
    if not jwks_reachable and not has_cached_keys:
        return MappedError(
            status_code=503,
            code=CODE_JWKS_UNAVAILABLE,
            shape="jwks",
            retryable=True,
            reason="authentication infrastructure (JWKS) unavailable; retry shortly",
            retry_after_s=2.0,
        )
    if not token_valid:
        return MappedError(
            status_code=401,
            code=CODE_TOKEN_INVALID,
            shape="auth",
            retryable=False,
            reason="invalid or expired token",
        )
    return None


# ---------------------------------------------------------------------------
# Traceparent propagation + gen_ai span convention (contract §3)
# ---------------------------------------------------------------------------


def propagate_traceparent(carrier: MutableMapping[str, str]) -> MutableMapping[str, str]:
    """Inject the active span's W3C traceparent into ``carrier`` (contract §3.3)."""
    from opentelemetry import propagate  # lazy import (import-safety)

    propagate.inject(carrier)
    return carrier


@contextmanager
def tool_span(
    tool_name: str,
    *,
    satellite: str = _SATELLITE,
    honesty: Mapping[str, Any] | None = None,
    capture_content: bool = False,
    tool_args: Any = None,
) -> Iterator[Any]:
    """Open the ONE gen_ai.* tool-execution span per call (contract §3.2)."""
    from opentelemetry import trace  # lazy import (import-safety)

    tracer = trace.get_tracer("asana_mcp.observability")
    with tracer.start_as_current_span(f"execute_tool {tool_name}") as span:
        span.set_attribute(GEN_AI_OPERATION, "execute_tool")
        span.set_attribute(GEN_AI_TOOL_NAME, tool_name)
        span.set_attribute(GEN_AI_TOOL_TYPE, "function")
        span.set_attribute(ATTR_SATELLITE, satellite)
        span.set_attribute(ATTR_TOOL_NAME, tool_name)
        span.set_attribute(ATTR_BUDGET_CLASS, "mcp")
        if capture_content and tool_args is not None:
            # OPT-IN ONLY, default OFF (PII posture, contract §3.2).
            span.set_attribute(GEN_AI_TOOL_ARGS, repr(tool_args))
        if honesty:
            for k, v in honesty.items():
                span.set_attribute(f"{ATTR_HONESTY_PREFIX}{k}", bool(v))
        yield span


# ---------------------------------------------------------------------------
# The core wrapper — the four seam guarantees live here
# ---------------------------------------------------------------------------


def _extract_honesty(payload: Any) -> dict[str, Any]:
    honesty: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        meta: Any = payload.get("meta", payload)
    else:
        meta = getattr(payload, "meta", payload)
    for name in NATIVE_HONESTY_FIELDS:
        if isinstance(meta, Mapping):
            if name in meta:
                honesty[name] = meta[name]
        elif hasattr(meta, name):
            honesty[name] = getattr(meta, name)
    return honesty


def _upstream_honesty_hint(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        hint = payload.get("_upstream_meta")
        if isinstance(hint, Mapping):
            return dict(hint)
    hint = getattr(payload, "_upstream_meta", None)
    if isinstance(hint, Mapping):
        return dict(hint)
    return {}


def _ctx_trace_carrier(ctx: Any) -> MutableMapping[str, str] | None:
    carrier = getattr(ctx, "trace_carrier", None)
    if isinstance(carrier, MutableMapping):
        return carrier
    http = getattr(ctx, "http", None)
    headers = getattr(http, "headers", None)
    if isinstance(headers, MutableMapping):
        return headers
    return None


def instrument_tool(
    fn: Callable[..., Any],
    *,
    tool_name: str,
    obs: ObservabilitySettings,
    rate_cap: RateCap,
    get_ctx: Callable[[], Any] | None = None,
    honesty_check: bool = True,
) -> Callable[..., Any]:
    """Wrap a single async tool callable with the seam guarantees (contract §3/§4)."""
    if getattr(fn, _WRAPPED_ATTR, False):
        return fn  # double-wrap guard (idempotency)

    tool_timeout_s = obs.timeouts.tool_timeout_for(tool_name)

    @functools.wraps(fn)
    async def wrapped(*args: Any, **kwargs: Any) -> Any:
        # (R3) rate cap — typed refusal, retry_after, NEVER queue.
        ok, retry_after = rate_cap.try_acquire()
        if not ok:
            with tool_span(tool_name, capture_content=obs.capture_content) as span:
                span.set_attribute(ATTR_REFUSAL_CAUSE, "rate_budget")
            raise RateCapExceeded(retry_after_s=retry_after)

        with tool_span(tool_name, capture_content=obs.capture_content) as span:
            # (C4/C5) traceparent onto ctx.http calls.
            if get_ctx is not None:
                ctx = get_ctx()
                carrier = _ctx_trace_carrier(ctx)
                if carrier is not None:
                    propagate_traceparent(carrier)

            # (R2/C4) outermost timeout guard; bound from the timeouts SoT.
            try:
                async with asyncio.timeout(tool_timeout_s):
                    result = await fn(*args, **kwargs)
            except TimeoutError as exc:
                span.set_attribute(ATTR_REFUSAL_CAUSE, "timeout")
                raise TimeoutError(
                    f"{CODE_UPSTREAM_TIMEOUT}: asana-mcp tool guard fired after "
                    f"{tool_timeout_s}s (outermost sidecar ring, strictly inside the "
                    f"ALB floor {ALB_IDLE_TIMEOUT_FLOOR_S}s); retry shortly"
                ) from exc

            # (C6) honesty passthrough — never hide the upstream honesty flags.
            if honesty_check:
                upstream = _upstream_honesty_hint(result)
                surfaced = _extract_honesty(result)
                if upstream:
                    assert_honesty_passthrough(upstream, surfaced)
                for k, v in surfaced.items():
                    span.set_attribute(f"{ATTR_HONESTY_PREFIX}{k}", bool(v))
            return result

    setattr(wrapped, _WRAPPED_ATTR, True)
    return wrapped


# ---------------------------------------------------------------------------
# The FROZEN seam: instrument(mcp, settings) -> mcp  (idempotent)
# ---------------------------------------------------------------------------


def _iter_tool_handles(
    mcp: Any,
) -> list[tuple[str, Any, Callable[[Callable[..., Any]], None]]]:
    """Best-effort adapter over FastMCP's tool registry (shortcut S2)."""
    registry = getattr(mcp, "_tools", None)
    if registry is None:
        tool_manager = getattr(mcp, "_tool_manager", None)
        registry = getattr(tool_manager, "_tools", None)
    handles: list[tuple[str, Any, Callable[[Callable[..., Any]], None]]] = []
    if isinstance(registry, Mapping):
        for name, tool_obj in registry.items():
            if hasattr(tool_obj, "fn"):

                def _setter(new_fn: Callable[..., Any], _t: Any = tool_obj) -> None:
                    _t.fn = new_fn

                handles.append((str(name), tool_obj.fn, _setter))
    return handles


def instrument(mcp: FastMCP, settings: Settings) -> FastMCP:
    """Wrap every tool execution with sprint-4 observability + guardrails.

    FROZEN mount-seam v1 item 3. IDEMPOTENT (checklist item 13): a second call is a
    no-op. Config is validated fail-loud (timeout cascade §1.3 + partition §2.2)
    BEFORE any tool is wrapped, so a misconfigured deploy refuses at startup.
    """
    if getattr(mcp, _INSTRUMENTED_ATTR, False):
        return mcp

    obs = _coerce_obs_settings(settings)
    obs.validate()  # fail-loud: timeout cascade + budget partition invariants
    rate_cap = obs.build_rate_cap()

    get_ctx = getattr(mcp, "get_context", None)
    for name, current_fn, set_fn in _iter_tool_handles(mcp):
        set_fn(
            instrument_tool(
                current_fn,
                tool_name=name,
                obs=obs,
                rate_cap=rate_cap,
                get_ctx=get_ctx if callable(get_ctx) else None,
            )
        )

    setattr(mcp, _INSTRUMENTED_ATTR, True)
    mcp._asana_mcp_obs = obs
    mcp._asana_mcp_rate_cap = rate_cap
    return mcp
