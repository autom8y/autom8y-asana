"""Contact schema extending BASE_SCHEMA with Contact fields."""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

CONTACT_COLUMNS: list[ColumnDef] = [
    # Core contact fields (9 for test compatibility)
    ColumnDef(
        name="full_name",
        dtype="Utf8",
        nullable=True,
        source="cf:Full Name",
        description="Full name of the contact",
    ),
    ColumnDef(
        name="nickname",
        dtype="Utf8",
        nullable=True,
        source="cf:Nickname",
        description="Nickname of the contact",
    ),
    ColumnDef(
        name="contact_phone",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact Phone",
        description="Contact phone number",
    ),
    ColumnDef(
        name="contact_email",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact Email",
        description="Contact email address",
    ),
    ColumnDef(
        name="position",
        dtype="Utf8",
        nullable=True,
        source="cf:Position",
        description="Position/role of the contact",
    ),
    ColumnDef(
        name="employee_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Employee ID",
        description="Employee identifier",
    ),
    ColumnDef(
        name="contact_url",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact URL",
        description="Contact URL (LinkedIn, etc.)",
    ),
    ColumnDef(
        name="time_zone",
        dtype="Utf8",
        nullable=True,
        source="cf:Time Zone",
        description="Time zone of the contact",
    ),
    ColumnDef(
        name="city",
        dtype="Utf8",
        nullable=True,
        source="cf:City",
        description="City of the contact",
    ),
    # Cascade and derived fields (4 additional)
    # CASCADE CONTRACT: sourced from Business.office_phone (warm_priority=1).
    # Resolution key column -- null cascade = silent NOT_FOUND (FIND-005).
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Office Phone",
        description="Office phone number (cascades from Business)",
    ),
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cascade:Vertical",
        description="Business vertical (cascades from Unit or Business)",
    ),
    ColumnDef(
        name="vertical_id",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from Vertical model
        description="Vertical identifier (derived)",
    ),
    ColumnDef(
        name="dashboard_uuid",
        dtype="Utf8",
        nullable=True,
        source="cf:Dashboard UUID",
        description="Dashboard UUID",
    ),
]

CONTACT_SCHEMA = DataFrameSchema(
    name="contact",
    task_type="Contact",
    columns=[
        *BASE_COLUMNS,
        *[
            c
            for c in CONTACT_COLUMNS
            if c.name not in {col.name for col in BASE_COLUMNS}
        ],
    ],
    version="1.4.0",  # parent_gid column added for hierarchy reconstruction on resume
)
