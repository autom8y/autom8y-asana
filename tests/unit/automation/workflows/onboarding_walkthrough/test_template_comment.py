"""Two-sided guard + poster matrix for the v3 tenant-matched rep-template comment.

Per TDD-rep-template-v3-tenant-match-2026-07-07.md §3 (guard teeth) + §4 (composition
surface) + §6 (exact golden). Design of record: rep-onboarding-deck-email-template-v3-
2026-07-07.md + ADR-contact-synthesis-card-on-play-2026-07-07 §13 (v3 Carrier
Ratification).

The load-bearing invariant is ``assert_template_tenant_match``: the crown-jewel guard
that lets ONLY this office's own routing address ride in the carrier email and refuses,
fail-closed, on any FOREIGN address or a malformed office guid. Two-sidedness is the
point (``non-interference-attestation-discipline``): the guard bites RED on a leak
(RED-1/1b/2b) AND on a bad anchor (RED-2), and passes GREEN on both the own-present
(GREEN-1) and the address-absent (GREEN-2) states — the SUBSET predicate is the unique
shape satisfying all six rows.

Every poster RED/dry-run/skip path carries the anti-theater invariant
``create_comment_async.assert_not_awaited()`` so a poster that silently posts on a
refusal/dry-run cannot pass green; the GREEN post path asserts it was awaited exactly
once. Fakes only (no live Asana), mirroring test_link_on_play / test_contact_synthesis.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough import template_comment as tc
from autom8_asana.automation.workflows.onboarding_walkthrough.contact_synthesis import (
    CONTACT_CARD_MARKER_PREFIX,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import (
    POSTER_MARKER_PREFIX,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.template_comment import (
    TEMPLATE_MARKER_PREFIX,
    TemplateCommentRefused,
    compose_marker,
    compose_template_comment,
    post_template_comment,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TemplateTenantMismatch,
    assert_template_tenant_match,
)

# --- Probe constants (TDD §3/§6; real Sand Lake target) ---

SAND_LAKE_GUID = "1b271a63-33ff-4135-a92d-f1ef0eeea062"
OWN = "1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com"
FOREIGN_GUID = "b167331c-536f-4996-9b2d-2f696f35f556"
FOREIGN = "b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com"
# Uppercase-hex foreign variant (RED-2b): CANONICAL_ROUTING_ADDR_RE is re.IGNORECASE,
# so it is harvested; lowercased at the boundary it is still != OWN -> refuse.
FOREIGN_UPPER = "B167331C-536F-4996-9B2D-2F696F35F556@appointments.contenteapp.com"

DECK_URL = "https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/"
SLUG = "207688021de88a6d7231e1d08ea77a85"
MARKER = "[autom8y:rep-template deck=207688021de88a6d7231e1d08ea77a85]"

TASK_GID = "1215823342887129"

# The EXACT v3 golden composed comment for Sand Lake (TDD §6). ``[RECIPIENT]`` stays a
# bracket (the human picks the receiver — P-NOVA: the system never picks); the clinic
# is a known fact so it is filled; the routing line + deck link are system-composed; the
# trailing marker is the idempotency key. Byte-for-byte — em-dash U+2014, arrow U+2192,
# ASCII apostrophes. V3-C grooming posts this verbatim.
GOLDEN_SAND_LAKE = (
    "Subject: Your Sand Lake Dental booking setup — a quick 5-minute walkthrough\n"
    "\n"
    "Hi [RECIPIENT],\n"
    "\n"
    "Thanks for getting Sand Lake Dental started. To bring your calendar integration "
    "live, here's a short personalized walkthrough — about five minutes, no technical "
    "setup on your end:\n"
    "\n"
    "→ https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/\n"
    "\n"
    "It covers the one forwarding step that connects your inbound leads to your "
    "calendar. For that step, forward your booking emails to your dedicated booking "
    "inbox:\n"
    "\n"
    "Your routing email is: 1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments."
    "contenteapp.com\n"
    "\n"
    "Once that's set, new booking requests flow straight into your scheduling, and "
    "we'll confirm it's live with a test booking.\n"
    "\n"
    "Any questions, just reply here.\n"
    "\n"
    "Best,\n"
    "Nova\n"
    "\n"
    "[autom8y:rep-template deck=207688021de88a6d7231e1d08ea77a85]"
)


# --- fake client builder (mirrors test_link_on_play._make_client) ---


def _make_client(*, stories=None, created_gid="NEW_STORY_GID", readback_text=None) -> MagicMock:
    """Fake AsanaClient: sync list -> async collect; async comment-create + read-back get."""
    client = MagicMock()
    client.stories.list_for_task_async = MagicMock(
        return_value=SimpleNamespace(collect=AsyncMock(return_value=list(stories or [])))
    )
    client.stories.create_comment_async = AsyncMock(return_value=SimpleNamespace(gid=created_gid))
    client.stories.get_async = AsyncMock(return_value=SimpleNamespace(text=readback_text))
    return client


# =========================================================================== the guard
# ``assert_template_tenant_match`` — the crown-jewel. Pure (no I/O); direct calls.


class TestTenantMatchGuard:
    def test_red1_foreign_present_with_own_refuses(self) -> None:
        """RED-1: OWN and a stale FOREIGN both ride in -> harvested-{own} = {foreign} != ∅
        -> REFUSE. The leak-by-containment crown-jewel: a second tenant's address is fatal."""
        text = f"Your routing email is: {OWN}\nstale hardcoded: {FOREIGN}"
        with pytest.raises(TemplateTenantMismatch, match="foreign"):
            assert_template_tenant_match(composed_text=text, office_guid=SAND_LAKE_GUID)

    def test_red1b_foreign_only_own_absent_refuses(self) -> None:
        """RED-1b: FOREIGN only (own absent) -> still REFUSE. Defeats an address SWAP:
        replacing own with a foreign address must not fail open just because own is gone."""
        text = f"forward your booking emails to {FOREIGN}"
        with pytest.raises(TemplateTenantMismatch, match="foreign"):
            assert_template_tenant_match(composed_text=text, office_guid=SAND_LAKE_GUID)

    def test_red2_malformed_guid_refuses_failclosed(self) -> None:
        """RED-2: a malformed office guid -> format_routing_address cannot compute own ->
        fail-closed refuse (the bad-anchor arm). A bad anchor can never yield a match."""
        text = f"Your routing email is: {OWN}"
        with pytest.raises(TemplateTenantMismatch, match="malformed office guid"):
            assert_template_tenant_match(composed_text=text, office_guid="not-a-uuid")

    def test_red2_malformed_guid_cause_is_valueerror(self) -> None:
        """RED-2 (provenance): the refusal wraps format_routing_address's ValueError
        (routing.py:98-108) as __cause__ — the guard is the single fail-closed surface,
        the ValueError is preserved for the incident breadcrumb."""
        with pytest.raises(TemplateTenantMismatch) as exc_info:
            assert_template_tenant_match(composed_text=OWN, office_guid="NOT-A-UUID")
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_red2b_case_variant_foreign_refuses(self) -> None:
        """RED-2b: an UPPERCASE-hex foreign address -> harvested via re.IGNORECASE,
        lowercased at the boundary -> still != own -> REFUSE. Never fails open on a case
        variant (mirrors tenant_binding.py:143-144)."""
        text = f"Your routing email is: {OWN}\nvariant: {FOREIGN_UPPER}"
        with pytest.raises(TemplateTenantMismatch, match="foreign"):
            assert_template_tenant_match(composed_text=text, office_guid=SAND_LAKE_GUID)

    def test_green1_own_only_passes(self) -> None:
        """GREEN-1: OWN present (even many times — display + inline) -> harvested = {own}
        -> harvested-{own} = ∅ -> PASS. Presence of own is the expected state."""
        text = f"To: {OWN}\nYour routing email is: {OWN} ({OWN})"
        assert_template_tenant_match(composed_text=text, office_guid=SAND_LAKE_GUID)

    def test_green2_no_address_passes(self) -> None:
        """GREEN-2: zero routing addresses (a valid re-send that omits the line) -> PASS.
        Presence is a SHOULD, not a MUST (spec §1 clause 2) — absence is permissible; only
        a FOREIGN address is fatal."""
        text = "Hi [RECIPIENT], here's your walkthrough link and a test-booking note."
        assert_template_tenant_match(composed_text=text, office_guid=SAND_LAKE_GUID)


# ==================================================================== compose_template
# ``compose_template_comment`` / ``compose_marker`` — pure composition.


class TestCompose:
    def test_cs1_routing_line_url_marker_and_guard_passes(self) -> None:
        """CS-1: compose injects the system-composed routing line (own), the deck URL, and
        the DISTINCT rep-template marker — and the composed text passes the guard (GREEN-1)."""
        text = compose_template_comment(office_guid=SAND_LAKE_GUID, deck_url=DECK_URL)
        assert f"Your routing email is: {OWN}" in text
        assert DECK_URL in text
        assert MARKER in text
        # the composed text is tenant-clean for THIS office (crown-jewel holds end-to-end)
        assert_template_tenant_match(composed_text=text, office_guid=SAND_LAKE_GUID)

    def test_compose_emits_exact_golden_sand_lake(self) -> None:
        """The composed Sand Lake comment is byte-for-byte the v3 golden (TDD §6) — the
        routing line system-composed, [RECIPIENT] a human bracket, clinic filled, marker
        appended. V3-C grooming posts this verbatim."""
        text = compose_template_comment(
            office_guid=SAND_LAKE_GUID, deck_url=DECK_URL, clinic="Sand Lake Dental"
        )
        assert text == GOLDEN_SAND_LAKE

    def test_compose_defaults_leave_clinic_and_recipient_brackets(self) -> None:
        """Defaults leave BOTH human-fills as brackets ([CLINIC], [RECIPIENT]); the system
        fills only the deck link + routing line (anti-fat-finger, spec §2)."""
        text = compose_template_comment(office_guid=SAND_LAKE_GUID, deck_url=DECK_URL)
        assert "[CLINIC]" in text
        assert "Hi [RECIPIENT]," in text
        assert f"Your routing email is: {OWN}" in text

    def test_compose_malformed_guid_raises_valueerror(self) -> None:
        """A malformed office guid cannot compose a routing line — format_routing_address
        raises ValueError (never a plausible-but-wrong address)."""
        with pytest.raises(ValueError, match="canonical lowercase UUID v4"):
            compose_template_comment(office_guid="not-a-uuid", deck_url=DECK_URL)

    def test_marker_is_slug_scoped_and_distinct_prefix(self) -> None:
        """The marker is slug-scoped and byte-exact; its prefix is DISTINCT from the
        link-on-play and contact-card prefixes so the three PLAY comments never collide."""
        assert compose_marker(SLUG) == MARKER
        assert compose_marker("A") != compose_marker("B")
        assert TEMPLATE_MARKER_PREFIX == "autom8y:rep-template"
        assert TEMPLATE_MARKER_PREFIX not in {POSTER_MARKER_PREFIX, CONTACT_CARD_MARKER_PREFIX}


# =========================================================================== the poster
# ``post_template_comment`` — dry-run default, ADD-only, guard upstream of the post.


class TestPoster:
    async def test_cs2_dry_run_default_composes_never_posts(self) -> None:
        """CS-2: execute=False (default) -> composes + reports would-post intent, NO
        create_comment (assert_not_awaited). The resolved office guid + composed text are
        carried for the operator's dry-run print."""
        client = _make_client(stories=[])
        result = await post_template_comment(
            client, task_gid=TASK_GID, deck_url=DECK_URL, office_guid=SAND_LAKE_GUID
        )
        assert result.outcome == "dry_run_would_post"
        assert result.story_gid is None
        assert result.office_guid == SAND_LAKE_GUID
        assert result.deck_slug == SLUG
        assert f"Your routing email is: {OWN}" in result.comment_text
        assert MARKER in result.comment_text
        client.stories.create_comment_async.assert_not_awaited()

    async def test_green_execute_posts_once_then_reads_back(self) -> None:
        """GREEN: valid target, no prior marker, execute -> posts once with the routing
        line + marker, then the read-back confirms the marker persisted."""
        client = _make_client(stories=[], readback_text=f"posted body\n{MARKER}")
        result = await post_template_comment(
            client, task_gid=TASK_GID, deck_url=DECK_URL, office_guid=SAND_LAKE_GUID, execute=True
        )
        assert result.outcome == "posted"
        assert result.story_gid == "NEW_STORY_GID"
        client.stories.create_comment_async.assert_awaited_once()
        _, kwargs = client.stories.create_comment_async.await_args
        assert kwargs["task"] == TASK_GID
        assert f"Your routing email is: {OWN}" in kwargs["text"]
        assert MARKER in kwargs["text"]
        client.stories.get_async.assert_awaited_once()

    async def test_cs3_idempotent_skip_no_second_post(self) -> None:
        """CS-3: a prior comment already carries THIS slug's rep-template marker -> skip,
        no second post (mirrors link_on_play idempotency)."""
        existing = SimpleNamespace(gid="EXISTING_STORY_GID", text=f"earlier note\n\n{MARKER}")
        client = _make_client(stories=[existing])
        result = await post_template_comment(
            client, task_gid=TASK_GID, deck_url=DECK_URL, office_guid=SAND_LAKE_GUID, execute=True
        )
        assert result.outcome == "skipped_existing"
        assert result.story_gid == "EXISTING_STORY_GID"
        client.stories.create_comment_async.assert_not_awaited()

    async def test_different_slug_marker_posts_afresh(self) -> None:
        """A prior marker for a DIFFERENT deck slug does not match -> this slug posts afresh."""
        other = SimpleNamespace(gid="OLD", text=compose_marker("0000000000000000000000000000abcd"))
        client = _make_client(stories=[other], readback_text=f"body {MARKER}")
        result = await post_template_comment(
            client, task_gid=TASK_GID, deck_url=DECK_URL, office_guid=SAND_LAKE_GUID, execute=True
        )
        assert result.outcome == "posted"
        client.stories.create_comment_async.assert_awaited_once()

    async def test_cs4_foreign_injection_refuses_upstream_of_post(self) -> None:
        """CS-4: a build/config drift injects a FOREIGN address into the composed body ->
        the step-4 guard fires BEFORE create_comment -> raise TemplateTenantMismatch, NO
        post. The guard is upstream of the mutation, exactly like link_on_play.py:225."""
        poisoned = f"Your routing email is: {OWN}\nstale: {FOREIGN}\n{MARKER}"
        client = _make_client(stories=[])
        with patch.object(tc, "compose_template_comment", return_value=poisoned):
            with pytest.raises(TemplateTenantMismatch, match="foreign"):
                await post_template_comment(
                    client,
                    task_gid=TASK_GID,
                    deck_url=DECK_URL,
                    office_guid=SAND_LAKE_GUID,
                    execute=True,
                )
        client.stories.create_comment_async.assert_not_awaited()

    async def test_poster_malformed_guid_refuses_no_post(self) -> None:
        """A malformed office guid at the poster boundary -> fail-closed as the guard's
        refusal type (TemplateTenantMismatch), NO post."""
        client = _make_client(stories=[])
        with pytest.raises(TemplateTenantMismatch, match="malformed office guid"):
            await post_template_comment(
                client,
                task_gid=TASK_GID,
                deck_url=DECK_URL,
                office_guid="not-a-uuid",
                execute=True,
            )
        client.stories.create_comment_async.assert_not_awaited()

    async def test_readback_absent_text_is_loud(self) -> None:
        """Read-back returns no text -> the post is unverifiable -> LOUD TemplateCommentRefused
        (fail-closed on absent read-back; mirrors the contact-card C-1 discipline). The post
        already happened, so the refusal surfaces AFTER the single create_comment."""
        client = _make_client(stories=[], readback_text=None)
        with pytest.raises(TemplateCommentRefused, match="read-back"):
            await post_template_comment(
                client,
                task_gid=TASK_GID,
                deck_url=DECK_URL,
                office_guid=SAND_LAKE_GUID,
                execute=True,
            )
        client.stories.create_comment_async.assert_awaited_once()

    async def test_bad_deck_host_refuses(self) -> None:
        """A non-DECK_HOST deck URL is refused at the host pin (reused deck_slug_from_url),
        before any compose or post."""
        from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import (
            LinkOnPlayRefused,
        )

        client = _make_client(stories=[])
        with pytest.raises(LinkOnPlayRefused, match="host"):
            await post_template_comment(
                client,
                task_gid=TASK_GID,
                deck_url="https://evil.example/207688021de88a6d7231e1d08ea77a85/",
                office_guid=SAND_LAKE_GUID,
                execute=True,
            )
        client.stories.create_comment_async.assert_not_awaited()


# ============================================================= FORK-GUID-SOURCE Option A
# office_guid sourced from the Business task's Company ID custom field, pure-Asana,
# reusing the proven contact_synthesis phone->Business bridge (never re-minted).


class TestOfficeGuidResolution:
    def test_company_id_from_task_reads_custom_field(self) -> None:
        """_company_id_from_task reads the 'Company ID' custom field's display_value
        (mirrors contact_synthesis._office_phone_from_task)."""
        task = SimpleNamespace(
            custom_fields=[
                {"name": "Office Phone", "display_value": "+14073550608"},
                {"name": "Company ID", "display_value": SAND_LAKE_GUID},
            ]
        )
        assert tc._company_id_from_task(task) == SAND_LAKE_GUID

    def test_company_id_absent_returns_none(self) -> None:
        task = SimpleNamespace(custom_fields=[{"name": "Office Phone", "display_value": "x"}])
        assert tc._company_id_from_task(task) is None

    async def test_office_guid_resolved_from_company_id_bridge(self) -> None:
        """office_guid=None -> resolve pure-Asana: PLAY -> office phone -> Business (proven
        bridge) -> Company ID custom field. The resolved guid composes the routing line."""
        business_task = SimpleNamespace(
            custom_fields=[{"name": "Company ID", "display_value": SAND_LAKE_GUID}]
        )
        client = _make_client(stories=[])
        client.tasks.get_async = AsyncMock(return_value=business_task)
        with (
            patch.object(tc, "_read_office_phone", new=AsyncMock(return_value="+14073550608")),
            patch.object(tc, "_business_gid_by_phone", new=AsyncMock(return_value="biz-1")),
        ):
            result = await post_template_comment(
                client, task_gid=TASK_GID, deck_url=DECK_URL, execute=False
            )
        assert result.office_guid == SAND_LAKE_GUID
        assert f"Your routing email is: {OWN}" in result.comment_text
        client.stories.create_comment_async.assert_not_awaited()

    async def test_no_office_phone_refuses_loudly(self) -> None:
        """No Office Phone on the PLAY -> cannot resolve the guid -> LOUD refuse (spec §2:
        escalate, never hand-type a routing address); no post."""
        client = _make_client(stories=[])
        with (
            patch.object(tc, "_read_office_phone", new=AsyncMock(return_value=None)),
            pytest.raises(TemplateCommentRefused, match="[Oo]ffice [Pp]hone"),
        ):
            await post_template_comment(client, task_gid=TASK_GID, deck_url=DECK_URL, execute=True)
        client.stories.create_comment_async.assert_not_awaited()

    async def test_no_company_id_on_business_refuses(self) -> None:
        """The Business task carries no Company ID -> cannot compose a tenant-matched
        routing address -> LOUD refuse; no post."""
        business_task = SimpleNamespace(custom_fields=[{"name": "Owner", "display_value": "x"}])
        client = _make_client(stories=[])
        client.tasks.get_async = AsyncMock(return_value=business_task)
        with (
            patch.object(tc, "_read_office_phone", new=AsyncMock(return_value="+14073550608")),
            patch.object(tc, "_business_gid_by_phone", new=AsyncMock(return_value="biz-1")),
            pytest.raises(TemplateCommentRefused, match="Company ID"),
        ):
            await post_template_comment(client, task_gid=TASK_GID, deck_url=DECK_URL, execute=True)
        client.stories.create_comment_async.assert_not_awaited()
