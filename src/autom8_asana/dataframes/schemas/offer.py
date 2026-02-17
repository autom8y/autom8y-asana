"""Offer Schema extending BASE_SCHEMA with Offer fields."""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

OFFER_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="office",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from business.office_phone lookup
        description="Office name (derived)",
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
        name="specialty",
        dtype="Utf8",
        nullable=True,
        source="cf:Specialty",  # Text field
        description="Business specialty",
    ),
    ColumnDef(
        name="offer_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Offer ID",  # Resolves to "Offer ID"
        description="Offer identifier",
    ),
    ColumnDef(
        name="platforms",
        dtype="List[Utf8]",
        nullable=True,
        source="cf:Platforms",  # Multi-enum field
        description="Platform list",
    ),
    ColumnDef(
        name="language",
        dtype="Utf8",
        nullable=True,
        source="cf:Language",  # Enum field
        description="Offer language",
    ),
    ColumnDef(
        name="name",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from .name property
        description="Name of the offer",
    ),
    ColumnDef(
        name="cost",
        dtype="Utf8",
        nullable=True,
        source="cf:Cost",  # Number field
        description="Cost of the offer",
    ),
    ColumnDef(
        name="mrr",
        dtype="Decimal",
        nullable=True,
        source="cascade:MRR",  # Cascades from Offer's ancestor Unit
        description="Monthly Recurring Revenue (cascades from Unit)",
    ),
    ColumnDef(
        name="weekly_ad_spend",
        dtype="Decimal",
        nullable=True,
        source="cascade:Weekly Ad Spend",  # Cascades from Offer's ancestor Unit
        description="Weekly advertising spend",
    ),
]

OFFER_SCHEMA = DataFrameSchema(
    name="offer",
    task_type="Offer",
    columns=[
        *BASE_COLUMNS,
        *[c for c in OFFER_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
    ],
    version="1.2.0",  # Bump to force rebuild with generalized cascade resolution fix
)
