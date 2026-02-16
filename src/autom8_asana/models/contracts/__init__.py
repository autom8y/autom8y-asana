"""Cross-service contracts for autom8 ecosystem.

Canonical type owned by autom8y-core SDK. Domain-specific adapters owned here.
"""

from autom8_asana.models.contracts.phone_vertical import (
    PhoneVerticalPair,
    pvp_from_business,
)

__all__ = [
    "PhoneVerticalPair",
    "pvp_from_business",
]
