"""Section model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
"""

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
