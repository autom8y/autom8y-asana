"""Contact schema extending BASE_SCHEMA with Contact fields."""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

CONTACT_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="contact_email",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact Email",  # Resolves to custom field named "Contact Email"
        description="Contact email address",
    ),
    ColumnDef(
        name="contact_phone",
        dtype="Utf8",
        nullable=True,
        source="cf:Contact Phone",  # Resolves to "Contact Phone"
        description="Contact phone number",
    ),
    ColumnDef(
        name="full_name",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from .full_name property
        description="Full name of the contact",
    ),
    ColumnDef(
        name="name",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from .name property
        description="Name of the contact",
    ),
    ColumnDef(
        name="time_zone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Time Zone",  # Cascades from Business's ancestor
        description="Time zone of the contact",
    ),
    ColumnDef(
        name="position",
        dtype="Utf8",
        nullable=True,
        source="cf:Position",  # Enum field
        description="Office location (derived)",
    ),
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Office Phone",  # Cascades from Business ancestor
        description="Office phone number (cascades from Business)",
    ),
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cascade:Vertical",  # Cascades from Unit or Business ancestor
        description="Business vertical",
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
        source="cf:Dashboard UUID",  # Text field
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
    version="1.1.0",  # Bumped version for schema change
)
