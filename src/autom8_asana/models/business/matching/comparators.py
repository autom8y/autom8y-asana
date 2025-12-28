"""Field comparison strategies for matching engine.

Per TDD: Comparators implement different matching strategies
with graduated scoring based on similarity levels.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from autom8_asana.models.business.matching.config import MatchingConfig


class Comparator(Protocol):
    """Field comparison strategy protocol.

    Comparators compare two normalized values and return
    similarity and weight multiplier.
    """

    def compare(
        self,
        left: str,
        right: str,
        config: "MatchingConfig",
    ) -> tuple[float, float]:
        """Compare two normalized values.

        Args:
            left: Left (query) value, normalized.
            right: Right (candidate) value, normalized.
            config: Matching configuration.

        Returns:
            Tuple of (similarity: 0.0-1.0, weight_multiplier: 0.0-1.0).
            weight_multiplier determines what fraction of field weight to apply.
        """
        ...


class ExactComparator:
    """Exact string comparison.

    Returns 1.0 similarity and full weight for exact match,
    0.0 similarity and zero weight for non-match.

    Example:
        >>> comp = ExactComparator()
        >>> comp.compare("test@example.com", "test@example.com", config)
        (1.0, 1.0)
        >>> comp.compare("test@example.com", "other@example.com", config)
        (0.0, 0.0)
    """

    def compare(
        self,
        left: str,
        right: str,
        config: "MatchingConfig",
    ) -> tuple[float, float]:
        """Compare two strings for exact equality.

        Args:
            left: Left value.
            right: Right value.
            config: Matching configuration (unused for exact).

        Returns:
            (1.0, 1.0) if exact match, (0.0, 0.0) otherwise.
        """
        if left == right:
            return (1.0, 1.0)
        return (0.0, 0.0)


class FuzzyComparator:
    """Jaro-Winkler fuzzy comparison with graduated levels.

    Per TDD: Fuzzy matching with graduated weight levels based on
    similarity thresholds.

    Thresholds (from config):
    - >= fuzzy_exact_threshold (0.95): Full weight (1.0)
    - >= fuzzy_high_threshold (0.90): 75% weight (0.75)
    - >= fuzzy_medium_threshold (0.80): 50% weight (0.50)
    - < fuzzy_medium_threshold: Non-match (0.0 weight)

    Example:
        >>> comp = FuzzyComparator()
        >>> comp.compare("acme corp", "acme corporation", config)
        (0.87, 0.50)  # High similarity but below 0.9
    """

    def compare(
        self,
        left: str,
        right: str,
        config: "MatchingConfig",
    ) -> tuple[float, float]:
        """Compare strings using Jaro-Winkler similarity.

        Args:
            left: Left value.
            right: Right value.
            config: Matching configuration with thresholds.

        Returns:
            Tuple of (similarity, weight_multiplier).
        """
        similarity = self._jaro_winkler(left, right)

        # Determine weight multiplier based on thresholds
        if similarity >= config.fuzzy_exact_threshold:
            return (similarity, 1.0)
        elif similarity >= config.fuzzy_high_threshold:
            return (similarity, 0.75)
        elif similarity >= config.fuzzy_medium_threshold:
            return (similarity, 0.50)
        else:
            return (similarity, 0.0)  # Non-match

    def _jaro_winkler(self, left: str, right: str) -> float:
        """Compute Jaro-Winkler similarity.

        Uses rapidfuzz if available, falls back to difflib.

        Args:
            left: First string.
            right: Second string.

        Returns:
            Similarity score 0.0-1.0.
        """
        # Try rapidfuzz first (faster, more accurate)
        try:
            from rapidfuzz.distance import JaroWinkler

            # rapidfuzz JaroWinkler.similarity returns 0.0-1.0
            return JaroWinkler.similarity(left, right)
        except ImportError:
            pass

        # Fallback to difflib SequenceMatcher
        # Note: This is Ratcliff/Obershelp, not true Jaro-Winkler,
        # but provides reasonable approximation for fallback
        from difflib import SequenceMatcher

        return SequenceMatcher(None, left, right).ratio()


class TermFrequencyAdjuster:
    """Reduce weight for common values.

    Per TDD FR-M-006: Common values (gmail.com, common cities)
    contribute less discriminating power.

    Example:
        >>> adjuster = TermFrequencyAdjuster()
        >>> adjuster.adjust_weight("domain", "gmail.com", 5.0, config)
        1.0  # Reduced from 5.0 due to high frequency
        >>> adjuster.adjust_weight("domain", "rarebusiness.com", 5.0, config)
        5.0  # Full weight for rare domain
    """

    # Pre-loaded common value lists (can be extended)
    COMMON_DOMAINS: frozenset[str] = frozenset(
        [
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "aol.com",
            "icloud.com",
            "live.com",
            "msn.com",
            "mail.com",
            "protonmail.com",
        ]
    )

    COMMON_CITIES: frozenset[str] = frozenset(
        [
            "new york",
            "los angeles",
            "chicago",
            "houston",
            "phoenix",
            "philadelphia",
            "san antonio",
            "san diego",
            "dallas",
            "austin",
            "san jose",
            "fort worth",
            "jacksonville",
            "columbus",
            "charlotte",
            "san francisco",
            "indianapolis",
            "seattle",
            "denver",
            "boston",
        ]
    )

    def __init__(self) -> None:
        """Initialize term frequency adjuster."""
        self._domain_frequencies: dict[str, float] = {}
        self._city_frequencies: dict[str, float] = {}

        # Pre-populate with known common values
        for domain in self.COMMON_DOMAINS:
            self._domain_frequencies[domain] = 0.05  # 5% frequency (common)

        for city in self.COMMON_CITIES:
            self._city_frequencies[city] = 0.02  # 2% frequency (common)

    def adjust_weight(
        self,
        field_name: str,
        value: str,
        base_weight: float,
        config: "MatchingConfig",
    ) -> float:
        """Adjust weight based on term frequency.

        Args:
            field_name: Field being compared (domain, city, etc.).
            value: Normalized field value.
            base_weight: Base match weight for field.
            config: Matching configuration.

        Returns:
            Adjusted weight (reduced for common values).
        """
        if not config.tf_enabled:
            return base_weight

        frequency = self._get_frequency(field_name, value)

        if frequency > config.tf_common_threshold:
            # Reduce weight proportionally to frequency
            # Common value = less discriminating power
            # Cap reduction at 80%
            reduction = min(frequency * 10, 0.8)
            return base_weight * (1.0 - reduction)

        return base_weight

    def _get_frequency(self, field_name: str, value: str) -> float:
        """Get frequency for a field value.

        Args:
            field_name: Field name.
            value: Normalized value.

        Returns:
            Estimated frequency (0.0-1.0).
        """
        if field_name == "domain":
            return self._domain_frequencies.get(value.lower(), 0.001)
        elif field_name == "city":
            return self._city_frequencies.get(value.lower(), 0.001)
        elif field_name == "state":
            # States are all relatively common, slight reduction
            return 0.02

        # Unknown field - no adjustment
        return 0.0

    def update_frequencies(
        self,
        field_name: str,
        frequencies: dict[str, float],
    ) -> None:
        """Update frequency table for a field.

        Allows runtime updating of frequency data from actual corpus.

        Args:
            field_name: Field name.
            frequencies: Dict mapping values to frequencies (0.0-1.0).
        """
        if field_name == "domain":
            self._domain_frequencies.update(frequencies)
        elif field_name == "city":
            self._city_frequencies.update(frequencies)
