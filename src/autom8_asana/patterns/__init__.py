"""Design patterns for the autom8_asana SDK.

This module provides reusable patterns that eliminate code duplication
across the SDK while maintaining clear contracts.

Per Initiative DESIGN-PATTERNS-B: Error classification mixin.
Per Initiative DESIGN-PATTERNS-D: Async/sync method generator.
"""

from autom8_asana.patterns.async_method import (
    AsyncMethodPair,
    async_method,
)
from autom8_asana.patterns.error_classification import (
    HasError,
    RetryableErrorMixin,
)

__all__ = [
    # Async/sync method generator
    "AsyncMethodPair",
    "async_method",
    # Error classification
    "HasError",
    "RetryableErrorMixin",
]
