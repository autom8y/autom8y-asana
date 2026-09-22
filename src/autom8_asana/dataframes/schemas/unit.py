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
        # Utf8 (honest enum string), NOT Decimal. Empirically proven against the
        # live unit project 1201081073731555 stored task dicts: Discount is an
        # Asana ENUM (resource_subtype="enum", enum_value.name="0%",
        # display_value="0%") -- never a number cf. The model declares it
        # EnumField() (models/business/unit.py), which is authoritative for
        # runtime shape. The prior Decimal dtype was a model/schema contract
        # mismatch: the resolver coercer dropped enum "0%" to None (the builder
        # coercer's %-strip masked it on one path only). Carrying the honest enum
        # string preserves values like "10%"/"None" without lossy numeric coercion.
        dtype="Utf8",
        nullable=True,
        source="cf:Discount",  # Enum field (percentage label, e.g. "0%", "10%")
        description="Discount percentage label (enum string, e.g. '0%', '10%')",
    ),
    ColumnDef(
        name="office",
        dtype="Utf8",
        nullable=True,
        source="cascade:Business Name",  # Per TDD-WS3: Cascades from Business ancestor's task name
        description="Office name (cascades from Business ancestor name via source_field)",
    ),
    # CASCADE CONTRACT: sourced from Business.office_phone (warm_priority=1).
    # Resolution key column -- null cascade = silent NOT_FOUND (FIND-005).
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
        name="specialty",
        dtype="Utf8",
        nullable=True,
        source="cf:Specialty",  # Text field
        description="Business specialty",
    ),
]


UNIT_SCHEMA = DataFrameSchema(
    name="unit",
    task_type="Unit",
    columns=[
        *BASE_COLUMNS,
        *[c for c in UNIT_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
    ],
    version="1.5.0",  # parent_gid column added for hierarchy reconstruction on resume
)
