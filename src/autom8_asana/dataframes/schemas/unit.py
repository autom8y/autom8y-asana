"""Unit schema with 23 columns (12 base + 11 Unit-specific).

Per FR-SUBCLASS-001: UNIT_SCHEMA extends BASE_SCHEMA with Unit fields.
Per TDD-0009.1: Custom fields use cf: prefix for dynamic resolution.
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS


# Unit-specific column definitions (11 columns) - FR-SUBCLASS-001
# Per TDD-0009.1: source="cf:Name" enables dynamic resolution by field name
UNIT_COLUMNS: list[ColumnDef] = [
    # Direct custom fields (5) - resolved by name
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
    # Derived fields (6) - no source, custom extractor logic
    ColumnDef(
        name="office",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from business.office_phone lookup
        description="Office location (derived)",
    ),
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from business
        description="Office phone number (derived)",
    ),
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cf:Vertical",  # Enum field
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
    columns=[*BASE_COLUMNS, *UNIT_COLUMNS],  # 12 + 11 = 23 columns
    version="1.0.0",
)
