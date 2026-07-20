"""Contract §4.1 readiness + inbound-JWKS postures — two-sided; checklist items 9 & 10.

Both directions asserted: fail-closed on not-ready / cold-unreachable JWKS; serve on
ready / valid. The JWKS infra-down (retryable 503) and credential-invalid (401)
families NEVER cross-dress.
"""

from __future__ import annotations

from asana_mcp.observability import (
    assert_never_auth_shaped,
    jwks_posture,
    readiness_refusal,
)


# --- readiness fail-closed, both directions ---
def test_readiness_serves_when_ready() -> None:
    assert readiness_refusal(True) is None


def test_readiness_refuses_when_not_ready_retryable_not_auth() -> None:
    r = readiness_refusal(False)
    assert r is not None
    assert r.retryable is True and r.shape == "not_ready"
    assert_never_auth_shaped(r)  # warming, never auth-shaped


# --- JWKS: cold + unreachable ⇒ retryable 503 AUTH_JWKS_UNAVAILABLE, NOT 401 ---
def test_jwks_cold_unreachable_is_retryable_503() -> None:
    r = jwks_posture(jwks_reachable=False, has_cached_keys=False, token_valid=False)
    assert r is not None
    assert r.status_code == 503 and r.retryable is True
    assert r.code == "AUTH_JWKS_UNAVAILABLE" and r.shape == "jwks"


# --- JWKS: invalid token + reachable ⇒ 401 AUTH_TOKEN_INVALID, non-retryable ---
def test_jwks_invalid_token_is_401_non_retryable() -> None:
    r = jwks_posture(jwks_reachable=True, has_cached_keys=True, token_valid=False)
    assert r is not None
    assert r.status_code == 401 and r.retryable is False
    assert r.code == "AUTH_TOKEN_INVALID" and r.shape == "auth"


# --- JWKS: warm/stale cache tolerates unreachable when the token is valid ---
def test_jwks_warm_cache_tolerates_unreachable() -> None:
    assert jwks_posture(jwks_reachable=False, has_cached_keys=True, token_valid=True) is None


# --- the two families never cross-dress (infra 503-retryable vs credential 401) ---
def test_jwks_families_never_cross_dress() -> None:
    infra = jwks_posture(jwks_reachable=False, has_cached_keys=False, token_valid=False)
    cred = jwks_posture(jwks_reachable=True, has_cached_keys=True, token_valid=False)
    assert infra is not None and cred is not None
    assert infra.status_code != cred.status_code  # 503 vs 401
    assert infra.retryable and not cred.retryable
