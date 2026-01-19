"""Task model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
Complex nested structures (memberships, custom_fields, external) remain as dicts.
Per TDD-TRIAGE-FIXES: Snapshot-based detection of direct custom field modifications.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger
from pydantic import Field, PrivateAttr, model_validator

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class Task(AsanaResource):
    """Asana Task resource model.

    Uses NameGid for typed resource references (assignee, projects, etc.).
    Custom fields and complex nested structures remain as dicts.

    Unknown fields from API responses are silently ignored (per ADR-0005).

    Example:
        >>> from autom8_asana.models import Task
        >>> task = Task.model_validate(api_response)
        >>> if task.assignee:
        ...     print(f"Assigned to {task.assignee.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="task")

    # Basic task fields
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status fields
    completed: bool | None = None
    completed_at: str | None = None
    completed_by: NameGid | None = None  # Changed from dict

    # Due dates
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    due_at: str | None = Field(default=None, description="Due datetime (ISO 8601)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    start_at: str | None = Field(default=None, description="Start datetime (ISO 8601)")

    # Relationships - typed with NameGid
    assignee: NameGid | None = None  # Changed from dict
    assignee_section: NameGid | None = None  # Changed from dict
    assignee_status: str | None = Field(
        default=None,
        description="Scheduling status (inbox, today, upcoming, later)",
    )
    projects: list[NameGid] | None = None  # Changed from list[dict]
    parent: NameGid | None = None  # Changed from dict
    workspace: NameGid | None = None  # Changed from dict
    memberships: list[dict[str, Any]] | None = None  # Keep as dict (complex structure)
    followers: list[NameGid] | None = None  # Changed from list[dict]
    tags: list[NameGid] | None = None  # Changed from list[dict]

    # Hierarchy and dependencies
    num_subtasks: int | None = None
    num_hearts: int | None = Field(
        default=None, description="Deprecated: use num_likes"
    )
    num_likes: int | None = None
    is_rendered_as_separator: bool | None = None

    # Custom fields - remain as dict (complex structure)
    custom_fields: list[dict[str, Any]] | None = None

    # Metadata
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )
    modified_at: str | None = Field(
        default=None, description="Modified datetime (ISO 8601)"
    )
    created_by: NameGid | None = None  # Changed from dict

    # Approval fields
    approval_status: str | None = Field(
        default=None,
        description="Approval status (pending, approved, rejected, changes_requested)",
    )

    # External data - remains as dict (arbitrary structure)
    external: dict[str, Any] | None = Field(
        default=None,
        description="External data (id and data fields for integrations)",
    )

    # Visibility and access
    resource_subtype: str | None = Field(
        default=None,
        description="Subtype (default_task, milestone, section, approval)",
    )

    # Permalink
    permalink_url: str | None = None

    # Liked status
    liked: bool | None = None
    hearted: bool | None = Field(default=None, description="Deprecated: use liked")
    hearts: list[dict[str, Any]] | None = Field(
        default=None,
        description="Deprecated: use likes",
    )
    likes: list[dict[str, Any]] | None = (
        None  # Keep as dict (user refs with extra data)
    )

    # Actual time tracking
    actual_time_minutes: float | None = None

    # Private accessor instance (not serialized)
    _custom_fields_accessor: CustomFieldAccessor | None = PrivateAttr(default=None)
    # Private client reference for save/refresh operations (not serialized)
    _client: Any = PrivateAttr(default=None)
    # Per TDD-TRIAGE-FIXES: Snapshot of original custom_fields for direct modification detection
    _original_custom_fields: list[dict[str, Any]] | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _capture_custom_fields_snapshot(self) -> Task:
        """Capture snapshot of custom_fields at initialization.

        Per TDD-TRIAGE-FIXES/ADR-0067: Enable detection of direct modifications.
        """
        if self.custom_fields is not None:
            self._original_custom_fields = copy.deepcopy(self.custom_fields)
        return self

    def _has_direct_custom_field_changes(self) -> bool:
        """Check if custom_fields was modified directly (not via accessor).

        Per TDD-TRIAGE-FIXES: Detect direct list mutations.

        Returns:
            True if custom_fields differs from original snapshot.
        """
        if self._original_custom_fields is None:
            # No snapshot means no custom_fields at init
            return self.custom_fields is not None and len(self.custom_fields) > 0

        if self.custom_fields is None:
            # Had custom_fields, now None
            return True

        # Compare current to snapshot
        return self.custom_fields != self._original_custom_fields

    def _extract_field_value(self, field: dict[str, Any]) -> Any:
        """Extract the appropriate value from a custom field dict.

        Per TDD-TRIAGE-FIXES: Convert direct modifications to API format.

        Args:
            field: Custom field dict from Asana API.

        Returns:
            Value suitable for API update payload.
        """
        # Check each value type in order of specificity
        if "text_value" in field and field["text_value"] is not None:
            return field["text_value"]
        if "number_value" in field and field["number_value"] is not None:
            return field["number_value"]
        if "enum_value" in field and field["enum_value"]:
            # Enum: extract GID
            return field["enum_value"].get("gid")
        if "multi_enum_value" in field and field["multi_enum_value"]:
            # Multi-enum: extract list of GIDs
            return [v.get("gid") for v in field["multi_enum_value"] if v.get("gid")]
        if "people_value" in field and field["people_value"]:
            # People: extract list of GIDs
            return [v.get("gid") for v in field["people_value"] if v.get("gid")]
        if "date_value" in field and field["date_value"]:
            return field["date_value"]
        # Default: None (field cleared)
        return None

    def _convert_direct_changes_to_api(self) -> dict[str, Any]:
        """Convert direct custom_fields modifications to API format.

        Per TDD-TRIAGE-FIXES: Convert direct modifications to {gid: value} format.

        Returns:
            Dict of {field_gid: value} for modified fields.
        """
        if self.custom_fields is None:
            return {}

        # Build lookup of original values by GID
        original_by_gid: dict[str, dict[str, Any]] = {}
        if self._original_custom_fields:
            for field in self._original_custom_fields:
                gid = field.get("gid")
                if gid:
                    original_by_gid[gid] = field

        # Find changed fields
        result: dict[str, Any] = {}
        for field in self.custom_fields:
            gid = field.get("gid")
            if not gid:
                continue

            original = original_by_gid.get(gid)
            if original is None or field != original:
                # Field is new or changed - extract value
                value = self._extract_field_value(field)
                result[gid] = value

        return result

    def _get_or_create_accessor(self) -> CustomFieldAccessor:
        """Internal: Get or create accessor instance.

        Per TDD-TRIAGE-FIXES: Uses strict=False to maintain backward compatibility
        with existing code that sets unknown custom fields (e.g., business models).

        Returns:
            CustomFieldAccessor instance (cached for this task).
        """
        if self._custom_fields_accessor is None:
            self._custom_fields_accessor = CustomFieldAccessor(
                self.custom_fields, strict=False
            )
        return self._custom_fields_accessor

    def custom_fields_editor(self) -> CustomFieldAccessor:
        """Get custom fields editor for reading and writing field values.

        Returns a CustomFieldAccessor that provides set/get/remove methods
        with automatic name->GID resolution. The accessor tracks modifications
        for change detection.

        This is the preferred method for accessing custom fields.

        Example:
            editor = task.custom_fields_editor()
            editor.set("Priority", "High")
            value = editor.get("Status")

        Returns:
            CustomFieldAccessor instance (cached for this task).
        """
        return self._get_or_create_accessor()

    def get_custom_fields(self) -> CustomFieldAccessor:
        """Get custom fields accessor for fluent API.

        .. deprecated::
            Use :meth:`custom_fields_editor` instead.

        Returns a CustomFieldAccessor that provides set/get/remove methods
        with automatic name->GID resolution. The accessor tracks modifications
        for change detection.

        Example:
            accessor = task.get_custom_fields()
            accessor.set("Priority", "High")
            value = accessor.get("Status")

        Returns:
            CustomFieldAccessor instance (cached for this task).
        """
        import warnings

        warnings.warn(
            "get_custom_fields() is deprecated. Use custom_fields_editor() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._get_or_create_accessor()

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to include custom field modifications.

        If the custom fields accessor has pending changes, the serialized
        output will use the accessor's to_api_dict() format instead of the
        original custom_fields data. Per ADR-0056, this produces the dict
        format expected by Asana's API: {"gid": value} not [{gid, value}].

        Per TDD-TRIAGE-FIXES/ADR-0067: Also detect and merge direct modifications
        to custom_fields list. Accessor changes take precedence.

        Args:
            **kwargs: Arguments passed to parent model_dump().

        Returns:
            Dict representation of the task.
        """
        data = super().model_dump(**kwargs)

        # Check for accessor changes
        accessor_changes = (
            self._custom_fields_accessor is not None
            and self._custom_fields_accessor.has_changes()
        )

        # Check for direct modifications
        direct_changes = self._has_direct_custom_field_changes()

        if accessor_changes and direct_changes:
            # Both types of changes - accessor takes precedence
            # Log warning for user awareness
            logger.warning(
                "Task %s has both accessor and direct custom_field modifications. "
                "Accessor changes take precedence.",
                self.gid,
            )
            # accessor is not None when accessor_changes is True
            assert self._custom_fields_accessor is not None
            data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
        elif accessor_changes:
            # Only accessor changes
            # accessor is not None when accessor_changes is True
            assert self._custom_fields_accessor is not None
            data["custom_fields"] = self._custom_fields_accessor.to_api_dict()
        elif direct_changes:
            # Only direct changes - convert to API format
            data["custom_fields"] = self._convert_direct_changes_to_api()

        return data

    async def save_async(self) -> Task:
        """Save changes to this task using implicit SaveSession (async).

        This method creates a SaveSession internally to persist changes
        (field updates, custom field modifications) back to Asana.

        Returns:
            This task instance (updated in-place with API response)

        Raises:
            ValueError: If task has no client reference (created outside client.tasks)
            SaveSessionError: If commit fails. Contains full SaveResult for inspection.
            APIError: If Asana API returns error

        Example:
            >>> task = await client.tasks.get(task_gid)
            >>> task.name = "Updated Name"
            >>> await task.save_async()  # Changes persisted

        Example showing error handling with full failure details:
            >>> try:
            ...     await task.save_async()
            ... except SaveSessionError as e:
            ...     for failed_op in e.result.failed:
            ...         print(f"Failed: {failed_op.error}")
        """
        if self._client is None:
            raise ValueError(
                "Cannot save task without client reference. "
                "Task must be obtained via client.tasks.get() or similar."
            )

        from autom8_asana.persistence.exceptions import SaveSessionError
        from autom8_asana.persistence.session import SaveSession

        async with SaveSession(self._client) as session:
            session.track(self)
            result = await session.commit_async()

            if not result.success:
                raise SaveSessionError(result)

            return self

    def save(self) -> Task:
        """Save changes to this task using implicit SaveSession (sync).

        Synchronous wrapper around save_async().
        See save_async() docstring for full documentation.
        """
        from autom8_asana.transport.sync import sync_wrapper

        return sync_wrapper("save_async")(self.save_async)()

    async def refresh_async(self) -> Task:
        """Reload this task from Asana API, discarding local changes (async).

        Fetches the latest task state from Asana and updates this instance
        in-place. All local changes are discarded (you can still access the
        original task.gid to identify it).

        Returns:
            This task instance (updated with fresh API data)

        Raises:
            ValueError: If task has no client reference
            APIError: If Asana API returns error

        Example:
            >>> task = await client.tasks.get(task_gid)
            >>> task.name = "Locally changed"
            >>> await task.refresh_async()  # Name reverted to API value
        """
        if self._client is None:
            raise ValueError(
                "Cannot refresh task without client reference. "
                "Task must be obtained via client.tasks.get() or similar."
            )

        # Fetch fresh copy from API
        updated = await self._client.tasks.get_async(self.gid)

        # Update all fields from fresh copy
        for field_name in self.__fields_set__:
            if hasattr(updated, field_name):
                setattr(self, field_name, getattr(updated, field_name))

        # Clear custom field modifications
        if self._custom_fields_accessor is not None:
            self._custom_fields_accessor._modifications.clear()

        return self

    def refresh(self) -> Task:
        """Reload this task from Asana API (sync).

        Synchronous wrapper around refresh_async().
        See refresh_async() docstring for full documentation.
        """
        from autom8_asana.transport.sync import sync_wrapper

        return sync_wrapper("refresh_async")(self.refresh_async)()

    def reset_custom_field_tracking(self) -> None:
        """Reset custom field tracking state after successful commit.

        Per ADR-0074: Called by SaveSession after successful entity commit.
        Clears accessor modifications (System 2) and updates snapshot (System 3).

        This method is idempotent - safe to call multiple times.
        """
        # System 2: Clear accessor modifications
        if self._custom_fields_accessor is not None:
            self._custom_fields_accessor.clear_changes()

        # System 3: Update snapshot to current state
        self._update_custom_fields_snapshot()

    def _update_custom_fields_snapshot(self) -> None:
        """Update the custom fields snapshot to current state.

        Per FR-002: Synchronize System 3 snapshot after commit.
        """
        if self.custom_fields is not None:
            self._original_custom_fields = copy.deepcopy(self.custom_fields)
        else:
            self._original_custom_fields = None
