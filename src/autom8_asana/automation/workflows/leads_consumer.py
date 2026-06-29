"""GrainBridgeLeadsConsumer -- per-business single-tenant LEADS read.

The orchestrator for the grain-bridge thin consumer. For each ACTIVE offer it:

1. resolves Offer -> Business -> ``(office_phone, vertical, company_id)``
2. derives the ebid LOCALLY from ``company_id`` (``compute_ebid``; bootstrap intact)
3. mints a single-tenant per-business token (``BusinessTokenMinter``; data:read only)
4. reads leads with that token (per-business ``DataServiceClient``; JWT tenant
   dominates the office_phone param -- anti-IDOR, SC-BUILD-3)
5. records success OR EMITs one of the CLOSED 4-class skips (log + metric +
   count); NEVER a silent drop, NEVER a fleet fallback.

Reconciliation invariant (AC-S3): ``attempted == succeeded + Sum(skip-class
counts)``. FATAL carve-out (ADR D5): a 401/403 delegator misconfiguration
(``MintCredentialError`` / ``MintScopeError``) raises-and-halts the whole run
rather than masquerading as N per-business ``resolution_miss`` skips.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.auth.business_token import (
    BusinessTokenMinter,
    MintCollision,
    MintRateLimited,
    MintResolutionMiss,
    MintUnavailable,
)
from autom8_asana.auth.per_business_provider import PerBusinessTokenProvider
from autom8_asana.automation.workflows.active_offer_enumeration import (
    enumerate_active_offers,
)
from autom8_asana.automation.workflows.leads_ebid import (
    EbidInputAbsent,
    EbidInputNull,
    compute_ebid,
)
from autom8_asana.automation.workflows.leads_skip import (
    MetricsHook,
    SkipClass,
    emit_skip,
)
from autom8_asana.errors import (
    CircuitBreakerOpenError,
    InsightsNotFoundError,
    InsightsServiceError,
)
from autom8_asana.resolution.context import ResolutionContext

if TYPE_CHECKING:
    from autom8_asana.clients.data.client import DataServiceClient
    from autom8_asana.core.scope import EntityScope
    from autom8_asana.protocols.auth import AuthProvider

logger = get_logger(__name__)

WORKFLOW_ID = "grain-bridge-leads"
DEFAULT_MAX_CONCURRENCY = 5
DEFAULT_LEADS_DAYS = 30
DEFAULT_LEADS_LIMIT = 100

DataClientFactory = Callable[["AuthProvider"], "DataServiceClient"]


@dataclass
class _ResolvedBusiness:
    """Resolved Business fields needed for the per-business leads read."""

    gid: str
    office_phone: str | None
    vertical: str | None
    company_id: str | None
    name: str | None


@dataclass
class _OfferResult:
    """Per-offer outcome: either succeeded, or skipped with a class."""

    succeeded: bool
    skip_class: SkipClass | None = None


@dataclass
class LeadsRunResult:
    """Aggregate result of a consumer run.

    Attributes:
        attempted: number of ACTIVE offers processed (the G-DENOM denominator).
        succeeded: number of fresh, non-empty per-business leads reads.
        skipped_by_class: per-skip-class counts (the EMITted skip signal).
    """

    attempted: int = 0
    succeeded: int = 0
    skipped_by_class: dict[SkipClass, int] = field(default_factory=dict)

    @property
    def total_skipped(self) -> int:
        return sum(self.skipped_by_class.values())


class GrainBridgeLeadsConsumer:
    """Per-business single-tenant leads consumer (WS-CONSUMER)."""

    def __init__(
        self,
        asana_client: Any,
        minter: BusinessTokenMinter,
        data_client_factory: DataClientFactory,
        *,
        metrics_hook: MetricsHook | None = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        leads_days: int = DEFAULT_LEADS_DAYS,
        leads_limit: int = DEFAULT_LEADS_LIMIT,
    ) -> None:
        self._asana_client = asana_client
        self._minter = minter
        self._data_client_factory = data_client_factory
        self._metrics_hook = metrics_hook
        self._max_concurrency = max_concurrency
        self._leads_days = leads_days
        self._leads_limit = leads_limit

    async def run(self, scope: EntityScope | None = None) -> LeadsRunResult:
        """Enumerate ACTIVE offers and read leads per-business.

        Raises:
            MintCredentialError: 401 delegator misconfig (FATAL -- halts run).
            MintScopeError: 403 delegator misconfig (FATAL -- halts run).
        """
        offers = await self._enumerate(scope)
        result = LeadsRunResult(attempted=len(offers))

        if not offers:
            logger.info("grain_bridge_leads_empty_active_set", attempted=0)
            return result

        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def _bounded(offer: dict[str, Any]) -> _OfferResult:
            async with semaphore:
                return await self._process_one(offer)

        # return_exceptions=False: a FATAL delegator misconfiguration
        # (MintCredentialError / MintScopeError) propagates out and halts the
        # run rather than being swallowed as N resolution_miss skips.
        outcomes = await asyncio.gather(*[_bounded(o) for o in offers])

        for outcome in outcomes:
            if outcome.succeeded:
                result.succeeded += 1
            elif outcome.skip_class is not None:
                result.skipped_by_class[outcome.skip_class] = (
                    result.skipped_by_class.get(outcome.skip_class, 0) + 1
                )

        # AC-S3 reconciliation invariant: every attempted offer is accounted.
        assert result.attempted == result.succeeded + result.total_skipped, (
            f"reconciliation invariant violated: attempted={result.attempted} "
            f"succeeded={result.succeeded} skipped={result.total_skipped}"
        )

        logger.info(
            "grain_bridge_leads_completed",
            attempted=result.attempted,
            succeeded=result.succeeded,
            skipped=result.total_skipped,
            skipped_by_class={k.value: v for k, v in result.skipped_by_class.items()},
        )
        return result

    async def _enumerate(self, scope: EntityScope | None) -> list[dict[str, Any]]:
        if scope is not None and scope.has_entity_ids:
            return [{"gid": gid, "name": None} for gid in scope.entity_ids]
        return await enumerate_active_offers(
            self._asana_client,
            logger=logger,
            workflow_id=WORKFLOW_ID,
        )

    async def _process_one(self, offer: dict[str, Any]) -> _OfferResult:
        offer_gid = offer["gid"]

        resolved = await self._resolve(offer_gid)
        if resolved is None:
            self._skip(SkipClass.INACTIVE_OR_EMPTY, "", sub_reason="no_resolution")
            return _OfferResult(succeeded=False, skip_class=SkipClass.INACTIVE_OR_EMPTY)

        office_phone = resolved.office_phone or ""

        # ebid derivation (company_id problems -> resolution_miss; no mint).
        try:
            ebid = compute_ebid(resolved.company_id)
        except EbidInputAbsent:
            self._skip(SkipClass.RESOLUTION_MISS, office_phone, sub_reason="input_absent")
            return _OfferResult(succeeded=False, skip_class=SkipClass.RESOLUTION_MISS)
        except EbidInputNull:
            self._skip(SkipClass.RESOLUTION_MISS, office_phone, sub_reason="input_null")
            return _OfferResult(succeeded=False, skip_class=SkipClass.RESOLUTION_MISS)

        # No read key -> cannot read leads; do not waste a mint.
        if not resolved.office_phone:
            self._skip(SkipClass.INACTIVE_OR_EMPTY, "", sub_reason="no_office_phone")
            return _OfferResult(succeeded=False, skip_class=SkipClass.INACTIVE_OR_EMPTY)

        # Mint the single-tenant per-business token. 401/403 are NOT caught:
        # they propagate as a FATAL run-halt (delegator misconfiguration).
        try:
            token = await self._minter.mint(ebid)
        except MintResolutionMiss:
            self._skip(SkipClass.RESOLUTION_MISS, office_phone, sub_reason="server_404")
            return _OfferResult(succeeded=False, skip_class=SkipClass.RESOLUTION_MISS)
        except MintRateLimited:
            self._skip(SkipClass.MINT_UNAVAILABLE, office_phone, sub_reason="rate_limited")
            return _OfferResult(succeeded=False, skip_class=SkipClass.MINT_UNAVAILABLE)
        except MintCollision:
            self._skip(SkipClass.COLLISION_CONFLICT, office_phone, sub_reason="mint_409")
            return _OfferResult(succeeded=False, skip_class=SkipClass.COLLISION_CONFLICT)
        except MintUnavailable:
            self._skip(SkipClass.MINT_UNAVAILABLE, office_phone, sub_reason="upstream_5xx")
            return _OfferResult(succeeded=False, skip_class=SkipClass.MINT_UNAVAILABLE)

        # Per-business isolation: one provider + one client per business; the
        # JWT business_id dominates the office_phone param (anti-IDOR).
        client = self._data_client_factory(PerBusinessTokenProvider(token))
        try:
            return await self._read_leads(client, office_phone)
        finally:
            await client.close()

    async def _read_leads(
        self,
        client: DataServiceClient,
        office_phone: str,
    ) -> _OfferResult:
        try:
            resp = await client.get_leads_async(
                office_phone,
                days=self._leads_days,
                limit=self._leads_limit,
            )
        except InsightsNotFoundError:
            self._skip(SkipClass.INACTIVE_OR_EMPTY, office_phone, sub_reason="empty_leads")
            return _OfferResult(succeeded=False, skip_class=SkipClass.INACTIVE_OR_EMPTY)
        except CircuitBreakerOpenError:
            self._skip(SkipClass.MINT_UNAVAILABLE, office_phone, sub_reason="read_circuit_open")
            return _OfferResult(succeeded=False, skip_class=SkipClass.MINT_UNAVAILABLE)
        except InsightsServiceError as exc:
            if exc.status_code == 409:
                self._skip(SkipClass.COLLISION_CONFLICT, office_phone, sub_reason="read_409")
                return _OfferResult(succeeded=False, skip_class=SkipClass.COLLISION_CONFLICT)
            self._skip(SkipClass.MINT_UNAVAILABLE, office_phone, sub_reason="read_5xx")
            return _OfferResult(succeeded=False, skip_class=SkipClass.MINT_UNAVAILABLE)

        # Success classification: fresh AND non-empty only.
        if not resp.data:
            self._skip(SkipClass.INACTIVE_OR_EMPTY, office_phone, sub_reason="empty_leads")
            return _OfferResult(succeeded=False, skip_class=SkipClass.INACTIVE_OR_EMPTY)
        if resp.metadata.is_stale:
            # EC-8: a stale-cache hit is NOT a fresh success.
            self._skip(SkipClass.INACTIVE_OR_EMPTY, office_phone, sub_reason="stale")
            return _OfferResult(succeeded=False, skip_class=SkipClass.INACTIVE_OR_EMPTY)
        return _OfferResult(succeeded=True)

    async def _resolve(self, offer_gid: str) -> _ResolvedBusiness | None:
        """Resolve Offer -> parent Business, surfacing company_id (D1)."""
        offer_task = await self._asana_client.tasks.get_async(
            offer_gid,
            opt_fields=["parent", "parent.gid"],
        )
        if not offer_task.parent or not offer_task.parent.gid:
            return None

        from autom8_asana.models.business.base import BusinessEntity

        offer_entity = BusinessEntity(gid=offer_gid)
        offer_entity.parent = offer_task.parent

        async with ResolutionContext(
            self._asana_client,
            trigger_entity=offer_entity,
        ) as ctx:
            business = await ctx.business_async()
            return _ResolvedBusiness(
                gid=business.gid,
                office_phone=business.office_phone,
                vertical=business.vertical,
                company_id=business.company_id,
                name=business.name,
            )

    def _skip(self, klass: SkipClass, office_phone: str, *, sub_reason: str) -> None:
        emit_skip(
            logger,
            self._metrics_hook,
            klass=klass,
            office_phone=office_phone,
            sub_reason=sub_reason,
        )
