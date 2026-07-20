"""``asana_mcp`` — FastMCP sidecar package for autom8y-asana (asana-mcp-v1).

THROWAWAY / REFERENCE-POSTURE prototype (charter constraint 8: no fleet-code
promotion before the §4 probe rules COMMIT). Deliberately NOT in the shipped
wheel (``pyproject.toml`` [tool.hatch.build.targets.wheel] packages).

IMPORT-SAFETY INVARIANT (charter §3 technical floor; slate C9a; SCAR-CW-001):
    Importing ``asana_mcp`` or any submodule MUST NOT read settings, touch the
    filesystem/network, or instantiate a client. All configuration resolves at
    CALL time (mount-seam v1 item 1). This ``__init__`` is a deliberately EMPTY
    package marker so each sub-surface stays independently import-safe — no
    eager submodule imports, ever.

Sprint ownership (frozen MOUNT-SEAM, .sos/wip/asana-mcp-v1.mount-seam.md):
    sprint-2 owns the skeleton (``create_server``, Settings, SidecarContext);
    sprint-3 owns ONLY the composite write tool module + its exposure gate;
    sprint-4 owns ONLY the ``asana_mcp.observability`` overlay;
    sprint-6 assembles: create_server() -> register(...) -> instrument(...).
"""
