"""Contract §4.3 cold-frame 503 mapping — two-sided; checklist item 5.

A typed 503 propagates the verbatim satellite cause, retryable, retry_after, and is
NEVER auth-shaped. The teeth: an auth-shaped rewrite of a cold-frame is REJECTED by
``assert_never_auth_shaped``; a genuine 401 IS auth (the guard exempts it, so the
mapping still discriminates).
"""

from __future__ import annotations

import pytest
from asana_mcp.observability import (
    AuthShapedError,
    MappedError,
    assert_never_auth_shaped,
    map_upstream_status,
)


# --- GREEN + teeth: typed 503 cause, retryable, and NOT auth-shaped ---
def test_cache_build_in_progress_is_retryable_true_cause_not_auth() -> None:
    mapped = map_upstream_status(503, cause_code="CACHE_BUILD_IN_PROGRESS")
    assert mapped is not None
    assert mapped.code == "CACHE_BUILD_IN_PROGRESS"  # verbatim satellite cause
    assert mapped.shape == "cache_warming"
    assert mapped.retryable is True
    assert mapped.retry_after_s is not None and mapped.retry_after_s > 0
    assert_never_auth_shaped(mapped)  # no raise: never matches /auth|forbidden|credential/i


def test_dataframe_build_timeout_cause_propagates() -> None:
    mapped = map_upstream_status(503, cause_code="DATAFRAME_BUILD_TIMEOUT")
    assert mapped is not None and mapped.code == "DATAFRAME_BUILD_TIMEOUT"
    assert mapped.retryable is True
    assert_never_auth_shaped(mapped)


# --- teeth: an auth-shaped rewrite of a cold-frame is REJECTED ---
def test_auth_shaped_cold_frame_rejected() -> None:
    bad = MappedError(
        status_code=503,
        code="UNAUTHORIZED",
        shape="cache_warming",
        retryable=True,
        reason="invalid credential; re-authenticate",
    )
    with pytest.raises(AuthShapedError):
        assert_never_auth_shaped(bad)


# --- discrimination: a genuine 401 IS auth-shaped (guard exempts the auth shape) ---
def test_401_is_auth_and_exempt_from_never_auth() -> None:
    mapped = map_upstream_status(401)
    assert mapped is not None and mapped.shape == "auth" and mapped.retryable is False
    assert_never_auth_shaped(mapped)  # no raise: the auth shape is exempt


def test_retry_after_bounded_by_min_budget_30() -> None:
    assert map_upstream_status(503, remaining_budget_s=10.0).retry_after_s == 10.0
    assert map_upstream_status(503, remaining_budget_s=100.0).retry_after_s == 30.0


def test_2xx_maps_to_no_error() -> None:
    assert map_upstream_status(200) is None
