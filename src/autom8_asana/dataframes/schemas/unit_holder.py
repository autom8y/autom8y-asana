"""UnitHolder Schema extending BASE_SCHEMA with the nine scheduling-posture fields.

WS-B / DIAG-ws-b-offer-frame-collapse-2026-08-05: the scheduling-posture producer
cannot reach these values through the OFFER frame. The offer frame sources them
``cascade:`` off the UnitHolder ancestor, and the ancestor walk terminates at
depth 1 (``warm_ancestors_completed {total_warmed: 0, final_depth: 1}``), so hops
3 (UnitHolder) and 4 (Business) are never visited. Measured on the live frame:
``custom_cal_status`` non-null on 2/4191 rows (0.05%); the eight provider columns
on 0/4191.

This schema gives UnitHolder a frame of its OWN that carries the posture natively.

SOURCE LEVEL — ``cf:`` NOT ``cascade:``:
    R-7 of the DIAG read the live Asana ancestor chain for two independent ACTIVE
    offices (Lazar Spinal Care PC, Oak Springs Chiropractic) and found all nine
    fields present as first-class custom fields on the UnitHolder task itself
    (project 1204433992667196), e.g. ``Custom Cal Status='Enabled'``,
    ``Sked ID='745fbcfc…'``. They are therefore read ``cf:`` off this entity's OWN
    manifest — zero ancestor traversal, so the depth-1 walk defect cannot reach
    this frame.

    The names below are the EXACT live Asana display names (Title Case), verbatim
    from ``UnitHolder.CascadingFields`` (``models/business/unit.py:497-505``) and
    corroborated by the R-7 live read. The custom-field match is ``lower()/strip()``
    (``cf_utils.get_custom_field_value``), so snake_case does NOT match — this is
    the exact defect OFFER_SCHEMA 1.5.0 shipped.

IDENTITY / JOIN KEY:
    ``parent_gid`` already ships in ``BASE_COLUMNS`` (base 1.1.0) and is the join
    key onto ``business.gid`` — measured 2082/2082 = 100.0% complete on today's
    frames. It is NOT re-declared here.

    ``company_id`` (the office guid) is deliberately ABSENT: it lives on the
    Business ancestor, not on UnitHolder (R-7: UnitHolder carries
    ``Company ID=None``). The producer joins for it rather than cascading for it.

NOT A CASCADE CONSUMER:
    Every column below is ``cf:`` or base — this schema declares ZERO ``cascade:``
    columns, so ``schema.get_cascade_columns()`` is empty and UnitHolder carries no
    frame-warm ordering constraint of its own.

    ``UnitHolder.CascadingFields`` is left untouched: it remains the correct
    declaration of what UnitHolder PROVIDES to its descendants. That the cascade
    mechanism cannot currently deliver it is the ancestor-walk defect
    (CARD WS-B/1), not this schema's concern.

All columns are ``nullable=True`` — an office genuinely lacking a field reads null,
which the pure normalizer treats as absent (fail-safe to GHL by absence).
"""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

# UnitHolder columns — the nine scheduling-posture fields, read cf: off the
# UnitHolder's OWN manifest (R-7 live-verified; see module docstring).
UNIT_HOLDER_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="custom_cal_status",
        dtype="Utf8",
        nullable=True,
        source="cf:Custom Cal Status",  # UnitHolder enrollment status enum option name
        description="Enrollment status (enum option name; projects to enrolled bit)",
    ),
    ColumnDef(
        name="reviewwave_id",
        dtype="Utf8",
        nullable=True,
        source="cf:ReviewWave ID",  # CASCADE_PRIORITY[0]
        description="Scheduling source: reviewwave id",
    ),
    ColumnDef(
        name="acuity_cal_url",
        dtype="Utf8",
        nullable=True,
        source="cf:Acuity Cal URL",  # CASCADE_PRIORITY[1]
        description="Scheduling source: acuity calendar url",
    ),
    ColumnDef(
        name="calendly_url",
        dtype="Utf8",
        nullable=True,
        source="cf:Calendly URL",  # CASCADE_PRIORITY[2]
        description="Scheduling source: calendly url",
    ),
    ColumnDef(
        name="janeapp_url",
        dtype="Utf8",
        nullable=True,
        source="cf:JaneApp URL",  # CASCADE_PRIORITY[3]
        description="Scheduling source: janeapp url",
    ),
    ColumnDef(
        name="ehr_cal_url",
        dtype="Utf8",
        nullable=True,
        source="cf:EHR Cal URL",  # CASCADE_PRIORITY[4]
        description="Scheduling source: ehr calendar url",
    ),
    ColumnDef(
        name="trackstat_id",
        dtype="Utf8",
        nullable=True,
        source="cf:TrackStat ID",  # CASCADE_PRIORITY[5]
        description="Scheduling source: trackstat id",
    ),
    ColumnDef(
        name="sked_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Sked ID",  # CASCADE_PRIORITY[6]
        description="Scheduling source: sked id",
    ),
    ColumnDef(
        name="custom_ghl_id",
        dtype="Utf8",
        nullable=True,
        source="cf:Custom GHL ID",  # CASCADE_PRIORITY[7]
        description="Scheduling source: custom ghl id",
    ),
]


UNIT_HOLDER_SCHEMA = DataFrameSchema(
    name="unit_holder",
    task_type="UnitHolder",
    columns=[
        *BASE_COLUMNS,
        *[c for c in UNIT_HOLDER_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
    ],
    version="1.0.0",  # WS-B: first UnitHolder frame schema (nine cf: posture columns)
)
