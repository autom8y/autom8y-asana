"""Cross-service identifier for business scoping.

Canonical type owned by autom8y-core SDK (autom8y_core.models.data_service).
from_business() adapter owned by autom8_asana (domain-specific factory).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8y_core.models.data_service import PhoneVerticalPair

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business


def pvp_from_business(business: Business) -> PhoneVerticalPair:
    """Create PhoneVerticalPair from Business entity.

    This factory function extracts office_phone and vertical from a
    Business model instance, validating that both required fields
    are present.

    Args:
        business: Business model with office_phone and vertical fields.

    Returns:
        PhoneVerticalPair instance.

    Raises:
        InsightsValidationError: If office_phone or vertical is None.
    """
    from autom8_asana.errors import InsightsValidationError

    if not business.office_phone:
        raise InsightsValidationError(
            "Cannot create PhoneVerticalPair: office_phone is required",
            field="office_phone",
        )
    if not business.vertical:
        raise InsightsValidationError(
            "Cannot create PhoneVerticalPair: vertical is required",
            field="vertical",
        )
    return PhoneVerticalPair(
        phone=business.office_phone,
        vertical=business.vertical,
    )


__all__ = ["PhoneVerticalPair", "pvp_from_business"]
