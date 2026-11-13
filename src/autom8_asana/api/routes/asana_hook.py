"""``POST /api/v1/webhooks/asana/{handle}``: the D6 shadow receiver route (A3, DARK).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.10, sections 3 and 4;
fixtures RT-1, JWT-1, IDEM-1, R-A1, HS-1 to HS-4, RL-1, RL-2, KS-1, SZ-1, ENC-1, LEAK-1
(section 9).

This module is HTTP only. Verification, persistence and the handshake live in
``trigger.receiver``; this route hands it the raw header bytes and the raw body stream,
and turns the result into a response.

Authentication is Asana's per-webhook HMAC, ``X-Hook-Signature`` over the raw body. It is
not JWT (the prefix is JWT-excluded, main.py) and it is not the ``?token=`` URL token of
the sibling ``/inbound`` route: no query parameter is read here.

DARK. The route answers 404 to every request, and touches nothing, unless
``ASANA_HOOK_SHADOW_ENABLED`` is exactly ``"1"`` (warden-bench F-1). With the flag on and
no receiver on ``app.state`` it answers 503: it never degrades to a noop (W F-4). Nothing
in this PR puts a receiver on ``app.state``.

The handler is exempt from the global SlowAPI limit, so a valid delivery never gets 429
(TM-4, RL-1, RL-2). SlowAPI matches the exemption by the handler's qualified name,
``autom8_asana.api.routes.asana_hook.receive_asana_hook``; a test pins it.

The handle is never logged here, at any level (auth-bench A3-1). The handshake value and
the signature are never logged and never appear in an error body (LEAK-1); the value
appears only in the one ``X-Hook-Secret`` echo header of a successful handshake.
"""

from __future__ import annotations

from typing import ClassVar, NoReturn

from autom8y_api_schemas.errors import (
    AsanaAuthenticationError,
    AsanaDependencyError,
    AsanaError,
    AsanaNotFoundError,
    AsanaPermissionError,
    AsanaRateLimitError,
    AsanaValidationError,
)
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response

from autom8_asana.api.error_responses import authenticated_responses
from autom8_asana.api.models import ErrorResponse
from autom8_asana.api.rate_limit import exempt_from_rate_limit
from autom8_asana.trigger.hook_environment import shadow_flag_on
from autom8_asana.trigger.liveness import RequestOutcome, record_request
from autom8_asana.trigger.receiver import (
    HOOK_SECRET_HEADER,
    RECEIVER_STATE_ATTR,
    ReceiveResult,
    ShadowReceiver,
)

# Raw APIRouter, as for /inbound: the HMAC is the auth, and SecureRouter would add JWT.
router = APIRouter(prefix="/api/v1/webhooks", tags=["asana-hook"])

HOOK_ROUTE_PATH = "/asana/{handle}"


class AsanaHookSignatureInvalidError(AsanaAuthenticationError):
    """A delivery's ``X-Hook-Signature`` is missing, malformed or does not verify.

    Canonical namespace ``asana.webhook.signature_invalid``, wire code ``ASANA-AUTH-002``
    (the fleet registry's code for an invalid webhook signature). Every signature failure
    shares it, so the response tells a caller nothing about which check failed.
    """

    code: ClassVar[str] = "ASANA-AUTH-002"
    message: ClassVar[str] = "Webhook signature invalid"


class AsanaHookNotFoundError(AsanaNotFoundError):
    message: ClassVar[str] = "Not found"


class AsanaHookForbiddenError(AsanaPermissionError):
    message: ClassVar[str] = "Refused"


class AsanaHookPayloadTooLargeError(AsanaValidationError):
    status_code: ClassVar[int] = 413
    message: ClassVar[str] = "Request body is too large"


class AsanaHookEncodingRefusedError(AsanaValidationError):
    status_code: ClassVar[int] = 415
    message: ClassVar[str] = "Content-Encoding must be absent or identity"


class AsanaHookBodyInvalidError(AsanaValidationError):
    message: ClassVar[str] = "Request body is not a webhook event batch"


class AsanaHookThrottledError(AsanaRateLimitError):
    message: ClassVar[str] = "Too many handshakes"


class AsanaHookInternalError(AsanaError):
    message: ClassVar[str] = "Webhook receiver error"


class AsanaHookUnavailableError(AsanaDependencyError):
    status_code: ClassVar[int] = 503
    message: ClassVar[str] = "Webhook receiver is unavailable"


_ERRORS: dict[int, type[AsanaError]] = {
    400: AsanaHookBodyInvalidError,
    401: AsanaHookSignatureInvalidError,
    403: AsanaHookForbiddenError,
    404: AsanaHookNotFoundError,
    413: AsanaHookPayloadTooLargeError,
    415: AsanaHookEncodingRefusedError,
    429: AsanaHookThrottledError,
    500: AsanaHookInternalError,
    503: AsanaHookUnavailableError,
}


def _error_doc(description: str) -> dict[str, object]:
    return {"model": ErrorResponse, "description": description}


_RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": (
            "A handshake echoed (empty body, X-Hook-Secret header), or a delivery verified "
            "and persisted"
        )
    },
    **authenticated_responses(),
    400: _error_doc("The verified body is not an event batch"),
    404: _error_doc("Unknown handle, or the receiver is off"),
    413: _error_doc("Body over 256 KiB"),
    415: _error_doc("Content-Encoding other than identity"),
    429: _error_doc("Handshake bucket exhausted (never sent for a delivery)"),
    500: _error_doc("Key read, registry read or persist failed; Asana retries"),
    503: _error_doc("The receiver is on but not built"),
}


def _raise_for(result: ReceiveResult) -> NoReturn:
    error = _ERRORS.get(result.status_code, AsanaHookInternalError)
    raise error()


@router.post(
    HOOK_ROUTE_PATH,
    summary="Receive an Asana webhook delivery or handshake (D6 shadow, signature auth)",
    response_description="Echoed handshake, or a verified and persisted delivery",
    responses=_RESPONSES,
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "dynamodb", "target": "hook_registry.delivery"},
            {"type": "secrets_manager", "target": "webhook_hook_value"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": "event-content-sha256"},
    },
)
@exempt_from_rate_limit
async def receive_asana_hook(
    handle: str, request: Request, background_tasks: BackgroundTasks
) -> Response:
    """Asana webhook target. Signature-authenticated; no JWT, no URL token.

    A request carrying ``X-Hook-Secret`` is a handshake: 200 echoes the value in the
    ``X-Hook-Secret`` response header, once, for a pending handle. Every other request is
    a delivery: it is verified against ``X-Hook-Signature`` over the raw body, persisted,
    and answered 200; the decision runs after the response. Refusals: 401 for any
    signature failure, 403 for an inactive hook, 404 for an unknown handle, 413 over
    256 KiB, 415 for a compressed body, 500 when a dependency fails (Asana retries).
    """
    # warden-bench F-1: dark unless the flag is exactly "1". Nothing is touched first.
    if not shadow_flag_on():
        record_request(RequestOutcome.SHADOW_OFF)
        raise AsanaHookNotFoundError()
    receiver = getattr(request.app.state, RECEIVER_STATE_ATTR, None)
    if not isinstance(receiver, ShadowReceiver):
        record_request(RequestOutcome.RECEIVER_UNAVAILABLE)
        raise AsanaHookUnavailableError()

    raw_headers: list[tuple[bytes, bytes]] = list(request.scope.get("headers", []))
    hook_values = [value for key, value in raw_headers if key.lower() == HOOK_SECRET_HEADER]
    if hook_values:
        sent = hook_values[0].decode("latin-1") if len(hook_values) == 1 else None
        result = await receiver.handshake(handle=handle, hook_header=sent)
        if result.status_code == 200 and result.echo is not None:
            return Response(status_code=200, headers={"X-Hook-Secret": result.echo})
        _raise_for(result)

    result = await receiver.receive(handle=handle, raw_headers=raw_headers, body=request.stream())
    if result.status_code != 200:
        _raise_for(result)
    if result.deliveries:
        background_tasks.add_task(receiver.decide_after_response, result.deliveries)
    return JSONResponse(status_code=200, content={"status": "accepted"})
