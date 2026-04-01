"""Tests for intake custom field write route models.

Covers: CustomFieldWriteRequest, CustomFieldWriteResponse.

Focus: dict value type polymorphism, frozen immutability,
error list defaults, serialization round-trips.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.api.routes.intake_custom_fields_models import (
    CustomFieldWriteRequest,
    CustomFieldWriteResponse,
)

# ---------------------------------------------------------------------------
# CustomFieldWriteRequest
# ---------------------------------------------------------------------------


class TestCustomFieldWriteRequest:
    """Tests for CustomFieldWriteRequest model."""

    def test_string_values(self) -> None:
        """Fields dict accepts string values."""
        req = CustomFieldWriteRequest(fields={"vertical": "chiro", "status": "active"})
        assert req.fields["vertical"] == "chiro"
        assert req.fields["status"] == "active"

    def test_int_values(self) -> None:
        """Fields dict accepts int values."""
        req = CustomFieldWriteRequest(fields={"num_reviews": 47})
        assert req.fields["num_reviews"] == 47

    def test_float_values(self) -> None:
        """Fields dict accepts float values."""
        req = CustomFieldWriteRequest(fields={"weekly_ad_spend": 250.50})
        assert req.fields["weekly_ad_spend"] == 250.50

    def test_bool_values(self) -> None:
        """Fields dict accepts bool values."""
        req = CustomFieldWriteRequest(fields={"is_active": True})
        assert req.fields["is_active"] is True

    def test_none_values(self) -> None:
        """Fields dict accepts None values (field clearing)."""
        req = CustomFieldWriteRequest(fields={"website": None})
        assert req.fields["website"] is None

    def test_mixed_types(self) -> None:
        """Fields dict accepts mixed value types."""
        req = CustomFieldWriteRequest(
            fields={
                "name": "Acme",
                "count": 10,
                "rate": 3.14,
                "active": False,
                "deprecated": None,
            }
        )
        assert len(req.fields) == 5
        assert isinstance(req.fields["name"], str)
        assert isinstance(req.fields["count"], int)
        assert isinstance(req.fields["rate"], float)
        assert req.fields["active"] is False
        assert req.fields["deprecated"] is None

    def test_empty_fields_dict(self) -> None:
        """Empty fields dict is valid (no-op write)."""
        req = CustomFieldWriteRequest(fields={})
        assert req.fields == {}

    def test_missing_fields_raises(self) -> None:
        """Missing fields key raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CustomFieldWriteRequest()  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("fields",) for e in errors)

    def test_frozen(self) -> None:
        """CustomFieldWriteRequest is frozen."""
        req = CustomFieldWriteRequest(fields={"x": "y"})
        with pytest.raises(ValidationError):
            req.fields = {"a": "b"}  # type: ignore[misc]

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip."""
        req = CustomFieldWriteRequest(
            fields={"name": "Acme", "count": 5, "active": True, "old": None}
        )
        restored = CustomFieldWriteRequest.model_validate(req.model_dump())
        assert restored.fields == req.fields


# ---------------------------------------------------------------------------
# CustomFieldWriteResponse
# ---------------------------------------------------------------------------


class TestCustomFieldWriteResponse:
    """Tests for CustomFieldWriteResponse model."""

    def test_success_response(self) -> None:
        """Successful write with no errors."""
        resp = CustomFieldWriteResponse(
            task_gid="T123",
            fields_written=3,
        )
        assert resp.task_gid == "T123"
        assert resp.fields_written == 3
        assert resp.errors == []  # default empty

    def test_partial_failure(self) -> None:
        """Write with some field errors."""
        resp = CustomFieldWriteResponse(
            task_gid="T123",
            fields_written=2,
            errors=["bad_field", "unknown_field"],
        )
        assert resp.fields_written == 2
        assert len(resp.errors) == 2
        assert "bad_field" in resp.errors

    def test_complete_failure(self) -> None:
        """Write where all fields fail."""
        resp = CustomFieldWriteResponse(
            task_gid="T123",
            fields_written=0,
            errors=["field_a", "field_b"],
        )
        assert resp.fields_written == 0
        assert len(resp.errors) == 2

    def test_errors_default_empty_list(self) -> None:
        """errors defaults to empty list, not None."""
        resp = CustomFieldWriteResponse(task_gid="T1", fields_written=1)
        assert resp.errors == []
        assert isinstance(resp.errors, list)

    def test_missing_task_gid_raises(self) -> None:
        """Missing task_gid raises ValidationError."""
        with pytest.raises(ValidationError):
            CustomFieldWriteResponse(fields_written=1)  # type: ignore[call-arg]

    def test_missing_fields_written_raises(self) -> None:
        """Missing fields_written raises ValidationError."""
        with pytest.raises(ValidationError):
            CustomFieldWriteResponse(task_gid="T1")  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        """CustomFieldWriteResponse is frozen."""
        resp = CustomFieldWriteResponse(task_gid="T1", fields_written=1)
        with pytest.raises(ValidationError):
            resp.task_gid = "T2"  # type: ignore[misc]

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip."""
        resp = CustomFieldWriteResponse(
            task_gid="T123",
            fields_written=2,
            errors=["x"],
        )
        restored = CustomFieldWriteResponse.model_validate(resp.model_dump())
        assert restored.task_gid == "T123"
        assert restored.errors == ["x"]
