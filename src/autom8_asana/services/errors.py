"""Service-layer exception hierarchy for business logic errors.

Services raise these domain-specific exceptions instead of framework-specific
HTTP errors. Route handlers catch and map them to HTTP responses via
map_service_error().

Per TDD-SERVICE-LAYER-001 / ADR-SLE-003:
- Services must never import or raise framework-specific HTTP errors
- Each error carries structured context via to_dict()
- Error codes are stable, machine-readable identifiers

Hierarchy:
    ServiceError (base, maps to 500)
    +-- EntityNotFoundError (maps to 404)
    |   +-- UnknownEntityError (entity type not resolvable)
    |   +-- UnknownSectionError (section name not found)
    +-- EntityValidationError (maps to 400/422)
    |   +-- InvalidFieldError (field not in schema)
    |   +-- InvalidParameterError (bad request parameter)
    +-- CacheNotReadyError (maps to 503)
    +-- ServiceNotConfiguredError (maps to 503)
"""

from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    """Base class for service-layer errors.

    All service exceptions inherit from this class. Provides
    structured serialization via to_dict() for API error responses.

    Attributes:
        message: Human-readable error description.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    @property
    def error_code(self) -> str:
        """Machine-readable error code for API responses."""
        return "SERVICE_ERROR"

    @property
    def status_hint(self) -> int:
        """Suggested HTTP status code for route-layer mapping."""
        return 500

    def to_dict(self) -> dict[str, Any]:
        """Serialize to API error response format.

        Returns:
            Dictionary matching existing error response structure.
        """
        return {"error": self.error_code, "message": self.message}


# ---------------------------------------------------------------------------
# Entity Not Found (404)
# ---------------------------------------------------------------------------


class EntityNotFoundError(ServiceError):
    """Entity or resource not found. Maps to HTTP 404."""

    @property
    def status_hint(self) -> int:
        return 404


class UnknownEntityError(EntityNotFoundError):
    """Entity type not resolvable via EntityRegistry.

    Attributes:
        entity_type: The requested entity type string.
        available: Sorted list of valid entity types.
    """

    def __init__(self, entity_type: str, available: list[str]) -> None:
        self.entity_type = entity_type
        self.available = available
        super().__init__(f"Unknown entity type: {entity_type}")

    @property
    def error_code(self) -> str:
        return "UNKNOWN_ENTITY_TYPE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "available_types": self.available,
        }


class UnknownSectionError(EntityNotFoundError):
    """Section name not found in project manifest.

    Attributes:
        section_name: The requested section name.
        available_sections: Sorted list of valid section names.
    """

    def __init__(
        self, section_name: str, available_sections: list[str] | None = None
    ) -> None:
        self.section_name = section_name
        self.available_sections = available_sections or []
        super().__init__(f"Unknown section: {section_name}")

    @property
    def error_code(self) -> str:
        return "UNKNOWN_SECTION"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "error": self.error_code,
            "message": self.message,
        }
        if self.available_sections:
            result["available_sections"] = self.available_sections
        return result


# ---------------------------------------------------------------------------
# Validation Errors (400/422)
# ---------------------------------------------------------------------------


class EntityValidationError(ServiceError):
    """Validation error for entity operations. Maps to HTTP 400 or 422."""

    @property
    def status_hint(self) -> int:
        return 400


class InvalidFieldError(EntityValidationError):
    """Field not valid for entity schema. Maps to HTTP 422.

    Attributes:
        invalid_fields: Sorted list of fields that failed validation.
        available_fields: Sorted list of valid schema fields.
    """

    def __init__(
        self, invalid_fields: list[str], available_fields: list[str]
    ) -> None:
        self.invalid_fields = invalid_fields
        self.available_fields = available_fields
        super().__init__(f"Invalid fields: {invalid_fields}")

    @property
    def error_code(self) -> str:
        return "INVALID_FIELD"

    @property
    def status_hint(self) -> int:
        return 422

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code,
            "message": self.message,
            "invalid_fields": self.invalid_fields,
            "available_fields": self.available_fields,
        }


class InvalidParameterError(EntityValidationError):
    """Invalid request parameter. Maps to HTTP 400."""

    @property
    def error_code(self) -> str:
        return "INVALID_PARAMETER"


# ---------------------------------------------------------------------------
# Service Availability (503)
# ---------------------------------------------------------------------------


class CacheNotReadyError(ServiceError):
    """Cache not warmed for requested entity. Maps to HTTP 503.

    Attributes:
        entity_type: Entity type whose cache is not ready.
    """

    def __init__(self, entity_type: str | None = None) -> None:
        self.entity_type = entity_type
        msg = "Cache not warmed"
        if entity_type:
            msg = f"Cache not warmed for entity type: {entity_type}"
        super().__init__(msg)

    @property
    def error_code(self) -> str:
        return "CACHE_NOT_WARMED"

    @property
    def status_hint(self) -> int:
        return 503


class ServiceNotConfiguredError(ServiceError):
    """Required service dependency not available. Maps to HTTP 503."""

    @property
    def error_code(self) -> str:
        return "SERVICE_NOT_CONFIGURED"

    @property
    def status_hint(self) -> int:
        return 503


# ---------------------------------------------------------------------------
# Error Mapping for Route Handlers
# ---------------------------------------------------------------------------

SERVICE_ERROR_MAP: dict[type[ServiceError], int] = {
    UnknownEntityError: 404,
    UnknownSectionError: 404,
    InvalidFieldError: 422,
    InvalidParameterError: 400,
    EntityValidationError: 400,
    ServiceNotConfiguredError: 503,
    CacheNotReadyError: 503,
    EntityNotFoundError: 404,
}


def get_status_for_error(error: ServiceError) -> int:
    """Get the HTTP status code for a service error.

    Walks the MRO to find the most specific mapping.

    Args:
        error: The service error instance.

    Returns:
        HTTP status code (defaults to 500 for unmapped errors).
    """
    for cls in type(error).__mro__:
        if cls in SERVICE_ERROR_MAP:
            return SERVICE_ERROR_MAP[cls]
    return error.status_hint


__all__ = [
    "CacheNotReadyError",
    "EntityNotFoundError",
    "EntityValidationError",
    "InvalidFieldError",
    "InvalidParameterError",
    "SERVICE_ERROR_MAP",
    "ServiceError",
    "ServiceNotConfiguredError",
    "UnknownEntityError",
    "UnknownSectionError",
    "get_status_for_error",
]
