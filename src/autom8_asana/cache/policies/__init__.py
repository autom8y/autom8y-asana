"""Cache policies: stateless evaluation and checking logic.

LAYER RULE: policies/ may import from models/ and external packages only.
It must NOT import from backends/, providers/, or integration/.
"""

from autom8_asana.cache.policies.coalescer import RequestCoalescer
from autom8_asana.cache.policies.freshness_policy import FreshnessPolicy
from autom8_asana.cache.policies.hierarchy import HierarchyIndex
from autom8_asana.cache.policies.lightweight_checker import LightweightChecker
from autom8_asana.cache.policies.staleness import (
    check_batch_staleness,
    check_entry_staleness,
    partition_by_staleness,
)

__all__ = [
    "FreshnessPolicy",
    "LightweightChecker",
    "RequestCoalescer",
    "HierarchyIndex",
    "check_entry_staleness",
    "check_batch_staleness",
    "partition_by_staleness",
]
