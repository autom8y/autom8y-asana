"""Base schema with 12 columns applicable to all task types.

Per FR-MODEL-002: BASE_SCHEMA defines common fields for all tasks.
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema


# Base column definitions (12 columns) - FR-MODEL-002
BASE_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="gid",
        dtype="Utf8",
        nullable=False,
        source="gid",
        description="Task identifier (globally unique)",
    ),
    ColumnDef(
        name="name",
        dtype="Utf8",
        nullable=False,
        source="name",
        description="Task name/title",
    ),
    ColumnDef(
        name="type",
        dtype="Utf8",
        nullable=False,
        source="resource_subtype",
        description="Task type discriminator",
    ),
    ColumnDef(
        name="date",
        dtype="Date",
        nullable=True,
        source=None,  # Custom extraction logic
        description="Primary date field (type-specific)",
    ),
    ColumnDef(
        name="created",
        dtype="Datetime",
        nullable=False,
        source="created_at",
        description="Task creation timestamp",
    ),
    ColumnDef(
        name="due_on",
        dtype="Date",
        nullable=True,
        source="due_on",
        description="Due date",
    ),
    ColumnDef(
        name="is_completed",
        dtype="Boolean",
        nullable=False,
        source="completed",
        description="Completion status",
    ),
    ColumnDef(
        name="completed_at",
        dtype="Datetime",
        nullable=True,
        source="completed_at",
        description="Completion timestamp",
    ),
    ColumnDef(
        name="url",
        dtype="Utf8",
        nullable=False,
        source=None,  # Constructed from GID: https://app.asana.com/0/0/{gid}
        description="Asana task URL",
    ),
    ColumnDef(
        name="last_modified",
        dtype="Datetime",
        nullable=False,
        source="modified_at",
        description="Last modification timestamp",
    ),
    ColumnDef(
        name="section",
        dtype="Utf8",
        nullable=True,
        source=None,  # Extracted from memberships
        description="Section name within project",
    ),
    ColumnDef(
        name="tags",
        dtype="List[Utf8]",
        nullable=False,
        source="tags",
        description="List of tag names",
    ),
]


BASE_SCHEMA = DataFrameSchema(
    name="base",
    task_type="*",  # Wildcard: applies to all task types
    columns=BASE_COLUMNS,
    version="1.0.0",
)
