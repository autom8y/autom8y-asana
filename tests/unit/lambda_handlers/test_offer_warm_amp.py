"""Two-sided discriminating canary for the OfferWarmComplete -> AMP emit (node-1).

Cross-repo series contract under test (FROZEN -- the monorepo's
``slo_offer_freshness`` recording rules + node-4 freshness alerts consume it):

    autom8y_offer_warm_complete_timestamp{entity_type="offer"}

The canary is TWO-SIDED and author-disjoint (telos-integrity / canary-signal-
contract §6): it PASSES against the real ``emit_offer_warm_complete`` and TRIPS
RED against a deliberately-broken SUCCESS-no-emit variant
(``_BROKEN_success_path_no_emit``) defined IN THIS FILE, independent of the
production code. A silent drop of the emit on the SUCCESS path therefore fails the
discrimination test rather than reading green.

Discrimination contract (the property both sides are graded on):
  * On ``WarmResult.SUCCESS`` AND ``ASR_AMP_EMIT_ENABLED`` armed, exactly one AMP
    remote-write series is pushed whose ``__name__`` is
    ``autom8y_offer_warm_complete_timestamp`` and whose ``entity_type`` label is
    the warmed entity (verbatim).
  * A SUCCESS path that does NOT call the emit (the broken twin) pushes ZERO
    series -> the GREEN assertion (>=1 matching series) FAILS. This is the RED
    side: it proves the test discriminates emit-present from emit-absent.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from autom8_asana.lambda_handlers.offer_warm_amp import (
    ENTITY_TYPE_LABEL,
    OFFER_WARM_COMPLETE_METRIC,
    emit_offer_warm_complete,
)

# Verbatim cross-repo contract literals. Hard-coded here (NOT imported as the
# value under test) so a rename of the production constant is itself caught: the
# canary asserts against these frozen strings, which the monorepo consumer also
# hard-codes.
CONTRACT_METRIC_NAME = "autom8y_offer_warm_complete_timestamp"
CONTRACT_LABEL_KEY = "entity_type"
CONTRACT_OFFER_LABEL_VALUE = "offer"

# Armed-and-reachable env: ASR_AMP_EMIT_ENABLED true + an endpoint set, so
# RemoteWriteConfig.from_env().is_active is True (past the inert-until-armed gate).
_ARMED_ENV = {
    "ASR_AMP_EMIT_ENABLED": "true",
    "AMP_REMOTE_WRITE_ENDPOINT": (
        "https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-test/api/v1/remote_write"
    ),
    "AWS_REGION": "us-east-1",
}


def _capture_emit_timeseries():
    """Patch-context that captures the ``series`` pushed to ``emit_timeseries``.

    Returns a context manager and a mutable list the captured series land in. The
    transport is never hit -- ``emit_timeseries`` itself is replaced with a
    capturing stub so we assert the WIRE-LEVEL series (label set + name) the
    warmer would sign, with no live socket.
    """
    captured: list = []

    def _fake_emit_timeseries(endpoint, series, *, region, creds, transport=None):
        captured.append(series)
        return None

    ctx = patch(
        "autom8y_telemetry.aws.remote_write.emit_timeseries",
        side_effect=_fake_emit_timeseries,
    )
    return ctx, captured


def _series_matches_contract(captured: list, *, entity_type: str) -> bool:
    """True iff some captured series carries the frozen name+label contract.

    This is the SINGLE discrimination predicate both the GREEN and RED sides are
    graded on: at least one pushed series whose ``__name__`` equals the frozen
    metric name and whose ``entity_type`` label equals the warmed entity.
    """
    for series in captured:
        for ts in series:
            labels = ts.labels
            if (
                labels.get("__name__") == CONTRACT_METRIC_NAME
                and labels.get(CONTRACT_LABEL_KEY) == entity_type
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# Author-disjoint BROKEN twin: a SUCCESS path that SILENTLY DROPS the emit.
# This stands in for the regression the canary must catch. It is defined here
# (not in production) so the RED side is independent of the code under test.
# ---------------------------------------------------------------------------
def _BROKEN_success_path_no_emit(entity_type: str) -> None:
    """Simulate the silent-drop defect: reach SUCCESS but never emit to AMP.

    A real regression of this shape is "the SUCCESS branch stopped calling
    ``emit_offer_warm_complete``". The body is intentionally a no-op: zero series
    are pushed, so the GREEN assertion must FAIL against it.
    """
    return None


class TestOfferWarmCompleteAmpCanary:
    """Two-sided discriminating canary (node-1 series contract)."""

    def test_GREEN_success_emits_contract_series(self) -> None:
        """HEALTHY: the real emit pushes the frozen name+label on SUCCESS (armed).

        This is the GREEN side: the production ``emit_offer_warm_complete`` MUST
        push a series matching ``autom8y_offer_warm_complete_timestamp
        {entity_type="offer"}``.
        """
        ctx, captured = _capture_emit_timeseries()
        with (
            patch.dict("os.environ", _ARMED_ENV, clear=True),
            ctx,
            patch(
                "autom8y_telemetry.aws.remote_write.resolve_credentials",
                return_value=("AKID", "SECRET", "TOKEN"),
            ),
        ):
            emit_offer_warm_complete(CONTRACT_OFFER_LABEL_VALUE)

        assert _series_matches_contract(captured, entity_type=CONTRACT_OFFER_LABEL_VALUE), (
            "HEALTHY emit must push "
            f"{CONTRACT_METRIC_NAME}{{{CONTRACT_LABEL_KEY}="
            f'"{CONTRACT_OFFER_LABEL_VALUE}"}} on WarmResult.SUCCESS'
        )

    def test_RED_silent_drop_trips_the_canary(self) -> None:
        """BROKEN twin: a SUCCESS path that drops the emit pushes ZERO series.

        This is the RED side, proven by construction: the same GREEN predicate
        (>=1 matching series) is asserted to FAIL against the broken twin. If this
        body's ``pytest.raises(AssertionError)`` did NOT fire, the canary would be
        unable to tell emit-present from emit-absent -- a non-discriminating test.
        """
        ctx, captured = _capture_emit_timeseries()
        with (
            patch.dict("os.environ", _ARMED_ENV, clear=True),
            ctx,
            patch(
                "autom8y_telemetry.aws.remote_write.resolve_credentials",
                return_value=("AKID", "SECRET", "TOKEN"),
            ),
        ):
            _BROKEN_success_path_no_emit(CONTRACT_OFFER_LABEL_VALUE)

        # The GREEN predicate MUST fail against the broken twin (zero series).
        with pytest.raises(AssertionError):
            assert _series_matches_contract(captured, entity_type=CONTRACT_OFFER_LABEL_VALUE), (
                "broken twin must not satisfy the contract predicate"
            )

    def test_label_value_is_the_warmed_entity_verbatim(self) -> None:
        """The ``entity_type`` label is the warmed entity verbatim (not hardcoded).

        Guards against a paste-bug that hardcodes ``"offer"``: warming ``unit``
        must label the series ``entity_type="unit"`` and must NOT produce an
        ``entity_type="offer"`` series.
        """
        ctx, captured = _capture_emit_timeseries()
        with (
            patch.dict("os.environ", _ARMED_ENV, clear=True),
            ctx,
            patch(
                "autom8y_telemetry.aws.remote_write.resolve_credentials",
                return_value=("AKID", "SECRET", "TOKEN"),
            ),
        ):
            emit_offer_warm_complete("unit")

        assert _series_matches_contract(captured, entity_type="unit")
        assert not _series_matches_contract(captured, entity_type="offer")

    def test_sample_is_single_last_write_wins_gauge(self) -> None:
        """Exactly one sample per call (last-write-wins gauge), value in seconds."""
        ctx, captured = _capture_emit_timeseries()
        with (
            patch.dict("os.environ", _ARMED_ENV, clear=True),
            ctx,
            patch(
                "autom8y_telemetry.aws.remote_write.resolve_credentials",
                return_value=("AKID", "SECRET", "TOKEN"),
            ),
        ):
            emit_offer_warm_complete(CONTRACT_OFFER_LABEL_VALUE)

        assert len(captured) == 1, "exactly one remote-write push per emit"
        series = captured[0]
        target = [ts for ts in series if ts.labels.get("__name__") == CONTRACT_METRIC_NAME]
        assert len(target) == 1, "exactly one contract series per emit"
        samples = target[0].samples
        assert len(samples) == 1, "last-write-wins gauge = single sample"
        # Value is a SECONDS epoch (freshness timestamp); sample ts is its ms form.
        assert samples[0].timestamp_ms == int(samples[0].value * 1000)

    def test_disabled_default_off_is_inert(self) -> None:
        """Unarmed (ASR_AMP_EMIT_ENABLED unset) pushes NOTHING -- inert until armed.

        Mirrors ASR ADR-ASR-010 default-off: prod stays inert until the operator
        arms the terraform lever. A clean env (no endpoint, no enable flag) must
        push zero series and must NOT raise.
        """
        ctx, captured = _capture_emit_timeseries()
        with patch.dict("os.environ", {}, clear=True), ctx:
            emit_offer_warm_complete(CONTRACT_OFFER_LABEL_VALUE)

        assert captured == [], "default-off emit must be fully inert"

    def test_failure_path_is_loud_via_breakglass_counter(self) -> None:
        """Armed-but-no-credentials emits the OfferWarmAmpFailed break-glass counter.

        INV-2/C7 loudness: past the is_active gate, an attempted-and-failed emit
        (here: ``resolve_credentials`` returns None) must bump the positive
        CloudWatch ``OfferWarmAmpFailed`` counter -- NOT silently no-op -- so a
        mis-keyed / unauthorized warmer role is structurally falsifiable.
        """
        with (
            patch.dict("os.environ", _ARMED_ENV, clear=True),
            patch(
                "autom8y_telemetry.aws.remote_write.resolve_credentials",
                return_value=None,
            ),
            patch("autom8_asana.lambda_handlers.offer_warm_amp.emit_metric") as mock_emit_metric,
        ):
            emit_offer_warm_complete(CONTRACT_OFFER_LABEL_VALUE)

        assert mock_emit_metric.call_count == 1
        args, kwargs = mock_emit_metric.call_args
        assert args[0] == "OfferWarmAmpFailed"
        assert args[1] == 1
        assert kwargs["dimensions"]["entity_type"] == CONTRACT_OFFER_LABEL_VALUE
        assert kwargs["dimensions"]["reason"] == "no_credentials"


class TestCacheWarmerSuccessGateWiring:
    """End-to-end: the REAL warm loop calls the emit ONLY on the SUCCESS gate.

    These drive the actual ``_warm_cache_async`` production path with the warmer
    mocked to return a chosen ``WarmResult``. The SUCCESS run MUST route through
    ``emit_offer_warm_complete`` with the warmed ``entity_type``; the FAILURE run
    MUST NOT. Deleting the production emit line at the SUCCESS gate makes
    ``test_real_success_path_emits`` go RED -- this is the discrimination twin at
    the production-wiring altitude (G-THEATER).
    """

    @staticmethod
    def _drive_warm(monkey_result):
        """Run _warm_cache_async for a single 'offer' entity, warmer -> monkey_result.

        Returns the AsyncMock patching ``emit_offer_warm_complete`` so the caller
        asserts call/no-call. All external surfaces (cache, registry, PAT,
        workspace gid, client, warmer) are mocked so only the loop body runs.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from autom8_asana.lambda_handlers.cache_warmer import _warm_cache_async

        mock_cache = MagicMock()
        mock_cache.put_async = AsyncMock()

        mock_registry = MagicMock()
        mock_registry.is_ready.return_value = True
        mock_registry.get_project_gid.return_value = "project-123"

        mock_warmer = MagicMock()
        mock_warmer.warm_entity_async = AsyncMock(return_value=monkey_result)

        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

        async def _run():
            with (
                patch.dict(
                    "os.environ",
                    {"ASANA_WORKSPACE_GID": "ws-123"},
                    clear=True,
                ),
                patch(
                    "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                    return_value=mock_cache,
                ),
                patch(
                    "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
                    return_value=mock_registry,
                ),
                patch(
                    "autom8_asana.auth.bot_pat.get_bot_pat",
                    return_value="test-pat",
                ),
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.resolve_secret_from_env",
                    return_value="ws-123",
                ),
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager.load_async",
                    new_callable=AsyncMock,
                    return_value=None,
                ),
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager.save_async",
                    new_callable=AsyncMock,
                ),
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager.clear_async",
                    new_callable=AsyncMock,
                ),
                patch(
                    "autom8_asana.AsanaClient",
                    return_value=_FakeClient(),
                ),
                patch(
                    "autom8_asana.cache.dataframe.warmer.CacheWarmer",
                    return_value=mock_warmer,
                ),
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_offer_warm_complete"
                ) as mock_emit,
            ):
                await _warm_cache_async(entity_types=["offer"], resume_from_checkpoint=False)
                return mock_emit

        return _run

    async def test_real_success_path_emits(self) -> None:
        """REAL SUCCESS path routes through emit_offer_warm_complete('offer').

        RED twin: comment out ``emit_offer_warm_complete(entity_type)`` at the
        cache_warmer SUCCESS gate and this assertion fails (zero calls).
        """
        from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

        success = WarmStatus(entity_type="offer", result=WarmResult.SUCCESS, row_count=10)
        mock_emit = await self._drive_warm(success)()
        mock_emit.assert_called_once_with("offer")

    async def test_real_failure_path_does_not_emit(self) -> None:
        """REAL FAILURE path must NOT route through emit_offer_warm_complete."""
        from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

        failure = WarmStatus(entity_type="offer", result=WarmResult.FAILURE, error="boom")
        mock_emit = await self._drive_warm(failure)()
        mock_emit.assert_not_called()


class TestPrematerializeBulkSetSuccessGateWiring:
    """End-to-end: the REAL bulk/checkpoint-resume loop calls the emit ONLY on SUCCESS.

    Companion to :class:`TestCacheWarmerSuccessGateWiring`, which covers the
    ``_warm_cache_async`` per-entity loop SUCCESS gate (cache_warmer.py:958). THIS
    class covers the SECOND, independent SUCCESS call site: the
    ``_prematerialize_bulk_set_async`` bulk/checkpoint-resume loop SUCCESS gate
    (cache_warmer.py:585). That path is the generic continuation-driven coroutine
    any offer warmed via the bulk/resume lane flows through; before this test it
    had NO discriminating coverage (commenting out the :585 emit alone left the
    canary fully GREEN).

    The bulk coroutine is keyed off an injected ``key_source``; here it yields a
    single ``("project-585", "offer")`` key so the SUCCESS branch decodes
    ``entity_type="offer"`` and MUST route through
    ``emit_offer_warm_complete("offer")``. ``warm_key_async`` is mocked to return a
    chosen ``WarmResult`` so only the loop body runs.

    Deleting the production emit line at the :585 SUCCESS gate makes
    ``test_real_bulk_success_path_emits`` go RED -- the production-wiring
    discrimination twin for the :585 site (G-THEATER).
    """

    @staticmethod
    def _drive_bulk_warm(monkey_result):
        """Run _prematerialize_bulk_set_async for a single 'offer' key.

        Injects a one-key ``key_source`` (``("project-585", "offer")``) and mocks
        ``warm_key_async`` -> ``monkey_result``. Returns the AsyncMock patching
        ``emit_offer_warm_complete`` so the caller asserts call/no-call. All
        external surfaces (cache, settings/bucket, PAT, workspace gid, client,
        warmer, checkpoint) are mocked so only the loop body runs.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from autom8_asana.lambda_handlers.cache_warmer import (
            _prematerialize_bulk_set_async,
        )

        mock_cache = MagicMock()

        mock_warmer = MagicMock()
        mock_warmer.warm_key_async = AsyncMock(return_value=monkey_result)

        mock_settings = MagicMock()
        mock_settings.s3.bucket = "test-bucket"

        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

        # The single injected bulk key. The bulk loop encodes/decodes
        # (gid, entity_type) tokens; this key decodes to entity_type="offer" so the
        # SUCCESS branch must emit with the verbatim warmed entity.
        def _offer_key_source():
            return [("project-585", "offer")]

        async def _run():
            with (
                patch.dict(
                    "os.environ",
                    {"ASANA_WORKSPACE_GID": "ws-123"},
                    clear=True,
                ),
                patch(
                    "autom8_asana.cache.dataframe.factory.get_dataframe_cache",
                    return_value=mock_cache,
                ),
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.get_settings",
                    return_value=mock_settings,
                ),
                patch(
                    "autom8_asana.auth.bot_pat.get_bot_pat",
                    return_value="test-pat",
                ),
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.resolve_secret_from_env",
                    return_value="ws-123",
                ),
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager.load_async",
                    new_callable=AsyncMock,
                    return_value=None,
                ),
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager.save_async",
                    new_callable=AsyncMock,
                ),
                patch(
                    "autom8_asana.lambda_handlers.checkpoint.CheckpointManager.clear_async",
                    new_callable=AsyncMock,
                ),
                patch(
                    "autom8_asana.AsanaClient",
                    return_value=_FakeClient(),
                ),
                patch(
                    "autom8_asana.cache.dataframe.warmer.CacheWarmer",
                    return_value=mock_warmer,
                ),
                patch(
                    "autom8_asana.lambda_handlers.cache_warmer.emit_offer_warm_complete"
                ) as mock_emit,
            ):
                await _prematerialize_bulk_set_async(
                    resume_from_checkpoint=False,
                    key_source=_offer_key_source,
                )
                return mock_emit

        return _run

    async def test_real_bulk_success_path_emits(self) -> None:
        """REAL bulk SUCCESS path routes through emit_offer_warm_complete('offer').

        RED twin: comment out ``emit_offer_warm_complete(entity_type)`` at the
        ``_prematerialize_bulk_set_async`` SUCCESS gate (cache_warmer.py:585) and
        this assertion fails (zero calls) -- proving the test bites the :585 site
        specifically, the gap the :958 canary did not cover.
        """
        from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

        success = WarmStatus(entity_type="offer", result=WarmResult.SUCCESS, row_count=10)
        mock_emit = await self._drive_bulk_warm(success)()
        mock_emit.assert_called_once_with("offer")

    async def test_real_bulk_failure_path_does_not_emit(self) -> None:
        """REAL bulk FAILURE path must NOT route through emit_offer_warm_complete."""
        from autom8_asana.cache.dataframe.warmer import WarmResult, WarmStatus

        failure = WarmStatus(entity_type="offer", result=WarmResult.FAILURE, error="boom")
        mock_emit = await self._drive_bulk_warm(failure)()
        mock_emit.assert_not_called()
