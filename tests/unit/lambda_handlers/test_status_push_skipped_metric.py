"""RED-first two-sided fixtures for the StatusPushSkipped{skip_reason} counter.

Wires the observability defect identified in the SRE dark-subsystem postmortem
(AI-4 / N1 §B-1, §S4): every StatusPush skip path is metric-silent, so a benign
idle skip and a misconfigured skip (url_absent / invalid_key) are
indistinguishable in CloudWatch.

The counter is additive observability ONLY -- it MUST NOT change push behavior
(every return value below is asserted identical to pre-change behavior).

Each of the four skip_reason values carries a TWO-SIDED pair:
  (+) positive: drive the exact skip precondition; assert
      StatusPushSkipped{skip_reason=X} == 1 AND that StatusPushSuccess/Failure
      were NOT emitted.
  (-) negative (no-defect variant -- MUST pass GREEN): drive the complement
      (happy path) and assert StatusPushSkipped{skip_reason=X} was NOT emitted
      (the counter does not over-fire).

Contract (N1 §B-1):
  metric name  = "StatusPushSkipped"
  namespace    = "Autom8y/AsanaBridgeFleet"   (shared bridge namespace)
  value        = 1
  dimension    = skip_reason in
                 {feature_disabled, url_absent, invalid_key,
                  three_way_denominator_null}
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from autom8_asana.services.gid_push import (
    STATUS_PUSH_ENABLED_ENV_VAR,
    push_status_to_data_service,
)

_EXPECTED_NAMESPACE = "Autom8y/AsanaBridgeFleet"
_METRIC = "StatusPushSkipped"


def _skip_calls(emit: MagicMock) -> list[Any]:
    """Return the emit_metric calls that targeted StatusPushSkipped."""
    return [c for c in emit.call_args_list if c.args and c.args[0] == _METRIC]


def _reasons_emitted(emit: MagicMock) -> list[str]:
    """Return the skip_reason dimension value for each StatusPushSkipped emit."""
    reasons: list[str] = []
    for c in _skip_calls(emit):
        dims = c.kwargs.get("dimensions") or {}
        reasons.append(dims.get("skip_reason"))
    return reasons


def _assert_skip_contract(emit: MagicMock, expected_reason: str) -> None:
    """Assert exactly one StatusPushSkipped emit with the right contract."""
    skip_calls = _skip_calls(emit)
    assert len(skip_calls) == 1, (
        f"expected exactly one StatusPushSkipped emit, got {len(skip_calls)}"
    )
    call = skip_calls[0]
    # counter value is one
    assert call.args[1] == 1
    # mandatory skip_reason dimension present
    dims = call.kwargs.get("dimensions") or {}
    assert dims.get("skip_reason") == expected_reason
    # emitted to the shared bridge namespace, not the default autom8/lambda
    assert call.kwargs.get("namespace") == _EXPECTED_NAMESPACE


# ===========================================================================
# Service-seam skips (gid_push.py:491-512) -- feature_disabled / url_absent /
# invalid_key. emit_metric is patched at the gid_push module boundary.
# ===========================================================================


class TestFeatureDisabledSkip:
    """skip_reason = feature_disabled (STATUS_PUSH_ENABLED=false)."""

    async def test_positive_emits_skip(self) -> None:
        with (
            patch.dict("os.environ", {STATUS_PUSH_ENABLED_ENV_VAR: "false"}),
            patch("autom8_asana.services.gid_push.emit_metric") as emit,
        ):
            result = await push_status_to_data_service(
                entries=[{"phone": "+15551234567"}],
                source_timestamp="2026-06-24T00:00:00+00:00",
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        # behavior unchanged: disabled still returns False
        assert result is False
        _assert_skip_contract(emit, "feature_disabled")

    async def test_negative_does_not_emit_on_happy_path(self) -> None:
        """No-defect variant: enabled + everything present -> no feature_disabled skip."""
        mock_response = httpx.Response(status_code=200, json={"inserted": 1})

        with (
            patch.dict("os.environ", {STATUS_PUSH_ENABLED_ENV_VAR: "true"}),
            patch("autom8_asana.services.gid_push.emit_metric") as emit,
            patch("autom8_asana.services.gid_push.Autom8yHttpClient") as http_cls,
        ):
            _wire_http(http_cls, mock_response)
            result = await push_status_to_data_service(
                entries=[{"phone": "+15551234567"}],
                source_timestamp="2026-06-24T00:00:00+00:00",
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is True
        assert "feature_disabled" not in _reasons_emitted(emit)


class TestUrlAbsentSkip:
    """skip_reason = url_absent (AUTOM8Y_DATA_URL not configured)."""

    async def test_positive_emits_skip(self) -> None:
        with (
            patch.dict("os.environ", {STATUS_PUSH_ENABLED_ENV_VAR: "true"}, clear=True),
            patch("autom8_asana.services.gid_push.emit_metric") as emit,
        ):
            result = await push_status_to_data_service(
                entries=[{"phone": "+15551234567"}],
                source_timestamp="2026-06-24T00:00:00+00:00",
                # no data_service_url -> falls through to env (unset)
                auth_token="test-token",
            )

        assert result is False
        _assert_skip_contract(emit, "url_absent")

    async def test_negative_does_not_emit_on_happy_path(self) -> None:
        """No-defect variant: URL present -> no url_absent skip."""
        mock_response = httpx.Response(status_code=200, json={"inserted": 1})

        with (
            patch.dict("os.environ", {STATUS_PUSH_ENABLED_ENV_VAR: "true"}),
            patch("autom8_asana.services.gid_push.emit_metric") as emit,
            patch("autom8_asana.services.gid_push.Autom8yHttpClient") as http_cls,
        ):
            _wire_http(http_cls, mock_response)
            result = await push_status_to_data_service(
                entries=[{"phone": "+15551234567"}],
                source_timestamp="2026-06-24T00:00:00+00:00",
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is True
        assert "url_absent" not in _reasons_emitted(emit)


class TestInvalidKeySkip:
    """skip_reason = invalid_key (AUTOM8Y_DATA_API_KEY not available)."""

    async def test_positive_emits_skip(self) -> None:
        with (
            patch.dict(
                "os.environ",
                {
                    STATUS_PUSH_ENABLED_ENV_VAR: "true",
                    "AUTOM8Y_DATA_URL": "http://localhost:8000",
                },
                clear=True,
            ),
            patch("autom8_asana.services.gid_push.emit_metric") as emit,
            patch(
                "autom8_asana.services.gid_push._get_auth_token",
                return_value=None,
            ),
        ):
            result = await push_status_to_data_service(
                entries=[{"phone": "+15551234567"}],
                source_timestamp="2026-06-24T00:00:00+00:00",
            )

        assert result is False
        _assert_skip_contract(emit, "invalid_key")

    async def test_negative_does_not_emit_on_happy_path(self) -> None:
        """No-defect variant: token present -> no invalid_key skip."""
        mock_response = httpx.Response(status_code=200, json={"inserted": 1})

        with (
            patch.dict("os.environ", {STATUS_PUSH_ENABLED_ENV_VAR: "true"}),
            patch("autom8_asana.services.gid_push.emit_metric") as emit,
            patch("autom8_asana.services.gid_push.Autom8yHttpClient") as http_cls,
        ):
            _wire_http(http_cls, mock_response)
            result = await push_status_to_data_service(
                entries=[{"phone": "+15551234567"}],
                source_timestamp="2026-06-24T00:00:00+00:00",
                data_service_url="http://localhost:8000",
                auth_token="test-token",
            )

        assert result is True
        assert "invalid_key" not in _reasons_emitted(emit)


# ===========================================================================
# Orchestrator-seam skip (push_orchestrator.py:183 if-all_entries false branch)
# -- three_way_denominator_null. emit_metric is patched at the orchestrator
# module boundary.
# ===========================================================================


class TestThreeWayDenominatorNullSkip:
    """skip_reason = three_way_denominator_null (empty all_entries branch)."""

    async def test_positive_emits_skip(self) -> None:
        """All warmed entities yield zero status entries -> empty denominator."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_entry = MagicMock()
        mock_entry.dataframe = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with (
            patch(
                "autom8_asana.services.gid_push.extract_status_from_dataframe",
                return_value=[],  # every entity contributes zero entries
            ),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as emit,
        ):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )

        _assert_skip_contract(emit, "three_way_denominator_null")
        # additive-only: the success/failure counters must NOT fire on the
        # empty-denominator branch
        assert "StatusPushSuccess" not in [c.args[0] for c in emit.call_args_list if c.args]
        assert "StatusPushFailure" not in [c.args[0] for c in emit.call_args_list if c.args]

    async def test_negative_does_not_emit_on_nonempty_denominator(self) -> None:
        """No-defect variant: non-empty all_entries -> no skip, push attempted."""
        from autom8_asana.lambda_handlers.push_orchestrator import (
            _push_account_status_for_completed_entities,
        )

        mock_entry = MagicMock()
        mock_entry.dataframe = MagicMock()
        mock_cache = MagicMock()
        mock_cache.get_async = AsyncMock(return_value=mock_entry)

        with (
            patch(
                "autom8_asana.services.gid_push.extract_status_from_dataframe",
                return_value=[{"phone": "+15551234567"}],
            ),
            patch(
                "autom8_asana.services.gid_push.push_status_to_data_service",
                new=AsyncMock(return_value=True),
            ),
            patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as emit,
        ):
            await _push_account_status_for_completed_entities(
                completed_entities=["unit"],
                get_project_gid=lambda _: "proj-001",
                cache=mock_cache,
                invocation_id="test-inv",
            )

        assert "three_way_denominator_null" not in _reasons_emitted(emit)
        # the happy path still emits its success counter (behavior unchanged)
        assert "StatusPushSuccess" in [c.args[0] for c in emit.call_args_list if c.args]


# ===========================================================================
# helpers
# ===========================================================================


def _wire_http(http_cls: MagicMock, response: httpx.Response) -> None:
    """Wire the two-layer Autom8yHttpClient mock chain for a 2xx push."""
    raw_client = AsyncMock()
    raw_client.post.return_value = response

    raw_cm = AsyncMock()
    raw_cm.__aenter__.return_value = raw_client

    outer = MagicMock()
    outer.raw.return_value = raw_cm

    http_cls.return_value = AsyncMock()
    http_cls.return_value.__aenter__.return_value = outer
