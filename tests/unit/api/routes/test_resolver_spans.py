"""Span tests for the resolver.entities.resolve span (Sprint 5, G-01/G-02/G-03/G-07).

Verifies that the `resolver.entities.resolve` context manager emits the correct
span, attributes, and error-path status for the three exception tiers.

Test coverage:
- T-G01: Happy path -- span name, creation attributes, post-execution counts
- T-G02: Tier 1 ServiceError -- error_code, error_tier, error.type, StatusCode.ERROR
- T-G03: Tier 3 Exception -- RESOLUTION_ERROR, unexpected tier, exception event
- T-G07: Tier 2 AsanaError -- asana_error tier, error.type, no exception event
"""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from autom8_asana.exceptions import AsanaError
from autom8_asana.services.errors import ServiceError
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNIT_PROJECT_GID = "1201081073731555"
JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}


# ---------------------------------------------------------------------------
# OTel fixture: patches the module-level _tracer in resolver.py
# ---------------------------------------------------------------------------


@pytest.fixture()
def otel_provider():
    """Fresh TracerProvider per test for span isolation.

    Patches autom8_asana.api.routes.resolver._tracer so the module-level
    singleton is bound to this test's provider, not the one active at import time.
    """
    import autom8_asana.api.routes.resolver as _resolver_module

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    fresh_tracer = provider.get_tracer("autom8_asana.api.routes.resolver")
    original_tracer = _resolver_module._tracer
    _resolver_module._tracer = fresh_tracer

    yield provider, exporter

    _resolver_module._tracer = original_tracer
    exporter.clear()


# ---------------------------------------------------------------------------
# Helpers (matching the existing resolver test pattern exactly)
# ---------------------------------------------------------------------------


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    """Create a mock JWT validation returning valid ServiceClaims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _make_async_client_mock(mock_client_class: MagicMock) -> MagicMock:
    """Configure mock AsanaClient as an async context manager."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_class.return_value = mock_client
    return mock_client


def _resolve_patches(resolve_results_or_error):
    """Build the standard patch stack for resolver route tests.

    Returns a list where the *last* element is the mock_resolve callable
    (not yet entered as a context manager) -- matching the pattern in
    test_resolver_status.py.

    resolve_results_or_error: either a list of ResolutionResult (happy path)
        or an Exception instance (error path).
    """
    if isinstance(resolve_results_or_error, BaseException) or (
        isinstance(resolve_results_or_error, type)
        and issubclass(resolve_results_or_error, BaseException)
    ):
        mock_resolve = AsyncMock(side_effect=resolve_results_or_error)
    else:
        mock_resolve = AsyncMock(return_value=resolve_results_or_error)

    jwt_patch = patch(
        "autom8_asana.api.routes.internal.validate_service_token",
        _mock_jwt_validation(),
    )
    jwt_patch_canonical = patch(
        "autom8_asana.auth.jwt_validator.validate_service_token",
        _mock_jwt_validation(),
    )
    pat_patch = patch(
        "autom8_asana.auth.bot_pat.get_bot_pat",
        return_value="test_bot_pat",
    )
    pat_patch_deps = patch(
        "autom8_asana.api.dependencies.get_bot_pat",
        return_value="test_bot_pat",
    )
    client_patch = patch("autom8_asana.AsanaClient")
    strategy_patch = patch(
        "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
        mock_resolve,
    )
    return (
        jwt_patch,
        jwt_patch_canonical,
        pat_patch,
        pat_patch_deps,
        client_patch,
        strategy_patch,
        mock_resolve,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before and after each test for isolation."""
    from autom8_asana.auth.bot_pat import clear_bot_pat_cache
    from autom8_asana.auth.jwt_validator import reset_auth_client

    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    """Create a test application with mocked discovery and entity registry."""
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")

    from autom8_asana.api.lifespan import _discover_entity_projects  # noqa: PLC2701
    from autom8_asana.api.main import create_app

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app: MagicMock) -> None:
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="unit",
                project_gid=UNIT_PROJECT_GID,
                project_name="Business Units",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def test_client(app):
    """Synchronous test client with lifespan events handled."""
    from fastapi.testclient import TestClient

    with TestClient(app) as tc:
        yield tc


def _call_resolve(test_client, resolve_results_or_error):
    """Call the resolve endpoint and return (response, spans_getter).

    Uses the same pattern as test_resolver_status.py: enter all ctx_patches,
    configure the AsanaClient mock, then make the request.
    """
    patches = _resolve_patches(resolve_results_or_error)
    *ctx_patches, mock_resolve = patches

    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in ctx_patches]  # type: ignore[arg-type]
        _make_async_client_mock(entered[4])  # index 4 is client_patch

        response = test_client.post(
            "/v1/resolve/unit",
            json={"criteria": [{"phone": "+15551234567", "vertical": "dental"}]},
            headers=AUTH_HEADER,
        )

    return response


# ---------------------------------------------------------------------------
# T-G01: Happy path
# ---------------------------------------------------------------------------


class TestResolverSpanHappyPath:
    """T-G01: resolver.entities.resolve on success."""

    def test_span_emitted_with_creation_and_output_attributes(
        self, otel_provider, test_client
    ):
        """Happy path emits span with entity_type, counts, project_gid, caller_service."""
        _, exporter = otel_provider

        resolved = ResolutionResult.from_gids(["1234567890123456"])
        _call_resolve(test_client, [resolved])

        spans = exporter.get_finished_spans()
        resolver_spans = [s for s in spans if s.name == "resolver.entities.resolve"]
        assert len(resolver_spans) == 1, (
            f"Expected 1 span named 'resolver.entities.resolve', got "
            f"{[s.name for s in spans]}"
        )

        span = resolver_spans[0]
        attrs = dict(span.attributes)

        assert attrs["resolver.entity_type"] == "unit"
        assert attrs["resolver.criteria_count"] == 1
        assert isinstance(attrs["resolver.project_gid"], str)
        assert len(attrs["resolver.project_gid"]) > 0
        assert isinstance(attrs["resolver.caller_service"], str)
        assert len(attrs["resolver.caller_service"]) > 0
        assert attrs["resolver.resolved_count"] == 1
        assert attrs["resolver.unresolved_count"] == 0
        assert span.status.status_code == StatusCode.UNSET

    def test_span_unresolved_count_when_not_found(self, otel_provider, test_client):
        """Happy path with NOT_FOUND result sets unresolved_count=1."""
        _, exporter = otel_provider

        not_found = ResolutionResult.not_found()
        _call_resolve(test_client, [not_found])

        spans = exporter.get_finished_spans()
        resolver_spans = [s for s in spans if s.name == "resolver.entities.resolve"]
        assert len(resolver_spans) == 1

        attrs = dict(resolver_spans[0].attributes)
        assert attrs["resolver.resolved_count"] == 0
        assert attrs["resolver.unresolved_count"] == 1


# ---------------------------------------------------------------------------
# T-G02: Tier 1 ServiceError
# ---------------------------------------------------------------------------


class TestResolverSpanServiceError:
    """T-G02: Tier 1 ServiceError sets error attributes and StatusCode.ERROR."""

    def test_service_error_sets_span_attributes(self, otel_provider, test_client):
        """ServiceError sets error_code, error_tier, error.type, and ERROR status."""
        _, exporter = otel_provider

        # Base ServiceError.error_code returns "SERVICE_ERROR"
        error = ServiceError("Test service error")
        _call_resolve(test_client, error)

        spans = exporter.get_finished_spans()
        resolver_spans = [s for s in spans if s.name == "resolver.entities.resolve"]
        assert len(resolver_spans) == 1

        span = resolver_spans[0]
        attrs = dict(span.attributes)

        assert attrs["resolver.error_code"] == "SERVICE_ERROR"
        assert attrs["resolver.error_tier"] == "service_error"
        assert attrs["error.type"] == "ServiceError"
        assert span.status.status_code == StatusCode.ERROR
        assert span.status.description == "SERVICE_ERROR"

        exception_events = [e for e in span.events if e.name == "exception"]
        assert len(exception_events) == 1


# ---------------------------------------------------------------------------
# T-G03: Tier 3 unexpected Exception
# ---------------------------------------------------------------------------


class TestResolverSpanUnexpectedError:
    """T-G03: Tier 3 Exception sets RESOLUTION_ERROR and unexpected tier."""

    def test_unexpected_exception_sets_span_attributes(
        self, otel_provider, test_client
    ):
        """RuntimeError sets error_code=RESOLUTION_ERROR, error_tier=unexpected."""
        _, exporter = otel_provider

        _call_resolve(test_client, RuntimeError("unexpected failure"))

        spans = exporter.get_finished_spans()
        resolver_spans = [s for s in spans if s.name == "resolver.entities.resolve"]
        assert len(resolver_spans) == 1

        span = resolver_spans[0]
        attrs = dict(span.attributes)

        assert attrs["resolver.error_code"] == "RESOLUTION_ERROR"
        assert attrs["resolver.error_tier"] == "unexpected"
        assert attrs["error.type"] == "RuntimeError"
        assert span.status.status_code == StatusCode.ERROR

        exception_events = [e for e in span.events if e.name == "exception"]
        assert len(exception_events) == 1

        event_attrs = dict(exception_events[0].attributes)
        assert "unexpected failure" in event_attrs.get("exception.message", "")


# ---------------------------------------------------------------------------
# T-G07: Tier 2 AsanaError
# ---------------------------------------------------------------------------


class TestResolverSpanAsanaError:
    """T-G07: Tier 2 AsanaError sets asana_error tier, no record_exception."""

    def test_asana_error_sets_tier_and_type_no_exception_event(
        self, otel_provider, test_client
    ):
        """AsanaError sets error_tier=asana_error, error.type, no exception event."""
        _, exporter = otel_provider

        _call_resolve(test_client, AsanaError("rate limited"))

        spans = exporter.get_finished_spans()
        resolver_spans = [s for s in spans if s.name == "resolver.entities.resolve"]
        assert len(resolver_spans) == 1

        span = resolver_spans[0]
        attrs = dict(span.attributes)

        assert attrs["resolver.error_tier"] == "asana_error"
        assert attrs["error.type"] == "AsanaError"
        assert span.status.status_code == StatusCode.ERROR

        # No record_exception on the re-raise path
        exception_events = [e for e in span.events if e.name == "exception"]
        assert len(exception_events) == 0
