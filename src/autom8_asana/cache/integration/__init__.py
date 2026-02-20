"""Cache integration: application wiring, adapters, and helpers.

LAYER RULE: integration/ may import from all cache sublayers, dataframe/,
external packages, and other autom8_asana modules. This is the application
wiring layer with no restrictions on inbound dependencies.
"""

from autom8_asana.cache.integration.derived import (
    get_cached_timelines,
    make_derived_timeline_key,
    store_derived_timelines,
)
from autom8_asana.cache.integration.freshness_coordinator import FreshnessMode
from autom8_asana.cache.integration.mutation_invalidator import (
    MutationInvalidator,
    SoftInvalidationConfig,
)
from autom8_asana.cache.integration.stories import (
    read_cached_stories,
    read_stories_batch,
)

__all__ = [
    "FreshnessMode",
    "MutationInvalidator",
    "SoftInvalidationConfig",
    # Per TDD-SECTION-TIMELINE-REMEDIATION: New cache primitives
    "read_cached_stories",
    "read_stories_batch",
    "make_derived_timeline_key",
    "get_cached_timelines",
    "store_derived_timelines",
]
