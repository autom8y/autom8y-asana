"""Data service client package for autom8_data integration.

Per TDD-INSIGHTS-001: Client and models for fetching analytics insights.
"""

from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.data.config import (
    CircuitBreakerConfig,
    ConnectionPoolConfig,
    DataServiceConfig,
    RetryConfig,
    TimeoutConfig,
)
from autom8_asana.clients.data.models import (
    ColumnInfo,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)

__all__ = [
    # Client class (per Story 1.5)
    "DataServiceClient",
    # Config classes (per Story 1.3)
    "CircuitBreakerConfig",
    "ConnectionPoolConfig",
    "DataServiceConfig",
    "RetryConfig",
    "TimeoutConfig",
    # Model classes
    "ColumnInfo",
    "InsightsMetadata",
    "InsightsRequest",
    "InsightsResponse",
]
