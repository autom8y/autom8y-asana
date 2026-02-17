"""Project-to-EntityType registry for deterministic entity type detection.

Per TDD-DETECTION Phase 1: ProjectTypeRegistry singleton for O(1) lookup.
Per ADR-0093: Module-level singleton with test reset capability.
Per FR-REG-001: O(1) registry lookup via dict.
Per FR-REG-003: Auto-population via BusinessEntity.__init_subclass__.
Per FR-REG-004: Environment variable override support.
Per FR-REG-005: Duplicate GID detection with ValueError.

Per TDD-WORKSPACE-PROJECT-REGISTRY: WorkspaceProjectRegistry for dynamic discovery.
Per ADR-0108: Composition wrapper around ProjectTypeRegistry, module-level singleton.
Per ADR-0109: Lazy discovery triggered on first unregistered GID in async path.
"""

from __future__ import annotations

import os
import re
import time
from typing import TYPE_CHECKING, Any, ClassVar

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.detection import EntityType
    from autom8_asana.models.business.process import ProcessType

__all__ = [
    "ProjectTypeRegistry",
    "WorkspaceProjectRegistry",
    "get_registry",
    "get_workspace_registry",
]

logger = get_logger(__name__)


class ProjectTypeRegistry:
    """Singleton registry mapping project GIDs to EntityType.

    Per FR-REG-001: O(1) lookup via dict.
    Per ADR-0093: Module-level singleton with test reset capability.

    The registry is populated automatically via BusinessEntity.__init_subclass__
    when entity classes are imported. Environment variables can override
    class-level PRIMARY_PROJECT_GID values.

    Usage:
        # Get singleton instance
        registry = get_registry()

        # Look up entity type by project GID
        entity_type = registry.lookup("1200653012566782")

        # Get primary project GID for an entity type
        project_gid = registry.get_primary_gid(EntityType.BUSINESS)

    Testing:
        # Reset registry for test isolation
        ProjectTypeRegistry.reset()
    """

    _instance: ClassVar[ProjectTypeRegistry | None] = None

    # Instance attributes - declared for type checking
    # Use Any in annotations to avoid import issues, actual typing is at runtime
    _gid_to_type: dict[str, Any]  # dict[str, EntityType] at runtime
    _type_to_gid: dict[Any, str]  # dict[EntityType, str] at runtime
    _initialized: bool

    def __new__(cls) -> ProjectTypeRegistry:
        """Get or create singleton instance.

        Returns:
            The singleton ProjectTypeRegistry instance.
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._gid_to_type = {}
            instance._type_to_gid = {}
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize instance attributes (only runs once due to singleton)."""
        # Attributes are set in __new__ to avoid re-initialization
        pass

    def register(self, project_gid: str, entity_type: EntityType) -> None:
        """Register a project GID to EntityType mapping.

        Per FR-REG-003: Called by __init_subclass__ for each entity.
        Per FR-REG-005: Raises ValueError on duplicate GID with different type.

        Args:
            project_gid: Asana project GID.
            entity_type: EntityType this project represents.

        Raises:
            ValueError: If project_gid already registered to different type.
        """
        if project_gid in self._gid_to_type:
            existing = self._gid_to_type[project_gid]
            if existing != entity_type:
                logger.warning(
                    "Duplicate project GID registration attempted",
                    extra={
                        "project_gid": project_gid,
                        "existing_type": existing.name,
                        "new_type": entity_type.name,
                    },
                )
                raise ValueError(
                    f"Project GID {project_gid} already registered to "
                    f"{existing.name}, cannot register to {entity_type.name}"
                )
            # Idempotent: same mapping already exists
            logger.debug(
                "Idempotent registration (same mapping exists)",
                extra={
                    "project_gid": project_gid,
                    "entity_type": entity_type.name,
                },
            )
            return

        self._gid_to_type[project_gid] = entity_type
        # Only set type_to_gid if not already set (first registration wins)
        if entity_type not in self._type_to_gid:
            self._type_to_gid[entity_type] = project_gid

        logger.debug(
            "Registered project GID to entity type",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type.name,
            },
        )

    def lookup(self, project_gid: str) -> EntityType | None:
        """Look up EntityType by project GID.

        Per FR-REG-001: O(1) dict lookup.

        Args:
            project_gid: Asana project GID.

        Returns:
            EntityType if found, None otherwise.
        """
        result = self._gid_to_type.get(project_gid)
        if result is None:
            logger.debug(
                "Project GID not found in registry",
                extra={"project_gid": project_gid},
            )
        return result

    def get_primary_gid(self, entity_type: EntityType) -> str | None:
        """Get primary project GID for an EntityType.

        Per FR-HEAL-001: Used to determine expected_project_gid for healing.

        Args:
            entity_type: The entity type.

        Returns:
            Primary project GID if registered, None otherwise.
        """
        return self._type_to_gid.get(entity_type)

    def is_registered(self, project_gid: str) -> bool:
        """Check if a project GID is registered.

        Args:
            project_gid: Asana project GID to check.

        Returns:
            True if registered, False otherwise.
        """
        return project_gid in self._gid_to_type

    def get_all_mappings(self) -> dict[str, EntityType]:
        """Get a copy of all GID-to-type mappings.

        Returns:
            Copy of the internal mapping dict (for testing/debugging).
        """
        return dict(self._gid_to_type)

    @classmethod
    def reset(cls) -> None:
        """Reset registry for testing.

        Per ADR-0093: Testing support via explicit reset.
        Clears the singleton instance so next access creates a fresh registry.
        """
        cls._instance = None
        logger.debug("Registry reset")


def get_registry() -> ProjectTypeRegistry:
    """Get the ProjectTypeRegistry singleton.

    Returns:
        The singleton ProjectTypeRegistry instance.
    """
    return ProjectTypeRegistry()


# --- Registration Helper Functions ---


def _class_name_to_entity_type(class_name: str) -> EntityType | None:
    """Convert class name to EntityType.

    Per FR-REG-003: Maps class names to EntityType enum values.

    Examples:
        Business -> EntityType.BUSINESS
        ContactHolder -> EntityType.CONTACT_HOLDER
        DNAHolder -> EntityType.DNA_HOLDER

    Args:
        class_name: The class name to convert.

    Returns:
        EntityType if class name maps to a known type, None otherwise.
    """
    from autom8_asana.models.business.detection import EntityType

    # Handle special cases where naming doesn't follow convention
    SPECIAL_CASES = {
        "DNAHolder": "DNA_HOLDER",
        "ReconciliationHolder": "RECONCILIATIONS_HOLDER",
    }

    if class_name in SPECIAL_CASES:
        type_name = SPECIAL_CASES[class_name]
    else:
        # Convert CamelCase to UPPER_SNAKE_CASE
        # Example: ContactHolder -> CONTACT_HOLDER
        type_name = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).upper()

    try:
        return EntityType[type_name]
    except KeyError:
        return None


def _register_entity_with_registry(cls: type) -> None:
    """Register entity class with ProjectTypeRegistry.

    Per FR-REG-003: Auto-population via __init_subclass__.
    Per FR-REG-004: Environment variable override.

    Called from BusinessEntity.__init_subclass__ and holder __init_subclass__
    hooks to register entity types with their project GIDs.

    Args:
        cls: The entity class to register.
    """
    from autom8_asana.models.business.detection import EntityType

    # Derive entity type from class name
    entity_type = _class_name_to_entity_type(cls.__name__)
    if entity_type is None:
        logger.debug(
            "Class name does not map to known EntityType",
            extra={"class_name": cls.__name__},
        )
        return

    # Skip UNKNOWN type
    if entity_type == EntityType.UNKNOWN:
        return

    # Get project GID (env var override, then class default)
    env_var = f"ASANA_PROJECT_{entity_type.name}"
    env_value = os.environ.get(env_var, "")
    class_value = getattr(cls, "PRIMARY_PROJECT_GID", None)

    # Environment variable takes precedence if set and non-empty
    if env_value.strip():
        project_gid = env_value.strip()
        logger.debug(
            "Using environment variable override for project GID",
            extra={
                "class_name": cls.__name__,
                "env_var": env_var,
                "project_gid": project_gid,
            },
        )
    elif class_value:
        project_gid = class_value
    else:
        # No project GID for this entity (e.g., LocationHolder, ProcessHolder)
        logger.debug(
            "No project GID defined for entity class",
            extra={"class_name": cls.__name__, "entity_type": entity_type.name},
        )
        return

    # Register with the singleton
    registry = get_registry()
    try:
        registry.register(project_gid, entity_type)
    except ValueError:
        # Log but don't re-raise - allow import to continue
        logger.warning(
            "Failed to register entity class with registry (duplicate GID)",
            extra={
                "class_name": cls.__name__,
                "entity_type": entity_type.name,
                "project_gid": project_gid,
            },
        )


# --- WorkspaceProjectRegistry ---


class WorkspaceProjectRegistry:
    """Workspace-aware project registry with dynamic pipeline discovery.

    Per TDD-WORKSPACE-PROJECT-REGISTRY: Extends detection with dynamic discovery.
    Per ADR-0108: Composes with ProjectTypeRegistry for static lookups.
    Per ADR-0109: Lazy discovery on first unregistered GID lookup.

    This registry provides:
    - Dynamic project discovery from Asana workspace
    - O(1) name-to-GID mapping after discovery
    - ProcessType identification for pipeline projects
    - Lazy or eager discovery modes

    Example (lazy discovery - recommended):
        registry = get_workspace_registry()
        entity_type = await registry.lookup_or_discover_async(project_gid, client)

    Example (eager discovery):
        registry = get_workspace_registry()
        await registry.discover_async(client)
        gid = registry.get_by_name("Sales Pipeline")

    Example (ProcessType lookup):
        process_type = registry.get_process_type(project_gid)
    """

    _instance: ClassVar[WorkspaceProjectRegistry | None] = None

    # Instance attributes - declared for type checking
    _type_registry: ProjectTypeRegistry
    _name_to_gid: dict[str, str]  # Normalized lowercase name -> GID
    _gid_to_process_type: dict[str, Any]  # GID -> ProcessType (Any to avoid import)
    _discovered_workspace: str | None

    def __new__(cls) -> WorkspaceProjectRegistry:
        """Get or create singleton instance.

        Returns:
            The singleton WorkspaceProjectRegistry instance.
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._type_registry = get_registry()
            instance._name_to_gid = {}
            instance._gid_to_process_type = {}
            instance._discovered_workspace = None
            cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize instance attributes (only runs once due to singleton)."""
        # Attributes are set in __new__ to avoid re-initialization
        pass

    async def discover_async(self, client: AsanaClient) -> None:
        """Discover all projects in client's default workspace.

        Per FR-DISC-001: Fetches all workspace projects.
        Per FR-DISC-002: Populates name-to-GID mapping.
        Per FR-PIPE-001/002: Identifies and registers pipeline projects.

        Idempotent: repeated calls refresh the registry.
        Does NOT overwrite static PRIMARY_PROJECT_GID registrations.

        Args:
            client: AsanaClient with default_workspace_gid set.

        Raises:
            ValueError: If client.default_workspace_gid is not set.
        """
        workspace_gid = client.default_workspace_gid
        if not workspace_gid:
            raise ValueError(
                "Cannot discover workspace projects: client.default_workspace_gid is not set. "
                "Create client with workspace_gid parameter: AsanaClient(token=..., workspace_gid='...')"
            )

        start_time = time.monotonic()

        # Fetch all projects in workspace (non-archived)
        projects = await client.projects.list_async(
            workspace=workspace_gid,
            archived=False,
        ).collect()

        # Clear previous dynamic registrations (refresh)
        self._name_to_gid.clear()
        self._gid_to_process_type.clear()

        # Process discovered projects
        self._populate_from_projects(projects)

        # Mark discovery complete
        self._discovered_workspace = workspace_gid

        elapsed = time.monotonic() - start_time
        logger.info(
            "Workspace discovery complete",
            extra={
                "workspace_gid": workspace_gid,
                "projects_count": len(projects),
                "pipeline_projects": len(self._gid_to_process_type),
                "duration_seconds": round(elapsed, 3),
            },
        )

    def _populate_from_projects(self, projects: list[Any]) -> None:
        """Populate internal mappings from discovered projects.

        Uses two-pass matching for ProcessType identification:
        1. First pass: Exact matches (name.lower() == process_type.value)
        2. Second pass: Contains matches for remaining ProcessTypes

        This ensures "Onboarding" matches ProcessType.ONBOARDING before
        "Onboarding/Review Calls" can claim it via contains matching.

        Args:
            projects: List of Project objects from API.
        """
        from autom8_asana.models.business.detection import EntityType

        # Build name-to-GID mapping for all projects
        for project in projects:
            if not project.gid or not project.name:
                continue
            normalized_name = project.name.lower().strip()
            self._name_to_gid[normalized_name] = project.gid

        # Track which ProcessTypes have been matched
        matched_process_types: set[ProcessType] = set()

        # Pass 1: Exact matches only
        for project in projects:
            if not project.gid or not project.name:
                continue

            process_type = self._match_process_type_exact(project.name)
            if process_type is not None and process_type not in matched_process_types:
                self._register_pipeline_project(
                    project.gid, project.name, process_type, EntityType
                )
                matched_process_types.add(process_type)

        # Pass 2: Contains matches for unmatched ProcessTypes
        for project in projects:
            if not project.gid or not project.name:
                continue

            process_type = self._match_process_type_contains(project.name)
            if process_type is not None and process_type not in matched_process_types:
                self._register_pipeline_project(
                    project.gid, project.name, process_type, EntityType
                )
                matched_process_types.add(process_type)

    def _register_pipeline_project(
        self, gid: str, name: str, process_type: ProcessType, EntityType: type
    ) -> None:
        """Register a pipeline project with the registry.

        Args:
            gid: Project GID.
            name: Project name.
            process_type: Matched ProcessType.
            EntityType: EntityType enum class.
        """
        self._gid_to_process_type[gid] = process_type

        # Register with static registry if not already registered
        if not self._type_registry.is_registered(gid):
            self._type_registry.register(gid, EntityType.PROCESS)  # type: ignore[attr-defined]

            logger.debug(
                "Registered pipeline project",
                extra={
                    "project_gid": gid,
                    "project_name": name,
                    "process_type": process_type.value,
                },
            )

    def _match_process_type_exact(self, name: str) -> ProcessType | None:
        """Match project name to ProcessType using exact matching.

        Case-insensitive exact match: name.lower().strip() == process_type.value

        Args:
            name: Project name.

        Returns:
            ProcessType if name exactly matches a type value, None otherwise.
        """
        from autom8_asana.models.business.process import ProcessType

        name_lower = name.lower().strip()

        # All pipeline ProcessTypes (GENERIC excluded per TDD)
        pipeline_types = [
            ProcessType.SALES,
            ProcessType.OUTREACH,
            ProcessType.ONBOARDING,
            ProcessType.IMPLEMENTATION,
            ProcessType.RETENTION,
            ProcessType.REACTIVATION,
        ]

        for process_type in pipeline_types:
            if name_lower == process_type.value:
                return process_type

        return None

    def _match_process_type_contains(self, name: str) -> ProcessType | None:
        """Match project name to ProcessType using contains matching.

        Per ADR-0108: Case-insensitive contains matching.
        Per TDD Appendix A: First match wins, GENERIC is never matched.

        Matching order: SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION

        Args:
            name: Project name.

        Returns:
            ProcessType if name contains a type value, None otherwise.
        """
        from autom8_asana.models.business.process import ProcessType

        name_lower = name.lower()

        # Match order per TDD Appendix A
        match_order = [
            ProcessType.SALES,
            ProcessType.OUTREACH,
            ProcessType.ONBOARDING,
            ProcessType.IMPLEMENTATION,
            ProcessType.RETENTION,
            ProcessType.REACTIVATION,
        ]

        for process_type in match_order:
            if process_type.value in name_lower:
                return process_type

        return None

    async def lookup_or_discover_async(
        self,
        project_gid: str,
        client: AsanaClient,
    ) -> EntityType | None:
        """Look up entity type, triggering discovery if needed.

        Per ADR-0109: Lazy discovery on first unregistered GID.

        Args:
            project_gid: Asana project GID.
            client: AsanaClient for discovery if needed.

        Returns:
            EntityType if found in static or dynamic registry, None otherwise.
        """
        # Try static registry first (O(1))
        result = self._type_registry.lookup(project_gid)
        if result is not None:
            return result

        # Trigger discovery if not yet performed
        if self._discovered_workspace is None:
            await self.discover_async(client)
            # Retry lookup after discovery
            return self._type_registry.lookup(project_gid)

        # Already discovered, GID is truly unknown
        return None

    def lookup(self, project_gid: str) -> EntityType | None:
        """Sync lookup (static registry only, no discovery).

        Per FR-DET-002: Detection API unchanged.

        Args:
            project_gid: Asana project GID.

        Returns:
            EntityType if in static registry, None otherwise.
        """
        return self._type_registry.lookup(project_gid)

    def get_by_name(self, name: str) -> str | None:
        """Get project GID by name (O(1) after discovery).

        Per FR-DISC-002: Case-insensitive, whitespace-normalized.

        Args:
            name: Project name.

        Returns:
            Project GID if found, None otherwise.
        """
        normalized = name.lower().strip()
        gid = self._name_to_gid.get(normalized)

        if gid is not None:
            logger.debug(
                "Resolved project name to GID",
                extra={
                    "name": name,
                    "project_gid": gid,
                },
            )

        return gid

    def get_process_type(self, project_gid: str) -> ProcessType | None:
        """Get ProcessType for a pipeline project.

        Per FR-PIPE-003: Returns ProcessType that matched project name.

        Args:
            project_gid: Pipeline project GID.

        Returns:
            ProcessType if GID is a registered pipeline project, None otherwise.
        """
        return self._gid_to_process_type.get(project_gid)

    def is_discovered(self) -> bool:
        """Check if workspace discovery has been performed.

        Returns:
            True if discover_async() has been called, False otherwise.
        """
        return self._discovered_workspace is not None

    def get_all_projects(self) -> dict[str, str]:
        """Get all discovered projects.

        Returns:
            Dict mapping normalized project name -> GID.
        """
        return dict(self._name_to_gid)

    @classmethod
    def reset(cls) -> None:
        """Reset registry for testing.

        Per ADR-0093 pattern: Test isolation via explicit reset.
        """
        cls._instance = None
        logger.debug("WorkspaceProjectRegistry reset")


def get_workspace_registry() -> WorkspaceProjectRegistry:
    """Get the WorkspaceProjectRegistry singleton.

    Returns:
        The singleton WorkspaceProjectRegistry instance.
    """
    return WorkspaceProjectRegistry()
