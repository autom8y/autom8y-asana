"""Tests for CascadingFieldDef, InheritedFieldDef, and cascading field registry.

Per TDD-BIZMODEL: Tests for field definition classes.
Per WS1-S3: Tests for descriptor-driven cascading field registry auto-wiring.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.fields import (
    CascadingFieldDef,
    InheritedFieldDef,
    _build_cascading_field_registry,
    get_cascading_field,
    get_cascading_field_registry,
)
from autom8_asana.models.task import Task


class TestCascadingFieldDef:
    """Tests for CascadingFieldDef class."""

    def test_default_allow_override_is_false(self) -> None:
        """allow_override defaults to False (parent always wins)."""
        field_def = CascadingFieldDef(name="Office Phone")
        assert field_def.allow_override is False

    def test_applies_to_with_none_targets(self) -> None:
        """applies_to returns True for any entity when target_types is None."""
        field_def = CascadingFieldDef(name="Company ID", target_types=None)
        task = Task(gid="123")
        assert field_def.applies_to(task) is True

    def test_applies_to_with_matching_target(self) -> None:
        """applies_to returns True when entity type is in target_types."""
        field_def = CascadingFieldDef(
            name="Office Phone",
            target_types={"Task", "Unit"},
        )
        task = Task(gid="123")
        assert field_def.applies_to(task) is True

    def test_applies_to_with_non_matching_target(self) -> None:
        """applies_to returns False when entity type is not in target_types."""
        field_def = CascadingFieldDef(
            name="Office Phone",
            target_types={"Unit", "Offer"},
        )
        task = Task(gid="123")
        assert field_def.applies_to(task) is False

    def test_should_update_descendant_no_override(self) -> None:
        """should_update_descendant always True when allow_override=False."""
        field_def = CascadingFieldDef(
            name="Office Phone",
            allow_override=False,
        )
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Office Phone", "text_value": "555-1234"}
            ],
        )
        # Even with existing value, should_update returns True
        assert field_def.should_update_descendant(task) is True

    def test_should_update_descendant_with_override_null_value(self) -> None:
        """should_update_descendant returns True when allow_override=True and value is None."""
        field_def = CascadingFieldDef(
            name="Platforms",
            allow_override=True,
        )
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Platforms", "multi_enum_values": None}
            ],
        )
        assert field_def.should_update_descendant(task) is True

    def test_should_update_descendant_with_override_has_value(self) -> None:
        """should_update_descendant returns False when allow_override=True and value exists."""
        field_def = CascadingFieldDef(
            name="Platforms",
            allow_override=True,
        )
        task = Task(
            gid="123",
            custom_fields=[
                {
                    "gid": "456",
                    "name": "Platforms",
                    "multi_enum_values": [{"name": "Google"}],
                }
            ],
        )
        assert field_def.should_update_descendant(task) is False

    def test_get_value_from_custom_field(self) -> None:
        """get_value returns value from custom field."""
        field_def = CascadingFieldDef(name="Office Phone")
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Office Phone", "text_value": "555-1234"}
            ],
        )
        assert field_def.get_value(task) == "555-1234"

    def test_get_value_from_source_field(self) -> None:
        """get_value returns value from model attribute when source_field set."""
        field_def = CascadingFieldDef(
            name="Business Name",
            source_field="name",
        )
        task = Task(gid="123", name="Acme Corp")
        assert field_def.get_value(task) == "Acme Corp"

    def test_get_value_with_transform(self) -> None:
        """get_value applies transform function."""
        field_def = CascadingFieldDef(
            name="Office Phone",
            transform=lambda x: x.upper() if x else x,
        )
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Office Phone", "text_value": "test"}
            ],
        )
        assert field_def.get_value(task) == "TEST"

    def test_frozen_dataclass(self) -> None:
        """CascadingFieldDef is immutable (frozen)."""
        field_def = CascadingFieldDef(name="Test")
        with pytest.raises(AttributeError):
            field_def.name = "Changed"  # type: ignore[misc]


class TestInheritedFieldDef:
    """Tests for InheritedFieldDef class."""

    def test_default_allow_override_is_true(self) -> None:
        """allow_override defaults to True for inherited fields."""
        field_def = InheritedFieldDef(name="Vertical")
        assert field_def.allow_override is True

    def test_override_field_name_default(self) -> None:
        """override_field_name defaults to '{name} Override'."""
        field_def = InheritedFieldDef(name="Vertical")
        assert field_def.override_field_name == "Vertical Override"

    def test_override_field_name_custom(self) -> None:
        """override_field_name uses custom field when set."""
        field_def = InheritedFieldDef(
            name="Vertical",
            override_flag_field="Custom Override Field",
        )
        assert field_def.override_field_name == "Custom Override Field"

    def test_applies_to_with_matching_inherit_from(self) -> None:
        """applies_to returns True when entity type is in inherit_from."""
        field_def = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],
        )
        # Note: applies_to checks if type is in inherit_from (parent types)
        # For a Task, it would be False unless Task is in inherit_from
        task = Task(gid="123")
        assert field_def.applies_to(task) is False

    def test_is_overridden_true(self) -> None:
        """is_overridden returns True when override flag is set."""
        field_def = InheritedFieldDef(name="Vertical")
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Vertical Override", "text_value": "Yes"}
            ],
        )
        assert field_def.is_overridden(task) is True

    def test_is_overridden_false_no_flag(self) -> None:
        """is_overridden returns False when override flag not set."""
        field_def = InheritedFieldDef(name="Vertical")
        task = Task(gid="123", custom_fields=[])
        assert field_def.is_overridden(task) is False

    def test_is_overridden_false_when_allow_override_false(self) -> None:
        """is_overridden returns False when allow_override=False."""
        field_def = InheritedFieldDef(
            name="Manager",
            allow_override=False,
        )
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Manager Override", "text_value": "Yes"}
            ],
        )
        assert field_def.is_overridden(task) is False

    def test_resolve_with_local_override(self) -> None:
        """resolve returns local value when override flag is set."""
        field_def = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit"],
        )
        entity = Task(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "text_value": "Legal"},
                {"gid": "2", "name": "Vertical Override", "text_value": "Yes"},
            ],
        )
        parent = Task(
            gid="456",
            custom_fields=[
                {"gid": "3", "name": "Vertical", "text_value": "Medical"},
            ],
        )
        # Local override should win
        result = field_def.resolve(entity, [parent])
        assert result == "Legal"

    def test_resolve_inherits_from_parent(self) -> None:
        """resolve returns parent value when no local override."""
        field_def = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Task"],  # Task is the parent type
        )
        entity = Task(gid="123", custom_fields=[])
        parent = Task(
            gid="456",
            custom_fields=[
                {"gid": "1", "name": "Vertical", "text_value": "Medical"},
            ],
        )
        result = field_def.resolve(entity, [parent])
        assert result == "Medical"

    def test_resolve_returns_default(self) -> None:
        """resolve returns default when no parent has value."""
        field_def = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit"],
            default="Unknown",
        )
        entity = Task(gid="123", custom_fields=[])
        parent = Task(gid="456", custom_fields=[])
        result = field_def.resolve(entity, [parent])
        assert result == "Unknown"

    def test_frozen_dataclass(self) -> None:
        """InheritedFieldDef is immutable (frozen)."""
        field_def = InheritedFieldDef(name="Test")
        with pytest.raises(AttributeError):
            field_def.name = "Changed"  # type: ignore[misc]


# ============================================================================
# WS1-S3: Auto-Wire Cascading Field Registry Tests
# ============================================================================


class TestCascadingFieldRegistryAutoWire:
    """Tests verifying descriptor-driven cascading field registry.

    Per ARCH-descriptor-driven-auto-wiring section 3.5: The auto-wired
    _build_cascading_field_registry() discovers Business and Unit as
    cascading field providers via descriptor cascading_field_provider=True.
    """

    def test_registry_discovers_business_provider(self) -> None:
        """Business cascading fields are discovered via descriptor."""
        registry = get_cascading_field_registry()
        # Business.CascadingFields declares: OFFICE_PHONE, COMPANY_ID,
        # BUSINESS_NAME, PRIMARY_CONTACT_PHONE
        result = registry.get("office phone")
        assert result is not None
        owner_class, field_def = result
        assert owner_class.__name__ == "Business"
        assert field_def.name == "Office Phone"

    def test_registry_discovers_unit_provider(self) -> None:
        """Unit cascading fields are discovered via descriptor."""
        registry = get_cascading_field_registry()
        # Unit.CascadingFields declares: PLATFORMS, VERTICAL, BOOKING_TYPE,
        # MRR, WEEKLY_AD_SPEND
        result = registry.get("vertical")
        assert result is not None
        owner_class, field_def = result
        assert owner_class.__name__ == "Unit"
        assert field_def.name == "Vertical"

    def test_registry_contains_all_business_fields(self) -> None:
        """All Business cascading fields are present in the registry."""
        registry = get_cascading_field_registry()
        expected_business_fields = [
            "office phone",
            "company id",
            "business name",
            "primary contact phone",
        ]
        for field_name in expected_business_fields:
            assert field_name in registry, (
                f"Business field {field_name!r} missing from registry"
            )
            owner_class, _ = registry[field_name]
            assert owner_class.__name__ == "Business"

    def test_registry_contains_all_unit_fields(self) -> None:
        """All Unit cascading fields are present in the registry."""
        registry = get_cascading_field_registry()
        expected_unit_fields = [
            "platforms",
            "vertical",
            "booking type",
            "mrr",
            "weekly ad spend",
        ]
        for field_name in expected_unit_fields:
            assert field_name in registry, (
                f"Unit field {field_name!r} missing from registry"
            )
            owner_class, _ = registry[field_name]
            assert owner_class.__name__ == "Unit"

    def test_non_provider_descriptors_are_skipped(self) -> None:
        """Descriptors without cascading_field_provider=True are not in registry."""
        from autom8_asana.core.entity_registry import get_registry

        registry_obj = get_registry()
        # Verify that offer, contact, etc. do NOT have cascading_field_provider
        for name in ("offer", "contact", "asset_edit", "process", "location"):
            desc = registry_obj.get(name)
            assert desc is not None
            assert desc.cascading_field_provider is False, (
                f"Descriptor {name!r} should not be a cascading field provider"
            )

    def test_only_two_providers_exist(self) -> None:
        """Only business and unit are cascading field providers."""
        from autom8_asana.core.entity_registry import get_registry

        providers = [
            desc.name
            for desc in get_registry().all_descriptors()
            if desc.cascading_field_provider
        ]
        assert sorted(providers) == ["business", "unit"]

    def test_get_cascading_field_helper_works(self) -> None:
        """get_cascading_field() works with auto-wired registry."""
        result = get_cascading_field("Office Phone")
        assert result is not None
        owner_class, field_def = result
        assert owner_class.__name__ == "Business"
        assert field_def.name == "Office Phone"

        # Case-insensitive
        result_lower = get_cascading_field("office phone")
        assert result_lower is not None
        assert result_lower[0].__name__ == "Business"

    def test_get_cascading_field_unknown_returns_none(self) -> None:
        """get_cascading_field() returns None for unknown fields."""
        assert get_cascading_field("Unknown Field XYZ") is None

    def test_build_is_deterministic(self) -> None:
        """_build_cascading_field_registry() returns same keys each call."""
        result1 = _build_cascading_field_registry()
        result2 = _build_cascading_field_registry()
        assert set(result1.keys()) == set(result2.keys())
        for key in result1:
            owner1, fd1 = result1[key]
            owner2, fd2 = result2[key]
            assert owner1.__name__ == owner2.__name__
            assert fd1.name == fd2.name
