"""API request and response models.

This module provides Pydantic models for structured API responses,
following the autom8y ecosystem patterns.

Fleet-standard envelope types (SuccessResponse, ErrorResponse, ErrorDetail,
ResponseMeta, PaginationMeta) are imported from autom8y-api-schemas and
re-exported here for backward compatibility.

Migration: Lexicon Ascension Sprint-4 (ASANA-QW-04)

Per TDD-ASANA-SATELLITE:
- Standard response envelope with data + meta
- Pagination metadata for list operations
- Structured error responses with request_id

Per PRD-ASANA-SATELLITE Appendix A:
- Success response: {"data": ..., "meta": {"request_id": ..., "timestamp": ...}}
- Error response: {"error": {"code": ..., "message": ...}, "meta": {...}}
"""

# Fleet-standard envelope types from shared package.
# Re-exported at this path for backward compatibility -- existing code
# imports these from autom8_asana.api.models.
import os
from typing import Annotated

from autom8y_api_schemas import (
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    ResponseMeta,
    SuccessResponse,
    build_error_response,
    build_success_response,
)
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Reusable GID type (Mandate 3: Regex Field patterns)
# Production enforces numeric-only GIDs. Test/local environments relax
# to allow human-readable GIDs in test fixtures.
_gid_pattern: str | None = (
    r"^\d{1,64}$"
    if os.environ.get("AUTOM8Y_ENV", "production") not in ("test", "local", "LOCAL")
    else None
)
GidStr = Annotated[
    str,
    StringConstraints(pattern=_gid_pattern),
]


class ListTasksParams(BaseModel):
    """Query parameters for listing tasks.

    Per FR-API-TASK-001/002: Exactly one of project or section must be provided.
    """

    project: GidStr | None = Field(
        default=None,
        description="Project GID to list tasks from",
    )
    section: GidStr | None = Field(
        default=None,
        description="Section GID to list tasks from",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Number of items per page",
    )
    offset: str | None = Field(
        default=None,
        description="Pagination cursor from previous response",
    )

    @model_validator(mode="after")
    def validate_exactly_one_target(self) -> "ListTasksParams":
        """Enforce that exactly one of project or section is provided."""
        if (self.project is None) == (self.section is None):
            raise ValueError("Exactly one of 'project' or 'section' must be provided")
        return self


class AsanaResource(BaseModel):
    """Base Asana resource returned by the Asana API.

    All Asana resources share a gid and resource_type. Additional fields
    vary by endpoint and the opt_fields parameter. The extra="allow"
    config accepts any additional fields without declaring them, which
    avoids the circular $ref problem that dict[str, Any] causes in the
    generated OpenAPI schema.

    Attributes:
        gid: Globally unique identifier for the Asana resource.
        resource_type: Resource type string (e.g., "task", "project").
        name: Display name of the resource (optional, depends on opt_fields).
    """

    gid: GidStr = Field(
        ...,
        description="Globally unique Asana resource identifier (numeric string)",
        examples=["1234567890123456"],
    )
    resource_type: str | None = Field(
        default=None,
        description="Asana resource type",
        examples=["task"],
    )
    name: str | None = Field(
        default=None,
        description="Resource display name",
        examples=["Review Q3 marketing proposal"],
    )

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "gid": "1234567890123456",
                    "resource_type": "task",
                    "name": "Review Q3 marketing proposal",
                }
            ]
        },
    )


# --- Request Models ---
# Per TDD-ASANA-SATELLITE: Pydantic models for request body validation


class CreateTaskRequest(BaseModel):
    """Request body for creating a task.

    Per FR-API-TASK-003: Create task endpoint.

    Attributes:
        name: Task name (required).
        notes: Task description (optional).
        assignee: Assignee user GID (optional).
        projects: List of project GIDs to add task to (optional).
        due_on: Due date in YYYY-MM-DD format (optional).
        workspace: Workspace GID (required if no projects specified).
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Task name",
        examples=["Review Q3 marketing proposal"],
    )
    notes: str | None = Field(
        default=None,
        description="Task description",
        examples=["Check accuracy and completeness before the team review."],
    )
    assignee: GidStr | None = Field(
        default=None,
        description="Assignee user GID",
        examples=["9876543210987654"],
    )
    projects: list[GidStr] | None = Field(
        default=None,
        description="Project GIDs to add task to",
        examples=[["1234567890123456"]],
    )
    due_on: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Due date (YYYY-MM-DD)",
        examples=["2026-03-15"],
    )
    workspace: GidStr | None = Field(
        default=None,
        description="Workspace GID (required if no projects)",
        examples=["1111111111111111"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Review Q3 marketing proposal",
                    "notes": "Check accuracy and completeness before the team review.",
                    "assignee": "9876543210987654",
                    "projects": ["1234567890123456"],
                    "due_on": "2026-03-15",
                    "workspace": None,
                }
            ]
        },
    )


class UpdateTaskRequest(BaseModel):
    """Request body for updating a task.

    Per FR-API-TASK-004: Update task endpoint.

    All fields are optional; only provided fields are updated.

    Attributes:
        name: New task name.
        notes: New task description.
        completed: Task completion status.
        due_on: Due date in YYYY-MM-DD format (null to clear).
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        description="Task name",
        examples=["Review Q3 marketing proposal (updated)"],
    )
    notes: str | None = Field(
        default=None,
        description="Task description",
        examples=["Updated after stakeholder review."],
    )
    completed: bool | None = Field(
        default=None,
        description="Completion status",
        examples=[True],
    )
    due_on: str | None = Field(
        default=None,
        description="Due date (YYYY-MM-DD, null to clear)",
        examples=["2026-03-20"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": None,
                    "notes": "Updated after stakeholder review.",
                    "completed": True,
                    "due_on": "2026-03-20",
                }
            ]
        },
    )


class AddTagRequest(BaseModel):
    """Request body for adding a tag to a task.

    Per FR-API-TASK-012: Add tag to task endpoint.

    Attributes:
        tag_gid: GID of the tag to add.
    """

    tag_gid: GidStr = Field(
        ...,
        description="Tag GID to add",
        examples=["2222222222222222"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"tag_gid": "2222222222222222"}]},
    )


class MoveSectionRequest(BaseModel):
    """Request body for moving a task to a section.

    Per FR-API-TASK-014: Move task to section endpoint.

    Attributes:
        section_gid: GID of the target section.
        project_gid: GID of the project containing the section.
    """

    section_gid: GidStr = Field(
        ...,
        description="Target section GID",
        examples=["3333333333333333"],
    )
    project_gid: GidStr = Field(
        ...,
        description="Project GID containing section",
        examples=["1234567890123456"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "section_gid": "3333333333333333",
                    "project_gid": "1234567890123456",
                }
            ]
        },
    )


class SetAssigneeRequest(BaseModel):
    """Request body for setting task assignee.

    Per FR-API-TASK-015: Set task assignee endpoint.

    Attributes:
        assignee_gid: GID of the user to assign (null to unassign).
    """

    assignee_gid: GidStr | None = Field(
        default=None,
        description="User GID to assign (null to unassign)",
        examples=["9876543210987654"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"assignee_gid": "9876543210987654"}]},
    )


class AddToProjectRequest(BaseModel):
    """Request body for adding task to a project.

    Per FR-API-TASK-016: Add task to project endpoint.

    Attributes:
        project_gid: GID of the project to add task to.
    """

    project_gid: GidStr = Field(
        ...,
        description="Project GID to add to",
        examples=["1234567890123456"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"project_gid": "1234567890123456"}]},
    )


class DuplicateTaskRequest(BaseModel):
    """Request body for duplicating a task.

    Per FR-API-TASK-011: Duplicate task endpoint.

    Attributes:
        name: Name for the new duplicated task.
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Name for duplicated task",
        examples=["Review Q3 marketing proposal (copy)"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"name": "Review Q3 marketing proposal (copy)"}]},
    )


# --- Project Request Models ---


class CreateProjectRequest(BaseModel):
    """Request body for creating a project.

    Per FR-API-PROJ-002: Create project endpoint.

    Attributes:
        name: Project name (required).
        workspace: Workspace GID (required).
        team: Team GID (optional, for organization workspaces).
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Project name",
        examples=["Website Redesign"],
    )
    workspace: GidStr = Field(
        ...,
        description="Workspace GID",
        examples=["1111111111111111"],
    )
    team: GidStr | None = Field(
        default=None,
        description="Team GID (for organizations)",
        examples=["4444444444444444"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Website Redesign",
                    "workspace": "1111111111111111",
                    "team": "4444444444444444",
                }
            ]
        },
    )


class UpdateProjectRequest(BaseModel):
    """Request body for updating a project.

    Per FR-API-PROJ-003: Update project endpoint.

    All fields are optional; only provided fields are updated.

    Attributes:
        name: New project name.
        notes: New project description.
        archived: Archive status.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        description="Project name",
        examples=["Website Redesign (Phase 2)"],
    )
    notes: str | None = Field(
        default=None,
        description="Project description",
        examples=["Continuation of the Q2 redesign initiative."],
    )
    archived: bool | None = Field(
        default=None,
        description="Archive status",
        examples=[False],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": None,
                    "notes": "Continuation of the Q2 redesign initiative.",
                    "archived": False,
                }
            ]
        },
    )


class MembersRequest(BaseModel):
    """Request body for adding/removing project members.

    Per FR-API-PROJ-007/008: Add/remove members endpoints.

    Attributes:
        members: List of user GIDs to add or remove.
    """

    members: list[GidStr] = Field(
        ...,
        min_length=1,
        description="List of user GIDs",
        examples=[["9876543210987654", "9876543210987655"]],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"members": ["9876543210987654", "9876543210987655"]}]},
    )


# --- Section Request Models ---


class CreateSectionRequest(BaseModel):
    """Request body for creating a section.

    Per FR-API-SECT-002: Create section endpoint.

    Attributes:
        name: Section name (required).
        project: Project GID to create section in (required).
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Section name",
        examples=["In Progress"],
    )
    project: GidStr = Field(
        ...,
        description="Project GID",
        examples=["1234567890123456"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "In Progress",
                    "project": "1234567890123456",
                }
            ]
        },
    )


class UpdateSectionRequest(BaseModel):
    """Request body for updating a section.

    Per FR-API-SECT-003: Update section endpoint.

    Attributes:
        name: New section name.
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Section name",
        examples=["Done"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"name": "Done"}]},
    )


class AddTaskToSectionRequest(BaseModel):
    """Request body for adding a task to a section.

    Per FR-API-SECT-005: Add task to section endpoint.

    Attributes:
        task_gid: GID of the task to add.
    """

    task_gid: GidStr = Field(
        ...,
        description="Task GID to add",
        examples=["1234567890123456"],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"task_gid": "1234567890123456"}]},
    )


class ReorderSectionRequest(BaseModel):
    """Request body for reordering a section within a project.

    Per FR-API-SECT-006: Reorder section endpoint.

    Exactly one of before_section or after_section must be provided.

    Attributes:
        project_gid: Project GID containing the section.
        before_section: Section GID to insert before (optional).
        after_section: Section GID to insert after (optional).
    """

    project_gid: GidStr = Field(
        ...,
        description="Project GID",
        examples=["1234567890123456"],
    )
    before_section: GidStr | None = Field(
        default=None,
        description="Section GID to insert before",
        examples=["3333333333333333"],
    )
    after_section: GidStr | None = Field(
        default=None,
        description="Section GID to insert after",
        examples=[None],
    )

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "project_gid": "1234567890123456",
                    "before_section": "3333333333333333",
                    "after_section": None,
                }
            ]
        },
    )


__all__ = [
    # Response models
    "AsanaResource",
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "ResponseMeta",
    "SuccessResponse",
    "build_error_response",
    "build_success_response",
    # Task request models
    "ListTasksParams",
    "AddTagRequest",
    "AddToProjectRequest",
    "CreateTaskRequest",
    "DuplicateTaskRequest",
    "MoveSectionRequest",
    "SetAssigneeRequest",
    "UpdateTaskRequest",
    # Project request models
    "CreateProjectRequest",
    "UpdateProjectRequest",
    "MembersRequest",
    # Section request models
    "CreateSectionRequest",
    "UpdateSectionRequest",
    "AddTaskToSectionRequest",
    "ReorderSectionRequest",
]
