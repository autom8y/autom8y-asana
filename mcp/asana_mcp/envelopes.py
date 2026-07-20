"""Local response-envelope helpers for the asana_mcp sidecar.

Re-implemented HERE (NOT imported from ``autom8y_core._envelopes``, a private
S1-boundary module) to keep the constraint-5 fence crisp: asana_mcp imports only
the sanctioned autom8y_core bridge surface (TokenManager) and NEVER reaches into
private internals or the autom8_asana domain SDK.

Wire shapes — verified live against ``autom8_asana/query/models.py`` and
``api/routes/{query,resolver}.py`` at HEAD f3d8eec1:

* Introspection GETs (``/v1/query/entities``, ``/{type}/fields``,
  ``/{type}/relations``) carry ``x-fleet-envelope-exempt`` and return a SINGLE
  envelope::

      {"data": [ ... ]}

* Execution POSTs (``/rows``, ``/aggregate``) and ``/v1/resolve/{type}`` return
  the fleet ``SuccessResponse[T]`` DOUBLE envelope::

      {"data": {"data": [...rows...], "meta": {...honesty...}}, "meta": {...req...}}

  The OUTER ``data`` holds the RowsResponse/AggregateResponse (resolve: its
  inner payload is ``{"results": [...], "meta": {...}}``). The INNER ``meta``
  carries the honesty attestations (``RowsMeta.stale_served`` / ``honest_empty``
  / ``contract_complete`` — SVR-5).
"""

from __future__ import annotations

from typing import Any

# Honesty-attestation fields the C6 convention obliges the tool layer to surface
# to the LLM UNWRAPPED-and-VISIBLE. Live in RowsMeta at HEAD (SVR-5). Only those
# actually emitted by a given endpoint are lifted — sprint-2 never fabricates a
# field an endpoint did not return (AggregateMeta emits only ``stale_served``).
HONESTY_FIELDS: tuple[str, ...] = (
    "stale_served",
    "honest_empty",
    "contract_complete",
    "honest_contract_complete",
    "unservable_required_columns",
)


def unwrap_outer(body: Any) -> Any:
    """Strip ONE SuccessResponse envelope layer if present.

    Mirrors ``autom8y_core._unwrap_envelope``: ``{"data": X, ...} -> X``; else
    ``body`` unchanged. Idempotent on an already-unwrapped payload.
    """
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def extract_honesty(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Return only the honesty attestations actually present in an inner ``meta``."""
    if not isinstance(meta, dict):
        return {}
    return {key: meta[key] for key in HONESTY_FIELDS if key in meta}
