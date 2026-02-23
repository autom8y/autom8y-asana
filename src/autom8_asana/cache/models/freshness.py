"""Cache freshness modes for controlling validation behavior.

.. deprecated::
    The ``Freshness`` name is a backward-compatible alias for
    :class:`~autom8_asana.cache.models.freshness_unified.FreshnessIntent`.
    New code should import ``FreshnessIntent`` directly.

Re-exports autom8y_cache.Freshness which includes STRICT, EVENTUAL,
and IMMEDIATE modes. Falls back to FreshnessIntent when the SDK import
is unavailable (Lambda version mismatch scenarios).
"""

from __future__ import annotations

# HOTFIX: Make import defensive for Lambda compatibility when autom8y_cache
# has missing modules (e.g., protocols.resolver in version mismatch scenarios)
try:
    from autom8y_cache import Freshness
except ImportError:
    # Fallback: use the unified enum as canonical definition
    from autom8_asana.cache.models.freshness_unified import FreshnessIntent

    Freshness = FreshnessIntent  # type: ignore[misc, assignment]


# For backward compatibility, expose Freshness from this module
# The SDK Freshness includes: STRICT, EVENTUAL, IMMEDIATE
__all__ = ["Freshness"]

# Note: The SDK Freshness enum has the same values:
#   - STRICT = "strict": Always validate version against source
#   - EVENTUAL = "eventual": Return cached if within TTL
#   - IMMEDIATE = "immediate": Return cached without any validation
