"""Tenant-matched v3 rep-template comment: composer + idempotent poster (Sand Lake, n=1).

The third PLAY-comment surface (sibling of ``link_on_play`` and ``contact_synthesis``).
Where the LINK and CARD comments carry NO routing address by design, the v3 carrier
email SHOULD carry the client's OWN routing address -- the one forwarding step the
walkthrough exists to teach (send-day operator ratification, 2026-07-07;
ADR-contact-synthesis-card-on-play-2026-07-07 §13). The blanket "no routing address"
refusal is REVERSED for this surface only, conditional on a hardening:

    the routing address that appears MUST be provably THIS office's own -- never
    another tenant's (the leak-by-containment crown-jewel) -- proven by a two-sided
    tenant-match guard, never by a checklist line alone.

The routing address is SYSTEM-COMPOSED from the office guid via
``format_routing_address`` (routing.py:75), never hand-typed by the rep (anti-fat-finger:
one transposed hex digit silently routes another clinic's bookings). The office guid is
the office's **Company ID** custom field on its Business task (FORK-GUID-SOURCE Option A,
pure-Asana), resolved via the proven ``contact_synthesis`` phone->Business bridge -- the
same Business the contact card already locates live (8/8 ACTIVE offices). Phase-1 stays
DataServiceClient-free.

Poster flow (every layer fails closed):

1. **Host pin** -- reuse ``deck_slug_from_url`` (link_on_play): the deck URL must be
   ``https`` at ``DECK_HOST`` exactly, else refuse.
2. **Guid resolve** (Option A) -- ALWAYS resolve the office guid from THIS task's Business
   Company ID via the phone->Business bridge (pure-Asana), so the routing address provably
   belongs to this PLAY's office. An explicit ``office_guid`` is a VERIFICATION, not a
   bypass: it must EQUAL the task-resolved guid or the poster refuses (``TaskOfficeMismatch``)
   -- a mis-paired ``(office_guid, task)`` is the cross-tenant leak.
3. **Compose** -- inject the system-composed routing line + a DISTINCT idempotency marker
   ``[autom8y:rep-template deck={slug}]`` (distinct from link-on-play's and
   contact-card's prefixes, so the three PLAY comments never collide).
4. **Guard** -- ``assert_template_tenant_match`` over the composed text (crown-jewel;
   step-4 position, exactly where ``link_on_play.py:225`` sits). A foreign address or a
   malformed guid refuses BEFORE any post.
5. **Idempotency** -- a comment already carrying THIS deck's marker is skipped.
6. **Post + read-back** -- ADD-only ``create_comment`` on ``--execute`` only, then a
   read-back asserts the marker persisted (fail-closed on absent text).

Default mode is dry-run (reads + composes + prints, never posts). ``--execute`` is the
sole mutating path; the dry-run print IS the "see the target before executing" mechanism.
The client SEND stays the operator's -- this poster only stages the PLAY template-comment.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from typing import Any

from autom8y_core.helpers.routing import format_routing_address

from autom8_asana.automation.workflows.onboarding_walkthrough.contact_synthesis import (
    ContactCardBusinessAmbiguous,
    _business_gid_by_phone,
    _read_office_phone,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import (
    LinkOnPlayRefused,
    deck_slug_from_url,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TaskOfficeMismatch,
    TemplateTenantMismatch,
    assert_template_tenant_match,
)
from autom8_asana.client import AsanaClient

__all__ = [
    "TEMPLATE_MARKER_PREFIX",
    "TemplateCommentRefused",
    "TemplateCommentResult",
    "compose_marker",
    "compose_template_comment",
    "main",
    "post_template_comment",
]

# DISTINCT from ``autom8y:link-on-play`` (link_on_play) and ``autom8y:contact-card``
# (contact_synthesis) so the three PLAY comments never collide on the same task (G-v).
TEMPLATE_MARKER_PREFIX = "autom8y:rep-template"

# The v3 carrier body (spec §3). ``{clinic}`` and ``{recipient}`` are the human's fills
# (default to brackets -- P-NOVA: the system never picks the receiver); ``{deck_url}`` and
# ``{routing_address}`` are SYSTEM-COMPOSED (anti-fat-finger); ``{marker}`` is the
# idempotency key (scopes the PLAY comment; not part of the email the human sends).
_BODY_TEMPLATE = (
    "Subject: Your {clinic} booking setup — a quick 5-minute walkthrough\n"
    "\n"
    "Hi {recipient},\n"
    "\n"
    "Thanks for getting {clinic} started. To bring your calendar integration live, "
    "here's a short personalized walkthrough — about five minutes, no technical setup "
    "on your end:\n"
    "\n"
    "→ {deck_url}\n"
    "\n"
    "For the step that connects your inbound booking notifications to the Contente "
    "calendar system, please forward your booking emails to your dedicated booking "
    "inbox: {routing_address}\n"
    "\n"
    "Once that's set, new booking requests flow straight into your scheduling, and "
    "we'll confirm it's live with a test booking.\n"
    "\n"
    "Any questions, just reply here.\n"
    "\n"
    "Best,\n"
    "Nova\n"
    "\n"
    "{marker}"
)


class TemplateCommentRefused(RuntimeError):
    """Fail-closed poster refusal: an office-guid resolution failure (no office phone /
    no Business / no Company ID) OR a read-back verification failure.

    Mirrors ``link_on_play.LinkOnPlayRefused`` -- the poster-level refusal type a CLI
    sibling idiomatically carries. The LOAD-BEARING tenant-match refusal is
    ``TemplateTenantMismatch`` (tenant_binding); this is the surrounding poster refusal.
    NON-transient: a missing field / unverifiable post reproduces on re-run; callers must
    fail closed, never retry.
    """


@dataclass(frozen=True)
class TemplateCommentResult:
    """The outcome of a poster run (composed text always carried for the operator).

    ``outcome`` is one of ``"posted"`` | ``"skipped_existing"`` |
    ``"dry_run_would_post"`` | ``"dry_run_would_skip"``. ``story_gid`` is the new gid on a
    post, the existing gid on a skip, and ``None`` for ``dry_run_would_post``.
    ``office_guid`` is THIS office's resolved guid (its Company ID) -- printed on the
    dry-run so the operator sees the tenant target before executing.
    """

    outcome: str
    story_gid: str | None
    deck_slug: str
    office_guid: str
    comment_text: str


def compose_marker(deck_slug: str) -> str:
    """The slug-scoped idempotency marker for this deck (distinct-prefix, G-v)."""
    return f"[{TEMPLATE_MARKER_PREFIX} deck={deck_slug}]"


def _reject_control_chars(field: str, value: str) -> None:
    """Refuse a caller-supplied field carrying a newline/CR (fail-closed composition).

    ``clinic`` and ``recipient`` compose into the Subject/greeting lines of the carrier
    email; a ``\\n``/``\\r`` corrupts the header/Subject line (QA surface 6) or smuggles a
    second header. These are human-typed names -- a newline is never valid -- so this refuses
    LOUD rather than silently stripping. Sits alongside ``compose``'s other fail-closed
    surfaces (``deck_slug_from_url`` -> ``LinkOnPlayRefused``; ``format_routing_address`` ->
    ``ValueError``); raises the module's poster-refusal type so the CLI reports it cleanly.
    """
    if "\n" in value or "\r" in value:
        raise TemplateCommentRefused(
            f"{field} must not contain a newline or carriage-return character "
            "(a control character in a caller-supplied name is never valid)."
        )


def _mask_guid(guid: str) -> str:
    """Mask an office guid to its first 8 chars (forensic breadcrumb; no full-guid spill).

    Mirrors ``tenant_binding._mask_addr``: enough to identify the implicated tenant against
    the DB during an incident, without spilling a full (wrong-)tenant guid into logs/errors.
    """
    return f"{guid[:8]}…" if guid else "<empty>"


def compose_template_comment(
    *,
    office_guid: str,
    deck_url: str,
    clinic: str = "[CLINIC]",
    recipient: str = "[RECIPIENT]",
) -> str:
    """Compose the exact v3 carrier body for ``office_guid`` + ``deck_url``.

    The inline routing address is SYSTEM-COMPOSED from the office guid via
    ``format_routing_address`` (routing.py:75) -- which RAISES ``ValueError`` on a
    malformed guid, so a plausible-but-wrong address can never be emitted. The deck URL is
    host-pinned via ``deck_slug_from_url`` (raises ``LinkOnPlayRefused`` on a foreign host
    or a slug-less URL). ``clinic`` and ``recipient`` default to their human-fill brackets
    and are rejected fail-closed (``TemplateCommentRefused``) if either carries a newline/CR
    (a control char would corrupt the Subject/header line -- QA surface 6).

    Args:
        office_guid: this office's guid (its Company ID). Canonical lowercase UUID v4.
        deck_url: the hosted ``https://decks.cntently.com/<slug>/`` capability URL.
        clinic: the clinic/business name (subject + greeting); default ``"[CLINIC]"``.
        recipient: the receiver's name; default ``"[RECIPIENT]"`` (the human picks it).

    Returns:
        The composed carrier-email text with the trailing idempotency marker.
    """
    _reject_control_chars("clinic", clinic)
    _reject_control_chars("recipient", recipient)
    deck_slug = deck_slug_from_url(deck_url)
    routing_address = format_routing_address(office_guid)
    return _BODY_TEMPLATE.format(
        clinic=clinic,
        recipient=recipient,
        deck_url=deck_url,
        routing_address=routing_address,
        marker=compose_marker(deck_slug),
    )


def _company_id_from_task(task: Any) -> str | None:
    """Read the Company ID from a Business task's custom fields (FORK-GUID-SOURCE Option A).

    Mirrors ``contact_synthesis._office_phone_from_task``: the office guid is the
    ``Company ID`` custom field's display value (``business.py:263`` ``company_id =
    TextField()``, ``source="cf:Company ID"``; the office guid per ``offer.py:123-130``).
    """
    for cf in getattr(task, "custom_fields", None) or []:
        cf = cf if isinstance(cf, dict) else {}
        if cf.get("name") == "Company ID":
            company_id = cf.get("display_value")
            return str(company_id) if company_id is not None else None
    return None


async def _resolve_office_guid(asana_client: AsanaClient, *, task_gid: str) -> str:
    """Resolve the office guid pure-Asana from the Business Company ID (Option A).

    PLAY -> Office Phone custom field -> Business task (the proven ``contact_synthesis``
    phone->Business bridge, reused not re-minted) -> Company ID custom field. Every miss is
    a LOUD refusal (spec §2: a missing routing line means escalate, never hand-type).
    """
    office_phone = await _read_office_phone(asana_client, task_gid)
    if not office_phone:
        raise TemplateCommentRefused(
            f"no Office Phone on PLAY task {task_gid}: cannot resolve the office guid. "
            "Escalate (spec §2) — never hand-type a routing address."
        )
    business_gid = await _business_gid_by_phone(asana_client, office_phone)
    if not business_gid:
        raise TemplateCommentRefused(
            f"no Business task matches the office phone for PLAY {task_gid}: cannot read a "
            "Company ID to compose the routing address."
        )
    business = await asana_client.tasks.get_async(
        business_gid,
        opt_fields=["custom_fields.name", "custom_fields.display_value"],
    )
    company_id = _company_id_from_task(business)
    if not company_id:
        raise TemplateCommentRefused(
            f"Business {business_gid} carries no Company ID custom field: cannot compose a "
            "tenant-matched routing address (spec §7 step 1)."
        )
    return company_id


async def _assert_marker_present(
    asana_client: AsanaClient, story_gid: str, expected_marker: str
) -> None:
    """Read the posted comment back and assert the marker persisted (loudness primitive).

    Fail-closed on ABSENT text (mirrors the contact-card C-1 discipline): a falsy
    read-back verifies NOTHING about the posted comment, so it is a LOUD failure rather
    than a vacuous pass. The comment is plain text (no html), so the check is the marker's
    presence in ``text``, not an entity-escape check.
    """
    story = await asana_client.stories.get_async(story_gid, opt_fields=["text"])
    text = story.text
    if not text:
        raise TemplateCommentRefused(
            "read-back returned no text — the posted comment is unverifiable; refusing to "
            f"attest the template-comment is live. story_gid={story_gid}"
        )
    if expected_marker not in text:
        raise TemplateCommentRefused(
            f"idempotency marker {expected_marker!r} absent from read-back; the comment did "
            f"not persist as composed. story_gid={story_gid}"
        )


async def post_template_comment(
    asana_client: AsanaClient,
    *,
    task_gid: str,
    deck_url: str,
    office_guid: str | None = None,
    clinic: str = "[CLINIC]",
    execute: bool = False,
) -> TemplateCommentResult:
    """Post (or, by default, dry-run) the tenant-matched v3 template comment onto a PLAY.

    Reads precede any write; the sole production mutation is the ``create_comment`` at
    step 6, reached only when ``execute`` is True, no prior marker exists, and the guard
    passed. Phase-1 is pure-Asana: the office guid is ALWAYS resolved from THIS task's
    Business Company ID (Option A) so the routing address provably belongs to this PLAY's
    office. An explicitly-supplied ``office_guid`` is a VERIFICATION, not a bypass -- it must
    equal the task-resolved guid or the poster refuses fail-closed with
    :class:`TaskOfficeMismatch` (a mis-paired ``(office_guid, task_gid)`` is the cross-tenant
    leak). Every guard fails closed.
    """
    # 1. Host pin + slug (reuses deck_slug_from_url; refuses a foreign host / slug-less URL).
    deck_slug = deck_slug_from_url(deck_url)

    # 2. Resolve the office guid FROM THE TASK (FORK-GUID-SOURCE Option A, pure-Asana). This
    #    runs ALWAYS: the routing address must provably belong to THIS PLAY's own office, so
    #    the guid is bound to the task, never trusted from a caller argument. When an explicit
    #    ``office_guid`` is ALSO supplied it is a VERIFICATION, never a bypass -- it MUST equal
    #    the task-resolved guid or we refuse fail-closed. (The prior explicit-guid short-circuit
    #    let a mis-paired ``(office_guid, task_gid)`` in a batch loop post one office's routing
    #    address onto ANOTHER office's PLAY -- the cross-tenant leak. Binding to the task closes
    #    it: the resolve-from-task path is unchanged; the explicit path can now only VERIFY.)
    task_office_guid = await _resolve_office_guid(asana_client, task_gid=task_gid)
    if office_guid is not None and office_guid != task_office_guid:
        raise TaskOfficeMismatch(
            f"office_guid does not belong to PLAY {task_gid}: supplied {_mask_guid(office_guid)} "
            f"but the task resolves to {_mask_guid(task_office_guid)}. Refusing fail-closed — "
            "posting this address would tell the client to forward bookings into another "
            "tenant's inbox."
        )
    office_guid = task_office_guid

    # 3. Compose the carrier body (system-composes the routing line).
    try:
        text = compose_template_comment(office_guid=office_guid, deck_url=deck_url, clinic=clinic)
    except ValueError as exc:
        # Bad-anchor arm at the poster boundary: a malformed office guid can never yield a
        # tenant-matched send. Surface as the guard's refusal type.
        raise TemplateTenantMismatch(
            f"cannot compose carrier email: malformed office guid ({exc})"
        ) from exc

    # 4. GUARD (crown-jewel, step-4 position — exactly where link_on_play.py:225 sits). The
    #    guard re-derives own from office_guid and harvests the composed text; it does NOT
    #    trust compose. A foreign address here refuses BEFORE any post.
    assert_template_tenant_match(composed_text=text, office_guid=office_guid)

    # 5. Idempotency (slug-scoped marker over existing stories).
    marker = compose_marker(deck_slug)
    stories = await asana_client.stories.list_for_task_async(
        task_gid, opt_fields=["text", "created_at"]
    ).collect()
    existing = next((s for s in stories if marker in (s.text or "")), None)
    if existing is not None:
        return TemplateCommentResult(
            outcome="skipped_existing" if execute else "dry_run_would_skip",
            story_gid=existing.gid,
            deck_slug=deck_slug,
            office_guid=office_guid,
            comment_text=text,
        )

    # 6. Absent marker -> post (execute-only) then read-back; else report the dry-run intent.
    if execute:
        story = await asana_client.stories.create_comment_async(task=task_gid, text=text)
        await _assert_marker_present(asana_client, story.gid, marker)
        return TemplateCommentResult(
            outcome="posted",
            story_gid=story.gid,
            deck_slug=deck_slug,
            office_guid=office_guid,
            comment_text=text,
        )
    return TemplateCommentResult(
        outcome="dry_run_would_post",
        story_gid=None,
        deck_slug=deck_slug,
        office_guid=office_guid,
        comment_text=text,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Default = dry-run; ``--execute`` is the only mutating mode.

    Dry-run prints the resolved office guid + the full composed comment (exactly what
    ``--execute`` would post) -- the "see the target before executing" mechanism. Exit
    codes: any fail-closed refusal -> ``REFUSED: <reason>`` to stderr, return 2; a
    resolved outcome -> return 0.
    """
    parser = argparse.ArgumentParser(
        prog=(
            "python -m autom8_asana.automation.workflows.onboarding_walkthrough.template_comment"
        ),
        description=(
            "Post a tenant-matched v3 rep-template comment onto a single Asana PLAY task, "
            "idempotently and fail-closed. Default is dry-run (reads + composes + prints, "
            "never posts); --execute performs the single ADD-only comment. The client SEND "
            "stays the operator's."
        ),
    )
    parser.add_argument("--task-gid", required=True, help="Asana task GID of the PLAY task.")
    parser.add_argument(
        "--deck-url",
        required=True,
        help="Frozen deck capability URL (its last path segment is the slug).",
    )
    parser.add_argument(
        "--office-guid",
        default=None,
        help=(
            "Office guid (Company ID). If omitted, resolved from the Business task's "
            "Company ID via the office-phone bridge (FORK-GUID-SOURCE Option A, pure-Asana)."
        ),
    )
    parser.add_argument(
        "--clinic",
        default="[CLINIC]",
        help="Clinic/business name for the subject + greeting (defaults to the [CLINIC] bracket).",
    )
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

    async def _run() -> TemplateCommentResult:
        async with AsanaClient() as asana_client:
            return await post_template_comment(
                asana_client,
                task_gid=args.task_gid,
                deck_url=args.deck_url,
                office_guid=args.office_guid,
                clinic=args.clinic,
                execute=execute,
            )

    try:
        result = asyncio.run(_run())
    except (
        TemplateTenantMismatch,
        TemplateCommentRefused,
        LinkOnPlayRefused,
        ContactCardBusinessAmbiguous,
    ) as refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2

    print(
        f"task_gid={args.task_gid} office_guid={result.office_guid} "
        f"deck_slug={result.deck_slug} outcome={result.outcome}"
    )
    if result.story_gid:
        print(f"story_gid={result.story_gid}")
    if result.outcome == "dry_run_would_post":
        print("--- comment_text (exactly what --execute would post) ---")
        print(result.comment_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
