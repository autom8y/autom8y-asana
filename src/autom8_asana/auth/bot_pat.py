"""Bot PAT provider for S2S requests.

This module provides secure access to the bot PAT from the environment.
The bot PAT is used for Asana API calls when the incoming auth is a JWT
(service-to-service mode).

Per ADR-S2S-002: Bot PAT Activation Pattern
- PAT loaded from ASANA_PAT environment variable
- Injected by ECS from Secrets Manager at container startup
- Cached in memory via lru_cache (single read)
- Never logged or exposed in error messages

Per TDD-S2S-001 Section 5.3:
- BotPATError raised if not configured
- Length validation as basic sanity check
- Exposed via get_bot_pat() function

Security:
- PAT value is never logged
- Error messages describe the problem without exposing the value
- Only the length is logged for diagnostics
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

from autom8y_config.lambda_extension import resolve_secret_from_env
from autom8y_log import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger("autom8_asana.auth")


class BotPATError(Exception):
    """Bot PAT configuration error.

    Raised when the ASANA_PAT environment variable is missing or invalid.
    This indicates a deployment configuration issue.

    Attributes:
        message: Human-readable error description (no credential data)
    """

    pass


@lru_cache(maxsize=1)
def get_bot_pat() -> str:
    """Get the bot PAT from environment.

    The bot PAT is used for S2S requests when the incoming auth
    is a JWT. It's the single credential that autom8_asana uses
    to call the Asana API on behalf of all S2S callers.

    Returns:
        Bot PAT string

    Raises:
        BotPATError: If ASANA_PAT is not configured or invalid

    Security:
        - PAT is loaded once and cached
        - Never logged or exposed in errors
        - Injected via ECS Secrets Manager -> env var

    Rationale:
        See ADR-S2S-002 for alternatives considered.
    """
    try:
        pat = resolve_secret_from_env("ASANA_PAT")
    except ValueError:
        pat = None

    if not pat:
        logger.error("bot_pat_not_configured")
        raise BotPATError(
            "ASANA_PAT environment variable is required for S2S mode. "
            "Check ECS task definition secrets configuration."
        )

    if len(pat) < 10:
        logger.error("bot_pat_invalid_length")
        raise BotPATError("ASANA_PAT appears invalid (too short)")

    # Log that we have a PAT configured, but never the value
    logger.debug(
        "bot_pat_configured",
        extra={"pat_length": len(pat)},
    )

    return pat


def clear_bot_pat_cache() -> None:
    """Clear the cached bot PAT.

    For testing only. Allows tests to simulate environment changes.
    """
    get_bot_pat.cache_clear()


def assert_no_plaintext_pat_in_caller(*, env: Mapping[str, str] | None = None) -> None:
    """Caller-startup guard (H5/V6): fail closed if a bare ``ASANA_PAT`` is set.

    The token-safe read-route requires the *interactive caller* (e.g. the iris
    read-route caller) to hold only a short-lived brokered identity — it must
    resolve the PAT through ``ASANA_PAT_ARN`` server-side and NEVER carry the
    plaintext PAT in its own environment. This guard is the caller-image
    assertion: invoke it at caller startup so a misconfigured caller that boots
    with a bare ``ASANA_PAT`` **halts** instead of silently degrading to a
    plaintext-PAT posture.

    It is intentionally NOT wired into the ECS server startup: the server
    legitimately receives ``ASANA_PAT`` injected from Secrets Manager and
    brokers it on callers' behalf. This guard is for the caller boundary only.

    Args:
        env: Environment mapping to inspect (defaults to ``os.environ``).
            Injectable for testing.

    Raises:
        BotPATError: if a non-empty bare ``ASANA_PAT`` is present — the "silent
            plaintext downgrade" the read-route forbids.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    if source.get("ASANA_PAT"):
        logger.error("caller_holds_plaintext_pat")
        raise BotPATError(
            "Caller context holds a bare ASANA_PAT; the token-safe read-route "
            "forbids the caller from materializing the plaintext PAT. Resolve "
            "the secret via ASANA_PAT_ARN brokerage and use a short-lived S2S "
            "identity instead."
        )


__all__ = [
    "BotPATError",
    "get_bot_pat",
    "clear_bot_pat_cache",
    "assert_no_plaintext_pat_in_caller",
]
