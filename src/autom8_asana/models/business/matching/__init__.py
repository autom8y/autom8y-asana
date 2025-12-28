"""Business entity matching module.

Per TDD-BusinessSeeder-v2: Fellegi-Sunter probabilistic matching
for robust business deduplication.

Public API:
    - MatchingEngine: Main matching engine
    - MatchingConfig: Configuration via environment variables
    - MatchResult: Match decision with audit trail
    - Candidate: Candidate record for comparison
    - FieldComparison: Per-field comparison result

Example:
    >>> from autom8_asana.models.business.matching import (
    ...     MatchingEngine,
    ...     MatchingConfig,
    ...     Candidate,
    ... )
    >>> engine = MatchingEngine()
    >>> result = engine.compute_match(business_data, candidate)
    >>> if result.is_match:
    ...     print(f"Match found: {result.candidate_gid}")
"""

from autom8_asana.models.business.matching.blocking import (
    BlockingRule,
    CompositeBlockingRule,
    DomainBlockingRule,
    NameTokenBlockingRule,
    PhonePrefixBlockingRule,
)
from autom8_asana.models.business.matching.comparators import (
    Comparator,
    ExactComparator,
    FuzzyComparator,
    TermFrequencyAdjuster,
)
from autom8_asana.models.business.matching.config import MatchingConfig
from autom8_asana.models.business.matching.engine import (
    MatchingEngine,
    log_odds_to_probability,
)
from autom8_asana.models.business.matching.models import (
    Candidate,
    FieldComparison,
    MatchResult,
)
from autom8_asana.models.business.matching.normalizers import (
    AddressNormalizer,
    BusinessNameNormalizer,
    DomainNormalizer,
    EmailNormalizer,
    Normalizer,
    PhoneNormalizer,
)

__all__ = [
    # Core engine
    "MatchingEngine",
    "MatchingConfig",
    "log_odds_to_probability",
    # Models
    "MatchResult",
    "FieldComparison",
    "Candidate",
    # Normalizers
    "Normalizer",
    "PhoneNormalizer",
    "EmailNormalizer",
    "BusinessNameNormalizer",
    "DomainNormalizer",
    "AddressNormalizer",
    # Comparators
    "Comparator",
    "ExactComparator",
    "FuzzyComparator",
    "TermFrequencyAdjuster",
    # Blocking
    "BlockingRule",
    "DomainBlockingRule",
    "PhonePrefixBlockingRule",
    "NameTokenBlockingRule",
    "CompositeBlockingRule",
]
