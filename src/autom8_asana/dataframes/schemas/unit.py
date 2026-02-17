"""Unit schema extending BASE_SCHEMA with Unit fields."""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

UNIT_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="mrr",
        dtype="Decimal",
        nullable=True,
        source="cf:MRR",  # Resolves to custom field named "MRR"
        description="Monthly recurring revenue",
    ),
    ColumnDef(
        name="weekly_ad_spend",
        dtype="Decimal",
        nullable=True,
        source="cf:Weekly Ad Spend",  # Resolves to "Weekly Ad Spend"
        description="Weekly advertising spend",
    ),
    ColumnDef(
        name="products",
        dtype="List[Utf8]",
        nullable=True,
        source="cf:Products",  # Multi-enum field
        description="Product list",
    ),
    ColumnDef(
        name="languages",
        dtype="List[Utf8]",
        nullable=True,
        source="cf:Languages",  # Multi-enum field
        description="Supported languages",
    ),
    ColumnDef(
        name="discount",
        dtype="Decimal",
        nullable=True,
        source="cf:Discount",  # Number field (percentage)
        description="Discount percentage",
    ),
    ColumnDef(
        name="office",
        dtype="Utf8",
        nullable=True,
        source="cascade:Business Name",  # Per TDD-WS3: Cascades from Business ancestor's task name
        description="Office name (cascades from Business ancestor name via source_field)",
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
        source="cf:Vertical",  # Custom field on task (vertical waterfalls down, no cascade)
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
        name="max_pipeline_stage",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from UnitHolder
        description="Maximum pipeline stage reached (derived)",
    ),
]


UNIT_SCHEMA = DataFrameSchema(
    name="unit",
    task_type="Unit",
    columns=[
        *BASE_COLUMNS,
        *[c for c in UNIT_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
    ],
    version="1.4.0",  # Per TDD-WS3: office source changed to cascade:Business Name
)
