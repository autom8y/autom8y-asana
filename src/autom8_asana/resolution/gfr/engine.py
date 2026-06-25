"""GFR orchestration spine — ``resolve_async`` (INVARIANT I1-I7; TDD §3, §4).

The thin engine ASSEMBLES the existing substrate; it holds no field-specific code
and no query logic. The flow (TDD §4):

1. **plan** — partition requested fields by owning schema (FM5 / unknown-field).
2. **entry** — ``_fetch_and_anchor_async``: the single accounted Asana-API read,
   hydrating + type-detecting + parent-walking to the Business gid (INVARIANT I1).
3. **guard** — identity-path purity on the plan (INVARIANT I1, defense in depth).
4. **identity read** — for tenant-identity fields, a GID-EXACT ``RowsRequest``
   (``where: gid == business_gid``) with ``join=None`` through ``execute_rows``
   (``query/engine.py:77``). INVARIANT I2: no join field means it can NEVER reach
   ``execute_join``'s ``keep='first'`` dedup (``query/join.py:157``). The guard
   re-asserts purity on the issued request.
5. **posture** — assemble per-field provenance from the ``RowsMeta`` freshness
   side-channel; all-or-nothing on empty frames (INVARIANT I4, I7).
6. **tier-2 (optional)** — when ``truth_tier=VERIFIED``, verify ``company_id``
   against the authoritative by-guid record (INVARIANT I7), stamping the
   provenance ``source`` as ``data-verified``.
7. **cardinality** — ``scalar=True`` raises ``AmbiguousCardinalityError`` on
   ``row_count != 1`` (INVARIANT I5).

Cache-only hard line (INVARIANT I3): all Asana-API reads GFR originates are in
the entry phase (step 2). An offer-domain data-frame miss in step 4 returns
``UnresolvedError`` with ZERO further API calls — there is no Asana-API frame
fallback wired here (HARD line #1). The PT-03 RED proof baselines the client
call count AFTER the entry phase and asserts the post-entry delta is zero.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.query.models import Comparison, Op, RowsRequest
from autom8_asana.resolution.gfr import guard as guard_mod
from autom8_asana.resolution.gfr.entry import EntryAnchor, _fetch_and_anchor_async
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import (
    FieldPlan,
    ResolutionPlan,
    ResolvedFields,
    TruthTier,
)
from autom8_asana.resolution.gfr.planner import plan_resolution
from autom8_asana.resolution.gfr.posture import assemble_rows
from autom8_asana.resolution.gfr.truth_source import (
    ByGuidVerifier,
    verify_company_id_async,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from autom8_asana.client import AsanaClient
    from autom8_asana.query.engine import QueryEngine

logger = get_logger(__name__)


def _business_project_gid() -> str:
    """Return the Business project gid for gid-exact identity reads.

    The Business frame is the multi-tenant project (``entity_registry.py:445``);
    the gid-exact ``where`` predicate selects the single correct tenant row
    within it (Vector A closed by construction — INVARIANT I1 / TDD §5.3).
    """
    descriptor = get_registry().get("business")
    if descriptor is None or descriptor.primary_project_gid is None:
        # Should never happen: the Business descriptor is statically registered.
        raise UnresolvedError(fields=["company_id"], reason="no-identity-path")
    return descriptor.primary_project_gid


def _build_identity_request(business_gid: str, fields: list[str]) -> RowsRequest:
    """Build a GID-EXACT identity ``RowsRequest`` (INVARIANT I1, I2).

    The request filters ``gid == business_gid`` and carries ``join=None`` — it is
    structurally incapable of reaching the ``office_phone`` dedup. This is the
    sole identity read shape; the engine never builds a join for identity.
    """
    return RowsRequest(
        where=Comparison(field="gid", op=Op.EQ, value=business_gid),
        select=list(fields),
        join=None,  # INVARIANT I2: no join => never reaches keep='first' dedup
    )


async def _resolve_identity_plan_async(
    *,
    anchor: EntryAnchor,
    field_plan: FieldPlan,
    query_engine: QueryEngine,
    client: AsanaClient,
    truth_tier: TruthTier,
    verifier: ByGuidVerifier | None,
) -> ResolvedFields:
    """Resolve a tenant-identity plan element via the gid-exact Business read.

    Builds the gid-exact request, re-asserts identity-path purity (INVARIANT I1),
    executes ``execute_rows`` (no join — INVARIANT I2), assembles provenance, and
    optionally runs the tier-2 by-guid verify (INVARIANT I7).
    """
    project_gid = _business_project_gid()
    request = _build_identity_request(anchor.business_gid, field_plan.fields)

    # Defense in depth: the issued request MUST be gid-exact with no phone join.
    guard_mod.assert_request_identity_pure(request)

    response = await query_engine.execute_rows(
        "business",
        project_gid,
        client,
        request,
    )

    # gid-exact => at most one row. Zero rows is an explicit identity failure,
    # never a silent phone fallback (INVARIANT I1 / I4).
    if not response.data:
        logger.info(
            "GFR engine: business row not found for anchored gid",
            extra={"business_gid": anchor.business_gid, "fields": field_plan.fields},
        )
        raise UnresolvedError(fields=field_plan.fields, reason="business-row-not-found")

    # ENGINE-OWNED Vector-A tenant guard (GAP-1, INVARIANT I1). The frozen query
    # substrate filtered the frame to the anchored tenant via the gid-exact
    # ``where`` (``query/engine.py:169`` ``df.filter``) — but that is the
    # SUBSTRATE's contract, not the engine's. Before reading ``data[0]``'s
    # company_id, the engine re-asserts in its OWN code that EVERY returned row
    # carries gid == business_gid. An unfiltered/cross-tenant frame (drifted
    # provider) would otherwise leak a different tenant's company_id silently;
    # this raises GuardViolationError instead (defense in depth, not a
    # replacement for the frozen filter).
    guard_mod.assert_rows_tenant_identity(response.data, anchor.business_gid)

    source = TruthTier.CACHE
    as_of: datetime | None = None
    if truth_tier == TruthTier.VERIFIED:
        # Tier-2: verify company_id against the authoritative by-guid record.
        if verifier is None:
            raise UnresolvedError(fields=field_plan.fields, reason="business-row-not-found")
        company_id = response.data[0].get("company_id")
        if not isinstance(company_id, str) or not await verify_company_id_async(
            company_id, verifier
        ):
            # The tier-1 value does not round-trip to a single authoritative
            # tenant -> treat as unresolved identity (all-or-nothing).
            raise UnresolvedError(fields=field_plan.fields, reason="business-row-not-found")
        source = TruthTier.VERIFIED
        as_of = datetime.now(UTC)

    return assemble_rows(
        gid=anchor.gid,
        fields=field_plan.fields,
        data=response.data,
        meta=response.meta,
        source=source,
        as_of=as_of,
    )


async def resolve_async(
    gid: str,
    fields: Sequence[str],
    *,
    client: AsanaClient,
    query_engine: QueryEngine,
    truth_tier: TruthTier = TruthTier.CACHE,
    scalar: bool = False,
    verifier: ByGuidVerifier | None = None,
) -> ResolvedFields:
    """Resolve schema-declared fields for a gid, topology hidden (TDD §3.1).

    Identity is resolved by gid + parent-chain (INVARIANT I1): the single entry
    fetch hydrates the task, detects its type, and walks the parent chain to the
    Business root; tenant-identity fields (``company_id``) are read off the
    GID-EXACT Business row, never via an ``office_phone`` value-join.

    Row-set native (INVARIANT I5): gid -> 1..N rows. ``scalar=True`` raises
    ``AmbiguousCardinalityError`` if the result is not provably a single row.
    Strict all-or-nothing (INVARIANT I4): if ANY requested field is genuinely
    unresolvable the WHOLE call raises ``UnresolvedError(fields=[...], reason=...)``.
    Stale-but-present counts as resolved. Never calls the Asana API on an
    offer-domain DATA-FRAME miss (INVARIANT I3); the entry fetch is a separate
    accounted read.

    Args:
        gid: Any task gid in the business hierarchy.
        fields: Schema-declared field names to resolve.
        client: AsanaClient threaded to the entry fetch and ``execute_rows``.
        query_engine: The substrate ``QueryEngine`` GFR consumes for field reads.
        truth_tier: CACHE (tier-1 default) or VERIFIED (tier-2 by-guid).
        scalar: If True, return the single row or raise on N != 1.
        verifier: A ``ByGuidVerifier`` for tier-2; required when truth_tier=VERIFIED.

    Returns:
        A ``ResolvedFields`` (row-set native) with per-field provenance.

    Raises:
        UnresolvedError: all-or-nothing failure (closed reason vocabulary).
        GuardViolationError: identity-path purity violation (defense in depth).
        AmbiguousCardinalityError: scalar requested but row_count != 1.
    """
    field_list = list(fields)
    logger.debug(
        "GFR resolve: start",
        extra={"gid": gid, "fields": field_list, "truth_tier": truth_tier.value},
    )

    # 1. ENTRY — the single accounted Asana-API read; also classifies the type
    #    used by the planner. (Plan needs the entity_type, which the entry phase
    #    supplies; the entry fetch is the only I/O origin — INVARIANT I1, I3.)
    anchor = await _fetch_and_anchor_async(gid, client)

    # 2. PLAN — partition by owning schema (FM5 unknown-field; INVARIANT I4).
    plan: ResolutionPlan = plan_resolution(anchor.entity_type, field_list)

    # 3. GUARD — identity-path purity on the plan (INVARIANT I1, defense in depth).
    guard_mod.assert_plan_identity_pure(plan)

    # 4-6. EXECUTE each plan element. For this telos rung the driving case is the
    #      identity plan (company_id); the engine resolves identity plan elements
    #      via the gid-exact Business read. Non-identity enrichment plans are out
    #      of scope for the identity-correctness rung this session drives.
    identity_plans = plan.identity_plans
    if not identity_plans:
        # No tenant-identity field requested: nothing on the identity spine to
        # resolve in this rung. A field set with no resolvable owner would have
        # already raised unknown-field in the planner; a non-identity-only set is
        # explicitly out of this session's identity-correctness scope.
        raise UnresolvedError(fields=field_list, reason="no-identity-path")

    # Identity is Business-owned and single-sourced; resolve the (single) identity
    # plan element. Multiple identity plans cannot occur (company_id is the only
    # identity field and is Business-only).
    result = await _resolve_identity_plan_async(
        anchor=anchor,
        field_plan=identity_plans[0],
        query_engine=query_engine,
        client=client,
        truth_tier=truth_tier,
        verifier=verifier,
    )

    # 7. CARDINALITY (INVARIANT I5).
    if scalar:
        result.scalar()  # raises AmbiguousCardinalityError if row_count != 1
    return result
