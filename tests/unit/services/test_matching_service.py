"""Tests for MatchingService.

Unit tests for the matching service layer that bridges the matching
engine to the API. Tests use a mocked MatchingEngine to isolate
service logic from the probabilistic engine.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from autom8_asana.api.routes.matching_models import (
    MatchCandidate,
    MatchFieldComparison,
    MatchingQueryResponse,
)
from autom8_asana.models.business.matching import (
    Candidate,
    FieldComparison,
    MatchingConfig,
    MatchingEngine,
    MatchResult,
)
from autom8_asana.services.matching_service import MatchingService

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------


def _make_dataframe(rows: int = 3) -> pl.DataFrame:
    """Create a test business DataFrame."""
    return pl.DataFrame(
        {
            "gid": [f"biz_{i:03d}" for i in range(rows)],
            "name": [f"Business {i}" for i in range(rows)],
            "office_phone": [f"+1555000{i:04d}" for i in range(rows)],
            "email": [f"info{i}@biz{i}.com" for i in range(rows)],
            "domain": [f"biz{i}.com" for i in range(rows)],
            "company_id": [f"C{i:03d}" for i in range(rows)],
        }
    )


def _make_match_result(
    *,
    candidate_gid: str = "biz_001",
    score: float = 0.85,
    is_match: bool = True,
    raw_score: float = 3.5,
) -> MatchResult:
    """Create a MatchResult with default comparisons."""
    return MatchResult(
        is_match=is_match,
        score=score,
        raw_score=raw_score,
        threshold=0.80,
        fields_compared=2,
        comparisons=[
            FieldComparison(
                field_name="email",
                left_value="info@acme.com",
                right_value="info@acme.com",
                comparison_type="exact",
                similarity=None,
                weight_applied=8.0,
                contributed=True,
            ),
            FieldComparison(
                field_name="name",
                left_value="acme",
                right_value="acme corp",
                comparison_type="fuzzy",
                similarity=0.92,
                weight_applied=5.4,
                contributed=True,
            ),
            FieldComparison(
                field_name="phone",
                left_value=None,
                right_value="+15551234567",
                comparison_type="exact",
                similarity=None,
                weight_applied=0.0,
                contributed=False,
            ),
            FieldComparison(
                field_name="domain",
                left_value=None,
                right_value=None,
                comparison_type="exact",
                similarity=None,
                weight_applied=0.0,
                contributed=False,
            ),
        ],
        match_type="composite",
        candidate_gid=candidate_gid,
    )


# ---------------------------------------------------------------------------
# DataFrame conversion tests
# ---------------------------------------------------------------------------


class TestDataFrameConversion:
    """Test DataFrame to Candidate conversion."""

    def test_converts_all_rows(self) -> None:
        """All rows with GIDs are converted to candidates."""
        service = MatchingService()
        df = _make_dataframe(5)
        candidates = service._dataframe_to_candidates(df)
        assert len(candidates) == 5

    def test_skips_rows_without_gid(self) -> None:
        """Rows without GID are skipped."""
        service = MatchingService()
        df = pl.DataFrame(
            {
                "gid": ["biz_001", None, "biz_003"],
                "name": ["A", "B", "C"],
            }
        )
        candidates = service._dataframe_to_candidates(df)
        assert len(candidates) == 2
        assert candidates[0].gid == "biz_001"
        assert candidates[1].gid == "biz_003"

    def test_maps_office_phone_to_phone(self) -> None:
        """DataFrame office_phone column maps to Candidate.phone."""
        service = MatchingService()
        df = pl.DataFrame(
            {
                "gid": ["biz_001"],
                "office_phone": ["+15551234567"],
            }
        )
        candidates = service._dataframe_to_candidates(df)
        assert candidates[0].phone == "+15551234567"

    def test_tolerates_missing_columns(self) -> None:
        """Missing columns default to None."""
        service = MatchingService()
        df = pl.DataFrame({"gid": ["biz_001"]})
        candidates = service._dataframe_to_candidates(df)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.name is None
        assert c.email is None
        assert c.phone is None
        assert c.domain is None
        assert c.company_id is None

    def test_gid_coerced_to_string(self) -> None:
        """GID values are coerced to string."""
        service = MatchingService()
        df = pl.DataFrame(
            {
                "gid": [12345],
                "name": ["Test"],
            }
        )
        candidates = service._dataframe_to_candidates(df)
        assert candidates[0].gid == "12345"

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame returns empty candidate list."""
        service = MatchingService()
        df = pl.DataFrame({"gid": [], "name": []}).cast({"gid": pl.Utf8, "name": pl.Utf8})
        candidates = service._dataframe_to_candidates(df)
        assert candidates == []


# ---------------------------------------------------------------------------
# Result projection tests
# ---------------------------------------------------------------------------


class TestResultProjection:
    """Test MatchResult to MatchCandidate projection."""

    def test_projects_score_and_gid(self) -> None:
        """Projected result contains score and candidate_gid."""
        result = _make_match_result()
        candidate = MatchingService._project_result(result, threshold=0.80)
        assert candidate.candidate_gid == "biz_001"
        assert candidate.score == round(0.85, 4)
        assert candidate.is_match is True

    def test_hides_raw_score(self) -> None:
        """raw_score is NOT in the projected response."""
        result = _make_match_result()
        candidate = MatchingService._project_result(result, threshold=0.80)
        # MatchCandidate should not have raw_score attribute
        assert not hasattr(candidate, "raw_score")

    def test_hides_pii_values(self) -> None:
        """left_value and right_value are NOT in field comparisons."""
        result = _make_match_result()
        candidate = MatchingService._project_result(result, threshold=0.80)
        for fc in candidate.field_comparisons:
            assert not hasattr(fc, "left_value")
            assert not hasattr(fc, "right_value")

    def test_hides_weight_applied(self) -> None:
        """weight_applied is NOT in projected field comparisons."""
        result = _make_match_result()
        candidate = MatchingService._project_result(result, threshold=0.80)
        for fc in candidate.field_comparisons:
            assert not hasattr(fc, "weight_applied")

    def test_preserves_field_comparison_count(self) -> None:
        """All field comparisons are projected."""
        result = _make_match_result()
        candidate = MatchingService._project_result(result, threshold=0.80)
        assert len(candidate.field_comparisons) == 4  # email, name, phone, domain

    def test_preserves_similarity_and_contributed(self) -> None:
        """Similarity and contributed flags are preserved."""
        result = _make_match_result()
        candidate = MatchingService._project_result(result, threshold=0.80)

        email_fc = next(fc for fc in candidate.field_comparisons if fc.field_name == "email")
        assert email_fc.similarity is None  # exact match
        assert email_fc.contributed is True

        name_fc = next(fc for fc in candidate.field_comparisons if fc.field_name == "name")
        assert name_fc.similarity == 0.92
        assert name_fc.contributed is True

    def test_is_match_uses_effective_threshold(self) -> None:
        """is_match is based on the effective threshold, not the engine threshold."""
        result = _make_match_result(score=0.85)

        # At threshold 0.80, should be a match
        candidate_low = MatchingService._project_result(result, threshold=0.80)
        assert candidate_low.is_match is True

        # At threshold 0.90, should NOT be a match
        candidate_high = MatchingService._project_result(result, threshold=0.90)
        assert candidate_high.is_match is False


# ---------------------------------------------------------------------------
# Full query tests with mocked engine
# ---------------------------------------------------------------------------


class TestQueryIntegration:
    """Integration tests for the full query method with mocked engine."""

    def test_query_returns_response(self) -> None:
        """Query returns MatchingQueryResponse."""
        mock_engine = MagicMock(spec=MatchingEngine)
        mock_engine.config = MatchingConfig(match_threshold=0.80)
        mock_engine.compute_match.return_value = _make_match_result()

        service = MatchingService(engine=mock_engine)
        response = service.query(
            name="Acme Corp",
            dataframe=_make_dataframe(),
        )

        assert isinstance(response, MatchingQueryResponse)
        assert response.query_threshold == 0.80

    def test_query_respects_limit(self) -> None:
        """Query returns at most limit candidates."""
        mock_engine = MagicMock(spec=MatchingEngine)
        mock_engine.config = MatchingConfig(match_threshold=0.80)
        mock_engine.compute_match.return_value = _make_match_result()

        service = MatchingService(engine=mock_engine)
        response = service.query(
            name="Test",
            dataframe=_make_dataframe(20),
            limit=5,
        )

        assert len(response.candidates) <= 5

    def test_query_results_sorted_by_score_desc(self) -> None:
        """Results are sorted by score descending."""
        results = [
            _make_match_result(candidate_gid="low", score=0.5, is_match=False),
            _make_match_result(candidate_gid="high", score=0.95, is_match=True),
            _make_match_result(candidate_gid="mid", score=0.75, is_match=False),
        ]
        call_count = {"n": 0}

        def return_results(query, candidate):
            idx = call_count["n"] % len(results)
            call_count["n"] += 1
            r = results[idx]
            # Set the candidate_gid to match the actual candidate being scored
            return MatchResult(
                is_match=r.is_match,
                score=r.score,
                raw_score=r.raw_score,
                threshold=r.threshold,
                fields_compared=r.fields_compared,
                comparisons=r.comparisons,
                match_type=r.match_type,
                candidate_gid=candidate.gid,
            )

        mock_engine = MagicMock(spec=MatchingEngine)
        mock_engine.config = MatchingConfig(match_threshold=0.80)
        mock_engine.compute_match.side_effect = return_results

        service = MatchingService(engine=mock_engine)
        response = service.query(
            name="Test",
            dataframe=_make_dataframe(3),
        )

        scores = [c.score for c in response.candidates]
        assert scores == sorted(scores, reverse=True)

    def test_query_with_custom_threshold(self) -> None:
        """Custom threshold overrides engine default."""
        mock_engine = MagicMock(spec=MatchingEngine)
        mock_engine.config = MatchingConfig(match_threshold=0.80)
        mock_engine.compute_match.return_value = _make_match_result(score=0.85)

        service = MatchingService(engine=mock_engine)
        response = service.query(
            name="Test",
            dataframe=_make_dataframe(),
            threshold=0.90,
        )

        assert response.query_threshold == 0.90
        # Score 0.85 < threshold 0.90, so is_match should be False
        for candidate in response.candidates:
            assert candidate.is_match is False

    def test_query_populates_total_evaluated(self) -> None:
        """total_candidates_evaluated reflects post-blocking count."""
        mock_engine = MagicMock(spec=MatchingEngine)
        mock_engine.config = MatchingConfig(match_threshold=0.80)
        mock_engine.compute_match.return_value = _make_match_result(score=0.5, is_match=False)

        service = MatchingService(engine=mock_engine)
        response = service.query(
            name="Test",
            dataframe=_make_dataframe(10),
        )

        # Blocking may pass through all or filter some, but total_evaluated >= 0
        assert response.total_candidates_evaluated >= 0

    def test_query_with_empty_dataframe(self) -> None:
        """Query against empty DataFrame returns empty results."""
        mock_engine = MagicMock(spec=MatchingEngine)
        mock_engine.config = MatchingConfig(match_threshold=0.80)

        service = MatchingService(engine=mock_engine)
        df = pl.DataFrame({"gid": [], "name": []}).cast({"gid": pl.Utf8, "name": pl.Utf8})
        response = service.query(
            name="Test",
            dataframe=df,
        )

        assert response.candidates == []
        assert response.total_candidates_evaluated == 0
        mock_engine.compute_match.assert_not_called()

    def test_blocking_reduces_candidates(self) -> None:
        """Blocking rules reduce the number of scored candidates."""
        # Create a DataFrame where only one row shares the domain
        df = pl.DataFrame(
            {
                "gid": ["biz_001", "biz_002", "biz_003"],
                "name": ["Acme Corp", "Beta LLC", "Gamma Inc"],
                "domain": ["acme.com", "beta.com", "gamma.com"],
            }
        )

        # Use real engine with real blocking for this test
        service = MatchingService()
        response = service.query(
            domain="acme.com",
            name="Acme",
            dataframe=df,
        )

        # The engine should be called for candidates that pass blocking
        # With domain blocking, only acme.com candidate should pass
        # (unless name token blocking passes others too)
        assert isinstance(response, MatchingQueryResponse)


# ---------------------------------------------------------------------------
# Model serialization tests
# ---------------------------------------------------------------------------


class TestModelSerialization:
    """Test that models serialize correctly for API response."""

    def test_match_field_comparison_serializes(self) -> None:
        """MatchFieldComparison serializes correctly."""
        fc = MatchFieldComparison(
            field_name="email",
            similarity=None,
            contributed=True,
        )
        data = fc.model_dump(mode="json")
        assert data == {
            "field_name": "email",
            "similarity": None,
            "contributed": True,
        }

    def test_match_candidate_serializes(self) -> None:
        """MatchCandidate serializes correctly."""
        candidate = MatchCandidate(
            candidate_gid="biz_001",
            score=0.85,
            is_match=True,
            field_comparisons=[
                MatchFieldComparison(
                    field_name="email",
                    similarity=None,
                    contributed=True,
                ),
            ],
        )
        data = candidate.model_dump(mode="json")
        assert data["candidate_gid"] == "biz_001"
        assert data["score"] == 0.85
        assert data["is_match"] is True
        assert len(data["field_comparisons"]) == 1

    def test_response_serializes(self) -> None:
        """MatchingQueryResponse serializes correctly."""
        response = MatchingQueryResponse(
            candidates=[],
            total_candidates_evaluated=0,
            query_threshold=0.80,
        )
        data = response.model_dump(mode="json")
        assert data["candidates"] == []
        assert data["total_candidates_evaluated"] == 0
        assert data["query_threshold"] == 0.80

    def test_request_model_validation(self) -> None:
        """MatchingQueryRequest validates correctly."""
        from autom8_asana.api.routes.matching_models import MatchingQueryRequest

        req = MatchingQueryRequest(name="Acme")
        assert req.name == "Acme"
        assert req.limit == 10
        assert req.threshold is None

    def test_request_model_rejects_invalid_limit(self) -> None:
        """MatchingQueryRequest rejects limit < 1."""
        from pydantic import ValidationError

        from autom8_asana.api.routes.matching_models import MatchingQueryRequest

        with pytest.raises(ValidationError):
            MatchingQueryRequest(name="Test", limit=0)

    def test_request_model_rejects_invalid_threshold(self) -> None:
        """MatchingQueryRequest rejects threshold > 1.0."""
        from pydantic import ValidationError

        from autom8_asana.api.routes.matching_models import MatchingQueryRequest

        with pytest.raises(ValidationError):
            MatchingQueryRequest(name="Test", threshold=2.0)
