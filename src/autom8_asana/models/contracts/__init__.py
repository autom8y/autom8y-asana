"""Cross-service contracts for autom8 ecosystem.

Per ADR-INS-001: PhoneVerticalPair is owned by autom8_asana, not a shared package.
"""

from autom8_asana.models.contracts.phone_vertical import PhoneVerticalPair

__all__ = [
    "PhoneVerticalPair",
]
