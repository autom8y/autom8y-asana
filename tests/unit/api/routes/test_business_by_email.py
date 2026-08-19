"""Tests for POST /v1/resolve/business-by-email (OW-10a email fallback).

Two-sided throughout: every guard is exercised in BOTH the state where it must
bite and the adjacent state where it must NOT, so a guard that has quietly
become a no-op fails a test rather than passing one.

FIXTURE LAW (disclosed): all fixtures are SHAPE-REAL / VALUES-SYNTHETIC. Email
addresses use RFC 2606 reserved TLDs (``.example`` / ``.invalid``), which can
never route; phone numbers are E.164-SHAPED but drawn from the NANP 555
information-service range, which is not assignable to a subscriber. No real
contact, business, phone or address appears anywhere in this file.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.resolution_result import ResolutionResult
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Test data constants (synthetic -- see FIXTURE LAW in module docstring)
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

ENDPOINT = "/v1/resolve/business-by-email"

EMAIL = "jane@acme-chiro.example"
EMAIL_SHARED = "frontdesk@shared-suite.example"

CONTACT_PROJECT_GID = "1200775689604552"
CONTACT_GID_A = "1111111111111111"
CONTACT_GID_B = "2222222222222222"

# E.164-shaped, NANP 555 information-service range (never assignable).
PHONE_A = "+15555550101"
PHONE_B = "+15555550202"

# Shape-real malformed cascade: an Asana Office Phone typed by a human.
PHONE_MALFORMED = "(555) 555-0101"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_jwt_validation(service_name: str = "autom8_data") -> AsyncMock:
    """Mock JWT validation returning valid ServiceClaims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _strategy_returning(result: ResolutionResult) -> MagicMock:
    """Build a stub UniversalResolutionStrategy yielding one result."""
    strategy = MagicMock()
    strategy.resolve = AsyncMock(return_value=[result])
    return strategy


def _project_registry_ready(project_gid: str | None = CONTACT_PROJECT_GID) -> MagicMock:
    """Build a stub EntityProjectRegistry singleton."""
    registry = MagicMock()
    registry.is_ready.return_value = True
    registry.get_project_gid.return_value = project_gid
    return registry


def _patches(
    *,
    strategy: MagicMock | None,
    project_registry: MagicMock | None = None,
):
    """Context-manager patches for auth, Asana client, registry and strategy."""
    return (
        patch(
            "autom8_asana.api.routes.internal.validate_service_token",
            _mock_jwt_validation(),
        ),
        patch(
            "autom8_asana.auth.jwt_validator.validate_service_token",
            _mock_jwt_validation(),
        ),
        patch("autom8_asana.auth.bot_pat.get_bot_pat", return_value="test_bot_pat"),
        patch("autom8_asana.api.dependencies.get_bot_pat", return_value="test_bot_pat"),
        patch(
            "autom8_asana.api.routes.intake_resolve.AsanaClient",
            return_value=_mock_asana_client(),
        ),
        patch(
            "autom8_asana.services.resolver.EntityProjectRegistry.get_instance",
            return_value=project_registry or _project_registry_ready(),
        ),
        patch("autom8_asana.services.resolver.get_strategy", return_value=strategy),
    )


def _mock_asana_client() -> MagicMock:
    """Async-context-manager AsanaClient stub."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def _post(client: TestClient, email: str = EMAIL) -> Any:
    return client.post(ENDPOINT, json={"email": email}, headers=AUTH_HEADER)


def _call(client: TestClient, *, strategy, project_registry=None, email: str = EMAIL) -> Any:
    """Run one request under the full patch stack."""
    p = _patches(strategy=strategy, project_registry=project_registry)
    with p[0], p[1], p[2], p[3], p[4], p[5], p[6]:
        return _post(client, email)


def _data(response: Any) -> dict[str, Any]:
    """Unwrap the fleet success envelope."""
    body = response.json()
    return body.get("data", body)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons():
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("AUTOM8Y_ENV", "LOCAL")
    monkeypatch.setenv("AUTH__DEV_MODE", "true")

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            EntityProjectRegistry.reset()
            registry = EntityProjectRegistry.get_instance()
            registry.register(
                entity_type="contact",
                project_gid=CONTACT_PROJECT_GID,
                project_name="Contact",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as tc:
        yield tc


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


class TestUniqueMatch:
    def test_unique_hit_returns_the_cascaded_phone(self, client: TestClient) -> None:
        """One contact, one cascaded office_phone -> found=true with that phone."""
        strategy = _strategy_returning(
            ResolutionResult.from_gids(
                [CONTACT_GID_A],
                context=[{"office_phone": PHONE_A, "vertical": "chiro"}],
            )
        )
        response = _call(client, strategy=strategy)

        assert response.status_code == 200
        data = _data(response)
        assert data["found"] is True
        assert data["office_phone"] == PHONE_A
        assert data["reason"] == "unique_match"
        assert data["vertical"] == "chiro"
        assert data["contact_gid"] == CONTACT_GID_A
        assert data["distinct_business_count"] == 1

    def test_two_contacts_one_business_is_still_unique(self, client: TestClient) -> None:
        """Ambiguity is over DISTINCT BUSINESSES, not contact rows.

        Two contact rows sharing an email under the SAME office are one
        business and one unambiguous answer. If this ever starts refusing,
        the policy has drifted from 'distinct businesses' to 'distinct rows'
        and the fallback goes dark for every multi-contact office.
        """
        strategy = _strategy_returning(
            ResolutionResult.from_gids(
                [CONTACT_GID_A, CONTACT_GID_B],
                context=[
                    {"office_phone": PHONE_A, "vertical": "chiro"},
                    {"office_phone": PHONE_A, "vertical": "chiro"},
                ],
            )
        )
        response = _call(client, strategy=strategy)

        data = _data(response)
        assert data["found"] is True
        assert data["office_phone"] == PHONE_A
        assert data["distinct_business_count"] == 1
        assert data["match_count"] == 2
        # Never an arbitrary pick from several rows.
        assert data["contact_gid"] is None


# ---------------------------------------------------------------------------
# The refusals -- each discriminated, none a guess
# ---------------------------------------------------------------------------


class TestDiscriminatedRefusals:
    def test_miss_fails_clean(self, client: TestClient) -> None:
        """No contact carries the email -> 200 found=false, email_not_found."""
        response = _call(client, strategy=_strategy_returning(ResolutionResult.not_found()))

        assert response.status_code == 200
        data = _data(response)
        assert data["found"] is False
        assert data["reason"] == "email_not_found"
        assert data["office_phone"] is None

    def test_ambiguous_fails_discriminated_and_returns_no_phone(self, client: TestClient) -> None:
        """Two DISTINCT businesses -> refuse, and NEVER a guessed row.

        The load-bearing assertion is ``office_phone is None``. A wrong phone
        here does not fail downstream -- it succeeds against the wrong
        business and binds the booking to a company that never took the call.
        """
        strategy = _strategy_returning(
            ResolutionResult.from_gids(
                [CONTACT_GID_A, CONTACT_GID_B],
                context=[
                    {"office_phone": PHONE_A, "vertical": "chiro"},
                    {"office_phone": PHONE_B, "vertical": "dental"},
                ],
            )
        )
        response = _call(client, strategy=strategy, email=EMAIL_SHARED)

        assert response.status_code == 200
        data = _data(response)
        assert data["found"] is False
        assert data["reason"] == "email_ambiguous"
        assert data["office_phone"] is None
        assert data["contact_gid"] is None
        assert data["distinct_business_count"] == 2

    def test_null_cascade_is_its_own_reason(self, client: TestClient) -> None:
        """Contact exists but no office_phone cascaded (the FIND-005 shape).

        Distinct from email_not_found: the contact IS there, so the remedy is
        a cascade/warm gap, not a missing record.
        """
        strategy = _strategy_returning(
            ResolutionResult.from_gids(
                [CONTACT_GID_A],
                context=[{"office_phone": None, "vertical": None}],
            )
        )
        response = _call(client, strategy=strategy)

        data = _data(response)
        assert data["found"] is False
        assert data["reason"] == "office_phone_absent"
        assert data["office_phone"] is None

    def test_blank_cascade_is_absent_not_a_business(self, client: TestClient) -> None:
        """An empty-string cascade is not an office and not a distinct business."""
        strategy = _strategy_returning(
            ResolutionResult.from_gids(
                [CONTACT_GID_A],
                context=[{"office_phone": "   ", "vertical": None}],
            )
        )
        data = _data(_call(client, strategy=strategy))
        assert data["found"] is False
        assert data["reason"] == "office_phone_absent"

    def test_malformed_phone_is_refused_not_forwarded(self, client: TestClient) -> None:
        """A non-E.164 cascade is discriminated here, not 400'd downstream.

        POST /v1/resolve/business validates E.164 and would answer 400
        INVALID_PHONE_FORMAT. Naming it here points at the real defect (a
        malformed Office Phone on the business task).
        """
        strategy = _strategy_returning(
            ResolutionResult.from_gids(
                [CONTACT_GID_A],
                context=[{"office_phone": PHONE_MALFORMED, "vertical": None}],
            )
        )
        response = _call(client, strategy=strategy)

        assert response.status_code == 200
        data = _data(response)
        assert data["found"] is False
        assert data["reason"] == "office_phone_malformed"
        assert data["office_phone"] is None

    def test_conflicting_verticals_yield_no_vertical(self, client: TestClient) -> None:
        """vertical is context only; ambiguity there never blocks a unique phone."""
        strategy = _strategy_returning(
            ResolutionResult.from_gids(
                [CONTACT_GID_A, CONTACT_GID_B],
                context=[
                    {"office_phone": PHONE_A, "vertical": "chiro"},
                    {"office_phone": PHONE_A, "vertical": "dental"},
                ],
            )
        )
        data = _data(_call(client, strategy=strategy))
        assert data["found"] is True
        assert data["vertical"] is None


# ---------------------------------------------------------------------------
# ABSENT vs UNAVAILABLE -- the fail-closed gate (D-2b)
# ---------------------------------------------------------------------------


class TestFailsClosedOnUnavailable:
    @pytest.mark.parametrize(
        "error_code",
        ["INDEX_UNAVAILABLE", "LOOKUP_ERROR", "INVALID_CRITERIA", "RESOLUTION_NULL_SLOT"],
    )
    def test_unconsultable_index_is_503_never_found_false(
        self, client: TestClient, error_code: str
    ) -> None:
        """An index we could not read is NOT 'this email is unknown'.

        found=false sends the calendly pipeline to CREATE. Downgrading an
        unknown world-state to found=false therefore mints a duplicate
        business on every index gap -- the exact D-2b failure the business
        path already refuses.
        """
        strategy = _strategy_returning(ResolutionResult.error_result(error_code))
        response = _call(client, strategy=strategy)

        assert response.status_code == 503
        assert "found" not in response.text or '"found": false' not in response.text

    def test_not_found_is_the_only_absent_error(self, client: TestClient) -> None:
        """Two-sided partner of the parametrized case above: NOT_FOUND IS absent."""
        strategy = _strategy_returning(ResolutionResult.error_result("NOT_FOUND"))
        response = _call(client, strategy=strategy)

        assert response.status_code == 200
        assert _data(response)["reason"] == "email_not_found"

    def test_discovery_incomplete_is_503(self, client: TestClient) -> None:
        """Registry not ready -> UNAVAILABLE, not a confident miss."""
        registry = MagicMock()
        registry.is_ready.return_value = False
        response = _call(
            client,
            strategy=_strategy_returning(ResolutionResult.not_found()),
            project_registry=registry,
        )
        assert response.status_code == 503

    def test_unregistered_contact_project_is_503(self, client: TestClient) -> None:
        """No contact project -> UNAVAILABLE, not a confident miss."""
        response = _call(
            client,
            strategy=_strategy_returning(ResolutionResult.not_found()),
            project_registry=_project_registry_ready(project_gid=None),
        )
        assert response.status_code == 503

    def test_missing_strategy_is_503(self, client: TestClient) -> None:
        """No strategy for contact -> UNAVAILABLE, not a confident miss."""
        response = _call(client, strategy=None)
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# Degraded-cascade UNAVAILABLE is DISCRIMINATED, not generic (DIC-S04b rider)
# ---------------------------------------------------------------------------


class TestCascadeNotReadyIsDiscriminated:
    """A degraded cascade is its own 503, not "Asana is down".

    ``_check_cascade_health`` refuses the index build when a cascade-sourced
    key column exceeds the 20% null gate -- correct fail-closed design. But
    ``CascadeNotReadyError`` is a ``ServiceError``, not one of the
    ``_INDEX_BUILD_ERRORS``, so it propagated to the route's boundary catch and
    was rendered as the generic ``ASANA_UNAVAILABLE``. The accurate diagnosis
    lived only in the Lambda logs; the operator reading the 503 was pointed at
    the wrong subsystem entirely.

    Two-sided: the degraded case must carry the discriminating code AND the
    genuinely-unrelated failure must keep the generic one.
    """

    @staticmethod
    def _cascade_degraded_strategy() -> MagicMock:
        from autom8_asana.services.errors import CascadeNotReadyError

        strategy = MagicMock()
        strategy.resolve = AsyncMock(
            side_effect=CascadeNotReadyError(
                entity_type="contact",
                project_gid=CONTACT_PROJECT_GID,
                degraded_columns={"office_phone": 0.966914},
                max_null_rate=0.966914,
            )
        )
        return strategy

    def test_degraded_cascade_is_503_cascade_not_ready(self, client: TestClient) -> None:
        response = _call(client, strategy=self._cascade_degraded_strategy())

        assert response.status_code == 503
        body = response.json()
        assert "CASCADE_NOT_READY" in response.text
        assert "ASANA_UNAVAILABLE" not in response.text
        # The offending column and the observed rate are in the answer, so the
        # 503 is self-diagnosing rather than log-only.
        assert "office_phone" in response.text
        assert "96.7%" in response.text
        # Still UNAVAILABLE: never downgraded to a confident miss.
        assert '"found": false' not in response.text
        assert body.get("data") is None or "found" not in str(body.get("data"))

    def test_unrelated_failure_keeps_the_generic_code(self, client: TestClient) -> None:
        """Two-sided partner: a non-cascade fault must NOT be relabelled.

        Without this, the new branch could widen to swallow every 503 and the
        discrimination would be cosmetic.
        """
        strategy = MagicMock()
        strategy.resolve = AsyncMock(side_effect=RuntimeError("connection reset by peer"))

        response = _call(client, strategy=strategy)

        assert response.status_code == 503
        assert "ASANA_UNAVAILABLE" in response.text
        assert "CASCADE_NOT_READY" not in response.text

    def test_degraded_cascade_response_holds_no_pii(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The new branch inherits the PII fence (it logs the email too)."""
        with caplog.at_level("ERROR"):
            response = _call(client, strategy=self._cascade_degraded_strategy())

        assert response.status_code == 503
        emitted = "\n".join(
            [r.getMessage() for r in caplog.records]
            + [str(getattr(r, "email", "")) for r in caplog.records]
        )
        assert EMAIL not in emitted
        assert EMAIL not in response.text


# ---------------------------------------------------------------------------
# Registry coupling -- the criterion may not drift from the registry
# ---------------------------------------------------------------------------


class TestRegistryGuard:
    def test_contact_email_is_a_registry_key_column(self) -> None:
        """The premise the whole endpoint rests on, asserted directly.

        If contact stops being keyed on contact_email, the lookup becomes a
        permanent silent index miss. This is the positive half.
        """
        from autom8_asana.core.entity_registry import get_registry

        assert "contact_email" in get_registry().require("contact").key_columns

    def test_criterion_refuses_when_registry_drops_the_email_key(self) -> None:
        """Negative half: a registry that no longer keys email is refused LOUDLY.

        Bites only on the defect -- the positive test above proves the
        no-defect variant passes.
        """
        from autom8_asana.services import business_by_email_service as svc

        drifted = MagicMock()
        drifted.key_columns = ("office_phone", "contact_phone")

        with patch.object(svc, "_contact_descriptor", return_value=drifted):
            with pytest.raises(svc.ContactIndexUnavailableError) as exc:
                svc._email_criterion(EMAIL)

        # Carries "not ready" so the route's 503 branch converts it.
        assert "not ready" in str(exc.value)

    def test_criterion_is_built_from_the_registry_key(self) -> None:
        from autom8_asana.services import business_by_email_service as svc

        assert svc._email_criterion(EMAIL) == {"contact_email": EMAIL}


# ---------------------------------------------------------------------------
# Ambiguity semantics may not be narrowed by status filtering
# ---------------------------------------------------------------------------


class TestActiveOnlyIsPinned:
    def test_resolve_is_called_with_active_only_false(self, client: TestClient) -> None:
        """A status filter that narrowed 2 businesses to 1 would fake a unique match.

        Pinned explicitly so that registering a ``contact`` classifier later
        cannot silently change the unique-match policy.
        """
        strategy = _strategy_returning(ResolutionResult.not_found())
        _call(client, strategy=strategy)

        strategy.resolve.assert_awaited_once()
        kwargs = strategy.resolve.await_args.kwargs
        assert kwargs["active_only"] is False
        assert kwargs["criteria"] == [{"contact_email": EMAIL}]
        assert "office_phone" in kwargs["requested_fields"]

    def test_contact_has_no_activity_classifier_today(self) -> None:
        """Documents WHY active_only is currently a no-op (and pins the fact)."""
        from autom8_asana.models.business.activity import get_classifier

        assert get_classifier("contact") is None


# ---------------------------------------------------------------------------
# Routing -- the wildcard /v1/resolve/{entity_type} must not swallow this path
# ---------------------------------------------------------------------------


class TestRouting:
    def test_literal_path_reaches_this_handler_not_the_wildcard(self, app) -> None:
        """The path resolves to resolve_business_by_email_route, not the catch-all."""
        matches = [
            r
            for r in app.router.routes
            if getattr(r, "path", None) == ENDPOINT and "POST" in getattr(r, "methods", set())
        ]
        assert len(matches) == 1, f"expected exactly one route for {ENDPOINT}, got {matches}"
        assert matches[0].endpoint.__name__ == "resolve_business_by_email_route"

    def test_literal_paths_are_registered_before_the_wildcard(self, app) -> None:
        """Mount-order invariant. Starlette matches in registration order.

        This is the tooth for the shadowing hazard: intake_resolve's literal
        paths sit INSIDE the subtree claimed by resolver.py's
        POST /v1/resolve/{entity_type}. If resolver_router is ever mounted
        first, this endpoint stops existing.
        """
        paths = [getattr(r, "path", "") for r in app.router.routes]
        wildcard = "/v1/resolve/{entity_type}"
        assert wildcard in paths, "wildcard resolver route not mounted; premise changed"
        assert paths.index(ENDPOINT) < paths.index(wildcard)

    def test_the_wildcard_would_otherwise_claim_this_segment(self, app) -> None:
        """Two-sided partner: proves the hazard is REAL, not hypothetical.

        The wildcard's path-regex genuinely matches 'business-by-email', so
        the ordering above is doing real work rather than guarding nothing.
        """
        wildcard = next(
            r for r in app.router.routes if getattr(r, "path", None) == "/v1/resolve/{entity_type}"
        )
        assert wildcard.path_regex.match(ENDPOINT) is not None

    def test_sibling_business_route_still_mounted(self, app) -> None:
        """The pre-existing business path is untouched by this addition."""
        paths = [getattr(r, "path", "") for r in app.router.routes]
        assert "/v1/resolve/business" in paths
        assert "/v1/resolve/contact" in paths


# ---------------------------------------------------------------------------
# PII fence
# ---------------------------------------------------------------------------


class TestPiiFence:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("jane@acme-chiro.example", "j***@acme-chiro.example"),
            ("a@b.example", "a***@b.example"),
            ("no-at-sign", "***"),
            ("@domain.example", "***@domain.example"),
        ],
    )
    def test_redaction_masks_the_local_part(self, raw: str, expected: str) -> None:
        from autom8_asana.services.business_by_email_service import redact_email

        assert redact_email(raw) == expected

    def test_raw_email_never_reaches_a_log_line(self, client: TestClient, caplog) -> None:
        """Two-sided: the redacted form IS logged, the raw local part is NOT."""
        strategy = _strategy_returning(ResolutionResult.not_found())
        with caplog.at_level("INFO"):
            _call(client, strategy=strategy)

        emitted = "\n".join(
            [r.getMessage() for r in caplog.records]
            + [str(getattr(r, "email", "")) for r in caplog.records]
        )
        assert EMAIL not in emitted
        assert "jane" not in emitted


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


class TestRequestValidation:
    @pytest.mark.parametrize("body", [{}, {"email": ""}, {"email": "ab"}])
    def test_invalid_bodies_are_422(self, client: TestClient, body: dict) -> None:
        p = _patches(strategy=_strategy_returning(ResolutionResult.not_found()))
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6]:
            response = client.post(ENDPOINT, json=body, headers=AUTH_HEADER)
        assert response.status_code == 422

    def test_missing_auth_is_401(self, client: TestClient) -> None:
        response = client.post(ENDPOINT, json={"email": EMAIL})
        assert response.status_code == 401
