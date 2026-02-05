"""Custom fields client - returns typed CustomField models by default.

Per TDD-0003: CustomFieldsClient provides CRUD, enum options, and project settings.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.custom_field import (
    CustomField,
    CustomFieldEnumOption,
    CustomFieldSetting,
)
from autom8_asana.observability import error_handler
from autom8_asana.settings import get_settings
from autom8_asana.transport.sync import sync_wrapper

# Cache TTL for custom field metadata (30 minutes)
# Custom fields change infrequently (structure/enum options rarely modified)
# Configurable via ASANA_CACHE_TTL_CUSTOM_FIELD environment variable
CUSTOM_FIELD_CACHE_TTL = get_settings().cache.ttl_custom_field


class CustomFieldsClient(BaseClient):
    """Client for Asana Custom Field operations.

    Returns typed CustomField models by default. Use raw=True for dict returns.
    """

    # --- Core CRUD Operations ---

    @overload
    async def get_async(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> CustomField:
        """Overload: get, returning CustomField model."""
        ...

    @overload
    async def get_async(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    @error_handler
    async def get_async(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> CustomField | dict[str, Any]:
        """Get a custom field by GID with cache support.

        Per TDD-CACHE-UTILIZATION: Checks cache before HTTP request.
        Per ADR-0119: 6-step client cache integration pattern.

        Args:
            custom_field_gid: Custom field GID
            raw: If True, return raw dict instead of CustomField model
            opt_fields: Optional fields to include

        Returns:
            CustomField model by default, or dict if raw=True

        Raises:
            GidValidationError: If custom_field_gid is invalid.
        """
        from autom8_asana.cache.models.entry import EntryType
        from autom8_asana.persistence.validation import validate_gid

        # Step 1: Validate GID
        validate_gid(custom_field_gid, "custom_field_gid")

        # Step 2: Check cache first
        cached_entry = self._cache_get(custom_field_gid, EntryType.CUSTOM_FIELD)
        if cached_entry is not None:
            # Step 3: Cache hit - return cached data
            data = cached_entry.data
            if raw:
                return data
            return CustomField.model_validate(data)

        # Step 4: Cache miss - fetch from API
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/custom_fields/{custom_field_gid}", params=params)

        # Step 5: Store in cache
        self._cache_set(custom_field_gid, data, EntryType.CUSTOM_FIELD, ttl=CUSTOM_FIELD_CACHE_TTL)

        # Step 6: Return model or raw dict
        if raw:
            return data
        return CustomField.model_validate(data)

    @overload
    def get(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> CustomField:
        """Overload: get (sync), returning CustomField model."""
        ...

    @overload
    def get(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> CustomField | dict[str, Any]:
        """Get a custom field by GID (sync).

        Args:
            custom_field_gid: Custom field GID
            raw: If True, return raw dict instead of CustomField model
            opt_fields: Optional fields to include

        Returns:
            CustomField model by default, or dict if raw=True
        """
        return self._get_sync(custom_field_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> CustomField | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(
                custom_field_gid, raw=True, opt_fields=opt_fields
            )
        return await self.get_async(custom_field_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        resource_subtype: str,
        raw: Literal[False] = ...,
        description: str | None = ...,
        enum_options: list[dict[str, Any]] | None = ...,
        precision: int | None = ...,
        format: str | None = ...,
        currency_code: str | None = ...,
        **kwargs: Any,
    ) -> CustomField:
        """Overload: create, returning CustomField model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        workspace: str,
        name: str,
        resource_subtype: str,
        raw: Literal[True],
        description: str | None = ...,
        enum_options: list[dict[str, Any]] | None = ...,
        precision: int | None = ...,
        format: str | None = ...,
        currency_code: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: create, returning raw dict."""
        ...

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
            workspace: Workspace GID (required)
            name: Custom field name (required)
            resource_subtype: Type (text, number, enum, multi_enum, date, people)
            raw: If True, return raw dict instead of CustomField model
            description: Field description
            enum_options: For enum types, list of option definitions
            precision: For number type, decimal precision
            format: Display format
            currency_code: For currency format
            **kwargs: Additional custom field fields

        Returns:
            CustomField model by default, or dict if raw=True
        """
        self._log_operation("create_async")

        data: dict[str, Any] = {
            "workspace": workspace,
            "name": name,
            "resource_subtype": resource_subtype,
        }

        if description is not None:
            data["description"] = description
        if enum_options is not None:
            data["enum_options"] = enum_options
        if precision is not None:
            data["precision"] = precision
        if format is not None:
            data["format"] = format
        if currency_code is not None:
            data["currency_code"] = currency_code

        data.update(kwargs)

        result = await self._http.post("/custom_fields", json={"data": data})
        if raw:
            return result
        return CustomField.model_validate(result)

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        resource_subtype: str,
        raw: Literal[False] = ...,
        description: str | None = ...,
        enum_options: list[dict[str, Any]] | None = ...,
        precision: int | None = ...,
        format: str | None = ...,
        currency_code: str | None = ...,
        **kwargs: Any,
    ) -> CustomField:
        """Overload: create (sync), returning CustomField model."""
        ...

    @overload
    def create(
        self,
        *,
        workspace: str,
        name: str,
        resource_subtype: str,
        raw: Literal[True],
        description: str | None = ...,
        enum_options: list[dict[str, Any]] | None = ...,
        precision: int | None = ...,
        format: str | None = ...,
        currency_code: str | None = ...,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: create (sync), returning raw dict."""
        ...

    def create(
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
        """Create a new custom field (sync).

        Args:
            workspace: Workspace GID (required)
            name: Custom field name (required)
            resource_subtype: Type (text, number, enum, multi_enum, date, people)
            raw: If True, return raw dict instead of CustomField model
            description: Field description
            enum_options: For enum types, list of option definitions
            precision: For number type, decimal precision
            format: Display format
            currency_code: For currency format
            **kwargs: Additional custom field fields

        Returns:
            CustomField model by default, or dict if raw=True
        """
        return self._create_sync(
            workspace=workspace,
            name=name,
            resource_subtype=resource_subtype,
            raw=raw,
            description=description,
            enum_options=enum_options,
            precision=precision,
            format=format,
            currency_code=currency_code,
            **kwargs,
        )

    @sync_wrapper("create_async")
    async def _create_sync(
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
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_async(
                workspace=workspace,
                name=name,
                resource_subtype=resource_subtype,
                raw=True,
                description=description,
                enum_options=enum_options,
                precision=precision,
                format=format,
                currency_code=currency_code,
                **kwargs,
            )
        return await self.create_async(
            workspace=workspace,
            name=name,
            resource_subtype=resource_subtype,
            raw=False,
            description=description,
            enum_options=enum_options,
            precision=precision,
            format=format,
            currency_code=currency_code,
            **kwargs,
        )

    @overload
    async def update_async(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> CustomField:
        """Overload: update, returning CustomField model."""
        ...

    @overload
    async def update_async(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

    async def update_async(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomField | dict[str, Any]:
        """Update a custom field.

        Args:
            custom_field_gid: Custom field GID
            raw: If True, return raw dict instead of CustomField model
            **kwargs: Fields to update

        Returns:
            CustomField model by default, or dict if raw=True
        """
        self._log_operation("update_async", custom_field_gid)
        result = await self._http.put(
            f"/custom_fields/{custom_field_gid}", json={"data": kwargs}
        )
        if raw:
            return result
        return CustomField.model_validate(result)

    @overload
    def update(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> CustomField:
        """Overload: update (sync), returning CustomField model."""
        ...

    @overload
    def update(
        self,
        custom_field_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    def update(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomField | dict[str, Any]:
        """Update a custom field (sync).

        Args:
            custom_field_gid: Custom field GID
            raw: If True, return raw dict instead of CustomField model
            **kwargs: Fields to update

        Returns:
            CustomField model by default, or dict if raw=True
        """
        return self._update_sync(custom_field_gid, raw=raw, **kwargs)

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        custom_field_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomField | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_async(custom_field_gid, raw=True, **kwargs)
        return await self.update_async(custom_field_gid, raw=False, **kwargs)

    async def delete_async(self, custom_field_gid: str) -> None:
        """Delete a custom field.

        Args:
            custom_field_gid: Custom field GID
        """
        self._log_operation("delete_async", custom_field_gid)
        await self._http.delete(f"/custom_fields/{custom_field_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, custom_field_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(custom_field_gid)

    def delete(self, custom_field_gid: str) -> None:
        """Delete a custom field (sync).

        Args:
            custom_field_gid: Custom field GID
        """
        self._delete_sync(custom_field_gid)

    def list_for_workspace_async(
        self,
        workspace_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[CustomField]:
        """List custom fields in a workspace with automatic pagination.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            workspace_gid: Workspace GID
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[CustomField] - async iterator over CustomField objects

        Example:
            async for cf in client.custom_fields.list_for_workspace_async("123"):
                print(f"{cf.name}: {cf.resource_subtype}")
        """
        self._log_operation("list_for_workspace_async", workspace_gid)

        async def fetch_page(
            offset: str | None,
        ) -> tuple[list[CustomField], str | None]:
            """Fetch a single page of CustomField objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/workspaces/{workspace_gid}/custom_fields", params=params
            )
            custom_fields = [CustomField.model_validate(cf) for cf in data]
            return custom_fields, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Enum Option Operations ---

    @overload
    async def create_enum_option_async(
        self,
        custom_field_gid: str,
        *,
        name: str,
        raw: Literal[False] = ...,
        color: str | None = ...,
        enabled: bool = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> CustomFieldEnumOption:
        """Overload: create enum option, returning CustomFieldEnumOption model."""
        ...

    @overload
    async def create_enum_option_async(
        self,
        custom_field_gid: str,
        *,
        name: str,
        raw: Literal[True],
        color: str | None = ...,
        enabled: bool = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: create enum option, returning raw dict."""
        ...

    async def create_enum_option_async(
        self,
        custom_field_gid: str,
        *,
        name: str,
        raw: bool = False,
        color: str | None = None,
        enabled: bool = True,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Create a new enum option for a custom field.

        Args:
            custom_field_gid: Custom field GID
            name: Option name (required)
            raw: If True, return raw dict instead of CustomFieldEnumOption model
            color: Option color
            enabled: Whether the option is enabled (default True)
            insert_before: Enum option GID to insert before
            insert_after: Enum option GID to insert after

        Returns:
            CustomFieldEnumOption model by default, or dict if raw=True
        """
        self._log_operation("create_enum_option_async", custom_field_gid)

        data: dict[str, Any] = {"name": name, "enabled": enabled}
        if color is not None:
            data["color"] = color
        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        result = await self._http.post(
            f"/custom_fields/{custom_field_gid}/enum_options", json={"data": data}
        )
        if raw:
            return result
        return CustomFieldEnumOption.model_validate(result)

    @overload
    def create_enum_option(
        self,
        custom_field_gid: str,
        *,
        name: str,
        raw: Literal[False] = ...,
        color: str | None = ...,
        enabled: bool = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> CustomFieldEnumOption:
        """Overload: create enum option (sync), returning CustomFieldEnumOption model."""
        ...

    @overload
    def create_enum_option(
        self,
        custom_field_gid: str,
        *,
        name: str,
        raw: Literal[True],
        color: str | None = ...,
        enabled: bool = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: create enum option (sync), returning raw dict."""
        ...

    def create_enum_option(
        self,
        custom_field_gid: str,
        *,
        name: str,
        raw: bool = False,
        color: str | None = None,
        enabled: bool = True,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Create a new enum option for a custom field (sync).

        Args:
            custom_field_gid: Custom field GID
            name: Option name (required)
            raw: If True, return raw dict instead of CustomFieldEnumOption model
            color: Option color
            enabled: Whether the option is enabled (default True)
            insert_before: Enum option GID to insert before
            insert_after: Enum option GID to insert after

        Returns:
            CustomFieldEnumOption model by default, or dict if raw=True
        """
        return self._create_enum_option_sync(
            custom_field_gid,
            name=name,
            raw=raw,
            color=color,
            enabled=enabled,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    @sync_wrapper("create_enum_option_async")
    async def _create_enum_option_sync(
        self,
        custom_field_gid: str,
        *,
        name: str,
        raw: bool = False,
        color: str | None = None,
        enabled: bool = True,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_enum_option_async(
                custom_field_gid,
                name=name,
                raw=True,
                color=color,
                enabled=enabled,
                insert_before=insert_before,
                insert_after=insert_after,
            )
        return await self.create_enum_option_async(
            custom_field_gid,
            name=name,
            raw=False,
            color=color,
            enabled=enabled,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    @overload
    async def update_enum_option_async(
        self,
        enum_option_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> CustomFieldEnumOption:
        """Overload: update enum option, returning CustomFieldEnumOption model."""
        ...

    @overload
    async def update_enum_option_async(
        self,
        enum_option_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update enum option, returning raw dict."""
        ...

    async def update_enum_option_async(
        self,
        enum_option_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Update an enum option.

        Args:
            enum_option_gid: Enum option GID
            raw: If True, return raw dict instead of CustomFieldEnumOption model
            **kwargs: Fields to update (name, color, enabled)

        Returns:
            CustomFieldEnumOption model by default, or dict if raw=True
        """
        self._log_operation("update_enum_option_async", enum_option_gid)
        result = await self._http.put(
            f"/enum_options/{enum_option_gid}", json={"data": kwargs}
        )
        if raw:
            return result
        return CustomFieldEnumOption.model_validate(result)

    @overload
    def update_enum_option(
        self,
        enum_option_gid: str,
        *,
        raw: Literal[False] = ...,
        **kwargs: Any,
    ) -> CustomFieldEnumOption:
        """Overload: update enum option (sync), returning CustomFieldEnumOption model."""
        ...

    @overload
    def update_enum_option(
        self,
        enum_option_gid: str,
        *,
        raw: Literal[True],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Overload: update enum option (sync), returning raw dict."""
        ...

    def update_enum_option(
        self,
        enum_option_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Update an enum option (sync).

        Args:
            enum_option_gid: Enum option GID
            raw: If True, return raw dict instead of CustomFieldEnumOption model
            **kwargs: Fields to update (name, color, enabled)

        Returns:
            CustomFieldEnumOption model by default, or dict if raw=True
        """
        return self._update_enum_option_sync(enum_option_gid, raw=raw, **kwargs)

    @sync_wrapper("update_enum_option_async")
    async def _update_enum_option_sync(
        self,
        enum_option_gid: str,
        *,
        raw: bool = False,
        **kwargs: Any,
    ) -> CustomFieldEnumOption | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_enum_option_async(
                enum_option_gid, raw=True, **kwargs
            )
        return await self.update_enum_option_async(enum_option_gid, raw=False, **kwargs)

    # --- Project Settings Operations ---

    def get_settings_for_project_async(
        self,
        project_gid: str,
        *,
        opt_fields: list[str] | None = None,
        limit: int = 100,
    ) -> PageIterator[CustomFieldSetting]:
        """Get custom field settings for a project.

        Returns a PageIterator that lazily fetches pages as you iterate.

        Args:
            project_gid: Project GID
            opt_fields: Fields to include in response
            limit: Number of items per page (default 100, max 100)

        Returns:
            PageIterator[CustomFieldSetting] - async iterator over settings

        Example:
            async for setting in client.custom_fields.get_settings_for_project_async("123"):
                print(f"Field: {setting.custom_field.name}")
        """
        self._log_operation("get_settings_for_project_async", project_gid)

        async def fetch_page(
            offset: str | None,
        ) -> tuple[list[CustomFieldSetting], str | None]:
            """Fetch a single page of CustomFieldSetting objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)  # Asana max is 100
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/projects/{project_gid}/custom_field_settings", params=params
            )
            settings = [CustomFieldSetting.model_validate(s) for s in data]
            return settings, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    @overload
    async def add_to_project_async(
        self,
        project_gid: str,
        *,
        custom_field: str,
        raw: Literal[False] = ...,
        is_important: bool | None = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> CustomFieldSetting:
        """Overload: add to project, returning CustomFieldSetting model."""
        ...

    @overload
    async def add_to_project_async(
        self,
        project_gid: str,
        *,
        custom_field: str,
        raw: Literal[True],
        is_important: bool | None = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: add to project, returning raw dict."""
        ...

    async def add_to_project_async(
        self,
        project_gid: str,
        *,
        custom_field: str,
        raw: bool = False,
        is_important: bool | None = None,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldSetting | dict[str, Any]:
        """Add a custom field to a project.

        Args:
            project_gid: Project GID
            custom_field: Custom field GID to add
            raw: If True, return raw dict instead of CustomFieldSetting model
            is_important: Whether to mark as important
            insert_before: Custom field GID to insert before
            insert_after: Custom field GID to insert after

        Returns:
            CustomFieldSetting model by default, or dict if raw=True
        """
        self._log_operation("add_to_project_async", project_gid)

        data: dict[str, Any] = {"custom_field": custom_field}
        if is_important is not None:
            data["is_important"] = is_important
        if insert_before is not None:
            data["insert_before"] = insert_before
        if insert_after is not None:
            data["insert_after"] = insert_after

        result = await self._http.post(
            f"/projects/{project_gid}/addCustomFieldSetting", json={"data": data}
        )
        if raw:
            return result
        return CustomFieldSetting.model_validate(result)

    @overload
    def add_to_project(
        self,
        project_gid: str,
        *,
        custom_field: str,
        raw: Literal[False] = ...,
        is_important: bool | None = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> CustomFieldSetting:
        """Overload: add to project (sync), returning CustomFieldSetting model."""
        ...

    @overload
    def add_to_project(
        self,
        project_gid: str,
        *,
        custom_field: str,
        raw: Literal[True],
        is_important: bool | None = ...,
        insert_before: str | None = ...,
        insert_after: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: add to project (sync), returning raw dict."""
        ...

    def add_to_project(
        self,
        project_gid: str,
        *,
        custom_field: str,
        raw: bool = False,
        is_important: bool | None = None,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldSetting | dict[str, Any]:
        """Add a custom field to a project (sync).

        Args:
            project_gid: Project GID
            custom_field: Custom field GID to add
            raw: If True, return raw dict instead of CustomFieldSetting model
            is_important: Whether to mark as important
            insert_before: Custom field GID to insert before
            insert_after: Custom field GID to insert after

        Returns:
            CustomFieldSetting model by default, or dict if raw=True
        """
        return self._add_to_project_sync(
            project_gid,
            custom_field=custom_field,
            raw=raw,
            is_important=is_important,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    @sync_wrapper("add_to_project_async")
    async def _add_to_project_sync(
        self,
        project_gid: str,
        *,
        custom_field: str,
        raw: bool = False,
        is_important: bool | None = None,
        insert_before: str | None = None,
        insert_after: str | None = None,
    ) -> CustomFieldSetting | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.add_to_project_async(
                project_gid,
                custom_field=custom_field,
                raw=True,
                is_important=is_important,
                insert_before=insert_before,
                insert_after=insert_after,
            )
        return await self.add_to_project_async(
            project_gid,
            custom_field=custom_field,
            raw=False,
            is_important=is_important,
            insert_before=insert_before,
            insert_after=insert_after,
        )

    async def remove_from_project_async(
        self,
        project_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Remove a custom field from a project.

        Args:
            project_gid: Project GID
            custom_field: Custom field GID to remove
        """
        self._log_operation("remove_from_project_async", project_gid)
        await self._http.post(
            f"/projects/{project_gid}/removeCustomFieldSetting",
            json={"data": {"custom_field": custom_field}},
        )

    @sync_wrapper("remove_from_project_async")
    async def _remove_from_project_sync(
        self,
        project_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Internal sync wrapper implementation."""
        await self.remove_from_project_async(project_gid, custom_field=custom_field)

    def remove_from_project(
        self,
        project_gid: str,
        *,
        custom_field: str,
    ) -> None:
        """Remove a custom field from a project (sync).

        Args:
            project_gid: Project GID
            custom_field: Custom field GID to remove
        """
        self._remove_from_project_sync(project_gid, custom_field=custom_field)
