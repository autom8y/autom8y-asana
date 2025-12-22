# TDD: Process Pipeline

> **PARTIAL SUPERSESSION NOTICE (2025-12-19)**
>
> The `ProcessProjectRegistry` design in this TDD has been **superseded** by [ADR-0101](../decisions/ADR-0101-process-pipeline-correction.md). The ProcessProjectRegistry was never implemented - pipeline project detection now uses the existing `ProjectTypeRegistry` with dynamic discovery via `WorkspaceProjectRegistry`. See [TDD-TECH-DEBT-REMEDIATION](TDD-TECH-DEBT-REMEDIATION.md) for the corrected approach.
>
> **Superseded sections**: FR-REG requirements, ProcessProjectRegistry class design, Section 5.3 process_registry.py
>
> **Still valid**: ProcessType enum, ProcessSection enum, BusinessSeeder factory, dual membership model concepts

## Metadata
- **TDD ID**: TDD-PROCESS-PIPELINE
- **Status**: Partially Superseded
- **Author**: Architect
- **Created**: 2025-12-17
- **Last Updated**: 2025-12-19
- **PRD Reference**: [PRD-PROCESS-PIPELINE](../requirements/PRD-PROCESS-PIPELINE.md)
- **Related TDDs**: [TDD-0017 Hierarchy Hydration](TDD-0017-hierarchy-hydration.md), [TDD-0024 Holder Factory](TDD-0024-holder-factory.md)
- **Related ADRs**: [ADR-0096](../decisions/ADR-0096-processtype-expansion.md), [ADR-0097](../decisions/ADR-0097-processsection-state-machine.md), [ADR-0098](../decisions/ADR-0098-dual-membership-model.md), [ADR-0099](../decisions/ADR-0099-businessseeder-factory.md), [ADR-0100](../decisions/ADR-0100-state-transition-composition.md), **[ADR-0101](../decisions/ADR-0101-process-pipeline-correction.md) (supersedes ProcessProjectRegistry)**

---

## Overview

This TDD specifies the technical design for modeling Process entities as first-class pipeline events. The design extends the existing Process/ProcessHolder pattern with type differentiation (ProcessType enum), pipeline state tracking (ProcessSection enum), and a factory pattern (BusinessSeeder) for complete hierarchy creation. All pipeline operations compose with existing SaveSession primitives.

---

## Requirements Summary

Key requirements from PRD-PROCESS-PIPELINE:

- **FR-TYPE**: ProcessType enum with 6 pipeline types + GENERIC fallback
- **FR-SECTION**: ProcessSection enum with 7 states + from_name() method
- **FR-REG**: ProcessProjectRegistry singleton mapping ProcessType to project GIDs
- **FR-STATE**: pipeline_state property extracting state from cached memberships
- **FR-DUAL**: Dual membership support (hierarchy + pipeline project)
- **FR-TRANS**: State transition helpers composing with SaveSession
- **FR-SEED**: BusinessSeeder factory for find-or-create pattern
- **NFR-PERF**: <1ms for pipeline_state and process_type access (no API calls)

See [PRD-PROCESS-PIPELINE](../requirements/PRD-PROCESS-PIPELINE.md) for complete requirements.

---

## System Context

```
+-----------------------------------------------------------+
|                   Consumer Applications                    |
|    (autom8 platform, webhook handlers, Calendly hooks)    |
+-----------------------------------------------------------+
                              |
                              v
+-----------------------------------------------------------+
|                    autom8_asana SDK                        |
|  +-----------------------------------------------------+  |
|  |                Business Model Layer                  |  |
|  |  +-------------+  +--------------+  +------------+  |  |
|  |  | ProcessType |  |ProcessSection|  |ProcessProj |  |  |
|  |  | (enum)      |  | (enum)       |  |Registry    |  |  |
|  |  +-------------+  +--------------+  +------------+  |  |
|  |                                                      |  |
|  |  +-------------+  +--------------+  +------------+  |  |
|  |  | Process     |  | Business     |  |Unit        |  |  |
|  |  | .pipeline_  |  | Seeder       |  |.processes  |  |  |
|  |  |  state      |  | (factory)    |  |            |  |  |
|  |  | .process_   |  +--------------+  +------------+  |  |
|  |  |  type       |                                    |  |
|  |  +-------------+                                    |  |
|  +-----------------------------------------------------+  |
|  +-----------------------------------------------------+  |
|  |              Persistence Layer                       |  |
|  |  SaveSession: add_to_project(), move_to_section()   |  |
|  +-----------------------------------------------------+  |
+-----------------------------------------------------------+
                              |
                              v
                     Asana REST API
                     (Projects, Sections, Tasks)
```

### Interaction Flow

1. **Entity Creation**: BusinessSeeder -> SaveSession -> Asana API
2. **State Query**: Process.pipeline_state -> cached memberships (no API)
3. **State Transition**: Process.move_to_state() -> SaveSession.move_to_section()

---

## Design

### Component Architecture

```
src/autom8_asana/models/business/
+-- process.py              # ProcessType, ProcessSection, Process (extended)
+-- process_registry.py     # ProcessProjectRegistry (NEW)
+-- seeder.py               # BusinessSeeder, SeederResult (NEW)

src/autom8_asana/models/business/detection.py
+-- (integration point for ProcessProjectRegistry)
```

| Component | Responsibility | Lines of Change |
|-----------|----------------|-----------------|
| `ProcessType` | Enum for process workflow types | ~15 (expand existing) |
| `ProcessSection` | Enum for pipeline states with from_name() | ~50 (new class) |
| `ProcessProjectRegistry` | Singleton mapping ProcessType -> project GID | ~150 (new module) |
| `Process` extensions | pipeline_state, process_type, add_to_pipeline, move_to_state | ~100 (extend existing) |
| `BusinessSeeder` | Factory for find-or-create hierarchy | ~250 (new module) |
| Detection integration | ProcessProjectRegistry in Tier 1 | ~30 (modify existing) |

---

### Module Structure

#### 1. process.py Extensions

**ProcessType Enum Expansion**

```python
class ProcessType(str, Enum):
    """Process types representing workflow stages.

    Per ADR-0096: Expanded from GENERIC-only to stakeholder-aligned types.
    """
    # Pipeline types (stakeholder-aligned)
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"

    # Fallback (backward compatibility)
    GENERIC = "generic"
```

**ProcessSection Enum (New)**

```python
class ProcessSection(str, Enum):
    """Standard sections in process pipeline projects.

    Per ADR-0097: State representation via section membership.
    """
    OPPORTUNITY = "opportunity"
    DELAYED = "delayed"
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    CONVERTED = "converted"
    DID_NOT_CONVERT = "did_not_convert"
    OTHER = "other"

    @classmethod
    def from_name(cls, name: str | None) -> ProcessSection | None:
        """Match section name case-insensitively.

        Per FR-SECTION-002/003/004: Graceful matching with OTHER fallback.

        Args:
            name: Section name from Asana (e.g., "Opportunity", "Did Not Convert")

        Returns:
            ProcessSection enum value, OTHER for unrecognized, None for None input.
        """
        if name is None:
            return None

        normalized = name.lower().replace(" ", "_").replace("-", "_")

        # Direct enum lookup
        for member in cls:
            if member.value == normalized:
                return member

        # Partial match for common variations
        ALIASES: dict[str, ProcessSection] = {
            "did_not_convert": cls.DID_NOT_CONVERT,
            "didnt_convert": cls.DID_NOT_CONVERT,
            "not_converted": cls.DID_NOT_CONVERT,
            "lost": cls.DID_NOT_CONVERT,
        }

        if normalized in ALIASES:
            return ALIASES[normalized]

        return cls.OTHER
```

**Process Class Extensions**

```python
class Process(BusinessEntity):
    # ... existing code ...

    @property
    def pipeline_state(self) -> ProcessSection | None:
        """Get current pipeline state from section membership.

        Per FR-STATE-001/002/003: Extract from cached memberships without API.
        Per ADR-0098: Identify pipeline project via ProcessProjectRegistry.

        Returns:
            ProcessSection or None if not in pipeline project.
        """
        if not self.memberships:
            return None

        from autom8_asana.models.business.process_registry import (
            get_process_project_registry,
        )

        registry = get_process_project_registry()
        pipeline_memberships = []

        for membership in self.memberships:
            project_gid = membership.get("project", {}).get("gid")
            if project_gid and registry.is_registered(project_gid):
                pipeline_memberships.append(membership)

        # Per FR-STATE-005: Multi-pipeline is error condition
        if len(pipeline_memberships) > 1:
            logger.warning(
                "Process in multiple pipeline projects",
                extra={
                    "process_gid": self.gid,
                    "pipeline_projects": [
                        m.get("project", {}).get("gid")
                        for m in pipeline_memberships
                    ],
                },
            )
            return None

        if not pipeline_memberships:
            return None

        section_name = pipeline_memberships[0].get("section", {}).get("name")
        return ProcessSection.from_name(section_name)

    @property
    def process_type(self) -> ProcessType:
        """Determine process type from pipeline project membership.

        Per FR-STATE-006/007/008: Detection via ProcessProjectRegistry.
        Per ADR-0096: Fallback to GENERIC for backward compatibility.

        Returns:
            ProcessType enum value (GENERIC if not in registered pipeline).
        """
        if not self.memberships:
            return ProcessType.GENERIC

        from autom8_asana.models.business.process_registry import (
            get_process_project_registry,
        )

        registry = get_process_project_registry()
        detected_types: list[ProcessType] = []

        for membership in self.memberships:
            project_gid = membership.get("project", {}).get("gid")
            if project_gid:
                process_type = registry.lookup(project_gid)
                if process_type is not None:
                    detected_types.append(process_type)

        # Per FR-STATE-008: Multi-pipeline is ambiguous
        if len(detected_types) > 1:
            logger.warning(
                "Process in multiple pipeline projects, defaulting to GENERIC",
                extra={
                    "process_gid": self.gid,
                    "detected_types": [t.value for t in detected_types],
                },
            )
            return ProcessType.GENERIC

        if not detected_types:
            return ProcessType.GENERIC

        return detected_types[0]

    def add_to_pipeline(
        self,
        session: SaveSession,
        process_type: ProcessType,
        *,
        section: ProcessSection | None = None,
    ) -> SaveSession:
        """Queue addition to pipeline project.

        Per FR-DUAL-001/002/003: Helper composing with SaveSession.add_to_project.

        Args:
            session: SaveSession for batching operations.
            process_type: Pipeline type to add to.
            section: Optional target section (default: project's first section).

        Returns:
            SaveSession for fluent chaining.

        Raises:
            ValueError: If process_type has no registered project GID.
        """
        from autom8_asana.models.business.process_registry import (
            get_process_project_registry,
        )

        registry = get_process_project_registry()
        project_gid = registry.get_project_gid(process_type)

        if project_gid is None:
            raise ValueError(
                f"No project GID registered for ProcessType.{process_type.name}. "
                f"Set ASANA_PROCESS_PROJECT_{process_type.name} environment variable."
            )

        session.add_to_project(self, project_gid)

        if section is not None:
            section_gid = registry.get_section_gid(process_type, section)
            if section_gid:
                session.move_to_section(self, section_gid)

        return session

    def move_to_state(
        self,
        session: SaveSession,
        target_state: ProcessSection,
    ) -> SaveSession:
        """Queue state transition via section move.

        Per FR-TRANS-001/002/003/004: Helper composing with SaveSession.move_to_section.
        Per ADR-0100: Composition over extension.

        Args:
            session: SaveSession for batching operations.
            target_state: Target ProcessSection state.

        Returns:
            SaveSession for fluent chaining.

        Raises:
            ValueError: If process not in pipeline project or section not found.
        """
        process_type = self.process_type
        if process_type == ProcessType.GENERIC:
            raise ValueError(
                "Cannot move_to_state: Process is not in a registered pipeline project"
            )

        from autom8_asana.models.business.process_registry import (
            get_process_project_registry,
        )

        registry = get_process_project_registry()
        section_gid = registry.get_section_gid(process_type, target_state)

        if section_gid is None:
            project_gid = registry.get_project_gid(process_type)
            raise ValueError(
                f"Section '{target_state.value}' not found in project {project_gid}. "
                f"Configure section GID or use SaveSession.move_to_section() directly."
            )

        session.move_to_section(self, section_gid)
        return session
```

---

#### 2. process_registry.py (New Module)

```python
"""Process type to project GID registry.

Per ADR-0096: ProcessProjectRegistry singleton for pipeline project lookup.
Per FR-REG-001/002/003/004/005: O(1) lookup with env var override.
"""

from __future__ import annotations

import logging
import os
from typing import ClassVar

from autom8_asana.models.business.process import ProcessType, ProcessSection

__all__ = [
    "ProcessProjectRegistry",
    "get_process_project_registry",
]

logger = logging.getLogger(__name__)


class ProcessProjectRegistry:
    """Singleton registry mapping ProcessType to project/section GIDs.

    Per FR-REG-001: Singleton accessed via get_process_project_registry().
    Per FR-REG-002: Maps ProcessType to project GID.
    Per FR-REG-003: Environment variable override pattern.
    Per FR-REG-004: Reverse lookup (GID -> ProcessType).
    Per FR-REG-005: Lazy initialization.

    Environment Variables:
        ASANA_PROCESS_PROJECT_SALES: Project GID for sales pipeline
        ASANA_PROCESS_PROJECT_OUTREACH: Project GID for outreach pipeline
        ASANA_PROCESS_PROJECT_ONBOARDING: Project GID for onboarding pipeline
        ASANA_PROCESS_PROJECT_IMPLEMENTATION: Project GID for implementation pipeline
        ASANA_PROCESS_PROJECT_RETENTION: Project GID for retention pipeline
        ASANA_PROCESS_PROJECT_REACTIVATION: Project GID for reactivation pipeline

        Section GIDs (optional, per project):
        ASANA_SECTION_{TYPE}_{SECTION}: e.g., ASANA_SECTION_SALES_OPPORTUNITY

    Usage:
        registry = get_process_project_registry()

        # Forward lookup
        project_gid = registry.get_project_gid(ProcessType.SALES)

        # Reverse lookup
        process_type = registry.lookup("1234567890")

        # Section lookup
        section_gid = registry.get_section_gid(ProcessType.SALES, ProcessSection.CONVERTED)
    """

    _instance: ClassVar[ProcessProjectRegistry | None] = None

    # Instance attributes
    _type_to_gid: dict[ProcessType, str]
    _gid_to_type: dict[str, ProcessType]
    _section_gids: dict[tuple[ProcessType, ProcessSection], str]
    _initialized: bool

    def __new__(cls) -> ProcessProjectRegistry:
        """Get or create singleton instance."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._type_to_gid = {}
            instance._gid_to_type = {}
            instance._section_gids = {}
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def _ensure_initialized(self) -> None:
        """Lazy initialization from environment variables.

        Per FR-REG-005: Env vars read on first access, not import.
        """
        if self._initialized:
            return

        # Load project GIDs from environment
        for process_type in ProcessType:
            if process_type == ProcessType.GENERIC:
                continue  # GENERIC has no project

            env_var = f"ASANA_PROCESS_PROJECT_{process_type.name}"
            env_value = os.environ.get(env_var, "").strip()

            if env_value:
                self._type_to_gid[process_type] = env_value
                self._gid_to_type[env_value] = process_type

                logger.debug(
                    "Registered process project from environment",
                    extra={
                        "process_type": process_type.value,
                        "project_gid": env_value,
                        "env_var": env_var,
                    },
                )

        # Load section GIDs from environment (optional)
        for process_type in ProcessType:
            if process_type == ProcessType.GENERIC:
                continue

            for section in ProcessSection:
                if section == ProcessSection.OTHER:
                    continue  # OTHER is fallback, not a real section

                env_var = f"ASANA_SECTION_{process_type.name}_{section.name}"
                env_value = os.environ.get(env_var, "").strip()

                if env_value:
                    self._section_gids[(process_type, section)] = env_value

        self._initialized = True

    def get_project_gid(self, process_type: ProcessType) -> str | None:
        """Get project GID for a ProcessType.

        Per FR-REG-002: Forward lookup.

        Args:
            process_type: The process type.

        Returns:
            Project GID if registered, None otherwise.
        """
        self._ensure_initialized()
        return self._type_to_gid.get(process_type)

    def lookup(self, project_gid: str) -> ProcessType | None:
        """Look up ProcessType by project GID.

        Per FR-REG-004: Reverse lookup.

        Args:
            project_gid: Asana project GID.

        Returns:
            ProcessType if found, None otherwise.
        """
        self._ensure_initialized()
        return self._gid_to_type.get(project_gid)

    def is_registered(self, project_gid: str) -> bool:
        """Check if project GID is a registered pipeline project.

        Args:
            project_gid: Asana project GID.

        Returns:
            True if registered as pipeline project.
        """
        self._ensure_initialized()
        return project_gid in self._gid_to_type

    def get_section_gid(
        self,
        process_type: ProcessType,
        section: ProcessSection,
    ) -> str | None:
        """Get section GID for a ProcessType and ProcessSection.

        Per FR-TRANS-005: Cached section lookup.

        Args:
            process_type: The process type.
            section: The target section.

        Returns:
            Section GID if configured, None otherwise.
        """
        self._ensure_initialized()
        return self._section_gids.get((process_type, section))

    def register(
        self,
        process_type: ProcessType,
        project_gid: str,
        section_gids: dict[ProcessSection, str] | None = None,
    ) -> None:
        """Programmatically register a process type (for testing).

        Args:
            process_type: The process type to register.
            project_gid: Asana project GID.
            section_gids: Optional mapping of sections to GIDs.
        """
        self._ensure_initialized()

        self._type_to_gid[process_type] = project_gid
        self._gid_to_type[project_gid] = process_type

        if section_gids:
            for section, gid in section_gids.items():
                self._section_gids[(process_type, section)] = gid

    @classmethod
    def reset(cls) -> None:
        """Reset registry for testing."""
        cls._instance = None


def get_process_project_registry() -> ProcessProjectRegistry:
    """Get the ProcessProjectRegistry singleton.

    Returns:
        The singleton ProcessProjectRegistry instance.
    """
    return ProcessProjectRegistry()
```

---

#### 3. seeder.py (New Module)

```python
"""Business entity seeding factory.

Per ADR-0099: Find-or-create pattern for complete hierarchy creation.
Per FR-SEED-001 through FR-SEED-011: BusinessSeeder factory implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

from autom8_asana.models.business.process import ProcessType, ProcessSection

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.business import Business
    from autom8_asana.models.business.contact import Contact
    from autom8_asana.models.business.process import Process, ProcessHolder
    from autom8_asana.models.business.unit import Unit

__all__ = [
    "BusinessSeeder",
    "SeederResult",
    "BusinessData",
    "ContactData",
    "ProcessData",
]

logger = logging.getLogger(__name__)


class BusinessData(BaseModel):
    """Input data for Business entity creation.

    Per FR-SEED-002: Fields used for find-or-create matching.
    """
    name: str
    company_id: str | None = None
    # Optional fields for creation
    business_address_line_1: str | None = None
    business_city: str | None = None
    business_state: str | None = None
    business_zip: str | None = None


class ContactData(BaseModel):
    """Input data for Contact entity creation.

    Per FR-SEED-010: Optional contact seeding.
    """
    full_name: str
    contact_email: str | None = None
    contact_phone: str | None = None


class ProcessData(BaseModel):
    """Input data for Process entity creation."""
    name: str
    process_type: ProcessType
    initial_state: ProcessSection = ProcessSection.OPPORTUNITY
    # Optional process fields
    priority: str | None = None
    vertical: str | None = None


@dataclass
class SeederResult:
    """Result of BusinessSeeder.seed_async().

    Per FR-SEED-007: Access to all created/found entities.

    Attributes:
        business: The Business entity (created or found).
        unit: The Unit entity (created or found).
        process_holder: The ProcessHolder (created or found).
        process: The Process entity (always created).
        contact: The Contact entity if ContactData provided.
        created_business: True if Business was created (not found).
        created_unit: True if Unit was created.
        created_process_holder: True if ProcessHolder was created.
    """
    business: Business
    unit: Unit
    process_holder: ProcessHolder
    process: Process
    contact: Contact | None = None
    created_business: bool = False
    created_unit: bool = False
    created_process_holder: bool = False


class BusinessSeeder:
    """Factory for creating complete business entity hierarchies.

    Per ADR-0099: Find-or-create pattern with SaveSession integration.

    The seeder implements a find-or-create pattern:
    1. Find existing Business by company_id or name
    2. Find or create Unit under Business
    3. Find or create ProcessHolder under Unit
    4. Create Process in ProcessHolder
    5. Add Process to pipeline project

    Example:
        seeder = BusinessSeeder(client)
        result = await seeder.seed_async(
            business=BusinessData(name="Acme Corp", company_id="ACME-001"),
            process=ProcessData(
                name="Sales Opportunity",
                process_type=ProcessType.SALES,
            ),
        )

        print(f"Business: {result.business.name}")
        print(f"Created new business: {result.created_business}")
        print(f"Process state: {result.process.pipeline_state}")
    """

    def __init__(self, client: AsanaClient) -> None:
        """Initialize seeder with Asana client.

        Args:
            client: AsanaClient for API operations.
        """
        self._client = client

    async def seed_async(
        self,
        business: BusinessData,
        process: ProcessData,
        *,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """Seed complete business hierarchy.

        Per FR-SEED-001 through FR-SEED-011: Find-or-create implementation.
        Per FR-SEED-008: Uses SaveSession for all operations.
        Per FR-SEED-011: Idempotent for same input.

        Args:
            business: Business entity data.
            process: Process entity data.
            contact: Optional contact data.
            unit_name: Optional Unit name (default: "Unit 1").

        Returns:
            SeederResult with all entities and creation flags.
        """
        from autom8_asana.models.business.business import Business
        from autom8_asana.models.business.contact import Contact
        from autom8_asana.models.business.process import Process, ProcessHolder
        from autom8_asana.models.business.unit import Unit
        from autom8_asana.models.business.process_registry import (
            get_process_project_registry,
        )

        async with self._client.save_session() as session:
            # Step 1: Find or create Business
            found_business, created_business = await self._find_or_create_business(
                session, business
            )

            # Step 2: Find or create Unit
            found_unit, created_unit = await self._find_or_create_unit(
                session, found_business, unit_name or "Unit 1"
            )

            # Step 3: Find or create ProcessHolder
            found_holder, created_holder = await self._find_or_create_process_holder(
                session, found_unit
            )

            # Step 4: Create Process
            new_process = await self._create_process(
                session, found_holder, process
            )

            # Step 5: Add to pipeline project
            registry = get_process_project_registry()
            project_gid = registry.get_project_gid(process.process_type)

            if project_gid:
                session.add_to_project(new_process, project_gid)

                # Move to initial section if configured
                section_gid = registry.get_section_gid(
                    process.process_type, process.initial_state
                )
                if section_gid:
                    session.move_to_section(new_process, section_gid)

            # Step 6: Optional contact creation
            found_contact = None
            if contact:
                found_contact = await self._create_contact(
                    session, found_business, contact
                )

            # Commit all changes
            await session.commit_async()

            return SeederResult(
                business=found_business,
                unit=found_unit,
                process_holder=found_holder,
                process=new_process,
                contact=found_contact,
                created_business=created_business,
                created_unit=created_unit,
                created_process_holder=created_holder,
            )

    def seed(
        self,
        business: BusinessData,
        process: ProcessData,
        *,
        contact: ContactData | None = None,
        unit_name: str | None = None,
    ) -> SeederResult:
        """Synchronous wrapper for seed_async().

        Per FR-SEED-009: Sync wrapper via run_sync().
        """
        from autom8_asana.transport.sync import run_sync
        return run_sync(
            self.seed_async(
                business=business,
                process=process,
                contact=contact,
                unit_name=unit_name,
            )
        )

    async def _find_or_create_business(
        self,
        session,
        data: BusinessData,
    ) -> tuple[Business, bool]:
        """Find existing Business or create new one.

        Per FR-SEED-002: Match by company_id first, then name.
        """
        from autom8_asana.models.business.business import Business

        # Try to find by company_id
        if data.company_id:
            existing = await self._find_business_by_company_id(data.company_id)
            if existing:
                return existing, False

        # Try to find by name
        existing = await self._find_business_by_name(data.name)
        if existing:
            return existing, False

        # Create new Business
        new_business = Business(
            name=data.name,
        )
        if data.company_id:
            new_business.company_id = data.company_id
        if data.business_address_line_1:
            new_business.business_address_line_1 = data.business_address_line_1

        session.add(new_business)
        return new_business, True

    async def _find_business_by_company_id(self, company_id: str) -> Business | None:
        """Search for Business by company_id custom field.

        Implementation uses search API with custom field filter.
        """
        # Implementation uses Asana search API
        # This is a simplified placeholder - actual implementation
        # would query tasks in Business project with company_id filter
        return None

    async def _find_business_by_name(self, name: str) -> Business | None:
        """Search for Business by exact name match."""
        # Implementation uses Asana search API
        return None

    async def _find_or_create_unit(
        self,
        session,
        business: Business,
        unit_name: str,
    ) -> tuple[Unit, bool]:
        """Find existing Unit or create new one under Business."""
        from autom8_asana.models.business.unit import Unit

        # Check if Business has units (requires hydration)
        if hasattr(business, 'units') and business.units:
            for unit in business.units:
                if unit.name == unit_name:
                    return unit, False

        # Create new Unit
        new_unit = Unit(name=unit_name)
        session.add(new_unit, parent=business.unit_holder)
        return new_unit, True

    async def _find_or_create_process_holder(
        self,
        session,
        unit: Unit,
    ) -> tuple[ProcessHolder, bool]:
        """Find existing ProcessHolder or create new one under Unit."""
        from autom8_asana.models.business.process import ProcessHolder

        # Check if Unit has process_holder (requires hydration)
        if hasattr(unit, 'process_holder') and unit.process_holder:
            return unit.process_holder, False

        # Create new ProcessHolder
        new_holder = ProcessHolder(name="Processes")
        session.add(new_holder, parent=unit)
        return new_holder, True

    async def _create_process(
        self,
        session,
        holder: ProcessHolder,
        data: ProcessData,
    ) -> Process:
        """Create new Process under ProcessHolder."""
        from autom8_asana.models.business.process import Process

        new_process = Process(name=data.name)

        if data.priority:
            new_process.priority = data.priority
        if data.vertical:
            new_process.vertical = data.vertical

        session.add(new_process, parent=holder)
        return new_process

    async def _create_contact(
        self,
        session,
        business: Business,
        data: ContactData,
    ) -> Contact:
        """Create Contact under Business's ContactHolder."""
        from autom8_asana.models.business.contact import Contact

        new_contact = Contact(name=data.full_name)

        if data.contact_email:
            new_contact.contact_email = data.contact_email
        if data.contact_phone:
            new_contact.contact_phone = data.contact_phone

        session.add(new_contact, parent=business.contact_holder)
        return new_contact
```

---

### Data Model

**ProcessType Enum Values**

| Value | Environment Variable | Purpose |
|-------|---------------------|---------|
| SALES | ASANA_PROCESS_PROJECT_SALES | Sales pipeline opportunities |
| OUTREACH | ASANA_PROCESS_PROJECT_OUTREACH | Outreach campaigns |
| ONBOARDING | ASANA_PROCESS_PROJECT_ONBOARDING | Customer onboarding |
| IMPLEMENTATION | ASANA_PROCESS_PROJECT_IMPLEMENTATION | Service implementation |
| RETENTION | ASANA_PROCESS_PROJECT_RETENTION | Customer retention |
| REACTIVATION | ASANA_PROCESS_PROJECT_REACTIVATION | Customer reactivation |
| GENERIC | (none) | Fallback for unregistered |

**ProcessSection Enum Values**

| Value | Asana Section Name | Meaning |
|-------|-------------------|---------|
| OPPORTUNITY | Opportunity | Initial lead state |
| DELAYED | Delayed | Temporarily paused |
| ACTIVE | Active | Currently working |
| SCHEDULED | Scheduled | Future action planned |
| CONVERTED | Converted | Success outcome |
| DID_NOT_CONVERT | Did Not Convert | Failed outcome |
| OTHER | (any unrecognized) | Fallback for custom sections |

---

### API Contracts

**Process.pipeline_state Property**

```python
@property
def pipeline_state(self) -> ProcessSection | None:
    """
    Returns:
        ProcessSection if in pipeline project, None otherwise.

    Side Effects:
        None (reads from cached memberships).

    Performance:
        O(n) where n = number of memberships (typically 1-3).
        No API calls.
    """
```

**Process.process_type Property**

```python
@property
def process_type(self) -> ProcessType:
    """
    Returns:
        ProcessType based on pipeline project membership.
        GENERIC if not in registered pipeline.

    Side Effects:
        None.

    Performance:
        O(n) where n = number of memberships.
        No API calls.
    """
```

**Process.add_to_pipeline() Method**

```python
def add_to_pipeline(
    self,
    session: SaveSession,
    process_type: ProcessType,
    *,
    section: ProcessSection | None = None,
) -> SaveSession:
    """
    Args:
        session: SaveSession for batching.
        process_type: Target pipeline type.
        section: Optional target section.

    Returns:
        SaveSession for fluent chaining.

    Raises:
        ValueError: If process_type has no registered project.
    """
```

**Process.move_to_state() Method**

```python
def move_to_state(
    self,
    session: SaveSession,
    target_state: ProcessSection,
) -> SaveSession:
    """
    Args:
        session: SaveSession for batching.
        target_state: Target ProcessSection.

    Returns:
        SaveSession for fluent chaining.

    Raises:
        ValueError: If not in pipeline project.
        ValueError: If section GID not configured.
    """
```

**BusinessSeeder.seed_async() Method**

```python
async def seed_async(
    self,
    business: BusinessData,
    process: ProcessData,
    *,
    contact: ContactData | None = None,
    unit_name: str | None = None,
) -> SeederResult:
    """
    Args:
        business: Business entity data for find-or-create.
        process: Process entity data (always created).
        contact: Optional Contact data.
        unit_name: Optional Unit name (default "Unit 1").

    Returns:
        SeederResult with all entities and creation flags.

    Side Effects:
        Creates entities via SaveSession.commit_async().

    Performance:
        1-5 API calls depending on find results.
    """
```

---

### Data Flow

**State Query Flow (pipeline_state)**

```
Process.pipeline_state
    |
    v
Check self.memberships (cached)
    |
    v
For each membership:
    ProcessProjectRegistry.is_registered(project_gid)
    |
    v
If multiple pipeline projects:
    Log warning, return None
    |
    v
Extract section name from membership
    |
    v
ProcessSection.from_name(section_name)
    |
    v
Return ProcessSection or None
```

**State Transition Flow (move_to_state)**

```
process.move_to_state(session, ProcessSection.CONVERTED)
    |
    v
self.process_type -> ProcessType.SALES
    |
    v
ProcessProjectRegistry.get_section_gid(SALES, CONVERTED)
    |
    v
session.move_to_section(process, section_gid)
    |
    v
(ActionOperation queued)
    |
    v
session.commit_async()
    |
    v
Asana API: POST /sections/{section_gid}/addTask
```

**BusinessSeeder Flow**

```
BusinessSeeder.seed_async(business_data, process_data)
    |
    v
1. Find Business by company_id/name
   |
   +-- Found: use existing
   +-- Not found: session.add(new_business)
    |
    v
2. Find Unit under Business
   |
   +-- Found: use existing
   +-- Not found: session.add(new_unit, parent=unit_holder)
    |
    v
3. Find ProcessHolder under Unit
   |
   +-- Found: use existing
   +-- Not found: session.add(new_holder, parent=unit)
    |
    v
4. Create Process
   session.add(new_process, parent=holder)
    |
    v
5. Add to pipeline project
   session.add_to_project(process, project_gid)
   session.move_to_section(process, section_gid)
    |
    v
6. session.commit_async()
   (Batch API creates all entities)
    |
    v
Return SeederResult
```

---

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| ProcessType expansion | 6 new types + GENERIC | Stakeholder-aligned, backward compatible | [ADR-0096](../decisions/ADR-0096-processtype-expansion.md) |
| ProcessSection as state | Section membership, not custom field | Matches Asana UI pipeline view | [ADR-0097](../decisions/ADR-0097-processsection-state-machine.md) |
| Dual membership model | Hierarchy + pipeline simultaneously | Preserves navigation while enabling pipeline tracking | [ADR-0098](../decisions/ADR-0098-dual-membership-model.md) |
| BusinessSeeder pattern | Find-or-create factory | Idempotent seeding, single entry point | [ADR-0099](../decisions/ADR-0099-businessseeder-factory.md) |
| State transition composition | Compose with SaveSession.move_to_section() | Reuse existing primitives, no new SaveSession methods | [ADR-0100](../decisions/ADR-0100-state-transition-composition.md) |
| Multi-pipeline as error | Return None/GENERIC with warning | Clear error condition, prevent undefined behavior | [ADR-0098](../decisions/ADR-0098-dual-membership-model.md) |

---

## Complexity Assessment

**Level: Module**

This design is appropriately sized as a **Module**:

- **Clear API surface**: ProcessType, ProcessSection, ProcessProjectRegistry, BusinessSeeder
- **Minimal structure**: 2-3 new modules, extensions to existing Process class
- **No independent deployment**: Part of SDK, not a separate service
- **Limited coordination**: All operations compose with existing SaveSession
- **Testable in isolation**: Registry and seeder can be unit tested independently

**Escalation signals NOT present**:
- No external API contracts required (consumers use SDK interfaces)
- No multi-service coordination
- No complex state machine enforcement

---

## Implementation Plan

### Phase 1: Core Enums and Registry (2-3 hours)

| Task | Deliverable | Dependencies |
|------|-------------|--------------|
| Expand ProcessType enum | 6 new values in process.py | None |
| Create ProcessSection enum | New enum with from_name() | None |
| Create ProcessProjectRegistry | New module process_registry.py | ProcessType |
| Update existing tests | Fix enum count test | ProcessType changes |

**Acceptance**: ProcessType and ProcessSection importable, registry reads env vars.

### Phase 2: Process Extensions (2-3 hours)

| Task | Deliverable | Dependencies |
|------|-------------|--------------|
| Add pipeline_state property | Process class extension | ProcessProjectRegistry |
| Update process_type property | Use registry lookup | ProcessProjectRegistry |
| Add add_to_pipeline() method | SaveSession composition helper | ProcessProjectRegistry |
| Add move_to_state() method | SaveSession composition helper | ProcessProjectRegistry |

**Acceptance**: Process entities report correct pipeline_state and process_type.

### Phase 3: Detection Integration (1-2 hours)

| Task | Deliverable | Dependencies |
|------|-------------|--------------|
| Integrate ProcessProjectRegistry in Tier 1 | Detection uses pipeline registry | ProcessProjectRegistry |
| Add tests for pipeline detection | Unit tests for detection | Phase 2 |

**Acceptance**: detect_entity_type() recognizes pipeline project membership.

### Phase 4: BusinessSeeder (3-4 hours)

| Task | Deliverable | Dependencies |
|------|-------------|--------------|
| Create seeder module | seeder.py with BusinessSeeder | Phases 1-2 |
| Implement find-or-create | _find_or_create_* methods | Asana search API |
| Integration tests | Test full seeding flow | Phase 3 |

**Acceptance**: BusinessSeeder.seed_async() creates complete hierarchy.

### Phase 5: Documentation and Polish (1 hour)

| Task | Deliverable | Dependencies |
|------|-------------|--------------|
| Update skill documentation | entities.md with pipeline info | All phases |
| Update INDEX.md | Register new documents | All phases |
| Final review | Code review, type checking | All phases |

**Total Estimate**: 9-13 hours implementation time

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Section names vary between projects** | High | Medium | from_name() with fuzzy matching, OTHER fallback, section GID override |
| **Pipeline project GIDs not configured** | Medium | High | Clear error messages, environment variable documentation |
| **Multi-pipeline membership edge case** | Medium | Low | Treat as error, log warning, return None/GENERIC |
| **BusinessSeeder search performance** | Medium | Medium | Caching in registry, limit search scope to Business project |
| **Backward compatibility breaks** | High | Low | GENERIC preserved, existing tests pass (enum count updated) |

---

## Observability

**Metrics**:
- `process_pipeline_state_lookups_total`: Count of pipeline_state property accesses
- `process_type_lookups_total`: Count of process_type property accesses
- `business_seeder_operations_total`: Count of seed operations by outcome (created/found)

**Logging**:
- DEBUG: Registry initialization, successful lookups
- WARNING: Multi-pipeline membership detected, section not found
- ERROR: Pipeline project not configured (ValueError raised)

**Alerting**:
- Alert on high rate of WARNING logs (indicates configuration issues)
- Alert on BusinessSeeder failures in production

---

## Testing Strategy

**Unit Tests**:
- ProcessType enum: All values accessible, string representation
- ProcessSection.from_name(): Case insensitivity, aliases, fallback to OTHER
- ProcessProjectRegistry: Singleton behavior, env var loading, lookups
- Process.pipeline_state: Various membership scenarios, multi-pipeline warning
- Process.process_type: Detection from memberships, GENERIC fallback

**Integration Tests**:
- Process.add_to_pipeline(): Queues correct ActionOperation
- Process.move_to_state(): Queues correct section move
- BusinessSeeder: Full hierarchy creation with mocked API

**Performance Tests**:
- pipeline_state access: Verify <1ms (no API calls)
- process_type access: Verify <1ms
- Registry initialization: Verify lazy loading

**Test Coverage Target**: >= 90% for new code

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should section GID lookup cache sections list from API? | Architect | Implementation | Deferred: env var config first, API lookup in Phase 2 |
| Should BusinessSeeder support bulk seeding? | Stakeholder | Post-MVP | TBD: Single entity focus for MVP |
| Should ProcessData accept arbitrary custom field overrides? | Stakeholder | Implementation | Likely yes: Add `extra_fields: dict` param |

---

## Requirement Traceability Matrix

| Requirement | Design Element | Test Coverage |
|-------------|----------------|---------------|
| FR-TYPE-001/002/003 | ProcessType enum expansion | test_process_type_values |
| FR-SECTION-001/002/003/004 | ProcessSection enum + from_name() | test_processsection_from_name |
| FR-REG-001/002/003/004/005 | ProcessProjectRegistry | test_registry_* |
| FR-STATE-001/002/003/004/005 | Process.pipeline_state | test_pipeline_state_* |
| FR-STATE-006/007/008 | Process.process_type | test_process_type_detection |
| FR-DUAL-001/002/003/004/005 | Process.add_to_pipeline() | test_add_to_pipeline_* |
| FR-TRANS-001/002/003/004/005 | Process.move_to_state() | test_move_to_state_* |
| FR-SEED-001 through 011 | BusinessSeeder | test_seeder_* |
| FR-DETECT-001/002/003 | Detection integration | test_detection_pipeline |
| FR-COMPAT-001/002/003/004/005 | Backward compatibility | existing tests pass |
| NFR-PERF-001/002 | No API in properties | benchmark tests |
| NFR-CONFIG-001/002 | Env var + case-insensitive | test_config_* |
| NFR-TEST-001/002 | Test coverage | pytest --cov |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-17 | Architect | Initial draft |
