"""Push GID mappings to autom8_data after index rebuild.

After the cache warmer rebuilds GID indexes, push the mapping snapshot
to autom8_data's sync endpoint so autom8_data can serve GID lookups
locally without calling back to autom8_asana.

The push is best-effort: failure does NOT fail the cache warmer.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from autom8y_config.lambda_extension import resolve_secret_from_env
from autom8y_log import get_logger

from autom8_asana.clients.data._pii import mask_pii_in_string
from autom8_asana.services.gid_lookup import GidLookupIndex

logger = get_logger(__name__)

# Environment variable to disable GID push (emergency kill switch).
# Enabled by default; set to "false", "0", or "no" to disable.
GID_PUSH_ENABLED_ENV_VAR = "GID_PUSH_ENABLED"

# Timeout for the push HTTP request (seconds).
_PUSH_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)


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
    return os.environ.get("AUTOM8_DATA_URL")


def _get_auth_token() -> str | None:
    """Resolve the S2S JWT token for autom8_data.

    Uses the same ``AUTOM8_DATA_API_KEY`` environment variable that
    ``DataServiceClient`` uses, resolved through the Lambda extension
    helper (supports SSM/Secrets Manager ARN references).

    Returns:
        Bearer token string, or None if not available.
    """
    try:
        return resolve_secret_from_env("AUTOM8_DATA_API_KEY")
    except ValueError:
        return None


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
            Defaults to ``AUTOM8_DATA_URL`` environment variable.
        auth_token: Override for the S2S JWT bearer token.
            Defaults to ``AUTOM8_DATA_API_KEY`` environment variable.

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
                "reason": "AUTOM8_DATA_URL not configured",
            },
        )
        return False

    token = auth_token or _get_auth_token()
    if not token:
        logger.warning(
            "gid_push_skipped",
            extra={
                "project_gid": project_gid,
                "reason": "AUTOM8_DATA_API_KEY not available",
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

    url = f"{base_url.rstrip('/')}/api/v1/gid-mappings/sync"

    headers: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    logger.info(
        "gid_push_starting",
        extra={
            "project_gid": project_gid,
            "entry_count": len(mappings),
            "url": url,
        },
    )

    try:
        async with httpx.AsyncClient(timeout=_PUSH_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code < 300:
            try:
                body = response.json()
            except ValueError:
                body = {}

            logger.info(
                "gid_push_success",
                extra={
                    "project_gid": project_gid,
                    "entry_count": len(mappings),
                    "status_code": response.status_code,
                    "accepted": body.get("accepted"),
                    "replaced": body.get("replaced"),
                },
            )
            return True

        # Non-success HTTP status
        logger.warning(
            "gid_push_failed",
            extra={
                "project_gid": project_gid,
                "status_code": response.status_code,
                "response_text": mask_pii_in_string(response.text[:500]),
            },
        )
        return False

    except httpx.TimeoutException as e:
        logger.warning(
            "gid_push_timeout",
            extra={
                "project_gid": project_gid,
                "error": mask_pii_in_string(str(e)),
            },
        )
        return False

    except (
        Exception
    ) as e:  # BROAD-CATCH: isolation -- push failure must never fail cache warmer
        logger.error(
            "gid_push_error",
            extra={
                "project_gid": project_gid,
                "error": mask_pii_in_string(str(e)),
                "error_type": type(e).__name__,
            },
        )
        return False
