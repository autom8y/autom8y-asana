"""Custom field GID constants for MVP task types.

.. deprecated:: 0.2.0
    Static GID constants are deprecated per ADR-0034. Use dynamic
    custom field resolution with ``source="cf:FieldName"`` in schemas
    instead. See :mod:`autom8_asana.dataframes.resolver` for the new
    approach.

Per ADR-0030: Static GIDs hardcoded for MVP. Post-MVP supports
configurable field mappings.

Per ADR-0034: This module is DEPRECATED. Use dynamic resolution via
:class:`~autom8_asana.dataframes.resolver.CustomFieldResolver` instead
of static GID constants. Schema definitions should use ``source="cf:Name"``
to enable runtime field name resolution.

Migration:
    Instead of::

        from autom8_asana.dataframes.models.custom_fields import MRR_GID
        ColumnDef(name="mrr", source=MRR_GID)

    Use::

        ColumnDef(name="mrr", source="cf:MRR")

NOTE: These placeholder constants are retained for backward compatibility
but will be removed in a future version.
"""

from __future__ import annotations

import warnings

# Emit deprecation warning on module import
warnings.warn(
    "autom8_asana.dataframes.models.custom_fields is deprecated. "
    "Use dynamic resolution with source='cf:FieldName' in schemas instead. "
    "See ADR-0034 and autom8_asana.dataframes.resolver for the new approach.",
    DeprecationWarning,
    stacklevel=2,
)

# === Unit Custom Fields ===
# NOTE: Replace PLACEHOLDER_* with actual Asana GIDs before Phase 3

# MRR (Monthly Recurring Revenue)
# Type: number
MRR_GID: str = "PLACEHOLDER_MRR_GID"

# Weekly Ad Spend
# Type: number
WEEKLY_AD_SPEND_GID: str = "PLACEHOLDER_WEEKLY_AD_SPEND_GID"

# Products
# Type: multi_enum
PRODUCTS_GID: str = "PLACEHOLDER_PRODUCTS_GID"

# Languages
# Type: multi_enum
LANGUAGES_GID: str = "PLACEHOLDER_LANGUAGES_GID"

# Discount
# Type: number (percentage)
DISCOUNT_GID: str = "PLACEHOLDER_DISCOUNT_GID"

# Vertical
# Type: enum
VERTICAL_GID: str = "PLACEHOLDER_VERTICAL_GID"

# Specialty
# Type: text
SPECIALTY_GID: str = "PLACEHOLDER_SPECIALTY_GID"


# === Contact Custom Fields ===

# Full Name
# Type: text
FULL_NAME_GID: str = "PLACEHOLDER_FULL_NAME_GID"

# Nickname
# Type: text
NICKNAME_GID: str = "PLACEHOLDER_NICKNAME_GID"

# Contact Phone
# Type: text
CONTACT_PHONE_GID: str = "PLACEHOLDER_CONTACT_PHONE_GID"

# Contact Email
# Type: text
CONTACT_EMAIL_GID: str = "PLACEHOLDER_CONTACT_EMAIL_GID"

# Position
# Type: text
POSITION_GID: str = "PLACEHOLDER_POSITION_GID"

# Employee ID
# Type: text
EMPLOYEE_ID_GID: str = "PLACEHOLDER_EMPLOYEE_ID_GID"

# Contact URL
# Type: text
CONTACT_URL_GID: str = "PLACEHOLDER_CONTACT_URL_GID"

# Time Zone
# Type: enum or text
TIME_ZONE_GID: str = "PLACEHOLDER_TIME_ZONE_GID"

# City
# Type: text
CITY_GID: str = "PLACEHOLDER_CITY_GID"


def validate_gids_configured() -> list[str]:
    """Check which GIDs are still placeholder values.

    Returns:
        List of GID constant names that are still placeholders
    """
    import sys

    module = sys.modules[__name__]
    placeholders: list[str] = []

    for name in dir(module):
        if name.endswith("_GID"):
            value = getattr(module, name)
            if isinstance(value, str) and value.startswith("PLACEHOLDER_"):
                placeholders.append(name)

    return placeholders
