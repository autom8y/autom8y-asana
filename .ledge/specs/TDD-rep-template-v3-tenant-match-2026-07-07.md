---
type: spec
artifact_subtype: tdd
status: proposed
date: 2026-07-07
initiative: client-onboarding-delivery
slug: rep-template-v3-tenant-match
rung: authored (design altitude only)
scope: micro-TDD (single guard + one composition surface)
implements_spec: rep-onboarding-deck-email-template-v3-2026-07-07.md
amends_adr: ADR-contact-synthesis-card-on-play-2026-07-07.md (§13 v3 Carrier Ratification)
reuses:
  - autom8y_core.helpers.routing.format_routing_address (routing.py:75)
  - CANONICAL_ROUTING_ADDR_RE (tenant_binding.py:66)
  - assert_exclusive_tenant_binding shape (tenant_binding.py:115) — mirrored, not called
mirrors_tdd_shape: link_on_play egress guard (link_on_play.py:224-228) two-sided RED/GREEN
---

# Micro-TDD — v3 Template-Comment Tenant-Match Guard

> **G-RUNG:** everything here is `authored` (design altitude). The build is the next
> station; the operator's `/qa` is the adversarial gate. No production code authored.
> Reserved (design around, never invoke): the client SEND, editing/deleting any human's
> Asana comment, `ASANA_PAT` rotation.

## 1. What is being built (one guard + one surface)

A single fail-closed verifier and the composition surface that calls it. This
REPLACES the blanket "no routing address" refusal **for the template-comment surface
only**; the blanket refusal STAYS on the LINK comment (`link_on_play.py:225`) and the
CARD comment (`contact_synthesis.py:299`) — those carry no address by design (spec §4).

### 1.1 The guard — `assert_template_tenant_match`

**Site (design decision):** `tenant_binding.py`, beside `assert_exclusive_tenant_binding`
(`tenant_binding.py:115`). Rationale: tenant_binding.py is the tenant-binding *verifier*
home and already owns `CANONICAL_ROUTING_ADDR_RE` (`:66`) and the casefold-at-boundary
discipline (`:143-144`). It is NOT the producer, so it MAY import
`format_routing_address` (the producer regex-freedom rule at `tenant_binding.py:29-34`
does not apply to a verifier). The build MAY instead site it in the new
`template_comment.py`; the contract below is site-independent.

**Signature (design):**

```python
def assert_template_tenant_match(*, composed_text: str, office_guid: str) -> None:
    """Assert every routing address in composed_text is THIS office's own.

    own = format_routing_address(office_guid)            # routing.py:75 — RAISES
                                                         # ValueError on malformed guid
    harvested = {a.lower() for a in
                 CANONICAL_ROUTING_ADDR_RE.findall(composed_text)}   # tenant_binding.py:66
    foreign = harvested - {own.lower()}
    if foreign:
        raise TemplateTenantMismatch(... masked(foreign) ...)   # fail-closed
    # presence NOT required: harvested == set() passes (spec §1 clause 2/3)
    return
```

**Predicate (exact):** `harvested − {own.lower()} == ∅`. Equivalently: *no foreign
address*. Presence of `own` is permitted (expected); absence of any address is
permitted; presence of any address ≠ `own` is REFUSED.

**Why SUBSET, not EQUALITY (the deliberate difference from the deck guard):**
`assert_exclusive_tenant_binding` (`tenant_binding.py:115,145`) requires
`harvested == {gated}` — presence AND exclusivity — because the deck's whole purpose
is to carry exactly that address (a deck missing it is a broken product). The template
email only SHOULD carry it (spec §1 clause 1); a valid re-send may omit it. So the
template guard drops the presence half and keeps only the **exclusivity/leak half** —
the crown-jewel. Presence is a checklist SHOULD (spec §5), not a guard MUST.

**Malformed-guid arm (fail-closed by construction):** if `office_guid` is not a
canonical lowercase UUID v4, `format_routing_address` raises `ValueError`
(`routing.py:98-108`) — the guard cannot even compute `own`, so it cannot pass. A
malformed office guid can never yield a "matched" send.

**Refusal type:** new `TemplateTenantMismatch(RuntimeError)` (non-transient; a foreign
address / bad guid reproduces on re-run — callers fail closed, never retry). Masks
foreign addresses to first-8-hex + domain in the message, mirroring
`tenant_binding._mask_addr` (`:105-112`) so an incident breadcrumb never spills a full
wrong-tenant address into logs.

### 1.2 The composition surface — `template_comment.py` (new)

A sibling module of `link_on_play.py` / `contact_synthesis.py` (F-2 idiom: policy in
workflow modules). Mirrors the `link_on_play` shape exactly:

- `compose_template_comment(*, office_guid, deck_url, recipient="[RECIPIENT]") -> str`
  — builds the v3 email body (spec §3) with `own = format_routing_address(office_guid)`
  injected on the `Your routing email is:` line + a DISTINCT idempotency marker
  `[autom8y:rep-template deck={slug}]` (marker-prefix distinct from
  `link_on_play.py:56` `autom8y:link-on-play` and `contact_synthesis.py:76`
  `autom8y:contact-card`, so all three PLAY comments never collide).
- `post_template_comment(client, *, task_gid, office_guid, deck_url, execute=False)` —
  reads → composes → **`assert_template_tenant_match` (step-4 guard, exactly where
  `link_on_play.py:225` sits)** → idempotency scan → ADD-only `create_comment` on
  `--execute` only. Dry-run default. Reuses `deck_slug_from_url` (`link_on_play.py:97`)
  for the host-pinned deck URL and its DECK_HOST pin (`link_on_play.py:62`).

**office_guid provenance — FORK-GUID-SOURCE (Pythia to ratify; recommendation below):**

- **Option A (RECOMMENDED, lean):** read the office's **Company ID** custom field off
  the Business task, pure-Asana — mirroring how `contact_synthesis._office_phone_from_task`
  (`contact_synthesis.py:356-371`) reads the Office Phone field and
  `_business_gid_by_phone` (`:374-414`) resolves the Business task. Keeps the template
  surface in the same Phase-1 pure-Asana seam the contact card already proved live
  (8/8 ACTIVE offices). Load-bearing premise: Company ID ≡ `BusinessRecord.guid`
  (`offer.py:123-130`; dispatch-asserted). Phone→Business resolution is already
  collision-guarded (`ContactCardBusinessAmbiguous`, `contact_synthesis.py:120`).
- **Option B:** `get_business_by_phone_async(office_phone).guid` (the SAME authority the
  deck uses, `workflow.py:568`). Provably identical to the deck's frozen routing
  address; re-adds the autom8y-data dependency contact_synthesis deliberately dropped.

The guard contract is identical under either option; only the anchor's provenance
differs. Recommend A; B is the fallback if the Company-ID ≡ guid invariant is ever
falsified in production.

## 2. Scope boundary (what does NOT change)

- `link_on_play._BODY_TEMPLATE` (`:133-140`) and its egress guard (`:225`) — **UNCHANGED.**
  The LINK comment carries no routing address; its blanket refusal is correct.
- `contact_synthesis._egress_guard` (`:291-313`) — **UNCHANGED.** The CARD carries no
  routing address; its blanket refusal is correct.
- `assert_exclusive_tenant_binding` (`tenant_binding.py:115`) — **UNCHANGED.** The deck
  guard keeps its presence-AND-exclusivity contract; v3 adds a sibling, does not edit it.
- The frozen-deck resolve→freeze pipeline (`workflow.py`, `producer.py`) — **UNCHANGED.**

Net build surface: **1 new guard + 1 new module + 1 new exception**. Zero edits to any
existing surface's invariant.

## 3. Two-sided teeth (RED before, GREEN after — mirrors `link_on_play.py:224-228`)

Guard fixtures. `OWN = 1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com`
(Sand Lake), `FOREIGN = b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com`.

| # | Case | Input | Expected |
|---|------|-------|----------|
| **RED-1** | **foreign address present** | composed text carries `OWN` **and** `FOREIGN` (a stale/hardcoded second-tenant address rode in) | `assert_template_tenant_match(composed_text, office_guid=1b271a63-…)` **RAISES** `TemplateTenantMismatch`; no comment posted. `harvested − {own} = {FOREIGN} ≠ ∅`. |
| **RED-1b** | **foreign ONLY (own absent)** | composed text carries `FOREIGN` only | **RAISES** — the leak fires even without the own address present (defeats a swap: replacing own with foreign must not pass). |
| **RED-2** | **malformed / uuid-mismatch guid** | `office_guid = "not-a-uuid"` (or an uppercase / whitespace-padded / non-v4 variant) | `format_routing_address` **RAISES `ValueError`** (`routing.py:98-108`) before any harvest → guard cannot compute `own` → refuse. Fail-closed on a bad anchor. |
| **RED-2b** | **case-variant foreign** | composed text carries an UPPERCASE-hex foreign address | harvested via `CANONICAL_ROUTING_ADDR_RE` `re.IGNORECASE` (`tenant_binding.py:68`), lowercased at the boundary → still `≠ own` → **RAISES** (never fails-open on a case variant; mirrors `tenant_binding.py:143-144`). |
| **GREEN-1** | **own only** | composed text carries `OWN` once (or many times — mailto + display) | **passes.** `harvested = {own}` → `harvested − {own} = ∅`. |
| **GREEN-2** | **no address** | composed text carries no `@appointments…` address (valid re-send) | **passes.** `harvested = ∅` → `∅ − {own} = ∅`. Presence is SHOULD, not MUST (spec §1 clause 2). |

**Two-sidedness is load-bearing (`non-interference-attestation-discipline`):** the guard
bites RED on a leak (RED-1/1b/2b) AND on a bad anchor (RED-2), and passes GREEN on both
the own-present (GREEN-1) and the address-absent (GREEN-2) states. A guard that only
refused-everything (the old blanket rule) would fail GREEN-1; a guard that only
required-presence would fail GREEN-2 and mis-classify a valid re-send as broken. The
subset predicate is the unique shape that satisfies all six rows.

## 4. Composition-surface tests (integration, dry-run — mirrors link_on_play test shape)

| # | Case | Expected |
|---|------|----------|
| **CS-1** | `compose_template_comment(office_guid=1b271a63-…, deck_url=…/207688021…/)` | body contains `Your routing email is: OWN`; contains the deck URL; contains marker `[autom8y:rep-template deck=207688021de88a6d7231e1d08ea77a85]`; `assert_template_tenant_match` passes (GREEN-1). |
| **CS-2** | `post_template_comment(..., execute=False)` (dry-run) | composes + prints; **no `create_comment`**; guard runs at step-4 position. |
| **CS-3** | idempotency: PLAY already carries the `autom8y:rep-template deck={slug}` marker | outcome `skipped_existing`; no second comment (mirrors `link_on_play.py:235-245`). |
| **CS-4** | a build/config drift injects a FOREIGN address into the body before post | `post_template_comment` raises `TemplateTenantMismatch`; **no post** (the guard is upstream of `create_comment`, exactly like `link_on_play.py:225` precedes `:249`). |

## 5. Evidence (live-verified at design time)

Executed against the real `autom8y_core.helpers.routing.format_routing_address` +
`CANONICAL_ROUTING_ADDR_RE` in the autom8y-asana `.venv` (2026-07-07):

- `format_routing_address("1b271a63-33ff-4135-a92d-f1ef0eeea062")` →
  `1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com`; regex matches it.
  → **GREEN-1 substrate confirmed.**
- Harvest of `"Your routing email is: {OWN} ... stale: {FOREIGN}"` →
  `{OWN, FOREIGN}`; `harvested − {OWN} = {FOREIGN} ≠ ∅`. → **RED-1 substrate confirmed.**
- `format_routing_address("not-a-uuid")` → raises `ValueError`. → **RED-2 substrate
  confirmed.**

These are the guard's inputs proven with the real symbols; the guard itself is the
build station's ~10-line assembly of them.

## 6. Golden Sand Lake composed template-comment (for downstream grooming)

`compose_template_comment(office_guid="1b271a63-33ff-4135-a92d-f1ef0eeea062",
deck_url="https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/")` yields (the
`[RECIPIENT]` and `[CLINIC]` brackets are the human's fills; the routing line and deck
link are system-composed):

```
Subject: Your Sand Lake Dental booking setup — a quick 5-minute walkthrough

Hi [RECIPIENT],

Thanks for getting Sand Lake Dental started. To bring your calendar integration live, here's a short personalized walkthrough — about five minutes, no technical setup on your end:

→ https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/

It covers the one forwarding step that connects your inbound leads to your calendar. For that step, forward your booking emails to your dedicated booking inbox:

Your routing email is: 1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com

Once that's set, new booking requests flow straight into your scheduling, and we'll confirm it's live with a test booking.

Any questions, just reply here.

Best,
Nova

[autom8y:rep-template deck=207688021de88a6d7231e1d08ea77a85]
```

The trailing marker line is the idempotency key (spec §7; not part of the email the
human sends — it scopes the PLAY comment so a re-run skips). The human copies the body
above the marker, fills `[RECIPIENT]` from the contact card, and sends via Intercom as
Nova.

## 7. Build errata (principal-engineer implementation notes)

Deviations from the §1–§4 design, recorded per the build-station discipline. None
weakens a load-bearing invariant; each is noted for the QA gate.

- **Guard order — host-pin position.** §1.2 lists the poster order as
  *compose → assert_template_tenant_match → host-pin → idempotency*. As built, the
  deck-link host pin (`deck_slug_from_url`, https + `DECK_HOST`) runs **first** (step 1,
  mirroring `link_on_play.post_link_on_play` step 1) so a foreign-host URL fails fast
  before any live read, AND is re-applied inside `compose_template_comment` (the trailing
  marker needs the slug, mirroring `link_on_play.compose_comment_text`). The load-bearing
  invariants are unchanged: `assert_template_tenant_match` runs over the FINAL composed
  text before idempotency/post, and the deck link is host-pinned before it appears in any
  posted text.
- **Preflight dropped for this surface.** `link_on_play._preflight` (PLAY-name + ACTIVE
  section membership) is NOT called by `post_template_comment`. The template poster's
  fail-closed layers are the host pin, the Company-ID guid resolution, the tenant-match
  crown-jewel guard, the slug-scoped idempotency, and the read-back — the caller supplies
  the correct PLAY `task_gid`. (The `/qa` matrix does not gate a membership preflight for
  this surface; the tenant-match guard, not section membership, is where the value
  concentrates.)
- **Malformed-guid at the poster boundary surfaces as `TemplateTenantMismatch`.**
  `compose_template_comment` raises a raw `ValueError` on a malformed guid (never a
  plausible-but-wrong address); the poster catches it and re-raises the guard's refusal
  type (`TemplateTenantMismatch`, message contains "malformed office guid") so callers
  fail closed on ONE refusal type. `assert_template_tenant_match` independently wraps the
  same `ValueError` (its bad-anchor arm), so the guid is fail-closed whether reached via
  compose or via a direct guard call.
- **CLI flags.** The CLI uses `--task-gid` + `--deck-url` (+ optional `--office-guid`
  override and `--clinic`) rather than a `play_gid` positional + `--deck-slug`. `--deck-url`
  keeps the host pin a genuine runtime guard (exercised by the QA matrix's bad-host case);
  `--office-guid` omitted triggers the pure-Asana Company-ID resolution (Option A). Dry-run
  is the default; `--execute` is the sole mutating mode. Not `/qa`-gated (no CLI test).

## 8. Supersession coherence (CH-02)

- v2 spec (`rep-onboarding-deck-email-template-v2-2026-07-07.md`) carries a SUPERSEDED
  banner + `status: superseded` / `superseded_by:` frontmatter pointing to v3.
- `link_on_play._BODY_TEMPLATE` template-pointer flipped v2 → v3 (the deck LINK comment
  now points reps at the v3 carrier template). No egress invariant changes; no test
  asserted the filename.
- ADR-contact-synthesis-card-on-play-2026-07-07 §13 (v3 Carrier Ratification) lands with
  this build as the design authority (additive amendment; §§1–12 preserved verbatim).
