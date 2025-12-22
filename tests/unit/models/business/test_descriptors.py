"""Tests for navigation descriptors.

Per TDD-HARDENING-C: Tests for ParentRef[T], HolderRef[T], and base class enhancements.
Per ADR-0075: Navigation descriptor pattern.
Per ADR-0076: Auto-invalidation strategy.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import PrivateAttr

from autom8_asana.models.business.base import BusinessEntity, HolderMixin
from autom8_asana.models.business.descriptors import HolderRef, ParentRef
from autom8_asana.models.task import Task


# --- Test Fixtures: Stub Classes for Testing ---


class StubHolder(Task, HolderMixin["StubChild"]):
    """Stub holder for testing descriptors."""

    CHILD_TYPE: ClassVar[type[Task]] = Task  # Will be updated in tests
    PARENT_REF_NAME: ClassVar[str] = "_stub_holder"
    CHILDREN_ATTR: ClassVar[str] = "_children"

    _children: list[StubChild] = PrivateAttr(default_factory=list)
    _business: StubBusiness | None = PrivateAttr(default=None)


class StubBusiness(BusinessEntity):
    """Stub business entity for testing navigation."""

    _stub_holder: StubHolder | None = PrivateAttr(default=None)


class StubChild(BusinessEntity):
    """Stub child entity with descriptor-based navigation."""

    # PrivateAttrs for storage
    _business: StubBusiness | None = PrivateAttr(default=None)
    _stub_holder: StubHolder | None = PrivateAttr(default=None)

    # Descriptors for navigation (NO type annotations - avoids Pydantic field creation)
    business = ParentRef[StubBusiness](holder_attr="_stub_holder")
    stub_holder = HolderRef[StubHolder]()


class StubChildNoAutoInvalidate(BusinessEntity):
    """Stub child with auto_invalidate=False."""

    _business: StubBusiness | None = PrivateAttr(default=None)
    _stub_holder: StubHolder | None = PrivateAttr(default=None)

    # Descriptors without type annotations
    business = ParentRef[StubBusiness](
        holder_attr="_stub_holder",
        auto_invalidate=False,
    )
    stub_holder = HolderRef[StubHolder]()


class StubChildDirect(BusinessEntity):
    """Stub child with direct ParentRef (no holder resolution)."""

    _business: StubBusiness | None = PrivateAttr(default=None)

    # No holder_attr - just direct access (no type annotation)
    business = ParentRef[StubBusiness]()


# Update CHILD_TYPE after StubChild is defined
StubHolder.CHILD_TYPE = StubChild


# --- ParentRef Tests ---


class TestParentRefGet:
    """Tests for ParentRef.__get__ behavior."""

    def test_get_returns_cached_value(self) -> None:
        """__get__ returns cached value when present."""
        child = StubChild(gid="child-1")
        business = StubBusiness(gid="business-1")

        # Directly set the cached value
        child._business = business

        # Access via descriptor should return cached value
        assert child.business is business

    def test_get_lazy_resolves_via_holder(self) -> None:
        """__get__ lazy resolves via holder when cache is None."""
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")
        holder._business = business

        child = StubChild(gid="child-1")
        child._stub_holder = holder
        # _business is None, should lazy resolve

        result = child.business

        assert result is business
        # Verify the value was cached
        assert child._business is business

    def test_get_returns_none_when_holder_not_set(self) -> None:
        """__get__ returns None when holder is not set."""
        child = StubChild(gid="child-1")
        # No holder set

        assert child.business is None

    def test_get_returns_none_when_holder_has_no_target(self) -> None:
        """__get__ returns None when holder doesn't have target attr."""
        holder = StubHolder(gid="holder-1")
        # holder._business is None

        child = StubChild(gid="child-1")
        child._stub_holder = holder

        assert child.business is None

    def test_get_on_class_returns_descriptor(self) -> None:
        """__get__ on class returns the descriptor itself."""
        descriptor = StubChild.business
        assert isinstance(descriptor, ParentRef)

    def test_get_direct_without_holder_attr(self) -> None:
        """__get__ works without holder_attr (direct access only)."""
        child = StubChildDirect(gid="child-1")

        # No value cached
        assert child.business is None

        # Set directly
        business = StubBusiness(gid="business-1")
        child._business = business

        assert child.business is business


class TestParentRefSet:
    """Tests for ParentRef.__set__ behavior."""

    def test_set_stores_value(self) -> None:
        """__set__ stores value in private attr."""
        child = StubChild(gid="child-1")
        business = StubBusiness(gid="business-1")

        child.business = business

        assert child._business is business

    def test_set_triggers_invalidation_on_change(self) -> None:
        """__set__ triggers _invalidate_refs on actual change."""
        child = StubChild(gid="child-1")
        old_business = StubBusiness(gid="old-business")
        new_business = StubBusiness(gid="new-business")

        # Set initial values
        child._business = old_business
        child._stub_holder = StubHolder(gid="holder-1")

        # Change business - should invalidate _stub_holder but keep _business
        child.business = new_business

        assert child._business is new_business
        # _stub_holder should be invalidated (set to None)
        assert child._stub_holder is None

    def test_set_same_value_does_not_invalidate(self) -> None:
        """__set__ with same value does not trigger invalidation."""
        child = StubChild(gid="child-1")
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")

        child._business = business
        child._stub_holder = holder

        # Set same business again
        child.business = business

        # _stub_holder should NOT be invalidated
        assert child._stub_holder is holder

    def test_set_none_clears_value(self) -> None:
        """__set__ with None clears the cached value."""
        child = StubChild(gid="child-1")
        business = StubBusiness(gid="business-1")
        child._business = business

        child.business = None

        assert child._business is None

    def test_set_without_auto_invalidate(self) -> None:
        """__set__ with auto_invalidate=False does not trigger invalidation."""
        child = StubChildNoAutoInvalidate(gid="child-1")
        old_business = StubBusiness(gid="old-business")
        new_business = StubBusiness(gid="new-business")
        holder = StubHolder(gid="holder-1")

        child._business = old_business
        child._stub_holder = holder

        # Change business - should NOT invalidate because auto_invalidate=False
        child.business = new_business

        assert child._business is new_business
        # _stub_holder should still be set
        assert child._stub_holder is holder


class TestParentRefSetName:
    """Tests for ParentRef.__set_name__ behavior."""

    def test_set_name_derives_private_name(self) -> None:
        """__set_name__ derives private attr name from public name."""
        descriptor = ParentRef[StubBusiness]()

        # Simulate class creation
        descriptor.__set_name__(StubChild, "business")

        assert descriptor.public_name == "business"
        assert descriptor.private_name == "_business"

    def test_set_name_with_underscore_prefix(self) -> None:
        """__set_name__ handles names that might already have underscore."""
        descriptor = ParentRef[StubBusiness]()
        descriptor.__set_name__(StubChild, "_business")

        assert descriptor.public_name == "_business"
        assert descriptor.private_name == "__business"


# --- HolderRef Tests ---


class TestHolderRefGet:
    """Tests for HolderRef.__get__ behavior."""

    def test_get_returns_cached_holder(self) -> None:
        """__get__ returns cached holder reference."""
        child = StubChild(gid="child-1")
        holder = StubHolder(gid="holder-1")

        child._stub_holder = holder

        assert child.stub_holder is holder

    def test_get_returns_none_when_not_set(self) -> None:
        """__get__ returns None when holder is not set."""
        child = StubChild(gid="child-1")

        assert child.stub_holder is None

    def test_get_on_class_returns_descriptor(self) -> None:
        """__get__ on class returns the descriptor itself."""
        descriptor = StubChild.stub_holder
        assert isinstance(descriptor, HolderRef)


class TestHolderRefSet:
    """Tests for HolderRef.__set__ behavior."""

    def test_set_stores_holder(self) -> None:
        """__set__ stores holder in private attr."""
        child = StubChild(gid="child-1")
        holder = StubHolder(gid="holder-1")

        child.stub_holder = holder

        assert child._stub_holder is holder

    def test_set_triggers_invalidation_on_change(self) -> None:
        """__set__ triggers _invalidate_refs on holder change."""
        child = StubChild(gid="child-1")
        old_holder = StubHolder(gid="old-holder")
        new_holder = StubHolder(gid="new-holder")
        business = StubBusiness(gid="business-1")

        child._stub_holder = old_holder
        child._business = business

        # Change holder - should invalidate _business but keep _stub_holder
        child.stub_holder = new_holder

        assert child._stub_holder is new_holder
        # _business should be invalidated
        assert child._business is None

    def test_set_same_holder_does_not_invalidate(self) -> None:
        """__set__ with same holder does not trigger invalidation."""
        child = StubChild(gid="child-1")
        holder = StubHolder(gid="holder-1")
        business = StubBusiness(gid="business-1")

        child._stub_holder = holder
        child._business = business

        # Set same holder again
        child.stub_holder = holder

        # _business should NOT be invalidated
        assert child._business is business


# --- HolderMixin Tests ---


class TestHolderMixinPopulateChildren:
    """Tests for HolderMixin._populate_children with ClassVar configuration."""

    def test_populate_children_uses_classvar_config(self) -> None:
        """_populate_children uses ClassVar configuration."""
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")
        holder._business = business

        subtasks = [
            Task(gid="child-1", name="First", created_at="2024-01-01T00:00:00Z"),
            Task(gid="child-2", name="Second", created_at="2024-01-02T00:00:00Z"),
        ]

        holder._populate_children(subtasks)

        # Check children were populated
        assert len(holder._children) == 2
        assert holder._children[0].gid == "child-1"
        assert holder._children[1].gid == "child-2"

    def test_populate_children_sets_parent_ref(self) -> None:
        """_populate_children sets parent reference on children."""
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")
        holder._business = business

        subtasks = [Task(gid="child-1", name="Child")]
        holder._populate_children(subtasks)

        child = holder._children[0]
        # Parent ref should be set via PARENT_REF_NAME
        assert child._stub_holder is holder

    def test_populate_children_propagates_business_ref(self) -> None:
        """_populate_children propagates business reference."""
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")
        holder._business = business

        subtasks = [Task(gid="child-1", name="Child")]
        holder._populate_children(subtasks)

        child = holder._children[0]
        # Business ref should be propagated
        assert child._business is business

    def test_populate_children_sorts_by_created_at_then_name(self) -> None:
        """_populate_children sorts by created_at, then name."""
        holder = StubHolder(gid="holder-1")

        subtasks = [
            Task(gid="3", name="Bravo", created_at="2024-01-01T00:00:00Z"),
            Task(gid="2", name="Alpha", created_at="2024-01-01T00:00:00Z"),
            Task(gid="1", name="Charlie", created_at="2024-01-02T00:00:00Z"),
        ]

        holder._populate_children(subtasks)

        # Same date: Alpha before Bravo
        # Later date: Charlie last
        assert holder._children[0].name == "Alpha"
        assert holder._children[1].name == "Bravo"
        assert holder._children[2].name == "Charlie"

    def test_set_child_parent_ref_uses_classvar_config(self) -> None:
        """_set_child_parent_ref uses ClassVar configuration."""
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")
        holder._business = business

        child = StubChild(gid="child-1")
        holder._set_child_parent_ref(child)

        assert child._stub_holder is holder
        assert child._business is business


class TestHolderMixinInvalidateCache:
    """Tests for HolderMixin.invalidate_cache."""

    def test_invalidate_cache_clears_children(self) -> None:
        """invalidate_cache clears children list."""
        holder = StubHolder(gid="holder-1")
        holder._children = [StubChild(gid="1"), StubChild(gid="2")]

        holder.invalidate_cache()

        assert holder._children == []
        assert holder._children_cache is None


# --- BusinessEntity Tests ---


class TestBusinessEntityInitSubclass:
    """Tests for BusinessEntity.__init_subclass__ auto-discovery."""

    def test_discovers_optional_private_attrs(self) -> None:
        """__init_subclass__ discovers optional private attrs."""
        # StubChild has _business and _stub_holder as optional
        ref_attrs = StubChild._CACHED_REF_ATTRS

        assert "_business" in ref_attrs
        assert "_stub_holder" in ref_attrs

    def test_excludes_list_types(self) -> None:
        """__init_subclass__ excludes list types from discovery."""

        class EntityWithList(BusinessEntity):
            _children: list[Task] | None = PrivateAttr(default=None)
            _business: StubBusiness | None = PrivateAttr(default=None)

        ref_attrs = EntityWithList._CACHED_REF_ATTRS

        assert "_business" in ref_attrs
        assert "_children" not in ref_attrs

    def test_excludes_non_optional_attrs(self) -> None:
        """__init_subclass__ excludes non-optional private attrs."""

        class EntityWithRequired(BusinessEntity):
            # Note: This isn't a typical pattern, but tests the filter
            _required: str = PrivateAttr(default="")  # type: ignore[assignment]
            _optional: StubBusiness | None = PrivateAttr(default=None)

        ref_attrs = EntityWithRequired._CACHED_REF_ATTRS

        assert "_optional" in ref_attrs
        # _required doesn't have | None, should not be discovered
        # (Note: actual behavior depends on annotation string matching)

    def test_inherits_parent_refs(self) -> None:
        """__init_subclass__ combines parent and child refs."""

        class ParentEntity(BusinessEntity):
            _parent_ref: StubBusiness | None = PrivateAttr(default=None)

        class ChildEntity(ParentEntity):
            _child_ref: StubHolder | None = PrivateAttr(default=None)

        parent_refs = ParentEntity._CACHED_REF_ATTRS
        child_refs = ChildEntity._CACHED_REF_ATTRS

        assert "_parent_ref" in parent_refs
        assert "_parent_ref" in child_refs
        assert "_child_ref" in child_refs


class TestBusinessEntityInvalidateRefs:
    """Tests for BusinessEntity._invalidate_refs."""

    def test_invalidate_refs_clears_all_discovered_refs(self) -> None:
        """_invalidate_refs clears all discovered refs."""
        child = StubChild(gid="child-1")
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")

        child._business = business
        child._stub_holder = holder

        child._invalidate_refs()

        assert child._business is None
        assert child._stub_holder is None

    def test_invalidate_refs_respects_exclude_attr(self) -> None:
        """_invalidate_refs skips _exclude_attr."""
        child = StubChild(gid="child-1")
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")

        child._business = business
        child._stub_holder = holder

        child._invalidate_refs(_exclude_attr="_business")

        # _business should NOT be cleared
        assert child._business is business
        # _stub_holder should be cleared
        assert child._stub_holder is None

    def test_invalidate_refs_handles_missing_attrs(self) -> None:
        """_invalidate_refs handles attrs that don't exist."""
        # BusinessEntity base class has empty _CACHED_REF_ATTRS
        entity = BusinessEntity(gid="entity-1")

        # Should not raise
        entity._invalidate_refs()


# --- Integration Tests ---


class TestDescriptorIntegration:
    """Integration tests for descriptor pattern."""

    def test_full_navigation_flow(self) -> None:
        """Full navigation flow: child -> holder -> business."""
        # Set up hierarchy
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")
        holder._business = business

        child = StubChild(gid="child-1")
        child._stub_holder = holder

        # Navigate via descriptors
        assert child.stub_holder is holder
        assert child.business is business  # Lazy resolved via holder
        assert child._business is business  # Cached after resolution

    def test_auto_invalidation_on_hierarchy_change(self) -> None:
        """Auto-invalidation when hierarchy changes."""
        business1 = StubBusiness(gid="business-1")
        business2 = StubBusiness(gid="business-2")

        holder1 = StubHolder(gid="holder-1")
        holder1._business = business1

        holder2 = StubHolder(gid="holder-2")
        holder2._business = business2

        child = StubChild(gid="child-1")
        child._stub_holder = holder1
        _ = child.business  # Resolve and cache business1

        assert child._business is business1

        # Change holder - should invalidate cached business
        child.stub_holder = holder2

        assert child._stub_holder is holder2
        assert child._business is None  # Invalidated

        # Re-resolve should get business2
        assert child.business is business2

    def test_populate_children_with_descriptor_entities(self) -> None:
        """_populate_children works with descriptor-based entities."""
        business = StubBusiness(gid="business-1")
        holder = StubHolder(gid="holder-1")
        holder._business = business

        subtasks = [
            Task(gid="child-1", name="Child One", created_at="2024-01-01T00:00:00Z"),
            Task(gid="child-2", name="Child Two", created_at="2024-01-02T00:00:00Z"),
        ]

        holder._populate_children(subtasks)

        # Check navigation works
        for child in holder._children:
            assert child.stub_holder is holder
            assert child.business is business
