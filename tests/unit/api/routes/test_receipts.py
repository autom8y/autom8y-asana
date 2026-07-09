"""Two-sided discriminating tests for the EBI OI-2 receipts route.

POST /v1/receipts - thread a forwarding-lifecycle receipt onto a clinic's
Business task.

Every guard is proven RED-on-the-defect AND GREEN-without-it (G-THEATER
discipline). The load-bearing cases:

  - T-R2/T-R3/T-R5 (fail-closed resolution): an unknown/ambiguous/degraded
    company MUST fail-closed (404/409), NEVER post to a fallback task. T-R5 is
    the anti-fail-open teeth: a search-degradation (empty hits) returns 404, not
    200 -- proving we did NOT wire the cold-cache-fail-open SearchService.
  - T-I2/T-I3 (idempotency): a re-delivered receipt is skipped; a NEW-day nudge
    re-fires (the marker's per-kind bucket has teeth on both sides).
  - T-D1 (retry discipline): a POST-5xx is a 503 and is NOT blind-retried.

Fakes are injected at the AsanaClient seam (client.http / client.stories),
exactly as intake_route / link_on_play are unit-tested. No live Asana.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autom8_asana.api.config import get_settings
from autom8_asana.api.main import create_app
from autom8_asana.auth.bot_pat import clear_bot_pat_cache
from autom8_asana.auth.jwt_validator import reset_auth_client
from autom8_asana.services.resolver import EntityProjectRegistry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JWT_TOKEN = "header.payload.signature"
AUTH_HEADER = {"Authorization": f"Bearer {JWT_TOKEN}"}

COMPANY_ID = "office-guid-abc123"
BUSINESS_GID = "1200000000000001"
BUSINESSES_PROJECT_GID = "1200653012566782"  # BUSINESS_PROJECT (project_registry.py:21)
COMPANY_ID_FIELD_GID = "1199000000000042"  # a configured (test) "Company ID" field gid
NEW_STORY_GID = "1216000000000009"
EXISTING_STORY_GID = "1216000000000001"

RECEIPT_BODY = {
    "company_id": COMPANY_ID,
    "kind": "verified",
    "body": "Forwarding lifecycle: verified\nClinic: Sand Lake Dental\n"
    "Forwarding address domain: gmail.com",
}


# ---------------------------------------------------------------------------
# Fake AsanaClient
# ---------------------------------------------------------------------------


def _make_collect_mock(return_value: list[Any]) -> MagicMock:
    """Mock whose .collect() returns an AsyncMock with the given list.

    Matches the PageIterator idiom: service calls method(...).collect().
    """
    collector = MagicMock()
    collector.collect = AsyncMock(return_value=return_value)
    return collector


def _business_task(gid: str, in_businesses: bool = True) -> dict[str, Any]:
    """A tasks/search result row with (optional) Businesses-project membership."""
    projects = [{"gid": BUSINESSES_PROJECT_GID}] if in_businesses else [{"gid": "9999"}]
    return {"gid": gid, "name": "Business Task", "projects": projects}


def _make_story(gid: str, text: str) -> MagicMock:
    """A Story-like object with .gid and .text."""
    story = MagicMock()
    story.gid = gid
    story.text = text
    return story


def _make_mock_asana_client(
    *,
    search_results: list[dict[str, Any]] | None = None,
    search_raises: Exception | None = None,
    existing_stories: list[MagicMock] | None = None,
    create_raises: Exception | None = None,
    workspace_gid: str | None = "1140000000000001",
) -> MagicMock:
    """Build a fake AsanaClient exercising the resolve -> dedup -> post path.

    Args:
        search_results: rows returned by http.get for tasks/search (WRAPPED as
            the unwrapped list -- http.get strips the {"data": ...} envelope).
        search_raises: exception raised by http.get (e.g. an Asana 5xx).
        existing_stories: stories already on the resolved task (dedup input).
        create_raises: exception raised by create_comment_async (e.g. a POST-5xx).
        workspace_gid: default_workspace_gid on the client.
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.default_workspace_gid = workspace_gid

    # http.get -> tasks/search. http.get UNWRAPS the {"data": ...} envelope, so
    # a search returns the inner list directly (the service dual-handles both).
    if search_raises is not None:
        mock_client.http.get = AsyncMock(side_effect=search_raises)
    else:
        mock_client.http.get = AsyncMock(return_value=search_results or [])

    # stories.list_for_task_async(...).collect() -> list[Story]
    mock_client.stories.list_for_task_async = MagicMock(
        return_value=_make_collect_mock(existing_stories or []),
    )

    # stories.create_comment_async(*, task, text) -> Story
    if create_raises is not None:
        mock_client.stories.create_comment_async = AsyncMock(side_effect=create_raises)
    else:
        mock_client.stories.create_comment_async = AsyncMock(
            return_value=_make_story(NEW_STORY_GID, "posted"),
        )

    return mock_client


def _mock_jwt_validation(service_name: str = "email_booking_intake") -> AsyncMock:
    """Mock JWT validation returning valid ServiceClaims."""
    mock_claims = MagicMock()
    mock_claims.sub = f"service:{service_name}"
    mock_claims.service_name = service_name
    mock_claims.scope = "multi-tenant"
    return AsyncMock(return_value=mock_claims)


def _receipts_patches(mock_client: MagicMock | None = None):
    """Patches for JWT, bot PAT, and the AsanaClient the route constructs."""
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
        patch(
            "autom8_asana.api.dependencies.get_bot_pat",
            return_value="test_bot_pat",
        ),
        patch(
            "autom8_asana.api.routes.receipts.AsanaClient",
            return_value=mock_client or _make_mock_asana_client(),
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singletons(monkeypatch):
    """Reset singletons and configure the (test) Company ID field GID."""
    monkeypatch.setenv("ASANA_API_COMPANY_ID_FIELD_GID", COMPANY_ID_FIELD_GID)
    get_settings.cache_clear()
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()
    yield
    get_settings.cache_clear()
    clear_bot_pat_cache()
    reset_auth_client()
    EntityProjectRegistry.reset()


@pytest.fixture()
def app(monkeypatch):
    """Test application with a mocked lifespan (no live discovery)."""
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
                entity_type="business",
                project_gid=BUSINESSES_PROJECT_GID,
                project_name="Business",
            )
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry
        yield create_app()


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as tc:
        yield tc


def _post(client: TestClient, mock_client: MagicMock, body: dict[str, Any]):
    patches = _receipts_patches(mock_client)
    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        return client.post("/v1/receipts", json=body, headers=AUTH_HEADER)


# ---------------------------------------------------------------------------
# 7.1 Resolution (FORK-R) -- fail-closed teeth
# ---------------------------------------------------------------------------


class TestResolution:
    def test_r1_green_single_business_posts(self, client: TestClient) -> None:
        """T-R1 GREEN: exactly one Business match -> resolves + posts."""
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["business_gid"] == BUSINESS_GID
        assert data["story_gid"] == NEW_STORY_GID
        assert data["outcome"] == "posted"
        mock_client.stories.create_comment_async.assert_awaited_once()

    def test_r2_red_zero_matches_404_no_post(self, client: TestClient) -> None:
        """T-R2 RED: no Business carries the company_id -> 404, NO comment."""
        mock_client = _make_mock_asana_client(search_results=[])
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "COMPANY_NOT_RESOLVED"
        mock_client.stories.create_comment_async.assert_not_called()

    def test_r3_red_ambiguous_409_no_post(self, client: TestClient) -> None:
        """T-R3 RED: two Business matches -> 409, NO comment, both gids surfaced."""
        mock_client = _make_mock_asana_client(
            search_results=[
                _business_task("1200000000000001"),
                _business_task("1200000000000002"),
            ],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 409
        err = resp.json()["error"]
        assert err["code"] == "COMPANY_AMBIGUOUS"
        assert set(err["details"]["gids"]) == {
            "1200000000000001",
            "1200000000000002",
        }
        mock_client.stories.create_comment_async.assert_not_called()

    def test_r4_discriminator_excludes_non_business(self, client: TestClient) -> None:
        """T-R4: a non-Business task carrying the company_id is filtered out.

        The project discriminator keeps only Businesses-project members, so a
        single Business match resolves cleanly (not a false ambiguity).
        """
        mock_client = _make_mock_asana_client(
            search_results=[
                _business_task("1200000000000099", in_businesses=False),  # Offer/Process
                _business_task(BUSINESS_GID, in_businesses=True),  # the Business
            ],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        assert resp.json()["data"]["business_gid"] == BUSINESS_GID

    def test_r5_anti_fail_open_empty_search_is_404_not_200(self, client: TestClient) -> None:
        """T-R5 anti-fail-open TEETH: a degraded/empty search returns 404, NOT 200.

        This proves we do NOT treat a search-degradation (the cold-cache
        SearchService failure mode) as "post to some default" -- and that we did
        NOT wire the fail-open SearchService whose cold-cache empty would look
        identical but for the wrong reason. The RED here is the whole point: a
        silent-drop-as-200 would be the defect this route exists to prevent.
        """
        mock_client = _make_mock_asana_client(search_results=[])
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "COMPANY_NOT_RESOLVED"
        # The teeth: NOT a 200, and NOT a comment on any fallback task.
        assert resp.status_code != 200
        mock_client.stories.create_comment_async.assert_not_called()


# ---------------------------------------------------------------------------
# 7.2 Idempotency (D-5)
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_i1_green_post_when_no_marker(self, client: TestClient) -> None:
        """T-I1 GREEN: no matching marker -> create_comment once, outcome=posted."""
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
            existing_stories=[_make_story("s0", "some unrelated comment")],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.stories.create_comment_async.assert_awaited_once()

    def test_i2_red_dup_guard_skips(self, client: TestClient) -> None:
        """T-I2 RED dup-guard: an existing matching marker -> skip, no create."""
        marker = f"RCPT|{COMPANY_ID}|verified|"
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
            existing_stories=[_make_story(EXISTING_STORY_GID, f"{marker}\nold body")],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["outcome"] == "skipped_duplicate"
        assert data["story_gid"] == EXISTING_STORY_GID
        mock_client.stories.create_comment_async.assert_not_called()

    def test_i3_two_sided_nudge_bucket(self, client: TestClient) -> None:
        """T-I3 two-sided nudge: same-day nudge skips; next-day nudge re-fires.

        The nudge bucket has teeth on BOTH sides: a re-delivered same-day nudge
        is a duplicate (skipped), but a new UTC-day nudge posts afresh (unlike
        the three once-per-clinic kinds, which are idempotent forever).
        """
        nudge_body = {"company_id": COMPANY_ID, "kind": "nudge", "body": "silent 26h"}

        # Day-1 nudge already threaded (marker carries the day-1 date bucket).
        with patch("autom8_asana.services.receipts_service.datetime") as mock_dt:
            from datetime import datetime as real_datetime

            mock_dt.now.return_value = real_datetime(2026, 7, 9, 12, 0, 0)
            mock_dt.strftime = real_datetime.strftime
            day1_marker = f"RCPT|{COMPANY_ID}|nudge|2026-07-09"

            # (a) same-day re-POST -> skipped (day-1 marker already present)
            mock_same = _make_mock_asana_client(
                search_results=[_business_task(BUSINESS_GID)],
                existing_stories=[_make_story("nudge-d1", f"{day1_marker}\nsilent")],
            )
            resp_same = _post(client, mock_same, nudge_body)
            assert resp_same.status_code == 200
            assert resp_same.json()["data"]["outcome"] == "skipped_duplicate"
            mock_same.stories.create_comment_async.assert_not_called()

        # (b) day-2 nudge: only the day-1 marker exists -> a fresh day-2 marker
        #     does NOT match -> posts afresh (the recurring intent).
        with patch("autom8_asana.services.receipts_service.datetime") as mock_dt:
            from datetime import datetime as real_datetime

            mock_dt.now.return_value = real_datetime(2026, 7, 10, 12, 0, 0)
            mock_dt.strftime = real_datetime.strftime
            day1_marker = f"RCPT|{COMPANY_ID}|nudge|2026-07-09"

            mock_next = _make_mock_asana_client(
                search_results=[_business_task(BUSINESS_GID)],
                existing_stories=[_make_story("nudge-d1", f"{day1_marker}\nsilent")],
            )
            resp_next = _post(client, mock_next, nudge_body)
            assert resp_next.status_code == 200
            assert resp_next.json()["data"]["outcome"] == "posted"
            mock_next.stories.create_comment_async.assert_awaited_once()

    def test_i4_kind_distinct_markers(self, client: TestClient) -> None:
        """T-I4: a 'verified' marker does not dedup a 'mail_observed' POST."""
        verified_marker = f"RCPT|{COMPANY_ID}|verified|"
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
            existing_stories=[_make_story("s-v", f"{verified_marker}\nold")],
        )
        resp = _post(
            client,
            mock_client,
            {"company_id": COMPANY_ID, "kind": "mail_observed", "body": "first inbound"},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.stories.create_comment_async.assert_awaited_once()


# ---------------------------------------------------------------------------
# 7.3 Contract / auth / validation
# ---------------------------------------------------------------------------


class TestContractAuth:
    def test_c1_unknown_kind_422_no_resolution(self, client: TestClient) -> None:
        """T-C1: kind='bogus' -> 422 UNKNOWN_RECEIPT_KIND; NO resolution/comment."""
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(
            client,
            mock_client,
            {"company_id": COMPANY_ID, "kind": "bogus", "body": "x"},
        )

        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "UNKNOWN_RECEIPT_KIND"
        mock_client.http.get.assert_not_called()
        mock_client.stories.create_comment_async.assert_not_called()

    def test_c2_empty_company_id_422(self, client: TestClient) -> None:
        """T-C2: empty company_id -> 422 (Pydantic min_length)."""
        mock_client = _make_mock_asana_client()
        resp = _post(
            client,
            mock_client,
            {"company_id": "", "kind": "verified", "body": "x"},
        )
        assert resp.status_code == 422

    def test_c7_oversize_body_422_no_asana_call(self, client: TestClient) -> None:
        """T-C7 DoS teeth: an over-limit body (16385 chars) -> 422, NO Asana call.

        The bound is enforced at the Pydantic layer BEFORE the handler runs, so
        an unbounded-body DoS attempt is rejected clean without touching Asana:
        no tasks/search, no story create. The teeth are the negative-space
        assertions -- the client mock is NEVER awaited.
        """
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(
            client,
            mock_client,
            {"company_id": COMPANY_ID, "kind": "verified", "body": "x" * 16385},
        )

        assert resp.status_code == 422
        # No Asana call attempted: neither resolve (http.get) nor post.
        mock_client.http.get.assert_not_awaited()
        mock_client.stories.create_comment_async.assert_not_awaited()

    def test_c7b_at_limit_body_200(self, client: TestClient) -> None:
        """T-C7b GREEN: an at-limit body (exactly 16384 chars) -> 200 (posts).

        The other side of the bound: the ceiling value is accepted and threaded
        normally, proving the 422 in T-C7 is the max_length guard biting on
        16385 -- not an off-by-one that would reject legitimate at-limit bodies.
        """
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(
            client,
            mock_client,
            {"company_id": COMPANY_ID, "kind": "verified", "body": "x" * 16384},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.stories.create_comment_async.assert_awaited_once()

    def test_c8_oversize_company_id_422_no_asana_call(self, client: TestClient) -> None:
        """T-C8 DoS teeth: an over-limit company_id (257 chars) -> 422, NO call.

        Same bound-before-handler discipline as T-C7, on the tenant key: an
        over-limit company_id is a clean 422 with no Asana call attempted.
        """
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(
            client,
            mock_client,
            {"company_id": "c" * 257, "kind": "verified", "body": "x"},
        )

        assert resp.status_code == 422
        mock_client.http.get.assert_not_awaited()
        mock_client.stories.create_comment_async.assert_not_awaited()

    def test_c8b_at_limit_company_id_200(self, client: TestClient) -> None:
        """T-C8b GREEN: an at-limit company_id (exactly 256 chars) -> 200.

        The other side of the company_id bound: the ceiling value resolves and
        posts normally (the mock search returns the one Business regardless of
        the key length), proving the 422 in T-C8 is the max_length guard biting
        on 257, not a rejection of legitimate at-limit identifiers.
        """
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(
            client,
            mock_client,
            {"company_id": "c" * 256, "kind": "verified", "body": "x"},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.stories.create_comment_async.assert_awaited_once()

    def test_c3_pat_token_rejected_401(self, client: TestClient) -> None:
        """T-C3: a non-JWT (PAT-shaped) token -> 401 SERVICE_TOKEN_REQUIRED."""
        mock_client = _make_mock_asana_client()
        patches = _receipts_patches(mock_client)
        with patches[2], patches[3], patches[4]:  # bot PAT + client, NO JWT mock
            resp = client.post(
                "/v1/receipts",
                json=RECEIPT_BODY,
                headers={"Authorization": "Bearer 1/1234567890:abcdefPATtoken"},
            )
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "SERVICE_TOKEN_REQUIRED"

    def test_c4_missing_auth_401(self, client: TestClient) -> None:
        """T-C4: no Authorization header -> 401 AUTH-TEB-001 (outer middleware).

        Two-layer auth, stated precisely:
          - OUTER: the fleet JWTAuthMiddleware rejects a MISSING header with
            AUTH-TEB-001. This leg fires even under AUTH__DEV_MODE=true (which
            this suite sets) because validate_from_header checks the empty header
            BEFORE the dev_mode signature bypass -- so this test genuinely
            exercises the middleware's missing-auth rejection, not the dev
            bypass.
          - INNER: Depends(require_service_claims) is the load-bearing guard the
            REST of this suite exercises. Under dev_mode the middleware bypasses
            SIGNATURE validation for any PRESENT token, so a present-but-wrong
            token (e.g. T-C3's PAT) is rejected by the inner dependency's
            fail-closed leg (SERVICE_TOKEN_REQUIRED), not by middleware signature
            checking. This test does NOT prove middleware signature rejection --
            see the COND-2 TODO in receipts.py; no production-mode JWKS
            integration idiom exists in this harness yet.
        """
        resp = client.post("/v1/receipts", json=RECEIPT_BODY)
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "AUTH-TEB-001"

    def test_c5_success_envelope_shape(self, client: TestClient) -> None:
        """T-C5: happy path returns SuccessResponse{data, meta}."""
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        body = resp.json()
        assert resp.status_code == 200
        assert "data" in body
        assert "meta" in body
        assert set(body["data"].keys()) == {"business_gid", "story_gid", "outcome"}

    def test_c6_frozen_consumer_shape_accepted(self, client: TestClient) -> None:
        """T-C6 request-fidelity: exactly {company_id, kind, body} is accepted.

        Documents the frozen consumer contract: the three-field body the EBI
        AsanaReceiptClient.post_receipt POSTs is accepted as-is.
        """
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(client, mock_client, dict(RECEIPT_BODY))
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 7.4 Retry / degradation (D-6)
# ---------------------------------------------------------------------------


class TestRetryDegradation:
    def test_d1_create_5xx_is_503_not_retried(self, client: TestClient) -> None:
        """T-D1: create_comment raises 5xx -> 503; the POST is NOT blind-retried.

        retry-429-only-never-POST-5xx: a POST-5xx may have partially succeeded;
        a blind retry risks a duplicate story. Assert exactly one POST attempt.
        """

        class FakeServerError(Exception):
            pass

        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
            create_raises=FakeServerError("Asana 500"),
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "ASANA_UNAVAILABLE"
        # NOT retried: exactly one create_comment attempt.
        assert mock_client.stories.create_comment_async.await_count == 1

    def test_d2_field_unconfigured_503(self, client: TestClient, monkeypatch) -> None:
        """OI-2b: an unconfigured Company ID field GID -> 503, never guesses.

        This is the honest activation prerequisite: rather than resolving against
        an unknown field (which would silently mis-target), the route fail-closes.
        """
        monkeypatch.setenv("ASANA_API_COMPANY_ID_FIELD_GID", "")
        get_settings.cache_clear()
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "COMPANY_ID_FIELD_UNCONFIGURED"
        mock_client.http.get.assert_not_called()
        mock_client.stories.create_comment_async.assert_not_called()
