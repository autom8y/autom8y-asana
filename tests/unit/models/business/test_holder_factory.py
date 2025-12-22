"""Tests for HolderFactory base class.

Per TDD-PATTERNS-C: Comprehensive test coverage for __init_subclass__ pattern.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import PrivateAttr

from autom8_asana.models.business.holder_factory import HolderFactory
from autom8_asana.models.task import Task


class TestHolderFactoryInitSubclass:
    """Test __init_subclass__ configuration."""

    def test_basic_configuration(self) -> None:
        """Test basic child_type and parent_ref configuration."""

        class TestHolder(
            HolderFactory,
            child_type="TestChild",
            parent_ref="_test_holder",
        ):
            pass

        assert TestHolder._CHILD_CLASS_NAME == "TestChild"
        # CamelCase converted to snake_case: TestChild -> test_child
        assert TestHolder._CHILD_MODULE == "autom8_asana.models.business.test_child"
        assert TestHolder.PARENT_REF_NAME == "_test_holder"
        assert TestHolder.CHILDREN_ATTR == "_children"

    def test_custom_children_attr(self) -> None:
        """Test custom children attribute name."""

        class TestHolder(
            HolderFactory,
            child_type="TestChild",
            parent_ref="_test_holder",
            children_attr="_custom_children",
        ):
            pass

        assert TestHolder.CHILDREN_ATTR == "_custom_children"

    def test_inferred_parent_ref(self) -> None:
        """Test parent_ref inference from child_type."""

        class TestHolder(HolderFactory, child_type="CustomEntity"):
            pass

        # Should infer _custom_entity_holder from CustomEntity (CamelCase -> snake_case)
        assert TestHolder.PARENT_REF_NAME == "_custom_entity_holder"

    def test_child_type_required_for_configuration(self) -> None:
        """Test that configuration only applies when child_type provided."""

        class IntermediateHolder(HolderFactory):
            """Intermediate class without configuration."""

            pass

        # Should retain defaults from HolderFactory
        assert IntermediateHolder._CHILD_CLASS_NAME == ""
        assert IntermediateHolder.PARENT_REF_NAME == ""


class TestSemanticAlias:
    """Test semantic alias property generation."""

    def test_semantic_alias_property(self) -> None:
        """Test that semantic alias property is generated."""

        class TestHolder(
            HolderFactory,
            child_type="Item",
            parent_ref="_item_holder",
            semantic_alias="items",
        ):
            pass

        # Create instance with mock data
        holder = TestHolder(gid="123", name="Test")

        # Alias property should exist
        assert hasattr(TestHolder, "items")

        # Both should return same list (empty initially)
        assert holder.children == holder.items  # type: ignore[attr-defined]

    def test_semantic_alias_same_as_children_skipped(self) -> None:
        """Test that alias named 'children' is not duplicated."""

        class TestHolder(
            HolderFactory,
            child_type="Item",
            parent_ref="_item_holder",
            semantic_alias="children",
        ):
            pass

        # Should only have one 'children' property (from base)
        # No duplicate property should be created
        assert hasattr(TestHolder, "children")

    def test_no_alias_when_not_specified(self) -> None:
        """Test that no alias is created when not specified."""

        class TestHolder(
            HolderFactory,
            child_type="Item",
            parent_ref="_item_holder",
        ):
            pass

        # Only 'children' should exist, not any custom alias
        assert hasattr(TestHolder, "children")
        assert not hasattr(TestHolder, "items")


class TestChildrenProperty:
    """Test children property behavior."""

    def test_children_returns_empty_list_by_default(self) -> None:
        """Test children returns empty list when not populated."""

        class TestHolder(
            HolderFactory,
            child_type="TestChild",
            parent_ref="_test_holder",
        ):
            pass

        holder = TestHolder(gid="123", name="Test")
        assert holder.children == []

    def test_children_returns_from_configured_attr(self) -> None:
        """Test children property returns from configured attribute."""

        class TestHolder(
            HolderFactory,
            child_type="TestChild",
            parent_ref="_test_holder",
            children_attr="_custom_list",
        ):
            _custom_list: list[Any] = PrivateAttr(default_factory=list)

        holder = TestHolder(gid="123", name="Test")
        holder._custom_list = ["item1", "item2"]

        assert holder.children == ["item1", "item2"]


class TestBusinessProperty:
    """Test business property behavior."""

    def test_business_returns_none_by_default(self) -> None:
        """Test business returns None when not set."""

        class TestHolder(
            HolderFactory,
            child_type="TestChild",
            parent_ref="_test_holder",
        ):
            pass

        holder = TestHolder(gid="123", name="Test")
        assert holder.business is None

    def test_business_returns_set_value(self) -> None:
        """Test business returns set value."""

        class TestHolder(
            HolderFactory,
            child_type="TestChild",
            parent_ref="_test_holder",
        ):
            pass

        holder = TestHolder(gid="123", name="Test")
        mock_business = MagicMock()
        holder._business = mock_business

        assert holder.business is mock_business


class TestClassVars:
    """Test ClassVar auto-generation."""

    def test_child_module_inference(self) -> None:
        """Test module path inference from child_type."""

        class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
            pass

        assert DNAHolder._CHILD_MODULE == "autom8_asana.models.business.dna"

        class ReconciliationHolder(
            HolderFactory,
            child_type="Reconciliation",
            parent_ref="_reconciliation_holder",
        ):
            pass

        assert (
            ReconciliationHolder._CHILD_MODULE
            == "autom8_asana.models.business.reconciliation"
        )

    def test_child_type_initially_task(self) -> None:
        """Test CHILD_TYPE is initially Task (resolved at runtime)."""

        class TestHolder(
            HolderFactory,
            child_type="TestChild",
            parent_ref="_test_holder",
        ):
            pass

        # Before _populate_children, CHILD_TYPE should be Task
        assert TestHolder.CHILD_TYPE is Task


class TestMigratedHolders:
    """Test the actual migrated holder classes."""

    def test_dna_holder_configuration(self) -> None:
        """Test DNAHolder has correct configuration."""
        from autom8_asana.models.business.business import DNAHolder

        assert DNAHolder._CHILD_CLASS_NAME == "DNA"
        assert DNAHolder._CHILD_MODULE == "autom8_asana.models.business.dna"
        assert DNAHolder.PARENT_REF_NAME == "_dna_holder"
        assert DNAHolder.CHILDREN_ATTR == "_children"

    def test_reconciliation_holder_configuration(self) -> None:
        """Test ReconciliationHolder has correct configuration."""
        from autom8_asana.models.business.business import ReconciliationHolder

        assert ReconciliationHolder._CHILD_CLASS_NAME == "Reconciliation"
        assert (
            ReconciliationHolder._CHILD_MODULE
            == "autom8_asana.models.business.reconciliation"
        )
        assert ReconciliationHolder.PARENT_REF_NAME == "_reconciliation_holder"
        assert ReconciliationHolder.CHILDREN_ATTR == "_children"

        # Semantic alias
        holder = ReconciliationHolder(gid="123", name="Test")
        assert hasattr(holder, "reconciliations")
        assert holder.children == holder.reconciliations

    def test_asset_edit_holder_configuration(self) -> None:
        """Test AssetEditHolder has correct configuration."""
        from autom8_asana.models.business.business import AssetEditHolder

        assert AssetEditHolder._CHILD_CLASS_NAME == "AssetEdit"
        assert (
            AssetEditHolder._CHILD_MODULE == "autom8_asana.models.business.asset_edit"
        )
        assert AssetEditHolder.PARENT_REF_NAME == "_asset_edit_holder"
        assert AssetEditHolder.CHILDREN_ATTR == "_asset_edits"

        # Semantic alias
        holder = AssetEditHolder(gid="123", name="Test")
        assert hasattr(holder, "asset_edits")
        assert holder.children == holder.asset_edits

    def test_videography_holder_configuration(self) -> None:
        """Test VideographyHolder has correct configuration."""
        from autom8_asana.models.business.business import VideographyHolder

        assert VideographyHolder._CHILD_CLASS_NAME == "Videography"
        assert (
            VideographyHolder._CHILD_MODULE
            == "autom8_asana.models.business.videography"
        )
        assert VideographyHolder.PARENT_REF_NAME == "_videography_holder"
        assert VideographyHolder.CHILDREN_ATTR == "_children"

        # Semantic alias
        holder = VideographyHolder(gid="123", name="Test")
        assert hasattr(holder, "videography")
        assert holder.children == holder.videography


class TestPopulateChildren:
    """Test _populate_children method."""

    def test_populate_children_with_dna(self) -> None:
        """Test _populate_children creates typed DNA children."""
        from autom8_asana.models.business.business import DNAHolder
        from autom8_asana.models.business.dna import DNA

        holder = DNAHolder(gid="holder123", name="DNA Holder")
        mock_business = MagicMock()
        holder._business = mock_business

        # Create mock subtasks
        task1 = Task(gid="task1", name="DNA 1", created_at="2025-01-01T00:00:00Z")
        task2 = Task(gid="task2", name="DNA 2", created_at="2025-01-02T00:00:00Z")

        holder._populate_children([task2, task1])  # Out of order

        # Children should be sorted by created_at
        assert len(holder.children) == 2
        assert holder.children[0].name == "DNA 1"
        assert holder.children[1].name == "DNA 2"

        # Children should be typed as DNA
        assert isinstance(holder.children[0], DNA)
        assert isinstance(holder.children[1], DNA)

        # Bidirectional references should be set
        assert holder.children[0]._dna_holder is holder
        assert holder.children[0]._business is mock_business

    def test_populate_children_with_reconciliation(self) -> None:
        """Test _populate_children creates typed Reconciliation children."""
        from autom8_asana.models.business.business import ReconciliationHolder
        from autom8_asana.models.business.reconciliation import Reconciliation

        holder = ReconciliationHolder(gid="holder123", name="Reconciliation Holder")
        mock_business = MagicMock()
        holder._business = mock_business

        task1 = Task(gid="task1", name="Recon 1", created_at="2025-01-01T00:00:00Z")

        holder._populate_children([task1])

        assert len(holder.children) == 1
        assert isinstance(holder.children[0], Reconciliation)
        assert holder.children[0]._reconciliation_holder is holder

        # Semantic alias should work
        assert holder.reconciliations == holder.children

    def test_populate_children_with_asset_edit(self) -> None:
        """Test _populate_children creates typed AssetEdit children."""
        from autom8_asana.models.business.asset_edit import AssetEdit
        from autom8_asana.models.business.business import AssetEditHolder

        holder = AssetEditHolder(gid="holder123", name="Asset Edit Holder")
        mock_business = MagicMock()
        holder._business = mock_business

        task1 = Task(gid="task1", name="Edit 1", created_at="2025-01-01T00:00:00Z")

        holder._populate_children([task1])

        # Uses custom children_attr
        assert len(holder._asset_edits) == 1
        assert isinstance(holder._asset_edits[0], AssetEdit)
        assert holder._asset_edits[0]._asset_edit_holder is holder

        # Children property should return same list
        assert holder.children == holder._asset_edits
        assert holder.asset_edits == holder._asset_edits

    def test_populate_children_with_videography(self) -> None:
        """Test _populate_children creates typed Videography children."""
        from autom8_asana.models.business.business import VideographyHolder
        from autom8_asana.models.business.videography import Videography

        holder = VideographyHolder(gid="holder123", name="Videography Holder")
        mock_business = MagicMock()
        holder._business = mock_business

        task1 = Task(gid="task1", name="Video 1", created_at="2025-01-01T00:00:00Z")

        holder._populate_children([task1])

        assert len(holder.children) == 1
        assert isinstance(holder.children[0], Videography)
        assert holder.children[0]._videography_holder is holder

        # Semantic alias
        assert holder.videography == holder.children

    def test_populate_children_sorting(self) -> None:
        """Test children are sorted by (created_at, name)."""
        from autom8_asana.models.business.business import DNAHolder

        holder = DNAHolder(gid="holder123", name="DNA Holder")

        # Create tasks with same created_at to test name sorting
        task1 = Task(gid="task1", name="B DNA", created_at="2025-01-01T00:00:00Z")
        task2 = Task(gid="task2", name="A DNA", created_at="2025-01-01T00:00:00Z")
        task3 = Task(gid="task3", name="C DNA", created_at="2024-12-01T00:00:00Z")

        holder._populate_children([task1, task2, task3])

        # First by created_at, then by name
        assert holder.children[0].name == "C DNA"  # Earliest date
        assert holder.children[1].name == "A DNA"  # Same date, A < B
        assert holder.children[2].name == "B DNA"  # Same date, B

    def test_populate_children_empty_list(self) -> None:
        """Test _populate_children with empty subtasks list."""
        from autom8_asana.models.business.business import DNAHolder

        holder = DNAHolder(gid="holder123", name="DNA Holder")
        holder._populate_children([])

        assert holder.children == []


class TestDeprecationAlias:
    """Test ReconciliationsHolder deprecation alias."""

    def test_reconciliations_holder_emits_warning(self) -> None:
        """Test ReconciliationsHolder emits deprecation warning."""
        from autom8_asana.models.business.business import ReconciliationsHolder

        with pytest.warns(DeprecationWarning, match="deprecated"):
            holder = ReconciliationsHolder(gid="123", name="Test")

        # Should still work
        assert holder.gid == "123"

    def test_reconciliations_holder_is_subclass(self) -> None:
        """Test ReconciliationsHolder inherits from ReconciliationHolder."""
        from autom8_asana.models.business.business import (
            ReconciliationHolder,
            ReconciliationsHolder,
        )

        assert issubclass(ReconciliationsHolder, ReconciliationHolder)


class TestPydanticCompatibility:
    """Test Pydantic model compatibility."""

    def test_model_validate_works(self) -> None:
        """Test model_validate works with migrated holders."""
        from autom8_asana.models.business.business import DNAHolder

        task_data = {
            "gid": "123",
            "name": "DNA Holder",
            "resource_type": "task",
        }

        holder = DNAHolder.model_validate(task_data)
        assert holder.gid == "123"
        assert holder.name == "DNA Holder"

    def test_private_attrs_accessible(self) -> None:
        """Test PrivateAttrs are accessible on instances."""
        from autom8_asana.models.business.business import DNAHolder

        holder = DNAHolder(gid="123", name="Test")

        # Should have _children and _business attrs
        assert hasattr(holder, "_children")
        assert hasattr(holder, "_business")

        # Should be settable
        holder._children = ["test"]
        assert holder._children == ["test"]

    def test_inheritance_chain(self) -> None:
        """Test inheritance chain is correct."""
        from autom8_asana.models.business.base import HolderMixin
        from autom8_asana.models.business.business import DNAHolder

        assert issubclass(DNAHolder, HolderFactory)
        assert issubclass(DNAHolder, Task)
        # HolderFactory inherits from HolderMixin
        assert issubclass(HolderFactory, HolderMixin)
