"""Pydantic models for type-safe DataFrame row representation.

Per FR-MODEL-020 through FR-MODEL-025: TaskRow with typed fields,
frozen for immutability, and to_dict() for Polars compatibility.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskRow(BaseModel):
    """Base row model for all task types (FR-MODEL-020-025).

    Per TDD-0009: Pydantic model with typed fields matching schema,
    validates on construction, immutable after creation.

    Attributes:
        gid: Task identifier (non-nullable)
        name: Task name (non-nullable)
        type: Task type discriminator (non-nullable)
        date: Primary date field
        created: Task creation timestamp (non-nullable)
        due_on: Due date
        is_completed: Completion status (non-nullable)
        completed_at: Completion timestamp
        url: Asana task URL (non-nullable)
        last_modified: Last modification timestamp (non-nullable)
        section: Section name
        tags: List of tag names (non-nullable, defaults empty)
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # Base fields (13) - FR-MODEL-021 + TDD-CASCADE-RESUME-FIX
    gid: str
    name: str
    type: str
    date: dt.date | None = None
    created: dt.datetime
    due_on: dt.date | None = None
    is_completed: bool
    completed_at: dt.datetime | None = None
    url: str
    last_modified: dt.datetime
    section: str | None = None
    tags: list[str] = Field(default_factory=list)
    parent_gid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for Polars compatibility (FR-MODEL-024).

        Returns:
            Dict with all fields, suitable for pl.DataFrame construction.
            Converts Decimal to float for Polars compatibility.
        """
        data = self.model_dump()
        # Convert any Decimal values to float for Polars
        return self._convert_decimals(data)

    @staticmethod
    def _convert_decimals(data: dict[str, Any]) -> dict[str, Any]:
        """Recursively convert Decimal values to float."""
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, Decimal):
                result[key] = float(value)
            elif isinstance(value, dict):
                result[key] = TaskRow._convert_decimals(value)
            elif isinstance(value, list):
                result[key] = [float(v) if isinstance(v, Decimal) else v for v in value]
            else:
                result[key] = value
        return result


class BusinessRow(TaskRow):
    """Business-specific row with 5 additional fields.

    Business fields (5):
        company_id, office_phone, stripe_id, booking_type, facebook_page_id
    """

    type: str = "Business"

    # Business custom fields (5)
    company_id: str | None = None
    office_phone: str | None = None
    stripe_id: str | None = None
    booking_type: str | None = None
    facebook_page_id: str | None = None


class UnitRow(TaskRow):
    """Unit-specific row with 9 additional fields (FR-SUBCLASS-001).

    Per TDD-0009: Extends base with Unit-specific fields including
    direct custom fields and cascade/derived fields.

    Direct custom fields (5):
        mrr, weekly_ad_spend, products, languages, discount

    Cascade/derived fields (4):
        office, office_phone, vertical, specialty
    """

    type: str = "Unit"

    # Direct custom fields (5)
    mrr: Decimal | None = None
    weekly_ad_spend: Decimal | None = None
    products: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    discount: Decimal | None = None

    # Cascade/derived fields (4)
    office: str | None = None
    office_phone: str | None = None
    vertical: str | None = None
    specialty: str | None = None


class ContactRow(TaskRow):
    """Contact-specific row with 12 additional fields (FR-SUBCLASS-002).

    Per TDD-0009: Extends base with Contact-specific fields.

    Contact fields (12):
        full_name, nickname, contact_phone, contact_email, position,
        employee_id, contact_url, time_zone, city,
        office_phone, vertical, dashboard_uuid
    """

    type: str = "Contact"

    # Contact fields (9 original)
    full_name: str | None = None
    nickname: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    position: str | None = None
    employee_id: str | None = None
    contact_url: str | None = None
    time_zone: str | None = None
    city: str | None = None

    # Cascade fields (3)
    office_phone: str | None = None
    vertical: str | None = None
    dashboard_uuid: str | None = None


class OfferRow(TaskRow):
    """Offer-specific row with 10 additional fields.

    Cascade fields (5):
        office, office_phone, vertical, mrr, weekly_ad_spend

    Custom fields (5):
        specialty, offer_id, platforms, language, cost
    """

    type: str = "Offer"

    # Cascade fields
    office: str | None = None
    office_phone: str | None = None
    vertical: str | None = None
    mrr: Decimal | None = None
    weekly_ad_spend: Decimal | None = None

    # Custom fields
    specialty: str | None = None
    offer_id: str | None = None
    platforms: list[str] = Field(default_factory=list)
    language: str | None = None
    cost: str | None = None


class AssetEditRow(TaskRow):
    """AssetEdit-specific row with 21 additional fields.

    Process fields (10):
        started_at, process_completed_at, process_notes, status,
        priority, process_due_date, assigned_to, vertical,
        office_phone, specialty

    AssetEdit-specific fields (11):
        asset_approval, asset_id, editor, reviewer, offer_id,
        raw_assets, review_all_ads, score, asset_edit_specialty,
        template_id, videos_paid
    """

    type: str = "AssetEdit"

    # Process fields (10)
    started_at: str | None = None
    process_completed_at: str | None = None
    process_notes: str | None = None
    status: str | None = None
    priority: str | None = None
    process_due_date: str | None = None
    assigned_to: str | None = None
    vertical: str | None = None
    office_phone: str | None = None
    specialty: list[str] = Field(default_factory=list)

    # AssetEdit-specific fields (11)
    asset_approval: str | None = None
    asset_id: str | None = None
    editor: str | None = None
    reviewer: str | None = None
    offer_id: int | None = None
    raw_assets: str | None = None
    review_all_ads: bool | None = None
    score: float | None = None
    asset_edit_specialty: list[str] = Field(default_factory=list)
    template_id: int | None = None
    videos_paid: int | None = None


class AssetEditHolderRow(TaskRow):
    """AssetEditHolder-specific row with 1 additional field.

    Cascade fields (1):
        office_phone
    """

    type: str = "AssetEditHolder"

    # Cascade fields
    office_phone: str | None = None
