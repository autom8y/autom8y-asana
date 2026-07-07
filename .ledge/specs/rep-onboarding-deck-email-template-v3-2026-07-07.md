---
type: spec
status: proposed
date: 2026-07-07
initiative: client-onboarding-delivery
artifact_class: rep-outbound-template
version: v3
supersedes: rep-onboarding-deck-email-template-v2-2026-07-07.md
amending_adr: ADR-contact-synthesis-card-on-play-2026-07-07.md (see §13 v3 Carrier Ratification amendment)
rung: authored (design altitude only)
change_reason: >
  Send-day ratification (operator ruling, 2026-07-07): the first client send
  (Nova -> Dr. Ziyad) deliberately INCLUDED the client's own routing address
  `1b271a63-...@appointments.contenteapp.com`, which v1/v2's carrier checklist
  FORBADE ("Nothing in your email mentions an @appointments.contenteapp.com
  address"). The operator ruled that inclusion CORRECT: Dr. Ziyad needs the
  address to complete the forwarding step the walkthrough teaches. v3 REVERSES
  the blanket no-address rule and REPLACES it with a tenant-match hardening:
  the address in the email MUST be provably THIS office's own (leak-by-
  containment crown-jewel), never another tenant's, proven by a two-sided
  tenant-match guard, never by a checklist line alone.
---

# Rep outbound: "Here's your setup walkthrough" — v3

> **v3 change summary (send-day ratification, 2026-07-07):**
> - **Doctrine flip.** v1/v2 rule *"Nothing in your email mentions an
>   `@appointments.contenteapp.com` address"* (v2 checklist item 3,
>   `rep-onboarding-deck-email-template-v2-2026-07-07.md:78-80`) is **REVERSED**.
>   The email **SHOULD** include the client's **own** routing address — the client
>   needs it to complete the one forwarding step the walkthrough teaches.
> - **The reversal is CONDITIONAL on a hardening.** The address that appears MUST
>   be **tenant-matched to this office's guid**: it MUST equal
>   `format_routing_address(office_guid)` and MUST NOT be any other tenant's
>   routing address. This is enforced by a **two-sided tenant-match guard**
>   (`TDD-rep-template-v3-tenant-match-2026-07-07.md`), not by a checklist line.
> - **System provides the address, never the rep.** The routing address is
>   SYSTEM-COMPOSED from the office guid via the SDK routing helper
>   (`autom8y_core.helpers.routing.format_routing_address`, `routing.py:75`), the
>   same guid the deck and the contact card use. The rep never hand-types it
>   (anti-fat-finger).
> - **Everything else from v2 is preserved verbatim:** sender is **Nova /
>   support@contenteapp.com** via Intercom (P-NOVA constant); receiver selection
>   is the rep's call from the **contact card** on the PLAY; link, not attachment.

---

## 1. The doctrine flip, precisely stated

v3 replaces the v2 carrier rule *"no `@appointments…` address in the email"* with a
**three-clause routing-address contract**:

1. **SHOULD-include.** The email SHOULD carry the client's own routing address on a
   dedicated `Your routing email is:` line — it is the address the client forwards
   their booking emails to, the one step the walkthrough exists to enable.
2. **MUST tenant-match.** Every `{uuid}@appointments.contenteapp.com` routing address
   present in the composed text MUST equal `format_routing_address(office_guid)` for
   THIS office's guid. (Present-and-own is the expected state; absent is also
   permissible — see §3.)
3. **MUST-NOT leak.** The composed text MUST NOT contain any routing address that
   belongs to a **different** guid. A single foreign address ⇒ fail-closed refuse
   (the leak-by-containment crown-jewel). This is the load-bearing invariant.

The v1/v2 blanket "no routing address" rule survives **only** on surfaces that
legitimately carry no address (§4).

---

## 2. Fill these (the only rep effort)

- `[RECIPIENT]` — the person's name **you** choose to send to. Pick from the
  **contact card comment** on this clinic's Calendar Integration PLAY (ranked
  candidates; *the system never picks the receiver*). Unchanged from v2.
- `[CLINIC]` — the clinic / business name (matches the deck cover — verify it).

> **System-provided (do NOT type these — anti-fat-finger):**
> - **Deck link** — the hosted `https://decks.cntently.com/<slug>/` URL from this
>   clinic's PLAY (the link-on-play comment carries it).
> - **`Your routing email is:` line** — SYSTEM-COMPOSED from this office's guid via
>   `format_routing_address(office_guid)`. It arrives pre-filled in the
>   template-comment on the PLAY. If you do not see a system-composed routing line,
>   **do not invent one** — a missing line means the guard has not run; escalate,
>   never hand-type a routing address.

> **Sender constants (P-NOVA, do not change):**
> Sign-off = **Nova**. Sending address = **support@contenteapp.com** via Intercom.
> You are operating the Nova persona for this send; the send is human-gated.

---

## 3. The email (copy the system-composed template-comment, fill `[RECIPIENT]`, send via Intercom as Nova)

> **Subject:** Your [CLINIC] booking setup — a quick 5-minute walkthrough

> Hi [RECIPIENT],
>
> Thanks for getting [CLINIC] started. To bring your calendar integration live,
> here's a short personalized walkthrough — about five minutes, no technical setup
> on your end:
>
> → **[DECK LINK]**
>
> It covers the one forwarding step that connects your inbound leads to your
> calendar. For that step, forward your booking emails to your dedicated booking
> inbox:
>
> **Your routing email is:** [ROUTING EMAIL — system-composed]
>
> Once that's set, new booking requests flow straight into your scheduling, and
> we'll confirm it's live with a test booking.
>
> Any questions, just reply here.
>
> Best,
> Nova

> **Presence is SHOULD, not MUST.** If a particular send legitimately omits the
> routing line (e.g. a re-send after the client already forwarded), the email is
> still valid — the guard passes on zero addresses (§4, TDD GREEN-2). What is never
> valid is a **foreign** address (§1 clause 3).

---

## 4. Which surface gets which rule (LINK vs TEMPLATE vs CARD)

Three PLAY-comment surfaces exist. v3 changes the rule for **exactly one**.

| Surface | Composer (file:line) | Carries a routing address? | Rule under v3 |
|---------|----------------------|----------------------------|---------------|
| **LINK comment** | `link_on_play.py` `_BODY_TEMPLATE` `:133-140`, `compose_comment_text:143` | No — deck URL + pointer to this template only | **BLANKET no-address STAYS** (`link_on_play.py:225` egress guard; U2 invariant). Unchanged. |
| **CARD comment** | `contact_synthesis.py` `compose_card:265`, `_egress_guard:291` | No — contact names/emails only | **BLANKET no-address STAYS** (`contact_synthesis.py:299` G-iii). Unchanged. |
| **TEMPLATE comment** *(new surface)* | NEW `template_comment.py` (build station) | **Yes, by design** — the `Your routing email is:` line | **TENANT-MATCH guard REPLACES the blanket refusal** for this surface only (TDD §Guard). |

The blanket "no routing address" refusal is correct **because those two surfaces
carry none**. The template surface is the only one that carries the address by
design, and it earns the tenant-match guard instead of a blanket ban. No existing
surface's invariant is weakened.

---

## 5. Before you hit send — hardened 20-second check

- ☐ The link **opens to [CLINIC]'s** guide (open it once; check the clinic name on
  the cover).
- ☐ It's a **link, not an attachment**.
- ☐ **The `Your routing email is:` line is present and is SYSTEM-COMPOSED** — it came
  pre-filled on the PLAY template-comment; you did not type it. *(Replaces the v2
  "no `@appointments…` address" item.)*
- ☐ **The routing address is THIS office's own.** Confirm the local-part (the part
  before `@`) matches this office's guid as shown on the PLAY template-comment. If it
  differs, or if two different `@appointments…` addresses appear, **STOP** — that is a
  tenant leak; escalate, do not send. *(The system guard already refuses this before
  the comment is posted; this checkbox is the human backstop, not the primary
  control.)*
- ☐ You are **sending as Nova from support@contenteapp.com** via Intercom.
- ☐ Recipient is the person **you** determined from the contact card — the system
  didn't pick one.

---

## 6. Why these rules (the *why* behind the *what*)

- **Include the routing address** — the client cannot complete the forwarding step
  without it. Withholding it (v1/v2) meant the client had to hunt inside the deck for
  the one address the whole email exists to deliver. The send-day ratification made
  the address a first-class, labelled line.
- **System composes it, never the rep** — a hand-typed routing address is one
  transposed hex digit away from silently routing another clinic's bookings. The SDK
  helper `format_routing_address(office_guid)` (`routing.py:75`) derives it
  deterministically from the office guid and **raises `ValueError` on any malformed
  guid** (`routing.py:98-108`) — it never emits a plausible-but-wrong address.
- **Tenant-match, not a checklist line** — "the address is your office's own" is a
  crown-jewel invariant (leak-by-containment). Crown-jewels are proven by a guard that
  fails closed, never by a human remembering to check a box. The guard harvests every
  `@appointments…` address in the composed text (`CANONICAL_ROUTING_ADDR_RE`,
  `tenant_binding.py:66`) and refuses if any is not this office's own — the same
  discipline `assert_exclusive_tenant_binding` (`tenant_binding.py:115`) already
  applies to the frozen deck bytes, now applied to the email text.
- **Nova / support@contenteapp.com** — unchanged P-NOVA ruling: receiver selection is
  where value concentrates; the sender is a constant.

---

## 7. The system-provides-tenant-matched rule (build contract)

The routing address on the template-comment is produced by this chain, entirely
system-side:

1. Resolve the office's guid (`office_guid`) — the office's **Company ID** custom
   field (`business.py:263` `company_id = TextField()`; `dataframes/schemas/
   business.py:13` `source="cf:Company ID"`; the office guid per `offer.py:123-130`).
   `office_guid` for Sand Lake = `1b271a63-33ff-4135-a92d-f1ef0eeea062`.
2. Compose `own = format_routing_address(office_guid)` (`routing.py:75`). For Sand
   Lake this is `1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com`
   (live-verified, TDD §Evidence).
3. Inject `own` into the `Your routing email is:` line of the composed comment text.
4. **Guard before posting:** harvest every routing address in the composed text and
   refuse fail-closed if any ≠ `own` (§1 clause 3). Only then post the comment.

The rep consumes the *output* of this chain. The rep never runs step 2, never sees a
guid, never types an address.

---

## 8. Golden Sand Lake instance (for downstream grooming)

- **office_guid (Company ID):** `1b271a63-33ff-4135-a92d-f1ef0eeea062`
- **deck slug:** `207688021de88a6d7231e1d08ea77a85`
- **deck link:** `https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/`
- **routing email (system-composed):**
  `1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com`
- **PLAY task:** `1215823342887129` (Sand Lake Dental)

The exact composed template-comment text for this instance is carried in the
architect's final message and in `TDD-rep-template-v3-tenant-match-2026-07-07.md`
§Golden so the downstream grooming can post the golden v3 comment.
