"""Attachments client - returns typed Attachment models by default.

Per TDD-0004: AttachmentsClient provides attachment operations for Tier 2.
Per TDD-DESIGN-PATTERNS-D: Uses @async_method for async/sync method generation.
Per ADR-0009: Uses multipart/form-data for file uploads, streaming for downloads.
Use raw=True for backward-compatible dict returns.
"""

from __future__ import annotations

import asyncio
import mimetypes
from pathlib import Path
from typing import Any, BinaryIO, Literal, overload

from autom8_asana.clients.base import BaseClient
from autom8_asana.errors import AsanaError
from autom8_asana.models import PageIterator
from autom8_asana.models.attachment import Attachment
from autom8_asana.patterns import async_method


class AttachmentsClient(BaseClient):
    """Client for Asana Attachment operations.

    Supports file upload via multipart/form-data and streaming download.
    Per ADR-0009: Uses httpx's streaming capabilities.

    Returns typed Attachment models by default. Use raw=True for dict returns.
    """

    # --- Core Operations ---

    @overload  # type: ignore[no-overload-impl]
    async def get_async(
        self,
        attachment_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Attachment:
        """Overload: get, returning Attachment model."""
        ...

    @overload
    async def get_async(
        self,
        attachment_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get, returning raw dict."""
        ...

    @overload
    def get(
        self,
        attachment_gid: str,
        *,
        raw: Literal[False] = ...,
        opt_fields: list[str] | None = ...,
    ) -> Attachment:
        """Overload: get (sync), returning Attachment model."""
        ...

    @overload
    def get(
        self,
        attachment_gid: str,
        *,
        raw: Literal[True],
        opt_fields: list[str] | None = ...,
    ) -> dict[str, Any]:
        """Overload: get (sync), returning raw dict."""
        ...

    @async_method  # type: ignore[operator, misc]
    async def get(
        self,
        attachment_gid: str,
        *,
        raw: bool = False,
        opt_fields: list[str] | None = None,
    ) -> Attachment | dict[str, Any]:
        """Get an attachment by GID.

        Args:
            attachment_gid: Attachment GID
            raw: If True, return raw dict instead of Attachment model
            opt_fields: Optional fields to include

        Returns:
            Attachment model by default, or dict if raw=True
        """
        self._log_operation("get_async", attachment_gid)
        params = self._build_opt_fields(opt_fields)
        data = await self._http.get(f"/attachments/{attachment_gid}", params=params)
        if raw:
            return data
        return Attachment.model_validate(data)

    @async_method
    async def delete(self, attachment_gid: str) -> None:
        """Delete an attachment.

        Args:
            attachment_gid: Attachment GID
        """
        self._log_operation("delete_async", attachment_gid)
        await self._http.delete(f"/attachments/{attachment_gid}")

    # --- List Operations ---

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
        self._log_operation("list_for_task_async", task_gid)

        async def fetch_page(offset: str | None) -> tuple[list[Attachment], str | None]:
            """Fetch a single page of Attachment objects."""
            params = self._build_opt_fields(opt_fields)
            params["limit"] = min(limit, 100)
            if offset:
                params["offset"] = offset

            data, next_offset = await self._http.get_paginated(
                f"/tasks/{task_gid}/attachments", params=params
            )
            attachments = [Attachment.model_validate(a) for a in data]
            return attachments, next_offset

        return PageIterator(fetch_page, page_size=min(limit, 100))

    # --- Upload Operations (per ADR-0009) ---

    @overload  # type: ignore[no-overload-impl]
    async def upload_async(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: Literal[False] = ...,
        content_type: str | None = ...,
    ) -> Attachment:
        """Overload: upload, returning Attachment model."""
        ...

    @overload
    async def upload_async(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: Literal[True],
        content_type: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: upload, returning raw dict."""
        ...

    @overload
    def upload(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: Literal[False] = ...,
        content_type: str | None = ...,
    ) -> Attachment:
        """Overload: upload (sync), returning Attachment model."""
        ...

    @overload
    def upload(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: Literal[True],
        content_type: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: upload (sync), returning raw dict."""
        ...

    @async_method  # type: ignore[operator, misc]
    async def upload(
        self,
        *,
        parent: str,
        file: BinaryIO,
        name: str,
        raw: bool = False,
        content_type: str | None = None,
    ) -> Attachment | dict[str, Any]:
        """Upload a file attachment to a task.

        Uses multipart/form-data encoding per Asana API requirements.
        Per ADR-0009: Streams file content to avoid memory issues.

        Args:
            parent: Parent task GID
            file: File-like object with read() method
            name: Filename for the attachment
            raw: If True, return raw dict instead of Attachment model
            content_type: Optional MIME type (guessed from name if not provided)

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
        self._log_operation("upload_async", parent)

        # Guess content type if not provided
        if content_type is None:
            content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"

        # Use multipart upload
        result = await self._http.post_multipart(
            f"/tasks/{parent}/attachments",
            files={"file": (name, file, content_type)},
        )
        if raw:
            return result
        return Attachment.model_validate(result)

    @overload  # type: ignore[no-overload-impl]
    async def upload_from_path_async(
        self,
        *,
        parent: str,
        path: Path | str,
        raw: Literal[False] = ...,
        name: str | None = ...,
    ) -> Attachment:
        """Overload: upload from path, returning Attachment model."""
        ...

    @overload
    async def upload_from_path_async(
        self,
        *,
        parent: str,
        path: Path | str,
        raw: Literal[True],
        name: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: upload from path, returning raw dict."""
        ...

    @overload
    def upload_from_path(
        self,
        *,
        parent: str,
        path: Path | str,
        raw: Literal[False] = ...,
        name: str | None = ...,
    ) -> Attachment:
        """Overload: upload from path (sync), returning Attachment model."""
        ...

    @overload
    def upload_from_path(
        self,
        *,
        parent: str,
        path: Path | str,
        raw: Literal[True],
        name: str | None = ...,
    ) -> dict[str, Any]:
        """Overload: upload from path (sync), returning raw dict."""
        ...

    @async_method  # type: ignore[operator, misc]
    async def upload_from_path(
        self,
        *,
        parent: str,
        path: Path | str,
        raw: bool = False,
        name: str | None = None,
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
        self._log_operation("upload_from_path_async", parent)

        path = Path(path)
        filename = name or path.name

        # C4-03: Read file content via thread pool to avoid blocking the
        # event loop on filesystem I/O.
        file_bytes = await asyncio.to_thread(path.read_bytes)

        import io

        f = io.BytesIO(file_bytes)
        if raw:
            return await self.upload_async(
                parent=parent, file=f, name=filename, raw=True
            )
        return await self.upload_async(parent=parent, file=f, name=filename, raw=False)

    # --- External Attachments ---

    @overload  # type: ignore[no-overload-impl]
    async def create_external_async(
        self,
        *,
        parent: str,
        url: str,
        name: str,
        raw: Literal[False] = ...,
    ) -> Attachment:
        """Overload: create external, returning Attachment model."""
        ...

    @overload
    async def create_external_async(
        self,
        *,
        parent: str,
        url: str,
        name: str,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: create external, returning raw dict."""
        ...

    @overload
    def create_external(
        self,
        *,
        parent: str,
        url: str,
        name: str,
        raw: Literal[False] = ...,
    ) -> Attachment:
        """Overload: create external (sync), returning Attachment model."""
        ...

    @overload
    def create_external(
        self,
        *,
        parent: str,
        url: str,
        name: str,
        raw: Literal[True],
    ) -> dict[str, Any]:
        """Overload: create external (sync), returning raw dict."""
        ...

    @async_method  # type: ignore[operator, misc]
    async def create_external(
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
        self._log_operation("create_external_async", parent)

        result = await self._http.post(
            f"/tasks/{parent}/attachments",
            json={
                "data": {
                    "resource_subtype": "external",
                    "url": url,
                    "name": name,
                }
            },
        )
        if raw:
            return result
        return Attachment.model_validate(result)

    # --- Download Operations ---

    @async_method
    async def download(
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
        self._log_operation("download_async", attachment_gid)

        # Get attachment info to get download URL
        attachment = await self.get_async(
            attachment_gid, opt_fields=["download_url", "name"]
        )

        if not attachment.download_url:
            raise AsanaError(
                f"Attachment {attachment_gid} has no download URL. "
                "It may be an external link or the download URL has expired."
            )

        # Determine if destination is a path or file object
        dest_path: Path | None = None
        file_obj: BinaryIO | None = None

        if isinstance(destination, (str, Path)):
            dest_path = Path(destination)
            # C4-02: Open file via thread pool to avoid blocking the event loop.
            file_obj = await asyncio.to_thread(open, dest_path, "wb")  # noqa: SIM115
            should_close = True
        else:
            file_obj = destination
            should_close = False

        try:
            # C4-02: Stream download with non-blocking writes via thread pool.
            async for chunk in self._http.get_stream_url(attachment.download_url):
                await asyncio.to_thread(file_obj.write, chunk)
        finally:
            if should_close and file_obj:
                await asyncio.to_thread(file_obj.close)

        return dest_path
