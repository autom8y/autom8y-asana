"""Business schema extending BASE_SCHEMA with Business fields."""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

BUSINESS_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="company_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Company ID",  # Text field
        description="Company identifier",
    ),
    ColumnDef(
        name="name",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from .name property
        description="Office name (derived)",
    ),
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cf:Office Phone",  # Text field
        description="Office phone number (cascades from Business)",
    ),
    ColumnDef(
        name="stripe_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Stripe ID",  # Text field
        description="Stripe customer identifier",
    ),
    ColumnDef(
        name="booking_type",
        dtype="Utf8",
        nullable=True,
        source="cf:Booking Type",  # Enum field
        description="Booking type",
    ),
    ColumnDef(
        name="facebook_page_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Facebook Page ID",  # Text field
        description="Facebook page identifier",
    ),
]


BUSINESS_SCHEMA = DataFrameSchema(
    name="business",
    task_type="business",
    columns=[
        *BASE_COLUMNS,
        *[c for c in BUSINESS_COLUMNS if c not in BASE_COLUMNS],
    ],
    version="1.1.0",  # Bump to invalidate stale caches missing warm_hierarchy fix
)
