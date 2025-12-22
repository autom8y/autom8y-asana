"""Webhooks client - returns typed Webhook models by default.

Per TDD-0004: WebhooksClient provides webhook CRUD and signature verification.
Per ADR-0008: Signature verification uses HMAC-SHA256 with static methods.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.models import PageIterator
from autom8_asana.models.webhook import Webhook
from autom8_asana.transport.sync import sync_wrapper


class WebhooksClient(BaseClient):
    """Client for Asana Webhook operations.

    Provides CRUD operations for webhooks and signature verification
    for incoming webhook events.

    Returns typed Webhook models by default. Use raw=True for dict returns.

    Per ADR-0008: Signature verification uses HMAC-SHA256 with the
    webhook secret provided during creation.
    """

    # --- Core CRUD Operations ---

    @overload
    async def get_async(
        self,
        webhook_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Webhook:
        """Overload: get, returning Webhook model."""
        ...

    @overload
    async def get_async(
        self,
        webhook_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

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
        self._log_operation("get_async", webhook_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/webhooks/{webhook_gid}", params=params)
        if raw:
            return data
        return Webhook.model_validate(data)

    @overload
    def get(
        self,
        webhook_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Webhook:
        """Overload: get (sync), returning Webhook model."""
        ...

    @overload
    def get(
        self,
        webhook_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    def get(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Get a webhook by GID (sync).

        Args:
            webhook_gid: Webhook GID
            raw: If True, return raw dict instead of Webhook model
            opt_fields: Optional fields to include

        Returns:
            Webhook model by default, or dict if raw=True
        """
        return self._get_sync(webhook_gid, raw=raw, opt_fields=opt_fields)

    @sync_wrapper("get_async")
    async def _get_sync(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.get_async(webhook_gid, raw=True, opt_fields=opt_fields)
        return await self.get_async(webhook_gid, raw=False, opt_fields=opt_fields)

    @overload
    async def create_async(
        self,
        *,
        resource: str,
        target: str,
        raw: Literal[False] = ...,
        filters: list[dict[str, Any]] | None = ...,
    ) -> Webhook:
        """Overload: create, returning Webhook model."""
        ...

    @overload
    async def create_async(
        self,
        *,
        resource: str,
        target: str,
        raw: Literal[True],
        filters: list[dict[str, Any]] | None = ...,
    ) -> dict[str, Any]:
        """Overload: create, returning raw dict."""
        ...

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
        self._log_operation("create_async")

        data: dict[str, Any] = {"resource": resource, "target": target}

        if filters is not None:
            data["filters"] = filters

        result = await self._http.post("/webhooks", json={"data": data})
        if raw:
            return result
        return Webhook.model_validate(result)

    @overload
    def create(
        self,
        *,
        resource: str,
        target: str,
        raw: Literal[False] = ...,
        filters: list[dict[str, Any]] | None = ...,
    ) -> Webhook:
        """Overload: create (sync), returning Webhook model."""
        ...

    @overload
    def create(
        self,
        *,
        resource: str,
        target: str,
        raw: Literal[True],
        filters: list[dict[str, Any]] | None = ...,
    ) -> dict[str, Any]:
        """Overload: create (sync), returning raw dict."""
        ...

    def create(
        self,
        *,
        resource: str,
        target: str,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Create a webhook (sync).

        Args:
            resource: GID of the resource to watch
            target: URL to receive webhook events
            raw: If True, return raw dict
            filters: Optional event filters

        Returns:
            Webhook model by default, or dict if raw=True
        """
        return self._create_sync(
            resource=resource, target=target, raw=raw, filters=filters
        )

    @sync_wrapper("create_async")
    async def _create_sync(
        self,
        *,
        resource: str,
        target: str,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.create_async(
                resource=resource, target=target, raw=True, filters=filters
            )
        return await self.create_async(
            resource=resource, target=target, raw=False, filters=filters
        )

    @overload
    async def update_async(
        self,
        webhook_gid: str,
        *,
        raw: Literal[False] = ...,
        filters: list[dict[str, Any]] | None = ...,
    ) -> Webhook:
        """Overload: update, returning Webhook model."""
        ...

    @overload
    async def update_async(
        self,
        webhook_gid: str,
        *,
        raw: Literal[True],
        filters: list[dict[str, Any]] | None = ...,
    ) -> dict[str, Any]:
        """Overload: update, returning raw dict."""
        ...

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
        self._log_operation("update_async", webhook_gid)

        data: dict[str, Any] = {}
        if filters is not None:
            data["filters"] = filters

        result = await self._http.put(f"/webhooks/{webhook_gid}", json={"data": data})
        if raw:
            return result
        return Webhook.model_validate(result)

    @overload
    def update(
        self,
        webhook_gid: str,
        *,
        raw: Literal[False] = ...,
        filters: list[dict[str, Any]] | None = ...,
    ) -> Webhook:
        """Overload: update (sync), returning Webhook model."""
        ...

    @overload
    def update(
        self,
        webhook_gid: str,
        *,
        raw: Literal[True],
        filters: list[dict[str, Any]] | None = ...,
    ) -> dict[str, Any]:
        """Overload: update (sync), returning raw dict."""
        ...

    def update(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Update a webhook (sync).

        Args:
            webhook_gid: Webhook GID
            raw: If True, return raw dict
            filters: New event filters

        Returns:
            Webhook model by default, or dict if raw=True
        """
        return self._update_sync(webhook_gid, raw=raw, filters=filters)

    @sync_wrapper("update_async")
    async def _update_sync(
        self,
        webhook_gid: str,
        *,
        raw: bool = False,
        filters: list[dict[str, Any]] | None = None,
    ) -> Webhook | dict[str, Any]:
        """Internal sync wrapper implementation."""
        if raw:
            return await self.update_async(webhook_gid, raw=True, filters=filters)
        return await self.update_async(webhook_gid, raw=False, filters=filters)

    async def delete_async(self, webhook_gid: str) -> None:
        """Delete a webhook.

        Args:
            webhook_gid: Webhook GID
        """
        self._log_operation("delete_async", webhook_gid)
        await self._http.delete(f"/webhooks/{webhook_gid}")

    @sync_wrapper("delete_async")
    async def _delete_sync(self, webhook_gid: str) -> None:
        """Internal sync wrapper implementation."""
        await self.delete_async(webhook_gid)

    def delete(self, webhook_gid: str) -> None:
        """Delete a webhook (sync).

        Args:
            webhook_gid: Webhook GID
        """
        self._delete_sync(webhook_gid)

    # --- List Operations ---

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
        self._log_operation("list_for_workspace_async", workspace_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Webhook], str | None]:
            """Fetch a single page of Webhook objects."""
            params = self._build_opt_fields(opt_fields)
            params["workspace"] = workspace_gid
            if resource:
                params["resource"] = resource
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                "/webhooks", params=params
            )
            webhooks = [Webhook.model_validate(w) for w in data]
            return webhooks, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Signature Verification (per ADR-0008) ---

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
            secret.encode("utf-8"),
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
            if key.lower() == "x-hook-secret":
                return value
        return None
