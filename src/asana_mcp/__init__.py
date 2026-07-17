"""asana_mcp — FastMCP sidecar package for autom8y-asana (asana-mcp-v1).

THROWAWAY / REFERENCE-POSTURE prototype (charter constraint 8: no fleet-code
promotion before the §4 probe rules COMMIT). This package is deliberately NOT in
the shipped wheel (`pyproject.toml` [tool.hatch.build.targets.wheel] packages).

Sprint ownership (frozen MOUNT-SEAM, autom8y-asana/.sos/wip/asana-mcp-v1.mount-seam.md):
  - sprint-2 owns the skeleton: create_server(), Settings, the concrete SidecarContext.
  - sprint-3 (this) owns ONLY the composite write tool module + its exposure gate.
  - sprint-6 assembles: create_server() -> register(...) per tool -> instrument(...).

Import-safety (C9a): no import-time settings/IO/network anywhere in this package.
"""
