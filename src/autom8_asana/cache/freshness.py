"""Cache freshness modes for controlling validation behavior.

Migration Note (SDK-PRIMITIVES-001):
    This module now re-exports autom8y_cache.Freshness which includes
    IMMEDIATE mode in addition to STRICT and EVENTUAL. The local enum
    is deprecated in favor of the SDK version.
"""

from __future__ import annotations

# Re-export SDK Freshness enum which includes IMMEDIATE
from autom8y_cache import Freshness

# For backward compatibility, expose Freshness from this module
# The SDK Freshness includes: STRICT, EVENTUAL, IMMEDIATE
__all__ = ["Freshness"]

# Note: The SDK Freshness enum has the same values:
#   - STRICT = "strict": Always validate version against source
#   - EVENTUAL = "eventual": Return cached if within TTL
#   - IMMEDIATE = "immediate": Return cached without any validation
