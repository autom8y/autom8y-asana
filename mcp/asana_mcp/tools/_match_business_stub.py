"""tool 6 — match_business: SURFACE-NOT-POC (shape §0 nuance). STUB-NOTE ONLY.

The charter §5.3 grant scopes the POC to read tools 1-5. The 6th curated tool,
``match_business`` (POST /v1/matching/query — fuzzy scored candidates on dirty
identifiers, spike table :114), is part of the read SURFACE but explicitly NOT
part of the POC. It rides as a named extension.

This module is a deliberate stub: it is NOT registered by ``create_server`` and
is NOT implemented. It exists to record the scope boundary in the code, so a
future builder (or sprint-6 harness) does not mistake tools 1-5 for the full
surface. Do NOT build this in sprint-2.
"""

from __future__ import annotations

STUB_NOTE = (
    "match_business (tool 6) is surface-not-POC per shape §0. Backing endpoint: "
    "POST /v1/matching/query. Not built in sprint-2; rides as a named extension "
    "(alongside +7 offer_timeline, +8 export_accounts, resources R1/R2)."
)


def register(mcp: object, ctx: object) -> None:  # pragma: no cover - intentionally inert
    """Intentionally NOT registered. See module docstring / STUB_NOTE."""
    raise NotImplementedError(STUB_NOTE)
