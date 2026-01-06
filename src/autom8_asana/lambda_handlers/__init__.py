"""Lambda handlers for AWS Lambda functions.

Per TDD-DATAFRAME-CACHE-001: Provides Lambda handlers for cache operations
including pre-deployment warming.

Handlers:
    - cache_warmer: Lambda handler for cache pre-warming
"""

from autom8_asana.lambda_handlers.cache_warmer import handler as cache_warmer_handler

__all__ = [
    "cache_warmer_handler",
]
