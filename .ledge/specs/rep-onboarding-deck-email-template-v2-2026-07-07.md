---
type: spec
status: proposed
date: 2026-07-07
initiative: client-onboarding-delivery
artifact_class: rep-outbound-template
version: v2
supersedes: rep-onboarding-deck-email-template-2026-07-06.md
amending_adr: ADR-contact-synthesis-card-on-play-2026-07-07.md
change_reason: >
  P-NOVA operator ruling (2026-07-07): the assigned rep is NOT the sender.
  Sender = Nova persona / support@contenteapp.com / Intercom, human sign-in, manual sends.
  The "send from the address the clinic recognizes — not a system address" rule in v1 was
  WRONG for the real flow. REP-NAME and SEND-FROM are now constants, not brackets.
  RECIPIENT is paired with the ranked contact card comment posted to the PLAY.
---

# Rep outbound: "Here's your setup walkthrough" — v2

> **v2 change summary (P-NOVA, 2026-07-07):**
> - Sender is always **Nova / support@contenteapp.com** via Intercom — a constant, not
>   a bracket you fill. The v1 instruction "send from the address the clinic recognizes"
>   is superseded by this ruling.
> - `[REP NAME]` sign-off = **Nova** (constant).
> - `[SEND FROM]` = **support@contenteapp.com** (constant; Intercom human-gated send).
> - `[RECIPIENT]` — still your choice; now paired with the **contact card** posted to the
>   Calendar Integration PLAY in Asana. That card shows ranked contacts for the office.
>   The system surfaces candidates; **you** pick the receiver.
> - All other rules (deck link source, carrier-safety checklist, no `@appointments…` in
>   email) are **preserved verbatim** from v1.

---

## Fill these (the only rep effort)

- `[RECIPIENT]` — the person's name **you** choose to send to. Pick from the **contact
  card comment** posted to this clinic's Calendar Integration PLAY in Asana. The card
  shows ranked contacts for this office. *The system never picks — that's your account-
  contact call.*
- `[CLINIC]` — the clinic / business name (matches the name on the deck's cover — verify
  it).
- `[DECK LINK]` — the hosted URL from **this clinic's** Calendar Integration PLAY
  (`https://decks.cntently.com/<slug>/`).

> **Sender constants (do not change):**
> Sign-off = **Nova**. Sending address = **support@contenteapp.com** via Intercom.
> These are fixed — you are operating the Nova persona for this send.

---

## The email (copy, fill the three brackets, send via Intercom as Nova)

> **Subject:** Your [CLINIC] booking setup — a quick 5-minute walkthrough

> Hi [RECIPIENT],
>
> Thanks for getting [CLINIC] started. To bring your calendar integration live, here's a
> short personalized walkthrough — about five minutes, no technical setup on your end:
>
> → **[DECK LINK]**
>
> It covers the one forwarding step that connects your inbound leads to your calendar.
> Once that's set, new booking requests flow straight into your scheduling, and we'll
> confirm it's live with a test booking.
>
> Any questions, just reply here.
>
> Best,
> Nova

---

## Before you hit send — 20-second check

- ☐ The link **opens to [CLINIC]'s** guide (open it once; check the clinic name on the
  cover).
- ☐ It's a **link, not an attachment**.
- ☐ **Nothing in your email mentions an `@appointments.contenteapp.com` address.** The
  guide teaches that forwarding step *inside* — it must never appear in the carrier email
  (that would defeat the privacy fix and confuse the client).
- ☐ You are **sending as Nova from support@contenteapp.com** via Intercom — not from a
  personal rep address.
- ☐ Recipient is the person **you** determined from the contact card on the PLAY — the
  system didn't pick one.

---

## Why these rules (the *why* behind the *what*)

- **Link, not attachment** — attachments trip B2B spam filters and render poorly on
  mobile; the hosted link is clean, updatable, and byte-proven correct.
- **No recipient inference** — the contact card surfaces ranked candidates from the
  office's Contacts plane; you hold the relationship and know who signs / who acts at the
  clinic. The card informs; you determine.
- **No `@appointments…` in the email** — the mailbox belongs in the guide (where the
  client sets up forwarding), never in the outreach; keeping it out of the carrier is the
  privacy guarantee.
- **Nova / support@contenteapp.com** — the sending identity is the AI-VA persona, not a
  personal rep address. Intercom is the channel; the send is human-gated (you click
  send). This is the P-NOVA ruling: receiver selection is where the value concentrates;
  the sender is a constant.
