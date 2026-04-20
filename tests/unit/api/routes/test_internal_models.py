"""Tests for internal route models.

Covers: ServiceClaims model from internal.py.

Focus: required fields, optional scope, serialization.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.api.routes.internal import ServiceClaims

# ---------------------------------------------------------------------------
# ServiceClaims
# ---------------------------------------------------------------------------


class TestServiceClaims:
    """Tests for ServiceClaims model."""

    def test_valid_with_all_fields(self) -> None:
        """ServiceClaims with all fields populated."""
        claims = ServiceClaims(
            sub="service-abc",
            service_name="autom8y-google",
            scope="multi-tenant",
        )
        assert claims.sub == "service-abc"
        assert claims.service_name == "autom8y-google"
        assert claims.scope == "multi-tenant"

    def test_scope_optional(self) -> None:
        """scope defaults to None."""
        claims = ServiceClaims(sub="svc-1", service_name="autom8y-data")
        assert claims.scope is None

    def test_missing_sub_raises(self) -> None:
        """Missing sub raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceClaims(service_name="test")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("sub",) for e in errors)

    def test_missing_service_name_raises(self) -> None:
        """Missing service_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceClaims(sub="svc-1")  # type: ignore[call-arg]
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("service_name",) for e in errors)

    def test_model_dump(self) -> None:
        """model_dump produces expected dict shape."""
        claims = ServiceClaims(sub="svc-1", service_name="autom8y-google", scope="read")
        dumped = claims.model_dump()
        assert dumped == {
            "sub": "svc-1",
            "service_name": "autom8y-google",
            "scope": "read",
            # permissions field added per Bedrock W4C-P3 / SEC-DT-10 (super-admin
            # cache-refresh gating); default empty list when ServiceAccount has
            # no scopes populated.
            "permissions": [],
        }

    def test_model_dump_exclude_none(self) -> None:
        """model_dump with exclude_none omits null scope."""
        claims = ServiceClaims(sub="svc-1", service_name="test-svc")
        dumped = claims.model_dump(exclude_none=True)
        assert "scope" not in dumped

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip."""
        claims = ServiceClaims(sub="svc-1", service_name="autom8y-asana", scope="admin")
        restored = ServiceClaims.model_validate(claims.model_dump())
        assert restored.sub == claims.sub
        assert restored.service_name == claims.service_name
        assert restored.scope == claims.scope
