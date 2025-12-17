"""Design patterns for the autom8_asana SDK.

This module provides reusable patterns that eliminate code duplication
across the SDK while maintaining clear contracts.

Per Initiative DESIGN-PATTERNS-B: Error classification mixin.
"""

from autom8_asana.patterns.error_classification import (
    HasError,
    RetryableErrorMixin,
)

__all__ = [
    "HasError",
    "RetryableErrorMixin",
]
