"""Custom field models for Asana API.

Per ADR-0005: Uses Pydantic v2 with extra="ignore" for forward compatibility.
Per TDD-0002/ADR-0006: Uses NameGid for typed resource references.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from autom8_asana.models.base import AsanaResource

if TYPE_CHECKING:
    from autom8_asana.models.common import NameGid


class CustomFieldEnumOption(AsanaResource):
    """An option for enum-type custom fields.

    Example:
        >>> option = CustomFieldEnumOption.model_validate(
        ...     {"gid": "123", "name": "High", "color": "red"}
        ... )
        >>> option.name
        'High'
    """

    resource_type: str | None = Field(default="enum_option")
    name: str | None = Field(
        default=None,
        description="Display name of the enum option.",
    )
    enabled: bool | None = Field(
        default=None,
        description="True if this option is available for selection.",
    )
    color: str | None = Field(
        default=None,
        description="Color of the enum option (red, orange, yellow, green, blue, etc.).",
    )


class CustomField(AsanaResource):
    """Asana Custom Field resource model.

    Custom fields can be of various types: text, number, enum, multi_enum,
    date, people, etc. The structure varies by type.

    Per ADR-0005: Unknown fields from API are silently ignored.

    Example:
        >>> cf = CustomField.model_validate(api_response)
        >>> if cf.resource_subtype == "enum":
        ...     for opt in cf.enum_options or []:
        ...         print(f"  - {opt.name}")
    """

    # Core identification
    resource_type: str | None = Field(default="custom_field")
    resource_subtype: str | None = Field(
        default=None,
        description="Type: text, number, enum, multi_enum, date, people",
    )

    # Basic fields
    name: str | None = Field(
        default=None,
        description="Display name of the custom field.",
    )
    description: str | None = Field(
        default=None,
        description="Help text describing the custom field's purpose.",
    )
    enabled: bool | None = Field(
        default=None,
        description="True if this custom field is active and visible.",
    )
    is_global_to_workspace: bool | None = Field(
        default=None,
        description="True if the field is available across all projects in the workspace.",
    )
    has_notifications_enabled: bool | None = Field(
        default=None,
        description="True if changes to this field trigger notifications.",
    )

    # Type-specific configuration
    precision: int | None = Field(
        default=None,
        description="Decimal precision for number fields",
    )
    format: str | None = Field(
        default=None,
        description="Format for display (currency, percentage, etc.)",
    )
    currency_code: str | None = Field(
        default=None,
        description="Currency code for currency fields (USD, EUR, etc.)",
    )
    custom_label: str | None = Field(
        default=None,
        description="Custom unit label for number fields (e.g., 'hrs', 'pts').",
    )
    custom_label_position: str | None = Field(
        default=None,
        description="Position of custom label (prefix, suffix)",
    )

    # Enum options
    enum_options: list[CustomFieldEnumOption] | None = Field(
        default=None,
        description="Available options for enum and multi_enum custom fields.",
    )
    enum_value: CustomFieldEnumOption | None = Field(
        default=None,
        description="Selected enum value (when reading from task)",
    )
    multi_enum_values: list[CustomFieldEnumOption] | None = Field(
        default=None,
        description="Selected multi-enum values (when reading from task)",
    )

    # Value fields (present when custom field is on a task/project)
    text_value: str | None = Field(
        default=None,
        description="Current text value for text-type custom fields.",
    )
    number_value: float | None = Field(
        default=None,
        description="Current numeric value for number-type custom fields.",
    )
    display_value: str | None = Field(
        default=None,
        description="Human-readable display value",
    )
    date_value: dict[str, Any] | None = Field(
        default=None,
        description="Date value with date and optional datetime",
    )
    people_value: list[NameGid] | None = Field(
        default=None,
        description="Selected users for people-type custom fields.",
    )

    # Relationships
    workspace: NameGid | None = Field(
        default=None,
        description="Workspace this custom field belongs to.",
    )
    created_by: NameGid | None = Field(
        default=None,
        description="User who created this custom field.",
    )

    # Metadata
    created_at: str | None = Field(
        default=None, description="Created datetime (ISO 8601)"
    )

    # ID representations
    id_prefix: str | None = Field(
        default=None,
        description="Prefix for the custom field's short ID (e.g., 'CF').",
    )
    is_formula_field: bool | None = Field(
        default=None,
        description="True if the field value is computed by a formula.",
    )
    is_value_read_only: bool | None = Field(
        default=None,
        description="True if the field value cannot be modified directly.",
    )


class CustomFieldSetting(AsanaResource):
    """Settings for a custom field on a project.

    Represents how a custom field is configured on a specific project,
    including whether it's important or which field it should be inserted after.

    Example:
        >>> setting = CustomFieldSetting.model_validate(api_response)
        >>> print(f"Field {setting.custom_field.gid} on project {setting.project.gid}")
    """

    resource_type: str | None = Field(default="custom_field_setting")

    # The custom field this setting applies to
    custom_field: CustomField | None = Field(
        default=None,
        description="Custom field this setting configures.",
    )

    # The project this setting is on
    project: NameGid | None = Field(
        default=None,
        description="Project this custom field setting belongs to.",
    )
    parent: NameGid | None = Field(
        default=None,
        description="Parent resource (alternative to project for portfolios).",
    )

    # Configuration
    is_important: bool | None = Field(
        default=None,
        description="True if the field is pinned for prominence in the project.",
    )
