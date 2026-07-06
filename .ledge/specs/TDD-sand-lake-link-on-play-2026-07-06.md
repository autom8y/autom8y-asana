---
type: spec
artifact_type: micro-tdd
status: draft
initiative_slug: sand-lake-link-on-play-e2e
station: N1-architect
authored_by: architect
authored_on: 2026-07-06
target_repo: autom8y-asana
target_branch_base: origin/main@eff75887
schema_version: 1
---

# MICRO-TDD — Sand Lake link-on-PLAY comment poster

> **Grandeur anchor.** The trust-first telos sends its first client deck today. This
> module posts the live capability URL onto Sand Lake Dental's real Asana PLAY,
> idempotently and fail-closed. The design is proven ONLY by two-sided teeth (a RED
> input the poster REFUSES) + a live read-back receipt — never by a green suite alone.
> The client SEND stays the operator's. The poster only ADDS a comment; it NEVER
> edits or deletes any story, NEVER sends anything to a client, NEVER mints/rotates a PAT.

## §0 Scope fence (bind these)

- **RUNG = n=1.** This designs the single-task comment poster for ONE office (Sand Lake).
- **Batch is OUT of scope** (§8 is a one-sentence seam only — `authored`/watch-registered, do NOT build).
- **Reserved levers (design around, NEVER invoke):** the real client SEND; `ASANA_PAT` mint/rotation;
  editing/deleting any existing human comment. The poster's only write is `create_comment` (ADD-only).
- **Two-way door.** Everything here is additive (one new module + one new test file). No schema, no
  existing-file edits, no infra. Fully reversible by deleting two files.

## §1 System context — home + entrypoint

**Module home (idiomatic — sits beside `tenant_binding.py` / `personalization_gate.py` / `constants.py`):**

```
src/autom8_asana/automation/workflows/onboarding_walkthrough/link_on_play.py
```

**CLI entrypoint (matches the repo's `python -m` + argparse + `asyncio.run` convention — see
`src/autom8_asana/metrics/__main__.py`; no `pyproject [project.scripts]` edit required):**

```
python -m autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play \
    --task-gid 1215823342887129 \
    --deck-url https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/ \
    [--execute]
```

Default (no `--execute`) = **dry-run** (reads + composes + prints, NEVER posts). `--execute` opts into the single ADD.

**Auth is inherited the idiomatic repo way.** The entrypoint constructs a bare `AsanaClient()` (no `token=`),
which resolves auth via `EnvAuthProvider` → `settings.asana.pat` (`client.py:132` → `_defaults/auth.py:57`).
`ASANA_PAT` is NOT in the plain shell env — the operator runs this inside the repo's configured environment
(direnv/secretspec) where `settings.asana.pat` resolves and the settings production-URL guard
(`settings.py:966`, needs `AUTOM8Y_DATA_URL`) is already satisfied. **Do NOT set offline stubs** (unlike
`autom8_query_cli.py`, which is an OFFLINE tool) — this poster needs the live workspace.

## §2 Public API (implement verbatim)

```python
from __future__ import annotations
import argparse, asyncio, re, sys
from dataclasses import dataclass
from urllib.parse import urlsplit

from autom8_asana.client import AsanaClient
from autom8_asana.automation.workflows.onboarding_walkthrough import constants
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    CANONICAL_ROUTING_ADDR_RE,
)
from autom8_asana.automation.workflows.section_resolution import resolve_section_gids

POSTER_MARKER_PREFIX = "autom8y:link-on-play"

# POSITIVE selection of the PLAY convention "PLAY: Custom Calendar Integration — {clinic}"
# (personalization_gate.py:5). Prefix-anchored, case-sensitive (internal nomenclature is
# uppercase PLAY). Near-miss "Playa Vista Dental" does NOT match (no "PLAY:" + phrase).
PLAY_NAME_RE = re.compile(r"^\s*PLAY:\s*Custom Calendar Integration\b")


class LinkOnPlayRefused(RuntimeError):
    """Fail-closed refusal (preflight mismatch OR egress-guard match). When raised,
    the poster has NOT called create_comment. Non-transient: re-running reproduces it."""


@dataclass(frozen=True)
class LinkOnPlayResult:
    outcome: str          # "posted" | "skipped_existing" | "dry_run_would_post" | "dry_run_would_skip"
    story_gid: str | None # posted: new gid; skipped: existing gid; would_post: None
    task_name: str
    section_name: str
    deck_slug: str
    comment_text: str     # the composed candidate text (what was / would be posted)


def deck_slug_from_url(deck_url: str) -> str:
    """Last non-empty path segment. Raises LinkOnPlayRefused on a slug-less URL."""
    path = urlsplit(deck_url).path.strip("/")
    slug = path.rsplit("/", 1)[-1] if path else ""
    if not slug:
        raise LinkOnPlayRefused(f"deck-url has no slug path segment: {deck_url!r}")
    return slug


def compose_marker(deck_slug: str) -> str:
    return f"[{POSTER_MARKER_PREFIX} deck={deck_slug}]"


def compose_comment_text(deck_url: str) -> str: ...   # exact body in §3

async def post_link_on_play(
    client: AsanaClient,
    *,
    task_gid: str,
    deck_url: str,
    execute: bool = False,   # default OFF => dry-run (safe default)
) -> LinkOnPlayResult: ...    # control flow in §4

def main(argv: list[str] | None = None) -> int: ...   # §1 CLI, exit codes in §4.1

if __name__ == "__main__":
    sys.exit(main())
```

`client: AsanaClient` is a **parameter** (dependency injection) so tests pass a fake and `main()` passes the
real `async with AsanaClient() as client:`.

## §3 Marker + rep-facing comment text (exact)

**Marker string (templated on the deck slug — slug-scoped so a NEW deck posts afresh, SAME deck skips):**

```
[autom8y:link-on-play deck=207688021de88a6d7231e1d08ea77a85]
```

i.e. `f"[{POSTER_MARKER_PREFIX} deck={slug}]"`. The slug `207688021de88a6d7231e1d08ea77a85` is a 32-hex deck
token (WS-GUARD'd), **distinct from any mailbox routing guid** — it has no `@appointments.contenteapp.com`
suffix, so it cannot match `CANONICAL_ROUTING_ADDR_RE` (which requires `[0-9a-f-]{36}@appointments.contenteapp.com`,
tenant_binding.py:66-69).

**Exact composed comment text** (ASCII-clean; rep-facing — reps read this, the client never does; no mailbox,
no guid, no routing domain):

```
Onboarding deck is live for this office. To send it to the client, use the approved rep email template (rep-onboarding-deck-email-template-2026-07-06.md; 5 bracketed fields, no recipient inference) and paste this capability link:

https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/

[autom8y:link-on-play deck=207688021de88a6d7231e1d08ea77a85]
```

`compose_comment_text(deck_url)` builds it as:

```python
_BODY_TEMPLATE = (
    "Onboarding deck is live for this office. To send it to the client, use the "
    "approved rep email template (rep-onboarding-deck-email-template-2026-07-06.md; "
    "5 bracketed fields, no recipient inference) and paste this capability link:\n\n"
    "{deck_url}\n\n"
    "{marker}"
)
def compose_comment_text(deck_url: str) -> str:
    return _BODY_TEMPLATE.format(deck_url=deck_url, marker=compose_marker(deck_slug_from_url(deck_url)))
```

## §4 Control flow — `post_link_on_play` (exact order)

1. `deck_slug = deck_slug_from_url(deck_url)`  → refuse on slug-less URL.
2. **Preflight (§5)** — read the task, assert PLAY name + ACTIVE membership. Raises `LinkOnPlayRefused` on
   mismatch. Yields `task_name`, `section_name`.
3. `text = compose_comment_text(deck_url)`.
4. **Egress guard (§6)** — `CANONICAL_ROUTING_ADDR_RE.search(text)` must be `None`; else refuse.
5. **Idempotency (§7)** — read stories; find any whose `.text` contains the marker.
   - present → `execute`: return `skipped_existing` (story_gid = existing.gid);
              dry-run: return `dry_run_would_skip` (story_gid = existing.gid).
6. absent →
   - `execute`: `story = await client.stories.create_comment_async(task=task_gid, text=text)`; return
     `posted` (story_gid = story.gid).
   - dry-run: return `dry_run_would_post` (story_gid = None). **No post.**

Reads before any write. The single write (step 6, execute-only) is the sole production mutation.

### §4.1 `main()` — printing + exit codes

- Parse `--task-gid` (required), `--deck-url` (required), and a mutually-exclusive `{--execute, --dry-run}`
  group; **default = dry-run** when neither is given (`--dry-run` accepted as an explicit no-op alias for the
  default). `execute = args.execute`.
- `async with AsanaClient() as client:` → `await post_link_on_play(...)`.
- Print (stdout, `print` is T201-allowed in entrypoints per pyproject:280-285): the resolved target
  `task=<name> section=<section> deck_slug=<slug>`, the `outcome`, and `story_gid`; in `dry_run_would_post`
  also print `comment_text` so the operator SEES exactly what `--execute` would post.
- Exit codes: `LinkOnPlayRefused` → print `REFUSED: <reason>` to stderr, **return 2**; `posted` /
  `skipped_existing` / `dry_run_*` → return 0; any other exception surfaces as a non-zero exit.

The dry-run default IS the "see the target before executing" mechanism: the operator runs it bare, reads the
target + would-post text, then re-runs with `--execute`.

## §5 Safety preflight (load-bearing — discharges the premise N0 could not verify from-shell)

Positively-selected (correct PLAY **and** ACTIVE), never blanket (G-DENOM).

```python
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
# (a) name convention
if not task.name or not PLAY_NAME_RE.search(task.name):
    raise LinkOnPlayRefused(f"task {task_gid} name is not a PLAY: Custom Calendar Integration task")

# (b) member of Calendar-Integrations project in an ACTIVE section (by CANONICAL resolved gid)
resolved = await resolve_section_gids(
    client.sections,
    constants.CALENDAR_INTEGRATIONS_PROJECT_GID,   # "1209442849265632" (constants.py:76)
    constants.ACTIVE_SECTION_NAMES,                # frozenset({"ACTIVE"}) (constants.py:85)
)
active_gids = set(resolved.values())
matched = next(
    (
        m for m in (task.memberships or [])
        if (m.get("project") or {}).get("gid") == constants.CALENDAR_INTEGRATIONS_PROJECT_GID
        and (m.get("section") or {}).get("gid") in active_gids
    ),
    None,
)
if matched is None:
    raise LinkOnPlayRefused(
        f"task {task_gid} is not in project {constants.CALENDAR_INTEGRATIONS_PROJECT_GID} ACTIVE section"
    )
section_name = (matched.get("section") or {}).get("name") or ""
```

Section identity is the **canonical gid resolved within the project** (reusing `resolve_section_gids`,
section_resolution.py:19 — the same primitive the batch uses), not a loose name match — no cross-project
name-collision risk. Empty `resolved` (resolution miss/failure) → `active_gids` empty → no match → **refuse**
(fail-closed; the single-task poster does NOT fall back to project-level like the batch does).

## §6 Egress guard (reuse — do NOT reimplement)

```python
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import CANONICAL_ROUTING_ADDR_RE
if CANONICAL_ROUTING_ADDR_RE.search(text) is not None:   # tenant_binding.py:66
    raise LinkOnPlayRefused("egress guard: composed comment text carries a canonical routing address")
```

Fail-closed. The only injection vector into `text` is `deck_url`; a `deck_url` carrying a
`{uuid}@appointments.contenteapp.com` rides into the composed text and is caught here BEFORE the post. This is
the last line of defense; the marker/URL are guid-free by construction (§3).

## §7 Idempotency semantics (exact predicate)

```python
marker = compose_marker(deck_slug)
stories = await client.stories.list_for_task_async(task_gid, opt_fields=["text", "created_at"]).collect()
existing = next((s for s in stories if marker in (s.text or "")), None)
```

`list_for_task_async` returns `PageIterator[Story]` (stories.py:210); `.collect()` (models/common.py:160)
materializes the list. `Story.text` is `str | None` (story.py:41) — the `or ""` guards None. Predicate =
`marker in story.text`. Marker is slug-scoped, so a comment for a DIFFERENT deck (different slug) does NOT
match → posts afresh; the SAME deck's marker matches → skip, returning `existing.gid` (Story.gid,
base.py:47).

## §8 Batch-forward seam (design ONLY — do NOT build; watch-registered)

A future ACTIVE-section batch would resolve the ACTIVE section gids once via
`resolve_section_gids(client.sections, CALENDAR_INTEGRATIONS_PROJECT_GID, ACTIVE_SECTION_NAMES)`, enumerate
each task in those sections (the `workflow.py:400` `tasks.list_async(section=...)` pattern), and call
`post_link_on_play(client, task_gid=<each>, deck_url=<per-office deck>, execute=...)` per office — the
single-task poster IS the batch's inner call, so N2 builds it with that clean seam and nothing more.

## §9 Two-sided teeth (N2 implements failing-first, then passing)

Test file: `tests/unit/automation/workflows/test_link_on_play.py` (mirror the `AsyncMock`/`MagicMock` fake-client
style of `tests/unit/automation/workflows/test_onboarding_walkthrough.py`).

**Fake shape (no live Asana):**
- `client = MagicMock()`;
  `client.tasks.get_async = AsyncMock(return_value=<fake_task>)` where fake_task is a `SimpleNamespace(name=..., memberships=[...])`;
  `client.stories.create_comment_async = AsyncMock(return_value=SimpleNamespace(gid="NEW_STORY_GID"))`;
  `client.stories.list_for_task_async = MagicMock(return_value=SimpleNamespace(collect=AsyncMock(return_value=[<fake stories>])))`.
- Patch `resolve_section_gids` at the link_on_play module path with `AsyncMock(return_value={"active": "SEC_ACTIVE"})`.
- GREEN fake_task membership: `[{"project": {"gid": "1209442849265632"}, "section": {"gid": "SEC_ACTIVE", "name": "ACTIVE"}}]`,
  name `"PLAY: Custom Calendar Integration — Sand Lake Dental"`.
- **Anti-theater invariant (every RED + every dry-run test):** `client.stories.create_comment_async.assert_not_awaited()`.

### GREEN
- **G1 fresh post** — valid target, stories `[]`, `execute=True` → `outcome=="posted"`, `story_gid=="NEW_STORY_GID"`;
  `create_comment_async.assert_awaited_once()` and its kwargs are `task=<task_gid>, text=<composed>` where the
  text contains the deck URL AND the marker.
- **G2 idempotent skip** — same target, stories contain one whose `.text` holds the marker for THIS slug,
  `execute=True` → `outcome=="skipped_existing"`, `story_gid==<existing gid>`; `create_comment_async.assert_not_awaited()`.
- **G3 new deck posts afresh** — stories contain a marker for a DIFFERENT slug (`deck=OLDSLUG…`), new deck_url,
  `execute=True` → `outcome=="posted"` (this-slug marker absent); proves slug-scoping.
- **G4 dry-run default never posts** — valid target, stories `[]`, `execute=False` → `outcome=="dry_run_would_post"`,
  `story_gid is None`; `create_comment_async.assert_not_awaited()`; `result.comment_text` contains URL + marker.

### RED (must REFUSE — assert `pytest.raises(LinkOnPlayRefused)` AND `create_comment_async.assert_not_awaited()`)
- **R1 egress guard (mailbox-bearing text)** — `deck_url` carrying a canonical routing address
  (e.g. append `b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com`); valid task; the composed
  text matches `CANONICAL_ROUTING_ADDR_RE` → refuse. (Real refusal: the guard inspects the composed bytes.)
- **R2 wrong task / not ACTIVE** — valid PLAY name but membership is a different project OR a section gid not in
  the resolved ACTIVE set → refuse.
- **R3 name not PLAY convention** — `task.name == "Playa Vista Dental"` (near-miss) or `"Weekly Sync"`, valid
  membership → refuse (proves `PLAY:` + phrase requirement, not a substring of "Playa").

### Unit (pure, cheap — lock the invariants)
- **U1 marker slug-scoping** — `compose_marker("A") != compose_marker("B")`;
  `compose_marker("207688021de88a6d7231e1d08ea77a85") == "[autom8y:link-on-play deck=207688021de88a6d7231e1d08ea77a85]"`.
- **U2 legit text is egress-clean** — `CANONICAL_ROUTING_ADDR_RE.search(compose_comment_text(REAL_DECK_URL)) is None`
  (catches a future template edit that introduces a routing address).
- **U3 slug extraction** — `deck_slug_from_url("https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/") == "207688021de88a6d7231e1d08ea77a85"`;
  slug-less URL raises `LinkOnPlayRefused`.

## §10 Reused-symbol provenance (G-PROVE — every symbol file:line, HEAD-verified)

| Symbol | Signature / value | Anchor |
|---|---|---|
| `StoriesClient.create_comment_async` | `(*, task: str, text: str) -> Story` | stories.py:301 (impl); usage init_actions.py:105 |
| `StoriesClient.list_for_task_async` | `(task_gid, *, opt_fields, limit) -> PageIterator[Story]` | stories.py:210 |
| `PageIterator.collect` | `() -> list[T]` (async) | models/common.py:160 |
| `TasksClient.get_async` | `(task_gid, *, raw=False, opt_fields) -> Task` | tasks.py:132 |
| `Task.name` / `Task.memberships` | `str \| None` / `list[dict] \| None` | task.py:51 / task.py:116 |
| `Story.text` / `Story.gid` | `str \| None` / `str` | story.py:41 / base.py:47 |
| `CANONICAL_ROUTING_ADDR_RE` | `[0-9a-f-]{36}@appointments.contenteapp.com` (IGNORECASE) | tenant_binding.py:66 |
| `resolve_section_gids` | `(sections_client, project_gid, target_names) -> dict[str,str]` | section_resolution.py:19 |
| `constants.CALENDAR_INTEGRATIONS_PROJECT_GID` | `"1209442849265632"` | constants.py:76 |
| `constants.ACTIVE_SECTION_NAMES` | `frozenset({"ACTIVE"})` | constants.py:85 |
| PLAY convention | `"PLAY: Custom Calendar Integration — {clinic}"` | personalization_gate.py:5 |
| `AsanaClient()` default auth | `EnvAuthProvider` → `settings.asana.pat` | client.py:132 / _defaults/auth.py:57 |
| `client.tasks` / `.sections` / `.stories` | accessors | client.py:332 / 376 / 578 |
| batch seam pattern | `resolve_section_gids` + `list_async(section=...)` | workflow.py:378-410 |
| CLI convention | argparse + `asyncio.run`; `main()->int` + `sys.exit(main())` | metrics/__main__.py; autom8_query_cli.py |

## §11 Reversibility & risk

- **Two-way door.** One new module + one new test file. Delete-to-revert. No edits to existing code, schema, or infra.
- **Blast radius = 1 comment on 1 task.** ADD-only; never edits/deletes a human comment.
- **Failure modes are fail-closed:** slug-less URL, non-PLAY name, non-ACTIVE membership, routing-address in text
  → refuse (exit 2), no post. Network/auth errors → non-zero exit, no partial write.
- **Risk R-1 (settings guard at import):** a bare-shell `python -m …` can trip the settings production-URL guard
  (settings.py:966) if `AUTOM8Y_DATA_URL` is unset. Mitigation: run inside the repo's configured env (where
  `settings.asana.pat` also resolves). Documented in §1; not a code change.

## §12 Handoff checklist (N2 done-bar)

- [ ] `link_on_play.py` created at §1 path; all §2 signatures exact.
- [ ] Marker + comment text byte-match §3; `compose_comment_text` egress-clean (U2).
- [ ] Preflight (§5) positively-selects PLAY + ACTIVE-by-resolved-gid; refuses fail-closed.
- [ ] Egress guard (§6) reuses `CANONICAL_ROUTING_ADDR_RE` (import, not reimpl).
- [ ] Idempotency (§7) predicate is `marker in story.text`, slug-scoped.
- [ ] Tests: G1–G4 + R1–R3 + U1–U3 pass; every RED/dry-run asserts `create_comment_async.assert_not_awaited()`.
- [ ] `--dry-run` is the default; `--execute` is the only path that calls `create_comment`.
- [ ] Live read-back receipt (operator/QA at N-later): after one `--execute` on task `1215823342887129`, the
      marker is present exactly once; a second `--execute` returns `skipped_existing`. (Client SEND stays operator's.)
