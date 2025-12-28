"""Data models for matching engine.

Per TDD-BusinessSeeder-v2: Models for match results and audit trails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class FieldComparison:
    """Result of comparing a single field.

    Per TDD: Per-field comparison details for audit trail.

    Attributes:
        field_name: Name of the compared field.
        left_value: Original query value (may be normalized).
        right_value: Candidate value (may be normalized).
        comparison_type: Type of comparison performed.
        similarity: Similarity score (0.0-1.0) for fuzzy, None for exact.
        weight_applied: Actual weight after TF adjustment.
        contributed: True if field contributed to score.
    """

    field_name: str
    left_value: str | None
    right_value: str | None
    comparison_type: Literal["exact", "fuzzy", "composite"]
    similarity: float | None  # 0.0-1.0 for fuzzy, None for exact
    weight_applied: float  # Actual weight after TF adjustment
    contributed: bool  # True if field contributed to score


@dataclass
class MatchResult:
    """Complete match decision with audit trail.

    Per TDD FR-S-002: Match audit logging support.

    Attributes:
        is_match: Boolean decision (opaque to API consumers).
        score: Normalized probability (0.0-1.0).
        raw_score: Sum of log-odds before conversion.
        threshold: Applied threshold for decision.
        fields_compared: Count of non-null field comparisons.
        comparisons: Per-field comparison details.
        match_type: Type of match found.
        candidate_gid: GID of matched entity (None if no match).
    """

    is_match: bool
    score: float  # Normalized 0.0-1.0
    raw_score: float  # Sum of log-odds
    threshold: float  # Applied threshold
    fields_compared: int  # Non-null comparisons
    comparisons: list[FieldComparison] = field(default_factory=list)
    match_type: Literal["exact", "composite", "no_match"] = "no_match"
    candidate_gid: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """Format for structured logging.

        Returns dict suitable for logging extra parameter.
        """
        return {
            "match_type": self.match_type,
            "score": round(self.score, 3),
            "threshold": self.threshold,
            "fields_compared": self.fields_compared,
            "weights": {
                c.field_name: c.weight_applied
                for c in self.comparisons
                if c.contributed
            },
            "candidate_gid": self.candidate_gid,
        }


@dataclass
class Candidate:
    """Candidate record for comparison.

    Extracted from SearchService results with normalized field values.

    Attributes:
        gid: Entity GID.
        name: Business name.
        email: Business email.
        phone: Business phone.
        domain: Website domain.
        city: Business city.
        state: Business state.
        zip_code: Business zip code.
        company_id: External company ID.
        normalized_name: Pre-normalized name for comparison.
        normalized_phone: Pre-normalized phone for comparison.
        normalized_email: Pre-normalized email for comparison.
    """

    gid: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    domain: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    company_id: str | None = None

    # Normalized versions (computed on construction or lazily)
    normalized_name: str | None = None
    normalized_phone: str | None = None
    normalized_email: str | None = None
