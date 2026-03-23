"""Pydantic models for intake resolve endpoints.

Contract constraint: These models MUST produce the exact same JSON shape
as the interop models in autom8y-interop/asana/models.py.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Business Resolution (ADR section 2.1)
# ---------------------------------------------------------------------------


class BusinessResolveRequest(BaseModel):
    """Resolve a business by phone and optional vertical.

    Phone is the primary key. Vertical narrows resolution for
    businesses that operate in multiple verticals.
    """

    model_config = ConfigDict(frozen=True)

    office_phone: str  # E.164 format
    vertical: str | None = None  # Optional vertical filter


class BusinessResolveResponse(BaseModel):
    """Result of business resolution.

    found=False means no business exists for this phone.
    Explicit not-found prevents the legacy stale-GID-fallback
    bug (ANOMALY-F) that silently created duplicates (ADR-INT-001).
    """

    model_config = ConfigDict(frozen=True)

    found: bool
    task_gid: str | None = None  # Asana task GID (null when not found)
    name: str | None = None  # Business name
    office_phone: str | None = None  # Echo back for correlation
    vertical: str | None = None  # Resolved vertical
    company_id: str | None = None  # Contente GUID (null if not onboarded)
    has_unit: bool = False  # Whether a unit subtask exists
    has_contact_holder: bool = False  # Whether contact_holder exists


# ---------------------------------------------------------------------------
# Contact Resolution (ADR section 2.2)
# ---------------------------------------------------------------------------


class ContactResolveRequest(BaseModel):
    """Resolve a contact within a business scope.

    Single algorithm: email (exact) -> phone (exact) -> no match.
    Name matching is deliberately excluded (ADR-INT-002).
    """

    model_config = ConfigDict(frozen=True)

    business_gid: str  # Scope resolution to this business
    email: str | None = None  # Exact match on contact_email
    phone: str | None = None  # E.164, exact match on contact_phone


class ContactResolveResponse(BaseModel):
    """Result of contact resolution.

    found=False means no existing contact matches the given
    email or phone within the business scope.
    """

    model_config = ConfigDict(frozen=True)

    found: bool
    contact_gid: str | None = None  # Asana task GID
    name: str | None = None  # Contact name
    email: str | None = None  # Contact email
    phone: str | None = None  # Contact phone
    match_field: str | None = None  # "email" | "phone" | null


__all__ = [
    "BusinessResolveRequest",
    "BusinessResolveResponse",
    "ContactResolveRequest",
    "ContactResolveResponse",
]
