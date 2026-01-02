"""Custom field resolver package for dynamic field resolution.

Per TDD-0009.1 and ADR-0034: Provides dynamic custom field resolution
that maps schema field names to Asana custom field GIDs at runtime.

Public API:
    - CustomFieldResolver: Protocol defining the resolver interface
    - DefaultCustomFieldResolver: Production implementation
    - MockCustomFieldResolver: Testing implementation with pre-defined values
    - FailingResolver: Error path testing implementation
    - NameNormalizer: Field name normalization utility
    - TypeCoercer: Schema-aware type coercion for custom field values
    - coerce_value: Module-level coercion function

Example:
    >>> from autom8_asana.dataframes.resolver import (
    ...     DefaultCustomFieldResolver,
    ...     MockCustomFieldResolver,
    ...     NameNormalizer,
    ...     TypeCoercer,
    ...     coerce_value,
    ... )
    >>> # Production use
    >>> resolver = DefaultCustomFieldResolver()
    >>> resolver.build_index(task.custom_fields)
    >>> value = resolver.get_value(task, "cf:MRR", Decimal)

    >>> # Testing use
    >>> resolver = MockCustomFieldResolver({"mrr": Decimal("5000")})
    >>> value = resolver.get_value(None, "cf:MRR")

    >>> # Name normalization
    >>> NameNormalizer.is_match("Weekly Ad Spend", "weekly_ad_spend")
    True

    >>> # Type coercion
    >>> coerce_value(["A", "B"], "Utf8")
    'A, B'
"""

from autom8_asana.dataframes.resolver.coercer import TypeCoercer, coerce_value
from autom8_asana.dataframes.resolver.default import DefaultCustomFieldResolver
from autom8_asana.dataframes.resolver.mock import (
    FailingResolver,
    MockCustomFieldResolver,
)
from autom8_asana.dataframes.resolver.normalizer import NameNormalizer
from autom8_asana.dataframes.resolver.protocol import CustomFieldResolver

__all__ = [
    # Protocol
    "CustomFieldResolver",
    # Implementations
    "DefaultCustomFieldResolver",
    "MockCustomFieldResolver",
    "FailingResolver",
    # Utilities
    "NameNormalizer",
    "TypeCoercer",
    "coerce_value",
]
