"""Contract §1.3 timeout invariant — two-sided; checklist items 6 & 8.

GREEN: the contract's default cascade (CONNECT 5 < HTTP 45 < TOOL 50 < ALB 60;
HTTP > satellite-honest 30) validates. RED (teeth): the literal RC001 scar value
HTTP=90 is rejected fail-loud, plus every other inversion variant.
"""

from __future__ import annotations

import os

import pytest
from asana_mcp.timeouts import (
    ALB_IDLE_TIMEOUT_FLOOR_S,
    SATELLITE_HONEST_BOUND_S,
    ConfigurationError,
    TimeoutConfig,
    effective_http,
    validate_timeout_config,
)


# --- GREEN: the contract defaults validate ---
def test_default_cascade_validates() -> None:
    cfg = TimeoutConfig()  # 5 / 45 / 50
    validate_timeout_config(cfg)  # no raise
    assert cfg.connect_s < cfg.http_s < cfg.tool_s < ALB_IDLE_TIMEOUT_FLOOR_S
    assert cfg.http_s > SATELLITE_HONEST_BOUND_S


# --- RED (teeth): the RC001 scar value HTTP=90 is rejected fail-loud ---
def test_rc001_scar_value_http_90_rejected() -> None:
    cfg = TimeoutConfig(connect_s=5.0, http_s=90.0, tool_s=50.0)
    with pytest.raises(ConfigurationError):
        validate_timeout_config(cfg)


# --- RED: HTTP below the satellite honest bound is rejected (typed 503s lost) ---
def test_http_below_satellite_honest_bound_rejected() -> None:
    cfg = TimeoutConfig(connect_s=5.0, http_s=25.0, tool_s=45.0)  # 25 < 30
    with pytest.raises(ConfigurationError):
        validate_timeout_config(cfg)


# --- RED: TOOL not strictly inside the ALB floor is rejected ---
def test_tool_at_or_above_alb_floor_rejected() -> None:
    cfg = TimeoutConfig(connect_s=5.0, http_s=45.0, tool_s=60.0)  # 60 !< 60
    with pytest.raises(ConfigurationError):
        validate_timeout_config(cfg)


# --- RED: a per-tool override out of band is rejected ---
def test_override_out_of_band_rejected() -> None:
    cfg = TimeoutConfig(overrides={"list_entity_types": 5.0})  # 5 < MIN_OVERRIDE 10
    with pytest.raises(ConfigurationError):
        validate_timeout_config(cfg)


# --- GREEN: a valid per-tool override preserves per-call ordering ---
def test_valid_override_preserves_ordering() -> None:
    cfg = TimeoutConfig(overrides={"list_entity_types": 20.0})
    validate_timeout_config(cfg)  # no raise
    assert cfg.tool_timeout_for("list_entity_types") == 20.0
    assert effective_http(20.0) < 20.0  # http < tool per call
    assert cfg.tool_timeout_for("query_rows") == cfg.tool_s  # default otherwise


# --- GREEN: from_env with no ASANA_MCP_* set yields the valid defaults ---
def test_from_env_defaults_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in list(os.environ):
        if k.startswith("ASANA_MCP_"):
            monkeypatch.delenv(k, raising=False)
    cfg = TimeoutConfig.from_env()
    validate_timeout_config(cfg)
    assert (cfg.connect_s, cfg.http_s, cfg.tool_s) == (5.0, 45.0, 50.0)
