"""AssetEditHolder Schema extending BASE_SCHEMA with office_phone cascading field.

Per TDD-resolution-hardening: AssetEditHolder is a simple holder schema
with office_phone as the primary lookup key (cascades from Business).
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

# AssetEditHolder columns - office_phone cascading from Business
ASSET_EDIT_HOLDER_COLUMNS: list[ColumnDef] = [
    # CASCADE CONTRACT: sourced from Business.office_phone (warm_priority=1).
    # Resolution key column -- null cascade = silent NOT_FOUND (FIND-005).
    # Sole key column (100% cascade dependency): if cascade fails, this
    # entity is entirely unlookable.
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Office Phone",
        description="Office phone number (cascades from Business, primary lookup key)",
    ),
]


ASSET_EDIT_HOLDER_SCHEMA = DataFrameSchema(
    name="asset_edit_holder",
    task_type="AssetEditHolder",
    columns=[
        *BASE_COLUMNS,
        *[
            c
            for c in ASSET_EDIT_HOLDER_COLUMNS
            if c.name not in {col.name for col in BASE_COLUMNS}
        ],
    ],
    version="1.2.0",  # parent_gid column added for hierarchy reconstruction on resume
)
