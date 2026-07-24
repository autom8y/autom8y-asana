"""Two-sided tests for the 401-fail-clean S2S mint-failure mapping (R21 Lane 1).

Scenario the fix exists for: the daily-tool mount's ``sa_*`` credential is
rotated/revoked. Before the fix, ``TokenManager``'s ``InvalidServiceKeyError``
erupted from the httpx request event-hook as a raw SDK traceback (read tools)
or was mislabeled ``transport error`` inside the composite write receipt.
After the fix it presents CLEANLY: auth-shaped, non-retryable, remediation
named by env-KEY (values never appear anywhere).

Two-sided teeth (no defect injected into working code — the RED comes from a
deliberately-broken INPUT, here a failing token provider):
  - POSITIVE control: an unrecognized provider failure propagates RAW (the
    seam never over-claims), and a pre-shaped McpToolError passes through
    IDENTICALLY.
  - NEGATIVE controls: credential-invalid -> 401/auth/non-retryable;
    auth-infra -> 503/server/retryable; the two families NEVER cross-dress;
    the backend transport is never reached on a mint failure.

Fake SDK exception classes are name-matched (the classifier deliberately
imports nothing from autom8y_core — C9a), so this suite needs no live SDK.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import httpx
import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1]  # mcp/ root
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from asana_mcp.context import build_context  # noqa: E402
from asana_mcp.errors import McpToolError  # noqa: E402
from asana_mcp.schemas import RowsArgs  # noqa: E402
from asana_mcp.settings import Settings  # noqa: E402
from asana_mcp.tools.composite_write import execute_composite_write  # noqa: E402
from asana_mcp.tools.query import query_rows_handler  # noqa: E402


# --------------------------------------------------------------------------- #
# Name-matched fakes of the autom8y-core token-error taxonomy (4.9.0 hierarchy)
# --------------------------------------------------------------------------- #
class TokenAcquisitionError(Exception):
    """Fake: other token exchange failure (name-matched to the SDK)."""


class InvalidServiceKeyError(TokenAcquisitionError):
    """Fake: API key invalid or revoked (the mint-401 signature)."""


class RetryExhaustedError(TokenAcquisitionError):
    """Fake: max retries exceeded reaching the auth service."""


def _ctx_with_failing_mint(exc: BaseException):
    """SidecarContext whose token provider raises; transport records reachability."""
    reached: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        reached.append(request.url.path)
        return httpx.Response(200, json={"data": {}})

    async def _provider() -> str:
        raise exc

    settings = Settings(base_url="http://sat.local", ready_path="/ready")
    ctx = build_context(settings, token_provider=_provider, transport=httpx.MockTransport(handler))
    return ctx, reached


# --------------------------------------------------------------------------- #
# The classified shapes (and their disjointness)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_invalid_key_presents_clean_auth_401():
    ctx, reached = _ctx_with_failing_mint(InvalidServiceKeyError("credentials rejected"))
    try:
        with pytest.raises(McpToolError) as err_info:
            await ctx.http.get("/v1/query/entities")
    finally:
        await ctx.http.aclose()

    err = err_info.value
    assert err.kind == "auth"
    assert err.status == 401
    assert err.retryable is False
    assert err.code == "S2S_MINT_CREDENTIALS_INVALID"
    # remediation names the env KEYS (never values) and disclaims warming
    assert "CLIENT_ID" in err.message and "CLIENT_SECRET" in err.message
    assert "NOT cache warming" in err.message
    assert isinstance(err.__cause__, InvalidServiceKeyError)  # chain preserved
    assert reached == []  # the satellite was NEVER contacted


@pytest.mark.asyncio
async def test_retry_exhausted_presents_retryable_infra_503():
    ctx, reached = _ctx_with_failing_mint(RetryExhaustedError("gave up"))
    try:
        with pytest.raises(McpToolError) as err_info:
            await ctx.http.get("/v1/query/entities")
    finally:
        await ctx.http.aclose()

    err = err_info.value
    assert err.kind == "server"
    assert err.status == 503
    assert err.retryable is True
    assert err.code == "S2S_MINT_UNAVAILABLE"
    assert "NOT a credential failure" in err.message
    assert reached == []


@pytest.mark.asyncio
async def test_generic_token_acquisition_error_is_infra_shaped():
    ctx, _ = _ctx_with_failing_mint(TokenAcquisitionError("exchange 500"))
    try:
        with pytest.raises(McpToolError) as err_info:
            await ctx.http.get("/v1/query/entities")
    finally:
        await ctx.http.aclose()
    assert err_info.value.code == "S2S_MINT_UNAVAILABLE"
    assert err_info.value.retryable is True


@pytest.mark.asyncio
async def test_the_two_families_never_cross_dress():
    ctx_cred, _ = _ctx_with_failing_mint(InvalidServiceKeyError("bad"))
    ctx_infra, _ = _ctx_with_failing_mint(RetryExhaustedError("down"))
    try:
        with pytest.raises(McpToolError) as cred_info:
            await ctx_cred.http.get("/x")
        with pytest.raises(McpToolError) as infra_info:
            await ctx_infra.http.get("/x")
    finally:
        await ctx_cred.http.aclose()
        await ctx_infra.http.aclose()

    cred, infra = cred_info.value, infra_info.value
    assert cred.status != infra.status  # 401 vs 503
    assert cred.kind != infra.kind  # auth vs server
    assert cred.retryable is False and infra.retryable is True


# --------------------------------------------------------------------------- #
# Never over-claim (positive controls)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_unrecognized_failures_propagate_raw():
    ctx, _ = _ctx_with_failing_mint(ValueError("not a token-mint class"))
    try:
        with pytest.raises(ValueError):
            await ctx.http.get("/v1/query/entities")
    finally:
        await ctx.http.aclose()


@pytest.mark.asyncio
async def test_preshaped_mcp_tool_error_passes_through_identically():
    preshaped = McpToolError("already classified", kind="auth", retryable=False, status=401)
    ctx, _ = _ctx_with_failing_mint(preshaped)
    try:
        with pytest.raises(McpToolError) as err_info:
            await ctx.http.get("/v1/query/entities")
    finally:
        await ctx.http.aclose()
    assert err_info.value is preshaped  # untouched, not re-wrapped


# --------------------------------------------------------------------------- #
# Surface-level fail-clean: the write receipt and the read path
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_composite_write_receipt_is_auth_shaped_not_transport():
    ctx, reached = _ctx_with_failing_mint(InvalidServiceKeyError("rotated away"))

    class _Ctx:
        def __init__(self, http: Any) -> None:
            self.http = http
            self.settings = None

    try:
        result = await execute_composite_write(
            _Ctx(ctx.http), task_gid="1209000000000001", tag_gid="1300000000000042"
        )
    finally:
        await ctx.http.aclose()

    assert result.status == "refused_incomplete"
    add_tag = result.steps[0]
    assert add_tag.status == "failed"
    assert add_tag.http_status == 401
    assert add_tag.detail.startswith("auth:")
    assert "transport error" not in add_tag.detail  # the old mislabel is dead
    assert "CLIENT_ID" in add_tag.detail  # remediation carried into the receipt
    # later steps never attempted; the satellite was never contacted
    assert [s.status for s in result.steps[1:]] == ["not_attempted", "not_attempted"]
    assert reached == []


@pytest.mark.asyncio
async def test_read_tool_path_raises_the_clean_auth_error():
    """The daily-driver read path (readiness GET included) surfaces the clean
    401 instead of a raw SDK traceback or a warming-shaped lie."""
    ctx, reached = _ctx_with_failing_mint(InvalidServiceKeyError("rotated away"))
    try:
        with pytest.raises(McpToolError) as err_info:
            await query_rows_handler(ctx, "offer", RowsArgs())
    finally:
        await ctx.http.aclose()

    assert err_info.value.code == "S2S_MINT_CREDENTIALS_INVALID"
    assert err_info.value.kind == "auth"  # never presented as warming
    assert reached == []
