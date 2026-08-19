"""Pydantic models for intake resolve endpoints.

Contract constraint: These models MUST produce the exact same JSON shape
as the interop models in autom8y-client-sdk/asana/models.py.

F-9 exception to that constraint (durable observation semantics, W-F lane):
``BusinessResolveResponse.has_unit`` / ``.has_contact_holder`` are tri-state
producer-side and are OMITTED from the wire when unobserved. The interop
models keep ``bool = False`` unchanged -- an omitted key parses to the same
attribute value there, while ``model_fields_set`` (the field the consuming
tripwire probe reads, calendly-intake ``tripwire/probe.py::read_field``)
correctly excludes it. Asserted values remain shape-identical.
"""

from __future__ import annotations

from autom8y_api_schemas import LeadPhoneField, OfficePhoneField
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
)

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
    # F-9 DURABLE CURE (tri-state sub-entity observation).
    # The pre-cure ``bool = False`` declaration made "not observed"
    # UNREPRESENTABLE: the producing service always stamped an explicit
    # false onto the wire, so ordinary production index lag (business task
    # indexed before its sub-entities) rendered as a POSITIVE assertion
    # ``has_unit: false`` -- which the W5-3 first-create tripwire correctly
    # read as a written(True) != read(False) contradiction -> MISMATCH ->
    # unattended revert of the client-facing subscription. Tri-state makes
    # the unknown state representable; the serializer below keeps it OFF
    # the wire entirely (the consuming probe's ``read_field`` then resolves
    # it to ABSENT/UNOBSERVED, which can never revert production).
    has_unit: bool | None = Field(
        default=None,
        description=(
            "Tri-state: True = a unit subtask was observed; False = a "
            "non-empty subtask listing was observed without one (a real "
            "assertion of absence); None/omitted = NOT OBSERVED (never "
            "rendered as false on the wire)."
        ),
        examples=[True],
    )
    has_contact_holder: bool | None = Field(
        default=None,
        description=(
            "Tri-state: True = a contact_holder subtask was observed; "
            "False = a non-empty subtask listing was observed without one; "
            "None/omitted = NOT OBSERVED (never rendered as false on the "
            "wire)."
        ),
        examples=[True],
    )

    # ★ NO return annotation on this serializer (critique A-1): annotating it
    # `-> dict[str, Any]` makes pydantic derive the SERIALIZATION json-schema
    # from the annotation and erases every property from
    # model_json_schema(mode="serialization"). Latent today only because the
    # router mounts include_in_schema=False (intake_resolve.py:51). The
    # targeted mypy ignore below exists BECAUSE the annotation must stay off;
    # do not "fix" it by re-annotating.
    @model_serializer(mode="wrap")
    def _omit_unobserved_sub_entities(  # type: ignore[no-untyped-def]
        self, handler: SerializerFunctionWrapHandler
    ):
        """F-9: exclude-unset semantics, scoped to the two sub-entity fields.

        Implemented at the model level rather than via the route's
        ``response_model_exclude_unset`` because the route-level flag also
        strips ``meta.timestamp`` (a ``default_factory`` field on the fleet
        ``ResponseMeta`` envelope) -- a collateral wire regression. Scoping
        the omission here changes exactly the two fields the F-9 ruling
        governs and nothing else.
        """
        out = handler(self)
        if isinstance(out, dict):
            for field in ("has_unit", "has_contact_holder"):
                if field not in self.model_fields_set:
                    out.pop(field, None)
        return out


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


# ---------------------------------------------------------------------------
# Business-by-Email Resolution (OW-10a email fallback)
# ---------------------------------------------------------------------------


class BusinessByEmailResolveRequest(BaseModel):
    """Resolve a business indirectly, via a contact's email.

    The fallback for bookings that carry no office-phone answer. Email is the
    ONLY input: this surface deliberately accepts no second criterion, because
    every additional narrowing knob is a way to turn an ambiguous email into a
    confident wrong answer.
    """

    model_config = ConfigDict(frozen=True)

    email: str = Field(
        min_length=3,
        max_length=320,  # RFC 3696 practical ceiling
        description="Contact email address. Exact match against contact_email.",
        examples=["jane@acmechiro.example"],
    )


class BusinessByEmailResolveResponse(BaseModel):
    """Result of email->business resolution.

    ``found=True`` is asserted ONLY on a unique, E.164-valid business phone.
    Every other outcome is ``found=False`` carrying a ``reason`` that names
    WHICH non-answer occurred -- the C3 failure-discrimination discipline. A
    collapsed "not found" would make "this email is unknown", "this email is
    shared across two companies" and "this contact's office phone never
    cascaded" indistinguishable, and they have three different remedies.

    ``found=False`` is never a guess and never a best-effort pick: an
    ``office_phone`` here becomes a business-of-record downstream, where a
    wrong value SUCCEEDS against the wrong business rather than failing.
    """

    model_config = ConfigDict(frozen=True)

    found: bool = Field(
        description="True only when the email resolved to exactly one business.",
        examples=[True],
    )
    office_phone: OfficePhoneField | None = Field(
        default=None,
        description=(
            "Office phone of the resolved business, cascaded from the parent "
            "Business onto the contact row. Null unless found=True. Feed this "
            "to POST /v1/resolve/business for the full business record."
        ),
        examples=["+19259998806"],
    )
    vertical: str | None = Field(
        default=None,
        description=(
            "Business vertical, when unambiguous across the matched contact "
            "rows. Context only -- never part of the found decision."
        ),
        examples=["chiro"],
    )
    contact_gid: str | None = Field(
        default=None,
        description=(
            "Asana task GID of the matched contact. Populated only when "
            "exactly one contact row matched, so it is never an arbitrary "
            "pick from several."
        ),
        examples=["1234567890123457"],
    )
    reason: str = Field(
        description=(
            "Discriminated outcome. One of: 'unique_match' (found=True); "
            "'email_not_found' (no contact carries this email); "
            "'email_ambiguous' (the email points at 2+ distinct businesses); "
            "'office_phone_absent' (contact(s) matched but no office phone "
            "cascaded); 'office_phone_malformed' (a phone cascaded but is not "
            "E.164, so it would be refused downstream)."
        ),
        examples=["unique_match"],
    )
    match_count: int = Field(
        default=0,
        ge=0,
        description="Number of contact ROWS matched (not distinct businesses).",
        examples=[1],
    )
    distinct_business_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Number of DISTINCT businesses the matched contacts belong to. "
            "This is the value the unique-match policy gates on; >1 forces "
            "found=False with reason='email_ambiguous'."
        ),
        examples=[1],
    )


__all__ = [
    "BusinessByEmailResolveRequest",
    "BusinessByEmailResolveResponse",
    "BusinessResolveRequest",
    "BusinessResolveResponse",
    "ContactResolveRequest",
    "ContactResolveResponse",
]
