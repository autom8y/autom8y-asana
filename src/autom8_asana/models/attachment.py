"""Attachment model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per ADR-0009: Attachment upload/download handled via multipart in AttachmentsClient.
"""

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
    download_url: str | None = Field(
        default=None, description="URL to download the file"
    )
    permanent_url: str | None = Field(
        default=None, description="Permanent URL for the file"
    )

    # File metadata
    size: int | None = Field(default=None, description="File size in bytes")

    # Relationships
    parent: NameGid | None = Field(default=None, description="Parent task")
    created_by: NameGid | None = None

    # Timestamps
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )
