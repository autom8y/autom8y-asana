"""Scheduling-stratum normalizer-seam (Phase 2 anti-corruption layer).

The SoE (Asana) -> SoR (autom8y-data) translation core for the scheduling-stratum
fleet primitive. Reconceives the legacy ``CustomCalUrl`` cascade clean:

  * :mod:`~autom8_asana.normalizer.scheduling_stratum` -- the PURE resolver: a
    declarative, first-non-empty-wins cascade over the eight provider source
    fields producing the resolved stratum + derived GHL coordinates. It is
    import-pure: no persistence, service-client, HTTP, AWS-SDK, or threading
    dependency, and no attribute mutation (TL-A1 / B1 / B2 / B5).
  * :mod:`~autom8_asana.normalizer.scheduling_extractor` -- the I/O boundary: reads
    the eight source values off an office via the GFR dynvocab by-name path and
    produces the ``normalized_inputs`` dict the pure resolver consumes.

The pure resolver imports NOTHING from the extractor; the dependency points one
way (extractor -> resolver), so the cascade core stays trivially testable.
"""

from __future__ import annotations

from autom8_asana.normalizer.scheduling_stratum import (
    CASCADE_PRIORITY,
    GHL_OWNERSHIP_CLIENT_OWNED,
    GHL_OWNERSHIP_INTERNAL_DURATION,
    GHL_OWNERSHIP_NONE,
    GHL_OWNERSHIP_VALUES,
    SOURCE_TO_STRATUM,
    StratumResult,
    build_ghl_url,
    derive_effective_ghl_id,
    derive_ghl_ownership,
    format_sked_url,
    format_trackstat_url,
    resolve_stratum,
)

__all__ = [
    "CASCADE_PRIORITY",
    "GHL_OWNERSHIP_CLIENT_OWNED",
    "GHL_OWNERSHIP_INTERNAL_DURATION",
    "GHL_OWNERSHIP_NONE",
    "GHL_OWNERSHIP_VALUES",
    "SOURCE_TO_STRATUM",
    "StratumResult",
    "build_ghl_url",
    "derive_effective_ghl_id",
    "derive_ghl_ownership",
    "format_sked_url",
    "format_trackstat_url",
    "resolve_stratum",
]
