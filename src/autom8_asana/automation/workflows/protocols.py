"""Protocols for bridge workflow data sources and format engines.

Per ADR-bridge-data-source-protocol: DataSource -- minimal protocol
with a single required method (is_healthy).

Per ADR-bridge-format-engine: FormatEngine -- platform protocol for
bridge output formatters with render(data) -> bytes.

Protocol Alignment with autom8y-interop (H-003)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Per ADR-bridge-dispatch-model: DataSource is the bridge platform's
health-check protocol. It overlaps with, but is intentionally distinct
from, the interop SDK's protocol hierarchy:

.. list-table:: Protocol Coverage Map
   :header-rows: 1

   * - Bridge Protocol
     - Interop Protocol
     - Overlap
     - Gap
   * - ``DataSource.is_healthy()``
     - ``DataReadProtocol.health_check()``
     - Health-check concept
     - Different signatures: ``is_healthy()`` raises on failure
       vs ``health_check()`` returns ``dict[str, Any]``
   * - (bridge-specific) ``get_insights_async()``
     - ``DataInsightProtocol.get_insight()``
     - Insight fetching
     - Bridge client has richer params (batch, caching, async)
   * - (bridge-specific) ``get_reconciliation_async()``
     - None
     - **GAP**: No interop reconciliation protocol
     - Requires upstream ``DataReconciliationProtocol`` PR
   * - (bridge-specific) ``get_export_csv_async()``
     - None
     - **GAP**: No interop export protocol
     - Requires upstream PR

**Migration status**: Do NOT migrate ``DataServiceClient`` to interop
protocols. Interop covers ~30% of the client surface. This protocol
file documents alignment pressure for future convergence. See
INTEGRATE-ecosystem-dispatch Section 1.4 for the phased plan.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DataSource(Protocol):
    """Minimal protocol for bridge data sources.

    Any object providing a health-check interface can serve as a data
    source for the BridgeWorkflowAction base class validate_async()
    method.

    Concrete data-fetching methods (e.g., get_insights_async,
    get_export_csv_async) are bridge-specific and NOT part of this
    protocol.

    Per ADR-bridge-data-source-protocol.

    Interop alignment (H-003): This protocol's ``is_healthy()`` method
    overlaps conceptually with ``autom8y_interop.data.DataReadProtocol
    .health_check()``, but the signatures differ intentionally:

    - ``DataSource.is_healthy()`` -> ``None`` (raises on failure)
    - ``DataReadProtocol.health_check()`` -> ``dict[str, Any]``

    When interop protocols gain async context manager support and
    reconciliation endpoints, a unified health-check adapter may bridge
    both signatures. Until then, DataSource remains the bridge platform's
    canonical health-check contract.
    """

    async def is_healthy(self) -> None:
        """Check data source health.

        Raises CircuitBreakerOpenError (or compatible) if the source
        is unavailable. Returns normally if the source is healthy.
        """
        ...


@runtime_checkable
class FormatEngine(Protocol):
    """Platform protocol for bridge output formatters.

    Bridges are not required to use this protocol -- they may format
    inline in process_entity(). FormatEngine is provided as a composable
    unit for bridges whose formatting logic is substantial enough to
    warrant isolation (e.g., InsightsExport's 1105-line HTML formatter).

    The data: dict[str, Any] input is intentionally loose -- the actual
    shape of data is a bridge-domain concern, not a platform concern.
    The protocol says "given some data, produce bytes." Concrete engine
    implementations type-check their input internally.

    Per ADR-bridge-format-engine.
    Per TDD-data-attachment-bridge-platform Section 5.2.
    """

    content_type: str
    file_extension: str

    def render(self, data: dict[str, Any]) -> bytes:
        """Transform domain-specific data dict into file bytes.

        Args:
            data: Domain-specific data dictionary. Shape is determined
                by the concrete engine, not this protocol.

        Returns:
            File content as bytes, ready for upload.
        """
        ...
