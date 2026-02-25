"""Base classes for Business Model layer.

Per TDD-BIZMODEL: HolderMixin and BusinessEntity base class.
Per TDD-HARDENING-C: Enhanced with ClassVar configuration and auto-discovery.
Per TDD-PATTERNS-A: Custom field descriptor support with Fields auto-generation.
Per TDD-registry-consolidation: Registration moved to _bootstrap.py (explicit bootstrap).
Per ADR-0050: Holder lazy loading with prefetch support.
Per ADR-0052: Cached bidirectional references with explicit invalidation.
Per ADR-0075: Navigation descriptor pattern support.
Per ADR-0076: Auto-invalidation strategy.
Per ADR-0082: Fields class auto-generation from descriptors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from autom8y_log import get_logger
from pydantic import ConfigDict, PrivateAttr

from autom8_asana.models.business.descriptors import (
    CustomFieldDescriptor,
    DateField,
    EnumField,
    HolderRef,
    IntField,
    MultiEnumField,
    NumberField,
    ParentRef,
    PeopleField,
    TextField,
    _pending_fields,
)
from autom8_asana.models.task import Task

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.fields import CascadingFieldDef, InheritedFieldDef


logger = get_logger(__name__)
T = TypeVar("T", bound=Task)


class HolderMixin(Generic[T]):
    """Mixin for holder tasks that contain typed children.

    Per ADR-0050: Holder lazy loading with prefetch support.
    Per TDD-HARDENING-C: ClassVar configuration for single _populate_children().
    Per TDD-registry-consolidation: Registration moved to _bootstrap.py.

    Holders group related child tasks under a parent. Each holder
    maintains a cached list of typed children that is populated
    by SaveSession during prefetch.

    Configuration ClassVars (set by subclass):
        CHILD_TYPE: Type of child entities (e.g., Contact).
        PARENT_REF_NAME: PrivateAttr name on child for holder ref (e.g., "_contact_holder").
        BUSINESS_REF_NAME: PrivateAttr name on child for business ref (default "_business").
        CHILDREN_ATTR: PrivateAttr name for children list (e.g., "_contacts").
        PRIMARY_PROJECT_GID: Optional project GID for registry detection.

    Example:
        class ContactHolder(Task, HolderMixin[Contact]):
            CHILD_TYPE: ClassVar[type[Contact]] = Contact
            PARENT_REF_NAME: ClassVar[str] = "_contact_holder"
            CHILDREN_ATTR: ClassVar[str] = "_contacts"
            PRIMARY_PROJECT_GID: ClassVar[str | None] = "1201500116978260"

            _contacts: list[Contact] = PrivateAttr(default_factory=list)
    """

    # Must be overridden by subclass
    CHILD_TYPE: ClassVar[type[Task]]

    # Optional ClassVars for generic _populate_children() (TDD-HARDENING-C)
    PARENT_REF_NAME: ClassVar[str] = ""  # e.g., "_contact_holder"
    BUSINESS_REF_NAME: ClassVar[str] = "_business"
    CHILDREN_ATTR: ClassVar[str] = "_children_cache"  # Default to legacy attr

    # Per TDD-DETECTION/ADR-0093: Primary project GID for holder type detection
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

    # Children cache - subclasses should define their own typed PrivateAttr
    _children_cache: list[T] | None = PrivateAttr(default=None)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize holder subclass.

        Per TDD-registry-consolidation: Registration REMOVED from __init_subclass__.
            Registration now happens explicitly via register_all_models() in _bootstrap.py.

        Args:
            **kwargs: Passed to parent __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Per TDD-registry-consolidation: Registration REMOVED from __init_subclass__.
        # Registration now happens explicitly via register_all_models() in _bootstrap.py.
        # Do NOT register here - it causes import-order-dependent behavior.

    def _populate_children(self, subtasks: list[Task]) -> None:
        """Populate typed children from fetched subtasks.

        Per FR-HOLD-001: Base implementation handles sorting, typing, reference setting.
        Per FR-HOLD-007: Sort by (created_at, name) for stability.

        Subclasses may override for special logic (see LocationHolder for Hours).
        When overriding, call super()._populate_children() for standard children.

        Args:
            subtasks: List of Task subtasks from API.
        """
        # Sort by created_at (oldest first), then by name for stability
        sorted_tasks = sorted(
            subtasks,
            key=lambda t: (t.created_at or "", t.name or ""),
        )

        # Get configuration from class
        child_type = getattr(self.__class__, "CHILD_TYPE", Task)
        parent_ref_name = getattr(self.__class__, "PARENT_REF_NAME", "")
        business_ref_name = getattr(self.__class__, "BUSINESS_REF_NAME", "_business")
        children_attr = getattr(self.__class__, "CHILDREN_ATTR", "_children_cache")

        # Build children list
        children: list[T] = []
        for task in sorted_tasks:
            child = child_type.model_validate(task, from_attributes=True)

            # Set parent reference (holder -> child) if configured
            if parent_ref_name:
                setattr(child, parent_ref_name, self)

            # Propagate business reference if available
            business_ref = getattr(self, business_ref_name, None)
            if business_ref is not None:
                setattr(child, business_ref_name, business_ref)

            children.append(cast("T", child))

        # Store in children list
        setattr(self, children_attr, children)

    def _set_child_parent_ref(self, child: T) -> None:
        """Set parent references on a single child.

        Called when adding individual children outside _populate_children.

        Per TDD-HARDENING-C: Uses ClassVar configuration when available.

        Args:
            child: Child entity to set references on.
        """
        parent_ref_name = getattr(self.__class__, "PARENT_REF_NAME", "")
        business_ref_name = getattr(self.__class__, "BUSINESS_REF_NAME", "_business")

        if parent_ref_name:
            setattr(child, parent_ref_name, self)

        business_ref = getattr(self, business_ref_name, None)
        if business_ref is not None:
            setattr(child, business_ref_name, business_ref)

    def invalidate_cache(self) -> None:
        """Invalidate children cache.

        Called when hierarchy changes and cache may be stale.
        Subclasses may override to clear additional state.
        """
        children_attr = getattr(self.__class__, "CHILDREN_ATTR", "_children_cache")
        setattr(self, children_attr, [])


class BusinessEntity(Task):
    """Base class for business model entities.

    Per TDD-BIZMODEL: Extends Task with business-specific attributes
    for naming conventions, primary project, and field definitions.
    Per TDD-HARDENING-C: Auto-discovery of cached ref attrs via __init_subclass__.
    Per ADR-0076: Base _invalidate_refs() clears discovered refs.

    All business entities (Business, Contact, Unit, Offer, etc.)
    should inherit from this base class.

    Class Attributes:
        NAME_CONVENTION: Naming convention for this entity type.
        PRIMARY_PROJECT_GID: GID of the primary Asana project.
        _CACHED_REF_ATTRS: Auto-discovered tuple of PrivateAttr names holding refs.
            Populated automatically by __init_subclass__ based on annotations
            matching pattern: underscore prefix + Optional type (T | None).

    Example:
        class Business(BusinessEntity):
            NAME_CONVENTION = "{name}"
            PRIMARY_PROJECT_GID = "123456789"

        class Contact(BusinessEntity):
            _business: Business | None = PrivateAttr(default=None)
            _contact_holder: ContactHolder | None = PrivateAttr(default=None)
            # _CACHED_REF_ATTRS auto-discovered: ("_business", "_contact_holder")
    """

    # Configure Pydantic to work with descriptors (ADR-0075, ADR-0077, ADR-0081)
    # - ignored_types: Prevents descriptors from being treated as model fields
    # - extra="allow": Allows setting attributes that aren't model fields
    #   (necessary for descriptor __set__ to be called)
    model_config = ConfigDict(
        ignored_types=(
            ParentRef,
            HolderRef,
            CustomFieldDescriptor,
            TextField,
            EnumField,
            MultiEnumField,
            NumberField,
            IntField,
            PeopleField,
            DateField,
        ),
        extra="allow",
    )

    # Class attributes - override in subclasses
    NAME_CONVENTION: ClassVar[str] = "{name}"
    PRIMARY_PROJECT_GID: ClassVar[str | None] = None

    # Auto-discovered by __init_subclass__ (ADR-0076)
    _CACHED_REF_ATTRS: ClassVar[tuple[str, ...]] = ()

    # Field definitions - override in subclasses with inner class pattern
    # e.g., class CascadingFields: ...

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-discover cached reference attributes and generate Fields class.

        Per FR-INV-001: Discovers attrs matching pattern:
        - Starts with underscore
        - Annotation contains optional type (T | None)
        - Not a list type (those are children, not refs)

        Per ADR-0082: Generates Fields class from registered custom field descriptors.
        Per TDD-registry-consolidation: Registration REMOVED from __init_subclass__.
            Registration now happens explicitly via register_all_models() in _bootstrap.py.

        IMPORTANT: Works correctly with Pydantic models because Pydantic
        also uses __init_subclass__ and this runs after class creation.

        Args:
            **kwargs: Passed to parent __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Collect PrivateAttrs that look like references
        ref_attrs: list[str] = []

        # Check annotations for this class (not inherited)
        for name, annotation in getattr(cls, "__annotations__", {}).items():
            if not name.startswith("_"):
                continue

            # Convert annotation to string for pattern matching
            ann_str = str(annotation)

            # Skip list types (children storage, not references)
            if "list[" in ann_str.lower():
                continue

            # Look for optional types (T | None pattern)
            if "| None" in ann_str or "Optional" in ann_str:
                ref_attrs.append(name)

        # Combine with parent's refs (for inheritance)
        parent_refs: tuple[str, ...] = ()
        for base in cls.__bases__:
            parent_refs = getattr(base, "_CACHED_REF_ATTRS", ())
            if parent_refs:
                break

        cls._CACHED_REF_ATTRS = tuple(set(parent_refs) | set(ref_attrs))

        # Generate Fields class from registered custom field descriptors (ADR-0082)
        # Per TDD-SPRINT-1: Also collect fields from mixin base classes
        field_constants: dict[str, str] = {}

        # First, collect from the entity class itself
        owner_id = id(cls)
        if owner_id in _pending_fields:
            field_constants.update(_pending_fields.pop(owner_id))

        # Then, collect from mixin base classes (excluding Task, BusinessEntity, object)
        # This handles fields inherited from SharedCascadingFieldsMixin, FinancialFieldsMixin, etc.
        for base in cls.__mro__:
            if base in (cls, Task, BusinessEntity, object):
                continue
            base_id = id(base)
            if base_id in _pending_fields:
                # Don't pop - mixin may be used by multiple entity classes
                for const_name, field_name in _pending_fields[base_id].items():
                    if const_name not in field_constants:
                        field_constants[const_name] = field_name

        if field_constants:
            # Get or create Fields inner class
            existing_fields = getattr(cls, "Fields", None)

            if existing_fields is not None:
                # Check if we need to add new constants
                new_constants: dict[str, str] = {}
                for const_name, field_name in field_constants.items():
                    if not hasattr(existing_fields, const_name):
                        new_constants[const_name] = field_name

                if new_constants:
                    # Create subclass with new constants
                    fields_cls = type("Fields", (existing_fields,), new_constants)
                    cls.Fields = fields_cls  # type: ignore[attr-defined]
            else:
                # Create new Fields class
                fields_cls = type("Fields", (), field_constants)
                cls.Fields = fields_cls  # type: ignore[attr-defined]

        # Per TDD-registry-consolidation: Registration REMOVED from __init_subclass__.
        # Registration now happens explicitly via register_all_models() in _bootstrap.py.
        # Do NOT register here - it causes import-order-dependent behavior.

    @classmethod
    async def from_gid_async(
        cls,
        client: AsanaClient,
        gid: str,
        *,
        hydrate: bool = True,
    ) -> BusinessEntity:
        """Fetch and construct entity from GID.

        Per TDD-BIZMODEL: Async factory method for loading entities.
        Per ADR-0069: Standardized on `hydrate` parameter for hierarchy loading.

        Args:
            client: AsanaClient for API calls.
            gid: Entity task GID.
            hydrate: If True, also fetch holder subtasks and children.

        Returns:
            Fully constructed entity with optional holders populated.
        """
        task_data = await client.tasks.get_async(gid)
        entity = cls.model_validate(task_data)

        if hydrate and hasattr(cls, "HOLDER_KEY_MAP"):
            await entity._fetch_holders_async(client)

        return entity

    async def _fetch_holders_async(self, client: AsanaClient) -> None:
        """Fetch and populate holder subtasks.

        Override in subclasses that have HOLDER_KEY_MAP.

        Args:
            client: AsanaClient for API calls.
        """
        pass  # Default: no-op, override in subclass

    def _invalidate_refs(self, _exclude_attr: str | None = None) -> None:
        """Invalidate all cached navigation references.

        Per FR-INV-001: Base implementation clears all discovered refs.
        Per FR-INV-002: Subclasses may override for additional logic.
        Per ADR-0076: Auto-invalidation strategy.

        Args:
            _exclude_attr: Attr to skip (used by descriptors to avoid
                clearing the attr that triggered invalidation).
        """
        for attr in self._CACHED_REF_ATTRS:
            if attr != _exclude_attr and hasattr(self, attr):
                try:
                    setattr(self, attr, None)
                except AttributeError:
                    # Some attrs may be read-only or not settable
                    logger.debug(
                        "invalidation_failed_readonly",
                        entity_type=type(self).__name__,
                        attr=attr,
                    )

    def get_cascading_fields(self) -> list[CascadingFieldDef]:
        """Get cascading field definitions for this entity.

        Returns:
            List of CascadingFieldDef instances.
        """
        cascading_fields_cls = getattr(self, "CascadingFields", None)
        if cascading_fields_cls and hasattr(cascading_fields_cls, "all"):
            result: list[CascadingFieldDef] = cascading_fields_cls.all()
            return result
        return []

    def get_inherited_fields(self) -> list[InheritedFieldDef]:
        """Get inherited field definitions for this entity.

        Returns:
            List of InheritedFieldDef instances.
        """
        inherited_fields_cls = getattr(self, "InheritedFields", None)
        if inherited_fields_cls and hasattr(inherited_fields_cls, "all"):
            result: list[InheritedFieldDef] = inherited_fields_cls.all()
            return result
        return []
