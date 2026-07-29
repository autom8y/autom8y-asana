"""Substrate-v2 Seam 3 — REBUILD (infra). RC-E.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 3. Protocol signatures
ONLY; the stage-validate-swap body is owned by S6.

``PacedAsanaFetcher`` and ``AcceptancePredicates`` are NAMED in §4 as injected
capabilities WITHOUT a drawn method surface — they land here as placeholder
Protocols for their owner sprints to draw (the method surface is emergent).
``RebuildResult`` is a referenced-but-undrawn return type landed as an
owner-filled placeholder so the frozen ``Rebuilder`` signature resolves.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from autom8_asana.substrate.identity import ArtifactId


class RebuildOutcome(Enum):
    """CLOSED rebuild outcome taxonomy."""

    SWAPPED = "swapped"
    STAGED_REJECTED = "staged_rejected"
    FETCH_REFUSED = "fetch_refused"


class RebuildResult:
    """Envelope returned by ``Rebuilder.rebuild``. Seam 3, FROZEN v1.0.

    Referenced but not drawn in §4 — SEAM-0 lands the NAME so the frozen
    ``Rebuilder`` signature resolves under mypy; the field surface (e.g. the
    ``RebuildOutcome``) is owned by S6. No fields are invented here.
    """


class PacedAsanaFetcher(Protocol):
    """Injected paced live-Asana fetcher ([H11]). Seam 3, FROZEN v1.0.

    §4 names this capability without drawing a method surface; the method surface
    is owned by S6 — the rebuilder delegates to the existing paced primitive
    (PE G6), never re-implements it.
    """


class AcceptancePredicates(Protocol):
    """Injected staged-version validator (validate-before-swap; [H13]/C9). Seam 3, FROZEN v1.0.

    §4 names this capability without drawing a method surface; the method surface
    (e.g. C9's ``validate()`` minting a ValidationReceipt) is a CARRY-TO-BUILD
    owned by S4/S6 — deliberately NOT designed into the S1 frozen contract (§11).
    """


class Rebuilder(Protocol):
    """Stage-validate-swap rebuilder (RC-E). Seam 3, FROZEN v1.0.

    ``Rebuilder`` and ``SubstrateReader`` are DISTINCT types ([H9]) — the
    rebuilder exposes no serve-read and the reader exposes no write.
    """

    async def rebuild(
        self,
        aid: ArtifactId,
        fetch: PacedAsanaFetcher,
        validate: AcceptancePredicates,
    ) -> RebuildResult:
        """ORDERED, swap LAST:
        1. read prior version's per-section provenance (each section's last real content-fetch instant).
        2. for each section: a cheap structural probe MAY decide re-fetch; a section older than (SLA - cadence) MUST re-fetch.
           a re-fetch pulls value-bytes from LIVE Asana (paced) and advances THAT section's instant to now. reused sections keep their instant. (C1)
        3. materialize the WHOLE version; content_digest = canonical_digest(frame); built_from_live_at = MIN over section instants. (C1)
        4. store.stage_version(...) — staging only, never the pointer.
        5. validate(staged) — population floor + digest self-consistency + proof well-formedness ([H13]).
        6. on PASS: store.swap_pointer(aid, staged, if_match=...) — the single atomic CAS swap. on FAIL: discard staging, live untouched.
        """
        ...
