"""Tests for GidPushResponse contract model (WS-1 ASN-7).

Validates:
- Valid response with both fields
- Missing fields default to None
- Extra fields are silently ignored (extra="ignore")
"""

from __future__ import annotations

from autom8_asana.services.gid_push import GidPushResponse


class TestGidPushResponse:
    """ASN-7: POST /api/v1/gid-mappings/sync response."""

    def test_valid_response_both_fields(self):
        resp = GidPushResponse.model_validate({"accepted": 10, "replaced": 3})
        assert resp.accepted == 10
        assert resp.replaced == 3

    def test_missing_fields_default_to_none(self):
        resp = GidPushResponse.model_validate({})
        assert resp.accepted is None
        assert resp.replaced is None

    def test_partial_fields(self):
        resp = GidPushResponse.model_validate({"accepted": 5})
        assert resp.accepted == 5
        assert resp.replaced is None

    def test_extra_fields_ignored(self):
        resp = GidPushResponse.model_validate(
            {
                "accepted": 7,
                "replaced": 2,
                "timestamp": "2026-02-22T12:00:00",
                "unknown": True,
            }
        )
        assert resp.accepted == 7
        assert resp.replaced == 2
        assert not hasattr(resp, "timestamp")
        assert not hasattr(resp, "unknown")

    def test_null_fields(self):
        resp = GidPushResponse.model_validate({"accepted": None, "replaced": None})
        assert resp.accepted is None
        assert resp.replaced is None

    def test_string_coercion_to_int(self):
        """Pydantic v2 coerces compatible types by default."""
        resp = GidPushResponse.model_validate({"accepted": "12", "replaced": "0"})
        assert resp.accepted == 12
        assert resp.replaced == 0
