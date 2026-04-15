"""Tests for Tier 1 Resource Clients (TDD-0003).

Tests WorkspacesClient, UsersClient, ProjectsClient, SectionsClient, and CustomFieldsClient.
Follows TasksClient test patterns with mocked HTTP dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autom8_asana.clients.custom_fields import CustomFieldsClient
from autom8_asana.clients.projects import ProjectsClient
from autom8_asana.clients.sections import SectionsClient
from autom8_asana.clients.users import UsersClient
from autom8_asana.clients.workspaces import WorkspacesClient
from autom8_asana.errors import SyncInAsyncContextError
from autom8_asana.models import (
    CustomField,
    CustomFieldEnumOption,
    CustomFieldSetting,
    PageIterator,
    Project,
    Section,
    User,
    Workspace,
)

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig


# =============================================================================
# Cross-Client Parametrized Tests (Pattern A per CRU-S3 TDD)
# =============================================================================


def _check_workspace(result: Workspace) -> None:
    assert result.is_organization is True


def _check_user(result: User) -> None:
    assert result.email == "alice@example.com"


def _check_project(result: Project) -> None:
    assert result.archived is False
    assert result.public is True


def _check_section(result: Section) -> None:
    assert result.project is not None
    assert result.project.gid == "9876543210987"


def _check_custom_field(result: CustomField) -> None:
    assert result.resource_subtype == "enum"
    assert result.enum_options is not None
    assert len(result.enum_options) == 2
    assert isinstance(result.enum_options[0], CustomFieldEnumOption)


@pytest.mark.parametrize(
    ("client_cls", "gid", "payload", "expected_model", "url_template", "extra_check"),
    [
        (
            WorkspacesClient,
            "ws123",
            {"gid": "ws123", "name": "My Workspace", "is_organization": True},
            Workspace,
            "/workspaces/{gid}",
            _check_workspace,
        ),
        (
            UsersClient,
            "1234567890123",
            {
                "gid": "1234567890123",
                "name": "Alice Smith",
                "email": "alice@example.com",
            },
            User,
            "/users/{gid}",
            _check_user,
        ),
        (
            ProjectsClient,
            "1234567890123",
            {
                "gid": "1234567890123",
                "name": "My Project",
                "archived": False,
                "public": True,
            },
            Project,
            "/projects/{gid}",
            _check_project,
        ),
        (
            SectionsClient,
            "1234567890123",
            {
                "gid": "1234567890123",
                "name": "To Do",
                "project": {"gid": "9876543210987", "name": "Project"},
            },
            Section,
            "/sections/{gid}",
            _check_section,
        ),
        (
            CustomFieldsClient,
            "1234567890123",
            {
                "gid": "1234567890123",
                "name": "Priority",
                "resource_subtype": "enum",
                "enum_options": [
                    {"gid": "1234567890001", "name": "High", "color": "red"},
                    {"gid": "1234567890002", "name": "Low", "color": "green"},
                ],
            },
            CustomField,
            "/custom_fields/{gid}",
            _check_custom_field,
        ),
    ],
    ids=[
        "workspaces_get",
        "users_get",
        "projects_get",
        "sections_get",
        "custom_fields_get",
    ],
)
async def test_get_async_returns_model(
    client_factory,
    mock_http,
    client_cls,
    gid,
    payload,
    expected_model,
    url_template,
    extra_check,
) -> None:
    """get_async returns the typed model for each tier-1 client.

    Consolidates the five previously-copy-pasted ``test_get_async_returns_*_model``
    tests (one per client class) into a single parametrized matrix. Asymmetric
    field assertions (is_organization, email, archived/public, project ref,
    enum_options) are captured per-case via ``extra_check`` callables.
    """
    client = client_factory(client_cls, use_cache=False)
    mock_http.get.return_value = payload

    result = await client.get_async(gid)

    # Behavioral assertions (typed model shape + common fields)
    assert isinstance(result, expected_model)
    assert result.gid == payload["gid"]
    assert result.name == payload["name"]
    extra_check(result)

    # Asana-contract assertion (URL + params) -- retained per Pattern E decision tree category 1
    mock_http.get.assert_called_once_with(url_template.format(gid=gid), params={})


@pytest.mark.parametrize(
    ("client_cls", "gid", "payload"),
    [
        (
            WorkspacesClient,
            "ws123",
            {"gid": "ws123", "name": "My Workspace"},
        ),
        (
            UsersClient,
            "1234567890123",
            {"gid": "1234567890123", "name": "Alice"},
        ),
        (
            ProjectsClient,
            "1234567890123",
            {"gid": "1234567890123", "name": "My Project"},
        ),
    ],
    ids=["workspaces_get", "users_get", "projects_get"],
)
async def test_get_async_raw_returns_dict(
    client_factory, mock_http, client_cls, gid, payload
) -> None:
    """get_async with raw=True returns the raw API dict.

    Consolidates three per-client copies of the same raw-dict assertion.
    The strongest assertion (exact dict equality, originally on Workspaces)
    is preserved as the common assertion across all cases -- a stricter
    uniform contract than the original Users/Projects copies.
    """
    client = client_factory(client_cls, use_cache=False)
    mock_http.get.return_value = payload

    result = await client.get_async(gid, raw=True)

    assert isinstance(result, dict)
    assert result == payload


@pytest.mark.parametrize(
    ("client_cls", "gid", "payload", "expected_model"),
    [
        (
            WorkspacesClient,
            "ws456",
            {"gid": "ws456", "name": "Sync Workspace"},
            Workspace,
        ),
        (
            ProjectsClient,
            "1234567890123",
            {"gid": "1234567890123", "name": "Sync Project"},
            Project,
        ),
        (
            CustomFieldsClient,
            "1234567890123",
            {"gid": "1234567890123", "name": "Field"},
            CustomField,
        ),
    ],
    ids=["workspaces_get", "projects_get", "custom_fields_get"],
)
def test_get_sync_returns_model(
    client_factory, mock_http, client_cls, gid, payload, expected_model
) -> None:
    """get() sync wrapper returns the typed model.

    Consolidates the three per-client sync-wrapper tests. Mirrors the
    original tests' omission of log_provider by passing log_provider=None
    to client_factory, preserving the "fresh client works standalone"
    semantic.

    Not folded with test_get_async_returns_model because pytest-asyncio
    cannot drive a sync top-level test alongside async cases in one
    parametrize block without introducing a bridge helper that obscures
    the sync-vs-async dispatch being verified here.
    """
    client = client_factory(client_cls, use_cache=False, log_provider=None)
    mock_http.get.return_value = payload

    result = client.get(gid)

    assert isinstance(result, expected_model)
    assert result.gid == payload["gid"]


@pytest.mark.parametrize(
    ("client_cls", "method_name", "call_args", "call_kwargs", "page_items", "expected_model"),
    [
        (
            WorkspacesClient,
            "list_async",
            (),
            {},
            [{"gid": "ws1", "name": "WS 1"}, {"gid": "ws2", "name": "WS 2"}],
            Workspace,
        ),
        (
            UsersClient,
            "list_for_workspace_async",
            ("ws123",),
            {},
            [{"gid": "u1", "name": "User 1"}, {"gid": "u2", "name": "User 2"}],
            User,
        ),
        (
            ProjectsClient,
            "list_async",
            (),
            {"workspace": "ws123"},
            [{"gid": "p1", "name": "Project 1"}, {"gid": "p2", "name": "Project 2"}],
            Project,
        ),
    ],
    ids=["workspaces_list", "users_list_for_workspace", "projects_list"],
)
async def test_list_async_returns_page_iterator(
    client_factory,
    mock_http,
    client_cls,
    method_name,
    call_args,
    call_kwargs,
    page_items,
    expected_model,
) -> None:
    """list_*_async methods return PageIterator wrapping the typed model.

    Consolidates three per-client list_async tests. Each client has a
    slightly different list signature (no-args / required workspace gid
    positional / workspace kwarg), captured via (call_args, call_kwargs)
    per case.
    """
    client = client_factory(client_cls, use_cache=False)
    mock_http.get_paginated.return_value = (page_items, None)

    method = getattr(client, method_name)
    result = method(*call_args, **call_kwargs)

    assert isinstance(result, PageIterator)

    items = await result.collect()
    assert len(items) == 2
    assert all(isinstance(m, expected_model) for m in items)
    # Preserve the stricter Workspaces-case assertion across all cases:
    assert items[0].gid == page_items[0]["gid"]
    assert items[1].gid == page_items[1]["gid"]


# =============================================================================
# WorkspacesClient Tests
# =============================================================================


@pytest.fixture
def workspaces_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> WorkspacesClient:
    """Create WorkspacesClient with mocked dependencies."""
    return WorkspacesClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestWorkspacesClientGetSync:
    """Tests for WorkspacesClient.get() sync wrapper."""

    async def test_get_sync_fails_in_async_context(
        self, workspaces_client: WorkspacesClient
    ) -> None:
        """get() raises SyncInAsyncContextError in async context.

        Not folded into Pattern B/A -- this asserts the distinct
        SyncInAsyncContextError behavior per TDD critical constraint.
        """
        with pytest.raises(SyncInAsyncContextError):
            workspaces_client.get("ws123")


# =============================================================================
# UsersClient Tests
# =============================================================================


@pytest.fixture
def users_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> UsersClient:
    """Create UsersClient with mocked dependencies."""
    return UsersClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


@pytest.mark.parametrize(
    ("raw", "expected_type"),
    [(False, User), (True, dict)],
    ids=["typed_model", "raw_dict"],
)
async def test_users_me_async_return_shape(client_factory, mock_http, raw, expected_type) -> None:
    """me_async returns User model by default and dict with raw=True.

    Pattern C: consolidates test_me_async_returns_user_model +
    test_me_async_raw_returns_dict. The URL contract assertion (/users/me)
    is retained only on the typed path where it was originally present.
    """
    payload = {"gid": "me123", "name": "Current User", "email": "me@example.com"}
    client = client_factory(UsersClient, use_cache=False)
    mock_http.get.return_value = payload

    kwargs = {"raw": True} if raw else {}
    result = await client.me_async(**kwargs)

    assert isinstance(result, expected_type)
    if not raw:
        assert result.gid == "me123"
        assert result.name == "Current User"
        mock_http.get.assert_called_once_with("/users/me", params={})


def test_users_me_sync_returns_user_model(client_factory, mock_http) -> None:
    """me() sync wrapper returns User model outside async context.

    Kept as a standalone sync test (not fused with me_async) -- the sync
    dispatch path is structurally distinct and the original omitted
    log_provider to exercise the "fresh client works standalone" semantic.
    """
    client = client_factory(UsersClient, use_cache=False, log_provider=None)
    mock_http.get.return_value = {"gid": "me456", "name": "Sync User"}

    result = client.me()

    assert isinstance(result, User)
    assert result.gid == "me456"


# =============================================================================
# ProjectsClient Tests
# =============================================================================


@pytest.fixture
def projects_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> ProjectsClient:
    """Create ProjectsClient with mocked dependencies."""
    return ProjectsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestProjectsClientCreateAsync:
    """Tests for ProjectsClient.create_async()."""

    async def test_create_async_returns_project_model(
        self, projects_client: ProjectsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns Project model by default."""
        mock_http.post.return_value = {"gid": "newproj123", "name": "New Project"}

        result = await projects_client.create_async(name="New Project", workspace="ws123")

        assert isinstance(result, Project)
        assert result.gid == "newproj123"
        assert result.name == "New Project"
        mock_http.post.assert_called_once_with(
            "/projects",
            json={"data": {"name": "New Project", "workspace": "ws123"}},
        )

    async def test_create_async_with_all_params(
        self, projects_client: ProjectsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async includes all parameters."""
        mock_http.post.return_value = {"gid": "newproj456", "name": "Full Project"}

        await projects_client.create_async(
            name="Full Project",
            workspace="ws123",
            team="team123",
            public=True,
            color="dark-pink",
            default_view="board",
        )

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["name"] == "Full Project"
        assert data["workspace"] == "ws123"
        assert data["team"] == "team123"
        assert data["public"] is True
        assert data["color"] == "dark-pink"
        assert data["default_view"] == "board"


class TestProjectsClientUpdateAsync:
    """Tests for ProjectsClient.update_async()."""

    async def test_update_async_returns_project_model(
        self, projects_client: ProjectsClient, mock_http: MockHTTPClient
    ) -> None:
        """update_async returns Project model by default."""
        mock_http.put.return_value = {"gid": "proj123", "name": "Updated Name"}

        result = await projects_client.update_async("proj123", name="Updated Name")

        assert isinstance(result, Project)
        assert result.gid == "proj123"
        assert result.name == "Updated Name"
        mock_http.put.assert_called_once_with(
            "/projects/proj123",
            json={"data": {"name": "Updated Name"}},
        )


class TestProjectsClientDeleteAsync:
    """Tests for ProjectsClient.delete_async()."""

    async def test_delete_async_success(
        self, projects_client: ProjectsClient, mock_http: MockHTTPClient
    ) -> None:
        """delete_async sends DELETE request and returns None."""
        mock_http.delete.return_value = {}

        result = await projects_client.delete_async("proj123")

        assert result is None
        mock_http.delete.assert_called_once_with("/projects/proj123")


class TestProjectsClientMemberships:
    """Tests for ProjectsClient membership operations."""

    @pytest.mark.parametrize(
        ("method_name", "members", "endpoint", "expected_members_str"),
        [
            (
                "add_members_async",
                ["user1", "user2"],
                "/projects/proj123/addMembers",
                "user1,user2",
            ),
            (
                "remove_members_async",
                ["user1"],
                "/projects/proj123/removeMembers",
                "user1",
            ),
        ],
        ids=["add_members", "remove_members"],
    )
    async def test_membership_op_returns_project(
        self,
        projects_client: ProjectsClient,
        mock_http: MockHTTPClient,
        method_name: str,
        members: list[str],
        endpoint: str,
        expected_members_str: str,
    ) -> None:
        """add/remove members POST to the right endpoint with comma-joined gids."""
        mock_http.post.return_value = {"gid": "proj123", "name": "Project"}

        result = await getattr(projects_client, method_name)("proj123", members=members)

        assert isinstance(result, Project)
        mock_http.post.assert_called_once_with(
            endpoint,
            json={"data": {"members": expected_members_str}},
        )


class TestProjectsClientSyncWrappers:
    """Test sync wrappers for ProjectsClient."""

    def test_create_sync_returns_project_model(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create() sync wrapper returns Project model."""
        client = ProjectsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.post.return_value = {"gid": "newproj", "name": "New Project"}

        result = client.create(name="New Project", workspace="ws123")

        assert isinstance(result, Project)

    def test_delete_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """delete() sync wrapper works."""
        client = ProjectsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.delete.return_value = {}

        client.delete("proj123")

        mock_http.delete.assert_called_once_with("/projects/proj123")


# =============================================================================
# SectionsClient Tests
# =============================================================================


@pytest.fixture
def sections_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> SectionsClient:
    """Create SectionsClient with mocked dependencies."""
    return SectionsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestSectionsClientCreateAsync:
    """Tests for SectionsClient.create_async()."""

    async def test_create_async_returns_section_model(
        self, sections_client: SectionsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns Section model by default."""
        mock_http.post.return_value = {"gid": "newsec123", "name": "New Section"}

        result = await sections_client.create_async(name="New Section", project="proj123")

        assert isinstance(result, Section)
        assert result.gid == "newsec123"
        assert result.name == "New Section"
        mock_http.post.assert_called_once_with(
            "/projects/proj123/sections",
            json={"data": {"name": "New Section"}},
        )

    async def test_create_async_with_position(
        self, sections_client: SectionsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async with insert_before/after."""
        mock_http.post.return_value = {"gid": "newsec456", "name": "Positioned Section"}

        await sections_client.create_async(
            name="Positioned Section",
            project="proj123",
            insert_after="sec_existing",
        )

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["insert_after"] == "sec_existing"


class TestSectionsClientTaskMovement:
    """Tests for SectionsClient task movement operations."""

    @pytest.mark.parametrize(
        ("extra_kwargs", "expected_body"),
        [
            ({}, {"task": "task456"}),
            (
                {"insert_before": "task_other"},
                {"task": "task456", "insert_before": "task_other"},
            ),
        ],
        ids=["no_position", "insert_before"],
    )
    async def test_add_task_async(
        self,
        sections_client: SectionsClient,
        mock_http: MockHTTPClient,
        extra_kwargs: dict,
        expected_body: dict,
    ) -> None:
        """add_task_async posts to /sections/{gid}/addTask with optional positioning."""
        mock_http.post.return_value = {}

        await sections_client.add_task_async("sec123", task="task456", **extra_kwargs)

        mock_http.post.assert_called_once_with(
            "/sections/sec123/addTask",
            json={"data": expected_body},
        )

    async def test_insert_section_async(
        self, sections_client: SectionsClient, mock_http: MockHTTPClient
    ) -> None:
        """insert_section_async reorders section."""
        mock_http.post.return_value = {}

        await sections_client.insert_section_async(
            "proj123", section="sec456", after_section="sec_other"
        )

        mock_http.post.assert_called_once_with(
            "/projects/proj123/sections/insert",
            json={"data": {"section": "sec456", "after_section": "sec_other"}},
        )


class TestSectionsClientSyncWrappers:
    """Test sync wrappers for SectionsClient."""

    def test_add_task_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """add_task() sync wrapper works."""
        client = SectionsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.post.return_value = {}

        client.add_task("sec123", task="task456")

        mock_http.post.assert_called_once()


# =============================================================================
# CustomFieldsClient Tests
# =============================================================================


@pytest.fixture
def custom_fields_client(
    mock_http: MockHTTPClient,
    config: AsanaConfig,
    auth_provider: MockAuthProvider,
    logger: MockLogger,
) -> CustomFieldsClient:
    """Create CustomFieldsClient with mocked dependencies."""
    return CustomFieldsClient(
        http=mock_http,  # type: ignore[arg-type]
        config=config,
        auth_provider=auth_provider,
        log_provider=logger,
    )


class TestCustomFieldsClientCreateAsync:
    """Tests for CustomFieldsClient.create_async()."""

    async def test_create_async_returns_custom_field_model(
        self, custom_fields_client: CustomFieldsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async returns CustomField model by default."""
        mock_http.post.return_value = {
            "gid": "newcf123",
            "name": "New Field",
            "resource_subtype": "text",
        }

        result = await custom_fields_client.create_async(
            workspace="ws123",
            name="New Field",
            resource_subtype="text",
        )

        assert isinstance(result, CustomField)
        assert result.gid == "newcf123"
        assert result.name == "New Field"
        mock_http.post.assert_called_once_with(
            "/custom_fields",
            json={
                "data": {
                    "workspace": "ws123",
                    "name": "New Field",
                    "resource_subtype": "text",
                }
            },
        )

    async def test_create_async_enum_field(
        self, custom_fields_client: CustomFieldsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_async for enum field includes enum_options."""
        mock_http.post.return_value = {"gid": "newcf456", "name": "Status"}

        await custom_fields_client.create_async(
            workspace="ws123",
            name="Status",
            resource_subtype="enum",
            enum_options=[
                {"name": "Active", "color": "green"},
                {"name": "Inactive", "color": "red"},
            ],
        )

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["enum_options"] == [
            {"name": "Active", "color": "green"},
            {"name": "Inactive", "color": "red"},
        ]


class TestCustomFieldsClientEnumOptions:
    """Tests for CustomFieldsClient enum option operations."""

    async def test_create_enum_option_async(
        self, custom_fields_client: CustomFieldsClient, mock_http: MockHTTPClient
    ) -> None:
        """create_enum_option_async creates enum option."""
        mock_http.post.return_value = {
            "gid": "opt123",
            "name": "New Option",
            "color": "blue",
            "enabled": True,
        }

        result = await custom_fields_client.create_enum_option_async(
            "cf123", name="New Option", color="blue"
        )

        assert isinstance(result, CustomFieldEnumOption)
        assert result.gid == "opt123"
        assert result.name == "New Option"
        mock_http.post.assert_called_once_with(
            "/custom_fields/cf123/enum_options",
            json={"data": {"name": "New Option", "enabled": True, "color": "blue"}},
        )

    async def test_update_enum_option_async(
        self, custom_fields_client: CustomFieldsClient, mock_http: MockHTTPClient
    ) -> None:
        """update_enum_option_async updates enum option."""
        mock_http.put.return_value = {"gid": "opt123", "name": "Updated Option"}

        result = await custom_fields_client.update_enum_option_async(
            "opt123", name="Updated Option"
        )

        assert isinstance(result, CustomFieldEnumOption)
        mock_http.put.assert_called_once_with(
            "/enum_options/opt123",
            json={"data": {"name": "Updated Option"}},
        )


class TestCustomFieldsClientProjectSettings:
    """Tests for CustomFieldsClient project settings operations."""

    async def test_get_settings_for_project_async(
        self, custom_fields_client: CustomFieldsClient, mock_http: MockHTTPClient
    ) -> None:
        """get_settings_for_project_async returns PageIterator."""
        mock_http.get_paginated.return_value = (
            [
                {
                    "gid": "setting1",
                    "custom_field": {"gid": "cf1", "name": "Field 1"},
                    "is_important": True,
                }
            ],
            None,
        )

        result = custom_fields_client.get_settings_for_project_async("proj123")

        assert isinstance(result, PageIterator)

        items = await result.collect()
        assert len(items) == 1
        assert isinstance(items[0], CustomFieldSetting)
        assert items[0].is_important is True

    async def test_add_to_project_async(
        self, custom_fields_client: CustomFieldsClient, mock_http: MockHTTPClient
    ) -> None:
        """add_to_project_async adds custom field to project."""
        mock_http.post.return_value = {
            "gid": "setting123",
            "custom_field": {"gid": "cf123", "name": "Field"},
            "is_important": True,
        }

        result = await custom_fields_client.add_to_project_async(
            "proj123", custom_field="cf123", is_important=True
        )

        assert isinstance(result, CustomFieldSetting)
        mock_http.post.assert_called_once_with(
            "/projects/proj123/addCustomFieldSetting",
            json={"data": {"custom_field": "cf123", "is_important": True}},
        )

    async def test_remove_from_project_async(
        self, custom_fields_client: CustomFieldsClient, mock_http: MockHTTPClient
    ) -> None:
        """remove_from_project_async removes custom field from project."""
        mock_http.post.return_value = {}

        await custom_fields_client.remove_from_project_async("proj123", custom_field="cf123")

        mock_http.post.assert_called_once_with(
            "/projects/proj123/removeCustomFieldSetting",
            json={"data": {"custom_field": "cf123"}},
        )


class TestCustomFieldsClientSyncWrappers:
    """Test sync wrappers for CustomFieldsClient."""

    def test_create_enum_option_sync_works(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create_enum_option() sync wrapper works."""
        client = CustomFieldsClient(
            http=mock_http,  # type: ignore[arg-type]
            config=config,
            auth_provider=auth_provider,
        )
        mock_http.post.return_value = {"gid": "opt123", "name": "Option"}

        result = client.create_enum_option("cf123", name="Option")

        assert isinstance(result, CustomFieldEnumOption)


# =============================================================================
# Model Tests - Verify models can be imported and used
# =============================================================================


@pytest.mark.parametrize(
    ("model_cls", "kwargs"),
    [
        (Workspace, {"gid": "123", "name": "Test"}),
        (User, {"gid": "456", "name": "Test User", "email": "test@example.com"}),
        (Project, {"gid": "789", "name": "Test Project", "archived": False}),
        (Section, {"gid": "abc", "name": "Test Section"}),
        (CustomField, {"gid": "def", "name": "Test Field", "resource_subtype": "text"}),
        (
            CustomFieldEnumOption,
            {"gid": "opt1", "name": "High", "color": "red", "enabled": True},
        ),
        (CustomFieldSetting, {"gid": "set1", "is_important": True}),
    ],
    ids=[
        "workspace",
        "user",
        "project",
        "section",
        "custom_field",
        "custom_field_enum_option",
        "custom_field_setting",
    ],
)
def test_import_and_instantiate_model(model_cls, kwargs) -> None:
    """Each Tier-1 model can be imported and instantiated with kwargs.

    Consolidates seven per-model ``test_import_*`` functions. Each case
    constructs the model from kwargs and asserts every provided field
    round-trips to the matching attribute.
    """
    instance = model_cls(**kwargs)
    for field, expected in kwargs.items():
        assert getattr(instance, field) == expected


class TestModelValidation:
    """Test that models validate API responses correctly."""

    def test_workspace_extra_fields_ignored(self) -> None:
        """Workspace ignores unknown fields per ADR-0005."""
        ws = Workspace.model_validate(
            {
                "gid": "123",
                "name": "Test",
                "unknown_field": "ignored",
            }
        )
        assert ws.gid == "123"
        assert not hasattr(ws, "unknown_field")

    def test_project_with_namegid_references(self) -> None:
        """Project validates NameGid references."""
        project = Project.model_validate(
            {
                "gid": "proj123",
                "name": "Project",
                "owner": {"gid": "user123", "name": "Alice"},
                "workspace": {"gid": "ws123", "name": "Workspace"},
            }
        )
        assert project.owner is not None
        assert project.owner.gid == "user123"
        assert project.workspace is not None
        assert project.workspace.gid == "ws123"

    def test_custom_field_with_enum_options(self) -> None:
        """CustomField validates nested enum options."""
        cf = CustomField.model_validate(
            {
                "gid": "cf123",
                "name": "Status",
                "resource_subtype": "enum",
                "enum_options": [
                    {"gid": "opt1", "name": "Active", "enabled": True},
                    {"gid": "opt2", "name": "Inactive", "enabled": False},
                ],
            }
        )
        assert cf.enum_options is not None
        assert len(cf.enum_options) == 2
        assert cf.enum_options[0].name == "Active"
        assert cf.enum_options[0].enabled is True


# =============================================================================
# Thread Safety Tests (merged from test_tier1_adversarial.py)
# =============================================================================


class TestAsanaClientThreadSafety:
    """Test thread safety of lazy initialization."""

    def test_concurrent_access_same_client(self) -> None:
        """Concurrent access from multiple threads returns same client."""
        import threading
        from unittest.mock import MagicMock, patch

        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http_class.return_value = MagicMock()
            from autom8_asana.client import AsanaClient
            from autom8_asana.clients.projects import ProjectsClient

            client = AsanaClient(token="test-token")

            results: list[ProjectsClient] = []
            errors: list[Exception] = []

            def access_projects() -> None:
                try:
                    results.append(client.projects)
                except Exception as e:  # noqa: BLE001
                    errors.append(e)

            # Create multiple threads
            threads = [threading.Thread(target=access_projects) for _ in range(10)]

            # Start all threads
            for t in threads:
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join(timeout=10)
                if t.is_alive():
                    raise AssertionError(f"Thread {t.name} did not complete within timeout")

            # No errors should have occurred
            assert len(errors) == 0

            # All results should be the same instance
            assert len(results) == 10
            first = results[0]
            assert all(r is first for r in results)
