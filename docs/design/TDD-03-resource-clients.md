# TDD-03: Resource Client Architecture

> Consolidated Technical Design Document covering Tier 1 and Tier 2 client implementations for all Asana resource types.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: TDD-0003 (Tier 1 Clients), TDD-0004 (Tier 2 Clients)
- **Related ADRs**:
  - [ADR-0034](../../decisions/ADR-0034-http-transport-integration.md) - HTTP Transport & Client Pattern
  - [ADR-0035](../../decisions/ADR-0035-specialized-protocol-handling.md) - Webhooks & Attachments Protocol

---

## Overview

This document defines the complete resource client architecture for the autom8_asana SDK. Resource clients provide typed access to all Asana API resources, organized into two tiers based on implementation priority and complexity.

**Tier 1 Clients** (Core Operations):
- ProjectsClient, SectionsClient, CustomFieldsClient, UsersClient, WorkspacesClient

**Tier 2 Clients** (Extended Operations):
- WebhooksClient, TeamsClient, AttachmentsClient, TagsClient, GoalsClient, PortfoliosClient, StoriesClient

All clients follow the established pattern from ADR-0034:
- Async-first methods with `_async` suffix
- Sync wrappers using `@sync_wrapper` decorator
- `raw=True` parameter for dict fallback
- Type overloads for correct return type inference
- PageIterator for list operations

---

## Tier Architecture

### Design Principles

| Principle | Implementation |
|-----------|----------------|
| Async-first | Primary methods are async; sync wrappers provided |
| Type safety | Typed models by default; `raw=True` for dict fallback |
| Lazy pagination | PageIterator for memory-efficient list operations |
| Consistent API | All clients follow identical patterns |
| Extra field tolerance | Pydantic `extra="ignore"` handles API evolution |

### System Context

```
                              autom8_asana SDK
+-----------------------------------------------------------------------------+
|                                                                             |
|  +------------------+     +---------------------------+                     |
|  | models/          |     | clients/                  |                     |
|  |                  |     |                           |                     |
|  | - base.py        |<----| - base.py (BaseClient)    |                     |
|  | - common.py      |     | - tasks.py                |                     |
|  | - project.py     |     | - projects.py             |                     |
|  | - section.py     |     | - sections.py             |                     |
|  | - custom_field.py|     | - custom_fields.py        |                     |
|  | - user.py        |     | - users.py                |                     |
|  | - workspace.py   |     | - workspaces.py           |                     |
|  | - webhook.py     |     | - webhooks.py             |                     |
|  | - team.py        |     | - teams.py                |                     |
|  | - attachment.py  |     | - attachments.py          |                     |
|  | - tag.py         |     | - tags.py                 |                     |
|  | - goal.py        |     | - goals.py                |                     |
|  | - portfolio.py   |     | - portfolios.py           |                     |
|  | - story.py       |     | - stories.py              |                     |
|  +------------------+     +---------------------------+                     |
|          ^                             |                                    |
|          |                             v                                    |
|          |                  +---------------------------+                   |
|          |                  | transport/                |                   |
|          |                  | - http.py (+ multipart)   |                   |
|          +------------------| - rate_limiter.py         |                   |
|                             +---------------------------+                   |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## Tier 1 Clients

Tier 1 clients cover core Asana resources required for basic SDK parity.

### ProjectsClient

**Responsibility**: Project CRUD operations and membership management.

```python
class ProjectsClient(BaseClient):
    """Client for Asana Project operations."""

    # Core CRUD
    async def get_async(self, project_gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Project | dict
    async def create_async(self, *, name: str, workspace: str, raw: bool = False, **kwargs) -> Project | dict
    async def update_async(self, project_gid: str, *, raw: bool = False, **kwargs) -> Project | dict
    async def delete_async(self, project_gid: str) -> None
    def list_async(self, *, workspace: str | None = None, team: str | None = None, ...) -> PageIterator[Project]

    # Membership operations
    async def add_members_async(self, project_gid: str, *, members: list[str]) -> Project | dict
    async def remove_members_async(self, project_gid: str, *, members: list[str]) -> Project | dict

    # Convenience
    def get_sections_async(self, project_gid: str, ...) -> PageIterator[Section]
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/projects/{gid}` |
| Create | POST | `/projects` |
| Update | PUT | `/projects/{gid}` |
| Delete | DELETE | `/projects/{gid}` |
| List | GET | `/projects` |
| Add Members | POST | `/projects/{gid}/addMembers` |
| Remove Members | POST | `/projects/{gid}/removeMembers` |

### SectionsClient

**Responsibility**: Section CRUD and task movement within projects.

```python
class SectionsClient(BaseClient):
    """Client for Asana Section operations."""

    # Core CRUD
    async def get_async(self, section_gid: str, ...) -> Section | dict
    async def create_async(self, *, name: str, project: str, insert_before: str | None = None, ...) -> Section | dict
    async def update_async(self, section_gid: str, ...) -> Section | dict
    async def delete_async(self, section_gid: str) -> None
    def list_for_project_async(self, project_gid: str, ...) -> PageIterator[Section]

    # Task movement
    async def add_task_async(self, section_gid: str, *, task: str, insert_before: str | None = None, ...) -> None
    async def insert_section_async(self, project_gid: str, *, section: str, before_section: str | None = None, ...) -> None
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/sections/{gid}` |
| Create | POST | `/projects/{project_gid}/sections` |
| Update | PUT | `/sections/{gid}` |
| Delete | DELETE | `/sections/{gid}` |
| List for Project | GET | `/projects/{project_gid}/sections` |
| Add Task | POST | `/sections/{gid}/addTask` |
| Insert Section | POST | `/projects/{project_gid}/sections/insert` |

### CustomFieldsClient

**Responsibility**: Custom field CRUD, enum options, and project settings.

```python
class CustomFieldsClient(BaseClient):
    """Client for Asana Custom Field operations."""

    # Core CRUD
    async def get_async(self, custom_field_gid: str, ...) -> CustomField | dict
    async def create_async(self, *, workspace: str, name: str, resource_subtype: str, ...) -> CustomField | dict
    async def update_async(self, custom_field_gid: str, ...) -> CustomField | dict
    async def delete_async(self, custom_field_gid: str) -> None
    def list_for_workspace_async(self, workspace_gid: str, ...) -> PageIterator[CustomField]

    # Enum options
    async def create_enum_option_async(self, custom_field_gid: str, *, name: str, color: str | None = None, ...) -> CustomFieldEnumOption | dict
    async def update_enum_option_async(self, enum_option_gid: str, ...) -> CustomFieldEnumOption | dict

    # Project settings
    def get_settings_for_project_async(self, project_gid: str, ...) -> PageIterator[CustomFieldSetting]
    async def add_to_project_async(self, project_gid: str, *, custom_field: str, is_important: bool | None = None, ...) -> CustomFieldSetting | dict
    async def remove_from_project_async(self, project_gid: str, *, custom_field: str) -> None
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/custom_fields/{gid}` |
| Create | POST | `/custom_fields` |
| Update | PUT | `/custom_fields/{gid}` |
| Delete | DELETE | `/custom_fields/{gid}` |
| List for Workspace | GET | `/workspaces/{workspace_gid}/custom_fields` |
| Create Enum Option | POST | `/custom_fields/{gid}/enum_options` |
| Update Enum Option | PUT | `/enum_options/{gid}` |
| Get Project Settings | GET | `/projects/{project_gid}/custom_field_settings` |
| Add to Project | POST | `/projects/{project_gid}/addCustomFieldSetting` |
| Remove from Project | POST | `/projects/{project_gid}/removeCustomFieldSetting` |

### UsersClient

**Responsibility**: User retrieval and workspace membership.

```python
class UsersClient(BaseClient):
    """Client for Asana User operations."""

    async def get_async(self, user_gid: str, ...) -> User | dict
    async def me_async(self, ...) -> User | dict  # Current authenticated user
    def list_for_workspace_async(self, workspace_gid: str, ...) -> PageIterator[User]
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/users/{gid}` |
| Me | GET | `/users/me` |
| List for Workspace | GET | `/workspaces/{workspace_gid}/users` |

### WorkspacesClient

**Responsibility**: Workspace retrieval and listing.

```python
class WorkspacesClient(BaseClient):
    """Client for Asana Workspace operations."""

    async def get_async(self, workspace_gid: str, ...) -> Workspace | dict
    def list_async(self, ...) -> PageIterator[Workspace]
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/workspaces/{gid}` |
| List | GET | `/workspaces` |

---

## Tier 2 Clients

Tier 2 clients extend SDK capabilities with specialized resource types.

### WebhooksClient

**Responsibility**: Webhook CRUD and signature verification.

Per ADR-0035, signature verification uses HMAC-SHA256 and is implemented as static methods.

```python
class WebhooksClient(BaseClient):
    """Client for Asana Webhook operations."""

    # Core CRUD
    async def get_async(self, webhook_gid: str, ...) -> Webhook | dict
    async def create_async(self, *, resource: str, target: str, filters: list[dict] | None = None, ...) -> Webhook | dict
    async def update_async(self, webhook_gid: str, *, filters: list[dict] | None = None, ...) -> Webhook | dict
    async def delete_async(self, webhook_gid: str) -> None
    def list_for_workspace_async(self, workspace_gid: str, *, resource: str | None = None, ...) -> PageIterator[Webhook]

    # Signature verification (static utilities)
    @staticmethod
    def verify_signature(request_body: bytes, signature: str, secret: str) -> bool:
        """Verify HMAC-SHA256 signature from X-Hook-Signature header."""
        computed = hmac.new(secret.encode('utf-8'), request_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    @staticmethod
    def extract_handshake_secret(headers: dict[str, str]) -> str | None:
        """Extract X-Hook-Secret from handshake request headers."""
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/webhooks/{gid}` |
| Create | POST | `/webhooks` |
| Update | PUT | `/webhooks/{gid}` |
| Delete | DELETE | `/webhooks/{gid}` |
| List for Workspace | GET | `/webhooks?workspace={gid}` |

### TeamsClient

**Responsibility**: Team operations and membership management.

```python
class TeamsClient(BaseClient):
    """Client for Asana Team operations (organization workspaces only)."""

    async def get_async(self, team_gid: str, ...) -> Team | dict
    def list_for_user_async(self, user_gid: str, *, organization: str | None = None, ...) -> PageIterator[Team]
    def list_for_workspace_async(self, workspace_gid: str, ...) -> PageIterator[Team]
    def list_users_async(self, team_gid: str, ...) -> PageIterator[User]

    # Membership
    async def add_user_async(self, team_gid: str, *, user: str) -> TeamMembership | dict
    async def remove_user_async(self, team_gid: str, *, user: str) -> None
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/teams/{gid}` |
| List for User | GET | `/users/{gid}/teams` |
| List for Workspace | GET | `/workspaces/{gid}/teams` |
| List Users | GET | `/teams/{gid}/users` |
| Add User | POST | `/teams/{gid}/addUser` |
| Remove User | POST | `/teams/{gid}/removeUser` |

### AttachmentsClient

**Responsibility**: File upload, download, and attachment management.

Per ADR-0035, uploads use multipart/form-data and downloads use streaming.

```python
class AttachmentsClient(BaseClient):
    """Client for Asana Attachment operations."""

    # Core operations
    async def get_async(self, attachment_gid: str, ...) -> Attachment | dict
    async def delete_async(self, attachment_gid: str) -> None
    def list_for_task_async(self, task_gid: str, ...) -> PageIterator[Attachment]

    # Upload (multipart/form-data)
    async def upload_async(self, *, parent: str, file: BinaryIO, name: str, ...) -> Attachment | dict
    async def upload_from_path_async(self, *, parent: str, path: Path | str, name: str | None = None, ...) -> Attachment | dict
    async def create_external_async(self, *, parent: str, url: str, name: str, ...) -> Attachment | dict

    # Download (streaming)
    async def download_async(self, attachment_gid: str, *, destination: Path | str | BinaryIO) -> Path | None
```

**API Endpoints**:

| Operation | Method | Endpoint | Content-Type |
|-----------|--------|----------|--------------|
| Get | GET | `/attachments/{gid}` | application/json |
| Delete | DELETE | `/attachments/{gid}` | application/json |
| List for Task | GET | `/tasks/{gid}/attachments` | application/json |
| Upload | POST | `/tasks/{gid}/attachments` | multipart/form-data |

### TagsClient

**Responsibility**: Tag CRUD and task tagging.

```python
class TagsClient(BaseClient):
    """Client for Asana Tag operations."""

    # Core CRUD
    async def get_async(self, tag_gid: str, ...) -> Tag | dict
    async def create_async(self, *, workspace: str, name: str, color: str | None = None, ...) -> Tag | dict
    async def update_async(self, tag_gid: str, ...) -> Tag | dict
    async def delete_async(self, tag_gid: str) -> None
    def list_for_workspace_async(self, workspace_gid: str, ...) -> PageIterator[Tag]
    def list_for_task_async(self, task_gid: str, ...) -> PageIterator[Tag]

    # Task tagging
    async def add_to_task_async(self, task_gid: str, *, tag: str) -> None
    async def remove_from_task_async(self, task_gid: str, *, tag: str) -> None
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/tags/{gid}` |
| Create | POST | `/tags` |
| Update | PUT | `/tags/{gid}` |
| Delete | DELETE | `/tags/{gid}` |
| List for Workspace | GET | `/workspaces/{gid}/tags` |
| List for Task | GET | `/tasks/{gid}/tags` |
| Add to Task | POST | `/tasks/{gid}/addTag` |
| Remove from Task | POST | `/tasks/{gid}/removeTag` |

### GoalsClient

**Responsibility**: Goal CRUD, hierarchy (subgoals), and supporting work.

```python
class GoalsClient(BaseClient):
    """Client for Asana Goal operations."""

    # Core CRUD
    async def get_async(self, goal_gid: str, ...) -> Goal | dict
    async def create_async(self, *, workspace: str, name: str, due_on: str | None = None, ...) -> Goal | dict
    async def update_async(self, goal_gid: str, ...) -> Goal | dict
    async def delete_async(self, goal_gid: str) -> None
    def list_async(self, *, workspace: str | None = None, team: str | None = None, ...) -> PageIterator[Goal]

    # Subgoals (hierarchy)
    def list_subgoals_async(self, goal_gid: str, ...) -> PageIterator[Goal]
    async def add_subgoal_async(self, goal_gid: str, *, subgoal: str, insert_before: str | None = None, ...) -> Goal | dict
    async def remove_subgoal_async(self, goal_gid: str, *, subgoal: str) -> None

    # Supporting work (projects/portfolios)
    async def add_supporting_work_async(self, goal_gid: str, *, supporting_resource: str, contribution_weight: float | None = None) -> Goal | dict
    async def remove_supporting_work_async(self, goal_gid: str, *, supporting_resource: str) -> None

    # Followers
    async def add_followers_async(self, goal_gid: str, *, followers: list[str]) -> Goal | dict
    async def remove_followers_async(self, goal_gid: str, *, followers: list[str]) -> Goal | dict
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
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

### PortfoliosClient

**Responsibility**: Portfolio CRUD, project management, and membership.

```python
class PortfoliosClient(BaseClient):
    """Client for Asana Portfolio operations."""

    # Core CRUD
    async def get_async(self, portfolio_gid: str, ...) -> Portfolio | dict
    async def create_async(self, *, workspace: str, name: str, color: str | None = None, ...) -> Portfolio | dict
    async def update_async(self, portfolio_gid: str, ...) -> Portfolio | dict
    async def delete_async(self, portfolio_gid: str) -> None
    def list_async(self, *, workspace: str, owner: str, ...) -> PageIterator[Portfolio]

    # Project management
    def list_items_async(self, portfolio_gid: str, ...) -> PageIterator[Project]
    async def add_item_async(self, portfolio_gid: str, *, item: str, insert_before: str | None = None, ...) -> None
    async def remove_item_async(self, portfolio_gid: str, *, item: str) -> None

    # Members
    async def add_members_async(self, portfolio_gid: str, *, members: list[str]) -> Portfolio | dict
    async def remove_members_async(self, portfolio_gid: str, *, members: list[str]) -> Portfolio | dict

    # Custom fields
    async def add_custom_field_setting_async(self, portfolio_gid: str, *, custom_field: str, is_important: bool | None = None) -> None
    async def remove_custom_field_setting_async(self, portfolio_gid: str, *, custom_field: str) -> None
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
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

### StoriesClient

**Responsibility**: Comment creation and story listing.

```python
class StoriesClient(BaseClient):
    """Client for Asana Story operations (comments and activity)."""

    # Core operations
    async def get_async(self, story_gid: str, ...) -> Story | dict
    async def update_async(self, story_gid: str, *, text: str | None = None, is_pinned: bool | None = None, ...) -> Story | dict
    async def delete_async(self, story_gid: str) -> None  # Comments only
    def list_for_task_async(self, task_gid: str, ...) -> PageIterator[Story]

    # Comment creation
    async def create_comment_async(self, *, task: str, text: str, html_text: str | None = None, is_pinned: bool | None = None, ...) -> Story | dict
```

**API Endpoints**:

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Get | GET | `/stories/{gid}` |
| Update | PUT | `/stories/{gid}` |
| Delete | DELETE | `/stories/{gid}` |
| List for Task | GET | `/tasks/{gid}/stories` |
| Create Comment | POST | `/tasks/{gid}/stories` |

---

## Shared Patterns

### Method Signature Pattern

All clients follow this consistent signature pattern:

```python
# Async primary method
@overload
async def get_async(self, gid: str, *, raw: Literal[False] = ..., opt_fields: list[str] | None = ...) -> Model: ...
@overload
async def get_async(self, gid: str, *, raw: Literal[True], opt_fields: list[str] | None = ...) -> dict[str, Any]: ...

async def get_async(self, gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Model | dict[str, Any]:
    """Implementation."""

# Sync wrapper
@sync_wrapper
def get(self, gid: str, *, raw: bool = False, opt_fields: list[str] | None = None) -> Model | dict[str, Any]:
    """Sync wrapper."""
```

### Standard Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `raw` | `bool` | If True, return raw dict instead of typed model |
| `opt_fields` | `list[str] \| None` | Fields to include in response |
| `limit` | `int` | Items per page for list operations (default 100, max 100) |

### Data Flow

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

---

## Error Handling

### Standard Error Types

All clients propagate errors from the transport layer:

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `AsanaNotFoundError` | 404 | Resource does not exist |
| `AsanaForbiddenError` | 403 | Insufficient permissions |
| `AsanaRateLimitError` | 429 | Rate limit exceeded (auto-retry) |
| `AsanaValidationError` | 400 | Invalid request parameters |
| `AsanaServerError` | 5xx | Asana service error |

### Webhook-Specific Handling

Webhook signature verification returns `bool` rather than raising exceptions to support logging-only failure modes:

```python
# Recommended usage
if not WebhooksClient.verify_signature(body, signature, secret):
    logger.warning("Invalid webhook signature", extra={"signature": signature})
    return  # Silently reject to avoid exposing secret validation behavior
```

---

## Testing Strategy

### Unit Testing

| Test Category | Coverage |
|---------------|----------|
| Models | Validation, serialization, extra field handling |
| Clients | Mock HTTP responses, endpoint verification |
| Overloads | Type checking with mypy |
| Signature verification | Known test vectors |
| Multipart | Content-Type and boundary handling |

### Integration Testing

| Test Category | Coverage |
|---------------|----------|
| Live API | Optional tests against real Asana API |
| Pagination | Multi-page result sets |
| File handling | Small and large file upload/download |
| Error handling | 404, 403, 429 responses |

### Contract Testing

| Test Category | Coverage |
|---------------|----------|
| API fixtures | Sample responses from Asana docs |
| Schema evolution | New fields don't break parsing |

---

## Cross-References

### Related Documents

| Document | Relationship |
|----------|--------------|
| [ADR-0034](../../decisions/ADR-0034-http-transport-integration.md) | HTTP transport and client pattern decisions |
| [ADR-0035](../../decisions/ADR-0035-specialized-protocol-handling.md) | Webhook and attachment protocol handling |
| [TDD-02](TDD-02-models-pagination.md) | Data models and PageIterator design |
| [TDD-01](TDD-01-sdk-architecture.md) | Overall SDK architecture |

### Model Files

| Model | File | Description |
|-------|------|-------------|
| Project | `models/project.py` | Project with NameGid references |
| Section | `models/section.py` | Lightweight section model |
| CustomField | `models/custom_field.py` | Custom field with enum options |
| User | `models/user.py` | User profile model |
| Workspace | `models/workspace.py` | Workspace/organization model |
| Webhook | `models/webhook.py` | Webhook with filters |
| Team | `models/team.py` | Team with visibility settings |
| Attachment | `models/attachment.py` | File attachment model |
| Tag | `models/tag.py` | Workspace-scoped tag |
| Goal | `models/goal.py` | Goal with metrics |
| Portfolio | `models/portfolio.py` | Portfolio container |
| Story | `models/story.py` | Comment and activity model |

### Client Files

| Client | File | Operations |
|--------|------|------------|
| ProjectsClient | `clients/projects.py` | CRUD + membership |
| SectionsClient | `clients/sections.py` | CRUD + task movement |
| CustomFieldsClient | `clients/custom_fields.py` | CRUD + enum + settings |
| UsersClient | `clients/users.py` | Get + list |
| WorkspacesClient | `clients/workspaces.py` | Get + list |
| WebhooksClient | `clients/webhooks.py` | CRUD + signature |
| TeamsClient | `clients/teams.py` | Get + list + membership |
| AttachmentsClient | `clients/attachments.py` | Upload + download |
| TagsClient | `clients/tags.py` | CRUD + task tagging |
| GoalsClient | `clients/goals.py` | CRUD + hierarchy + supporting |
| PortfoliosClient | `clients/portfolios.py` | CRUD + items + members |
| StoriesClient | `clients/stories.py` | CRUD + comments |

---

## Implementation Summary

| Tier | Clients | Total Operations | Estimate |
|------|---------|------------------|----------|
| Tier 1 | 5 clients | ~30 operations | 8.5 hours |
| Tier 2 | 7 clients | ~50 operations | 15.5 hours |
| **Total** | **12 clients** | **~80 operations** | **24 hours** |

All clients follow MODULE-level complexity: self-contained with clear responsibilities, following established patterns without new architectural concepts.
