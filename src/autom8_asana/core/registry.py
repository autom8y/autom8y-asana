"""Holder registry for write-path auto-creation.

Extracted from persistence/holder_construction.py to avoid cross-layer imports
(models/business/ should not import from persistence/).

Per R-009 (REM-ASANA-ARCH WS-DFEX): Each Holder module self-registers via
register_holder() at module level, following the register_reset() pattern.
"""

from __future__ import annotations

# Public registry: populated by each Holder module at import time.
# Each Holder file calls register_holder(key, cls) at module level.
HOLDER_REGISTRY: dict[str, type] = {}


def register_holder(holder_key: str, holder_class: type) -> None:
    """Register a Holder class for the given holder_key.

    Called at module level in each Holder file so that importing the file
    automatically populates HOLDER_REGISTRY. Duplicates are silently ignored.

    Args:
        holder_key: Canonical key (e.g., "contact_holder", "unit_holder").
        holder_class: The Holder class to register.
    """
    if holder_key not in HOLDER_REGISTRY:
        HOLDER_REGISTRY[holder_key] = holder_class
