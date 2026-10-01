"""PT-CI-03 A104.1: the data-service push seam prefers the fleet service account.

``services/gid_push._get_auth_token`` is the credential seam behind the gid
(``push_gid_mappings_to_data_service``), vocab
(``push_vocabulary_to_data_service``) and stratum
(``scheduling_stratum_push.push_stratum_snapshot``) pushes. The status push
(``push_status_to_data_service``) left this seam under A109 (W23, form (beta)): it
mints with its own account from ``STATUS_PUSH_CLIENT_*`` (``TestStatusSeam``
below; the planted REDs are in ``test_status_push_dedicated_account.py``). The
ruled behaviour of the general seam, each case proven two-sided:

* SA credentials present -> the service-account token is used and the legacy
  ``AUTOM8Y_DATA_API_KEY`` is NOT read.
* SA credentials absent -> the legacy key is used, exactly as before.
* SA credentials present but the mint fails -> a named
  ``ServiceTokenMintError`` -> the push logs
  ``<push>_service_token_mint_failed`` and returns success=False. There is NO
  fallback to the legacy key, and NO silent "skip".

The ``TestRealTokenManager`` cases drive the REAL ServiceTokenAuthProvider and
TokenManager against a respx-mocked auth endpoint (no network). They pin the
exact exchange an ``sa_*`` client sends with no ``business_id`` (Basic auth,
``{}`` body), and show that a 400 refusal from that endpoint (the
``AUTH-TEB-004`` shape) fails visibly.
"""

from __future__ import annotations

import json
import threading
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx
from autom8y_core.errors import TokenAcquisitionError

from autom8_asana.services import gid_push
from autom8_asana.services import scheduling_stratum_push as stratum

_DATA_URL = "http://data.internal.test"
_AUTH_EXCHANGE_URL = "https://auth.api.autom8y.io/tokens/exchange-business"
_SA_BEARER = "sa-bearer-from-provider"
_LEGACY_BEARER = "legacy-bearer-from-env"
_UNIT_PROJECT_GID = "1201081073731555"

_SEAM_ENV = (
    "SERVICE_CLIENT_ID",
    "SERVICE_CLIENT_SECRET",
    "SERVICE_CLIENT_SECRET_ARN",
    "STATUS_PUSH_CLIENT_ID",
    "STATUS_PUSH_CLIENT_SECRET",
    "STATUS_PUSH_CLIENT_SECRET_ARN",
    "AUTOM8Y_DATA_API_KEY",
    "AUTOM8Y_DATA_API_KEY_ARN",
    "AUTOM8Y_DATA_URL",
    "STATUS_PUSH_ENABLED",
    "GID_PUSH_ENABLED",
    "VOCAB_SYNC_ENABLED",
    "SCHEDULING_STRATUM_PUSH_ENABLED",
)


# ---------------------------------------------------------------------------
# Fixtures and fakes
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _hermetic_seam(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Clear every seam variable and the cached provider around each test."""
    for name in _SEAM_ENV:
        monkeypatch.delenv(name, raising=False)
    gid_push._reset_service_token_provider()
    gid_push._reset_status_push_token_provider()
    yield
    gid_push._reset_service_token_provider()
    gid_push._reset_status_push_token_provider()


class _ProviderRecorder:
    """Stand-in for ServiceTokenAuthProvider, with the same surface."""

    def __init__(
        self,
        *,
        bearer: str = _SA_BEARER,
        get_exc: Exception | None = None,
        init_exc: Exception | None = None,
    ) -> None:
        self.bearer = bearer
        self.get_exc = get_exc
        self.init_exc = init_exc
        self.constructed = 0
        self.get_calls = 0
        self.closed = 0

    def factory(self) -> type:
        recorder = self

        class _FakeProvider:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                if recorder.init_exc is not None:
                    raise recorder.init_exc
                recorder.constructed += 1

            def get_secret(self, key: str) -> str:
                recorder.get_calls += 1
                if recorder.get_exc is not None:
                    raise recorder.get_exc
                return recorder.bearer

            def close(self) -> None:
                recorder.closed += 1

        return _FakeProvider


def _install_provider(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> _ProviderRecorder:
    recorder = _ProviderRecorder(**kwargs)
    monkeypatch.setattr(
        "autom8_asana.auth.service_token.ServiceTokenAuthProvider", recorder.factory()
    )
    return recorder


def _set_sa(monkeypatch: pytest.MonkeyPatch, *, arn_form: bool = False) -> None:
    monkeypatch.setenv("SERVICE_CLIENT_ID", "sa_testonly")
    monkeypatch.setenv(
        "SERVICE_CLIENT_SECRET_ARN" if arn_form else "SERVICE_CLIENT_SECRET", "test-only-value"
    )


def _set_status_push_sa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STATUS_PUSH_CLIENT_ID", "sa_statuspushtestonly")
    monkeypatch.setenv("STATUS_PUSH_CLIENT_SECRET", "status-push-test-only-value")


def _set_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOM8Y_DATA_API_KEY", _LEGACY_BEARER)


def _spy_legacy_reads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every name the seam passes to resolve_secret_from_env."""
    real = gid_push.resolve_secret_from_env
    names: list[str] = []

    def spy(name: str) -> str:
        names.append(name)
        return real(name)

    monkeypatch.setattr(gid_push, "resolve_secret_from_env", spy)
    return names


def _mock_logger(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    log = MagicMock()
    monkeypatch.setattr(gid_push, "logger", log)
    return log


def _events(log_method: MagicMock) -> list[str]:
    return [c.args[0] for c in log_method.call_args_list]


def _wire_http(monkeypatch: pytest.MonkeyPatch, status: int = 200, body: Any = None) -> AsyncMock:
    """Patch gid_push.Autom8yHttpClient; return the raw client whose .post is asserted."""
    raw = AsyncMock()
    raw.post.return_value = httpx.Response(status_code=status, json=body or {})
    raw_cm = AsyncMock()
    raw_cm.__aenter__.return_value = raw
    outer = MagicMock()
    outer.raw.return_value = raw_cm
    http_cls = MagicMock()
    http_cls.return_value = AsyncMock()
    http_cls.return_value.__aenter__.return_value = outer
    monkeypatch.setattr(gid_push, "Autom8yHttpClient", http_cls)
    return raw


def _bearer_sent(raw: AsyncMock) -> str:
    raw.post.assert_called_once()
    return str(raw.post.call_args.kwargs["headers"]["Authorization"])


def _status_entry() -> dict[str, Any]:
    return {
        "phone": "+15551230001",
        "vertical": "chiropractor",
        "pipeline_type": "unit",
        "account_activity": "active",
        "pipeline_section": "Active",
        "stage_entered_at": "2026-07-08T00:00:00+00:00",
    }


def _gid_index() -> Any:
    from datetime import UTC, datetime

    from autom8_asana.services.gid_lookup import GidLookupIndex

    return GidLookupIndex(
        lookup_dict={"pv1:+15551230001:chiropractor": "1111111111111111"},
        created_at=datetime(2026, 9, 30, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# 1. Selection: SA present -> SA token, legacy NOT read
# ---------------------------------------------------------------------------


class TestSelectionServiceAccountPresent:
    def test_sa_token_used_and_legacy_not_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        recorder = _install_provider(monkeypatch)
        reads = _spy_legacy_reads(monkeypatch)

        assert gid_push._get_auth_token() == _SA_BEARER
        assert recorder.constructed == 1
        assert recorder.get_calls == 1
        assert "AUTOM8Y_DATA_API_KEY" not in reads

    def test_lambda_arn_secret_form_counts_as_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_sa(monkeypatch, arn_form=True)
        _set_legacy(monkeypatch)
        _install_provider(monkeypatch)
        reads = _spy_legacy_reads(monkeypatch)

        assert gid_push._get_auth_token() == _SA_BEARER
        assert "AUTOM8Y_DATA_API_KEY" not in reads

    def test_selection_line_names_the_source(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _install_provider(monkeypatch)
        log = _mock_logger(monkeypatch)

        gid_push._get_auth_token()

        selected = [
            c.kwargs["extra"]["credential_source"]
            for c in log.info.call_args_list
            if c.args[0] == "data_push_credential_selected"
        ]
        assert selected == ["service_account"]


# ---------------------------------------------------------------------------
# 2. Selection: SA absent -> legacy fallback
# ---------------------------------------------------------------------------


class TestSelectionServiceAccountAbsent:
    def test_legacy_key_used_and_no_provider_built(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_legacy(monkeypatch)
        recorder = _install_provider(monkeypatch)
        reads = _spy_legacy_reads(monkeypatch)

        assert gid_push._get_auth_token() == _LEGACY_BEARER
        assert recorder.constructed == 0
        assert reads == ["AUTOM8Y_DATA_API_KEY"]

    def test_nothing_configured_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        recorder = _install_provider(monkeypatch)
        log = _mock_logger(monkeypatch)

        assert gid_push._get_auth_token() is None
        assert recorder.constructed == 0
        selected = [
            c.kwargs["extra"]["credential_source"]
            for c in log.info.call_args_list
            if c.args[0] == "data_push_credential_selected"
        ]
        assert selected == ["none"]

    def test_blank_values_count_as_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SERVICE_CLIENT_ID", "  ")
        monkeypatch.setenv("SERVICE_CLIENT_SECRET", "")
        _set_legacy(monkeypatch)
        recorder = _install_provider(monkeypatch)

        assert gid_push._get_auth_token() == _LEGACY_BEARER
        assert recorder.constructed == 0


# ---------------------------------------------------------------------------
# 3. Selection: SA present but mint fails -> named error, NO fallback
# ---------------------------------------------------------------------------


class TestSelectionMintFailureNoFallback:
    def test_exchange_refusal_raises_named_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        _install_provider(
            monkeypatch,
            get_exc=TokenAcquisitionError("Token exchange failed with status 400", status_code=400),
        )
        reads = _spy_legacy_reads(monkeypatch)

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_auth_token()

        assert caught.value.reason == gid_push.MINT_REASON_EXCHANGE_FAILED
        assert caught.value.status_code == 400
        assert caught.value.error_type == "TokenAcquisitionError"
        assert "AUTOM8Y_DATA_API_KEY" not in reads

    def test_provider_build_failure_raises_named_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        _install_provider(monkeypatch, init_exc=RuntimeError("extension unreachable"))
        reads = _spy_legacy_reads(monkeypatch)

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_auth_token()

        assert caught.value.reason == gid_push.MINT_REASON_PROVIDER_INIT_FAILED
        assert caught.value.error_type == "RuntimeError"
        assert "AUTOM8Y_DATA_API_KEY" not in reads

    def test_empty_bearer_raises_named_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        _install_provider(monkeypatch, bearer="")

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_auth_token()

        assert caught.value.reason == gid_push.MINT_REASON_EMPTY_BEARER

    @pytest.mark.parametrize("present", ["SERVICE_CLIENT_ID", "SERVICE_CLIENT_SECRET"])
    def test_half_configured_pair_raises_not_legacy(
        self, monkeypatch: pytest.MonkeyPatch, present: str
    ) -> None:
        monkeypatch.setenv(present, "test-only-value")
        _set_legacy(monkeypatch)
        recorder = _install_provider(monkeypatch)
        reads = _spy_legacy_reads(monkeypatch)

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_auth_token()

        assert caught.value.reason == gid_push.MINT_REASON_PARTIAL_CREDENTIALS
        assert recorder.constructed == 0
        assert "AUTOM8Y_DATA_API_KEY" not in reads

    def test_error_message_carries_no_credential_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_sa(monkeypatch)
        _install_provider(monkeypatch, get_exc=TokenAcquisitionError("refused", status_code=401))

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_auth_token()

        assert "test-only-value" not in str(caught.value)
        assert "sa_testonly" not in str(caught.value)


# ---------------------------------------------------------------------------
# 4. Provider lifetime: reused across pushes, rebuilt only on client-id change
# ---------------------------------------------------------------------------


class TestProviderReuse:
    def test_one_provider_per_process(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        recorder = _install_provider(monkeypatch)

        gid_push._get_auth_token()
        gid_push._get_auth_token()
        gid_push._get_auth_token()

        assert recorder.constructed == 1
        assert recorder.get_calls == 3  # the provider's TokenManager owns caching

    def test_client_id_change_rebuilds_and_closes_old(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_sa(monkeypatch)
        recorder = _install_provider(monkeypatch)

        gid_push._get_auth_token()
        monkeypatch.setenv("SERVICE_CLIENT_ID", "sa_rotated")
        gid_push._get_auth_token()

        assert recorder.constructed == 2
        assert recorder.closed == 1

    def test_failed_build_is_not_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        recorder = _install_provider(monkeypatch, init_exc=RuntimeError("transient"))

        with pytest.raises(gid_push.ServiceTokenMintError):
            gid_push._get_auth_token()

        recorder.init_exc = None
        assert gid_push._get_auth_token() == _SA_BEARER
        assert recorder.constructed == 1


async def test_resolve_runs_off_the_event_loop_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, int] = {}

    def fake() -> str:
        seen["thread"] = threading.get_ident()
        return "x"

    monkeypatch.setattr(gid_push, "_get_auth_token", fake)

    assert await gid_push._resolve_auth_token() == "x"
    assert seen["thread"] != threading.get_ident()


# ---------------------------------------------------------------------------
# 5. The real TokenManager against a mocked auth endpoint (no network)
# ---------------------------------------------------------------------------


class TestRealTokenManager:
    def test_sa_exchange_shape_and_token_cache(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        reads = _spy_legacy_reads(monkeypatch)
        body = {
            "data": {"access_token": "jwt-minted-once", "token_type": "bearer", "expires_in": 1800},
            "meta": {"request_id": "req-1"},
        }
        with respx.mock(assert_all_mocked=True, assert_all_called=True) as router:
            route = router.post(_AUTH_EXCHANGE_URL).mock(
                return_value=httpx.Response(200, json=body)
            )
            first = gid_push._get_auth_token()
            second = gid_push._get_auth_token()
            gid_push._reset_service_token_provider()
            third = gid_push._get_auth_token()

        assert first == second == third == "jwt-minted-once"
        # Reused while fresh (1 exchange for 2 calls); a fresh provider exchanges again.
        assert route.call_count == 2
        request = route.calls[0].request
        assert request.headers["authorization"].startswith("Basic ")
        # No business_id is sent: ServiceTokenAuthProvider builds Config without one.
        assert json.loads(request.content) == {}
        assert "AUTOM8Y_DATA_API_KEY" not in reads

    def test_teb004_shaped_refusal_fails_visibly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        reads = _spy_legacy_reads(monkeypatch)
        refusal = {"error": {"code": "AUTH-TEB-004", "message": "business_id required"}}
        with respx.mock(assert_all_mocked=True, assert_all_called=True) as router:
            route = router.post(_AUTH_EXCHANGE_URL).mock(
                return_value=httpx.Response(400, json=refusal)
            )
            with pytest.raises(gid_push.ServiceTokenMintError) as caught:
                gid_push._get_auth_token()

        assert caught.value.reason == gid_push.MINT_REASON_EXCHANGE_FAILED
        assert caught.value.status_code == 400
        assert route.call_count == 1  # 4xx is not retried by TokenManager
        assert "AUTOM8Y_DATA_API_KEY" not in reads


# ---------------------------------------------------------------------------
# 6. The three seams (+ vocab) on the new path, each two-sided
# ---------------------------------------------------------------------------


class TestStatusSeam:
    """A109: the status push mints from STATUS_PUSH_CLIENT_* only (W23 form (beta))."""

    async def test_status_push_bearer_reaches_the_sync_post(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_status_push_sa(monkeypatch)
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setenv("STATUS_PUSH_ENABLED", "true")
        _install_provider(monkeypatch)
        monkeypatch.setattr(gid_push, "emit_metric", MagicMock())
        raw = _wire_http(monkeypatch, body={"deleted": 0, "inserted": 1})

        ok = await gid_push.push_status_to_data_service(
            [_status_entry()], "2026-09-30T00:00:00+00:00", data_service_url=_DATA_URL
        )

        assert ok is True
        assert _bearer_sent(raw) == f"Bearer {_SA_BEARER}"
        assert raw.post.call_args.args[0] == f"{_DATA_URL}/api/v1/account-status/sync"

    async def test_no_status_push_account_is_a_named_failure_not_legacy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The cure's "SA absent -> legacy" rule no longer applies to the status push."""
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setenv("STATUS_PUSH_ENABLED", "true")
        recorder = _install_provider(monkeypatch)
        emit = MagicMock()
        monkeypatch.setattr(gid_push, "emit_metric", emit)
        log = _mock_logger(monkeypatch)
        raw = _wire_http(monkeypatch, body={"deleted": 0, "inserted": 1})

        ok = await gid_push.push_status_to_data_service(
            [_status_entry()], "2026-09-30T00:00:00+00:00", data_service_url=_DATA_URL
        )

        assert ok is False
        raw.post.assert_not_called()
        assert recorder.constructed == 0
        failed = next(
            c
            for c in log.error.call_args_list
            if c.args[0] == "status_push_service_token_mint_failed"
        )
        assert failed.kwargs["extra"]["reason"] == gid_push.MINT_REASON_CREDENTIALS_ABSENT
        assert failed.kwargs["extra"]["credential_lane"] == "status_push"
        assert failed.kwargs["extra"]["fallback"] == "none"
        assert not [c for c in emit.call_args_list if c.args[0] == "StatusPushSkipped"]

    async def test_mint_failure_is_a_named_failure_not_a_skip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_status_push_sa(monkeypatch)
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setenv("STATUS_PUSH_ENABLED", "true")
        _install_provider(monkeypatch, get_exc=TokenAcquisitionError("refused", status_code=400))
        emit = MagicMock()
        monkeypatch.setattr(gid_push, "emit_metric", emit)
        log = _mock_logger(monkeypatch)
        raw = _wire_http(monkeypatch)

        ok = await gid_push.push_status_to_data_service(
            [_status_entry()], "2026-09-30T00:00:00+00:00", data_service_url=_DATA_URL
        )

        assert ok is False
        raw.post.assert_not_called()
        assert "status_push_service_token_mint_failed" in _events(log.error)
        failed = next(
            c
            for c in log.error.call_args_list
            if c.args[0] == "status_push_service_token_mint_failed"
        )
        assert failed.kwargs["extra"]["reason"] == "exchange_failed"
        assert failed.kwargs["extra"]["status_code"] == 400
        assert failed.kwargs["extra"]["fallback"] == "none"
        assert "status_push_skipped" not in _events(log.warning)
        assert not [c for c in emit.call_args_list if c.args[0] == "StatusPushSkipped"]

    async def test_orchestrator_records_failure_and_success_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from autom8_asana.lambda_handlers import push_orchestrator

        _set_status_push_sa(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setenv("STATUS_PUSH_ENABLED", "true")
        monkeypatch.setenv("AUTOM8Y_DATA_URL", _DATA_URL)
        _install_provider(monkeypatch, get_exc=TokenAcquisitionError("refused", status_code=400))
        monkeypatch.setattr(gid_push, "emit_metric", MagicMock())
        monkeypatch.setattr(
            gid_push, "extract_status_from_dataframe", lambda **_: [_status_entry()]
        )
        orch_emit = MagicMock()
        orch_log = MagicMock()
        monkeypatch.setattr(push_orchestrator, "emit_metric", orch_emit)
        monkeypatch.setattr(push_orchestrator, "logger", orch_log)
        raw = _wire_http(monkeypatch)
        cache = MagicMock()
        cache.get_async = AsyncMock(return_value=MagicMock(dataframe=object()))

        await push_orchestrator._push_account_status_for_completed_entities(
            completed_entities=["unit"],
            get_project_gid=lambda _et: _UNIT_PROJECT_GID,
            cache=cache,
            invocation_id="ecs-test",
        )

        raw.post.assert_not_called()
        assert [c.args[0] for c in orch_emit.call_args_list].count("StatusPushFailure") == 1
        assert "StatusPushSuccess" not in [c.args[0] for c in orch_emit.call_args_list]
        complete = [c for c in orch_log.info.call_args_list if c.args[0] == "status_push_complete"]
        assert len(complete) == 1
        assert complete[0].kwargs["extra"]["success"] is False

    async def test_orchestrator_records_success_on_the_status_push_account(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from autom8_asana.lambda_handlers import push_orchestrator

        _set_status_push_sa(monkeypatch)
        monkeypatch.setenv("STATUS_PUSH_ENABLED", "true")
        monkeypatch.setenv("AUTOM8Y_DATA_URL", _DATA_URL)
        _install_provider(monkeypatch)
        monkeypatch.setattr(gid_push, "emit_metric", MagicMock())
        monkeypatch.setattr(
            gid_push, "extract_status_from_dataframe", lambda **_: [_status_entry()]
        )
        orch_emit = MagicMock()
        orch_log = MagicMock()
        monkeypatch.setattr(push_orchestrator, "emit_metric", orch_emit)
        monkeypatch.setattr(push_orchestrator, "logger", orch_log)
        raw = _wire_http(monkeypatch, body={"deleted": 0, "inserted": 1})
        cache = MagicMock()
        cache.get_async = AsyncMock(return_value=MagicMock(dataframe=object()))

        await push_orchestrator._push_account_status_for_completed_entities(
            completed_entities=["unit"],
            get_project_gid=lambda _et: _UNIT_PROJECT_GID,
            cache=cache,
            invocation_id="ecs-test",
        )

        assert _bearer_sent(raw) == f"Bearer {_SA_BEARER}"
        assert "StatusPushSuccess" in [c.args[0] for c in orch_emit.call_args_list]
        complete = [c for c in orch_log.info.call_args_list if c.args[0] == "status_push_complete"]
        assert complete[0].kwargs["extra"]["success"] is True


class TestGidSeam:
    async def test_sa_bearer_reaches_the_sync_post(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        _install_provider(monkeypatch)
        raw = _wire_http(monkeypatch, body={"accepted": 1, "replaced": 0})

        ok = await gid_push.push_gid_mappings_to_data_service(
            _UNIT_PROJECT_GID, _gid_index(), data_service_url=_DATA_URL
        )

        assert ok is True
        assert _bearer_sent(raw) == f"Bearer {_SA_BEARER}"

    async def test_legacy_bearer_when_sa_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_legacy(monkeypatch)
        raw = _wire_http(monkeypatch, body={"accepted": 1, "replaced": 0})

        ok = await gid_push.push_gid_mappings_to_data_service(
            _UNIT_PROJECT_GID, _gid_index(), data_service_url=_DATA_URL
        )

        assert ok is True
        assert _bearer_sent(raw) == f"Bearer {_LEGACY_BEARER}"

    async def test_mint_failure_is_named_and_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        _install_provider(monkeypatch, get_exc=TokenAcquisitionError("refused", status_code=400))
        log = _mock_logger(monkeypatch)
        raw = _wire_http(monkeypatch)

        ok = await gid_push.push_gid_mappings_to_data_service(
            _UNIT_PROJECT_GID, _gid_index(), data_service_url=_DATA_URL
        )

        assert ok is False
        raw.post.assert_not_called()
        assert "gid_push_service_token_mint_failed" in _events(log.error)
        assert "gid_push_skipped" not in _events(log.warning)


class TestStratumSeam:
    async def test_sa_bearer_reaches_the_sync_post(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        _install_provider(monkeypatch)
        raw = _wire_http(monkeypatch, body={"synced": 1})

        result = await stratum.push_stratum_snapshot(
            [{"guid": "g-1"}],
            "2026-09-30T00:00:00+00:00",
            dry_run=False,
            data_service_url=_DATA_URL,
        )

        assert result.pushed is True
        assert _bearer_sent(raw) == f"Bearer {_SA_BEARER}"
        assert raw.post.call_args.args[0] == f"{_DATA_URL}/api/v1/scheduling-stratum/sync"

    async def test_legacy_bearer_when_sa_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_legacy(monkeypatch)
        raw = _wire_http(monkeypatch, body={"synced": 1})

        result = await stratum.push_stratum_snapshot(
            [{"guid": "g-1"}],
            "2026-09-30T00:00:00+00:00",
            dry_run=False,
            data_service_url=_DATA_URL,
        )

        assert result.pushed is True
        assert _bearer_sent(raw) == f"Bearer {_LEGACY_BEARER}"

    async def test_mint_failure_is_named_and_not_pushed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        _install_provider(monkeypatch, get_exc=TokenAcquisitionError("refused", status_code=400))
        log = _mock_logger(monkeypatch)
        stratum_log = MagicMock()
        monkeypatch.setattr(stratum, "logger", stratum_log)
        raw = _wire_http(monkeypatch)

        result = await stratum.push_stratum_snapshot(
            [{"guid": "g-1"}],
            "2026-09-30T00:00:00+00:00",
            dry_run=False,
            data_service_url=_DATA_URL,
        )

        assert result.pushed is False
        assert result.dry_run is False
        raw.post.assert_not_called()
        assert "scheduling_stratum_push_service_token_mint_failed" in _events(log.error)
        assert "scheduling_stratum_push_skipped" not in _events(stratum_log.warning)

    async def test_missing_url_never_mints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_sa(monkeypatch)
        recorder = _install_provider(monkeypatch)

        result = await stratum.push_stratum_snapshot(
            [{"guid": "g-1"}], "2026-09-30T00:00:00+00:00", dry_run=False
        )

        assert result.pushed is False
        assert recorder.get_calls == 0


class TestVocabSeam:
    async def test_sa_bearer_and_named_mint_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from autom8_asana.contracts.vocabulary_sync import VocabularyOption

        options = [VocabularyOption(vertical_key="chiropractor", name="Chiropractor", enabled=True)]
        monkeypatch.setenv("VOCAB_SYNC_ENABLED", "true")
        _set_sa(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setattr(gid_push, "emit_metric", MagicMock())
        recorder = _install_provider(monkeypatch)
        log = _mock_logger(monkeypatch)
        monkeypatch.setattr(gid_push, "_push_to_data_service", AsyncMock(return_value=True))

        assert await gid_push.push_vocabulary_to_data_service(options, data_service_url=_DATA_URL)
        assert gid_push._push_to_data_service.call_args.kwargs["token"] == _SA_BEARER  # type: ignore[attr-defined]

        recorder.get_exc = TokenAcquisitionError("refused", status_code=400)
        assert not await gid_push.push_vocabulary_to_data_service(
            options, data_service_url=_DATA_URL
        )
        assert gid_push._push_to_data_service.await_count == 1  # type: ignore[attr-defined]
        assert "vocab_sync_service_token_mint_failed" in _events(log.error)
