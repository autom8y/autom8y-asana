"""Two-sided teeth for the GOVERNED WRITE PATH client (WS-A PR-3).

Contract (TDD §3.4 / §4 / §5): every enrollment write crosses exactly one seam --
``PATCH /api/v1/businesses/{phone}/config`` on autom8y-scheduling, carrying a
service token. The client's job is to turn every response into a BOUNDED, TYPED
outcome so the caller counts rather than interprets, and so no expected condition
(a 404, a prereq refusal, a guard denial) arrives as a stack trace.

The sharpest legs here:
  * a failed read yields ``scheduling_enabled = None``, NEVER ``False`` -- confusing
    "unknown" with "disabled" is how a bridge mass-enables;
  * ``PREREQ_REFUSED`` is terminal and is NOT in the error budget;
  * ``401/403`` is classified, not raised -- it is the observable side of the guard.
"""

from __future__ import annotations

from typing import Any

import pytest

from autom8_asana.enrollment.scheduling_client import (
    BUSINESSES_PREFIX,
    NON_ERROR_OUTCOMES,
    Outcome,
    SchedulingConfigClient,
)

AUTHORIZED_TOKEN = "jwt-asana-enrollment-bridge"
PHONE = "+15550001111"


class _Response:
    """Minimal httpx-shaped response."""

    def __init__(self, status_code: int, body: Any = None, *, raises: bool = False) -> None:
        self.status_code = status_code
        self._body = body
        self._raises = raises

    def json(self) -> Any:
        if self._raises:
            raise ValueError("not json")
        return self._body


class _FakeSchedulingApi:
    """A fake governed write path.

    Enforces the SAME auth shape the real service does (service token required),
    so the "authorized token path" leg is a real assertion rather than a stub that
    accepts anything.
    """

    def __init__(
        self,
        *,
        authorized_token: str | None = AUTHORIZED_TOKEN,
        state: dict[str, bool] | None = None,
    ) -> None:
        self.authorized_token = authorized_token
        self.state: dict[str, bool] = dict(state or {})
        self.get_calls: list[str] = []
        self.patch_calls: list[tuple[str, dict[str, Any]]] = []
        self.prereq_refuse: set[str] = set()
        self.unknown_business: set[str] = set()
        self.not_configured: set[str] = set()

    def _denied(self, headers: dict[str, str] | None) -> _Response | None:
        token = (headers or {}).get("Authorization", "").removeprefix("Bearer ")
        if self.authorized_token is None or token != self.authorized_token:
            return _Response(403, {"error": {"code": "AUTH_FORBIDDEN"}})
        return None

    def _phone(self, url: str) -> str:
        return url.removeprefix(f"{BUSINESSES_PREFIX}/").removesuffix("/config")

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> _Response:
        denial = self._denied(headers)
        if denial is not None:
            return denial
        phone = self._phone(url)
        self.get_calls.append(phone)
        if phone in self.unknown_business:
            return _Response(404, {"error": {"code": "BUSINESS_NOT_FOUND"}})
        if phone in self.not_configured:
            return _Response(404, {"error": {"code": "SCHEDULING_NOT_CONFIGURED"}})
        if phone not in self.state:
            return _Response(404, {"error": {"code": "BUSINESS_NOT_FOUND"}})
        return _Response(
            200,
            {
                "data": {
                    "office_phone": phone,
                    "scheduling_enabled": self.state[phone],
                    "offer_id": 4242,
                    "offer_guid": "offer-guid",
                }
            },
        )

    def patch(
        self, url: str, *, json: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> _Response:
        denial = self._denied(headers)
        if denial is not None:
            return denial
        phone = self._phone(url)
        payload = json or {}
        self.patch_calls.append((phone, payload))
        if payload.get("office_phone") != phone:
            return _Response(400, {"error": {"code": "OFFICE_PHONE_MISMATCH"}})
        desired = bool(payload.get("scheduling_enabled"))
        # The real gate is enable-only: a disable is never prereq-gated.
        if desired and phone in self.prereq_refuse and not self.state.get(phone, False):
            return _Response(
                400,
                {
                    "error": {
                        "code": "SCHEDULING_ENABLE_REFUSED",
                        "details": {
                            "reasons": ["timezone_not_configured", "business_hours_not_configured"]
                        },
                    }
                },
            )
        self.state[phone] = desired
        return _Response(200, {"data": {"office_phone": phone, "updated": True}})


def _client(api: _FakeSchedulingApi, token: str = AUTHORIZED_TOKEN) -> SchedulingConfigClient:
    return SchedulingConfigClient(api, lambda: token)


class TestAuthorizedPath:
    def test_GREEN_authorized_token_reads_and_writes(self) -> None:
        api = _FakeSchedulingApi(state={PHONE: False})
        client = _client(api)

        read = client.get_config(PHONE)
        assert read.outcome is Outcome.READ_OK
        assert read.scheduling_enabled is False
        assert read.offer_id == 4242

        write = client.set_scheduling_enabled(
            PHONE, scheduling_enabled=True, intent_source="coerced_unset"
        )
        assert write.outcome is Outcome.APPLIED
        assert api.state[PHONE] is True

    def test_RED_wrong_token_is_classified_write_denied_not_raised(self) -> None:
        """The guard biting is DATA, not an exception -- it must be countable."""
        api = _FakeSchedulingApi(state={PHONE: False})
        client = _client(api, token="jwt-some-other-service")

        assert client.get_config(PHONE).outcome is Outcome.WRITE_DENIED
        write = client.set_scheduling_enabled(
            PHONE, scheduling_enabled=True, intent_source="explicit_enabled"
        )
        assert write.outcome is Outcome.WRITE_DENIED
        assert api.state[PHONE] is False, "a denied write must not have moved state"

    def test_token_is_fetched_per_request_never_cached_in_the_client(self) -> None:
        """TokenManager owns refresh; this client must not pin a stale credential."""
        api = _FakeSchedulingApi(state={PHONE: False})
        issued: list[str] = []

        def _provider() -> str:
            issued.append(AUTHORIZED_TOKEN)
            return AUTHORIZED_TOKEN

        client = SchedulingConfigClient(api, _provider)
        client.get_config(PHONE)
        client.set_scheduling_enabled(PHONE, scheduling_enabled=True, intent_source="x")
        assert len(issued) == 2


class TestReadFailureIsUnknownNotDisabled:
    """★ The single most dangerous confusion in this design."""

    @pytest.mark.parametrize(
        ("status", "body", "expected"),
        [
            (404, {"error": {"code": "BUSINESS_NOT_FOUND"}}, Outcome.UNRESOLVED),
            (404, {"error": {"code": "SCHEDULING_NOT_CONFIGURED"}}, Outcome.NOT_CONFIGURED),
            (403, {"error": {"code": "AUTH_FORBIDDEN"}}, Outcome.WRITE_DENIED),
            (422, None, Outcome.INVALID_PHONE),
            (500, None, Outcome.READ_FAILED),
        ],
    )
    def test_every_failed_read_yields_none_never_false(
        self, status: int, body: Any, expected: Outcome
    ) -> None:
        class _Api:
            def get(self, url: str, *, headers: Any = None) -> _Response:
                return _Response(status, body)

        read = SchedulingConfigClient(_Api(), lambda: "t").get_config(PHONE)
        assert read.outcome is expected
        assert read.scheduling_enabled is None, (
            "a failed read must be UNKNOWN, never False -- defaulting to False makes "
            "every unreadable office look like a pending enable"
        )

    def test_transport_failure_is_classified_not_propagated(self) -> None:
        class _Api:
            def get(self, url: str, *, headers: Any = None) -> _Response:
                raise TimeoutError("connect timeout")

        read = SchedulingConfigClient(_Api(), lambda: "t").get_config(PHONE)
        assert read.outcome is Outcome.READ_FAILED
        assert read.scheduling_enabled is None

    def test_200_with_a_missing_enabled_field_is_a_read_failure_not_a_false(self) -> None:
        """A malformed 200 must not silently become 'disabled'."""

        class _Api:
            def get(self, url: str, *, headers: Any = None) -> _Response:
                return _Response(200, {"data": {"office_phone": PHONE}})

        read = SchedulingConfigClient(_Api(), lambda: "t").get_config(PHONE)
        assert read.outcome is Outcome.READ_FAILED
        assert read.scheduling_enabled is None

    def test_non_json_body_does_not_raise(self) -> None:
        class _Api:
            def get(self, url: str, *, headers: Any = None) -> _Response:
                return _Response(502, raises=True)

        assert (
            SchedulingConfigClient(_Api(), lambda: "t").get_config(PHONE).outcome
            is Outcome.READ_FAILED
        )


class TestPrereqRefusalIsTerminalAndNotAnError:
    def test_RED_prereq_refusal_carries_reasons_and_does_not_flip(self) -> None:
        api = _FakeSchedulingApi(state={PHONE: False})
        api.prereq_refuse.add(PHONE)

        write = _client(api).set_scheduling_enabled(
            PHONE, scheduling_enabled=True, intent_source="coerced_unset"
        )

        assert write.outcome is Outcome.PREREQ_REFUSED
        assert write.reasons == ("timezone_not_configured", "business_hours_not_configured")
        assert api.state[PHONE] is False, "never force-flipped"

    def test_GREEN_satisfied_prerequisites_flip(self) -> None:
        """Two-sided: the guard bites only on the defect."""
        api = _FakeSchedulingApi(state={PHONE: False})
        write = _client(api).set_scheduling_enabled(
            PHONE, scheduling_enabled=True, intent_source="explicit_enabled"
        )
        assert write.outcome is Outcome.APPLIED
        assert api.state[PHONE] is True

    def test_prereq_refusal_is_not_in_the_error_budget(self) -> None:
        """Conflating 'correctly refused' with 'broken' trains the operator to
        ignore the signal."""
        assert Outcome.PREREQ_REFUSED in NON_ERROR_OUTCOMES
        assert Outcome.UNRESOLVED in NON_ERROR_OUTCOMES
        assert Outcome.NOT_CONFIGURED in NON_ERROR_OUTCOMES
        assert Outcome.ERROR not in NON_ERROR_OUTCOMES
        assert Outcome.READ_FAILED not in NON_ERROR_OUTCOMES
        assert Outcome.WRITE_DENIED not in NON_ERROR_OUTCOMES

    def test_disable_is_never_prereq_gated(self) -> None:
        """Fail-closed means never OPENING on unproven ground, never blocking a close."""
        api = _FakeSchedulingApi(state={PHONE: True})
        api.prereq_refuse.add(PHONE)

        write = _client(api).set_scheduling_enabled(
            PHONE, scheduling_enabled=False, intent_source="explicit_disabled"
        )
        assert write.outcome is Outcome.APPLIED
        assert api.state[PHONE] is False


class TestPathBodyCoherenceAndProvenance:
    def test_phone_is_sent_in_both_path_and_body(self) -> None:
        """Closes the silent-ignore wart: the service 400s a mismatch, so a caller
        can never believe it wrote office X while office Y moved."""
        api = _FakeSchedulingApi(state={PHONE: False})
        _client(api).set_scheduling_enabled(
            PHONE, scheduling_enabled=True, intent_source="coerced_unset"
        )
        phone, payload = api.patch_calls[0]
        assert phone == PHONE
        assert payload["office_phone"] == PHONE

    def test_intent_source_is_carried_into_the_receipt(self) -> None:
        api = _FakeSchedulingApi(state={PHONE: False})
        _client(api).set_scheduling_enabled(
            PHONE, scheduling_enabled=True, intent_source="coerced_unset"
        )
        assert api.patch_calls[0][1]["intent_source"] == "coerced_unset"

    def test_office_phone_mismatch_is_classified_invalid_phone(self) -> None:
        class _Api:
            def patch(self, url: str, *, json: Any = None, headers: Any = None) -> _Response:
                return _Response(400, {"error": {"code": "OFFICE_PHONE_MISMATCH"}})

        write = SchedulingConfigClient(_Api(), lambda: "t").set_scheduling_enabled(
            PHONE, scheduling_enabled=True, intent_source="x"
        )
        assert write.outcome is Outcome.INVALID_PHONE

    def test_e164_validation_rejection_is_counted_never_canonicalized(self) -> None:
        """★ The gate's OfficePhoneField has an E.164 pattern. A non-E.164 frame
        phone 422s -- and the honest disposition is to COUNT it. Canonicalizing here
        would risk a false join, i.e. writing one office's enrollment onto another."""

        class _Api:
            def patch(self, url: str, *, json: Any = None, headers: Any = None) -> _Response:
                return _Response(422, {"detail": "string does not match regex"})

        write = SchedulingConfigClient(_Api(), lambda: "t").set_scheduling_enabled(
            "(555) 000-1111", scheduling_enabled=True, intent_source="x"
        )
        assert write.outcome is Outcome.INVALID_PHONE

    def test_url_targets_the_governed_route_only(self) -> None:
        seen: list[str] = []

        class _Api:
            def get(self, url: str, *, headers: Any = None) -> _Response:
                seen.append(url)
                return _Response(200, {"data": {"scheduling_enabled": True}})

        SchedulingConfigClient(_Api(), lambda: "t").get_config(PHONE)
        assert seen == [f"/api/v1/businesses/{PHONE}/config"]
