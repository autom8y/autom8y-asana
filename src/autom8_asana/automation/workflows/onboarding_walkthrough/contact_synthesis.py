"""Ranked contact-card synthesis + idempotent poster for Calendar-Integration PLAYs.

When the Calendar-Integration PLAY workflow runs for an office, this module composes a
second Asana comment: a deterministically **ranked contact card** listing the office's
person-shaped contacts, escaped for safe ``html_text`` rendering, with a read-back
assertion that makes any rendering failure LOUD rather than silently wrong.

Design of record: ADR-contact-synthesis-card-on-play-2026-07-07 + TDD-contact-card-on-
play-phase1-2026-07-07. This module owns POLICY (filter, dedup, escape, render, egress,
idempotency, traversal); the pure ranking lives on ``ContactHolder.ranked_contacts()``
(entity layer) per the F-2 split ruling.

Six named guards (ADR §8):

* **G-i** escape every contact-sourced string BEFORE composition (``html.escape``). This
  is simultaneously the injection guard AND the ``<br>``-poison guard: a name ``Dr <br>
  Smith`` escapes to ``Dr &lt;br&gt; Smith``, which cannot trip Asana's silent-201
  whole-payload entity-escape.
* **G-ii** read-back render assert (the load-bearing loudness primitive): after POST,
  GET the story back and RAISE ``ContactCardRenderError`` if ``html_text`` came back
  entity-escaped (``&lt;table``) or the idempotency marker is absent. Asana returns 201
  and silently escapes the ENTIRE payload for an unsupported tag, so the renderer is
  verified by round-trip, NOT by HTTP status (A0 probe receipts).
* **G-iii** egress chain over the FINAL composed text: refuse to post if a canonical
  routing address, the routing-domain literal, or a non-``DECK_HOST`` URL rode in.
* **G-iv** length cap: overflow drops lowest-ranked rows + a ``+N more`` line, never a
  mid-tag truncation (which could birth an unclosed tag and trip the escape).
* **G-v** slug-scoped idempotency marker, DISTINCT from link-on-play's prefix.
* **G-vi** mixed-plane person-shaped filter (has email OR non-null role) + dedup. A
  holder with >=1 subtask where none pass the filter yields the LOUD
  ``no_usable_contacts`` outcome — never a silent ``no_contacts``.

Default mode is dry-run (reads + composes + prints, never posts). ``--execute`` is the
sole mutating path.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import re
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from autom8_asana.automation.workflows.onboarding_walkthrough import office_resolution
from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import DECK_HOST
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    CANONICAL_ROUTING_ADDR_RE,
)
from autom8_asana.client import AsanaClient
from autom8_asana.core.types import EntityType
from autom8_asana.models.business.contact import ContactCard, ContactHolder
from autom8_asana.models.business.detection import detect_entity_type

if TYPE_CHECKING:
    from autom8_asana.models.story import Story

__all__ = [
    "CONTACT_CARD_MARKER_PREFIX",
    "MAX_CONTACT_CARD_HTML_LENGTH",
    "ContactCardBusinessAmbiguous",
    "ContactCardEgressRefused",
    "ContactCardRenderError",
    "ContactCardResult",
    "compose_card",
    "main",
    "post_contact_card",
    "render_l1_table",
    "render_l3_list",
    "render_plain_text",
]

# DISTINCT from link-on-play's ``autom8y:link-on-play`` prefix so the contact-card
# comment and the link-on-play comment never collide on the same PLAY task (G-v).
CONTACT_CARD_MARKER_PREFIX = "autom8y:contact-card"

# G-iv length cap. UV-P (TDD §13): the exact Asana html_text comment ceiling is
# discharged by a sandbox bisect at N5 (a downstream station — a real post is required,
# which this build never makes). A conservative non-zero placeholder is committed here;
# the N5 sandbox bisect updates it as the first post-probe commit. The G-ii read-back is
# the runtime backstop regardless of this value.
MAX_CONTACT_CARD_HTML_LENGTH = 32000

# The routing-domain literal a card must NEVER carry. Full-domain-literal refusal (ADR
# §8 G-iii) catches a non-canonical (non-36-hex) address at this domain that the
# canonical UUID regex would miss.
_ROUTING_DOMAIN_LITERAL = "appointments.contenteapp.com"

# Extract any http(s) URL host for the DECK_HOST pin over composed card text.
_URL_RE = re.compile(r"https?://([^\s/\"'<>]+)", re.IGNORECASE)

# --- Business lookup (F-1 Call-1, AMENDED at B5 — Asana-native bridge) ---
# B5 falsified the ratified get_gid_map Call-1 in production: the data-service gid_map
# returns None for Sand Lake under EVERY vertical candidate (BusinessRecord
# default_vertical_key='none'), i.e. the dataset does not cover these offices. The
# proven-live path is the N0 pre-flight bridge (8/8 ACTIVE offices): search the workspace
# by the Office Phone custom field, then keep only results that are members of the
# "Businesses" project (the deterministic discriminator — Offer/Process/Commission rows
# also carry the phone). Org-stable gids, per the codebase idiom (cf.
# Contact.PRIMARY_PROJECT_GID, CALENDAR_INTEGRATIONS_PROJECT_GID).
_OFFICE_PHONE_FIELD_GID = "1181686411188348"  # "Office Phone" custom-field definition
_BUSINESSES_PROJECT_GID = "1200653012566782"  # "Businesses" project (N0-proven discriminator)


class ContactCardRenderError(RuntimeError):
    """Raised when the Asana read-back reveals entity-escaped ``html_text`` (G-ii).

    NOT transient: a poison tag re-escapes on every post. Callers must fail closed.
    """


class ContactCardEgressRefused(RuntimeError):
    """Raised when the composed card carries a routing address / foreign host (G-iii).

    NOT transient: the offending field reproduces on re-run. Callers must fail closed.
    """


class ContactCardBusinessAmbiguous(RuntimeError):
    """Raised when >1 Business task matches the office phone after the Businesses-project
    discriminator (F-1 bridge). Refuse loudly rather than pick a receiver silently — the
    QA multi-holder note applies: an ambiguous business must never post a card off a
    guessed match. NOT transient; callers must fail closed.
    """


@dataclass
class ContactCardResult:
    """Outcome of a poster run (mirrors ``LinkOnPlayResult``; TDD §15).

    ``comment_html`` / ``comment_text`` carry the composed card for the operator (the
    dry-run print surface) — additive to TDD §15 so the CLI can show exactly what
    ``--execute`` would post.
    """

    outcome: Literal[
        "posted",
        "skipped_existing",
        "no_holder",
        "no_contacts",
        "no_usable_contacts",
        "dry_run",
    ]
    story_gid: str | None = None
    cards: list[ContactCard] = field(default_factory=list)
    deck_slug: str = ""
    no_usable_reason: str | None = None
    comment_html: str | None = None
    comment_text: str | None = None


# --------------------------------------------------------------------------- G-i escape


def _esc(value: str | None) -> str:
    """Escape ``< > & " '`` for one field value (G-i).

    Applied to the FIELD VALUE at the last moment before template injection — never to
    the whole composed string. ``html.escape(quote=True)`` also encodes ``"`` and ``'``.
    """
    if value is None:
        return ""
    return html.escape(value, quote=True)


# ---------------------------------------------------------------- G-vi filter + dedup


def _is_person_shaped(card: ContactCard) -> bool:
    """G-vi person-shaped heuristic: has an email OR a non-null role (position)."""
    return card.contact_email is not None or card.role is not None


def _dedup(cards: list[ContactCard]) -> list[ContactCard]:
    """Dedup on ``(full_name, contact_email)``; first occurrence wins (rank preserved)."""
    seen: set[tuple[str, str | None]] = set()
    result: list[ContactCard] = []
    for card in cards:
        key = (card.full_name, card.contact_email)
        if key not in seen:
            seen.add(key)
            result.append(card)
    return result


# ------------------------------------------------------------------- G-v idempotency


def compose_marker(deck_slug: str) -> str:
    """The slug-scoped idempotency marker for this deck (G-v)."""
    return f"[{CONTACT_CARD_MARKER_PREFIX} deck={deck_slug}]"


def _marker_present_in_stories(stories: list[Story], deck_slug: str) -> bool:
    """True if any story already carries THIS deck's contact-card marker (G-v scan)."""
    marker = compose_marker(deck_slug)
    return any(marker in (s.html_text or "") or marker in (s.text or "") for s in stories)


# -------------------------------------------------------------------------- renderers


def render_l1_table(cards: list[ContactCard], deck_slug: str, *, more: int = 0) -> str:
    """L1 primary layout: real ``<table>`` (A0-proven tags only; ``\\n`` separators).

    NO ``<br>`` in any form (A0: ``<br>`` is the sole probed tag that trips the
    silent-201 whole-payload entity-escape). ``more`` > 0 appends a ``+N more`` line
    AFTER the closed ``</table>`` (G-iv), so a truncated card still ends on a closed tag.
    """
    marker = compose_marker(deck_slug)
    header = (
        "<tr><td><strong>#</strong></td>"
        "<td><strong>Name</strong></td>"
        "<td><strong>Nickname</strong></td>"
        "<td><strong>Email</strong></td>"
        "<td><strong>Role</strong></td></tr>"
    )
    rows = []
    for card in cards:
        rows.append(
            f"<tr><td>{card.rank}</td>"
            f"<td>{_esc(card.full_name)}</td>"
            f"<td>{_esc(card.nickname)}</td>"
            f"<td>{_esc(card.contact_email)}</td>"
            f"<td>{_esc(card.role)}</td></tr>"
            f'<tr><td></td><td colspan="4"><em>{_esc(card.rank_reason)}</em></td></tr>'
        )
    table_body = "\n".join(rows)
    more_line = f"\n+{more} more" if more > 0 else ""
    return f"<body>\n<table>\n{header}\n{table_body}\n</table>{more_line}\n{marker}\n</body>"


def render_l3_list(cards: list[ContactCard], deck_slug: str, *, more: int = 0) -> str:
    """L3 fallback layout: ``<ul><li>`` (used only if a future Asana change breaks tables)."""
    marker = compose_marker(deck_slug)
    items = [
        f"<li><strong>{card.rank}.</strong> {_esc(card.full_name)}"
        f" ({_esc(card.nickname)}) — {_esc(card.contact_email)}"
        f" — {_esc(card.role)} — <em>{_esc(card.rank_reason)}</em></li>"
        for card in cards
    ]
    more_line = f"\n<li>+{more} more</li>" if more > 0 else ""
    return "<body><ul>\n" + "\n".join(items) + f"{more_line}\n</ul>\n{marker}\n</body>"


def render_plain_text(cards: list[ContactCard], deck_slug: str, *, more: int = 0) -> str:
    """Plain-text fallback (ALWAYS populated — mirrors ``link_on_play`` convention)."""
    marker = compose_marker(deck_slug)
    lines = [
        f"{card.rank}. {card.full_name}"
        f" | {card.contact_email or 'no email'}"
        f" | {card.role or 'no role'}"
        f" | {card.rank_reason}"
        for card in cards
    ]
    if more > 0:
        lines.append(f"+{more} more")
    return "\n".join(lines) + f"\n{marker}"


# ------------------------------------------------------------------- G-iv length cap


def compose_card(
    cards: list[ContactCard],
    deck_slug: str,
    *,
    max_len: int = MAX_CONTACT_CARD_HTML_LENGTH,
) -> tuple[str, str, int]:
    """Compose (html, plain_text, dropped_count) under the G-iv length cap.

    Overflow drops the lowest-ranked rows (the tail — rows are already rank-sorted) and
    appends a ``+N more`` line, re-rendering until the html fits ``max_len`` or only the
    single top-ranked row remains. Never a mid-tag truncation.
    """
    kept = list(cards)
    dropped = 0
    while True:
        html_text = render_l1_table(kept, deck_slug, more=dropped)
        if len(html_text) <= max_len or len(kept) <= 1:
            plain_text = render_plain_text(kept, deck_slug, more=dropped)
            return html_text, plain_text, dropped
        kept = kept[:-1]
        dropped += 1


# ------------------------------------------------------------------- G-iii egress guard


def _egress_guard(*texts: str) -> None:
    """Refuse to post if any composed text carries an egress hazard (G-iii).

    Chain: canonical routing-address regex + routing-domain literal + DECK_HOST URL pin.
    Reuses ``CANONICAL_ROUTING_ADDR_RE`` (``tenant_binding``) and ``DECK_HOST``
    (``link_on_play``). Mirrors ``link_on_play`` step 4.
    """
    for text in texts:
        if CANONICAL_ROUTING_ADDR_RE.search(text) is not None:
            raise ContactCardEgressRefused(
                "composed contact card carries a canonical routing address; refusing post"
            )
        if _ROUTING_DOMAIN_LITERAL in text.lower():
            raise ContactCardEgressRefused(
                f"composed contact card carries the routing domain {_ROUTING_DOMAIN_LITERAL!r}; "
                "refusing post"
            )
        for host in _URL_RE.findall(text):
            if host.lower() != DECK_HOST:
                raise ContactCardEgressRefused(
                    f"composed contact card carries a non-{DECK_HOST} URL host {host!r}; "
                    "refusing post"
                )


# --------------------------------------------------------------- G-ii read-back assert


async def _assert_render_not_escaped(
    story_gid: str, expected_marker: str, asana_client: AsanaClient
) -> None:
    """Post -> GET story back -> assert ``html_text`` is NOT entity-escaped AND marker present.

    The opt_fields include is load-bearing (build errata D2): WITHOUT ``html_text`` in
    opt_fields Asana omits it and this guard would false-trip. Raises
    ``ContactCardRenderError`` on any failure (LOUD, never a warning-log; ADR §8 G-ii).

    Fail-closed on ABSENT html_text (C-1 / B3 D-1): a falsy read-back ``html_text``
    verifies NOTHING about the rendered card — passing off the plain ``text`` marker
    would be a vacuous guard (the silent-wrong-outcome class this primitive exists to
    make loud). Absent html_text is therefore a LOUD failure, checked FIRST.
    """
    story = await asana_client.stories.get_async(story_gid, opt_fields=["html_text", "text"])
    html_text = story.html_text
    if not html_text:
        raise ContactCardRenderError(
            "read-back returned no html_text — render unverifiable (Asana may have "
            "dropped it, or the comment posted as plain text only). The card render "
            f"cannot be confirmed; refusing to attest. story_gid={story_gid}"
        )
    if "&lt;table" in html_text or "&lt;ul" in html_text:
        raise ContactCardRenderError(
            "contact card html_text came back entity-escaped (contains '&lt;table' or "
            "'&lt;ul'): an unsupported tag tripped Asana's silent-201 whole-payload "
            f"entity-escape. story_gid={story_gid}"
        )
    if expected_marker not in html_text and expected_marker not in (story.text or ""):
        raise ContactCardRenderError(
            f"idempotency marker {expected_marker!r} absent from read-back. story_gid={story_gid}"
        )


# --------------------------------------------------------------------- ~3-call traversal


def _office_phone_from_task(task: Any) -> str | None:
    """Read the Office Phone from a PLAY task's custom fields (identity leg = phone only)."""
    for cf in getattr(task, "custom_fields", None) or []:
        cf = cf if isinstance(cf, dict) else {}
        if cf.get("name") == "Office Phone":
            return cf.get("display_value")
    return None


async def _read_office_phone(asana_client: AsanaClient, play_gid: str) -> str | None:
    """Fetch the PLAY task and extract its Office Phone custom field."""
    task = await asana_client.tasks.get_async(
        play_gid,
        opt_fields=["custom_fields.name", "custom_fields.display_value"],
    )
    return _office_phone_from_task(task)


async def _business_gid_by_phone(asana_client: AsanaClient, office_phone: str) -> str | None:
    """Resolve office_phone -> Business task_gid via the N0-proven Asana-native bridge.

    F-1 Call-1 (AMENDED at B5): search the workspace by the Office Phone custom field,
    then keep ONLY results that are members of the "Businesses" project (deterministic
    discriminator — Offer/Process/Commission rows also carry the phone). Returns the
    single Business gid, or ``None`` if no Business matches. Raises
    ``ContactCardBusinessAmbiguous`` if >1 match after the discriminator (never picks a
    receiver silently). This drops the DataServiceClient / M2M-creds dependency; the seam
    invariant is strengthened (Phase-1 is now pure-Asana).
    """
    workspace_gid = asana_client.default_workspace_gid
    if not workspace_gid:
        raise ContactCardBusinessAmbiguous(
            "no workspace configured for the Business lookup; cannot resolve office_phone "
            f"{office_phone!r} — refusing rather than guessing a workspace"
        )
    data = await asana_client._http.get(
        f"/workspaces/{workspace_gid}/tasks/search",
        params={
            f"custom_fields.{_OFFICE_PHONE_FIELD_GID}.value": office_phone,
            "opt_fields": "name,projects.gid",
        },
    )
    results = data.get("data", []) if isinstance(data, dict) else (data or [])
    matches = [
        t
        for t in results
        if any((p or {}).get("gid") == _BUSINESSES_PROJECT_GID for p in (t.get("projects") or []))
    ]
    if not matches:
        return None
    if len(matches) > 1:
        raise ContactCardBusinessAmbiguous(
            f"{len(matches)} Business tasks match office_phone={office_phone!r} after the "
            "Businesses-project discriminator; refusing to pick a receiver silently. "
            f"gids={[m.get('gid') for m in matches]}"
        )
    # Narrow the untyped-JSON access to str | None (mypy strict no-any-return).
    gid = matches[0].get("gid")
    return str(gid) if gid is not None else None


async def resolve_ranked_cards(
    asana_client: AsanaClient,
    office_phone: str | None = None,
    *,
    task_gid: str | None = None,
) -> tuple[bool, list[ContactCard]]:
    """The ~3-call live traversal (ADR §4 F-1, AMENDED at B5; build errata D1-D4).

    Returns ``(holder_found, ranked_cards)``:
      * ``(False, [])``  -> business/holder not locatable -> ``no_holder``
      * ``(True, [])``   -> holder found, zero contact subtasks -> ``no_contacts``
      * ``(True, cards)``-> ranked (unfiltered) cards for the caller to G-vi filter

    Call 1 resolves the owning Business (FORK-5, entity-resolution-primitive): the
    hierarchy walk is PRIMARY when ``task_gid`` is supplied (walk PLAY -> first
    ``BUSINESS_PROJECT`` ancestor -> its gid; immune to office-phone aliasing), and the
    ``office_phone`` bridge (``_business_gid_by_phone``; the ratified get_gid_map path was
    falsified live at B5) is the deprecation-window FALLBACK when the walk finds no Business
    ancestor OR no ``task_gid`` is supplied. Calls 2-3 traverse Business -> "Contacts"
    holder -> Contact children. ``Business.hydrate_async`` (10-20+ calls) is deliberately
    avoided. May raise ``ContactCardBusinessAmbiguous`` on a multi-Business phone match
    (fallback path) or ``BusinessResolutionAmbiguous`` on a multi-Business ancestor (walk).
    """
    business_gid: str | None = None
    if task_gid is not None:
        resolution = await office_resolution.resolve_business_gid(asana_client, task_gid=task_gid)
        business_gid = resolution.business_gid
    if business_gid is None and office_phone:
        business_gid = await _business_gid_by_phone(asana_client, office_phone)
    if not business_gid:
        return False, []

    business_subtasks = await asana_client.tasks.subtasks_async(
        business_gid, include_detection_fields=True
    ).collect()
    holder_task = next(
        (
            t
            for t in business_subtasks
            if detect_entity_type(t).entity_type == EntityType.CONTACT_HOLDER
        ),
        None,
    )
    if holder_task is None:
        return False, []

    # D4: hydrate the holder's typed children via the _populate_children precedent
    # (holder_factory.py:128-130) BEFORE ranked_contacts() is called.
    holder = ContactHolder.model_validate(holder_task, from_attributes=True)
    raw_contacts = await asana_client.tasks.subtasks_async(
        holder_task.gid, include_detection_fields=True
    ).collect()
    holder._populate_children(raw_contacts)
    return True, holder.ranked_contacts()


# ----------------------------------------------------------------------- orchestrator


async def post_contact_card(
    asana_client: AsanaClient,
    *,
    play_gid: str,
    deck_slug: str,
    office_phone: str | None = None,
    execute: bool = False,
) -> ContactCardResult:
    """Compose (and, with ``execute``, post) a ranked contact card onto a PLAY task.

    Reads precede any write; the sole mutation is the ``create_comment`` reached only
    when ``execute`` is True, no prior marker exists, and >=1 usable contact survives
    G-vi. Every guard fails closed. Phase-1 is pure-Asana (no DataServiceClient): the
    identity leg needs the office phone only (F-1 Call-1 amended at B5).
    """
    marker = compose_marker(deck_slug)

    # G-v idempotency: slug-scoped marker over existing stories.
    stories = await asana_client.stories.list_for_task_async(
        play_gid, opt_fields=["text", "html_text", "created_at"]
    ).collect()
    if _marker_present_in_stories(stories, deck_slug):
        existing = next(
            (s for s in stories if marker in (s.html_text or "") or marker in (s.text or "")),
            None,
        )
        return ContactCardResult(
            outcome="skipped_existing",
            story_gid=existing.gid if existing else None,
            deck_slug=deck_slug,
        )

    # Derive the office phone from the PLAY task (the deprecation-window fallback input)
    # when not supplied by the caller. With the hierarchy walk PRIMARY (threaded via
    # play_gid), office_phone is now a pure override / fallback -- a missing phone is no
    # longer terminal on its own, so we do not return no_holder here before the walk runs.
    if office_phone is None:
        office_phone = await _read_office_phone(asana_client, play_gid)

    holder_found, raw_cards = await resolve_ranked_cards(
        asana_client, office_phone, task_gid=play_gid
    )
    if not holder_found:
        return ContactCardResult(outcome="no_holder", deck_slug=deck_slug)
    if not raw_cards:
        return ContactCardResult(outcome="no_contacts", deck_slug=deck_slug)

    # G-vi person-shaped filter + dedup (applied AFTER ranking; TDD §5).
    usable = _dedup([c for c in raw_cards if _is_person_shaped(c)])
    if not usable:
        # >=1 holder subtask, none pass G-vi -> LOUD named-reason (CH-05), NOT silent
        # no_contacts. The false-exclusion of a real person is surfaced, not hidden.
        reason = (
            f"{len(raw_cards)} contact(s) found in holder; none carry contact_email "
            "or position (person-shaped filter excluded all)"
        )
        return ContactCardResult(
            outcome="no_usable_contacts", deck_slug=deck_slug, no_usable_reason=reason
        )

    # Compose under the G-iv length cap, then G-iii egress over the FINAL composed text.
    html_text, plain_text, _dropped = compose_card(usable, deck_slug)
    _egress_guard(html_text, plain_text)

    if not execute:
        return ContactCardResult(
            outcome="dry_run",
            deck_slug=deck_slug,
            cards=usable,
            comment_html=html_text,
            comment_text=plain_text,
        )

    story = await asana_client.stories.create_comment_async(
        task=play_gid, text=plain_text, html_text=html_text
    )
    # G-ii read-back render assert (LOUD): raises before returning success.
    await _assert_render_not_escaped(story.gid, marker, asana_client)
    return ContactCardResult(
        outcome="posted",
        story_gid=story.gid,
        deck_slug=deck_slug,
        cards=usable,
        comment_html=html_text,
        comment_text=plain_text,
    )


# -------------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Default = dry-run; ``--execute`` is the only mutating mode.

    Dry-run prints the resolved target + the full composed html (exactly what
    ``--execute`` would post) — the "see the target before executing" mechanism. Exit
    codes: an egress/render refusal -> ``REFUSED: <reason>`` to stderr, return 2;
    any resolved outcome -> return 0.

    retry-429-only-never-POST-5xx: the underlying ``AsanaClient`` retries HTTP 429
    (rate-limited) only; a POST 5xx is never retried (non-idempotent).
    """
    parser = argparse.ArgumentParser(
        prog=(
            "python -m autom8_asana.automation.workflows.onboarding_walkthrough.contact_synthesis"
        ),
        description=(
            "Post a ranked contact-card comment onto a single Asana PLAY task, "
            "idempotently and fail-closed. Default is dry-run (reads + composes + "
            "prints, never posts); --execute performs the single ADD-only comment."
        ),
    )
    parser.add_argument("play_gid", help="Asana task GID of the PLAY task.")
    parser.add_argument("--deck-slug", required=True, help="Deck slug (marker scope).")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Perform the single ADD-only comment (the only mutating mode).",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit no-op alias for the default (read + compose + print, never post).",
    )
    args = parser.parse_args(argv)
    execute = args.execute

    async def _run() -> ContactCardResult:
        async with AsanaClient() as asana_client:
            return await post_contact_card(
                asana_client,
                play_gid=args.play_gid,
                deck_slug=args.deck_slug,
                execute=execute,
            )

    try:
        result = asyncio.run(_run())
    except (
        ContactCardEgressRefused,
        ContactCardRenderError,
        ContactCardBusinessAmbiguous,
    ) as refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2

    print(f"play_gid={args.play_gid} deck_slug={result.deck_slug} outcome={result.outcome}")
    if result.outcome == "no_usable_contacts":
        # LOUD: the operator must see WHY no card posted (data-hygiene signal; CH-05).
        print(f"no_usable_reason: {result.no_usable_reason}")
    if result.story_gid:
        print(f"story_gid={result.story_gid}")
    if result.comment_html is not None:
        label = (
            "posted html_text" if execute else "comment_html (exactly what --execute would post)"
        )
        print(f"--- {label} ---")
        print(result.comment_html)
    return 0


if __name__ == "__main__":
    sys.exit(main())
