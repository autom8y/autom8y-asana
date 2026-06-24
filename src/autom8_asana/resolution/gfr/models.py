"""GFR result and plan types.

Per GFR TDD v2 §3.2 (Result types) and §5 (Generalized planner). All models are
pydantic with ``extra="forbid"`` so an unknown key is a hard validation error
rather than a silent pass-through.

Type map (TDD §2 ``models.py`` row):

* ``FieldStatus``  — FRESH | STALE (INVARIANT I4: no UNRESOLVED member; unresolved
  fields raise ``UnresolvedError``, never appear as a status).
* ``TruthTier``    — CACHE | VERIFIED (INVARIANT I7 provenance ``source``).
* ``HopClass``     — LOCAL | IN_FRAME_PARENT | PARENT_CHAIN (TDD §5.1).
* ``FieldWithProvenance`` — {value, status, source, as_of} per resolved field
  (INVARIANT I7: every resolved field carries provenance).
* ``ResolvedFields`` — row-set native (INVARIANT I5): ``rows`` is 1..N; ``.scalar()``
  raises ``AmbiguousCardinalityError`` on ``row_count != 1``.
* ``ResolutionPlan`` — the planner output consumed by the engine (TDD §4 step 3).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.resolution.gfr.errors import AmbiguousCardinalityError


class FieldStatus(StrEnum):
    """Freshness status of a resolved field value (INVARIANT I4).

    There is intentionally NO ``UNRESOLVED`` member: an unresolvable field
    collapses the whole call into ``UnresolvedError`` (all-or-nothing), so a
    field that appears in a ``ResolvedFields`` result is ALWAYS resolved — the
    only question is whether it is fresh or served stale-within-bound.
    """

    FRESH = "fresh"  # within TTL
    STALE = "stale"  # past TTL, served stale-within-bound; async refresh triggered


class TruthTier(StrEnum):
    """Truth-source tier and the provenance ``source`` it stamps (INVARIANT I7).

    Tier-1 (CACHE) reads ``company_id`` off the gid-exact Business row from the
    local asana-cache. Tier-2 (VERIFIED) verifies on demand via
    ``get_business_by_guid_async`` (BY-GUID, INVARIANT I7) — never the
    ``office_phone`` analytics join.
    """

    CACHE = "asana-cache"  # tier-1 default: local cached copy off the gid-exact row
    VERIFIED = "data-verified"  # tier-2 on demand: authoritative by-guid data-service


class HopClass(StrEnum):
    """How a field's owning entity is reached from the entry entity (TDD §5.1)."""

    LOCAL = "local"  # field on the entry entity's own frame row
    IN_FRAME_PARENT = "in-frame"  # owner reachable via in-frame parent_gid
    PARENT_CHAIN = "parent-chain"  # owner reachable only via live _traverse_upward_async


class FieldWithProvenance(BaseModel):
    """A single resolved field value with provenance (INVARIANT I7).

    Every resolved field carries the full provenance tuple so a consumer can
    reason about freshness and source without re-querying. ``as_of`` is the
    frame watermark (tier-1) or the data-service response timestamp (tier-2);
    it is never fabricated (TDD §6.2 clause 4).
    """

    model_config = ConfigDict(extra="forbid")

    value: object | None = Field(description="The resolved field value (may be None).")
    status: FieldStatus = Field(description="FRESH or STALE (served stale-within-bound).")
    source: TruthTier = Field(description="Provenance source: asana-cache or data-verified.")
    as_of: datetime | None = Field(
        default=None,
        description="Frame watermark (tier-1) or data-service timestamp (tier-2).",
    )


class ResolvedFields(BaseModel):
    """Row-set native resolution result (INVARIANT I5).

    ``resolve_async`` returns 1..N rows; the result NEVER silently collapses N
    rows into one. ``scalar()`` is opt-in sugar that raises
    ``AmbiguousCardinalityError`` if the result is not provably a single row.
    """

    model_config = ConfigDict(extra="forbid")

    gid: str = Field(description="The entry gid that was resolved.")
    rows: list[dict[str, FieldWithProvenance]] = Field(
        description="Resolved rows, 1..N; each row maps field name -> provenance."
    )
    row_count: int = Field(description="Number of rows in the result set.")

    def scalar(self) -> dict[str, FieldWithProvenance]:
        """Return the single resolved row, or raise (INVARIANT I5).

        Returns:
            The one row's ``{field -> FieldWithProvenance}`` mapping.

        Raises:
            AmbiguousCardinalityError: if ``row_count != 1`` (never silent N->1).
        """
        if self.row_count != 1:
            raise AmbiguousCardinalityError(row_count=self.row_count)
        return self.rows[0]


class FieldPlan(BaseModel):
    """Per-owner hop plan element produced by the planner (TDD §5.1).

    Records which owning entity supplies a set of requested fields and the hop
    class by which that owner is reached from the entry entity. ``is_identity``
    marks tenant-identity owners (Business for ``company_id``) so the guard's
    identity-purity check (INVARIANT I1) can target them precisely.
    """

    model_config = ConfigDict(extra="forbid")

    owner: str = Field(description="Owning entity type (snake_case, e.g. 'business').")
    fields: list[str] = Field(description="Requested fields owned by this entity.")
    hop: HopClass = Field(description="How the owner is reached from the entry entity.")
    is_identity: bool = Field(
        default=False,
        description="True if this owner supplies a tenant-identity field (company_id).",
    )


class ResolutionPlan(BaseModel):
    """The planner output the engine executes (TDD §4 step 3).

    Pure data: the planner is synchronous and performs no I/O. The engine reads
    ``field_plans`` to decide which reads are gid-exact identity reads (off the
    parent-chain-anchored Business gid) versus local/in-frame enrichment reads.
    """

    model_config = ConfigDict(extra="forbid")

    entry_entity_type: str = Field(description="Detected entity type of the entry gid.")
    field_plans: list[FieldPlan] = Field(description="One plan element per distinct owning entity.")

    @property
    def identity_plans(self) -> list[FieldPlan]:
        """Plan elements that resolve a tenant-identity field (company_id)."""
        return [fp for fp in self.field_plans if fp.is_identity]
