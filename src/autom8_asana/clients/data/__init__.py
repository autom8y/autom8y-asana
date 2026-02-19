"""Data service client package for autom8_data integration.

Client and models for fetching analytics insights from autom8_data.
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
    BatchInsightsResponse,
    BatchInsightsResult,
    ColumnInfo,
    ExportResult,
    InsightsMetadata,
    InsightsRequest,
    InsightsResponse,
)

__all__ = [
    # Client class
    "DataServiceClient",
    # Config classes
    "CircuitBreakerConfig",
    "ConnectionPoolConfig",
    "DataServiceConfig",
    "RetryConfig",
    "TimeoutConfig",
    # Model classes
    "BatchInsightsResponse",
    "BatchInsightsResult",
    "ColumnInfo",
    "ExportResult",
    "InsightsMetadata",
    "InsightsRequest",
    "InsightsResponse",
]
