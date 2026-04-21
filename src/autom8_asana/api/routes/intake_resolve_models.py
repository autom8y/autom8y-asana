"""Pydantic models for intake resolve endpoints.

Contract constraint: These models MUST produce the exact same JSON shape
as the interop models in autom8y-client-sdk/asana/models.py.
"""

from __future__ import annotations

from autom8y_api_schemas import LeadPhoneField, OfficePhoneField
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Business Resolution (ADR section 2.1)
# ---------------------------------------------------------------------------


class BusinessResolveRequest(BaseModel):
    """Resolve a business by phone and optional vertical.

    Phone is the primary key. Vertical narrows resolution for
    businesses that operate in multiple verticals.
    """

    model_config = ConfigDict(frozen=True)

    office_phone: OfficePhoneField = Field(
        description="Office phone number in E.164 format. Primary lookup key.",
        examples=["+19259998806"],
    )
    vertical: str | None = Field(
        default=None,
        description="Optional vertical filter to narrow resolution.",
        examples=["chiro"],
    )


class BusinessResolveResponse(BaseModel):
    """Result of business resolution.

    found=False means no business exists for this phone.
    Explicit not-found prevents the legacy stale-GID-fallback
    bug (ANOMALY-F) that silently created duplicates (ADR-INT-001).
    """

    model_config = ConfigDict(frozen=True)

    found: bool = Field(
        description="True if a business was resolved for the given phone.",
        examples=[True],
    )
    task_gid: str | None = Field(
        default=None,
        description="Asana task GID of the resolved business. Null when not found.",
        examples=["1234567890123456"],
    )
    name: str | None = Field(
        default=None,
        description="Resolved business display name.",
        examples=["Acme Chiropractic"],
    )
    office_phone: OfficePhoneField | None = Field(
        default=None,
        description="Office phone echoed back for request correlation.",
        examples=["+19259998806"],
    )
    vertical: str | None = Field(
        default=None, description="Resolved business vertical.", examples=["chiro"]
    )
    company_id: str | None = Field(
        default=None,
        description="External company GUID. Null if not onboarded.",
        examples=["b1c2d3e4-f5a6-7890-bcde-f12345678901"],
    )
    has_unit: bool = Field(
        default=False,
        description="True if a unit subtask exists under the business.",
        examples=[True],
    )
    has_contact_holder: bool = Field(
        default=False,
        description="True if a contact_holder subtask exists under the business.",
        examples=[True],
    )


# ---------------------------------------------------------------------------
# Contact Resolution (ADR section 2.2)
# ---------------------------------------------------------------------------


class ContactResolveRequest(BaseModel):
    """Resolve a contact within a business scope.

    Single algorithm: email (exact) -> phone (exact) -> no match.
    Name matching is deliberately excluded (ADR-INT-002).
    """

    model_config = ConfigDict(frozen=True)

    business_gid: str = Field(
        min_length=1,
        description="Asana GID of the business to scope contact resolution to.",
        examples=["1234567890123456"],
    )
    email: str | None = Field(
        default=None,
        description="Email address for exact match on contact_email field.",
        examples=["jane@acmechiro.com"],
    )
    phone: LeadPhoneField | None = Field(
        default=None,
        description="Phone number in E.164 format for exact match on contact_phone field.",
        examples=["+14155551234"],
    )


class ContactResolveResponse(BaseModel):
    """Result of contact resolution.

    found=False means no existing contact matches the given
    email or phone within the business scope.
    """

    model_config = ConfigDict(frozen=True)

    found: bool = Field(
        description="True if a contact was resolved within the business scope.",
        examples=[True],
    )
    contact_gid: str | None = Field(
        default=None,
        description="Asana task GID of the resolved contact. Null when not found.",
        examples=["1234567890123457"],
    )
    name: str | None = Field(
        default=None,
        description="Resolved contact display name.",
        examples=["Dr. Jane Smith"],
    )
    email: str | None = Field(
        default=None,
        description="Resolved contact email address.",
        examples=["jane@acmechiro.com"],
    )
    phone: LeadPhoneField | None = Field(
        default=None,
        description="Resolved contact phone number.",
        examples=["+14155551234"],
    )
    match_field: str | None = Field(
        default=None,
        description="Field that matched: 'email', 'phone', or null if not found.",
        examples=["email"],
    )


__all__ = [
    "BusinessResolveRequest",
    "BusinessResolveResponse",
    "ContactResolveRequest",
    "ContactResolveResponse",
]
