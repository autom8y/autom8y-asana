"""``asana_mcp`` — FastMCP sidecar package for autom8y-asana (asana-mcp-v1).

IMPORT-SAFETY INVARIANT (charter §3 technical floor; slate C9a; SCAR-CW-001):
    Importing ``asana_mcp`` or any submodule MUST NOT read settings, touch the
    filesystem/network, or instantiate a client. All configuration resolves at
    CALL time (mount-seam v1 item 1). This ``__init__`` is a deliberately EMPTY
    package marker so that importing ``asana_mcp.observability`` (sprint-4) does
    not force-import the sprint-2 skeleton (``create_server``) or the sprint-3
    tool modules — each sub-surface stays independently import-safe.

OWNERSHIP: the server skeleton (``create_server``, ``Settings`` dataclass, tool
    ``register`` modules) is owned by sprint-2/sprint-3. Sprint-4 owns ONLY the
    ``asana_mcp.observability`` overlay. If sprint-2's skeleton PR also authors
    this ``__init__``, KEEP IT EMPTY (no eager submodule imports) to preserve the
    import-safety invariant.
"""
