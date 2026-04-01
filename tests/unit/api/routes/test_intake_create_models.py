"""Tests for intake creation route models.

Covers: IntakeAddress, IntakeSocialProfile, IntakeContact,
IntakeProcessConfig, IntakeBusinessCreateRequest,
IntakeBusinessCreateResponse, IntakeRouteRequest, IntakeRouteResponse.

Focus: frozen immutability, field defaults, nested model composition,
serialization round-trips.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.api.routes.intake_create_models import (
    IntakeAddress,
    IntakeBusinessCreateRequest,
    IntakeBusinessCreateResponse,
    IntakeContact,
    IntakeProcessConfig,
    IntakeRouteRequest,
    IntakeRouteResponse,
    IntakeSocialProfile,
)

# ---------------------------------------------------------------------------
# IntakeAddress
# ---------------------------------------------------------------------------


class TestIntakeAddress:
    """Tests for IntakeAddress model."""

    def test_all_fields_optional(self) -> None:
        """All address fields default to None."""
        addr = IntakeAddress()
        assert addr.street_number is None
        assert addr.street_name is None
        assert addr.suite is None
        assert addr.city is None
        assert addr.state is None
        assert addr.postal_code is None
        assert addr.country is None
        assert addr.timezone is None

    def test_fully_populated(self) -> None:
        """Address with all fields set round-trips correctly."""
        addr = IntakeAddress(
            street_number="123",
            street_name="Main St",
            suite="Suite 200",
            city="Walnut Creek",
            state="CA",
            postal_code="94596",
            country="US",
            timezone="America/Los_Angeles",
        )
        assert addr.postal_code == "94596"
        assert addr.timezone == "America/Los_Angeles"

    def test_frozen_immutability(self) -> None:
        """IntakeAddress is frozen and rejects mutation."""
        addr = IntakeAddress(city="Oakland")
        with pytest.raises(ValidationError):
            addr.city = "Berkeley"  # type: ignore[misc]

    def test_model_dump_round_trip(self) -> None:
        """model_dump -> model_validate preserves all fields."""
        addr = IntakeAddress(city="Oakland", state="CA", postal_code="94612")
        restored = IntakeAddress.model_validate(addr.model_dump())
        assert restored == addr

    def test_model_dump_exclude_none(self) -> None:
        """model_dump with exclude_none omits unset fields."""
        addr = IntakeAddress(city="Oakland")
        dumped = addr.model_dump(exclude_none=True)
        assert dumped == {"city": "Oakland"}
        assert "street_number" not in dumped


# ---------------------------------------------------------------------------
# IntakeSocialProfile
# ---------------------------------------------------------------------------


class TestIntakeSocialProfile:
    """Tests for IntakeSocialProfile model."""

    def test_valid_profile(self) -> None:
        """Social profile with platform and url."""
        profile = IntakeSocialProfile(
            platform="facebook",
            url="https://www.facebook.com/acme.chiro",
        )
        assert profile.platform == "facebook"
        assert profile.url == "https://www.facebook.com/acme.chiro"

    def test_platform_required(self) -> None:
        """platform is required."""
        with pytest.raises(ValidationError):
            IntakeSocialProfile(url="https://fb.com/acme")  # type: ignore[call-arg]

    def test_url_required(self) -> None:
        """url is required."""
        with pytest.raises(ValidationError):
            IntakeSocialProfile(platform="facebook")  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        """IntakeSocialProfile is frozen."""
        profile = IntakeSocialProfile(
            platform="instagram",
            url="https://instagram.com/acme",
        )
        with pytest.raises(ValidationError):
            profile.platform = "tiktok"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IntakeContact
# ---------------------------------------------------------------------------


class TestIntakeContact:
    """Tests for IntakeContact model."""

    def test_name_required(self) -> None:
        """name is the only required field."""
        contact = IntakeContact(name="Dr. Jane Smith")
        assert contact.name == "Dr. Jane Smith"
        assert contact.email is None
        assert contact.phone is None
        assert contact.timezone is None

    def test_missing_name_raises(self) -> None:
        """Missing name raises ValidationError."""
        with pytest.raises(ValidationError):
            IntakeContact()  # type: ignore[call-arg]

    def test_fully_populated(self) -> None:
        """Contact with all fields."""
        contact = IntakeContact(
            name="Dr. Jane Smith",
            email="jane@acmechiro.com",
            phone="+19259998806",
            timezone="America/Los_Angeles",
        )
        assert contact.email == "jane@acmechiro.com"
        assert contact.phone == "+19259998806"

    def test_frozen(self) -> None:
        """IntakeContact is frozen."""
        contact = IntakeContact(name="Test")
        with pytest.raises(ValidationError):
            contact.name = "Modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IntakeProcessConfig
# ---------------------------------------------------------------------------


class TestIntakeProcessConfig:
    """Tests for IntakeProcessConfig model."""

    def test_process_type_required(self) -> None:
        """process_type is required, others optional."""
        config = IntakeProcessConfig(process_type="consultation")
        assert config.process_type == "consultation"
        assert config.due_at is None
        assert config.assignee_name is None

    def test_missing_process_type_raises(self) -> None:
        """Missing process_type raises ValidationError."""
        with pytest.raises(ValidationError):
            IntakeProcessConfig()  # type: ignore[call-arg]

    def test_fully_populated(self) -> None:
        """ProcessConfig with all fields."""
        config = IntakeProcessConfig(
            process_type="sales",
            due_at="2026-03-20T10:00:00Z",
            assignee_name="Alice Johnson",
        )
        assert config.due_at == "2026-03-20T10:00:00Z"
        assert config.assignee_name == "Alice Johnson"

    def test_frozen(self) -> None:
        """IntakeProcessConfig is frozen."""
        config = IntakeProcessConfig(process_type="retention")
        with pytest.raises(ValidationError):
            config.process_type = "implementation"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IntakeBusinessCreateRequest
# ---------------------------------------------------------------------------


class TestIntakeBusinessCreateRequest:
    """Tests for IntakeBusinessCreateRequest model."""

    @staticmethod
    def _minimal_payload() -> dict:
        """Smallest valid request payload."""
        return {
            "name": "Acme Chiropractic",
            "office_phone": "+19259998806",
            "contact": {"name": "Dr. Jane Smith"},
            "vertical": "chiro",
        }

    def test_minimal_valid(self) -> None:
        """Minimal request has correct defaults."""
        req = IntakeBusinessCreateRequest.model_validate(self._minimal_payload())
        assert req.name == "Acme Chiropractic"
        assert req.office_phone == "+19259998806"
        assert req.vertical == "chiro"
        assert req.contact.name == "Dr. Jane Smith"
        # Defaults
        assert req.num_reviews is None
        assert req.website is None
        assert req.hours is None
        assert req.address is None
        assert req.social_profiles == []
        assert req.unit_name is None
        assert req.process is None

    def test_missing_required_field_name(self) -> None:
        """Missing name raises ValidationError."""
        payload = self._minimal_payload()
        del payload["name"]
        with pytest.raises(ValidationError) as exc_info:
            IntakeBusinessCreateRequest.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_missing_required_field_contact(self) -> None:
        """Missing contact raises ValidationError."""
        payload = self._minimal_payload()
        del payload["contact"]
        with pytest.raises(ValidationError) as exc_info:
            IntakeBusinessCreateRequest.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("contact",) for e in errors)

    def test_nested_address(self) -> None:
        """Address sub-model is parsed correctly."""
        payload = self._minimal_payload()
        payload["address"] = {"city": "Oakland", "state": "CA", "postal_code": "94612"}
        req = IntakeBusinessCreateRequest.model_validate(payload)
        assert req.address is not None
        assert req.address.city == "Oakland"
        assert req.address.postal_code == "94612"

    def test_social_profiles_list(self) -> None:
        """Social profiles are parsed as list of IntakeSocialProfile."""
        payload = self._minimal_payload()
        payload["social_profiles"] = [
            {"platform": "facebook", "url": "https://fb.com/acme"},
            {"platform": "instagram", "url": "https://ig.com/acme"},
        ]
        req = IntakeBusinessCreateRequest.model_validate(payload)
        assert len(req.social_profiles) == 2
        assert req.social_profiles[0].platform == "facebook"
        assert req.social_profiles[1].platform == "instagram"

    def test_empty_social_profiles(self) -> None:
        """Empty social_profiles list is valid (default)."""
        req = IntakeBusinessCreateRequest.model_validate(self._minimal_payload())
        assert req.social_profiles == []

    def test_nested_process_config(self) -> None:
        """Process sub-model is parsed correctly."""
        payload = self._minimal_payload()
        payload["process"] = {
            "process_type": "consultation",
            "due_at": "2026-03-20T10:00:00Z",
        }
        req = IntakeBusinessCreateRequest.model_validate(payload)
        assert req.process is not None
        assert req.process.process_type == "consultation"

    def test_frozen(self) -> None:
        """IntakeBusinessCreateRequest is frozen."""
        req = IntakeBusinessCreateRequest.model_validate(self._minimal_payload())
        with pytest.raises(ValidationError):
            req.name = "Changed"  # type: ignore[misc]

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate preserves structure."""
        payload = self._minimal_payload()
        payload["address"] = {"city": "SF", "postal_code": "94105"}
        payload["social_profiles"] = [
            {"platform": "linkedin", "url": "https://linkedin.com/acme"}
        ]
        req = IntakeBusinessCreateRequest.model_validate(payload)
        restored = IntakeBusinessCreateRequest.model_validate(req.model_dump())
        assert restored.name == req.name
        assert restored.address.city == req.address.city  # type: ignore[union-attr]
        assert len(restored.social_profiles) == 1


# ---------------------------------------------------------------------------
# IntakeBusinessCreateResponse
# ---------------------------------------------------------------------------


class TestIntakeBusinessCreateResponse:
    """Tests for IntakeBusinessCreateResponse model."""

    @staticmethod
    def _minimal_payload() -> dict:
        """Smallest valid response payload."""
        return {
            "business_gid": "1111",
            "contact_gid": "2222",
            "unit_gid": "3333",
            "contact_holder_gid": "4444",
            "unit_holder_gid": "5555",
            "holders": {"contact_holder": "4444", "unit_holder": "5555"},
        }

    def test_minimal_valid(self) -> None:
        """Minimal response parses correctly."""
        resp = IntakeBusinessCreateResponse.model_validate(self._minimal_payload())
        assert resp.business_gid == "1111"
        assert resp.process_gid is None

    def test_with_process_gid(self) -> None:
        """Response with process_gid populated."""
        payload = self._minimal_payload()
        payload["process_gid"] = "6666"
        resp = IntakeBusinessCreateResponse.model_validate(payload)
        assert resp.process_gid == "6666"

    def test_holders_dict(self) -> None:
        """holders dict maps holder type to GID."""
        resp = IntakeBusinessCreateResponse.model_validate(self._minimal_payload())
        assert resp.holders["contact_holder"] == "4444"

    def test_frozen(self) -> None:
        """IntakeBusinessCreateResponse is frozen."""
        resp = IntakeBusinessCreateResponse.model_validate(self._minimal_payload())
        with pytest.raises(ValidationError):
            resp.business_gid = "9999"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IntakeRouteRequest
# ---------------------------------------------------------------------------


class TestIntakeRouteRequest:
    """Tests for IntakeRouteRequest model."""

    def test_minimal_valid(self) -> None:
        """Minimal request with required fields and defaults."""
        req = IntakeRouteRequest(unit_gid="U123", process_type="consultation")
        assert req.unit_gid == "U123"
        assert req.process_type == "consultation"
        assert req.due_at is None
        assert req.assignee_name is None
        assert req.triggered_by == "automation"  # default

    def test_triggered_by_override(self) -> None:
        """triggered_by can be overridden."""
        req = IntakeRouteRequest(
            unit_gid="U123", process_type="sales", triggered_by="manual"
        )
        assert req.triggered_by == "manual"

    def test_missing_unit_gid_raises(self) -> None:
        """Missing unit_gid raises ValidationError."""
        with pytest.raises(ValidationError):
            IntakeRouteRequest(process_type="sales")  # type: ignore[call-arg]

    def test_missing_process_type_raises(self) -> None:
        """Missing process_type raises ValidationError."""
        with pytest.raises(ValidationError):
            IntakeRouteRequest(unit_gid="U123")  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        """IntakeRouteRequest is frozen."""
        req = IntakeRouteRequest(unit_gid="U123", process_type="consultation")
        with pytest.raises(ValidationError):
            req.process_type = "sales"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IntakeRouteResponse
# ---------------------------------------------------------------------------


class TestIntakeRouteResponse:
    """Tests for IntakeRouteResponse model."""

    def test_valid_response(self) -> None:
        """Full response parses correctly."""
        resp = IntakeRouteResponse(
            process_gid="P999",
            process_type="consultation",
            is_new=True,
            assignee_name="Alice Johnson",
        )
        assert resp.process_gid == "P999"
        assert resp.is_new is True
        assert resp.assignee_name == "Alice Johnson"

    def test_assignee_name_optional(self) -> None:
        """assignee_name defaults to None."""
        resp = IntakeRouteResponse(
            process_gid="P999", process_type="sales", is_new=False
        )
        assert resp.assignee_name is None

    def test_frozen(self) -> None:
        """IntakeRouteResponse is frozen."""
        resp = IntakeRouteResponse(
            process_gid="P999", process_type="sales", is_new=True
        )
        with pytest.raises(ValidationError):
            resp.is_new = False  # type: ignore[misc]
