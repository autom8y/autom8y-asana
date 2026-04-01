"""Tests for entity resolution route models.

Covers: ResolutionCriterion, ResolutionRequest, ResolutionResultModel,
ResolutionMeta, ResolutionResponse.

Focus: E.164 phone validation, strip_phone_whitespace validator,
batch size enforcement, extra="allow" vs extra="forbid" behavior,
model composition.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.api.routes.resolver_models import (
    ResolutionCriterion,
    ResolutionMeta,
    ResolutionRequest,
    ResolutionResponse,
    ResolutionResultModel,
)

# ---------------------------------------------------------------------------
# ResolutionCriterion
# ---------------------------------------------------------------------------


class TestResolutionCriterion:
    """Tests for ResolutionCriterion model."""

    def test_empty_criterion_is_valid(self) -> None:
        """Criterion with no fields set is valid (extra=allow)."""
        crit = ResolutionCriterion()
        assert crit.phone is None
        assert crit.vertical is None
        assert crit.offer_id is None
        assert crit.contact_email is None
        assert crit.contact_phone is None

    def test_phone_valid_e164(self) -> None:
        """Valid E.164 phone passes validation."""
        crit = ResolutionCriterion(phone="+19259998806")
        assert crit.phone == "+19259998806"

    def test_phone_invalid_format_rejected(self) -> None:
        """Non-E.164 phone is rejected by pattern validation."""
        with pytest.raises(ValidationError):
            ResolutionCriterion(phone="925-999-8806")

    def test_phone_missing_plus_rejected(self) -> None:
        """Phone without leading + is rejected."""
        with pytest.raises(ValidationError):
            ResolutionCriterion(phone="19259998806")

    def test_phone_too_short_rejected(self) -> None:
        """Phone with fewer than 7 digits after + is rejected."""
        with pytest.raises(ValidationError):
            ResolutionCriterion(phone="+12345")

    def test_phone_too_long_rejected(self) -> None:
        """Phone with more than 15 digits after + is rejected."""
        with pytest.raises(ValidationError):
            ResolutionCriterion(phone="+1234567890123456")

    def test_strip_phone_whitespace_trailing(self) -> None:
        """Trailing whitespace on phone is stripped before validation."""
        crit = ResolutionCriterion(phone="+19259998806  ")
        assert crit.phone == "+19259998806"

    def test_strip_phone_whitespace_leading(self) -> None:
        """Leading whitespace on phone is stripped before validation."""
        crit = ResolutionCriterion(phone="  +19259998806")
        assert crit.phone == "+19259998806"

    def test_strip_phone_whitespace_newline(self) -> None:
        """Newline in phone string is stripped before validation."""
        crit = ResolutionCriterion(phone="+19259998806\n")
        assert crit.phone == "+19259998806"

    def test_strip_contact_phone_whitespace(self) -> None:
        """contact_phone also has whitespace stripped."""
        crit = ResolutionCriterion(contact_phone="  +14155551234  ")
        assert crit.contact_phone == "+14155551234"

    def test_phone_none_passes_validator(self) -> None:
        """None phone value passes through strip_phone_whitespace."""
        crit = ResolutionCriterion(phone=None)
        assert crit.phone is None

    def test_extra_fields_allowed(self) -> None:
        """Dynamic schema columns are accepted (extra=allow)."""
        crit = ResolutionCriterion.model_validate(
            {"phone": "+19259998806", "mrr": 500, "stripe_id": "cus_abc123"}
        )
        assert crit.phone == "+19259998806"
        # Extra fields accessible via model_extra
        assert crit.model_extra is not None
        assert crit.model_extra["mrr"] == 500
        assert crit.model_extra["stripe_id"] == "cus_abc123"

    def test_vertical_field(self) -> None:
        """vertical field works for scope narrowing."""
        crit = ResolutionCriterion(phone="+19259998806", vertical="chiro")
        assert crit.vertical == "chiro"

    def test_offer_fields(self) -> None:
        """offer_id and offer_name are typed optional fields."""
        crit = ResolutionCriterion(offer_id="OFF-0042", offer_name="Free Consultation")
        assert crit.offer_id == "OFF-0042"
        assert crit.offer_name == "Free Consultation"

    def test_contact_fields(self) -> None:
        """contact_email and contact_phone are typed optional fields."""
        crit = ResolutionCriterion(
            contact_email="jane@acme.com", contact_phone="+14155551234"
        )
        assert crit.contact_email == "jane@acme.com"
        assert crit.contact_phone == "+14155551234"


# ---------------------------------------------------------------------------
# ResolutionRequest
# ---------------------------------------------------------------------------


class TestResolutionRequest:
    """Tests for ResolutionRequest model."""

    def test_minimal_valid(self) -> None:
        """Request with one criterion and defaults."""
        req = ResolutionRequest(criteria=[ResolutionCriterion(phone="+19259998806")])
        assert len(req.criteria) == 1
        assert req.fields is None
        assert req.active_only is True  # FR-1 intentional default

    def test_active_only_default_true(self) -> None:
        """active_only defaults to True per FR-1 / SD-1."""
        req = ResolutionRequest(criteria=[ResolutionCriterion()])
        assert req.active_only is True

    def test_active_only_can_be_overridden(self) -> None:
        """active_only can be explicitly set to False."""
        req = ResolutionRequest(criteria=[ResolutionCriterion()], active_only=False)
        assert req.active_only is False

    def test_batch_size_at_limit(self) -> None:
        """Exactly 1000 criteria is accepted."""
        criteria = [ResolutionCriterion() for _ in range(1000)]
        req = ResolutionRequest(criteria=criteria)
        assert len(req.criteria) == 1000

    def test_batch_size_over_limit_rejected(self) -> None:
        """More than 1000 criteria raises ValueError."""
        criteria = [ResolutionCriterion() for _ in range(1001)]
        with pytest.raises(ValidationError) as exc_info:
            ResolutionRequest(criteria=criteria)
        # Verify the error message references the limit
        error_text = str(exc_info.value)
        assert "1001" in error_text
        assert "1000" in error_text

    def test_empty_criteria_list(self) -> None:
        """Empty criteria list is valid (no minimum enforced)."""
        req = ResolutionRequest(criteria=[])
        assert len(req.criteria) == 0

    def test_fields_filtering(self) -> None:
        """Optional fields list for field selection."""
        req = ResolutionRequest(
            criteria=[ResolutionCriterion()],
            fields=["mrr", "weekly_ad_spend"],
        )
        assert req.fields == ["mrr", "weekly_ad_spend"]

    def test_extra_fields_rejected(self) -> None:
        """Request-level extra fields are rejected (extra=forbid)."""
        with pytest.raises(ValidationError):
            ResolutionRequest.model_validate({"criteria": [], "bogus_field": True})


# ---------------------------------------------------------------------------
# ResolutionResultModel
# ---------------------------------------------------------------------------


class TestResolutionResultModel:
    """Tests for ResolutionResultModel."""

    def test_minimal_not_found(self) -> None:
        """Unresolved result with gid=None."""
        result = ResolutionResultModel(gid=None)
        assert result.gid is None
        assert result.gids is None
        assert result.match_count == 0
        assert result.error is None
        assert result.data is None
        assert result.status is None
        assert result.total_match_count is None

    def test_single_match(self) -> None:
        """Single match result."""
        result = ResolutionResultModel(
            gid="123456",
            gids=["123456"],
            match_count=1,
            status=["active"],
            total_match_count=1,
        )
        assert result.gid == "123456"
        assert result.gids == ["123456"]
        assert result.match_count == 1
        assert result.status == ["active"]

    def test_multi_match(self) -> None:
        """Multiple matches with parallel status list."""
        result = ResolutionResultModel(
            gid="111",
            gids=["111", "222", "333"],
            match_count=3,
            status=["active", "inactive", None],
            total_match_count=5,
        )
        assert len(result.gids) == 3
        assert result.total_match_count == 5
        assert result.status[2] is None  # FR-7: None when no classifier

    def test_with_enriched_data(self) -> None:
        """Result with enriched field data."""
        result = ResolutionResultModel(
            gid="123",
            gids=["123"],
            match_count=1,
            data=[{"mrr": 500, "vertical": "chiro"}],
        )
        assert result.data is not None
        assert result.data[0]["mrr"] == 500

    def test_error_result(self) -> None:
        """Result with error code."""
        result = ResolutionResultModel(gid=None, error="SCHEMA_MISMATCH")
        assert result.error == "SCHEMA_MISMATCH"

    def test_extra_fields_rejected(self) -> None:
        """ResolutionResultModel rejects extra fields (extra=forbid)."""
        with pytest.raises(ValidationError):
            ResolutionResultModel.model_validate({"gid": "123", "bogus": True})


# ---------------------------------------------------------------------------
# ResolutionMeta
# ---------------------------------------------------------------------------


class TestResolutionMeta:
    """Tests for ResolutionMeta model."""

    def test_valid_meta(self) -> None:
        """Fully populated meta."""
        meta = ResolutionMeta(
            resolved_count=8,
            unresolved_count=2,
            entity_type="unit",
            project_gid="1111111111111111",
            available_fields=["mrr", "vertical"],
            criteria_schema=["phone", "vertical"],
        )
        assert meta.resolved_count == 8
        assert meta.unresolved_count == 2
        assert meta.entity_type == "unit"
        assert "mrr" in meta.available_fields

    def test_lists_default_empty(self) -> None:
        """available_fields and criteria_schema default to empty lists."""
        meta = ResolutionMeta(
            resolved_count=0,
            unresolved_count=0,
            entity_type="unit",
            project_gid="P123",
        )
        assert meta.available_fields == []
        assert meta.criteria_schema == []

    def test_extra_fields_rejected(self) -> None:
        """ResolutionMeta rejects extra fields (extra=forbid)."""
        with pytest.raises(ValidationError):
            ResolutionMeta.model_validate(
                {
                    "resolved_count": 0,
                    "unresolved_count": 0,
                    "entity_type": "unit",
                    "project_gid": "P1",
                    "unexpected": True,
                }
            )


# ---------------------------------------------------------------------------
# ResolutionResponse
# ---------------------------------------------------------------------------


class TestResolutionResponse:
    """Tests for ResolutionResponse model."""

    def test_valid_response(self) -> None:
        """Full response with results and meta."""
        resp = ResolutionResponse(
            results=[
                ResolutionResultModel(gid="123", match_count=1),
                ResolutionResultModel(gid=None, match_count=0),
            ],
            meta=ResolutionMeta(
                resolved_count=1,
                unresolved_count=1,
                entity_type="unit",
                project_gid="P123",
            ),
        )
        assert len(resp.results) == 2
        assert resp.meta.resolved_count == 1

    def test_empty_results(self) -> None:
        """Response with empty results list."""
        resp = ResolutionResponse(
            results=[],
            meta=ResolutionMeta(
                resolved_count=0,
                unresolved_count=0,
                entity_type="unit",
                project_gid="P123",
            ),
        )
        assert len(resp.results) == 0

    def test_extra_fields_rejected(self) -> None:
        """ResolutionResponse rejects extra fields (extra=forbid)."""
        with pytest.raises(ValidationError):
            ResolutionResponse.model_validate(
                {
                    "results": [],
                    "meta": {
                        "resolved_count": 0,
                        "unresolved_count": 0,
                        "entity_type": "unit",
                        "project_gid": "P1",
                    },
                    "extra": True,
                }
            )

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate preserves structure."""
        resp = ResolutionResponse(
            results=[
                ResolutionResultModel(
                    gid="123",
                    gids=["123"],
                    match_count=1,
                    status=["active"],
                ),
            ],
            meta=ResolutionMeta(
                resolved_count=1,
                unresolved_count=0,
                entity_type="unit",
                project_gid="P123",
                available_fields=["mrr"],
            ),
        )
        restored = ResolutionResponse.model_validate(resp.model_dump())
        assert restored.results[0].gid == "123"
        assert restored.results[0].status == ["active"]
        assert restored.meta.available_fields == ["mrr"]
