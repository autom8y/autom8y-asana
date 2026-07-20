"""Settings for the asana_mcp sidecar (env prefix ``ASANA_MCP_*``).

Owned by sprint-2 per the FROZEN mount-seam ("settings dataclass is YOURS").
Budget-partition vars (B4) are sprint-4's — an extension point is marked below,
deliberately NOT implemented here.

C9a import-safety: this module performs NO IO at import time. Every environment
read happens inside :meth:`Settings.from_env`, which ``create_server`` calls at
call time, never at import.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# autom8y_core.AsanaServiceConfig.DEFAULT_URL — kept as a literal so importing
# this module does NOT import autom8y_core (constraint-5 fence + C9a).
_DEFAULT_BASE_URL = "https://asana.api.autom8y.io"


@dataclass(frozen=True)
class Settings:
    """Resolved sidecar configuration. Immutable; built at call time."""

    base_url: str = _DEFAULT_BASE_URL
    ready_path: str = "/ready"
    request_timeout_s: float = 30.0
    connect_timeout_s: float = 5.0
    # C3/C9 readiness posture. Default fail-CLOSED: a readiness-probe transport
    # error is treated as "not ready" -> a retryable cache-warming refusal, NEVER
    # auth-shaped. sprint-4 finalizes the C9 fail-open/fail-closed declaration.
    readiness_fail_open: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        """Resolve settings from the environment AT CALL TIME (never at import)."""
        base_url = (
            os.environ.get("ASANA_MCP_BASE_URL")
            or os.environ.get("AUTOM8Y_ASANA_URL")  # autom8y_core AsanaServiceConfig fallback
            or _DEFAULT_BASE_URL
        )
        return cls(
            base_url=base_url,
            ready_path=os.environ.get("ASANA_MCP_READY_PATH", "/ready"),
            request_timeout_s=float(os.environ.get("ASANA_MCP_REQUEST_TIMEOUT_S", "30.0")),
            connect_timeout_s=float(os.environ.get("ASANA_MCP_CONNECT_TIMEOUT_S", "5.0")),
            readiness_fail_open=os.environ.get("ASANA_MCP_READINESS_FAIL_OPEN", "").lower()
            in {"1", "true", "yes"},
        )

    # --- sprint-4 extension point (B4 budget-partition) ----------------------
    # sprint-4 owns ASANA_MCP_BUDGET_* (static partition across the shared-PAT's
    # three consumer classes: warmers / API / MCP) and the MCP-side rate cap.
    # sprint-2 deliberately does NOT define these — they are s4's partition vars.
