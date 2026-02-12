"""Tests for EntityWriteRegistry.

Per TDD-ENTITY-WRITE-API Section 16.1:
    9 tests validating discovery, filtering, and lookup behavior.
"""

from __future__ import annotations

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.resolution.write_registry import (
    CORE_FIELD_NAMES,
    EntityWriteRegistry,
    WritableEntityInfo,
)


# Build once for the entire test module -- registry is immutable after construction
_entity_registry = get_registry()
_write_registry = EntityWriteRegistry(_entity_registry)


class TestEntityWriteRegistry:
    """Tests for EntityWriteRegistry auto-discovery and lookup."""

    def test_discovers_offer_descriptors(self) -> None:
        """Offer with 39+ descriptors is discovered; descriptor_index has expected mappings."""
        info = _write_registry.get("offer")
        assert info is not None
        assert isinstance(info, WritableEntityInfo)
        assert info.entity_type == "offer"
        assert info.project_gid == "1143843662099250"

        # Verify specific descriptor mappings (note: "ad" is an abbreviation -> "AD")
        assert info.descriptor_index["weekly_ad_spend"] == "Weekly AD Spend"
        assert info.descriptor_index["mrr"] == "MRR"
        assert info.descriptor_index["ad_id"] == "Ad ID"
        assert info.descriptor_index["campaign_id"] == "Campaign ID"
        assert info.descriptor_index["platforms"] == "Platforms"
        assert info.descriptor_index["office_phone"] == "Office Phone"

        # Offer has 39+ descriptors (direct + mixin inherited)
        assert len(info.descriptor_index) >= 39

    def test_discovers_business_descriptors(self) -> None:
        """Business with inherited mixin descriptors is discovered."""
        info = _write_registry.get("business")
        assert info is not None
        assert info.entity_type == "business"
        assert info.project_gid == "1200653012566782"

        # Business has its own descriptors
        assert "company_id" in info.descriptor_index
        assert info.descriptor_index["company_id"] == "Company ID"
        assert "office_phone" in info.descriptor_index
        assert "vca_status" in info.descriptor_index

        # Business inherits from SharedCascadingFieldsMixin
        assert "vertical" in info.descriptor_index
        assert info.descriptor_index["vertical"] == "Vertical"
        assert "rep" in info.descriptor_index
        assert info.descriptor_index["rep"] == "Rep"

        # Business inherits from FinancialFieldsMixin
        assert "booking_type" in info.descriptor_index
        assert "mrr" in info.descriptor_index
        assert info.descriptor_index["mrr"] == "MRR"

    def test_skips_holder_types(self) -> None:
        """Holder types are NOT registered as writable."""
        holder_names = [
            "offer_holder",
            "contact_holder",
            "unit_holder",
            "dna_holder",
            "reconciliation_holder",
            "asset_edit_holder",
            "videography_holder",
            "location_holder",
            "process_holder",
        ]
        for holder_name in holder_names:
            assert _write_registry.get(holder_name) is None, (
                f"{holder_name} should not be writable"
            )

    def test_skips_entities_without_project_gid(self) -> None:
        """Entities without primary_project_gid are excluded.

        Process has primary_project_gid=None in entity_registry, so it
        should be excluded even though it has CustomFieldDescriptor properties.
        """
        info = _write_registry.get("process")
        assert info is None

    def test_writable_types_sorted(self) -> None:
        """writable_types() returns sorted list of all writable entity names."""
        types = _write_registry.writable_types()
        assert types == sorted(types)
        assert len(types) > 0

        # All known leaf/root entities with project GIDs and descriptors should be present
        assert "offer" in types
        assert "business" in types
        assert "unit" in types

        # Holders and no-project entities should be absent
        assert "offer_holder" not in types
        assert "process" not in types

    def test_is_writable_true_for_offer(self) -> None:
        """is_writable('offer') returns True."""
        assert _write_registry.is_writable("offer") is True

    def test_is_writable_false_for_holder(self) -> None:
        """is_writable('offer_holder') returns False."""
        assert _write_registry.is_writable("offer_holder") is False

    def test_descriptor_index_includes_mixin_fields(self) -> None:
        """Inherited descriptors from mixins appear in descriptor_index.

        Offer inherits:
        - vertical, rep from SharedCascadingFieldsMixin
        - booking_type, mrr, weekly_ad_spend from FinancialFieldsMixin
        """
        info = _write_registry.get("offer")
        assert info is not None

        # From SharedCascadingFieldsMixin
        assert "vertical" in info.descriptor_index
        assert info.descriptor_index["vertical"] == "Vertical"
        assert "rep" in info.descriptor_index
        assert info.descriptor_index["rep"] == "Rep"

        # From FinancialFieldsMixin
        assert "booking_type" in info.descriptor_index
        assert info.descriptor_index["booking_type"] == "Booking Type"
        assert "mrr" in info.descriptor_index
        assert info.descriptor_index["mrr"] == "MRR"
        assert "weekly_ad_spend" in info.descriptor_index
        assert info.descriptor_index["weekly_ad_spend"] == "Weekly AD Spend"

    def test_core_fields_set(self) -> None:
        """CORE_FIELD_NAMES contains exactly {name, assignee, due_on, completed, notes}."""
        expected = frozenset({"name", "assignee", "due_on", "completed", "notes"})
        assert CORE_FIELD_NAMES == expected

        # Also verify it's set on WritableEntityInfo
        info = _write_registry.get("offer")
        assert info is not None
        assert info.core_fields == expected
