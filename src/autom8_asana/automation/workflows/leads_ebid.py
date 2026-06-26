"""Local ebid derivation for the grain-bridge leads consumer.

Per ADR grain-bridge D1/D2: the external_business_id (ebid) is derived LOCALLY
from the resolved Business's ``company_id`` (== chiropractors.guid) using the
canonical ``autom8y_guid.normalize_chiropractor_guid`` transform -- the SAME
transform the producer (auth-mysql-sync) and the data plane pin. asana is the
THIRD pinned consumer; re-derivation would risk silent fleet-wide drift, so the
transform is imported, never re-implemented.

The bootstrap is intact: ``company_id`` is already held on the resolved Business
entity after the Offer->Business hierarchy walk -- NO guid fetch (a fetch would
be a genuine chicken-and-egg break, since the data self-read is tenant-scoped
behind the very token being minted).

Three-state input discriminability (EC-1): ``input_absent`` (None) and
``input_null`` (empty/whitespace) are observably distinct from a server-side
``server_404`` -- and NO exchange-business call is made with an empty ebid.
"""

from __future__ import annotations

from autom8y_guid import normalize_chiropractor_guid

from autom8_asana.errors import AsanaError


class EbidInputError(AsanaError):
    """company_id cannot produce an ebid (absent or null).

    Both subclasses map to ``SkipClass.RESOLUTION_MISS`` with a distinct
    sub_reason; neither reaches exchange-business with an empty ebid.
    """


class EbidInputAbsent(EbidInputError):
    """company_id is None -- the attribute is unset on the resolved Business.

    Maps to ``resolution_miss(input_absent)``.
    """


class EbidInputNull(EbidInputError):
    """company_id is present but empty / whitespace-only.

    Maps to ``resolution_miss(input_null)``.
    """


def compute_ebid(company_id: str | None) -> str:
    """Derive the ebid from a Business's company_id via the canonical transform.

    Args:
        company_id: the resolved Business's ``company_id`` (== guid). UUID
            strings pass through lowercased; numeric strings (incl. the 116
            cohort) convert to uuid5 under the frozen namespace.

    Returns:
        The normalized ebid string.

    Raises:
        EbidInputAbsent: company_id is None.
        EbidInputNull: company_id is empty or whitespace-only.
    """
    if company_id is None:
        raise EbidInputAbsent("company_id absent on resolved Business (input_absent)")
    try:
        normalized, _was_converted = normalize_chiropractor_guid(company_id)
    except ValueError as exc:
        # normalize raises ValueError on empty / whitespace-only input.
        raise EbidInputNull(
            f"company_id null/empty on resolved Business (input_null): {exc}"
        ) from exc
    return normalized
