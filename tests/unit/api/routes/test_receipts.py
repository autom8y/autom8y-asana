"""Two-sided discriminating tests for the EBI OI-2 receipts route.

POST /v1/receipts - thread a forwarding-lifecycle receipt onto a clinic's
Business task.

Every guard is proven RED-on-the-defect AND GREEN-without-it (G-THEATER
discipline). The load-bearing cases:

  - T-R2/T-R3/T-R5 (fail-closed resolution): an unknown/ambiguous/degraded
    company MUST fail-closed (404/409), NEVER post to a fallback task. T-R5 is
    the anti-fail-open teeth: a search-degradation (empty hits) returns 404, not
    200 -- proving we did NOT wire the cold-cache-fail-open SearchService.
  - T-R6..T-R9 (duplicate-Company-ID union descend, G3): a practice card plus
    practitioner card(s) sharing one Company ID is the data model's NORMAL shape
    (the Total Wellness first-real-client shape), not an error. Exactly ONE
    distinct PLAY across the union names its HOLDING Business the receiver
    (T-R6); >1 (T-R7) or zero (T-R8) distinct PLAYs still fail-close 409 with
    the pre-cure signature; a truncated subtask page aborts LOUD as 503 (T-R9).
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

# The live Total Wellness duplicate-Company-ID shape (G3, first real client):
# ONE Company ID on TWO Business cards -- the practice (whose subtree holds the
# PLAY task, multi-homed into Calendar Integrations) and the practitioner
# (zero PLAYs). The data model's NORMAL shape, not an error.
TW_COMPANY_ID = "7363c7ea-66f8-487f-9f6e-c7a12a63d33f"
TW_PRACTICE_GID = "1214127219419742"  # "Total Wellness Center" -- holds the PLAY
TW_PRACTITIONER_GID = "1214420107547660"  # "Holly R. Geersen DC" -- zero PLAYs
TW_PLAY_GID = "1215766139321621"  # the PLAY task (Calendar Integrations member)
TW_HOLDER_GID = "1214127219419900"  # the "{Clinic} PLAYS/REQUESTS" holder
CALENDAR_INTEGRATIONS_PROJECT_GID = "1209442849265632"  # CALENDAR_INTEGRATIONS_PROJECT

TW_RECEIPT_BODY = {
    "company_id": TW_COMPANY_ID,
    "kind": "verified",
    "body": "Forwarding lifecycle: verified\nClinic: Total Wellness Center\n"
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


def _subtask(gid: str, *, in_ci: bool = False) -> dict[str, Any]:
    """A ``/tasks/{gid}/subtasks`` row; the name is deliberately unhelpful
    (the union descend filters by PROJECT MEMBERSHIP, never by name)."""
    projects = [{"gid": CALENDAR_INTEGRATIONS_PROJECT_GID}] if in_ci else [{"gid": "9999"}]
    return {"gid": gid, "name": "an unrelated-looking task name", "projects": projects}


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
    subtasks: dict[str, list[dict[str, Any]]] | None = None,
    existing_stories: list[MagicMock] | None = None,
    create_raises: Exception | None = None,
    workspace_gid: str | None = "1140000000000001",
) -> MagicMock:
    """Build a fake AsanaClient exercising the resolve -> dedup -> post path.

    Args:
        search_results: rows returned by http.get for tasks/search (WRAPPED as
            the unwrapped list -- http.get strips the {"data": ...} envelope).
        search_raises: exception raised by http.get (e.g. an Asana 5xx).
        subtasks: parent task gid -> rows its ``/tasks/{gid}/subtasks`` listing
            returns (the union-descend seam; absent parents list empty -- so a
            duplicate-Company-ID fixture with no subtask map models the
            zero-PLAY union).
        existing_stories: stories already on the resolved task (dedup input).
        create_raises: exception raised by create_comment_async (e.g. a POST-5xx).
        workspace_gid: default_workspace_gid on the client.
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.default_workspace_gid = workspace_gid

    # http.get, URL-routed: tasks/search -> search_results; /tasks/{gid}/subtasks
    # -> the fixture's per-parent rows (the union-descend seam). http.get UNWRAPS
    # the {"data": ...} envelope, so both return inner lists directly (the
    # service dual-handles both shapes).
    if search_raises is not None:
        mock_client.http.get = AsyncMock(side_effect=search_raises)
    else:
        subtasks_by_parent = subtasks or {}

        async def _routed_get(url: str, *, params: dict[str, Any] | None = None) -> Any:
            if url.endswith("/tasks/search"):
                return search_results or []
            if url.startswith("/tasks/") and url.endswith("/subtasks"):
                return subtasks_by_parent.get(url.split("/")[2], [])
            raise AssertionError(f"unexpected GET in fake client: {url}")

        mock_client.http.get = AsyncMock(side_effect=_routed_get)

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
        """T-R3 RED: two Business matches, NO disambiguating PLAY -> 409, NO
        comment, both gids surfaced.

        Post-G3 semantics: a duplicate Company-ID alone no longer fail-closes --
        the union descend looks for exactly one distinct PLAY. Here NEITHER
        subtree holds any subtask (the default empty subtasks map), so the union
        yields zero PLAYs and the resolution fail-closes with the SAME
        CompanyAmbiguous/409 signature as before the cure.
        """
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
# 7.1b Duplicate-Company-ID UNION DESCEND (G3) -- T-R6..T-R9
#
# The Total Wellness first-real-client shape: ONE Company ID on TWO Business
# cards (practice + practitioner) is the data model's NORMAL shape. Pre-cure,
# _resolve_business_gid fail-closed CompanyAmbiguous/409 on it, silently
# dropping the first real client's receipt trail. The ruled cure is the SAME
# union-descend semantics already live in ci_task_resolution (D3 / PR #226):
# descend ALL matched subtrees (membership-filtered, name-free, depth cap 2);
# exactly ONE distinct PLAY names its HOLDING Business the receiver; zero or
# >1 distinct PLAYs keep the pre-cure fail-close.
# ---------------------------------------------------------------------------


class TestUnionDescendResolution:
    def _tw_mock(
        self,
        *,
        practitioner_subtree: dict[str, list[dict[str, Any]]] | None = None,
    ) -> MagicMock:
        """The live TW shape: practice subtree holds THE one PLAY (via the
        holder hop); the practitioner subtree defaults to a holder with zero
        PLAYs (override to model other shapes)."""
        subtasks: dict[str, list[dict[str, Any]]] = {
            TW_PRACTICE_GID: [_subtask(TW_HOLDER_GID)],
            TW_HOLDER_GID: [_subtask(TW_PLAY_GID, in_ci=True), _subtask("noise-1")],
        }
        subtasks.update(
            practitioner_subtree
            if practitioner_subtree is not None
            else {
                TW_PRACTITIONER_GID: [_subtask("practitioner-holder")],
                "practitioner-holder": [],
            }
        )
        return _make_mock_asana_client(
            search_results=[
                _business_task(TW_PRACTICE_GID),
                _business_task(TW_PRACTITIONER_GID),
            ],
            subtasks=subtasks,
        )

    def test_r6_green_tw_duplicate_resolves_play_holding_business(self, client: TestClient) -> None:
        """T-R6 GREEN (the G3 cure, live TW shape): two Business cards share the
        Company ID; ONLY the practice subtree holds the PLAY -> the receipt
        resolves to the PRACTICE card and posts there.

        RED side (the pre-cure defect, proven by running this test against the
        pinned pre-cure code): _resolve_business_gid raised
        CompanyAmbiguous -> 409 COMPANY_AMBIGUOUS on the bare duplicate,
        silently dropping the first real client's receipt trail.
        """
        mock_client = self._tw_mock()
        resp = _post(client, mock_client, TW_RECEIPT_BODY)

        assert resp.status_code == 200, f"expected resolve, got {resp.status_code}: {resp.text}"
        data = resp.json()["data"]
        assert data["business_gid"] == TW_PRACTICE_GID
        assert data["outcome"] == "posted"
        # The comment threads onto the PRACTICE card (the PLAY holder), never
        # the practitioner card.
        create_kwargs = mock_client.stories.create_comment_async.await_args.kwargs
        assert create_kwargs["task"] == TW_PRACTICE_GID

    def test_r7_red_two_distinct_plays_still_409_no_post(self, client: TestClient) -> None:
        """T-R7 RED (no over-relax): EACH subtree holds a DISTINCT PLAY -> the
        union yields two distinct receivers -> 409 with the pre-cure signature,
        NO comment. Ambiguity is adjudicated at the PLAY level and still
        fail-closes. This test passes PRE-cure and POST-cure (two-sided guard
        against over-relaxation).
        """
        mock_client = self._tw_mock(
            practitioner_subtree={
                TW_PRACTITIONER_GID: [_subtask("practitioner-holder")],
                "practitioner-holder": [_subtask("second-play", in_ci=True)],
            }
        )
        resp = _post(client, mock_client, TW_RECEIPT_BODY)

        assert resp.status_code == 409
        err = resp.json()["error"]
        assert err["code"] == "COMPANY_AMBIGUOUS"
        assert set(err["details"]["gids"]) == {TW_PRACTICE_GID, TW_PRACTITIONER_GID}
        mock_client.stories.create_comment_async.assert_not_called()

    def test_r8_red_zero_plays_still_409_no_post(self, client: TestClient) -> None:
        """T-R8 RED: duplicate Business cards but ZERO PLAYs anywhere in the
        union -> no disambiguating evidence -> 409 with the pre-cure signature,
        NO comment (never guess a receiver).
        """
        mock_client = _make_mock_asana_client(
            search_results=[
                _business_task(TW_PRACTICE_GID),
                _business_task(TW_PRACTITIONER_GID),
            ],
            subtasks={
                TW_PRACTICE_GID: [_subtask("empty-holder-a")],
                "empty-holder-a": [],
                TW_PRACTITIONER_GID: [],
            },
        )
        resp = _post(client, mock_client, TW_RECEIPT_BODY)

        assert resp.status_code == 409
        err = resp.json()["error"]
        assert err["code"] == "COMPANY_AMBIGUOUS"
        assert set(err["details"]["gids"]) == {TW_PRACTICE_GID, TW_PRACTITIONER_GID}
        mock_client.stories.create_comment_async.assert_not_called()

    def test_r9_red_truncated_subtask_page_is_503_no_post(self, client: TestClient) -> None:
        """T-R9 RED (cap-abort teeth at the route altitude): a FULL subtask page
        under ANY matched Business cannot prove completeness -> the descend
        aborts LOUD (SubtaskPageCapExceeded), the route's boundary catch maps it
        to 503, and NO comment posts (never resolve against a truncated union).
        """
        full_page = [_subtask(f"bulk-{i}") for i in range(100)]
        mock_client = _make_mock_asana_client(
            search_results=[
                _business_task(TW_PRACTICE_GID),
                _business_task(TW_PRACTITIONER_GID),
            ],
            subtasks={TW_PRACTICE_GID: full_page},
        )
        resp = _post(client, mock_client, TW_RECEIPT_BODY)

        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "ASANA_UNAVAILABLE"
        mock_client.stories.create_comment_async.assert_not_called()

    def test_r10_single_match_never_descends(self, client: TestClient) -> None:
        """T-R10 (happy-path byte-parity teeth): exactly ONE Business match
        short-circuits BEFORE any union descend -- the only GET issued is the
        Company-ID search, zero subtask listings.

        RED side: a resolver that descended unconditionally would issue
        /tasks/{gid}/subtasks GETs and trip the call-count assertion.
        """
        mock_client = _make_mock_asana_client(
            search_results=[_business_task(BUSINESS_GID)],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        assert resp.json()["data"]["business_gid"] == BUSINESS_GID
        urls = [call.args[0] for call in mock_client.http.get.await_args_list]
        assert all(url.endswith("/tasks/search") for url in urls)
        assert len(urls) == 1


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


# ===========================================================================
# 7.5 Forwarding-Stage WRITE surface (S1 / ADR-FS-004) -- T-W1..T-W6
#
# The receipts route optionally advances the "Forwarding Stage" single-select on
# the clinic's Calendar Integrations task after threading the comment. Default
# OFF = INERT (byte-identical to the comment-only baseline). Every guard is
# two-sided: the defect variant fires RED, the no-defect variant GREEN.
# ===========================================================================

# CI-task (Calendar Integrations) constants for the SECOND resolution.
CI_PROJECT_GID = "1209442849265632"  # CALENDAR_INTEGRATIONS_PROJECT (project_registry.py:60)
CI_TASK_GID = "1209000000000007"
FORWARDING_FIELD_GID = "1216419441591239"  # operator-seeded field def (test value)

# stage value -> option GID (the operator-supplied config map; test values).
STAGE_OPTION_GIDS = {
    "Sent": "1216419441591240",
    "Approved": "1216419441591241",
    "Verified": "1216419441591242",
    "Stalled": "1216419441591243",
    "Flowing": "1216419441591244",
    "Live": "1216419441591245",
    "Inactive": "1216419441591246",
}


def _ci_task(gid: str = CI_TASK_GID) -> dict[str, Any]:
    """A tasks/search row that is a member of the Calendar Integrations project."""
    return {"gid": gid, "name": "PLAY: CI Task", "projects": [{"gid": CI_PROJECT_GID}]}


def _ci_task_raw(current_option_gid: str | None) -> dict[str, Any]:
    """A tasks.get(raw=True) payload carrying the Forwarding-Stage custom field.

    ``current_option_gid=None`` models an unset field; a GID models a set value.
    """
    enum_value = {"gid": current_option_gid} if current_option_gid else None
    return {
        "gid": CI_TASK_GID,
        "custom_fields": [
            {"gid": "9999999999", "name": "Some Other Field", "enum_value": None},
            {
                "gid": FORWARDING_FIELD_GID,
                "name": "Forwarding Stage",
                "enum_value": enum_value,
            },
        ],
    }


def _make_stage_aware_client(
    *,
    search_rows: list[dict[str, Any]],
    current_option_gid: str | None,
    existing_stories: list[MagicMock] | None = None,
    ci_get_raises: Exception | None = None,
    update_raises: Exception | None = None,
) -> MagicMock:
    """A fake AsanaClient wired for BOTH the comment leg and the stage-advance leg.

    ``http.get`` returns the SAME ``search_rows`` for every tasks/search call --
    faithful to Asana, which returns every task carrying the Company ID value; the
    service filters each resolution to its own project (Businesses vs Calendar
    Integrations). Include a Business row AND a CI row to satisfy both.
    ``tasks.get_async`` returns the CI-task raw payload (the current stage read);
    ``tasks.update_async`` is the PUT.
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.default_workspace_gid = "1140000000000001"

    mock_client.http.get = AsyncMock(return_value=search_rows)

    mock_client.stories.list_for_task_async = MagicMock(
        return_value=_make_collect_mock(existing_stories or []),
    )
    mock_client.stories.create_comment_async = AsyncMock(
        return_value=_make_story(NEW_STORY_GID, "posted"),
    )

    # tasks.get_async(ci_gid, raw=True, opt_fields=[...]) -> raw dict
    if ci_get_raises is not None:
        mock_client.tasks.get_async = AsyncMock(side_effect=ci_get_raises)
    else:
        mock_client.tasks.get_async = AsyncMock(
            return_value=_ci_task_raw(current_option_gid),
        )
    # tasks.update_async(ci_gid, custom_fields={...}) -> Task (ignored)
    if update_raises is not None:
        mock_client.tasks.update_async = AsyncMock(side_effect=update_raises)
    else:
        mock_client.tasks.update_async = AsyncMock(return_value=MagicMock())

    return mock_client


def _enable_stage_write(monkeypatch, *, disposition: dict[str, str] | None = None) -> None:
    """Flip the master switch ON and configure the field + option-GID map."""
    import json

    monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_WRITE_ENABLED", "true")
    monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_FIELD_GID", FORWARDING_FIELD_GID)
    monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_OPTION_GIDS", json.dumps(STAGE_OPTION_GIDS))
    if disposition is not None:
        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_DISPOSITION", json.dumps(disposition))
    get_settings.cache_clear()


class TestStageWriteSurface:
    def test_w1_inert_default_is_byte_identical(self, client: TestClient) -> None:
        """T-W1: switch OFF (default) -> comment posts, NO stage read/PUT.

        The dark-posture teeth: with the master switch OFF the write leg is a pure
        NO-OP. The response is identical to the comment-only baseline and NEITHER
        tasks.get_async NOR tasks.update_async is ever awaited.

        RED side: a leg that fired a PUT regardless of the flag would trip
        update_async.assert_not_called().
        """
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=None,
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["business_gid"] == BUSINESS_GID
        assert data["outcome"] == "posted"
        # No stage-advance activity at all (INERT).
        mock_client.tasks.get_async.assert_not_called()
        mock_client.tasks.update_async.assert_not_called()

    def test_w1b_flag_off_but_fully_configured_still_inert(
        self, client: TestClient, monkeypatch
    ) -> None:
        """T-W1b: field GID + option map configured but the FLAG is OFF -> INERT.

        This is the discriminating teeth on the master switch SPECIFICALLY: with
        the field GID and the option-GID map fully populated (so the other two
        gates are satisfied), the write leg STILL does nothing because the master
        switch is off. This proves the flag is independently load-bearing -- not
        merely masked by an empty option map.

        RED side: removing the `is_active` flag gate (advancing whenever the field
        + map are present, ignoring the switch) would trip
        tasks.get_async.assert_not_called().
        """
        import json

        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_WRITE_ENABLED", "false")  # OFF
        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_FIELD_GID", FORWARDING_FIELD_GID)
        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_OPTION_GIDS", json.dumps(STAGE_OPTION_GIDS))
        get_settings.cache_clear()

        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=None,
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        # The flag alone keeps it INERT despite full field/option config.
        mock_client.tasks.get_async.assert_not_called()
        mock_client.tasks.update_async.assert_not_called()

    def test_w1c_flag_on_but_field_gid_empty_is_noop(self, client: TestClient, monkeypatch) -> None:
        """T-W1c: flag ON but field GID empty -> NO-OP (comment still succeeds).

        The unconfigured-field gate: with the switch ON but no field GID, the write
        leg is a NO-OP (never a 503 -- the comment already succeeded). Proves the
        field-GID gate is independently load-bearing.
        """
        import json

        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_WRITE_ENABLED", "true")  # ON
        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_FIELD_GID", "")  # but empty
        monkeypatch.setenv("ASANA_API_FORWARDING_STAGE_OPTION_GIDS", json.dumps(STAGE_OPTION_GIDS))
        get_settings.cache_clear()

        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=None,
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.tasks.update_async.assert_not_called()

    def test_w2_configured_path_advances(self, client: TestClient, monkeypatch) -> None:
        """T-W2: switch ON + resolvable CI task + fresh field -> PUT Verified option.

        RED side: a leg that did NOT PUT (or PUT the wrong option) would fail the
        exact-args assertion below. The 'verified' receipt maps to the Verified
        stage; the PUT targets the CI task with the Verified option GID.
        """
        _enable_stage_write(monkeypatch)
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=None,  # fresh clinic -> advance allowed
        )
        resp = _post(client, mock_client, RECEIPT_BODY)  # kind='verified'

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.tasks.update_async.assert_awaited_once_with(
            CI_TASK_GID,
            custom_fields={FORWARDING_FIELD_GID: STAGE_OPTION_GIDS["Verified"]},
        )

    def test_w3_idempotent_repost_no_duplicate_advance(
        self, client: TestClient, monkeypatch
    ) -> None:
        """T-W3: a receipt whose stage is already set -> validator NO_OP, ZERO PUT.

        The current CI field already reads Verified; a 'verified' receipt maps to
        Verified -> NO_OP -> no PUT (idempotent re-post).

        RED side: a leg missing the current-read + validator guard would PUT again
        (a duplicate advance) and trip update_async.assert_not_called().
        """
        _enable_stage_write(monkeypatch)
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=STAGE_OPTION_GIDS["Verified"],  # already Verified
        )
        resp = _post(client, mock_client, RECEIPT_BODY)  # kind='verified'

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.tasks.get_async.assert_awaited_once()  # it DID read
        mock_client.tasks.update_async.assert_not_called()  # but did NOT re-PUT

    def test_w4_regression_via_receipt_refused(self, client: TestClient, monkeypatch) -> None:
        """T-W4: field at Live, a late 'verified' receipt -> REFUSE, no PUT.

        The machine-never-regresses teeth at the route altitude: the CI field
        already reads Live; a stale 'verified' receipt maps to Verified (rank 2 <
        Live rank 4) -> REFUSE_REGRESSION -> no PUT.

        RED side: a leg without the monotonic validator would PUT Verified over
        Live (dragging the board backward) and trip update_async.assert_not_called().
        The comment still succeeds (best-effort advance).
        """
        _enable_stage_write(monkeypatch)
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=STAGE_OPTION_GIDS["Live"],  # already Live
        )
        resp = _post(client, mock_client, RECEIPT_BODY)  # stale kind='verified'

        assert resp.status_code == 200  # comment still posts
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.tasks.update_async.assert_not_called()

    def test_w5_ci_unresolved_is_best_effort_comment_succeeds(
        self, client: TestClient, monkeypatch
    ) -> None:
        """T-W5: 0 CI matches -> stage advance skipped, comment STILL 200.

        The best-effort teeth: when the second resolution finds no Calendar
        Integrations task (only a Business row in the search), the advance is
        skipped and logged -- but the receipt route returns the comment outcome
        (200), NEVER a 5xx.

        RED side: a leg that raised on a 0-match CI resolution (instead of
        skipping) would turn this into a 503 and fail the 200 assertion.
        """
        _enable_stage_write(monkeypatch)
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID)],  # NO CI row -> 0 CI matches
            current_option_gid=None,
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        assert resp.json()["data"]["outcome"] == "posted"
        mock_client.stories.create_comment_async.assert_awaited_once()
        mock_client.tasks.update_async.assert_not_called()  # skipped, never guessed

    def test_w5b_stage_advance_error_never_fails_receipt(
        self, client: TestClient, monkeypatch
    ) -> None:
        """T-W5b: a PUT that raises is swallowed -> receipt route still 200.

        The no-throw wrapper teeth: even if tasks.update_async raises (an Asana
        5xx on the write leg), the comment already succeeded, so the route returns
        200. The stage-advance failure is logged and swallowed.

        RED side: an unwrapped advance leg would propagate the exception to the
        route's broad handler -> 503, failing the 200 assertion.
        """
        _enable_stage_write(monkeypatch)

        class FakeAsanaError(Exception):
            pass

        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=None,
            update_raises=FakeAsanaError("Asana 500 on PUT"),
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200  # comment stands; advance error swallowed
        assert resp.json()["data"]["outcome"] == "posted"

    def test_w6_unknown_current_option_fails_closed_no_put(
        self, client: TestClient, monkeypatch
    ) -> None:
        """T-W6: CI field reads an option GID NOT in the config map -> no PUT.

        Fail-closed teeth at the route altitude: the current field carries an
        option GID absent from the operator config map (an out-of-band value). The
        service maps it to an _UnknownStage sentinel -> validator REFUSE_UNKNOWN ->
        no PUT (never guess an advance off an unknown value).

        RED side: a leg that treated an unmapped current as 'unset' (fail-open)
        would advance and PUT -- tripping update_async.assert_not_called().
        """
        _enable_stage_write(monkeypatch)
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid="9090909090909090",  # NOT in STAGE_OPTION_GIDS
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        mock_client.tasks.get_async.assert_awaited_once()
        mock_client.tasks.update_async.assert_not_called()

    def test_w7_stall_overlay_advances_on_nudge(self, client: TestClient, monkeypatch) -> None:
        """T-W7: a nudge on a Verified clinic -> PUT the Stalled option (overlay).

        The nudge->Stalled reconciliation at the route altitude: a 'nudge' receipt
        maps to Stalled; from a Verified current that is a legitimate overlay ->
        PUT the Stalled option GID.

        RED side: a leg that refused the Stalled overlay (or mapped nudge to the
        wrong stage) would not PUT the Stalled option.
        """
        _enable_stage_write(monkeypatch)
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=STAGE_OPTION_GIDS["Verified"],
        )
        resp = _post(
            client,
            mock_client,
            {"company_id": COMPANY_ID, "kind": "nudge", "body": "silent 26h"},
        )

        assert resp.status_code == 200
        mock_client.tasks.update_async.assert_awaited_once_with(
            CI_TASK_GID,
            custom_fields={FORWARDING_FIELD_GID: STAGE_OPTION_GIDS["Stalled"]},
        )

    def test_w8_inactive_parked_refuses_advance(self, client: TestClient, monkeypatch) -> None:
        """T-W8: an Inactive clinic (disposition=parked) -> no PUT (data-driven).

        The Inactive-disposition teeth at the route altitude: the CI field reads
        Inactive; with the default (parked) disposition the machine refuses to
        auto-advance -> no PUT. The comment still succeeds.
        """
        _enable_stage_write(monkeypatch, disposition={"Inactive": "parked"})
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=STAGE_OPTION_GIDS["Inactive"],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        mock_client.tasks.update_async.assert_not_called()

    def test_w8b_inactive_ignored_advances_data_driven(
        self, client: TestClient, monkeypatch
    ) -> None:
        """T-W8b: the SAME Inactive clinic, disposition=ignored -> PUT proceeds.

        The DATA-DRIVEN proof at the route altitude: identical task state, ONLY
        the config disposition differs (ignored vs parked in T-W8), and the
        outcome inverts -- the advance now PUTs. The Inactive ruling is config,
        never code (ADR-FS-005 / operator sovereign ruling 2026-07-09).
        """
        _enable_stage_write(monkeypatch, disposition={"Inactive": "ignored"})
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=STAGE_OPTION_GIDS["Inactive"],
        )
        resp = _post(client, mock_client, RECEIPT_BODY)  # kind='verified'

        assert resp.status_code == 200
        mock_client.tasks.update_async.assert_awaited_once_with(
            CI_TASK_GID,
            custom_fields={FORWARDING_FIELD_GID: STAGE_OPTION_GIDS["Verified"]},
        )

    def test_w9_guest_pat_scope_no_workspace_field_listing(
        self, client: TestClient, monkeypatch
    ) -> None:
        """T-W9: the write leg NEVER calls a workspace-level custom_fields listing.

        Guest-PAT scope teeth: the field GID + option GIDs arrive via config; the
        write leg only uses tasks/search (http.get), tasks.get_async, and
        tasks.update_async (all task/project scope). A workspace-level
        custom_fields listing (which 402s for the guest PAT) is NEVER attempted --
        the fake has no such method configured, and asserting the absence of any
        custom_fields client attribute access proves the scope discipline.
        """
        _enable_stage_write(monkeypatch)
        mock_client = _make_stage_aware_client(
            search_rows=[_business_task(BUSINESS_GID), _ci_task()],
            current_option_gid=None,
        )
        # A workspace-level listing would go through a custom_fields client; assert
        # the service never reaches for one. We attach a tripwire that records any
        # access to a `custom_fields` attribute on the client.
        tripwire = MagicMock()
        mock_client.custom_fields = tripwire

        resp = _post(client, mock_client, RECEIPT_BODY)

        assert resp.status_code == 200
        # The only task-scope calls were made; no custom_fields client method used.
        tripwire.assert_not_called()
        assert not tripwire.method_calls
        # Positive: the task-scope PUT did fire.
        mock_client.tasks.update_async.assert_awaited_once()
