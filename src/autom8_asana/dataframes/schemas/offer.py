"""Offer Schema extending BASE_SCHEMA with Offer fields."""

from __future__ import annotations

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.schemas.base import BASE_COLUMNS

OFFER_COLUMNS: list[ColumnDef] = [
    ColumnDef(
        name="office",
        dtype="Utf8",
        nullable=True,
        source="cascade:Business Name",  # Cascades from Business ancestor Task.name
        description="Office name (cascades from Business)",
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
    # CASCADE CONTRACT: sourced from Unit.vertical or Business.vertical (warm_priority=2/1).
    # Resolution key column -- null cascade = silent NOT_FOUND (FIND-005).
    ColumnDef(
        name="vertical",
        dtype="Utf8",
        nullable=True,
        source="cascade:Vertical",  # Cascades from Unit or Business ancestor
        description="Business vertical",
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
    # -----------------------------------------------------------------------
    # Scheduling-posture projection columns (schema 1.6.0 -- warm-projection,
    # frame-first extraction; FORK-1 A∘D).
    #
    # The scheduling-stratum whole-snapshot push (lambda_handlers/
    # scheduling_stratum_snapshot.py) reconceived as a PURE Polars read over the
    # ALREADY-WARMED offer frame: the office identity + the office-global
    # enrollment status + the eight CASCADE_PRIORITY provider source fields are
    # projected HERE, at bulk frame-warm time, so the snapshot Lambda does
    # sub-second column reads with ZERO per-office Asana calls (the measured
    # 900s-Lambda-ceiling blocker is dissolved -- see TDD-DELTA 2026-07-02).
    #
    # All columns are nullable=True (purely ADDITIVE -- an office genuinely
    # lacking a field reads null, which the pure normalizer treats as absent).
    #
    # SOURCE LEVEL (1.6.0 CORRECTION -- was the degenerate 1.5.0 defect):
    # custom_cal_status + the eight provider fields do NOT live on the Offer task.
    # They are custom fields on the office-level UNIT_HOLDER ancestor (the monolith
    # ``UnitHolder`` -- ``apis/.../custom_field/models/enum/binary/custom_cal_status``
    # "must be called from a UnitHolder object"; verified live: the Offer manifest
    # carries none of them, the UnitHolder "…Business Units 🔎" task carries them
    # POPULATED, e.g. Custom Cal Status='Enabled'). 1.5.0 sourced them ``cf:`` off
    # the Offer's OWN manifest with snake_case names -- which matched NOTHING (both
    # WRONG LEVEL and WRONG NAME), so every projected row resolved null and the push
    # was degenerate (all enrolled=true / stratum='inactive'). They are therefore
    # sourced ``cascade:`` (ancestor traversal, same mechanism as company_id/
    # office_phone) keyed by the REAL Asana display names (Title Case). The cascade
    # resolver traverses Offer -> OfferHolder -> Unit -> UnitHolder and reads the
    # value off the UNIT_HOLDER (registered UnitHolder.CascadingFields, target_types
    # None). The name match is lower()/strip() (cf_utils.get_custom_field_value), so
    # the display name MUST be exact modulo case/outer-whitespace -- snake names do
    # NOT match.
    #
    # company_id is the office guid, cascaded from the Business ancestor (registered
    # Business.CascadingFields.COMPANY_ID); it already resolved correctly in 1.5.0.
    ColumnDef(
        name="company_id",
        dtype="Utf8",
        nullable=True,
        source="cascade:Company ID",  # Cascades from Business ancestor (office guid)
        description="Office guid (cascades from Business Company ID)",
    ),
    ColumnDef(
        name="custom_cal_status",
        dtype="Utf8",
        nullable=True,
        source="cascade:Custom Cal Status",  # UnitHolder enrollment status enum option name
        description="Enrollment status (enum option name; projects to enrolled bit)",
    ),
    ColumnDef(
        name="reviewwave_id",
        dtype="Utf8",
        nullable=True,
        source="cascade:ReviewWave ID",  # CASCADE_PRIORITY[0] (UnitHolder)
        description="Scheduling source: reviewwave id",
    ),
    ColumnDef(
        name="acuity_cal_url",
        dtype="Utf8",
        nullable=True,
        source="cascade:Acuity Cal URL",  # CASCADE_PRIORITY[1] (UnitHolder)
        description="Scheduling source: acuity calendar url",
    ),
    ColumnDef(
        name="calendly_url",
        dtype="Utf8",
        nullable=True,
        source="cascade:Calendly URL",  # CASCADE_PRIORITY[2] (UnitHolder)
        description="Scheduling source: calendly url",
    ),
    ColumnDef(
        name="janeapp_url",
        dtype="Utf8",
        nullable=True,
        source="cascade:JaneApp URL",  # CASCADE_PRIORITY[3] (UnitHolder)
        description="Scheduling source: janeapp url",
    ),
    ColumnDef(
        name="ehr_cal_url",
        dtype="Utf8",
        nullable=True,
        source="cascade:EHR Cal URL",  # CASCADE_PRIORITY[4] (UnitHolder)
        description="Scheduling source: ehr calendar url",
    ),
    ColumnDef(
        name="trackstat_id",
        dtype="Utf8",
        nullable=True,
        source="cascade:TrackStat ID",  # CASCADE_PRIORITY[5] (UnitHolder)
        description="Scheduling source: trackstat id",
    ),
    ColumnDef(
        name="sked_id",
        dtype="Utf8",
        nullable=True,
        source="cascade:Sked ID",  # CASCADE_PRIORITY[6] (UnitHolder)
        description="Scheduling source: sked id",
    ),
    ColumnDef(
        name="custom_ghl_id",
        dtype="Utf8",
        nullable=True,
        source="cascade:Custom GHL ID",  # CASCADE_PRIORITY[7] (UnitHolder, cascade terminal)
        description="Scheduling source: GHL calendar id (cascade terminal)",
    ),
]

OFFER_SCHEMA = DataFrameSchema(
    name="offer",
    task_type="Offer",
    columns=[
        *BASE_COLUMNS,
        *[c for c in OFFER_COLUMNS if c.name not in {col.name for col in BASE_COLUMNS}],
    ],
    version="1.6.0",  # re-source scheduling-posture columns cascade:UnitHolder (fix degenerate 1.5.0 cf:Offer)
)
