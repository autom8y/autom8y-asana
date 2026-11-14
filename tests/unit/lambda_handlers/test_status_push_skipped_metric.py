"""RED-first two-sided fixtures for the StatusPushSkipped{skip_reason} counter.

Wires the observability defect identified in the SRE dark-subsystem postmortem
(AI-4 / N1 §B-1, §S4): every StatusPush skip path is metric-silent, so a benign
idle skip and a misconfigured skip (url_absent / invalid_key) are
indistinguishable in CloudWatch.

The counter is additive observability ONLY -- it MUST NOT change push behavior
(every return value below is asserted identical to pre-change behavior).

Each emitted skip_reason value carries a TWO-SIDED pair:
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
                  three_way_denominator_null, unit_activity_unavailable}
                 invalid_key is RETIRED (PT-CI-03 A109): the status push now mints
                 with its own account, so missing credentials are a named mint
                 failure, not a skip. The value stays reserved; nothing emits it.
                 unit_activity_unavailable: the orchestrator withheld the whole
                 snapshot because its Unit rows could not be computed; emitted
                 once per withheld snapshot.
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


def _unit_activity_passthrough() -> Any:
    """The Unit activity step, faked to hand the frame on unchanged.

    These tests drive the push seam with a patched extraction, so the Unit
    activity step is out of their scope; the fake matches the real signature.
    """
    from unittest.mock import create_autospec

    from autom8_asana.lambda_handlers import push_orchestrator

    return create_autospec(
        push_orchestrator._unit_frame_with_activity,
        side_effect=lambda unit_df, **_: unit_df,
    )


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
    """skip_reason = invalid_key is RETIRED from the status push (PT-CI-03 A109).

    The status push mints with its own service account (STATUS_PUSH_CLIENT_*).
    Missing credentials are a named mint FAILURE
    (status_push_service_token_mint_failed, reason=credentials_absent), never a
    StatusPushSkipped{invalid_key} skip and never a fallback to the legacy key.
    """

    async def test_positive_credentials_absent_is_a_failure_not_a_skip(self) -> None:
        with (
            patch.dict(
                "os.environ",
                {
                    STATUS_PUSH_ENABLED_ENV_VAR: "true",
                    "AUTOM8Y_DATA_URL": "http://localhost:8000",
                    # The legacy key is present and must NOT be used.
                    "AUTOM8Y_DATA_API_KEY": "legacy-test-only",
                },
                clear=True,
            ),
            patch("autom8_asana.services.gid_push.emit_metric") as emit,
            patch("autom8_asana.services.gid_push.logger") as log,
        ):
            result = await push_status_to_data_service(
                entries=[{"phone": "+15551234567"}],
                source_timestamp="2026-06-24T00:00:00+00:00",
            )

        assert result is False
        assert _skip_calls(emit) == []
        failed = [
            c
            for c in log.error.call_args_list
            if c.args[0] == "status_push_service_token_mint_failed"
        ]
        assert len(failed) == 1
        assert failed[0].kwargs["extra"]["reason"] == "credentials_absent"

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
            patch(
                "autom8_asana.lambda_handlers.push_orchestrator._unit_frame_with_activity",
                new=_unit_activity_passthrough(),
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
                "autom8_asana.lambda_handlers.push_orchestrator._unit_frame_with_activity",
                new=_unit_activity_passthrough(),
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
# Orchestrator-seam skip -- unit_activity_unavailable. The snapshot is
# withheld because its Unit rows could not be computed. Driven through the
# REAL Unit activity step (no passthrough fake) from real frames.
# ===========================================================================


def _unit_project_gid() -> str:
    from autom8_asana.services.gid_push import PIPELINE_TYPE_BY_PROJECT_GID

    return next(g for g, kind in PIPELINE_TYPE_BY_PROJECT_GID.items() if kind == "unit")


async def _drive_unit_push(frames: dict[str, Any]) -> MagicMock:
    """Run the real orchestrator over ``frames`` (entity type -> frame or None)."""
    from autom8_asana.lambda_handlers.push_orchestrator import (
        _push_account_status_for_completed_entities,
    )

    def _entry(project_gid: str, entity_type: str) -> Any:
        df = frames.get(entity_type)
        if df is None:
            return None
        entry = MagicMock()
        entry.dataframe = df
        return entry

    cache = MagicMock()
    cache.get_async = AsyncMock(side_effect=_entry)
    gids = {"unit": _unit_project_gid(), "offer": "offer-project"}

    with (
        patch(
            "autom8_asana.services.gid_push.push_status_to_data_service",
            new=AsyncMock(return_value=True),
        ),
        patch("autom8_asana.lambda_handlers.push_orchestrator.emit_metric") as emit,
    ):
        await _push_account_status_for_completed_entities(
            completed_entities=["unit", "offer"],
            get_project_gid=gids.get,
            cache=cache,
            invocation_id="test-inv",
        )
    return emit


def _marketing_unit_frames() -> dict[str, Any]:
    import polars as pl

    return {
        "unit": pl.DataFrame(
            {
                "office_phone": ["+15550100001"],
                "vertical": ["dental"],
                "section": ["Engaged"],
                "products": [["Meta Marketing"]],
            }
        ),
        "offer": pl.DataFrame(
            {"office_phone": ["+15550100001"], "vertical": ["dental"], "section": ["ACTIVE"]}
        ),
    }


class TestUnitActivityUnavailableSkip:
    """skip_reason = unit_activity_unavailable (the snapshot is withheld)."""

    async def test_positive_withheld_snapshot_emits_skip_exactly_once(self) -> None:
        """No Offer frame: the Unit rows cannot be computed, so nothing is pushed."""
        frames = _marketing_unit_frames()
        frames["offer"] = None

        emit = await _drive_unit_push(frames)

        _assert_skip_contract(emit, "unit_activity_unavailable")
        names = [c.args[0] for c in emit.call_args_list if c.args]
        assert "StatusPushSuccess" not in names
        assert "StatusPushFailure" not in names

    async def test_negative_does_not_emit_when_unit_activity_is_computed(self) -> None:
        """No-defect variant: both frames present -> pushed, no withhold skip."""
        emit = await _drive_unit_push(_marketing_unit_frames())

        assert "unit_activity_unavailable" not in _reasons_emitted(emit)
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
