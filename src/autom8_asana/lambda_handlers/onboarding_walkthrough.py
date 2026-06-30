"""Lambda handler for the onboarding walkthrough batch sweep (W4, DEPLOYED-DARK).

Per TDD-onboarding-walkthrough-batch-sweep Section W4: entry point for scheduled
Lambda execution. Mirrors ``insights_export.py`` / ``conversation_audit.py`` via
the generic ``workflow_handler`` factory, but the ``workflow_factory`` callable
injects the WIDER DI surface this workflow needs beyond the sibling bridges:

* ``query_engine`` -- the REAL GFR-backed ``QueryEngine`` (W1 by-GUID identity
  substrate). G-PROPAGATE: never a reimplementation.
* ``resolver`` -- the autom8y-core SDK ``DataServiceClient`` (B1 phone-leg address
  source). This is a SEPARATE client from the generic factory's ``data_client``:
  only the core-SDK client carries ``resolve_routing_address_by_phone_async``.

The YAML schedule-rule path (``config/rules/*.yaml``) cannot express that DI -- it
routes a workflow through the rules-engine's generic factory, which knows nothing
of ``query_engine`` and would construct an UNWIRED workflow (the W1 guard silently
inert). The Lambda-handler factory seam is therefore the chosen trigger (TDD W4
decision), and it is the ONLY construction path that wires ``query_engine``.

DEPLOYED-DARK: the workflow's opt-IN ``validate_async`` keeps it disabled unless
``AUTOM8_WALKTHROUGH_ENABLED`` is explicitly set (=true/1/yes/on). With the flag
unset, the handler short-circuits to ``skipped`` BEFORE any enumeration or Asana
write (workflow_handler.py:258). The EventBridge schedule + per-function Lambda
CMD override + env live in EXTERNAL deploy infra (this repo carries no IaC; the
container is dual-mode per Dockerfile); the flag stays UNSET this session.

Environment Variables:
    ASANA_PAT: Asana Personal Access Token.
    AUTOM8Y_DATA_URL (+ S2S auth env): base URL/creds for the core-SDK resolver
        and the query-engine cross-service join surface.
    AUTOM8_WALKTHROUGH_PRODUCER_DIR: bundled Node>=22 producer dir (sole freezer).
    AUTOM8_WALKTHROUGH_ENABLED: opt-IN feature flag (UNSET => DARK no-op).
"""

from __future__ import annotations

import os
from typing import Any

from autom8_asana.models.business._bootstrap import bootstrap

bootstrap()

# ruff: noqa: E402
from autom8_asana.automation.workflows.onboarding_walkthrough import constants
from autom8_asana.lambda_handlers.workflow_handler import (
    WorkflowHandlerConfig,
    create_workflow_handler,
)


def _create_workflow(asana_client: Any, data_client: Any) -> Any:
    """Deferred workflow construction for cold-start optimization.

    Injects the deps the sweep needs. ``data_client`` (the asana-local
    ``DataServiceClient`` the generic factory builds) backs the ``query_engine``
    cross-service join surface. The B1 ``resolver`` is a SEPARATE client -- the
    autom8y-core SDK ``DataServiceClient``, which carries
    ``resolve_routing_address_by_phone_async`` (data_service.py:438) that the
    asana-local ``data_client`` does NOT expose. That same core-SDK client also
    carries ``get_business_by_guid_async`` and is reused as the W1 ``verifier`` so
    the identity anchor runs the VERIFIED tier (BTM-3 harden), not blind CACHE.
    """
    from autom8y_core.clients.data_service import DataServiceClient as SdkResolver

    from autom8_asana.automation.workflows.onboarding_walkthrough.workflow import (
        OnboardingWalkthroughWorkflow,
    )
    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.services.query_service import EntityQueryService

    # Real GFR substrate. QueryEngine is a plain dataclass and EntityQueryService()
    # is zero-arg, so this constructs OUTSIDE the API-route context (UV-P-W1
    # discharged; the proven shape is api/routes/query.py:468-469).
    query_engine = QueryEngine(provider=EntityQueryService(), data_client=data_client)

    # B1 address resolver = the core-SDK client (NOT data_client, which lacks the
    # phone-resolve leg). from_env() reads AUTOM8Y_DATA_URL + S2S creds; an
    # unresolvable env is an honest 500 via the handler's top-level catch (the
    # repo's deliberate fail-loud-on-misconfig posture, not a silent degrade).
    resolver = SdkResolver.from_env()

    return OnboardingWalkthroughWorkflow(
        asana_client=asana_client,
        resolver=resolver,
        attachments_client=asana_client.attachments,
        producer_dir=os.environ[constants.WALKTHROUGH_PRODUCER_DIR_ENV_VAR],
        query_engine=query_engine,
        # BTM-3 harden (SEC-N3 F-N3-002): wire the W1 tier-2 by-GUID verifier so the
        # identity anchor runs TruthTier.VERIFIED, not the blind CACHE tier. The SAME
        # core-SDK DataServiceClient already built for the B1 resolver ALSO exposes
        # get_business_by_guid_async (the ByGuidVerifier port; data_service.py:434), so
        # reuse it -- no second client, no new infra. This narrows cache-poisoning /
        # data-integrity drift (a company_id that does not round-trip by-GUID ->
        # UnresolvedError -> skip), consistent with the existing fail-CLOSED posture; an
        # unresolvable env already fails loud via from_env() above. (Does NOT close
        # BTM-2: a consistent double-fault to a REAL wrong tenant still round-trips.)
        verifier=resolver,
        calendar_integrations_project_gid=constants.CALENDAR_INTEGRATIONS_PROJECT_GID,
    )


_config = WorkflowHandlerConfig(
    workflow_factory=_create_workflow,
    workflow_id="onboarding-walkthrough",
    log_prefix="lambda_onboarding_walkthrough",
    default_params={
        "max_concurrency": 5,
        "attachment_pattern": constants.ATTACHMENT_GLOB,
    },
    dms_namespace="Autom8y/AsanaWalkthrough",
)

handler = create_workflow_handler(_config)
