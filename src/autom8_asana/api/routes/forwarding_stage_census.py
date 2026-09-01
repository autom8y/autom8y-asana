"""Forwarding-Stage census read route — the tripwire's second operand.

``GET /v1/forwarding-stage/census``

READ-ONLY. This route performs Asana ``GET`` requests and returns counts. It has
no write class, no ``require_write_authz`` dependency, and no Asana mutation on
any path -- which is also why SEC-001's deny-by-default write-class
authorization does not apply to it (that gate is per-route opt-in via the route
decorator's ``dependencies=``, and reads are explicitly out of its scope; see
``tests/unit/api/test_write_authz_coverage.py`` GUARD-1's own
``test_red_guard_does_not_trip_on_reads``).

★ WHY THIS ROUTE EXISTS
------------------------
It supplies the SECOND OPERAND of the EBI F3 cross-source tripwire
(autom8y#1834, ``funnel_liveness.StageOfRecordCounter``). Without it the
tripwire can only ever report ``STAGE_OF_RECORD_UNAVAILABLE``: it can neither
agree nor disagree, and a tripwire with one operand is a different artifact than
the one specified -- not a partial one.

The tripwire's job is to make a self-emptied DynamoDB keyspace's ``scanned: 0``
distinguishable from a healthy zero. It can only do that against a source that
shares NO failure mode with the keyspace. The Asana Forwarding Stage field is
that source: different service, different store, no TTL, no claim protocol.

★ IDENTITY — NO NEW PRINCIPAL
------------------------------
This route sits on the SAME ``s2s_router`` and takes the SAME
``require_service_claims`` dependency as ``/v1/receipts``, which the EBI caller
already authenticates to today as ``sa_e92a…94`` (observed live: 1140
``receipts:write`` harvest receipts at tier ``client_id`` over 10 days). It
therefore mints nothing, requires no new credential, and introduces no new
principal.

That is a deliberate constraint, not an accident of reuse. U-4's whole finding
(``FINDING-u4-nudge-lambda-client-id-2026-09-01.md``) is that a caller
presenting a DIFFERENT principal becomes structurally invisible to the
OBSERVE-mode allowlist harvest -- authentication precedes authorization, so a
caller that cannot authenticate never reaches the gate that emits the harvest
receipt. Creating a second instance of that class while closing the first would
be a self-inflicted repeat of the exact defect.

★ REFUSAL, NOT A SMALLER NUMBER
--------------------------------
Every degraded read raises. The route NEVER returns a count it cannot vouch for,
because an under-reported Verified count makes the tripwire produce a FALSE
DISAGREE -- and a tripwire that cries wolf discredits itself faster than one
that stays silent. See ``services/forwarding_stage_census`` for the four refusal
conditions and why each would otherwise surface as a plausible ``0``.
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
from autom8_asana.api.error_responses import authenticated_responses
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.forwarding_stage_census_models import (
    ForwardingStageCensusResponse,
)
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.services.forwarding_stage_census import (
    StageCensusEmptyCorpus,
    StageCensusError,
    StageCensusFieldAbsent,
    StageCensusTruncated,
    StageCensusUnconfigured,
    census,
)

__all__ = ["router"]

logger = get_logger(__name__)

router = s2s_router(prefix="/v1/forwarding-stage", tags=["forwarding-stage"])


@router.get(
    "/census",
    response_model=SuccessResponse[ForwardingStageCensusResponse],
    # The refusal taxonomy is PUBLISHED, not merely documented in the docstring.
    # For this route the refusals ARE the contract: a consumer that treats a 502
    # as an unexpected error rather than a first-class "I cannot vouch for a
    # number" would either retry into a wall or, worse, fall back to a default
    # count -- reintroducing the ambiguous zero from the client side after the
    # server refused to produce it. A generated client must see these.
    #
    # ``authenticated_responses()`` supplies the fleet-standard 401/403 entries.
    # It is REQUIRED, not decorative: those entries declare the 401 body as
    # ``oneOf[ErrorResponse, AuthTebError]``, and the auth middleware emits the
    # AUTH-TEB shape (no ``meta`` key). A route that documents only
    # ``ErrorResponse`` therefore publishes a contract its own 401 violates --
    # which the schemathesis fuzz suite catches, correctly. Declaring the
    # refusal taxonomy below WITHOUT this would have replaced a documentation
    # gap with a documentation LIE.
    responses={
        **authenticated_responses(),
        502: {
            "description": (
                "REFUSED -- the census could not be vouched for. "
                "STAGE_CENSUS_TRUNCATED (completeness unproven: page ceiling, or "
                "a brim-full page whose continuation token a confirmation read "
                "falsified), STAGE_CENSUS_EMPTY_CORPUS (zero tasks -- an empty "
                "project and a wrong project gid are one shape), or "
                "STAGE_CENSUS_FIELD_ABSENT (no drained task carries the field). "
                "NOT retryable without investigation; NEVER interpret as zero."
            )
        },
        503: {
            "description": (
                "REFUSED -- STAGE_CENSUS_UNCONFIGURED (field gid or Verified "
                "option gid unset) or ASANA_UNAVAILABLE (degraded upstream "
                "read). Retryable. NEVER interpret as zero Verified clinics."
            )
        },
    },
    openapi_extra={
        # Declared READ-ONLY. This route makes Asana GET calls only; there is no
        # write class to gate. The absence of x-fleet-side-effects here is the
        # machine-readable counterpart of the human claim in the docstring.
        "x-fleet-read-only": True,
        "x-fleet-cross-service-refs": {
            "service": "autom8y",
            "entity": "forwarding_stage_census",
        },
    },
)
async def get_forwarding_stage_census(
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[ForwardingStageCensusResponse]:
    """Return a TOTAL Forwarding-Stage census, or refuse with a typed error.

    Authentication: S2S JWT only, via the same ``require_service_claims``
    dependency ``/v1/receipts`` uses. No new principal (see module docstring).

    Returns:
        200: SuccessResponse[ForwardingStageCensusResponse]. ``verified_count``
             is a TOTAL over the whole Calendar Integrations project. The
             ``stage_counts`` values sum to ``field_present_count`` (partition
             invariant, asserted service-side), so the operand is auditable.

    Error Responses -- each is a refusal to report a number that cannot be
    vouched for, NEVER a degraded count:
        - 401 MISSING_AUTH / SERVICE_TOKEN_REQUIRED: auth failures (S2S only)
        - 503 STAGE_CENSUS_UNCONFIGURED: the Forwarding Stage field gid or the
          Verified option gid is unset. An unconfigured census would report 0
          Verified with total confidence.
        - 502 STAGE_CENSUS_TRUNCATED: completeness could not be PROVEN -- the
          page ceiling was reached, or the absent-fuel invariant tripped (a
          brim-full page with no continuation token). This is the S-3 defect
          class refused at the source.
        - 502 STAGE_CENSUS_EMPTY_CORPUS: the project returned zero tasks. An
          empty project and a wrong project gid are indistinguishable here.
        - 502 STAGE_CENSUS_FIELD_ABSENT: tasks drained but none carries the
          field -- a configuration defect that reads like "nobody is Verified".
        - 503 ASANA_UNAVAILABLE: any other degraded read.
    """
    start_time = time.monotonic()
    settings = get_settings()

    logger.info(
        "forwarding_stage_census_request",
        extra={"request_id": request_id, "caller_service": claims.service_name},
    )

    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            result = await census(
                client,
                field_gid=settings.forwarding_stage_field_gid,
                option_gids=dict(settings.forwarding_stage_option_gids or {}),
                max_pages=settings.forwarding_stage_census_max_pages,
            )
    except StageCensusUnconfigured as exc:
        raise_api_error(request_id, 503, "STAGE_CENSUS_UNCONFIGURED", str(exc))
    except StageCensusTruncated as exc:
        raise_api_error(request_id, 502, "STAGE_CENSUS_TRUNCATED", str(exc))
    except StageCensusEmptyCorpus as exc:
        raise_api_error(request_id, 502, "STAGE_CENSUS_EMPTY_CORPUS", str(exc))
    except StageCensusFieldAbsent as exc:
        raise_api_error(request_id, 502, "STAGE_CENSUS_FIELD_ABSENT", str(exc))
    except StageCensusError as exc:
        # The taxonomy's catch-all. Still a REFUSAL -- never an empty census.
        raise_api_error(request_id, 503, "ASANA_UNAVAILABLE", str(exc))
    except Exception as exc:  # BROAD-CATCH: boundary
        # Nothing may escape as a 200. A leaked exception that some caller
        # interpreted as "no Verified clinics" is the precise ambiguity this
        # route exists to make impossible (S-3 critic F-6, same correction).
        logger.exception(
            "forwarding_stage_census_unexpected_error",
            extra={"request_id": request_id, "error_type": type(exc).__name__},
        )
        raise_api_error(
            request_id,
            503,
            "ASANA_UNAVAILABLE",
            f"forwarding-stage census failed ({type(exc).__name__}); "
            "refusing rather than reporting an unvouchable count.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "forwarding_stage_census_complete",
        extra={
            "request_id": request_id,
            "verified_count": result.verified_count,
            "tasks_scanned": result.tasks_scanned,
            "pages_drained": result.pages_drained,
            "elapsed_ms": round(elapsed_ms, 2),
        },
    )

    return build_success_response(
        data=ForwardingStageCensusResponse(
            verified_count=result.verified_count,
            tasks_scanned=result.tasks_scanned,
            field_present_count=result.field_present_count,
            stage_counts=result.stage_counts,
            pages_drained=result.pages_drained,
        ),
        request_id=request_id,
    )
