"""GFR tiered truth-source — by-guid verify, NOT the office_phone join (INVARIANT I7; TDD §7).

Two tiers (TDD §7.1):

* **Tier-1 (default, ``TruthTier.CACHE``)**: the local asana-cache ``company_id``
  (``cf:Company ID``, ``business.py:8-13``) read off the GID-EXACT Business row.
  Fast path; ``as_of`` is the frame watermark. This is the engine's normal read
  and does not route through this module.
* **Tier-2 (on demand, ``TruthTier.VERIFIED``)**: authoritative verification via
  ``get_business_by_guid_async(guid)`` (``autom8y-core data_service.py``) — the
  SAME by-guid record the inbound resolver consumes (TDD §11.4). It is NOT the
  ``office_phone`` analytics join (``query/engine.py:701`` defaults its key to
  ``office_phone`` and returns metrics with no guid/company_id column — it cannot
  verify identity, B4 / INVARIANT I7).

Dependency inversion (DIP): GFR depends on the ``ByGuidVerifier`` Protocol, not a
concrete core client. Any object exposing ``get_business_by_guid_async`` satisfies
it (the autom8y-core ``DataServiceClient``/``DataReadClient`` in production; a mock
in tests). GFR adds NO new cross-service client (TDD §7.2).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from autom8y_log import get_logger

logger = get_logger(__name__)


@runtime_checkable
class ByGuidVerifier(Protocol):
    """Port for the authoritative by-guid identity lookup (INVARIANT I7).

    The single method GFR's tier-2 verify needs. Implemented in production by the
    autom8y-core data-service client (``get_business_by_guid_async``,
    ``data_service.py:434``). Returns the authoritative record on hit, ``None`` on
    miss (the endpoint uses a ``200 + data=null`` envelope, never 404).
    """

    async def get_business_by_guid_async(self, guid: str) -> object | None:
        """Return the authoritative business record for ``guid``, or ``None``."""
        ...


async def verify_company_id_async(
    company_id: str,
    verifier: ByGuidVerifier,
) -> bool:
    """Verify a tier-1 ``company_id`` against the authoritative by-guid record.

    Treats the tier-1 ``company_id`` (== chiropractors.guid, the UUID before ``@``
    in the appointments address) as the candidate guid and asserts the
    authoritative ``get_business_by_guid_async(company_id)`` returns a record
    whose guid matches. A None record (miss) or a guid mismatch means the tier-1
    value does NOT round-trip to a single authoritative tenant.

    INVARIANT I7: this is the BY-GUID port, never the office_phone analytics join.

    Args:
        company_id: The tier-1 ``company_id`` to verify (candidate guid).
        verifier: A ``ByGuidVerifier`` (the autom8y-core data-service client).

    Returns:
        True if the authoritative record exists and its guid matches
        ``company_id``; False on miss or mismatch.
    """
    record = await verifier.get_business_by_guid_async(company_id)
    if record is None:
        logger.info(
            "GFR tier-2: by-guid miss",
            extra={"company_id": company_id},
        )
        return False
    record_guid = getattr(record, "guid", None)
    matched = record_guid == company_id
    if not matched:
        logger.warning(
            "GFR tier-2: by-guid record guid mismatch",
            extra={"company_id": company_id, "record_guid": record_guid},
        )
    return matched
