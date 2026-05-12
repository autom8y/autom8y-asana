"""Section Schema for Asana section-level queries.

Sprint 1 — asana-clean-break-leaf initiative.

Shortcut S-07 invoked: minimal schema (3 columns beyond BASE_SCHEMA) per
spike §5.8 S-07 (acceptable for Sprint 1). Full column-parity (30+ columns)
is PG-02, deferred to Sprint 2.

This schema enables POST /v1/query/section/rows to return non-empty rows
with the attestation field present.
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

SECTION_EXTRA_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="status",
        dtype="Utf8",
        nullable=True,
        source=None,  # Derived from custom fields; S-07: minimal extraction
        description="Section status label",
    ),
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Office Phone",
        description="Office phone number (cascades from Business); Sprint 2 PG-02 will add full cascade",
    ),
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cascade:Vertical",
        description="Business vertical; Sprint 2 PG-02 will add full parity",
    ),
]

SECTION_SCHEMA = DataFrameSchema(
    name="section",
    task_type="Section",
    columns=[
        *BASE_COLUMNS,
        *[c for c in SECTION_EXTRA_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
    ],
    version="1.0.0",
)
