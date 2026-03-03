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


class UnitRow(TaskRow):
    """Unit-specific row with 11 additional fields (FR-SUBCLASS-001).

    Per TDD-0009: Extends base with Unit-specific fields including
    direct custom fields and derived fields.

    Direct custom fields (5):
        mrr, weekly_ad_spend, products, languages, discount

    Derived fields (6):
        office, office_phone, vertical, vertical_id, specialty, max_pipeline_stage
    """

    type: str = "Unit"

    # Direct custom fields (5)
    mrr: Decimal | None = None
    weekly_ad_spend: Decimal | None = None
    products: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    discount: Decimal | None = None

    # Derived fields (6)
    office: str | None = None
    office_phone: str | None = None
    vertical: str | None = None
    vertical_id: str | None = None
    specialty: str | None = None
    max_pipeline_stage: str | None = None


class ContactRow(TaskRow):
    """Contact-specific row with 13 additional fields (FR-SUBCLASS-002).

    Per TDD-0009: Extends base with Contact-specific fields.

    Contact fields (13):
        full_name, nickname, contact_phone, contact_email, position,
        employee_id, contact_url, time_zone, city,
        office_phone, vertical, vertical_id, dashboard_uuid
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

    # Cascade and derived fields (4)
    office_phone: str | None = None
    vertical: str | None = None
    vertical_id: str | None = None
    dashboard_uuid: str | None = None
