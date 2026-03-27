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

    street_number: str | None = Field(
        default=None, description="Street number portion of the address."
    )
    street_name: str | None = Field(
        default=None, description="Street name portion of the address."
    )
    suite: str | None = Field(
        default=None, description="Suite, unit, or apartment number."
    )
    city: str | None = Field(default=None, description="City name.")
    state: str | None = Field(default=None, description="State or province code.")
    postal_code: str | None = Field(
        default=None,
        description="Postal or ZIP code. Canonical field name (never 'zip').",
    )
    country: str | None = Field(default=None, description="Country name or ISO code.")
    timezone: str | None = Field(
        default=None, description="IANA timezone identifier (e.g., 'America/New_York')."
    )


class IntakeSocialProfile(BaseModel):
    """A social media profile URL to persist on the Business entity."""

    model_config = ConfigDict(frozen=True)

    platform: str = Field(
        description="Social media platform name (facebook, instagram, youtube, linkedin)."
    )
    url: str = Field(description="Full URL to the social media profile.")


class IntakeContact(BaseModel):
    """Primary contact to create under the business's contact_holder."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Full name of the primary contact.")
    email: str | None = Field(default=None, description="Email address of the contact.")
    phone: str | None = Field(default=None, description="Phone number in E.164 format.")
    timezone: str | None = Field(
        default=None, description="IANA timezone identifier for the contact."
    )


class IntakeProcessConfig(BaseModel):
    """Process routing configuration for inline creation."""

    model_config = ConfigDict(frozen=True)

    process_type: str = Field(
        description="Process type to route to (sales, consultation, retention, implementation)."
    )
    due_at: str | None = Field(
        default=None, description="Due datetime in ISO 8601 format."
    )
    assignee_name: str | None = Field(
        default=None, description="Host name for assignee fuzzy matching."
    )


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
    name: str = Field(description="Business display name.")
    office_phone: str = Field(
        description="Primary office phone number in E.164 format."
    )

    # Enrichment data
    num_reviews: int | None = Field(
        default=None, description="Number of online reviews for the business."
    )
    website: str | None = Field(default=None, description="Business website URL.")
    hours: dict[str, Any] | None = Field(
        default=None, description="Business operating hours by day of week."
    )

    # Address (postal_code canonical -- ZIP-MISMATCH fix)
    address: IntakeAddress | None = Field(
        default=None, description="Business street address."
    )

    # Social profiles (SOCIAL-PROFILES-ORPHANED fix)
    social_profiles: list[IntakeSocialProfile] = Field(
        default_factory=list,
        description="Social media profile URLs for the business.",
    )

    # Contact (primary invitee)
    contact: IntakeContact = Field(
        description="Primary contact to create under the business."
    )

    # Unit configuration
    vertical: str = Field(
        description="Business vertical category (e.g., 'dental', 'medical')."
    )
    unit_name: str | None = Field(
        default=None,
        description="Unit display name. Defaults to '{name} -- {vertical_title}'.",
    )

    # Process routing (optional -- created if provided)
    process: IntakeProcessConfig | None = Field(
        default=None,
        description="Optional process routing configuration. Creates a process subtask if provided.",
    )


class IntakeBusinessCreateResponse(BaseModel):
    """Result of full business hierarchy creation.

    Returns GIDs for all created entities so the caller can
    reference them in subsequent operations.
    """

    model_config = ConfigDict(frozen=True)

    business_gid: str = Field(description="Asana GID of the created business task.")
    contact_gid: str = Field(description="Asana GID of the created contact subtask.")
    unit_gid: str = Field(description="Asana GID of the created unit subtask.")
    contact_holder_gid: str = Field(
        description="Asana GID of the contact holder subtask."
    )
    unit_holder_gid: str = Field(description="Asana GID of the unit holder subtask.")
    process_gid: str | None = Field(
        default=None,
        description="Asana GID of the created process subtask. Null if process was not requested.",
    )

    # Holder GIDs (all 7 holders created)
    holders: dict[str, str] = Field(
        description="Map of holder type names to their Asana GIDs (e.g., 'contact_holder' -> 'gid').",
    )


# ---------------------------------------------------------------------------
# Process Routing (ADR section 2.4)
# ---------------------------------------------------------------------------


class IntakeRouteRequest(BaseModel):
    """Route a unit to a specific process type.

    Replaces legacy unit.route(f"route_{process_name}") string dispatch.
    """

    model_config = ConfigDict(frozen=True)

    unit_gid: str = Field(description="Asana GID of the unit to route from.")
    process_type: str = Field(
        description="Process type to route to (sales, consultation, retention, implementation)."
    )
    due_at: str | None = Field(
        default=None, description="Due datetime in ISO 8601 format."
    )
    assignee_name: str | None = Field(
        default=None, description="Host name for assignee fuzzy matching."
    )
    triggered_by: str = Field(
        default="automation",
        description="Actor that triggered this route (e.g., 'automation', 'manual').",
    )


class IntakeRouteResponse(BaseModel):
    """Result of process routing."""

    model_config = ConfigDict(frozen=True)

    process_gid: str = Field(description="Asana GID of the routed process subtask.")
    process_type: str = Field(description="Process type that was routed to.")
    is_new: bool = Field(
        description="True if a new process was created, false if an existing process was reused."
    )
    assignee_name: str | None = Field(
        default=None, description="Resolved assignee name after fuzzy matching."
    )


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
