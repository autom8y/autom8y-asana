"""Tests for intake resolve route models.

Covers: BusinessResolveRequest, BusinessResolveResponse,
ContactResolveRequest, ContactResolveResponse.

Focus: frozen immutability, required vs optional fields,
boolean defaults, serialization round-trips.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.api.routes.intake_resolve_models import (
    BusinessResolveRequest,
    BusinessResolveResponse,
    ContactResolveRequest,
    ContactResolveResponse,
)

# ---------------------------------------------------------------------------
# BusinessResolveRequest
# ---------------------------------------------------------------------------


class TestBusinessResolveRequest:
    """Tests for BusinessResolveRequest model."""

    def test_minimal_valid(self) -> None:
        """Request with only office_phone (required)."""
        req = BusinessResolveRequest(office_phone="+19259998806")
        assert req.office_phone == "+19259998806"
        assert req.vertical is None

    def test_with_vertical(self) -> None:
        """Request with vertical filter."""
        req = BusinessResolveRequest(office_phone="+19259998806", vertical="chiro")
        assert req.vertical == "chiro"

    def test_missing_office_phone_raises(self) -> None:
        """Missing office_phone raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BusinessResolveRequest()  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("office_phone",) for e in errors)

    def test_frozen(self) -> None:
        """BusinessResolveRequest is frozen."""
        req = BusinessResolveRequest(office_phone="+19259998806")
        with pytest.raises(ValidationError):
            req.office_phone = "+14155551234"  # type: ignore[misc]

    def test_model_dump_round_trip(self) -> None:
        """model_dump -> model_validate round-trip."""
        req = BusinessResolveRequest(office_phone="+19259998806", vertical="dental")
        restored = BusinessResolveRequest.model_validate(req.model_dump())
        assert restored.office_phone == req.office_phone
        assert restored.vertical == req.vertical


# ---------------------------------------------------------------------------
# BusinessResolveResponse
# ---------------------------------------------------------------------------


class TestBusinessResolveResponse:
    """Tests for BusinessResolveResponse model."""

    def test_found_response(self) -> None:
        """Response when business is found."""
        resp = BusinessResolveResponse(
            found=True,
            task_gid="1234567890123456",
            name="Acme Chiropractic",
            office_phone="+19259998806",
            vertical="chiro",
            company_id="b1c2d3e4-f5a6-7890-bcde-f12345678901",
            has_unit=True,
            has_contact_holder=True,
        )
        assert resp.found is True
        assert resp.task_gid == "1234567890123456"
        assert resp.has_unit is True
        assert resp.has_contact_holder is True

    def test_not_found_response(self) -> None:
        """Response when business is not found."""
        resp = BusinessResolveResponse(found=False)
        assert resp.found is False
        assert resp.task_gid is None
        assert resp.name is None
        assert resp.office_phone is None
        assert resp.vertical is None
        assert resp.company_id is None
        assert resp.has_unit is None  # F-9 tri-state default: UNOBSERVED
        assert resp.has_contact_holder is None  # F-9 tri-state default

    def test_sub_entity_defaults_unobserved(self) -> None:
        """F-9: has_unit and has_contact_holder default to None (UNOBSERVED),
        never False -- an unobserved sub-entity must not be representable as
        an asserted absence."""
        resp = BusinessResolveResponse(found=True, task_gid="123")
        assert resp.has_unit is None
        assert resp.has_contact_holder is None

    def test_unobserved_sub_entities_are_omitted_from_the_wire(self) -> None:
        """F-9 exclude-unset semantics: unset sub-entity fields do not appear
        in the serialized output at all (the consuming probe's
        ``model_fields_set`` read then resolves them to ABSENT/UNOBSERVED)."""
        resp = BusinessResolveResponse(found=True, task_gid="123")
        dumped = resp.model_dump()
        assert "has_unit" not in dumped
        assert "has_contact_holder" not in dumped
        json_dumped = resp.model_dump_json()
        assert "has_unit" not in json_dumped
        assert "has_contact_holder" not in json_dumped

    def test_serialization_schema_retains_all_properties(self) -> None:
        """A-1 regression guard (CRITIQUE-s09-wf-asana-2026-08-18): a return
        annotation on the scoped model serializer makes pydantic derive the
        serialization json-schema from the annotation, erasing every property.
        Latent today only because the router mounts include_in_schema=False."""
        schema = BusinessResolveResponse.model_json_schema(mode="serialization")
        assert set(schema.get("properties", {})) == {
            "found",
            "task_gid",
            "name",
            "office_phone",
            "vertical",
            "company_id",
            "has_unit",
            "has_contact_holder",
        }

    def test_asserted_false_sub_entities_stay_on_the_wire(self) -> None:
        """F-9 teeth-preservation: an EXPLICITLY asserted false (a non-empty
        listing observed without the holder) is serialized -- the first-create
        tripwire keeps its positive-contradiction bite."""
        resp = BusinessResolveResponse(
            found=True,
            task_gid="123",
            has_unit=False,
            has_contact_holder=True,
        )
        dumped = resp.model_dump()
        assert dumped["has_unit"] is False
        assert dumped["has_contact_holder"] is True

    def test_frozen(self) -> None:
        """BusinessResolveResponse is frozen."""
        resp = BusinessResolveResponse(found=True, task_gid="123")
        with pytest.raises(ValidationError):
            resp.found = False  # type: ignore[misc]

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip."""
        resp = BusinessResolveResponse(
            found=True,
            task_gid="123",
            name="Test Biz",
            has_unit=True,
        )
        restored = BusinessResolveResponse.model_validate(resp.model_dump())
        assert restored.found is True
        assert restored.has_unit is True
        assert restored.name == "Test Biz"


# ---------------------------------------------------------------------------
# ContactResolveRequest
# ---------------------------------------------------------------------------


class TestContactResolveRequest:
    """Tests for ContactResolveRequest model."""

    def test_minimal_valid(self) -> None:
        """Request with only business_gid (required)."""
        req = ContactResolveRequest(business_gid="1234567890123456")
        assert req.business_gid == "1234567890123456"
        assert req.email is None
        assert req.phone is None

    def test_with_email(self) -> None:
        """Request with email lookup."""
        req = ContactResolveRequest(business_gid="123", email="jane@acmechiro.com")
        assert req.email == "jane@acmechiro.com"

    def test_with_phone(self) -> None:
        """Request with phone lookup."""
        req = ContactResolveRequest(business_gid="123", phone="+14155551234")
        assert req.phone == "+14155551234"

    def test_with_both_email_and_phone(self) -> None:
        """Request with both email and phone (email wins at resolution)."""
        req = ContactResolveRequest(
            business_gid="123",
            email="jane@acme.com",
            phone="+14155551234",
        )
        assert req.email == "jane@acme.com"
        assert req.phone == "+14155551234"

    def test_missing_business_gid_raises(self) -> None:
        """Missing business_gid raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ContactResolveRequest()  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("business_gid",) for e in errors)

    def test_frozen(self) -> None:
        """ContactResolveRequest is frozen."""
        req = ContactResolveRequest(business_gid="123", email="test@test.com")
        with pytest.raises(ValidationError):
            req.email = "other@test.com"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ContactResolveResponse
# ---------------------------------------------------------------------------


class TestContactResolveResponse:
    """Tests for ContactResolveResponse model."""

    def test_found_by_email(self) -> None:
        """Response when contact found by email match."""
        resp = ContactResolveResponse(
            found=True,
            contact_gid="C456",
            name="Dr. Jane Smith",
            email="jane@acmechiro.com",
            phone="+14155551234",
            match_field="email",
        )
        assert resp.found is True
        assert resp.contact_gid == "C456"
        assert resp.match_field == "email"

    def test_found_by_phone(self) -> None:
        """Response when contact found by phone match."""
        resp = ContactResolveResponse(
            found=True,
            contact_gid="C789",
            name="Bob",
            phone="+14155551234",
            match_field="phone",
        )
        assert resp.match_field == "phone"

    def test_not_found(self) -> None:
        """Response when no contact matches."""
        resp = ContactResolveResponse(found=False)
        assert resp.found is False
        assert resp.contact_gid is None
        assert resp.name is None
        assert resp.email is None
        assert resp.phone is None
        assert resp.match_field is None

    def test_frozen(self) -> None:
        """ContactResolveResponse is frozen."""
        resp = ContactResolveResponse(found=False)
        with pytest.raises(ValidationError):
            resp.found = True  # type: ignore[misc]

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip."""
        resp = ContactResolveResponse(
            found=True,
            contact_gid="C456",
            name="Jane",
            match_field="email",
        )
        restored = ContactResolveResponse.model_validate(resp.model_dump())
        assert restored.contact_gid == "C456"
        assert restored.match_field == "email"
