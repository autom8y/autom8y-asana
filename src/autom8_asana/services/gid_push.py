"""Push GID mappings to autom8_data after index rebuild.

After the cache warmer rebuilds GID indexes, push the mapping snapshot
to autom8_data's sync endpoint so autom8_data can serve GID lookups
locally without calling back to autom8_asana.

The push is best-effort: failure does NOT fail the cache warmer.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from autom8y_config.lambda_extension import resolve_secret_from_env
from autom8y_http import Autom8yHttpClient, HttpClientConfig, TimeoutException
from autom8y_log import get_logger
from pydantic import BaseModel, ConfigDict

from autom8_asana.clients.data._pii import mask_pii_in_string

if TYPE_CHECKING:
    from autom8_asana.services.gid_lookup import GidLookupIndex

logger = get_logger(__name__)

# Environment variable to disable GID push (emergency kill switch).
# Enabled by default; set to "false", "0", or "no" to disable.
GID_PUSH_ENABLED_ENV_VAR = "GID_PUSH_ENABLED"

# Timeout for the push HTTP request (seconds).
_PUSH_CONFIG = HttpClientConfig(
    connect_timeout=5.0,
    read_timeout=10.0,
    write_timeout=10.0,
    pool_timeout=5.0,
    enable_retry=False,
    enable_circuit_breaker=False,
)


class GidPushResponse(BaseModel):
    """POST /api/v1/gid-mappings/sync response envelope.

    Per ADR-WS1-001: Pydantic BaseModel with extra="ignore".
    Both fields are optional since the upstream response shape
    is not formally documented.
    """

    model_config = ConfigDict(extra="ignore")

    accepted: int | None = None
    replaced: int | None = None


def _is_push_enabled() -> bool:
    """Check whether GID push is enabled via environment variable.

    Returns:
        True unless GID_PUSH_ENABLED is explicitly set to a falsy value.
    """
    val = os.environ.get(GID_PUSH_ENABLED_ENV_VAR, "").lower()
    return val not in {"false", "0", "no"}


def extract_mappings_from_index(
    index: GidLookupIndex,
) -> list[dict[str, str]]:
    """Extract phone/vertical/task_gid mappings from a GidLookupIndex.

    Parses the canonical_key format ``pv1:{phone}:{vertical}`` and pairs
    each entry with its task GID.

    Args:
        index: GidLookupIndex containing the lookup dictionary.

    Returns:
        List of mapping dicts with keys: phone, vertical, task_gid.
        Entries whose canonical_key does not match the expected format
        are silently skipped.
    """
    mappings: list[dict[str, str]] = []
    for canonical_key, task_gid in index._lookup.items():
        parts = canonical_key.split(":")
        # Expected format: pv1:{phone}:{vertical}
        if len(parts) == 3 and parts[0] == "pv1":
            mappings.append(
                {
                    "phone": parts[1],
                    "vertical": parts[2],
                    "task_gid": task_gid,
                }
            )
        else:
            logger.debug(
                "gid_push_skip_entry",
                extra={
                    "canonical_key": canonical_key,
                    "reason": "unexpected_format",
                },
            )
    return mappings


def _get_data_service_url() -> str | None:
    """Resolve the autom8_data base URL from environment.

    Returns:
        Base URL string, or None if not configured.
    """
    return os.environ.get("AUTOM8Y_DATA_URL")


def _get_auth_token() -> str | None:
    """Resolve the S2S JWT token for autom8_data.

    Uses the same ``AUTOM8Y_DATA_API_KEY`` environment variable that
    ``DataServiceClient`` uses, resolved through the Lambda extension
    helper (supports SSM/Secrets Manager ARN references).

    Returns:
        Bearer token string, or None if not available.
    """
    try:
        return resolve_secret_from_env("AUTOM8Y_DATA_API_KEY")
    except ValueError:
        return None


async def _push_to_data_service(
    *,
    endpoint_path: str,
    payload: dict[str, Any],
    response_model: type[BaseModel],
    metric_dimensions: dict[str, str],
    log_prefix: str,
    base_url: str,
    token: str,
) -> bool:
    """Shared HTTP push helper for data-service endpoints.

    Handles the HTTP POST, response parsing, timeout, and broad-catch
    boilerplate shared by push_gid_mappings_to_data_service and
    push_status_to_data_service.

    Args:
        endpoint_path: Path appended to base_url (e.g. '/api/v1/gid-mappings/sync').
        payload: Request body dict to POST as JSON.
        response_model: Pydantic model class to parse the 2xx response body.
        metric_dimensions: Key/value pairs logged with success/failure events.
        log_prefix: Prefix for log event names ('gid_push' or 'status_push').
        base_url: Resolved autom8_data base URL (trailing slash stripped internally).
        token: Bearer token for Authorization header.

    Returns:
        True if the push succeeded (HTTP 2xx), False otherwise.
    """
    url = f"{base_url.rstrip('/')}{endpoint_path}"
    headers: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    logger.info(
        f"{log_prefix}_starting",
        extra={**metric_dimensions, "url": url},
    )

    try:
        async with (
            Autom8yHttpClient(_PUSH_CONFIG) as client,
            client.raw() as raw_client,
        ):
            response = await raw_client.post(url, json=payload, headers=headers)

        if response.status_code < 300:
            try:
                parsed = response_model.model_validate(response.json())
            except Exception:
                parsed = response_model()

            logger.info(
                f"{log_prefix}_success",
                extra={
                    **metric_dimensions,
                    "status_code": response.status_code,
                    **{
                        k: v
                        for k, v in parsed.model_dump().items()
                        if v is not None
                    },
                },
            )
            return True

        logger.warning(
            f"{log_prefix}_failed",
            extra={
                **metric_dimensions,
                "status_code": response.status_code,
                "response_text": mask_pii_in_string(response.text[:500]),
            },
        )
        return False

    except TimeoutException as e:
        logger.warning(
            f"{log_prefix}_timeout",
            extra={**metric_dimensions, "error": mask_pii_in_string(str(e))},
        )
        return False

    except Exception as e:  # BROAD-CATCH: isolation -- push failure must never fail cache warmer
        logger.error(
            f"{log_prefix}_error",
            extra={
                **metric_dimensions,
                "error": mask_pii_in_string(str(e)),
                "error_type": type(e).__name__,
            },
        )
        return False


async def push_gid_mappings_to_data_service(
    project_gid: str,
    index: GidLookupIndex,
    *,
    data_service_url: str | None = None,
    auth_token: str | None = None,
) -> bool:
    """Push GID mappings to autom8_data after index rebuild.

    Extracts all ``(phone, vertical) -> task_gid`` entries from the
    index and POSTs them to ``POST /api/v1/gid-mappings/sync``.

    This function is **non-blocking** with respect to the caller:
    all exceptions are caught and logged so that a push failure never
    propagates to the cache warmer.

    Args:
        project_gid: Asana project GID that the mappings belong to.
        index: The freshly-built GidLookupIndex to push.
        data_service_url: Override for the autom8_data base URL.
            Defaults to ``AUTOM8Y_DATA_URL`` environment variable.
        auth_token: Override for the S2S JWT bearer token.
            Defaults to ``AUTOM8Y_DATA_API_KEY`` environment variable.

    Returns:
        True if the push succeeded (HTTP 2xx), False otherwise.
    """
    # Feature flag check
    if not _is_push_enabled():
        logger.info(
            "gid_push_disabled",
            extra={
                "project_gid": project_gid,
                "reason": f"{GID_PUSH_ENABLED_ENV_VAR} is false",
            },
        )
        return False

    # Resolve configuration
    base_url = data_service_url or _get_data_service_url()
    if not base_url:
        logger.warning(
            "gid_push_skipped",
            extra={
                "project_gid": project_gid,
                "reason": "AUTOM8Y_DATA_URL not configured",
            },
        )
        return False

    token = auth_token or _get_auth_token()
    if not token:
        logger.warning(
            "gid_push_skipped",
            extra={
                "project_gid": project_gid,
                "reason": "AUTOM8Y_DATA_API_KEY not available",
            },
        )
        return False

    # Extract mappings from index
    mappings = extract_mappings_from_index(index)
    if not mappings:
        logger.info(
            "gid_push_skipped",
            extra={
                "project_gid": project_gid,
                "reason": "no_mappings_to_push",
                "index_size": len(index),
            },
        )
        return True  # Nothing to push is not a failure

    # Build request payload
    payload: dict[str, Any] = {
        "project_gid": project_gid,
        "mappings": mappings,
        "source_timestamp": index.created_at.isoformat(),
        "entry_count": len(mappings),
    }

    return await _push_to_data_service(
        endpoint_path="/api/v1/gid-mappings/sync",
        payload=payload,
        response_model=GidPushResponse,
        metric_dimensions={"project_gid": project_gid, "entry_count": str(len(mappings))},
        log_prefix="gid_push",
        base_url=base_url,
        token=token,
    )


# ============================================================================
# Account Status Push (ADR-account-status-state-projection)
# ============================================================================

# Pipeline type mapping: Asana project GID -> pipeline_type string
PIPELINE_TYPE_BY_PROJECT_GID: dict[str, str] = {
    "1201081073731555": "unit",           # Business Units
    "1200944186565610": "sales",          # Sales
    "1201319387632570": "onboarding",     # Onboarding
    "1201753128450029": "outreach",       # Outreach
    "1201346565918814": "retention",      # Retention
    "1201265144487549": "reactivation",   # Reactivation
    "1201265144487557": "expansion",      # Expansion
    "1201476141989746": "implementation", # Implementation
    "1201684018234520": "account_error",  # Account Error
    "1209247943184021": "month1",          # Activation Consultation
}

# Environment variable to disable status push (emergency kill switch).
STATUS_PUSH_ENABLED_ENV_VAR = "STATUS_PUSH_ENABLED"


class AccountStatusPushResponse(BaseModel):
    """POST /api/v1/account-status/sync response envelope."""

    model_config = ConfigDict(extra="ignore")

    deleted: int | None = None
    inserted: int | None = None


def _is_status_push_enabled() -> bool:
    """Check whether status push is enabled via environment variable."""
    val = os.environ.get(STATUS_PUSH_ENABLED_ENV_VAR, "").lower()
    # Enabled by default; set to "false", "0", or "no" to disable
    return val not in {"false", "0", "no"}


def extract_status_from_dataframe(
    df: Any,
    project_gid: str,
    entity_type: str,
) -> list[dict[str, Any]]:
    """Extract account status entries from a warmed DataFrame.

    Classifies each (phone, vertical) row using the appropriate
    SectionClassifier, filtering to only ACTIVE and ACTIVATING
    classifications (active-only registry [SD-02]).

    Args:
        df: Polars DataFrame with columns: office_phone, vertical, gid,
            and section membership data.
        project_gid: Asana project GID for pipeline_type resolution.
        entity_type: Entity type (e.g., 'unit', 'offer').

    Returns:
        List of entry dicts with keys: phone, vertical, pipeline_type,
        account_activity, pipeline_section, stage_entered_at.
    """
    from autom8_asana.models.business.activity import (
        AccountActivity,
        extract_section_name,
        get_classifier,
    )

    pipeline_type = PIPELINE_TYPE_BY_PROJECT_GID.get(project_gid)
    if pipeline_type is None:
        logger.debug(
            "status_extract_unknown_project",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
            },
        )
        return []

    # Get the appropriate classifier
    classifier = get_classifier(entity_type)
    if classifier is None:
        logger.warning(
            "process_pipeline_no_classifier",
            extra={
                "entity_type": entity_type,
                "project_gid": project_gid,
            },
        )
        return []

    entries: list[dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()

    # Required columns check
    required_cols = {"office_phone"}
    if not required_cols.issubset(set(df.columns)):
        return []

    has_vertical = "vertical" in df.columns
    # Per REVIEW-reconciliation-deep-audit TC-1 / P0-A:
    # Use canonical "section" column from schemas/base.py:84, NOT "section_name"
    has_section = "section" in df.columns
    has_memberships = "memberships" in df.columns

    for row_idx in range(len(df)):
        phone = df["office_phone"][row_idx]
        if not phone:
            continue

        vertical = df["vertical"][row_idx] if has_vertical else ""
        if vertical is None:
            vertical = ""

        # Extract section name from row
        section_name = None
        if has_section:
            section_name = df["section"][row_idx]
        elif has_memberships:
            memberships = df["memberships"][row_idx]
            if memberships is not None:
                section_name = extract_section_name(
                    {"memberships": memberships},
                    project_gid=project_gid,
                )

        if not section_name:
            continue

        # Classify
        activity = classifier.classify(section_name)
        if activity is None:
            continue

        # Active-only registry [SD-02]: only persist ACTIVE and ACTIVATING
        if activity not in (AccountActivity.ACTIVE, AccountActivity.ACTIVATING):
            continue

        entries.append({
            "phone": phone,
            "vertical": str(vertical),
            "pipeline_type": pipeline_type,
            "account_activity": activity.value,
            "pipeline_section": section_name,
            "stage_entered_at": now,  # Overridden by store carry-forward logic
        })

    return entries


async def push_status_to_data_service(
    entries: list[dict[str, Any]],
    source_timestamp: str,
    *,
    data_service_url: str | None = None,
    auth_token: str | None = None,
) -> bool:
    """Push account status snapshot to autom8_data.

    Mirrors push_gid_mappings_to_data_service() pattern.
    Non-blocking: all exceptions are caught and logged so that
    a push failure never propagates to the cache warmer.

    Args:
        entries: List of status entry dicts.
        source_timestamp: ISO timestamp of snapshot generation.
        data_service_url: Override for the autom8_data base URL.
        auth_token: Override for the S2S JWT bearer token.

    Returns:
        True if the push succeeded (HTTP 2xx), False otherwise.
    """
    if not _is_status_push_enabled():
        logger.info(
            "status_push_disabled",
            extra={"reason": f"{STATUS_PUSH_ENABLED_ENV_VAR} is false"},
        )
        return False

    base_url = data_service_url or _get_data_service_url()
    if not base_url:
        logger.warning(
            "status_push_skipped",
            extra={"reason": "AUTOM8Y_DATA_URL not configured"},
        )
        return False

    token = auth_token or _get_auth_token()
    if not token:
        logger.warning(
            "status_push_skipped",
            extra={"reason": "AUTOM8Y_DATA_API_KEY not available"},
        )
        return False

    if not entries:
        logger.info(
            "status_push_skipped",
            extra={"reason": "no_entries_to_push"},
        )
        return True  # Nothing to push is not a failure

    payload: dict[str, Any] = {
        "source": "section_classifier",
        "entries": entries,
        "source_timestamp": source_timestamp,
        "entry_count": len(entries),
    }

    return await _push_to_data_service(
        endpoint_path="/api/v1/account-status/sync",
        payload=payload,
        response_model=AccountStatusPushResponse,
        metric_dimensions={"entry_count": str(len(entries))},
        log_prefix="status_push",
        base_url=base_url,
        token=token,
    )
