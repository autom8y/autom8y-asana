"""Contact schema with 21 columns (12 base + 9 Contact-specific).

Per FR-SUBCLASS-002: CONTACT_SCHEMA extends BASE_SCHEMA with Contact fields.
Per TDD-0009.1: Custom fields use cf: prefix for dynamic resolution.
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS


# Contact-specific column definitions (9 columns) - FR-SUBCLASS-002
# Per TDD-0009.1: source="cf:Name" enables dynamic resolution by field name
CONTACT_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="full_name",
        dtype="Utf8",
        nullable=True,
        source="cf:Full Name",  # Resolves to custom field "Full Name"
        description="Contact full name",
    ),
    ColumnDef(
        name="nickname",
        dtype="Utf8",
        nullable=True,
        source="cf:Nickname",  # Resolves to custom field "Nickname"
        description="Contact nickname",
    ),
    ColumnDef(
        name="contact_phone",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact Phone",  # Resolves to "Contact Phone"
        description="Contact phone number",
    ),
    ColumnDef(
        name="contact_email",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact Email",  # Resolves to "Contact Email"
        description="Contact email address",
    ),
    ColumnDef(
        name="position",
        dtype="Utf8",
        nullable=True,
        source="cf:Position",  # Resolves to custom field "Position"
        description="Job position/title",
    ),
    ColumnDef(
        name="employee_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Employee ID",  # Resolves to "Employee ID"
        description="Employee identifier",
    ),
    ColumnDef(
        name="contact_url",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact URL",  # Resolves to "Contact URL"
        description="Contact URL/website",
    ),
    ColumnDef(
        name="time_zone",
        dtype="Utf8",
        nullable=True,
        source="cf:Time Zone",  # Resolves to "Time Zone"
        description="Contact time zone",
    ),
    ColumnDef(
        name="city",
        dtype="Utf8",
        nullable=True,
        source="cf:City",  # Resolves to custom field "City"
        description="Contact city",
    ),
]


CONTACT_SCHEMA = DataFrameSchema(
    name="contact",
    task_type="Contact",
    columns=[*BASE_COLUMNS, *CONTACT_COLUMNS],  # 12 + 9 = 21 columns
    version="1.0.0",
)
