"""Adversarial tests for Tier 1 Resource Clients (TDD-0003).

This test file validates edge cases, error handling, and integration scenarios
for Phase 2B implementation. Tests are designed to find problems before
production does.

Test Categories:
1. Model Validation Tests - Required fields, deserialization, extra fields
2. Client Operation Tests - CRUD, PageIterator, raw mode, errors
3. Special Operations Tests - add_members, insert_section, enum options
4. AsanaClient Integration Tests - lazy initialization, HTTP client sharing
5. Edge Case Tests - empty, null, unicode, long strings
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from autom8_asana.client import AsanaClient
from autom8_asana.clients.custom_fields import CustomFieldsClient
from autom8_asana.clients.projects import ProjectsClient
from autom8_asana.clients.sections import SectionsClient
from autom8_asana.clients.users import UsersClient
from autom8_asana.clients.workspaces import WorkspacesClient
from autom8_asana.exceptions import (
    SyncInAsyncContextError,
)
from autom8_asana.models import (
    CustomField,
    CustomFieldEnumOption,
    CustomFieldSetting,
    NameGid,
    PageIterator,
    Project,
    Section,
    User,
    Workspace,
)
from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.config import AsanaConfig

# =============================================================================
# 1. MODEL VALIDATION TESTS
# =============================================================================


class TestModelRequiredFields:
    """Test required fields enforcement across all models."""

    def test_workspace_requires_gid(self) -> None:
        """Workspace model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Workspace.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_user_requires_gid(self) -> None:
        """User model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            User.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_project_requires_gid(self) -> None:
        """Project model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Project.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_section_requires_gid(self) -> None:
        """Section model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            Section.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_custom_field_requires_gid(self) -> None:
        """CustomField model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            CustomField.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_custom_field_enum_option_requires_gid(self) -> None:
        """CustomFieldEnumOption model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldEnumOption.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_custom_field_setting_requires_gid(self) -> None:
        """CustomFieldSetting model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldSetting.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)

    def test_namegid_requires_gid(self) -> None:
        """NameGid model requires gid field."""
        with pytest.raises(ValidationError) as exc_info:
            NameGid.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("gid",) for e in errors)


class TestNameGidDeserialization:
    """Test NameGid deserialization from various dict formats."""

    def test_deserialize_from_minimal_dict(self) -> None:
        """NameGid deserializes from dict with only gid."""
        ref = NameGid.model_validate({"gid": "123"})
        assert ref.gid == "123"
        assert ref.name is None

    def test_deserialize_from_full_dict(self) -> None:
        """NameGid deserializes from dict with all fields."""
        ref = NameGid.model_validate(
            {
                "gid": "123",
                "name": "Test User",
                "resource_type": "user",
            }
        )
        assert ref.gid == "123"
        assert ref.name == "Test User"
        assert ref.resource_type == "user"

    def test_deserialize_nested_in_model(self) -> None:
        """NameGid deserializes correctly when nested in parent model."""
        project = Project.model_validate(
            {
                "gid": "proj123",
                "owner": {"gid": "user123", "name": "Alice"},
                "team": {"gid": "team123", "name": "Engineering"},
                "workspace": {"gid": "ws123", "name": "My Workspace"},
            }
        )

        assert project.owner is not None
        assert isinstance(project.owner, NameGid)
        assert project.owner.gid == "user123"
        assert project.owner.name == "Alice"

        assert project.team is not None
        assert project.team.gid == "team123"

        assert project.workspace is not None
        assert project.workspace.gid == "ws123"

    def test_deserialize_list_of_namegid(self) -> None:
        """List[NameGid] deserializes correctly."""
        project = Project.model_validate(
            {
                "gid": "proj123",
                "members": [
                    {"gid": "user1", "name": "Alice"},
                    {"gid": "user2", "name": "Bob"},
                    {"gid": "user3"},  # Name is optional
                ],
            }
        )

        assert project.members is not None
        assert len(project.members) == 3
        assert all(isinstance(m, NameGid) for m in project.members)
        assert project.members[0].name == "Alice"
        assert project.members[2].name is None


class TestExtraFieldsIgnored:
    """Test that extra fields are ignored per ADR-0005."""

    def test_workspace_ignores_unknown_fields(self) -> None:
        """Workspace ignores unknown API fields."""
        ws = Workspace.model_validate(
            {
                "gid": "123",
                "name": "Test",
                "future_field": "ignored",
                "another_new_field": {"nested": "data"},
            }
        )

        assert ws.gid == "123"
        assert ws.name == "Test"
        # Extra fields should not be accessible
        assert not hasattr(ws, "future_field")
        assert not hasattr(ws, "another_new_field")

    def test_user_ignores_unknown_fields(self) -> None:
        """User ignores unknown API fields."""
        user = User.model_validate(
            {
                "gid": "456",
                "name": "Test User",
                "email": "test@example.com",
                "avatar_url": "https://example.com/avatar.png",  # Unknown field
                "department": "Engineering",  # Unknown field
            }
        )

        assert user.gid == "456"
        assert not hasattr(user, "avatar_url")
        assert not hasattr(user, "department")

    def test_project_ignores_unknown_fields(self) -> None:
        """Project ignores unknown API fields."""
        project = Project.model_validate(
            {
                "gid": "789",
                "name": "Test Project",
                "new_feature_flag": True,  # Unknown field
                "experimental": {"data": "here"},  # Unknown field
            }
        )

        assert project.gid == "789"
        assert not hasattr(project, "new_feature_flag")
        assert not hasattr(project, "experimental")

    def test_namegid_ignores_extra_fields(self) -> None:
        """NameGid ignores extra fields in nested objects."""
        ref = NameGid.model_validate(
            {
                "gid": "123",
                "name": "Test",
                "email": "extra@example.com",
                "photo": {"url": "https://..."},
            }
        )

        assert ref.gid == "123"
        assert ref.name == "Test"
        assert not hasattr(ref, "email")
        assert not hasattr(ref, "photo")


class TestRoundtripSerialization:
    """Test serialization roundtrips for all models."""

    def test_workspace_roundtrip(self) -> None:
        """Workspace can roundtrip through dict."""
        original = Workspace(gid="123", name="Test", is_organization=True)
        dumped = original.model_dump()
        restored = Workspace.model_validate(dumped)

        assert restored.gid == original.gid
        assert restored.name == original.name
        assert restored.is_organization == original.is_organization

    def test_user_roundtrip(self) -> None:
        """User can roundtrip through dict."""
        original = User(
            gid="456",
            name="Test User",
            email="test@example.com",
            workspaces=[
                NameGid(gid="ws1", name="Workspace 1"),
                NameGid(gid="ws2", name="Workspace 2"),
            ],
        )
        dumped = original.model_dump()
        restored = User.model_validate(dumped)

        assert restored.gid == original.gid
        assert restored.workspaces is not None
        assert len(restored.workspaces) == 2
        assert restored.workspaces[0].gid == "ws1"

    def test_project_roundtrip_with_namegid(self) -> None:
        """Project with NameGid references can roundtrip."""
        original = Project(
            gid="proj123",
            name="Test Project",
            owner=NameGid(gid="user123", name="Alice"),
            members=[
                NameGid(gid="user1", name="Bob"),
                NameGid(gid="user2", name="Charlie"),
            ],
        )
        dumped = original.model_dump()
        restored = Project.model_validate(dumped)

        assert restored.owner is not None
        assert restored.owner.gid == "user123"
        assert restored.members is not None
        assert len(restored.members) == 2

    def test_custom_field_roundtrip_with_enum_options(self) -> None:
        """CustomField with enum options can roundtrip."""
        original = CustomField(
            gid="cf123",
            name="Status",
            resource_subtype="enum",
            enum_options=[
                CustomFieldEnumOption(gid="opt1", name="Active", color="green"),
                CustomFieldEnumOption(gid="opt2", name="Inactive", color="red"),
            ],
        )
        dumped = original.model_dump()
        restored = CustomField.model_validate(dumped)

        assert restored.enum_options is not None
        assert len(restored.enum_options) == 2
        assert restored.enum_options[0].name == "Active"
        assert restored.enum_options[1].color == "red"


# =============================================================================
# 2. CLIENT OPERATION TESTS
# =============================================================================


class TestCRUDOperationsAllClients:
    """Test CRUD operations work consistently across all clients."""

    async def test_workspaces_get_calls_correct_endpoint(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """WorkspacesClient.get_async calls correct API endpoint."""
        client = WorkspacesClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "ws123", "name": "Test"}

        await client.get_async("ws123")

        mock_http.get.assert_called_once_with("/workspaces/ws123", params={})

    async def test_users_get_calls_correct_endpoint(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """UsersClient.get_async calls correct API endpoint."""
        client = UsersClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "1234567890123", "name": "Test"}

        await client.get_async("1234567890123")

        mock_http.get.assert_called_once_with("/users/1234567890123", params={})

    async def test_projects_crud_endpoints(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """ProjectsClient uses correct endpoints for all CRUD operations."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        # GET
        mock_http.get.return_value = {"gid": "1234567890123", "name": "Test"}
        await client.get_async("1234567890123")
        mock_http.get.assert_called_with("/projects/1234567890123", params={})

        # POST (Create)  # noqa: ERA001
        mock_http.post.return_value = {"gid": "newproj", "name": "New"}
        await client.create_async(name="New", workspace="ws123")
        mock_http.post.assert_called_with(
            "/projects",
            json={"data": {"name": "New", "workspace": "ws123"}},
        )

        # PUT (Update)  # noqa: ERA001
        mock_http.put.return_value = {"gid": "proj123", "name": "Updated"}
        await client.update_async("proj123", name="Updated")
        mock_http.put.assert_called_with(
            "/projects/proj123",
            json={"data": {"name": "Updated"}},
        )

        # DELETE
        mock_http.delete.return_value = {}
        await client.delete_async("proj123")
        mock_http.delete.assert_called_with("/projects/proj123")

    async def test_sections_crud_endpoints(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """SectionsClient uses correct endpoints for all CRUD operations."""
        client = SectionsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        # GET
        mock_http.get.return_value = {"gid": "1234567890123", "name": "To Do"}
        await client.get_async("1234567890123")
        mock_http.get.assert_called_with("/sections/1234567890123", params={})

        # POST (Create) - Note: sections are created under projects
        mock_http.post.return_value = {"gid": "newsec", "name": "New Section"}
        await client.create_async(name="New Section", project="proj123")
        mock_http.post.assert_called_with(
            "/projects/proj123/sections",
            json={"data": {"name": "New Section"}},
        )

        # PUT (Update)  # noqa: ERA001
        mock_http.put.return_value = {"gid": "sec123", "name": "Renamed"}
        await client.update_async("sec123", name="Renamed")
        mock_http.put.assert_called_with(
            "/sections/sec123",
            json={"data": {"name": "Renamed"}},
        )

        # DELETE
        mock_http.delete.return_value = {}
        await client.delete_async("sec123")
        mock_http.delete.assert_called_with("/sections/sec123")

    async def test_custom_fields_crud_endpoints(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """CustomFieldsClient uses correct endpoints for all CRUD operations."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        # GET
        mock_http.get.return_value = {"gid": "1234567890123", "name": "Priority"}
        await client.get_async("1234567890123")
        mock_http.get.assert_called_with("/custom_fields/1234567890123", params={})

        # POST (Create)  # noqa: ERA001
        mock_http.post.return_value = {"gid": "newcf", "name": "New Field"}
        await client.create_async(
            workspace="ws123", name="New Field", resource_subtype="text"
        )
        mock_http.post.assert_called_with(
            "/custom_fields",
            json={
                "data": {
                    "workspace": "ws123",
                    "name": "New Field",
                    "resource_subtype": "text",
                }
            },
        )

        # PUT (Update)  # noqa: ERA001
        mock_http.put.return_value = {"gid": "cf123", "name": "Updated"}
        await client.update_async("cf123", name="Updated")
        mock_http.put.assert_called_with(
            "/custom_fields/cf123",
            json={"data": {"name": "Updated"}},
        )

        # DELETE
        mock_http.delete.return_value = {}
        await client.delete_async("cf123")
        mock_http.delete.assert_called_with("/custom_fields/cf123")


class TestRawModeAllClients:
    """Test raw=True returns dict for all client operations."""

    async def test_workspaces_raw_mode(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """WorkspacesClient returns dict when raw=True."""
        client = WorkspacesClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "ws123", "custom_field": "preserved"}

        result = await client.get_async("ws123", raw=True)

        assert isinstance(result, dict)
        assert result["custom_field"] == "preserved"

    async def test_users_raw_mode(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """UsersClient returns dict when raw=True."""
        client = UsersClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "1234567890123", "extra": "data"}

        result = await client.get_async("1234567890123", raw=True)

        assert isinstance(result, dict)
        assert result["extra"] == "data"

        # Also test me_async
        mock_http.get.return_value = {"gid": "1234567890124", "extra": "me_data"}
        result = await client.me_async(raw=True)
        assert isinstance(result, dict)

    async def test_projects_raw_mode_all_operations(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """ProjectsClient returns dict when raw=True for all operations."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        # get_async raw
        mock_http.get.return_value = {"gid": "1234567890123", "extra": "get"}
        result = await client.get_async("1234567890123", raw=True)
        assert isinstance(result, dict)
        assert result["extra"] == "get"

        # create_async raw
        mock_http.post.return_value = {"gid": "newproj", "extra": "create"}
        result = await client.create_async(name="Test", workspace="ws123", raw=True)
        assert isinstance(result, dict)
        assert result["extra"] == "create"

        # update_async raw
        mock_http.put.return_value = {"gid": "proj123", "extra": "update"}
        result = await client.update_async("proj123", raw=True, name="Updated")
        assert isinstance(result, dict)
        assert result["extra"] == "update"

        # add_members_async raw
        mock_http.post.return_value = {"gid": "proj123", "extra": "members"}
        result = await client.add_members_async("proj123", members=["u1"], raw=True)
        assert isinstance(result, dict)
        assert result["extra"] == "members"

    async def test_sections_raw_mode(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """SectionsClient returns dict when raw=True."""
        client = SectionsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        mock_http.get.return_value = {"gid": "1234567890123", "extra": "data"}
        result = await client.get_async("1234567890123", raw=True)
        assert isinstance(result, dict)

        mock_http.post.return_value = {"gid": "newsec", "extra": "create"}
        result = await client.create_async(name="Test", project="proj123", raw=True)
        assert isinstance(result, dict)

    async def test_custom_fields_raw_mode(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """CustomFieldsClient returns dict when raw=True."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        mock_http.get.return_value = {"gid": "1234567890123", "extra": "data"}
        result = await client.get_async("1234567890123", raw=True)
        assert isinstance(result, dict)

        mock_http.post.return_value = {"gid": "1234567890124", "extra": "enum"}
        result = await client.create_enum_option_async(
            "1234567890123", name="Opt", raw=True
        )
        assert isinstance(result, dict)


class TestPageIteratorReturnsCorrectType:
    """Test that list operations return PageIterator with correct model types."""

    async def test_workspaces_list_returns_workspace_models(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """WorkspacesClient.list_async returns PageIterator[Workspace]."""
        client = WorkspacesClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = (
            [{"gid": "ws1", "name": "WS1"}, {"gid": "ws2", "name": "WS2"}],
            None,
        )

        iterator = client.list_async()
        assert isinstance(iterator, PageIterator)

        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(w, Workspace) for w in items)

    async def test_users_list_returns_user_models(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """UsersClient.list_for_workspace_async returns PageIterator[User]."""
        client = UsersClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = (
            [{"gid": "u1", "name": "User1"}, {"gid": "u2", "name": "User2"}],
            None,
        )

        iterator = client.list_for_workspace_async("ws123")
        items = await iterator.collect()

        assert all(isinstance(u, User) for u in items)

    async def test_projects_list_returns_project_models(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """ProjectsClient.list_async returns PageIterator[Project]."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = (
            [{"gid": "p1", "name": "Project1"}],
            None,
        )

        iterator = client.list_async(workspace="ws123")
        items = await iterator.collect()

        assert all(isinstance(p, Project) for p in items)

    async def test_sections_list_returns_section_models(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """SectionsClient.list_for_project_async returns PageIterator[Section]."""
        client = SectionsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = (
            [{"gid": "s1", "name": "To Do"}],
            None,
        )

        iterator = client.list_for_project_async("proj123")
        items = await iterator.collect()

        assert all(isinstance(s, Section) for s in items)

    async def test_custom_fields_list_returns_custom_field_models(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """CustomFieldsClient.list_for_workspace_async returns PageIterator[CustomField]."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = (
            [{"gid": "cf1", "name": "Priority"}],
            None,
        )

        iterator = client.list_for_workspace_async("ws123")
        items = await iterator.collect()

        assert all(isinstance(cf, CustomField) for cf in items)

    async def test_custom_field_settings_returns_setting_models(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """CustomFieldsClient.get_settings_for_project_async returns PageIterator[CustomFieldSetting]."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = (
            [{"gid": "set1", "is_important": True}],
            None,
        )

        iterator = client.get_settings_for_project_async("proj123")
        items = await iterator.collect()

        assert all(isinstance(s, CustomFieldSetting) for s in items)


class TestSyncWrapperBehavior:
    """Test sync wrapper behavior across all clients."""

    async def test_sync_wrapper_fails_in_async_context_workspaces(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """WorkspacesClient sync methods fail in async context."""
        client = WorkspacesClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        with pytest.raises(SyncInAsyncContextError):
            client.get("ws123")

    async def test_sync_wrapper_fails_in_async_context_users(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """UsersClient sync methods fail in async context."""
        client = UsersClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        with pytest.raises(SyncInAsyncContextError):
            client.get("user123")

        with pytest.raises(SyncInAsyncContextError):
            client.me()

    async def test_sync_wrapper_fails_in_async_context_projects(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """ProjectsClient sync methods fail in async context."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        with pytest.raises(SyncInAsyncContextError):
            client.get("proj123")

        with pytest.raises(SyncInAsyncContextError):
            client.create(name="Test", workspace="ws123")

        with pytest.raises(SyncInAsyncContextError):
            client.update("proj123", name="Updated")

        with pytest.raises(SyncInAsyncContextError):
            client.delete("proj123")

        with pytest.raises(SyncInAsyncContextError):
            client.add_members("proj123", members=["u1"])

        with pytest.raises(SyncInAsyncContextError):
            client.remove_members("proj123", members=["u1"])

    async def test_sync_wrapper_fails_in_async_context_sections(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """SectionsClient sync methods fail in async context."""
        client = SectionsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        with pytest.raises(SyncInAsyncContextError):
            client.get("sec123")

        with pytest.raises(SyncInAsyncContextError):
            client.add_task("sec123", task="task123")

        with pytest.raises(SyncInAsyncContextError):
            client.insert_section("proj123", section="sec123")

    async def test_sync_wrapper_fails_in_async_context_custom_fields(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """CustomFieldsClient sync methods fail in async context."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )

        with pytest.raises(SyncInAsyncContextError):
            client.get("cf123")

        with pytest.raises(SyncInAsyncContextError):
            client.create_enum_option("cf123", name="Test")

        with pytest.raises(SyncInAsyncContextError):
            client.add_to_project("proj123", custom_field="cf123")

        with pytest.raises(SyncInAsyncContextError):
            client.remove_from_project("proj123", custom_field="cf123")


# =============================================================================
# 3. SPECIAL OPERATIONS TESTS
# =============================================================================


class TestProjectMembershipOperations:
    """Test ProjectsClient membership operations in detail."""

    async def test_add_members_joins_gids_with_comma(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """add_members_async joins member GIDs with comma."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {"gid": "proj123", "name": "Project"}

        await client.add_members_async("proj123", members=["user1", "user2", "user3"])

        mock_http.post.assert_called_with(
            "/projects/proj123/addMembers",
            json={"data": {"members": "user1,user2,user3"}},
        )

    async def test_add_members_single_member(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """add_members_async works with single member."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {"gid": "proj123", "name": "Project"}

        await client.add_members_async("proj123", members=["user1"])

        call_args = mock_http.post.call_args
        assert call_args[1]["json"]["data"]["members"] == "user1"

    async def test_remove_members_joins_gids_with_comma(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """remove_members_async joins member GIDs with comma."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {"gid": "proj123", "name": "Project"}

        await client.remove_members_async("proj123", members=["user1", "user2"])

        mock_http.post.assert_called_with(
            "/projects/proj123/removeMembers",
            json={"data": {"members": "user1,user2"}},
        )


class TestSectionTaskOperations:
    """Test SectionsClient task movement operations."""

    async def test_add_task_with_all_positioning_options(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """add_task_async includes all positioning options when specified."""
        client = SectionsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {}

        # Test with insert_before
        await client.add_task_async("sec123", task="task1", insert_before="task_ref")

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["task"] == "task1"
        assert data["insert_before"] == "task_ref"

        # Reset and test with insert_after
        mock_http.post.reset_mock()
        await client.add_task_async("sec123", task="task2", insert_after="task_ref2")

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["task"] == "task2"
        assert data["insert_after"] == "task_ref2"

    async def test_insert_section_with_positioning(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """insert_section_async includes positioning options."""
        client = SectionsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {}

        await client.insert_section_async(
            "proj123",
            section="sec456",
            before_section="sec_before",
        )

        call_args = mock_http.post.call_args
        assert call_args[0][0] == "/projects/proj123/sections/insert"
        data = call_args[1]["json"]["data"]
        assert data["section"] == "sec456"
        assert data["before_section"] == "sec_before"

    async def test_section_create_with_positioning(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create_async for sections includes positioning options."""
        client = SectionsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {"gid": "newsec", "name": "New"}

        await client.create_async(
            name="New Section",
            project="proj123",
            insert_before="sec_existing",
        )

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["name"] == "New Section"
        assert data["insert_before"] == "sec_existing"


class TestCustomFieldEnumOperations:
    """Test CustomFieldsClient enum option operations."""

    async def test_create_enum_option_all_params(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create_enum_option_async includes all parameters."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {"gid": "opt123", "name": "New Option"}

        await client.create_enum_option_async(
            "cf123",
            name="High Priority",
            color="red",
            enabled=True,
            insert_after="opt_existing",
        )

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["name"] == "High Priority"
        assert data["color"] == "red"
        assert data["enabled"] is True
        assert data["insert_after"] == "opt_existing"

    async def test_create_enum_option_default_enabled(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """create_enum_option_async defaults enabled to True."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {"gid": "opt123", "name": "Option"}

        await client.create_enum_option_async("cf123", name="Option")

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["enabled"] is True

    async def test_update_enum_option_endpoint(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """update_enum_option_async uses correct endpoint."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.put.return_value = {"gid": "opt123", "name": "Updated"}

        await client.update_enum_option_async("opt123", name="Updated", color="blue")

        mock_http.put.assert_called_with(
            "/enum_options/opt123",
            json={"data": {"name": "Updated", "color": "blue"}},
        )


class TestCustomFieldProjectOperations:
    """Test CustomFieldsClient project settings operations."""

    async def test_add_to_project_all_params(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """add_to_project_async includes all parameters."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {"gid": "setting123"}

        await client.add_to_project_async(
            "proj123",
            custom_field="cf456",
            is_important=True,
            insert_before="cf_existing",
        )

        call_args = mock_http.post.call_args
        data = call_args[1]["json"]["data"]
        assert data["custom_field"] == "cf456"
        assert data["is_important"] is True
        assert data["insert_before"] == "cf_existing"

    async def test_remove_from_project_returns_none(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """remove_from_project_async returns None."""
        client = CustomFieldsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.post.return_value = {}

        result = await client.remove_from_project_async("proj123", custom_field="cf456")

        assert result is None
        mock_http.post.assert_called_with(
            "/projects/proj123/removeCustomFieldSetting",
            json={"data": {"custom_field": "cf456"}},
        )


class TestUsersClientMe:
    """Test UsersClient.me() operation."""

    async def test_me_async_uses_me_endpoint(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """me_async calls /users/me endpoint."""
        client = UsersClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "me123", "name": "Current User"}

        await client.me_async()

        mock_http.get.assert_called_with("/users/me", params={})

    async def test_me_async_with_opt_fields(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """me_async includes opt_fields in request."""
        client = UsersClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "me123", "name": "Current User"}

        await client.me_async(opt_fields=["email", "workspaces"])

        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]


# =============================================================================
# 4. ASANACLIENT INTEGRATION TESTS
# =============================================================================


class TestAsanaClientProperties:
    """Test AsanaClient property access for all Tier 1 clients."""

    def test_all_client_properties_accessible(self) -> None:
        """All Tier 1 client properties are accessible."""
        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http_class.return_value = MagicMock()
            client = AsanaClient(token="test-token")

            # Access all properties - should not raise
            assert client.tasks is not None
            assert client.projects is not None
            assert client.sections is not None
            assert client.custom_fields is not None
            assert client.users is not None
            assert client.workspaces is not None

    def test_client_properties_return_correct_types(self) -> None:
        """Client properties return correct client types."""
        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http_class.return_value = MagicMock()
            client = AsanaClient(token="test-token")

            from autom8_asana.clients.tasks import TasksClient

            assert isinstance(client.tasks, TasksClient)
            assert isinstance(client.projects, ProjectsClient)
            assert isinstance(client.sections, SectionsClient)
            assert isinstance(client.custom_fields, CustomFieldsClient)
            assert isinstance(client.users, UsersClient)
            assert isinstance(client.workspaces, WorkspacesClient)


class TestAsanaClientLazyInitialization:
    """Test lazy initialization of resource clients."""

    def test_clients_not_created_on_init(self) -> None:
        """Resource clients are not created during AsanaClient init."""
        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http_class.return_value = MagicMock()
            client = AsanaClient(token="test-token")

            # Internal attributes should be None before access
            assert client._tasks is None
            assert client._projects is None
            assert client._sections is None
            assert client._custom_fields is None
            assert client._users is None
            assert client._workspaces is None

    def test_clients_created_on_first_access(self) -> None:
        """Resource clients are created on first property access."""
        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http_class.return_value = MagicMock()
            client = AsanaClient(token="test-token")

            # Before access
            assert client._projects is None

            # First access creates the client
            _ = client.projects

            # After access
            assert client._projects is not None
            assert isinstance(client._projects, ProjectsClient)

    def test_same_client_returned_on_multiple_access(self) -> None:
        """Same client instance returned on multiple property accesses."""
        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http_class.return_value = MagicMock()
            client = AsanaClient(token="test-token")

            first_access = client.workspaces
            second_access = client.workspaces
            third_access = client.workspaces

            assert first_access is second_access
            assert second_access is third_access


class TestAsanaClientHTTPSharing:
    """Test that all clients share the same HTTP client."""

    def test_all_clients_share_http_client(self) -> None:
        """All resource clients share the same HTTP client instance."""
        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http = MagicMock()
            mock_http_class.return_value = mock_http
            client = AsanaClient(token="test-token")

            # Access all clients
            tasks_http = client.tasks._http
            projects_http = client.projects._http
            sections_http = client.sections._http
            custom_fields_http = client.custom_fields._http
            users_http = client.users._http
            workspaces_http = client.workspaces._http

            # All should be the same instance
            assert tasks_http is projects_http
            assert projects_http is sections_http
            assert sections_http is custom_fields_http
            assert custom_fields_http is users_http
            assert users_http is workspaces_http


class TestAsanaClientThreadSafety:
    """Test thread safety of lazy initialization."""

    def test_concurrent_access_same_client(self) -> None:
        """Concurrent access from multiple threads returns same client."""
        with patch("autom8_asana.client.AsanaHttpClient") as mock_http_class:
            mock_http_class.return_value = MagicMock()
            client = AsanaClient(token="test-token")

            results: list[ProjectsClient] = []
            errors: list[Exception] = []

            def access_projects() -> None:
                try:
                    results.append(client.projects)
                except Exception as e:
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
                    raise AssertionError(
                        f"Thread {t.name} did not complete within timeout"
                    )

            # No errors should have occurred
            assert len(errors) == 0

            # All results should be the same instance
            assert len(results) == 10
            first = results[0]
            assert all(r is first for r in results)


# =============================================================================
# 5. EDGE CASE TESTS
# =============================================================================


class TestEmptyCollections:
    """Test handling of empty collections."""

    def test_project_empty_members_list(self) -> None:
        """Project handles empty members list."""
        project = Project.model_validate({"gid": "123", "members": []})
        assert project.members == []

    def test_project_empty_followers_list(self) -> None:
        """Project handles empty followers list."""
        project = Project.model_validate({"gid": "123", "followers": []})
        assert project.followers == []

    def test_user_empty_workspaces_list(self) -> None:
        """User handles empty workspaces list."""
        user = User.model_validate({"gid": "123", "workspaces": []})
        assert user.workspaces == []

    def test_custom_field_empty_enum_options(self) -> None:
        """CustomField handles empty enum_options list."""
        cf = CustomField.model_validate({"gid": "123", "enum_options": []})
        assert cf.enum_options == []

    def test_workspace_empty_email_domains(self) -> None:
        """Workspace handles empty email_domains list."""
        ws = Workspace.model_validate({"gid": "123", "email_domains": []})
        assert ws.email_domains == []

    async def test_page_iterator_empty_first_page(self) -> None:
        """PageIterator handles empty first page correctly."""

        async def fetch_page(offset: str | None) -> tuple[list[Any], str | None]:
            return [], None

        iterator = PageIterator(fetch_page)
        items = await iterator.collect()

        assert items == []

    async def test_page_iterator_first_on_empty(self) -> None:
        """PageIterator.first() returns None for empty results."""

        async def fetch_page(offset: str | None) -> tuple[list[Any], str | None]:
            return [], None

        iterator = PageIterator(fetch_page)
        result = await iterator.first()

        assert result is None


class TestNullVsMissing:
    """Test handling of null values vs missing fields."""

    def test_project_null_owner_vs_missing(self) -> None:
        """Project handles null owner vs missing owner."""
        # Explicit null
        project_null = Project.model_validate({"gid": "123", "owner": None})
        assert project_null.owner is None

        # Missing field
        project_missing = Project.model_validate({"gid": "123"})
        assert project_missing.owner is None

    def test_section_null_project_vs_missing(self) -> None:
        """Section handles null project vs missing project."""
        section_null = Section.model_validate({"gid": "123", "project": None})
        assert section_null.project is None

        section_missing = Section.model_validate({"gid": "123"})
        assert section_missing.project is None

    def test_custom_field_null_enum_value_vs_missing(self) -> None:
        """CustomField handles null enum_value vs missing."""
        cf_null = CustomField.model_validate({"gid": "123", "enum_value": None})
        assert cf_null.enum_value is None

        cf_missing = CustomField.model_validate({"gid": "123"})
        assert cf_missing.enum_value is None

    def test_workspace_null_name_vs_missing(self) -> None:
        """Workspace handles null name vs missing name."""
        ws_null = Workspace.model_validate({"gid": "123", "name": None})
        assert ws_null.name is None

        ws_missing = Workspace.model_validate({"gid": "123"})
        assert ws_missing.name is None


class TestUnicodeHandling:
    """Test handling of Unicode in various fields."""

    def test_workspace_unicode_name(self) -> None:
        """Workspace handles Unicode in name."""
        ws = Workspace.model_validate(
            {
                "gid": "123",
                "name": "Projet Alpha - Dev",
            }
        )
        assert ws.name == "Projet Alpha - Dev"

    def test_project_unicode_name_and_notes(self) -> None:
        """Project handles Unicode in name and notes."""
        project = Project.model_validate(
            {
                "gid": "123",
                "name": "Project Name",
                "notes": "Notes with emoji",
                "html_notes": "<p>HTML with emoji</p>",
            }
        )
        assert "emoji" in project.notes

    def test_user_unicode_name(self) -> None:
        """User handles Unicode in name."""
        user = User.model_validate(
            {
                "gid": "123",
                "name": "Yamada Taro",  # Japanese name
                "email": "taro@example.com",
            }
        )
        assert "Yamada" in user.name

    def test_section_unicode_name(self) -> None:
        """Section handles Unicode in name."""
        section = Section.model_validate(
            {
                "gid": "123",
                "name": "A Faire",  # French "To Do" with accent
            }
        )
        assert section.name == "A Faire"

    def test_custom_field_unicode_values(self) -> None:
        """CustomField handles Unicode in various fields."""
        cf = CustomField.model_validate(
            {
                "gid": "123",
                "name": "Priorite",  # French with accent
                "description": "Description with special chars: < > &",
                "text_value": "Chinese value",
            }
        )
        assert "Priorite" in cf.name

    def test_namegid_unicode(self) -> None:
        """NameGid handles Unicode in name."""
        ref = NameGid.model_validate(
            {
                "gid": "123",
                "name": "Internationalization Test",
            }
        )
        assert ref.name is not None


class TestLongStrings:
    """Test handling of very long strings."""

    def test_project_long_name(self) -> None:
        """Project handles long name."""
        long_name = "A" * 1000
        project = Project.model_validate({"gid": "123", "name": long_name})
        assert len(project.name) == 1000

    def test_project_long_notes(self) -> None:
        """Project handles long notes."""
        long_notes = "B" * 10000
        project = Project.model_validate({"gid": "123", "notes": long_notes})
        assert len(project.notes) == 10000

    def test_custom_field_long_description(self) -> None:
        """CustomField handles long description."""
        long_desc = "C" * 5000
        cf = CustomField.model_validate({"gid": "123", "description": long_desc})
        assert len(cf.description) == 5000

    def test_namegid_long_name(self) -> None:
        """NameGid handles long name."""
        long_name = "D" * 500
        ref = NameGid.model_validate({"gid": "123", "name": long_name})
        assert len(ref.name) == 500


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_custom_field_precision_zero(self) -> None:
        """CustomField handles precision of 0."""
        cf = CustomField.model_validate(
            {
                "gid": "123",
                "precision": 0,
            }
        )
        assert cf.precision == 0

    def test_custom_field_precision_max(self) -> None:
        """CustomField handles large precision value."""
        cf = CustomField.model_validate(
            {
                "gid": "123",
                "precision": 10,
            }
        )
        assert cf.precision == 10

    def test_project_many_members(self) -> None:
        """Project handles many members."""
        members = [{"gid": str(i), "name": f"User {i}"} for i in range(100)]
        project = Project.model_validate({"gid": "123", "members": members})
        assert len(project.members) == 100

    def test_custom_field_many_enum_options(self) -> None:
        """CustomField handles many enum options."""
        options = [{"gid": str(i), "name": f"Option {i}"} for i in range(50)]
        cf = CustomField.model_validate({"gid": "123", "enum_options": options})
        assert len(cf.enum_options) == 50


class TestOptFieldsParameter:
    """Test opt_fields parameter handling across clients."""

    async def test_workspaces_get_with_opt_fields(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """WorkspacesClient.get_async passes opt_fields correctly."""
        client = WorkspacesClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "ws123", "name": "Test"}

        await client.get_async("ws123", opt_fields=["name", "is_organization"])

        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]

    async def test_users_get_with_opt_fields(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """UsersClient.get_async passes opt_fields correctly."""
        client = UsersClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "1234567890123", "name": "Test"}

        await client.get_async(
            "1234567890123", opt_fields=["name", "email", "workspaces"]
        )

        call_args = mock_http.get.call_args
        assert "opt_fields" in call_args[1]["params"]


class TestProjectsSectionConvenience:
    """Test ProjectsClient.get_sections_async convenience method."""

    async def test_get_sections_async_returns_page_iterator(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """ProjectsClient.get_sections_async returns PageIterator[Section]."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = (
            [{"gid": "s1", "name": "To Do"}, {"gid": "s2", "name": "Done"}],
            None,
        )

        iterator = client.get_sections_async("proj123")
        assert isinstance(iterator, PageIterator)

        items = await iterator.collect()
        assert len(items) == 2
        assert all(isinstance(s, Section) for s in items)

    async def test_get_sections_async_calls_correct_endpoint(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
    ) -> None:
        """ProjectsClient.get_sections_async calls correct API endpoint."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,  # type: ignore
        )
        mock_http.get_paginated.return_value = ([{"gid": "s1", "name": "Test"}], None)

        iterator = client.get_sections_async("proj123")
        await iterator.collect()

        call_args = mock_http.get_paginated.call_args
        assert call_args[0][0] == "/projects/proj123/sections"


# =============================================================================
# MODEL INHERITANCE TESTS
# =============================================================================


class TestModelInheritance:
    """Test model inheritance from AsanaResource."""

    def test_all_models_inherit_from_asana_resource(self) -> None:
        """All Tier 1 models inherit from AsanaResource."""
        assert issubclass(Workspace, AsanaResource)
        assert issubclass(User, AsanaResource)
        assert issubclass(Project, AsanaResource)
        assert issubclass(Section, AsanaResource)
        assert issubclass(CustomField, AsanaResource)
        assert issubclass(CustomFieldEnumOption, AsanaResource)
        assert issubclass(CustomFieldSetting, AsanaResource)

    def test_all_models_have_gid_field(self) -> None:
        """All models have gid field from AsanaResource."""
        ws = Workspace(gid="123")
        assert hasattr(ws, "gid")
        assert ws.gid == "123"

        user = User(gid="456")
        assert hasattr(user, "gid")
        assert user.gid == "456"

    def test_all_models_have_resource_type_field(self) -> None:
        """All models have resource_type field from AsanaResource."""
        ws = Workspace(gid="123")
        assert hasattr(ws, "resource_type")
        assert ws.resource_type == "workspace"

        project = Project(gid="456")
        assert project.resource_type == "project"

        section = Section(gid="789")
        assert section.resource_type == "section"


class TestModelDefaults:
    """Test default values for model fields."""

    def test_workspace_defaults(self) -> None:
        """Workspace has correct default resource_type."""
        ws = Workspace(gid="123")
        assert ws.resource_type == "workspace"
        assert ws.name is None
        assert ws.is_organization is None
        assert ws.email_domains is None

    def test_user_defaults(self) -> None:
        """User has correct default resource_type."""
        user = User(gid="123")
        assert user.resource_type == "user"
        assert user.name is None
        assert user.email is None
        assert user.photo is None
        assert user.workspaces is None

    def test_project_defaults(self) -> None:
        """Project has correct default resource_type."""
        project = Project(gid="123")
        assert project.resource_type == "project"
        assert project.name is None
        assert project.archived is None
        assert project.public is None

    def test_section_defaults(self) -> None:
        """Section has correct default resource_type."""
        section = Section(gid="123")
        assert section.resource_type == "section"
        assert section.name is None
        assert section.project is None

    def test_custom_field_defaults(self) -> None:
        """CustomField has correct default resource_type."""
        cf = CustomField(gid="123")
        assert cf.resource_type == "custom_field"
        assert cf.name is None
        assert cf.resource_subtype is None

    def test_custom_field_enum_option_defaults(self) -> None:
        """CustomFieldEnumOption has correct default resource_type."""
        opt = CustomFieldEnumOption(gid="123")
        assert opt.resource_type == "enum_option"
        assert opt.name is None
        assert opt.enabled is None
        assert opt.color is None

    def test_custom_field_setting_defaults(self) -> None:
        """CustomFieldSetting has correct default resource_type."""
        setting = CustomFieldSetting(gid="123")
        assert setting.resource_type == "custom_field_setting"
        assert setting.custom_field is None
        assert setting.project is None
        assert setting.is_important is None


# =============================================================================
# LOGGING TESTS
# =============================================================================


class TestClientLogging:
    """Test that clients log operations correctly."""

    async def test_client_logs_get_operation(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
        logger: MockLogger,
    ) -> None:
        """Client logs get operations."""
        client = WorkspacesClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,
            log_provider=logger,  # type: ignore
        )
        mock_http.get.return_value = {"gid": "ws123", "name": "Test"}

        await client.get_async("ws123")

        # Should have logged something (SDK MockLogger: .entries with .level/.event)
        assert len(logger.entries) > 0
        # Should have logged at debug level
        assert len(logger.get_events("debug")) > 0

    async def test_client_logs_list_operation(
        self,
        mock_http: MockHTTPClient,
        config: AsanaConfig,
        auth_provider: MockAuthProvider,
        logger: MockLogger,
    ) -> None:
        """Client logs list operations."""
        client = ProjectsClient(
            http=mock_http,
            config=config,
            auth_provider=auth_provider,
            log_provider=logger,  # type: ignore
        )
        mock_http.get_paginated.return_value = ([{"gid": "p1", "name": "Test"}], None)

        iterator = client.list_async(workspace="ws123")
        await iterator.collect()

        # Should have logged something (SDK MockLogger: .entries with .level/.event)
        assert len(logger.entries) > 0
