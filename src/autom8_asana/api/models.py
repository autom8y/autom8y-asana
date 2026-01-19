"""API request and response models.

This module provides Pydantic models for structured API responses,
following the autom8y ecosystem patterns from autom8_data.

Per TDD-ASANA-SATELLITE:
- Standard response envelope with data + meta
- Pagination metadata for list operations
- Structured error responses with request_id

Per PRD-ASANA-SATELLITE Appendix A:
- Success response: {"data": ..., "meta": {"request_id": ..., "timestamp": ...}}
- Error response: {"error": {"code": ..., "message": ...}, "meta": {...}}
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses.

    Per ADR-ASANA-008: Cursor-based pagination with opaque offset.

    Attributes:
        limit: Number of items requested per page.
        has_more: Whether more items exist after this page.
        next_offset: Opaque cursor for next page (None if no more pages).
    """

    limit: int = Field(..., ge=1, description="Number of items per page")
    has_more: bool = Field(..., description="Whether more items exist")
    next_offset: str | None = Field(
        default=None,
        description="Opaque cursor for next page",
    )

    model_config = {"extra": "forbid"}


class ResponseMeta(BaseModel):
    """Metadata included with all API responses.

    Provides request correlation and timing information for
    debugging and observability.

    Attributes:
        request_id: Unique 16-character hex identifier for this request.
        timestamp: UTC timestamp when response was generated.
        pagination: Pagination info for list responses (optional).
    """

    request_id: str = Field(
        ...,
        min_length=1,
        description="Request correlation ID",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Response timestamp (UTC)",
    )
    pagination: PaginationMeta | None = Field(
        default=None,
        description="Pagination metadata for list responses",
    )

    model_config = {"extra": "forbid"}


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope.

    Wraps response data with metadata for consistent API responses.

    Attributes:
        data: The response payload (single item or list).
        meta: Response metadata including request_id and timestamp.
    """

    data: T = Field(..., description="Response data payload")
    meta: ResponseMeta = Field(..., description="Response metadata")

    model_config = {"extra": "forbid"}


class ErrorDetail(BaseModel):
    """Structured error information.

    Per ADR-ASANA-004: Error codes map to specific failure modes.

    Attributes:
        code: Machine-readable error code (e.g., RESOURCE_NOT_FOUND).
        message: Human-readable error description.
        details: Additional context about the error (optional).
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional error context",
    )

    model_config = {"extra": "forbid"}


class ErrorResponse(BaseModel):
    """Standard error response envelope.

    Per PRD-ASANA-SATELLITE (FR-ERR-008): All error responses
    include request_id for correlation.

    Attributes:
        error: Structured error details.
        meta: Response metadata with request_id.
    """

    error: ErrorDetail = Field(..., description="Error details")
    meta: ResponseMeta = Field(..., description="Response metadata")

    model_config = {"extra": "forbid"}


def build_success_response(
    data: T,
    request_id: str,
    pagination: PaginationMeta | None = None,
) -> SuccessResponse[T]:
    """Build a standard success response.

    Args:
        data: Response payload.
        request_id: Request correlation ID.
        pagination: Pagination metadata for list responses.

    Returns:
        SuccessResponse with data and metadata.
    """
    return SuccessResponse(
        data=data,
        meta=ResponseMeta(
            request_id=request_id,
            pagination=pagination,
        ),
    )


def build_error_response(
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> ErrorResponse:
    """Build a standard error response.

    Args:
        code: Machine-readable error code.
        message: Human-readable error message.
        request_id: Request correlation ID.
        details: Additional error context.

    Returns:
        ErrorResponse with error details and metadata.
    """
    return ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
        ),
        meta=ResponseMeta(request_id=request_id),
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

    name: str = Field(..., min_length=1, description="Task name")
    notes: str | None = Field(default=None, description="Task description")
    assignee: str | None = Field(default=None, description="Assignee user GID")
    projects: list[str] | None = Field(
        default=None, description="Project GIDs to add task to"
    )
    due_on: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Due date (YYYY-MM-DD)",
    )
    workspace: str | None = Field(
        default=None, description="Workspace GID (required if no projects)"
    )

    model_config = {"extra": "forbid"}


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

    name: str | None = Field(default=None, min_length=1, description="Task name")
    notes: str | None = Field(default=None, description="Task description")
    completed: bool | None = Field(default=None, description="Completion status")
    due_on: str | None = Field(
        default=None,
        description="Due date (YYYY-MM-DD, null to clear)",
    )

    model_config = {"extra": "forbid"}


class AddTagRequest(BaseModel):
    """Request body for adding a tag to a task.

    Per FR-API-TASK-012: Add tag to task endpoint.

    Attributes:
        tag_gid: GID of the tag to add.
    """

    tag_gid: str = Field(..., min_length=1, description="Tag GID to add")

    model_config = {"extra": "forbid"}


class MoveSectionRequest(BaseModel):
    """Request body for moving a task to a section.

    Per FR-API-TASK-014: Move task to section endpoint.

    Attributes:
        section_gid: GID of the target section.
        project_gid: GID of the project containing the section.
    """

    section_gid: str = Field(..., min_length=1, description="Target section GID")
    project_gid: str = Field(
        ..., min_length=1, description="Project GID containing section"
    )

    model_config = {"extra": "forbid"}


class SetAssigneeRequest(BaseModel):
    """Request body for setting task assignee.

    Per FR-API-TASK-015: Set task assignee endpoint.

    Attributes:
        assignee_gid: GID of the user to assign (null to unassign).
    """

    assignee_gid: str | None = Field(
        default=None, description="User GID to assign (null to unassign)"
    )

    model_config = {"extra": "forbid"}


class AddToProjectRequest(BaseModel):
    """Request body for adding task to a project.

    Per FR-API-TASK-016: Add task to project endpoint.

    Attributes:
        project_gid: GID of the project to add task to.
    """

    project_gid: str = Field(..., min_length=1, description="Project GID to add to")

    model_config = {"extra": "forbid"}


class DuplicateTaskRequest(BaseModel):
    """Request body for duplicating a task.

    Per FR-API-TASK-011: Duplicate task endpoint.

    Attributes:
        name: Name for the new duplicated task.
    """

    name: str = Field(..., min_length=1, description="Name for duplicated task")

    model_config = {"extra": "forbid"}


# --- Project Request Models ---


class CreateProjectRequest(BaseModel):
    """Request body for creating a project.

    Per FR-API-PROJ-002: Create project endpoint.

    Attributes:
        name: Project name (required).
        workspace: Workspace GID (required).
        team: Team GID (optional, for organization workspaces).
    """

    name: str = Field(..., min_length=1, description="Project name")
    workspace: str = Field(..., min_length=1, description="Workspace GID")
    team: str | None = Field(default=None, description="Team GID (for organizations)")

    model_config = {"extra": "forbid"}


class UpdateProjectRequest(BaseModel):
    """Request body for updating a project.

    Per FR-API-PROJ-003: Update project endpoint.

    All fields are optional; only provided fields are updated.

    Attributes:
        name: New project name.
        notes: New project description.
        archived: Archive status.
    """

    name: str | None = Field(default=None, min_length=1, description="Project name")
    notes: str | None = Field(default=None, description="Project description")
    archived: bool | None = Field(default=None, description="Archive status")

    model_config = {"extra": "forbid"}


class MembersRequest(BaseModel):
    """Request body for adding/removing project members.

    Per FR-API-PROJ-007/008: Add/remove members endpoints.

    Attributes:
        members: List of user GIDs to add or remove.
    """

    members: list[str] = Field(..., min_length=1, description="List of user GIDs")

    model_config = {"extra": "forbid"}


# --- Section Request Models ---


class CreateSectionRequest(BaseModel):
    """Request body for creating a section.

    Per FR-API-SECT-002: Create section endpoint.

    Attributes:
        name: Section name (required).
        project: Project GID to create section in (required).
    """

    name: str = Field(..., min_length=1, description="Section name")
    project: str = Field(..., min_length=1, description="Project GID")

    model_config = {"extra": "forbid"}


class UpdateSectionRequest(BaseModel):
    """Request body for updating a section.

    Per FR-API-SECT-003: Update section endpoint.

    Attributes:
        name: New section name.
    """

    name: str = Field(..., min_length=1, description="Section name")

    model_config = {"extra": "forbid"}


class AddTaskToSectionRequest(BaseModel):
    """Request body for adding a task to a section.

    Per FR-API-SECT-005: Add task to section endpoint.

    Attributes:
        task_gid: GID of the task to add.
    """

    task_gid: str = Field(..., min_length=1, description="Task GID to add")

    model_config = {"extra": "forbid"}


class ReorderSectionRequest(BaseModel):
    """Request body for reordering a section within a project.

    Per FR-API-SECT-006: Reorder section endpoint.

    Exactly one of before_section or after_section must be provided.

    Attributes:
        project_gid: Project GID containing the section.
        before_section: Section GID to insert before (optional).
        after_section: Section GID to insert after (optional).
    """

    project_gid: str = Field(..., min_length=1, description="Project GID")
    before_section: str | None = Field(
        default=None, description="Section GID to insert before"
    )
    after_section: str | None = Field(
        default=None, description="Section GID to insert after"
    )

    model_config = {"extra": "forbid"}


__all__ = [
    # Response models
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "ResponseMeta",
    "SuccessResponse",
    "build_error_response",
    "build_success_response",
    # Task request models
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
