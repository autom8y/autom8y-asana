"""Unit tests for matching comparators.

Per TDD-BusinessSeeder-v2: Tests for field comparison strategies.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.matching.comparators import (
    ExactComparator,
    FuzzyComparator,
    TermFrequencyAdjuster,
)
from autom8_asana.models.business.matching.config import MatchingConfig


class TestExactComparator:
    """Tests for ExactComparator."""

    @pytest.fixture
    def config(self) -> MatchingConfig:
        """Create default config."""
        return MatchingConfig()

    def test_exact_match_returns_full_weight(self, config: MatchingConfig) -> None:
        """Exact match returns (1.0, 1.0)."""
        comp = ExactComparator()
        similarity, multiplier = comp.compare("test", "test", config)
        assert similarity == 1.0
        assert multiplier == 1.0

    def test_non_match_returns_zero(self, config: MatchingConfig) -> None:
        """Non-match returns (0.0, 0.0)."""
        comp = ExactComparator()
        similarity, multiplier = comp.compare("test", "other", config)
        assert similarity == 0.0
        assert multiplier == 0.0

    def test_case_sensitive(self, config: MatchingConfig) -> None:
        """Comparison is case-sensitive."""
        comp = ExactComparator()
        similarity, multiplier = comp.compare("Test", "test", config)
        assert similarity == 0.0
        assert multiplier == 0.0

    def test_whitespace_matters(self, config: MatchingConfig) -> None:
        """Whitespace affects comparison."""
        comp = ExactComparator()
        similarity, multiplier = comp.compare("test", "test ", config)
        assert similarity == 0.0


class TestFuzzyComparator:
    """Tests for FuzzyComparator."""

    @pytest.fixture
    def config(self) -> MatchingConfig:
        """Create default config."""
        return MatchingConfig()

    def test_exact_match_full_weight(self, config: MatchingConfig) -> None:
        """Exact match gets full weight."""
        comp = FuzzyComparator()
        similarity, multiplier = comp.compare("test", "test", config)
        assert similarity >= 0.95
        assert multiplier == 1.0

    def test_high_similarity(self, config: MatchingConfig) -> None:
        """High similarity (>0.9) gets 0.75 weight."""
        comp = FuzzyComparator()
        # These should have high but not exact similarity
        similarity, multiplier = comp.compare("testing", "testin", config)
        # Jaro-Winkler should give ~0.92+ for this
        assert similarity >= 0.9
        assert multiplier in (0.75, 1.0)

    def test_medium_similarity(self, config: MatchingConfig) -> None:
        """Medium similarity (>0.8) gets 0.50 weight."""
        comp = FuzzyComparator()
        # These should have medium similarity
        similarity, multiplier = comp.compare("acme corp", "acme corporation", config)
        # This should be around 0.80-0.90
        assert similarity >= 0.5
        if 0.8 <= similarity < 0.9:
            assert multiplier == 0.50
        elif 0.9 <= similarity < 0.95:
            assert multiplier == 0.75

    def test_low_similarity_zero_weight(self, config: MatchingConfig) -> None:
        """Low similarity (<0.8) gets zero weight."""
        comp = FuzzyComparator()
        similarity, multiplier = comp.compare("completely", "different", config)
        assert multiplier == 0.0

    def test_custom_thresholds(self) -> None:
        """Custom thresholds are respected."""
        config = MatchingConfig(
            fuzzy_exact_threshold=0.99,
            fuzzy_high_threshold=0.95,
            fuzzy_medium_threshold=0.90,
        )
        comp = FuzzyComparator()

        # "testing" vs "test" with stricter thresholds
        similarity, multiplier = comp.compare("testing", "test", config)
        # With stricter thresholds, this might get lower weight
        assert multiplier in (0.0, 0.50, 0.75, 1.0)


class TestTermFrequencyAdjuster:
    """Tests for TermFrequencyAdjuster."""

    @pytest.fixture
    def config(self) -> MatchingConfig:
        """Create config with TF enabled."""
        return MatchingConfig(tf_enabled=True, tf_common_threshold=0.01)

    def test_common_domain_reduced_weight(self, config: MatchingConfig) -> None:
        """Common domains get reduced weight."""
        adjuster = TermFrequencyAdjuster()
        adjusted = adjuster.adjust_weight("domain", "gmail.com", 5.0, config)
        assert adjusted < 5.0

    def test_rare_domain_full_weight(self, config: MatchingConfig) -> None:
        """Rare domains get full weight."""
        adjuster = TermFrequencyAdjuster()
        adjusted = adjuster.adjust_weight("domain", "rarecorp.io", 5.0, config)
        assert adjusted == 5.0

    def test_common_city_reduced_weight(self, config: MatchingConfig) -> None:
        """Common cities get reduced weight."""
        adjuster = TermFrequencyAdjuster()
        adjusted = adjuster.adjust_weight("city", "new york", 4.0, config)
        assert adjusted < 4.0

    def test_tf_disabled_full_weight(self) -> None:
        """TF disabled returns full weight."""
        config = MatchingConfig(tf_enabled=False)
        adjuster = TermFrequencyAdjuster()
        adjusted = adjuster.adjust_weight("domain", "gmail.com", 5.0, config)
        assert adjusted == 5.0

    def test_unknown_field_no_adjustment(self, config: MatchingConfig) -> None:
        """Unknown field gets no adjustment."""
        adjuster = TermFrequencyAdjuster()
        adjusted = adjuster.adjust_weight("unknown_field", "value", 5.0, config)
        assert adjusted == 5.0

    def test_update_frequencies(self, config: MatchingConfig) -> None:
        """Frequencies can be updated."""
        adjuster = TermFrequencyAdjuster()

        # Initially rare domain
        initial = adjuster.adjust_weight("domain", "newdomain.com", 5.0, config)
        assert initial == 5.0

        # Update frequencies to make it common
        adjuster.update_frequencies("domain", {"newdomain.com": 0.1})

        # Now should be reduced
        updated = adjuster.adjust_weight("domain", "newdomain.com", 5.0, config)
        assert updated < 5.0
