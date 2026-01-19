"""Tests for BusinessEntity and HolderMixin base classes.

Per TDD-BIZMODEL: Tests for base classes.
"""

from __future__ import annotations

from typing import ClassVar

from autom8_asana.models.business.base import BusinessEntity, HolderMixin
from autom8_asana.models.task import Task


class TestBusinessEntity:
    """Tests for BusinessEntity base class."""

    def test_business_entity_inherits_from_task(self) -> None:
        """BusinessEntity inherits from Task."""
        entity = BusinessEntity(gid="123", name="Test Entity")
        assert entity.gid == "123"
        assert entity.name == "Test Entity"

    def test_name_convention_class_attribute(self) -> None:
        """BusinessEntity has NAME_CONVENTION class attribute."""
        assert hasattr(BusinessEntity, "NAME_CONVENTION")
        assert BusinessEntity.NAME_CONVENTION == "{name}"

    def test_primary_project_gid_class_attribute(self) -> None:
        """BusinessEntity has PRIMARY_PROJECT_GID class attribute."""
        assert hasattr(BusinessEntity, "PRIMARY_PROJECT_GID")
        assert BusinessEntity.PRIMARY_PROJECT_GID is None

    def test_invalidate_refs_no_op(self) -> None:
        """_invalidate_refs is no-op on base class."""
        entity = BusinessEntity(gid="123")
        # Should not raise
        entity._invalidate_refs()

    def test_get_cascading_fields_empty(self) -> None:
        """get_cascading_fields returns empty list on base class."""
        entity = BusinessEntity(gid="123")
        assert entity.get_cascading_fields() == []

    def test_get_inherited_fields_empty(self) -> None:
        """get_inherited_fields returns empty list on base class."""
        entity = BusinessEntity(gid="123")
        assert entity.get_inherited_fields() == []


class TestBusinessEntitySubclass:
    """Tests for subclassing BusinessEntity."""

    def test_subclass_can_override_name_convention(self) -> None:
        """Subclass can override NAME_CONVENTION."""

        class MyEntity(BusinessEntity):
            NAME_CONVENTION = "{name} - {vertical}"

        assert MyEntity.NAME_CONVENTION == "{name} - {vertical}"

    def test_subclass_can_override_primary_project_gid(self) -> None:
        """Subclass can override PRIMARY_PROJECT_GID."""

        class MyEntity(BusinessEntity):
            PRIMARY_PROJECT_GID = "123456789"

        assert MyEntity.PRIMARY_PROJECT_GID == "123456789"

    def test_subclass_instance_has_custom_fields(self) -> None:
        """Subclass instances can use custom field accessors."""

        class MyEntity(BusinessEntity):
            pass

        entity = MyEntity(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Test Field", "text_value": "test"}],
        )
        assert entity.get_custom_fields().get("Test Field") == "test"


class TestHolderMixin:
    """Tests for HolderMixin class."""

    def test_holder_mixin_generic_type(self) -> None:
        """HolderMixin is generic over child type."""

        class MyHolder(Task, HolderMixin[Task]):
            CHILD_TYPE: ClassVar[type[Task]] = Task

        holder = MyHolder(gid="123")
        assert hasattr(holder, "_children_cache")

    def test_invalidate_cache(self) -> None:
        """invalidate_cache sets _children_cache to None."""

        class MyHolder(Task, HolderMixin[Task]):
            CHILD_TYPE: ClassVar[type[Task]] = Task

        holder = MyHolder(gid="123")
        holder._children_cache = [Task(gid="1"), Task(gid="2")]
        holder.invalidate_cache()
        assert holder._children_cache is None

    def test_populate_children_sorts_by_created_at(self) -> None:
        """_populate_children sorts by created_at."""

        class MyHolder(Task, HolderMixin[Task]):
            CHILD_TYPE: ClassVar[type[Task]] = Task

        holder = MyHolder(gid="123")
        subtasks = [
            Task(gid="2", name="Second", created_at="2024-01-02T00:00:00Z"),
            Task(gid="1", name="First", created_at="2024-01-01T00:00:00Z"),
            Task(gid="3", name="Third", created_at="2024-01-03T00:00:00Z"),
        ]
        holder._populate_children(subtasks)

        assert holder._children_cache is not None
        assert len(holder._children_cache) == 3
        # Should be sorted by created_at
        assert holder._children_cache[0].name == "First"
        assert holder._children_cache[1].name == "Second"
        assert holder._children_cache[2].name == "Third"

    def test_populate_children_fallback_to_name(self) -> None:
        """_populate_children uses name as fallback when created_at same."""

        class MyHolder(Task, HolderMixin[Task]):
            CHILD_TYPE: ClassVar[type[Task]] = Task

        holder = MyHolder(gid="123")
        subtasks = [
            Task(gid="2", name="Bravo", created_at="2024-01-01T00:00:00Z"),
            Task(gid="1", name="Alpha", created_at="2024-01-01T00:00:00Z"),
        ]
        holder._populate_children(subtasks)

        assert holder._children_cache is not None
        # Same created_at, sorted by name
        assert holder._children_cache[0].name == "Alpha"
        assert holder._children_cache[1].name == "Bravo"

    def test_set_child_parent_ref_default_noop(self) -> None:
        """_set_child_parent_ref is no-op by default."""

        class MyHolder(Task, HolderMixin[Task]):
            CHILD_TYPE: ClassVar[type[Task]] = Task

        holder = MyHolder(gid="123")
        child = Task(gid="456")
        # Should not raise
        holder._set_child_parent_ref(child)
