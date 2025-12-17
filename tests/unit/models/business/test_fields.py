"""Tests for CascadingFieldDef and InheritedFieldDef.

Per TDD-BIZMODEL: Tests for field definition classes.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.fields import CascadingFieldDef, InheritedFieldDef
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
