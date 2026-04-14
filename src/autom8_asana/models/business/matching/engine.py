"""Fellegi-Sunter probabilistic matching engine.

Per TDD FR-M-001: Probabilistic matching using log-odds accumulation.
Per TDD FR-M-002: Composite field comparison with configurable weights.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.models.business.matching.comparators import (
    ExactComparator,
    FuzzyComparator,
    TermFrequencyAdjuster,
)
from autom8_asana.models.business.matching.config import MatchingConfig
from autom8_asana.models.business.matching.models import (
    Candidate,
    FieldComparison,
    MatchResult,
)
from autom8_asana.models.business.matching.normalizers import (
    BusinessNameNormalizer,
    DomainNormalizer,
    EmailNormalizer,
    PhoneNormalizer,
)

if TYPE_CHECKING:
    from autom8_asana.models.business.seeder import BusinessData

logger = get_logger(__name__)


def log_odds_to_probability(log_odds: float) -> float:
    """Convert log-odds to probability (0.0-1.0).

    Per TDD ADR-SEEDER-003: Use log-odds internally, probability for API.

    Args:
        log_odds: Sum of log-odds from field comparisons.

    Returns:
        Probability between 0.0 and 1.0.
    """
    # Handle extreme values to avoid overflow
    if log_odds > 20:
        return 0.9999
    if log_odds < -20:
        return 0.0001

    odds = math.exp(log_odds)
    return odds / (1 + odds)


class MatchingEngine:
    """Fellegi-Sunter probabilistic matching engine.

    Computes match scores using log-odds accumulation across
    multiple corroborating fields.

    Per FR-M-001: Fellegi-Sunter model implementation.
    Per FR-M-002: Composite field comparison.
    Per FR-M-003: Minimum evidence threshold.
    Per FR-M-004: Neutral null handling.

    Example:
        >>> engine = MatchingEngine()
        >>> result = engine.compute_match(
        ...     BusinessData(name="Acme Corp", email="info@acme.com"),
        ...     Candidate(gid="123", name="Acme Corporation", email="info@acme.com")
        ... )
        >>> result.is_match
        True
    """

    def __init__(self, config: MatchingConfig | None = None) -> None:
        """Initialize matching engine.

        Args:
            config: Matching configuration. If None, loads from environment.
        """
        self._config = config or MatchingConfig.from_env()

        # Initialize normalizers
        self._phone_normalizer = PhoneNormalizer()
        self._email_normalizer = EmailNormalizer()
        self._name_normalizer = BusinessNameNormalizer()
        self._domain_normalizer = DomainNormalizer()

        # Initialize comparators
        self._exact_comparator = ExactComparator()
        self._fuzzy_comparator = FuzzyComparator()

        # Term frequency adjuster
        self._tf_adjuster = TermFrequencyAdjuster()

    @property
    def config(self) -> MatchingConfig:
        """Get current configuration."""
        return self._config

    def compute_match(
        self,
        query: BusinessData,
        candidate: Candidate,
    ) -> MatchResult:
        """Compute match score between query and candidate.

        Uses Fellegi-Sunter log-odds accumulation across fields.

        Args:
            query: Input business data (from seed request).
            candidate: Existing business record (from search).

        Returns:
            MatchResult with score, decision, and audit trail.
        """
        comparisons: list[FieldComparison] = []
        total_log_odds = 0.0
        fields_compared = 0

        # Compare email (exact match)
        email_comp = self._compare_email(query, candidate)
        comparisons.append(email_comp)
        if email_comp.contributed:
            total_log_odds += email_comp.weight_applied
            fields_compared += 1

        # Compare phone (exact match on normalized)
        phone_comp = self._compare_phone(query, candidate)
        comparisons.append(phone_comp)
        if phone_comp.contributed:
            total_log_odds += phone_comp.weight_applied
            fields_compared += 1

        # Compare name (fuzzy match)
        name_comp = self._compare_name(query, candidate)
        comparisons.append(name_comp)
        if name_comp.contributed:
            total_log_odds += name_comp.weight_applied
            fields_compared += 1

        # Compare domain (exact match)
        domain_comp = self._compare_domain(query, candidate)
        comparisons.append(domain_comp)
        if domain_comp.contributed:
            total_log_odds += domain_comp.weight_applied
            fields_compared += 1

        # Convert to probability
        probability = log_odds_to_probability(total_log_odds)

        # Apply minimum evidence threshold
        if fields_compared < self._config.min_fields:
            # Not enough evidence - cannot match
            return MatchResult(
                is_match=False,
                score=probability,
                raw_score=total_log_odds,
                threshold=self._config.match_threshold,
                fields_compared=fields_compared,
                comparisons=comparisons,
                match_type="no_match",
                candidate_gid=candidate.gid,
            )

        # Apply match threshold
        is_match = probability >= self._config.match_threshold

        return MatchResult(
            is_match=is_match,
            score=probability,
            raw_score=total_log_odds,
            threshold=self._config.match_threshold,
            fields_compared=fields_compared,
            comparisons=comparisons,
            match_type="composite" if is_match else "no_match",
            candidate_gid=candidate.gid,
        )

    def find_best_match(
        self,
        query: BusinessData,
        candidates: list[Candidate],
    ) -> MatchResult | None:
        """Find best matching candidate above threshold.

        Compares query against all candidates and returns the best
        match if it exceeds the threshold.

        Args:
            query: Input business data.
            candidates: List of candidates to compare.

        Returns:
            Best MatchResult above threshold, or None if no match.
        """
        if not candidates:
            return None

        best_result: MatchResult | None = None
        best_score = 0.0

        for candidate in candidates:
            result = self.compute_match(query, candidate)

            if result.is_match and result.score > best_score:
                best_result = result
                best_score = result.score

        if best_result:
            logger.info(
                "Best match found",
                extra=best_result.to_log_dict(),
            )

        return best_result

    def _compare_email(
        self,
        query: BusinessData,
        candidate: Candidate,
    ) -> FieldComparison:
        """Compare email fields.

        Args:
            query: Query business data.
            candidate: Candidate to compare.

        Returns:
            FieldComparison with result.
        """
        query_email = getattr(query, "email", None)
        candidate_email = candidate.email

        # Normalize
        norm_query = self._email_normalizer.normalize(query_email)
        norm_candidate = self._email_normalizer.normalize(candidate_email)

        # Handle null cases
        if norm_query is None or norm_candidate is None:
            return FieldComparison(
                field_name="email",
                left_value=query_email,
                right_value=candidate_email,
                comparison_type="exact",
                similarity=None,
                weight_applied=0.0,  # Neutral
                contributed=False,
            )

        # Exact comparison
        similarity, multiplier = self._exact_comparator.compare(
            norm_query, norm_candidate, self._config
        )

        weight = self._config.email_weight if multiplier > 0 else self._config.email_nonmatch

        return FieldComparison(
            field_name="email",
            left_value=norm_query,
            right_value=norm_candidate,
            comparison_type="exact",
            similarity=similarity,
            weight_applied=weight,
            contributed=True,
        )

    def _compare_phone(
        self,
        query: BusinessData,
        candidate: Candidate,
    ) -> FieldComparison:
        """Compare phone fields.

        Args:
            query: Query business data.
            candidate: Candidate to compare.

        Returns:
            FieldComparison with result.
        """
        query_phone = getattr(query, "phone", None)
        candidate_phone = candidate.phone

        # Normalize
        norm_query = self._phone_normalizer.normalize(query_phone)
        norm_candidate = self._phone_normalizer.normalize(candidate_phone)

        # Handle null cases
        if norm_query is None or norm_candidate is None:
            return FieldComparison(
                field_name="phone",
                left_value=query_phone,
                right_value=candidate_phone,
                comparison_type="exact",
                similarity=None,
                weight_applied=0.0,  # Neutral
                contributed=False,
            )

        # Exact comparison
        similarity, multiplier = self._exact_comparator.compare(
            norm_query, norm_candidate, self._config
        )

        weight = self._config.phone_weight if multiplier > 0 else self._config.phone_nonmatch

        return FieldComparison(
            field_name="phone",
            left_value=norm_query,
            right_value=norm_candidate,
            comparison_type="exact",
            similarity=similarity,
            weight_applied=weight,
            contributed=True,
        )

    def _compare_name(
        self,
        query: BusinessData,
        candidate: Candidate,
    ) -> FieldComparison:
        """Compare name fields using fuzzy matching.

        Args:
            query: Query business data.
            candidate: Candidate to compare.

        Returns:
            FieldComparison with result.
        """
        query_name = query.name
        candidate_name = candidate.name

        # Normalize
        norm_query = self._name_normalizer.normalize(query_name)
        norm_candidate = self._name_normalizer.normalize(candidate_name)

        # Handle null cases
        if norm_query is None or norm_candidate is None:
            return FieldComparison(
                field_name="name",
                left_value=query_name,
                right_value=candidate_name,
                comparison_type="fuzzy",
                similarity=None,
                weight_applied=0.0,  # Neutral
                contributed=False,
            )

        # Fuzzy comparison
        similarity, multiplier = self._fuzzy_comparator.compare(
            norm_query, norm_candidate, self._config
        )

        if multiplier > 0:
            # Match - apply TF adjustment
            base_weight = self._config.name_weight * multiplier
            weight = base_weight  # No TF adjustment for names
        else:
            # Non-match
            weight = self._config.name_nonmatch

        return FieldComparison(
            field_name="name",
            left_value=norm_query,
            right_value=norm_candidate,
            comparison_type="fuzzy",
            similarity=similarity,
            weight_applied=weight,
            contributed=True,
        )

    def _compare_domain(
        self,
        query: BusinessData,
        candidate: Candidate,
    ) -> FieldComparison:
        """Compare domain fields.

        Args:
            query: Query business data.
            candidate: Candidate to compare.

        Returns:
            FieldComparison with result.
        """
        query_domain = getattr(query, "domain", None)
        candidate_domain = candidate.domain

        # Normalize
        norm_query = self._domain_normalizer.normalize(query_domain)
        norm_candidate = self._domain_normalizer.normalize(candidate_domain)

        # Handle null cases
        if norm_query is None or norm_candidate is None:
            return FieldComparison(
                field_name="domain",
                left_value=query_domain,
                right_value=candidate_domain,
                comparison_type="exact",
                similarity=None,
                weight_applied=0.0,  # Neutral
                contributed=False,
            )

        # Exact comparison
        similarity, multiplier = self._exact_comparator.compare(
            norm_query, norm_candidate, self._config
        )

        if multiplier > 0:
            # Match - apply TF adjustment for common domains
            base_weight = self._config.domain_weight
            weight = self._tf_adjuster.adjust_weight(
                "domain", norm_query, base_weight, self._config
            )
        else:
            # Non-match
            weight = self._config.domain_nonmatch

        return FieldComparison(
            field_name="domain",
            left_value=norm_query,
            right_value=norm_candidate,
            comparison_type="exact",
            similarity=similarity,
            weight_applied=weight,
            contributed=True,
        )

    def normalize_candidate(self, candidate: Candidate) -> Candidate:
        """Pre-normalize candidate fields for efficient comparison.

        Args:
            candidate: Candidate with raw field values.

        Returns:
            Candidate with normalized_* fields populated.
        """
        candidate.normalized_name = self._name_normalizer.normalize(candidate.name)
        candidate.normalized_phone = self._phone_normalizer.normalize(candidate.phone)
        candidate.normalized_email = self._email_normalizer.normalize(candidate.email)
        return candidate
