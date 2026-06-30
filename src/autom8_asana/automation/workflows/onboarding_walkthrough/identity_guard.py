"""W1 -- GFR by-GUID structural identity guard (GATE-1, UPSTREAM, resolve-CORRECTNESS).

Per ADR-contente-onboarding-walkthrough-batch-sweep §Decision 1 + TDD §W1.

The onboarding-walkthrough ``process_entity`` resolves the gated routing address
from the task's ``office_phone`` via the autom8y-core SDK (Source A, the PHONE
leg). A phone collision that maps two clinics to one address would mint a guid
that points at the WRONG tenant -- and the producer's presence check + the T7
exclusivity oracle would both still pass (the artifact correctly carries the
resolved address; the resolve itself is wrong). This module closes that
resolve-CORRECTNESS hole UPSTREAM of the freeze.

The guard compares two INDEPENDENTLY-derived guids (Pythia Fork-1 -- the guard is
sound ONLY because the two are disjoint, never a tautology):

* **Source A (PHONE)** -- ``extract_address_guid``: the UUID-before-``@`` in the
  SDK-(phone)-resolved address. Derivation: ``office_phone -> SDK join -> address``.
* **Source B (PARENT-CHAIN)** -- ``anchor_company_id``: ``company_id`` read off the
  GID-EXACT Business row that GFR reaches by walking the task's OWN parent chain
  (``gid -> current.parent.gid -> ... -> business_gid``). Derivation never reads
  ``office_phone`` (``guard.py`` FORBIDS the ``office_phone`` identity join key;
  the by-GUID truth-source is INVARIANT I7).

G-PROPAGATE: this module calls ``gfr.resolve_async`` (the SOLE by-GUID identity
substrate) -- it does NOT reimplement parent-chain walking, gid-exact reads, or
by-guid verification. The guid extract is a ``str.split("@")`` on the resolver's
OWN output, not a re-derivation of the canonical address form (the Node producer
remains the sole address formatter, G-PROPAGATE P3).

The workflow consumes both helpers and gid-exact-compares; a mismatch fail-closes
to ``skipped(guid_anchor_mismatch)`` (NO freeze, NO upload), an unresolvable
anchor to ``skipped(anchor_unresolved)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from autom8_asana.resolution import gfr
from autom8_asana.resolution.gfr.models import TruthTier

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.query.engine import QueryEngine
    from autom8_asana.resolution.gfr.truth_source import ByGuidVerifier

# The tenant-identity field GFR resolves off the gid-exact Business row. A module
# constant so the request field name and any assertion share one source of truth.
_COMPANY_ID_FIELD = "company_id"


def extract_address_guid(gated_address: str) -> str:
    """Return the UUID-before-``@`` of the gated routing address (Source A).

    The SDK-(phone)-resolved address is ``{guid}@appointments.contenteapp.com``;
    the embedded guid is the substring before the first ``@``, lowercased so the
    gid-exact comparison is case-insensitive (canonical guids are lowercase v4,
    but the verifier must fail-CLOSED on a case-variant, never fail to SEE it --
    mirroring ``tenant_binding.py`` casefold-at-the-boundary discipline).

    Args:
        gated_address: the canonical routing address resolved by the SDK PHONE leg.

    Returns:
        The lowercased UUID local-part (Source A guid).
    """
    return gated_address.split("@", 1)[0].lower()


async def anchor_company_id(
    *,
    task_gid: str,
    client: AsanaClient,
    query_engine: QueryEngine,
    verifier: ByGuidVerifier | None = None,
) -> str:
    """Return the parent-chain-anchored, gid-exact ``company_id`` (Source B).

    Delegates to ``gfr.resolve_async`` (the SOLE by-GUID substrate): GFR walks the
    task's OWN parent chain to the Business root and reads ``company_id`` off the
    GID-EXACT Business row (``join=None``; INVARIANT I2 -- structurally incapable
    of reaching the ``office_phone`` dedup). ``scalar=True`` enforces single-row
    cardinality (INVARIANT I5); the value is lowercased to match Source A.

    Args:
        task_gid: the task's own gid (GFR anchors from this by parent-chain walk).
        client: AsanaClient threaded to GFR's single entry fetch.
        query_engine: the substrate QueryEngine GFR consumes for the gid-exact read.
        verifier: optional tier-2 by-GUID verifier; when provided, GFR verifies
            the tier-1 value against the authoritative by-guid record (INVARIANT
            I7 -- the by-GUID port, NEVER the office_phone analytics join).

    Returns:
        The lowercased ``company_id`` string (Source B guid).

    Raises:
        gfr.UnresolvedError: the parent chain cannot reach a Business root
            (``no-identity-path``), the anchored business row is absent
            (``business-row-not-found``), or the entry type is undetectable.
        Other ``GfrError`` subclasses (GuardViolationError on identity-path purity
            drift, AmbiguousCardinalityError on a non-single-row result) propagate;
            the workflow catches the ``GfrError`` base and fail-closes.
    """
    result = await gfr.resolve_async(
        task_gid,
        [_COMPANY_ID_FIELD],
        client=client,
        query_engine=query_engine,
        truth_tier=TruthTier.VERIFIED if verifier is not None else TruthTier.CACHE,
        scalar=True,
        verifier=verifier,
    )
    # scalar=True guarantees exactly one row; read the single row's company_id.
    return str(result.scalar()[_COMPANY_ID_FIELD].value).lower()


def mask_guid(guid: str) -> str:
    """Mask a guid to its first 8 hex chars (forensic breadcrumb, never the full guid).

    Enough to identify the implicated tenant against the DB during an incident
    without spilling a full (wrong-)tenant guid into logs/errors. Mirrors
    ``tenant_binding._mask_addr``; the masked prefix is lowercase, the form an
    operator matches against the lowercase-guid DB.

    Args:
        guid: a tenant guid (Source A or Source B).

    Returns:
        The first 8 chars plus an ellipsis (e.g. ``d167d635…``).
    """
    return f"{guid[:8]}…"
