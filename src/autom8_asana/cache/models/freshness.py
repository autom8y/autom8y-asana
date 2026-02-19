"""Cache freshness modes for controlling validation behavior.

Re-exports autom8y_cache.Freshness which includes STRICT, EVENTUAL,
and IMMEDIATE modes. Falls back to a local enum when the SDK import
is unavailable (Lambda version mismatch scenarios).
"""

from __future__ import annotations

from enum import Enum

# HOTFIX: Make import defensive for Lambda compatibility when autom8y_cache
# has missing modules (e.g., protocols.resolver in version mismatch scenarios)
try:
    from autom8y_cache import Freshness
except ImportError:
    # Fallback to local enum when SDK import fails

    class Freshness(str, Enum):  # type: ignore[no-redef]
        """Cache freshness modes - fallback when SDK unavailable."""

        STRICT = "strict"
        EVENTUAL = "eventual"
        IMMEDIATE = "immediate"


# For backward compatibility, expose Freshness from this module
# The SDK Freshness includes: STRICT, EVENTUAL, IMMEDIATE
__all__ = ["Freshness"]

# Note: The SDK Freshness enum has the same values:
#   - STRICT = "strict": Always validate version against source
#   - EVENTUAL = "eventual": Return cached if within TTL
#   - IMMEDIATE = "immediate": Return cached without any validation
