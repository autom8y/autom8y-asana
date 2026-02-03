"""Query engine error hierarchy.

Each error carries a structured error_code and serializes to a JSON-compatible
dict for HTTP response bodies.

Error codes:
- QUERY_TOO_COMPLEX: Predicate tree exceeds max depth.
- UNKNOWN_FIELD: Referenced field not in entity schema.
- INVALID_OPERATOR: Operator incompatible with field dtype.
- COERCION_FAILED: Value cannot be coerced to field dtype.
- UNKNOWN_SECTION: Section name cannot be resolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QueryEngineError(Exception):
    """Base error for all query engine domain errors.

    Subclasses define the error_code and HTTP status mapping.
    """

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict for HTTP response."""
        raise NotImplementedError


@dataclass
class QueryTooComplexError(QueryEngineError):
    """Predicate tree exceeds max depth."""

    depth: int
    max_depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "QUERY_TOO_COMPLEX",
            "message": (
                f"Predicate tree depth {self.depth} exceeds maximum of {self.max_depth}"
            ),
            "max_depth": self.max_depth,
        }


@dataclass
class UnknownFieldError(QueryEngineError):
    """Referenced field not in entity schema."""

    field: str
    available: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "UNKNOWN_FIELD",
            "message": f"Unknown field: {self.field}",
            "available_fields": sorted(self.available),
        }


@dataclass
class InvalidOperatorError(QueryEngineError):
    """Operator incompatible with field dtype."""

    field: str
    dtype: str
    op: str
    allowed: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "INVALID_OPERATOR",
            "message": (
                f"Operator '{self.op}' not supported for "
                f"{self.dtype} field '{self.field}'"
            ),
            "field": self.field,
            "field_dtype": self.dtype,
            "operator": self.op,
            "supported_operators": self.allowed,
        }


@dataclass
class CoercionError(QueryEngineError):
    """Value cannot be coerced to field dtype."""

    field: str
    dtype: str
    value: Any
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "COERCION_FAILED",
            "message": (
                f"Cannot coerce {self.value!r} to {self.dtype} for field '{self.field}'"
            ),
            "field": self.field,
            "field_dtype": self.dtype,
            "value": self.value,
        }


@dataclass
class UnknownSectionError(QueryEngineError):
    """Section name cannot be resolved."""

    section: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "UNKNOWN_SECTION",
            "message": f"Unknown section: '{self.section}'",
            "section": self.section,
        }


@dataclass
class AggregationError(QueryEngineError):
    """Aggregation-specific error (dtype mismatch, invalid group_by, etc.)."""

    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "AGGREGATION_ERROR",
            "message": self.message,
        }


@dataclass
class AggregateGroupLimitError(QueryEngineError):
    """Aggregation produced too many groups."""

    group_count: int
    max_groups: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "TOO_MANY_GROUPS",
            "message": (
                f"Aggregation produced {self.group_count} groups, "
                f"exceeding maximum of {self.max_groups}"
            ),
            "group_count": self.group_count,
            "max_groups": self.max_groups,
        }


@dataclass
class JoinError(QueryEngineError):
    """Cross-entity join failed."""

    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": "JOIN_ERROR",
            "message": self.message,
        }
