"""Tests for matching query route models.

Covers: MatchingQueryRequest, MatchFieldComparison,
MatchCandidate, MatchingQueryResponse.

Focus: field constraints (ge/le), frozen immutability, nested
list composition, boundary values for limit and threshold.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from autom8_asana.api.routes.matching_models import (
    MatchCandidate,
    MatchFieldComparison,
    MatchingQueryRequest,
    MatchingQueryResponse,
)

# ---------------------------------------------------------------------------
# MatchingQueryRequest
# ---------------------------------------------------------------------------


class TestMatchingQueryRequest:
    """Tests for MatchingQueryRequest model."""

    def test_all_identity_fields_optional(self) -> None:
        """All identity fields default to None; limit has default."""
        req = MatchingQueryRequest()
        assert req.name is None
        assert req.phone is None
        assert req.email is None
        assert req.domain is None
        assert req.limit == 10
        assert req.threshold is None

    def test_with_name(self) -> None:
        """Request with name for fuzzy matching."""
        req = MatchingQueryRequest(name="Acme Chiropractic")
        assert req.name == "Acme Chiropractic"

    def test_with_phone(self) -> None:
        """Request with phone for exact matching."""
        req = MatchingQueryRequest(phone="+19259998806")
        assert req.phone == "+19259998806"

    def test_with_all_identity_fields(self) -> None:
        """Request with all identity fields populated."""
        req = MatchingQueryRequest(
            name="Acme",
            phone="+19259998806",
            email="contact@acme.com",
            domain="acme.com",
        )
        assert req.name == "Acme"
        assert req.email == "contact@acme.com"
        assert req.domain == "acme.com"

    # --- limit constraints (ge=1, le=100) ---

    def test_limit_default(self) -> None:
        """Default limit is 10."""
        req = MatchingQueryRequest()
        assert req.limit == 10

    def test_limit_minimum(self) -> None:
        """Minimum limit is 1."""
        req = MatchingQueryRequest(limit=1)
        assert req.limit == 1

    def test_limit_maximum(self) -> None:
        """Maximum limit is 100."""
        req = MatchingQueryRequest(limit=100)
        assert req.limit == 100

    def test_limit_below_minimum_rejected(self) -> None:
        """limit=0 is rejected (ge=1)."""
        with pytest.raises(ValidationError):
            MatchingQueryRequest(limit=0)

    def test_limit_above_maximum_rejected(self) -> None:
        """limit=101 is rejected (le=100)."""
        with pytest.raises(ValidationError):
            MatchingQueryRequest(limit=101)

    def test_limit_negative_rejected(self) -> None:
        """Negative limit is rejected."""
        with pytest.raises(ValidationError):
            MatchingQueryRequest(limit=-1)

    # --- threshold constraints (ge=0.0, le=1.0) ---

    def test_threshold_none_default(self) -> None:
        """threshold defaults to None (uses engine default)."""
        req = MatchingQueryRequest()
        assert req.threshold is None

    def test_threshold_zero(self) -> None:
        """threshold=0.0 is the minimum valid value."""
        req = MatchingQueryRequest(threshold=0.0)
        assert req.threshold == 0.0

    def test_threshold_one(self) -> None:
        """threshold=1.0 is the maximum valid value."""
        req = MatchingQueryRequest(threshold=1.0)
        assert req.threshold == 1.0

    def test_threshold_below_zero_rejected(self) -> None:
        """Negative threshold is rejected."""
        with pytest.raises(ValidationError):
            MatchingQueryRequest(threshold=-0.1)

    def test_threshold_above_one_rejected(self) -> None:
        """threshold > 1.0 is rejected."""
        with pytest.raises(ValidationError):
            MatchingQueryRequest(threshold=1.1)

    def test_threshold_mid_range(self) -> None:
        """Typical threshold value."""
        req = MatchingQueryRequest(threshold=0.7)
        assert req.threshold == 0.7

    # --- frozen ---

    def test_frozen(self) -> None:
        """MatchingQueryRequest is frozen."""
        req = MatchingQueryRequest(name="Acme")
        with pytest.raises(ValidationError):
            req.name = "Changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MatchFieldComparison
# ---------------------------------------------------------------------------


class TestMatchFieldComparison:
    """Tests for MatchFieldComparison model."""

    def test_fuzzy_field(self) -> None:
        """Fuzzy field with similarity score."""
        comp = MatchFieldComparison(
            field_name="name", similarity=0.92, contributed=True
        )
        assert comp.field_name == "name"
        assert comp.similarity == 0.92
        assert comp.contributed is True

    def test_exact_field_null_similarity(self) -> None:
        """Exact match field has null similarity."""
        comp = MatchFieldComparison(
            field_name="email", similarity=None, contributed=True
        )
        assert comp.similarity is None
        assert comp.contributed is True

    def test_non_contributing_field(self) -> None:
        """Field that did not contribute to score."""
        comp = MatchFieldComparison(
            field_name="domain", similarity=0.5, contributed=False
        )
        assert comp.contributed is False

    def test_frozen(self) -> None:
        """MatchFieldComparison is frozen."""
        comp = MatchFieldComparison(field_name="name", similarity=0.9, contributed=True)
        with pytest.raises(ValidationError):
            comp.contributed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MatchCandidate
# ---------------------------------------------------------------------------


class TestMatchCandidate:
    """Tests for MatchCandidate model."""

    def test_valid_candidate(self) -> None:
        """Full candidate with field comparisons."""
        candidate = MatchCandidate(
            candidate_gid="123456",
            score=0.87,
            is_match=True,
            field_comparisons=[
                MatchFieldComparison(
                    field_name="name", similarity=0.92, contributed=True
                ),
                MatchFieldComparison(
                    field_name="phone", similarity=None, contributed=True
                ),
            ],
        )
        assert candidate.candidate_gid == "123456"
        assert candidate.score == 0.87
        assert candidate.is_match is True
        assert len(candidate.field_comparisons) == 2

    def test_below_threshold_candidate(self) -> None:
        """Candidate below threshold."""
        candidate = MatchCandidate(
            candidate_gid="789",
            score=0.3,
            is_match=False,
            field_comparisons=[],
        )
        assert candidate.is_match is False

    def test_frozen(self) -> None:
        """MatchCandidate is frozen."""
        candidate = MatchCandidate(
            candidate_gid="123",
            score=0.9,
            is_match=True,
            field_comparisons=[],
        )
        with pytest.raises(ValidationError):
            candidate.score = 0.1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MatchingQueryResponse
# ---------------------------------------------------------------------------


class TestMatchingQueryResponse:
    """Tests for MatchingQueryResponse model."""

    def test_valid_response(self) -> None:
        """Full response with candidates."""
        resp = MatchingQueryResponse(
            candidates=[
                MatchCandidate(
                    candidate_gid="123",
                    score=0.95,
                    is_match=True,
                    field_comparisons=[],
                ),
                MatchCandidate(
                    candidate_gid="456",
                    score=0.72,
                    is_match=True,
                    field_comparisons=[],
                ),
            ],
            total_candidates_evaluated=150,
            query_threshold=0.7,
        )
        assert len(resp.candidates) == 2
        assert resp.total_candidates_evaluated == 150
        assert resp.query_threshold == 0.7

    def test_empty_candidates(self) -> None:
        """Response with no matches."""
        resp = MatchingQueryResponse(
            candidates=[],
            total_candidates_evaluated=100,
            query_threshold=0.7,
        )
        assert len(resp.candidates) == 0
        assert resp.total_candidates_evaluated == 100

    def test_frozen(self) -> None:
        """MatchingQueryResponse is frozen."""
        resp = MatchingQueryResponse(
            candidates=[],
            total_candidates_evaluated=0,
            query_threshold=0.5,
        )
        with pytest.raises(ValidationError):
            resp.query_threshold = 0.9  # type: ignore[misc]

    def test_serialization_round_trip(self) -> None:
        """model_dump -> model_validate round-trip."""
        resp = MatchingQueryResponse(
            candidates=[
                MatchCandidate(
                    candidate_gid="123",
                    score=0.88,
                    is_match=True,
                    field_comparisons=[
                        MatchFieldComparison(
                            field_name="name",
                            similarity=0.88,
                            contributed=True,
                        )
                    ],
                ),
            ],
            total_candidates_evaluated=50,
            query_threshold=0.6,
        )
        restored = MatchingQueryResponse.model_validate(resp.model_dump())
        assert restored.candidates[0].score == 0.88
        assert restored.candidates[0].field_comparisons[0].similarity == 0.88
        assert restored.total_candidates_evaluated == 50
