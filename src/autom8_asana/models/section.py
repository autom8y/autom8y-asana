"""Section model for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
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
    resource_type: str | None = Field(
        default="section",
        description="Asana resource type name. Always 'section' for section resources.",
    )

    # Basic section fields
    name: str | None = Field(
        default=None,
        description="Display name of the section.",
    )

    # Relationships - typed with NameGid
    project: NameGid | None = Field(
        default=None,
        description="Project this section belongs to.",
    )

    # Metadata
    created_at: str | None = Field(default=None, description="Created datetime (ISO 8601)")

    # Tasks attribute for DataFrame building (populated externally)
    tasks: list[Any] | None = Field(
        default=None,
        exclude=True,
        description="Task list populated externally for DataFrame building. Excluded from serialization.",
    )
