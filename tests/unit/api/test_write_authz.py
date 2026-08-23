"""Two-sided teeth for RE-2 write-class authorization (SEC-001, layer 1).

Design of record: `.ledge/decisions/DESIGN-re2-two-layer-authz-2026-08-13.md`.
UV-P-4 of that design is the acceptance criterion this file discharges:

    "the deny-by-default allowlist of §5.1 L1-2 fails closed under every
     misconfiguration mode (unset env var, empty string, malformed value)
     | METHOD: two-sided test harness at implementation time — denied-caller
     RED / authorized-caller GREEN, plus a malformed-config RED"

Every control asserted here is proved in BOTH polarities. A test that only shows
a denial proves nothing: a gate that denies everything is indistinguishable from
a gate that is broken, and an unearned RED is as worthless as an unearned GREEN.
So each denial is paired with the minimal-delta case that must be ALLOWED.

The gate under test is the REAL `require_write_authz` dependency, not a
reimplementation. Denials are proved to happen BEFORE the handler body runs
(`_handler_calls`), which is what makes the control meaningful: a refused
request never reaches Asana and never spends the shared bot PAT.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AuthContext, get_auth_context
from autom8_asana.api.write_authz import (
    ALLOWLIST_ENV,
    MODE_ENV,
    AuthzMode,
    WriteClass,
    has_permission_no_wildcard,
    is_authorized,
    load_writer_allowlist,
    require_write_authz,
    resolve_mode,
    resolve_principal,
)
from autom8_asana.auth.dual_mode import AuthMode

ALL_ENV = [MODE_ENV, *ALLOWLIST_ENV.values()]


@pytest.fixture(autouse=True)
def _clean_authz_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from a fully unset environment.

    The suite-wide allowlist fixture in `tests/conftest.py` authorizes a set of
    test principals so pre-existing route tests keep passing. This file must NOT
    inherit that, or its RED cases would be testing the fixture rather than the
    gate. Stripping the env here is what keeps these teeth honest.
    """
    for name in ALL_ENV:
        monkeypatch.delenv(name, raising=False)


def _claims(
    *,
    sub: str = "sa-uuid-0000",
    client_id: str | None = None,
    scope: str | None = None,
    permissions: list[str] | None = None,
) -> SimpleNamespace:
    """A stand-in for the SDK's validated ServiceClaims.

    Only the attributes the gate reads are modelled. `service_name` mirrors the
    SDK's `@property` returning `sub` (claims.py:183-185).
    """
    return SimpleNamespace(
        sub=sub,
        service_name=sub,
        client_id=client_id,
        scope=scope,
        scopes=[],
        permissions=permissions or [],
    )


def _build_app(
    write_class: WriteClass,
    auth_context: AuthContext,
    *,
    claims_dict: dict[str, Any] | None = None,
) -> tuple[FastAPI, list[str]]:
    """Mount the REAL gate on a stub handler.

    Returns the app and a mutable list the handler appends to when it runs, so
    a test can prove the handler was never entered on a denial (rather than
    merely observing a 403 that might have come from anywhere).
    """
    app = FastAPI()
    handler_calls: list[str] = []

    @app.middleware("http")
    async def _state(request, call_next):  # type: ignore[no-untyped-def]
        request.state.request_id = "test-request-id"
        if claims_dict is not None:
            request.state.claims_dict = claims_dict
        return await call_next(request)

    @app.post("/w", dependencies=[Depends(require_write_authz(write_class))])
    async def _w() -> dict[str, bool]:
        handler_calls.append("entered")
        return {"ok": True}

    app.dependency_overrides[get_auth_context] = lambda: auth_context
    return app, handler_calls


def _jwt_ctx(claims: Any) -> AuthContext:
    return AuthContext(
        mode=AuthMode.JWT,
        asana_pat="bot-pat-placeholder",
        caller_service=getattr(claims, "sub", None),
        claims=claims,
    )


def _error_code(response: Any) -> str | None:
    """Pull the machine-readable code out of either envelope shape."""
    body = response.json()
    detail = body.get("detail", body)
    if isinstance(detail, dict) and "error" in detail:
        return detail["error"].get("code")
    return None


# ---------------------------------------------------------------------------
# Mode resolution — fails closed
# ---------------------------------------------------------------------------


class TestModeResolutionFailsClosed:
    """A misconfigured mode must degrade toward ENFORCE, never toward OBSERVE."""

    def test_unset_resolves_enforce(self) -> None:
        assert resolve_mode() is AuthzMode.ENFORCE

    @pytest.mark.parametrize(
        "raw",
        ["", "   ", "observ", "OBSERVE!", "off", "disabled", "true", "0", "enforce"],
    )
    def test_absent_or_malformed_resolves_enforce(
        self, monkeypatch: pytest.MonkeyPatch, raw: str
    ) -> None:
        """RED side: nothing except the exact literal buys a pass-through."""
        monkeypatch.setenv(MODE_ENV, raw)
        assert resolve_mode() is AuthzMode.ENFORCE

    @pytest.mark.parametrize("raw", ["observe", "OBSERVE", "  Observe  "])
    def test_exact_literal_resolves_observe(
        self, monkeypatch: pytest.MonkeyPatch, raw: str
    ) -> None:
        """GREEN side: without this, the RED above would be vacuous.

        If no input could ever produce OBSERVE, `resolve_mode` returning ENFORCE
        for garbage would prove nothing about fail-closed behaviour — it would
        just be a constant function.
        """
        monkeypatch.setenv(MODE_ENV, raw)
        assert resolve_mode() is AuthzMode.OBSERVE


# ---------------------------------------------------------------------------
# Allowlist parsing — fails closed
# ---------------------------------------------------------------------------


class TestAllowlistFailsClosed:
    @pytest.mark.parametrize("raw", ["", "   ", ",", ",,,", " , , "])
    def test_malformed_yields_empty_set(self, monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], raw)
        assert load_writer_allowlist(WriteClass.TASKS) == frozenset()

    def test_unset_yields_empty_set(self) -> None:
        assert load_writer_allowlist(WriteClass.TASKS) == frozenset()

    def test_wellformed_parses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], " svc-a , svc-b ,")
        assert load_writer_allowlist(WriteClass.TASKS) == frozenset({"svc-a", "svc-b"})

    def test_allowlists_are_per_write_class_not_shared(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Authorization for one class must not leak into another."""
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "svc-a")
        assert load_writer_allowlist(WriteClass.TASKS) == frozenset({"svc-a"})
        assert load_writer_allowlist(WriteClass.RECEIPTS) == frozenset()


# ---------------------------------------------------------------------------
# Principal resolution
# ---------------------------------------------------------------------------


class TestPrincipalResolution:
    def test_tier1_service_account_id_wins(self) -> None:
        req = SimpleNamespace(
            state=SimpleNamespace(claims_dict={"service_account_id": "canonical-sa"})
        )
        got = resolve_principal(req, _claims(sub="uuid", client_id="cid"))
        assert got.principal == "canonical-sa"
        assert got.tier == "service_account_id"

    def test_tier2_client_id_when_no_sa_id(self) -> None:
        req = SimpleNamespace(state=SimpleNamespace(claims_dict={}))
        got = resolve_principal(req, _claims(sub="uuid", client_id="cid"))
        assert got.principal == "cid"
        assert got.tier == "client_id"

    def test_tier3_sub_when_no_client_id(self) -> None:
        got = resolve_principal(None, _claims(sub="uuid"))
        assert got.principal == "uuid"
        assert got.tier in {"service_name", "sub"}

    def test_no_claims_is_unresolved(self) -> None:
        got = resolve_principal(None, None)
        assert got.principal is None

    def test_non_string_identity_is_never_a_principal(self) -> None:
        """An authorization key must be a real string or absent.

        A duck-typed object reaching the allowlist comparison would get to
        define its own `__eq__`. `resolve_principal` must skip any non-`str`
        tier and fall through, rather than admitting it.
        """

        class AlwaysEqual:
            def __eq__(self, other: object) -> bool:
                return True

        claims = SimpleNamespace(
            sub="real-sub",
            service_name="real-sub",
            client_id=AlwaysEqual(),
            scope=None,
            scopes=[],
            permissions=[],
        )
        got = resolve_principal(None, claims)
        assert got.principal == "real-sub"
        assert got.tier in {"service_name", "sub"}

    def test_local_claims_model_narrows_non_string_client_id_to_none(self) -> None:
        """DEV-1 construction-side pair for the resolver test above."""
        from autom8_asana.api.routes.internal import ServiceClaims as LocalClaims

        assert LocalClaims(sub="s", service_name="s", client_id=None).client_id is None
        assert LocalClaims(sub="s", service_name="s", client_id="cid").client_id == "cid"

    def test_lower_tier_cannot_override_higher_tier(self) -> None:
        """A caller controlling a lower-precedence field cannot demote itself.

        If precedence were 'match any identity field', a caller whose canonical
        `service_account_id` is NOT allowlisted could still get in by presenting
        an allowlisted `client_id`. Strict precedence forecloses that.
        """
        req = SimpleNamespace(
            state=SimpleNamespace(claims_dict={"service_account_id": "not-allowed"})
        )
        got = resolve_principal(req, _claims(sub="uuid", client_id="allowed-cid"))
        assert got.principal == "not-allowed"
        assert not is_authorized(got.principal, frozenset({"allowed-cid"}))


# ---------------------------------------------------------------------------
# Deny-by-default predicate
# ---------------------------------------------------------------------------


class TestIsAuthorizedDenyByDefault:
    def test_empty_allowlist_denies(self) -> None:
        assert is_authorized("svc-a", frozenset()) is False

    def test_unresolved_principal_denies(self) -> None:
        assert is_authorized(None, frozenset({"svc-a"})) is False

    def test_member_allowed(self) -> None:
        assert is_authorized("svc-a", frozenset({"svc-a"})) is True

    def test_star_in_allowlist_is_not_a_wildcard(self) -> None:
        """CORRECTION-3, config side.

        A literal "*" in the allowlist authorizes a principal NAMED "*" and
        nothing else. There must be no configuration value meaning "allow all" —
        that is the fail-open shape this whole finding is about.
        """
        assert is_authorized("svc-a", frozenset({"*"})) is False
        assert is_authorized("*", frozenset({"*"})) is True


# ---------------------------------------------------------------------------
# CORRECTION-3 — the axis ruling, proved
# ---------------------------------------------------------------------------


class TestCorrection3WildcardAxis:
    """The `has_scope` wildcard fail-open must not be inherited by this gate.

    `autom8y_auth.claims.ServiceClaims.has_scope` short-circuits True on
    `scope == "*"` (claims.py:220-222). These tests prove the RE-2 gate is
    immune to that carrier, on both the identity axis and the permissions axis.
    """

    def test_sdk_wildcard_fail_open_still_exists_upstream(self) -> None:
        """Pin the upstream hazard the axis ruling routes around.

        If a future SDK bump removes the wildcard, this test fails and the axis
        ruling should be revisited — deliberately, not by silent drift. It
        asserts the PREMISE of CORRECTION-3, so the remediation cannot outlive
        its own justification unnoticed.
        """
        from autom8y_auth.claims import ServiceClaims

        wildcard = ServiceClaims(sub="s", iss="i", exp=0, iat=0, scope="*", permissions=[])
        assert wildcard.has_scope("asana:write") is True, (
            "Upstream wildcard fail-open is gone — revisit the CORRECTION-3 axis ruling"
        )

    def test_the_wildcard_carrier_is_not_hypothetical(self) -> None:
        """The SDK itself MINTS a `scope="*"` token — this is a live carrier.

        `AuthClient._dev_bypass_service_claims` (client.py:554-570) returns
        `ServiceClaims(sub="dev-bypass-service", scope="*", ...)` whenever
        `dev_mode` is set. So the fail-open carrier is not a legacy curiosity
        that may never appear: it is issued by the auth SDK under an env toggle.

        Had RE-2 keyed enforcement on `has_scope` — option (a) as originally
        posed — every dev-mode token would have satisfied every write gate.
        This test makes that concrete rather than leaving it as an argument.
        """
        from autom8y_auth.claims import ServiceClaims

        dev = ServiceClaims(sub="dev-bypass-service", iss="i", exp=0, iat=0, scope="*")
        assert dev.has_scope("asana:write") is True  # the fail-open, demonstrated
        assert is_authorized(dev.sub, load_writer_allowlist(WriteClass.TASKS)) is False

    def test_wildcard_scope_token_is_denied_by_the_gate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RED: the exact carrier that defeats `has_scope` gets no write access."""
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "authorized-svc")
        claims = _claims(sub="attacker-svc", scope="*", permissions=[])
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(claims))
        resp = TestClient(app).post("/w")
        assert resp.status_code == 403
        assert _error_code(resp) == "INSUFFICIENT_PRIVILEGE"
        assert calls == []

    def test_authorized_principal_with_wildcard_scope_still_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GREEN pair: the denial above is about the ALLOWLIST, not about `scope`.

        Without this, the RED above would be consistent with a gate that simply
        rejects any token carrying `scope="*"` — a different (and wrong) control.
        The gate must be indifferent to `scope` entirely.
        """
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "authorized-svc")
        claims = _claims(sub="authorized-svc", scope="*", permissions=[])
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(claims))
        resp = TestClient(app).post("/w")
        assert resp.status_code == 200
        assert calls == ["entered"]

    def test_has_permission_no_wildcard_refuses_star(self) -> None:
        assert has_permission_no_wildcard(_claims(permissions=["*"]), "asana:write") is False
        assert has_permission_no_wildcard(_claims(permissions=["*"]), "*") is False

    def test_has_permission_no_wildcard_allows_exact_membership(self) -> None:
        """GREEN pair — otherwise the refusal above could be a constant False."""
        assert (
            has_permission_no_wildcard(_claims(permissions=["asana:write"]), "asana:write") is True
        )

    def test_has_permission_never_consults_scope(self) -> None:
        """The permissions axis must not read `scope` at all."""
        claims = _claims(scope="*", permissions=[])
        assert has_permission_no_wildcard(claims, "asana:write") is False


# ---------------------------------------------------------------------------
# The gate, end to end, both polarities
# ---------------------------------------------------------------------------


class TestGateTwoSided:
    def test_deny_red_unauthorized_caller_gets_403_and_handler_never_runs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "authorized-svc")
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(_claims(sub="other-svc")))
        resp = TestClient(app).post("/w")
        assert resp.status_code == 403
        assert _error_code(resp) == "INSUFFICIENT_PRIVILEGE"
        assert calls == [], "handler ran despite denial — no Asana write may be reachable"

    def test_allow_green_authorized_caller_reaches_handler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "authorized-svc")
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(_claims(sub="authorized-svc")))
        resp = TestClient(app).post("/w")
        assert resp.status_code == 200
        assert calls == ["entered"]

    def test_malformed_config_red_unset_allowlist_denies_everyone(self) -> None:
        """Malformed/absent config must deny, not open."""
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(_claims(sub="anyone")))
        resp = TestClient(app).post("/w")
        assert resp.status_code == 403
        assert calls == []

    @pytest.mark.parametrize("raw", ["", "   ", ",,,"])
    def test_malformed_config_red_garbage_allowlist_denies_everyone(
        self, monkeypatch: pytest.MonkeyPatch, raw: str
    ) -> None:
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], raw)
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(_claims(sub="anyone")))
        assert TestClient(app).post("/w").status_code == 403
        assert calls == []

    def test_malformed_mode_red_does_not_become_observe(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A typo'd mode must not silently disable the control."""
        monkeypatch.setenv(MODE_ENV, "observ")  # one character short of a bypass
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "authorized-svc")
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(_claims(sub="other-svc")))
        assert TestClient(app).post("/w").status_code == 403
        assert calls == []

    def test_observe_mode_allows_but_only_on_the_exact_literal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GREEN pair for the malformed-mode RED above.

        Proves OBSERVE is genuinely reachable, so the previous test discriminates
        'typo' from 'bypass' rather than asserting a gate that never observes.
        """
        monkeypatch.setenv(MODE_ENV, "observe")
        app, calls = _build_app(WriteClass.TASKS, _jwt_ctx(_claims(sub="other-svc")))
        assert TestClient(app).post("/w").status_code == 200
        assert calls == ["entered"]

    def test_pat_branch_is_not_gated(self) -> None:
        """DEV-3's highest-regression-risk case (design §5.1 L1-3).

        PAT callers present their own Asana credential and are authorized by
        Asana's own ACL. Gating them would break every human caller for no
        security gain. Deny-by-default must NOT reach this branch — note the
        allowlist is unset here, so an over-broad gate would 403.
        """
        ctx = AuthContext(mode=AuthMode.PAT, asana_pat="user-pat-placeholder")
        app, calls = _build_app(WriteClass.TASKS, ctx)
        assert TestClient(app).post("/w").status_code == 200
        assert calls == ["entered"]

    def test_write_classes_are_independently_authorized(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Authorization for tasks must not confer receipts."""
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "svc-a")
        claims = _claims(sub="svc-a")
        tasks_app, _ = _build_app(WriteClass.TASKS, _jwt_ctx(claims))
        receipts_app, _ = _build_app(WriteClass.RECEIPTS, _jwt_ctx(claims))
        assert TestClient(tasks_app).post("/w").status_code == 200
        assert TestClient(receipts_app).post("/w").status_code == 403

    def test_tier1_principal_is_the_one_authorized(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The canonical `service_account_id` is what must be allowlisted."""
        monkeypatch.setenv(ALLOWLIST_ENV[WriteClass.TASKS], "canonical-sa")
        claims = _claims(sub="uuid", client_id="cid")
        app, calls = _build_app(
            WriteClass.TASKS,
            _jwt_ctx(claims),
            claims_dict={"service_account_id": "canonical-sa"},
        )
        assert TestClient(app).post("/w").status_code == 200
        assert calls == ["entered"]
