"""Timeout detection and continuation for the cache warmer Lambda.

Per TDD-lambda-cache-warmer Section 3.2: Provides timeout detection via
get_remaining_time_in_millis() and self-invocation continuation when the
Lambda approaches its timeout limit.
"""

from __future__ import annotations

from typing import Any

from autom8y_log import get_logger

from autom8_asana.lambda_handlers.cloudwatch import emit_metric

logger = get_logger(__name__)

__all__ = [
    "TIMEOUT_BUFFER_MS",
    "_should_exit_early",
    "_self_invoke_continuation",
]

# ============================================================================
# Constants (per TDD-lambda-cache-warmer Section 3.2)
# ============================================================================

# Timeout buffer: exit 2 minutes before Lambda timeout (per PRD FR-001)
TIMEOUT_BUFFER_MS = 120_000


def _should_exit_early(context: Any) -> bool:
    """Check if we should exit to avoid Lambda timeout.

    Per TDD-lambda-cache-warmer: Monitors context.get_remaining_time_in_millis()
    and signals exit when remaining time falls below TIMEOUT_BUFFER_MS (2 minutes).

    Args:
        context: Lambda context with get_remaining_time_in_millis() method.
            May be None in test or non-Lambda environments.

    Returns:
        True if remaining time < TIMEOUT_BUFFER_MS, False otherwise.
        Returns False if context is None (no timeout enforcement).
    """
    if context is None:
        return False

    try:
        remaining_ms: int = context.get_remaining_time_in_millis()
        return bool(remaining_ms < TIMEOUT_BUFFER_MS)
    except AttributeError:
        # Context doesn't have the method (e.g., mock without it)
        return False


def _self_invoke_continuation(
    context: Any,
    pending_entities: list[str],
    parent_invocation_id: str,
    *,
    prematerialize_bulk_set: bool = False,
    prematerialize_section_set: bool = False,
) -> None:
    """Self-invoke Lambda with remaining entities for continuation.

    Uses context.invoked_function_arn to get own ARN.
    Fires asynchronously (InvocationType=Event) so current invocation
    can return cleanly.

    Args:
        context: Lambda context exposing ``invoked_function_arn``.
        pending_entities: Remaining work items (entity types, or TD-005
            ``"{gid}:{entity_type}"`` key tokens for the bulk/section paths).
        parent_invocation_id: Correlation id of the invocation self-continuing.
        prematerialize_bulk_set: TD-005. When True, the continuation payload
            carries the ``prematerialize_bulk_set`` flag so the next invocation
            re-enters the bulk pre-materialization branch (not the offer-domain
            warm). Defaults False to preserve the legacy entity-type behavior.
            Either way the next invocation resumes pending work from the shared
            checkpoint via ``resume_from_checkpoint=True``.
        prematerialize_section_set: ADR §B section lane. When True, the
            continuation payload carries the ``prematerialize_section_set`` flag
            so the next invocation re-enters the section-only warm lane (34 keys,
            disjoint checkpoint prefix). Mutually exclusive with
            ``prematerialize_bulk_set``; section flag takes precedence if both
            are accidentally set.
    """
    if not pending_entities:
        return

    function_arn = getattr(context, "invoked_function_arn", None)
    if not function_arn:
        logger.warning(
            "self_invoke_no_arn",
            extra={"parent_invocation_id": parent_invocation_id},
        )
        return

    import json

    import boto3

    payload: dict[str, Any] = {
        "strict": False,
        "resume_from_checkpoint": True,
    }
    if prematerialize_section_set:
        # Section lane: checkpoint carries pending key tokens; flag routes
        # the continuation back into the section-only branch.
        payload["prematerialize_section_set"] = True
    elif prematerialize_bulk_set:
        # Bulk path: the checkpoint carries the pending key tokens; the flag
        # routes the continuation back into _prematerialize_bulk_set_async.
        payload["prematerialize_bulk_set"] = True
    else:
        payload["entity_types"] = pending_entities
    try:
        client = boto3.client("lambda")
        client.invoke(
            FunctionName=function_arn,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        logger.info(
            "self_invoke_continuation",
            extra={
                "function_arn": function_arn,
                "pending_entities": pending_entities,
                "parent_invocation_id": parent_invocation_id,
            },
        )
        emit_metric("SelfContinuationInvoked", 1)
    except (
        Exception  # noqa: BLE001
    ) as e:  # BROAD-CATCH: isolation -- self-invoke failure must not fail current invocation
        logger.error(
            "self_invoke_failed",
            extra={
                "error": str(e),
                "parent_invocation_id": parent_invocation_id,
            },
        )
