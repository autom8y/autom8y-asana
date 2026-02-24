"""Protocol definitions for dependency injection boundaries.

Per TDD-HARDENING-A/FR-OBS-008: Export ObservabilityHook protocol.
Per R-010 (WS-QUERY): Export DataFrameProvider protocol.
"""

from autom8_asana.protocols.auth import AuthProvider
from autom8_asana.protocols.cache import (
    CacheProvider,
    DataFrameCacheProtocol,
    WarmResult,
)
from autom8_asana.protocols.dataframe_provider import DataFrameProvider
from autom8_asana.protocols.insights import InsightsProvider
from autom8_asana.protocols.item_loader import ItemLoader
from autom8_asana.protocols.log import LogProvider
from autom8_asana.protocols.metrics import MetricsEmitter
from autom8_asana.protocols.observability import ObservabilityHook

__all__ = [
    "AuthProvider",
    "CacheProvider",
    "DataFrameCacheProtocol",
    # R-010
    "DataFrameProvider",
    "InsightsProvider",
    "ItemLoader",
    "MetricsEmitter",
    "LogProvider",
    "WarmResult",
    # TDD-HARDENING-A/FR-OBS-008
    "ObservabilityHook",
]
