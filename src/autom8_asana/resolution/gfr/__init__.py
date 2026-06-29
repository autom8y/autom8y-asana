"""GID Field Resolver (GFR) — gid-first, field-declarative READ facade.

One verb: ``resolve_async(gid, fields) -> ResolvedFields``. The caller passes a
gid and schema-declared field names; GFR returns the values with per-field
provenance, hiding entity-tree topology entirely (INVARIANT: the caller never
learns whether the gid is a Business/Unit/Offer/Contact, whether resolution was
an up-traversal or a down-join, or which frame served it).

Identity is resolved by gid + parent-chain edges (INVARIANT GFR-IDENTITY-1):
tenant-identity fields (``company_id``) are read off the GID-EXACT Business row,
never via an ``office_phone`` value-join (the v1 cross-tenant collision trap).

**Public surface (the ONLY symbols fleet callers import).** Topology types
(``EntityType``, ``JoinSpec``, ``HopClass``, the entry/plan internals) are
deliberately NOT re-exported — they stay hidden behind the facade.
"""

from __future__ import annotations

from autom8_asana.resolution.gfr.engine import resolve_async
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import FieldWithProvenance, ResolvedFields

__all__ = [
    "FieldWithProvenance",
    "ResolvedFields",
    "UnresolvedError",
    "resolve_async",
]
