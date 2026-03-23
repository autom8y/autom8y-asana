"""Pydantic models for intake creation and routing endpoints.

Contract constraint: These models MUST produce the exact same JSON shape
as the interop models in autom8y-interop/asana/models.py:
- IntakeBusinessCreateRequest/Response (ADR section 2.3)
- IntakeRouteRequest/Response (ADR section 2.4)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Business Creation (ADR section 2.3)
# ---------------------------------------------------------------------------


class IntakeAddress(BaseModel):
    """Address with postal_code as the canonical field.

    No alias needed here -- the ZIP alias lives in autom8y-google's
    StructuredAddress. By the time data reaches this model, it is
    already normalized to postal_code.
    """

    model_config = ConfigDict(frozen=True)

    street_number: str | None = None
    street_name: str | None = None
    suite: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None  # Canonical. Never "zip".
    country: str | None = None
    timezone: str | None = None


class IntakeSocialProfile(BaseModel):
    """A social media profile URL to persist on the Business entity."""

    model_config = ConfigDict(frozen=True)

    platform: str  # "facebook" | "instagram" | "youtube" | "linkedin"
    url: str


class IntakeContact(BaseModel):
    """Primary contact to create under the business's contact_holder."""

    model_config = ConfigDict(frozen=True)

    name: str
    email: str | None = None
    phone: str | None = None  # E.164
    timezone: str | None = None


class IntakeProcessConfig(BaseModel):
    """Process routing configuration for inline creation."""

    model_config = ConfigDict(frozen=True)

    process_type: str  # "sales" | "consultation" | "retention" | "implementation"
    due_at: str | None = None  # ISO 8601
    assignee_name: str | None = None


class IntakeBusinessCreateRequest(BaseModel):
    """Full business creation request for the intake pipeline.

    Creates the complete Asana entity hierarchy in a single
    SaveSession batch. All fields map to Asana custom fields
    on the Business task and its subtasks.

    Social profiles are first-class fields (fixes SOCIAL-PROFILES-ORPHANED).
    Address uses postal_code everywhere (fixes ZIP-MISMATCH).
    """

    model_config = ConfigDict(frozen=True)

    # Business identity
    name: str
    office_phone: str  # E.164 format

    # Enrichment data
    num_reviews: int | None = None
    website: str | None = None
    hours: dict[str, Any] | None = None

    # Address (postal_code canonical -- ZIP-MISMATCH fix)
    address: IntakeAddress | None = None

    # Social profiles (SOCIAL-PROFILES-ORPHANED fix)
    social_profiles: list[IntakeSocialProfile] = Field(default_factory=list)

    # Contact (primary invitee)
    contact: IntakeContact

    # Unit configuration
    vertical: str
    unit_name: str | None = None  # Default: "{name} -- {vertical_title}"

    # Process routing (optional -- created if provided)
    process: IntakeProcessConfig | None = None


class IntakeBusinessCreateResponse(BaseModel):
    """Result of full business hierarchy creation.

    Returns GIDs for all created entities so the caller can
    reference them in subsequent operations.
    """

    model_config = ConfigDict(frozen=True)

    business_gid: str
    contact_gid: str
    unit_gid: str
    contact_holder_gid: str
    unit_holder_gid: str
    process_gid: str | None = None  # Null if process was not requested

    # Holder GIDs (all 7 holders created)
    holders: dict[str, str]  # {"contact_holder": "gid", "unit_holder": "gid", ...}


# ---------------------------------------------------------------------------
# Process Routing (ADR section 2.4)
# ---------------------------------------------------------------------------


class IntakeRouteRequest(BaseModel):
    """Route a unit to a specific process type.

    Replaces legacy unit.route(f"route_{process_name}") string dispatch.
    """

    model_config = ConfigDict(frozen=True)

    unit_gid: str  # Unit to route from
    process_type: str  # "sales" | "consultation" | "retention" | "implementation"
    due_at: str | None = None  # ISO 8601 datetime
    assignee_name: str | None = None  # Host name for assignee fuzzy match
    triggered_by: str = "automation"  # Who triggered this route


class IntakeRouteResponse(BaseModel):
    """Result of process routing."""

    model_config = ConfigDict(frozen=True)

    process_gid: str
    process_type: str
    is_new: bool  # True if new process created, false if existing reused
    assignee_name: str | None = None  # Resolved assignee


__all__ = [
    "IntakeAddress",
    "IntakeBusinessCreateRequest",
    "IntakeBusinessCreateResponse",
    "IntakeContact",
    "IntakeProcessConfig",
    "IntakeRouteRequest",
    "IntakeRouteResponse",
    "IntakeSocialProfile",
]
