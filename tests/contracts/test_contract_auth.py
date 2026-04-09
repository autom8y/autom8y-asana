"""Consumer-side JWT claims contract test for autom8y-asana.

This test asserts that the autom8y-auth SDK's ServiceClaims type
contains the fields this service depends on. If a field is renamed
or removed in the SDK, this test fails in THIS service's CI before
the change is consumed.

Fields asserted are derived from actual usage in:
  - auth/jwt_validator.py: claims.service_name, claims.scope
  - api/dependencies.py: claims.service_name, claims.scope
  - api/routes/internal.py: claims.sub, claims.service_name, claims.scope
  - api/routes/*.py: claims.service_name (caller_service logging)

autom8y-asana exclusively uses ServiceClaims. All inbound requests
are S2S (service-to-service). The three critical fields are:
sub, service_name (property), and scope.

SP-L3-4 Boundary A: ServiceClaims -> autom8y-asana
"""

from __future__ import annotations

from typing import get_type_hints

from autom8y_auth import BaseClaims, ServiceClaims


class TestServiceClaimsContract:
    """Fields autom8y-asana reads from ServiceClaims."""

    def test_service_claims_has_sub(self) -> None:
        hints = get_type_hints(ServiceClaims)
        assert "sub" in hints, "asana uses claims.sub for caller identity"

    def test_service_claims_has_scope(self) -> None:
        hints = get_type_hints(ServiceClaims)
        assert "scope" in hints, "asana uses claims.scope for access control"

    def test_service_claims_has_service_name_property(self) -> None:
        """asana uses claims.service_name extensively for caller logging."""
        assert hasattr(ServiceClaims, "service_name"), (
            "asana depends on ServiceClaims.service_name property"
        )

    def test_service_claims_has_has_scope_method(self) -> None:
        """asana may use has_scope for scope validation."""
        assert hasattr(ServiceClaims, "has_scope"), (
            "asana depends on ServiceClaims.has_scope() method"
        )

    def test_service_claims_has_permissions(self) -> None:
        hints = get_type_hints(ServiceClaims)
        assert "permissions" in hints, "asana checks service permissions"


class TestBaseClaimsContract:
    """Structural fields inherited from BaseClaims."""

    def test_base_claims_has_sub(self) -> None:
        hints = get_type_hints(BaseClaims)
        assert "sub" in hints

    def test_base_claims_has_iss(self) -> None:
        hints = get_type_hints(BaseClaims)
        assert "iss" in hints

    def test_base_claims_has_exp(self) -> None:
        hints = get_type_hints(BaseClaims)
        assert "exp" in hints


class TestClaimsInheritance:
    """Structural contract: claims type hierarchy is intact."""

    def test_service_claims_extends_base(self) -> None:
        assert issubclass(ServiceClaims, BaseClaims)
