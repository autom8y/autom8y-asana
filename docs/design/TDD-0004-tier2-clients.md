# TDD: Tier 2 Resource Clients

## Metadata
- **TDD ID**: TDD-0004
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-08
- **Last Updated**: 2025-12-08
- **PRD Reference**: [PRD-0001](../requirements/PRD-0001-sdk-extraction.md) (FR-SDK-020, FR-SDK-022, FR-SDK-023, FR-SDK-024, FR-SDK-025, FR-SDK-026, FR-SDK-028)
- **Related TDDs**: [TDD-0001](TDD-0001-sdk-architecture.md), [TDD-0002](TDD-0002-models-pagination.md), [TDD-0003](TDD-0003-tier1-clients.md)
- **Related ADRs**:
  - [ADR-0005](../decisions/ADR-0005-pydantic-model-config.md) - Pydantic v2 with extra="ignore"
  - [ADR-0006](../decisions/ADR-0006-namegid-standalone-model.md) - NameGid as standalone model
  - [ADR-0007](../decisions/ADR-0007-consistent-client-pattern.md) - Consistent client pattern
  - [ADR-0008](../decisions/ADR-0008-webhook-signature-verification.md) - Webhook signature verification
  - [ADR-0009](../decisions/ADR-0009-attachment-multipart-handling.md) - Attachment multipart/form-data handling

## Overview

This TDD defines the design for 7 Tier 2 resource clients: WebhooksClient, TeamsClient, AttachmentsClient, TagsClient, GoalsClient, PortfoliosClient, and StoriesClient. These clients follow the established patterns from TDD-0003 and ADR-0007, with special handling for webhooks (signature verification) and attachments (multipart upload/streaming download).

## Requirements Summary

From PRD-0001:
- **FR-SDK-020**: WebhooksClient - Create, delete, list webhooks; webhook signature verification
- **FR-SDK-022**: TeamsClient - List teams, get team by ID, list team members
- **FR-SDK-023**: AttachmentsClient - Upload, download, delete attachments; list task attachments
- **FR-SDK-024**: TagsClient - Create, read, update, delete tags; add/remove tags from tasks
- **FR-SDK-025**: GoalsClient - Create, read, update goals; list goals; manage goal memberships
- **FR-SDK-026**: PortfoliosClient - Create, read, update portfolios; add/remove projects
- **FR-SDK-028**: StoriesClient - Create comments; list stories on tasks

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
|  | - webhook.py NEW |     | - projects.py (EXISTING)  |                     |
|  | - team.py NEW    |     | - webhooks.py (NEW)       |                     |
|  | - attachment.py  |     | - teams.py (NEW)          |                     |
|  |   (NEW)          |     | - attachments.py (NEW)    |                     |
|  | - tag.py NEW     |     | - tags.py (NEW)           |                     |
|  | - goal.py NEW    |     | - goals.py (NEW)          |                     |
|  | - portfolio.py   |     | - portfolios.py (NEW)     |                     |
|  |   (NEW)          |     | - stories.py (NEW)        |                     |
|  | - story.py NEW   |     +---------------------------+                     |
|  +------------------+                  |                                    |
|          ^                             v                                    |
|          |                  +---------------------------+                   |
|          |                  | transport/                |                   |
|          |                  | - http.py (+ multipart)   |                   |
|          +------------------| - rate_limiter.py         |                   |
|                             +---------------------------+                   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

## Design

### Component Architecture

| Component | Responsibility | File Location |
|-----------|---------------|---------------|
| `Webhook` | Webhook resource model | `models/webhook.py` |
| `Team` | Team resource model | `models/team.py` |
| `Attachment` | Attachment resource model | `models/attachment.py` |
| `Tag` | Tag resource model | `models/tag.py` |
| `Goal` | Goal resource model | `models/goal.py` |
| `Portfolio` | Portfolio resource model | `models/portfolio.py` |
| `Story` | Story/comment resource model | `models/story.py` |
| `WebhooksClient` | Webhook CRUD + signature verification | `clients/webhooks.py` |
| `TeamsClient` | Team operations | `clients/teams.py` |
| `AttachmentsClient` | Attachment upload/download/delete | `clients/attachments.py` |
| `TagsClient` | Tag CRUD + task tagging | `clients/tags.py` |
| `GoalsClient` | Goal CRUD + memberships | `clients/goals.py` |
| `PortfoliosClient` | Portfolio CRUD + project management | `clients/portfolios.py` |
| `StoriesClient` | Story creation and listing | `clients/stories.py` |

### Data Models

#### Webhook Model

```python
# /src/autom8_asana/models/webhook.py

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class WebhookFilter(AsanaResource):
    """Filter for webhook events.

    Determines which events trigger the webhook.

    Example:
        >>> filter = WebhookFilter(resource_type="task", action="changed", fields=["completed"])
    """

    resource_type: str | None = Field(default=None, description="Resource type to filter (task, project, etc.)")
    resource_subtype: str | None = None
    action: str | None = Field(default=None, description="Action to filter (changed, added, removed, etc.)")
    fields: list[str] | None = Field(default=None, description="Fields that trigger the webhook")


class Webhook(AsanaResource):
    """Asana Webhook resource model.

    Webhooks receive notifications when resources change.
    The target URL receives POST requests with event data.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> webhook = Webhook.model_validate(api_response)
        >>> print(f"Webhook {webhook.gid} -> {webhook.target}")
    """

    # Core identification
    resource_type: str | None = Field(default="webhook")

    # Webhook configuration
    target: str | None = Field(default=None, description="URL to receive webhook events")
    active: bool | None = Field(default=None, description="Whether the webhook is active")

    # Resource being watched
    resource: NameGid | None = Field(default=None, description="Resource being watched")

    # Filters
    filters: list[WebhookFilter] | None = Field(default=None, description="Event filters")

    # Timestamps
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
    last_failure_at: str | None = Field(default=None, description="Last failure datetime")
    last_failure_content: str | None = Field(default=None, description="Last failure message")
    last_success_at: str | None = Field(default=None, description="Last success datetime")
```

**Webhook Model Notes:**
- `target` is the URL that receives event POSTs
- `resource` is the object being watched (task, project, etc.)
- `filters` control which events trigger notifications
- Failure tracking fields help debug webhook issues

#### Team Model

```python
# /src/autom8_asana/models/team.py

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Team(AsanaResource):
    """Asana Team resource model.

    Teams are groups of users within an organization workspace.
    Projects can be assigned to teams.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> team = Team.model_validate(api_response)
        >>> print(f"Team: {team.name} in {team.organization.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="team")

    # Basic team fields
    name: str | None = None
    description: str | None = None
    html_description: str | None = None

    # Relationships
    organization: NameGid | None = Field(default=None, description="Organization workspace")

    # Visibility
    visibility: str | None = Field(
        default=None,
        description="Team visibility (secret, request_to_join, public)",
    )

    # Settings
    permalink_url: str | None = None
    edit_team_name_or_description_access_level: str | None = None
    edit_team_visibility_or_trash_team_access_level: str | None = None
    member_invite_management_access_level: str | None = None
    guest_invite_management_access_level: str | None = None
    join_request_management_access_level: str | None = None
    team_member_removal_access_level: str | None = None
```

**Team Model Notes:**
- Teams only exist in organization workspaces
- `visibility` controls how users can join the team
- Access level fields control team administration permissions

#### Attachment Model

```python
# /src/autom8_asana/models/attachment.py

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Attachment(AsanaResource):
    """Asana Attachment resource model.

    Attachments are files attached to tasks. They can be uploaded
    directly or linked from external services.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> attachment = Attachment.model_validate(api_response)
        >>> print(f"File: {attachment.name} ({attachment.size} bytes)")
    """

    # Core identification
    resource_type: str | None = Field(default="attachment")

    # Basic attachment fields
    name: str | None = None

    # File properties
    host: str | None = Field(
        default=None,
        description="Host type (asana, dropbox, gdrive, onedrive, box, vimeo, external)",
    )
    view_url: str | None = Field(default=None, description="URL to view the attachment")
    download_url: str | None = Field(default=None, description="URL to download the file")
    permanent_url: str | None = Field(default=None, description="Permanent URL for the file")

    # File metadata
    size: int | None = Field(default=None, description="File size in bytes")

    # Relationships
    parent: NameGid | None = Field(default=None, description="Parent task")
    created_by: NameGid | None = None

    # Timestamps
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")
```

**Attachment Model Notes:**
- `host` indicates where the file is stored
- `download_url` may be temporary and require authentication
- `size` is only present for directly uploaded files

#### Tag Model

```python
# /src/autom8_asana/models/tag.py

from __future__ import annotations

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Tag(AsanaResource):
    """Asana Tag resource model.

    Tags are labels that can be applied to tasks for organization.
    Tags belong to a workspace and can be applied across projects.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> tag = Tag.model_validate(api_response)
        >>> print(f"Tag: {tag.name} (color: {tag.color})")
    """

    # Core identification
    resource_type: str | None = Field(default="tag")

    # Basic tag fields
    name: str | None = None
    color: str | None = Field(
        default=None,
        description="Tag color (dark-pink, dark-green, dark-blue, etc.)",
    )
    notes: str | None = None

    # Relationships
    workspace: NameGid | None = None

    # Followers
    followers: list[NameGid] | None = None

    # Timestamps
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")

    # URL
    permalink_url: str | None = None
```

**Tag Model Notes:**
- Tags are workspace-scoped, not project-scoped
- `color` uses Asana's predefined color palette
- Tags can have followers who receive notifications

#### Goal Model

```python
# /src/autom8_asana/models/goal.py

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class GoalMetric(AsanaResource):
    """Metric for tracking goal progress.

    Goals can have numeric metrics with current and target values.

    Example:
        >>> metric = GoalMetric.model_validate(api_response)
        >>> progress = metric.current_number_value / metric.target_number_value
    """

    resource_type: str | None = Field(default="goal_metric")
    resource_subtype: str | None = Field(
        default=None,
        description="Metric type (number, percentage, currency)",
    )

    # Metric configuration
    unit: str | None = Field(default=None, description="Unit of measurement")
    precision: int | None = Field(default=None, description="Decimal precision")
    currency_code: str | None = None

    # Values
    current_number_value: float | None = None
    target_number_value: float | None = None
    initial_number_value: float | None = None

    # Progress
    progress_source: str | None = Field(
        default=None,
        description="How progress is calculated (manual, subgoal_progress, etc.)",
    )


class Goal(AsanaResource):
    """Asana Goal resource model.

    Goals track high-level objectives. They can be hierarchical
    (goals can have subgoals) and time-bound.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> goal = Goal.model_validate(api_response)
        >>> print(f"Goal: {goal.name} ({goal.status})")
    """

    # Core identification
    resource_type: str | None = Field(default="goal")

    # Basic goal fields
    name: str | None = None
    notes: str | None = None
    html_notes: str | None = None

    # Status
    status: str | None = Field(
        default=None,
        description="Goal status (on_track, at_risk, off_track, achieved, partial, missed, dropped)",
    )
    is_workspace_level: bool | None = None

    # Time period
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    time_period: NameGid | None = Field(default=None, description="Associated time period")

    # Relationships
    owner: NameGid | None = None
    workspace: NameGid | None = None
    team: NameGid | None = None

    # Followers and likes
    followers: list[NameGid] | None = None
    liked: bool | None = None
    likes: list[NameGid] | None = None
    num_likes: int | None = None

    # Metric tracking
    metric: GoalMetric | None = None
    current_status_update: NameGid | None = None

    # URLs
    permalink_url: str | None = None


class GoalMembership(AsanaResource):
    """Membership of a user or team in a goal.

    Example:
        >>> membership = GoalMembership.model_validate(api_response)
        >>> print(f"{membership.member.name} is {membership.role} of goal")
    """

    resource_type: str | None = Field(default="goal_membership")

    member: NameGid | None = None
    goal: NameGid | None = None
    role: str | None = Field(default=None, description="Member role (owner, editor, commenter)")
```

**Goal Model Notes:**
- Goals can have numeric metrics tracked via `GoalMetric`
- `status` tracks progress against the goal
- Goals can be workspace-level or team-level
- `time_period` links to Asana's time period feature

#### Portfolio Model

```python
# /src/autom8_asana/models/portfolio.py

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Portfolio(AsanaResource):
    """Asana Portfolio resource model.

    Portfolios are collections of projects for high-level tracking.
    They provide rollup status and visibility across multiple projects.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> portfolio = Portfolio.model_validate(api_response)
        >>> print(f"Portfolio: {portfolio.name} by {portfolio.owner.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="portfolio")

    # Basic portfolio fields
    name: str | None = None
    color: str | None = Field(
        default=None,
        description="Portfolio color (dark-pink, dark-green, etc.)",
    )

    # Status
    public: bool | None = None

    # Relationships
    owner: NameGid | None = None
    workspace: NameGid | None = None

    # Members
    members: list[NameGid] | None = None

    # Custom fields (complex structure)
    custom_fields: list[dict[str, Any]] | None = None
    custom_field_settings: list[dict[str, Any]] | None = None

    # Current status
    current_status_update: NameGid | None = None

    # Dates
    due_on: str | None = Field(default=None, description="Due date (YYYY-MM-DD)")
    start_on: str | None = Field(default=None, description="Start date (YYYY-MM-DD)")
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")

    # URLs
    permalink_url: str | None = None
```

**Portfolio Model Notes:**
- Portfolios contain projects (items)
- `custom_fields` and `custom_field_settings` remain as dicts due to complexity
- `public` controls visibility to workspace members

#### Story Model

```python
# /src/autom8_asana/models/story.py

from __future__ import annotations

from typing import Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource
from autom8_asana.models.common import NameGid


class Story(AsanaResource):
    """Asana Story resource model.

    Stories are activity entries on tasks. They can be comments
    (created by users) or system-generated (tracking changes).

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> story = Story.model_validate(api_response)
        >>> if story.resource_subtype == "comment_added":
        ...     print(f"{story.created_by.name}: {story.text}")
    """

    # Core identification
    resource_type: str | None = Field(default="story")
    resource_subtype: str | None = Field(
        default=None,
        description="Story type (comment_added, assigned, due_date_changed, etc.)",
    )

    # Content
    text: str | None = Field(default=None, description="Story text content")
    html_text: str | None = Field(default=None, description="HTML formatted text")

    # Relationships
    target: NameGid | None = Field(default=None, description="Task this story is on")
    created_by: NameGid | None = None

    # Timestamps
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")

    # Editing
    is_editable: bool | None = None
    is_edited: bool | None = None
    is_pinned: bool | None = None

    # Reactions
    liked: bool | None = None
    likes: list[NameGid] | None = None
    num_likes: int | None = None

    # Sticker (for sticker stories)
    sticker_name: str | None = None

    # For system stories, these track what changed
    new_text_value: str | None = None
    old_text_value: str | None = None
    new_name: str | None = None
    old_name: str | None = None
    new_number_value: float | None = None
    old_number_value: float | None = None
    new_enum_value: NameGid | None = None
    old_enum_value: NameGid | None = None
    new_dates: dict[str, Any] | None = None
    old_dates: dict[str, Any] | None = None
    new_resource_subtype: str | None = None
    old_resource_subtype: str | None = None
    assignee: NameGid | None = None
    follower: NameGid | None = None
    new_section: NameGid | None = None
    old_section: NameGid | None = None
    new_approval_status: str | None = None
    old_approval_status: str | None = None
    duplicate_of: NameGid | None = None
    duplicated_from: NameGid | None = None
    task: NameGid | None = None  # For dependency stories
    dependency: NameGid | None = None
    project: NameGid | None = None  # For project stories
    tag: NameGid | None = None  # For tag stories
    custom_field: NameGid | None = None  # For custom field stories
```

**Story Model Notes:**
- `resource_subtype` determines the story type
- Comments have `text` and `html_text`
- System stories have old/new value fields for tracking changes
- Many fields are only present for specific story types

### Client Implementations

All clients follow the established pattern per ADR-0007.

#### WebhooksClient

```python
# /src/autom8_asana/clients/webhooks.py

import hashlib
import hmac
from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.webhook import Webhook


class WebhooksClient(BaseClient):
    """Client for Asana Webhook operations.

    Provides CRUD operations for webhooks and signature verification
    for incoming webhook events.

    Returns typed Webhook models by default. Use raw=True for dict returns.

    Per ADR-0008: Signature verification uses HMAC-SHA256 with the
    webhook secret provided during creation.
    """

    # --- Core Operations ---

    @overload
    async def get_async(
        self,
        webhook_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Webhook: ...

    @overload
    async def get_async(
        self,
        webhook_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]: ...

    async def get_async(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Get a webhook by GID.

        Args:
            webhook_gid: Webhook GID
            raw: If True, return raw dict instead of Webhook model
            opt_fields: Optional fields to include

        Returns:
            Webhook model by default, or dict if raw=True
        """

    def get(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Get a webhook by GID (sync)."""

    @overload
    async def create_async(
        self,
        *,
        resource: str,
        target: str,
        raw: Literal[False] = ...,
        filters: list[dict[str, Any]] | None = ...,
    ) -> Webhook: ...

    @overload
    async def create_async(
        self,
        *,
        resource: str,
        target: str,
        raw: Literal[True],
        filters: list[dict[str, Any]] | None = ...,
    ) -> dict[str, Any]: ...

    async def create_async(
        self,
        *,
        resource: str,
        target: str,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Create a webhook.

        Note: After creation, Asana sends a handshake request to the target
        URL with X-Hook-Secret header. The target must respond with this
        secret in the X-Hook-Secret response header.

        Args:
            resource: GID of the resource to watch (task, project, etc.)
            target: URL to receive webhook events
            raw: If True, return raw dict instead of Webhook model
            filters: Optional event filters

        Returns:
            Webhook model by default, or dict if raw=True
        """

    def create(
        self,
        *,
        resource: str,
        target: str,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Create a webhook (sync)."""

    async def update_async(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Update a webhook.

        Args:
            webhook_gid: Webhook GID
            raw: If True, return raw dict instead of Webhook model
            filters: New event filters

        Returns:
            Webhook model by default, or dict if raw=True
        """

    def update(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Update a webhook (sync)."""

    async def delete_async(self, webhook_gid: str) -> None:
        """Delete a webhook.

        Args:
            webhook_gid: Webhook GID
        """

    def delete(self, webhook_gid: str) -> None:
        """Delete a webhook (sync)."""

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        resource: str | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Webhook]:
        """List webhooks in a workspace.

        Args:
            workspace_gid: Workspace GID
            resource: Optional filter by resource GID
            opt_fields: Fields to include in response
            limit: Number of items per page

        Returns:
            PageIterator[Webhook] - async iterator over Webhook objects
        """

    # --- Signature Verification ---

    @staticmethod
    def verify_signature(
        request_body: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """Verify the signature of an incoming webhook event.

        Per ADR-0008: Uses HMAC-SHA256 to verify the X-Hook-Signature header.

        Args:
            request_body: Raw request body bytes
            signature: Value of X-Hook-Signature header
            secret: Webhook secret (from X-Hook-Secret during handshake)

        Returns:
            True if signature is valid, False otherwise

        Example:
            >>> is_valid = WebhooksClient.verify_signature(
            ...     request_body=request.body,
            ...     signature=request.headers['X-Hook-Signature'],
            ...     secret=stored_webhook_secret,
            ... )
            >>> if not is_valid:
            ...     raise ValueError("Invalid webhook signature")
        """
        computed = hmac.new(
            secret.encode('utf-8'),
            request_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    @staticmethod
    def extract_handshake_secret(headers: dict[str, str]) -> str | None:
        """Extract the webhook secret from handshake request headers.

        During webhook creation, Asana sends a handshake request with
        X-Hook-Secret header. This secret must be stored and used for
        signature verification.

        Args:
            headers: Request headers (case-insensitive lookup)

        Returns:
            The secret string, or None if not present
        """
        # Case-insensitive header lookup
        for key, value in headers.items():
            if key.lower() == 'x-hook-secret':
                return value
        return None
```

**Asana API Endpoints for Webhooks:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/webhooks/{gid}` |
| Create | POST | `/webhooks` |
| Update | PUT | `/webhooks/{gid}` |
| Delete | DELETE | `/webhooks/{gid}` |
| List for Workspace | GET | `/webhooks?workspace={gid}` |

#### TeamsClient

```python
# /src/autom8_asana/clients/teams.py

class TeamsClient(BaseClient):
    """Client for Asana Team operations.

    Teams exist only in organization workspaces.
    Returns typed Team models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        team_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Team | dict[str, Any]:
        """Get a team by GID."""

    def get(self, team_gid: str, ...) -> Team | dict[str, Any]:
        """Get a team by GID (sync)."""

    def list_for_user_async(
        self,
        user_gid: str,
        *,
        organization: str | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Team]:
        """List teams for a user.

        Args:
            user_gid: User GID (or 'me' for current user)
            organization: Filter by organization workspace GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Team]
        """

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Team]:
        """List teams in an organization workspace.

        Args:
            workspace_gid: Organization workspace GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Team]
        """

    def list_users_async(
        self,
        team_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[User]:
        """List users in a team.

        Args:
            team_gid: Team GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[User] - team members
        """

    async def add_user_async(
        self,
        team_gid: str,
        *,
        user: str,
    ) -> TeamMembership | dict[str, Any]:
        """Add a user to a team.

        Args:
            team_gid: Team GID
            user: User GID to add

        Returns:
            TeamMembership result
        """

    def add_user(self, team_gid: str, *, user: str) -> TeamMembership | dict[str, Any]:
        """Add a user to a team (sync)."""

    async def remove_user_async(
        self,
        team_gid: str,
        *,
        user: str,
    ) -> None:
        """Remove a user from a team.

        Args:
            team_gid: Team GID
            user: User GID to remove
        """

    def remove_user(self, team_gid: str, *, user: str) -> None:
        """Remove a user from a team (sync)."""
```

**Asana API Endpoints for Teams:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/teams/{gid}` |
| List for User | GET | `/users/{gid}/teams` |
| List for Workspace | GET | `/workspaces/{gid}/teams` |
| List Users | GET | `/teams/{gid}/users` |
| Add User | POST | `/teams/{gid}/addUser` |
| Remove User | POST | `/teams/{gid}/removeUser` |

#### AttachmentsClient

```python
# /src/autom8_asana/clients/attachments.py

from pathlib import Path
from typing import BinaryIO

class AttachmentsClient(BaseClient):
    """Client for Asana Attachment operations.

    Supports file upload via multipart/form-data and streaming download.
    Per ADR-0009: Uses httpx's streaming capabilities.

    Returns typed Attachment models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        attachment_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Attachment | dict[str, Any]:
        """Get an attachment by GID."""

    def get(self, attachment_gid: str, ...) -> Attachment | dict[str, Any]:
        """Get an attachment by GID (sync)."""

    async def delete_async(self, attachment_gid: str) -> None:
        """Delete an attachment."""

    def delete(self, attachment_gid: str) -> None:
        """Delete an attachment (sync)."""

    def list_for_task_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Attachment]:
        """List attachments on a task.

        Args:
            task_gid: Task GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Attachment]
        """

    # --- Upload Operations (per ADR-0009) ---

    @overload
    async def upload_async(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: Literal[False] = ...,
    ) -> Attachment: ...

    @overload
    async def upload_async(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: Literal[True],
    ) -> dict[str, Any]: ...

    async def upload_async(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: bool = False,
    ) -> Attachment | dict[str, Any]:
        """Upload a file attachment to a task.

        Uses multipart/form-data encoding per Asana API requirements.
        Per ADR-0009: Streams file content to avoid memory issues.

        Args:
            parent: Parent task GID
            file: File-like object with read() method
            name: Filename for the attachment
            raw: If True, return raw dict instead of Attachment model

        Returns:
            Attachment model by default, or dict if raw=True

        Example:
            >>> with open('report.pdf', 'rb') as f:
            ...     attachment = await client.attachments.upload_async(
            ...         parent="123",
            ...         file=f,
            ...         name="report.pdf",
            ...     )
        """

    def upload(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: bool = False,
    ) -> Attachment | dict[str, Any]:
        """Upload a file attachment (sync)."""

    async def upload_from_path_async(
        self,
        *,
        parent: str,
        path: Path | str,
        name: str | None = None,
        raw: bool = False,
    ) -> Attachment | dict[str, Any]:
        """Upload a file from filesystem path.

        Convenience method that handles file opening.

        Args:
            parent: Parent task GID
            path: Path to file
            name: Optional filename (defaults to path basename)
            raw: If True, return raw dict

        Returns:
            Attachment model by default, or dict if raw=True
        """

    def upload_from_path(
        self,
        *,
        parent: str,
        path: Path | str,
        name: str | None = None,
        raw: bool = False,
    ) -> Attachment | dict[str, Any]:
        """Upload a file from path (sync)."""

    async def create_external_async(
        self,
        *,
        parent: str,
        url: str,
        name: str,
        raw: bool = False,
    ) -> Attachment | dict[str, Any]:
        """Create an external attachment (link).

        Creates an attachment that links to an external URL instead
        of uploading file content.

        Args:
            parent: Parent task GID
            url: External URL
            name: Display name for the attachment
            raw: If True, return raw dict

        Returns:
            Attachment model by default, or dict if raw=True
        """

    def create_external(
        self,
        *,
        parent: str,
        url: str,
        name: str,
        raw: bool = False,
    ) -> Attachment | dict[str, Any]:
        """Create an external attachment (sync)."""

    # --- Download Operations ---

    async def download_async(
        self,
        attachment_gid: str,
        *,
        destination: Path | str | BinaryIO,
    ) -> Path | None:
        """Download an attachment.

        Per ADR-0009: Uses streaming download to handle large files.

        Args:
            attachment_gid: Attachment GID
            destination: Path to save file, or file-like object

        Returns:
            Path to downloaded file (if destination was path), or None

        Raises:
            AsanaError: If attachment has no download URL

        Example:
            >>> await client.attachments.download_async(
            ...     "attachment_gid",
            ...     destination="/tmp/report.pdf",
            ... )
        """

    def download(
        self,
        attachment_gid: str,
        *,
        destination: Path | str | BinaryIO,
    ) -> Path | None:
        """Download an attachment (sync)."""
```

**Asana API Endpoints for Attachments:**

| Operation | HTTP Method | Endpoint | Content-Type |
|-----------|-------------|----------|--------------|
| Get | GET | `/attachments/{gid}` | application/json |
| Delete | DELETE | `/attachments/{gid}` | application/json |
| List for Task | GET | `/tasks/{gid}/attachments` | application/json |
| Upload | POST | `/tasks/{gid}/attachments` | multipart/form-data |

#### TagsClient

```python
# /src/autom8_asana/clients/tags.py

class TagsClient(BaseClient):
    """Client for Asana Tag operations.

    Returns typed Tag models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        tag_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Tag | dict[str, Any]:
        """Get a tag by GID."""

    def get(self, tag_gid: str, ...) -> Tag | dict[str, Any]:
        """Get a tag by GID (sync)."""

    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        color: str | None = None,
        notes: str | None = None,
    ) -> Tag | dict[str, Any]:
        """Create a tag.

        Args:
            workspace: Workspace GID
            name: Tag name
            raw: If True, return raw dict
            color: Optional tag color
            notes: Optional tag description

        Returns:
            Tag model by default, or dict if raw=True
        """

    def create(self, *, workspace: str, name: str, ...) -> Tag | dict[str, Any]:
        """Create a tag (sync)."""

    async def update_async(
        self,
        tag_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Tag | dict[str, Any]:
        """Update a tag."""

    def update(self, tag_gid: str, ...) -> Tag | dict[str, Any]:
        """Update a tag (sync)."""

    async def delete_async(self, tag_gid: str) -> None:
        """Delete a tag."""

    def delete(self, tag_gid: str) -> None:
        """Delete a tag (sync)."""

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Tag]:
        """List tags in a workspace."""

    def list_for_task_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Tag]:
        """List tags on a task."""

    # --- Task Tagging Operations ---

    async def add_to_task_async(
        self,
        task_gid: str,
        *,
        tag: str,
    ) -> None:
        """Add a tag to a task.

        Args:
            task_gid: Task GID
            tag: Tag GID to add
        """

    def add_to_task(self, task_gid: str, *, tag: str) -> None:
        """Add a tag to a task (sync)."""

    async def remove_from_task_async(
        self,
        task_gid: str,
        *,
        tag: str,
    ) -> None:
        """Remove a tag from a task.

        Args:
            task_gid: Task GID
            tag: Tag GID to remove
        """

    def remove_from_task(self, task_gid: str, *, tag: str) -> None:
        """Remove a tag from a task (sync)."""
```

**Asana API Endpoints for Tags:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/tags/{gid}` |
| Create | POST | `/tags` |
| Update | PUT | `/tags/{gid}` |
| Delete | DELETE | `/tags/{gid}` |
| List for Workspace | GET | `/workspaces/{gid}/tags` |
| List for Task | GET | `/tasks/{gid}/tags` |
| Add to Task | POST | `/tasks/{gid}/addTag` |
| Remove from Task | POST | `/tasks/{gid}/removeTag` |

#### GoalsClient

```python
# /src/autom8_asana/clients/goals.py

class GoalsClient(BaseClient):
    """Client for Asana Goal operations.

    Goals support hierarchical organization (subgoals).
    Returns typed Goal models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Goal | dict[str, Any]:
        """Get a goal by GID."""

    def get(self, goal_gid: str, ...) -> Goal | dict[str, Any]:
        """Get a goal by GID (sync)."""

    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        due_on: str | None = None,
        start_on: str | None = None,
        owner: str | None = None,
        team: str | None = None,
        time_period: str | None = None,
        notes: str | None = None,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Create a goal.

        Args:
            workspace: Workspace GID
            name: Goal name
            raw: If True, return raw dict
            due_on: Due date (YYYY-MM-DD)
            start_on: Start date (YYYY-MM-DD)
            owner: Owner user GID
            team: Team GID (for team goals)
            time_period: Time period GID
            notes: Goal description

        Returns:
            Goal model by default, or dict if raw=True
        """

    def create(self, *, workspace: str, name: str, ...) -> Goal | dict[str, Any]:
        """Create a goal (sync)."""

    async def update_async(
        self,
        goal_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Goal | dict[str, Any]:
        """Update a goal."""

    def update(self, goal_gid: str, ...) -> Goal | dict[str, Any]:
        """Update a goal (sync)."""

    async def delete_async(self, goal_gid: str) -> None:
        """Delete a goal."""

    def delete(self, goal_gid: str) -> None:
        """Delete a goal (sync)."""

    def list_async(
        self,
        *,
        workspace: str | None = None,
        team: str | None = None,
        portfolio: str | None = None,
        project: str | None = None,
        is_workspace_level: bool | None = None,
        time_periods: list[str] | None = None,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Goal]:
        """List goals.

        At least one of workspace, team, portfolio, or project is required.

        Args:
            workspace: Filter by workspace
            team: Filter by team
            portfolio: Filter by portfolio
            project: Filter by supporting project
            is_workspace_level: Filter workspace-level goals
            time_periods: Filter by time period GIDs
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Goal]
        """

    # --- Subgoals ---

    def list_subgoals_async(
        self,
        goal_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Goal]:
        """List subgoals of a goal.

        Args:
            goal_gid: Parent goal GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Goal]
        """

    async def add_subgoal_async(
        self,
        goal_gid: str,
        *,
        subgoal: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> Goal | dict[str, Any]:
        """Add a subgoal to a goal.

        Args:
            goal_gid: Parent goal GID
            subgoal: Subgoal GID to add
            insert_before: Subgoal GID to insert before
            insert_after: Subgoal GID to insert after

        Returns:
            Updated parent goal
        """

    def add_subgoal(self, goal_gid: str, *, subgoal: str, ...) -> Goal | dict[str, Any]:
        """Add a subgoal (sync)."""

    async def remove_subgoal_async(
        self,
        goal_gid: str,
        *,
        subgoal: str,
    ) -> None:
        """Remove a subgoal from a goal.

        Args:
            goal_gid: Parent goal GID
            subgoal: Subgoal GID to remove
        """

    def remove_subgoal(self, goal_gid: str, *, subgoal: str) -> None:
        """Remove a subgoal (sync)."""

    # --- Supporting Resources ---

    async def add_supporting_work_async(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
        contribution_weight: float | None = None,
    ) -> Goal | dict[str, Any]:
        """Add supporting work (project/portfolio) to a goal.

        Args:
            goal_gid: Goal GID
            supporting_resource: Project or portfolio GID
            contribution_weight: Optional weight (0.0 to 1.0)

        Returns:
            Updated goal
        """

    def add_supporting_work(
        self, goal_gid: str, *, supporting_resource: str, ...
    ) -> Goal | dict[str, Any]:
        """Add supporting work (sync)."""

    async def remove_supporting_work_async(
        self,
        goal_gid: str,
        *,
        supporting_resource: str,
    ) -> None:
        """Remove supporting work from a goal."""

    def remove_supporting_work(self, goal_gid: str, *, supporting_resource: str) -> None:
        """Remove supporting work (sync)."""

    # --- Followers ---

    async def add_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
    ) -> Goal | dict[str, Any]:
        """Add followers to a goal.

        Args:
            goal_gid: Goal GID
            followers: List of user GIDs

        Returns:
            Updated goal
        """

    def add_followers(self, goal_gid: str, *, followers: list[str]) -> Goal | dict[str, Any]:
        """Add followers (sync)."""

    async def remove_followers_async(
        self,
        goal_gid: str,
        *,
        followers: list[str],
    ) -> Goal | dict[str, Any]:
        """Remove followers from a goal."""

    def remove_followers(
        self, goal_gid: str, *, followers: list[str]
    ) -> Goal | dict[str, Any]:
        """Remove followers (sync)."""
```

**Asana API Endpoints for Goals:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/goals/{gid}` |
| Create | POST | `/goals` |
| Update | PUT | `/goals/{gid}` |
| Delete | DELETE | `/goals/{gid}` |
| List | GET | `/goals` |
| List Subgoals | GET | `/goals/{gid}/subgoals` |
| Add Subgoal | POST | `/goals/{gid}/addSubgoal` |
| Remove Subgoal | POST | `/goals/{gid}/removeSubgoal` |
| Add Supporting | POST | `/goals/{gid}/addSupportingRelationship` |
| Remove Supporting | POST | `/goals/{gid}/removeSupportingRelationship` |
| Add Followers | POST | `/goals/{gid}/addFollowers` |
| Remove Followers | POST | `/goals/{gid}/removeFollowers` |

#### PortfoliosClient

```python
# /src/autom8_asana/clients/portfolios.py

class PortfoliosClient(BaseClient):
    """Client for Asana Portfolio operations.

    Portfolios contain projects for high-level tracking.
    Returns typed Portfolio models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Portfolio | dict[str, Any]:
        """Get a portfolio by GID."""

    def get(self, portfolio_gid: str, ...) -> Portfolio | dict[str, Any]:
        """Get a portfolio by GID (sync)."""

    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        raw: bool = False,
        color: str | None = None,
        public: bool | None = None,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Create a portfolio.

        Args:
            workspace: Workspace GID
            name: Portfolio name
            raw: If True, return raw dict
            color: Optional color
            public: Whether portfolio is public

        Returns:
            Portfolio model by default, or dict if raw=True
        """

    def create(self, *, workspace: str, name: str, ...) -> Portfolio | dict[str, Any]:
        """Create a portfolio (sync)."""

    async def update_async(
        self,
        portfolio_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> Portfolio | dict[str, Any]:
        """Update a portfolio."""

    def update(self, portfolio_gid: str, ...) -> Portfolio | dict[str, Any]:
        """Update a portfolio (sync)."""

    async def delete_async(self, portfolio_gid: str) -> None:
        """Delete a portfolio."""

    def delete(self, portfolio_gid: str) -> None:
        """Delete a portfolio (sync)."""

    def list_async(
        self,
        *,
        workspace: str,
        owner: str,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Portfolio]:
        """List portfolios.

        Args:
            workspace: Workspace GID
            owner: Owner user GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Portfolio]
        """

    # --- Project Management ---

    def list_items_async(
        self,
        portfolio_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Project]:
        """List projects in a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Project]
        """

    async def add_item_async(
        self,
        portfolio_gid: str,
        *,
        item: str,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> None:
        """Add a project to a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            item: Project GID to add
            insert_before: Project GID to insert before
            insert_after: Project GID to insert after
        """

    def add_item(
        self, portfolio_gid: str, *, item: str, ...
    ) -> None:
        """Add a project to a portfolio (sync)."""

    async def remove_item_async(
        self,
        portfolio_gid: str,
        *,
        item: str,
    ) -> None:
        """Remove a project from a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            item: Project GID to remove
        """

    def remove_item(self, portfolio_gid: str, *, item: str) -> None:
        """Remove a project from a portfolio (sync)."""

    # --- Members ---

    async def add_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
    ) -> Portfolio | dict[str, Any]:
        """Add members to a portfolio.

        Args:
            portfolio_gid: Portfolio GID
            members: List of user GIDs

        Returns:
            Updated portfolio
        """

    def add_members(
        self, portfolio_gid: str, *, members: list[str]
    ) -> Portfolio | dict[str, Any]:
        """Add members (sync)."""

    async def remove_members_async(
        self,
        portfolio_gid: str,
        *,
        members: list[str],
    ) -> Portfolio | dict[str, Any]:
        """Remove members from a portfolio."""

    def remove_members(
        self, portfolio_gid: str, *, members: list[str]
    ) -> Portfolio | dict[str, Any]:
        """Remove members (sync)."""

    # --- Custom Fields ---

    async def add_custom_field_setting_async(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
        is_important: bool | None = None,
    ) -> None:
        """Add a custom field to a portfolio."""

    def add_custom_field_setting(
        self, portfolio_gid: str, *, custom_field: str, ...
    ) -> None:
        """Add a custom field (sync)."""

    async def remove_custom_field_setting_async(
        self,
        portfolio_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Remove a custom field from a portfolio."""

    def remove_custom_field_setting(
        self, portfolio_gid: str, *, custom_field: str
    ) -> None:
        """Remove a custom field (sync)."""
```

**Asana API Endpoints for Portfolios:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/portfolios/{gid}` |
| Create | POST | `/portfolios` |
| Update | PUT | `/portfolios/{gid}` |
| Delete | DELETE | `/portfolios/{gid}` |
| List | GET | `/portfolios` |
| List Items | GET | `/portfolios/{gid}/items` |
| Add Item | POST | `/portfolios/{gid}/addItem` |
| Remove Item | POST | `/portfolios/{gid}/removeItem` |
| Add Members | POST | `/portfolios/{gid}/addMembers` |
| Remove Members | POST | `/portfolios/{gid}/removeMembers` |
| Add Custom Field | POST | `/portfolios/{gid}/addCustomFieldSetting` |
| Remove Custom Field | POST | `/portfolios/{gid}/removeCustomFieldSetting` |

#### StoriesClient

```python
# /src/autom8_asana/clients/stories.py

class StoriesClient(BaseClient):
    """Client for Asana Story operations.

    Stories include comments and system-generated activity.
    Returns typed Story models by default. Use raw=True for dict returns.
    """

    async def get_async(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Story | dict[str, Any]:
        """Get a story by GID."""

    def get(self, story_gid: str, ...) -> Story | dict[str, Any]:
        """Get a story by GID (sync)."""

    async def update_async(
        self,
        story_gid: str,
        *,
        raw: bool = False,
        text: str | None = None,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Update a story (comment only).

        Only comments (resource_subtype=comment_added) can be updated.

        Args:
            story_gid: Story GID
            raw: If True, return raw dict
            text: New text content
            html_text: New HTML content
            is_pinned: Whether to pin the comment

        Returns:
            Story model by default, or dict if raw=True
        """

    def update(self, story_gid: str, ...) -> Story | dict[str, Any]:
        """Update a story (sync)."""

    async def delete_async(self, story_gid: str) -> None:
        """Delete a story (comment only).

        Only comments can be deleted. System stories cannot be deleted.
        """

    def delete(self, story_gid: str) -> None:
        """Delete a story (sync)."""

    def list_for_task_async(
        self,
        task_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[Story]:
        """List stories on a task.

        Returns both comments and system activity.

        Args:
            task_gid: Task GID
            opt_fields: Fields to include
            limit: Items per page

        Returns:
            PageIterator[Story]
        """

    # --- Comment Creation ---

    @overload
    async def create_comment_async(
        self,
        *,
        task: str,
        text: str,
        raw: Literal[False] = ...,
    ) -> Story: ...

    @overload
    async def create_comment_async(
        self,
        *,
        task: str,
        text: str,
        raw: Literal[True],
    ) -> dict[str, Any]: ...

    async def create_comment_async(
        self,
        *,
        task: str,
        text: str,
        raw: bool = False,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Create a comment on a task.

        Args:
            task: Task GID
            text: Comment text
            raw: If True, return raw dict
            html_text: Optional HTML formatted text
            is_pinned: Whether to pin the comment

        Returns:
            Story model by default, or dict if raw=True

        Example:
            >>> comment = await client.stories.create_comment_async(
            ...     task="123",
            ...     text="Great progress on this task!",
            ... )
        """

    def create_comment(
        self,
        *,
        task: str,
        text: str,
        raw: bool = False,
        html_text: str | None = None,
        is_pinned: bool | None = None,
    ) -> Story | dict[str, Any]:
        """Create a comment on a task (sync)."""
```

**Asana API Endpoints for Stories:**

| Operation | HTTP Method | Endpoint |
|-----------|-------------|----------|
| Get | GET | `/stories/{gid}` |
| Update | PUT | `/stories/{gid}` |
| Delete | DELETE | `/stories/{gid}` |
| List for Task | GET | `/tasks/{gid}/stories` |
| Create Comment | POST | `/tasks/{gid}/stories` |

### Data Flow

#### Webhook Signature Verification

```
Asana                Webhook Handler          WebhooksClient
  |                        |                        |
  | POST /webhook          |                        |
  | X-Hook-Signature: abc  |                        |
  |----------------------->|                        |
  |                        | verify_signature(body, sig, secret)
  |                        |----------------------->|
  |                        |                        | HMAC-SHA256
  |                        |                        | compare_digest
  |                        | True/False             |
  |                        |<-----------------------|
  |                        |                        |
  | (process if valid)     |                        |
```

#### Attachment Upload (Multipart)

```
User Code           AttachmentsClient         AsyncHTTPClient          Asana
    |                      |                        |                    |
    | upload_async(parent, file, name)              |                    |
    |--------------------->|                        |                    |
    |                      | POST /tasks/{gid}/attachments              |
    |                      | Content-Type: multipart/form-data          |
    |                      | Body: file + metadata  |                    |
    |                      |----------------------->|                    |
    |                      |                        | (stream chunks)    |
    |                      |                        |------------------->|
    |                      |                        | {"data": {...}}    |
    |                      |                        |<-------------------|
    |                      | Attachment             |                    |
    |<---------------------|                        |                    |
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Webhook signature | HMAC-SHA256 | Asana uses this algorithm | ADR-0008 |
| Signature method | Static method | No client state needed, pure function | ADR-0008 |
| Attachment upload | multipart/form-data | Asana API requirement | ADR-0009 |
| File streaming | httpx streaming | Memory efficiency for large files | ADR-0009 |
| External attachments | Separate method | Different API semantics | ADR-0009 |
| Story comments | create_comment method | Clearer than generic create | N/A |
| Goal hierarchy | Separate subgoal methods | Matches Asana API structure | N/A |
| Portfolio items | Project type | Items are always projects | N/A |

## Complexity Assessment

**Level**: MODULE

**Justification**:
- Each client is self-contained with clear responsibilities
- Follows established patterns from Tier 1 (ADR-0007)
- Special handling (webhooks, attachments) is encapsulated
- No new protocols or abstractions beyond multipart support
- Clean API boundaries between clients

Special complexity notes:
1. **WebhooksClient**: Signature verification is a static utility
2. **AttachmentsClient**: Multipart requires transport layer enhancement
3. **GoalsClient**: More operations due to hierarchical nature

## Implementation Plan

### Phase 1: Models (3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Create `models/webhook.py` | None | 20min |
| Create `models/team.py` | None | 15min |
| Create `models/attachment.py` | None | 15min |
| Create `models/tag.py` | None | 15min |
| Create `models/goal.py` | None | 30min |
| Create `models/portfolio.py` | None | 20min |
| Create `models/story.py` | None | 30min |
| Unit tests for all models | Models | 45min |

**Exit Criteria**: All models validate against sample API responses.

### Phase 2: Simple Clients (3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `TeamsClient` | Team model | 40min |
| Implement `TagsClient` | Tag model | 40min |
| Implement `StoriesClient` | Story model | 30min |
| Unit tests for simple clients | Clients | 70min |

**Exit Criteria**: Basic operations pass unit tests.

### Phase 3: WebhooksClient (2 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `WebhooksClient` CRUD | Webhook model | 45min |
| Implement signature verification | None | 30min |
| Unit tests | Client | 45min |

**Exit Criteria**: Webhook CRUD and signature verification pass tests.

### Phase 4: AttachmentsClient (3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Add multipart support to transport | AsyncHTTPClient | 60min |
| Implement `AttachmentsClient` | Attachment model | 45min |
| Implement download streaming | AsyncHTTPClient | 30min |
| Unit tests | Client | 45min |

**Exit Criteria**: Upload and download pass tests with various file sizes.

### Phase 5: Complex Clients (3 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Implement `GoalsClient` | Goal model | 60min |
| Implement `PortfoliosClient` | Portfolio model | 50min |
| Unit tests | Clients | 70min |

**Exit Criteria**: All CRUD and relationship operations pass tests.

### Phase 6: Integration and Export (1.5 hours)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Update `models/__init__.py` exports | All models | 10min |
| Update `clients/__init__.py` exports | All clients | 10min |
| Update AsanaClient facade | All clients | 20min |
| Integration tests | All components | 50min |

**Exit Criteria**: All 7 clients integrated, 600+ tests pass.

**Total Estimate**: 15.5 hours

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Multipart upload complexity | High | Medium | Use httpx built-in multipart support |
| Large file memory issues | Medium | Medium | Streaming upload/download |
| Webhook handshake failures | Medium | Low | Clear documentation, helper methods |
| Goal API complexity | Low | Medium | Start with core operations, add features incrementally |
| Story field explosion | Low | Low | Only include common fields, rest via opt_fields |

## Observability

### Logging

- **DEBUG**: All client operations logged via `_log_operation()`
- **INFO**: File upload/download sizes, batch operations
- **WARNING**: Webhook signature failures (not errors to avoid DOS)
- **ERROR**: API errors, upload failures with context

### Metrics (future)

- `asana_client_requests_total{client, operation}` (counter)
- `asana_attachment_bytes_total{direction}` (counter for upload/download)
- `asana_webhook_verifications_total{result}` (counter for valid/invalid)

## Testing Strategy

### Unit Testing

- **Models**: Validation, serialization, extra field handling
- **Clients**: Mock HTTP responses, verify correct endpoints called
- **Webhook signature**: Known test vectors
- **Multipart**: Verify correct Content-Type and boundary handling

### Integration Testing

- **Live API**: Optional tests against real Asana API
- **File upload**: Small and large file handling
- **Webhook**: End-to-end with mock server

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
