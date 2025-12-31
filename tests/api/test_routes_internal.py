"""Tests for internal routes module (/api/v1/internal/*).

The legacy /api/v1/internal/gid-lookup endpoint has been removed.
GID resolution is now handled by the Entity Resolver at /api/v1/resolver.

This module tests the remaining authentication infrastructure that
may be used by future internal S2S endpoints.
"""

from __future__ import annotations

import pytest


class TestServiceClaimsModel:
    """Test ServiceClaims model."""

    def test_service_claims_creation(self) -> None:
        """ServiceClaims can be created with valid data."""
        from autom8_asana.api.routes.internal import ServiceClaims

        claims = ServiceClaims(
            sub="service:autom8_data",
            service_name="autom8_data",
            scope="multi-tenant",
        )

        assert claims.sub == "service:autom8_data"
        assert claims.service_name == "autom8_data"
        assert claims.scope == "multi-tenant"

    def test_service_claims_optional_scope(self) -> None:
        """ServiceClaims scope is optional."""
        from autom8_asana.api.routes.internal import ServiceClaims

        claims = ServiceClaims(
            sub="service:test",
            service_name="test",
        )

        assert claims.scope is None


class TestInternalRouterExports:
    """Test module exports are correct."""

    def test_router_exported(self) -> None:
        """Router is exported from internal module."""
        from autom8_asana.api.routes.internal import router

        assert router is not None
        assert router.prefix == "/api/v1/internal"

    def test_require_service_claims_exported(self) -> None:
        """require_service_claims dependency is exported."""
        from autom8_asana.api.routes.internal import require_service_claims

        assert callable(require_service_claims)

    def test_gid_lookup_endpoint_removed(self) -> None:
        """Verify gid-lookup endpoint is no longer registered.

        Per TDD Migration Phase 3: The /gid-lookup endpoint has been
        replaced by the Entity Resolver at /api/v1/resolver.
        """
        from autom8_asana.api.routes.internal import router

        # Get all registered routes
        route_paths = [route.path for route in router.routes]

        # Verify /gid-lookup is not in the routes
        assert "/gid-lookup" not in route_paths
        assert "/api/v1/internal/gid-lookup" not in route_paths


class TestDeprecatedImportsRemoved:
    """Test that deprecated components are no longer importable."""

    def test_gid_lookup_request_not_importable(self) -> None:
        """GidLookupRequest model has been removed."""
        with pytest.raises(ImportError):
            from autom8_asana.api.routes.internal import GidLookupRequest  # noqa: F401

    def test_gid_lookup_response_not_importable(self) -> None:
        """GidLookupResponse model has been removed."""
        with pytest.raises(ImportError):
            from autom8_asana.api.routes.internal import GidLookupResponse  # noqa: F401

    def test_phone_vertical_input_not_importable(self) -> None:
        """PhoneVerticalInput model has been removed."""
        with pytest.raises(ImportError):
            from autom8_asana.api.routes.internal import PhoneVerticalInput  # noqa: F401

    def test_resolve_gids_not_importable(self) -> None:
        """resolve_gids function has been removed."""
        with pytest.raises(ImportError):
            from autom8_asana.api.routes.internal import resolve_gids  # noqa: F401

    def test_gid_index_cache_not_importable(self) -> None:
        """_gid_index_cache has been removed."""
        with pytest.raises(ImportError):
            from autom8_asana.api.routes.internal import _gid_index_cache  # noqa: F401
