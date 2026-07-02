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
    # Scheduling-posture projection columns (schema 1.5.0 -- warm-projection,
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
    # The eight provider fields + custom_cal_status are read off the Offer task's
    # OWN custom-field manifest (cf:; NameNormalizer-robust by-name match, so the
    # snake_case logical names below match whatever the live Asana display string
    # is). company_id is the office guid, cascaded from the Business ancestor
    # (same parent-chain mechanism as `office`/`office_phone`; registered
    # CascadingFieldDef Business.CascadingFields.COMPANY_ID, target_types=None).
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
        source="cf:custom_cal_status",  # Office-global enrollment status enum option name
        description="Enrollment status (enum option name; projects to enrolled bit)",
    ),
    ColumnDef(
        name="reviewwave_id",
        dtype="Utf8",
        nullable=True,
        source="cf:reviewwave_id",  # CASCADE_PRIORITY[0]
        description="Scheduling source: reviewwave id",
    ),
    ColumnDef(
        name="acuity_cal_url",
        dtype="Utf8",
        nullable=True,
        source="cf:acuity_cal_url",  # CASCADE_PRIORITY[1]
        description="Scheduling source: acuity calendar url",
    ),
    ColumnDef(
        name="calendly_url",
        dtype="Utf8",
        nullable=True,
        source="cf:calendly_url",  # CASCADE_PRIORITY[2]
        description="Scheduling source: calendly url",
    ),
    ColumnDef(
        name="janeapp_url",
        dtype="Utf8",
        nullable=True,
        source="cf:janeapp_url",  # CASCADE_PRIORITY[3]
        description="Scheduling source: janeapp url",
    ),
    ColumnDef(
        name="ehr_cal_url",
        dtype="Utf8",
        nullable=True,
        source="cf:ehr_cal_url",  # CASCADE_PRIORITY[4]
        description="Scheduling source: ehr calendar url",
    ),
    ColumnDef(
        name="trackstat_id",
        dtype="Utf8",
        nullable=True,
        source="cf:trackstat_id",  # CASCADE_PRIORITY[5]
        description="Scheduling source: trackstat id",
    ),
    ColumnDef(
        name="sked_id",
        dtype="Utf8",
        nullable=True,
        source="cf:sked_id",  # CASCADE_PRIORITY[6]
        description="Scheduling source: sked id",
    ),
    ColumnDef(
        name="custom_ghl_id",
        dtype="Utf8",
        nullable=True,
        source="cf:custom_ghl_id",  # CASCADE_PRIORITY[7]
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
    version="1.5.0",  # scheduling-posture projection columns (frame-first extraction)
)
