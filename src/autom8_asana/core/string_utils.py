"""String utility functions used across layers.

Extracted from services/resolver.py to avoid cross-layer imports
(cache/, core/, dataframes/ should not import from services/).
"""

from __future__ import annotations


def to_pascal_case(s: str) -> str:
    """Convert snake_case to PascalCase.

    Used for entity type to schema key conversion.
    Python's .title() incorrectly handles underscores:
    - "asset_edit".title() -> "Asset_Edit" (WRONG)
    - to_pascal_case("asset_edit") -> "AssetEdit" (CORRECT)

    Args:
        s: Snake_case string to convert.

    Returns:
        PascalCase string suitable for SchemaRegistry lookups.

    Examples:
        >>> to_pascal_case("unit")
        "Unit"
        >>> to_pascal_case("asset_edit")
        "AssetEdit"
        >>> to_pascal_case("asset_edit_holder")
        "AssetEditHolder"
    """
    return "".join(word.capitalize() for word in s.split("_"))
