"""PT-CI-03 A109 (operator word W23, form (beta)): the status push's own account.

The account-status push (``gid_push.push_status_to_data_service``) mints with a
DEDICATED service account, ``asana-status-push`` (auth registry: not
business-scoped, ``data:write`` only), read from ``STATUS_PUSH_CLIENT_ID`` and
``STATUS_PUSH_CLIENT_SECRET`` (the ``_ARN`` form counts). Every other push keeps
the general seam (``_get_auth_token``: ``SERVICE_CLIENT_*`` = ``asana-service``,
which stays business-scoped, else the legacy key).

Planted REDs, each two-sided:
  * the status push mints ONLY from the new names, even when the asana-service
    pair and the legacy key are also set (a recorder captures the provider's
    arguments; a respx-mocked exchange shows the Basic credential on the wire);
  * the new names absent -> a named ``credentials_absent`` failure: no provider is
    built, no other credential is read, nothing is POSTed;
  * a half pair -> ``partial_credentials``; a secret that resolves empty ->
    ``provider_init_failed`` (the provider's SERVICE_CLIENT_* defaults are never
    reached);
  * no other seam (gid, vocab, stratum, the general ``_get_auth_token``) ever uses
    the new names;
  * the asana-service names never reach the status push (runtime and AST).
"""

from __future__ import annotations

import ast
import base64
import json
import pathlib
import threading
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
import respx

from autom8_asana.services import gid_push
from autom8_asana.services import scheduling_stratum_push as stratum

_SRC = pathlib.Path(gid_push.__file__).resolve().parents[1]
_GID_PUSH_PY = pathlib.Path(gid_push.__file__).resolve()

_DATA_URL = "http://data.internal.test"
_AUTH_EXCHANGE_URL = "https://auth.api.autom8y.io/tokens/exchange-business"

# SYNTHETIC values only. Distinct per account so a crossed wire is visible.
_STATUS_ID = "sa_" + "5" * 32
_STATUS_VALUE = "a8sa_status-push-synthetic-test-value"
_GENERAL_ID = "sa_" + "a" * 32  # stands in for asana-service
_GENERAL_VALUE = "a8sa_general-seam-synthetic-test-value"
_LEGACY_BEARER = "legacy-bearer-from-env"

_ALL_ENV = (
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

# The names the status lane must never read, and the general-seam functions it
# must never call.
_GENERAL_NAMES = {
    "SERVICE_CLIENT_ID_ENV_VAR",
    "SERVICE_CLIENT_CREDENTIAL_ENV_VAR",
    "LEGACY_DATA_API_KEY_ENV_VAR",
}
_GENERAL_FUNCS = {
    "_get_auth_token",
    "_resolve_auth_token",
    "_mint_service_token",
    "_get_service_token_provider",
    "_service_account_presence",
}
_STATUS_NAMES = {"STATUS_PUSH_CLIENT_ID_ENV_VAR", "STATUS_PUSH_CLIENT_CREDENTIAL_ENV_VAR"}
_STATUS_FUNCS = {
    "_get_status_push_token",
    "_resolve_status_push_token",
    "_get_status_push_provider",
    "_build_status_push_provider",
    "_status_push_presence",
}


# ---------------------------------------------------------------------------
# Fixtures and fakes
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch: pytest.MonkeyPatch) -> Any:
    for name in _ALL_ENV:
        monkeypatch.delenv(name, raising=False)
    gid_push._reset_service_token_provider()
    gid_push._reset_status_push_token_provider()
    yield
    gid_push._reset_service_token_provider()
    gid_push._reset_status_push_token_provider()


class _Recorder:
    """Stand-in for ServiceTokenAuthProvider that records how it was built."""

    def __init__(self, *, get_exc: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.get_exc = get_exc
        self.closed = 0

    def factory(self) -> type:
        recorder = self

        class _Fake:
            def __init__(
                self, client_id: str | None = None, client_secret: str | None = None, **kwargs: Any
            ) -> None:
                recorder.calls.append(
                    {"client_id": client_id, "client_secret": client_secret, **kwargs}
                )
                self._client_id = client_id

            def get_secret(self, key: str) -> str:
                if recorder.get_exc is not None:
                    raise recorder.get_exc
                return f"bearer-for-{self._client_id}"

            def close(self) -> None:
                recorder.closed += 1

        return _Fake


def _install(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> _Recorder:
    recorder = _Recorder(**kwargs)
    monkeypatch.setattr(
        "autom8_asana.auth.service_token.ServiceTokenAuthProvider", recorder.factory()
    )
    return recorder


def _set_status(monkeypatch: pytest.MonkeyPatch, *, arn_form: bool = False) -> None:
    monkeypatch.setenv("STATUS_PUSH_CLIENT_ID", _STATUS_ID)
    monkeypatch.setenv(
        "STATUS_PUSH_CLIENT_SECRET_ARN" if arn_form else "STATUS_PUSH_CLIENT_SECRET",
        _STATUS_VALUE,
    )


def _set_general(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE_CLIENT_ID", _GENERAL_ID)
    monkeypatch.setenv("SERVICE_CLIENT_SECRET", _GENERAL_VALUE)


def _set_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOM8Y_DATA_API_KEY", _LEGACY_BEARER)


def _spy_resolves(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every name gid_push passes to resolve_secret_from_env."""
    real = gid_push.resolve_secret_from_env
    names: list[str] = []

    def spy(name: str, *args: Any, **kwargs: Any) -> str:
        names.append(name)
        return real(name, *args, **kwargs)

    monkeypatch.setattr(gid_push, "resolve_secret_from_env", spy)
    return names


def _wire_http(monkeypatch: pytest.MonkeyPatch, status: int = 200, body: Any = None) -> Any:
    from unittest.mock import AsyncMock

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


def _status_entry() -> dict[str, Any]:
    return {
        "phone": "+15551230001",
        "vertical": "chiropractor",
        "pipeline_type": "unit",
        "account_activity": "active",
        "pipeline_section": "Active",
        "stage_entered_at": "2026-07-08T00:00:00+00:00",
    }


async def _push_status() -> bool:
    return await gid_push.push_status_to_data_service(
        [_status_entry()], "2026-10-01T00:00:00+00:00", data_service_url=_DATA_URL
    )


def _mint_failure(log: MagicMock) -> dict[str, Any]:
    call = next(
        c for c in log.error.call_args_list if c.args[0] == "status_push_service_token_mint_failed"
    )
    return dict(call.kwargs["extra"])


# ---------------------------------------------------------------------------
# RED 1: the status push mints ONLY from the new names
# ---------------------------------------------------------------------------


class TestMintsOnlyFromTheNewNames:
    def test_provider_is_built_from_the_status_push_values_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_status(monkeypatch)
        _set_general(monkeypatch)
        _set_legacy(monkeypatch)
        recorder = _install(monkeypatch)
        resolved = _spy_resolves(monkeypatch)

        token = gid_push._get_status_push_token()

        assert token == f"bearer-for-{_STATUS_ID}"
        assert recorder.calls == [{"client_id": _STATUS_ID, "client_secret": _STATUS_VALUE}]
        assert resolved == ["STATUS_PUSH_CLIENT_SECRET"]

    def test_real_exchange_presents_the_status_push_account(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """REAL provider + TokenManager, respx-mocked auth (no network)."""
        _set_status(monkeypatch)
        _set_general(monkeypatch)
        _set_legacy(monkeypatch)
        body = {
            "data": {"access_token": "jwt-status-push", "token_type": "bearer", "expires_in": 300},
            "meta": {"request_id": "req-1"},
        }
        with respx.mock(assert_all_mocked=True, assert_all_called=True) as router:
            route = router.post(_AUTH_EXCHANGE_URL).mock(
                return_value=httpx.Response(200, json=body)
            )
            first = gid_push._get_status_push_token()
            second = gid_push._get_status_push_token()

        assert first == second == "jwt-status-push"
        assert route.call_count == 1  # cached while fresh
        request = route.calls[0].request
        scheme, _, encoded = request.headers["authorization"].partition(" ")
        assert scheme == "Basic"
        presented = base64.b64decode(encoded).decode()
        assert presented == f"{_STATUS_ID}:{_STATUS_VALUE}"
        assert _GENERAL_ID not in presented and _GENERAL_VALUE not in presented
        # No business_id and no requested scopes: the grant decides the token.
        assert json.loads(request.content) == {}

    async def test_the_sync_post_carries_the_status_push_bearer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_status(monkeypatch)
        _set_general(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setenv("STATUS_PUSH_ENABLED", "true")
        _install(monkeypatch)
        monkeypatch.setattr(gid_push, "emit_metric", MagicMock())
        raw = _wire_http(monkeypatch, body={"deleted": 0, "inserted": 1})

        assert await _push_status() is True
        headers = raw.post.call_args.kwargs["headers"]
        assert headers["Authorization"] == f"Bearer bearer-for-{_STATUS_ID}"

    def test_lambda_arn_secret_form_counts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_status(monkeypatch, arn_form=True)
        recorder = _install(monkeypatch)
        seen: list[str] = []

        def fake_resolve(name: str, *args: Any, **kwargs: Any) -> str:
            seen.append(name)
            return "resolved-from-arn"

        monkeypatch.setattr(gid_push, "resolve_secret_from_env", fake_resolve)

        gid_push._get_status_push_token()

        assert seen == ["STATUS_PUSH_CLIENT_SECRET"]
        assert recorder.calls == [{"client_id": _STATUS_ID, "client_secret": "resolved-from-arn"}]

    def test_selection_line_names_the_status_lane(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_status(monkeypatch)
        _install(monkeypatch)
        log = MagicMock()
        monkeypatch.setattr(gid_push, "logger", log)

        gid_push._get_status_push_token()

        selected = [
            c for c in log.info.call_args_list if c.args[0] == "data_push_credential_selected"
        ]
        assert len(selected) == 1
        assert selected[0].kwargs["extra"] == {
            "credential_source": "service_account",
            "credential_lane": "status_push",
        }


# ---------------------------------------------------------------------------
# RED 2: the new names absent -> a visible, named failure (no fallback)
# ---------------------------------------------------------------------------


class TestNewNamesAbsent:
    def test_absent_raises_credentials_absent_without_reading_anything(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_general(monkeypatch)
        _set_legacy(monkeypatch)
        recorder = _install(monkeypatch)
        resolved = _spy_resolves(monkeypatch)

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_status_push_token()

        assert caught.value.reason == gid_push.MINT_REASON_CREDENTIALS_ABSENT
        assert recorder.calls == []
        assert resolved == []

    async def test_absent_push_fails_loud_and_posts_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_general(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setenv("STATUS_PUSH_ENABLED", "true")
        recorder = _install(monkeypatch)
        emit = MagicMock()
        monkeypatch.setattr(gid_push, "emit_metric", emit)
        log = MagicMock()
        monkeypatch.setattr(gid_push, "logger", log)
        raw = _wire_http(monkeypatch)

        assert await _push_status() is False

        raw.post.assert_not_called()
        assert recorder.calls == []
        extra = _mint_failure(log)
        assert extra["reason"] == "credentials_absent"
        assert extra["fallback"] == "none"
        assert extra["credential_lane"] == "status_push"
        # A failure, not a skip: no StatusPushSkipped, no status_push_skipped line.
        assert not [c for c in emit.call_args_list if c.args[0] == "StatusPushSkipped"]
        assert "status_push_skipped" not in [c.args[0] for c in log.warning.call_args_list]

    def test_blank_values_count_as_absent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STATUS_PUSH_CLIENT_ID", "   ")
        monkeypatch.setenv("STATUS_PUSH_CLIENT_SECRET", "")
        recorder = _install(monkeypatch)

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_status_push_token()

        assert caught.value.reason == "credentials_absent"
        assert recorder.calls == []


# ---------------------------------------------------------------------------
# RED 3: half pairs and empty resolutions never fall back
# ---------------------------------------------------------------------------


class TestNoFallback:
    @pytest.mark.parametrize(
        "present",
        [
            ("STATUS_PUSH_CLIENT_ID",),
            ("STATUS_PUSH_CLIENT_SECRET",),
            ("STATUS_PUSH_CLIENT_SECRET_ARN",),
        ],
    )
    def test_half_pair_is_partial_credentials(
        self, monkeypatch: pytest.MonkeyPatch, present: tuple[str, ...]
    ) -> None:
        _set_general(monkeypatch)
        _set_legacy(monkeypatch)
        for name in present:
            monkeypatch.setenv(name, "x-test-only")
        recorder = _install(monkeypatch)
        resolved = _spy_resolves(monkeypatch)

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_status_push_token()

        assert caught.value.reason == gid_push.MINT_REASON_PARTIAL_CREDENTIALS
        assert recorder.calls == []
        assert resolved == []

    def test_secret_resolving_empty_never_reaches_the_provider_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ServiceTokenAuthProvider substitutes SERVICE_CLIENT_* for an EMPTY argument.
        The status lane refuses before constructing it, so asana-service's pair can
        never be picked up through that default."""
        _set_status(monkeypatch)
        _set_general(monkeypatch)
        monkeypatch.setattr(gid_push, "resolve_secret_from_env", lambda *_a, **_k: "")
        recorder = _install(monkeypatch)

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_status_push_token()

        assert caught.value.reason == gid_push.MINT_REASON_PROVIDER_INIT_FAILED
        assert caught.value.error_type == "ValueError"
        assert recorder.calls == []

    def test_exchange_refusal_is_named_with_status(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from autom8y_core.errors import TokenAcquisitionError

        _set_status(monkeypatch)
        _install(monkeypatch, get_exc=TokenAcquisitionError("refused", status_code=403))

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_status_push_token()

        assert caught.value.reason == gid_push.MINT_REASON_EXCHANGE_FAILED
        assert caught.value.status_code == 403

    def test_error_text_carries_no_credential_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from autom8y_core.errors import TokenAcquisitionError

        _set_status(monkeypatch)
        _install(monkeypatch, get_exc=TokenAcquisitionError(f"boom {_STATUS_VALUE}"))

        with pytest.raises(gid_push.ServiceTokenMintError) as caught:
            gid_push._get_status_push_token()

        assert _STATUS_VALUE not in str(caught.value)
        assert _STATUS_ID not in str(caught.value)


# ---------------------------------------------------------------------------
# RED 4: no other seam uses the new names
# ---------------------------------------------------------------------------


class TestOtherSeamsNeverUseTheNewNames:
    def test_general_seam_ignores_status_names(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Only the status pair set: the general seam sees "no SA" and reads legacy."""
        _set_status(monkeypatch)
        _set_legacy(monkeypatch)
        recorder = _install(monkeypatch)

        assert gid_push._get_auth_token() == _LEGACY_BEARER
        assert recorder.calls == []

    async def test_gid_push_does_not_mint_from_status_names(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from datetime import UTC, datetime

        from autom8_asana.services.gid_lookup import GidLookupIndex

        _set_status(monkeypatch)
        _set_legacy(monkeypatch)
        recorder = _install(monkeypatch)
        monkeypatch.setattr(gid_push, "emit_metric", MagicMock())
        raw = _wire_http(monkeypatch, body={"accepted": 1, "replaced": 0})
        index = GidLookupIndex(
            lookup_dict={"pv1:+15551230001:chiropractor": "1111111111111111"},
            created_at=datetime(2026, 10, 1, tzinfo=UTC),
        )

        ok = await gid_push.push_gid_mappings_to_data_service(
            project_gid="1201081073731555", index=index, data_service_url=_DATA_URL
        )

        assert ok is True
        assert raw.post.call_args.kwargs["headers"]["Authorization"] == f"Bearer {_LEGACY_BEARER}"
        assert recorder.calls == []

    async def test_stratum_push_does_not_mint_from_status_names(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_status(monkeypatch)
        _set_legacy(monkeypatch)
        recorder = _install(monkeypatch)
        raw = _wire_http(monkeypatch, body={"synced": 1})

        result = await stratum.push_stratum_snapshot(
            [{"guid": "g-1"}],
            "2026-10-01T00:00:00+00:00",
            dry_run=False,
            data_service_url=_DATA_URL,
        )

        assert result.pushed is True
        assert raw.post.call_args.kwargs["headers"]["Authorization"] == f"Bearer {_LEGACY_BEARER}"
        assert recorder.calls == []

    async def test_vocab_push_does_not_mint_from_status_names(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from unittest.mock import AsyncMock

        from autom8_asana.contracts.vocabulary_sync import VocabularyOption

        options = [VocabularyOption(vertical_key="chiropractor", name="Chiropractor", enabled=True)]
        monkeypatch.setenv("VOCAB_SYNC_ENABLED", "true")
        _set_status(monkeypatch)
        _set_legacy(monkeypatch)
        monkeypatch.setattr(gid_push, "emit_metric", MagicMock())
        recorder = _install(monkeypatch)
        push = AsyncMock(return_value=True)
        monkeypatch.setattr(gid_push, "_push_to_data_service", push)

        assert await gid_push.push_vocabulary_to_data_service(options, data_service_url=_DATA_URL)
        assert push.call_args.kwargs["token"] == _LEGACY_BEARER
        assert recorder.calls == []

    def test_status_names_are_referenced_only_by_the_status_lane(self) -> None:
        """AST: across src/, the STATUS_PUSH_CLIENT_* names and the status-lane
        functions are referenced only inside the status lane and the status push."""
        offenders: list[str] = []
        for py in _SRC.rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            if "STATUS_PUSH_CLIENT" not in text and "status_push_token" not in text:
                continue
            if py.resolve() != _GID_PUSH_PY:
                offenders.append(str(py.relative_to(_SRC)))
        assert offenders == []

        tree = ast.parse(_GID_PUSH_PY.read_text(encoding="utf-8"))
        users: dict[str, set[str]] = {}
        for fn in (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
            for target in names & (_STATUS_NAMES | _STATUS_FUNCS):
                users.setdefault(target, set()).add(fn.name)
        allowed = _STATUS_FUNCS | {"push_status_to_data_service"}
        stray = {t: sorted(u - allowed) for t, u in users.items() if u - allowed}
        assert stray == {}
        assert users["_resolve_status_push_token"] == {"push_status_to_data_service"}

    def test_general_seam_functions_never_name_the_status_lane(self) -> None:
        tree = ast.parse(_GID_PUSH_PY.read_text(encoding="utf-8"))
        bad: dict[str, list[str]] = {}
        for fn in (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            if fn.name not in _GENERAL_FUNCS:
                continue
            names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
            hit = sorted(names & (_STATUS_NAMES | _STATUS_FUNCS))
            if hit:
                bad[fn.name] = hit
        assert bad == {}


# ---------------------------------------------------------------------------
# RED 5: the asana-service names never reach the status push
# ---------------------------------------------------------------------------


class TestAsanaServiceNamesNeverReachTheStatusPush:
    def test_status_lane_never_names_the_general_credentials(self) -> None:
        tree = ast.parse(_GID_PUSH_PY.read_text(encoding="utf-8"))
        bad: dict[str, list[str]] = {}
        lane = _STATUS_FUNCS | {"push_status_to_data_service"}
        for fn in (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            if fn.name not in lane:
                continue
            names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
            strings = {
                n.value
                for n in ast.walk(fn)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            }
            hit = sorted(
                (names & (_GENERAL_NAMES | _GENERAL_FUNCS))
                | {s for s in strings if s.startswith(("SERVICE_CLIENT", "AUTOM8Y_DATA_API_KEY"))}
            )
            if hit:
                bad[fn.name] = hit
        assert bad == {}

    def test_status_provider_is_separate_from_the_general_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_status(monkeypatch)
        _set_general(monkeypatch)
        recorder = _install(monkeypatch)

        status_token = gid_push._get_status_push_token()
        general_token = gid_push._get_auth_token()
        status_again = gid_push._get_status_push_token()

        assert status_token == status_again == f"bearer-for-{_STATUS_ID}"
        assert general_token == f"bearer-for-{None}"  # general builds with no args (its env)
        assert recorder.calls == [
            {"client_id": _STATUS_ID, "client_secret": _STATUS_VALUE},
            {"client_id": None, "client_secret": None},
        ]

    def test_status_provider_rebuilds_only_when_its_own_id_changes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_status(monkeypatch)
        recorder = _install(monkeypatch)

        gid_push._get_status_push_token()
        monkeypatch.setenv(
            "SERVICE_CLIENT_ID", _GENERAL_ID
        )  # the general id changing is irrelevant
        gid_push._get_status_push_token()
        assert len(recorder.calls) == 1
        monkeypatch.setenv("STATUS_PUSH_CLIENT_ID", "sa_" + "6" * 32)
        gid_push._get_status_push_token()
        assert len(recorder.calls) == 2
        assert recorder.closed == 1


# ---------------------------------------------------------------------------
# Wiring facts
# ---------------------------------------------------------------------------


def test_no_production_caller_passes_auth_token_to_the_status_push() -> None:
    """The ``auth_token=`` override is test surface only; every production call
    resolves through the status push's own account."""
    callers: list[str] = []
    for py in _SRC.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if name != "push_status_to_data_service":
                continue
            callers.append(str(py.relative_to(_SRC)))
            assert not any(k.arg == "auth_token" for k in node.keywords), py
            assert len(node.args) <= 2, py
    assert callers, "expected at least one production caller of push_status_to_data_service"


async def test_status_resolution_runs_off_the_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, int] = {}

    def fake() -> str:
        seen["thread"] = threading.get_ident()
        return "x"

    monkeypatch.setattr(gid_push, "_get_status_push_token", fake)

    assert await gid_push._resolve_status_push_token() == "x"
    assert seen["thread"] != threading.get_ident()
