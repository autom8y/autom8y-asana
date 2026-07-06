"""Idempotent link-on-PLAY deck comment poster (Sand Lake onboarding, n=1).

Posts the live capability URL for a frozen onboarding deck onto a single Asana
``PLAY: Custom Calendar Integration`` task, idempotently and fail-closed. The
poster's ONLY write is a single ``create_comment`` (ADD-only): it never edits or
deletes an existing story, never sends anything to a client, never mints or
rotates a PAT.

Safety is layered and every layer fails closed:

* **Preflight** (§5) positively selects the target -- the task name must match the
  ``PLAY: Custom Calendar Integration`` convention AND the task must be a member of
  the Calendar-Integrations project in a section whose CANONICAL resolved gid is in
  the ACTIVE set (reusing ``resolve_section_gids`` -- the same primitive the batch
  uses -- so there is no cross-project name-collision risk). Any mismatch (wrong
  name, wrong project, non-ACTIVE section, or a resolution miss that empties the
  ACTIVE set) refuses -- the single-task poster never falls back to project-level
  like the batch does.
* **Egress guard** (§6) reuses the canonical routing-address oracle
  (``CANONICAL_ROUTING_ADDR_RE``): if the composed comment text carries any
  ``{uuid}@appointments.contenteapp.com`` routing address it refuses BEFORE posting.
  The only injection vector into the text is the deck URL; a routing address riding
  in via a malformed deck URL is caught here, the last line of defense.
* **Idempotency** (§7) keys a slug-scoped marker: a comment already carrying THIS
  deck's marker is skipped (returning the existing story gid); a marker for a
  DIFFERENT deck does not match, so a new deck posts afresh.

Default mode is dry-run (reads + composes + prints, never posts). ``--execute`` is
the sole mutating path. The dry-run print IS the "see the target before executing"
mechanism: the operator runs it bare, reads the resolved target + would-post text,
then re-runs with ``--execute``.

Auth is inherited the idiomatic repo way: ``main`` constructs a bare
``AsanaClient()`` (no ``token=``), which resolves auth via ``EnvAuthProvider`` ->
``settings.asana.pat``. Run inside the repo's configured environment (direnv /
secretspec) where ``settings.asana.pat`` and the settings production-URL guard are
already satisfied -- do NOT set offline stubs (this poster needs the live workspace).
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass
from urllib.parse import urlsplit

from autom8_asana.automation.workflows.onboarding_walkthrough import constants
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    CANONICAL_ROUTING_ADDR_RE,
)
from autom8_asana.automation.workflows.section_resolution import resolve_section_gids
from autom8_asana.client import AsanaClient

POSTER_MARKER_PREFIX = "autom8y:link-on-play"

# The ONLY host a deck URL may point at (N3 QA pre-merge condition). The URL must be
# https AND its netloc must equal DECK_HOST EXACTLY -- an exact netloc match refuses
# userinfo (user@host), an explicit port (host:port), and any foreign host in one
# predicate, so an attacker-supplied URL can never be composed into a posted comment.
DECK_HOST: str = "decks.cntently.com"

# POSITIVE selection of the PLAY convention "PLAY: Custom Calendar Integration — {clinic}"
# (personalization_gate.py:5). Prefix-anchored, case-sensitive (the internal
# nomenclature is uppercase PLAY). A near-miss like "Playa Vista Dental" does NOT
# match: the "PLAY:" separator + phrase is required, not the substring "Play".
PLAY_NAME_RE = re.compile(r"^\s*PLAY:\s*Custom Calendar Integration\b")


class LinkOnPlayRefused(RuntimeError):
    """Fail-closed refusal (preflight mismatch OR egress-guard match).

    When raised, the poster has NOT called ``create_comment``. The condition is
    non-transient: re-running reproduces it (a wrong name, a non-ACTIVE section, a
    routing address in the composed text). Callers must fail closed, not retry.
    """


@dataclass(frozen=True)
class LinkOnPlayResult:
    """The outcome of a poster run (composed text always carried for the operator).

    ``outcome`` is one of ``"posted"`` | ``"skipped_existing"`` |
    ``"dry_run_would_post"`` | ``"dry_run_would_skip"``. ``story_gid`` is the new
    gid on a post, the existing gid on a skip, and ``None`` for ``dry_run_would_post``.
    """

    outcome: str
    story_gid: str | None
    task_name: str
    section_name: str
    deck_slug: str
    comment_text: str


def deck_slug_from_url(deck_url: str) -> str:
    """Return the last non-empty path segment of a host-pinned https deck URL.

    Fail-closed host pin (N3 QA condition): the URL MUST be ``https`` AND its
    ``netloc`` MUST equal :data:`DECK_HOST` exactly, else refuse naming the
    offending host. The exact netloc match refuses userinfo (``user@host``), an
    explicit port (``host:port``), and any foreign host, so an attacker-supplied
    URL can never be composed. A slug-less URL (empty last path segment) refuses.
    This is the single URL-parsing chokepoint (``post_link_on_play`` step 1 and
    ``compose_comment_text`` both route through it), so the pin covers every path.
    """
    parts = urlsplit(deck_url)
    if parts.scheme != "https" or parts.netloc != DECK_HOST:
        raise LinkOnPlayRefused(
            f"deck-url host not allowed: scheme={parts.scheme!r} host={parts.netloc!r} "
            f"(require https://{DECK_HOST})"
        )
    path = parts.path.strip("/")
    slug = path.rsplit("/", 1)[-1] if path else ""
    if not slug:
        raise LinkOnPlayRefused(f"deck-url has no slug path segment: {deck_url!r}")
    return slug


def compose_marker(deck_slug: str) -> str:
    """The slug-scoped idempotency marker for this deck."""
    return f"[{POSTER_MARKER_PREFIX} deck={deck_slug}]"


# Rep-facing body (reps read this, the client never does): capability URL + a
# pointer to the approved email template + a trailing marker line. No mailbox, no
# guid, no routing domain -- egress-clean by construction (locked by test U2).
_BODY_TEMPLATE = (
    "Onboarding deck is live for this office. To send it to the client, use the "
    "approved rep email template (rep-onboarding-deck-email-template-2026-07-06.md; "
    "5 bracketed fields, no recipient inference) and paste this capability link:\n\n"
    "{deck_url}\n\n"
    "{marker}"
)


def compose_comment_text(deck_url: str) -> str:
    """Compose the exact rep-facing comment text for ``deck_url`` (marker appended)."""
    return _BODY_TEMPLATE.format(
        deck_url=deck_url,
        marker=compose_marker(deck_slug_from_url(deck_url)),
    )


async def _preflight(client: AsanaClient, task_gid: str) -> tuple[str, str]:
    """Fail-closed safety preflight (§5): assert PLAY name + ACTIVE membership.

    Positively selected (correct PLAY name AND an ACTIVE-section membership by
    CANONICAL resolved gid), never blanket. Returns ``(task_name, section_name)``;
    raises ``LinkOnPlayRefused`` on any mismatch.
    """
    task = await client.tasks.get_async(
        task_gid,
        opt_fields=[
            "name",
            "memberships.project.gid",
            "memberships.project.name",
            "memberships.section.gid",
            "memberships.section.name",
        ],
    )
    # (a) name convention.
    if not task.name or not PLAY_NAME_RE.search(task.name):
        raise LinkOnPlayRefused(
            f"task {task_gid} name is not a PLAY: Custom Calendar Integration task"
        )

    # (b) member of the Calendar-Integrations project in an ACTIVE section, matched
    # by the canonical section gid resolved WITHIN the project (never a loose name
    # match). An empty resolution (miss/failure) empties the ACTIVE set, so nothing
    # matches and we refuse -- the single-task poster does not fall back to project
    # level like the batch does.
    resolved = await resolve_section_gids(
        client.sections,
        constants.CALENDAR_INTEGRATIONS_PROJECT_GID,
        constants.ACTIVE_SECTION_NAMES,
    )
    active_gids = set(resolved.values())
    matched = next(
        (
            m
            for m in (task.memberships or [])
            if (m.get("project") or {}).get("gid") == constants.CALENDAR_INTEGRATIONS_PROJECT_GID
            and (m.get("section") or {}).get("gid") in active_gids
        ),
        None,
    )
    if matched is None:
        raise LinkOnPlayRefused(
            f"task {task_gid} is not in project "
            f"{constants.CALENDAR_INTEGRATIONS_PROJECT_GID} ACTIVE section"
        )
    section_name = (matched.get("section") or {}).get("name") or ""
    return task.name, section_name


async def post_link_on_play(
    client: AsanaClient,
    *,
    task_gid: str,
    deck_url: str,
    execute: bool = False,
) -> LinkOnPlayResult:
    """Post (or, by default, dry-run) the capability link onto a single PLAY task.

    Reads precede any write; the sole production mutation is the ``create_comment``
    at step 6, reached only when ``execute`` is True and no prior marker exists.
    """
    # 1. Slug (refuses on a slug-less URL).
    deck_slug = deck_slug_from_url(deck_url)

    # 2. Preflight (§5): PLAY name + ACTIVE membership, or refuse.
    task_name, section_name = await _preflight(client, task_gid)

    # 3. Compose the candidate comment text.
    text = compose_comment_text(deck_url)

    # 4. Egress guard (§6): refuse if a routing address rode into the composed text.
    if CANONICAL_ROUTING_ADDR_RE.search(text) is not None:
        raise LinkOnPlayRefused(
            "egress guard: composed comment text carries a canonical routing address"
        )

    # 5. Idempotency (§7): slug-scoped marker over the existing stories.
    marker = compose_marker(deck_slug)
    stories = await client.stories.list_for_task_async(
        task_gid, opt_fields=["text", "created_at"]
    ).collect()
    existing = next((s for s in stories if marker in (s.text or "")), None)

    if existing is not None:
        return LinkOnPlayResult(
            outcome="skipped_existing" if execute else "dry_run_would_skip",
            story_gid=existing.gid,
            task_name=task_name,
            section_name=section_name,
            deck_slug=deck_slug,
            comment_text=text,
        )

    # 6. Absent -> post (execute-only), else report the dry-run intent. No post on dry-run.
    if execute:
        story = await client.stories.create_comment_async(task=task_gid, text=text)
        return LinkOnPlayResult(
            outcome="posted",
            story_gid=story.gid,
            task_name=task_name,
            section_name=section_name,
            deck_slug=deck_slug,
            comment_text=text,
        )
    return LinkOnPlayResult(
        outcome="dry_run_would_post",
        story_gid=None,
        task_name=task_name,
        section_name=section_name,
        deck_slug=deck_slug,
        comment_text=text,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Default = dry-run; ``--execute`` is the only mutating mode.

    Exit codes: ``LinkOnPlayRefused`` -> print ``REFUSED: <reason>`` to stderr,
    return 2; a posted/skipped/dry-run outcome -> return 0; any other exception
    propagates and surfaces as a non-zero exit.
    """
    parser = argparse.ArgumentParser(
        prog=("python -m autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play"),
        description=(
            "Post a live onboarding-deck capability link onto a single Asana "
            "PLAY: Custom Calendar Integration task, idempotently and fail-closed. "
            "Default is dry-run (reads + composes + prints, never posts); --execute "
            "performs the single ADD-only comment."
        ),
    )
    parser.add_argument("--task-gid", required=True, help="Asana task GID of the PLAY task.")
    parser.add_argument(
        "--deck-url",
        required=True,
        help="Frozen deck capability URL (its last path segment is the slug).",
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

    async def _run() -> LinkOnPlayResult:
        async with AsanaClient() as client:
            return await post_link_on_play(
                client,
                task_gid=args.task_gid,
                deck_url=args.deck_url,
                execute=execute,
            )

    try:
        result = asyncio.run(_run())
    except LinkOnPlayRefused as refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2

    print(f"task={result.task_name!r} section={result.section_name!r} deck_slug={result.deck_slug}")
    print(f"outcome={result.outcome} story_gid={result.story_gid}")
    if result.outcome == "dry_run_would_post":
        print("--- comment_text (exactly what --execute would post) ---")
        print(result.comment_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
