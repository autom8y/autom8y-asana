"""Tool modules for the asana_mcp sidecar.

Two-tier grain (C1):
* ``discovery`` — thin, FleetQuery-shaped discovery tier (list_entity_types,
  describe_entity).
* ``query`` / ``resolve`` — rich per-satellite tier authored from the native
  RowsRequest / AggregateRequest / ResolutionRequest models.

Each module exposes ``register(mcp, ctx)`` (mount-seam item 2). sprint-2 ships
the READ tools (1-5); tool 6 (match_business) is surface-not-POC and only
stub-noted (see ``_match_business_stub``).
"""
