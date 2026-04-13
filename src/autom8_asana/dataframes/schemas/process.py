"""Process Schema extending BASE_SCHEMA with Process pipeline fields.

Per ADR-pipeline-stage-aggregation: Process entities span 9 separate
pipeline projects. Each pipeline project shares this schema. The
pipeline_type discriminator column is derived (set by the aggregator
in Phase 2, not by the extractor).
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

PROCESS_COLUMNS: list[ColumnDef] = [
    # CASCADE CONTRACT: sourced from Business.office_phone (warm_priority=1).
    # Resolution key column -- null cascade = silent NOT_FOUND (FIND-005).
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Office Phone",
        description="Office phone number (cascades from Business)",
    ),
    # CASCADE CONTRACT: sourced from Unit.vertical or Business.vertical (warm_priority=2/1).
    # Resolution key column -- null cascade = silent NOT_FOUND (FIND-005).
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cascade:Vertical",
        description="Business vertical (cascades from Unit or Business ancestor)",
    ),
    # Derived column: set by Phase 2 pipeline_stage_aggregator, not by the extractor.
    # Source is None because the value is not extracted from Asana task data.
    ColumnDef(
        name="pipeline_type",
        dtype="Utf8",
        nullable=True,
        source=None,
        description="Pipeline type discriminator (derived, set by aggregator)",
    ),
]

PROCESS_SCHEMA = DataFrameSchema(
    name="process",
    task_type="Process",
    columns=[
        *BASE_COLUMNS,
        *[c for c in PROCESS_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
    ],
    version="1.0.0",
)
