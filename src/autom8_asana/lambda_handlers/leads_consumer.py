"""Lambda handler for the grain-bridge per-business leads consumer.

Thin entrypoint mirroring ``insights_export.py``: ``bootstrap()`` then a handler
that wires :class:`GrainBridgeLeadsConsumer` with a hand-built
:class:`BusinessTokenMinter` and a per-business ``DataServiceClient`` factory.

NOT wired into prod scheduling by this build (operator deploy, OOS-2). Gated by
the ``AUTOM8_LEADS_BRIDGE_ENABLED`` feature flag, which defaults to DISABLED so
an accidental schedule wiring is a no-op until the operator opts in.

Credentials are process-env only (``SERVICE_CLIENT_ID`` /
``SERVICE_CLIENT_SECRET``); the consumer authenticates as the delegator and
exchanges for single-tenant per-business tokens -- never the fleet token.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from typing import TYPE_CHECKING, Any

from autom8_asana.models.business._bootstrap import bootstrap

bootstrap()

# ruff: noqa: E402
from autom8y_log import get_logger

from autom8_asana.core.scope import EntityScope

if TYPE_CHECKING:
    from autom8_asana.protocols.auth import AuthProvider

logger = get_logger(__name__)

LEADS_BRIDGE_ENABLED_ENV_VAR = "AUTOM8_LEADS_BRIDGE_ENABLED"
WORKFLOW_ID = "grain-bridge-leads"
DMS_NAMESPACE = "Autom8y/AsanaLeadsBridge"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _feature_enabled() -> bool:
    """Read the feature flag (default DISABLED -- opt-in)."""
    return os.environ.get(LEADS_BRIDGE_ENABLED_ENV_VAR, "").strip().lower() in _TRUTHY


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point."""
    return asyncio.run(_handler_async(event))


async def _handler_async(event: dict[str, Any]) -> dict[str, Any]:
    if not _feature_enabled():
        logger.info("grain_bridge_leads_disabled", flag=LEADS_BRIDGE_ENABLED_ENV_VAR)
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "skipped", "reason": "feature_disabled"}),
        }
    try:
        return await _execute(event)
    except (
        Exception  # noqa: BLE001
    ) as exc:  # BROAD-CATCH: boundary -- lambda top-level handler returns 500
        logger.error(
            "grain_bridge_leads_error",
            error=str(exc),
            error_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "error",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            ),
        }


async def _execute(event: dict[str, Any]) -> dict[str, Any]:
    from autom8_asana.auth.business_token import BusinessTokenMinter
    from autom8_asana.automation.workflows.leads_consumer import (
        GrainBridgeLeadsConsumer,
    )
    from autom8_asana.client import AsanaClient
    from autom8_asana.clients.data.client import DataServiceClient

    logger.info("grain_bridge_leads_started", lambda_event=event)
    scope = EntityScope.from_event(event)

    asana_client = AsanaClient()
    # Delegator credentials resolved from process-env (SC-BUILD-4). A
    # missing/unresolvable secret is a hard misconfiguration -> propagates to
    # the top-level catch as a 500 (honest failure), never a silent dark-run.
    minter = BusinessTokenMinter()

    def _data_client_factory(provider: AuthProvider) -> DataServiceClient:
        # Per-business client: the injected provider carries the single-tenant
        # token; the JWT business_id dominates the office_phone param.
        return DataServiceClient(auth_provider=provider)

    consumer = GrainBridgeLeadsConsumer(
        asana_client,
        minter,
        _data_client_factory,
    )
    try:
        result = await consumer.run(scope)
    finally:
        await minter.close()

    if result.succeeded > 0:
        _emit_success_timestamp()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "status": "ok",
                "workflow_id": WORKFLOW_ID,
                "attempted": result.attempted,
                "succeeded": result.succeeded,
                "skipped": result.total_skipped,
                "skipped_by_class": {k.value: v for k, v in result.skipped_by_class.items()},
            }
        ),
    }


def _emit_success_timestamp() -> None:
    """Emit the dead-man's-switch success timestamp (best-effort)."""
    try:
        from autom8y_telemetry.aws import emit_success_timestamp

        emit_success_timestamp(DMS_NAMESPACE)
    except Exception:  # BROAD-CATCH: telemetry is best-effort  # noqa: BLE001
        logger.warning("grain_bridge_leads_dms_emit_failed", namespace=DMS_NAMESPACE)
