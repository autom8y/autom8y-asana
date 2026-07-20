"""``asana_mcp.timeouts`` — the SINGLE timeout source-of-truth for the sidecar.

Contract: ``autom8y-asana/.sos/wip/asana-mcp-v1.s4-seam-contract.md`` §1 (C4
one-contract; R2 timeout-inversion scar guard) + checklist items 6/7/8. Named
after the ``autom8y-data`` precedent (``analytics/core/timeouts.py``) that encodes
``query < middleware < ALB`` as importable constants (SVR-C1). instrument() reads
these SAME constants — there is NO second timeout definition site in ``asana_mcp``
(checklist item 7).

MIRROR DISCIPLINE (contract §1.3; TENSION-016 gap NOT reproduced): the satellite
bounds below are MIRRORED here with source-anchor comments because the sidecar
MUST NOT import satellite settings (constraint 5). Cross-deploy drift of these
mirrors is a D10 behavioral-contract-test concern (ledgered sprint-1); this module
carries the in-repo invariant + the anchors now.

IMPORT-SAFE: constants + frozen dataclass + pure functions only. ``from_env`` reads
``ASANA_MCP_*`` at CALL time (never import). No I/O, no network, no settings.

THE CHAIN THAT MUST HOLD (contract §1.2):
    satellite-honest(30) < HTTP(45) < TOOL(50) < ALB_floor(60), and CONNECT(5) < HTTP.
Every layer that ANSWERS is faster than every layer that WAITS on it; every layer
that WAITS gives up before the transport beneath it is killed. Cold-frame 503s thus
surface as typed satellite codes (retryable, never auth-shaped), never as
client-timeout mush.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

# --- MIRROR constants (cannot import satellite settings — constraint 5) --------
#: Satellite honest give-up bound: 503 CACHE_BUILD_IN_PROGRESS build-wait.
#: MIRROR of autom8y-asana/src/autom8_asana/settings.py:259-267 (SVR-C5). HTTP
#: MUST exceed this so honest cold-frame 503s always arrive as typed responses.
SATELLITE_HONEST_BOUND_S = 30.0
#: ALB idle timeout floor. MIRROR of the RC001 scar + design-constraints floor
#: (autom8y-data/.../timeouts.py:11-13, .know/design-constraints.md:142; SVR-C2).
#: The sidecar's own typed guard MUST fire before this opaque proxy kill.
ALB_IDLE_TIMEOUT_FLOOR_S = 60.0

# --- Sidecar-owned defaults (contract §1.2 REQUIRED values) --------------------
CONNECT_TIMEOUT_DEFAULT_S = 5.0  # mirrors satellite SDK connect=5 (config.py:458)
HTTP_TIMEOUT_DEFAULT_S = 45.0  # band (30, 60) exclusive
TOOL_TIMEOUT_DEFAULT_S = 50.0  # band (HTTP, 60) exclusive; outermost instrument() guard
#: Per-call serialization overhead reserved between the tool guard and the http
#: deadline: effective_http(tool) = tool - overhead (contract §1.2 overrides row).
TOOL_OVERHEAD_S = 2.0
#: Per-tool override floor (contract §1.2: overrides per-tool >= 10, <= default).
MIN_OVERRIDE_S = 10.0

ENV_CONNECT = "ASANA_MCP_HTTP_CONNECT_TIMEOUT_S"
ENV_HTTP = "ASANA_MCP_HTTP_TIMEOUT_S"
ENV_TOOL = "ASANA_MCP_TOOL_TIMEOUT_S"
ENV_OVERRIDES = "ASANA_MCP_TOOL_TIMEOUT_OVERRIDES"


class ConfigurationError(ValueError):
    """A timeout configuration violates the R2 anti-inversion invariant (§1.3)."""


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"env {name}={raw!r} is not a float") from exc


def effective_http(tool_timeout_s: float) -> float:
    """The effective http deadline reserved inside a tool guard (contract §1.2)."""
    return tool_timeout_s - TOOL_OVERHEAD_S


@dataclass(frozen=True)
class TimeoutConfig:
    """Resolved sidecar timeout constants (the SoT instance instrument() reads)."""

    connect_s: float = CONNECT_TIMEOUT_DEFAULT_S
    http_s: float = HTTP_TIMEOUT_DEFAULT_S
    tool_s: float = TOOL_TIMEOUT_DEFAULT_S
    overrides: Mapping[str, float] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> TimeoutConfig:
        raw_overrides = os.environ.get(ENV_OVERRIDES, "") or "{}"
        try:
            parsed = json.loads(raw_overrides)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"env {ENV_OVERRIDES}={raw_overrides!r} is not valid JSON"
            ) from exc
        overrides = {str(k): float(v) for k, v in parsed.items()}
        return cls(
            connect_s=_env_float(ENV_CONNECT, CONNECT_TIMEOUT_DEFAULT_S),
            http_s=_env_float(ENV_HTTP, HTTP_TIMEOUT_DEFAULT_S),
            tool_s=_env_float(ENV_TOOL, TOOL_TIMEOUT_DEFAULT_S),
            overrides=overrides,
        )

    def tool_timeout_for(self, tool_name: str) -> float:
        return self.overrides.get(tool_name, self.tool_s)


def validate_timeout_config(cfg: TimeoutConfig) -> None:
    """Fail loud unless the cascade holds (contract §1.3; checklist items 6/8).

    Asserts, in order:
      * ``CONNECT < HTTP < TOOL < ALB_IDLE_TIMEOUT_FLOOR_S``  (outer-fires-first,
        the sidecar guard strictly inside the ALB floor)
      * ``HTTP > SATELLITE_HONEST_BOUND_S``  (honest 503s always arrive typed)
      * every per-tool override ``t``: ``MIN_OVERRIDE_S <= t <= TOOL`` and
        ``effective_http(t) < t``  (per-call ordering preserved)
    The RC001 scar value ``HTTP=90`` is rejected here (90 !< TOOL and 90 > ALB).
    """
    if not (cfg.connect_s < cfg.http_s < cfg.tool_s < ALB_IDLE_TIMEOUT_FLOOR_S):
        raise ConfigurationError(
            "timeout inversion (R2/RC001): require CONNECT < HTTP < TOOL < "
            f"ALB_floor({ALB_IDLE_TIMEOUT_FLOOR_S}); got CONNECT={cfg.connect_s}, "
            f"HTTP={cfg.http_s}, TOOL={cfg.tool_s}. Every waiting layer must give "
            "up before the transport beneath it is killed."
        )
    if not (cfg.http_s > SATELLITE_HONEST_BOUND_S):
        raise ConfigurationError(
            f"HTTP timeout {cfg.http_s}s must exceed the satellite honest bound "
            f"{SATELLITE_HONEST_BOUND_S}s so cold-frame 503s always arrive typed "
            "(not as client-timeout mush)"
        )
    for tool, t in cfg.overrides.items():
        if not (MIN_OVERRIDE_S <= t <= cfg.tool_s):
            raise ConfigurationError(
                f"tool override '{tool}'={t}s out of band [{MIN_OVERRIDE_S}, {cfg.tool_s}]"
            )
        if not (effective_http(t) < t):
            raise ConfigurationError(
                f"tool override '{tool}'={t}s: effective_http({effective_http(t)}) not < tool ({t})"
            )
