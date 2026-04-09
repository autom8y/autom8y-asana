"""Base model classes for Asana API resources.

Per ADR-0005: Pydantic v2 with extra="ignore" for forward compatibility.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AsanaResource(BaseModel):
    """Base class for all Asana API resources.

    Configuration:
        - extra="ignore": Unknown fields from API responses are silently ignored.
          This ensures forward compatibility when Asana adds new fields.
        - populate_by_name=True: Allows both Python field names and API aliases.
        - str_strip_whitespace=True: Normalizes string inputs.

    All Asana resources have a GID (globally unique identifier) and typically
    have a resource_type field identifying the type of resource.
    """

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    gid: str = Field(
        pattern=r"^\d{1,64}$",
        description="Globally unique identifier for this Asana resource. A numeric string (1-64 digits).",
    )
    resource_type: str | None = Field(
        default=None,
        description="Asana resource type name (e.g., 'task', 'project', 'section').",
    )
