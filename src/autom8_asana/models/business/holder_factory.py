"""Holder factory base class using __init_subclass__ pattern.

Per TDD-PATTERNS-C: Declarative holder definitions with auto-configuration.
Per PRD-PATTERNS-C: Consolidates 4 near-identical stub holder implementations.
Per TDD-registry-consolidation: Registration moved to _bootstrap.py.

This module provides HolderFactory, a base class that uses Python's
__init_subclass__ hook to enable declarative holder definitions:

    class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
        '''Holder for DNA children.'''
        pass

This replaces ~70 lines of boilerplate per holder with 3-5 lines.
"""

from __future__ import annotations

import importlib
import re
from typing import TYPE_CHECKING, Any, ClassVar

from autom8y_log import get_logger
from pydantic import PrivateAttr

from autom8_asana.models.business.base import HolderMixin
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business


logger = get_logger(__name__)


def _camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case.

    Examples:
        AssetEdit -> asset_edit
        DNA -> dna
        Reconciliation -> reconciliation

    Args:
        name: CamelCase string.

    Returns:
        snake_case string.
    """
    # Insert underscore before uppercase letters (except at start)
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class HolderFactory(Task, HolderMixin[Task]):
    """Base class for holder tasks using __init_subclass__ pattern.

    Per TDD-PATTERNS-C: Automatically configures holder behavior based on
    class keyword arguments.
    Per TDD-SPRINT-5-CLEANUP: HolderFactory/HolderMixin relationship documented.

    Architecture:
        HolderFactory inherits from both Task (Pydantic model for Asana tasks)
        and HolderMixin[Task] (generic protocol for holder behavior).

        - Task: Provides gid, name, custom_fields, and all Asana task attributes
        - HolderMixin[Task]: Provides holder-specific typing and protocol

        HolderFactory then uses __init_subclass__ to auto-configure subclasses
        based on keyword arguments (child_type, parent_ref, etc.).

    MRO Note for Subclasses:
        When a subclass also inherits from UnitNestedHolderMixin (e.g., OfferHolder,
        ProcessHolder), the mixin must come FIRST to override HolderFactory.business:

            class OfferHolder(UnitNestedHolderMixin, HolderFactory, ...):
                # UnitNestedHolderMixin.business overrides HolderFactory.business
                pass

        This is necessary because HolderFactory.business simply returns _business,
        while UnitNestedHolderMixin.business navigates via _unit when needed.

    Usage:
        class DNAHolder(HolderFactory, child_type="DNA", parent_ref="_dna_holder"):
            '''Holder for DNA children.'''
            pass

        class ReconciliationHolder(
            HolderFactory,
            child_type="Reconciliation",
            parent_ref="_reconciliation_holder",
            semantic_alias="reconciliations",
        ):
            '''Holder for Reconciliation children with alias.'''
            pass

    This generates:
    - CHILD_TYPE, PARENT_REF_NAME, CHILDREN_ATTR class vars
    - _children PrivateAttr (or custom attr name via children_attr)
    - _business PrivateAttr
    - children property
    - business property
    - Optional semantic alias property
    - _populate_children method with dynamic import

    Class Arguments:
        child_type: Name of child class (e.g., "DNA", "Reconciliation").
            Used to infer module path and class name for dynamic import.
        parent_ref: Name of parent reference attribute on child entities
            (e.g., "_dna_holder"). Set on each child during population.
        children_attr: Name of children storage attribute (default: "_children").
            Override for holders with custom storage (e.g., "_asset_edits").
        semantic_alias: Optional alias property for children (e.g., "reconciliations").
            If provided, generates a property with this name that returns children.

    Example:
        # Define holder with semantic alias
        class AssetEditHolder(
            HolderFactory,
            child_type="AssetEdit",
            parent_ref="_asset_edit_holder",
            children_attr="_asset_edits",
            semantic_alias="asset_edits",
        ):
            pass

        # Use holder
        holder = AssetEditHolder.model_validate(task_data)
        holder._business = business
        holder._populate_children(subtasks)

        # Access children via either property
        assert holder.children == holder.asset_edits
        for child in holder.asset_edits:
            assert child._asset_edit_holder is holder
    """

    # ClassVars set by __init_subclass__ - provide defaults for base class
    CHILD_TYPE: ClassVar[type[Task]] = Task
    PARENT_REF_NAME: ClassVar[str] = ""
    CHILDREN_ATTR: ClassVar[str] = "_children"
    _CHILD_MODULE: ClassVar[str] = ""
    _CHILD_CLASS_NAME: ClassVar[str] = ""

    # Per TDD-DETECTION/ADR-0093: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

    # Storage - inherited by all subclasses
    # Note: Pydantic PrivateAttrs are inherited correctly
    _children: list[Any] = PrivateAttr(default_factory=list)
    _business: Business | None = PrivateAttr(default=None)

    def __init_subclass__(
        cls,
        *,
        child_type: str | None = None,
        parent_ref: str | None = None,
        children_attr: str = "_children",
        semantic_alias: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Configure holder subclass automatically.

        Per FR-FACTORY-001: Accept keyword arguments in class definition.
        Per FR-FACTORY-002: Auto-generate ClassVars.
        Per FR-FACTORY-005: Generate semantic alias property if requested.

        Args:
            child_type: Name of child class (e.g., "DNA", "Reconciliation").
                Module path inferred as autom8_asana.models.business.{lowercase}.
            parent_ref: Name of parent reference attribute on children.
                Defaults to "_{lowercase(child_type)}_holder" if not provided.
            children_attr: Name of children storage attribute (default: "_children").
            semantic_alias: Optional alias property name for children.
            **kwargs: Passed to parent __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Skip configuration for intermediate classes or base class
        if child_type is None:
            return

        # Store configuration in ClassVars (FR-FACTORY-002)
        cls._CHILD_CLASS_NAME = child_type
        # Convert CamelCase to snake_case for module path (e.g., AssetEdit -> asset_edit)
        module_name = _camel_to_snake(child_type)
        cls._CHILD_MODULE = f"autom8_asana.models.business.{module_name}"
        cls.PARENT_REF_NAME = parent_ref or f"_{module_name}_holder"
        cls.CHILDREN_ATTR = children_attr

        # Initially set CHILD_TYPE to Task (resolved at runtime in _populate_children)
        cls.CHILD_TYPE = Task

        # Generate semantic alias property if requested (FR-FACTORY-005)
        if semantic_alias and semantic_alias != "children":
            # Create property that returns children list
            def make_alias_property(alias_name: str) -> property:
                """Create closure for alias property."""

                def getter(self: HolderFactory) -> list[Any]:
                    return self.children

                return property(
                    getter,
                    doc=f"Alias for children with semantic name '{alias_name}'.",
                )

            setattr(cls, semantic_alias, make_alias_property(semantic_alias))

        logger.debug(
            "Configured HolderFactory subclass",
            extra={
                "class_name": cls.__name__,
                "child_type": child_type,
                "parent_ref": cls.PARENT_REF_NAME,
                "children_attr": children_attr,
                "semantic_alias": semantic_alias,
            },
        )

        # Per TDD-registry-consolidation: Registration REMOVED from __init_subclass__.
        # Registration now happens explicitly via register_all_models() in _bootstrap.py.
        # Do NOT register here - it causes import-order-dependent behavior.

    @property
    def children(self) -> list[Any]:
        """All child entities.

        Per FR-FACTORY-005: Auto-generated property.

        Returns:
            List of typed child entities from the configured children attribute.
        """
        return getattr(self, self.CHILDREN_ATTR, [])

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business.

        Per FR-FACTORY-005: Auto-generated property.

        Returns:
            Business entity or None if not populated.
        """
        return self._business

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate children from fetched subtasks.

        Per FR-FACTORY-003: Generic implementation with dynamic import.
        Per FR-FACTORY-004: Deferred import to avoid circular dependencies.
        Per FR-STUB-007: CHILD_TYPE set at runtime via import.
        Per FR-STUB-008: Bidirectional references set during population.

        Algorithm:
        1. Dynamically import child class using _CHILD_MODULE and _CHILD_CLASS_NAME
        2. Sort subtasks by (created_at, name) for stability
        3. Convert Task instances to typed children via model_validate()
        4. Set bidirectional references (parent_ref -> self, _business -> self._business)
        5. Store children in the configured children attribute

        Args:
            subtasks: List of Task subtasks from API.

        Raises:
            ImportError: If child module cannot be imported.
            AttributeError: If child class not found in module.
        """
        # Skip dynamic import if CHILD_TYPE already resolved (not the Task stub).
        # After the first call, CHILD_TYPE points to the concrete class, so
        # subsequent calls avoid the importlib overhead entirely.
        if self.__class__.CHILD_TYPE is Task:
            # Dynamic import to avoid circular imports at class definition time (FR-FACTORY-004)
            try:
                module = importlib.import_module(self._CHILD_MODULE)
                child_class = getattr(module, self._CHILD_CLASS_NAME)
            except ImportError as e:
                logger.error(
                    "Failed to import child module",
                    extra={
                        "holder_class": type(self).__name__,
                        "child_module": self._CHILD_MODULE,
                        "error": str(e),
                    },
                )
                raise
            except AttributeError as e:
                logger.error(
                    "Child class not found in module",
                    extra={
                        "holder_class": type(self).__name__,
                        "child_module": self._CHILD_MODULE,
                        "child_class_name": self._CHILD_CLASS_NAME,
                        "error": str(e),
                    },
                )
                raise

            # Update CHILD_TYPE for runtime type checking (FR-STUB-007)
            self.__class__.CHILD_TYPE = child_class

        child_class = self.__class__.CHILD_TYPE

        # Sort by (created_at, name) for stability
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        # Build children list with bidirectional references (FR-STUB-008)
        children: list[Any] = []
        for task in sorted_tasks:
            # Convert Task to typed child
            child = child_class.model_validate(task, from_attributes=True)

            # Set parent reference (holder -> child)
            setattr(child, self.PARENT_REF_NAME, self)

            # Propagate business reference (child is dynamically-typed at runtime)
            child._business = self._business  # type: ignore[attr-defined]  # set on BusinessEntity subclasses

            children.append(child)

        # Store in configured attribute
        setattr(self, self.CHILDREN_ATTR, children)

        logger.debug(
            "Populated holder children",
            extra={
                "holder_class": type(self).__name__,
                "holder_gid": self.gid,
                "child_count": len(children),
            },
        )


__all__ = ["HolderFactory"]
