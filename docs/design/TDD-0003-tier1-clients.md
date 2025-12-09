# TDD: Tier 1 Resource Clients

## Metadata
- **TDD ID**: TDD-0003
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-SDK-017, FR-SDK-018, FR-SDK-019, FR-SDK-021, FR-SDK-027)
- **Related TDDs**: [TDD-0001](TDD-0001-sdk-architecture.md), [TDD-0002](TDD-0002-models-pagination.md)
- **Related ADRs**:
  - [ADR-0005](../decisions/ADR-0005-pydantic-model-config.md) - Pydantic v2 with extra="ignore"
  - [ADR-0006](../decisions/ADR-0006-namegid-standalone-model.md) - NameGid as standalone model
  - ADR-0007 (this TDD) - Consistent client pattern across resources

## Overview

This TDD defines the design for 5 Tier 1 resource clients that achieve autom8 parity: ProjectsClient, SectionsClient, CustomFieldsClient, UsersClient, and WorkspacesClient. Each client follows the established TasksClient pattern with async-first design, sync wrappers, typed models, and PageIterator for list operations.

## Requirements Summary

From PRD-0001:
- **FR-SDK-017**: ProjectsClient - CRUD + membership management
- **FR-SDK-018**: SectionsClient - CRUD + task movement between sections
- **FR-SDK-019**: CustomFieldsClient - CRUD + project settings management
- **FR-SDK-021**: UsersClient - Get user, list users, current user
- **FR-SDK-027**: WorkspacesClient - Get workspace, list workspaces

## System Context

```
                              autom8_asana SDK
+-----------------------------------------------------------------------------+
|                                                                             |
|  +------------------+     +---------------------------+                     |
|  | models/          |     | clients/                  |                     |
|  |                  |     |                           |                     |
|  | - base.py        |<----| - base.py (BaseClient)    |                     |
|  | - common.py      |     | - tasks.py (EXISTING)     |                     |
|  | - task.py        |     | - projects.py (NEW)       |                     |
|  | - project.py NEW |     | - sections.py (NEW)       |                     |
|  | - section.py NEW |     | - custom_fields.py (NEW)  |                     |
|  | - custom_field   |     | - users.py (NEW)          |                     |
|  |   .py (NEW)      |     | - workspaces.py (NEW)     |                     |
|  | - user.py (NEW)  |     |                           |                     |
|  | - workspace.py   |     +---------------------------+                     |
|  |   (NEW)          |                  |                                    |
|  +------------------+                  |                                    |
|          ^                             v                                    |
|          |                  +---------------------------+                   |
|          |                  | transport/                |                   |
|          |                  | - http.py                 |                   |
|          +------------------| - rate_limiter.py         |                   |
|                             +---------------------------+                   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

## Design

### Component Architecture

| Component | Responsibility | File Location |
|-----------|---------------|---------------|
| `Project` | Project resource model | `models/project.py` |
| `Section` | Section resource model | `models/section.py` |
| `CustomField` | Custom field resource model | `models/custom_field.py` |
| `User` | User resource model | `models/user.py` |
| `Workspace` | Workspace resource model | `models/workspace.py` |
| `ProjectsClient` | Project CRUD + memberships | `clients/projects.py` |
| `SectionsClient` | Section CRUD + task movement | `clients/sections.py` |
| `CustomFieldsClient` | Custom field CRUD + settings | `clients/custom_fields.py` |
| `UsersClient` | User operations | `clients/users.py` |
| `WorkspacesClient` | Workspace operations | `clients/workspaces.py` |

### Data Models

#### Project Model

```python
# /src/autom8_asana/models/project.py

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Project(AsanaResource):
    """Asana Project resource model.

    Uses NameGid for typed resource references (owner, team, workspace).
    Custom fields and complex nested structures remain as dicts.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> project = Project.model_validate(api_response)
        >>> if project.owner:
        ...     print(f"Owned by {project.owner.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="project")

    # Basic project fields
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status
    archived: bool | None = None
    public: bool | None = None
    color: str | None = Field(
        default=None,
        description="Color of the project (dark-pink, dark-green, etc.)",
    )

    # Dates
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
    modified_at: str | None = Field(default=None, description="Modified datetime (ISO 8601)")
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    due_at: str | None = Field(default=None, description="Due datetime (ISO 8601)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")

    # Relationships - typed with NameGid
    owner: NameGid | None = None
    team: NameGid | None = None
    workspace: NameGid | None = None
    current_status: NameGid | None = None
    current_status_update: NameGid | None = None

    # Collections
    members: list[NameGid] | None = None
    followers: list[NameGid] | None = None
    custom_fields: list[dict[str, Any]] | None = None  # Complex structure
    custom_field_settings: list[dict[str, Any]] | None = None  # Complex structure

    # Project properties
    default_view: str | None = Field(
        default=None,
        description="Default view (list, board, calendar, timeline)",
    )
    default_access_level: str | None = Field(
        default=None,
        description="Default access for new members (admin, editor, commenter, viewer)",
    )
    minimum_access_level_for_customization: str | None = None
    minimum_access_level_for_sharing: str | None = None
    is_template: bool | None = None
    completed: bool | None = None
    completed_at: str | None = None
    completed_by: NameGid | None = None
    created_from_template: NameGid | None = None

    # Layout-specific
    icon: str | None = None
    permalink_url: str | None = None

    # Privacy
    privacy_setting: str | None = Field(
        default=None,
        description="Privacy setting (public_to_workspace, private_to_team, private)",
    )
```

**Project Model Fields Rationale:**

| Field Type | Fields | Rationale |
|------------|--------|-----------|
| NameGid | owner, team, workspace, current_status, completed_by, created_from_template | Simple resource references with gid+name |
| list[NameGid] | members, followers | Lists of simple references |
| dict | custom_fields, custom_field_settings | Complex nested structures with varying schemas |
| str | color, default_view, privacy_setting | Enum-like strings (not Python enums for flexibility) |

#### Section Model

```python
# /src/autom8_asana/models/section.py

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Section(AsanaResource):
    """Asana Section resource model.

    Sections organize tasks within projects. Each section belongs to
    exactly one project.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> section = Section.model_validate(api_response)
        >>> print(f"Section '{section.name}' in project {section.project.gid}")
    """

    # Core identification
    resource_type: str | None = Field(default="section")

    # Basic section fields
    name: str | None = None

    # Relationships - typed with NameGid
    project: NameGid | None = None

    # Metadata
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
```

**Section Model Notes:**
- Sections are lightweight - only name, project reference, and timestamps
- The `project` field is critical for identifying which project contains the section

#### CustomField Model

```python
# /src/autom8_asana/models/custom_field.py

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class CustomFieldEnumOption(AsanaResource):
    """An option for enum-type custom fields.

    Example:
        >>> option = CustomFieldEnumOption.model_validate({"gid": "123", "name": "High", "color": "red"})
        >>> option.name
        'High'
    """

    resource_type: str | None = Field(default="enum_option")
    name: str | None = None
    enabled: bool | None = None
    color: str | None = None


class CustomField(AsanaResource):
    """Asana Custom Field resource model.

    Custom fields can be of various types: text, number, enum, multi_enum,
    date, people, etc. The structure varies by type.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> cf = CustomField.model_validate(api_response)
        >>> if cf.resource_subtype == "enum":
        ...     for opt in cf.enum_options or []:
        ...         print(f"  - {opt.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="custom_field")
    resource_subtype: str | None = Field(
        default=None,
        description="Type: text, number, enum, multi_enum, date, people",
    )

    # Basic fields
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    is_global_to_workspace: bool | None = None
    has_notifications_enabled: bool | None = None

    # Type-specific configuration
    precision: int | None = Field(
        default=None,
        description="Decimal precision for number fields",
    )
    format: str | None = Field(
        default=None,
        description="Format for display (currency, percentage, etc.)",
    )
    currency_code: str | None = Field(
        default=None,
        description="Currency code for currency fields (USD, EUR, etc.)",
    )
    custom_label: str | None = None
    custom_label_position: str | None = Field(
        default=None,
        description="Position of custom label (prefix, suffix)",
    )

    # Enum options
    enum_options: list[CustomFieldEnumOption] | None = None
    enum_value: CustomFieldEnumOption | None = Field(
        default=None,
        description="Selected enum value (when reading from task)",
    )
    multi_enum_values: list[CustomFieldEnumOption] | None = Field(
        default=None,
        description="Selected multi-enum values (when reading from task)",
    )

    # Value fields (present when custom field is on a task/project)
    text_value: str | None = None
    number_value: float | None = None
    display_value: str | None = Field(
        default=None,
        description="Human-readable display value",
    )
    date_value: dict[str, Any] | None = Field(
        default=None,
        description="Date value with date and optional datetime",
    )
    people_value: list[NameGid] | None = None

    # Relationships
    workspace: NameGid | None = None
    created_by: NameGid | None = None

    # Metadata
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")

    # ID representations
    id_prefix: str | None = None
    is_formula_field: bool | None = None
    is_value_read_only: bool | None = None


class CustomFieldSetting(AsanaResource):
    """Settings for a custom field on a project.

    Represents how a custom field is configured on a specific project,
    including whether it's important or which field it should be inserted after.

    Example:
        >>> setting = CustomFieldSetting.model_validate(api_response)
        >>> print(f"Field {setting.custom_field.gid} on project {setting.project.gid}")
    """

    resource_type: str | None = Field(default="custom_field_setting")

    # The custom field this setting applies to
    custom_field: CustomField | None = None

    # The project this setting is on
    project: NameGid | None = None
    parent: NameGid | None = None  # Alternative to project

    # Configuration
    is_important: bool | None = None
```

**CustomField Model Notes:**
- `resource_subtype` determines which value fields are populated
- `enum_options` contains the full list of options for enum/multi_enum types
- `enum_value` and `multi_enum_values` contain selected values when reading from tasks
- `CustomFieldSetting` is a separate model for project-level settings

#### User Model

```python
# /src/autom8_asana/models/user.py

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class User(AsanaResource):
    """Asana User resource model.

    Represents an Asana user account. Can be the current authenticated user
    or any user in accessible workspaces.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> user = User.model_validate(api_response)
        >>> print(f"User: {user.name} ({user.email})")
    """

    # Core identification
    resource_type: str | None = Field(default="user")

    # Basic user fields
    name: str | None = None
    email: str | None = None

    # Profile
    photo: dict[str, Any] | None = Field(
        default=None,
        description="Photo URLs in various sizes (image_21x21, image_27x27, etc.)",
    )

    # Workspace memberships
    workspaces: list[NameGid] | None = None
```

**User Model Notes:**
- Minimal model - users have few fields in Asana API
- `photo` is a dict because it contains multiple size URLs
- `workspaces` lists all workspaces the user belongs to

#### Workspace Model

```python
# /src/autom8_asana/models/workspace.py

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource


class Workspace(AsanaResource):
    """Asana Workspace resource model.

    Workspaces are the highest-level organizational unit in Asana.
    Organizations are a type of workspace with additional features.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> ws = Workspace.model_validate(api_response)
        >>> print(f"Workspace: {ws.name} (org: {ws.is_organization})")
    """

    # Core identification
    resource_type: str | None = Field(default="workspace")

    # Basic workspace fields
    name: str | None = None
    is_organization: bool | None = Field(
        default=None,
        description="True if this workspace is an organization",
    )

    # Email domains (for organizations)
    email_domains: list[str] | None = Field(
        default=None,
        description="Email domains associated with the organization",
    )
```

**Workspace Model Notes:**
- Very lightweight model - workspaces have minimal fields
- `is_organization` distinguishes organizations from basic workspaces
- `email_domains` only applies to organizations

### Client Implementations

All clients follow the established TasksClient pattern per TDD-0001:
- Async-first methods with `_async` suffix
- Sync wrappers using `@sync_wrapper` decorator
- `raw=True` parameter for dict fallback
- Type overloads for correct return type inference
- PageIterator for list operations

#### ProjectsClient

```python
# /src/autom8_asana/clients/projects.py

class ProjectsClient(BaseClient):
    """Client for Asana Project operations.

    Returns typed Project models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    async def get_async(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Project | dict[str, Any]:
        """Get a project by GID."""

    def get(self, project_gid: str, ...) -> Project | dict[str, Any]:
        """Get a project by GID (sync)."""

    async def create_async(
        self,
        *,
        name: str,
        workspace: str,
        raw: bool = False,
        team: str | None = None,
        public: bool | None = None,
        color: str | None = None,
        default_view: str | None = None,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Create a new project."""

    def create(self, *, name: str, workspace: str, ...) -> Project | dict[str, Any]:
        """Create a new project (sync)."""

    async def update_async(
        self,
        project_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Project | dict[str, Any]:
        """Update a project."""

    def update(self, project_gid: str, ...) -> Project | dict[str, Any]:
        """Update a project (sync)."""

    async def delete_async(self, project_gid: str) -> None:
        """Delete a project."""

    def delete(self, project_gid: str) -> None:
        """Delete a project (sync)."""

    def list_async(
        self,
        *,
        workspace: str | None = None,
        team: str | None = None,
        archived: bool | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Project]:
        """List projects with automatic pagination."""

    # --- Membership Operations ---

    async def add_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
    ) -> Project | dict[str, Any]:
        """Add members to a project.

        Args:
            project_gid: Project GID
            members: List of user GIDs to add

        Returns:
            Updated project
        """

    def add_members(self, project_gid: str, *, members: list[str]) -> Project | dict[str, Any]:
        """Add members to a project (sync)."""

    async def remove_members_async(
        self,
        project_gid: str,
        *,
        members: list[str],
    ) -> Project | dict[str, Any]:
        """Remove members from a project.

        Args:
            project_gid: Project GID
            members: List of user GIDs to remove

        Returns:
            Updated project
        """

    def remove_members(self, project_gid: str, *, members: list[str]) -> Project | dict[str, Any]:
        """Remove members from a project (sync)."""

    # --- Section-related convenience ---

    def get_sections_async(
        self,
        project_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Section]:
        """Get sections in a project (convenience method)."""
```

**Asana API Endpoints for Projects:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/projects/{gid}` |
| Create | POST | `/projects` |
| Update | PUT | `/projects/{gid}` |
| Delete | DELETE | `/projects/{gid}` |
| List | GET | `/projects` |
| Add Members | POST | `/projects/{gid}/addMembers` |
| Remove Members | POST | `/projects/{gid}/removeMembers` |

#### SectionsClient

```python
# /src/autom8_asana/clients/sections.py

class SectionsClient(BaseClient):
    """Client for Asana Section operations.

    Returns typed Section models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    async def get_async(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Section | dict[str, Any]:
        """Get a section by GID."""

    def get(self, section_gid: str, ...) -> Section | dict[str, Any]:
        """Get a section by GID (sync)."""

    async def create_async(
        self,
        *,
        name: str,
        project: str,
        raw: bool = False,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Section | dict[str, Any]:
        """Create a new section in a project.

        Args:
            name: Section name
            project: Project GID to create section in
            raw: If True, return raw dict
            insert_before: Section GID to insert before
            insert_after: Section GID to insert after
        """

    def create(self, *, name: str, project: str, ...) -> Section | dict[str, Any]:
        """Create a new section (sync)."""

    async def update_async(
        self,
        section_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Section | dict[str, Any]:
        """Update a section (rename)."""

    def update(self, section_gid: str, ...) -> Section | dict[str, Any]:
        """Update a section (sync)."""

    async def delete_async(self, section_gid: str) -> None:
        """Delete a section."""

    def delete(self, section_gid: str) -> None:
        """Delete a section (sync)."""

    def list_for_project_async(
        self,
        project_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Section]:
        """List sections in a project with automatic pagination."""

    # --- Task Movement Operations ---

    async def add_task_async(
        self,
        section_gid: str,
        *,
        task: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a task to a section.

        Moves the task to the specified section. If the task is already
        in another section of the same project, it will be moved.

        Args:
            section_gid: Section GID to add task to
            task: Task GID to add
            insert_before: Task GID to insert before
            insert_after: Task GID to insert after
        """

    def add_task(
        self,
        section_gid: str,
        *,
        task: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a task to a section (sync)."""

    async def insert_section_async(
        self,
        project_gid: str,
        *,
        section: str,
        before_section: str | None = None,
        after_section: str | None = None,
    ) -> None:
        """Reorder a section within a project.

        Args:
            project_gid: Project GID
            section: Section GID to move
            before_section: Section GID to insert before
            after_section: Section GID to insert after
        """

    def insert_section(
        self,
        project_gid: str,
        *,
        section: str,
        before_section: str | None = None,
        after_section: str | None = None,
    ) -> None:
        """Reorder a section within a project (sync)."""
```

**Asana API Endpoints for Sections:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/sections/{gid}` |
| Create | POST | `/projects/{project_gid}/sections` |
| Update | PUT | `/sections/{gid}` |
| Delete | DELETE | `/sections/{gid}` |
| List for Project | GET | `/projects/{project_gid}/sections` |
| Add Task | POST | `/sections/{gid}/addTask` |
| Insert Section | POST | `/projects/{project_gid}/sections/insert` |

#### CustomFieldsClient

```python
# /src/autom8_asana/clients/custom_fields.py

class CustomFieldsClient(BaseClient):
    """Client for Asana Custom Field operations.

    Returns typed CustomField models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    async def get_async(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> CustomField | dict[str, Any]:
        """Get a custom field by GID."""

    def get(self, custom_field_gid: str, ...) -> CustomField | dict[str, Any]:
        """Get a custom field by GID (sync)."""

    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        resource_subtype: str,
        raw: bool = False,
        description: str | None = None,
        enum_options: list[dict[str, Any]] | None = None,
        precision: int | None = None,
        format: str | None = None,
        currency_code: str | None = None,
        **kwargs: Any,
    ) -> CustomField | dict[str, Any]:
        """Create a new custom field.

        Args:
            workspace: Workspace GID
            name: Custom field name
            resource_subtype: Type (text, number, enum, multi_enum, date, people)
            raw: If True, return raw dict
            description: Field description
            enum_options: For enum types, list of option definitions
            precision: For number type, decimal precision
            format: Display format
            currency_code: For currency format
        """

    def create(self, *, workspace: str, name: str, ...) -> CustomField | dict[str, Any]:
        """Create a new custom field (sync)."""

    async def update_async(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomField | dict[str, Any]:
        """Update a custom field."""

    def update(self, custom_field_gid: str, ...) -> CustomField | dict[str, Any]:
        """Update a custom field (sync)."""

    async def delete_async(self, custom_field_gid: str) -> None:
        """Delete a custom field."""

    def delete(self, custom_field_gid: str) -> None:
        """Delete a custom field (sync)."""

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[CustomField]:
        """List custom fields in a workspace with automatic pagination."""

    # --- Enum Option Operations ---

    async def create_enum_option_async(
        self,
        custom_field_gid: str,
        *,
        name: str,
        color: str | None = None,
        enabled: bool = True,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Create a new enum option for a custom field."""

    def create_enum_option(
        self,
        custom_field_gid: str,
        *,
        name: str,
        **kwargs,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Create a new enum option (sync)."""

    async def update_enum_option_async(
        self,
        enum_option_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Update an enum option."""

    def update_enum_option(
        self,
        enum_option_gid: str,
        **kwargs,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Update an enum option (sync)."""

    # --- Project Settings Operations ---

    def get_settings_for_project_async(
        self,
        project_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[CustomFieldSetting]:
        """Get custom field settings for a project."""

    async def add_to_project_async(
        self,
        project_gid: str,
        *,
        custom_field: str,
        is_important: bool | None = None,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldSetting | dict[str, Any]:
        """Add a custom field to a project.

        Args:
            project_gid: Project GID
            custom_field: Custom field GID to add
            is_important: Whether to mark as important
            insert_before: Custom field GID to insert before
            insert_after: Custom field GID to insert after
        """

    def add_to_project(
        self,
        project_gid: str,
        *,
        custom_field: str,
        **kwargs,
    ) -> CustomFieldSetting | dict[str, Any]:
        """Add a custom field to a project (sync)."""

    async def remove_from_project_async(
        self,
        project_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Remove a custom field from a project."""

    def remove_from_project(
        self,
        project_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Remove a custom field from a project (sync)."""
```

**Asana API Endpoints for Custom Fields:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/custom_fields/{gid}` |
| Create | POST | `/custom_fields` |
| Update | PUT | `/custom_fields/{gid}` |
| Delete | DELETE | `/custom_fields/{gid}` |
| List for Workspace | GET | `/workspaces/{workspace_gid}/custom_fields` |
| Create Enum Option | POST | `/custom_fields/{gid}/enum_options` |
| Update Enum Option | PUT | `/enum_options/{gid}` |
| Get Settings for Project | GET | `/projects/{project_gid}/custom_field_settings` |
| Add to Project | POST | `/projects/{project_gid}/addCustomFieldSetting` |
| Remove from Project | POST | `/projects/{project_gid}/removeCustomFieldSetting` |

#### UsersClient

```python
# /src/autom8_asana/clients/users.py

class UsersClient(BaseClient):
    """Client for Asana User operations.

    Returns typed User models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        user_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Get a user by GID."""

    def get(self, user_gid: str, ...) -> User | dict[str, Any]:
        """Get a user by GID (sync)."""

    async def me_async(
        self,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> User | dict[str, Any]:
        """Get the current authenticated user.

        This is a convenience method that calls GET /users/me.
        """

    def me(self, ...) -> User | dict[str, Any]:
        """Get the current authenticated user (sync)."""

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[User]:
        """List users in a workspace with automatic pagination."""
```

**Asana API Endpoints for Users:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/users/{gid}` |
| Me | GET | `/users/me` |
| List for Workspace | GET | `/workspaces/{workspace_gid}/users` |

#### WorkspacesClient

```python
# /src/autom8_asana/clients/workspaces.py

class WorkspacesClient(BaseClient):
    """Client for Asana Workspace operations.

    Returns typed Workspace models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        workspace_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Workspace | dict[str, Any]:
        """Get a workspace by GID."""

    def get(self, workspace_gid: str, ...) -> Workspace | dict[str, Any]:
        """Get a workspace by GID (sync)."""

    def list_async(
        self,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Workspace]:
        """List workspaces accessible to the authenticated user."""
```

**Asana API Endpoints for Workspaces:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/workspaces/{gid}` |
| List | GET | `/workspaces` |

### API Contracts Summary

#### Method Pattern (all clients follow this)

```python
# Async primary methods
async def {operation}_async(self, ..., raw: bool = False, ...) -> Model | dict:
    """Async implementation."""

# Sync wrappers
def {operation}(self, ..., raw: bool = False, ...) -> Model | dict:
    """Sync wrapper."""

# List operations return PageIterator (always async)
def list_async(self, ...) -> PageIterator[Model]:
    """Returns PageIterator for automatic pagination."""
```

#### Standard Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `raw` | `bool` | If True, return raw dict instead of typed model |
| `opt_fields` | `list[str] | None` | Fields to include in response |
| `limit` | `int` | Items per page for list operations (default 100, max 100) |

### Data Flow

#### CRUD Operations

```
User Code                  Client                  BaseClient              HTTP
    |                         |                        |                     |
    | client.projects.get_async("123")                 |                     |
    |------------------------>|                        |                     |
    |                         | _log_operation()       |                     |
    |                         |----------------------->|                     |
    |                         | _build_opt_fields()    |                     |
    |                         |----------------------->|                     |
    |                         |                        |                     |
    |                         | self._http.get("/projects/123", params)      |
    |                         |------------------------------------------------>|
    |                         |                        |                     |
    |                         | data (dict)            |                     |
    |                         |<------------------------------------------------|
    |                         |                        |                     |
    |                         | Project.model_validate(data) if not raw      |
    |                         |----------------------->|                     |
    |                         |                        |                     |
    | Project (or dict)       |                        |                     |
    |<------------------------|                        |                     |
```

#### List with Pagination

```
User Code              Client.list_async()        PageIterator          HTTP
    |                         |                        |                   |
    | async for project in client.projects.list_async(workspace="x"):     |
    |------------------------>|                        |                   |
    |                         | return PageIterator(fetch_page)            |
    |                         |<-----------------------|                   |
    |                         |                        |                   |
    | __anext__()             |                        |                   |
    |----------------------------------------->|       |                   |
    |                         |                | _fetch_next_page()        |
    |                         |                |------>|                   |
    |                         |                |       | fetch_page(None)  |
    |                         |                |<------|                   |
    |                         |                |       |                   |
    |                         | GET /projects?workspace=x&limit=100        |
    |                         |------------------------------------------------>|
    |                         | {"data": [...], "next_page": {"offset": "Y"}}   |
    |                         |<------------------------------------------------|
    |                         |                |       |                   |
    |                         |                | (projects, "Y")           |
    |                         |                |<------|                   |
    |                         |                | buffer.extend()           |
    |                         |                | buffer.pop(0)             |
    | Project                 |                |                           |
    |<-----------------------------------------|                           |
    |                         |                |                           |
    | (continues...)          |                |                           |
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Consistent client pattern | Follow TasksClient | Predictable API, tested pattern | N/A (established) |
| NameGid for references | Yes | Type safety for resource refs | ADR-0006 |
| Dict for complex nested | Yes | CustomField values vary by type | ADR-0005 |
| PageIterator for lists | Yes | Memory efficient, lazy loading | TDD-0002 |
| No delete return value | Void | Asana API returns empty, match semantics | N/A |
| Workspace required for create | Explicit param | Clear resource ownership | N/A |

## Complexity Assessment

**Level**: MODULE

**Justification**:
- Each client is self-contained with clear responsibilities
- Follows established patterns (no new architectural concepts)
- Models are straightforward Pydantic classes
- No new configuration or operational concerns
- Clean API boundaries between clients

This maintains MODULE level (not SERVICE) because:
1. These are internal SDK components, not deployable services
2. No new protocols or abstractions introduced
3. Reuses existing infrastructure (BaseClient, PageIterator, sync_wrapper)

## Implementation Plan

### Phase 1: Models (2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Create `models/project.py` | None | 20min |
| Create `models/section.py` | None | 10min |
| Create `models/custom_field.py` | None | 30min |
| Create `models/user.py` | None | 10min |
| Create `models/workspace.py` | None | 10min |
| Unit tests for all models | Models | 40min |

**Exit Criteria**: All models validate against sample API responses.

### Phase 2: WorkspacesClient and UsersClient (1.5 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `WorkspacesClient` | Workspace model | 30min |
| Implement `UsersClient` | User model | 30min |
| Unit tests with mocks | Clients | 30min |

**Exit Criteria**: Basic CRUD operations pass unit tests.

### Phase 3: ProjectsClient (1.5 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `ProjectsClient` CRUD | Project model | 40min |
| Implement membership operations | ProjectsClient | 20min |
| Unit tests | Client | 30min |

**Exit Criteria**: All project operations pass unit tests.

### Phase 4: SectionsClient (1 hour)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `SectionsClient` | Section model | 30min |
| Unit tests | Client | 30min |

**Exit Criteria**: Section CRUD and task movement pass tests.

### Phase 5: CustomFieldsClient (1.5 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `CustomFieldsClient` | CustomField model | 45min |
| Implement enum and project settings | Client | 25min |
| Unit tests | Client | 20min |

**Exit Criteria**: All custom field operations pass unit tests.

### Phase 6: Integration and Export (1 hour)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Update `models/__init__.py` exports | All models | 10min |
| Update `clients/__init__.py` exports | All clients | 10min |
| Integration tests | All components | 40min |

**Exit Criteria**: All 5 clients integrated, 373+ tests pass.

**Total Estimate**: 8.5 hours

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Asana API field changes | Medium | Low | `extra="ignore"` handles gracefully |
| Model schema mismatches | Medium | Medium | Test against real API responses |
| Missing edge cases | Low | Medium | Review Asana API docs thoroughly |
| PageIterator performance | Low | Low | Already proven with TasksClient |

## Observability

### Logging

- **DEBUG**: All client operations logged via `_log_operation()`
- **INFO**: Batch operations, pagination totals
- **WARNING**: Unexpected API responses, empty results
- **ERROR**: API errors with full context

### Metrics (future)

- `asana_client_requests_total{client, operation}` (counter)
- `asana_client_request_duration_seconds{client, operation}` (histogram)
- `asana_client_errors_total{client, operation, error_type}` (counter)

## Testing Strategy

### Unit Testing

- **Models**: Validation, serialization, extra field handling
- **Clients**: Mock HTTP responses, verify correct endpoints called
- **Overloads**: Type checking with mypy in tests

### Integration Testing

- **Live API**: Optional tests against real Asana API (CI can skip)
- **Pagination**: Multi-page result sets
- **Error handling**: 404, 403, 429 responses

### Contract Testing

- **API fixtures**: Sample responses from Asana API documentation
- **Schema evolution**: Test that new fields don't break parsing

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | Design complete |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-08 | Architect | Initial design |
