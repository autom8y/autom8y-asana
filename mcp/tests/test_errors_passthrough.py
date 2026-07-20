"""MCP-1: upstream error context passes through to the tool error.

Born from the asana-mcp-v1 limb-(a) witness (2026-07-19): the satellite's 404
body carried a self-correcting ``available_types`` hint, but the tool layer
flattened it to a hintless string and the witness agent burned a four-call
guess loop (then, at the mint halt, hallucinated a re-auth flow that does not
exist). Evidence dossier:
.sos/wip/asana-mcp-v1.limb-a-witness-evidence-digest.md (MCP-1).

Contract: 404/4xx/auth tool errors CARRY the satellite's code, message, and
the actionable details (available_types, validation_errors, missing_field).
The 503-warming branch deliberately keeps its curated C3 attribution text —
that scope fence is asserted here too.
"""

from __future__ import annotations

import httpx
from asana_mcp.errors import map_http_error


def test_404_carries_available_types_recovery_hint():
    err = map_http_error(
        httpx.Response(
            404,
            json={
                "error": {
                    "code": "UNKNOWN_ENTITY_TYPE",
                    "message": "Unknown entity type: process_sale",
                    "details": {
                        "available_types": ["business", "process_sales", "unit"],
                    },
                }
            },
        )
    )
    assert err.kind == "not_found"
    assert err.retryable is False
    assert err.code == "UNKNOWN_ENTITY_TYPE"
    # The recovery hint the limb-(a) agent never received:
    assert "process_sales" in err.message
    assert "UNKNOWN_ENTITY_TYPE" in err.message
    assert "Unknown entity type: process_sale" in err.message


def test_404_without_body_keeps_static_fallback():
    err = map_http_error(httpx.Response(404))
    assert err.kind == "not_found"
    assert err.message == "The requested entity type or route was not found."


def test_422_surfaces_validation_errors():
    err = map_http_error(
        httpx.Response(
            422,
            json={
                "error": {
                    "code": "ASANA-VAL-001",
                    "message": "Request validation failed: 1 error(s)",
                    "details": {
                        "validation_errors": [
                            {
                                "field": "body.project_gid",
                                "message": "Extra inputs are not permitted",
                                "type": "extra_forbidden",
                            }
                        ]
                    },
                }
            },
        )
    )
    assert err.kind == "client"
    assert "body.project_gid" in err.message
    assert "Extra inputs are not permitted" in err.message


def test_400_surfaces_missing_field():
    err = map_http_error(
        httpx.Response(
            400,
            json={
                "error": {
                    "code": "AUTH-TEB-004",
                    "message": "business_id required",
                    "details": {"missing_field": "business_id"},
                }
            },
        )
    )
    assert err.kind == "client"
    assert "business_id" in err.message
    assert "AUTH-TEB-004" in err.message


def test_auth_branch_carries_code_and_keeps_attribution():
    err = map_http_error(
        httpx.Response(
            401,
            json={
                "error": {
                    "code": "SERVICE_TOKEN_REQUIRED",
                    "message": "S2S bearer missing or invalid",
                }
            },
        )
    )
    assert err.kind == "auth"
    assert err.retryable is False
    assert "SERVICE_TOKEN_REQUIRED" in err.message
    assert "S2S bearer missing or invalid" in err.message
    # The C3 disambiguation stays present:
    assert "NOT a cache-warming" in err.message


def test_warming_message_stays_curated():
    """Scope fence: the 503-warming branch keeps its load-bearing C3 text and
    does NOT inject upstream prose."""
    err = map_http_error(
        httpx.Response(
            503,
            json={
                "error": {
                    "code": "CACHE_NOT_WARMED",
                    "message": "some upstream phrasing that must not displace C3",
                }
            },
        )
    )
    assert err.kind == "warming"
    assert err.retryable is True
    assert "warming" in err.message.lower()
    assert "some upstream phrasing" not in err.message
