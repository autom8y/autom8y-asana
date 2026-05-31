"""Tests for receiver-bulk-fanout-reliability Stage-1 (IMPL-1) surfaces.

Covers the 5 surfaces wired in this initiative:

* Surface A — BuildCoordinator wired into ``_build_on_miss`` (universal_strategy)
* Surface E — SA exemption in rate-limit key resolver (api/rate_limit)
* Surface F — HTTP Retry-After header on 503 (api/errors)
* Surface F' — Harmonized 30s retry_after_seconds in decorator
* Surface 5 — Stage-1 metrics emission (cache_lookup, semaphore_utilization,
  rate_limit_429 by namespace, receiver_query_outcome)

Design references:
- HANDOFF-thermia-to-10x-dev-receiver-bulk-fanout-reliability-2026-05-31 §IMPL-1
- .sos/wip/thermia/cache-architecture.md §A,§E,§F/F'
- .sos/wip/thermia/observability-plan.md §Stage-1 metrics

Each test names the acceptance criterion it covers in the docstring.
"""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_jwt(payload: dict[str, object]) -> str:
    """Construct a syntactically valid JWT (no signature verification needed).

    The rate-limit key function only DECODES the payload (it does not verify
    signature/audience/expiry — that happens later in the route auth
    dependency). Tests fabricate the payload to control the service_name claim.
    """
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    signature = "ZmFrZS1zaWctZm9yLXVuaXQtdGVzdA"  # base64url, no padding
    return f"{header}.{body}.{signature}"


def _make_request_with_auth(token: str | None = None) -> MagicMock:
    """Construct a minimal FastAPI Request stub for the rate-limit key func."""
    req = MagicMock()
    req.headers = (
        {"authorization": f"Bearer {token}"} if token else {}
    )
    # get_remote_address inspects request.client.host
    req.client = SimpleNamespace(host="127.0.0.1")
    req.scope = {"type": "http", "client": ("127.0.0.1", 12345), "headers": []}
    return req


# ===========================================================================
# Surface F' — harmonize retry_after_seconds to 30s in decorator
# ===========================================================================


class TestSurfaceFPrimeRetryHarmonization:
    """Surface F' — decorator.py:155 raises CACHE_BUILD_IN_PROGRESS with 30s.

    Acceptance: 'F': unit test asserts decorator.py raises CACHE_BUILD_IN_PROGRESS
    with retry_after_seconds=30 (was 5).
    """

    async def test_wait_for_build_timeout_raises_30s_retry(self) -> None:
        """The decorator's wait-timeout branch carries retry_after_seconds=30.

        Previously this raised with retry_after_seconds=5 — inconsistent with
        the 30s value used by services/universal_strategy._build_on_miss.
        Harmonized to 30s per Phase-3 Knob 3 derivation.
        """
        from autom8_asana.api.exception_types import ApiDataFrameBuildError
        from autom8_asana.cache.dataframe.decorator import dataframe_cache

        # Mock cache that returns None (cache miss) and forces the wait-for-build
        # path by returning False from acquire_build_lock_async and None from
        # wait_for_build_async (timeout).
        cache = MagicMock()
        cache.get_async = AsyncMock(return_value=None)
        cache.acquire_build_lock_async = AsyncMock(return_value=False)
        cache.wait_for_build_async = AsyncMock(return_value=None)

        @dataframe_cache(
            cache_provider=lambda: cache,
            entity_type="offer",
            bypass_env_var="NEVER_SET",
        )
        class _Strategy:
            async def resolve(
                self, criteria: list[object], project_gid: str, client: object
            ) -> list[object]:
                return []

        with patch(
            "autom8_asana.settings.get_settings",
            return_value=SimpleNamespace(runtime=SimpleNamespace(dataframe_cache_bypass=False)),
        ):
            with pytest.raises(ApiDataFrameBuildError) as exc_info:
                await _Strategy().resolve([], "12345", MagicMock())

        assert exc_info.value.code == "CACHE_BUILD_IN_PROGRESS"
        # F' harmonization: 30s, not 5s.
        assert exc_info.value.details == {"retry_after_seconds": 30}


# ===========================================================================
# Surface F — HTTP Retry-After header on 503 response envelope
# ===========================================================================


class TestSurfaceFRetryAfterHeader:
    """Surface F — 503 response carries HTTP Retry-After header.

    Acceptance: 'F': integration test confirms 503 response carries HTTP
    Retry-After header (matching the body error.details.retry_after_seconds).
    """

    async def test_503_carries_retry_after_header_matching_body(self) -> None:
        """The api_dataframe_build_error_handler emits Retry-After header.

        The header value mirrors exc.details["retry_after_seconds"] (the body-
        level field), and the body field is preserved for legacy consumers
        that parse the envelope (additive, not a replacement).
        """
        from autom8_asana.api.errors import api_dataframe_build_error_handler
        from autom8_asana.api.exception_types import ApiDataFrameBuildError

        request = MagicMock()
        request.state = SimpleNamespace(request_id="abcdef0123456789")
        exc = ApiDataFrameBuildError(
            "CACHE_BUILD_IN_PROGRESS",
            "DataFrame build in progress, retry shortly",
            retry_after_seconds=30,
        )

        response = await api_dataframe_build_error_handler(request, exc)

        assert response.status_code == 503
        # F: HTTP-level Retry-After header.
        assert response.headers.get("retry-after") == "30"
        # Body-level field preserved (additive, not removed).
        body = json.loads(response.body.decode())
        assert body["error"]["details"]["retry_after_seconds"] == 30

    async def test_503_without_retry_after_omits_header(self) -> None:
        """When the exception carries no retry_after_seconds, the header is omitted.

        Some error codes (e.g., DATAFRAME_BUILD_UNAVAILABLE) intentionally have
        no retry calibration — emitting a default would mislead consumers into
        retrying when the problem is structural (no build method configured).
        """
        from autom8_asana.api.errors import api_dataframe_build_error_handler
        from autom8_asana.api.exception_types import ApiDataFrameBuildError

        request = MagicMock()
        request.state = SimpleNamespace(request_id="fedcba9876543210")
        exc = ApiDataFrameBuildError(
            "DATAFRAME_BUILD_UNAVAILABLE",
            "No build method configured",
        )

        response = await api_dataframe_build_error_handler(request, exc)

        assert response.status_code == 503
        assert response.headers.get("retry-after") is None


# ===========================================================================
# Surface E — SA exemption in rate-limit key resolver
# ===========================================================================


class TestSurfaceERateLimitSAExemption:
    """Surface E — SA-class JWTs route to ``sa:asana-dataframe-resolver`` namespace.

    Acceptance: 'E': integration test confirms bearer token matching SA pattern
    routes to sa: namespace bucket; per-namespace rate-limit metric labels
    emit correctly.
    """

    def test_sa_jwt_routes_to_sa_namespace(self) -> None:
        """A JWT carrying service_name=asana-dataframe-resolver → sa: namespace."""
        from autom8_asana.api.rate_limit import (
            SA_RATE_LIMIT_NAMESPACE,
            _get_rate_limit_key,
        )

        sa_jwt = _make_jwt({
            "sub": "service-account",
            "service_name": "asana-dataframe-resolver",
            "iss": "auth.api.autom8y.io",
        })
        request = _make_request_with_auth(sa_jwt)

        key = _get_rate_limit_key(request)

        assert key == SA_RATE_LIMIT_NAMESPACE

    def test_non_sa_jwt_routes_to_pat_namespace(self) -> None:
        """A JWT carrying a different service_name → pat: namespace (fallback).

        The rate-limit key function only special-cases the
        ``asana-dataframe-resolver`` SA. All other JWTs (and PATs) fall
        through to the existing pat:{prefix} key — preserving the existing
        contract for non-SA callers.
        """
        from autom8_asana.api.rate_limit import _get_rate_limit_key

        other_jwt = _make_jwt({
            "sub": "service-account",
            "service_name": "some-other-service",
            "iss": "auth.api.autom8y.io",
        })
        request = _make_request_with_auth(other_jwt)

        key = _get_rate_limit_key(request)

        assert key.startswith("pat:")
        assert key != "sa:asana-dataframe-resolver"

    def test_pat_token_routes_to_pat_namespace(self) -> None:
        """Asana PAT (no dots) → pat:{prefix} namespace, unchanged."""
        from autom8_asana.api.rate_limit import _get_rate_limit_key

        # Asana PAT format: 0/xxxxxxxx, no dots
        request = _make_request_with_auth("0/abcdefghijklmnop")

        key = _get_rate_limit_key(request)

        assert key.startswith("pat:")

    def test_no_auth_falls_back_to_ip_namespace(self) -> None:
        """Unauthenticated requests fall back to ip: namespace, unchanged."""
        from autom8_asana.api.rate_limit import _get_rate_limit_key

        request = _make_request_with_auth(None)

        key = _get_rate_limit_key(request)

        assert key.startswith("ip:")

    def test_malformed_jwt_falls_back_to_pat_namespace(self) -> None:
        """A JWT-shaped token with malformed payload silently falls through.

        Guards against AttributeError / decode errors at key-time —
        misclassification as PAT preserves the global ceiling for that caller
        (which then fails at the route's auth dependency anyway).
        """
        from autom8_asana.api.rate_limit import _get_rate_limit_key

        # 2-dot token but middle segment is not valid base64-encoded JSON
        request = _make_request_with_auth("hdr.malformed!@#$.sig")

        key = _get_rate_limit_key(request)

        assert key.startswith("pat:")

    def test_sa_namespace_limit_string_is_high_ceiling(self) -> None:
        """SA_NAMESPACE_LIMIT exposes the high-ceiling string for route decoration.

        Body-parameterized query routes (project/section rows) decorate with
        ``@limiter.limit(SA_NAMESPACE_LIMIT, key_func=...)`` to get the 600/min
        SA bucket. The constant is the route-altitude mechanism for surface E.
        """
        from autom8_asana.api.rate_limit import SA_NAMESPACE_LIMIT, SA_RATE_LIMIT_RPM

        assert SA_NAMESPACE_LIMIT == f"{SA_RATE_LIMIT_RPM}/minute"
        assert SA_NAMESPACE_LIMIT == "600/minute"

    def test_default_rate_limit_string_returns_configured_ceiling(self) -> None:
        """_get_rate_limit_string returns the configured global ceiling.

        Default per api/config.py:56-60 is 100/minute. The SlowAPI limiter
        invokes this no-arg callable at config-resolution time (per
        slowapi/wrappers.py:94 — LimitGroup.__iter__).
        """
        from autom8_asana.api.rate_limit import _get_rate_limit_string

        result = _get_rate_limit_string()

        # Default per api/config.py:56-60
        assert result == "100/minute"

    def test_is_sa_token_recognizes_sa_jwt(self) -> None:
        """_is_sa_token returns True for the resolver SA JWT."""
        from autom8_asana.api.rate_limit import _is_sa_token

        sa_jwt = _make_jwt({"service_name": "asana-dataframe-resolver"})
        assert _is_sa_token(f"Bearer {sa_jwt}") is True

    def test_is_sa_token_rejects_non_sa_jwt(self) -> None:
        """_is_sa_token returns False for JWTs with other service_name claims."""
        from autom8_asana.api.rate_limit import _is_sa_token

        other_jwt = _make_jwt({"service_name": "some-other-service"})
        assert _is_sa_token(f"Bearer {other_jwt}") is False

    def test_is_sa_token_rejects_pat(self) -> None:
        """_is_sa_token returns False for PAT tokens (no JWT structure)."""
        from autom8_asana.api.rate_limit import _is_sa_token

        assert _is_sa_token("Bearer 0/abcdefghijklmnop") is False

    def test_is_sa_token_rejects_missing_auth(self) -> None:
        """_is_sa_token returns False when no auth header present."""
        from autom8_asana.api.rate_limit import _is_sa_token

        assert _is_sa_token("") is False
        assert _is_sa_token("Bearer ") is False


# ===========================================================================
# Surface A — BuildCoordinator wired into _build_on_miss
# ===========================================================================


class TestSurfaceABuildCoordinatorAccessors:
    """Surface A — factory accessor pattern.

    The accessors mirror get_dataframe_cache_provider() exactly. Tests
    verify the singleton lifecycle: uninitialized -> initialize -> get -> reset.
    """

    def setup_method(self) -> None:
        """Reset singleton before each test for isolation."""
        from autom8_asana.cache.dataframe.factory import reset_build_coordinator

        reset_build_coordinator()

    def teardown_method(self) -> None:
        """Reset singleton after each test for isolation."""
        from autom8_asana.cache.dataframe.factory import reset_build_coordinator

        reset_build_coordinator()

    def test_get_before_init_returns_none(self) -> None:
        """Before initialize_build_coordinator() runs, get returns None."""
        from autom8_asana.cache.dataframe.factory import get_build_coordinator

        assert get_build_coordinator() is None

    async def test_initialize_creates_singleton_with_defaults(self) -> None:
        """initialize_build_coordinator() returns a coordinator with capacity defaults.

        Defaults derived from Phase-3 capacity-specification.md:
        - max_concurrent_builds=4 (Knob 1)
        - default_timeout_seconds=55.0 (Knob 2; fits < 60s ALB idle)
        """
        from autom8_asana.cache.dataframe.factory import (
            get_build_coordinator,
            initialize_build_coordinator,
        )

        # Must run inside event loop because BuildCoordinator creates a Semaphore.
        coord = initialize_build_coordinator()

        assert coord is not None
        assert coord.max_concurrent_builds == 4
        assert coord.default_timeout_seconds == 55.0
        assert get_build_coordinator() is coord

    async def test_initialize_is_idempotent(self) -> None:
        """Calling initialize twice returns the same instance.

        Critical for hot-reload / repeated lifespan invocations: replacing
        the singleton mid-flight would orphan in-flight build futures.
        """
        from autom8_asana.cache.dataframe.factory import initialize_build_coordinator

        first = initialize_build_coordinator()
        second = initialize_build_coordinator()

        assert first is second


class TestSurfaceABuildOnMissWiring:
    """Surface A — _build_on_miss invokes BuildCoordinator semantics.

    Acceptance: 'A': unit test confirms 5+ concurrent same-key requests = 1 build
    (per-key dedup); 5+ concurrent distinct-key requests = ≤4 concurrent builds
    (cross-key semaphore).
    """

    async def test_same_key_concurrent_requests_dedup_to_one_build(self) -> None:
        """5 concurrent same-key cold misses → exactly 1 build via BuildCoordinator.

        Demonstrates Layer 1 (per-key dedup) of the two-layer concurrency
        model: BuildCoordinator._in_flight + asyncio.Future coalesce all
        same-key arrivals onto the first one.
        """
        from autom8_asana.cache.dataframe.build_coordinator import BuildCoordinator
        from autom8_asana.cache.dataframe.factory import set_build_coordinator

        build_calls = 0

        async def fake_build() -> tuple[None, datetime]:
            nonlocal build_calls
            build_calls += 1
            await asyncio.sleep(0.05)  # ensure overlap among concurrent waiters
            return (None, datetime.now(UTC))

        coord = BuildCoordinator(
            max_concurrent_builds=4,
            default_timeout_seconds=2.0,
        )
        set_build_coordinator(coord)

        try:
            key = ("proj-A", "project")
            # Fire 5 concurrent build_or_wait_async on the SAME key.
            results = await asyncio.gather(
                *[
                    coord.build_or_wait_async(key, fake_build, caller=f"w{i}")
                    for i in range(5)
                ]
            )

            # Exactly one BUILT, the other 4 COALESCED.
            from autom8_asana.cache.dataframe.build_coordinator import BuildOutcome

            built_count = sum(1 for r in results if r.outcome == BuildOutcome.BUILT)
            coalesced_count = sum(
                1 for r in results if r.outcome == BuildOutcome.COALESCED
            )
            assert built_count == 1, f"Expected 1 BUILT, got {built_count}"
            assert coalesced_count == 4, f"Expected 4 COALESCED, got {coalesced_count}"
            # build_fn invoked exactly once despite 5 callers.
            assert build_calls == 1
        finally:
            set_build_coordinator(None)

    async def test_distinct_key_concurrent_requests_respect_semaphore(self) -> None:
        """5 concurrent distinct-key cold misses → at most 4 concurrent builds.

        Demonstrates Layer 2 (cross-key cap) of the two-layer concurrency
        model: BuildCoordinator._build_semaphore bounds simultaneous builds
        regardless of key diversity. The 5th caller waits for a slot.
        """
        from autom8_asana.cache.dataframe.build_coordinator import (
            BuildCoordinator,
            BuildOutcome,
        )
        from autom8_asana.cache.dataframe.factory import set_build_coordinator

        active_builds = 0
        peak_active = 0
        peak_lock = asyncio.Lock()

        async def measuring_build() -> tuple[None, datetime]:
            nonlocal active_builds, peak_active
            async with peak_lock:
                active_builds += 1
                peak_active = max(peak_active, active_builds)
            try:
                await asyncio.sleep(0.1)
            finally:
                async with peak_lock:
                    active_builds -= 1
            return (None, datetime.now(UTC))

        coord = BuildCoordinator(
            max_concurrent_builds=4,
            default_timeout_seconds=5.0,
        )
        set_build_coordinator(coord)

        try:
            # 5 DISTINCT keys, all cold-miss concurrently.
            results = await asyncio.gather(
                *[
                    coord.build_or_wait_async(
                        (f"proj-{i}", "project"),
                        measuring_build,
                        caller=f"w{i}",
                    )
                    for i in range(5)
                ]
            )

            # All 5 are BUILT (distinct keys, no coalescing) but peak in-flight
            # never exceeds max_concurrent_builds=4 thanks to the semaphore.
            assert all(r.outcome == BuildOutcome.BUILT for r in results)
            assert peak_active <= 4, (
                f"Semaphore violated — peak concurrent builds = {peak_active}, "
                f"but max_concurrent_builds = 4"
            )
        finally:
            set_build_coordinator(None)


# ===========================================================================
# Surface 5 — Stage-1 metrics emission
# ===========================================================================


class TestSurface5StageOneMetrics:
    """Surface 5 — Stage-1 metrics emit on the correct conditions.

    Acceptance: 'Stage-1 metrics': smoke tests that each new metric emits at
    least once under deterministic test conditions.
    """

    def test_record_cache_lookup_increments_hit_outcome(self) -> None:
        """record_cache_lookup(hit=True) increments the hit outcome counter."""
        from autom8_asana.api.metrics import (
            CACHE_LOOKUP_OUTCOME,
            record_cache_lookup,
        )

        before = CACHE_LOOKUP_OUTCOME.labels(
            entity_type="project", outcome="hit"
        )._value.get()
        record_cache_lookup("project", hit=True)
        after = CACHE_LOOKUP_OUTCOME.labels(
            entity_type="project", outcome="hit"
        )._value.get()

        assert after == before + 1

    def test_record_cache_lookup_increments_miss_outcome(self) -> None:
        """record_cache_lookup(hit=False) increments the miss outcome counter."""
        from autom8_asana.api.metrics import (
            CACHE_LOOKUP_OUTCOME,
            record_cache_lookup,
        )

        before = CACHE_LOOKUP_OUTCOME.labels(
            entity_type="section", outcome="miss"
        )._value.get()
        record_cache_lookup("section", hit=False)
        after = CACHE_LOOKUP_OUTCOME.labels(
            entity_type="section", outcome="miss"
        )._value.get()

        assert after == before + 1

    def test_record_build_coordinator_utilization_updates_gauge(self) -> None:
        """semaphore utilization = in_flight / max_concurrent."""
        from autom8_asana.api.metrics import (
            BUILD_COORDINATOR_SEMAPHORE_UTILIZATION,
            record_build_coordinator_utilization,
        )

        record_build_coordinator_utilization(in_flight=3, max_concurrent=4)
        # 3/4 = 0.75; Gauge._value.get() returns the latest set value.
        assert BUILD_COORDINATOR_SEMAPHORE_UTILIZATION._value.get() == pytest.approx(0.75)

    def test_record_build_coordinator_utilization_handles_zero_max(self) -> None:
        """Defensive: 0 max_concurrent must not raise (div-by-zero)."""
        from autom8_asana.api.metrics import record_build_coordinator_utilization

        # Must not raise; behavior is no-op (defensive guard).
        record_build_coordinator_utilization(in_flight=0, max_concurrent=0)

    def test_record_rate_limit_429_known_namespace(self) -> None:
        """sa / pat / ip namespaces are recorded verbatim."""
        from autom8_asana.api.metrics import (
            RATE_LIMIT_429_BY_NAMESPACE,
            record_rate_limit_429,
        )

        before = RATE_LIMIT_429_BY_NAMESPACE.labels(namespace="sa")._value.get()
        record_rate_limit_429("sa")
        after = RATE_LIMIT_429_BY_NAMESPACE.labels(namespace="sa")._value.get()

        assert after == before + 1

    def test_record_rate_limit_429_unknown_namespace_buckets_as_other(self) -> None:
        """Unknown namespaces are bucketed under 'other' (not silently dropped)."""
        from autom8_asana.api.metrics import (
            RATE_LIMIT_429_BY_NAMESPACE,
            record_rate_limit_429,
        )

        before = RATE_LIMIT_429_BY_NAMESPACE.labels(namespace="other")._value.get()
        record_rate_limit_429("unexpected-prefix")
        after = RATE_LIMIT_429_BY_NAMESPACE.labels(namespace="other")._value.get()

        assert after == before + 1

    def test_record_receiver_query_outcome_success(self) -> None:
        """Success outcome increments per-arm success counter."""
        from autom8_asana.api.metrics import (
            RECEIVER_QUERY_OUTCOME,
            record_receiver_query_outcome,
        )

        before = RECEIVER_QUERY_OUTCOME.labels(
            entity_type="project", outcome="success"
        )._value.get()
        record_receiver_query_outcome("project", success=True)
        after = RECEIVER_QUERY_OUTCOME.labels(
            entity_type="project", outcome="success"
        )._value.get()

        assert after == before + 1

    def test_record_receiver_query_outcome_server_error(self) -> None:
        """Failure outcome increments per-arm server_error counter."""
        from autom8_asana.api.metrics import (
            RECEIVER_QUERY_OUTCOME,
            record_receiver_query_outcome,
        )

        before = RECEIVER_QUERY_OUTCOME.labels(
            entity_type="section", outcome="server_error"
        )._value.get()
        record_receiver_query_outcome("section", success=False)
        after = RECEIVER_QUERY_OUTCOME.labels(
            entity_type="section", outcome="server_error"
        )._value.get()

        assert after == before + 1


class TestSurface5RateLimit429NamespaceHandler:
    """Surface 5 — 429 wrapper handler extracts namespace from rate-limit key."""

    async def test_429_handler_records_sa_namespace_for_sa_token(self) -> None:
        """A 429 raised on an SA token records the sa namespace.

        The wrapper handler reads the rate-limit key (computed via the same
        key function as SlowAPI itself), takes the prefix before the colon,
        and records the per-namespace 429 counter. Delegates the response
        construction to SlowAPI's default handler unchanged.
        """
        from autom8_asana.api.errors import rate_limit_exceeded_namespace_handler
        from autom8_asana.api.metrics import RATE_LIMIT_429_BY_NAMESPACE

        # Build an app + request with the SA JWT.
        sa_jwt = _make_jwt({
            "sub": "service-account",
            "service_name": "asana-dataframe-resolver",
        })

        # SlowAPI's default handler inspects request.app.state.limiter and
        # request.state.view_rate_limit. Provide minimal stubs that let
        # _rate_limit_exceeded_handler return a JSONResponse.
        request = MagicMock()
        request.headers = {"authorization": f"Bearer {sa_jwt}"}
        request.client = SimpleNamespace(host="127.0.0.1")
        request.scope = {"type": "http", "client": ("127.0.0.1", 12345), "headers": []}

        # Stub limiter._inject_headers to be a no-op (returns the response).
        limiter_stub = MagicMock()
        limiter_stub._inject_headers = lambda resp, _vrl: resp
        request.app = MagicMock()
        request.app.state = SimpleNamespace(limiter=limiter_stub)
        request.state = SimpleNamespace(view_rate_limit=None, request_id="0011223344556677")

        # Build a fake RateLimitExceeded with a detail attribute.
        exc = MagicMock()
        exc.detail = "600 per 1 minute"

        before = RATE_LIMIT_429_BY_NAMESPACE.labels(namespace="sa")._value.get()
        response = await rate_limit_exceeded_namespace_handler(request, exc)
        after = RATE_LIMIT_429_BY_NAMESPACE.labels(namespace="sa")._value.get()

        # Namespace metric incremented for sa.
        assert after == before + 1
        # SlowAPI's default response shape preserved (429 JSON).
        assert response.status_code == 429
