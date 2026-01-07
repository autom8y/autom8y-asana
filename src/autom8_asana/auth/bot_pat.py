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

from autom8y_log import get_logger
import os
from functools import lru_cache

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
    pat = os.environ.get("ASANA_PAT")

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


__all__ = [
    "BotPATError",
    "get_bot_pat",
    "clear_bot_pat_cache",
]
