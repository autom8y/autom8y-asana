"""EBI OI-2 forwarding-receipt route.

POST /v1/receipts - thread an internal forwarding-lifecycle receipt onto the
clinic's Business task as an Asana comment.

The EBI ``AsanaReceiptClient`` (autom8y satellite, branch
``ebi/s4-loud-receipt-nudge``) POSTs ``{company_id, kind, body}`` here; this
service resolves the Business task from ``company_id`` (LIVE tasks/search,
fail-closed) and threads the comment (idempotent via a content marker). EBI
never sees a task gid -- surface minimisation; this satellite owns the
``company_id -> task_gid`` resolution (F-1 single-source lesson).

Authentication:
    S2S JWT only (``require_service_claims``). PAT tokens are NOT supported.
    Asana writes use the bot PAT (``auth_context.asana_pat`` in JWT mode).

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

    # 2. Orchestrate: resolve -> dedup -> post.
    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            service = ReceiptsService(client, company_id_field_gid=settings.company_id_field_gid)
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
