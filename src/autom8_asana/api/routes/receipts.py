"""EBI OI-2 forwarding-receipt route.

POST /v1/receipts - thread an internal forwarding-lifecycle receipt onto the
clinic's Business task as an Asana comment.

The EBI ``AsanaReceiptClient`` (autom8y satellite, branch
``ebi/s4-loud-receipt-nudge``) POSTs ``{company_id, kind, body}`` here; this
service resolves the Business task from ``company_id`` (LIVE tasks/search,
fail-closed) and threads the comment (idempotent via a content marker). EBI
never sees a task gid -- surface minimisation; this satellite owns the
``company_id -> task_gid`` resolution (F-1 single-source lesson).

Authentication (two layers -- state the truth precisely):
    OUTER: the fleet ``JWTAuthMiddleware`` (``autom8y_auth``, wired via
    ``create_fleet_app(jwt_auth=...)``) runs ahead of the route. In PRODUCTION
    (``AUTH__DEV_MODE`` unset/false) it validates the JWT signature against JWKS
    and rejects a missing/malformed/invalid token with an ``AUTH-TEB-NNN`` 401.
    A missing Authorization header ALWAYS rejects (``AUTH-TEB-001``) because the
    header check precedes the dev bypass.

    INNER (load-bearing in the test suite): ``Depends(require_service_claims)``.
    Under ``AUTH__DEV_MODE=true`` -- which the unit tests set -- the outer
    middleware bypasses SIGNATURE validation and returns dev-bypass claims for
    ANY present token, so signature-rejection is NOT exercised by the unit
    tests. What the tests exercise is this inner dependency's fail-closed leg: it
    re-invokes ``validate_service_token`` and rejects a PAT-shaped token
    (``SERVICE_TOKEN_REQUIRED`` 401) or a validation failure. PAT tokens are NOT
    supported. Asana writes use the bot PAT (``auth_context.asana_pat`` in JWT
    mode).

    TODO(COND-2): no production-mode (``AUTH__DEV_MODE=false``) middleware JWKS
    integration test exists in this harness -- the auth suite mocks
    ``validate_service_token`` at the jwt_validator seam (see
    tests/unit/auth/test_integration.py::test_invalid_signature_returns_401)
    rather than minting a real RS256-signed token against a JWKS fixture. Add a
    genuine outer-middleware signature-rejection integration test once such an
    idiom lands fleet-wide.

D12: the comment threads onto the TEAM's INTERNAL Business task -- never a
client-facing message. This route has no outward channel.
"""

from __future__ import annotations

import time
from typing import Annotated

from autom8y_log import get_logger
from fastapi import Depends

from autom8_asana import AsanaClient
from autom8_asana.api.config import get_settings
from autom8_asana.api.dependencies import (  # noqa: TC001 -- FastAPI resolves these at runtime
    AuthContextDep,
    RequestId,
)
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.api.routes.receipts_models import (
    ReceiptKind,
    ReceiptPostRequest,
    ReceiptPostResponse,
)
from autom8_asana.services.receipts_service import (
    CompanyAmbiguous,
    CompanyIdFieldUnconfigured,
    CompanyNotResolved,
    ForwardingStageWriteConfig,
    NoWorkspaceConfigured,
    ReceiptsService,
)

__all__ = ["router"]

logger = get_logger(__name__)

router = s2s_router(prefix="/v1", tags=["receipts"], include_in_schema=False)


@router.post(
    "/receipts",
    response_model=SuccessResponse[ReceiptPostResponse],
    openapi_extra={
        "x-fleet-side-effects": [
            {"type": "asana_api", "target": "business_task_comment"},
        ],
        "x-fleet-idempotency": {"idempotent": True, "key_source": "content-marker"},
        "x-fleet-cross-service-refs": {
            "service": "autom8y",
            "entity": "forwarding_receipt",
        },
    },
)
async def post_receipt(
    body: ReceiptPostRequest,
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[ReceiptPostResponse]:
    """Thread one forwarding-lifecycle receipt onto the clinic's Business task.

    Authentication: S2S JWT only (require_service_claims dependency).

    Request Body:
        ReceiptPostRequest = {company_id: str≥1, kind: str, body: str≥1}
        (the frozen EBI consumer shape).

    Returns:
        200: SuccessResponse[{business_gid, story_gid, outcome}] where
             outcome ∈ {"posted", "skipped_duplicate"}.

    Error Responses:
        - 401 MISSING_AUTH / SERVICE_TOKEN_REQUIRED: auth failures (S2S only)
        - 404 COMPANY_NOT_RESOLVED: no Business task carries this company_id
        - 409 COMPANY_AMBIGUOUS: >1 Business task carries this company_id
        - 422 UNKNOWN_RECEIPT_KIND: kind ∉ the four ReceiptKind literals
        - 503 COMPANY_ID_FIELD_UNCONFIGURED: OI-2b field GID not configured
        - 503 ASANA_UNAVAILABLE: Asana API failure
    """
    start_time = time.monotonic()

    logger.info(
        "forwarding_receipt_request",
        extra={
            "request_id": request_id,
            "kind": body.kind,
            "caller_service": claims.service_name,
        },
    )

    # 1. Validate kind -- fail-LOUD on contract drift (a new EBI kind shipped
    #    without a provider update surfaces as a 422, not a malformed comment).
    if body.kind not in {k.value for k in ReceiptKind}:
        raise_api_error(
            request_id,
            422,
            "UNKNOWN_RECEIPT_KIND",
            f"Unknown receipt kind: {body.kind}. "
            f"Valid: {', '.join(sorted(k.value for k in ReceiptKind))}",
        )

    settings = get_settings()

    # 2. Orchestrate: resolve -> dedup -> post (+ config-gated stage advance).
    #    The stage-write config is built from settings; when the master switch is
    #    OFF (default) the write leg is INERT and the route behaves identically to
    #    the comment-only baseline (ADR-FS-004 / T-W1).
    stage_write_config = ForwardingStageWriteConfig.from_settings(
        enabled=settings.forwarding_stage_write_enabled,
        field_gid=settings.forwarding_stage_field_gid,
        option_gids=settings.forwarding_stage_option_gids,
        disposition=settings.forwarding_stage_disposition,
    )
    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = ReceiptsService(
                client,
                company_id_field_gid=settings.company_id_field_gid,
                stage_write_config=stage_write_config,
            )
            result = await service.thread_receipt(
                company_id=body.company_id,
                kind=body.kind,
                body=body.body,
            )
    except CompanyNotResolved as exc:
        raise_api_error(request_id, 404, "COMPANY_NOT_RESOLVED", str(exc))
    except CompanyAmbiguous as exc:
        raise_api_error(
            request_id,
            409,
            "COMPANY_AMBIGUOUS",
            str(exc),
            details={"gids": exc.gids},
        )
    except CompanyIdFieldUnconfigured as exc:
        raise_api_error(request_id, 503, "COMPANY_ID_FIELD_UNCONFIGURED", str(exc))
    except NoWorkspaceConfigured as exc:
        raise_api_error(request_id, 503, "ASANA_UNAVAILABLE", str(exc))
    except Exception as exc:  # BROAD-CATCH: boundary
        logger.exception(
            "forwarding_receipt_error",
            extra={
                "request_id": request_id,
                "kind": body.kind,
                "error": str(exc),
            },
        )
        # retry-429-only-never-POST-5xx: the AsanaClient transport already
        # retries idempotent reads on 429; an unrecoverable Asana failure
        # (including a POST-5xx, which is NEVER blind-retried) becomes a 503.
        # The EBI consumer raises; the FanOutReceiptSink swallows it (an Asana
        # failure never halts the pipeline nor blocks the Slack mirror).
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            "Failed to thread forwarding receipt. Asana service unavailable.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "forwarding_receipt_complete",
        extra={
            "request_id": request_id,
            "business_gid": result.business_gid,
            "story_gid": result.story_gid,
            "outcome": result.outcome,
            "kind": body.kind,
            "duration_ms": round(elapsed_ms, 2),
            "caller_service": claims.service_name,
        },
    )

    return build_success_response(data=result, request_id=request_id)
