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
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autom8_asana.resolution.gfr.errors import AmbiguousCardinalityError

# Typing-provenance vocabulary (sprint-3 FRAME-004). The CLOSED set of origins a
# resolved field's typed value can carry, so a caller can distinguish a
# schema-validated value from a heuristically-coerced one from an override-
# transformed one. Surfaced as a module ``Literal`` so the field type and any
# consumer share one source of truth.
#
# * ``schema``    — value came from a certified dataframe schema dtype (reserved for
#                   the schema-resolved path; the dynamic tail does NOT mint it).
# * ``heuristic`` — value extracted by the ``resource_subtype`` typing table
#                   (``_extract_raw_value``) for a KNOWN subtype.
# * ``override``  — a registered NAME-keyed, EntityType-scoped override transformed
#                   the raw value (e.g. asset_id text -> comma-split SET).
# * ``absent``    — reserved: a genuinely-absent field never reaches a row (it
#                   raises ``unknown-field``); kept in the vocabulary for caller
#                   completeness and downstream provenance consumers.
# * ``fallback``  — value came from the ``case _`` ``display_value`` fallthrough for
#                   an UNKNOWN ``resource_subtype`` (FRAME-003 observability).
TypingOrigin = Literal["schema", "heuristic", "override", "absent", "fallback"]


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
    typing_origin: TypingOrigin | None = Field(
        default=None,
        description=(
            "How the value was typed (sprint-3 FRAME-004): schema | heuristic | "
            "override | absent | fallback. Lets a caller distinguish a "
            "schema-validated value from a heuristically-coerced or "
            "override-transformed one. None for the certified identity-spine path "
            "(which predates this tag); the dynamic tail always stamps it. Additive, "
            "default None so every existing construction stays valid."
        ),
    )
    cf_type: str | None = Field(
        default=None,
        description=(
            "The Asana custom-field ``resource_subtype`` the value was typed from "
            "(sprint-3 FRAME-004), e.g. 'text' | 'number' | 'date'. None for the "
            "identity-spine path; stamped by the dynamic tail. Additive, default None."
        ),
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
    dynamic_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Requested fields with no resolvable schema owner (sprint-2 D-T1a). The "
            "planner CANNOT pre-judge absence for these — that requires the live cf "
            "manifest — so it partitions them here instead of raising 'unknown-field' "
            "at plan time. The is_identity=False dynamic tail "
            "(``dynvocab.resolve_dynamic_fields``) resolves them off the hydrated "
            "``anchor.entry_task`` manifest, NAME-keyed, governed-strict: a field "
            "genuinely absent from the manifest STILL raises "
            "``UnresolvedError(reason='unknown-field')`` (closed vocab preserved); "
            "only the interception point moves from plan-time to tail-time. Additive, "
            "default empty so every existing construction and the identity-plan path "
            "are byte-identical.",
        ),
    )

    @property
    def identity_plans(self) -> list[FieldPlan]:
        """Plan elements that resolve a tenant-identity field (company_id)."""
        return [fp for fp in self.field_plans if fp.is_identity]
