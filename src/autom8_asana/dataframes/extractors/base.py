"""Base extractor with shared field extraction logic.

Per TDD-0009 Phase 3: Abstract base extractor with 12 base field methods
and schema-driven column extraction supporting custom field resolution.

Per TDD-CASCADING-FIELD-RESOLUTION-001: Added cascade: prefix support for
parent chain traversal of custom fields.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from autom8_asana.dataframes.exceptions import ExtractionError

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
    from autom8_asana.dataframes.models.task_row import TaskRow
    from autom8_asana.dataframes.resolver.cascading import CascadingFieldResolver
    from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver
    from autom8_asana.models.task import Task


class BaseExtractor(ABC):
    """Abstract base extractor with 12 base field extraction methods.

    Per TDD-0009: Provides schema-driven extraction with support for:
    - Direct attribute access (source = attribute name)
    - Custom field extraction (source starts with "cf:" or "gid:")
    - Derived fields (source = None, delegates to subclass method)

    Per TDD-CASCADING-FIELD-RESOLUTION-001: Added cascade: prefix support for
    parent chain traversal of custom fields (requires async extraction).

    Subclasses implement type-specific extraction by overriding
    derived field methods and the row construction method.

    Attributes:
        schema: DataFrameSchema defining columns to extract
        resolver: Optional CustomFieldResolver for cf:/gid: fields
        client: Optional AsanaClient for cascade: field resolution

    Example:
        >>> extractor = UnitExtractor(UNIT_SCHEMA, resolver)
        >>> row = extractor.extract(task)
        >>> row.gid
        '1234567890'

        >>> # With cascade support:
        >>> extractor = UnitExtractor(UNIT_SCHEMA, resolver, client=client)
        >>> row = await extractor.extract_async(task)
        >>> row.office_phone  # Resolved from Business ancestor
        '555-123-4567'
    """

    def __init__(
        self,
        schema: DataFrameSchema,
        resolver: CustomFieldResolver | None = None,
        client: AsanaClient | None = None,
    ) -> None:
        """Initialize extractor with schema and optional resolver.

        Args:
            schema: DataFrameSchema defining columns to extract
            resolver: CustomFieldResolver for custom field extraction.
                      Required if schema contains cf: or gid: sources.
            client: AsanaClient for cascade: field resolution.
                    Required if schema contains cascade: sources.
        """
        self._schema = schema
        self._resolver = resolver
        self._client = client
        self._cascading_resolver: CascadingFieldResolver | None = None

    @property
    def schema(self) -> DataFrameSchema:
        """Get the schema used by this extractor."""
        return self._schema

    @property
    def resolver(self) -> CustomFieldResolver | None:
        """Get the custom field resolver."""
        return self._resolver

    @property
    def client(self) -> AsanaClient | None:
        """Get the Asana client for cascade resolution."""
        return self._client

    def _get_cascading_resolver(self) -> CascadingFieldResolver:
        """Lazy initialization of cascading resolver.

        Per TDD-CASCADING-FIELD-RESOLUTION-001: Creates CascadingFieldResolver
        on first access, requiring client to be set.

        Per MIGRATION-PLAN-legacy-cache-elimination RF-008: Wires CascadeViewPlugin
        when unified_store is available for integrated parent chain resolution.

        Returns:
            CascadingFieldResolver instance for parent chain traversal.

        Raises:
            ValueError: If client is not set (required for cascade: sources).
        """
        if self._cascading_resolver is None:
            if self._client is None:
                raise ValueError(
                    "AsanaClient required for cascade: sources. "
                    "Pass client parameter to extractor constructor."
                )
            from autom8_asana.dataframes.resolver.cascading import (
                CascadingFieldResolver,
            )

            # Create cascade plugin if unified store available
            cascade_plugin = None
            if hasattr(self._client, "unified_store") and self._client.unified_store:
                from autom8_asana.dataframes.views.cascade_view import CascadeViewPlugin

                cascade_plugin = CascadeViewPlugin(store=self._client.unified_store)

            self._cascading_resolver = CascadingFieldResolver(
                self._client,
                cascade_plugin=cascade_plugin,
            )
        return self._cascading_resolver

    def _normalize_list_fields(self, data: dict[str, Any]) -> None:
        """Normalize None values to empty lists for List-typed schema columns.

        Called by extract() and extract_async() before _create_row() to ensure
        subclasses always receive pre-normalized data for list fields.

        Args:
            data: Mutable dict of column_name -> extracted value (modified in-place)
        """
        for col in self._schema.columns:
            if (
                col.dtype in ("List[Utf8]", "List[String]")
                and data.get(col.name) is None
            ):
                data[col.name] = []

    def extract(self, task: Task, project_gid: str | None = None) -> TaskRow:
        """Extract a TaskRow from a Task using the schema.

        Per FR-MODEL-008: Extracts all 12 base fields from task model.
        Per FR-ERROR-005: Continues on individual field failures.

        Args:
            task: Task to extract data from
            project_gid: Optional project GID for section extraction

        Returns:
            TaskRow (or subclass) with extracted field values

        Raises:
            ExtractionError: If extraction fails for critical fields
        """
        data: dict[str, Any] = {}
        errors: list[ExtractionError] = []

        for col in self._schema.columns:
            try:
                value = self._extract_column(task, col, project_gid)
                data[col.name] = value
            except Exception as e:  # BROAD-CATCH: isolation
                # Per FR-ERROR-005: Continue on individual failures
                task_gid = getattr(task, "gid", "unknown")
                errors.append(ExtractionError(task_gid, col.name, e))
                data[col.name] = None

        # Log errors if any occurred (future: use LogProvider)
        # For now, store them for debugging access
        self._normalize_list_fields(data)
        row = self._create_row(data)
        return row

    async def extract_async(
        self, task: Task, project_gid: str | None = None
    ) -> TaskRow:
        """Extract a TaskRow from a Task using async resolution for cascade fields.

        Per TDD-CASCADING-FIELD-RESOLUTION-001: Async extraction supporting
        cascade: prefix for parent chain traversal.

        Args:
            task: Task to extract data from
            project_gid: Optional project GID for section extraction

        Returns:
            TaskRow (or subclass) with extracted field values

        Raises:
            ExtractionError: If extraction fails for critical fields
        """
        data: dict[str, Any] = {}
        errors: list[ExtractionError] = []

        for col in self._schema.columns:
            try:
                value = await self._extract_column_async(task, col, project_gid)
                data[col.name] = value
            except Exception as e:  # BROAD-CATCH: isolation
                # Per FR-ERROR-005: Continue on individual failures
                task_gid = getattr(task, "gid", "unknown")
                errors.append(ExtractionError(task_gid, col.name, e))
                data[col.name] = None

        self._normalize_list_fields(data)
        row = self._create_row(data)
        return row

    @abstractmethod
    def _create_row(self, data: dict[str, Any]) -> TaskRow:
        """Create the appropriate TaskRow subclass from extracted data.

        Args:
            data: Dict of column_name -> extracted value

        Returns:
            TaskRow or subclass instance
        """
        ...

    def _extract_column(
        self,
        task: Task,
        col: ColumnDef,
        project_gid: str | None = None,
    ) -> Any:
        """Extract a single column value from a task.

        Per TDD-0009 custom field extraction logic:
        - source is None: Derived field, delegate to _extract_{name} method
        - source starts with "cf:" or "gid:": Custom field via resolver
        - source starts with "cascade:": Requires async - use extract_async()
        - Otherwise: Direct attribute access

        Args:
            task: Task to extract from
            col: Column definition specifying source
            project_gid: Optional project GID for section extraction

        Returns:
            Extracted and optionally coerced value

        Raises:
            ValueError: If resolver required but not provided
            ValueError: If cascade: source used (requires extract_async)
        """
        if col.source is None:
            # Derived field - delegate to subclass method
            method_name = f"_extract_{col.name}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                # Special case for section which needs project_gid
                if col.name == "section":
                    return method(task, project_gid)
                return method(task)
            return None

        # Per TDD-CASCADING-FIELD-RESOLUTION-001: cascade: requires async
        if col.source.lower().startswith("cascade:"):
            raise ValueError(
                f"cascade: sources require async extraction. "
                f"Use extract_async() for field: {col.source}"
            )

        if col.source.startswith("cf:") or col.source.startswith("gid:"):
            # Custom field extraction via resolver with schema-aware coercion
            if self._resolver is None:
                raise ValueError(
                    f"Resolver required for custom field extraction: {col.source}"
                )
            # Pass column_def for schema-aware coercion
            return self._resolver.get_value(task, col.source, column_def=col)

        # Direct attribute access with dtype-aware parsing
        return self._extract_attribute(task, col.source, col)

    async def _extract_column_async(
        self,
        task: Task,
        col: ColumnDef,
        project_gid: str | None = None,
    ) -> Any:
        """Extract a single column value from a task (async version).

        Per TDD-CASCADING-FIELD-RESOLUTION-001: Async extraction supporting
        cascade: prefix for parent chain traversal.

        Args:
            task: Task to extract from
            col: Column definition specifying source
            project_gid: Optional project GID for section extraction

        Returns:
            Extracted and optionally coerced value

        Raises:
            ValueError: If resolver/client required but not provided
        """
        if col.source is None:
            # Derived field - delegate to subclass method
            # Per WS3-001: Check for async variant first (e.g., _extract_office_async),
            # falling back to sync variant (e.g., _extract_office) if not found.
            async_method_name = f"_extract_{col.name}_async"
            if hasattr(self, async_method_name):
                async_method = getattr(self, async_method_name)
                if col.name == "section":
                    return await async_method(task, project_gid)
                return await async_method(task)

            method_name = f"_extract_{col.name}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                # Special case for section which needs project_gid
                if col.name == "section":
                    return method(task, project_gid)
                return method(task)
            return None

        # Per TDD-CASCADING-FIELD-RESOLUTION-001: Handle cascade: prefix
        if col.source.lower().startswith("cascade:"):
            field_name = col.source[8:]  # Strip "cascade:" prefix
            resolver = self._get_cascading_resolver()
            return await resolver.resolve_async(task, field_name)

        if col.source.startswith("cf:") or col.source.startswith("gid:"):
            # Custom field extraction via resolver with schema-aware coercion
            if self._resolver is None:
                raise ValueError(
                    f"Resolver required for custom field extraction: {col.source}"
                )
            # Pass column_def for schema-aware coercion
            return self._resolver.get_value(task, col.source, column_def=col)

        # Direct attribute access with dtype-aware parsing
        return self._extract_attribute(task, col.source, col)

    def _extract_attribute(
        self, task: Task, source: str, col: ColumnDef | None = None
    ) -> Any:
        """Extract a direct attribute from a task.

        Handles simple attribute names, datetime parsing, and type coercion.

        Args:
            task: Task to extract from
            source: Attribute name
            col: Optional ColumnDef for dtype-aware parsing

        Returns:
            Attribute value, with datetime strings parsed based on dtype
        """
        value = getattr(task, source, None)

        # Handle special cases
        if source == "completed":
            return bool(value) if value is not None else False

        if source == "tags" and value is not None:
            # Extract tag names from NameGid list
            return [tag.name for tag in value if tag.name]

        # Parse datetime strings based on column dtype
        if col is not None and value is not None and isinstance(value, str):
            if col.dtype == "Datetime":
                return self._parse_datetime(value)
            elif col.dtype == "Date":
                return self._parse_date(value)

        return value

    # =========================================================================
    # Base field extraction methods (12 fields)
    # Per FR-MODEL-021: All 12 base fields extracted correctly
    # =========================================================================

    def _extract_gid(self, task: Task) -> str:
        """Extract task GID (FR-MODEL-021).

        Args:
            task: Task to extract from

        Returns:
            Task GID string
        """
        return task.gid or ""

    def _extract_name(self, task: Task) -> str:
        """Extract task name (FR-MODEL-021).

        Args:
            task: Task to extract from

        Returns:
            Task name string
        """
        return task.name or ""

    def _extract_type(self, task: Task) -> str:
        """Extract task type discriminator (FR-MODEL-021).

        Per PRD-0003: Type from resource_subtype or inferred from task class.

        Args:
            task: Task to extract from

        Returns:
            Task type string (e.g., "default_task", "Unit", "Contact")
        """
        # First check resource_subtype
        if task.resource_subtype:
            return task.resource_subtype

        # Default to schema task_type if available
        return self._schema.task_type

    def _extract_created(self, task: Task) -> dt.datetime:
        """Extract task creation timestamp (FR-MODEL-021).

        Per FR-MODEL-012: Parse ISO 8601 strings to datetime objects.

        Args:
            task: Task to extract from

        Returns:
            Creation datetime (UTC)
        """
        if task.created_at:
            return self._parse_datetime(task.created_at)
        # Return epoch as fallback for required field
        return dt.datetime(1970, 1, 1, tzinfo=dt.UTC)

    def _extract_due_on(self, task: Task) -> dt.date | None:
        """Extract due date (FR-MODEL-021).

        Args:
            task: Task to extract from

        Returns:
            Due date or None
        """
        if task.due_on:
            return self._parse_date(task.due_on)
        return None

    def _extract_is_completed(self, task: Task) -> bool:
        """Extract completion status (FR-MODEL-021).

        Args:
            task: Task to extract from

        Returns:
            True if task is completed
        """
        return bool(task.completed)

    def _extract_completed_at(self, task: Task) -> dt.datetime | None:
        """Extract completion timestamp (FR-MODEL-021).

        Args:
            task: Task to extract from

        Returns:
            Completion datetime or None
        """
        if task.completed_at:
            return self._parse_datetime(task.completed_at)
        return None

    def _extract_url(self, task: Task) -> str:
        """Extract Asana task URL (FR-MODEL-011).

        Per PRD-0003: Format https://app.asana.com/0/0/{gid}

        Args:
            task: Task to extract from

        Returns:
            Asana task URL
        """
        gid = task.gid or ""
        return f"https://app.asana.com/0/0/{gid}"

    def _extract_last_modified(self, task: Task) -> dt.datetime:
        """Extract last modification timestamp (FR-MODEL-021).

        Args:
            task: Task to extract from

        Returns:
            Last modified datetime (UTC)
        """
        if task.modified_at:
            return self._parse_datetime(task.modified_at)
        # Return epoch as fallback for required field
        return dt.datetime(1970, 1, 1, tzinfo=dt.UTC)

    def _extract_section(
        self,
        task: Task,
        project_gid: str | None = None,
    ) -> str | None:
        """Extract section name from task memberships (FR-MODEL-009).

        Per PRD-0003: Section extracted from task's memberships for target project.
        Delegates to canonical extract_section_name() per DRY-001.

        Args:
            task: Task to extract from
            project_gid: Project GID to filter memberships by

        Returns:
            Section name or None
        """
        from autom8_asana.models.business.activity import extract_section_name

        return extract_section_name(task, project_gid)

    def _extract_tags(self, task: Task) -> list[str]:
        """Extract tag names (FR-MODEL-010).

        Per PRD-0003: Tags extracted as list[str] of tag names.

        Args:
            task: Task to extract from

        Returns:
            List of tag names (empty list if no tags)
        """
        if not task.tags:
            return []
        return [tag.name for tag in task.tags if tag.name]

    def _extract_date(self, task: Task) -> dt.date | None:
        """Extract primary date field (FR-MODEL-021).

        Per PRD-0003: Primary date field is type-specific.
        Default implementation uses due_on.

        Args:
            task: Task to extract from

        Returns:
            Primary date or None
        """
        return self._extract_due_on(task)

    # =========================================================================
    # Datetime parsing utilities
    # Per FR-MODEL-012: ISO 8601 strings converted to datetime/date objects
    # =========================================================================

    @staticmethod
    def _parse_datetime(value: str) -> dt.datetime:
        """Parse ISO 8601 datetime string to datetime object.

        Args:
            value: ISO 8601 datetime string

        Returns:
            datetime object with timezone
        """
        # Handle various ISO 8601 formats
        # Remove trailing Z and replace with +00:00
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        try:
            return dt.datetime.fromisoformat(value)
        except ValueError:
            # Try alternative parsing for edge cases
            for fmt in [
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    parsed = dt.datetime.strptime(value, fmt)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=dt.UTC)
                    return parsed
                except ValueError:
                    continue

            # Last resort: return with UTC timezone
            return dt.datetime(1970, 1, 1, tzinfo=dt.UTC)

    @staticmethod
    def _parse_date(value: str) -> dt.date:
        """Parse date string to date object.

        Args:
            value: Date string (YYYY-MM-DD)

        Returns:
            date object
        """
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            # Try alternative parsing
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"]:
                try:
                    return dt.datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            # Last resort: return epoch date
            return dt.date(1970, 1, 1)
