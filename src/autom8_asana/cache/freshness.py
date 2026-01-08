"""Cache freshness modes for controlling validation behavior.

Migration Note (SDK-PRIMITIVES-001):
    This module now re-exports autom8y_cache.Freshness which includes
    IMMEDIATE mode in addition to STRICT and EVENTUAL. The local enum
    is deprecated in favor of the SDK version.
"""

from __future__ import annotations

from enum import Enum

# HOTFIX: Make import defensive for Lambda compatibility when autom8y_cache
# has missing modules (e.g., protocols.resolver in version mismatch scenarios)
try:
    from autom8y_cache import Freshness
except ImportError:
    # Fallback to local enum when SDK import fails

    class Freshness(str, Enum):
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
