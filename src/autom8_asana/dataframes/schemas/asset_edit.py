"""AssetEdit Schema extending BASE_SCHEMA with Process and AssetEdit fields.

Per TDD-resolution-hardening: AssetEdit schema with 21 fields total:
- 10 Process fields (common to all process types, includes office_phone cascade)
- 11 AssetEdit-specific fields

Field sources derived from:
- Process.Fields class (inherited by AssetEdit)
- AssetEdit.Fields class
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

# Process fields (10 fields) - inherited by AssetEdit from Process
PROCESS_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="started_at",
        dtype="Utf8",
        nullable=True,
        source="cf:Started At",
        description="Process start timestamp",
    ),
    ColumnDef(
        name="process_completed_at",
        dtype="Utf8",
        nullable=True,
        source="cf:Process Completed At",
        description="Process completion timestamp",
    ),
    ColumnDef(
        name="process_notes",
        dtype="Utf8",
        nullable=True,
        source="cf:Process Notes",
        description="Process notes",
    ),
    ColumnDef(
        name="status",
        dtype="Utf8",
        nullable=True,
        source="cf:Status",
        description="Process status (enum)",
    ),
    ColumnDef(
        name="priority",
        dtype="Utf8",
        nullable=True,
        source="cf:Priority",
        description="Process priority (enum)",
    ),
    ColumnDef(
        name="process_due_date",
        dtype="Utf8",
        nullable=True,
        source="cf:Due Date",
        description="Process due date",
    ),
    ColumnDef(
        name="assigned_to",
        dtype="Utf8",
        nullable=True,
        source="cf:Assigned To",
        description="Assigned user (people field)",
    ),
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cascade:Vertical",
        description="Business vertical (cascades from Unit or Business)",
    ),
    ColumnDef(
        name="office_phone",
        dtype="Utf8",
        nullable=True,
        source="cascade:Office Phone",
        description="Office phone number (cascades from Business)",
    ),
    ColumnDef(
        name="specialty",
        dtype="List[Utf8]",
        nullable=True,
        source="cf:Specialty",
        description="Specialty types (multi-enum from Process)",
    ),
]


# AssetEdit-specific fields (11 fields) - from AssetEdit.Fields class
ASSET_EDIT_SPECIFIC_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="asset_approval",
        dtype="Utf8",
        nullable=True,
        source="cf:Asset Approval",
        description="Asset approval status (enum)",
    ),
    ColumnDef(
        name="asset_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Asset ID",
        description="Asset identifier (text)",
    ),
    ColumnDef(
        name="editor",
        dtype="Utf8",
        nullable=True,
        source="cf:Editor",
        description="Editor users (people field)",
    ),
    ColumnDef(
        name="reviewer",
        dtype="Utf8",
        nullable=True,
        source="cf:Reviewer",
        description="Reviewer users (people field)",
    ),
    ColumnDef(
        name="offer_id",
        dtype="Int64",
        nullable=True,
        source="cf:Offer ID",
        description="Offer identifier (integer, primary lookup key)",
    ),
    ColumnDef(
        name="raw_assets",
        dtype="Utf8",
        nullable=True,
        source="cf:Raw Assets",
        description="Raw assets link/text",
    ),
    ColumnDef(
        name="review_all_ads",
        dtype="Boolean",
        nullable=True,
        source="cf:Review All Ads",
        description="Review all ads flag (Yes/No enum mapped to bool)",
    ),
    ColumnDef(
        name="score",
        dtype="Float64",
        nullable=True,
        source="cf:Score",
        description="Score value (number)",
    ),
    ColumnDef(
        name="asset_edit_specialty",
        dtype="List[Utf8]",
        nullable=True,
        source="cf:Specialty",
        description="AssetEdit specialty types (multi-enum, distinct from Process.specialty)",
    ),
    ColumnDef(
        name="template_id",
        dtype="Int64",
        nullable=True,
        source="cf:Template ID",
        description="Template identifier (integer)",
    ),
    ColumnDef(
        name="videos_paid",
        dtype="Int64",
        nullable=True,
        source="cf:Videos Paid",
        description="Number of videos paid (integer)",
    ),
]


# Combined AssetEdit columns (21 fields total)
ASSET_EDIT_COLUMNS: list[ColumnDef] = [
    *PROCESS_COLUMNS,
    *ASSET_EDIT_SPECIFIC_COLUMNS,
]


ASSET_EDIT_SCHEMA = DataFrameSchema(
    name="asset_edit",
    task_type="AssetEdit",
    columns=[
        *BASE_COLUMNS,
        *[
            c
            for c in ASSET_EDIT_COLUMNS
            if c.name not in {col.name for col in BASE_COLUMNS}
        ],
    ],
    version="1.2.0",  # Bump to force rebuild with generalized cascade resolution fix
)
