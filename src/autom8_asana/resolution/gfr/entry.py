"""GFR entry phase — the single Asana-API origin (INVARIANT I1, TDD §4.1).

``_fetch_and_anchor_async`` is the ONLY Asana-API read GFR itself originates. It
does TRIPLE DUTY in one logical entry phase by consuming
``hydrate_from_gid_async`` (``hydration.py:208``) with ``hydrate_full=False``:

1. **hydrate** the entry Task (1 ``client.tasks.get_async`` read);
2. **detect** its ``entity_type`` via ``detect_entity_type_async``
   (``facade.py:405`` — the O(1) discriminator, NOT ``model_validate``); and
3. **anchor** the tenant identity by walking ``current.parent.gid`` upward to the
   Business root via ``_traverse_upward_async`` (``hydration.py:571``), yielding
   the collision-free ``business_gid``.

``hydrate_full=False`` is deliberate: GFR's identity spine needs the Business
root located, NOT the full downward hierarchy hydrated. This keeps the entry
read budget at ``1 entry hydrate + <=3 parent-chain reads`` for an offer chain
(``hydration.py:670`` per-level fetch) and avoids the holder-fetch fan-out.

**Read-budget accounting (INVARIANT I3 / B5 / QA new_hole 3).** Every Asana-API
read GFR originates happens INSIDE this entry phase. The cache-only guarantee is
scoped to the POST-ENTRY data-frame phase: the PT-03 RED proof baselines the
client call count AFTER this function returns, then asserts zero further reads.
The entry+chain reads here are LEGITIMATE and EXCLUDED from that delta — a test
that counts total reads and expects zero would FALSE-FAIL on this budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.core.types import EntityType
from autom8_asana.errors import HydrationError
from autom8_asana.models.business.hydration import hydrate_from_gid_async
from autom8_asana.resolution.gfr.errors import UnresolvedError

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.base import BusinessEntity

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class EntryAnchor:
    """Result of the entry phase — the tenant-identity anchor (TDD §2 entry.py).

    Attributes:
        gid: The entry gid that was resolved.
        entity_type: Detected type of the entry entity (never UNKNOWN — an
            undetectable type raises ``UnresolvedError`` before this is built).
        business_gid: The parent-chain-anchored Business root gid. Tenant-identity
            fields (``company_id``) are read off THIS gid by a gid-exact predicate,
            never via an ``office_phone`` value-join.
        path_len: Number of intermediate entities traversed upward (excluding the
            Business root). Used by tests to attest the bounded entry budget.
        entry_task: Carries the hydrated entry task (cf manifest) for the
            ``is_identity=False`` dynamic tail (sprint-2). The same object
            hydration already produced — for a non-Business entry it is the
            hydrated entry entity; for a Business entry (where
            ``HydrationResult.entry_entity`` is ``None``) it is the hydrated
            Business root, which carries the cf manifest. NOT part of the identity
            spine; never read by ``assert_rows_tenant_identity``. Optional with a
            ``None`` default so the field is strictly additive.
    """

    gid: str
    entity_type: EntityType
    business_gid: str
    path_len: int
    entry_task: BusinessEntity | None = None


async def _fetch_and_anchor_async(gid: str, client: AsanaClient) -> EntryAnchor:
    """Fetch the entry task, detect its type, and anchor the Business gid.

    This is the ONLY Asana-API read GFR originates (INVARIANT I1, I3). It
    consumes ``hydrate_from_gid_async(..., hydrate_full=False)`` which hydrates
    the entry task, detects its type, and (for non-Business entries) walks the
    single-parent chain to the Business root with cycle detection — a
    collision-free identity edge.

    Args:
        gid: Any task gid in the business hierarchy (Offer, Unit, Contact, ...).
        client: AsanaClient threaded to the hydrate + parent-chain reads.

    Returns:
        EntryAnchor with the detected entity_type and the anchored business_gid.

    Raises:
        UnresolvedError(reason="entity-type-undetectable"): if detection returns
            ``EntityType.UNKNOWN`` (the discriminator could not classify the gid).
        UnresolvedError(reason="no-identity-path"): if the parent chain cannot
            reach a Business (``HydrationError`` — root reached, cycle, depth, or
            missing parent reference).
    """
    logger.debug("GFR entry: fetch and anchor", extra={"gid": gid})
    try:
        # hydrate_full=False: locate the Business root only (the identity spine),
        # not the full downward hierarchy. Triple duty in one fetch chain.
        result = await hydrate_from_gid_async(client, gid, hydrate_full=False)
    except HydrationError as exc:
        # No collision-free path to a Business root — surface explicitly rather
        # than falling back to a phone match (INVARIANT I1 / I4).
        logger.info(
            "GFR entry: no identity path to Business",
            extra={"gid": gid, "phase": getattr(exc, "phase", None)},
        )
        raise UnresolvedError(fields=[gid], reason="no-identity-path") from exc

    entity_type = result.entry_type
    if entity_type is None or entity_type == EntityType.UNKNOWN:
        # The O(1) discriminator could not classify this gid; do NOT guess via
        # model_validate (the documented anti-pattern — TDD §6.3).
        logger.info("GFR entry: entity type undetectable", extra={"gid": gid})
        raise UnresolvedError(fields=[gid], reason="entity-type-undetectable")

    business_gid = result.business.gid
    # GAP-2 (D-3): thread the cf-CARRYING task in BOTH entry topologies. For a
    # non-Business entry, the hydrated task is result.entry_entity. For a Business
    # entry, result.entry_entity is None (hydration.py:319-322 "Started at
    # Business") and the cf manifest lives on result.business. Either way this is
    # the cf-bearing task for the entry gid — a uniform source for the sprint-2
    # dynamic tail. No new fetch: both objects already exist in ``result``.
    entry_task = result.entry_entity if result.entry_entity is not None else result.business
    anchor = EntryAnchor(
        gid=gid,
        entity_type=entity_type,
        business_gid=business_gid,
        path_len=len(result.path),
        entry_task=entry_task,
    )
    logger.debug(
        "GFR entry: anchored",
        extra={
            "gid": gid,
            "entity_type": entity_type.value,
            "business_gid": business_gid,
            "path_len": anchor.path_len,
        },
    )
    return anchor
