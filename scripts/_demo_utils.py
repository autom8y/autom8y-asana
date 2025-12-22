"""Demo utilities for SDK demonstration suite.

Internal module providing shared utilities for demo scripts:
- UserAction enum and confirm() function
- NameResolver for name-to-GID resolution
- StateManager for entity state capture/restoration
- DemoLogger for structured logging
- Data structures for state tracking

Per TDD-SDKDEMO: Module-level implementation for SDK validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.task import Task
    from autom8_asana.persistence.models import PlannedOperation, ActionOperation


# ---------------------------------------------------------------------------
# User Interaction
# ---------------------------------------------------------------------------


class UserAction(Enum):
    """User response to confirmation prompt.

    Per TDD-SDKDEMO: Interactive confirmation for every mutation.

    Values:
        PROCEED: User pressed Enter to execute the operation
        SKIP: User pressed 's' to skip this operation
        QUIT: User pressed 'q' to quit and restore state
    """

    PROCEED = "proceed"
    SKIP = "skip"
    QUIT = "quit"


def confirm(
    message: str,
    step_info: str | None = None,
    show_preview: bool = True,
) -> UserAction:
    """Display preview and prompt for user confirmation.

    Per TDD-SDKDEMO: Interactive confirmation before every mutation.

    Args:
        message: Description of the operation to confirm.
        step_info: Optional context about the current step.
        show_preview: Whether to show the Enter/s/q prompt hint.

    Returns:
        UserAction indicating user's choice.

    Display Format:
        [step_info if provided]

        message

        [Enter] Proceed  [s] Skip  [q] Quit
        >
    """
    if step_info:
        print(f"\n{step_info}")
    print(f"\n{message}")
    if show_preview:
        print("\n[Enter] Proceed  [s] Skip  [q] Quit")

    while True:
        try:
            response = input("> ").strip().lower()
        except EOFError:
            # Handle non-interactive mode
            return UserAction.QUIT
        except KeyboardInterrupt:
            print("\n")
            return UserAction.QUIT

        if response == "" or response == "y":
            return UserAction.PROCEED
        elif response == "s":
            return UserAction.SKIP
        elif response == "q":
            return UserAction.QUIT
        print("Invalid input. Press Enter to proceed, 's' to skip, or 'q' to quit.")


def confirm_with_preview(
    operation_description: str,
    crud_ops: list[PlannedOperation],
    action_ops: list[ActionOperation],
) -> UserAction:
    """Display operation preview and prompt for user confirmation.

    Per TDD-SDKDEMO: Show CRUD and action operations before execution.

    Args:
        operation_description: Human-readable description of pending operation.
        crud_ops: CRUD operations from session.preview().
        action_ops: Action operations from session.preview().

    Returns:
        UserAction indicating user's choice.

    Display Format:
        --- {operation_description} ---

        CRUD Operations:
          CREATE Task(temp_1): {name: "...", notes: "..."}
          UPDATE Task(123456): {notes: "changed"}

        Action Operations:
          ADD_TAG on task 123456 -> tag 789012
          MOVE_TO_SECTION on task 123456 -> section 345678

        Press Enter to execute, 's' to skip, 'q' to quit:
    """
    print(f"\n--- {operation_description} ---")

    if crud_ops:
        print("\nCRUD Operations:")
        for op in crud_ops:
            entity_type = type(op.entity).__name__
            entity_gid = op.entity.gid
            # Summarize payload (just keys for brevity)
            payload_summary = ", ".join(op.payload.keys()) if op.payload else "(empty)"
            print(
                f"  {op.operation.value.upper()} {entity_type}({entity_gid}): {{{payload_summary}}}"
            )

    if action_ops:
        print("\nAction Operations:")
        for action in action_ops:
            task_gid = action.task.gid
            target = action.target_gid or "(no target)"
            print(f"  {action.action.value.upper()} on task {task_gid} -> {target}")

    if not crud_ops and not action_ops:
        print("\n(No pending operations)")

    print("\n[Enter] Proceed  [s] Skip  [q] Quit")

    while True:
        try:
            response = input("> ").strip().lower()
        except EOFError:
            return UserAction.QUIT
        except KeyboardInterrupt:
            print("\n")
            return UserAction.QUIT

        if response == "" or response == "y":
            return UserAction.PROCEED
        elif response == "s":
            return UserAction.SKIP
        elif response == "q":
            return UserAction.QUIT
        print("Invalid input. Press Enter to proceed, 's' to skip, or 'q' to quit.")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ResolutionError(Exception):
    """Raised when name resolution fails.

    Attributes:
        resource_type: Type of resource (tag, user, section, etc.)
        name: The name that could not be resolved
    """

    def __init__(self, resource_type: str, name: str) -> None:
        self.resource_type = resource_type
        self.name = name
        super().__init__(f"Could not resolve {resource_type} '{name}'")


# ---------------------------------------------------------------------------
# Data Structures (Per ADR-DEMO-001)
# ---------------------------------------------------------------------------


@dataclass
class EntityState:
    """Captured scalar/custom field state of an entity.

    Per ADR-DEMO-001: Shallow copy with GID references for memory efficiency.

    Attributes:
        gid: The entity's GID.
        notes: Plain text notes/description.
        html_notes: HTML-formatted notes.
        name: Entity name.
        completed: Completion status (for tasks).
        due_on: Due date (YYYY-MM-DD format).
        custom_fields: Dict of {field_gid: value}.
    """

    gid: str
    notes: str | None = None
    html_notes: str | None = None
    name: str | None = None
    completed: bool | None = None
    due_on: str | None = None
    custom_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class MembershipState:
    """Task's membership in a project/section.

    Attributes:
        project_gid: The project GID.
        section_gid: The section GID within the project (optional).
    """

    project_gid: str
    section_gid: str | None = None


@dataclass
class TaskSnapshot:
    """Complete snapshot of a task for restoration.

    Per ADR-DEMO-001: Captures all restorable state.

    Attributes:
        entity_state: Scalar and custom field state.
        tag_gids: List of tag GIDs attached to the task.
        parent_gid: Parent task GID (for subtasks).
        memberships: List of project/section memberships.
        dependency_gids: List of task GIDs this task depends on.
        dependent_gids: List of task GIDs that depend on this task.
    """

    entity_state: EntityState
    tag_gids: list[str] = field(default_factory=list)
    parent_gid: str | None = None
    memberships: list[MembershipState] = field(default_factory=list)
    dependency_gids: list[str] = field(default_factory=list)
    dependent_gids: list[str] = field(default_factory=list)


@dataclass
class SubtaskState:
    """Position state for a subtask within its parent.

    Per Demo 9 requirements: Captures subtask position for restoration.

    Attributes:
        gid: The subtask's GID.
        parent_gid: Parent task GID.
        sibling_gids: List of sibling GIDs in order.
        position_index: Index position within siblings (0-based).
        insert_after_gid: GID of sibling before this task (None if first).
        insert_before_gid: GID of sibling after this task (None if last).
    """

    gid: str
    parent_gid: str | None
    sibling_gids: list[str] = field(default_factory=list)
    position_index: int = 0
    insert_after_gid: str | None = None
    insert_before_gid: str | None = None


@dataclass
class RestoreResult:
    """Outcome of a restoration attempt.

    Attributes:
        entity_gid: The GID of the entity being restored.
        success: Whether restoration succeeded.
        fields_restored: List of field names successfully restored.
        fields_failed: List of field names that failed to restore.
        error: Error message if restoration failed.
    """

    entity_gid: str
    success: bool
    fields_restored: list[str] = field(default_factory=list)
    fields_failed: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class DemoError:
    """Structured error with recovery guidance.

    Attributes:
        category: Error category (e.g., "tag_operation", "custom_field").
        operation: The operation that failed (e.g., "add_tag", "set_field").
        entity_gid: The GID of the entity involved.
        message: Human-readable error message.
        recovery_hint: Suggestion for manual recovery.
    """

    category: str
    operation: str
    entity_gid: str
    message: str
    recovery_hint: str | None = None


# ---------------------------------------------------------------------------
# NameResolver (Per ADR-DEMO-002)
# ---------------------------------------------------------------------------


class NameResolver:
    """Resolves human-readable names to Asana GIDs with lazy caching.

    Per ADR-DEMO-002: Lazy-loading with session cache for minimal startup latency.

    All lookups are case-insensitive.

    Attributes:
        client: SDK client for API calls.
        workspace_gid: Workspace for tag/user lookups.
    """

    def __init__(self, client: AsanaClient, workspace_gid: str) -> None:
        """Initialize resolver.

        Args:
            client: SDK client for API calls.
            workspace_gid: Workspace for tag/user lookups.
        """
        self._client = client
        self._workspace_gid = workspace_gid

        # Caches (lazily populated)
        self._tag_cache: dict[str, str] | None = None  # name.lower() -> gid
        self._user_cache: dict[str, str] | None = None  # name.lower() -> gid
        self._section_cache: dict[
            str, dict[str, str]
        ] = {}  # project_gid -> {name.lower() -> gid}
        self._project_cache: dict[str, str] | None = None  # name.lower() -> gid
        self._enum_cache: dict[
            str, dict[str, str]
        ] = {}  # cf_gid -> {option_name.lower() -> gid}

    async def resolve_tag(self, name: str) -> str | None:
        """Resolve tag name to GID. Case-insensitive.

        Args:
            name: Tag name to resolve.

        Returns:
            Tag GID if found, None otherwise.
        """
        if self._tag_cache is None:
            await self._load_tags()

        return self._tag_cache.get(name.lower()) if self._tag_cache else None

    async def resolve_user(self, display_name: str) -> str | None:
        """Resolve user display name to GID. Case-insensitive.

        Args:
            display_name: User's display name.

        Returns:
            User GID if found, None otherwise.
        """
        if self._user_cache is None:
            await self._load_users()

        return self._user_cache.get(display_name.lower()) if self._user_cache else None

    async def resolve_section(self, project_gid: str, name: str) -> str | None:
        """Resolve section name within a project. Case-insensitive.

        Args:
            project_gid: Project GID to search within.
            name: Section name to resolve.

        Returns:
            Section GID if found, None otherwise.
        """
        if project_gid not in self._section_cache:
            await self._load_sections(project_gid)

        sections = self._section_cache.get(project_gid, {})
        return sections.get(name.lower())

    async def resolve_project(self, name: str) -> str | None:
        """Resolve project name to GID. Case-insensitive.

        Args:
            name: Project name to resolve.

        Returns:
            Project GID if found, None otherwise.
        """
        if self._project_cache is None:
            await self._load_projects()

        return self._project_cache.get(name.lower()) if self._project_cache else None

    async def resolve_enum_option(
        self,
        custom_field_gid: str,
        option_name: str,
    ) -> str | None:
        """Resolve enum option name to GID within a custom field.

        Args:
            custom_field_gid: GID of the custom field.
            option_name: Name of the enum option.

        Returns:
            Option GID if found, None otherwise.
        """
        if custom_field_gid not in self._enum_cache:
            await self._load_enum_options(custom_field_gid)

        options = self._enum_cache.get(custom_field_gid, {})
        return options.get(option_name.lower())

    def resolve_enum_option_from_task(
        self,
        task_custom_fields: list[dict[str, Any]],
        field_gid: str,
        option_name: str,
    ) -> str | None:
        """Resolve enum option name to GID from task's custom field data.

        This avoids an API call by using the enum_options already on the task.

        Args:
            task_custom_fields: List of custom field dicts from task.custom_fields.
            field_gid: GID of the custom field.
            option_name: Name of the enum option.

        Returns:
            Option GID if found, None otherwise.
        """
        for field in task_custom_fields:
            if field.get("gid") == field_gid:
                options = field.get("enum_options") or []
                for opt in options:
                    if opt.get("name", "").lower() == option_name.lower():
                        return opt.get("gid")
        return None

    def get_all_users(self) -> dict[str, str]:
        """Get cached user name->GID mapping.

        Returns:
            Dict of {name.lower(): gid} or empty dict if not loaded.
        """
        return self._user_cache or {}

    async def get_all_sections(self, project_gid: str) -> dict[str, str]:
        """Get all sections in a project as name->GID mapping.

        Args:
            project_gid: Project GID to get sections for.

        Returns:
            Dict of {name.lower(): gid} for all sections in the project.
        """
        if project_gid not in self._section_cache:
            await self._load_sections(project_gid)

        return self._section_cache.get(project_gid, {})

    async def get_all_projects(self) -> dict[str, str]:
        """Get all projects as name->GID mapping.

        Returns:
            Dict of {name.lower(): gid} for all projects.
        """
        if self._project_cache is None:
            await self._load_projects()

        return self._project_cache or {}

    def clear_cache(self) -> None:
        """Clear all cached lookups. Useful for testing."""
        self._tag_cache = None
        self._user_cache = None
        self._section_cache = {}
        self._project_cache = None
        self._enum_cache = {}

    # --- Internal Loading Methods ---

    async def _load_tags(self) -> None:
        """Load all tags from workspace into cache."""
        self._tag_cache = {}
        try:
            iterator = self._client.tags.list_for_workspace_async(
                self._workspace_gid,
                opt_fields=["name"],
            )
            async for tag in iterator:
                if tag.name:
                    self._tag_cache[tag.name.lower()] = tag.gid
        except Exception as e:
            print(f"[WARN] Failed to load tags: {e}")
            self._tag_cache = {}

    async def _load_users(self) -> None:
        """Load all users from workspace into cache."""
        self._user_cache = {}
        try:
            iterator = self._client.users.list_for_workspace_async(
                self._workspace_gid,
                opt_fields=["name"],
            )
            async for user in iterator:
                if user.name:
                    self._user_cache[user.name.lower()] = user.gid
        except Exception as e:
            print(f"[WARN] Failed to load users: {e}")
            self._user_cache = {}

    async def _load_sections(self, project_gid: str) -> None:
        """Load all sections from project into cache."""
        self._section_cache[project_gid] = {}
        try:
            iterator = self._client.sections.list_for_project_async(
                project_gid,
                opt_fields=["name"],
            )
            async for section in iterator:
                if section.name:
                    self._section_cache[project_gid][section.name.lower()] = section.gid
        except Exception as e:
            print(f"[WARN] Failed to load sections for project {project_gid}: {e}")
            self._section_cache[project_gid] = {}

    async def _load_projects(self) -> None:
        """Load all projects from workspace into cache."""
        self._project_cache = {}
        try:
            iterator = self._client.projects.list_for_workspace_async(
                self._workspace_gid,
                opt_fields=["name"],
            )
            async for project in iterator:
                if project.name:
                    self._project_cache[project.name.lower()] = project.gid
        except Exception as e:
            print(f"[WARN] Failed to load projects: {e}")
            self._project_cache = {}

    async def _load_enum_options(self, custom_field_gid: str) -> None:
        """Load enum options for a custom field into cache."""
        self._enum_cache[custom_field_gid] = {}
        try:
            cf = await self._client.custom_fields.get_async(
                custom_field_gid,
                opt_fields=["enum_options", "enum_options.name"],
            )
            if hasattr(cf, "enum_options") and cf.enum_options:
                for opt in cf.enum_options:
                    if isinstance(opt, dict) and opt.get("name"):
                        self._enum_cache[custom_field_gid][opt["name"].lower()] = opt[
                            "gid"
                        ]
        except Exception as e:
            print(
                f"[WARN] Failed to load enum options for field {custom_field_gid}: {e}"
            )
            self._enum_cache[custom_field_gid] = {}


# ---------------------------------------------------------------------------
# StateManager (Per ADR-DEMO-001)
# ---------------------------------------------------------------------------


class StateManager:
    """Manages entity state capture and restoration.

    Per ADR-DEMO-001: Captures task state for post-demo restoration.

    Attributes:
        client: SDK client for restoration operations.
    """

    def __init__(self, client: AsanaClient) -> None:
        """Initialize with SDK client for restoration operations.

        Args:
            client: SDK client for API operations.
        """
        self._client = client
        self._initial_states: dict[str, TaskSnapshot] = {}
        self._current_states: dict[str, TaskSnapshot] = {}

    async def capture(self, task: Task) -> TaskSnapshot:
        """Capture current state of a task.

        Per ADR-DEMO-001: Shallow copy with GID references.

        Captures:
        - Scalar fields (notes, name, completed, due_on)
        - Custom field values (keyed by GID)
        - Tag GIDs
        - Parent GID
        - Membership (project/section) GIDs
        - Dependency/dependent GIDs

        Args:
            task: Task to capture state from.

        Returns:
            TaskSnapshot containing the task's current state.
        """
        # Capture scalar fields
        entity_state = EntityState(
            gid=task.gid,
            notes=task.notes,
            html_notes=task.html_notes,
            name=task.name,
            completed=task.completed,
            due_on=task.due_on,
        )

        # Capture custom fields
        if task.custom_fields:
            for cf in task.custom_fields:
                cf_gid = cf.get("gid")
                if cf_gid:
                    # Store the display_value or actual value depending on type
                    cf_type = cf.get("type") or cf.get("resource_subtype")
                    if cf_type == "enum":
                        # Store enum option GID
                        enum_value = cf.get("enum_value")
                        entity_state.custom_fields[cf_gid] = (
                            enum_value.get("gid") if enum_value else None
                        )
                    elif cf_type == "multi_enum":
                        # Store list of enum option GIDs
                        enum_values = cf.get("multi_enum_values") or []
                        entity_state.custom_fields[cf_gid] = [
                            ev.get("gid") for ev in enum_values if ev.get("gid")
                        ]
                    elif cf_type == "people":
                        # Store list of user GIDs
                        people = cf.get("people_value") or []
                        entity_state.custom_fields[cf_gid] = [
                            p.get("gid") for p in people if p.get("gid")
                        ]
                    elif cf_type == "number":
                        entity_state.custom_fields[cf_gid] = cf.get("number_value")
                    elif cf_type == "text":
                        entity_state.custom_fields[cf_gid] = cf.get("text_value")
                    else:
                        # Default: store display_value
                        entity_state.custom_fields[cf_gid] = cf.get("display_value")

        # Capture tag GIDs
        tag_gids: list[str] = []
        if task.tags:
            tag_gids = [t.gid for t in task.tags if t.gid]

        # Capture parent GID
        parent_gid: str | None = None
        if task.parent:
            parent_gid = task.parent.gid

        # Capture memberships
        memberships: list[MembershipState] = []
        if task.memberships:
            for m in task.memberships:
                project = m.get("project", {})
                section = m.get("section", {})
                if project.get("gid"):
                    memberships.append(
                        MembershipState(
                            project_gid=project["gid"],
                            section_gid=section.get("gid") if section else None,
                        )
                    )

        # Note: Dependency/dependent GIDs would require additional API calls
        # For now, we return empty lists (can be populated via separate fetch)
        return TaskSnapshot(
            entity_state=entity_state,
            tag_gids=tag_gids,
            parent_gid=parent_gid,
            memberships=memberships,
            dependency_gids=[],
            dependent_gids=[],
        )

    def store_initial(self, gid: str, snapshot: TaskSnapshot) -> None:
        """Store snapshot as initial state for later restoration.

        Args:
            gid: Task GID.
            snapshot: Snapshot to store as initial state.
        """
        self._initial_states[gid] = snapshot

    def store_current(self, gid: str, snapshot: TaskSnapshot) -> None:
        """Update current state after successful operation.

        Args:
            gid: Task GID.
            snapshot: Snapshot to store as current state.
        """
        self._current_states[gid] = snapshot

    def get_initial(self, gid: str) -> TaskSnapshot | None:
        """Get initial state snapshot.

        Args:
            gid: Task GID.

        Returns:
            Initial TaskSnapshot if stored, None otherwise.
        """
        return self._initial_states.get(gid)

    def get_current(self, gid: str) -> TaskSnapshot | None:
        """Get current state snapshot.

        Args:
            gid: Task GID.

        Returns:
            Current TaskSnapshot if stored, None otherwise.
        """
        return self._current_states.get(gid)

    def has_changes(self, gid: str) -> bool:
        """Check if entity has changed from initial state.

        Args:
            gid: Task GID.

        Returns:
            True if current differs from initial, False otherwise.
        """
        initial = self.get_initial(gid)
        current = self.get_current(gid)
        if initial is None or current is None:
            return False
        # Simple comparison - could be more sophisticated
        return initial != current

    def get_tracked_gids(self) -> list[str]:
        """Get list of all tracked entity GIDs.

        Returns:
            List of GIDs that have initial state stored.
        """
        return list(self._initial_states.keys())


# ---------------------------------------------------------------------------
# DemoLogger
# ---------------------------------------------------------------------------


class DemoLogger:
    """Structured logging for demo operations.

    Provides consistent logging format for demo scripts.

    Attributes:
        verbose: Whether to log detailed operation info.
    """

    def __init__(self, verbose: bool = False) -> None:
        """Initialize logger.

        Args:
            verbose: If True, log detailed operation info.
        """
        self._verbose = verbose

    @property
    def verbose(self) -> bool:
        """Whether verbose logging is enabled."""
        return self._verbose

    def category_start(self, name: str) -> None:
        """Log start of demo category.

        Args:
            name: Category name.
        """
        print(f"\n{'=' * 60}")
        print(f"[DEMO] Starting: {name}")
        print(f"{'=' * 60}")

    def category_end(self, name: str, success: bool) -> None:
        """Log end of demo category.

        Args:
            name: Category name.
            success: Whether category completed successfully.
        """
        status = "COMPLETED" if success else "FAILED"
        print(f"\n[DEMO] {name}: {status}")
        print(f"{'-' * 60}")

    def operation(self, op_type: str, entity_gid: str, details: dict[str, Any]) -> None:
        """Log operation execution.

        Args:
            op_type: Type of operation (e.g., "add_tag", "set_field").
            entity_gid: GID of the entity being operated on.
            details: Additional details about the operation.
        """
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        print(f"[OP] {op_type}: entity={entity_gid}, {detail_str}")

    def resolution(self, resource_type: str, name: str, gid: str | None) -> None:
        """Log name resolution result.

        Args:
            resource_type: Type of resource (tag, user, section, etc.).
            name: Name that was resolved.
            gid: Resolved GID or None if not found.
        """
        if gid:
            print(f'[RESOLVE] {resource_type} "{name}" -> {gid}')
        else:
            print(f'[RESOLVE] {resource_type} "{name}" -> NOT FOUND')

    def error(self, error: DemoError) -> None:
        """Log error with recovery hint.

        Args:
            error: DemoError instance.
        """
        print(
            f"[ERROR] {error.operation} failed on {error.entity_gid}: {error.message}"
        )
        if error.recovery_hint:
            print(f"        Recovery: {error.recovery_hint}")

    def state_capture(self, gid: str, snapshot: TaskSnapshot) -> None:
        """Log state capture (verbose only).

        Args:
            gid: Task GID.
            snapshot: Captured snapshot.
        """
        if self._verbose:
            print(f"[STATE] Captured state for {gid}")
            print(f"        tags: {snapshot.tag_gids}")
            print(f"        parent: {snapshot.parent_gid}")

    def state_restore(self, result: RestoreResult) -> None:
        """Log restoration result.

        Args:
            result: RestoreResult instance.
        """
        status = "SUCCESS" if result.success else "FAILED"
        print(f"[RESTORE] {result.entity_gid}: {status}")
        if result.fields_restored:
            print(f"          Restored: {', '.join(result.fields_restored)}")
        if result.fields_failed:
            print(f"          Failed: {', '.join(result.fields_failed)}")
        if result.error:
            print(f"          Error: {result.error}")

    def info(self, message: str) -> None:
        """Log informational message.

        Args:
            message: Message to log.
        """
        print(f"[INFO] {message}")

    def success(self, message: str) -> None:
        """Log success message.

        Args:
            message: Message to log.
        """
        print(f"[SUCCESS] {message}")

    def warn(self, message: str) -> None:
        """Log warning message.

        Args:
            message: Message to log.
        """
        print(f"[WARN] {message}")

    def debug(self, message: str) -> None:
        """Log debug message (verbose only).

        Args:
            message: Message to log.
        """
        if self._verbose:
            print(f"[DEBUG] {message}")


# ---------------------------------------------------------------------------
# Custom Field Helpers
# ---------------------------------------------------------------------------


@dataclass
class CustomFieldInfo:
    """Information about a custom field on a task.

    Attributes:
        gid: Custom field GID.
        name: Custom field name.
        field_type: Field type (text, number, enum, multi_enum, people).
        current_value: Current value (type depends on field_type).
        display_value: Human-readable display value.
        enum_options: List of {gid, name} dicts for enum/multi_enum fields.
    """

    gid: str
    name: str
    field_type: str
    current_value: Any
    display_value: str | None
    enum_options: list[dict[str, str]] = field(default_factory=list)


def find_custom_field_by_type(
    custom_fields: list[dict[str, Any]] | None,
    field_type: str,
) -> CustomFieldInfo | None:
    """Find the first custom field of a given type on a task.

    Args:
        custom_fields: List of custom field dicts from task.custom_fields.
        field_type: One of 'text', 'number', 'enum', 'multi_enum', 'people'.

    Returns:
        CustomFieldInfo if found, None otherwise.
    """
    if not custom_fields:
        return None

    for cf in custom_fields:
        cf_type = cf.get("type") or cf.get("resource_subtype")
        if cf_type == field_type:
            # Extract current value based on type
            current_value: Any = None
            if field_type == "text":
                current_value = cf.get("text_value")
            elif field_type == "number":
                current_value = cf.get("number_value")
            elif field_type == "enum":
                enum_val = cf.get("enum_value")
                current_value = enum_val.get("gid") if enum_val else None
            elif field_type == "multi_enum":
                multi_vals = cf.get("multi_enum_values") or []
                current_value = [v.get("gid") for v in multi_vals if v.get("gid")]
            elif field_type == "people":
                people_vals = cf.get("people_value") or []
                current_value = [p.get("gid") for p in people_vals if p.get("gid")]

            # Extract enum options if available
            enum_options = []
            if field_type in ("enum", "multi_enum"):
                raw_opts = cf.get("enum_options") or []
                enum_options = [
                    {"gid": opt.get("gid"), "name": opt.get("name")}
                    for opt in raw_opts
                    if opt.get("gid") and opt.get("name")
                ]

            return CustomFieldInfo(
                gid=cf.get("gid", ""),
                name=cf.get("name", ""),
                field_type=field_type,
                current_value=current_value,
                display_value=cf.get("display_value"),
                enum_options=enum_options,
            )

    return None


def get_enum_option_by_index(
    field_info: CustomFieldInfo,
    index: int,
    exclude_current: bool = True,
) -> tuple[str, str] | None:
    """Get an enum option by index, optionally excluding current value.

    Args:
        field_info: CustomFieldInfo with enum_options populated.
        index: Index into the options list (after filtering).
        exclude_current: If True, skip options matching current_value.

    Returns:
        Tuple of (option_gid, option_name) or None if not found.
    """
    options = field_info.enum_options
    if not options:
        return None

    # Filter out current value if requested
    if exclude_current and field_info.current_value:
        if field_info.field_type == "enum":
            options = [opt for opt in options if opt["gid"] != field_info.current_value]
        elif field_info.field_type == "multi_enum":
            current_gids = set(field_info.current_value)
            options = [opt for opt in options if opt["gid"] not in current_gids]

    if index < 0 or index >= len(options):
        return None

    opt = options[index]
    return (opt["gid"], opt["name"])
