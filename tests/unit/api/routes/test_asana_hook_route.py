"""D6 hook route through the FULL app: RT-1, JWT-1, IDEM-1, R-A1, HS, RL-1, RL-2, SZ-1,
ENC-1, LEAK-1, W F-1, W F-4, W F-14, W F-16, auth-bench A3-1 (TDD r4.10 sections 4, 9).

Every request here goes through ``create_app()`` with its real middleware stack (CORS,
JWT, SlowAPI, idempotency, request id, security headers, metrics) and the real
module-level limiter. Only these are test doubles: DynamoDB is moto behind the real
``HookRegistry``; the key store is the in-memory test adapter; the decider is a recorder;
the default rate limit is lowered so the RL fixtures stay small. Nothing reaches AWS or
Asana. Every handle, gid and hook value is generated at runtime.

The receiver is put on ``app.state`` by each test. Nothing in ``src/`` does that in this
PR, which is why the route is dark when deployed.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import secrets
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from slowapi.middleware import _get_route_name

from autom8_asana import lifecycle
from autom8_asana.api import main as main_module
from autom8_asana.api import rate_limit
from autom8_asana.api.main import _resolve_scopes_for_operation, create_app
from autom8_asana.api.middleware.idempotency import _is_eligible
from autom8_asana.api.rate_limit import limiter
from autom8_asana.trigger import hook_registry as hook_registry_module
from autom8_asana.trigger import hook_store as hook_store_module
from autom8_asana.trigger import liveness as liveness_module
from autom8_asana.trigger import receiver as receiver_module
from autom8_asana.trigger import registration as registration_module
from autom8_asana.trigger.hook_registry import DeliveryState, HookState
from autom8_asana.trigger.receiver import RECEIVER_STATE_ATTR, ShadowReceiver

# The trigger helpers, and its fixtures (aws_env, ddb_client, registry, store, clock,
# events, hex_handle), imported so this module, outside tests/unit/trigger/, can request
# them by name.
from tests.unit.trigger.conftest import (
    SHADOW_TEST_ENV,
    ActiveHook,
    CallCounter,
    FakeClock,
    LogSpy,
    RecordingDecider,
    aws_env,
    batch,
    clock,
    completion_event,
    ddb_client,
    events,
    hex_handle,
    make_active_hook,
    registry,
    runtime_gid,
    runtime_hook_value,
    sign,
    store,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tests.unit.trigger.adapters import InMemoryHookRegistry, InMemoryKeyHookStore

PREFIX = "/api/v1/webhooks"
HOOK_PATH = f"{PREFIX}/asana/{{handle}}"
# RT-1 / W F-1: exactly these routes under the JWT-excluded webhooks prefix.
WEBHOOK_ROUTE_SET = frozenset({("POST", f"{PREFIX}/inbound"), ("POST", HOOK_PATH)})
HOOK_HANDLER = "autom8_asana.api.routes.asana_hook.receive_asana_hook"
TINY_LIMIT = 3
HOOK_HEADER = "X-Hook-Secret"
SIG_HEADER = "X-Hook-Signature"


def webhook_prefix_routes(app: FastAPI) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path == PREFIX or path.startswith(PREFIX + "/"):
            for method in sorted(getattr(route, "methods", None) or {"*"}):
                found.add((method, path))
    return found


@pytest.fixture
def harness(
    monkeypatch: pytest.MonkeyPatch,
    registry: InMemoryHookRegistry,
    store: InMemoryKeyHookStore,
    clock: FakeClock,
) -> Iterator[SimpleNamespace]:
    """The full app, the shadow flag on, a receiver on app.state with one active hook."""
    monkeypatch.delenv("AUTH__DEV_MODE", raising=False)
    monkeypatch.setenv("ASANA_HOOK_SHADOW_ENABLED", "1")
    # The real settings object with only the default limit lowered (no stand-in class).
    tiny_limit_settings = rate_limit.get_settings().model_copy(
        update={"rate_limit_rpm": TINY_LIMIT}
    )
    monkeypatch.setattr(rate_limit, "get_settings", lambda: tiny_limit_settings)
    decider = RecordingDecider()
    hook = make_active_hook(registry, store, clock)
    receiver = ShadowReceiver(
        registry=registry,
        store=store,
        decider=decider,
        project_gids=[hook.project_gid],
        clock=clock,
        environ=dict(SHADOW_TEST_ENV),
    )
    asyncio.run(receiver.refresh_index())
    app = create_app()
    setattr(app.state, RECEIVER_STATE_ATTR, receiver)
    limiter.reset()
    # No context manager: the lifespan (startup discovery) is not needed.
    client = TestClient(app, raise_server_exceptions=False)
    yield SimpleNamespace(
        app=app,
        client=client,
        receiver=receiver,
        registry=registry,
        store=store,
        decider=decider,
        hook=hook,
        clock=clock,
    )
    limiter.reset()


def _post(h: SimpleNamespace, hook: ActiveHook, body: bytes, **headers: Any) -> Any:
    return h.client.post(
        f"{PREFIX}/asana/{hook.handle}",
        content=body,
        headers={SIG_HEADER: sign(hook.hook_value, body), **headers},
    )


# ---------------------------------------------------------------------------
# RT-1 / W F-1, W F-14: the route set under the JWT-excluded prefix
# ---------------------------------------------------------------------------


def test_webhooks_prefix_holds_exactly_the_two_routes() -> None:
    """RT-1, W F-1 (D6 TDD fixture or review id)."""
    assert webhook_prefix_routes(create_app()) == WEBHOOK_ROUTE_SET


def test_a_planted_route_under_the_webhooks_prefix_is_flagged() -> None:
    """RT-1 teeth (D6 TDD fixture or review id)."""
    app = create_app()
    planted = APIRouter(prefix=PREFIX)

    @planted.post("/asana")
    async def unauthenticated() -> dict[str, str]:
        return {}

    app.include_router(planted)
    assert webhook_prefix_routes(app) - WEBHOOK_ROUTE_SET == {("POST", f"{PREFIX}/asana")}


def test_unmounted_lifecycle_webhook_is_deleted_with_its_exports() -> None:
    """W F-14 (D6 TDD fixture or review id)."""
    assert importlib.util.find_spec("autom8_asana.lifecycle.webhook") is None
    for name in ("router", "AsanaWebhookPayload", "WebhookResponse"):
        assert not hasattr(lifecycle, name), name
        assert name not in lifecycle.__all__
    assert ("POST", f"{PREFIX}/asana") not in webhook_prefix_routes(create_app())


def test_jwt_exclusion_is_the_one_prefix_glob() -> None:
    """The hook route rides the existing exclusion; no new exclusion was added for it."""
    from pathlib import Path

    assert main_module.__file__ is not None
    text = Path(main_module.__file__).read_text()
    assert text.count('"/api/v1/webhooks/*"') == 1
    assert '"/api/v1/webhooks/asana' not in text.split("exclude_paths=")[1].split("]")[0]


# ---------------------------------------------------------------------------
# W F-1 through the full app: dark unless the flag is exactly "1"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", [None, "", "0", "true", "1 ", "1\n"])
def test_flag_off_route_is_404_with_zero_registry_or_store_calls(
    flag: str | None, harness: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, hex_handle: str
) -> None:
    """warden-bench F-1 (D6 TDD fixture or review id)."""
    counted_registry, counted_store = CallCounter(harness.registry), CallCounter(harness.store)
    receiver = ShadowReceiver(
        registry=counted_registry,
        store=counted_store,
        decider=harness.decider,
        project_gids=[harness.hook.project_gid],
        clock=harness.clock,
        environ=dict(SHADOW_TEST_ENV),
    )
    asyncio.run(receiver.refresh_index())
    counted_registry.calls.clear()
    setattr(harness.app.state, RECEIVER_STATE_ATTR, receiver)
    harness.registry.put_pending(
        handle=hex_handle, resource_gid=runtime_gid(), now=int(harness.clock())
    )
    if flag is None:
        monkeypatch.delenv("ASANA_HOOK_SHADOW_ENABLED")
    else:
        monkeypatch.setenv("ASANA_HOOK_SHADOW_ENABLED", flag)
    handshake = harness.client.post(
        f"{PREFIX}/asana/{hex_handle}", headers={HOOK_HEADER: runtime_hook_value()}
    )
    delivery = _post(harness, harness.hook, batch(completion_event()))
    assert (handshake.status_code, delivery.status_code) == (404, 404)
    assert HOOK_HEADER.lower() not in {k.lower() for k in handshake.headers}
    assert counted_registry.calls == [] and counted_store.calls == []
    record = harness.registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.PENDING


def test_flag_on_without_a_receiver_is_503_never_noop(harness: SimpleNamespace) -> None:
    """W F-4 (D6 TDD fixture or review id)."""
    delattr(harness.app.state, RECEIVER_STATE_ATTR)
    response = _post(harness, harness.hook, batch(completion_event()))
    assert response.status_code == 503
    assert harness.registry.query_undecided() == []


# ---------------------------------------------------------------------------
# JWT-1, R-A1: signature auth through the full app
# ---------------------------------------------------------------------------


def test_unsigned_post_through_the_full_app_is_signature_invalid(
    harness: SimpleNamespace,
) -> None:
    """JWT-1 (D6 TDD fixture or review id)."""
    response = harness.client.post(
        f"{PREFIX}/asana/{harness.hook.handle}", content=batch(completion_event())
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ASANA-AUTH-002"


def test_signed_post_through_the_full_app_is_200_and_decided(harness: SimpleNamespace) -> None:
    """JWT-1 twin (D6 TDD fixture or review id)."""
    body = batch(completion_event())
    response = _post(harness, harness.hook, body)
    assert (response.status_code, response.json()) == (200, {"status": "accepted"})
    (call,) = harness.decider.calls  # decided after the response (background task)
    row = harness.registry.get_delivery(harness.hook.handle, call.event_key)
    assert row is not None and row.state is DeliveryState.DECIDED


@pytest.mark.parametrize(
    "value",
    [b"", b"A" * 64, "é".encode() * 32, b"\xff" * 64, b"a" * 63],
    ids=["empty", "uppercase", "non-ascii", "high-bytes", "short"],
)
def test_bad_signature_header_is_401_never_400_or_500(
    value: bytes, harness: SimpleNamespace
) -> None:
    """R-A1 (D6 TDD fixture or review id)."""
    response = harness.client.post(
        f"{PREFIX}/asana/{harness.hook.handle}",
        content=batch(completion_event()),
        headers=[(SIG_HEADER.encode(), value)],
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ASANA-AUTH-002"
    assert harness.store.reads == 0


def test_garbage_json_with_a_wrong_signature_is_401(harness: SimpleNamespace) -> None:
    """R-A1 (D6 TDD fixture or review id)."""
    garbage = b"{definitely not json"
    response = harness.client.post(
        f"{PREFIX}/asana/{harness.hook.handle}",
        content=garbage,
        headers={SIG_HEADER: sign(runtime_hook_value(), garbage)},
    )
    assert response.status_code == 401


def test_token_query_parameter_is_not_auth_here(harness: SimpleNamespace) -> None:
    """The sibling /inbound URL token does not apply: a token alone is still 401."""
    response = harness.client.post(
        f"{PREFIX}/asana/{harness.hook.handle}?token=anything",
        content=batch(completion_event()),
    )
    assert response.status_code == 401


def test_hook_path_is_not_idempotency_eligible(harness: SimpleNamespace) -> None:
    """IDEM-1 (D6 TDD fixture or review id)."""
    assert _is_eligible("POST", f"{PREFIX}/asana/{harness.hook.handle}") is None


# ---------------------------------------------------------------------------
# Handshake through the full app (HS-1 to HS-4)
# ---------------------------------------------------------------------------


def test_pending_handle_handshake_echoes_once_in_the_header_only(
    harness: SimpleNamespace, hex_handle: str
) -> None:
    """HS-1 twin, HS-2 (D6 TDD fixture or review id)."""
    harness.registry.put_pending(
        handle=hex_handle, resource_gid=runtime_gid(), now=int(harness.clock())
    )
    value = runtime_hook_value()
    first = harness.client.post(f"{PREFIX}/asana/{hex_handle}", headers={HOOK_HEADER: value})
    assert first.status_code == 200
    assert first.headers[HOOK_HEADER] == value
    assert first.content == b"", "the value is never in a body"
    second = harness.client.post(
        f"{PREFIX}/asana/{hex_handle}", headers={HOOK_HEADER: runtime_hook_value()}
    )
    assert second.status_code == 403 and HOOK_HEADER not in second.headers
    record = harness.registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.COMPROMISED


def test_handshake_unknown_handle_is_404_and_store_failure_is_500(
    harness: SimpleNamespace, hex_handle: str
) -> None:
    """HS-1, HS-4 (D6 TDD fixture or review id)."""
    unknown = harness.client.post(
        f"{PREFIX}/asana/{hex_handle}", headers={HOOK_HEADER: runtime_hook_value()}
    )
    assert unknown.status_code == 404
    harness.registry.put_pending(
        handle=hex_handle, resource_gid=runtime_gid(), now=int(harness.clock())
    )
    harness.store.fail_create = True
    failed = harness.client.post(
        f"{PREFIX}/asana/{hex_handle}", headers={HOOK_HEADER: runtime_hook_value()}
    )
    assert failed.status_code == 500 and HOOK_HEADER not in failed.headers
    record = harness.registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.FAILED


def test_duplicated_handshake_header_is_refused(harness: SimpleNamespace, hex_handle: str) -> None:
    """HS-1 (D6 TDD fixture or review id)."""
    harness.registry.put_pending(
        handle=hex_handle, resource_gid=runtime_gid(), now=int(harness.clock())
    )
    response = harness.client.post(
        f"{PREFIX}/asana/{hex_handle}",
        headers=[(HOOK_HEADER.encode(), b"x" * 20), (HOOK_HEADER.encode(), b"y" * 20)],
    )
    assert response.status_code == 403
    record = harness.registry.get_hook(hex_handle)
    assert record is not None and record.state is HookState.PENDING


# ---------------------------------------------------------------------------
# RL-1, RL-2: a valid delivery is never 429 (TM-4)
# ---------------------------------------------------------------------------


def test_handler_name_is_pinned_in_the_limiter_exempt_set(harness: SimpleNamespace) -> None:
    """TM-4 (D6 TDD fixture or review id)."""
    assert HOOK_HANDLER in limiter._exempt_routes
    endpoints = [r.endpoint for r in harness.app.routes if getattr(r, "path", None) == HOOK_PATH]
    assert len(endpoints) == 1 and _get_route_name(endpoints[0]) == HOOK_HANDLER


def _flood_then_valid(harness: SimpleNamespace, forged_posts: int) -> None:
    body = batch(completion_event())
    forged = sign(runtime_hook_value(), body)
    url = f"{PREFIX}/asana/{harness.hook.handle}"
    statuses = {
        harness.client.post(url, content=body, headers={SIG_HEADER: forged}).status_code
        for _ in range(forged_posts)
    }
    assert statuses == {401}
    assert harness.store.reads <= 1, "KS-1 through the full app"
    assert _post(harness, harness.hook, body).status_code == 200


@pytest.mark.slow
def test_500_forged_posts_then_one_valid_post_is_200(harness: SimpleNamespace) -> None:
    """RL-1 at the TDD's volume, and KS-1 through the full app (about 4 s: marked slow)."""
    _flood_then_valid(harness, 500)


def test_forged_flood_past_the_budget_and_the_limit_then_one_valid_post_is_200(
    harness: SimpleNamespace,
) -> None:
    """RL-1, the fast form that runs on every PR: 40 forged posts exceed both the 30-a-minute
    failure budget and the lowered default limit, and the valid post is still 200."""
    _flood_then_valid(harness, 40)


def test_n_plus_one_valid_deliveries_are_all_200(harness: SimpleNamespace) -> None:
    """RL-2 (D6 TDD fixture or review id)."""
    statuses = [
        _post(harness, harness.hook, batch(completion_event())).status_code
        for _ in range(TINY_LIMIT + 1)
    ]
    assert statuses == [200] * (TINY_LIMIT + 1)


def test_the_same_volume_to_a_limited_route_is_429(harness: SimpleNamespace) -> None:
    """RL-1 and RL-2 teeth (D6 TDD fixture or review id)."""
    statuses = [harness.client.get("/docs").status_code for _ in range(TINY_LIMIT + 1)]
    assert 429 in statuses, "the tiny limit is live, so the RL twins are not vacuous"


# ---------------------------------------------------------------------------
# SZ-1, ENC-1 through the full app
# ---------------------------------------------------------------------------


def test_ten_mib_chunked_body_is_413_before_the_hmac(harness: SimpleNamespace) -> None:
    """SZ-1 (D6 TDD fixture or review id)."""
    chunk = b"x" * (1024 * 1024)

    def chunked() -> Any:
        for _ in range(10):
            yield chunk

    response = harness.client.post(
        f"{PREFIX}/asana/{harness.hook.handle}",
        content=chunked(),
        headers={SIG_HEADER: "a" * 64},
    )
    assert response.status_code == 413
    assert harness.store.reads == 0


def test_200_kib_body_passes(harness: SimpleNamespace) -> None:
    """SZ-1 twin (D6 TDD fixture or review id)."""
    padded = json.dumps({"events": [], "pad": "p" * (200 * 1024)}).encode()
    assert _post(harness, harness.hook, padded).status_code == 200


def test_gzip_body_is_415(harness: SimpleNamespace) -> None:
    """ENC-1 (D6 TDD fixture or review id)."""
    body = batch(completion_event())
    response = _post(harness, harness.hook, body, **{"Content-Encoding": "gzip"})
    assert response.status_code == 415


def test_raw_body_bytes_reach_the_route_unchanged(harness: SimpleNamespace) -> None:
    """ENC-1: No middleware rewrites the body: odd spacing and escapes still verify."""
    body = (
        b'{ "events" :[ {"action":"changed","created_at":"2026-11-13T19:00:00.000Z",'
        b'"resource":{"gid":"' + runtime_gid().encode() + b'","resource_type":"task"},'
        b'"user":{"gid":"' + runtime_gid().encode() + b'"},"note":"caf\\u00e9\\t"}  ]}\n'
    )
    response = _post(harness, harness.hook, body)
    assert response.status_code == 200
    (call,) = harness.decider.calls
    assert call.event["note"] == "café\t"


# ---------------------------------------------------------------------------
# W F-16, the OpenAPI contract: the hook is HMAC, never the URL token or a scope
# ---------------------------------------------------------------------------


def test_openapi_documents_the_signature_scheme_not_the_url_token() -> None:
    """W F-16 (D6 TDD fixture or review id)."""
    spec = create_app().openapi()
    operation = spec["paths"][HOOK_PATH]["post"]
    assert operation["security"] == [{"AsanaHookSignature": []}]
    assert "token" not in {p["name"] for p in operation.get("parameters", [])}
    scheme = spec["components"]["securitySchemes"]["AsanaHookSignature"]
    assert (scheme["in"], scheme["name"]) == ("header", "X-Hook-Signature")
    inbound = spec["paths"][f"{PREFIX}/inbound"]["post"]
    assert {"WebhookToken": []} in inbound["security"], "twin: /inbound keeps its URL token"


def test_scope_row_advertises_no_scope_for_the_hook() -> None:
    """W F-16 (D6 TDD fixture or review id)."""
    assert _resolve_scopes_for_operation(HOOK_PATH, "post") == []
    assert _resolve_scopes_for_operation(f"{PREFIX}/inbound", "post") == ["webhooks:receive"]


# ---------------------------------------------------------------------------
# LEAK-1 and auth-bench A3-1, through the full app
# ---------------------------------------------------------------------------


def _attach_span_exporter() -> Any:
    from opentelemetry import trace

    provider = trace.get_tracer_provider()
    if not hasattr(provider, "add_span_processor"):
        return None
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def test_hook_value_and_signature_appear_only_in_the_one_echo_header(
    harness: SimpleNamespace,
    hex_handle: str,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """LEAK-1, auth-bench A3-1 (D6 TDD fixture or review id)."""
    from prometheus_client import generate_latest

    spy = LogSpy()
    for module in (
        receiver_module,
        registration_module,
        liveness_module,
        hook_store_module,
        hook_registry_module,
    ):
        monkeypatch.setattr(module, "logger", spy)
    exporter = _attach_span_exporter()
    harness.registry.put_pending(
        handle=hex_handle, resource_gid=runtime_gid(), now=int(harness.clock())
    )
    value = runtime_hook_value()
    body = batch(completion_event())
    signature = sign(harness.hook.hook_value, body)
    responses = [
        harness.client.post(f"{PREFIX}/asana/{hex_handle}", headers={HOOK_HEADER: value}),
        harness.client.post(f"{PREFIX}/asana/{hex_handle}", headers={HOOK_HEADER: value}),
        harness.client.post(
            f"{PREFIX}/asana/{harness.hook.handle}", content=body, headers={SIG_HEADER: signature}
        ),
        harness.client.post(
            f"{PREFIX}/asana/{harness.hook.handle}",
            content=b"x",
            headers={SIG_HEADER: signature},
        ),
        harness.client.post(
            f"{PREFIX}/asana/{harness.hook.handle}",
            content=body,
            headers={SIG_HEADER: signature, "Content-Encoding": "gzip"},
        ),
    ]
    assert [r.status_code for r in responses] == [200, 403, 200, 401, 415]
    echo_headers = [r.headers.get(HOOK_HEADER) for r in responses]
    assert echo_headers == [value, None, None, None, None], "exactly one echo"

    captured = capfd.readouterr()
    surfaces = {
        "logs": repr(spy.events),
        "stdout": captured.out,
        "stderr": captured.err,
        "metrics": generate_latest().decode("utf-8", "replace"),
        "bodies": "".join(r.text for r in responses),
        "other_headers": repr([dict(r.headers) for r in responses[1:]]),
    }
    assert exporter is not None, "the app sets an SDK tracer provider; spans are captured"
    spans = exporter.get_finished_spans()
    assert spans, "positive control: the requests produced spans"
    surfaces["spans"] = repr([(span.name, dict(span.attributes or {})) for span in spans])
    for name, text in surfaces.items():
        assert value not in text, f"the handshake value leaked into {name}"
        assert signature not in text, f"the signature leaked into {name}"
        assert harness.hook.hook_value not in text, f"the stored key leaked into {name}"
    # auth-bench A3-1: the route's logs never carry the handle, at any level.
    assert len(spy.events) >= 5, "positive control: the route logged"
    for handle in (hex_handle, harness.hook.handle):
        assert handle not in surfaces["logs"]
        assert handle not in captured.out and handle not in captured.err
