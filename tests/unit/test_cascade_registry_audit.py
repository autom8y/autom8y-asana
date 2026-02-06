"""Audit test: all cascade:* schema sources must have registry entries.

Prevents future regressions where schemas declare cascade fields without
registering them in CASCADING_FIELD_REGISTRY. Any new cascade:* column
added to a schema without a corresponding CascadingFieldDef entry will
cause this test to fail.

Per TDD-cascade-field-resolution-generalized Section 4.3.
"""

from __future__ import annotations

from autom8_asana.dataframes.schemas import (
    ASSET_EDIT_HOLDER_SCHEMA,
    ASSET_EDIT_SCHEMA,
    BASE_SCHEMA,
    BUSINESS_SCHEMA,
    CONTACT_SCHEMA,
    OFFER_SCHEMA,
    UNIT_SCHEMA,
)
from autom8_asana.models.business.fields import get_cascading_field_registry

# All entity schemas that may contain cascade:* source declarations.
# BASE_SCHEMA and BUSINESS_SCHEMA included for completeness -- if someone
# adds a cascade column there in the future, this test will catch it.
ALL_SCHEMAS = [
    BASE_SCHEMA,
    BUSINESS_SCHEMA,
    UNIT_SCHEMA,
    OFFER_SCHEMA,
    CONTACT_SCHEMA,
    ASSET_EDIT_SCHEMA,
    ASSET_EDIT_HOLDER_SCHEMA,
]


def test_all_cascade_sources_have_registry_entries() -> None:
    """Every cascade:* source in every schema must exist in CASCADING_FIELD_REGISTRY."""
    registry = get_cascading_field_registry()
    missing: list[str] = []

    for schema in ALL_SCHEMAS:
        for col in schema.columns:
            if col.source and col.source.lower().startswith("cascade:"):
                field_name = col.source[len("cascade:") :]
                normalized = field_name.lower().strip()
                if normalized not in registry:
                    missing.append(
                        f"Schema '{schema.name}' column '{col.name}' "
                        f"declares source='cascade:{field_name}' "
                        f"but no registry entry exists for '{field_name}'"
                    )

    assert not missing, (
        "Unregistered cascade fields found. Each cascade:* source in a schema "
        "must have a matching CascadingFieldDef in Business.CascadingFields "
        "or Unit.CascadingFields:\n" + "\n".join(f"  - {m}" for m in missing)
    )


def test_registry_is_not_empty() -> None:
    """Sanity check: registry should contain known cascade fields."""
    registry = get_cascading_field_registry()
    assert len(registry) >= 5, (
        f"Expected at least 5 registry entries "
        f"(Office Phone, Platforms, Vertical, Booking Type, MRR, Weekly Ad Spend), "
        f"got {len(registry)}"
    )


def test_known_cascade_fields_are_registered() -> None:
    """Verify specific cascade fields that are known to exist in schemas."""
    registry = get_cascading_field_registry()
    expected_fields = [
        "office phone",
        "vertical",
        "platforms",
        "booking type",
        "mrr",
        "weekly ad spend",
    ]
    for field_name in expected_fields:
        assert field_name in registry, (
            f"Expected '{field_name}' in cascade registry but it was not found. "
            f"Available keys: {sorted(registry.keys())}"
        )
