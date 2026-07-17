"""Two-sided discriminating tests for the link-on-PLAY deck comment poster.

Per TDD-sand-lake-link-on-play-2026-07-06.md §9. Every test is RED/GREEN
discriminating. The single production-mutating boundary -- the Asana
``create_comment`` ADD -- is NEVER hit outside the two GREEN execute-paths that
assert it was awaited exactly once; every RED (refusal) path and every dry-run
path carries the anti-theater invariant
``create_comment_async.assert_not_awaited()`` so a poster that silently posts on
a refusal/dry-run cannot pass green.

Fakes only (no live Asana): a ``MagicMock`` client with ``AsyncMock`` task-get and
comment-create, a ``list_for_task_async`` returning an object whose ``collect`` is
an ``AsyncMock``, and ``resolve_section_gids`` patched at the link_on_play module
path. Mirrors the fake-client style of test_onboarding_walkthrough.py.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough import constants
from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import (
    POSTER_MARKER_PREFIX,
    LinkOnPlayRefused,
    compose_comment_text,
    compose_marker,
    deck_slug_from_url,
    post_link_on_play,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    CANONICAL_ROUTING_ADDR_RE,
)

# --- Probe constants (TDD §1/§3; real Sand Lake target) ---

PROJECT_GID = constants.CALENDAR_INTEGRATIONS_PROJECT_GID  # "1209442849265632"
TASK_GID = "1215823342887129"
REAL_DECK_URL = "https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/"
REAL_SLUG = "207688021de88a6d7231e1d08ea77a85"
# A canonical routing address (the spike test GUID) -- distinct from a deck slug;
# only reaches the composed text via a malformed deck URL, where §6 must catch it.
ROUTING_ADDR = "b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com"

_RESOLVE_PATH = (
    "autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play.resolve_section_gids"
)


# --- Fake builders ---


def _play_name(clinic: str = "Sand Lake Dental") -> str:
    return f"PLAY: Custom Calendar Integration — {clinic}"


def _active_membership() -> dict:
    return {
        "project": {"gid": PROJECT_GID, "name": "Calendar Integrations"},
        "section": {"gid": "SEC_ACTIVE", "name": "ACTIVE"},
    }


def _make_task(name: str, memberships: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(name=name, memberships=memberships)


def _make_client(*, task: SimpleNamespace, stories: list) -> MagicMock:
    """Fake AsanaClient: async task-get + comment-create, sync list -> async collect."""
    client = MagicMock()
    client.tasks.get_async = AsyncMock(return_value=task)
    client.stories.create_comment_async = AsyncMock(
        return_value=SimpleNamespace(gid="NEW_STORY_GID")
    )
    client.stories.list_for_task_async = MagicMock(
        return_value=SimpleNamespace(collect=AsyncMock(return_value=list(stories)))
    )
    return client


def _resolved_active() -> dict[str, str]:
    # Mirrors resolve_section_gids: lowercase section name -> gid.
    return {"active": "SEC_ACTIVE"}


# --- GREEN ---


async def test_g1_fresh_post_awaited_once_with_composed_text() -> None:
    """G1: valid target, no prior marker, execute -> posts once with URL + marker."""
    task = _make_task(_play_name(), [_active_membership()])
    client = _make_client(task=task, stories=[])
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=_resolved_active())):
        result = await post_link_on_play(
            client, task_gid=TASK_GID, deck_url=REAL_DECK_URL, execute=True
        )
    assert result.outcome == "posted"
    assert result.story_gid == "NEW_STORY_GID"
    assert result.deck_slug == REAL_SLUG
    client.stories.create_comment_async.assert_awaited_once()
    _, kwargs = client.stories.create_comment_async.await_args
    assert kwargs["task"] == TASK_GID
    assert REAL_DECK_URL in kwargs["text"]
    assert compose_marker(REAL_SLUG) in kwargs["text"]


async def test_g2_idempotent_skip_returns_existing_gid_no_post() -> None:
    """G2: a prior comment already carries THIS slug's marker -> skip, no post."""
    task = _make_task(_play_name(), [_active_membership()])
    existing = SimpleNamespace(
        gid="EXISTING_STORY_GID",
        text=f"earlier rep note\n\n{compose_marker(REAL_SLUG)}",
    )
    client = _make_client(task=task, stories=[existing])
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=_resolved_active())):
        result = await post_link_on_play(
            client, task_gid=TASK_GID, deck_url=REAL_DECK_URL, execute=True
        )
    assert result.outcome == "skipped_existing"
    assert result.story_gid == "EXISTING_STORY_GID"
    client.stories.create_comment_async.assert_not_awaited()


async def test_g3_different_slug_posts_afresh() -> None:
    """G3: prior marker is for a DIFFERENT deck slug -> this slug absent -> posts."""
    task = _make_task(_play_name(), [_active_membership()])
    other = SimpleNamespace(
        gid="OLD_STORY_GID",
        text=compose_marker("0000000000000000000000000000abcd"),
    )
    client = _make_client(task=task, stories=[other])
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=_resolved_active())):
        result = await post_link_on_play(
            client, task_gid=TASK_GID, deck_url=REAL_DECK_URL, execute=True
        )
    assert result.outcome == "posted"
    assert result.story_gid == "NEW_STORY_GID"
    client.stories.create_comment_async.assert_awaited_once()


async def test_g4_dry_run_default_composes_but_never_posts() -> None:
    """G4: execute=False (the default) -> would-post intent, URL + marker composed, no post."""
    task = _make_task(_play_name(), [_active_membership()])
    client = _make_client(task=task, stories=[])
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=_resolved_active())):
        result = await post_link_on_play(
            client, task_gid=TASK_GID, deck_url=REAL_DECK_URL, execute=False
        )
    assert result.outcome == "dry_run_would_post"
    assert result.story_gid is None
    assert REAL_DECK_URL in result.comment_text
    assert compose_marker(REAL_SLUG) in result.comment_text
    client.stories.create_comment_async.assert_not_awaited()


# --- RED (must REFUSE; every case asserts create_comment_async NOT awaited) ---


async def test_r1_egress_guard_refuses_mailbox_bearing_text() -> None:
    """R1: a routing address rides in via the deck URL -> composed bytes match the
    egress oracle -> refuse BEFORE any post. Real teeth: the guard inspects the
    composed text, not the URL in isolation."""
    task = _make_task(_play_name(), [_active_membership()])
    client = _make_client(task=task, stories=[])
    mailbox_deck_url = f"https://decks.cntently.com/{ROUTING_ADDR}/"
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=_resolved_active())):
        with pytest.raises(LinkOnPlayRefused, match="egress guard"):
            await post_link_on_play(
                client, task_gid=TASK_GID, deck_url=mailbox_deck_url, execute=True
            )
    client.stories.create_comment_async.assert_not_awaited()


@pytest.mark.parametrize(
    ("memberships", "resolved"),
    [
        pytest.param(
            [
                {
                    "project": {"gid": "9999999999999999", "name": "Other Project"},
                    "section": {"gid": "SEC_ACTIVE", "name": "ACTIVE"},
                }
            ],
            {"active": "SEC_ACTIVE"},
            id="wrong_project",
        ),
        pytest.param(
            [
                {
                    "project": {"gid": PROJECT_GID, "name": "Calendar Integrations"},
                    "section": {"gid": "SEC_BACKLOG", "name": "BACKLOG"},
                }
            ],
            {"active": "SEC_ACTIVE"},
            id="inactive_section",
        ),
        pytest.param(
            [_active_membership()],
            {},
            id="empty_resolved_fail_closed",
        ),
    ],
)
async def test_r2_wrong_project_or_not_active_refuses(
    memberships: list[dict], resolved: dict[str, str]
) -> None:
    """R2: correct PLAY name but membership is a different project, a non-ACTIVE
    section, or the ACTIVE resolution came back empty -> fail-closed refuse."""
    task = _make_task(_play_name(), memberships)
    client = _make_client(task=task, stories=[])
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=resolved)):
        with pytest.raises(LinkOnPlayRefused, match="ACTIVE section"):
            await post_link_on_play(client, task_gid=TASK_GID, deck_url=REAL_DECK_URL, execute=True)
    client.stories.create_comment_async.assert_not_awaited()


@pytest.mark.parametrize(
    "bad_name",
    [
        "Playa Vista Dental",  # near-miss: contains "Play" but not "PLAY:" + phrase
        "Weekly Sync",
        "play: custom calendar integration — x",  # case-sensitive: lowercase must not match
        "",
    ],
)
async def test_r3_name_not_play_convention_refuses(bad_name: str) -> None:
    """R3: the name fails the PLAY: Custom Calendar Integration convention (membership
    is otherwise valid, isolating the name as the sole refusal cause) -> refuse."""
    task = _make_task(bad_name, [_active_membership()])
    client = _make_client(task=task, stories=[])
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=_resolved_active())):
        with pytest.raises(LinkOnPlayRefused, match="PLAY"):
            await post_link_on_play(client, task_gid=TASK_GID, deck_url=REAL_DECK_URL, execute=True)
    client.stories.create_comment_async.assert_not_awaited()


@pytest.mark.parametrize(
    "bad_url",
    [
        pytest.param("https://evil.example/207688021de88a6d7231e1d08ea77a85/", id="R4_evil_domain"),
        pytest.param(
            "http://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/", id="R5_http_scheme"
        ),
        pytest.param(
            "https://deck@decks.cntently.com/207688021de88a6d7231e1d08ea77a85/", id="R6_userinfo"
        ),
    ],
)
async def test_deck_url_host_pin_refuses(bad_url: str) -> None:
    """R4-R6 (N3 QA host-pin condition): a foreign host, an http scheme, or a
    userinfo form is refused at URL validation (step 1) -- before preflight,
    compose, or any post -- naming the offending host. Even a valid 32-hex slug
    on a non-decks.cntently.com host cannot be composed into a posted comment."""
    task = _make_task(_play_name(), [_active_membership()])
    client = _make_client(task=task, stories=[])
    with patch(_RESOLVE_PATH, new=AsyncMock(return_value=_resolved_active())):
        with pytest.raises(LinkOnPlayRefused, match="host"):
            await post_link_on_play(client, task_gid=TASK_GID, deck_url=bad_url, execute=True)
    client.stories.create_comment_async.assert_not_awaited()


# --- Unit (pure, cheap -- lock the invariants) ---


def test_u1_marker_slug_scoping() -> None:
    """U1: the marker is slug-scoped and byte-exact for the real deck slug."""
    assert compose_marker("A") != compose_marker("B")
    assert compose_marker(REAL_SLUG) == f"[{POSTER_MARKER_PREFIX} deck={REAL_SLUG}]"
    assert (
        compose_marker(REAL_SLUG) == "[autom8y:link-on-play deck=207688021de88a6d7231e1d08ea77a85]"
    )


def test_u2_composed_text_is_egress_clean() -> None:
    """U2: the legit composed text carries NO routing address (catches a future
    template edit that would introduce one), while the URL + marker ARE present."""
    text = compose_comment_text(REAL_DECK_URL)
    assert CANONICAL_ROUTING_ADDR_RE.search(text) is None
    assert REAL_DECK_URL in text
    assert compose_marker(REAL_SLUG) in text


def test_u3_slug_extraction_and_slugless_refusal() -> None:
    """U3: last path segment is the slug (trailing slash or not); a slug-less URL refuses."""
    assert deck_slug_from_url(REAL_DECK_URL) == REAL_SLUG
    assert (
        deck_slug_from_url("https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85")
        == REAL_SLUG
    )
    for slugless in ("https://decks.cntently.com/", "https://decks.cntently.com", ""):
        with pytest.raises(LinkOnPlayRefused):
            deck_slug_from_url(slugless)
