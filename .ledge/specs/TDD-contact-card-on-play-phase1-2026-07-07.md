---
type: spec
status: draft
date: 2026-07-07
initiative: client-onboarding-delivery
slug: contact-synthesis-card-on-play
phase: 1 (Asana-only; no employees endpoint dependency)
rung: authored (design altitude only)
origin_main_sha: 5604789f0699d81fbca2461a55f02134bbf4852a
adr_of_record: ADR-contact-synthesis-card-on-play-2026-07-07.md
out_of_scope: [Phase-2 employees merge, GET /employees/by-company endpoint, Intercom seam]
---

# TDD — Contact Card on PLAY, Phase-1 (Asana-only)

Implementable-verbatim for the 10x-dev build sprint. Every design claim traces to a
file:line receipt from A2/A3 upstream artifacts or the ADR. No production code authored
here; target repos unmodified. G-RUNG: everything = `authored`.

---

## 0. Build Goal (one sentence)

When the Calendar Integration PLAY workflow runs for an office, post a second Asana
comment containing a **ranked contact card** — a deterministically ordered list of the
office's person-shaped contacts, escaped for safe html_text rendering, with a read-back
assertion that makes any rendering failure loud rather than silently wrong.

A0 probe receipts (durable): A0-pv-probes-report-2026-07-07.md. [CH-03]

---

## 1. Module Homes

| Module | Path | Relationship to #201 |
|--------|------|----------------------|
| `ContactHolder.ranked_contacts()` | `src/autom8_asana/models/business/contact.py` | New pure method on existing `ContactHolder` class (`:206-236`). Zero new imports on the model. |
| `contact_synthesis.py` | `src/autom8_asana/automation/workflows/onboarding_walkthrough/contact_synthesis.py` | New module, beside `link_on_play.py` at the same directory path. Owns filter/dedup/card assembly/render/egress. |
| Test: entity method | `tests/unit/models/business/test_contact_synthesis_ranker.py` (suggested) | Pure function — no stubs required |
| Test: workflow module | `tests/unit/automation/workflows/onboarding_walkthrough/test_contact_synthesis.py` (suggested) | Stubs `subtasks_async`, `get_gid_map_async`, `create_comment_async`, `get_story_async` |

**Constraint**: `ContactHolder.ranked_contacts()` MUST have zero imports outside
entity internals. It is a pure ordering over `self.children`. If it imports any client
or SDK — the build is wrong. Refuse drift. (AP-F, ADR §10.)

---

## 2. The ~3-Call Traversal Recipe

Entry state at PLAY-comment build time (from B1 in `workflow.py:561-568`):
- `office_phone` (E.164 string)
- `record.guid` == `company_id` (already resolved from B1)
- `vertical` (from business record)

### Call sequence

```python
# Call 1 — map phone+vertical to Business task_gid (1 POST to data service)
gid_map = await data_client.get_gid_map_async([(office_phone, vertical)])
#   data_service.py:264,283-311
business_task_gid = gid_map[(office_phone, vertical)].task_gid

# Call 2 — fetch Business subtasks to locate "Contacts 🧑" holder
business_subtasks = await asana_client.subtasks_async(business_task_gid)
#   business.py:609
contacts_holder = next(
    (t for t in business_subtasks if detect_entity_type(t) == EntityType.CONTACT_HOLDER),
    None
)
# 0-contact graceful-degrade path:
if contacts_holder is None:
    return ContactCardResult(outcome="no_holder", contacts=[])

# Call 3 — fetch holder children (the Contact rows)
raw_contacts = await asana_client.subtasks_async(
    contacts_holder.gid, include_detection_fields=True
)
#   business.py:698-707 _fetch_holder_children_async pattern
```

At Phase-1 volume (one PLAY comment per human-gated send): 1 data-svc POST + 2 Asana
GETs = 3 calls total. 94% of offices have exactly ONE contact (A0-pv-probes-report-2026-07-07.md
§UV-P-1) → custom-field hydration ≤ 1 extra call worst-case.

**Do NOT call `Business.hydrate_async`** (`business.py:588-654`) — that fetches all 7
holders + recursive Unit/Offer/Process holders (10-20+ calls). Use the targeted path
above only.

---

## 3. ContactCard Dataclass

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Provenance(str, Enum):
    ASANA = "asana"
    EMPLOYEES = "employees"          # Phase-2 only
    CORROBORATED = "corroborated"    # Phase-2 only

@dataclass
class ContactCard:
    full_name: str                   # Contact.full_name contact.py:134-141
    nickname: Optional[str]          # Contact.nickname :89; fallback preferred_name :196-203
    contact_email: Optional[str]     # Contact.contact_email :82
    role: Optional[str]              # Contact.position :97 (43% present, A0)
    provenance: Provenance           # always ASANA at Phase-1
    rank: int                        # 1-based
    rank_reason: str                 # MANDATORY; rendered as <em>; required even at n=1
```

Phase-1: `provenance` is always `Provenance.ASANA`. Phase-2 activates EMPLOYEES and
CORROBORATED tiers by adding the employees traversal in `ContactSynthesis` only —
the `ContactCard` dataclass shape is unchanged.

---

## 4. Ranker Tiers and rank_reason Strings

Live in `ContactHolder.ranked_contacts()`. Pure function over `self.children`.

```python
def ranked_contacts(self) -> list[ContactCard]:
    """
    Pure deterministic ordering over self.children.
    No I/O. No external data. No rendering.
    Extends ContactHolder.owner (contact.py:223-236) — same bounded scope.
    """
    POSITION_WEIGHT: dict[str, int] = {
        "owner": 5, "ceo": 5, "founder": 5, "president": 4,
        "principal": 4, "manager": 3, "director": 3,
        # extend as Position enum evolves; absent key → 0
    }

    def _sort_key(c: Contact) -> tuple:
        return (
            -int(c.is_owner),                          # Tier 1: is_owner DESC
            -POSITION_WEIGHT.get(c.position or "", 0), # Tier 2: position-weight DESC
            -int(c.contact_email is not None),         # Tier 3: has-email DESC
            0,                                         # Tier 4: corroborated (Phase-2; 0 at Phase-1)
            c.full_name or "",                         # Tier 5: alpha ASC
        )

    def _rank_reason(c: Contact) -> str:
        if c.is_owner:
            return f"owner/{c.position}" if c.position else "owner"
        if c.position:
            return c.position
        if c.contact_email:
            return "has email on file"
        return "sole contact on file"  # n=1 case (94% of offices, A0)

    sorted_children = sorted(self.children, key=_sort_key)
    return [
        ContactCard(
            full_name=c.full_name or "",
            nickname=c.nickname or c.preferred_name,
            contact_email=c.contact_email,
            role=c.position,
            provenance=Provenance.ASANA,
            rank=i + 1,
            rank_reason=_rank_reason(c),
        )
        for i, c in enumerate(sorted_children)
    ]
```

---

## 5. Person-Shaped Filter and Dedup (ContactSynthesis — NOT on entity)

The filter and dedup live in `contact_synthesis.py`, applied AFTER calling
`holder.ranked_contacts()`. This is policy; it does not belong on the entity (ADR §F-2
grounds; `tenant_binding.py:29-34` idiom).

```python
def _is_person_shaped(card: ContactCard) -> bool:
    """G-vi: has email OR non-null role (position). A0: email 99%, role 43%."""
    return card.contact_email is not None or card.role is not None

def _dedup(cards: list[ContactCard]) -> list[ContactCard]:
    """Dedup on (full_name, contact_email). First occurrence wins (rank preserved)."""
    seen: set[tuple] = set()
    result = []
    for card in cards:
        key = (card.full_name, card.contact_email)
        if key not in seen:
            seen.add(key)
            result.append(card)
    return result

# In the synthesis entrypoint:
raw_cards = holder.ranked_contacts()
filtered = [c for c in raw_cards if _is_person_shaped(c)]
cards = _dedup(filtered)
```

---

## 6. `<table>` Card Template and Escaping Rule

### Escaping rule (G-i)

Escape `< > & " '` for every ContactCard field before composition. Use
`html.escape(value, quote=True)` (stdlib). Apply at the last moment before injection
into the template string — escape the FIELD VALUE, not the whole composed string.

```python
import html

def _esc(value: str | None) -> str:
    if value is None:
        return ""
    return html.escape(value, quote=True)
```

**Critical**: a contact named `Dr <br> Smith` escapes to `Dr &lt;br&gt; Smith`.
The escaped form CANNOT trip the `<br>` silent-201 whole-payload entity-escape.
Escaping is simultaneously the injection guard AND the `<br>`-poison guard (A3 §F-4.4 G-i).

### L1 template (primary — A0-proven tags only; `\n` separator, never `<br>`)

```python
MARKER_PREFIX = "autom8y:contact-card"

def _render_l1_table(cards: list[ContactCard], deck_slug: str) -> str:
    marker = f"[{MARKER_PREFIX} deck={deck_slug}]"
    rows = []
    for card in cards:
        rows.append(
            f"<tr><td>{card.rank}</td>"
            f"<td>{_esc(card.full_name)}</td>"
            f"<td>{_esc(card.nickname)}</td>"
            f"<td>{_esc(card.contact_email)}</td>"
            f"<td>{_esc(card.role)}</td></tr>"
            f"<tr><td></td><td colspan=\"4\"><em>{_esc(card.rank_reason)}</em></td></tr>"
        )
    header = (
        "<tr><td><strong>#</strong></td>"
        "<td><strong>Name</strong></td>"
        "<td><strong>Nickname</strong></td>"
        "<td><strong>Email</strong></td>"
        "<td><strong>Role</strong></td></tr>"
    )
    table_body = "\n".join(rows)
    return (
        f"<body>\n<table>\n{header}\n{table_body}\n</table>\n{marker}\n</body>"
    )
```

**Whitespace rule**: `\n` characters between tags are fine. `<br>` in any form is
forbidden — even `<br/>` or `<br />`. The template above uses NO `<br>` anywhere.

[UV-P-colspan: `colspan="4"` attribute survival in Asana html_text | METHOD:
deferred-to-build-probe (G-ii read-back at N5 discharges — if colspan triggers
silent-201 entity-escape, `ContactCardRenderError` is raised before any rep sees the
output; if G-ii passes cleanly at N5, colspan is confirmed safe; no separate probe
required before build) | REASON: A0 confirmed cell width attrs survive (Asana injects
`width="120" data-cell-widths` per T4 story `1216333984133231`) but `colspan`
specifically was not probed; given the silent-201 failure mode, unprobed attributes
must be treated as unproven per A0-pv-probes-report-2026-07-07.md ★orchestrator-addendum]
[CH-03]

### L3 fallback template (`<ul><li>` — used if future Asana change breaks `<table>`)

```python
def _render_l3_list(cards: list[ContactCard], deck_slug: str) -> str:
    marker = f"[{MARKER_PREFIX} deck={deck_slug}]"
    items = [
        f"<li><strong>{card.rank}.</strong> {_esc(card.full_name)}"
        f" ({_esc(card.nickname)}) — {_esc(card.contact_email)}"
        f" — {_esc(card.role)} — <em>{_esc(card.rank_reason)}</em></li>"
        for card in cards
    ]
    return f"<body><ul>\n" + "\n".join(items) + f"\n</ul>\n{marker}\n</body>"
```

### Plain-text fallback (ALWAYS populated — LB-8, mirrors `link_on_play.py:94`)

```python
def _render_plain_text(cards: list[ContactCard], deck_slug: str) -> str:
    marker = f"[{MARKER_PREFIX} deck={deck_slug}]"
    lines = [
        f"{card.rank}. {card.full_name}"
        f" | {card.contact_email or 'no email'}"
        f" | {card.role or 'no role'}"
        f" | {card.rank_reason}"
        for card in cards
    ]
    return "\n".join(lines) + f"\n{marker}"
```

---

## 7. Read-Back Render Assert (G-ii — the load-bearing loudness primitive)

**This guard MUST NOT be dropped or weakened to a warning.** Without it, a `<br>` (or
any future unproven tag) that trips the silent-201 escape produces tag-soup that a human
reads as a garbled card and picks the WRONG receiver = the silent-wrong-outcome failure
class. (A3 AP-A; ADR §8 G-ii; A0-pv-probes-report-2026-07-07.md §UV-P-html: "the
renderer must therefore be verified by read-back round-trip, not by HTTP status".)

```python
class ContactCardRenderError(Exception):
    """Raised when the Asana read-back reveals entity-escaped html_text."""
    pass

async def _assert_render_not_escaped(
    story_gid: str, expected_marker: str, asana_client
) -> None:
    """
    Post → GET story back → assert html_text NOT entity-escaped AND marker present.
    Raises ContactCardRenderError if either check fails.
    """
    story = await asana_client.get_story_async(story_gid)
    html_text = story.html_text or ""
    if "&lt;table" in html_text or "&lt;ul" in html_text:
        raise ContactCardRenderError(
            f"Contact card html_text is entity-escaped (contains '&lt;table' or '&lt;ul'). "
            f"A <br> or unsupported tag triggered Asana's silent 201 entity-escape. "
            f"story_gid={story_gid}"
        )
    if expected_marker not in html_text and expected_marker not in (story.text or ""):
        raise ContactCardRenderError(
            f"Idempotency marker '{expected_marker}' absent from read-back. "
            f"story_gid={story_gid}"
        )
```

**RED twin — fixture with literal `<br>` must be caught BEFORE post by G-i escaping guard.**
The `<br>`-in-fixture test exercises the pre-post escaping path, NOT the post path.
A fixture containing a contact with `full_name = "Dr <br> Smith"` must produce
composed html_text that contains `&lt;br&gt;` — no raw `<br>`. A raw-`<br>` assertion
over the composed html_text must return empty (zero occurrences). The `create_comment`
call is never reached for that payload because the escaping guard processes BEFORE
composition.

Note: the `<br>` escaping guard fires at field-escape time (step 6). The post-level
read-back in G-ii is the second line of defense for any tag that gets through.

---

## 8. Egress Chain Reuse (G-iii)

Reuse existing primitives from `tenant_binding.py:66-69` and `link_on_play.py:62,219-223`.
Apply over the FINAL composed text (card + any link).

```python
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    CANONICAL_ROUTING_ADDR_RE,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import (
    DECK_HOST,
    deck_slug_from_url,
)

def _egress_guard(html_text: str) -> None:
    """
    Refuses posting if the composed text contains a routing address or
    an unverified deck host. Mirrors link_on_play.py:219-223.
    Raises ContactCardEgressRefused on violation.
    """
    if CANONICAL_ROUTING_ADDR_RE.search(html_text):
        raise ContactCardEgressRefused(
            "Composed contact card contains a @appointments.contenteapp.com "
            "routing address. Refusing post."
        )
    # full-domain-literal refusal and DECK_HOST pin follow the same pattern
    # as link_on_play.py:219-223 — extend here if deck URL appears in card text.
```

---

## 9. Marker and Idempotency (G-v)

```python
CONTACT_CARD_MARKER_PREFIX = "autom8y:contact-card"  # DISTINCT from link-on-play's prefix

def _compose_marker(deck_slug: str) -> str:
    return f"[{CONTACT_CARD_MARKER_PREFIX} deck={deck_slug}]"

def _marker_present_in_stories(stories: list, deck_slug: str) -> bool:
    marker = _compose_marker(deck_slug)
    return any(
        marker in (s.html_text or "") or marker in (s.text or "")
        for s in stories
    )
```

Scan pattern: mirrors `link_on_play.py:225-230`. If marker already present →
return `ContactCardResult(outcome="skipped_existing")`. Do not call `create_comment`.

---

## 10. CLI Entrypoint (dry-run-default + --execute)

```python
# contact_synthesis_cli.py  (beside link_on_play.py; mirrors its CLI shape)

@click.command()
@click.argument("play_gid")
@click.option("--deck-slug", required=True)
@click.option("--execute", is_flag=True, default=False,
              help="Actually post the comment. Default: dry-run only.")
def contact_card_on_play(play_gid: str, deck_slug: str, execute: bool) -> None:
    """
    Post a ranked contact card comment to a PLAY task.
    Dry-run by default — use --execute to post.
    """
    result = asyncio.run(
        _contact_card_flow(play_gid, deck_slug, dry_run=not execute)
    )
    click.echo(result)
```

**retry-429-only-never-POST-5xx**: retry on HTTP 429 (rate-limited) only. Never retry
a POST on 5xx (non-idempotent; mirrors `link_on_play.py` retry rule).

---

## 11. Graceful-Degrade Paths [CH-05]

> CH-05 fix: `no_contacts` and `no_usable_contacts` are distinct outcomes.
> `no_usable_contacts` MUST be LOUD (named-reason in CLI output + log). Silently
> returning `no_contacts` when holder subtasks exist but none pass G-vi is a
> false-exclusion failure — it hides the fact that a real person may be present
> but has no email/role on file.

| Condition | Behavior | Outcome token |
|-----------|----------|---------------|
| "Contacts 🧑" holder not found in Business subtasks | Skip card post; no error raised | `no_holder` |
| Holder found; zero subtasks after structural scan | Skip card post; no error raised | `no_contacts` |
| Holder found; ≥1 subtasks found; NONE pass G-vi person-shaped test | LOUD named-reason in CLI output + log; skip card post — NOT silently `no_contacts` | `no_usable_contacts` [CH-05] |
| Idempotency marker already present for this deck_slug | Skip post; return early | `skipped_existing` |
| employees endpoint unavailable (Phase-2) | Degrade to asana-only; do NOT hard-fail | `asana_only_fallback` |
| Compose → G-iii egress guard fires | Raise `ContactCardEgressRefused`; no post | raises |
| Post → G-ii read-back shows entity-escaped html | Raise `ContactCardRenderError` | raises |

The `no_usable_contacts` path must emit something like:
```
ContactCardResult(
    outcome="no_usable_contacts",
    cards=[],
    deck_slug=deck_slug,
    no_usable_reason="N contacts found in holder; none carry contact_email or position"
)
```
The CLI must print this reason string explicitly so an operator can investigate the
data hygiene issue for that office.

---

## 12. GREEN / RED Test Matrix (six guards)

All test fixtures use `origin/main @ 5604789f` entity shapes.

### G-i — HTML escaping

| # | Type | Input | Expected |
|---|------|-------|----------|
| G-i-RED-1 | RED | `full_name = "Dr <br> Smith"` | Composed `html_text` contains `&lt;br&gt;`; zero occurrences of raw `<br>` |
| G-i-RED-2 | RED | `contact_email = "a&b@clinic.com"` | Composed `html_text` contains `a&amp;b@clinic.com` |
| G-i-GREEN-1 | GREEN | `full_name = "José O'Neil"` | Composed contains `José O&#39;Neil`; renders in table cell |

### G-ii — Read-back render assert

| # | Type | Setup | Expected |
|---|------|-------|----------|
| G-ii-RED-1 | RED | Mock `get_story_async` returns `html_text` containing `&lt;table` | `ContactCardRenderError` raised |
| G-ii-RED-2 | RED | Mock `get_story_async` returns `html_text` without idempotency marker | `ContactCardRenderError` raised |
| G-ii-GREEN-1 | GREEN | Mock returns `html_text` containing `<table` and marker | No exception; result is success |

### G-iii — Egress chain

| # | Type | Input | Expected |
|---|------|-------|----------|
| G-iii-RED-1 | RED | `contact_email = "abc123@appointments.contenteapp.com"` | `ContactCardEgressRefused` raised; no `create_comment` call |
| G-iii-GREEN-1 | GREEN | `contact_email = "jane@sandlake.com"` | No refusal; `create_comment` called |

### G-iv — Length cap

| # | Type | Input | Expected |
|---|------|-------|----------|
| G-iv-RED-1 | RED | Synthesize contacts until composed html exceeds cap | Composed html ≤ cap; ends on closed `</table>`; contains "+N more" line |
| G-iv-GREEN-1 | GREEN | Small number of contacts (within cap) | Composed html unchanged; no truncation notice |

Note: exact cap value = UV-P (build-probe discharges). Set a conservative placeholder
constant (e.g., 32000 chars) until the sandbox bisect resolves it. Update constant as
the first post-probe commit.

### G-v — Idempotency

| # | Type | Input | Expected |
|---|------|-------|----------|
| G-v-RED-1 | RED | `--execute` twice for same `deck_slug` | Second call returns `skipped_existing`; `create_comment` called exactly once total |
| G-v-GREEN-1 | GREEN | Different `deck_slug` on same PLAY | Both calls post; two distinct markers present |

### G-vi — Mixed-plane filter

| # | Type | Input | Expected |
|---|------|-------|----------|
| G-vi-RED-1 | RED | Child with `contact_email=None`, `position=None` | Excluded from card |
| G-vi-GREEN-1 | GREEN | Child with `contact_email` set, `position=None` | Included |

#### G-vi supplement fixtures [CH-05]

These fixtures cover the two G-vi misclassification residuals named in the HANDOFF Named
Residuals and ADR §8 G-vi.

| # | Type | Input | Expected |
|---|------|-------|----------|
| G-vi-RED-garbage-with-email | Residual (false-inclusion) | Holder child with `full_name="Sales Process — X Team"`, `contact_email="team@clinic.com"`, `position=None` | INCLUDED in card (person-shaped heuristic passes: has email → Tier-3 boost); `rank_reason` must be non-empty (e.g., "has email on file"); the human picker uses `rank_reason` to recognize a non-person row |
| G-vi-RED-real-person-null-null | Residual (false-exclusion) | Holder child with `full_name="Dr. Patel"`, `contact_email=None`, `position=None`; this is the ONLY child in the holder | Excluded by G-vi (neither email nor role); outcome MUST be `no_usable_contacts` (not `no_contacts`); CLI output must include a named-reason string distinguishing this from the zero-subtasks case |

---

## 13. UV-P Length Discharge Step

Before finalizing `G-iv`'s truncation threshold:

1. In a sandbox Asana workspace, post a comment with `html_text` of known length L.
2. If accepted: increase L; bisect upward until Asana returns an error or silently
   truncates.
3. Record the exact boundary. Update `MAX_CONTACT_CARD_HTML_LENGTH` constant in
   `contact_synthesis.py`.
4. Add a test asserting the constant is set to a non-zero value (smoke-guards against
   accidental reset).

This probe must run BEFORE the build sprint closes. If the probe reveals a very low
limit (< 500 chars), escalate to operator for policy decision on how many contacts to
show in the card vs. the "+N more" notice.

---

## 14. Out of Scope (Phase-1)

- Phase-2 employees cross-plane merge (activates when `GET /employees/by-company/{guid}`
  goes live on autom8y-data and SDK bump is published)
- The `GET /employees/by-company/{guid}` endpoint itself (autom8y-data owns it;
  spec in `SPEC-employees-by-company-endpoint-2026-07-07.md`)
- Any Intercom / Nova account action (`intercom_link` = storage-only field `dna.py:64`;
  no in-code seam for Intercom exists)
- Batch-lane template-infill for CLINIC/LINK brackets (spike §5 remaining legs; not
  blocked on this build)

---

## 15. Result Shape (mirrors `LinkOnPlayResult`)

```python
from dataclasses import dataclass, field
from typing import Literal, Optional

@dataclass
class ContactCardResult:
    outcome: Literal[
        "posted",
        "skipped_existing",
        "no_holder",
        "no_contacts",           # zero holder subtasks after structural scan
        "no_usable_contacts",    # ≥1 subtasks found; none pass G-vi — LOUD path [CH-05]
        "dry_run",
    ]
    story_gid: str | None = None    # set when outcome == "posted"
    cards: list[ContactCard] = field(default_factory=list)
    deck_slug: str = ""
    no_usable_reason: Optional[str] = None  # populated when outcome == "no_usable_contacts"
```

---

## Build errata (B1 D1-D4 + implementation call-site corrections)

Additive-only. Recorded by the 10x-dev build sprint (station B2) where the built code
diverged from the design pseudocode at these call sites. The DESIGN is unchanged; these
are faithful corrections to method names/shapes verified against origin/main @ 5604789f
and the installed `autom8y-core` 4.9.0.

- **D1 (applied)** — traversal calls are `await client.tasks.subtasks_async(gid,
  include_detection_fields=True).collect()` (the `tasks` sub-client + pageable
  `.collect()`; idiom at `business.py:614,698-707`), NOT a bare `client.subtasks_async`.
- **D2 (applied)** — read-back is `await client.stories.get_async(story_gid,
  opt_fields=["html_text", "text"])` (`clients/stories.py:81`). `get_story_async` does
  NOT exist. The `opt_fields` include is load-bearing: without `html_text` in
  opt_fields Asana omits it and G-ii would false-trip.
- **D3 (applied, with correction)** — `detect_entity_type` (`detection/facade.py:357`)
  returns a `DetectionResult`, NOT a bare `EntityType`. The holder match is therefore
  `detect_entity_type(t).entity_type == EntityType.CONTACT_HOLDER`. Imports:
  `from autom8_asana.models.business.detection import detect_entity_type` +
  `from autom8_asana.core.types import EntityType`.
- **D4 (applied)** — the ContactHolder found in the traversal is hydrated via the
  `holder_factory.py:128-130` precedent: `ContactHolder.model_validate(holder_task,
  from_attributes=True)` then `holder._populate_children(raw_contacts)` BEFORE
  `ranked_contacts()` is called.
- **W1 (confirmed)** — `autom8y_core.clients.data_service.DataServiceClient` in the
  installed 4.9.0 (pin `>=4.2.0,<5.0.0`) HAS `get_gid_map_async`. No re-adjudication.
- **get_gid_map shape (correction)** — `get_gid_map_async` takes
  `list[PhoneVerticalPair]` (`autom8y_core.models.PhoneVerticalPair`, fields
  `phone`/`vertical`; E.164-validated) and returns `dict[(phone, vertical) -> gid_str |
  None]` — a Business task-gid STRING directly, not an object with `.task_gid` (§2
  pseudocode `gid_map[...].task_gid` corrected to `gid_map.get((phone, vertical))`).
- **ContactCard/Provenance home (correction)** — sited in the entity layer
  (`models/business/contact.py`) beside `ranked_contacts()`, NOT in
  `contact_synthesis.py`. Siting them in the workflow module would create a circular
  import (that module imports `ContactHolder` from `contact.py`). Entity-layer placement
  also makes `ranked_contacts()` a zero-external-import derivation (strongest AP-F form).
- **Position-weight case (correction)** — §4 `_sort_key` matches `position` case-
  insensitively (`(c.position or "").lower().strip()`); Position enum values are
  Title-case ("Owner"), the weight map keys are lowercase — mirrors `Contact.is_owner`.
- **CLI framework (deviation)** — `argparse` (stdlib), not `click` (§10): `click` is not
  a dependency of autom8y-asana and the zero-new-deps constraint forbids adding it;
  `argparse` is the established sibling idiom (`link_on_play.py`). `main()` is co-located
  in `contact_synthesis.py` (not a separate `contact_synthesis_cli.py`) per that idiom.
- **G-iii domain-literal (correction)** — the egress guard refuses on the routing-domain
  literal `appointments.contenteapp.com` (plus the canonical 36-hex
  `CANONICAL_ROUTING_ADDR_RE` and a DECK_HOST URL pin). §12 G-iii-RED-1's `abc123@…`
  local-part is only 6 hex chars and would NOT match the canonical 36-hex regex; the
  domain-literal arm is what refuses it. This is the "full-domain-literal refusal" in §8.
- **G-i apostrophe entity (test-fixture correction)** — stdlib `html.escape(quote=True)`
  emits the HEX entity `&#x27;` for `'` (not decimal `&#39;` as §12 G-i-GREEN-1 wrote).
- **G-iv length constant** — `MAX_CONTACT_CARD_HTML_LENGTH = 32000` (non-zero
  placeholder). The exact ceiling (UV-P §13) discharges at the N5 sandbox bisect — a
  DOWNSTREAM station requiring a real post, which this build never makes.
- **F-1 Call-1 AMENDED at B5 (major)** — the ratified get_gid_map Call-1 was FALSIFIED
  live in production: the autom8y-core data-service `get_gid_map_async` returns `None`
  for Sand Lake under EVERY vertical candidate (`{dentistry, dental, dentist, none}`);
  live receipts show the PLAY identity leg reads clean (`phone='+14073550608'`,
  `vertical='dentistry'`) but `BusinessRecord.default_vertical_key='none'` (literal
  string), `default_vertical_id=None`, and `gid_map[(phone, v)]=None` for all `v`. The
  gid-map dataset does not cover these offices (vertical keys aren't populated).
  Call-1 is REPLACED with the N0-proven Asana-native bridge (`_business_gid_by_phone`:
  workspace tasks/search by the Office Phone custom field → keep only members of the
  "Businesses" project `1200653012566782`; refuse loudly via `ContactCardBusinessAmbiguous`
  on >1 match; `None` → `no_holder`). Phase-1 is now **pure-Asana**: the
  `DataServiceClient` dependency, `PhoneVerticalPair`, and the `vertical` requirement are
  removed (identity leg = phone only); the S-B seam invariant is strengthened (no
  autom8y-data dependency at Phase-1) and the local M2M-creds wall is removed. Two-sided
  tests added (`TestBusinessBridge`: none→no_holder, multiple→loud refusal
  no create_comment, one→proceeds) + a no-core-import guard. See ADR §4 F-1
  amended-at-build note.
