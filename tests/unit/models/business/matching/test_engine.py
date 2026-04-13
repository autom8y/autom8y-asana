"""Unit tests for MatchingEngine.

Per TDD-BusinessSeeder-v2: Tests for Fellegi-Sunter matching engine.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.matching.config import MatchingConfig
from autom8_asana.models.business.matching.engine import (
    MatchingEngine,
    log_odds_to_probability,
)
from autom8_asana.models.business.matching.models import Candidate
from autom8_asana.models.business.seeder import BusinessData


class TestLogOddsToProbability:
    """Tests for log_odds_to_probability function."""

    def test_zero_log_odds(self) -> None:
        """Zero log-odds = 0.5 probability."""
        prob = log_odds_to_probability(0.0)
        assert abs(prob - 0.5) < 0.001

    def test_positive_log_odds(self) -> None:
        """Positive log-odds > 0.5 probability."""
        prob = log_odds_to_probability(2.0)
        assert prob > 0.5
        assert prob < 1.0

    def test_negative_log_odds(self) -> None:
        """Negative log-odds < 0.5 probability."""
        prob = log_odds_to_probability(-2.0)
        assert prob < 0.5
        assert prob > 0.0

    def test_extreme_positive_capped(self) -> None:
        """Extreme positive log-odds capped near 1.0."""
        prob = log_odds_to_probability(100.0)
        assert prob > 0.999
        assert prob < 1.0

    def test_extreme_negative_capped(self) -> None:
        """Extreme negative log-odds capped near 0.0."""
        prob = log_odds_to_probability(-100.0)
        assert prob < 0.001
        assert prob > 0.0


class TestMatchingEngine:
    """Tests for MatchingEngine."""

    @pytest.fixture
    def engine(self) -> MatchingEngine:
        """Create engine with default config."""
        return MatchingEngine(MatchingConfig())

    @pytest.fixture
    def config(self) -> MatchingConfig:
        """Create default config."""
        return MatchingConfig()

    def test_compute_match_exact_email_match(self, engine: MatchingEngine) -> None:
        """Exact email match contributes to score."""
        query = BusinessData(name="Acme Corp", email="info@acme.com")
        candidate = Candidate(gid="123", name="Acme Corporation", email="info@acme.com")

        result = engine.compute_match(query, candidate)

        # Email should contribute positively
        email_comp = next(c for c in result.comparisons if c.field_name == "email")
        assert email_comp.contributed is True
        assert email_comp.weight_applied > 0
        assert email_comp.similarity == 1.0

    def test_compute_match_null_field_neutral(self, engine: MatchingEngine) -> None:
        """Null fields contribute neutral weight."""
        query = BusinessData(name="Acme Corp")
        candidate = Candidate(gid="123", name="Acme Corporation")

        result = engine.compute_match(query, candidate)

        # Email should not contribute (null on both sides)
        email_comp = next(c for c in result.comparisons if c.field_name == "email")
        assert email_comp.contributed is False
        assert email_comp.weight_applied == 0.0

    def test_compute_match_fuzzy_name(self, engine: MatchingEngine) -> None:
        """Fuzzy name matching works."""
        query = BusinessData(name="Acme Corporation")
        candidate = Candidate(gid="123", name="Acme Corp Inc")

        result = engine.compute_match(query, candidate)

        name_comp = next(c for c in result.comparisons if c.field_name == "name")
        assert name_comp.contributed is True
        assert name_comp.comparison_type == "fuzzy"
        assert name_comp.similarity is not None
        assert name_comp.similarity > 0.5

    def test_compute_match_minimum_fields_required(self, engine: MatchingEngine) -> None:
        """Minimum fields requirement enforced."""
        # Only name available - not enough for match
        query = BusinessData(name="Acme Corp")
        candidate = Candidate(gid="123", name="Acme Corp")

        result = engine.compute_match(query, candidate)

        # Even with high name similarity, min_fields=2 requires more evidence
        assert result.fields_compared == 1
        assert result.is_match is False  # Not enough fields

    def test_compute_match_threshold_applied(self) -> None:
        """Match threshold is applied."""
        config = MatchingConfig(match_threshold=0.99)  # Very strict
        engine = MatchingEngine(config)

        query = BusinessData(name="Acme Corp", email="info@acme.com")
        candidate = Candidate(gid="123", name="Acme Corporation", email="other@acme.com")

        result = engine.compute_match(query, candidate)

        # Email mismatch should push below threshold
        assert result.is_match is False or result.score < 0.99

    def test_compute_match_non_match_weights(self, engine: MatchingEngine) -> None:
        """Non-matching fields contribute negative weight."""
        query = BusinessData(name="Acme Corp", email="info@acme.com")
        candidate = Candidate(gid="123", name="Acme Corp", email="other@xyz.com")

        result = engine.compute_match(query, candidate)

        email_comp = next(c for c in result.comparisons if c.field_name == "email")
        assert email_comp.contributed is True
        assert email_comp.weight_applied < 0  # Non-match = negative weight

    def test_find_best_match_returns_highest(self, engine: MatchingEngine) -> None:
        """find_best_match returns highest scoring match."""
        query = BusinessData(name="Acme Corp", email="info@acme.com", phone="+15551234567")

        candidates = [
            Candidate(gid="1", name="Some Other Business"),
            Candidate(
                gid="2",
                name="Acme Corporation",
                email="info@acme.com",
                phone="+15551234567",
            ),
            Candidate(gid="3", name="Acme Corp", email="different@email.com"),
        ]

        result = engine.find_best_match(query, candidates)

        # Candidate 2 should be best match (exact email and phone)
        assert result is not None
        assert result.candidate_gid == "2"

    def test_find_best_match_no_candidates(self, engine: MatchingEngine) -> None:
        """find_best_match returns None for empty candidates."""
        query = BusinessData(name="Acme Corp")
        result = engine.find_best_match(query, [])
        assert result is None

    def test_find_best_match_none_above_threshold(self) -> None:
        """find_best_match returns None if none above threshold."""
        config = MatchingConfig(match_threshold=0.99, min_fields=1)
        engine = MatchingEngine(config)

        query = BusinessData(name="Acme Corp")
        candidates = [
            Candidate(gid="1", name="Completely Different Business"),
            Candidate(gid="2", name="Also Not Similar"),
        ]

        result = engine.find_best_match(query, candidates)
        assert result is None

    def test_match_result_to_log_dict(self, engine: MatchingEngine) -> None:
        """MatchResult.to_log_dict produces valid output."""
        query = BusinessData(name="Acme Corp", email="info@acme.com")
        candidate = Candidate(gid="123", name="Acme Corp", email="info@acme.com")

        result = engine.compute_match(query, candidate)
        log_dict = result.to_log_dict()

        assert "match_type" in log_dict
        assert "score" in log_dict
        assert "threshold" in log_dict
        assert "fields_compared" in log_dict
        assert "weights" in log_dict

    def test_normalize_candidate(self, engine: MatchingEngine) -> None:
        """normalize_candidate populates normalized fields."""
        candidate = Candidate(
            gid="123",
            name="ACME Corp Inc.",
            phone="(555) 123-4567",
            email="INFO@ACME.COM",
        )

        normalized = engine.normalize_candidate(candidate)

        assert normalized.normalized_name == "acme"  # Legal suffix stripped
        assert normalized.normalized_phone == "+15551234567"
        assert normalized.normalized_email == "info@acme.com"


class TestMatchingConfig:
    """Tests for MatchingConfig."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        config = MatchingConfig()

        assert config.match_threshold == 0.80
        assert config.min_fields == 2
        assert config.email_weight == 8.0
        assert config.phone_weight == 7.0
        assert config.name_weight == 6.0
        assert config.domain_weight == 5.0
        assert config.fuzzy_exact_threshold == 0.95
        assert config.tf_enabled is True

    def test_from_env(self) -> None:
        """from_env creates valid config."""
        config = MatchingConfig.from_env()
        assert config.match_threshold > 0

    def test_get_field_weight(self) -> None:
        """get_field_weight returns correct weights."""
        config = MatchingConfig()

        assert config.get_field_weight("email") == 8.0
        assert config.get_field_weight("phone") == 7.0
        assert config.get_field_weight("name") == 6.0
        assert config.get_field_weight("domain") == 5.0
        assert config.get_field_weight("unknown") == 0.0

    def test_get_nonmatch_weight(self) -> None:
        """get_nonmatch_weight returns correct weights."""
        config = MatchingConfig()

        assert config.get_nonmatch_weight("email") == -4.0
        assert config.get_nonmatch_weight("phone") == -4.0
        assert config.get_nonmatch_weight("name") == -3.0
        assert config.get_nonmatch_weight("unknown") == 0.0

    def test_custom_values(self) -> None:
        """Custom values override defaults."""
        config = MatchingConfig(
            match_threshold=0.90,
            min_fields=3,
            email_weight=10.0,
        )

        assert config.match_threshold == 0.90
        assert config.min_fields == 3
        assert config.email_weight == 10.0
        assert config.phone_weight == 7.0  # Still default


class TestIntegrationScenarios:
    """Integration test scenarios from PRD edge cases."""

    @pytest.fixture
    def engine(self) -> MatchingEngine:
        """Create engine with default config."""
        return MatchingEngine(MatchingConfig())

    def test_typo_in_company_name(self, engine: MatchingEngine) -> None:
        """Typo in company name still matches with corroborating fields."""
        query = BusinessData(
            name="Acme Coporation",  # Typo
            email="info@acme.com",
            phone="+15551234567",
        )
        candidate = Candidate(
            gid="123",
            name="Acme Corporation",  # Correct spelling
            email="info@acme.com",
            phone="+15551234567",
        )

        result = engine.compute_match(query, candidate)

        # Should match due to email and phone corroboration
        assert result.is_match is True
        assert result.fields_compared >= 2

    def test_legal_suffix_variation(self, engine: MatchingEngine) -> None:
        """Different legal suffixes still match."""
        query = BusinessData(
            name="Acme Inc.",
            email="info@acme.com",
            phone="+15551234567",
        )
        candidate = Candidate(
            gid="123",
            name="Acme LLC",
            email="info@acme.com",
            phone="+15551234567",
        )

        result = engine.compute_match(query, candidate)

        # Names should normalize to same base, plus email/phone match
        assert result.is_match is True

    def test_same_phone_different_name(self, engine: MatchingEngine) -> None:
        """Same phone with different name - phone is strong signal."""
        query = BusinessData(
            name="Joe's Pizza",
            phone="+15551234567",
        )
        candidate = Candidate(
            gid="123",
            name="Joe Pizza Palace",
            phone="+15551234567",
        )

        result = engine.compute_match(query, candidate)

        # Phone match is strong (+7), names partially match
        assert result.fields_compared >= 2

    def test_common_domain_reduced_weight(self) -> None:
        """Common domains like gmail.com have reduced weight."""
        config = MatchingConfig(tf_enabled=True)
        engine = MatchingEngine(config)

        query = BusinessData(
            name="Acme Corp",
            domain="gmail.com",  # Common domain
        )
        candidate = Candidate(
            gid="123",
            name="Different Business",
            domain="gmail.com",
        )

        result = engine.compute_match(query, candidate)

        # Gmail match should have reduced weight
        domain_comp = next(c for c in result.comparisons if c.field_name == "domain")
        assert domain_comp.weight_applied < 5.0  # Less than full domain weight

    def test_name_only_insufficient_evidence(self, engine: MatchingEngine) -> None:
        """Name-only match doesn't meet minimum evidence."""
        query = BusinessData(name="Acme Corp")
        candidate = Candidate(gid="123", name="Acme Corp")

        result = engine.compute_match(query, candidate)

        # Only 1 field compared, min_fields=2
        assert result.fields_compared == 1
        assert result.is_match is False
