# Cascading and Inherited Fields - Implementation Guide

> Implementation patterns for ADR-0054. This document provides code sketches and integration details for engineers implementing the cascading fields feature.

## Overview

This guide covers implementation of two field patterns:
1. **Cascading Fields**: Multi-level values that propagate downward (any level -> descendants)
2. **Inherited Fields**: Values resolved from parent chain with optional override

## Critical Design Constraint

**`allow_override=False` is the DEFAULT behavior.**

This means:
- Parent value ALWAYS overwrites descendant value during cascade
- Descendants cannot maintain local overrides unless explicitly configured
- Only set `allow_override=True` when the specific business requirement demands it

**Examples:**
- `Business.office_phone` -> cascades to all descendants, NO override (default)
- `Unit.platforms` -> cascades to Offers, WITH override (explicit opt-in)

## Module Structure

```
src/autom8_asana/
+-- models/
|   +-- business/
|   |   +-- fields.py           # CascadingFieldDef, InheritedFieldDef
|   |   +-- business.py         # Business model with cascade declarations
|   |   +-- unit.py             # Unit model with cascading and inherited fields
|   |   +-- offer.py            # Offer model with inherited fields
+-- persistence/
|   +-- session.py              # cascade_field() method
|   +-- cascade.py              # CascadeOperation, CascadeExecutor
|   +-- reconciler.py           # CascadeReconciler for drift detection
```

## Pattern 1: Cascading Fields (Multi-Level)

### Field Definition Dataclass

```python
# src/autom8_asana/models/business/fields.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


@dataclass(frozen=True)
class CascadingFieldDef:
    """Definition of a custom field that cascades from owner to descendants.

    Supports MULTI-LEVEL cascading: any entity can declare cascading fields
    that propagate to its descendants. The owner level is implicit from
    where the field is declared.

    CRITICAL DESIGN CONSTRAINT:
    - allow_override=False is the DEFAULT
    - This means parent value ALWAYS overwrites descendant value
    - Only set allow_override=True when descendants should keep non-null values

    Attributes:
        name: Custom field name in Asana (must match exactly)
        target_types: Set of entity types to cascade to, or None for all descendants
        allow_override: If False (DEFAULT), always overwrite descendant value.
                       If True, only overwrite if descendant value is None.
        cascade_on_change: If True, change detection includes this field
        source_field: Model attribute to use as source (if not a custom field)
        transform: Optional function to transform value before cascading

    Example - No override (DEFAULT):
        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is default - parent always wins
        )

    Example - With override opt-in:
        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},
            allow_override=True,  # EXPLICIT: Offer can have its own value
        )
    """

    name: str
    target_types: set[type] | None = None  # None = all descendants
    allow_override: bool = False  # DEFAULT: NO override - parent always wins
    cascade_on_change: bool = True
    source_field: str | None = None
    transform: Callable[[Any], Any] | None = None

    def applies_to(self, entity: AsanaResource) -> bool:
        """Check if this cascade should apply to given entity.

        Args:
            entity: Entity to check (e.g., Unit, Offer instance)

        Returns:
            True if cascade targets this entity type
        """
        if self.target_types is None:
            return True  # None means all descendants
        return type(entity) in self.target_types

    def applies_to_type(self, entity_type: type) -> bool:
        """Check if this cascade applies to given entity class.

        Args:
            entity_type: Entity class (e.g., Unit, Offer)

        Returns:
            True if cascade targets this entity type
        """
        if self.target_types is None:
            return True
        return entity_type in self.target_types

    def get_value(self, entity: AsanaResource) -> Any:
        """Extract value from source entity.

        Args:
            entity: Source entity (e.g., Business, Unit)

        Returns:
            Value to cascade, optionally transformed
        """
        if self.source_field:
            value = getattr(entity, self.source_field, None)
        else:
            value = entity.get_custom_fields().get(self.name)

        if self.transform and value is not None:
            value = self.transform(value)

        return value

    def should_update_descendant(self, descendant: AsanaResource) -> bool:
        """Determine if descendant should be updated during cascade.

        Args:
            descendant: Entity that would receive the cascaded value

        Returns:
            True if descendant should be updated

        Logic:
            - allow_override=False (DEFAULT): Always update
            - allow_override=True: Only update if descendant has null value
        """
        if not self.allow_override:
            return True  # DEFAULT: Always overwrite

        # allow_override=True: Check if descendant has a value
        current_value = descendant.get_custom_fields().get(self.name)
        return current_value is None


@dataclass(frozen=True)
class InheritedFieldDef:
    """Definition of a custom field inherited from parent entities.

    This is for READ-TIME resolution (property access), not write-time propagation.
    For write-time propagation, use CascadingFieldDef.

    Inherited fields resolve their value from the nearest ancestor that
    has a value set. Optionally, child entities can override with local value.

    Attributes:
        name: Custom field name in Asana
        inherit_from: List of parent entity types, in resolution order
        allow_override: Whether child can set its own value
        override_flag_field: Custom field name tracking if locally overridden
        default: Default value if no ancestor has a value

    Example:
        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],
            allow_override=True,
        )
    """

    name: str
    inherit_from: list[str] = field(default_factory=list)
    allow_override: bool = True
    override_flag_field: str | None = None
    default: Any = None

    @property
    def override_field_name(self) -> str:
        """Name of the custom field tracking override status."""
        return self.override_flag_field or f"{self.name} Override"

    def should_inherit(self, entity: Any) -> bool:
        """Check if entity should inherit (not locally overridden).

        Args:
            entity: Entity to check

        Returns:
            True if should inherit from parent
        """
        if not self.allow_override:
            return True

        override_value = entity.get_custom_fields().get(self.override_field_name)
        return override_value not in ("Yes", "yes", True, "true", "1")
```

### Business Model with Cascade Declarations

```python
# src/autom8_asana/models/business/business.py

from __future__ import annotations
from typing import ClassVar, TYPE_CHECKING

from autom8_asana.models.task import Task
from autom8_asana.models.business.fields import CascadingFieldDef

if TYPE_CHECKING:
    from decimal import Decimal
    from autom8_asana.models.business.unit import Unit
    from autom8_asana.models.business.offer import Offer
    from autom8_asana.models.business.process import Process
    from autom8_asana.models.business.contact import Contact


class Business(Task):
    """Business entity - root of the hierarchy.

    Business is the top-level entity containing ContactHolder, UnitHolder,
    LocationHolder, etc. It owns cascading fields that propagate to descendants.

    CASCADING FIELDS: All use allow_override=False (DEFAULT).
    This means descendant values are ALWAYS overwritten during cascade.
    """

    # --- Cascading Field Declarations ---
    # These fields exist on Business and cascade to descendants
    # CRITICAL: allow_override=False is DEFAULT - parent always wins

    class CascadingFields:
        """Fields that cascade from Business to descendants.

        All fields use allow_override=False (DEFAULT).
        Descendant values are ALWAYS overwritten during cascade.
        """

        OFFICE_PHONE = CascadingFieldDef(
            name="Office Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is DEFAULT - no local overrides
        )

        COMPANY_ID = CascadingFieldDef(
            name="Company ID",
            target_types=None,  # None = all descendants
            # allow_override=False is DEFAULT
        )

        BUSINESS_NAME = CascadingFieldDef(
            name="Business Name",
            target_types={Unit, Offer},
            source_field="name",  # Maps from Task.name, not custom field
            # allow_override=False is DEFAULT
        )

        PRIMARY_CONTACT_PHONE = CascadingFieldDef(
            name="Primary Contact Phone",
            target_types={Unit, Offer, Process},
            # allow_override=False is DEFAULT
        )

        # Class method to get all field definitions
        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            """Return all cascading field definitions."""
            return [
                cls.OFFICE_PHONE,
                cls.COMPANY_ID,
                cls.BUSINESS_NAME,
                cls.PRIMARY_CONTACT_PHONE,
            ]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            """Get cascading field definition by name."""
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None

        @classmethod
        def get_target_types(cls, field_name: str) -> set[type] | None:
            """Get target entity types for a cascading field."""
            field_def = cls.get(field_name)
            return field_def.target_types if field_def else None

    # --- Custom Field Properties ---

    @property
    def office_phone(self) -> str | None:
        """Office phone number (cascading field - no override)."""
        return self.get_custom_fields().get("Office Phone")

    @office_phone.setter
    def office_phone(self, value: str | None) -> None:
        self.get_custom_fields().set("Office Phone", value)

    @property
    def company_id(self) -> str | None:
        """Company identifier (cascading field - no override)."""
        return self.get_custom_fields().get("Company ID")

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        self.get_custom_fields().set("Company ID", value)

    # ... other properties following same pattern
```

### Unit Model with Cascading Fields (Multi-Level Example)

```python
# src/autom8_asana/models/business/unit.py

from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from autom8_asana.models.task import Task
from autom8_asana.models.business.fields import CascadingFieldDef, InheritedFieldDef

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.offer import Offer
    from autom8_asana.models.business.process import Process


class Unit(Task):
    """Unit entity within a Business.

    Units contain OfferHolder and ProcessHolder. Unit can declare its own
    cascading fields that propagate to its descendants (Offers, Processes).

    MULTI-LEVEL CASCADING: Unit can cascade fields to its children,
    independent of Business-level cascading.
    """

    # Cached parent reference
    _business: Business | None = PrivateAttr(default=None)

    # --- Cascading Field Declarations (Unit -> Offer/Process) ---

    class CascadingFields:
        """Fields that cascade from Unit to its descendants.

        NOTE: Some fields allow override (explicit opt-in), others don't.
        """

        PLATFORMS = CascadingFieldDef(
            name="Platforms",
            target_types={Offer},  # Only cascade to Offers
            allow_override=True,   # EXPLICIT OPT-IN: Offers can keep their value
        )

        VERTICAL = CascadingFieldDef(
            name="Vertical",
            target_types={Offer, Process},
            # allow_override=False is DEFAULT - Offers get Unit's vertical
        )

        BOOKING_TYPE = CascadingFieldDef(
            name="Booking Type",
            target_types={Offer},
            # allow_override=False is DEFAULT
        )

        @classmethod
        def all(cls) -> list[CascadingFieldDef]:
            return [cls.PLATFORMS, cls.VERTICAL, cls.BOOKING_TYPE]

        @classmethod
        def get(cls, field_name: str) -> CascadingFieldDef | None:
            for field_def in cls.all():
                if field_def.name == field_name:
                    return field_def
            return None

    # --- Inherited Field Declarations (from Business) ---

    class InheritedFields:
        """Fields inherited from parent entities."""

        DEFAULT_VERTICAL = InheritedFieldDef(
            name="Default Vertical",
            inherit_from=["Business"],
            allow_override=True,
            default="General",
        )

    # --- Property Implementation ---

    @property
    def platforms(self) -> list[str] | None:
        """Platforms for this unit (cascades to Offers with override allowed)."""
        return self.get_custom_fields().get("Platforms")

    @platforms.setter
    def platforms(self, value: list[str] | None) -> None:
        self.get_custom_fields().set("Platforms", value)

    @property
    def vertical(self) -> str | None:
        """Vertical for this unit (cascades to Offers/Processes, no override)."""
        return self.get_custom_fields().get("Vertical")

    @vertical.setter
    def vertical(self, value: str | None) -> None:
        self.get_custom_fields().set("Vertical", value)

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business (cached)."""
        if self._business is None:
            self._business = self._resolve_business()
        return self._business

    def _resolve_business(self) -> Business | None:
        """Walk up tree to find Business."""
        from autom8_asana.models.business.business import Business

        current = getattr(self, 'parent', None)
        while current is not None:
            if isinstance(current, Business):
                return current
            current = getattr(current, 'parent', None)
        return None
```

### Cascade Operation and Executor

```python
# src/autom8_asana/persistence/cascade.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.batch.client import BatchClient
    from autom8_asana.batch.models import BatchResult


@dataclass
class CascadeOperation:
    """Represents a field cascade operation to be executed.

    Created when SaveSession.cascade_field() is called. Executed
    during commit_async() after CRUD operations complete.

    Supports multi-level cascading from any source entity.
    """

    source: AsanaResource  # Entity whose value is being cascaded (Business, Unit, etc.)
    field_name: str        # Custom field name to cascade
    field_gid: str | None  # Resolved GID (populated during execution)
    new_value: Any         # Value to propagate
    target_types: set[type] | None  # Entity type filter (None = all descendants)
    allow_override: bool   # If True, skip descendants with non-null values

    def __post_init__(self) -> None:
        """Validate operation parameters."""
        if not self.source.gid:
            raise ValueError("Cannot cascade from entity without GID")
        if self.source.gid.startswith("temp_"):
            raise ValueError("Cannot cascade from entity with temp GID")


class CascadeExecutor:
    """Executes cascade operations via batch API.

    Responsible for:
    1. Collecting descendant GIDs to update (scoped to source entity)
    2. Applying allow_override filtering
    3. Resolving custom field name to GID
    4. Building batch update requests
    5. Executing via BatchClient with chunking

    CRITICAL: Descendants are scoped to the source entity.
    - cascade from Unit X only affects Unit X's children
    - cascade from Business affects all Business descendants
    """

    def __init__(
        self,
        batch_client: BatchClient,
        resolver: Any = None,  # CustomFieldResolver for name->GID
    ) -> None:
        self._batch = batch_client
        self._resolver = resolver

    async def execute(
        self,
        cascades: list[CascadeOperation],
        descendants_cache: dict[str, list[AsanaResource]] | None = None,
    ) -> list[BatchResult]:
        """Execute all pending cascade operations.

        Args:
            cascades: List of cascade operations to execute
            descendants_cache: Optional pre-loaded descendants by source GID

        Returns:
            List of BatchResult for all update operations
        """
        if not cascades:
            return []

        all_updates: list[tuple[str, dict[str, Any]]] = []

        for cascade in cascades:
            # Get descendants of THIS SPECIFIC source entity
            descendants = await self._get_descendants(
                cascade.source,
                cascade.target_types,
                descendants_cache,
            )

            # Resolve field name to GID
            field_gid = await self._resolve_field_gid(cascade.field_name)
            cascade.field_gid = field_gid

            # Build update for each descendant (with override filtering)
            for descendant in descendants:
                # Skip entities without real GID
                if not descendant.gid or descendant.gid.startswith("temp_"):
                    continue

                # Handle allow_override behavior
                if cascade.allow_override:
                    # Only update if descendant value is null
                    current_value = descendant.get_custom_fields().get(cascade.field_name)
                    if current_value is not None:
                        continue  # Skip - descendant has override value

                # Default (allow_override=False): Always update
                all_updates.append((
                    descendant.gid,
                    {"custom_fields": {field_gid: cascade.new_value}},
                ))

        if not all_updates:
            return []

        # Execute via batch client (handles chunking)
        return await self._batch.update_tasks_async(all_updates)

    async def _get_descendants(
        self,
        source: AsanaResource,
        target_types: set[type] | None,
        cache: dict[str, list[AsanaResource]] | None,
    ) -> list[AsanaResource]:
        """Get descendant entities matching target types.

        IMPORTANT: Only returns descendants of the specific source entity,
        not all entities of that type across the entire hierarchy.

        Args:
            source: Root entity (Business, Unit, etc.)
            target_types: Entity type filter (None = all descendants)
            cache: Optional pre-loaded descendants

        Returns:
            List of descendant entities to update
        """
        if cache and source.gid in cache:
            all_descendants = cache[source.gid]
        else:
            # Fetch descendants of THIS source entity only
            all_descendants = await self._fetch_descendants(source)

        # Filter by target types
        if target_types is None:
            return all_descendants

        return [
            d for d in all_descendants
            if type(d) in target_types
        ]

    async def _fetch_descendants(
        self,
        source: AsanaResource,
    ) -> list[AsanaResource]:
        """Fetch all descendants of source entity.

        This requires traversing the subtask hierarchy starting from source.
        Implementation depends on how holders/children are structured.
        """
        # Implementation would use TasksClient to fetch subtasks recursively
        raise NotImplementedError("Requires TasksClient integration")

    async def _resolve_field_gid(self, field_name: str) -> str:
        """Resolve custom field name to GID.

        Args:
            field_name: Human-readable field name

        Returns:
            Asana GID for the custom field

        Raises:
            KeyError: If field not found
        """
        if self._resolver:
            return self._resolver.resolve(field_name)
        raise KeyError(f"Cannot resolve field GID for: {field_name}")
```

### SaveSession Integration

```python
# Addition to src/autom8_asana/persistence/session.py

from autom8_asana.persistence.cascade import CascadeOperation, CascadeExecutor
from autom8_asana.models.business.fields import CascadingFieldDef


class SaveSession:
    """Extended with cascade support for multi-level cascading."""

    def __init__(self, client: AsanaClient, ...) -> None:
        # ... existing init ...
        self._pending_cascades: list[CascadeOperation] = []
        self._cascade_executor = CascadeExecutor(
            batch_client=client.batch,
            resolver=getattr(client, '_field_resolver', None),
        )

    def cascade_field(
        self,
        entity: AsanaResource,
        field_name: str,
        *,
        target_types: set[type] | None = None,
    ) -> SaveSession:
        """Queue cascade of field value to descendants.

        The cascade executes during commit_async() after CRUD operations,
        ensuring the source entity exists with a real GID.

        IMPORTANT: Cascade scope is relative to the source entity.
        - cascade_field(unit, "platforms") only affects that unit's offers
        - cascade_field(business, "office_phone") affects all business descendants

        The allow_override behavior is determined by the field's CascadingFieldDef:
        - allow_override=False (DEFAULT): Always overwrite descendant value
        - allow_override=True: Only overwrite if descendant value is None

        Args:
            entity: Source entity (Business, Unit, etc.)
            field_name: Custom field to cascade (e.g., "Office Phone", "Platforms")
            target_types: Optional filter of target entity types. If None,
                         uses the field's declared target_types from CascadingFields.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.
            ValueError: If entity has temp GID or field is not cascading.

        Example - Business field (no override):
            business.office_phone = "555-9999"
            session.cascade_field(business, "Office Phone")
            await session.commit_async()
            # All descendants get "555-9999" regardless of their current value

        Example - Unit field (with override opt-in):
            unit.platforms = ["Google", "Meta"]
            session.cascade_field(unit, "Platforms")
            await session.commit_async()
            # Only offers with null platforms get updated
        """
        self._ensure_open()

        # Validate entity has real GID
        if not entity.gid or entity.gid.startswith("temp_"):
            raise ValueError(
                f"Cannot cascade from entity without real GID: {entity.gid}"
            )

        # Get field definition to determine override behavior
        field_def = self._get_cascade_field_def(entity, field_name)

        # Get target_types from field definition if not provided
        if target_types is None and field_def:
            target_types = field_def.target_types

        # Determine allow_override from field definition (default False)
        allow_override = field_def.allow_override if field_def else False

        # Get current value
        new_value = entity.get_custom_fields().get(field_name)

        cascade = CascadeOperation(
            source=entity,
            field_name=field_name,
            field_gid=None,  # Resolved during execution
            new_value=new_value,
            target_types=target_types,
            allow_override=allow_override,
        )
        self._pending_cascades.append(cascade)

        if self._log:
            self._log.debug(
                "session_cascade_field",
                source_gid=entity.gid,
                field_name=field_name,
                target_types=str(target_types),
                allow_override=allow_override,
            )

        return self

    def _get_cascade_field_def(
        self,
        entity: AsanaResource,
        field_name: str,
    ) -> CascadingFieldDef | None:
        """Lookup field definition from entity's CascadingFields class."""
        if hasattr(entity, 'CascadingFields'):
            return entity.CascadingFields.get(field_name)
        return None

    async def commit_async(self) -> SaveResult:
        """Execute all pending changes including cascades.

        Execution order:
        1. CRUD operations (create/update/delete)
        2. Cascade operations (propagate field values)
        3. Action operations (add_tag, etc.)
        """
        self._ensure_open()

        dirty_entities = self._tracker.get_dirty_entities()
        pending_cascades = list(self._pending_cascades)
        pending_actions = list(self._pending_actions)

        if not dirty_entities and not pending_cascades and not pending_actions:
            return SaveResult()

        # Phase 1: Execute CRUD operations
        crud_result = await self._pipeline.execute(dirty_entities)

        # Phase 2: Execute cascades (after CRUD so entities have real GIDs)
        cascade_results: list[Any] = []
        if pending_cascades:
            cascade_results = await self._cascade_executor.execute(
                pending_cascades,
                descendants_cache=self._build_descendants_cache(),
            )
            self._pending_cascades.clear()

        # Phase 3: Execute actions
        action_results = []
        if pending_actions:
            action_results = await self._action_executor.execute(pending_actions)
            self._pending_actions.clear()

        # Mark entities clean
        for entity in crud_result.succeeded:
            self._tracker.mark_clean(entity)

        self._state = SessionState.COMMITTED

        # Include cascade failures in result
        return self._merge_results(crud_result, cascade_results, action_results)

    def _build_descendants_cache(self) -> dict[str, list[AsanaResource]]:
        """Build cache of descendants from tracked entities.

        Optimization: If recursive=True was used during track(),
        we already have the descendants in memory.
        """
        cache: dict[str, list[AsanaResource]] = {}

        for entity in self._tracker._entities.values():
            if hasattr(entity, '_children'):
                cache[entity.gid] = self._collect_descendants(entity)

        return cache

    def _collect_descendants(
        self,
        entity: AsanaResource,
    ) -> list[AsanaResource]:
        """Recursively collect all descendants of an entity."""
        descendants: list[AsanaResource] = []

        children = getattr(entity, '_children', [])
        for child in children:
            descendants.append(child)
            descendants.extend(self._collect_descendants(child))

        return descendants
```

## Pattern 2: Inherited Fields

### Unit Model with Inherited Fields

```python
# src/autom8_asana/models/business/unit.py

from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from autom8_asana.models.task import Task
from autom8_asana.models.business.fields import InheritedFieldDef

if TYPE_CHECKING:
    from autom8_asana.models.business.business import Business


class Unit(Task):
    """Unit entity within a Business.

    Units contain OfferHolder and ProcessHolder. The Unit's vertical
    is inherited by its children (Offer, Process) unless overridden.
    """

    # Cached parent reference
    _business: Business | None = PrivateAttr(default=None)

    # --- Inherited Field Declarations ---

    class InheritedFields:
        """Fields inherited from parent entities."""

        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Business"],  # Unit inherits from Business
            allow_override=True,
            default="General",
        )

        @classmethod
        def all(cls) -> list[InheritedFieldDef]:
            return [cls.VERTICAL]

    # --- Property Implementation ---

    @property
    def vertical(self) -> str | None:
        """Get vertical, inheriting from Business if not set locally.

        Resolution order:
        1. Local value (if set)
        2. Business.default_vertical
        3. InheritedFieldDef.default
        """
        # Check for local value
        local_value = self.get_custom_fields().get("Vertical")
        if local_value is not None:
            return local_value

        # Inherit from Business
        if self._business:
            business_default = self._business.get_custom_fields().get("Default Vertical")
            if business_default is not None:
                return business_default

        # Use field default
        return self.InheritedFields.VERTICAL.default

    @vertical.setter
    def vertical(self, value: str | None) -> None:
        """Set vertical locally."""
        self.get_custom_fields().set("Vertical", value)

    @property
    def business(self) -> Business | None:
        """Navigate to parent Business (cached)."""
        if self._business is None:
            self._business = self._resolve_business()
        return self._business

    def _resolve_business(self) -> Business | None:
        """Walk up tree to find Business."""
        from autom8_asana.models.business.business import Business

        current = getattr(self, 'parent', None)
        while current is not None:
            if isinstance(current, Business):
                return current
            current = getattr(current, 'parent', None)
        return None
```

### Offer Model with Override Pattern

```python
# src/autom8_asana/models/business/offer.py

from __future__ import annotations
from typing import TYPE_CHECKING

from pydantic import PrivateAttr

from autom8_asana.models.task import Task
from autom8_asana.models.business.fields import InheritedFieldDef

if TYPE_CHECKING:
    from autom8_asana.models.business.unit import Unit


class Offer(Task):
    """Offer entity within a Unit.

    Offers inherit vertical and manager from their parent Unit,
    but can optionally override these values locally.
    """

    # Cached parent reference
    _unit: Unit | None = PrivateAttr(default=None)

    # --- Inherited Field Declarations ---

    class InheritedFields:
        """Fields inherited from parent Unit."""

        VERTICAL = InheritedFieldDef(
            name="Vertical",
            inherit_from=["Unit", "Business"],  # Resolution order
            allow_override=True,
        )

        MANAGER = InheritedFieldDef(
            name="Manager",
            inherit_from=["Unit"],
            allow_override=False,  # Always use Unit's manager
        )

    # --- Vertical Property with Override ---

    @property
    def vertical(self) -> str | None:
        """Get vertical, inheriting from Unit if not overridden.

        If Vertical Override is set to "Yes", uses local value.
        Otherwise, inherits from parent Unit.
        """
        if self._is_field_overridden("Vertical"):
            return self.get_custom_fields().get("Vertical")

        # Inherit from Unit
        if self._unit:
            return self._unit.vertical

        # No parent, return local value or None
        return self.get_custom_fields().get("Vertical")

    @vertical.setter
    def vertical(self, value: str | None) -> None:
        """Set vertical locally, marking as overridden."""
        self.get_custom_fields().set("Vertical", value)
        self.get_custom_fields().set("Vertical Override", "Yes")

    def inherit_vertical(self) -> None:
        """Clear local override, inherit from parent Unit.

        Removes the local value and override flag, causing
        subsequent reads to resolve from parent.
        """
        self.get_custom_fields().remove("Vertical")
        self.get_custom_fields().remove("Vertical Override")

    # --- Manager Property (No Override) ---

    @property
    def manager(self) -> str | None:
        """Get manager (always inherited from Unit, no override)."""
        if self._unit:
            return self._unit.get_custom_fields().get("Manager")
        return None

    # manager has no setter - always inherited

    # --- Helper Methods ---

    def _is_field_overridden(self, field_name: str) -> bool:
        """Check if field is locally overridden.

        Args:
            field_name: Name of the inherited field

        Returns:
            True if local override is set
        """
        override_field = f"{field_name} Override"
        override_value = self.get_custom_fields().get(override_field)
        return override_value in ("Yes", "yes", True, "true", "1")

    @property
    def unit(self) -> Unit | None:
        """Navigate to parent Unit (cached)."""
        if self._unit is None:
            self._unit = self._resolve_unit()
        return self._unit

    def _resolve_unit(self) -> Unit | None:
        """Walk up tree to find Unit."""
        from autom8_asana.models.business.unit import Unit

        current = getattr(self, 'parent', None)
        while current is not None:
            if isinstance(current, Unit):
                return current
            current = getattr(current, 'parent', None)
        return None
```

## Reconciliation

```python
# src/autom8_asana/persistence/reconciler.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.session import SaveSession


@dataclass
class DriftReport:
    """Report of a cascading field value mismatch."""

    entity: AsanaResource  # Entity with stale value
    field_name: str        # Custom field name
    expected: Any          # Value from source
    actual: Any            # Current value on entity


class CascadeReconciler:
    """Detect and repair cascading field drift.

    Over time, descendant entities may have stale cascaded values if:
    - cascade_field() was forgotten after a change
    - Batch update partially failed
    - Manual edit in Asana UI

    This class provides detection and repair capabilities.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def check_consistency(
        self,
        source: AsanaResource,
        field_name: str,
        *,
        targets: list[str] | None = None,
    ) -> list[DriftReport]:
        """Check if descendants have consistent cascade values.

        Args:
            source: Root entity (e.g., Business)
            field_name: Cascading field to check
            targets: Optional entity type filter

        Returns:
            List of DriftReport for entities with mismatched values
        """
        expected = source.get_custom_fields().get(field_name)
        descendants = await self._get_descendants(source, targets)

        drifts: list[DriftReport] = []
        for descendant in descendants:
            actual = descendant.get_custom_fields().get(field_name)
            if actual != expected:
                drifts.append(DriftReport(
                    entity=descendant,
                    field_name=field_name,
                    expected=expected,
                    actual=actual,
                ))

        return drifts

    async def repair(
        self,
        session: SaveSession,
        drifts: list[DriftReport],
    ) -> None:
        """Repair detected drift by updating stale entities.

        Args:
            session: Active SaveSession to track repairs
            drifts: List of DriftReport from check_consistency()

        Example:
            drifts = await reconciler.check_consistency(business, "Office Phone")
            if drifts:
                await reconciler.repair(session, drifts)
                await session.commit_async()
        """
        for drift in drifts:
            drift.entity.get_custom_fields().set(
                drift.field_name,
                drift.expected,
            )
            session.track(drift.entity)

    async def full_reconciliation(
        self,
        source: AsanaResource,
        session: SaveSession,
    ) -> dict[str, list[DriftReport]]:
        """Check and repair all cascading fields for an entity.

        Args:
            source: Root entity with CascadingFields declarations
            session: Active SaveSession for repairs

        Returns:
            Dict of field_name -> list of DriftReport (for logging)
        """
        if not hasattr(source, 'CascadingFields'):
            return {}

        all_drifts: dict[str, list[DriftReport]] = {}

        for field_def in source.CascadingFields.all():
            drifts = await self.check_consistency(
                source,
                field_def.name,
                targets=field_def.targets,
            )
            if drifts:
                all_drifts[field_def.name] = drifts
                await self.repair(session, drifts)

        return all_drifts

    async def _get_descendants(
        self,
        source: AsanaResource,
        targets: list[str] | None,
    ) -> list[AsanaResource]:
        """Fetch descendants from API."""
        # Implementation would fetch subtasks recursively
        # Similar to CascadeExecutor._fetch_descendants
        raise NotImplementedError("Requires TasksClient integration")
```

## Usage Examples

### Business Cascade (No Override - Default)

```python
async with client.save_session() as session:
    # Load and track business with all descendants
    business = await client.tasks.get_async(business_gid)
    session.track(business, recursive=True)

    # Modify cascading field
    business.office_phone = "555-9999"

    # Explicitly cascade to descendants
    # allow_override=False is DEFAULT - all descendants get updated
    session.cascade_field(business, "Office Phone")

    # Commit (saves business, then cascades to 50+ descendants)
    result = await session.commit_async()

    print(f"Updated {len(result.succeeded)} entities")
    # ALL descendants now have "555-9999" regardless of previous value
```

### Unit-Level Cascade with Override (Explicit Opt-In)

```python
async with client.save_session() as session:
    # Load unit with its offers
    unit = await client.tasks.get_async(unit_gid)
    session.track(unit, recursive=True)

    # Set unit's platforms
    unit.platforms = ["Google", "Meta"]

    # Cascade to offers (allow_override=True for this field)
    session.cascade_field(unit, "Platforms")

    await session.commit_async()

    # Results:
    # - Offers with platforms=None: Updated to ["Google", "Meta"]
    # - Offers with existing platforms: KEPT their original value
```

### Multiple Cascades (Same Source)

```python
async with client.save_session() as session:
    session.track(business, recursive=True)

    # Multiple field changes
    business.office_phone = "555-9999"  # No override (default)
    business.company_id = "NEW-123"      # No override (default)

    # Cascade both fields
    session.cascade_field(business, "Office Phone")
    session.cascade_field(business, "Company ID")

    await session.commit_async()
```

### Multi-Level Cascade (Different Sources)

```python
async with client.save_session() as session:
    # Track entire hierarchy
    session.track(business, recursive=True)

    # Business-level cascade (no override)
    business.office_phone = "555-9999"
    session.cascade_field(business, "Office Phone")  # -> Unit, Offer, Process

    # Unit-level cascade (with override for platforms)
    for unit in business.units:
        unit.platforms = ["Google"]
        session.cascade_field(unit, "Platforms")  # -> Offers only

    await session.commit_async()
    # Business cascade: ALL descendants get office_phone
    # Unit cascades: Only offers with null platforms get updated
```

### Scope-Limited Cascade

```python
async with client.save_session() as session:
    # Load two different units
    unit_retail = await client.tasks.get_async(unit_retail_gid)
    unit_industrial = await client.tasks.get_async(unit_industrial_gid)

    session.track(unit_retail, recursive=True)
    session.track(unit_industrial, recursive=True)

    # Change platforms on retail unit only
    unit_retail.platforms = ["Google Shopping", "Amazon"]
    session.cascade_field(unit_retail, "Platforms")

    await session.commit_async()

    # Result:
    # - unit_retail's offers: Updated (respecting allow_override)
    # - unit_industrial's offers: UNCHANGED (not in scope)
```

### Filtered Cascade (Override Target Types)

```python
async with client.save_session() as session:
    session.track(business, recursive=True)
    business.office_phone = "555-9999"

    # Only cascade to Units and Offers (not Processes)
    # Even though field definition includes Process
    session.cascade_field(
        business,
        "Office Phone",
        target_types={Unit, Offer},  # Explicit filter
    )

    await session.commit_async()
```

### Inherited Field with Override (Read-Time Pattern)

```python
async with client.save_session() as session:
    # Load unit with its offers
    unit = await client.tasks.get_async(unit_gid)
    session.track(unit, recursive=True)

    # Set unit's vertical (will cascade with no override)
    unit.vertical = "Retail"
    session.cascade_field(unit, "Vertical")

    # Inherited field pattern: offer.vertical reads from parent
    other_offer = unit.offers[1]
    assert other_offer.vertical == "Retail"  # Inherits from unit

    await session.commit_async()
```

### Clear Override (Return to Parent Value)

```python
async with client.save_session() as session:
    session.track(offer)

    # Clear local value, will receive parent's value on next cascade
    offer.get_custom_fields().set("Platforms", None)

    await session.commit_async()

    # Next cascade from Unit will populate this Offer's platforms
```

### Reconciliation

```python
# One-time reconciliation check
reconciler = CascadeReconciler(client)

async with client.save_session() as session:
    # Check for drift
    drifts = await reconciler.check_consistency(
        business,
        "Office Phone",
    )

    if drifts:
        print(f"Found {len(drifts)} entities with stale Office Phone")
        await reconciler.repair(session, drifts)
        await session.commit_async()
```

### Full Reconciliation

```python
# Check all cascading fields
reconciler = CascadeReconciler(client)

async with client.save_session() as session:
    all_drifts = await reconciler.full_reconciliation(business, session)

    for field_name, drifts in all_drifts.items():
        print(f"{field_name}: {len(drifts)} entities repaired")

    if all_drifts:
        await session.commit_async()
```

## Testing Patterns

### Unit Test: Cascading Field Definition

```python
def test_cascading_field_applies_to_target():
    field = CascadingFieldDef(
        name="Office Phone",
        targets=["Unit", "Offer"],
    )

    assert field.applies_to("Unit") is True
    assert field.applies_to("Offer") is True
    assert field.applies_to("Process") is False
    assert field.applies_to("Contact") is False


def test_cascading_field_wildcard():
    field = CascadingFieldDef(
        name="Company ID",
        targets=["*"],
    )

    assert field.applies_to("Unit") is True
    assert field.applies_to("Anything") is True
```

### Unit Test: Inherited Field Resolution

```python
def test_offer_inherits_vertical_from_unit(unit: Unit, offer: Offer):
    unit.vertical = "Retail"
    offer._unit = unit

    # Offer inherits from unit
    assert offer.vertical == "Retail"


def test_offer_override_vertical(unit: Unit, offer: Offer):
    unit.vertical = "Retail"
    offer._unit = unit

    # Override locally
    offer.vertical = "Industrial"

    assert offer.vertical == "Industrial"
    assert offer._is_field_overridden("Vertical") is True


def test_offer_inherit_clears_override(unit: Unit, offer: Offer):
    unit.vertical = "Retail"
    offer._unit = unit
    offer.vertical = "Industrial"  # Override

    # Clear override
    offer.inherit_vertical()

    assert offer.vertical == "Retail"  # Back to inherited
    assert offer._is_field_overridden("Vertical") is False
```

### Integration Test: Cascade Execution

```python
@pytest.mark.integration
async def test_cascade_updates_descendants(
    client: AsanaClient,
    business_with_units: Business,
):
    async with client.save_session() as session:
        session.track(business_with_units, recursive=True)

        # Change cascading field
        business_with_units.office_phone = "555-NEW"
        session.cascade_field(business_with_units, "Office Phone")

        result = await session.commit_async()

    # Verify all units updated
    for unit in business_with_units.units:
        refreshed = await client.tasks.get_async(unit.gid)
        assert refreshed.get_custom_fields().get("Office Phone") == "555-NEW"
```

## Error Handling

### Rate Limit During Cascade

```python
async with client.save_session() as session:
    try:
        session.cascade_field(business, "Office Phone")
        result = await session.commit_async()

        # Check for partial failures
        if result.partial:
            failed_gids = [err.entity.gid for err in result.failed]
            print(f"Cascade partial failure: {len(failed_gids)} entities")
            # Could retry failed entities

    except RateLimitError as e:
        # Exponential backoff handled internally
        # This only raises if retries exhausted
        print(f"Rate limit exceeded after retries: {e}")
```

### Entity Without Real GID

```python
async with client.save_session() as session:
    # New entity with temp GID
    new_business = Business(gid="temp_1", name="New Business")
    session.track(new_business)

    # This will raise ValueError - can't cascade from temp GID
    try:
        session.cascade_field(new_business, "Office Phone")
    except ValueError as e:
        print(f"Expected error: {e}")

    # Solution: cascade after entity is created
    result = await session.commit_async()

    # Now entity has real GID
    assert not new_business.gid.startswith("temp_")

    # Can cascade in next session
```

## Performance Considerations

1. **Batch Size**: Cascades use BatchClient which chunks to 10 requests. A cascade to 100 entities = 10 batch API calls.

2. **Descendants Cache**: If `track(business, recursive=True)` was used, descendants are already in memory and reused for cascade.

3. **Parallel Cascades**: Multiple `cascade_field()` calls are collected and executed in a single batch pass during commit.

4. **Rate Limits**: BatchClient handles rate limits with exponential backoff per ADR-0010.

5. **Large Hierarchies**: For >500 descendants, consider:
   - Streaming descendants instead of loading all in memory
   - Progress callbacks for UI feedback
   - Configurable timeout
