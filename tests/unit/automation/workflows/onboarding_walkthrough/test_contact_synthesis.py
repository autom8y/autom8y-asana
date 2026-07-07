"""Guard matrix for ``contact_synthesis`` (the ranked contact-card poster).

Per TDD-contact-card-on-play-phase1-2026-07-07 §12 (six guards G-i..G-vi + supplement
fixtures) + ADR §8. Every RED test names the refusal/exclusion it proves; every GREEN
test names the accepted path.

The traversal mechanics (D1-D4) are exercised against real ``Task`` fixtures in
``TestTraversal``; the orchestrator branch/guard logic is exercised with ``resolve_ranked_cards``
monkeypatched to a canned result so the two concerns stay separable.
"""

from __future__ import annotations

import types

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough import contact_synthesis as cs
from autom8_asana.automation.workflows.onboarding_walkthrough.contact_synthesis import (
    ContactCardEgressRefused,
    ContactCardRenderError,
    compose_card,
    compose_marker,
    post_contact_card,
    render_l1_table,
    render_plain_text,
)
from autom8_asana.models import Task
from autom8_asana.models.business.contact import ContactCard, Provenance

DECK = "sand-lake"


# --------------------------------------------------------------------------- helpers


def _card(
    *,
    full_name="Jane Roe",
    nickname="Jane",
    contact_email="jane@clinic.com",
    role="Owner",
    rank=1,
    rank_reason="owner/Owner",
    provenance=Provenance.ASANA,
) -> ContactCard:
    return ContactCard(
        full_name=full_name,
        nickname=nickname,
        contact_email=contact_email,
        role=role,
        provenance=provenance,
        rank=rank,
        rank_reason=rank_reason,
    )


class _Story:
    def __init__(self, gid, *, text=None, html_text=None):
        self.gid = gid
        self.text = text
        self.html_text = html_text


class _Collectable:
    def __init__(self, items):
        self._items = items

    async def collect(self):
        return self._items


class _FakeStories:
    def __init__(self, *, existing=None, created=None, readback=None):
        self._existing = existing or []
        self._created = created
        self._readback = readback
        self.create_calls: list[dict] = []

    def list_for_task_async(self, task_gid, opt_fields=None):
        return _Collectable(self._existing)

    async def create_comment_async(self, *, task, text, html_text=None, is_pinned=None):
        self.create_calls.append({"task": task, "text": text, "html_text": html_text})
        return self._created or _Story("new-story")

    async def get_async(self, story_gid, opt_fields=None):
        return self._readback


class _FakeAsana:
    def __init__(self, stories):
        self.stories = stories
        self.tasks = None


def _patch_resolve(monkeypatch, *, holder_found, cards):
    async def _fake(asana_client, data_client, office_phone, vertical):
        return holder_found, cards

    monkeypatch.setattr(cs, "resolve_ranked_cards", _fake)


async def _run(asana, *, execute=False, cards=None, holder_found=True, monkeypatch=None):
    _patch_resolve(monkeypatch, holder_found=holder_found, cards=cards or [])
    return await post_contact_card(
        asana,
        play_gid="PLAY-1",
        deck_slug=DECK,
        data_client=object(),
        office_phone="+14073550608",
        vertical="dentistry",
        execute=execute,
    )


# ------------------------------------------------------------------- G-i HTML escaping


class TestGiEscaping:
    def test_red1_br_in_name_is_escaped_no_raw_br(self) -> None:
        """G-i-RED-1: 'Dr <br> Smith' -> composed html has &lt;br&gt; and zero raw <br>.

        The escape fires at field-escape time (PRE composition/post): the raw <br> that
        would trip Asana's silent-201 entity-escape can never reach the wire.
        """
        html_text = render_l1_table([_card(full_name="Dr <br> Smith")], DECK)
        assert "&lt;br&gt;" in html_text
        assert "<br>" not in html_text  # no raw <br> anywhere

    def test_red2_ampersand_in_email_is_escaped(self) -> None:
        html_text = render_l1_table([_card(contact_email="a&b@clinic.com")], DECK)
        assert "a&amp;b@clinic.com" in html_text

    def test_green1_unicode_and_apostrophe_render(self) -> None:
        html_text = render_l1_table([_card(full_name="José O'Neil")], DECK)
        # stdlib html.escape emits hex entity &#x27; for the apostrophe (not decimal &#39;)
        assert "José O&#x27;Neil" in html_text
        # not over-escaped: the accented letter survives literally
        assert "José" in html_text


# --------------------------------------------------------------- G-ii read-back assert


class TestGiiReadBack:
    async def test_red1_entity_escaped_readback_raises(self) -> None:
        """G-ii-RED-1: read-back html_text contains &lt;table -> LOUD raise."""
        story = _Story("s1", html_text="&lt;body&gt;&lt;table&gt;...", text="")
        asana = _FakeAsana(_FakeStories(readback=story))
        with pytest.raises(ContactCardRenderError, match="entity-escaped"):
            await cs._assert_render_not_escaped("s1", compose_marker(DECK), asana)

    async def test_red2_missing_marker_readback_raises(self) -> None:
        """G-ii-RED-2: read-back html_text lacks the idempotency marker -> raise."""
        story = _Story("s1", html_text="<body><table>...</table></body>", text="")
        asana = _FakeAsana(_FakeStories(readback=story))
        with pytest.raises(ContactCardRenderError, match="marker"):
            await cs._assert_render_not_escaped("s1", compose_marker(DECK), asana)

    async def test_green1_live_table_with_marker_passes(self) -> None:
        marker = compose_marker(DECK)
        story = _Story("s1", html_text=f"<body><table>...</table>{marker}</body>", text="")
        asana = _FakeAsana(_FakeStories(readback=story))
        await cs._assert_render_not_escaped("s1", marker, asana)  # no raise

    async def test_posted_path_runs_readback_and_raises_loudly(self, monkeypatch) -> None:
        """The orchestrator's execute path runs G-ii and propagates the LOUD raise."""
        escaped = _Story("s1", html_text="&lt;table&gt; soup", text="")
        stories = _FakeStories(created=_Story("s1"), readback=escaped)
        asana = _FakeAsana(stories)
        with pytest.raises(ContactCardRenderError):
            await _run(asana, execute=True, cards=[_card()], monkeypatch=monkeypatch)
        assert len(stories.create_calls) == 1  # posted, then read-back caught it LOUD


# --------------------------------------------------------------------- G-iii egress


class TestGiiiEgress:
    async def test_red1_routing_address_refuses_no_post(self, monkeypatch) -> None:
        """G-iii-RED-1: a routing-domain email refuses BEFORE create_comment."""
        stories = _FakeStories(created=_Story("s1"))
        asana = _FakeAsana(stories)
        poison = _card(contact_email="abc123@appointments.contenteapp.com")
        with pytest.raises(ContactCardEgressRefused):
            await _run(asana, execute=True, cards=[poison], monkeypatch=monkeypatch)
        assert stories.create_calls == []  # NEVER posted

    async def test_red_canonical_uuid_routing_address_refuses(self, monkeypatch) -> None:
        uuid_addr = "0123456789abcdef0123456789abcdef0123"  # 36-hex canonical local-part
        stories = _FakeStories(created=_Story("s1"))
        asana = _FakeAsana(stories)
        poison = _card(contact_email=f"{uuid_addr}@appointments.contenteapp.com")
        with pytest.raises(ContactCardEgressRefused):
            await _run(asana, execute=True, cards=[poison], monkeypatch=monkeypatch)
        assert stories.create_calls == []

    async def test_green1_clean_email_posts(self, monkeypatch) -> None:
        marker = compose_marker(DECK)
        readback = _Story("s1", html_text=f"<table>{marker}", text="")
        stories = _FakeStories(created=_Story("s1"), readback=readback)
        asana = _FakeAsana(stories)
        result = await _run(
            asana,
            execute=True,
            cards=[_card(contact_email="jane@sandlake.com")],
            monkeypatch=monkeypatch,
        )
        assert result.outcome == "posted"
        assert len(stories.create_calls) == 1

    def test_egress_guard_refuses_foreign_url_host(self) -> None:
        """DECK_HOST pin: a non-decks.cntently.com URL in the composed text refuses."""
        with pytest.raises(ContactCardEgressRefused, match="URL host"):
            cs._egress_guard("see https://evil.example.com/x")

    def test_egress_guard_allows_deck_host_url(self) -> None:
        cs._egress_guard("see https://decks.cntently.com/deck/x")  # no raise


# ----------------------------------------------------------------------- G-iv length


class TestGivLengthCap:
    def test_red1_overflow_truncates_ends_on_closed_table_with_more(self) -> None:
        """G-iv-RED-1: many contacts over a small cap -> capped, closed </table>, +N more."""
        cards = [
            _card(full_name=f"Person {i}", contact_email=f"p{i}@x.com", rank=i + 1)
            for i in range(20)
        ]
        html_text, plain_text, dropped = compose_card(cards, DECK, max_len=1200)
        assert len(html_text) <= 1200
        assert dropped > 0
        assert html_text.count("</table>") == 1
        assert html_text.rstrip().endswith("</body>")
        assert "</table>" in html_text
        assert f"+{dropped} more" in html_text
        assert f"+{dropped} more" in plain_text

    def test_green1_within_cap_no_truncation(self) -> None:
        cards = [_card()]
        html_text, plain_text, dropped = compose_card(cards, DECK, max_len=32000)
        assert dropped == 0
        assert "more" not in html_text
        assert html_text == render_l1_table(cards, DECK)


# ----------------------------------------------------------------- G-v idempotency


class TestGvIdempotency:
    async def test_red1_second_run_same_slug_skips(self, monkeypatch) -> None:
        """G-v-RED-1: a story already carrying THIS deck's marker -> skipped_existing."""
        marker = compose_marker(DECK)
        existing = [_Story("old", text=f"prior comment {marker}")]
        stories = _FakeStories(existing=existing, created=_Story("s1"))
        asana = _FakeAsana(stories)
        result = await _run(asana, execute=True, cards=[_card()], monkeypatch=monkeypatch)
        assert result.outcome == "skipped_existing"
        assert result.story_gid == "old"
        assert stories.create_calls == []  # exactly zero posts on the repeat

    async def test_green1_different_slug_posts_afresh(self, monkeypatch) -> None:
        other = compose_marker("other-office")
        existing = [_Story("old", text=f"prior {other}")]
        marker = compose_marker(DECK)
        readback = _Story("s1", html_text=f"<table>{marker}", text="")
        stories = _FakeStories(existing=existing, created=_Story("s1"), readback=readback)
        asana = _FakeAsana(stories)
        result = await _run(asana, execute=True, cards=[_card()], monkeypatch=monkeypatch)
        assert result.outcome == "posted"
        assert len(stories.create_calls) == 1


# ------------------------------------------------------------------ G-vi mixed-plane


class TestGviFilter:
    def test_red1_null_email_null_role_excluded(self) -> None:
        keep = _card(contact_email="a@x.com", role=None)
        drop = _card(full_name="Ghost", contact_email=None, role=None)
        filtered = cs._dedup([c for c in [keep, drop] if cs._is_person_shaped(c)])
        assert keep in filtered and drop not in filtered

    def test_green1_email_set_role_null_included(self) -> None:
        c = _card(contact_email="a@x.com", role=None)
        assert cs._is_person_shaped(c) is True

    def test_dedup_first_occurrence_wins(self) -> None:
        a = _card(full_name="Dup", contact_email="d@x.com", rank=1)
        b = _card(full_name="Dup", contact_email="d@x.com", rank=2)
        assert cs._dedup([a, b]) == [a]

    async def test_supplement_garbage_with_email_included(self, monkeypatch) -> None:
        """G-vi-RED-garbage-with-email: a non-person row WITH an email is INCLUDED
        (person-shaped heuristic passes on email); its rank_reason is the human's
        signal to recognize a non-person row."""
        garbage = _card(
            full_name="Sales Process — X Team",
            nickname="",
            contact_email="team@clinic.com",
            role=None,
            rank_reason="has email on file",
        )
        marker = compose_marker(DECK)
        readback = _Story("s1", html_text=f"<table>{marker}", text="")
        stories = _FakeStories(created=_Story("s1"), readback=readback)
        asana = _FakeAsana(stories)
        result = await _run(asana, execute=True, cards=[garbage], monkeypatch=monkeypatch)
        assert result.outcome == "posted"
        assert result.cards[0].full_name == "Sales Process — X Team"
        assert result.cards[0].rank_reason  # non-empty signal for the picker

    async def test_supplement_real_person_null_null_is_loud_no_usable(self, monkeypatch) -> None:
        """G-vi-RED-real-person-null-null: the ONLY holder child is a real person with
        null email AND null position -> excluded by G-vi -> LOUD ``no_usable_contacts``
        (NOT silent ``no_contacts``), with a named reason and NO post."""
        real_but_bare = _card(
            full_name="Dr. Patel",
            nickname=None,
            contact_email=None,
            role=None,
            rank_reason="sole contact on file",
        )
        stories = _FakeStories(created=_Story("s1"))
        asana = _FakeAsana(stories)
        result = await _run(asana, execute=True, cards=[real_but_bare], monkeypatch=monkeypatch)
        assert result.outcome == "no_usable_contacts"
        assert result.no_usable_reason and "none carry contact_email" in result.no_usable_reason
        assert stories.create_calls == []  # nothing posted


# ------------------------------------------------------------- degrade-path outcomes


class TestDegradePaths:
    async def test_no_holder(self, monkeypatch) -> None:
        stories = _FakeStories()
        asana = _FakeAsana(stories)
        result = await _run(
            asana, execute=True, holder_found=False, cards=[], monkeypatch=monkeypatch
        )
        assert result.outcome == "no_holder"
        assert stories.create_calls == []

    async def test_no_contacts_distinct_from_no_usable(self, monkeypatch) -> None:
        """Holder found, ZERO subtasks -> ``no_contacts`` (distinct from no_usable)."""
        stories = _FakeStories()
        asana = _FakeAsana(stories)
        result = await _run(
            asana, execute=True, holder_found=True, cards=[], monkeypatch=monkeypatch
        )
        assert result.outcome == "no_contacts"
        assert result.no_usable_reason is None

    async def test_dry_run_default_composes_never_posts(self, monkeypatch) -> None:
        stories = _FakeStories()
        asana = _FakeAsana(stories)
        result = await _run(asana, execute=False, cards=[_card()], monkeypatch=monkeypatch)
        assert result.outcome == "dry_run"
        assert stories.create_calls == []
        assert result.comment_html and "<table>" in result.comment_html
        assert compose_marker(DECK) in result.comment_html


# ----------------------------------------------------------- traversal D1-D4 mechanics


class TestTraversal:
    async def test_resolve_ranked_cards_full_path(self) -> None:
        """D1/D3/D4 + get_gid_map correction: (phone,vertical) -> business -> holder ->
        ranked cards, via subtasks_async(...).collect(), detect_entity_type().entity_type,
        and _populate_children."""
        holder_task = Task(
            gid="holder-1",
            name="Sand Lake Contacts \U0001f9d1",
            memberships=[{"project": {"gid": "1201500116978260"}}],
        )
        decoy = Task(gid="unit-1", name="Business Units \U0001f50e", memberships=[])
        contact_task = Task(
            gid="c1",
            name="Dr. Ziyad Maali",
            custom_fields=[
                {"gid": "e", "name": "Contact Email", "text_value": "z@sandlake.com"},
                {"gid": "p", "name": "Position", "enum_value": {"name": "Owner"}},
            ],
        )

        class _Tasks:
            def __init__(self):
                self._map = {"biz-1": [decoy, holder_task], "holder-1": [contact_task]}

            def subtasks_async(self, gid, include_detection_fields=False):
                assert include_detection_fields is True  # D1
                return _Collectable(self._map[gid])

        class _Data:
            async def get_gid_map_async(self, pairs):
                # get_gid_map correction: returns dict[(phone,vertical) -> gid_str]
                p = pairs[0]
                return {(p.phone, p.vertical): "biz-1"}

        asana = types.SimpleNamespace(tasks=_Tasks(), stories=None)
        found, cards = await cs.resolve_ranked_cards(asana, _Data(), "+14073550608", "dentistry")
        assert found is True
        assert [c.full_name for c in cards] == ["Dr. Ziyad Maali"]
        assert cards[0].contact_email == "z@sandlake.com"
        assert cards[0].provenance is Provenance.ASANA

    async def test_resolve_no_business_is_no_holder(self) -> None:
        class _Data:
            async def get_gid_map_async(self, pairs):
                p = pairs[0]
                return {(p.phone, p.vertical): None}

        asana = types.SimpleNamespace(tasks=None, stories=None)
        found, cards = await cs.resolve_ranked_cards(asana, _Data(), "+14073550608", "dentistry")
        assert found is False and cards == []


# --------------------------------------------------------------------------- CLI


class TestCli:
    """main() builds an async closure and hands it to asyncio.run. Patching
    asyncio.run to close the (never-awaited) coroutine and return a canned result lets
    us assert the CLI print/exit surface without constructing live clients."""

    def test_dry_run_prints_composed_html_returns_0(self, monkeypatch, capsys) -> None:
        result = cs.ContactCardResult(
            outcome="dry_run",
            deck_slug=DECK,
            cards=[_card()],
            comment_html=render_l1_table([_card()], DECK),
            comment_text=render_plain_text([_card()], DECK),
        )

        def fake_run(coro):
            coro.close()
            return result

        monkeypatch.setattr(cs.asyncio, "run", fake_run)
        rc = cs.main(["PLAY-1", "--deck-slug", DECK])
        out = capsys.readouterr().out
        assert rc == 0
        assert "outcome=dry_run" in out
        assert "<table>" in out
        assert compose_marker(DECK) in out

    def test_no_usable_prints_loud_reason(self, monkeypatch, capsys) -> None:
        result = cs.ContactCardResult(
            outcome="no_usable_contacts",
            deck_slug=DECK,
            no_usable_reason="1 contact(s) found in holder; none carry contact_email or position",
        )
        monkeypatch.setattr(cs.asyncio, "run", lambda coro: (coro.close(), result)[1])
        rc = cs.main(["PLAY-1", "--deck-slug", DECK])
        out = capsys.readouterr().out
        assert rc == 0
        assert "no_usable_reason:" in out
        assert "none carry contact_email" in out

    def test_refusal_returns_2(self, monkeypatch, capsys) -> None:
        def boom(coro):
            coro.close()
            raise ContactCardEgressRefused("routing address")

        monkeypatch.setattr(cs.asyncio, "run", boom)
        rc = cs.main(["PLAY-1", "--deck-slug", DECK])
        err = capsys.readouterr().err
        assert rc == 2
        assert "REFUSED:" in err
