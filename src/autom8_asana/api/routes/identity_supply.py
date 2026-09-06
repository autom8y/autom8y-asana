"""The id-walk identity-evidence exposure -- the ``[asana]`` half of the substrate.

``GET /v1/identity-supply/{offer_gid}``

READ-ONLY. One offer gid, one walk, the supply's own typed objects back. No
batch, no list, no write of any kind.

WHY THIS ROUTE EXISTS
---------------------
``supply_identity_evidence_async`` landed with ZERO production callers: the
supply runs in ``[asana]``, and seat A -- the appender that consumes it -- has
custody in ``[data]`` (ADR §14.1). The transport between them is S2S over the
pattern ``[data]`` already calls this service with, not a package dependency:
``[data]`` carries ``AsanaEnrichmentSettings`` today, and a dependency bump
would additionally have to clear ``[data]``'s own required
``dependency-boundary-gate``. This route is that transport's ``[asana]`` end.

★ NO WRITE VERB IS REACHABLE
-----------------------------
The reachable call graph from this handler bottoms out in exactly three Asana
client verbs, ALL reads:

  * ``client.tasks.get_async``      -- the entry fetch and every parent hop
  * ``client.tasks.subtasks_async`` -- tier-4 structure inspection
  * ``client.projects.list_async``  -- lazy workspace discovery, only when a
    project gid is absent from the static registry

That census is asserted mechanically, over the import-resolved call graph, in
``tests/unit/api/routes/test_identity_supply_route.py`` (with a positive
control proving the census can see a write verb where one exists). The docstring
on ``walk_business_candidates_async`` names only the first two because tier-1
discovery is a third-party hop it does not own -- naming all three here is the
correction, not a widening: every one of them is a GET.

★ THE TIER-4 REFUSAL ARM IS CARRIED, NOT SMOOTHED
--------------------------------------------------
A self-flagged tier-4 identification reaches the wire as it left the supply:
``value=null``, ``absent_reason="undecidable"``, ``detection_tier=4``,
``needs_healing=true``. The route does not downgrade it, does not drop the
discriminators, and does not turn it into an error. ``CONFIDENCE_TIER_4 = 0.9``
is the SECOND-HIGHEST confidence in the detector's set, so a consumer screening
on the number would read a self-flagged structure-inspection identification as
near-certain -- which is exactly why the flag, not the number, is what crosses.

★ THE GID IS DIGITS-VALIDATED HERE, UNCONDITIONALLY
----------------------------------------------------
The path parameter carries its own ``^[0-9]{1,64}$`` pattern rather than the
shared ``GidStr`` alias. ``GidStr``'s constraint is env-conditional
(``api/models.py:46-54``: the pattern is ``None`` under ``AUTOM8Y_ENV`` in
test/local so fixtures may use readable gids), so a route relying on it would
have a validation claim that no test in this repo could falsify. An
unconditional pattern is testable in every environment and is a strictly
higher bar than the incumbent -- the shared alias is the floor, not the target.

★ IDENTITY -- NO NEW PRINCIPAL
-------------------------------
The same ``s2s_router`` and the same ``require_service_claims`` dependency
``/v1/receipts`` and ``/v1/forwarding-stage/census`` already take, and the
existing ``query:read`` scope rather than a minted ``identity-supply:read``.
Nothing new is provisioned. A caller presenting a principal the fleet has not
provisioned goes dark BEFORE any authorization gate can observe it -- the U-4
class (``FINDING-u4-nudge-lambda-client-id-2026-09-01.md``) -- and creating a
second instance of it here would be self-inflicted.

★ REFUSALS
-----------
The supply types its own absences: an unreachable offer comes back as
``resolver_unavailable`` evidence, not as an HTTP error, and that disposition
belongs to the supply, not to this route. What the route adds is the guarantee
that nothing escapes as an untyped 500 with a stack: any exception the supply
lets through becomes a typed 503, and a supply whose evidence objects disagreed
on ``basis_version`` becomes a typed 502 rather than an envelope asserting a
version its own rows do not share.
"""

from __future__ import annotations

import time
from typing import Annotated

from autom8y_log import get_logger
from fastapi import Depends, Path

from autom8_asana import AsanaClient
from autom8_asana.api.dependencies import (  # noqa: TC001 -- FastAPI resolves these at runtime
    AuthContextDep,
    RequestId,
)
from autom8_asana.api.error_responses import authenticated_responses
from autom8_asana.api.errors import raise_api_error
from autom8_asana.api.models import SuccessResponse, build_success_response
from autom8_asana.api.routes._security import s2s_router
from autom8_asana.api.routes.identity_supply_models import (
    BasisVersionConflict,
    IdentitySupplyResponse,
    build_identity_supply_response,
)
from autom8_asana.api.routes.internal import (
    ServiceClaims,
    require_service_claims,
)
from autom8_asana.models.business.identity_supply import supply_identity_evidence_async

__all__ = ["OFFER_GID_PATTERN", "router"]

logger = get_logger(__name__)

#: Asana gids are decimal strings. Declared as a module constant so the guard is
#: one object a test can pin, and unconditional so the pattern is the same in
#: every environment (see the module docstring on ``GidStr``).
OFFER_GID_PATTERN = r"^[0-9]{1,64}$"

OfferGid = Annotated[
    str,
    Path(
        pattern=OFFER_GID_PATTERN,
        examples=["3000000000000001"],
        description=(
            "The `contract.offer_gid` carried on the producer's rows. Digits "
            "only; anything else is rejected with 422 before any Asana read."
        ),
    ),
]

router = s2s_router(prefix="/v1/identity-supply", tags=["identity-supply"])


@router.get(
    "/{offer_gid}",
    summary="Supply id-walk identity evidence for one offer gid",
    response_description="The supply's typed evidence objects and candidate set",
    response_model=SuccessResponse[IdentitySupplyResponse],
    responses={
        **authenticated_responses(),
        422: {
            "description": (
                "REFUSED -- the offer gid is not a decimal string. Rejected by "
                "path validation before any Asana read is issued."
            )
        },
        502: {
            "description": (
                "REFUSED -- IDENTITY_SUPPLY_BASIS_CONFLICT: the supplied "
                "evidence objects disagree on basis_version, so no single "
                "envelope version is true of all of them. NEVER retry into "
                "this; it is a supplier contract violation."
            )
        },
        503: {
            "description": (
                "REFUSED -- IDENTITY_SUPPLY_UNAVAILABLE: the supply raised. "
                "Retryable. This is NOT the shape of an unreachable offer -- "
                "an unreachable offer is a 200 carrying "
                "`absent_reason: resolver_unavailable` evidence, because the "
                "supply types that absence itself."
            )
        },
    },
    openapi_extra={
        # Declared READ-ONLY and machine-readable. The reachable call graph from
        # this operation contains GET verbs only; there is no write class to
        # gate, and the absence of x-fleet-side-effects is the machine-readable
        # counterpart of the census asserted in this route's test module.
        "x-fleet-read-only": True,
        "x-fleet-cross-service-refs": {
            "service": "autom8y",
            "entity": "identity_observation_ledger",
        },
    },
)
async def get_identity_supply(
    offer_gid: OfferGid,
    request_id: RequestId,
    auth_context: AuthContextDep,
    claims: Annotated[ServiceClaims, Depends(require_service_claims)],
) -> SuccessResponse[IdentitySupplyResponse]:
    """Walk upward from one offer gid and return the id-walk evidence objects.

    Authentication: S2S JWT only, via the same ``require_service_claims``
    dependency ``/v1/receipts`` and ``/v1/forwarding-stage/census`` use. No new
    principal (see module docstring).

    Args:
        offer_gid: The producer-held offer gid to walk from. Digits only.

    Returns:
        200: ``SuccessResponse[IdentitySupplyResponse]``. Three evidence
             objects -- ``asana_business``, ``business_display_name``,
             ``offer`` -- plus the candidate SET and the agreed
             ``basis_version``. A typed absence is a 200, not an error: the
             supply publishes absence as evidence, and collapsing that into an
             HTTP error would destroy the very distinction the substrate
             exists to record.

    Error Responses:
        - 401 MISSING_AUTH / SERVICE_TOKEN_REQUIRED: auth failures (S2S only)
        - 422: the offer gid is not a decimal string
        - 502 IDENTITY_SUPPLY_BASIS_CONFLICT: the evidence objects disagree on
          ``basis_version``
        - 503 IDENTITY_SUPPLY_UNAVAILABLE: the supply raised
    """
    start_time = time.monotonic()

    logger.info(
        "identity_supply_request",
        extra={
            "request_id": request_id,
            "caller_service": claims.service_name,
            "offer_gid": offer_gid,
        },
    )

    try:
        async with AsanaClient(token=auth_context.asana_pat) as client:
            supply = await supply_identity_evidence_async(client, offer_gid)
        response = build_identity_supply_response(supply, offer_gid=offer_gid)
    except BasisVersionConflict as exc:
        logger.error(
            "identity_supply_basis_conflict",
            extra={"request_id": request_id, "offer_gid": offer_gid},
        )
        raise_api_error(request_id, 502, "IDENTITY_SUPPLY_BASIS_CONFLICT", str(exc))
    except Exception as exc:  # BROAD-CATCH: boundary
        # Nothing escapes as an untyped 500 with a stack. The supply already
        # types every absence it knows how to name; anything that gets past it
        # is a supplier fault, and the consumer must be able to tell that apart
        # from a walk that honestly found nothing.
        logger.exception(
            "identity_supply_unexpected_error",
            extra={
                "request_id": request_id,
                "offer_gid": offer_gid,
                "error_type": type(exc).__name__,
            },
        )
        raise_api_error(
            request_id,
            503,
            "IDENTITY_SUPPLY_UNAVAILABLE",
            f"identity supply failed ({type(exc).__name__}); refusing rather "
            "than returning evidence it did not produce.",
        )

    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.info(
        "identity_supply_complete",
        extra={
            "request_id": request_id,
            "offer_gid": offer_gid,
            # Counts, tiers and tokens only -- never a value, never a name.
            "match_count": response.asana_business.match_count,
            "candidate_count": len(response.candidates),
            "detection_tier": response.asana_business.detection_tier,
            "needs_healing": response.asana_business.needs_healing,
            "identity_published": response.asana_business.value is not None,
            "absent_reason": (
                response.asana_business.absent_reason.value
                if response.asana_business.absent_reason is not None
                else None
            ),
            "basis_version": response.basis_version,
            "elapsed_ms": round(elapsed_ms, 2),
        },
    )

    return build_success_response(data=response, request_id=request_id)
