"""Static fences — two-sided; checklist items 14 (constraint-5) & 7 (one SoT).

Constraint-5: no domain-SDK import and no direct Asana endpoint anywhere in
asana_mcp. One-SoT: timeout constants are defined ONLY in asana_mcp/timeouts.py and
observability.py imports them (no second definition site).
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src" / "asana_mcp"
_IMPORT_DOMAIN = re.compile(r"^\s*(import|from)\s+autom8_asana", re.MULTILINE)
# Ban-scanner over SOURCE TEXT (not URL sanitization): any occurrence of the
# endpoint literal in sidecar source is a constraint-5 violation, so substring
# over-matching is the intended, stricter direction. Regex form keeps the
# scanner style consistent with _IMPORT_DOMAIN (and outside CodeQL's
# py/incomplete-url-substring-sanitization pattern, which mis-read the old
# `in` check as an allowlist).
_ASANA_ENDPOINT = re.compile(r"app\.asana\.com")


def _py_files() -> list[Path]:
    return sorted(_SRC.glob("*.py"))


# --- constraint-5: no domain-SDK import statement anywhere in asana_mcp ---
def test_no_domain_sdk_import() -> None:
    offenders = [f.name for f in _py_files() if _IMPORT_DOMAIN.search(f.read_text())]
    assert offenders == [], f"domain-SDK import found in {offenders}"


# --- constraint-5: no direct Asana endpoint literal ---
def test_no_direct_asana_endpoint() -> None:
    offenders = [f.name for f in _py_files() if _ASANA_ENDPOINT.search(f.read_text())]
    assert offenders == [], f"direct Asana endpoint found in {offenders}"


# --- teeth: the same scanner bites on a fixture that DOES import the domain SDK ---
def test_domain_import_scanner_has_teeth() -> None:
    violating = "from autom8_asana.query.models import RowsMeta\n"
    clean = "from asana_mcp.timeouts import TimeoutConfig\n"
    assert _IMPORT_DOMAIN.search(violating) is not None  # bites on the violation
    assert _IMPORT_DOMAIN.search(clean) is None  # passes the clean import


# --- one timeout SoT: constants defined only in timeouts.py; observability imports them ---
def test_one_timeout_sot() -> None:
    obs_src = (_SRC / "observability.py").read_text()
    assert "from asana_mcp.timeouts import" in obs_src  # reads the SoT
    # no redefinition of the mirror/timeout constants in observability.py
    for const in (
        "ALB_IDLE_TIMEOUT_FLOOR_S =",
        "SATELLITE_HONEST_BOUND_S =",
        "HTTP_TIMEOUT_DEFAULT_S =",
        "TOOL_TIMEOUT_DEFAULT_S =",
    ):
        assert const not in obs_src, f"timeout constant redefined in observability.py: {const}"
    # they ARE defined in timeouts.py
    to_src = (_SRC / "timeouts.py").read_text()
    assert "ALB_IDLE_TIMEOUT_FLOOR_S = 60.0" in to_src
    assert "SATELLITE_HONEST_BOUND_S = 30.0" in to_src


def test_env_prefix_discipline() -> None:
    """Checklist item 16: every new env var is ASANA_MCP_*."""
    import asana_mcp.observability as o
    import asana_mcp.timeouts as t

    for mod in (o, t):
        env_values = [v for n, v in vars(mod).items() if n.startswith("ENV_")]
        assert env_values, f"no ENV_ constants found in {mod.__name__}"
        for v in env_values:
            assert isinstance(v, str) and v.startswith("ASANA_MCP_"), (
                f"env var {v!r} in {mod.__name__} violates the ASANA_MCP_* prefix"
            )
