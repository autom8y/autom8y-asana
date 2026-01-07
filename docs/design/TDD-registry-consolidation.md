---
artifact_id: TDD-registry-consolidation
title: "Technical Design Document: Entity Registry Consolidation"
created_at: "2026-01-07T10:00:00Z"
author: architect
status: draft
complexity: SYSTEM
prd_ref: null
components:
  - name: ProjectRegistry
    type: module
    description: "Unified registry for entity type to project GID mappings"
    dependencies:
      - name: EntityType
        type: internal
      - name: BusinessEntity models
        type: internal
  - name: RegistryBootstrap
    type: module
    description: "Explicit registration mechanism replacing __init_subclass__ auto-registration"
    dependencies:
      - name: ProjectRegistry
        type: internal
  - name: EntityProjectRegistryShim
    type: module
    description: "Deprecation shim for backward compatibility during migration"
    dependencies:
      - name: ProjectRegistry
        type: internal
related_adrs:
  - ADR-registry-consolidation
  - ADR-0031
  - ADR-0060
schema_version: "1.0"
---

# TDD: Entity Registry Consolidation

## Overview

This TDD addresses the architectural issue of duplicate registries (`ProjectTypeRegistry` and `EntityProjectRegistry`) causing detection failures during cache warming. The document specifies a consolidation strategy that establishes a single source of truth for entity-to-project mappings.

## Executive Summary

**Problem**: Two separate registries maintain `entity_type <-> project_gid` mappings with different population mechanisms, leading to synchronization failures and detection breakdowns.

**Root Cause**: `ProjectTypeRegistry` relies on implicit `__init_subclass__` auto-registration (import-time), while `EntityProjectRegistry` uses explicit startup discovery (runtime). During cache warming, detection may query `ProjectTypeRegistry` before entity classes are imported.

**Solution**:
1. Consolidate to a single `ProjectRegistry` with explicit model-first registration
2. Replace `__init_subclass__` auto-registration with deterministic bootstrap
3. Deprecate and remove `EntityProjectRegistry`
4. Ensure registry is fully populated before any detection calls

## Problem Statement

### Current State: Two Registries

| Registry | Location | Population Mechanism | Consumers |
|----------|----------|---------------------|-----------|
| `ProjectTypeRegistry` | `models/business/registry.py` | `__init_subclass__` auto-registration when classes are imported | Detection system (Tier 1) |
| `EntityProjectRegistry` | `services/resolver.py` | `_discover_entity_projects()` during API startup | Entity Resolver API |

### Observed Failure

Tasks in known projects (e.g., "Businesses" project GID `1200653012566782`) fail Tier 1 detection:

```
Unable to detect type for task 1210979806530397 (Tier 5 fallback)
```

The task is in the "Businesses" project, but `ProjectTypeRegistry.lookup("1200653012566782")` returns `None` because the `Business` class was not yet imported when detection ran during cache warming.

### Design Principle Violations

| Principle | Violation |
|-----------|-----------|
| **DRY** | Same entity-project mappings maintained in two places |
| **Single Source of Truth** | Both registries claim authority; they can disagree |
| **Explicit over Implicit** | `__init_subclass__` auto-registration is "magic" dependent on import order |
| **Fail-Fast** | Detection fails silently when registry empty; no clear error at startup |

## Goals

1. **G-001**: Single registry for all entity-to-project mappings
2. **G-002**: Deterministic, import-order-independent registration
3. **G-003**: Detection works correctly during cache warming
4. **G-004**: Entity Resolver API continues to function
5. **G-005**: Backward compatibility during migration period
6. **G-006**: Clear initialization contract: registry populated before any lookups

## Non-Goals

1. Runtime API discovery as primary registration mechanism (model is authoritative)
2. Multi-workspace support (single workspace per deployment)
3. Dynamic registry updates after initialization
4. Breaking changes to detection or resolver public APIs

## Design Overview

### Architecture Decision

**Consolidate to unified `ProjectRegistry` with explicit model-first registration.**

```
BEFORE (Two Registries):
+----------------------+          +------------------------+
|  ProjectTypeRegistry |          |  EntityProjectRegistry |
|----------------------|          |------------------------|
| gid -> EntityType    |          | entity_type -> config  |
| Populated: import    |          | Populated: startup     |
| Consumer: Detection  |          | Consumer: Resolver API |
+----------------------+          +------------------------+
         |                                  |
         |    (Can be out of sync)         |
         v                                  v
   Detection: Tier 5 fallback         Resolver: Works

AFTER (Unified Registry):
+--------------------------------------------------+
|               ProjectRegistry (Unified)           |
|--------------------------------------------------|
| gid -> EntityType                                 |
| EntityType -> gid (primary)                       |
| EntityType -> ProjectConfig (rich metadata)       |
|--------------------------------------------------|
| Population: Explicit bootstrap (model-first)      |
| Supplement: Discovery for pipeline projects       |
| Consumers: Detection, Resolver, Cache Warming     |
+--------------------------------------------------+
         |
         v
   Single Source of Truth
```

### Registration Flow

```
                     Application Startup
                            |
                            v
              +---------------------------+
              |  register_all_models()    |  Phase 1: Model-First
              |  Called from __init__.py  |  (No API calls)
              |  - Imports all entities   |
              |  - Reads PRIMARY_PROJECT_ |
              |    GID from each class    |
              |  - Registers mappings     |
              +---------------------------+
                            |
                            v
              +---------------------------+
              |  Discovery Supplement     |  Phase 2: Runtime
              |  (API startup lifespan)   |  (Optional API calls)
              |  - Discover workspace     |
              |    projects               |
              |  - Register pipelines     |
              |    (Sales, Onboarding)    |
              |  - Do NOT overwrite       |
              |    model registrations    |
              +---------------------------+
                            |
                            v
              +---------------------------+
              |  Registry Ready           |  Phase 3: Operational
              |  - All lookups work       |
              |  - Detection uses Tier 1  |
              |  - Resolver API responds  |
              +---------------------------+
```

## Detailed Design

### Component 1: Unified ProjectRegistry

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/registry.py`

Extend existing `ProjectTypeRegistry` with additional capabilities:

```python
from dataclasses import dataclass
from typing import ClassVar

@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Configuration for an entity type's project mapping.

    Consolidates metadata from both legacy registries.
    """
    entity_type: EntityType
    project_gid: str
    project_name: str | None = None  # From discovery (optional)
    schema_task_type: str | None = None  # For SchemaRegistry key

    def __post_init__(self) -> None:
        # Default schema_task_type from entity_type
        if self.schema_task_type is None:
            object.__setattr__(
                self,
                'schema_task_type',
                self.entity_type.value.replace('_', ' ').title().replace(' ', '')
            )


class ProjectRegistry:
    """Unified registry for entity type to project GID mappings.

    Per TDD-registry-consolidation: Single source of truth.
    Per ADR-registry-consolidation: Model-first with discovery supplement.

    This registry provides:
    - O(1) lookup: project_gid -> EntityType (for detection)
    - O(1) lookup: EntityType -> project_gid (for resolver)
    - O(1) lookup: EntityType -> ProjectConfig (for rich metadata)

    Initialization:
    1. Call register_all_models() at module import time
    2. Optionally call supplement_from_discovery() at API startup

    Usage:
        registry = get_project_registry()

        # Detection (Tier 1)
        entity_type = registry.lookup(project_gid)

        # Resolver API
        gid = registry.get_primary_gid(EntityType.BUSINESS)
        config = registry.get_config(EntityType.BUSINESS)

    Testing:
        ProjectRegistry.reset()
    """

    _instance: ClassVar[ProjectRegistry | None] = None

    # Instance attributes
    _gid_to_type: dict[str, EntityType]
    _type_to_gid: dict[EntityType, str]
    _type_to_config: dict[EntityType, ProjectConfig]
    _initialized: bool
    _discovery_complete: bool

    def __new__(cls) -> ProjectRegistry:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._gid_to_type = {}
            instance._type_to_gid = {}
            instance._type_to_config = {}
            instance._initialized = False
            instance._discovery_complete = False
            cls._instance = instance
        return cls._instance

    def register(
        self,
        project_gid: str,
        entity_type: EntityType,
        *,
        project_name: str | None = None,
        schema_task_type: str | None = None,
        source: str = "model",
    ) -> None:
        """Register a project GID to EntityType mapping.

        Args:
            project_gid: Asana project GID.
            entity_type: EntityType for this project.
            project_name: Human-readable name (from discovery).
            schema_task_type: SchemaRegistry key override.
            source: Registration source ("model" or "discovery").

        Raises:
            ValueError: If project_gid already registered to different type.
        """
        if project_gid in self._gid_to_type:
            existing = self._gid_to_type[project_gid]
            if existing != entity_type:
                raise ValueError(
                    f"Project GID {project_gid} already registered to "
                    f"{existing.name}, cannot register to {entity_type.name}"
                )
            # Idempotent: same mapping exists
            return

        # Create config
        config = ProjectConfig(
            entity_type=entity_type,
            project_gid=project_gid,
            project_name=project_name,
            schema_task_type=schema_task_type,
        )

        self._gid_to_type[project_gid] = entity_type
        self._type_to_config[entity_type] = config

        # Primary GID: first registration wins
        if entity_type not in self._type_to_gid:
            self._type_to_gid[entity_type] = project_gid

        self._initialized = True

        logger.debug(
            "project_registered",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type.name,
                "source": source,
            },
        )

    def lookup(self, project_gid: str) -> EntityType | None:
        """Look up EntityType by project GID. O(1).

        Per FR-DET-002: Detection API unchanged.
        """
        return self._gid_to_type.get(project_gid)

    def get_primary_gid(self, entity_type: EntityType) -> str | None:
        """Get primary project GID for an EntityType. O(1).

        Per Resolver API: entity_type -> project_gid.
        """
        return self._type_to_gid.get(entity_type)

    def get_config(self, entity_type: EntityType) -> ProjectConfig | None:
        """Get full configuration for an EntityType. O(1).

        Returns ProjectConfig with project_gid, project_name, schema_task_type.
        """
        return self._type_to_config.get(entity_type)

    def get_project_gid(self, entity_type_str: str) -> str | None:
        """Get project GID by entity type string. O(1).

        Backward compatibility for EntityProjectRegistry.get_project_gid().

        Args:
            entity_type_str: Entity type as string (e.g., "business").

        Returns:
            Project GID if registered, None otherwise.
        """
        try:
            entity_type = EntityType(entity_type_str)
            return self.get_primary_gid(entity_type)
        except ValueError:
            return None

    def get_all_entity_types(self) -> list[str]:
        """Get all registered entity type strings.

        Backward compatibility for EntityProjectRegistry.get_all_entity_types().
        """
        return [et.value for et in self._type_to_config.keys()]

    def is_ready(self) -> bool:
        """True if registry has been initialized with at least one mapping."""
        return self._initialized and len(self._gid_to_type) > 0

    def is_discovery_complete(self) -> bool:
        """True if discovery supplement has been run."""
        return self._discovery_complete

    def mark_discovery_complete(self) -> None:
        """Mark discovery phase as complete."""
        self._discovery_complete = True

    def get_all_mappings(self) -> dict[str, EntityType]:
        """Get copy of all GID-to-type mappings."""
        return dict(self._gid_to_type)

    @classmethod
    def reset(cls) -> None:
        """Reset for testing."""
        cls._instance = None
        logger.debug("ProjectRegistry reset")


def get_project_registry() -> ProjectRegistry:
    """Get the unified ProjectRegistry singleton."""
    return ProjectRegistry()


# Backward compatibility alias
def get_registry() -> ProjectRegistry:
    """Alias for get_project_registry().

    Maintains backward compatibility with existing code.
    """
    return get_project_registry()
```

### Component 2: Explicit Registration Bootstrap

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/_bootstrap.py`

New module for explicit, deterministic registration:

```python
"""Explicit model registration for ProjectRegistry.

Per TDD-registry-consolidation: Replaces __init_subclass__ auto-registration
with deterministic bootstrap that runs at module import time.

This module is imported by models/business/__init__.py to ensure
registration happens before any detection calls.

IMPORTANT: This is the ONLY place where entity types should be registered.
Do NOT add registration logic to __init_subclass__ or other hooks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.business.detection.types import EntityType

logger = logging.getLogger(__name__)

_BOOTSTRAP_COMPLETE = False


def register_all_models() -> None:
    """Register all entity types from model PRIMARY_PROJECT_GID attributes.

    Per TDD-registry-consolidation Phase 1: Model-first registration.

    This function:
    1. Imports all entity model classes
    2. Reads PRIMARY_PROJECT_GID from each class
    3. Registers non-None GIDs with ProjectRegistry
    4. Logs registration summary

    Called once at module import time from models/business/__init__.py.
    Idempotent: subsequent calls are no-ops.
    """
    global _BOOTSTRAP_COMPLETE

    if _BOOTSTRAP_COMPLETE:
        logger.debug("register_all_models already complete, skipping")
        return

    from autom8_asana.models.business.detection.types import EntityType
    from autom8_asana.models.business.registry import get_project_registry

    # Import all entity model classes
    # Imports are inside function to avoid circular imports
    from autom8_asana.models.business.business import (
        Business,
        DNAHolder,
        ReconciliationHolder,
        AssetEditHolder,
        VideographyHolder,
    )
    from autom8_asana.models.business.unit import Unit, UnitHolder
    from autom8_asana.models.business.contact import Contact, ContactHolder
    from autom8_asana.models.business.offer import Offer, OfferHolder
    from autom8_asana.models.business.location import Location, LocationHolder
    from autom8_asana.models.business.hours import Hours
    from autom8_asana.models.business.process import Process, ProcessHolder
    from autom8_asana.models.business.asset_edit import AssetEdit

    # Entity type -> Model class mapping
    # Order matters: more specific types first (holders before parents)
    ENTITY_MODELS: list[tuple[EntityType, type]] = [
        # Root entities
        (EntityType.BUSINESS, Business),
        (EntityType.UNIT, Unit),
        (EntityType.CONTACT, Contact),
        (EntityType.OFFER, Offer),
        (EntityType.LOCATION, Location),
        (EntityType.HOURS, Hours),
        (EntityType.PROCESS, Process),

        # Holders
        (EntityType.CONTACT_HOLDER, ContactHolder),
        (EntityType.UNIT_HOLDER, UnitHolder),
        (EntityType.OFFER_HOLDER, OfferHolder),
        (EntityType.LOCATION_HOLDER, LocationHolder),
        (EntityType.PROCESS_HOLDER, ProcessHolder),
        (EntityType.DNA_HOLDER, DNAHolder),
        (EntityType.RECONCILIATIONS_HOLDER, ReconciliationHolder),
        (EntityType.ASSET_EDIT_HOLDER, AssetEditHolder),
        (EntityType.VIDEOGRAPHY_HOLDER, VideographyHolder),
    ]

    registry = get_project_registry()
    registered_count = 0
    skipped_count = 0

    for entity_type, model_class in ENTITY_MODELS:
        gid = getattr(model_class, 'PRIMARY_PROJECT_GID', None)

        if gid is None:
            logger.debug(
                "model_no_primary_gid",
                extra={
                    "entity_type": entity_type.name,
                    "model_class": model_class.__name__,
                },
            )
            skipped_count += 1
            continue

        try:
            registry.register(
                project_gid=gid,
                entity_type=entity_type,
                source="model",
            )
            registered_count += 1
        except ValueError as e:
            # Duplicate GID - log warning but continue
            logger.warning(
                "model_registration_conflict",
                extra={
                    "entity_type": entity_type.name,
                    "model_class": model_class.__name__,
                    "project_gid": gid,
                    "error": str(e),
                },
            )

    _BOOTSTRAP_COMPLETE = True

    logger.info(
        "model_registration_complete",
        extra={
            "registered_count": registered_count,
            "skipped_count": skipped_count,
            "total_models": len(ENTITY_MODELS),
        },
    )


def is_bootstrap_complete() -> bool:
    """Check if model bootstrap has been run."""
    return _BOOTSTRAP_COMPLETE


def reset_bootstrap() -> None:
    """Reset bootstrap state for testing."""
    global _BOOTSTRAP_COMPLETE
    _BOOTSTRAP_COMPLETE = False
```

### Component 3: Bootstrap Integration

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/__init__.py`

Update to call bootstrap at import time:

```python
"""Business model entities.

Per TDD-registry-consolidation: Bootstrap registration runs at import time.
"""

# Bootstrap registration FIRST - before any other imports that might
# trigger detection. This ensures ProjectRegistry is populated.
from autom8_asana.models.business._bootstrap import register_all_models

register_all_models()

# Then export all entity classes (unchanged)
from autom8_asana.models.business.business import (
    Business,
    DNAHolder,
    ReconciliationHolder,
    AssetEditHolder,
    VideographyHolder,
)
from autom8_asana.models.business.unit import Unit, UnitHolder
from autom8_asana.models.business.contact import Contact, ContactHolder
from autom8_asana.models.business.offer import Offer, OfferHolder
from autom8_asana.models.business.location import Location, LocationHolder
from autom8_asana.models.business.hours import Hours
from autom8_asana.models.business.process import Process, ProcessHolder

__all__ = [
    "Business",
    "Unit",
    "UnitHolder",
    "Contact",
    "ContactHolder",
    "Offer",
    "OfferHolder",
    "Location",
    "LocationHolder",
    "Hours",
    "Process",
    "ProcessHolder",
    "DNAHolder",
    "ReconciliationHolder",
    "AssetEditHolder",
    "VideographyHolder",
]
```

### Component 4: Remove __init_subclass__ Auto-Registration

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/base.py`

Remove registration from `BusinessEntity.__init_subclass__`:

```python
def __init_subclass__(cls, **kwargs: Any) -> None:
    """Auto-discover cached reference attributes and generate Fields class.

    Per TDD-registry-consolidation: Registration REMOVED from __init_subclass__.
    Registration now happens explicitly via register_all_models().

    Per ADR-0076: Base _invalidate_refs() clears discovered refs.
    Per ADR-0082: Generates Fields class from registered custom field descriptors.

    Args:
        **kwargs: Passed to parent __init_subclass__.
    """
    super().__init_subclass__(**kwargs)

    # ... existing ref discovery code (unchanged) ...

    # ... existing Fields class generation code (unchanged) ...

    # REMOVED: Registration with ProjectTypeRegistry
    # Per TDD-registry-consolidation: Registration is now explicit via
    # register_all_models() in _bootstrap.py. Do NOT register here.
    #
    # OLD CODE (removed):
    # from autom8_asana.models.business.registry import _register_entity_with_registry
    # _register_entity_with_registry(cls)
```

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/base.py` (HolderMixin)

Same change for `HolderMixin.__init_subclass__`:

```python
def __init_subclass__(cls, **kwargs: Any) -> None:
    """Initialize holder subclass.

    Per TDD-registry-consolidation: Registration REMOVED.
    Registration now happens explicitly via register_all_models().

    Args:
        **kwargs: Passed to parent __init_subclass__.
    """
    super().__init_subclass__(**kwargs)

    # REMOVED: Registration with ProjectTypeRegistry
    # Per TDD-registry-consolidation: Registration is now explicit.
    #
    # OLD CODE (removed):
    # from autom8_asana.models.business.registry import _register_entity_with_registry
    # _register_entity_with_registry(cls)
```

### Component 5: Discovery Supplement

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py`

Update `_discover_entity_projects()` to use unified registry:

```python
async def _discover_entity_projects(app: FastAPI) -> None:
    """Supplement registry with discovered project metadata.

    Per TDD-registry-consolidation Phase 2: Discovery supplement.

    This function:
    1. Discovers all workspace projects
    2. Adds project_name metadata to existing registrations
    3. Registers pipeline projects (Sales, Onboarding, etc.) as PROCESS
    4. Does NOT overwrite model registrations

    Model registration (Phase 1) has already happened at import time.
    """
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import BotPATError, get_bot_pat
    from autom8_asana.models.business.registry import (
        get_project_registry,
        get_workspace_registry,
    )
    from autom8_asana.models.business.detection.types import EntityType

    registry = get_project_registry()

    # Verify model registration happened
    if not registry.is_ready():
        logger.warning(
            "discovery_before_model_registration",
            extra={
                "detail": "Model registration should happen at import time",
            },
        )

    # Get bot PAT for discovery
    try:
        bot_pat = get_bot_pat()
    except BotPATError as e:
        logger.warning(
            "discovery_no_bot_pat",
            extra={"error": str(e)},
        )
        registry.mark_discovery_complete()
        app.state.project_registry = registry
        return

    workspace_gid = os.environ.get("ASANA_WORKSPACE_GID")
    if not workspace_gid:
        logger.warning(
            "discovery_no_workspace",
            extra={"detail": "ASANA_WORKSPACE_GID not set"},
        )
        registry.mark_discovery_complete()
        app.state.project_registry = registry
        return

    async with AsanaClient(token=bot_pat, workspace_gid=workspace_gid) as client:
        # Run workspace discovery
        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(client)

        # Get discovered projects
        discovered = workspace_registry.get_all_projects()
        gid_to_name = {gid: name for name, gid in discovered.items()}

        # Update existing registrations with project names
        for entity_type in EntityType:
            gid = registry.get_primary_gid(entity_type)
            if gid and gid in gid_to_name:
                # Update config with discovered name
                # (registration is idempotent, will update metadata)
                registry.register(
                    project_gid=gid,
                    entity_type=entity_type,
                    project_name=gid_to_name[gid],
                    source="discovery_update",
                )

        # Pipeline projects are registered by WorkspaceProjectRegistry
        # (Sales, Onboarding, etc. -> EntityType.PROCESS)
        # No additional action needed here

        registry.mark_discovery_complete()

        logger.info(
            "discovery_complete",
            extra={
                "registered_types": registry.get_all_entity_types(),
                "discovered_projects": len(discovered),
            },
        )

    # Store registry in app.state (unified)
    app.state.project_registry = registry

    # Backward compatibility: also set as entity_project_registry
    # DEPRECATED: Will be removed in Phase 3
    app.state.entity_project_registry = registry
```

### Component 6: EntityProjectRegistry Deprecation Shim

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py`

Add deprecation wrapper:

```python
import warnings
from functools import cached_property


class EntityProjectRegistry:
    """DEPRECATED: Use ProjectRegistry from models.business.registry instead.

    Per TDD-registry-consolidation: This class is a shim for backward
    compatibility. All calls are delegated to the unified ProjectRegistry.

    Migration:
        # Old
        from autom8_asana.services.resolver import EntityProjectRegistry
        registry = EntityProjectRegistry.get_instance()
        gid = registry.get_project_gid("business")

        # New
        from autom8_asana.models.business.registry import get_project_registry
        from autom8_asana.models.business.detection.types import EntityType
        registry = get_project_registry()
        gid = registry.get_primary_gid(EntityType.BUSINESS)
    """

    _instance: ClassVar[EntityProjectRegistry | None] = None

    def __new__(cls) -> EntityProjectRegistry:
        warnings.warn(
            "EntityProjectRegistry is deprecated. "
            "Use get_project_registry() from models.business.registry instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @cached_property
    def _delegate(self):
        """Lazy import to avoid circular dependencies."""
        from autom8_asana.models.business.registry import get_project_registry
        return get_project_registry()

    @classmethod
    def get_instance(cls) -> EntityProjectRegistry:
        return cls()

    def register(
        self,
        entity_type: str,
        project_gid: str,
        project_name: str,
        schema_task_type: str | None = None,
    ) -> None:
        """Delegate to unified registry."""
        from autom8_asana.models.business.detection.types import EntityType as ET

        try:
            et = ET(entity_type)
        except ValueError:
            logger.warning(
                "unknown_entity_type_registration",
                extra={"entity_type": entity_type},
            )
            return

        self._delegate.register(
            project_gid=project_gid,
            entity_type=et,
            project_name=project_name,
            schema_task_type=schema_task_type,
            source="legacy_shim",
        )

    def get_project_gid(self, entity_type: str) -> str | None:
        """Delegate to unified registry."""
        return self._delegate.get_project_gid(entity_type)

    def get_config(self, entity_type: str) -> EntityProjectConfig | None:
        """Delegate to unified registry, convert to legacy format."""
        from autom8_asana.models.business.detection.types import EntityType as ET

        try:
            et = ET(entity_type)
        except ValueError:
            return None

        config = self._delegate.get_config(et)
        if config is None:
            return None

        return EntityProjectConfig(
            entity_type=entity_type,
            project_gid=config.project_gid,
            project_name=config.project_name or "",
            schema_task_type=config.schema_task_type,
        )

    def is_ready(self) -> bool:
        """Delegate to unified registry."""
        return self._delegate.is_ready()

    def get_all_entity_types(self) -> list[str]:
        """Delegate to unified registry."""
        return self._delegate.get_all_entity_types()

    @classmethod
    def reset(cls) -> None:
        """Reset for testing."""
        cls._instance = None
        # Also reset unified registry
        from autom8_asana.models.business.registry import ProjectRegistry
        ProjectRegistry.reset()
```

## Implementation Plan

### Phase 1: Explicit Model Registration (Week 1)

**Goal**: Fix immediate detection failures during cache warming.

**Tasks**:

| ID | Task | Effort | Risk |
|----|------|--------|------|
| P1-1 | Create `_bootstrap.py` with `register_all_models()` | 2h | Low |
| P1-2 | Update `models/business/__init__.py` to call bootstrap | 30m | Low |
| P1-3 | Remove `__init_subclass__` registration from `BusinessEntity` | 1h | Medium |
| P1-4 | Remove `__init_subclass__` registration from `HolderMixin` | 30m | Low |
| P1-5 | Update test fixtures to call bootstrap | 2h | Medium |
| P1-6 | Verify detection works during cache warming | 1h | Low |

**Verification**:
- `registry.lookup("1200653012566782")` returns `EntityType.BUSINESS`
- No Tier 5 fallbacks for tasks in known projects during cache warming
- All existing detection tests pass

### Phase 2: Registry Consolidation (Week 2)

**Goal**: Extend `ProjectTypeRegistry` to unified `ProjectRegistry`.

**Tasks**:

| ID | Task | Effort | Risk |
|----|------|--------|------|
| P2-1 | Add `ProjectConfig` dataclass | 30m | Low |
| P2-2 | Add `get_config()`, `get_project_gid()`, `get_all_entity_types()` | 1h | Low |
| P2-3 | Add `is_discovery_complete()`, `mark_discovery_complete()` | 30m | Low |
| P2-4 | Update `_discover_entity_projects()` to use unified registry | 2h | Medium |
| P2-5 | Create `EntityProjectRegistry` deprecation shim | 2h | Medium |
| P2-6 | Update Resolver API routes to use unified registry | 2h | Medium |
| P2-7 | Add deprecation warnings to old imports | 1h | Low |

**Verification**:
- Entity Resolver API returns correct project GIDs
- Deprecation warnings appear in logs for old usage
- All resolver tests pass

### Phase 3: Cleanup (Week 3)

**Goal**: Remove deprecated code and update documentation.

**Tasks**:

| ID | Task | Effort | Risk |
|----|------|--------|------|
| P3-1 | Remove `EntityProjectRegistry` class | 1h | Low |
| P3-2 | Remove `_register_entity_with_registry()` helper | 30m | Low |
| P3-3 | Update all imports to use unified registry | 2h | Medium |
| P3-4 | Update ADR-0031 and ADR-0060 with consolidation notes | 1h | Low |
| P3-5 | Create ADR-registry-consolidation | 1h | Low |
| P3-6 | Update CLAUDE.md and architecture docs | 1h | Low |

**Verification**:
- No references to `EntityProjectRegistry` except in ADRs
- All tests pass without deprecation warnings
- Documentation reflects unified registry

## Testing Strategy

### Unit Tests

**File**: `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/business/test_registry_consolidation.py`

```python
"""Tests for unified ProjectRegistry.

Per TDD-registry-consolidation: Validates consolidation requirements.
"""

import pytest

from autom8_asana.models.business.registry import (
    ProjectRegistry,
    ProjectConfig,
    get_project_registry,
)
from autom8_asana.models.business.detection.types import EntityType


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry before and after each test."""
    ProjectRegistry.reset()
    yield
    ProjectRegistry.reset()


class TestProjectRegistry:
    """Tests for unified ProjectRegistry."""

    def test_register_and_lookup(self):
        """Test basic register/lookup flow."""
        registry = get_project_registry()

        registry.register(
            project_gid="123",
            entity_type=EntityType.BUSINESS,
        )

        assert registry.lookup("123") == EntityType.BUSINESS
        assert registry.get_primary_gid(EntityType.BUSINESS) == "123"

    def test_idempotent_registration(self):
        """Test that same mapping can be registered multiple times."""
        registry = get_project_registry()

        registry.register("123", EntityType.BUSINESS)
        registry.register("123", EntityType.BUSINESS)  # No error

        assert registry.lookup("123") == EntityType.BUSINESS

    def test_conflict_detection(self):
        """Test that conflicting registrations raise ValueError."""
        registry = get_project_registry()

        registry.register("123", EntityType.BUSINESS)

        with pytest.raises(ValueError, match="already registered"):
            registry.register("123", EntityType.UNIT)

    def test_first_registration_wins_for_type_to_gid(self):
        """Test that first GID registered for a type is primary."""
        registry = get_project_registry()

        registry.register("123", EntityType.BUSINESS)
        registry.register("456", EntityType.BUSINESS)  # Same type, different GID

        # First GID is primary
        assert registry.get_primary_gid(EntityType.BUSINESS) == "123"

        # But both GIDs map to BUSINESS
        assert registry.lookup("123") == EntityType.BUSINESS
        assert registry.lookup("456") == EntityType.BUSINESS

    def test_get_config(self):
        """Test ProjectConfig retrieval."""
        registry = get_project_registry()

        registry.register(
            project_gid="123",
            entity_type=EntityType.BUSINESS,
            project_name="Businesses",
            schema_task_type="Business",
        )

        config = registry.get_config(EntityType.BUSINESS)

        assert config is not None
        assert config.project_gid == "123"
        assert config.project_name == "Businesses"
        assert config.schema_task_type == "Business"

    def test_backward_compatible_api(self):
        """Test backward-compatible string-based API."""
        registry = get_project_registry()

        registry.register("123", EntityType.BUSINESS)
        registry.register("456", EntityType.UNIT)

        # String-based lookup (EntityProjectRegistry compatibility)
        assert registry.get_project_gid("business") == "123"
        assert registry.get_project_gid("unit") == "456"
        assert registry.get_project_gid("unknown") is None

        # List all types
        types = registry.get_all_entity_types()
        assert "business" in types
        assert "unit" in types

    def test_is_ready(self):
        """Test readiness check."""
        registry = get_project_registry()

        assert not registry.is_ready()

        registry.register("123", EntityType.BUSINESS)

        assert registry.is_ready()


class TestBootstrap:
    """Tests for model registration bootstrap."""

    def test_register_all_models_populates_registry(self):
        """Test that bootstrap registers all entity models."""
        from autom8_asana.models.business._bootstrap import (
            register_all_models,
            reset_bootstrap,
        )

        reset_bootstrap()
        ProjectRegistry.reset()

        register_all_models()

        registry = get_project_registry()

        # Business should be registered
        assert registry.lookup("1200653012566782") == EntityType.BUSINESS

        # Unit should be registered
        assert registry.lookup("1201081073731555") == EntityType.UNIT

        # Contact should be registered
        assert registry.lookup("1200775689604552") == EntityType.CONTACT

    def test_bootstrap_is_idempotent(self):
        """Test that bootstrap can be called multiple times."""
        from autom8_asana.models.business._bootstrap import (
            register_all_models,
            reset_bootstrap,
        )

        reset_bootstrap()
        ProjectRegistry.reset()

        register_all_models()
        register_all_models()  # No error

        registry = get_project_registry()
        assert registry.is_ready()


class TestDeprecationShim:
    """Tests for EntityProjectRegistry deprecation shim."""

    def test_deprecation_warning(self):
        """Test that using EntityProjectRegistry emits warning."""
        # Import here to avoid warning in other tests
        with pytest.warns(DeprecationWarning, match="deprecated"):
            from autom8_asana.services.resolver import EntityProjectRegistry
            EntityProjectRegistry.get_instance()

    def test_delegation_to_unified_registry(self):
        """Test that shim delegates to unified registry."""
        from autom8_asana.services.resolver import EntityProjectRegistry

        # Pre-populate unified registry
        unified = get_project_registry()
        unified.register("123", EntityType.BUSINESS)

        # Use deprecated API
        with pytest.warns(DeprecationWarning):
            legacy = EntityProjectRegistry.get_instance()

        assert legacy.get_project_gid("business") == "123"
        assert legacy.is_ready()
```

### Integration Tests

**File**: `/Users/tomtenuta/Code/autom8_asana/tests/integration/test_registry_detection.py`

```python
"""Integration tests for registry-based detection.

Per TDD-registry-consolidation: Validates detection works with unified registry.
"""

import pytest


@pytest.fixture(autouse=True)
def reset_all_registries():
    """Reset all registries for clean test state."""
    from autom8_asana.models.business.registry import (
        ProjectRegistry,
        WorkspaceProjectRegistry,
    )
    from autom8_asana.models.business._bootstrap import reset_bootstrap

    ProjectRegistry.reset()
    WorkspaceProjectRegistry.reset()
    reset_bootstrap()

    # Run bootstrap
    from autom8_asana.models.business._bootstrap import register_all_models
    register_all_models()

    yield

    ProjectRegistry.reset()
    WorkspaceProjectRegistry.reset()
    reset_bootstrap()


class TestDetectionWithRegistry:
    """Test detection uses registry correctly."""

    def test_tier1_detection_uses_registry(self):
        """Test Tier 1 detection looks up project in registry."""
        from autom8_asana.models.task import Task
        from autom8_asana.models.business.detection import detect_entity_type
        from autom8_asana.models.business.detection.types import EntityType

        # Task in Businesses project
        task = Task(
            gid="test-123",
            name="Test Business",
            memberships=[{"project": {"gid": "1200653012566782"}}],
        )

        result = detect_entity_type(task)

        assert result.entity_type == EntityType.BUSINESS
        assert result.tier_used == 1  # Tier 1 = registry lookup
        assert result.confidence == 1.0

    def test_detection_before_bootstrap_fails_gracefully(self):
        """Test detection returns UNKNOWN if registry empty."""
        from autom8_asana.models.business.registry import ProjectRegistry
        from autom8_asana.models.business._bootstrap import reset_bootstrap
        from autom8_asana.models.task import Task
        from autom8_asana.models.business.detection import detect_entity_type
        from autom8_asana.models.business.detection.types import EntityType

        # Reset registry to empty state
        ProjectRegistry.reset()
        reset_bootstrap()

        task = Task(
            gid="test-123",
            name="Test Business",
            memberships=[{"project": {"gid": "1200653012566782"}}],
        )

        result = detect_entity_type(task)

        # Should fall through to Tier 5 UNKNOWN
        assert result.entity_type == EntityType.UNKNOWN
        assert result.tier_used == 5
```

## Rollback Plan

If issues arise during migration:

### Phase 1 Rollback

1. Revert `models/business/__init__.py` to not call bootstrap
2. Re-enable `__init_subclass__` registration in `base.py`
3. Detection returns to import-order-dependent behavior

### Phase 2 Rollback

1. Revert `_discover_entity_projects()` to populate `EntityProjectRegistry`
2. Keep `EntityProjectRegistry` as primary for Resolver API
3. `ProjectTypeRegistry` remains for detection only

### Phase 3 Rollback

N/A - Phase 3 is cleanup, reversible by git revert.

## Success Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| SC-001 | Single registry for all entity-project mappings | `ProjectRegistry` is only registry class used |
| SC-002 | Detection works during cache warming | No Tier 5 fallbacks for tasks in known projects |
| SC-003 | Entity Resolver API returns correct GIDs | API tests pass |
| SC-004 | Bootstrap runs at import time | `register_all_models()` called from `__init__.py` |
| SC-005 | No import-order dependencies | Detection works regardless of class import order |
| SC-006 | Deprecation warnings for old API | `EntityProjectRegistry` usage logs warning |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import cycle from bootstrap | Medium | High | Lazy imports inside `register_all_models()` |
| Tests rely on auto-registration | High | Medium | Update fixtures to call `register_all_models()` |
| Third-party code uses `EntityProjectRegistry` | Low | Low | Deprecation shim maintains compatibility |
| Performance impact of eager imports | Low | Low | All models already imported by most code paths |

## Files to Modify

| File | Change |
|------|--------|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/registry.py` | Extend to unified `ProjectRegistry` |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/_bootstrap.py` | NEW: Explicit registration |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/__init__.py` | Call bootstrap |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/base.py` | Remove auto-registration |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Deprecation shim |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Use unified registry |
| `/Users/tomtenuta/Code/autom8_asana/tests/unit/models/business/test_registry_consolidation.py` | NEW: Unit tests |
| `/Users/tomtenuta/Code/autom8_asana/tests/integration/test_registry_detection.py` | NEW: Integration tests |

## Artifact Attestation

| Artifact | Absolute Path | Status |
|----------|---------------|--------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-registry-consolidation.md` | This file |
| ADR | `/Users/tomtenuta/Code/autom8_asana/docs/decisions/ADR-registry-consolidation.md` | Pending |
| registry.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/registry.py` | Existing, to modify |
| resolver.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolver.py` | Existing, to modify |
| base.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/base.py` | Existing, to modify |
| main.py | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/main.py` | Existing, to modify |

## Handoff to Principal Engineer

This TDD is ready for implementation. The core insight is:

**Problem**: `__init_subclass__` auto-registration is timing-dependent and fails when detection runs before entity class imports.

**Solution**: Replace implicit registration with explicit `register_all_models()` called at module import time, before any detection can occur.

**Implementation order**:
1. Phase 1 first (fixes immediate detection failures)
2. Phase 2 adds consolidation (can be deferred if needed)
3. Phase 3 is cleanup (lowest priority)

**Key validation**: After Phase 1, the following should work during cache warming:
```python
from autom8_asana.models.business.registry import get_project_registry
registry = get_project_registry()
assert registry.lookup("1200653012566782") == EntityType.BUSINESS
```

If this assertion passes before any model classes are explicitly imported, the fix is working.

---

## Related Documents

- **ADR-0031**: Registry and Discovery Architecture
- **ADR-0060**: Entity Resolver Project Discovery
- **ADR-registry-consolidation**: Decision record for this consolidation (to be created)
