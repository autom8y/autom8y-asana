"""Pydantic models for the matching query API.

Request/response models for POST /v1/matching/query.

Security constraints (HD-01):
- Response models do NOT expose engine internals (raw_score, weights,
  normalizer configs, PII values like left_value/right_value).
- Only projected fields are included: candidate_gid, score, is_match,
  and per-field similarity + contribution flag.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------


class MatchingQueryRequest(BaseModel):
    """Business identity fields for matching query.

    At least one identity field (name, phone, email, domain) must be
    provided. The engine normalizes all fields before comparison.

    Attributes:
        name: Business name (fuzzy matched).
        phone: Business phone number (exact on normalized digits).
        email: Business email address (exact on normalized).
        domain: Website domain (exact on normalized).
        limit: Maximum match candidates to return.
        threshold: Minimum score to include in results (0.0-1.0).
    """

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(
        default=None,
        description="Business name for fuzzy matching.",
        examples=["Acme Chiropractic"],
    )
    phone: str | None = Field(
        default=None,
        description="Business phone number (any format, normalized internally).",
        examples=["+19259998806"],
    )
    email: str | None = Field(
        default=None,
        description="Business email address.",
        examples=["contact@acmechiro.com"],
    )
    domain: str | None = Field(
        default=None,
        description="Website domain (e.g., 'acme.com').",
        examples=["acmechiro.com"],
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of match candidates to return.",
        examples=[10],
    )
    threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum score to include in results. "
            "If omitted, uses the engine's configured match_threshold."
        ),
        examples=[0.7],
    )


# ---------------------------------------------------------------------------
# Response components
# ---------------------------------------------------------------------------


class MatchFieldComparison(BaseModel):
    """Per-field similarity result (projected -- no PII, no weights).

    Attributes:
        field_name: Name of the compared field.
        similarity: Similarity score (0.0-1.0) for fuzzy fields; None for exact-match fields.
        contributed: Whether this field contributed to the overall score.
    """

    model_config = ConfigDict(frozen=True)

    field_name: str = Field(
        description="Name of the compared field (e.g., 'email', 'name').",
        examples=["name"],
    )
    similarity: float | None = Field(
        description="Similarity score (0.0-1.0) for fuzzy fields; null for exact fields or missing data.",
        examples=[0.92],
    )
    contributed: bool = Field(
        description="True if this field contributed to the match score.",
        examples=[True],
    )


class MatchCandidate(BaseModel):
    """A single match candidate with score and per-field comparisons.

    Attributes:
        candidate_gid: Asana GID of the matched business entity.
        score: Normalized match probability (0.0-1.0).
        is_match: Whether the score exceeds the match threshold.
        field_comparisons: Per-field comparison details.
    """

    model_config = ConfigDict(frozen=True)

    candidate_gid: str = Field(description="Asana GID of the matched business entity.", examples=["1234567890123456"])
    score: float = Field(description="Normalized match probability (0.0-1.0).", examples=[0.87])
    is_match: bool = Field(description="True if score exceeds the match threshold.", examples=[True])
    field_comparisons: list[MatchFieldComparison] = Field(
        description="Per-field comparison results."
    )


class MatchingQueryResponse(BaseModel):
    """Response for a matching query.

    Attributes:
        candidates: Scored match candidates, ordered by score descending.
        total_candidates_evaluated: Number of candidates evaluated before filtering.
        query_threshold: Effective threshold used for is_match decisions.
    """

    model_config = ConfigDict(frozen=True)

    candidates: list[MatchCandidate] = Field(
        description="Scored match candidates, ordered by score descending."
    )
    total_candidates_evaluated: int = Field(
        description="Total candidates evaluated (before score filtering).",
        examples=[150],
    )
    query_threshold: float = Field(
        description="Effective threshold used for is_match decisions.",
        examples=[0.7],
    )


__all__ = [
    "MatchCandidate",
    "MatchFieldComparison",
    "MatchingQueryRequest",
    "MatchingQueryResponse",
]
